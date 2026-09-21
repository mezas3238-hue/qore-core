# QORE Trader Execution Profile Freeze 001

Status: FROZEN
Scope: resident FundedNext MT5 execution transport only.
Methodology impact: NONE.

## Non-negotiable separation

Strategy methodology, signal logic, cognitive logic, entry definition, stop placement,
target selection, CIBO authority and QORE Risk authority remain unchanged.

Execution freshness and execution deadline are transport/runtime concerns only.

## Frozen profiles

### M1 execution profile

- decision_deadline = 5.0 seconds
- order_send_deadline = 5.0 seconds
- tick_max_age = 2.0 seconds
- normal_feed_refresh = 1.0 second
- boundary_arm_lead = 10.0 seconds
- boundary_retry = 75 ms

### M5 execution profile

- decision_deadline = 10.0 seconds
- order_send_deadline = 10.0 seconds
- tick_max_age = 2.0 seconds
- normal_feed_refresh = 1.0 second
- boundary_arm_lead = 10.0 seconds
- boundary_retry = 75 ms

## Feed-latency diagnosis

QORE distinguishes three different clocks and never treats them as the same signal:

1. **Transport latency** — measured only when a *new* broker tick timestamp is first
   observed locally. This answers whether the broker/terminal/Core path delivered
   new market data late.
2. **Tick inter-arrival time** — the time since the market last produced a new quote.
   A quiet instrument can legitimately exceed two seconds without any transport
   fault. This must not be reported as broker/Core delivery latency.
3. **Execution quote age** — immediately before LIVE mutation, the last executable
   broker quote must still be <= 2.0 seconds old. This remains a hard fail-closed
   safety invariant even when transport health is otherwise good.

Activation/readiness diagnostics therefore must not require every instrument to have
a <=2 second quote at the exact same wall-clock instant. They must verify the
delivery latency of newly observed ticks/candles. The LIVE send boundary separately
enforces quote age <=2 seconds on the instrument that is actually about to execute.

## Pre-send invariants

Immediately before a LIVE order can reach MT5:

1. The trader-specific order-send deadline must not have expired.
2. The real broker tick timestamp must be no older than 2.0 seconds.
3. The broker session must remain open and trading enabled.
4. QORE Account-Wide Risk authorization must still be valid.
5. The previously certified signal contract must still be within its causal execution window.
6. Entry drift remains governed by the trader's certified containment; no universal timeframe drift is introduced.

A wider M5 decision window never authorizes execution from stale market data.

## Boundary publication rule

For M5-driven Turtle Soup adapters, a newly opened M5 that is not yet visible at
the exact boundary is a transient infrastructure state, not a strategy abstention.
The anchor must not be consumed for this reason. The resident runtime retries on its
normal loop while the 10-second M5 execution window remains open. If the window
expires, execution fails closed; it never waits for the next five-minute candle.

## Trader bindings

- VT31 NAS100: M1 execution profile.
- Turtle Soup XAUUSD R34: M5 execution profile.
- Turtle Soup EURUSD R38: M5 execution profile.
- Turtle Soup GBPUSD R43: M5 execution profile.
- Turtle Soup GBPJPY R38: M5 execution profile.
- Turtle Soup AUDJPY R42: M5 execution profile.
- VT08 Forex keeps its certified H4/M15 methodology and expiry contract, while the
  universal LIVE transport still enforces broker tick freshness <= 2 seconds at send.

Changing these execution contracts requires an explicit contract revision, tests and
evidence. It is not a performance-only tuning change.
