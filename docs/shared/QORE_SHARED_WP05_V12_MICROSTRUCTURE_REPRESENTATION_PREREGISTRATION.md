# QORE Shared WP-05 V12 — Causal Microstructure Representation Preregistration

Identity:

`QORE_SHARED_WP05_ACTIVE_PERCEPTION_V12_MICROSTRUCTURE_REPRESENTATION_001`

## Purpose

Freeze the exact candidate representation family before any V12 target-aware
R8 discovery.

The representation is built only from independently retained historical BID
and ASK provider events available at-or-before each frozen R8 evaluation
anchor.

The numerical quote-staleness limit is not target-tuned. It is supplied only by
the separately preregistered source-only anchor-observability freeze.

## Frozen evaluation universe

- partition: R8 only;
- evaluation anchors: exact frozen 6,804 source-only timestamps;
- BID/ASK dataset:
  `ebbe30a887867bb917f0992b15e1600f9f06eccb07562b9625fcb9517fb381c8`;
- microstructure windows:
  `1000, 5000, 15000, 60000 ms`.

No evaluation timestamp may be added, removed or reordered using target/outcome
information.

## Availability semantics

At each evaluation anchor:

1. use latest BID at-or-before the anchor;
2. use latest ASK at-or-before the anchor;
3. require both ages <= frozen source-only staleness limit;
4. require non-negative causal spread;
5. otherwise pair-dependent features are unavailable.

No future interpolation, nearest-neighbor pairing or unbounded forward fill is
permitted.

Missingness is explicit and causal.

## Deterministic normalization

Let:

- `B` = latest causal BID relative integer price;
- `A` = latest causal ASK relative integer price;
- `M = floor((A+B)/2)`;
- `T` = frozen staleness limit in ms.

When pair state is available:

- `spread_bps = floor((A-B) * 10000 / M)`;
- `bid_age_ratio_bps = min(10000, floor(bid_age_ms * 10000 / T))`;
- `ask_age_ratio_bps = min(10000, floor(ask_age_ms * 10000 / T))`;
- `age_skew_ratio_bps = min(10000, floor(abs(bid_age_ms-ask_age_ms) * 10000 / T))`.

For each fixed window `W`:

- `bid_update_rate_x1000 = floor(bid_count * 1000000 / W)`;
- `ask_update_rate_x1000 = floor(ask_count * 1000000 / W)`;
- `total_update_rate_x1000 = bid_update_rate_x1000 + ask_update_rate_x1000`;
- `update_imbalance_bps = (bid_count-ask_count)/(bid_count+ask_count)` in signed bps,
  with exact zero when no updates exist;
- `bid_displacement_bps = trunc(bid_displacement * 10000 / M)`;
- `ask_displacement_bps = trunc(ask_displacement * 10000 / M)`;
- `bid_path_variation_bps = floor(bid_path_variation * 10000 / M)`;
- `ask_path_variation_bps = floor(ask_path_variation * 10000 / M)`;
- `path_variation_asymmetry_bps = (bid_path_variation-ask_path_variation) /
  (bid_path_variation+ask_path_variation)` in signed bps, zero when denominator is zero.

All arithmetic is deterministic integer arithmetic.

## Explicit missingness encoding

The representation carries these binary/source-quality fields:

- BID present;
- ASK present;
- BID fresh;
- ASK fresh;
- causal pair available;
- crossed causal quote.

Unavailable pair-dependent numerical fields are stored as `null` in the
scientific evidence artifact. Any later model matrix must preserve an explicit
missingness indicator; it may use deterministic zero-fill only after that
indicator is present.

No statistical imputation is permitted before the final representation is
frozen.

## Frozen candidate blocks

Only the following four candidates are permitted for the first V12
information-gain experiment:

### M0 — QUOTE_STATE

- source-quality / availability flags;
- BID/ASK age ratios;
- age-skew ratio;
- causal spread bps.

### M1 — QUOTE_STATE + UPDATE_INTENSITY

M0 plus, for all four frozen windows:

- BID update rate;
- ASK update rate;
- total update rate;
- update imbalance bps.

### M2 — QUOTE_STATE + PATH_RESPONSE

M0 plus, for all four frozen windows:

- BID displacement bps;
- ASK displacement bps;
- BID path variation bps;
- ASK path variation bps;
- path-variation asymmetry bps.

### M3 — FULL_CAUSAL_MICROSTRUCTURE

Exact union of M0 + M1 + M2.

No fifth ad-hoc representation may be introduced after R8 target results are
observed.

## Scientific interpretation

The blocks target distinct mechanisms:

- M0: quote-state quality / spread / side synchronization;
- M1: arrival-intensity asymmetry;
- M2: directional response and path turbulence;
- M3: joint causal state.

They are new information relative to the closed OHLC-only V11 universe because
they derive from provider-retained BID/ASK event chronology, not candle
re-expression.

## Information-gain experiment boundary

After all source-only freezes are complete, R8 target/outcomes may be opened
only for the preregistered comparison of M0-M3 against the frozen V11/OHLC
baseline.

The later experiment must use chronological validation and must select at most
one final V12 representation before R6/R5 are opened.

R6/R5 remain single-shot consumed falsification partitions.

No R6/R5 feature mining, threshold mining or candidate switching is permitted.

## Sovereignty

The representation produces scientific market evidence only. It has no Trader
methodology, CIBO sizing/capital, Risk, order or Execution authority.
