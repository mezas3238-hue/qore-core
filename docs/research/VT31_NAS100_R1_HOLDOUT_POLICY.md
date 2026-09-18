# VT31_NAS100 — Calibration / Final Holdout Governance

## Current owner-authorized research path

The previous one-year sealed interval `[2015-04-19, 2016-04-19)` is now
subsumed into a two-year calibration interval:

- market: NAS100
- calibration id: `VT31_NAS100_2Y_CALIBRATION_001`
- start: `2014-04-14T00:00:00Z`
- end-exclusive: `2016-04-19T00:00:00Z`
- calendar span: 736 days

The **first successful acquisition** opens that historical interval. From that
moment onward the full two-year interval is permanently classified:

`CONSUMED_FOR_TUNING`

It may be reused repeatedly to improve the intelligent specialist's drawdown,
profit factor, journey reasoning, position management and selection policy.

## Freshness rule

After the first successful acquisition:

- the interval must never again be called fresh;
- repeated tests are calibration / development tests;
- parameter or reasoning changes may be evaluated on it;
- success on this interval is not final independent certification.

The workflow must reuse the exact canonical evidence artifact instead of
re-downloading or silently changing the historical sample.

## Low-drawdown research objective

The calibration report tracks, at minimum:

- stressed sample size;
- stressed mean R;
- stressed profit factor;
- observed max drawdown;
- max losing streak;
- Monte Carlo positive-terminal probability;
- Monte Carlo p95 max drawdown;
- half-year and quarter stability.

The current research target is to drive drawdown materially lower while
preserving a strong profit factor. Passing the 2Y calibration objectives does
not itself authorize live or production trading.

## Final certification evidence

A future final certification must use **other genuinely unobserved evidence**
that was not used to create, select, tune or reject the final candidate.

That final interval is intentionally not selected from the 2Y calibration
results. Its identity and boundary must be frozen separately before opening.

## Authority

This research branch remains:

- `candidate_frozen = FALSE`
- `live_authorized = FALSE`
- `real_capital_authorized = FALSE`
- `production_authorized = FALSE`

No merge or production authorization is implied by 2Y calibration.
