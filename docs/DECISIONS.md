# Design decisions

Each entry records the decision, why it was made, and what would reverse it.
Decisions are never deleted. A reversal is a new entry that points back to the old one.

---

## D1 — Primary decision check: two levels, empirical error rate is the primary metric
*16 Nov 2026 · Status: adopted, to be confirmed by the M2 pilot*

**Decision.**
- **Primary outcome:** the audited frequency of regret above δ, together with the
  fraction of decisions made and the compute cost (risk-coverage-cost). This matches
  the dossier's primary hypothesis.
- **Operational check ("checked at δ"):** simultaneous Student-t intervals on
  replicate means, Bonferroni-corrected over every context × option in the declared
  design. A choice is checked when its worst-case regret under these intervals is ≤ δ.
- **Distribution-free check:** the union-bound Hoeffding check stays in the code and
  is reported as "the price of a distribution-free guarantee". It shows how many seeds
  a guarantee would need.

**Why.** For outcomes in [0, 1], Hoeffding ignores the observed variance. With
12 contexts × 3 options and 20 seeds, its half-width is 0.58. Even 1,000 seeds give
0.10, and δ = 0.01 needs about 0.005. That check would therefore abstain on every
decision by construction, so it can't distinguish between methods. Between-seed SD is
about 0.01 at 500 people and expected to be smaller at 5,000, so t-intervals at 20
seeds are about ±0.003–0.008, narrow enough to resolve decisions. The t-interval error
rate is not assumed; it is measured on the independent audit.

**Reverse if** the M2 pilot shows clearly non-normal replicate means (Shapiro–Wilk
p < 0.01 at most pilot settings, or skew that a bootstrap check doesn't fix). Fallback:
percentile bootstrap intervals.

---

## D2 — A negative result is a valid outcome
*16 Nov 2026 · Status: adopted*

If decision-focused allocation does not beat the baselines, that is reported as the
finding, following the dossier's "minimum worthwhile paper". The comparison is fixed
before the audit (M3) so the result can't be tuned in either direction.

---

## D3 — Compute: local machine, parallel by sharding
*16 Nov 2026 · Status: adopted*

Runs execute on this Windows machine. The R runner takes `--shard i --of N`, so N
separate `Rscript` processes run in parallel without R's PSOCK clusters (which are
fragile on Windows). Runs resume: completed `run_id`s are skipped. Budget ceiling:
100 CPU-hours (dossier), re-estimated in M2.

---

## D4 — Seed plan: shared seeds across options, disjoint seeds across contexts and partitions
*16 Nov 2026 · Status: adopted*

`seed = partition_base + 1000 × context_index + rep`, with bases pilot = 1,000,000,
train = 2,000,000, tune = 3,000,000, audit = 4,000,000, adaptive = 5,000,000.

- **Within a context and replicate, all 3 net options use the same seed** (common
  random numbers). This reduces noise in comparisons between options, which is what
  decides the choice.
- **Different contexts and partitions never share a seed,** so audit data are
  independent of training data (dossier requirement).
- Pairing is recorded in the manifest. The covariance between options is inspected in
  M2, not assumed. The per-option checks in D1 don't rely on independence between
  options.

**Why.** The demonstration reused seeds 231001/231002 everywhere, which breaks the
dossier's independence requirement.

---

## D5 — Net scenario: 0.5 baseline in burn-in, option coverage in 3-yearly campaigns
*16 Nov 2026 · Status: adopted*

**Finding.** `set_bednets()` overwrites earlier calls (package source,
`vector_control_parameters.R` lines 96–97). In `imperial_experiments.R`, the
intended 0.5 baseline (line 68) was therefore discarded. Each option's coverage was
applied from day 1, and nets were distributed only twice (day 1 and day 731). With a
2-year insecticide half-life and 3-year retention, coverage decayed through most of the
5-year follow-up.

