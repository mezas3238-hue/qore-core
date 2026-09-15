# ICT Turtle Soup R2 Forex — Full Holdout Ledger Forensics Freeze

Status: FORENSICS-ONLY / CONSUMED EVIDENCE
Identity: `ICT_TURTLE_SOUP_R2_FOREX_FULL_LEDGER_FORENSICS_001`
Parent holdout: run `35030690033`, HEAD `3cb3d789eb73aa346affad7a80fe5214942ca992`, artifact `10420839755`
Parent structural forensics: run `35031070205`, HEAD `035bcc2322d09be4f61538bdc3125854644c4f52`, artifact `10420619118`

## Mission

Materialize a complete deterministic ledger of every holdout event produced by the frozen ICT Turtle Soup R2 Forex replay so that every executed winner, executed loser/flat, and non-executed opportunity is individually auditable.

This is not a new candidate, not a backtest rerun for selection, and not an optimization exercise. The parent R2 economic result remains immutable and rejected for this Forex slice.

## Required reconciliation

The forensic ledger MUST reconcile exactly to the authoritative parent holdout:

- swept-pool events: `27,840`
- swept pools: `38,047`
- executed trades: `5,162`
- winners: `1,486`
- losers: `3,676`
- flats: `0`
- non-executed events: `22,678`

Parent non-execution funnel:

- ambiguous multi-pool sweep: `6,933`
- event data gap: `334`
- ignored while position open: `3,286`
- insufficient projected R: `6,350`
- invalid geometry: `3`
- no causal entry: `42`
- no CISD: `3,940`
- no opposing series: `799`
- no opposing target: `32`
- no reclaim: `959`

Any mismatch is a forensic failure and MUST stop artifact publication.

## Ledger outputs

1. `event-ledger.json` — all 27,840 sweep events in chronological order.
2. `winners.json` — every executed trade with primary net R > 0.
3. `losers.json` — every executed trade with primary net R < 0.
4. `flats.json` — every executed trade with primary net R == 0.
5. `non-executed.json` — every abstained/ignored event with exact stage reason.
6. `full-ledger-report.json` — aggregate reconciliation and decompositions.

For executed trades retain the immutable parent fields: symbol, side, swept/target pool and family, sweep/CISD/entry/exit timestamps, entry/stop/target/exit prices, projected R, gross/primary/stress R, and exit reason.

For non-executed events retain as much causally available state as exists at the rejection stage, including symbol, sweep time, swept pool IDs/families, side where unambiguous, CISD threshold/reclaim/CISD time when reached, candidate entry/stop/target geometry when reached, projected R when calculable, and the terminal non-execution reason.

## Required diagnostics

Report counts and percentages by:

- execution status and outcome;
- non-execution reason;
- symbol;
- side where defined;
- swept liquidity family;
- target liquidity family where defined;
- New-York session bucket and entry/sweep hour;
- year and quarter;
- exit reason for executed trades.

No positive pocket may be converted into a filter.

## Governance

- consumed evidence only;
- no fresh OOS access;
- no change to pool definitions, CISD, entry, stop, target, R:R, lifecycle, friction, market universe or clock logic;
- no counterfactual P&L for non-executed events;
- no candidate selection or promotion;
- no hour/session/symbol/pool filtering;
- no Monte Carlo/Risk/CIBO/prop-firm authority.

`DEMO_ELIGIBLE=false`
`LIVE_AUTHORIZED=false`
`REAL_CAPITAL_AUTHORIZED=false`
`PRODUCTION_AUTHORIZED=false`
