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

## Active-runtime source verification

Read-only inspection of the active VPS source confirms the frozen Phase-2 base-risk contracts:

- VT08: AUDJPY 25 bps, GBPUSD 25 bps, GBPJPY 20 bps of assigned capital.
- R34 XAUUSD: base risk fraction 0.002; broker-risk buffer 1.02; max source-entry drift 0.10R.
- R38 EURUSD: base risk fraction 0.002; broker-risk buffer 1.02; max source-entry drift 0.10R.
- R43 GBPUSD: base risk fraction 0.002; broker-risk buffer 1.02; max source-entry drift 0.10R.
- R38 GBPJPY: base risk fraction 0.002; broker-risk buffer 1.02; max source-entry drift 0.10R.
- R42 AUDJPY: base risk fraction 0.002; broker-risk buffer 1.02; max source-entry drift 0.10R.
- VT31 NAS100: QORE 1R account fraction 0.002; broker-risk buffer 1.02.

The active workspace HEAD is local/unpublished relative to GitHub at this checkpoint, so CE2I records
the observed runtime identity separately instead of pretending GitHub can resolve that SHA.

## First source-proven CE2I economic finding — VT31 minimum-volume uplift

The active runtime source predates the two 25-SEP submits and the current uncommitted diff does not
modify VT31's `nominal_risk_r`, `resolve_certified_risk` or `build_risk_request` sizing logic.

Therefore the source-defined upper bound of the pre-broker strategy risk budget can be compared
against the observed submitted stop risk.

### Case 1 — SECONDARY

Observed:

- assigned capital: USD 142857.19;
- QORE 1R account fraction: 0.002;
- 1R: USD 285.71438;
- tier: SECONDARY;
- observed submitted stop risk: USD 10.2408;
- observed volume: 0.04.

Source upper bound before any protective shields:

```text
SECONDARY nominal risk = 0.05R
max SECONDARY allocation multiplier = 1.00
global scalar = 0.60

maximum strategy requested risk
= 285.71438 * 0.05 * 1.00 * 0.60
= USD 8.5714314
```

The actual submitted stop risk is therefore at least:

```text
10.2408 / 8.5714314 = 1.1947596x
```

or approximately **19.48% above the maximum possible strategy-requested budget** before any
additional state/loss/breaker shields, which can only reduce that budget further.

Derived stop-risk per 1.00 source volume:

```text
10.2408 / 0.04 = USD 256.02
```

The maximum raw risk-sized volume under the upper-bound strategy budget is:

```text
8.5714314 / 256.02 = 0.03348
```

which is below the observed 0.04 execution volume.

### Case 2 — REARM_MID

Observed runtime decision reason: `AUTHORIZED_REARM_MID`.

Observed:

- assigned capital: USD 142857.19;
- 1R: USD 285.71438;
- REARM MID nominal risk: 0.05R;
- REARM allocation multiplier: 0.50;
- global scalar: 0.60;
- observed submitted stop risk: USD 26.0712;
- observed volume: 0.04.

Source upper bound before any further shields:

```text
maximum strategy requested risk
= 285.71438 * 0.05 * 0.50 * 0.60
= USD 4.2857157
```

The actual submitted stop risk is at least:

```text
26.0712 / 4.2857157 = 6.083278x
```

or approximately **508.33% above the maximum pre-broker strategy budget**.

Derived stop-risk per 1.00 source volume:

```text
26.0712 / 0.04 = USD 651.78
```

The maximum raw risk-sized volume under the upper-bound strategy budget is:

```text
4.2857157 / 651.78 = 0.006575
```

which is far below 0.04.

### Why 0.04 matters

The active cTrader DEMO contract normalizes NAS100 minimum source volume to 0.01.

VT31's frozen four-leg management requires:

```text
execution_minimum_volume = broker minimum volume * 4
                         = 0.01 * 4
                         = 0.04
```

Both observed submits are exactly 0.04.

Given the source risk bounds above, both cases necessarily mapped below 0.04 before the broker/management
minimum was applied.

**CE2I finding:**

```text
VT31 MANAGEMENT GRANULARITY FLOOR
-> MINIMUM VOLUME UPLIFT
-> ACTUAL STOP RISK > STRATEGY REQUESTED RISK
```

This is the opposite of capital efficiency. It is not yet a policy defect verdict because the
four-leg management structure may itself create compensating economic value. It is, however, a
proven inefficiency family that Phase 2/3 must quantify across a larger sample.

CE2I must later test alternatives such as:

- provider/contract granularity with smaller executable legs;
- economically equivalent exposure representation;
- management structures that preserve certified behavior at finer granularity;
- explicit Risk accounting for mandatory minimum-volume uplift.

No runtime change is authorized by this finding.

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
