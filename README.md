# malaria-gp-emulator

A Gaussian Process emulator for Imperial College London's
[`malariasimulation`](https://github.com/mrc-ide/malariasimulation). It predicts
malaria prevalence in children aged 2–10 across transmission intensity (EIR) and
bed-net coverage, and audits the bed-net coverage decisions it would make.

> **Status: a demonstration, not finished research.** The reference simulations are
> uncalibrated, with 9 configurations and 2 random seeds each. The conservative
> simulator-based check rejects (abstains on) every decision, which is the correct
> result at this sample size. See [What is not done yet](#what-is-not-done-yet).

## What it does

1. **Summarises simulator output.** It averages the seeds for each (EIR, net coverage)
   setting.
2. **Fits a noise-aware Gaussian Process** (Matérn 5/2 kernel) on log(EIR) and net
   coverage. Each setting's seed variance is passed to the model as its noise level.
3. **Grouped holdout.** It holds out each whole EIR level in turn and predicts it from
   the other levels, which is a harder test than leaving out random runs.
4. **Decision audit.** For effort weights from 0 to 1, it picks the coverage that
   minimises `prevalence + effort × coverage` and checks that choice two ways:
   - **Simulator check:** Hoeffding bounds with a union bound over every setting and
     seed count. Passing this is a guarantee.
   - **GP screen:** the GP's ±1.96 SD bands. This is a quick screen, not a guarantee.

## Quick start

```bash
python -m pip install -r requirements.txt
python ammikam_code.py --input native_reference/integration_summary.csv --out results
python plot_companion.py ammikam results
```

To run only the built-in checks:

```bash
python ammikam_code.py --self-test --out results/self_test
```

### Outputs

| File | Contents |
|---|---|
| `native_summary.csv` | Mean, variance and seed count for each (EIR, net) setting |
| `heldout_predictions.csv` | GP predictions for held-out EIR levels, next to the simulator values and bounds |
| `decision_audit.csv` | Chosen and reference coverage, regret estimates and pass/fail checks at each effort weight |
| `status.json` | Input file hash, prediction error, share of decisions passed, whether each fit converged, limitations |

## Regenerating the simulator data (R)

The reference data in `native_reference/` was produced with `malariasimulation`
3.0.0 on R 4.6.1, source commit `5f63ccd61c8e893892fd12e7580fc22a7c882285`.

```bash
Rscript install_R.R
Rscript imperial_experiments.R emulator results/native
```

## Repository layout

```
ammikam_code.py           GP emulator, holdout and decision audit
plot_companion.py         figure from the executed outputs
imperial_experiments.R    malariasimulation experiments that produce the input CSV
install_R.R               installs and checks the pinned malariasimulation version
fetch_public_inputs.py    downloads named public data and records URLs and hashes
native_reference/         simulator output (summary, one daily example, environment record)
results/                  reference run of the command above
Companion.ipynb / .html   executed notebook with saved outputs
EXECUTION_RECORD.json     record of the executed run
```

## What is not done yet

- A full simulation design with an independent high-replication reference
- Adaptive choice of new simulator runs, compared with a grid at the same budget
- Population size and burn-in convergence study
- Empirical calibration of the emulator's uncertainty
- Calibrated, country-specific scenarios. **This repository makes no country policy
  recommendation.**

## Acknowledgements

Simulations use [`malariasimulation`](https://github.com/mrc-ide/malariasimulation)
by the MRC Centre for Global Infectious Disease Analysis, Imperial College London.
