# Turtle Soup Candidate R1 — Data Split Freeze

Status: FROZEN BEFORE ANY ECONOMIC REPLAY RESULT.

Research identity: `turtle-soup-candidate-r1`
Canonical trader code: `CODE_UNASSIGNED`

## Acquisition universe

Initial development acquisition is predeclared for these seven prop-relevant Forex instruments:

- EURUSD
- GBPUSD
- USDJPY
- AUDUSD
- USDCAD
- GBPJPY
- AUDJPY

The acquisition source is read-only cTrader historical market data. Acquisition is evidence collection only; it is not account trading and grants no execution authority.

## Time span

Request up to 1095 calendar days of native D1 history ending at collection time.

## Development / fresh-OOS boundary

`FRESH_OOS_EMBARGO_START = 2026-03-01T00:00:00Z`

Development characterization may consume only bars whose `opened_at` is strictly earlier than the embargo start.

Bars on or after the embargo start are **acquired but embargoed**. Merely acquiring and hashing them does not authorize reading their price path for candidate selection.

No code that computes setups, trades, P&L, metrics, rankings, policy selection or market selection during development may receive embargoed bars.

## Holdout release condition

The embargo may be released exactly once only after:

1. development replay is complete;
2. one Classic policy/config and one Plus-One policy/config are either frozen or explicitly rejected;
3. market universe is frozen without holdout outcome knowledge;
4. source configuration is frozen;
5. execution model is frozen;
6. transaction-cost model is frozen;
7. candidate fingerprints are recorded in GitHub.

After release there is no parameter retuning, management-grid change, entry-offset change, market deletion/addition based on holdout results, or second use of the same OOS as an independent holdout.

## Data semantics

The initial campaign uses provider-native D1 bars rather than D1 fabricated from H4 aggregation.

For Forex this is a source-authorized market transfer. The historical futures-specific `night data ignored / day-session only` source rule is not silently projected onto 24-hour spot-FX bar construction. Any later futures campaign requires an explicit exchange day-session calendar and separate dataset fingerprint.

## Governance

This split was frozen before any Turtle Soup economic result was inspected.

No DEMO/LIVE/Production/real-capital authority is granted.
