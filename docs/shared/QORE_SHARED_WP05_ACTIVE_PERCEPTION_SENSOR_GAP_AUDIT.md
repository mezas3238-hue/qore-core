# QORE Shared WP-05 — Active Perception Sensor Gap Audit

**Program:** QORE Meta-Cognitive Scientific Intelligence  
**PR:** #635  
**Issue:** #643  
**Status:** PRE-V10-OUTCOME CAPABILITY AUDIT / NO V11 EXECUTION  
**Fresh holdout:** CLOSED

## Purpose

This audit separates three facts that must never be conflated:

1. Core has a semantic contract for a sensor.
2. Core can read that sensor from a provider now.
3. Core has causally retained historical evidence suitable for R8 discovery.

Only (3), with exact replay/provenance, permits historical scientific use.

## Current sensor audit

### 1. NAS100/SP500/US30 OHLC

**State:** historically replayable but already inside the exhausted WP-05 sensor universe.

Existing V3-V10 research already consumes the NAS100/SP500/US30 OHLC-derived
state space. More transformations of these same observations are not a
genuinely new sensor for a post-V10 Active Perception branch.

**V11 admission:** NOT_NEW_INFORMATION.

### 2. cTrader exact Bid/Ask quote ticks

Core already contains:

- `CTraderOpenApiMarketDataClient.read_quote(...)`;
- native `ProtoOASubscribeSpotsReq` / `ProtoOASpotEvent`;
- provider timestamp when supplied;
- exact formatted Bid/Ask strings;
- `QualifiedQuoteTickObservation`;
- exact spread semantics;
- `RetainedMarketEventObservation`;
- deterministic mixed market-event replay;
- `HistoricalMarketEventDataset` with SHA-256 evidence digest.

Additional bridge work now exists:

- `qualified_quote_evidence.py`: provider decimal payload -> exact qualified
  quote evidence, caller-supplied IDs only;
- `quote_tick_capture.py`: exact quote -> retained replay event with explicit
  lineage/session/ingress chronology, no hidden clock or UUID.

However the architecture document
`docs/architecture/QORE-MARKET-EVENT-REPLAY-002.md` explicitly states that
live cTrader Bid/Ask capture and historical tick completeness were not closed
by that slice.

Repository search also found no production capture writer that persists
`RetainedMarketEventObservation` quote events into a historical dataset.

**State:** LIVE_READ_CAPABILITY + REPLAY_ALGEBRA, but HISTORICAL_R8_EVIDENCE_NOT_YET_PROVEN.

**V11 admission today:** REJECT until an immutable retained capture dataset with
causal availability and sufficient R8 coverage exists.

### 3. Tick-arrival / quote-update intensity

This can only be derived from retained quote-event chronology. It must not be
reconstructed from M1 OHLC counts.

**State:** DEPENDS_ON_RETAINED_QUOTE_CAPTURE.

**V11 admission today:** REJECT.

### 4. Bid/Ask spread dynamics

Instantaneous spread is exactly defined by `QualifiedQuoteTickObservation`.
Spread acceleration, widening duration and replenishment require chronological
quote capture.

**State:** DEPENDS_ON_RETAINED_QUOTE_CAPTURE.

**V11 admission today:** REJECT for historical R8 until capture exists.

### 5. Top-of-book depth / imbalance

Core has market-topology semantics, but repository evidence does not establish
a concrete NAS100 historical depth provider/capture path.

No order book may be fabricated from candles or quote spread.

**State:** NO_CAUSAL_HISTORICAL_EVIDENCE_PROVEN.

**V11 admission today:** REJECT.

### 6. VIX / VXN / volatility-index state

Repository source search found no VIX/VXN market-data provider implementation
or retained historical replay path for Shared.

**State:** PROVIDER_AND_DATASET_GAP.

**V11 admission today:** REJECT.

### 7. Implied volatility / skew / volatility term structure

No current Shared historical provider/capture path was established by this
audit.

**State:** PROVIDER_AND_DATASET_GAP.

**V11 admission today:** REJECT.

### 8. DXY / provider-neutral dollar basket

No DXY source adapter or retained Shared historical dataset was found in the
current repository audit.

**State:** PROVIDER_AND_DATASET_GAP.

**V11 admission today:** REJECT.

### 9. U.S. rates / yield curve

Core contains generic `rate_term_structure.py` semantics for observed/computed
curves, tenors, rates, yields, spreads and provenance. Semantics alone are not
market observations.

Repository audit did not establish a concrete point-in-time historical U.S.
rates provider/dataset wired to Shared WP-05.

**State:** SEMANTICS_PRESENT / HISTORICAL_PROVIDER_EVIDENCE_NOT_PROVEN.

**V11 admission today:** REJECT.

### 10. Equity leadership / breadth

Repository audit did not establish a replayable historical breadth or
semiconductor/technology leadership sensor universe for this WP-05 experiment.

**State:** PROVIDER_AND_DATASET_GAP.

**V11 admission today:** REJECT.

### 11. Provider / observation-quality telemetry

Core already has source identity, timestamps, health, latency/freshness and
market-event arrival provenance contracts. These can diagnose Core Reality.

They may qualify evidence quality and detect system-vs-market anomalies, but
must not be used as a semantic shortcut for market structural failure.

**State:** CORE_REALITY_SENSOR / NOT_STANDALONE_MARKET_FAILURE_TARGET.

## Consequence if V10 activates Active Perception

V11 cannot legally begin by simply adding a feature column.

The first admissible work becomes **sensor evidence acquisition engineering**:

1. choose a preregistered sensor family from the post-V10 reservation;
2. prove provider identity and economic/listing scope;
3. implement read-only capture;
4. retain exact arrival chronology;
5. define missingness and revision policy;
6. generate immutable evidence digests;
7. prove deterministic point-in-time replay;
8. quantify R8 coverage without reading target outcomes;
9. only then admit the sensor to the R8 information-gain experiment.

## First concrete candidate

The shortest infrastructure path currently visible is cTrader exact Bid/Ask
quote capture because read capability, quote semantics and replay algebra
already exist.

That does **not** mean it has been selected scientifically. It means it has the
smallest known infrastructure gap.

No V11 sensor is admitted by this audit.
