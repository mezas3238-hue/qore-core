# VT08 Forex Cognitive V1 — Journey / Destination + Position Intelligence

Status: **IMPLEMENTED RESEARCH/SHADOW COGNITION / NOT LIVE-WIRED**

This checkpoint adds causal in-trade cognition without changing the certified
VT08 methodology or current VPS runtime.

## Journey / Destination Intelligence

The journey layer consumes only the current causal Situation Model and emits one
of:

- PRE_ENTRY
- ADVANCING
- STALLED
- EXHAUSTION_RISK
- DESTINATION_REACHED
- INVALIDATED
- UNKNOWN

Destination state is represented separately as:

- SUPPORTED
- APPROACHING
- REACHED
- CONTRADICTED
- UNKNOWN

No future terminal label is used. No PnL-derived threshold is used. No VT31,
Capitalizer, or Turtle Soup management threshold is copied.

## Position Intelligence

The frozen action vocabulary remains:

- HOLD
- PROTECT
- REDUCE
- EXIT

The layer is explicitly non-authoritative:

- execution_authorized = false
- quantity_change_authorized = false
- capital_authority = false

QORE Risk remains sovereign.

### Hard invariant — stop monotonicity

A stop may improve or hold. It may never widen.

For LONG:
current_stop < candidate_stop < current_price

For SHORT:
current_price < candidate_stop < current_stop

A Position Snapshot that already widened beyond its initial structural stop
fails closed.

### Default research policy

Structural trailing and causal reduction are **disabled by default** because
VT08-specific evidence has not yet calibrated them:

- allow_confirmed_structural_protection = false
- allow_reduce_on_causal_exhaustion = false

The mechanics can be exercised under an explicit research policy in replay, but
that does not grant LIVE behavior.

H4 lifecycle expiration and bound-destination completion remain explicit journey
terminal states. The cognitive recommendation may be EXIT, but this module
still cannot submit or authorize an order.

## Next validation requirement

The next economic/causal lab must compare the frozen VT08 baseline against
candidate Position Intelligence policies on consumed evidence before any
management behavior can be promoted. At minimum:

- baseline terminal path;
- HOLD-only cognitive shadow;
- confirmed-structure PROTECT candidate;
- exhaustion REDUCE candidate;
- combined candidate;
- density unchanged unless a separately justified lifecycle rule says otherwise;
- PF / DD / losing streak / terminal R;
- missed continuation after protection;
- premature exits;
- market × anchor stability;
- future-leakage and source-identity audits.

No policy may be selected from best historical PF alone.
