# CE2I Phase 2 — Real Sizing-Path Reconstruction

Status: **IN PROGRESS**

## Objective

Reconstruct the economic provenance of every requested volume used by the seven
active cTrader DEMO Trader lineages before proposing any new CE2I sizing policy.

## Source-truth finding

All seven paths ultimately use the shared broker primitive
`size_volume_for_risk`, but their risk budgets are not homogeneous.

| Trader | Base risk model | Strategy/cognitive scaling before broker sizing |
|---|---|---|
| VT08 FOREX | symbol BPS x assigned capital | CIBO ALLOW/DENY; frozen symbol risk fraction |
| R34 XAUUSD | assigned capital x 0.002 | R34 state/governor risk scale |
| R38 EURUSD | assigned capital x 0.002 | fragility scale x structural overlays |
| R43 GBPUSD | assigned capital x 0.002 | structural x side/rank overlay x drawdown governor |
| R38 GBPJPY | assigned capital x 0.002 | selected policy x fragility overlay |
| R42 AUDJPY | assigned capital x 0.002 | authority scale x first fragility x second fragility |
| VT31 NAS100 | assigned capital x 0.002 = 1R | nominal tier x allocation x 0.60 x state/loss/breaker shields |

VT31 additionally requires a four-broker-step minimum volume because the certified
management model needs executable half/quarter legs.

## Phase-2 implementation

`src/qore/infrastructure/cibo_capital_efficiency_reconstruction.py`

The module freezes:

- one source contract per Trader sizing path;
- base risk model;
- strategy/cognitive scaler identity;
- shared broker sizing identity;
- COMPLETE vs PARTIAL evidence semantics;
- deterministic reconstruction of:
  - requested volume;
  - assigned capital;
  - requested stop risk;
  - strategy requested risk budget;
  - stop risk per volume;
  - requested margin;
  - margin per volume;
  - broker step/minimum;
  - broker-minimum uplift;
  - risk-budget utilization;
  - unused strategy risk after broker step flooring;
  - margin fraction of assigned capital.

Historical events that predate the richer telemetry are **PARTIAL**, never silently
filled from current code.

## Passive telemetry extension

The cTrader DEMO free sink is extended only to record the already-existing
`CiboRiskRequest` economics used for the submission.

This does not:

- change requested volume;
- change Risk;
- change broker quantity;
- change entry/stop/target;
- add an execution gate;
- create a new order.

It only makes future behavior evidence sufficient for CE2I reconstruction.

## Remaining Phase-2 work

1. Consume real PR #637 / runtime behavior rows.
2. Produce per-Trader observed reconstruction ledgers.
3. Quantify COMPLETE vs PARTIAL evidence coverage.
4. Identify observed unused strategy-risk headroom caused by broker flooring.
5. Preserve margin consumption for Phase 3 provider normalization.
6. Do not claim unused *margin headroom* until decision-time authoritative
   free-margin/margin-budget evidence is explicitly captured.

## Exit gate

Phase 2 closes only when actual observed sizing cases for the seven Trader paths can
be reconstructed chronologically and the evidence gaps are explicitly reported.
