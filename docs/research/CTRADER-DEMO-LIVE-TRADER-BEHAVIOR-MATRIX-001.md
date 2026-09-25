# cTrader DEMO LIVE — Trader Behavioral Matrix V1

**Laboratory:** QORE_CTRADER_DEMO_LIVE_BEHAVIOR_LAB_V1  
**Source branch reviewed:** agent/ctrader-demo-free-cibo-lab-001  
**Laboratory branch:** agent/ctrader-demo-live-behavior-lab-001  
**Scope:** seven traders currently loaded by the independent cTrader DEMO FREE runtime.

This matrix records source truth. It does not redesign the strategies.

## Cross-cutting finding

The runtime declares:

- QORE Risk = CAPITAL_ALLOCATOR_ONLY;
- CIBO = SIZING_AND_POSITION_INTELLIGENCE_SOVEREIGN.

The actual call graph is more fragmented.

A `CiboRiskRequest` is the common execution envelope, but the object name does
not prove that CIBO calculated the requested volume.

Current source paths show four distinct sizing behaviors:

1. VT08 calls CIBO for an ALLOW/DENY authorization, then its dedicated DEMO
   sizing module converts a frozen symbol risk fraction into broker volume.
2. VT31 resolves its own certified VT31 risk context and converts that result
   into broker volume. The VT08 CIBO sizing path is not invoked.
3. Turtle Soup EURUSD/GBPUSD/GBPJPY/AUDJPY compute base risk times their own
   cognitive/fragility/structural risk scale, then convert it into broker volume.
4. R34 XAUUSD computes its own base risk times the R34 risk governor scale, then
   converts it into broker volume.

The LIVE lab must therefore preserve a separate `sizing_path` field and must
not equate `CiboRiskRequest` with CIBO-owned sizing.

---

## VT08_FOREX

### Entry / decision path

VT08 B01 candidate -> CIBO setup -> CIBO posture -> VT08 Forex CIBO decision ->
DEMO symbol economics -> VT08 DEMO sizing -> execution sink.

### Sizing source truth

The dedicated DEMO sizing module uses the frozen per-symbol risk basis points
from `R315_BASE_RISK_BPS`.

It calculates:

`monetary_risk = assigned_demo_capital * frozen_symbol_risk_fraction`

and then converts this risk to volume using live cTrader tick size, tick value
and broker volume constraints.

### CIBO LIVE-state limitation found

The current runtime asks CIBO for posture using:

- initial_balance = assigned DEMO capital;
- balance = assigned DEMO capital;
- equity = assigned DEMO capital;
- current_aggregate_risk = 0.

Therefore the posture request does not currently carry the actual changing
account equity, open risk or realized journey state at that call site.

This must be visible in the laboratory as input provenance.

### Position management

- broker SL/TP;
- H4 containment lifecycle exit;
- no generic continuous trailing contract was found in this DEMO path.

### Lab questions

- What posture did CIBO receive?
- What actual live account state existed at the same timestamp?
- Did those values differ?
- What risk fraction was used?
- What volume resulted?
- Was CIBO's authorization economically adaptive or only permissive?
- What closed the trade: SL, TP or H4 containment?

---

## R34_XAUUSD

### Entry / sizing

R34 signal includes a governor `risk_scale`.

Current risk construction:

`base_risk_usd = account_equity * 0.002`

`requested_risk = base_risk_usd * signal.risk_scale`

Then broker-native sizing converts risk to volume.

### Position management

Declared current DEMO lifecycle:

`STATIC_SL_TP_PLUS_24H_EXIT`

No certified generic trailing-stop path was found in the current R34 live
adapter.

### Lab interpretation

A missing trailing event on R34 is not a defect under the current contract.

The laboratory should instead measure:

- target/stop excursion;
- profit giveback before exit;
- whether static management is structurally leaving capital unprotected.

That evidence can later motivate research, but the lab must not silently invent
a trailing rule.

---

## R38_EURUSD

### Entry / sizing

Current risk construction:

`base_risk_usd = account_equity * 0.002`

`requested_risk = base_risk_usd * signal.risk_scale`

The signal's risk scale already contains the frozen cognitive / fragility /
structural policy.

### Certified management

- STATIC or PROTECT posture;
- DOL lock for non-static target rank > 1;
- confirmed M5 swing trail only for PROTECT;
- monotonic stop: improve or hold, never widen;
- structural rearm after a trailing-stop exit;
- 24-hour maximum lifecycle.

`certified_stop_for_open_trade` causally replays only closed M5 evidence up to
the current time and computes the stop allowed by the frozen lifecycle.

`manage_open_position` compares that expected stop with the broker stop. It
sends an SL/TP amendment only when the new stop is a valid improvement.

### Lab questions

- STATIC or PROTECT?
- Target rank and DOL ladder?
- First DOL conquered?
- First confirmed swing eligible?
- Expected stop vs broker stop at each state change?
- Order-check/send accepted or rejected?
- MFE before stop advance and final giveback?

---

## R43_GBPUSD

### Entry / sizing

Same economic pattern as R38 EURUSD:

`base_risk_usd = account_equity * 0.002`

`requested_risk = base_risk_usd * signal.risk_scale`

The final scale is produced by the R43 frozen cognitive/risk overlays.

### Certified management

