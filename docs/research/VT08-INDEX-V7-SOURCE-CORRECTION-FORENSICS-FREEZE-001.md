# VT-08 INDEX V7 — SOURCE CORRECTION FORENSICS FREEZE 001

Date: 2026-09-16

## Governance

This document is written after the V6 fresh holdout `[2020-09-15, 2022-09-15)` was opened and consumed. That interval is permanently consumed and MUST NOT be described as fresh again.

V7 corrections below are accepted only because they repair source-faithfulness defects independently supported by TTrades methodology. The consumed V6 outcome may be used for forensics and descriptive counterfactuals, but MUST NOT be used as fresh validation.

`LIVE_AUTHORIZED = FALSE`
`REAL_CAPITAL_AUTHORIZED = FALSE`
`PRODUCTION_AUTHORIZED = FALSE`

## V6 one-shot decision

Candidate: `VT08_INDEX_V6_TTRADES_SOURCE_FAITHFUL_001`
Freeze SHA: `2bcc7054d32745f39f670460b2a0561722eca293`
Rule fingerprint: `775746fdc6de11ca4cb7fdc6a664acbe0541c4f6befe8cbe4ca79336fccbc221`
Fresh run: `35054539866`
Decision artifact: `10430512799`

Primary stress `-0.05R/trade`:

- sample: 477
- total: +36.7997175141R
- mean: +0.0771482547R/trade
- PF: 1.1178532721
- max DD: 21.45R
- wins/losses: 179/298
- max losing streak: 10

Failed frozen gates:

- PF >= 1.15
- max DD <= 15R
- both chronological halves positive

The holdout is consumed regardless of the correction outcome.

## Forensic finding F1 — 18:00 was incorrectly executable

TTrades Important Time Levels explicitly distinguishes:

- 18:00 New York = daily candle open
- 02:00 / 06:00 / 10:00 / 14:00 New York = intraday four-hour candle opens

The H4 timing table may include 18:00 as part of the repeating chart alignment, but that does not make the daily open an ordinary VT-08 execution anchor. Owner also confirmed the operating rationale: the 18:00 futures reopen carries unfavorable spread/liquidity conditions and is not used for trade execution.

V6 incorrectly placed 18 in one tuple used both to build H4 context and to permit execution.

Consumed-evidence forensic result at `-0.05R/trade`:

- anchor 18 sample 33
- total -16.65R
- mean -0.504545R/trade
- PF 0.412698
- standalone DD 19.20R
- max losing streak 17

### V7 correction F1

Keep the complete H4 source cycle for structural aggregation/context, but split it from executable anchors.

- `H4_SOURCE_CYCLE_NY = (18, 22, 2, 6, 10, 14)`
- `EXECUTABLE_H4_ANCHORS_NY = (22, 2, 6, 10, 14)`

18:00 remains available as daily-open/context evidence and MUST NOT create a V7 signal.

No result-based removal of any other anchor is permitted in this correction.

## Forensic finding F2 — SAME_C2 could enter before price reached the H4 body

V6 freezes the source maxim `let the wick form, trade the body`, but its implementation did not require a SAME_C2 continuation close to be on the body side of the active H4 open.

V6 logic accepted the first M15 continuation after CISD/protected-swing confirmation even when:

- LONG entry close remained at or below the active H4 open; or
- SHORT entry close remained at or above the active H4 open.

That is a mechanical mismatch with the source concept: the wick may be confirmed, but an entry still located on the wick side of the H4 open is not yet trading the H4 body in the intended direction.

TTrades source support:

- `Let The Wick Form, Trade The Body` (2026-08-29): confirm the wick with protected swing / IC-CISD, then participate in the body/expansion.
- `Intracandle CISD` (2026-06-13): after IC-CISD, confirm continuation and enter in higher-timeframe bias; late/used-up candles should not be forced.
- `Trading the 4-Hour Power of 3`: shallow C2 may reverse-to-expand inside the same candle; deep opposing run should wait for C3.

No new percentage wick threshold, ATR filter, body/wick ratio, optimized time cutoff, or geometry threshold is introduced.

### V7 correction F2

For `SAME_C2` only, after the existing POI -> CISD/protected swing -> M15 continuation chain:

- LONG: continuation close / entry must be strictly `> active_h4.open`
- SHORT: continuation close / entry must be strictly `< active_h4.open`

Otherwise V7 abstains for that H4.

Completed C2/C3 next-H4 expansion paths are unchanged.

## Consumed counterfactual — diagnostic only

Applying only F1 + F2 to the already-consumed 2020-2022 trade stream gives the following descriptive counterfactual at `-0.05R/trade`:

- sample: 336
- total: +82.8497175141R
- mean: +0.2465765402R/trade
- PF: 1.4144552298
- max DD: 12.00R
- both halves positive
- quartiles: 3/4 positive

At `-0.10R/trade`:

- total: +66.0497175141R
- mean: +0.1965765402R/trade
- PF: 1.3153479515
- max DD: 14.0R

This is NOT validation and MUST NOT be used to claim V7 passes a holdout.

## V7 identity

Candidate ID: `VT08_INDEX_V7_TTRADES_SOURCE_CORRECTED_001`

V7 inherits V6 unless explicitly changed above:

- NAS100 / SP500 / US30
- New York DST-aware
- source POI -> CISD/protected swing -> continuation execution
- stop at protected swing extreme
- 2R initial replay target retained for comparability with V6
- stop-first same-bar ambiguity
- no daily unique-only
- no V3 geometry
- no D1 peer-count gate
- SMT not mandatory
- no forced one-H4 lifecycle

## Next fresh holdout

The following intervals are already consumed and unavailable as fresh:

- 2024-08-13 through 2026-09-11/12
- 2023-09-15 through 2024-08-13
- 2022-09-15 through 2023-09-15
- 2020-09-15 through 2022-09-15

The next candidate fresh interval is preregistered as:

`[2018-09-15, 2020-09-15)`

Acquisition may begin earlier solely for causal context, but evaluation MUST start on 2018-09-15 and no bar at or after 2020-09-15 may be requested before the V7 freeze/hardening gates pass.

If the provider cannot supply sufficient deterministic evidence for this interval, the holdout MUST fail closed as unavailable; it may not silently substitute a consumed interval.

## Fresh gates

Before the new holdout opens, V7 must be fingerprinted and hardening must pass. Fresh gates remain preregistered:

- sample >= 30
- `-0.05R/trade` mean > 0
- `-0.05R/trade` PF >= 1.15
- `-0.05R/trade` max DD <= 15R
- both chronological halves positive
- at least 3/4 quartiles positive when quartile sample is supported
- `-0.10R/trade` mean > 0
- `-0.10R/trade` PF > 1
- no supported market (`n >= 8`) mean <= -0.10R/trade
- no supported side (`n >= 10`) mean <= -0.10R/trade

A failed fresh gate consumes the interval and rejects this candidate identity. Post-result tuning of V7 using that fresh interval is prohibited.
