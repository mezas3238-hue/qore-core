# VT-08 R3.10 — preregistered fresh holdout 2022–2024

Status: **PREREGISTERED / OUTCOMES NOT YET ACCESSED**

Parent source contract: VT-08 R3.9 (`r3.9-source-contract-v1`)

Source-contract fingerprint:
`403d54304f241f4a11b1ef847aa2a8b12d5ba6ffa2d9be5bb5cd9c19586943e3`

Consumed baseline run: `34693803930`

Consumed failure-forensics run: `34696371933`

Forbidden independent-validation reuse: `run-34693803930`

## Purpose

Reserve a genuinely non-overlapping historical holdout before any 2022–2024
outcome is accessed. This campaign validates the frozen executable VT-08 B01
research subset under the final R3.9 source contract. It does not tune, select,
or mutate methodology from holdout outcomes.

## Frozen evaluation interval

- Evaluation start, inclusive: `2022-08-13T00:00:00Z`
- Evaluation end, exclusive: `2024-08-12T00:00:00Z`
- Duration: exactly 730 calendar days.
- Consumed-baseline boundary: `2024-08-13T00:00:00Z`.
- Required gap to consumed baseline: at least one full UTC day.

The evidence collector acquires from `2022-07-14T00:00:00Z` through
`2024-08-12T00:00:00Z`. The additional 30 calendar days are warm-up / coverage
margin only. Economic holdout metrics are restricted to signals whose
`signal_at` lies inside the frozen 730-day evaluation interval.

No bar or trade at or after `2024-08-12T00:00:00Z` belongs to the holdout
metrics. Therefore the evaluation interval cannot overlap the prior moving
760-day campaign that begins in August 2024.

## Frozen markets

Exactly seven Forex markets:

- `AUDJPY`
- `AUDUSD`
- `EURUSD`
- `GBPJPY`
- `GBPUSD`
- `USDCAD`
- `USDJPY`

No market may be removed, substituted, promoted, or blacklisted after outcomes
are observed.

## Frozen entry anchors

Exactly the source-authorized Forex entry anchors:

- 01:00 America/New_York
- 05:00 America/New_York
- 09:00 America/New_York

No anchor may be selected or removed after outcomes are observed.

## Frozen executable methodology

The campaign executes the R3.8 narrow completed-C2 B01 implementation only
because R3.9 established that its economic behavior remains aligned with the
frozen source contract. The campaign binds every result to the R3.9
source-contract fingerprint above.

The executable containments remain:

- exact historical fill at the new H4 open;
- Protected Swing structural stop with no broker offset;
- fixed 2R conservative replay target;
- close a still-open modeled trade at the next H4 boundary;
- exactly one valid Protected Swing or abstain;
- exactly one B01 candidate per market/New-York date or abstain;
- abstain when directional acceptance is not uniquely resolved.

### C3 governance

C3 is source-authorized, but the frozen R3.9 contract explicitly keeps it
outside the current R3.8 executable subset. The primary source distinguishes
shallow versus large/deep opposing runs qualitatively and supplies no numeric
classifier. This holdout therefore **does not invent a C3 gate** and does not
silently broaden the consumed executable methodology.

`c3_included = false`

`c3_reason = source-authorized-but-not-machine-deterministic-without-new-rule`

A later C3 implementation would be a new methodology version and may not reuse
this holdout as independent validation.

## Frozen outcome reporting

For the 730-day core interval report, at minimum:

- total modeled trades;
- winning, losing and flat trades;
- win rate;
- mean return;
- exit-reason counts (`stop`, `target`, `h4_containment_exit`);
- long/short segmentation;
- 01/05/09 anchor segmentation;
- per-market metrics;
- seven-market aggregate.

Raw acquisition-window replay is retained only for audit. The official fresh
holdout metrics are computed solely from the frozen core interval.

## Failure policy

If any of the seven markets cannot provide sufficient M5/M15/H4 historical
coverage for the preregistered acquisition window, the campaign must fail
explicitly. It may not silently move the dates, shorten the interval, replace a
market, or substitute another data source after outcomes are known.

## Authority

- Research only: YES.
- Independent-validation interval reserved before outcome access: YES.
- Methodology mutation after outcome access: PROHIBITED.
- DEMO_ELIGIBLE: NO automatic promotion.
- LIVE: NO.
- Real capital: NO.

SOURCE FIRST. FREEZE SECOND. FRESH HOLDOUT THIRD.