- STATIC / PROTECT;
- DOL locking;
- confirmed M5 swing protection in PROTECT;
- monotonic stop;
- 24-hour maximum lifecycle.

### Lab questions

Same causal protection questions as EURUSD, plus preservation of the R43-specific
risk overlays used to create the initial requested size.

---

## R38_GBPJPY

### Entry / sizing

Current risk construction:

`base_risk_usd = account_equity * 0.002`

`requested_risk = base_risk_usd * signal.risk_scale`

The final signal scale incorporates the frozen GBPJPY cognitive/fragility
policy.

### Certified management

- DOL lock;
- PROTECT-only confirmed M5 swing trail;
- monotonic stop;
- 24-hour lifecycle;
- explicit broker order-check before every stop amendment.

### Lab questions

- Was a better certified stop actually available?
- If yes, was the broker amendment checked?
- If checked, was it sent?
- If sent, was it accepted?
- If no better stop existed, preserve HOLD as a valid management result.

---

## R42_AUDJPY

### Entry / sizing

Current risk construction:

`base_risk_usd = account_equity * 0.002`

`requested_risk = base_risk_usd * signal.risk_scale`

The scale contains the frozen AUDJPY two-layer fragility/cognitive policy.

### Certified management

- DOL lock;
- PROTECT-only confirmed M5 swing trail;
- monotonic stop;
- 24-hour lifecycle;
- explicit broker check/send path for SL/TP amendments.

### Lab questions

Same as GBPJPY, with both AUDJPY fragility layers preserved in the decision
evidence so sizing can be traced to its real source.

---

## VT31_NAS100

### Entry / sizing

VT31 does not call the VT08 CIBO sizing module.

Current path:

VT31 causal candidate -> `Vt31RiskContext` ->
`resolve_certified_risk(context)` -> `final_risk_r` ->
`build_risk_request` -> DEMO broker-native volume -> execution sink.

This is the source-level explanation for the Owner observation that CIBO did not
appear to use its sizing on the recent VT31 DEMO trade.

### Certified V4 management

VT31 is not using a generic always-on trailing stop.

Its management is a state machine.

#### Base partial / break-even route

For eligible CORE non-compressed trades:

- a 50% base partial can be banked at 1.25R;
- the remaining leg receives a next-M1 arm time;
- only after that arm may the stop advance to entry;
- successful advancement logs `VT31_NAS100_BASE_BE_ADVANCED`.

A separate 3R state can also arm BE in the relevant architecture.

#### DOL1 route

DOL1 touch can create acceptance logic.

Depending on state/volatility:

- a quarter leg may be banked;
- acceptance is evaluated on the required M1 close;
- non-acceptance may close the remainder;
- acceptance can activate the runner and its next target.

#### PS2 trailing route

PS2 trailing is available only after runner activation.

The algorithm:

- starts from the DOL1 touch;
- searches closed M1 structure;
- requires qualifying protected-swing improvements;
- requires two confirmations;
- advances the stop only if the candidate is strictly better and remains before
  the runner target.

Successful mutation logs `VT31_NAS100_PS2_STOP_ADVANCED`.

### First LIVE forensic questions

For the recent VT31 DEMO operation, reconstruct:

1. signal fingerprint and broker position;
2. tier and entry family;
3. `final_risk_r`;
4. requested and filled volume;
5. initial stop;
6. reference volatility state;
7. whether 1.25R base partial became eligible and was banked;
8. whether BE was armed;
9. whether BE stop mutation was accepted;
10. DOL1 touch state;
11. DOL1 acceptance/non-acceptance;
12. whether runner became active;
13. PS confirmation count over time;
14. whether a valid PS2 candidate ever existed;
15. every broker stop value;
16. final broker close reason;
17. realized PnL/R;
18. maximum favorable excursion and giveback.

Only after points 7-14 are reconstructed can the lab classify the absence of a
PS2 trailing event as a defect rather than a non-eligible state.

---

## Laboratory diagnostic vocabulary

### NOT_OBSERVED

The relevant event is absent from captured evidence.

This is not a defect conclusion.

### NOT_ELIGIBLE

Source-state reconstruction proves that the trader's frozen rule had not become
eligible.

This is valid trader behavior.

### ELIGIBLE_AND_EXECUTED

Eligibility occurred and the expected action was accepted.

### ELIGIBLE_BUT_NOT_ATTEMPTED

Eligibility occurred but no matching mutation attempt exists.

This is a trader/runtime orchestration defect candidate.

### ATTEMPTED_BUT_REJECTED

The trader attempted the valid action but order-check or broker execution
rejected it.

This is an execution-path defect candidate.

### STATE_DIVERGENCE

The strategy store, reconstructed causal state and broker position disagree.

This is a high-priority correctness defect.

---

## Measurement set for every completed trade

Every case should ultimately expose:

- trader / symbol / signal;
- methodology identity;
- decision timestamp;
- CIBO input and output, if used;
- sizing authority;
- requested risk;
- requested volume;
- filled volume and price;
- initial SL/TP;
- management contract;
- every management state transition;
- every eligible stop improvement;
- every broker amendment;
- MFE / MAE;
- protected profit through time;
- final close reason;
- gross/net PnL;
- realized R;
- maximum profit giveback;
- discrepancies between declared contract and realized LIVE behavior.

This is the evidence basis for improving capital protection without contaminating
the traders while they are being observed.
