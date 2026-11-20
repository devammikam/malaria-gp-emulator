"""protocol.json (protocol-v1) must agree with design.py and with itself."""
import hashlib
import json
from pathlib import Path

import numpy as np
import pytest

import design

ROOT = Path(__file__).resolve().parents[1]
P = json.loads((ROOT / "protocol.json").read_text(encoding="utf-8"))


def candidate_eirs():
    return design.log_grid(np.arange(31) / 30)


def test_domain_matches_design():
    assert P["domain"]["eir_min"] == design.EIR_MIN
    assert P["domain"]["eir_max"] == design.EIR_MAX
    assert tuple(P["domain"]["options_net_coverage"]) == design.NETS
    assert P["simulator"]["horizon_days"] == design.HORIZON_DAYS
    assert P["simulator"]["burn_days"] % design.CAMPAIGN_CYCLE == 0


def test_seed_bases_match_design_and_are_disjoint():
    bases = P["seeds"]["bases"]
    for name, base in design.SEED_BASE.items():
        assert bases[name] == base
    spacing = design.MAX_CONTEXTS * 1000
    values = sorted(bases.values())
    assert all(b - a >= spacing for a, b in zip(values, values[1:]))


def test_candidates_cover_training_and_avoid_tune_and_audit():
    parts = design.partition_eirs()
    cand = np.log(candidate_eirs())
    for eir in np.log(parts["train"]):
        assert np.abs(cand - eir).min() < 1e-6
    for name in ("tune", "audit"):
        gaps = np.abs(cand[:, None] - np.log(parts[name])[None])
        assert gaps.min() > 1e-3, name


def test_lambda_grids_and_delta():
    d = P["decision"]
    primary = np.linspace(d["lambda_primary"]["start"], d["lambda_primary"]["stop"],
                          d["lambda_primary"]["count"])
    assert len(primary) == 21 and np.isclose(primary[1], 0.05)
    fine = np.linspace(d["lambda_fine_secondary"]["start"], d["lambda_fine_secondary"]["stop"],
                       d["lambda_fine_secondary"]["count"])
    assert np.isclose(fine[1] - fine[0], 0.01)
    assert d["delta_primary"] == 0.01 and d["delta_sensitivity"] == [0.005, 0.02]


def test_budget_arithmetic():
    b = P["budget"]
    adaptive = b["adaptive_blocks"] * b["block_runs"]
    assert adaptive <= b["adaptive_cap_runs"]
    assert b["checkpoints_blocks"][-1] == b["adaptive_blocks"]
    assert b["direct_total_runs"] == b["initial_runs"] + adaptive
    initial_direct = 12 * 3 * b["direct_initial_seeds_per_config"]
    assert (b["direct_total_runs"] - initial_direct) % b["block_runs"] == 0


def test_compute_plan_under_ceiling():
    c = P["compute_plan_cpu_hours"]
    total = sum(v for k, v in c.items() if k not in ("seconds_per_run_measured", "ceiling"))
    assert total <= c["ceiling"]
    assert c["audit"] == pytest.approx(720 * c["seconds_per_run_measured"] / 3600, abs=0.1)


def test_research_manifest_hash_matches_committed_file():
    path = ROOT / "manifests" / "research_p10000_b3285.csv"
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    assert digest == P["partitions"]["research_manifest_sha256"]
    assert digest == hashlib.sha256(
        design.research_manifest(10000, 3285).to_csv(index=False, lineterminator="\n")
        .encode()).hexdigest()
