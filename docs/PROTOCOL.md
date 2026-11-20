# Study protocol (`protocol-v1`)

*Locked 20 November 2026, before any audit run existed. Frozen numbers are in
[`protocol.json`](../protocol.json). Reasons for each choice are in
[DECISIONS.md](DECISIONS.md) (D1–D12). Source protocol: the research dossier
"When can a fast malaria simulator preserve an intervention decision?"*

## Pre-registration note

This document fixes the estimand, methods, decision gate, audit classification and
endpoints **before** the 720 audit runs are generated (D11). The following already
existed when it was written:

- the M2 pilots (`results/pilot/`, `results/pilot_burnin/`)
- the 264 training and tuning runs (`results/research_train_tune/`)
- the full research manifest, whose sha256 (`c1c9e82e…d7e9a`) fixes the audit seeds

Training and tuning data informed exactly two choices, both disclosed here: the
secondary fine λ grid (§3) and the noise model (§5). Audit data will not be analysed
until the M4 code and the M5 runs are complete and committed. Any later change is a
**deviation** (§11).

## 1. Question and hypothesis

**Primary question:** does decision-focused adaptive allocation of expensive
simulator runs buy more reliable intervention decisions per run than equal-budget
space-filling allocation?

**Primary hypothesis:** at equal budget, the decision-focused method accepts more
decisions without a higher audited rate of regret above δ. This is not assumed true,
and a negative result is reported as the finding (D2).

All results are conditional on malariasimulation 3.0.0, the declared domain and an
illustrative decision rule. Nothing here estimates policy for a real country.

## 2. Simulator, domain and outcome

| Item | Locked value |
|---|---|
| Simulator | malariasimulation 3.0.0, source SHA `5f63ccd6…`, R 4.6.1 |
| Population, burn-in, follow-up | 10,000 people; 3285 days (9 years, D9); 1825 days (5 years) |
| Context | Baseline EIR 5–50 infectious bites per person-year, log scale |
| Options | Net campaign coverage 0.3, 0.5, 0.7 (scenario D5); treatment 0.45 |
| Outcome *m(x, a)* | `mean_lm_prevalence_2to10`: person-day-weighted microscopy prevalence, ages 2–10, over follow-up ([SCHEMA.md](SCHEMA.md)) |
| Training | 16 EIRs at log fractions i/15 (including 5 and 50) × 3 options × 4 seeds = 192 runs |
| Tuning | 6 EIRs at (2j+1)/12 × 3 × 4 = 72 runs. Used only for uncertainty calibration (§5). |
| Audit | 12 EIRs at (2k+1)/24 × 3 × 20 = 720 runs, fresh seeds |
| Adaptive candidates | 31 EIRs at k/30. These include every training EIR and never coincide with a tuning or audit EIR. |

Every audit EIR lies strictly inside the training range, so no audit decision is an
extrapolation.

## 3. Decision estimand

For context *x*, effort weight λ and option *a* with coverage *cₐ*:

- objective *J(x, a; λ) = m(x, a) + λ·cₐ*
- regret of a choice â: *R = J(x, â; λ) − min_b J(x, b; λ)*
- tolerance set: *A_δ = {a : J(x, a; λ) ≤ min_b J(x, b; λ) + δ}*

λ is an illustrative trade-off weight. It is not a price or a willingness-to-pay value.

| Item | Locked value |
|---|---|
| Primary λ grid | 21 values, 0, 0.05, …, 1 (dossier). That gives 12 × 21 = 252 audit decisions. |
| Secondary λ grid | 31 values, 0, 0.01, …, 0.30 |
| δ | **0.01** primary; 0.005 and 0.02 sensitivity. Never changed after seeing results. |
| Contested subset (secondary) | Decisions where the reference gap between the best and second-best option is < 0.05 |

*Disclosure:* on training data the preferred option changes only for λ ≤ 0.2. The
fine grid was added so the boundary region is resolved, and it is labelled secondary
because it was chosen after seeing training data.

## 4. Methods compared (equal budget: 192 + 63 = 255 runs)

The adaptive budget is 21 **blocks**. A block is 3 runs, one per option, sharing one
seed, at one candidate EIR. That is 63 runs, within the dossier's 64-run cap. A block
at an EIR with no data is a new option block. A block at an EIR already sampled is a
replicate block.

