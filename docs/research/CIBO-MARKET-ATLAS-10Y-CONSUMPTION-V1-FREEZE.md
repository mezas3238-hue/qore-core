# QORE CORE — CIBO MARKET ATLAS 10Y CONSUMPTION V1

**Status:** RESEARCH FREEZE — NO TRADER AUTHORITY  
**Identity:** `CIBO_MARKET_ATLAS_10Y_CONSUMPTION_V1`  
**Parent:** `CIBO_MARKET_ATLAS_20Y_V1`  
**Tracker:** Issue #602  
**Execution surface:** GitHub / GitHub Actions only. VPS is out of scope.

## 0. Owner scope decision — 16-Sep-2026

The primary CIBO market-consumption corpus is frozen to ten calendar years of canonical M5 evidence. The availability layer may inspect older history to establish provider boundaries, but bulk analytical ingestion is limited to the ten-year corpus defined here.

This scope change preserves the existing parent identity and previously produced evidence. It does not retroactively rename or reinterpret earlier artifacts.

## 1. Canonical ten-year corpus

Target interval:

`2016-09-17T00:00:00Z -> 2026-09-17T00:00:00Z` (end exclusive)

This is the ten-calendar-year M5 research corpus anchored to the current frozen close used by the Atlas program.

For each canonical symbol:

`actual_start = max(TARGET_CORPUS_START, EARLIEST_CONTIGUOUS_VERIFIED_M5)`

`actual_end = min(TARGET_CORPUS_END_EXCLUSIVE, LATEST_VERIFIED_M5 + 5 minutes)`

Rules:
- Never invent unavailable history.
- If the provider exposes less than ten years for a symbol, consume only the verified shorter interval and report the shortfall explicitly.
- If older history exists, do not bulk-ingest it under this identity.
- M5 is the canonical raw evidence. M15/H1/H4/D1/W1/MN are derived later from the retained M5 ledger.
- Every consumed row keeps canonical symbol identity and exact provider symbol identity.
- Raw evidence and large derived ledgers live in immutable GitHub Actions artifacts, not git history.
- Data-quality ambiguity fails closed or remains explicitly unresolved; it is never guessed away.

## 2. Frozen universe and provider identity

Canonical -> provider symbol:

- `AUDJPY -> AUDJPY`
- `AUDUSD -> AUDUSD`
- `EURUSD -> EURUSD`
- `GBPJPY -> GBPJPY`
- `GBPUSD -> GBPUSD`
- `USDCAD -> USDCAD`
- `USDJPY -> USDJPY`
- `NAS100 -> USTEC`
- `SP500 -> US500`
- `US30 -> US30`
- `XAUUSD -> XAUUSD`
- `XAGUSD -> XAGUSD`

`SPXUSD` is not an accepted substitute for `SP500/US500` under this identity.

## 3. Consumption outputs

Every symbol artifact must retain yearly partitions for the target corpus and a symbol manifest. At minimum:

1. `RAW_M5_LEDGER` — one immutable row per provider M5 bar with provider-relative integer OHLC fields and exact timestamp.
2. `DATA_QUALITY_LEDGER` — duplicate, contradictory, non-aligned, out-of-window and unresolved-gap observations.
3. `PARTITION_MANIFEST` — symbol/year first bar, last bar, row count, duplicate count, contradiction count, unresolved gap count and SHA-256.
4. `SYMBOL_CONSUMPTION_MANIFEST` — requested interval, actual verified interval, provider identity, precision metadata, total retained bars, partition lineage and governance flags.
5. `TEN_YEAR_CONSUMPTION_INDEX` — cross-symbol aggregate generated only from retained manifests.

The raw row must preserve provider-relative integers (`low`, `deltaOpen`, `deltaHigh`, `deltaClose`) so price reconstruction is deterministic and lossless with respect to the provider payload.

## 4. Integrity rules

- Retrieval is chunked so provider response limits cannot silently truncate a year.
- Chunks overlap only when needed for boundary validation; duplicate timestamps are detected explicitly.
- Identical duplicate rows are counted and deduplicated in the canonical ledger.
- Same timestamp with different OHLC payload is `CONTRADICTORY_BAR` and prevents the partition from being called clean.
- Timestamps must lie on the five-minute grid and inside the frozen partition.
- A chronological gap is not automatically called missing market data. Until provider-session/holiday evidence proves that a slot should have been open, the gap is labeled `UNRESOLVED_CLOSURE_OR_MISSING_DATA` with exact bounds and duration.
- Weekend involvement is metadata, not proof that an entire gap is explained.
- Session-adjusted completeness may only be published after the expected-open calendar is verified for that provider symbol.

## 5. What CIBO may learn from this corpus

Once the raw corpus and data-quality manifests are valid, the Journey Layer may reconstruct and statistically study:

- full source-boundary -> opposite-boundary price journeys;
- liquidity raids/sweeps, reclaim/acceptance and causal CISD/Protected Swing events;
- FVG, order-block, breaker and other deterministic/versioned structures;
- the last structure touched before departure;
- structure creation/touch/departure timestamps and departure latency;
- accumulation/compression before expansion;
- weekday/hour/session behavior as descriptive evidence, never an automatic filter;
- target/DOL reach, extension, reversal and ordered destination path;
- whether a trader was stopped before the later market departure;
- NAS100/SP500/US30 synchronized, divergent and lead/lag journeys;
- volatility, state transitions and extreme events;
- complete forward paths, kept strictly outcome-only.

All summaries must remain reproducible from retained ledgers and include sample size, interval, symbols, provenance and evidence tier.

## 6. Research-consumption consequence

The entire ten-year corpus is **consumed research evidence** once CIBO uses it to discover or refine a future trader rule. It must not later be relabeled as fresh out-of-sample evidence for that rule.

Any future R6 candidate influenced by this Atlas must be validated on a separately sealed untouched holdout or on genuinely future forward evidence under a new identity.

## 7. Governance

`DEMO_ELIGIBLE=false`  
`LIVE_AUTHORIZED=false`  
`REAL_CAPITAL_AUTHORIZED=false`  
`PRODUCTION_AUTHORIZED=false`  
`CANONICAL_TRADER_CODE=CODE_UNASSIGNED`

This Atlas consumes and explains markets. It does not promote a trader by itself.
