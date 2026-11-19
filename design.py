"""Scenario manifests for native malariasimulation runs (decisions D4, D5).

Usage:
    python design.py pilot --out manifests
    python design.py pilot-burnin --out manifests
    python design.py research --population 10000 --burn 3285 --out manifests

The manifest lists every simulator run, with one row per run. The R runner
(native_runner.R) reads it, so the manifest is the single archived record of
inputs and seeds.

Seed plan (D4): seed = partition base + 1000 * context index + replicate.
All net options in the same context and replicate share a seed (common random
numbers). Different contexts and partitions never share a seed.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

EIR_MIN, EIR_MAX = 5.0, 50.0
NETS = (0.3, 0.5, 0.7)
HORIZON_DAYS = 1825
SEED_BASE = {"pilot": 1_000_000, "train": 2_000_000, "tune": 3_000_000,
             "audit": 4_000_000, "adaptive": 5_000_000}
MAX_CONTEXTS = 1000          # contexts per partition before seeds would collide
MAX_REPS = 1000              # replicates per context before seeds would collide

# Runtime model from the 18-run demonstration: ~8.1 s per run at 500 people
# for 2555 simulated days. Assumes cost scales with people x days (checked in M2).
SECONDS_PER_PERSON_DAY = 8.13 / (500 * 2555)


def log_grid(fractions):
    """Map fractions of [0, 1] onto the log-EIR range."""
    lo, hi = np.log(EIR_MIN), np.log(EIR_MAX)
    return np.round(np.exp(lo + np.asarray(fractions) * (hi - lo)), 6)


def partition_eirs():
    """Training, tuning and audit EIR settings, interleaved on the log scale.

    Train: 16 points including both ends, so audit settings are never
    extrapolations. Tune: 6 midpoints. Audit: 12 midpoints. The fractions
    i/15, (2j+1)/12 and (2k+1)/24 never coincide, so the sets are disjoint.
    """
    return {"train": log_grid(np.arange(16) / 15),
            "tune": log_grid((2 * np.arange(6) + 1) / 12),
            "audit": log_grid((2 * np.arange(12) + 1) / 24)}


def seed_for(partition, context, rep):
    if not 0 <= context < MAX_CONTEXTS or not 1 <= rep < MAX_REPS:
        raise ValueError(f"context {context} or rep {rep} outside the seed plan")
    return SEED_BASE[partition] + 1000 * context + rep


def rows_for(partition, eirs, reps, population, burn, extra=None):
    rows = []
    for context, eir in enumerate(eirs):
        for net in NETS:
            for rep in range(1, reps + 1):
                rows.append({
                    "run_id": f"{partition}-c{context:02d}-n{net:.1f}-p{population}"
                              f"-b{burn}-r{rep:02d}",
                    "partition": partition, "context": context, "eir": float(eir),
                    "net": net, "rep": rep, "seed": seed_for(partition, context, rep),
                    "population": population, "burn_days": burn,
                    "horizon_days": HORIZON_DAYS, **(extra or {})})
    return rows


def pilot_manifest(reps=10):
    """M2 pilot: low/medium/high EIR x 3 nets x population x burn-in.

    Population and burn-in variants reuse the same seeds, so their effects are
    compared on paired runs.
    """
    eirs = log_grid([0, .5, 1])  # 5, 15.81, 50
    rows = []
    for population in (500, 5000, 10000):
        for burn in (730, 1460):
            rows += rows_for("pilot", eirs, reps, population, burn)
    return pd.DataFrame(rows)


CAMPAIGN_CYCLE = 1095  # days between net campaigns (D5)


def pilot_burnin_manifest(population=10000, burns=(2190, 3285), reps=10):
    """Follow-up burn-in pilot (D9): whole campaign cycles, same seeds as the pilot."""
    if any(b % CAMPAIGN_CYCLE for b in burns):
        raise ValueError("Burn-ins must be whole campaign cycles (D9)")
    rows = []
    for burn in burns:
        rows += rows_for("pilot", log_grid([0, .5, 1]), reps, population, burn)
    return pd.DataFrame(rows)


def research_manifest(population, burn, reps=None):
    if burn % CAMPAIGN_CYCLE:
        raise ValueError(f"Burn-in {burn} is not a multiple of {CAMPAIGN_CYCLE} days (D9)")
    reps = reps or {"train": 4, "tune": 4, "audit": 20}
    rows = []
    for partition, eirs in partition_eirs().items():
        rows += rows_for(partition, eirs, reps[partition], population, burn)
    return pd.DataFrame(rows)


def estimated_cpu_hours(manifest):
    person_days = manifest.population * (manifest.burn_days + manifest.horizon_days)
    return float((person_days * SECONDS_PER_PERSON_DAY).sum() / 3600)


def write(manifest, out, name):
    out.mkdir(parents=True, exist_ok=True)
    path = out / f"{name}.csv"
    manifest.to_csv(path, index=False, lineterminator="\n")
    info = {"manifest": path.name, "runs": len(manifest),
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "estimated_cpu_hours": round(estimated_cpu_hours(manifest), 1),
            "runs_by_partition": manifest.partition.value_counts().to_dict(),
            "seed_plan": "seed = base[partition] + 1000*context + rep; "
                         "shared across net options (D4)",
            "bases": SEED_BASE}
    (out / f"{name}.json").write_text(json.dumps(info, indent=2) + "\n")
    return info


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("kind", choices=["pilot", "pilot-burnin", "research"])
    parser.add_argument("--out", type=Path, default=Path("manifests"))
    parser.add_argument("--population", type=int, default=10000)
    parser.add_argument("--burn", type=int, default=3285)
    parser.add_argument("--reps", type=int, default=10, help="pilot replicates")
    args = parser.parse_args()
    if args.kind == "pilot":
        info = write(pilot_manifest(args.reps), args.out, "pilot")
    elif args.kind == "pilot-burnin":
        info = write(pilot_burnin_manifest(args.population, reps=args.reps), args.out,
                     "pilot_burnin")
    else:
        info = write(research_manifest(args.population, args.burn), args.out,
                     f"research_p{args.population}_b{args.burn}")
    print(json.dumps(info, indent=2))


if __name__ == "__main__":
    main()
