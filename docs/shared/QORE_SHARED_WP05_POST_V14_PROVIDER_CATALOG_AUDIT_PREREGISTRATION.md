# QORE Shared WP-05 — Post-V14 Provider Catalog Audit Preregistration

**Identity:** `QORE_SHARED_WP05_POST_V14_PROVIDER_CATALOG_AUDIT_001`  
**Status:** PREREGISTERED / SOURCE-ONLY / NO V15 HYPOTHESIS  
**Primary PR:** #635  
**Work package:** #643 — WP-05 Temporal Hierarchical Brain  
**R8 outcomes:** CLOSED  
**R6/R5:** CLOSED  
**Fresh WP-05 holdout:** CLOSED

## 1. Reason for this audit

V14 was falsified before any Target-V2 outcome was opened.

The exact dual-peer source law required one shared staleness threshold from
5s / 10s / 30s / 60s / 120s for which US500 and US30 both provided causal
BID+ASK coverage >=9500 bps at every frozen checkpoint.

At 120s US30 passed all checkpoints, but US500 remained below the frozen gate
at 3/5/10/15 minutes. No staleness rescue, peer removal or V14.1 is legal.

The next experiment therefore must not be a retuned V14. Before defining V15,
Shared must inventory genuinely unconsumed provider sensors.

## 2. Audit question

What exact symbols are enabled in the authorized cTrader DEMO provider
catalogue now?

This audit answers only provider availability. It does not claim historical
coverage, causal value, information gain or predictive value.

## 3. Frozen inputs

Only the authenticated read-only cTrader symbol-list response is allowed.

The audit records for every enabled provider symbol:

- exact provider symbol name;
- exact provider symbol id;
- syntax-only normalized name;
- deterministic catalogue SHA256.

No market history is requested by this audit.

## 4. Selection prohibition

The audit performs **no candidate selection**.

No symbol may be preferred because of:

- Target-V2 labels;
- terminal/recoverable outcomes;
- R8/R6/R5 performance;
- false-veto reduction;
- terminal preservation;
- PnL;
- fresh holdout evidence.

After the full catalogue is frozen, a later source-only step may nominate a
new sensor family from economic/market semantics and then test historical
replay availability on already-consumed R8 source windows.

## 5. Governance

The report must state:

- `candidate_selection_performed = false`;
- `historical_market_data_read = false`;
- `target_or_outcome_read = false`;
- `r6_r5_read = false`;
- `fresh_holdout_opened = false`;
- `scientific_v15_opened = false`.

Shared gains no methodology, sizing, Risk, order, execution or broker-mutation
authority.

## 6. Anti-loop law

This audit may not be used to:

- remove US500 from V14;
- extend V14 staleness beyond 120s;
- lower the 9500-bps source gate;
- change V14 checkpoints;
- change the V14 M3 representation;
- call an US30-only rerun V15;
- open V14 outcomes after source rejection.

V14 remains permanently falsified.

## 7. Next legal transition

Only after this catalogue is frozen may the architect define a source-only
historical availability probe for a genuinely new sensor family.

A scientific V15 identity, representation, thresholds and outcome protocol
must be preregistered **after** source availability is demonstrated and
**before** any V15 outcome is opened.
