# QORE Shared WP-05 — Post-V14 Cross-Asset Sensor Availability Preregistration

**Identity:** `QORE_SHARED_WP05_POST_V14_CROSS_ASSET_SENSOR_AVAILABILITY_001`  
**Status:** PREREGISTERED / SOURCE-ONLY / PRE-V15  
**Primary PR:** #635  
**Work package:** #643  
**R8 outcomes:** CLOSED  
**R6/R5:** CLOSED  
**Fresh holdout:** CLOSED

## Purpose

V14 is permanently falsified because the frozen US500+US30 microstructure law
could not satisfy the source-observability gate.

The full post-V14 provider catalogue froze 177 enabled symbols with provider
catalogue SHA256:

`4c10aede99704b937caa772e1ae07257c8e12c3d0644c06ca751b6885b9a363f`

No performance or outcome information was used.

Before any V15 scientific hypothesis exists, this audit asks whether three
structurally different source families have replayable historical BID/ASK
evidence on the already-consumed R8 source windows.

## Frozen candidates

The candidates are selected only from market semantics and exact provider
identity, not from historical performance:

1. `US2000` / id `10012` — `EQUITY_BREADTH_PROXY`;
2. `XAUUSD` / id `41` — `DEFENSIVE_ASSET_PROXY`;
3. `XTIUSD` / id `10019` — `CYCLICAL_COMMODITY_PROXY`.

This is not a claim that any sensor is predictive.

## Frozen temporal pilot

Reuse exactly the V12 source-only R8 acquisition manifest:

- manifest SHA256:
  `2f18b9f11d5893effa46ac85c712edd6646d1d90a9de521b235143e42155d191`;
- pilot manifest indices:
  `[0, 736, 1473, 2210, 2947]`;
- source-only historical BID and ASK queries only.

## Admission classification

For each frozen candidate:

- `full_bid_ask_history`: every pilot window has BID > 0 and ASK > 0;
- `partial_bid_ask_history`: some but not all source evidence exists;
- `no_history`: all pilot windows have zero BID and ASK;
- `technical_error`: provider read failed and scientific interpretation is
  forbidden.

No candidate is selected by tick count, freshness, Target-V2 outcome or
performance in this audit.

## Governance

Required outputs remain:

- target/outcome read = false;
- R6/R5 read = false;
- fresh holdout opened = false;
- scientific V15 opened = false;
- no methodology/sizing/Risk/order/execution authority.

## Next legal step

If one or more genuinely new sensor families have source evidence, the next
step is a new scientific preregistration with a new identity and representation
defined before any Target-V2 outcome is opened.

This audit cannot rescue or amend V14.
