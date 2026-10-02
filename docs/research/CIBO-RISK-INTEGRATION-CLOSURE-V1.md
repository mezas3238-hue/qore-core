# CIBO Risk Integration Closure V1

Status: **MECHANICAL CLOSURE GATE / NO ECONOMIC UTILITY CLAIM**

This gate proves the authority order:

```text
Trader opportunity (volume-free)
  -> CIBO requested volume
  -> QORE Risk ALLOW / REDUCE / REJECT
  -> Execution later
```

QORE Risk does not choose opportunity geometry and does not become a sizing
optimizer. It independently bounds CIBO's request.

## Frozen closure scenarios

Using XAUUSD provider minimum volume `0.01`, volume step `0.01`,
`800 USD/lot` structural stop-risk and approximately `60 USD` QORE
authorizable headroom:

1. **Minimal seed fits** — CIBO requests `0.01` / `8 USD`; Risk returns
   `ALLOW`.
2. **Larger CIBO request** — CIBO requests `0.10` / `80 USD`; Risk floors
   safely to `0.07` / `56 USD` and returns `REDUCE`, not reject-all.
3. **Minimum genuinely cannot fit** — at `7 USD` hard headroom, even
   `0.01` implies `8 USD`; Risk returns `REJECT`.

In all cases `strategy_requested_risk_usd=None`: Trader does not own sizing.

## Scope

This closes the mechanical Risk/CIBO boundary required by
`RISK_INTEGRATION`. It does not prove profitability, authorize LIVE trading,
override provider restrictions, or weaken hard survivability rules.
