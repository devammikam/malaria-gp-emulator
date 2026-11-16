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
