# Improvements log

Every code change is listed here **before** it is written, with its reason and the
milestone it serves. Status: 📝 planned · 🟨 in progress · ✅ done · ❌ dropped.

---

## M1 — Model identity and design (Week 1)

| ID | Improvement | Why | Status |
|---|---|---|---|
| I1 | **`design.py`**: generates a scenario manifest (`run_id, partition, context, eir, net, rep, seed, population, burn_days, horizon_days`) for the pilot, train, tune and audit partitions | One archived, deterministic source of truth for every run. Fixes seed reuse (D4). | ✅ |
| I2 | **`tests/test_design.py`**: seeds disjoint across partitions and contexts, shared across options, identical on regeneration. Training and audit EIRs don't overlap. EIR inside 5–50. | Catches design mistakes before CPU-hours are spent | ✅ 9/9 pass |
| I3 | **`native_runner.R`** + **`R/scenario.R`**: reads the manifest. Fixed net scenario (D5). `--shard/--of` parallelism and resume (D3). Gzipped daily output (D6). One parameter archive per scenario. Records CPU and elapsed time. Checks the prevalence denominator is positive. | Research-grade runner. `imperial_experiments.R` stays unchanged as provenance for the demonstration data. | ✅ smoke run + resume verified |
| I4 | **Version record**: the runner writes `version_record_shardNN.json` (R version, malariasimulation version and source SHA, git commit and dirty flag, manifest hash) plus `sessionInfo` | Dossier: "preserve package versions, source revision… seed lists" | ✅ manifest hash matches Python's |
| I5 | **Reproducibility test**: `tests/test_reproducible.R` runs one small scenario twice with the same seed and checks identical output, then once with a different seed and checks it differs. Also checks the D5 net schedule reaches the parameter object. | Confirms `set.seed` fully controls the C++ RNG (`model.R:114`) | ✅ 9/9 pass |
| I6 | **`docs/SCHEMA.md`**: column definitions for the manifest and run summary, including the exact prevalence numerator and denominator | Dossier outcome contract (A1) | ✅ |
| I7 | `.gitignore` adds `runs/` | D6 | ✅ |

| I8 | **`.gitattributes`**: store `manifests/` byte-for-byte (`-text`) and use LF endings for code | With Windows `autocrlf`, a checkout could rewrite `pilot.csv` with CRLF endings, so its sha256 would stop matching `pilot.json` and the version records | ✅ |
| I9 | **Repo-local git sign-in**: this repo fetches the `devammikam` token from the GitHub CLI when pushing (`gh auth token -u devammikam`). The global active account (`Ammikam`) is unchanged. | Pushes failed after the CLI's active account changed to a different GitHub user | ✅ |



## M2 — Pilot (Week 2)

| ID | Improvement | Why | Status |
|---|---|---|---|
| I10 | **`scripts/run_pilot.ps1`**: starts 6 `native_runner.R` shards in parallel with one log each, keeps Windows awake until all finish (`SetThreadExecutionState`), and writes `DONE.txt` with each shard's exit code. Outputs go to `%USERPROFILE%\malaria-runs\pilot` (D7). | One command for long batches. A sleeping laptop would pause the runs. | ✅ tested: 2 runs on 2 shards, exit codes 0, run 1 reproduced exactly |
| I12 | **`pilot_analysis.py`**: combines the shard summaries into `results/pilot/pilot_summary.csv`, applies the D8 rules, and writes `results/pilot/pilot_report.json` and `pilot_figure.png` (SD vs population, burn-in differences, coverage curves) | Makes the M2 decisions reproducible and traceable to data. `.gitignore` now keeps `results/pilot*/`. | ✅ |
| I13 | **`design.py pilot-burnin`**: follow-up manifest (population 10,000, burn-in 2190 vs 3285, same seeds as the pilot). `research_manifest` rejects burn-ins that aren't multiples of 1095 (D9). Tests for both. | D9 | ✅ 11 tests pass |
| I14 | **`pilot_analysis.py`**: works for any pilot folder (`--runs`, `--out`), reads wall time from `DONE.txt`, and reports mean as well as max SD per population | Same rules applied to the follow-up. Max-of-9 SD with 10 seeds is noisy. | ✅ |
| I15 | **Lock burn-in 3285 days**: `design.py` research default `--burn 3285`. Follow-up results committed in `results/pilot_burnin/`. | D9 outcome | ✅ |
| I16 | **`design.py research --partitions train,tune`**: writes a subset manifest from the same rows and seeds as the full research manifest. The full manifest is written too, so its hash fixes the whole plan. Test: subset rows are identical to the matching full-manifest rows. | D11: start training and tuning runs early | ✅ 12 tests pass |
| I17 | **Training and tuning summaries in git**: the combined run summary goes to `results/research_train_tune/summary.csv`, with the batch record. `.gitignore` keeps `results/research*/`. Daily outputs stay outside git (D6). | D6, D11 | ✅ |
| I11 | **Scheduled task** `malaria-pilot`: runs `run_pilot.ps1` once on Tue 17 Nov 2026 at 21:00 (wakes the PC, allowed on battery, starts late if missed, 14 h limit) | The user chose this start time | ✅ registered, next run 17 Nov 21:00 |

**Design details settled while writing M1 code**
- EIR partitions are interleaved on the log scale: train = 16 points at fractions i/15
  (including 5 and 50, so the audit never extrapolates), tune = 6 at (2j+1)/12, audit =
  12 at (2k+1)/24. These fractions can never coincide, so the sets are disjoint.
- Pilot = EIR {5, 15.8, 50} × 3 nets × population {500, 5000, 10000} × burn-in
  {730, 1460} × 10 replicates = 540 runs. Population and burn-in variants reuse seeds,
  so their effects are compared on paired runs.
- `design.py` estimates CPU-hours from the demonstration's runtime (8.1 s per run at 500
  people over 2,555 days), assuming cost scales with people × days. M2 checks this.

## M1 verification results (16 Nov 2026)
- `pytest tests`: 9 passed. `Rscript tests/test_reproducible.R`: 9 passed.
- `manifests/pilot.csv`: 540 runs, sha256 `a6cdd594…ad34b3`, committed.
- Smoke run (`pilot-c00-n0.3-p500-b730-r01`): prevalence 0.168, rerun correctly skipped.
  Under the old scenario the comparable demonstration value was 0.205. The difference
  fits D5: the 0.5 baseline and repeated campaigns keep more nets in use.
- **Runtime:** the smoke run took 14.0 s, where the demonstration averaged 8.1 s.
  `design.py`'s estimate (14.4 CPU-h for the pilot) is probably about 1.7× too low, so
  plan for about 25 CPU-h. The machine has 8 logical cores, so the pilot takes about
  4–5 h on 6 shards. M2 will refit the runtime model from pilot timings.
