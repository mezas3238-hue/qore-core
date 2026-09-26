# CE2I Phase 2 — Observed cTrader DEMO Evidence Checkpoint — 2026-09-26

Status: **OBSERVED / PARTIAL / PHASE 2 IN PROGRESS**

## Runtime evidence source

Observed read-only from the active cTrader DEMO workspace:

- workspace: `C:\QORE_CTRADER_DEMO_FREE`
- runtime branch: `agent/ctrader-demo-free-cibo-lab-001`
- runtime HEAD observed: `c83179b1f4a48d8af5a4370e63e397ab0f66eb39`
- event source: `var/ctrader_demo_free/events.jsonl`
- total rows observed: 126
- `CTRADER_DEMO_FREE_SUBMIT` rows observed: 2

No VPS file, runtime, broker order or configuration was changed during this inspection.

## Submit coverage

| Trader | Observed submit rows |
|---|---:|
| VT08_FOREX | 0 |
| R34_XAUUSD | 0 |
| R38_EURUSD | 0 |
| R43_GBPUSD | 0 |
| R38_GBPJPY | 0 |
| R42_AUDJPY | 0 |
| VT31_NAS100 | 2 |

Observed submit coverage is therefore **1/7 Trader paths**.

This is not enough to close Phase 2.

## Observed VT31 cases

### Case 1

- recorded_at: `2026-09-25T14:08:05.580619+00:00`
- request_id: `vt31-004195ab46dc82573e0a22ed`
- side: long
- intended entry: 30498.3
- stop: 30473.2
- target: 30684.000
- requested volume: 0.04
- requested stop risk: USD 10.2408
- assigned capital: USD 142857.19
- derived stop risk / requested volume: USD 256.02
- observed stop risk / assigned capital: approximately 0.0071686%

### Case 2

- recorded_at: `2026-09-25T14:36:05.212798+00:00`
- request_id: `vt31-67b10587bf793e37af3c6c64`
- side: long
- intended entry: 30468.5
- stop: 30404.6
- target: 30684.000
- requested volume: 0.04
- requested stop risk: USD 26.0712
- assigned capital: USD 142857.19
- derived stop risk / requested volume: USD 651.78
- observed stop risk / assigned capital: approximately 0.0182498%

## Why both rows are PARTIAL under CE2I

These submits occurred before the richer CE2I sizing telemetry was present in the event rows.

The historical rows do not contain:

- observed `sizing_path`;
- `strategy_requested_risk_usd`;
- `stop_loss_per_volume`;
- `requested_margin`;
- `margin_per_volume`;
- `volume_step`;
- `minimum_volume`;
- `minimum_volume_uplifted`.

The current source contract can identify the expected VT31 sizing path, but CE2I does not pretend
that current source text is the same thing as event-time observed telemetry.

Therefore these two rows remain:

```text
RECONSTRUCTION_STATUS = PARTIAL
```

## Current account allocation evidence

The observed cTrader DEMO binding records:

- account balance at binding: USD 1,000,000;
- seven equal Trader allocations;
- allocation per Trader: approximately USD 142,857.142857;
- risk role: `CAPITAL_ALLOCATOR_ONLY`;
- CIBO role: `SIZING_AND_POSITION_INTELLIGENCE_SOVEREIGN`;
- cross-trader risk reduction: false.

This confirms that Phase 2 must reconstruct requested sizing independently from the allocator:
the allocator preserves the requested size and does not prove who economically selected it.

## Additional behavior evidence present

The Behavior Lab contains substantial position/runtime evidence, including:

- 1,503 normalized runtime behavior rows;
- 781 position-path samples;
- 490 management fail-closed observations;
- 39 management observations;
- VT31 settlement evidence.

That evidence is valuable for later CE2I capital-recycling and path-aware phases, but it does not
replace missing decision-time sizing economics.

## Engineering response added to PR #651

Phase 2 now adds:

- frozen sizing-path contracts for all seven Trader lineages;
- COMPLETE/PARTIAL evidence semantics;
- passive reconstruction of risk-budget utilization where evidence exists;
- passive reconstruction of unused strategy risk caused by volume quantization;
- passive reconstruction of requested margin fraction;
- enriched sink telemetry for future submits;
- an automated JSONL reconstruction/report script.

The sink extension records already-existing request economics only. It does not alter any order.

## Phase-2 gate state

```text
SOURCE PATH RECONSTRUCTION: IMPLEMENTED
PASSIVE TELEMETRY CONTRACT: IMPLEMENTED
HISTORICAL OBSERVED SUBMITS: 2
OBSERVED TRADER COVERAGE: 1/7
COMPLETE CE2I ROWS IN EXISTING HISTORY: 0
PARTIAL CE2I ROWS IN EXISTING HISTORY: 2
PHASE 2: NOT CLOSED
```

Next evidence target:

Acquire real submit evidence for the remaining Trader paths and future VT31 submissions with the
complete telemetry schema, then quantify risk-budget utilization and margin consumption without
changing sizing policy.
