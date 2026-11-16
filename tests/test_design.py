import numpy as np
import pandas as pd
import pytest

import design


@pytest.fixture(scope="module")
def research():
    return design.research_manifest(population=5000, burn=730)


@pytest.fixture(scope="module")
def pilot():
    return design.pilot_manifest()


def test_run_ids_unique(research, pilot):
    assert research.run_id.is_unique
    assert pilot.run_id.is_unique


def test_planned_run_counts(research):
    counts = research.partition.value_counts()
    assert counts["train"] == 16 * 3 * 4 == 192
    assert counts["audit"] == 12 * 3 * 20 == 720


def test_seeds_shared_across_net_options(research, pilot):
    for m in (research, pilot):
        per_run = m.groupby(["partition", "context", "rep", "population", "burn_days"])
        assert (per_run.seed.nunique() == 1).all()
        assert (per_run.net.nunique() == len(design.NETS)).all()


def test_seeds_disjoint_across_contexts_and_partitions(research, pilot):
    combined = pd.concat([research, pilot])
    owners = combined.groupby("seed")[["partition", "context"]].nunique()
    assert (owners.partition == 1).all() and (owners.context == 1).all()


def test_audit_never_reuses_training_seeds_or_eirs(research):
    train = research[research.partition == "train"]
    audit = research[research.partition == "audit"]
    assert not set(train.seed) & set(audit.seed)
    gaps = np.abs(np.log(audit.eir.unique())[:, None] - np.log(train.eir.unique())[None])
    assert gaps.min() > 1e-3


def test_audit_inside_training_range(research):
    train = research[research.partition == "train"].eir
    audit = research[research.partition == "audit"].eir
    assert train.min() == design.EIR_MIN and train.max() == design.EIR_MAX
    assert audit.between(train.min(), train.max(), inclusive="neither").all()


def test_manifest_is_deterministic():
    a = design.research_manifest(5000, 730)
    b = design.research_manifest(5000, 730)
    pd.testing.assert_frame_equal(a, b)


def test_seed_plan_rejects_overflow():
    with pytest.raises(ValueError):
        design.seed_for("train", design.MAX_CONTEXTS, 1)
    with pytest.raises(ValueError):
        design.seed_for("train", 0, design.MAX_REPS)


def test_cpu_estimate_matches_demonstration():
    demo = pd.DataFrame({"population": [500], "burn_days": [730], "horizon_days": [1825]})
    assert design.estimated_cpu_hours(demo) * 3600 == pytest.approx(8.13)