| Method | Data | Model | How blocks are allocated |
|---|---|---|---|
| **DF**: decision-focused GP | 192 + 21 blocks | GP (§5) | Highest unresolved-decision score. Every 4th block (blocks 4, 8, …, 20) follows the SF rule instead. |
| **SF**: space-filling GP | 192 + 21 blocks | GP | Maximin: the candidate furthest in log EIR from any sampled EIR. Once every candidate is sampled, the candidate with the fewest blocks, then maximin. |
| **PV**: prediction-variance GP | 192 + 21 blocks | GP | Candidate with the largest mean posterior SD across the 3 options |
| **LI**: linear interpolator | SF's data | Piecewise linear in log EIR, per option | None (reuses SF's design, so the model is the only difference) |
| **DS**: direct sampling | 255 new runs at the 12 audit EIRs, with their own seeds | None | 2 seeds per configuration (72 runs), then 61 blocks to the context with the most unresolved decisions (§6). Ties go to the fewest seeds, then the lowest index. |

**Unresolved-decision score (DF).** At candidate *x*, for each λ on the primary grid,
take the predicted best option â. The decision is unresolved if its screening envelope
(§6) exceeds δ. The score is the fraction of the 21 λ values that are unresolved. Ties
go to the larger mean posterior SD, then the lower candidate index.

Rules are deterministic given data. One block per round, and the model is refitted
after every block. No acquisition setting is tuned on audit data.

## 5. Emulator

- GP on inputs (log EIR, net coverage), standardised by the training design: Matérn 5/2
  with ARD and a constant mean. Hyperparameters by maximum marginal likelihood
  (L-BFGS-B; log-length bounds [−3, 3], log-amplitude [−5, 1]).
- **Observation noise:** a configuration mean based on *n* seeds has variance *s²/n*,
  where *s²* is the pooled within-configuration variance. Means at the same EIR share
  seeds (D4), so their errors have covariance *ρs²/n*, with ρ pooled from the same-seed
  pairs. *Disclosure:* the pilots showed similar SDs across settings and same-seed correlations of 0.53–0.83.
  This choice uses that, and it is the same for every method.
- **Calibration on tuning data:** a single multiplier κ on the predictive SD. κ is the
  smallest value in {1, 1.5, 2, 3, 5} for which at least 16 of the 18 tuning means
  **and** at least 16 of the 18 tuning contrasts (option pairs at one EIR) fall inside
  their 95% predictive intervals. It is recomputed at every checkpoint, for every
  method that has a model, including LI. If no κ passes, the method **abstains on every
  decision** at that checkpoint (dossier: failed calibration triggers abstention).

## 6. Decision gate

For each method, audit context and λ, the output is one of three things: a
**provisional choice** â (accepted), the predicted tolerance set, or **abstain**.

- **Screening envelope (DF, SF, PV, LI):**
  *max_b [ μ̂(â) − μ̂(b) + λ(c_â − c_b) + z·κ·sd(m̂(â) − m̂(b)) ]*, using the joint
  posterior of the contrast. Accept if it is ≤ δ, otherwise abstain. The operating
  point is z = 1.96. The risk-coverage curve uses z ∈ {0, 0.5, 1, 1.5, 1.96, 2.5, 3}.
  z = 0 accepts every decision.
- **Native check (DS):** paired-contrast t-intervals (D10). For each option pair at a
  context, the per-seed differences give a two-sided Student-t interval, Bonferroni
  over 12 contexts × 3 pairs at α = 0.05. Accept â if
  *max_b [ U(â − b) + λ(c_â − c_b) ] ≤ δ*. The nominal α ignores DS's sequential
  allocation. That is stated as a limitation, and the audit measures the actual error.
- **Out of domain:** any context outside log EIR ∈ [log 5, log 50] abstains
  automatically. This is tested in code (EIR 2, 4.9, 51, 100). No runs are needed.

GP-based acceptances are "provisional" (emulator-based). Only a native check may be
labelled "checked at δ" (dossier eq. 8).

## 7. Audit classification

