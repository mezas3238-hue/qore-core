# VT08 Cognitive Expansion 5M — Latest Confirmed Protected Swing V1 Freeze

Status: **PRE-ECONOMIC SOURCE-ADJUDICATED DENSITY TEST**

This freeze is committed before economic results from the selector are observed.

## Primary-source adjudication

TTrades primary material establishes that:

1. A protected swing is confirmed after price reaches an important level and
   closes through the opposing candle series.
2. During continuation, subsequent reaches into important levels can create
   **new protected swings**.
3. TTrades explicitly describes these as stepping stones and says to repeat the
   process as new protected swings form.
4. Current point-of-interest logic should adjust to the **newest protected
   swing**.
5. Stop refinement may use closer protected swings following CISD.

Primary sources:
- TTrades, "Protected Swings in Trading: How to Identify and Use Them for
  Entries & Continuations", 2025-08-06.
- TTrades, "Stop Loss Mastery – Using Protected Swings for Precise
  Invalidations", 2025-08-07.
- TTrades, "How Change in the State of Delivery (CISD) Confirms Swing Points",
  2026-01-10.
- TTrades, "The Only Points of Interest That Actually Matter For Trading",
  2026.

This evidence falsifies the idea that multiple valid same-direction protected
swings automatically invalidate a setup.

## Frozen research selector

When the independent LTF profile contains more than one source-valid protected
swing before the H4 decision boundary:

1. consider only swings already confirmed by closed bars;
2. consider only the setup side;
3. choose the swing with the latest `confirmed_at`;
4. if confirmation timestamps tie, choose the one whose opposing candle series
   started latest;
5. if identity still ties, fail closed.

Selector ID:

`LATEST_CONFIRMED_PROTECTED_SWING_V1`

This is causal and as-of. It does not inspect terminal PnL, future bars, target
outcome, market ranking, anchor ranking, or fold identity.

## Independent profile contract

Run the selector independently on:

- M15_STANDARD;
- M5_FRACTAL;
- M3_FRACTAL.

Never union, vote or cross-confirm profiles after seeing outcomes.

All other rules remain frozen:
- daily bias;
- completed C2 H4 reversal;
- 01/05/09 NY anchors;
- new-H4-open entry;
- structural PS stop;
- zero offset;
- fixed 2R replay target;
- next-H4 containment;
- one selected candidate / market / NY date.

## Why this is a density experiment

Consumed 1095D diagnostics show:

- M15: 488 exactly-one candidates + 145 multiple-PS cases;
- M5: 415 exactly-one candidates + 442 multiple-PS cases;
- M3: 322 exactly-one candidates + 631 multiple-PS cases.

These counts do not claim the recovered cases have edge. The experiment asks
whether source-adjudicated current-PS selection recovers density while retaining
economics.

## Evidence

- M15/M5 immutable base: run 35934924907.
- M3 immutable independent-profile artifacts: run 35941643396.

All evidence is consumed development evidence.

## Authority

research_only=true
profiles_combined=false
demo_eligible=false
live_authorized=false
production_authorized=false
real_capital_authorized=false
