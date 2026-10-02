# QORE SHARED WP-05 — V15 CROSS-ASSET FULL R8 SOURCE ACQUISITION PREREGISTRATION

Status: **PREREGISTERED · SOURCE-ONLY · NO V15 OUTCOME SCIENCE OPENED**

## Purpose

Acquire complete historical BID/ASK source evidence over the already frozen
2,948 causal R8 manifest windows for the two post-V14 sensors whose source-only
availability pilot proved full BID/ASK history:

- `US2000` — semantic role `EQUITY_BREADTH_PROXY` — provider symbol id `10012`
- `XAUUSD` — semantic role `DEFENSIVE_ASSET_PROXY` — provider symbol id `41`

`XTIUSD` is **not admitted to this acquisition** because the post-V14 source
availability pilot classified it as partial BID/ASK history.

## Frozen upstream source identity

- manifest identity: `QORE_SHARED_WP05_ACTIVE_PERCEPTION_V12_ACQUISITION_MANIFEST_001`
- manifest SHA256: `2f18b9f11d5893effa46ac85c712edd6646d1d90a9de521b235143e42155d191`
- windows: `2948`
- partition: `R8 source-only`

## Acquisition law

For each admitted sensor:

- exactly 16 deterministic shards;
- assignment: `manifest_index % 16`;
- every manifest index 0..2947 exactly once;
- BID and ASK retained independently;
- immutable raw provider pages;
- provider-event time preserved separately from retrieval time;
- cTrader historical read-only message firewall;
- provider symbol id must equal the frozen post-V14 catalogue identity;
- provider digits are observed from the authenticated provider identity and must
  be identical across all 16 shards; they are not guessed in advance.

## Scientific firewall

This work may read only source/provider evidence.

It MUST NOT read or use:

- Target-V2 labels;
- terminal outcomes;
- R6;
- R5;
- any fresh holdout;
- Trader PnL;
- future bars for source selection.

This acquisition does **not** constitute:

- V15 scientific sensor admission;
- a regime-transition result;
- a continuation result;
- an Opportunity Discovery result;
- certification.

A later V15 scientific hypothesis may exist only after source integrity,
observability and a source-only representation are frozen.

## Governance

Shared gains no:

- methodology authority;
- position-management authority;
- sizing authority;
- capital authority;
- Risk authority;
- order authority;
- Execution authority.

Protected certification holdout remains CLOSED.
