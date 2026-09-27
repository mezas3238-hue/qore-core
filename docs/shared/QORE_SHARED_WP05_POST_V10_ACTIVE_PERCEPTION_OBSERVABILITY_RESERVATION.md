# QORE Shared WP-05 — Post-V10 Active Perception / Observability Reservation

**Program:** QORE Meta-Cognitive Scientific Intelligence  
**PR:** #635  
**Issue:** #643 — WP-05 Temporal Hierarchical Brain  
**Original reserved identity:** `QORE_SHARED_WP05_ACTIVE_PERCEPTION_OBSERVABILITY_V11_CANDIDATE_001`  
**Carried-forward identity after material V10 observability:** `QORE_SHARED_WP05_ACTIVE_PERCEPTION_OBSERVABILITY_V12_CANDIDATE_001`  
**Status:** RESERVED / PRE-V10-OUTCOME / NOT EXECUTABLE  
**Fresh holdout:** CLOSED

## 1. Purpose

This document is frozen before the authoritative V10 result so that a V10
failure cannot be followed by outcome-aware sensor mining.

WP-05 has repeatedly shown a high-terminal-preservation / low-false-suppression
frontier. V10 is the decisive test of whether causal observations arriving
during the first 15 minutes materially improve observability.

If they do not, the problem is treated as missing information rather than a
classifier-selection problem.

## 2. Pre-frozen material-observability criterion

Define for each consumed partition:

```text
incremental_observability_bps =
    V10 sequential false-declaration reduction
    - V10 source-only false-declaration reduction
```

Sequential evidence is considered **materially informative** only if BOTH R6
and R5 satisfy:

```text
incremental_observability_bps >= 500
AND
sequential terminal preservation >= 9500 bps
```

No averaging across R6/R5.

The 500-bps criterion is diagnostic; it does not replace or weaken the WP-05
exit gate of 2000/9500.

## 3. Deterministic transition after V10

If V10 passes the full 2000/9500 gate on R6 and R5:

- freeze V10;
- preregister one fresh holdout;
- this reservation remains inactive.

If V10 fails the full gate but satisfies the material-observability criterion:

- V10 remains falsified;
- one structurally new sequential-state hypothesis may be preregistered;
- no V10 threshold or feature retuning is allowed.

If V10 fails AND material observability is <500 bps on either R6 or R5:

- stop classifier iteration over the current sensor universe;
- activate Active Perception / observability engineering;
- no V10.1, threshold search, density tuning or source-feature mining.

## 4. Existing sensor universe that is declared exhausted for this question

If the Active Perception branch activates, these alone are considered
insufficient as a closed sensor universe:

- NAS100 M1 OHLC;
- SP500 M1 OHLC;
- US30 M1 OHLC;
- derived M1/M3/M5/M15/H1/H4/D1 hierarchy states;
- source-frontier geometry;
- pre-source causal trajectories;
- 0/3/5/10/15m post-source paths derived only from those three OHLC streams.

Active Perception must add genuinely new observations rather than another
transform of the same closed information set.

## 5. Frozen new-sensor families

The first Active Perception program may investigate only these preregistered
families before any expansion:

### A. Market microstructure

- bid/ask spread and spread acceleration;
- tick-arrival intensity;
- signed tick imbalance where causally observable;
- quote-update imbalance;
- top-of-book depth/imbalance where provider evidence supports it;
- short-horizon liquidity withdrawal/replenishment.

No fabricated order book may be inferred from OHLC.

### B. Volatility / optionality state

- VIX/VXN-like volatility-index state when retained with exact provenance;
- volatility term-structure slope;
- implied-vs-realized volatility divergence where data exists;
- skew/tail-demand state where replayable evidence exists.

### C. Rates / dollar / macro transmission

- DXY or provider-neutral dollar-basket observations;
- U.S. front-end and long-end rates/yields;
- curve slope/change;
- rate-volatility shocks;
- timestamped macro-event state when independently retained.

The existing `rate_term_structure` infrastructure may provide semantics but
does not itself count as observed evidence.

### D. Equity leadership / breadth

- technology/semiconductor leadership;
- index breadth;
- leader-laggard divergence;
- sector confirmation/contradiction;
- concentration-driven vs broad-market motion.

### E. Venue/provider/broker observation quality

- bid/ask availability;
- provider disagreement;
- stale-price risk;
- spread dislocation;
- quote gaps;
- observation latency.

These belong to Core Reality and may qualify market evidence quality, but may
not be used as a shortcut to fabricate market structural failure.

## 6. Active Perception law

Shared must ask:

```text
Which presently unavailable observation would most reduce uncertainty
between TERMINAL and NON-TERMINAL worlds?
```

Candidate sensors are ranked on R8 only by expected information gain under
strict timestamp/replay integrity.

A sensor is not accepted merely because it correlates with the historical
target. It must provide incremental discrimination beyond the frozen existing
sensor universe.

## 7. Sensor admission protocol

Before R6/R5 consumption, every admitted sensor must have:

- exact economic/listing identity;
- provider/source identity;
- timestamp semantics;
- freshness semantics;
- missingness semantics;
- retained evidence hash/fingerprint;
- deterministic historical replay;
- no future backfill visible at an earlier timestamp;
- no outcome/PnL/trader/setup shortcut;
- availability compatible with the intended runtime use.

If a sensor cannot be replayed causally, it is excluded.

## 8. R8-only discovery

Sensor-family discovery and active-perception ranking occur only on R8.

R6/R5 remain one-way falsification partitions.

Forbidden after R8 freeze:

- adding a sensor because R6/R5 failed;
- dropping a sensor because R6/R5 failed;
- changing timestamp alignment;
- changing missing-data rules;
- changing the WP-05 2000/9500 gate.

## 9. Exit evidence

The Active Perception branch is not successful because a new sensor has mutual
information.

It must eventually demonstrate the unchanged WP-05 consumed gate:

```text
false structural-failure reduction >= 2000 bps
AND
terminal preservation >= 9500 bps
```

independently on R6 and R5, followed by one sealed fresh holdout.

## 10. Sovereignty

This reservation creates observation and cognition authority only.

It gives Shared no authority over:

- Trader methodology;
- entries/exits;
- stops/targets;
- CIBO sizing or capital allocation;
- QORE Risk;
- broker mutation or Execution.



## Post-V10 disposition

Authoritative V10 run `36325040251` proved material sequential observability:

- R6 incremental observability: **+727 bps**, terminal preservation **9810 bps**;
- R5 incremental observability: **+721 bps**, terminal preservation **9858 bps**.

Therefore this Active Perception reservation does **not** activate directly
after V10. Per the pre-frozen transition law, one structurally new sequential
state hypothesis is permitted first.

That hypothesis is V11:

`QORE_SHARED_WP05_SEQUENTIAL_MECHANISM_CONFIRMATION_V11_001`.

The Active Perception reservation is carried forward without changing its
sensor families or admission laws and is renumbered operationally as the
post-V11 **V12 candidate**:

`QORE_SHARED_WP05_ACTIVE_PERCEPTION_OBSERVABILITY_V12_CANDIDATE_001`.

If V11 fails the unchanged 2000/9500 consumed gate, this V12 branch activates
and classifier iteration over the current NAS100/SP500/US30 OHLC sensor
universe stops.