The reference is the 20-seed audit. Regret of â is *max_b D_b* with
*D_b = m(â) − m(b) + λ(c_â − c_b)*. Each *m(â) − m(b)* gets a paired-contrast
t-interval (df 19, Bonferroni over 12 × 3 pairs, two-sided α = 0.05), which bounds
regret within [*R_L*, *R_U*].

| Class | Rule |
|---|---|
| Clearly within tolerance | *R_U* ≤ δ |
| Clearly outside tolerance | *R_L* > δ |
| Unresolved | otherwise |

Secondary classifications: marginal t-intervals per option (the original D1 check)
and the Hoeffding union bound, reported as the cost of a distribution-free guarantee.

**Audit reserve.** If decisions are unresolved, add 20 seeds at up to 3 audit contexts
with the most unresolved primary decisions (≤ 180 runs, with their own audit seeds
21–40). The stage-1 classification above stays primary. The 40-seed classification is
secondary, so the confidence accounting is not reopened.

## 8. Endpoints

**Primary.** At the full budget (255 runs), δ = 0.01, z = 1.96 and the primary λ grid:

- **Coverage** *C*: the fraction of the 252 decisions accepted
- **Risk** *ε*: (clearly outside) / (accepted)

The primary comparison is DF vs SF: *ΔC = C_DF − C_SF* and *Δε = ε_DF − ε_SF*, with a
paired bootstrap over the 12 audit contexts (10,000 resamples, seed 20261130). The
hypothesis is **supported** only if the 95% CI for ΔC lies above 0 **and** the upper
95% limit for Δε is ≤ 0.02. Otherwise it is reported as not supported. With 12
contexts the power is limited, and that is stated.

**Key secondary (cost).** The smallest checkpoint (0, 15, 30, 45, 63 adaptive runs) at
which DF reaches SF's full-budget coverage with no higher risk.

**Secondary.**
1. DF vs PV, LI and DS on the same metrics
2. Pessimistic risk: (clearly outside + unresolved) / accepted
3. Risk-coverage curves over z, at every checkpoint
4. δ = 0.005 and 0.02
5. The fine λ grid and the contested subset
6. Prediction error (MAE and RMSE at the 36 audit configurations) against decision
   error, per method and checkpoint, which tests whether global error predicts
   decision reliability
7. Coverage of the GP intervals at audit configurations
8. The out-of-domain stress test
9. Population and burn-in sensitivity from the pilots

## 9. Cost accounting

Reported per method: expensive runs (first use: all 255; amortised: the 192 shared
runs counted once), CPU and elapsed time, failed runs and retries. All runs use the
same machine and settings. Audit cost is reported separately, because it evaluates
the methods rather than operating them.

## 10. Compute plan (measured 172 s per run)

| Item | Runs | CPU-h |
|---|---|---|
| Training + tuning (done) | 264 | 12.6 |
| Adaptive: DF, SF, PV | 189 | 9.1 |
| Direct sampling | 255 | 12.2 |
| Audit | 720 | 34.5 |
| Audit reserve (if needed) | ≤ 180 | 8.6 |
| **Total** | | **≈ 77 of 100** |

**Repeat 2.** A second independent repeat of the adaptive and DS phases (new seeds,
rep offset 100) runs only if the measured cumulative CPU after the primary runs and
the audit is ≤ 75 h. That condition depends on compute alone, never on results. If it
runs, it is reported as a replication.

**Order.** M4 code and tests, then M5 adaptive and DS runs, then the M6 audit runs,
then M7 analysis. Methods never see audit seeds or audit outputs.

## 11. Deviation policy

After the `protocol-v1` tag, any change to a frozen item needs a new dated entry in
DECISIONS.md, labelled **deviation**, which states whether audit data had been seen.
The manuscript reports every deviation. Bugs fixed in code are not deviations unless
they change a frozen rule. They are logged in IMPROVEMENTS.md.

## 12. Positioning

The distinctions from malariasimple, Reiker et al. (adaptive calibration), Langmüller
et al. (GP emulation), StateMINT and ranking-and-selection theory are as set out in
the dossier's comparison table. Tolerance and abstention are applications of
indifference-zone selection logic, not new principles. The claimed contribution is a
controlled, audited comparison of decision-focused and prediction-focused allocation
under simulator noise and a fixed budget. A final check of competing work happens at
M8.
