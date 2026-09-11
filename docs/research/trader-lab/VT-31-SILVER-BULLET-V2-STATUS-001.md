# VT-31 Silver Bullet V2 — Reconstruction Status 001

Status: ACTIVE RESEARCH CANDIDATE — NO DEMO/LIVE/REAL-CAPITAL AUTHORITY

## Source

Human Owner-provided video corresponding to `youtube:o0v4KQxZbpU`.

## Frozen source-derived implementation

- exact new Trader version: `VT-31 v2`;
- V1 remains unchanged as historical implementation evidence;
- source-authorized candidate market: `NAS100` only;
- no other canonical market is executed, scored, or emitted as a comparison row;
- New York DST-aware AM entry window: 10:00-11:00;
- 09:00-10:00 New York range derived from exact closed M1 evidence;
- strict range-side raid;
- post-raid M1 structural confirmation;
- current frozen entry model: post-confirmation FVG consequent encroachment;
- stop at raid extreme;
- target at opposite side of the frozen 09:00-10:00 range;
- unfilled entry expires at 11:00;
- no M5 substitution for source-required M1 decisions.

## Research infrastructure

Dedicated additive NAS100 M1 long-horizon collector and V2 backtest exist so the
legacy V1 collector/backtest contract is not silently changed. This campaign is
NAS100-only; provider aliases resolve only to the canonical NAS100 identity and
cannot widen the research universe.

Directional reporting is connected to the established QORE Core characterization
semantics in `first_cohort_characterization.py`. Direction is counted at SETUP
time, before fill modeling, through `side_counts`; `by_side` then reports setup
count, filled count, unfilled count, fill rate, terminal sample, targets, stops,
censored outcomes, win rate, expectancy R, and population variance R. Direct
`long_setup_count`, `short_setup_count`, `long_trade_count`, and
`short_trade_count` counters are retained for operational readability.

LONG + SHORT setup counts must reconcile exactly to `setup_count`; LONG + SHORT
filled counts must reconcile exactly to `filled_count`. A valid directional setup
therefore does not disappear merely because its limit order remained unfilled.
Top-level `pending_gap_count` remains separate evidence-quality information and
is never reclassified as a filled trade.

Historical execution evidence is conservative: fills occur only after the setup
decision and before the source window expires; stop wins same-bar SL/TP
ambiguity; evidence gaps/data-end before terminal resolution are censored rather
than fabricated.

## First completed NAS100 long-horizon research observation

The broker-backed run on software SHA
`17ff79edf47de169e6606dfbeb07f46dcf9db6ed` completed SUCCESS over the retained
760-day NAS100 M1 campaign and produced:

- decision days: 165;
- setups: 123 = 59 LONG + 64 SHORT;
- filled trades: 100 = 45 LONG + 55 SHORT;
- unfilled setups: 23;
- pending pre-fill evidence gaps: 0;
- terminal sample: 96;
- targets: 18;
- stops: 78;
- filled trades censored by later evidence gap: 4;
- aggregate win rate: 0.1875;
- aggregate expectancy: -0.009687754050818831464354622656 R.

Directional observations from that run:

- LONG: 59 setups, 45 fills, 14 unfilled, 42 terminal, 9 targets, 33 stops,
  3 gap-censored, win rate 0.2142857142857142857142857143, expectancy
  -0.1176884118862004669740179288 R;
- SHORT: 64 setups, 55 fills, 9 unfilled, 54 terminal, 9 targets, 45 stops,
  1 gap-censored, win rate 0.1666666666666666666666666667, expectancy
  0.07431275759892244059871683759 R.

These figures are research evidence for this exact V2 implementation and dataset,
not promotion evidence by themselves.

## Remaining gates

Full Quality Gate and the broker-backed NAS100 research path must remain GREEN on
the exact retained head. Economic results remain research-only and cannot promote
the candidate without later characterization, OOS/stress/Monte Carlo, Story
Forensics, fresh holdout, authority review and Human Owner visual review.