**Decision.** `coverage` means the **proportion of the population receiving a net at a
mass distribution** (the package's own definition). Scenarios:
- Burn-in: 0.5 baseline campaigns at day 1 (and every 3 years if the burn-in is longer).
- Follow-up: the option's coverage at campaigns on day `burn+1` and `burn+3·365+1`.

**Why.** Campaigns every 3 years are standard practice. The decision becomes "change
from the current programme to coverage *c*", and the option's effect lasts through
follow-up.

**Consequence.** The 18-run demonstration data used the old scenario. It stays in
`native_reference/` as archived evidence and is not mixed with research runs.

---

## D10 — Proposal for M3: regret check on paired contrasts
*19 Nov 2026 · Status: proposed (decided at M3). Proposed **after** seeing the pilot,
and labelled as such.*

The current check, `checked_regret`, combines each option's own interval
(worst case of the chosen option minus best case of the alternatives). This ignores that
options share seeds (D4), so it counts seed-to-seed noise twice. A check on the paired
difference (chosen − alternative, per seed) uses the noise that matters for the
decision. In the pilot, paired contrasts had 35–40% lower SD than unpaired ones. Both
checks will be implemented in M4. Which one is primary is fixed at M3, before any audit
data exist. The justification is the purpose of D4, not the pilot numbers.

---

## D9 — Burn-in lengths are whole 3-year campaign cycles; follow-up burn-in pilot
*19 Nov 2026 · Status: adopted*

**Finding.** Under D5, campaigns run every 1095 days from day 1. A 730-day burn-in puts
the last baseline campaign 730 days before follow-up. A 1460-day burn-in adds one on
day 1096, only 365 days before follow-up. The D8.1 comparison therefore mixed
equilibration with **fresher nets at follow-up start**. Its result (1460 − 730 ≈ −0.015,
consistent at every population) can't be read as a pure burn-in effect.

**Decision.**
- Research burn-ins must be multiples of 1095 days. Then baseline campaigns run on an
  unbroken 3-year cadence straight into the option campaign at `burn+1`, and the net
  history at follow-up start is identical across burn-in lengths. `design.py` enforces this.
- Follow-up pilot at population 10,000 (D8.2's choice): burn-in 2190 vs 3285 days
  (6 vs 9 years), 3 EIR × 3 nets × 10 reps = 180 runs, same seeds as the pilot. D8.1's
  rule applies unchanged: 2190 is adequate if every paired-difference CI lies within
  ±0.005. Otherwise use 3285.

**Status of D8 outcomes.** Population 10,000 stands (D8.2 fallback: no population
reached the ±0.0025 target within budget). The D8.1 burn-in outcome (1460) is
superseded by this follow-up.

**Outcome (19 Nov 2026): burn-in locked at 3285 days.** All 180 runs finished (6 shards,
exit code 0, 1.4 h wall). Every paired difference (3285 − 2190) was small, between
−0.0011 and +0.0019, and 7 of 9 CIs lay inside ±0.005. Two CIs at EIR 50 crossed it
(upper ends 0.0063 at net 0.3 and 0.7), so the rule as written selects 3285. The failure
comes from imprecision with 10 seeds, not from a detected bias. 3285 costs about 55
CPU-hours for the full study, inside the 100-hour budget. Normality: 0 of 9 cells with
p < 0.01 (min p = 0.15), so D1 stands. Details: `results/pilot_burnin/`.

---

## D8 — Pilot decision rules (written before the pilot results were analysed)
*19 Nov 2026 · Status: adopted. The 540 pilot runs finished on 18 Nov; their
summaries had not been opened when these rules were written.*

δ = 0.01 throughout.

1. **Burn-in.** 730 days is adequate if, at the chosen population and for every
   EIR × net cell, the 95% CI of the paired difference (1460 − 730 days, same seeds)
   lies inside ±δ/2 = ±0.005. Otherwise use 1460 days.
2. **Population.** Choose the smallest population that meets both conditions:
   (a) the projected full research study fits in 100 CPU-hours, with the chosen
   burn-in and the runtime model refitted from pilot timings; and (b) the audit
   t-interval half-width is ≤ δ/4 = 0.0025. That half-width uses 20 seeds,
   Bonferroni over 12 × 3 = 36 cells and the largest pilot SD at that population.
   If no population meets (b), take the largest within budget and record that more
   abstention is expected.
3. **Normality (confirms D1).** D1 stands unless Shapiro–Wilk p < 0.01 in more than half
   of the cells at the chosen population. With 10 replicates this test has low power, so
   the M6 audit (20 seeds) rechecks it.
4. **Curvature (reported, no decision).** Second difference p(0.3) − 2p(0.5) + p(0.7) at
   each EIR, compared with its standard error. If |curvature| < 2 SE at every EIR,
   the response is "near-linear in coverage" and the risk that adaptation won't help is
   flagged.
5. **Common random numbers (reported).** Correlation between options sharing a seed,
   and how much it reduces the SD of option contrasts.

---

## D7 — Run outputs live outside OneDrive
*16 Nov 2026 · Status: adopted*

The repository sits in a OneDrive folder. OneDrive would sync every daily file as it is
written and can lock files mid-write. Run outputs therefore go to
`%USERPROFILE%\malaria-runs\<name>`. Only the run summaries are copied into the repo
(`results/pilot/`) for analysis and version control. Refines D6.

---

## D6 — Storage: summaries in git, daily outputs compressed outside git
*16 Nov 2026 · Status: adopted*

Daily outputs (~1.1 MB each, ~1 GB for the full study) are written as `.csv.gz` to
`runs/` (git-ignored) and archived to Zenodo at M9. The run summary, manifest,
parameter archive and version record are small and go in git.
