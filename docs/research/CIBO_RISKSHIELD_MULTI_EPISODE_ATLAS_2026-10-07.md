# QORE CIBO — 20% drawdown engineering: multi-episode risk atlas and D1 continuity

**Date:** 2026-10-07 America/Asuncion. **Branch:** `agent/cibo-dd-riskshield-highmult-window4-d1-001`. **Source:** canonical scientific 37.772111615% replay `carrier37772-p4150`. **Research only:** the 36-month historical holdout is reused, NOT external certification evidence.

## Sovereign invariants
Trader owns and executes entries. CIBO administers after execution and cannot reject/defer. Keep 3,368/3,368 entries, zero financial Sizing rejection/defer, zero ATTACK sovereign breach and functioning Sizing + Adaptive Leverage + CIBO Compound + Compound Portfolio. Frozen capital floor USD 582,440.025295..., current target capital USD 668,910.439683, maximum DD <=25% certification gate and ideal <=20%, always optimize loss and profit jointly. Do not claim that any rule guarantees 20% OOS.

## Evidence — 37.772111615% incumbent

| Rank | Max DD % | Peak UTC | Trough UTC | Primary causal area |
|---:|---:|---|---|---|
| 1 | 37.7721 | 2021-02-09 | 2021-02-26 | ATTACK dominant, capital USD 61,696.54 peak |
| 2 | 37.6660 | 2019-07-19 | 2019-08-12 | MEDIUM 1x/2x, bootstrap |
| 3 | 37.0168 | 2020-09-10 | 2020-10-05 | ATTACK dominant |
| 4 | 36.4063 | 2020-04-03 | 2020-05-13 | ATTACK dominant |
| 5 | 34.8693 | 2020-01-31 | 2020-03-02 | ATTACK+MEDIUM |
| 6 | 32.3447 | 2020-03-23 | 2020-03-26 | ATTACK dominant |
| 7 | 31.5321 | 2019-11-04 | 2019-12-18 | ATTACK+MEDIUM |
| 8 | 31.3885 | 2020-08-19 | 2020-08-26 | ATTACK dominant |
| 9 | 30.7466 | 2020-05-21 | 2020-06-08 | ATTACK dominant |
| 10 | 30.0799 | 2020-06-24 | 2020-06-30 | ATTACK dominant |

**Interpretation:** lowering the 2021 worst episode alone cannot yield <=25%, because nine additional episodes have >30% DD. Do not tune one recorded event indefinitely. The risk protection has to generalize across market regimes and epochs.

2021 peak USD 61,696.539773 → trough USD 38,392.453907, about USD 23,304.086 losses. To reach 20% at the *same peak*, peak-to-trough loss must be <=USD 12,339.308, implying ~USD 10,965 less realized loss. This is only a local counterfactual—not a valid outcome prediction because economic path and peaks change under different policies.

Large negative 2021 ATTACK settlements: 8,106x/−USD 9,565.08, 5,000x/−USD 5,980.56 and 5,000x/−USD 3,862.30. Generalize risk by causal state and multiplier/capital stress, **not by specific Trader IDs or known future losers**.

## Experiment B1 — complete, rejected

