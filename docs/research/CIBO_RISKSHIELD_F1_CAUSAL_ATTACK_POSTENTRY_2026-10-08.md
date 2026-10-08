# QORE CORE — CIBO RiskShield F1: ATTACK causal post-entry lifecycle

Date: 2026-10-08 (America/Asuncion). Status: research on reused 3-year holdout, **NOT certified**. Isolated branch: `agent/cibo-riskshield-attack-lifecycle-f1-001`. Source revision `ebbfacc6d28c26c32e76fb3bb6043e9d55f32dec`.

## Source-of-truth economic baseline

Research carrier: `carrier37772-p4150`, historical replay [37716702999](https://github.com/mezas3238-hue/qore-core/actions/runs/37716702999), terminal capital **USD 668,910.439682713**, max DD **37.7721116155%**, gross loss total **USD 957,225.911831171**, ATTACK gross loss **USD 955,665.772155971**, profit factor ~**1.6987383**, **3,368/3,368 entries**; zero ATTACK sovereign breach.

A separate accounting diagnostic `sovereign_floor_breach_usd` was observed around USD 84.617 in the source replay. Unlike `attack_sovereign_breach_usd=0`, this remains unresolved and must not be presented as completely clean sovereign accounting without further inspection.

Frozen acceptance floor **USD 582,440.025295**, but the preferred goal is >= current capital and >= current profit, with falling gross loss and DD. Final milestone for the user is **DD <= 22%**, distinct from certification; independent fresh 3-year holdout stays sealed until parameters are frozen.

## E1 predecessor — completed and rejected

[RiskShield Portfolio Shock E1](https://github.com/mezas3238-hue/qore-core/actions/runs/37721188855), run 37721188855, artifact 11525552745, all 9 cases replayed successfully. No STRICT PARETO candidate. Weak modifications to the 0.05 portfolio last-loss trigger or 0.50 taper remained non-incremental (DD **37.7721%** unchanged). Stronger changes led to 40.48%, 41.79%, 55.58%, 60.95% or 67.11% DD and/or sharp compounding degradation. The broad allocator is a proven dangerous knob, not the solution.

## B1/C1/D1 predecessor scientific evidence

- B1 pressure2 context lane: no new binds; all narrow pressure2 variants were equivalent to the current control, no economic win.
- C1 high multiplier cap via repurposed window7: 37.6659827% DD but greater gross losses; loss of original window7 can destroy economic compounding.
- D1 widening existing window4 from 5200x up to 9000x: significant wealth destruction; DD frequently worsened.
- Top-10 peaks across 2019–2021 all >30% DD; correcting 2021 alone cannot deliver 22%.

## New hypothesis F1

Test isolated, **optional ATTACK-only post-entry** lifecycle `ADVERSE_PARTIAL_REDUCTION`, using strictly causal bar-close adverse signal with action at next M5 open (source `cibo_position_lifecycle.py`) and a *pre-existing at-entry* projected open stop-risk fraction, without touching any MEDIUM stop or bootstrap map, without rejecting Trader entries, and without replacing the seven ATTACK drawdown windows or the portfolio shock controls.

This uses already-supported experimental interfaces:
- `--lifecycle-attack-override-feature ADVERSE_PARTIAL_REDUCTION`
- `--lifecycle-attack-override-adverse-partial-fraction`
- `--lifecycle-attack-override-projected-open-stop-risk-fraction-trigger`
- `--lifecycle-adverse-loss-cut-r -0.40`
- `--lifecycle-adverse-partial-max-favorable-r 0.50`

Frozen control plus 7 test combinations:

| Candidate | Partial fraction | Projected risk trigger |
|---|---:|---:|
| carrier37772-control | no ATTACK override | n/a |
| atk-p05-risk10 | 0.05 | 0.10 |
| atk-p10-risk10 | 0.10 | 0.10 |
| atk-p15-risk10 | 0.15 | 0.10 |
| atk-p20-risk10 | 0.20 | 0.10 |
| atk-p10-risk15 | 0.10 | 0.15 |
| atk-p15-risk15 | 0.15 | 0.15 |
| atk-p10-risk20 | 0.10 | 0.20 |

Workflow: [RiskShield F1](https://github.com/mezas3238-hue/qore-core/actions/runs/37737555155), source `.github/workflows/cibo-riskshield-attack-lifecycle-f1.yml`. Never infer win before final rankings and artifact.

STRICT PARETO gate asserts `decision_count=trade_count=3368`, all entries preserved, no MEDIUM Sizing rejection/defer, `attack_sovereign_breach_usd=0`, capital >= frozen floor, total gross loss <= current and ATTACK gross loss <= current, max DD strictly below 37.772111615%. A stronger dominant gate additionally requires terminal capital >= **USD 668,910.439682713**.

The design attempts to preserve profitable ATTACK tails by leaving residual runners and avoiding full stop cuts. But partial reductions can hurt future compounding; severe adverse movement can happen before M5 defenses activate; there is NO guarantee DD <=22% in unseen periods.

## Next steps

1. Complete 8 replay rankings; distinguish lifecycle application count vs actual M5 exit event count and whether triggers bind. Reconcile the source and experimental control.
2. If ATTACK override is helpful but globally harmful, add pre-entry *causal context* criteria to the override, separate from Trader identity and future outcome, and test winner collateral damage via receipts.
3. Build separate portfolio-open-risk telemetry and aggregate post-entry risk budget, ensuring it is genuinely consumed in decisions. Preserve original seven windows.
4. Re-run all top-ten DD episodes on any new Pareto candidate, not only current worst.
5. Investigate `sovereign_floor_breach_usd` with ledger provenance before certification. Seal fresh unseen 3-year holdout.

**No default promotion authorized in this document.** Only replay-confirmed improvements can be promoted.

## F1 final experimental result and winner collateral analysis

- Corrected authoritative [run 37737706543](https://github.com/mezas3238-hue/qore-core/actions/runs/37737706543): **SUCCESS**, all eight complete replay cases; artifact **11532810886**. Earlier 37737555155 was a shell configuration failure; 37737663208 is a non-authoritative configuration variant with missing portfolio shock parity.
- Exact frozen control reproduced capital USD **668,910.439682713**, max DD **37.77211161549%**, total gross loss USD **957,225.91183**, ATTACK gross loss USD **955,665.77216**. `sovereign_floor_breach_usd=84.6172359344`, separate existing accounting anomaly.
- Best of the seven isolated adverse partials by DD, `atk-p05-risk10` (partial **5%**, projected ATTACK open stop risk >=10%), produced capital USD **664,842.8864057**, DD **49.795139385%**, gross loss **937,825.5143346**, PF **1.70886**, applied to 124 ATTACK positions. **NOT Pareto**; all larger partials were worse, with DD up to ~70.891%, capital as low as USD 49,230.4455.
- Differential receipt-level forensic comparison against *exact control* for the mild 5% case, using all `trade_receipts`:
  - **207 positions** had nontrivial realized net PnL changes (not equal to applied-override count, because path changes cascade to later positions).
  - **116 originally profitable positions** lost a total of **USD 23,468.111593** net PnL.
  - **91 originally loss-making positions** were improved by **USD 19,400.558316** net PnL.
  - **Net difference: −USD 4,067.553277**, matching terminal capital deficit before rounding.
  - Example significant originally positive positions impacted across years, not just 2021: June 2022 USD 48,900 winner loses USD 3,785; March 2022 USD 31,100 winner loses USD 3,300; March 2021 USD 4,746.96 winner loses USD 2,751.71.
- Causal scientific conclusion: a *directionally correct* loss reduction gate is NOT sufficient. This intervention harms far more winning PnL than it rescues in losses and triggers pathological compounded drawdowns; attack global partial EXIT should be rejected.
- **Stop tuning this ATTACK override** unless an incremental predecision/closed-bar discriminator separates loser deteriorations from winners using strictly causal MFE/MAE/expected-R/market context and proves preserved winner PnL; no Trader identity hardcode, no future outcome classification.

The next independent code path is additive window8 scientific test [run 37738207384](https://github.com/mezas3238-hue/qore-core/actions/runs/37738207384), preserving original window7 and all four economic engines. See `agent/cibo-riskshield-additive-window8-g1-001` and its separate G1 report; G1 results are not yet a certification.
