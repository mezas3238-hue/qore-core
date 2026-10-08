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
