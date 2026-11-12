"""Auditable emulator demonstration on native Imperial output.

Usage: python ammikam_code.py --input integration_summary.csv --out output_dir
Requires numpy, scipy, pandas. --out is a directory.
This executes grouped holdout prediction and a finite-context decision audit.
It does not execute native R, adaptive retraining, or the full research study.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.linalg import cho_factor, cho_solve
from scipy.optimize import minimize


def kernel(x, z, length, amplitude):
    d = np.sqrt(np.maximum(0, ((x[:, None, :] - z[None, :, :]) ** 2
                              / length[None, None, :] ** 2).sum(axis=2)))
    v = np.sqrt(5.0) * d
    return amplitude ** 2 * (1 + v + v * v / 3) * np.exp(-v)


class SmallGP:
    """Noise-aware Matern 5/2 GP; no claim of simultaneous GP coverage."""
    def fit(self, x, y, variance):
        self.shift = x.mean(axis=0)
        self.scale = np.maximum(x.std(axis=0), 1e-8)
        self.x = (x - self.shift) / self.scale
        self.offset = float(np.mean(y))
        yc = y - self.offset
        variance = np.maximum(np.asarray(variance), 1e-6)

        def objective(p):
            lengths = np.exp(p[:2])
            amplitude = np.exp(p[2])
            cov = kernel(self.x, self.x, lengths, amplitude)
            cov.flat[::len(cov) + 1] += variance + 1e-9
            try:
                factor = cho_factor(cov, lower=True, check_finite=True)
                alpha = cho_solve(factor, yc)
                value = .5 * yc @ alpha + np.log(np.diag(factor[0])).sum()
                return float(value + .5 * len(y) * np.log(2 * np.pi))
            except np.linalg.LinAlgError:
                return 1e100

        initial = np.array([0., 0., np.log(max(float(y.std()), .03))])
        fitted = minimize(objective, initial, method="L-BFGS-B",
                          bounds=[(-3, 3), (-3, 3), (-5, 1)])
        self.length = np.exp(fitted.x[:2])
        self.amplitude = np.exp(fitted.x[2])
        cov = kernel(self.x, self.x, self.length, self.amplitude)
        cov.flat[::len(cov) + 1] += variance + 1e-9
        self.factor = cho_factor(cov, lower=True)
        self.alpha = cho_solve(self.factor, yc)
        self.optimisation_converged = bool(fitted.success)
        return self

    def predict(self, x):
        xx = (x - self.shift) / self.scale
        cross = kernel(xx, self.x, self.length, self.amplitude)
        mean = self.offset + cross @ self.alpha
        variance = self.amplitude ** 2 - np.einsum(
            "ij,ji->i", cross, cho_solve(self.factor, cross.T))
        return mean, np.sqrt(np.maximum(variance, 0))


def native_bounds(mean, n, contexts, alternatives, alpha=.05):
    # alpha/(J*K*n*(n+1)) sums to at most alpha across all integer n.
    allocated = alpha / (contexts * alternatives * n * (n + 1))
    halfwidth = np.sqrt(np.log(2 / allocated) / (2 * n))
    return np.maximum(0, mean - halfwidth), np.minimum(1, mean + halfwidth)


def checked_regret(selected, lower, upper, coverage, effort):
    return float(upper[selected] + effort * coverage[selected]
                 - np.min(lower + effort * coverage))


def self_test():
    x = np.array([[0., .3], [0., .7], [1., .3], [1., .7]])
    y = np.array([.3, .2, .6, .4])
    gp = SmallGP().fit(x, y, np.full(4, 1e-5))
    mean, sd = gp.predict(x)
    assert np.max(np.abs(mean - y)) < .03
    assert np.all(sd >= 0)
    lo, hi = native_bounds(np.array([.2, .3, .4]), np.array([2, 2, 2]), 3, 3)
    assert checked_regret(0, lo, hi, np.array([.3, .5, .7]), 0) > .01
    # With exact bounds a clearly inferior choice fails and a good one passes.
    assert checked_regret(2, y[:3], y[:3], np.array([.3, .5, .7]), 0) > .01
    assert checked_regret(1, y[:3], y[:3], np.array([.3, .5, .7]), 0) <= .01
    return {"gp_training_sanity": True, "two_seed_abstention": True,
            "deliberately_wrong_choice_rejected": True}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path)
    parser.add_argument("--out", type=Path, default=Path("ammikam_demo"))
    parser.add_argument("--delta", type=float, default=.01)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    checks = self_test()
    if args.self_test and args.input is None:
        (args.out / "self_test.json").write_text(json.dumps(checks, indent=2))
        return
    if args.input is None:
        parser.error("--input is required unless only --self-test is requested")
    source = pd.read_csv(args.input)
    required = {"family", "eir", "net", "seed", "mean_lm_prevalence_2to10"}
    if not required.issubset(source):
        raise ValueError(f"Missing columns: {sorted(required-set(source))}")
    data = source.loc[source.family == "emulator"].copy()
    target = "mean_lm_prevalence_2to10"
    if data.empty or not np.isfinite(data[target]).all():
        raise ValueError("No finite emulator-family native outputs")
    if not data[target].between(0, 1).all():
        raise ValueError("The primary bounded outcome must be in [0,1]")
    if data.duplicated(["eir", "net", "seed"]).any():
        raise ValueError("Repeated seed within a configuration is not independent replication")
    grouped = data.groupby(["eir", "net"])[target].agg(
        mean="mean", variance="var", n="count").reset_index()
    if (grouped.n < 2).any():
        raise ValueError("At least two native seeds per configuration are needed")
    grouped["mean_variance"] = grouped.variance / grouped.n
    grouped.to_csv(args.out / "native_summary.csv", index=False)
    rows, decisions = [], []
    test_eirs = sorted(grouped.eir.unique())
    converged = []
    for held_eir in test_eirs:
        train = grouped.loc[grouped.eir != held_eir]
        test = grouped.loc[grouped.eir == held_eir].sort_values("net")
        xx = np.c_[np.log(train.eir), train.net]
        gp = SmallGP().fit(xx, train["mean"].to_numpy(), train.mean_variance.to_numpy())
        converged.append(gp.optimisation_converged)
        pred, sd = gp.predict(np.c_[np.log(test.eir), test.net])
        reference = test["mean"].to_numpy()
        coverage = test.net.to_numpy()
        lo, hi = native_bounds(reference, test.n.to_numpy(), len(test_eirs), len(test))
        for k, (_, item) in enumerate(test.iterrows()):
            rows.append({"held_eir": held_eir, "net": item.net,
                         "native_replicate_mean": reference[k], "prediction": pred[k],
                         "latent_gp_sd": sd[k], "native_lower": lo[k],
                         "native_upper": hi[k], "n_reference_seeds": item.n})
        for effort in np.linspace(0, 1, 21):
            selected = int(np.argmin(pred + effort * coverage))
            reference_best = int(np.argmin(reference + effort * coverage))
            estimated_regret = (reference[selected] + effort * coverage[selected]
                                - reference[reference_best] - effort * coverage[reference_best])
            conservative_regret = checked_regret(selected, lo, hi, coverage, effort)
            screen_regret = checked_regret(selected, np.maximum(0, pred-1.96*sd),
                                          np.minimum(1, pred+1.96*sd), coverage, effort)
            decisions.append({"held_eir": held_eir, "effort_weight": effort,
                              "chosen_net": coverage[selected],
                              "finite_sample_reference_net": coverage[reference_best],
                              "estimated_regret_not_truth": estimated_regret,
                              "conservative_native_regret_upper": conservative_regret,
                              "native_checked": conservative_regret <= args.delta,
                              "gp_screen_acceptable_not_certified": screen_regret <= args.delta,
                              "delta": args.delta})
    prediction_table = pd.DataFrame(rows)
    decision_table = pd.DataFrame(decisions)
    prediction_table.to_csv(args.out / "heldout_predictions.csv", index=False)
    decision_table.to_csv(args.out / "decision_audit.csv", index=False)
    status = {
        "status": "native_input_demonstrator_not_full_research",
        "source_sha256": hashlib.sha256(args.input.read_bytes()).hexdigest(),
        "input_native_rows": len(data), "configurations": len(grouped),
        "group_holdout": "complete EIR levels, not random seeds",
        "prediction_mae_demonstration": float(np.abs(prediction_table.prediction-
                                                    prediction_table.native_replicate_mean).mean()),
        "checked_fraction": float(decision_table.native_checked.mean()),
        "gp_optimisations_converged": converged,
        "checks": checks,
        "not_implemented_research_steps": [
            "Full simulation design and independent high-replication reference",
            "Native adaptive acquisition and budget-matched repeated experiments",
            "Population and burn-in convergence study",
            "Empirical calibration of emulator uncertainty and risk-coverage-cost inference",
            "Optional native malariasimple fidelity and StateMINT benchmark"],
        "limitations": "Small native grid, uncalibrated settings and uncertain reference means; no country recommendation"
    }
    (args.out / "status.json").write_text(json.dumps(status, indent=2), encoding="utf-8")
    print(json.dumps({"out": str(args.out.resolve()), "status": status["status"],
                      "native_rows": len(data), "checked_fraction": status["checked_fraction"]}))


if __name__ == "__main__":
    main()
