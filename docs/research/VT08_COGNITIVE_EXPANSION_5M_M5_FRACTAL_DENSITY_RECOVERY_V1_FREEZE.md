# VT08 Cognitive Expansion 5M — M5 Fractal Density Recovery V1 Freeze

Status: **PRE-ECONOMIC SOURCE-AUTHORIZED PROFILE TEST**

This experiment is frozen before inspecting M5 economics.

## Source authority

The VT08 Forex Source Rulebook and R3.2 Source Freeze explicitly define:

- M15 as the standard H4 pairing;
- M5_FRACTAL as an independent alternative profile;
- M3_FRACTAL as an independent alternative profile;
- profiles must be run separately and must not retroactively confirm one another.

This experiment tests **M5_FRACTAL only**.

## Frozen invariants

Unchanged from the rejected M15 B01 line:

- markets: EURJPY, USDCHF, NZDUSD, CADJPY, USDCAD;
- anchors: 01/05/09 New York;
- source-day reconstruction;
- daily bias;
- completed-C2 H4 admission;
- C2 side must agree with bias;
- positional entry at the new H4 open;
- structural stop at Protected Swing;
- no stop offset;
- fixed 2R replay target;
- next-H4 containment;
- exactly-one candidate per market/New-York date containment;
- same-M15 exit semantics remain unchanged for the outer replay.

Only the LTF fractal observation changes:

`M15 standard -> M5_FRACTAL`

Inside the completed C2 H4, important-level interaction, opposing series, CISD
and Protected Swing are reconstructed from closed M5 bars.

## Purpose

Measure whether M15 granularity is suppressing:

- valid CISD/Protected Swing formation;
- exactly-one Protected Swing resolution;
- candidate density.

This is NOT an authorization to combine M15 and M5 signals.

## Evidence

Use the immutable 1095-day evidence from run `35934924907`, which already
contains full M5 and M15 history for all five markets.

This evidence is consumed development evidence. Any M5 candidate that survives
must later be frozen and validated on unseen temporal evidence.

## Reporting

For every market report:

- M15 baseline terminal trades/PF/total/DD;
- M5 mechanical candidates;
- M5 terminal trades;
- annualized and 2Y-equivalent density;
- M5 PF/total/DD;
- candidate delta versus M15;
- terminal-trade delta versus M15;
- first-failure counts after C2 admission;
- by-anchor density/economics.

## Authority

- research_only=true
- profiles_combined=false
- demo_eligible=false
- live_authorized=false
- production_authorized=false
- real_capital_authorized=false
