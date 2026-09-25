# QORE cTrader DEMO LIVE Behavioral Lab V1

**Research identity:** QORE_CTRADER_DEMO_LIVE_BEHAVIOR_LAB_V1  
**Branch:** agent/ctrader-demo-live-behavior-lab-001  
**Base:** agent/ctrader-demo-free-cibo-lab-001 @ e30a03ebab380a6d2b64f294aa1292203e8d8de8  
**Environment:** cTrader DEMO only  
**Authority:** OBSERVE / RECONSTRUCT / COMPARE only

## 1. Owner objective

Turn the existing cTrader DEMO FREE runtime into a behavioral laboratory that can
study every case solved by every trader in live market conditions.

The lab must answer, trade by trade:

1. What market evidence did the trader see?
2. What candidate or abstention did the trader produce?
3. What did CIBO contribute?
4. What sizing path actually produced the requested volume?
5. What did QORE Risk allocate or block?
6. What order was requested and what did cTrader fill?
7. How did the position evolve after entry?
8. Which protection actions became eligible?
9. Which protection actions were actually sent and accepted?
10. Was there partial banking, break-even, trailing, target extension or early exit?
11. What finally closed the trade?
12. Did the realized live behavior match the trader's declared lifecycle contract?

The laboratory must never change the answer to any of those questions by altering
the trader while it is observing it.

## 2. Non-interference law

The lab has no authority to:

- create or cancel strategy candidates;
- change CIBO posture or sizing;
- change QORE Risk allocation;
- submit, cancel or amend broker orders;
- modify stop loss or take profit;
- close positions;
- change strategy thresholds or methodology;
- promote a trader to another execution environment.

It is an append-only evidence and reconstruction layer.

## 3. Current cTrader DEMO population

The current DEMO FREE runtime loads seven trader lineages:

- VT08
- TURTLE_SOUP_XAUUSD_R34
- TURTLE_SOUP_EURUSD_R38
- TURTLE_SOUP_GBPUSD_R43
- TURTLE_SOUP_GBPJPY_R38
- TURTLE_SOUP_AUDJPY_R42
- VT31_NAS100

The runtime declares QORE Risk as CAPITAL_ALLOCATOR_ONLY.

## 4. Current behavior contracts found in source

### VT08 Forex

Observed source path:

CIBO authorization -> DEMO-native risk sizing -> cTrader DEMO request.

The present sizing implementation uses symbol-specific frozen base risk basis
points and converts the resulting monetary risk into broker volume from the
current cTrader contract economics.

This is not equivalent to evidence that CIBO is dynamically increasing or
decreasing risk from live trade-by-trade learning. The lab must therefore record
the exact CIBO authorization, requested risk, requested volume and resulting fill
rather than infer that dynamic CIBO sizing occurred.

Current lifecycle evidence includes static broker SL/TP plus the certified H4
containment exit.

### R34 XAUUSD

Declared lifecycle:

STATIC_SL_TP_PLUS_24H_EXIT.

No generic trailing contract is declared by the cTrader DEMO runtime metadata.

### R38 EURUSD

Declared lifecycle:

STATIC_OR_PROTECT_DOL_LOCK_M5_SWING_TRAIL_PLUS_24H_EXIT.

The lab must preserve DOL eligibility, protection activation, every stop
amendment and final exit.

### R43 GBPUSD

Declared lifecycle:

STATIC_OR_PROTECT_DOL_LOCK_M5_SWING_TRAIL_PLUS_24H_EXIT.

The lab must distinguish a valid hold from a missed protection action.

### R38 GBPJPY

Declared lifecycle:

STATIC_OR_PROTECT_DOL_LOCK_M5_SWING_TRAIL_PLUS_24H_EXIT.

### R42 AUDJPY

Declared lifecycle:

STATIC_OR_PROTECT_DOL_LOCK_M5_SWING_TRAIL_PLUS_24H_EXIT.

### VT31 NAS100

VT31 does not currently take its DEMO requested volume from the VT08 CIBO sizing
module. Its adapter resolves the frozen VT31 certified risk context and then
builds a DEMO-native risk request from that resolution and the current cTrader
symbol contract.

Current VT31 V4 position management is conditional, not a generic continuous
trailing stop:

1. A CORE/non-compressed trade may bank a base partial at 1.25R.
2. Break-even on the remaining runner is armed only after the relevant next-M1
   arm condition.
3. DOL1 can trigger banking / acceptance logic.
4. Runner state is activated only after DOL1 acceptance where applicable.
5. PS2 stop advancement requires the runner state and two qualifying protected
   swing confirmations.
6. Therefore an exit in profit does not by itself prove that a trailing stop
   should already have been active.

