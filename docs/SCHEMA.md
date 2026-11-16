# Data schema

## Scenario manifest (`manifests/*.csv`, written by `design.py`)

| Column | Meaning |
|---|---|
| `run_id` | Unique run name: `{partition}-c{context}-n{net}-p{population}-b{burn}-r{rep}` |
| `partition` | `pilot`, `train`, `tune`, `audit` (later `adaptive`). Partitions never share seeds or EIR settings. |
| `context` | Index of the EIR setting within its partition |
| `eir` | Baseline entomological inoculation rate (infectious bites per person per year), log-spaced within 5–50 |
| `net` | Net option: proportion of the population receiving a net at each follow-up campaign (0.3, 0.5, 0.7) |
| `rep` | Replicate number, starting at 1 |
| `seed` | `base[partition] + 1000·context + rep`. Shared by the 3 net options of a context and replicate (D4). |
| `population` | Simulated human population |
| `burn_days` | Burn-in days before follow-up |
| `horizon_days` | Follow-up days (1825 = 5 years) |

## Run summary (`runs/<name>/summary_shardNN.csv`, written by `native_runner.R`)

All manifest columns, plus:

| Column | Meaning |
|---|---|
| `mean_lm_prevalence_2to10` | **Primary outcome.** Person-day-weighted microscopy-detectable prevalence, ages 2–10, over follow-up: `prevalence_numerator_person_days / prevalence_denominator_person_days`. Lies in [0, 1]. |
| `prevalence_numerator_person_days` | Sum over follow-up days of `n_detect_lm_730_3650` (people aged 730–3650 days detectable by light microscopy) |
| `prevalence_denominator_person_days` | Sum over follow-up days of `n_age_730_3650`. Must be positive. |
| `clinical_under5`, `clinical_all` | Clinical episodes during follow-up, ages 0–5 and all ages (secondary) |
| `severe_under5`, `severe_all` | Severe episodes during follow-up (secondary) |
| `under5_person_years`, `all_person_years` | Person-time denominators for the episode counts |
| `net_scenario` | Net schedule version (`D5_campaign_v1`: 0.5 baseline in burn-in, option campaigns every 3 years in follow-up) |
| `elapsed_seconds`, `cpu_seconds` | Wall-clock and CPU time of the simulation call |
| `malariasimulation_version` | Installed package version |
| `calibrated` | Always `FALSE`. Settings are experimental inputs, not calibrated to any country. |

## Other run outputs

| File | Contents |
|---|---|
| `daily/<run_id>.csv.gz` | Full daily simulator output (git-ignored, archived at M9) |
| `params/<scenario>.rds` | The exact parameter object passed to `run_simulation()` |
| `version_record_shardNN.json` | R and package versions, package source SHA, git commit and dirty flag, manifest hash, start time |
| `sessionInfo_shardNN.txt` | R `sessionInfo()` |
