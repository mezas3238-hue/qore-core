# QORE CIBO — forensic addendum / 2026-10-08: dual and multi-episode DD bottlenecks

**Status:** research-only, not certification; exact reused holdout.  
**Canonical master handoff remains:** `docs/research/CIBO_MASTER_CONTINUITY_HANDOFF_2026-10-07_TRUE_CEILING_DD_AND_ATTACK_LOSS_COMPRESSION.md`.  
**Branch:** `agent/cibo-causal-expectation-leakage-fix-001`.  
**Preserve sovereign rules:** $60 initial; capital floor USD 582440.0252953678696769360345; 3368/3368 Trader admissions; no reject/defer, sovereign breach, identity/date hardcoding, or future-outcome leakage. Goal DD <=25%, ideal 20–22%; final certification only after scientific exams and fresh OOS.

## Findings independently verified from GitHub Actions

1. **Early W6 DD defense** [run 37764222387](https://github.com/mezas3238-hue/qore-core/actions/runs/37764222387) succeeded operationally; 16 candidates, **no** floor-valid DD improvement and no strict Pareto improvement. Its best raw DD reduction at `w6-l010-f750` reached 35.22709% but terminal capital USD 527455.13, **below sovereign floor**. Most useful insight: early-DD W6 is exposed to discrete compounding cliffs. Reject all cases below floor.
2. **W6 taper boundary ridge** [run 37764486057](https://github.com/mezas3238-hue/qore-core/actions/runs/37764486057) produced **`w6-f9490`**: DD **35.227092840837%**, ending capital **USD 670925.7207689918**, total gross loss **USD 959321.2644996847**, ATTACK gross loss **USD 957755.1920641476**, total PF **1.6993128846**, floor headroom ~USD 88485.70, all 3368 entries, no sovereign breach. This is **STRICT PARETO relative to `m1-0700`**: DD -0.0130966 percentage points, total gross loss -USD 40.79266 and ATTACK gross loss -USD 40.79266; capital -USD 0.28669.
3. **Important policy distinction**: `w6-f9490` is **not a strict global Pareto improvement** versus `f-m2850-h0060` (global GL comparator from run 37762989521). Versus that comparator, `w6-f9490` lowers DD by ~1.18162 percentage points and retains floor, but still has ~USD 1636.20 more total GL, ~USD 1626.08 more ATTACK GL, and ~USD 48.38 less capital. Treat as the current local lower-DD frontier; **do not claim global PROMOTION** without the rebound compensation.
4. **2020 causal atlas** [run 37764884178](https://github.com/mezas3238-hue/qore-core/actions/runs/37764884178) traced original `m1-0700` Apr–May 2020 window to 118 final trade receipts and reconciled its USD 1676.99 total gross-loss rebound against the strict-global comparator. Summary trade receipts lack joined pre-entry context; no decisions may be tuned from ex-post outcomes or signal IDs.
5. **Dual-bottleneck forensic workflow** [run 37764941027](https://github.com/mezas3238-hue/qore-core/actions/runs/37764941027) and expanded [run 37765054291](https://github.com/mezas3238-hue/qore-core/actions/runs/37765054291) verified source artifact SHA256 `3ed693e2e8b583bf542b328bd6332c702d0b4b589bf0e8518ee4ff38005835ed`. Workflow: `.github/workflows/cibo-trader-lab-dd-dual-bottleneck-forensics-20261008.yml`. These are forensic observations, no policy change or new performance claim.

## Updated top DD atlas on w6-f9490 (official engine attribution)

| Rank | Peak → Trough (UTC) | DD | Dominant mode |
|---:|---|---:|---|
| 1 | 2019-07-19 → 2019-08-07 | 35.227093% | MEDIUM |
| 2 | 2020-04-03 → 2020-05-13 | 35.012921% | ATTACK |
| 3 | 2020-09-10 → 2020-09-28 | 34.604591% | ATTACK |
| 4 | 2021-02-09 → 2021-03-03 | 33.382323% | ATTACK |
| 5 | 2020-03-23 → 2020-03-26 | 32.272043% | ATTACK |
| 6 | 2020-08-19 → 2020-08-26 | 31.897901% | ATTACK |
| 7 | 2020-05-21 → 2020-06-08 | 30.835124% | mixed ATTACK/MEDIUM |
| 8 | 2020-06-24 → 2020-06-30 | 30.823193% | mixed ATTACK/MEDIUM |
| 9 | 2020-01-31 → 2020-03-06 | 30.026655% | mixed ATTACK/MEDIUM |
| 10 | 2019-11-04 → 2019-12-11 | 28.700043% | mixed ATTACK/MEDIUM |

**Implication:** to reach DD <=25%, solving only the first two episodes is insufficient. At least these ten historically observed peaks would need to move below target; additional episodes may appear after the path changes. Avoid overoptimizing one cliff.

## 2019 MEDIUM loss mechanics (w6-f9490)

Official peak equity USD 79.7639386, trough equity USD 51.6654219, official max-DD net USD -28.0985167. Mode MEDIUM only; net by multiplier: 1x **-USD 24.0403661**, 2x **-USD 4.05815063**. From 59 final receipts with exits inside episode: 41 losses and 18 wins; gross receipt losses USD 40.4529, gross profit USD 16.0044, final receipt net **-USD 24.4485**. The **USD 3.65** difference from official DD attribution must be reconciled using timeline/open-risk/partial-settlement accounting before treating final receipts as causal PnL. The summary-only trade receipts do **not** have pre-entry expectation/M5 features; inspect frozen manifest and replay ledger, not outcome labels, when developing interventions. Do not blacklist traders, symbols, or dates.

## 2020 ATTACK mechanics (m1-0700)

Official original peak-to-trough 2020-04-03 to 2020-05-13; ATTACK USD -253.8994, MEDIUM +USD 5.4120. The 118 final receipts have 66 losers / 52 winners; receipt gross losses ~USD 743.2249, gross profit ~USD 495.0379 and final receipt net ~USD -248.1870; **do not equate receipt aggregation directly to official event-time drawdown attribution**. `w6-f9490` compresses this episode to **35.012921%**, moving maximum DD back to 2019 MEDIUM.

## Next engineering sequence

1. Freeze case `w6-f9490` as a **local research comparison**, not globally approved sovereign carrier. Record both `w6-f9490` and global comparator.
2. Join frozen manifest with 2019 MEDIUM losing AND winning signal contexts. Measure discriminative power of closed M5-bar deterioration, H1/H4 regime, expected-R, MFE before adverse, time underwater, live DD, peak capital, active stop risk, portfolio concurrency. No outcome or future signal as policy input.
3. Join ATTACK 2020 loss clusters and identify whether pre-entry/causal post-entry risk signals differentiate 50–170x clusters from winners. Explicitly count protected winners and gross-profit sacrificed under each candidate, not just losses saved.
4. Design **multi-bottleneck**, identity-free **post-entry** lifecycle defense (and bounded economic-group envelope where independently justified), respecting all 3368 entries. Avoid broad global taper or simply moving one DD episode above another.
5. Every replay must compare capital, DD, total/ATTACK GL, PF, admissions, breaches, bind counts, full top-10 DD atlas and economic-compounding cliffs. Iterate causal hypothesis → Trader Lab replay → STRICT PARETO; no certification claims from reused holdout.
6. Once DD <=25% achieved **without economic floor violation**, freeze and begin scientific battery: accounting provenance, ablations of Sizing/Adaptive Leverage/CIBO Compound/Compound Portfolio, clustered loss & Monte Carlo/path stress, costs/slippage, provider/margin/concurrency stress, temporal walk-forward, fresh sealed OOS, forward/shadow, rescue/integrated/World Cup exams.

**Note:** This addendum is a traceable supplement, not an override of the master handoff, and avoids overwriting another architect's document on a shared active branch.
