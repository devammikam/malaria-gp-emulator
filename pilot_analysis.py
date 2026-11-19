"""M2 pilot analysis: apply the pre-registered D8 rules (docs/DECISIONS.md).

Usage: python pilot_analysis.py [--runs %USERPROFILE%/malaria-runs/pilot] [--out results/pilot]
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

import design

DELTA = 0.01
AUDIT_SEEDS, AUDIT_CELLS = 20, 12 * 3
BUDGET_CPU_HOURS = 100
ADAPTIVE_RUNS = 4 * 64  # up to 64 adaptive runs for each of 4 adaptive methods
KEYS = ["eir", "net", "population", "burn_days"]


def load(runs: Path) -> pd.DataFrame:
    shards = sorted(runs.glob("summary_shard*.csv"))
    data = pd.concat([pd.read_csv(f) for f in shards], ignore_index=True)
    if data.run_id.duplicated().any():
        raise ValueError("Duplicate run_id across shards")
    return data.sort_values(["population", "burn_days", "eir", "net", "rep"]).reset_index(drop=True)


def runtime_model(data):
    """cpu_seconds = a + b * population * simulated days (least squares)."""
    x = data.population * (data.burn_days + data.horizon_days)
    b, a = np.polyfit(x, data.cpu_seconds, 1)
    return {"intercept_s": float(a), "s_per_person_day": float(b),
            "r2": float(np.corrcoef(x, data.cpu_seconds)[0, 1] ** 2)}


def projected_cpu_hours(model, population, burn):
    # Run count doesn't depend on burn-in, so count it with any valid burn-in.
    m = design.research_manifest(population, 2 * design.CAMPAIGN_CYCLE)
    days = burn + design.HORIZON_DAYS
    runs = len(m) + ADAPTIVE_RUNS
    return runs * (model["intercept_s"] + model["s_per_person_day"] * population * days) / 3600


def burn_in_check(data, population):
    """D8.1: paired difference (longer - shorter burn-in) per EIR x net cell."""
    d = data[data.population == population]
    short, long_ = sorted(d.burn_days.unique())
    wide = d.pivot_table(index=["eir", "net", "rep"], columns="burn_days",
                         values="mean_lm_prevalence_2to10")
    diff = (wide[long_] - wide[short]).rename("diff").reset_index()
    rows = []
    for (eir, net), g in diff.groupby(["eir", "net"]):
        n, m, s = len(g), g["diff"].mean(), g["diff"].std(ddof=1)
        h = stats.t.ppf(.975, n - 1) * s / np.sqrt(n)
        rows.append({"eir": eir, "net": net, "mean_diff": m, "ci_low": m - h, "ci_high": m + h})
    table = pd.DataFrame(rows)
    ok = bool(((table.ci_low > -DELTA / 2) & (table.ci_high < DELTA / 2)).all())
    return ok, table


def cell_sd(data):
    return data.groupby(KEYS).mean_lm_prevalence_2to10.agg(
        mean="mean", sd=lambda v: v.std(ddof=1), n="count").reset_index()


def audit_halfwidth(sd):
    return float(stats.t.ppf(1 - .05 / (2 * AUDIT_CELLS), AUDIT_SEEDS - 1) * sd / np.sqrt(AUDIT_SEEDS))


def curvature(d):
    """Per-seed second difference p(.3) - 2p(.5) + p(.7); seeds are shared across nets."""
    wide = d.pivot_table(index=["eir", "rep"], columns="net", values="mean_lm_prevalence_2to10")
    c = (wide[0.3] - 2 * wide[0.5] + wide[0.7]).rename("c").reset_index()
    out = c.groupby("eir").c.agg(curvature="mean", se=lambda v: v.std(ddof=1) / np.sqrt(len(v)))
    out["ratio"] = out.curvature / out.se
    return out.reset_index()


def crn(d):
    wide = d.pivot_table(index=["eir", "rep"], columns="net", values="mean_lm_prevalence_2to10")
    rows = []
    for eir, g in wide.groupby(level="eir"):
        a, b = g[0.3], g[0.7]
        rows.append({"eir": eir, "corr_0.3_0.7": float(np.corrcoef(a, b)[0, 1]),
                     "sd_contrast_paired": float((a - b).std(ddof=1)),
                     "sd_contrast_if_independent": float(np.sqrt(a.var(ddof=1) + b.var(ddof=1)))})
    return pd.DataFrame(rows)


def decide(data):
    model = runtime_model(data)
    sds = cell_sd(data)
    candidates = []
    for population in sorted(data.population.unique()):
        burn_ok, burn_table = burn_in_check(data, population)
        short, long_ = sorted(data[data.population == population].burn_days.unique())
        burn = int(short if burn_ok else long_)
        cell = sds[(sds.population == population) & (sds.burn_days == burn)].sd
        max_sd, mean_sd = float(cell.max()), float(cell.mean())
        hw = audit_halfwidth(max_sd)
        cpu = projected_cpu_hours(model, population, burn)
        candidates.append({"population": int(population), "shorter_burn_adequate": burn_ok,
                           "burn_days": burn, "max_sd": max_sd, "mean_sd": mean_sd,
                           "audit_halfwidth": hw,
                           "audit_halfwidth_at_mean_sd": audit_halfwidth(mean_sd),
                           "projected_cpu_hours": cpu, "within_budget": cpu <= BUDGET_CPU_HOURS,
                           "halfwidth_ok": hw <= DELTA / 4, "burn_table": burn_table})
    chosen = next((c for c in candidates if c["within_budget"] and c["halfwidth_ok"]), None)
    rule = "smallest population meeting budget and half-width (D8.2)"
    if chosen is None:
        within = [c for c in candidates if c["within_budget"]]
        chosen = within[-1] if within else candidates[0]
        rule = "no population met the half-width target: largest within budget (D8.2 fallback)"
    return model, sds, candidates, chosen, rule


def normality(data, population, burn):
    d = data[(data.population == population) & (data.burn_days == burn)]
    p = d.groupby(["eir", "net"]).mean_lm_prevalence_2to10.apply(lambda v: stats.shapiro(v).pvalue)
    return p.reset_index(name="shapiro_p")


def figure(data, sds, candidates, chosen, path):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    ink, muted, grid = "#0b0b0b", "#52514e", "#e4e3df"
    series = ["#2a78d6", "#eb6834", "#1baf7a"]  # reference categorical slots 1-3
    plt.rcParams.update({"font.size": 9, "axes.edgecolor": muted, "axes.labelcolor": ink,
                         "xtick.color": muted, "ytick.color": muted,
                         "axes.spines.top": False, "axes.spines.right": False})
    fig, axs = plt.subplots(1, 3, figsize=(12, 3.8), facecolor="#fcfcfb")
    eirs = sorted(data.eir.unique())
    labels = {e: f"EIR {e:g}" if e == int(e) else f"EIR {e:.1f}" for e in eirs}
    burn = chosen["burn_days"]

    ax = axs[0]
    for color, eir in zip(series, eirs):
        g = sds[(sds.eir == eir) & (sds.burn_days == burn)].groupby("population").sd.max()
        ax.plot(g.index, g.values, "-o", color=color, lw=2, ms=6, label=labels[eir])
    pops = np.array(sorted(data.population.unique()))
    ref = sds[(sds.population == pops[0]) & (sds.burn_days == burn)].sd.max() * np.sqrt(pops[0] / pops)
    ax.plot(pops, ref, "--", color=muted, lw=1, label="1/√population")
    ax.set(xscale="log", yscale="log", xlabel="Simulated population",
           ylabel="Largest between-seed SD", title=f"A. Noise vs population (burn-in {burn} d)")
    ticks = [.003, .005, .01, .02, .03, .05]
    ax.set_yticks(ticks, [f"{t:g}" for t in ticks])
    ax.minorticks_off()
    ax.legend(frameon=False, fontsize=8)

    ax = axs[1]
    table = next(c for c in candidates if c["population"] == chosen["population"])["burn_table"]
    for k, (color, eir) in enumerate(zip(series, eirs)):
        t = table[table.eir == eir]
        x = np.arange(len(t)) + 4 * k
        ax.errorbar(x, t.mean_diff, yerr=[t.mean_diff - t.ci_low, t.ci_high - t.mean_diff],
                    fmt="o", color=color, ms=6, lw=2, capsize=0, label=labels[eir])
    ax.axhspan(-DELTA / 2, DELTA / 2, color=grid, zorder=0, label="±δ/2 tolerance")
    ax.axhline(0, color=muted, lw=1)
    ax.set_xticks([4 * k + j for k in range(len(eirs)) for j in range(3)],
                  [f"{n:.1f}" for _ in eirs for n in design.NETS])
    short, long_ = sorted(data[data.population == chosen["population"]].burn_days.unique())
    ax.set(xlabel="Net coverage (grouped by EIR)",
           ylabel=f"Prevalence: {long_} d − {short} d burn-in",
           title=f"B. Burn-in effect (population {chosen['population']})")
    ax.legend(frameon=False, fontsize=8, loc="upper right", ncol=2)

    ax = axs[2]
    d = sds[(sds.population == chosen["population"]) & (sds.burn_days == burn)]
    for color, eir in zip(series, eirs):
        g = d[d.eir == eir]
        ax.errorbar(g.net, g["mean"], yerr=1.96 * g.sd / np.sqrt(g.n), fmt="-o", color=color,
                    lw=2, ms=6, capsize=0, label=labels[eir])
    ax.set(xlabel="Net coverage", ylabel="Prevalence, ages 2–10",
           title="C. Coverage response (mean ± 95% CI)", xticks=list(design.NETS))
    ax.legend(frameon=False, fontsize=8)
    for a in axs:
        a.set_facecolor("#fcfcfb")
        a.grid(color=grid, lw=.6)
        a.set_axisbelow(True)
    fig.tight_layout()
    fig.savefig(path, dpi=160)
    plt.close(fig)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runs", type=Path,
                        default=Path(os.environ.get("USERPROFILE", "~")) / "malaria-runs" / "pilot")
    parser.add_argument("--out", type=Path, default=Path("results/pilot"))
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    data = load(args.runs)
    data.to_csv(args.out / "pilot_summary.csv", index=False, lineterminator="\n")
    model, sds, candidates, chosen, rule = decide(data)
    pop, burn = chosen["population"], chosen["burn_days"]
    d = data[(data.population == pop) & (data.burn_days == burn)]
    norm = normality(data, pop, burn)
    curv, paired = curvature(d), crn(d)
    figure(data, sds, candidates, chosen, args.out / "pilot_figure.png")
    sds.to_csv(args.out / "pilot_cell_sd.csv", index=False, lineterminator="\n")
    report = {
        "runs": len(data), "rules": "docs/DECISIONS.md D8",
        "runtime_model": model,
        "batch_record": (args.runs / "DONE.txt").read_text().splitlines()
                        if (args.runs / "DONE.txt").exists() else None,
        "candidates": [{k: v for k, v in c.items() if k != "burn_table"} for c in candidates],
        "burn_in_tables": {str(c["population"]): c["burn_table"].round(5).to_dict("records")
                           for c in candidates},
        "decision": {"population": pop, "burn_days": burn, "rule_applied": rule},
        "normality": {"cells": len(norm), "cells_p_below_0.01": int((norm.shapiro_p < .01).sum()),
                      "d1_stands": bool((norm.shapiro_p < .01).mean() <= .5),
                      "min_p": float(norm.shapiro_p.min())},
        "curvature": curv.round(5).to_dict("records"),
        "near_linear_in_coverage": bool((curv.ratio.abs() < 2).all()),
        "common_random_numbers": paired.round(5).to_dict("records"),
    }
    (args.out / "pilot_report.json").write_text(json.dumps(report, indent=2, default=float) + "\n")
    print(json.dumps({k: report[k] for k in ("decision", "normality", "near_linear_in_coverage")}, indent=2))
    print(pd.DataFrame(report["candidates"]).round(4).to_string(index=False))
    print(curv.round(4).to_string(index=False))
    print(paired.round(4).to_string(index=False))


if __name__ == "__main__":
    main()