[Run 37717684638](https://github.com/mezas3238-hue/qore-core/actions/runs/37717684638) — 10 experiments, SUCCESS. Eight pressure2 target/risk/capital combinations produced zero pressure2 risk binds and identical DD/capital; the MEDIUM partial 0.42 transferred from A1 worsened DD 40.6534%, capital USD 661,549.44. Reject; no incumbent promotion.

## Experiment C1 — complete, rejected

[Run 37718339097](https://github.com/mezas3238-hue/qore-core/actions/runs/37718339097) — 9 experiments, SUCCESS. Experimentally repurposing window7 for high multipliers (5,000–10,000x, capital USD 35k–65k) produced DD 37.66598266%, capital USD 668,746.73 and loss USD 963,755.87 vs control loss USD 957,225.91. Worse gross loss, slight capital degradation: NOT STRICT PARETO. Neutralizing original window7 caused catastrophic drop to USD 550,446: original low-capital window7 is indispensable in tested path despite 3 binds. **Do not replace window7 to create new feature.**

## Experiment D1 — completed, rejected

Workflow `.github/workflows/cibo-trader-lab-riskshield-highmult-window4-d1.yml` in isolated branch. Unlike C1, retains **original window7** and varies width/taper of the existing high multiplier window4 (initially 4,800–5,200x, factor 0.90) to include exposure up to 9,000x. Nine parallel cases include exact control, and full count/no-breach/capital/loss DD ranking. The hypothesis is causal and portfolio-wide, rather than Trader-specific.

**Do not promote D1 if its gross loss increases, its capital drops below the frozen floor, or it fails invariant checks.** Given user priority for equal-or-better terminal wealth, economic dominance vs USD 668,910 is preferred over only passing USD 582,440.

## Structural next engineering when coarse sweeps stop improving

1. Preserve the original 7 causal windows. Introduce additive optional window8 or a separate local risk-budget shield, *only* after verified comparative tests show additional usefulness. Avoid reusing a valuable existing window.
2. Build a running portfolio *loss-to-stop stress estimate* from strictly causal current open positions, adverse slippage and same-asset/correlation clusters. A risk limit is advisory for CIBO post-entry management; no entry rejection authority.
3. In MEDIUM 2019, assess MFE, MAE, closed M5 bars and expected-R for predictive partial exits vs winners harmed; no blanket stops.
4. Test all top-10 episodes after every accepted policy, not only max DD. Prevent bottleneck migration from defeating progress.
5. Run walk-forward, loss-clustering and fee/slippage stresses; **seal any fresh 3-year OOS** until architecture, parameters and calibration freeze. Results from reused research period are not certification.

## Traceability

- Baseline [run 37716702999](https://github.com/mezas3238-hue/qore-core/actions/runs/37716702999).
- B1 run `37717684638`, artifact `11524622662`, includes forensic baseline JSON and `drawdown_forensics.top_10_episodes`.
- C1 run `37718339097`, artifact `11524349886`.
- D1 isolated workflow provided above; use GitHub Actions branch filter to locate its exact run.

## D1 FINAL RESULTS — 2026-10-07 / GitHub 2026-10-08 UTC

- Initial technical run `37718642771` failed before any replay because `w4lo` was unbound outside `run_case`. Isolated workflow corrected in commit `43bb8ee92ac722777c72feebb1762287d20e6da6`.
- Corrected [run 37718741078](https://github.com/mezas3238-hue/qore-core/actions/runs/37718741078) **SUCCESS**, complete 9-case ranking and replay artifact **11525186866**. No production change.
- Frozen control reproduced exactly: capital USD **668,910.439683**, max DD **37.772111615%**, gross loss USD **957,225.911831**, ATTACK gross loss USD **955,665.772156**, window4 binds **39**, window7 binds **3**.
- W4 upper limit **6,500x** at taper 0.90: DD unchanged at **37.772111615%**, capital falls to **663,774.49**, total GL **956,731.47**. DD unchanged, no strict improvement.
- W4 upper limit **8,000x** at taper 0.90: capital USD **548,064.74** (BELOW sovereign floor), DD still 37.7721%, rejects.
- W4 upper **8,200–9,000x** at taper 0.90: capital USD **440,852.83**, DD **48.4281%**, 107 binds, rejects.
- W4 upper **9,000x** at taper 0.95: capital USD **461,193.02**, DD **58.3452%**, rejects.
- W4 upper **9,000x** at taper 0.99: capital USD **568,137.70**, DD **44.4388%**, rejects.
- Repurposed 7,000–9,000x at 0.90: capital USD **572,748.84**, DD **44.5605%**, 0 window4 binds, rejects.
- **Verdict: STRICT_PARETO_CASES=[], DOMINATES_CURRENT_CASES=[], DD_LE_25_CASES=[].** Keep the frozen 37.772111615% control; D1 did not find a promotion candidate.

## Revised P0 — additive causal headroom architecture, not global multiplier widening

These tests clarify that the current 7-window system is path dependent. Removing the 3-bind original window7 can cost more than USD 100k of terminal capital, while widening window4 broadly beyond 8,000x can destroy capital and raise DD. The ATTACK 2021 worst-loss cluster (8,106x and two 5,000x negative settlements) needs **a separate additive, state-dependent, forward-only risk monitor and response**, leaving existing windows intact.

Required scientific implementation on a fresh isolated branch:
1. Record **pre-decision and post-entry** bankroll, peak, live DD, open position stop-risk, portfolio cushion, net trader loss pressure, correlated exposure by symbol, and coherent scenario loss headroom. Validate ledger timing, no outcome leakage or use of future price.
2. Calculate stochastic/stress total downside headroom vs internal 20% DD *aspiration*, with reserves and slippage guard, but never claim mathematical guarantee. Keep Trader entries sovereign. CIBO may manage post-entry partials, stop tightening and authorized risk budget, subject to provider/account constraints.
3. Implement a new optional **eighth** independent guard ONLY if supported by causal entry/position information and promote neither this nor any result until strict replays establish DD compression with cap >=USD 668,910.44 as growth-preserving ambition, loss <=USD 957,225.91, 3,368 entries and no breaches.
4. Demonstrate value against all top-10 DD episodes: 2021 ATTACK (37.772%), 2019 MEDIUM (37.666%), 2020 Sep/Oct ATTACK (37.017%) and other >30% epochs. A local win that only shifts DD to 37.666% cannot be considered 20%-ready.
5. After research convergence: freeze and run independent unseen three-year holdout. Reused research replay is NOT certification evidence.

**No promotion performed.** Canonical branch `agent/cibo-causal-expectation-leakage-fix-001` remains unchanged by the independent RiskShield B1/C1/D1 experiments.
