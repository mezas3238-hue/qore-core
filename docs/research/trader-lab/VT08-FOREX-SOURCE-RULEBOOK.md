# VT-08-FOREX Source Rulebook

Status: reconstruction contract; economics remain blocked pending final methodology
adjudication.

Primary methodology source remains the Human Owner-provided TTrades H4 Power of Three /
AMD lesson already frozen in the shared VT-08 source kernel. This rulebook separates Forex
operational authority from futures/index authority without inventing new trading rules.

## Family authority

Authorized markets:

`EURUSD, GBPUSD, USDJPY, AUDUSD, USDCAD, GBPJPY, AUDJPY`

Owner-authorized New York H4 evaluation anchors:

`01:00, 05:00, 09:00 America/New_York`

These are evaluation windows, not three daily trading permissions.

Daily ceiling:

`MAXIMUM_FILLED_TRADES_PER_MARKET_PER_NY_DATE = 1`

Provenance of the ceiling: `HUMAN_OWNER_EXECUTION_POLICY`.

## Shared source kernel

The rebuilt Forex Trader may consume only source-proven common primitives from the
conservative VT-08 source kernel, including H4 PO3/AMD, C2/C3 scenario primitives,
CISD/protected-swing primitives and causal evidence validation.

The following remain subject to final source adjudication and must not be selected from
P&L:

- shallow versus large/deep wick classification;
- exact contextual bias;
- exact POI selection where multiple source-consistent POIs exist;
- exact entry-family selection;
- stop-family alternatives;
- contextual target-family selection;
- policy when more than one fully valid window exists on the same market-day.

## Daily selection

The cardinality layer permits multiple diagnostic candidates and multiple qualified setups,
but it does not decide which one wins. `FIRST_FULLY_VALID_SETUP_CHRONOLOGICALLY` is not
encoded as a source rule. If adopted later, it must be a separately versioned Human Owner
execution policy.

## Economics gate

No rebuilt Forex economic campaign is final evidence until the rule matrix and unresolved
methodology are frozen, full Ruff/Mypy/Pytest is green and the backtest reports exact
eligible market-days with zero daily-cardinality violations.
