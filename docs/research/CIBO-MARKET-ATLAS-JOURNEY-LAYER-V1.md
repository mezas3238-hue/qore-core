# QORE CORE — CIBO MARKET ATLAS JOURNEY LAYER V1

**Status:** RESEARCH FREEZE — NO TRADER AUTHORITY  
**Parent identity:** `CIBO_MARKET_ATLAS_20Y_V1`  
**Layer identity:** `CIBO_MARKET_JOURNEY_LAYER_V1`  
**Tracker:** Issue #602  
**Execution surface:** GitHub / GitHub Actions only. VPS is out of scope.

## 0. Mission

Extend CIBO Market Atlas from static market-state statistics into a complete historical reconstruction of the **price journey**.

The layer must answer, from retained market evidence:

> Before price expanded toward the opposite boundary, what exact structures did it visit, in what order, at what time, how long did it remain there, and what happened next?

It must also answer:

> Once price departed, where did it normally deliver, how far did it continue beyond the first objective, how did this vary by weekday/regime/time, and what were NAS100/SP500/US30 doing differently or together?

This layer is descriptive/diagnostic research. It cannot create a trader rule, change a target, filter a weekday, or authorize execution.

## 1. Canonical journey

Every eligible historical episode must be reconstructable as an ordered path:

`SOURCE BOUNDARY / LIQUIDITY EVENT`
`-> PRE-DEPARTURE PATH`
`-> STRUCTURE TOUCHES`
`-> LAST STRUCTURE BEFORE DEPARTURE`
`-> DEPARTURE / EXPANSION`
`-> FIRST OBJECTIVE`
`-> OPPOSITE BOUNDARY`
`-> POST-BOUNDARY EXTENSION / FAILURE / REVERSAL`

The laboratory must retain the exact underlying timestamps and prices for every step.

## 2. Pre-departure structure ledger

CIBO must detect and retain versioned observations for structures such as, where a deterministic/source-bound definition exists:

- liquidity raid / sweep;
- prior high / prior low;
- swing high / swing low;
- equal highs / equal lows;
- stacked liquidity;
- order block;
- breaker block;
- fair value gap / imbalance;
- displacement origin;
- protected swing;
- CISD-related structure;
- session high/low;
- daily/weekly boundary;
- compression / accumulation range;
- expansion/rejection zone;
- unresolved structure.

No structure type may be guessed. If the evidence or definition is ambiguous, retain `UNRESOLVED_STRUCTURE` plus the raw geometry instead of inventing a label.

For each structure touch retain at minimum:

- `episode_id`;
- `event_id`;
- symbol;
- side / directional context;
- structure type and detector version;
- source timeframe;
- structure creation timestamp;
- first-touch timestamp;
- last-touch timestamp;
- price bounds;
- distance from source boundary;
- distance from opposite boundary;
- penetration depth;
- reclaim/acceptance state;
- dwell time;
- number of revisits;
- whether this was the **last structure touched before departure**;
- exact parent M5 evidence references.

## 3. Departure clock

The layer must measure when price actually leaves the pre-departure structure/range rather than assuming the entry timestamp is the departure.

Retain:

- structure appearance time;
- first touch time;
- last touch time;
- departure timestamp;
- minutes from structure creation to first touch;
- minutes from first touch to departure;
- minutes from last touch to departure;
- minutes from source liquidity event to departure;
- New York local hour/minute, DST-aware;
- session as metadata only;
- weekday, week, month, quarter, year.

This supports questions such as:

> At what time did the final pre-expansion structure usually appear?

> How many minutes later did the expansion begin?

Time is diagnostic metadata and does not become an operating filter automatically.

## 4. Entry/trader synchronization

When an episode is linked to a historical Turtle Soup trade, retain separately:

- trader entry timestamp;
- trader stop timestamp if any;
- trader target/exit timestamp;
- whether departure had already occurred at entry;
- whether the trader was stopped **before** the later market departure;
- minutes from stop to later departure;
- whether entry was recovered after stop;
- whether original target was later reached;
- where the market was structurally at entry vs at true departure.

These fields are diagnostic only and must not be used to rewrite consumed R5 outcomes.

## 5. Cross-index journey — NAS100 / SP500 / US30

Canonical provider mapping for the current cTrader DEMO evidence identity:

- `NAS100 -> USTEC`
- `SP500 -> US500`
- `US30 -> US30`

The atlas must align the three indices on M5 timestamps and retain, for every index episode:

- contemporaneous state of all three indices;
- whether each had already swept/reclaimed/accepted comparable liquidity;
- structure type each index was touching;
- departure timestamp per index;
- lead/lag in minutes;
- agreement vs divergence;
- normalized displacement;
- normalized volatility;
- whether one index reached the opposite boundary while another did not;
- whether correlation/co-movement broke down.