This distinction is a primary reason for the Behavioral Lab.

## 5. Evidence sources already produced by DEMO FREE

The current runtime already writes two independent append-only evidence streams:

- artifacts/ctrader_demo_free_runtime_events.jsonl
- var/ctrader_demo_free/events.jsonl

The first contains strategy/runtime/management telemetry.
The second contains cTrader DEMO execution-sink telemetry.

The V1 lab normalizes both streams into one chronological evidence model and
groups events into a stable case identity, preferring:

1. signal fingerprint;
2. broker position id;
3. request/client/basket identity plus decision boundary;
4. deterministic event fingerprint as a final fallback.

## 6. V1 implementation

New module:

src/qore/infrastructure/ctrader_demo_live_behavior_lab.py

Responsibilities:

- classify events into SIGNAL / CIBO / RISK / EXECUTION / POSITION /
  MANAGEMENT / EXIT / FAULT;
- preserve the original payload;
- produce stable case ids;
- build per-case chronology;
- capture requested volume and requested stop risk;
- surface protection, partial-close, exit and fault events;
- attach the declared sizing and management contract for known traders;
- report observational gaps without declaring a strategy failure when
  eligibility has not yet been proven.

New report builder:

scripts/ctrader_demo_live_behavior_report.py

Default inputs:

- artifacts/ctrader_demo_free_runtime_events.jsonl
- var/ctrader_demo_free/events.jsonl

Default outputs:

- artifacts/ctrader_demo_live_behavior_lab/events.normalized.json
- artifacts/ctrader_demo_live_behavior_lab/case-report.json
- artifacts/ctrader_demo_live_behavior_lab/case-report.md

## 7. Interpretation law

The laboratory uses three different statements and they must never be confused.

### NOT_OBSERVED

The evidence does not contain the event.

Example:

no_protection_or_trailing_event_observed

This alone is not a defect verdict.

### ELIGIBLE_BUT_NOT_EXECUTED

A future V2 diagnostic may use trader-state evidence to prove that a protection
rule became eligible but no broker amendment was attempted.

This is actionable.

### ATTEMPTED_BUT_REJECTED

The trader attempted the action and the execution path rejected or failed it.

This is an execution defect.

The first implementation intentionally stops at NOT_OBSERVED unless eligibility
can be demonstrated from source evidence.

## 8. VT31 first forensic case

The Owner reports a recent VT31 cTrader DEMO operation that closed at a
profit-protecting stop while CIBO sizing and trailing were not visibly observed.

The source review already establishes two points that the forensic report must
separate:

1. VT31's current sizing route is VT31 certified-risk resolution -> DEMO broker
   sizing, not the VT08 CIBO sizing module.
2. VT31 trailing/protection is state-gated. Break-even and PS2 stop advancement
   are separate events with explicit prerequisites.

The next case reconstruction must therefore answer:

- what VT31 tier/family was executed;
- final_risk_r;
- requested and filled volume;
- initial stop and DOL1;
- whether base partial was reached;
- whether BE became armed;
- whether BE amendment was accepted;
- whether DOL1 was touched and accepted;
- whether runner_active became true;
- PS confirmation count;
- whether a PS2 candidate existed;
- every stop price change;
- exact close reason and realized PnL.

No conclusion about a missed trailing action is valid until these states are
reconstructed.

## 9. V2 expansion

V2 should add explicit state snapshots at meaningful state transitions, not
blindly mutate traders:

- candidate snapshot;
- CIBO posture/sizing snapshot;
- Risk allocation snapshot;
- broker request/fill snapshot;
- MFE/MAE path;
- stop/target history;
- management eligibility snapshot;
- mutation attempt/accept/reject;
- close reason;
- realized net PnL and R;
- counterfactual observation fields for research only.

For traders with trailing contracts, the lab should calculate:

- first timestamp trailing became eligible;
- first timestamp a candidate stop improvement existed;
- first mutation attempt;
- broker acceptance timestamp;
- protected-R gained;
- giveback from MFE to realized exit;
- whether a tighter valid stop would have protected more capital without
  inventing future knowledge.

## 10. Acceptance criteria

V1 is accepted when:

- every input row is preserved or explicitly rejected as malformed;
- case grouping is deterministic;
- source payloads remain unmodified;
- a report never labels absence as failure without eligibility evidence;
- VT31 sizing path is represented accurately;
- all known DEMO trader lifecycle contracts are represented;
- unit tests cover chronology, case grouping and the no-false-failure rule.

V2 is accepted only after state-transition evidence allows precise
ELIGIBLE_BUT_NOT_EXECUTED diagnosis for every trader with dynamic position
management.
