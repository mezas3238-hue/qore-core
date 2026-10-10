# VT08 Cognitive Expansion 5M — Three-Year Opportunity Census V1 Freeze

Status: **DIAGNOSTIC IDENTITY CENSUS / NO PROFILE COMBINATION AUTHORITY**

## Purpose

Count where all source-generated opportunities exist across the common
~1095-day five-market corpus without double-counting the same market/anchor/side
event across M15, M5 and M3.

## Identity

A C2 opportunity identity is:

`market + signal_at + side`

This intentionally ignores the LTF profile and Protected-Swing price so the
same H4 event discovered by multiple source-authorized LTF profiles is counted
once in the union.

A profile variant additionally records:

- profile;
- Protected-Swing price;
- Protected-Swing confirmation timestamp;
- opposing-series opening timestamp.

Therefore the census reports both:
- distinct opportunities;
- profile-specific variants.

## Profiles

Independent source-authorized profiles:

- M15_STANDARD
- M5_FRACTAL
- M3_FRACTAL

All use `LATEST_CONFIRMED_PROTECTED_SWING_V1`, which is source-adjudicated and
does not use PnL.

This census does **not** authorize combining these profiles for trading.

## C2 stages

Report separately:

1. mechanical candidate identities before daily cardinality;
2. terminal identities after each profile's existing daily-cardinality and
   complete-exit containment.

Presence masks:

- M15_ONLY
- M5_ONLY
- M3_ONLY
- M15_M5
- M15_M3
- M5_M3
- M15_M5_M3

## C3

C3 remains shape-only.

A C3 identity is:

`market + signal_at + bias_side`

Report:
- total C3 shape identities;
- C3 shapes overlapping a C2 mechanical identity;
- C3-only shapes not present in the C2 mechanical union.

C3-only shapes are **not trades** until POI, CISD, Protected Swing, entry, stop
and target semantics are source-bound.

## Evidence

- base M5/M15/H4 1095D evidence: run 35934924907;
- exact-window M3 evidence: run 35941643396;
- same five markets;
- no new market/anchor/side filtering;
- no capital weighting;
- no PnL used to define identity.

## Authority

- diagnostics_only=true
- profiles_combined_for_execution=false
- c3_executable=false
- demo_eligible=false
- live_authorized=false
- production_authorized=false
- real_capital_authorized=false