Lead/lag remains association until independently replicated. No index may be declared causal merely because it moved first.

## 6. Full target / destination study

The laboratory must not assume the first valid DOL is the dominant destination.

For every departure retain all valid contemporaneous objective candidates that were knowable at departure, including their distance and structural type. Then, as outcome-only data, retain:

- first objective touched;
- time to first objective;
- opposite-boundary reach;
- time to opposite boundary;
- maximum extension beyond first objective;
- maximum extension beyond opposite boundary;
- later objective touches in exact order;
- reversal point after maximum favorable delivery;
- path drawdown during delivery;
- final 24h/48h/5-day path state.

Required questions include:

> Was the historical trader target too short relative to the dominant delivery distribution?

> Was it too far for the current regime/day?

> Which objective type most often became the first destination, and which type most often preceded continued delivery?

Those are statistical questions only. No target rule is promoted without E2->E3 replication and a new trader identity.

## 7. Day-of-week and daily journey characterization

For every market/day retain at minimum:

- weekday;
- total range;
- realized volatility;
- directional displacement;
- path efficiency;
- overlap/chop fraction;
- compression duration;
- expansion duration;
- trend/range/stagnation/reversal/shock state;
- time of first material expansion;
- time of daily high/low;
- liquidity raids before expansion;
- structure sequence before expansion;
- target reach distribution;
- continuation beyond first objective;
- close location within daily range.

CIBO must be able to answer, by market and rolling period:

- which weekdays historically expanded more or less;
- which weekdays spent more time in range/stagnation;
- whether the apparent weekday behavior is stable across years/regimes;
- whether target-reach distributions differ materially by weekday/regime.

A weekday pattern is never an automatic trade/no-trade rule.

## 8. Accumulation / pre-expansion behavior

Before departure, CIBO must characterize whether price was:

- compressing;
- overlapping;
- accumulating inside a bounded range;
- repeatedly raiding both sides;
- progressively narrowing;
- displacing and retracing;
- accepting beyond a boundary;
- rejecting beyond a boundary;
- building equal/stacked liquidity;
- forming a versioned ICT structure.

Retain causal/time-local measurements only, including range width, overlap, swing count, sweep count, duration, realized volatility contraction/expansion, and structure chronology.

## 9. Required machine ledgers added by this amendment

The parent Atlas must add the following retained datasets:

1. `MARKET_JOURNEY_LEDGER` — one row per canonical journey/episode.
2. `STRUCTURE_TOUCH_LEDGER` — every structure visit in exact chronological order.
3. `PRE_DEPARTURE_SEQUENCE_LEDGER` — ordered causal sequence before departure.
4. `DEPARTURE_TIMING_LEDGER` — all structure/departure latency measurements.
5. `TARGET_DESTINATION_LEDGER` — all contemporaneous target candidates plus outcome path.
6. `CROSS_INDEX_JOURNEY_LEDGER` — synchronized NAS100/SP500/US30 state and lead/lag.
7. `DAILY_PATH_LEDGER` — complete daily movement/regime characterization.
8. `TRADER_MARKET_SYNC_LEDGER` — optional linkage between historical trader lifecycle and market departure.

Every summary must be regenerable from these ledgers. No conclusion may exist only in prose.

## 10. Causal / outcome split

All fields must be explicitly partitioned:

### `CAUSAL_FEATURE=true`
Only information available by the observation/departure timestamp.

### `OUTCOME_ONLY=true`
Anything learned after that timestamp, including:

- final target reached;
- later boundary reach;
- MFE/MAE after departure;
- later structure touches;
- post-stop recovery;
- post-target continuation;
- eventual daily high/low;
- later cross-index behavior.

Outcome data may diagnose and generate hypotheses, but may never leak into state classification or candidate selection.

## 11. Statistical outputs

For each queryable journey family, return:

- exact episode IDs;
- sample size;
- market(s);
- interval;
- detector/schema version;
- distribution of last pre-departure structure types;
- distribution of departure hours;
- latency quantiles;
- target/destination reach probabilities as descriptive frequencies;
- continuation-distance quantiles;
- weekday/regime breakdowns;
- cross-index agreement/divergence breakdowns;
- rolling-period stability;
- confidence intervals where valid;
- evidence tier;
- provenance/hashes.

CIBO must return the underlying episodes, not merely averages.

## 12. Evidence ladder / authority

`E0 OBSERVATION -> E1 ASSOCIATION -> E2 CAUSAL HYPOTHESIS -> E3 REPLICATED MECHANISM -> E4 CANDIDATE RULE`

Nothing in this layer bypasses that ladder.

Permanent governance:

`DEMO_ELIGIBLE=false`
`LIVE_AUTHORIZED=false`
`REAL_CAPITAL_AUTHORIZED=false`
`PRODUCTION_AUTHORIZED=false`

This amendment does not authorize R6 and does not mutate R5.
