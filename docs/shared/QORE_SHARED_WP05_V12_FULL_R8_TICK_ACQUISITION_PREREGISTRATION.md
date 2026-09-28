# QORE Shared WP-05 V12 — Full R8 Historical Tick Acquisition Preregistration

**Program:** QORE Meta-Cognitive Scientific Intelligence  
**PR:** #635  
**Issue:** #643  
**Identity:** `QORE_SHARED_WP05_ACTIVE_PERCEPTION_V12_FULL_R8_ACQUISITION_001`  
**Status:** PREREGISTERED / ACQUISITION ONLY / OUTCOME-BLIND  
**Fresh holdout:** CLOSED

## 1. Authorization basis

The preregistered provider-history coverage pilot passed:

- run: `36452997906`;
- producer SHA: `f266893f2aa04533fbf584b89b215d49cc917a5b`;
- status: `full_bid_ask_history`;
- temporal pilot indices: `[0, 736, 1473, 2210, 2947]`;
- BID ticks retained: `50,200`;
- ASK ticks retained: `50,307`;
- immutable pilot dataset SHA256:
  `06a145f763145eac5121878d4aa81c8c11bae86ea5a865eed9a7d6f5621d23e6`.

The frozen pilot disposition explicitly authorizes full R8 acquisition when every
selected temporal window contains both BID and ASK history.

## 2. Frozen upstream manifest

Full acquisition is bound to exactly:

- manifest identity:
  `QORE_SHARED_WP05_ACTIVE_PERCEPTION_V12_ACQUISITION_MANIFEST_001`;
- manifest SHA256:
  `2f18b9f11d5893effa46ac85c712edd6646d1d90a9de521b235143e42155d191`;
- source population: `6,804`;
- merged acquisition windows: `2,948`;
- source range:
  `2016-04-20T14:00:00Z -> 2018-05-18T19:30:00Z`;
- sensor context: `t-60m -> t+15m`;
- requested provider symbol: `USTEC`.

The manifest was built source-only. No matured Target-V2 outcome was used to
select a source or window.

## 3. Frozen acquisition partitioning

The 2,948 manifest windows are partitioned into exactly **8 deterministic
contiguous shards**.

For shard `s` in `0..7`, with `N=2948`:

```text
start = floor(N * s / 8)
end   = floor(N * (s + 1) / 8)
selected manifest indices = [start, end)
```

Every manifest index belongs to exactly one shard. No market state, target,
outcome, tick density, volatility, session or provider response may influence
shard membership.

## 4. Acquisition protocol

Each shard independently:

1. authenticates only to cTrader DEMO;
2. resolves the single authorized DEMO account fail-closed;
3. resolves the exact enabled `USTEC` identity and symbol digits;
4. wraps the native client in `CTraderHistoricalReadOnlyMessageClient`;
5. permits only symbol-list, symbol-detail and historical-tick messages;
6. requests BID and ASK independently for every assigned manifest window;
7. splits any provider interval to <=7 days;
8. paginates backward while `hasMore=true`;
9. respects the frozen per-connection historical request interval;
10. reconstructs signed timestamp and signed price deltas;
11. preserves raw wire timestamp/price values alongside reconstructed values;
12. preserves provider event time separately from retrieval time;
13. writes each page to an immutable quote-side shard before continuing;
14. fails closed on account/symbol mismatch, malformed chronology, non-positive
    reconstructed price, no pagination progress or any provider/provenance error.

No provider order/subscription message is admitted.

## 5. Required shard evidence

Each shard must report:

- manifest SHA256;
- shard index/count;
- first/last assigned manifest index;
- assigned manifest window count;
- provider symbol id/name/digits;
- sanitized account fingerprint;
- BID tick count;
- ASK tick count;
- BID page count;
- ASK page count;
- first/last provider event timestamp per side;
- immutable page/shard count;
- shard dataset SHA256;
- zero target/outcome reads;
- zero R6/R5 reads;
- fresh holdout closed;
- zero methodology/sizing/Risk/order/Execution authority.

Each raw-data artifact must carry its own `SHA256SUMS` and producer Git SHA.

## 6. Completion gate

Full R8 acquisition is valid only if:

- all 8 deterministic shards complete;
- all 2,948 manifest indices are covered exactly once;
- no shard overlaps another;
- every assigned window is attempted for both BID and ASK;
- every shard passes provenance/integrity checks;
- all raw artifact checksums verify;
- a deterministic global dataset identity is produced from the frozen manifest
  plus the ordered 8 shard dataset identities;
- no target/outcome, R6/R5 or fresh holdout was opened.

A technical failure may be repaired and the same shard rerun. It does not
authorize changing manifest membership or scientific selection.

## 7. What this does NOT authorize

Even a complete R8 tick dataset does **not** authorize:

- target-aware feature selection;
- R6/R5 access;
- WP-05 fresh holdout access;
- a claim that V12 passed scientifically;
- staleness threshold selection after seeing R6/R5;
- spread/feature mining against consumed partitions;
- Trader methodology changes;
- CIBO, Risk or Execution authority.

## 8. Next lawful step after complete acquisition

Only after full R8 acquisition and integrity binding pass may V12 preregister
the **R8-only sensor preprocessing / missingness / staleness candidate family**
and begin information-gain discovery against Target V2 inside R8.

R6/R5 remain sealed until one exact V12 representation is frozen.
