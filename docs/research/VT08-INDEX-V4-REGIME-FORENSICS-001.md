# VT-08 Index V4 — Regime/Context Failure Forensics 001

Checkpoint: 2026-09-14
Issue: #547

## Status

Research-only. No V4 candidate is frozen by this document.

`DEMO_ELIGIBLE=false`
`LIVE_AUTHORIZED=false`
`REAL_CAPITAL_AUTHORIZED=false`
`PRODUCTION_AUTHORIZED=false`

## Prior governed outcomes

V2 `VT08_INDEX_V2_QORE_CANDIDATE_001` is rejected.

V3 `VT08_INDEX_V3_QORE_GEOMETRY_001` is rejected. Official one-shot V3 run `34798973408`, software SHA `106a34282fe8eac2f8c466bcc8502d4ec8d73855`, freeze SHA `138f4f4a9793ea5a6cab4572f415c387fdc8e90d`, decision artifact `10331011705`, artifact digest `sha256:1e05ff16c4b1d8924d422f3ed3d367bd69d65cae35e9d9417c49a90ebe80f2ea`.

The V3 fresh partition `[2022-09-15, 2023-09-15)` is consumed. The V2 fresh partition `[2023-09-15, 2024-08-13)` is consumed. The original development interval beginning `2024-08-13` is consumed research evidence. None of these intervals may later be relabeled as fresh validation.

## V3 failure fact pattern

The official V3 fresh result produced 51 trades, 20 winners and 31 losers, total `-9.052346600843836319822996806R`, mean `-0.1774969921734085552906469962R/trade`, PF `0.5961767113921719155635808046`, and max drawdown `11.49289879393972235909673277R`.

All three markets were negative on the fresh tranche. Both LONG and SHORT were negative. Stress after `0.05R/trade` friction failed. The deterministic 10,000-path block bootstrap failed both the positive-terminal-probability and p95-drawdown gates.

Therefore V4 research MUST NOT start from a retrospective instruction to remove one market, one side, or the 06:00 anchor.

## Exact consumed-evidence reproduction lead

A local exact-mechanics replay was performed using only the already-consumed V2 decision artifact raw-truncated evidence and the frozen V3 mechanics:

- partition: `[2023-09-15, 2024-08-13)`;
- same C2-or-C3 body-close resolver;
- same farthest-structural protected swing;
- same `risk/entry >= 0.003` geometry gate;
- same closure/reference range ratio `>= 1.2`;
- same 2.5R target;
- same next-H4 lifecycle;
- same gap and STOP-first containment.

The reproduction emitted 42 trades with approximately `+11.4015733971R`, `+0.271466R/trade`, PF `1.91`, and max DD `5.13R`.

This sign flip must be reproduced in official CI before it is treated as durable QORE evidence. It is recorded here only as the starting research lead.

## Initial structural census

The same consumed-evidence comparison shows that simple dimension cuts are not a sufficient explanation:

- 2022-23 V3 was negative in NAS100, SP500, and US30;
- 2022-23 V3 was negative in LONG and SHORT;
- 2023-24 V3 reproduction was positive in NAS100, SP500, and US30;
- 2023-24 V3 reproduction was positive in LONG and SHORT;
- both 06:00 and 10:00 changed sign between the two consumed windows.

The strongest simple categorical lead observed so far is protected-swing multiplicity. Among V3-admitted setups, `protected_swing_count == 2` produced approximately:

- 2022-23: 19 trades, `+0.204R/trade`;
- 2023-24: 14 trades, `+0.423R/trade`.

This is explicitly POST-HOC and does not authorize a V4 rule. It is a falsification target.

Other exploratory one-dimensional structural leads that were positive in both consumed one-year windows, subject to small samples and multiplicity risk, included earlier CISD/protected-swing confirmation, shallower normalized sweep depth, and stronger source-day body conviction. None is frozen.

## V4 research hypothesis families

### H1 — Protected-swing multiplicity

Test whether the farthest-swing resolver is too permissive when the closure H4 contains only one or three-plus qualifying protected swings, and whether exactly two causal protected swings encode a repeatable structural sequence rather than a fitted count.

Required outputs: count distribution, expectancy, PF, DD, market/side/anchor decomposition, temporal slices, and stress for each multiplicity class.

### H2 — CISD/protected-swing timing

Measure confirmation bar index inside the closure H4, opposing-series length, and time from manipulation extreme to confirmation. The goal is to distinguish early structural confirmation from late confirmation without turning a post-hoc timestamp threshold into a trading rule.

### H3 — Sweep/reclaim quality

Measure sweep depth normalized by the causal reference H4 range, reclaim/failed-C2 close depth, C3 close-through strength, protected-swing depth, and closure/reference expansion. Test monotonicity and stability instead of selecting the best threshold.

### H4 — Daily-bias family

Separate breakout-long, breakout-short, reversal-long, and reversal-short. Determine whether `resolve_daily_bias` combines contexts that require different entry interpretation. Bias family must remain distinct from draw-on-liquidity and from target selection.

### H5 — Regime state

Use causal diagnostics only: source-day range, source-day body fraction, rolling realized range/volatility, and cross-index agreement. These are research descriptors, not approved signal indicators. No EMA/RSI-style rule may be smuggled into VT-08 under a regime label.

### H6 — Cross-index synchronization

Measure whether same-timestamp signals across NAS100/SP500/US30 represent one correlated economic bet. Separate signal quality from portfolio concentration. A portfolio-risk finding must not be misrepresented as a trader-edge repair.

### H7 — Payoff-shape dependence

Reconstruct pathwise MFE/MAE and lifecycle exits on consumed evidence to determine whether the sign flip is caused primarily by admission quality or by the fixed 2.5R/lifecycle interaction. Target exploration remains forensic until a separate causal hypothesis is justified.

## Multiplicity discipline

The V4 research program must enumerate the hypothesis family before evaluating outcomes. Reports must distinguish:

1. predeclared structural variables;
2. exploratory thresholds;
3. post-hoc combinations;
4. findings that replicate across independent consumed time windows.

A V4 freeze is prohibited if its decisive rule exists only because it maximizes combined consumed P&L.

## Required consumed-evidence workflow

`V2 decision artifact + V3 decision artifact + existing development evidence`

-> exact V3 replay reproduction

-> per-setup structural feature ledger

-> period-by-period census

-> market / side / anchor / closure / bias-family decomposition

-> temporal slicing

-> stress and dependence diagnostics

-> multiplicity-controlled hypothesis ranking

-> V4 GO / NO-GO adjudication.

No new older tranche and no forward data may be opened before a distinct V4 identity and its validation contract are frozen.

## Definition of V4 research completion

The investigation is complete only when one of two outcomes is supported:

- **GO:** a source/structure-grounded hypothesis reproduces across consumed windows with adequate sample and stability, after which a new identity and genuinely unseen validation plan are frozen before data access; or
- **NO-GO:** no stable structural explanation survives, and Index VT-08 remains rejected rather than being rescued through retrospective filtering.
