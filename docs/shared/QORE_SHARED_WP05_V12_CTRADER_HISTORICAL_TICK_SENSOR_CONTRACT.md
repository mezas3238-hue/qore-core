# QORE Shared WP-05 — V12 cTrader Historical Tick Sensor Contract

**Program:** QORE Meta-Cognitive Scientific Intelligence  
**PR:** #635  
**Issue:** #643  
**Identity:** `QORE_SHARED_WP05_V12_CTRADER_HISTORICAL_TICK_SENSOR_CONTRACT_001`  
**Status:** RESERVED / INFRASTRUCTURE-ONLY / PRE-ACTIVATION  
**Fresh holdout:** CLOSED

## Purpose

This contract freezes a candidate source of genuinely new market observations
before any post-V11 sensor experiment is allowed.

It does not activate V12 and does not admit historical ticks scientifically.
It defines what must be true before cTrader Bid/Ask tick evidence may enter the
R8 Active Perception lab.

## Official provider semantics frozen

Provider documentation establishes:

- historical ticks are requested with `ProtoOAGetTickDataReq`;
- request identity includes trader account, symbol, quote `type`,
  `fromTimestamp` and `toTimestamp`;
- quote type is explicit Bid or Ask;
- one request window must not exceed 604800000 ms (7 days);
- responses use `ProtoOAGetTickDataRes.tickData`;
- `hasMore` indicates a truncated response requiring pagination;
- returned ticks are newest-first;
- the first tick timestamp is absolute Unix milliseconds;
- subsequent tick timestamps are positive millisecond differences from the
  preceding newer tick;
- tick price is an integer relative price scaled by 100000;
- historical request traffic is limited to 5 requests per second per
  connection.

Provider references:

- https://help.ctrader.com/open-api/symbol-data/
- https://help.ctrader.com/open-api/messages/
- https://help.ctrader.com/open-api/model-messages/
- https://help.ctrader.com/open-api/

## Immutable acquisition law

Historical acquisition must:

1. request Bid and Ask as separate provider quote identities;
2. preserve exact account and symbol identifiers;
3. use UTC-aware request boundaries;
4. never request more than seven days in one provider message;
5. paginate while `hasMore=true`;
6. reconstruct every timestamp deterministically from provider absolute+delta
   encoding;
7. retain the original relative integer price as well as the exact normalized
   decimal representation;
8. preserve which quote side produced every tick;
9. reject malformed/non-monotonic timestamp chains;
10. reject response/account mismatches;
11. keep provider retrieval metadata separate from market-event availability
    semantics;
12. never fabricate opposite-side quotes when Bid or Ask is absent.

## Historical-vs-runtime causality law

Historical provider retrieval time is NOT the historical market availability
time.

A provider response fetched today may only be used to reconstruct the market
event's provider timestamp. It must never be treated as evidence that QORE
observed the event historically at that time.

For scientific Active Perception, the admissible question is whether the
historical tick itself is a provider-retained market observation with an exact
market timestamp and a deterministic replay contract.

Any Core-only fields that did not exist historically, such as present-day
network latency or core-ingress delay, must remain UNKNOWN rather than
backfilled.

## Bid/Ask pairing law

Bid and Ask streams may have distinct update timestamps.

Do not force one-to-one pairing.

At an evaluation timestamp, a spread may be constructed only from the latest
causally available Bid and latest causally available Ask at-or-before that
timestamp, subject to a preregistered maximum staleness rule.

The staleness rule must be frozen on R8 before target inspection and cannot be
changed after R6/R5 are opened.

## Pagination law

Because responses are newest-first, an older-page request must move the
`toTimestamp` strictly earlier than the oldest decoded tick from the previous
page.

A paginator must prove strict progress. Repeated oldest timestamps, empty pages
with `hasMore=true`, or a page outside the requested time window fail closed.

## Rate-limit law

The acquisition scheduler must remain at or below the documented historical
limit of 5 requests/second/connection.

The default QORE research scheduler SHOULD operate below the ceiling and use
provider backoff on explicit rate-limit responses. Speed is never allowed to
trade away evidence integrity.

## Retention bridge

Admitted ticks must flow through the existing evidence stack:

```text
provider historical tick
    -> exact quote-side observation
    -> retained market-event observation
    -> canonical chronological order
    -> HistoricalMarketEventDataset
    -> SHA-256 evidence digest
    -> deterministic point-in-time replay
```

No direct feature extraction from unretained API responses is allowed in the
scientific lab.

## R8 admission gates

Before target outcomes are read, report:

- requested interval coverage;
- Bid coverage;
- Ask coverage;
- longest quote-side gap;
- timestamp monotonicity;
- duplicate/conflict counts;
- page count and pagination completeness;
- provider error/rate-limit count;
- exact retained observation count;
- evidence digest;
- deterministic replay fingerprint.

A sensor is not admitted merely because data was downloaded.

## Scientific isolation

If V12 activates after V11 falsification:

- sensor acquisition/coverage is completed before target-based selection;
- R8 alone may perform information-gain discovery;
- R6/R5 remain untouched until the sensor representation is frozen;
- no target-aware choice of quote-side staleness, spread features, sampling
  cadence or missing-data policy;
- unchanged WP-05 2000/9500 gate remains binding.

## Sovereignty

Historical tick acquisition is read-only observation infrastructure.

It creates no entry, exit, sizing, allocation, Risk, order or Execution
authority.


## Historical quote-side provenance boundary

Historical BID and ASK data are independent provider event streams. The
research boundary is:

`src/qore/infrastructure/historical_quote_side_evidence.py`

Each retained side observation must preserve, independently:

- canonical QORE instrument;
- exact provider/account identity;
- exact provider symbol id/name;
- quote side (BID or ASK);
- provider event timestamp;
- historical retrieval timestamp;
- exact provider relative integer price;
- exact normalized decimal price.

The historical replay timestamp is the provider event timestamp. This is a
research replay rule only and must never be represented as historical
`core_ingress_at` or as evidence that Core observed the event live at that
time.

A BID page may create BID-side observations only. An ASK page may create
ASK-side observations only. No boundary may synthesize the opposite quote side
or force one-to-one event pairing.

Any later spread representation must use the latest causal BID and latest causal
ASK available at-or-before the evaluation timestamp, subject to a separately
preregistered staleness law.
