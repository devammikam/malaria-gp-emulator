# 12-week plan

Started **Monday 16 November 2026** (Week 1). The source protocol is the research
dossier (*When can a fast malaria simulator preserve an intervention decision?*).
Design decisions are in [DECISIONS.md](DECISIONS.md). Each code change is announced
in [IMPROVEMENTS.md](IMPROVEMENTS.md) before it is written.

Status key: ⬜ not started · 🟨 in progress · ✅ done · ⛔ blocked

| # | Week (starts) | Milestone | Deliverables | Gate: done when | Status |
|---|---|---|---|---|---|
| M1 | 1 (16 Nov) | Model identity and design | Version record, scenario manifest, seed plan, fixed net scenario, reproducible R runner | Every run reproducible from the archive. Training, tuning and audit seeds disjoint. Same seed gives identical output. | ✅ 16 Nov |
| M2 | 2 (23 Nov) | Pilot *(go/no-go)* | Runtime at 500/5000/10000 people. Burn-in 730 vs 1460 days, then 2190 vs 3285 (D9). Between-seed SD. Curvature of the coverage response. Normality check of replicate means. | Budget ≤ 100 CPU-hours. Population and burn-in locked. Primary check confirmed (D1). | ✅ 19 Nov: population 10,000, burn-in 3285 days (D8, D9) |
| M3 | 3 (30 Nov) | Locked protocol | 16 training and 12 audit EIR settings, 21 λ values, δ = 0.01 (0.005, 0.02 sensitivity), frozen allocation rule, pre-registration note | Protocol committed and tagged `protocol-v1`. Nothing tuned on audit data afterwards. | ⬜ |
| M4 | 4 (7 Dec) | Working prototype | Modules `design.py`, `gp.py`, `allocate.py`, `decision_audit.py`, `figures.py`. Out-of-domain abstention. Tests. | Tests show a wrong choice fails, a clear choice passes and an extrapolated setting abstains. | ⬜ |
| M5 | 5–6 (14 Dec) | Training and matched comparisons | 192 initial runs, then ≤ 64 adaptive runs for each method (decision-focused, variance, space-filling, interpolator, direct sampling) | Every method used the same expensive-run budget, logged. | ⬜ |
| M6 | 7 (28 Dec) | Independent audit | 720 audit runs with fresh seeds | Reference decisions classified as clearly within tolerance, clearly outside, or unresolved. | ⬜ |
| M7 | 8 (4 Jan) | Analysis | Risk-coverage-cost figure, prediction error vs regret, δ sensitivity | δ not changed after seeing results. | ⬜ |
| M8 | 9–10 (11 Jan) | Manuscript draft | Methods and Results, then Introduction, Discussion and supplement | Every number maps to an archived table. Final check of competing work. AI tool use disclosed in Methods or Acknowledgements (journal policy). | ⬜ |
| M9 | 11 (25 Jan) | Reproducibility | Clean-environment rerun, documentation, LICENSE, tagged release with DOI | One command regenerates every figure. | ⬜ |
| M10 | 12 (1 Feb) | Submission package | PLOS Comp Bio (fallback: Epidemics) | Supervisor confirms significance and journal fit. | ⬜ |

**Presentation:** the supervisor meeting comes before or during Week 1–2. The slides
cover the question, the comparison that makes it new, the model, the data, and M1–M2.

**Extension (weeks 13–24)** runs only if the core is complete. It adds native
`malariasimple` as a cheaper model, at matched cost. Stop it if installation or input
matching fails.

## Scope cuts if behind schedule (in order)
1. Drop the extension.
2. Drop the prediction-variance baseline (keep space-filling, interpolator, direct sampling).
3. Reduce training EIR settings from 16 to 12. Never reduce audit replication.
