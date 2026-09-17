# VT08 Index — CIBO Semantic V2

## Purpose

This layer is a research-only semantic correction over the already-materialized
CIBO ledgers for consumed VT08 Index evidence.

It does **not** modify the frozen economic identity
`VT08_INDEX_V7_TTRADES_SOURCE_CORRECTED_001`.

## Corrections

### 1. Departure timing

The V1 complete-ledger pass used the first favorable +0.5R touch after signal as a
descriptive departure proxy.

Semantic V2 replaces that as the canonical departure definition with the frozen V7
mechanic itself:

`first-causal-M15-continuation-closure`.

For every consumed trade, V2 reconstructs the frozen V7 signal directly through
`vt08_index_v7_ttrades_source_corrected._signal_for_h4` and verifies that:

- reconstructed signal timestamp equals the Journey Atlas signal timestamp;
- reconstructed side equals the frozen side;
- reconstructed model kind equals the frozen model kind;
- reconstructed POI family equals the frozen POI family.

The previous +0.5R timestamp remains present only as
`legacy_0_5r_proxy` with `is_departure_definition=false`.

### 2. Source structure

V2 materializes the exact source POI and its first H4-cycle touch, CISD level and
confirmation timestamp, protected-swing extreme and confirmation timestamp, frozen
stop, frozen target, and continuation timestamp.

Protected-swing confirmation is bound to the same frozen CISD confirmation bar
that establishes the protected swing in V7.

### 3. Cross-index ordering

For each New York date + H4 anchor cohort, V2 records ordering and lag for:

- source-POI arrival;
- CISD confirmation;
- causal continuation/departure.

This is descriptive lead/lag evidence only and cannot promote a cross-index gate.

### 4. Trader/market error taxonomy A-I

V2 exposes all requested classes A-I as a non-causal, multi-label diagnostic:

- A Direction error
- B Timing error
- C Stop-location error
- D Structure-selection error
- E Confirmation error
- F Target error
- G Regime error
- H Cross-index context error
- I Correct loss

Where the current evidence cannot distinguish causation, the class is explicitly
`unresolved` rather than fabricated. B and C can both be candidates for a
stopped trade that later reaches the original-entry 2R because that observable
signature alone cannot distinguish timing from stop-location causation.

## Governance

- diagnostic only;
- consumed evidence only;
- V7 unchanged;
- no automatic rule promotion;
- no fresh holdout opened;
- LIVE_AUTHORIZED = FALSE;
- REAL_CAPITAL_AUTHORIZED = FALSE;
- PRODUCTION_AUTHORIZED = FALSE.

Any specialist admission, stop, target, timing, regime, or cross-index policy
derived from these diagnostics requires a new frozen identity and genuinely unseen
validation.
