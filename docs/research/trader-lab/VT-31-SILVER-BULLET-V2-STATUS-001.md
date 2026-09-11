# VT-31 Silver Bullet V2 — Reconstruction Status 001

Status: ACTIVE RESEARCH CANDIDATE — NO DEMO/LIVE/REAL-CAPITAL AUTHORITY

## Source

Human Owner-provided video corresponding to `youtube:o0v4KQxZbpU`.

## Frozen source-derived implementation

- exact new Trader version: `VT-31 v2`;
- V1 remains unchanged as historical implementation evidence;
- source-authorized candidate market: `NAS100`;
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
legacy V1 collector/backtest contract is not silently changed. The canonical
11-market matrix is retained, but the ten non-NAS100 markets are explicitly
reported as unsupported-method-market rather than forced to trade.

Historical execution evidence is conservative: fills occur only after the setup
decision and before the source window expires; stop wins same-bar SL/TP
ambiguity; evidence gaps/data-end before terminal resolution are censored rather
than fabricated.

## Remaining gates

The exact branch must pass full `ruff`, `mypy`, and `pytest --cov` before the
long-horizon broker-backed research job is activated. Economic results remain
research-only and cannot promote the candidate without later characterization,
OOS/stress/Monte Carlo, Story Forensics, fresh holdout, authority review and
Human Owner visual review.
