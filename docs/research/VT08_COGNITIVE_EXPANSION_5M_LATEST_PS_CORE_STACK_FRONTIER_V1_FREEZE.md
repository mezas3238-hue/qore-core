# VT08 Cognitive Expansion — Latest-PS Core Stack Frontier V1 Freeze

Status: **PRE-RESULT / CONSUMED DEVELOPMENT**

## Purpose

Test whether the already source-adjudicated high-density
`LATEST_CONFIRMED_PROTECTED_SWING_V1` admission can retain its recovered trade
density while VT08's previously frozen Core Stack improves realized economics.

This experiment is committed before its economic replay is executed.

## Frozen universe

Markets:
- EURJPY
- USDCHF
- NZDUSD
- CADJPY
- USDCAD

Independent LTF profiles:
- M15_STANDARD
- M5_FRACTAL
- M3_FRACTAL

Evidence:
- immutable 1095-day base evidence from run `35934924907`;
- exact-window M3 evidence from run `35941643396`.

The evidence is consumed development evidence. No freshness claim is permitted.

## Admission contract

For each profile independently:

1. preserve VT08 daily bias;
2. preserve completed-C2 reversal admission;
3. preserve 01/05/09 New York anchors;
4. reconstruct source-valid Protected Swings only inside that profile;
5. when multiple same-direction Protected Swings exist, select the latest
   causally confirmed identity with
   `LATEST_CONFIRMED_PROTECTED_SWING_V1`;
6. preserve the existing exactly-one-candidate-per-market-day containment;
7. preserve positional entry at the new H4 open;
8. preserve the selected structural Protected Swing as initial stop;
9. preserve the original fixed 2R target and H4 lifecycle.

Profiles remain independent. No union, vote or cross-profile confirmation is
allowed.

## Frozen management layer

Apply the existing `VT08_COGNITIVE_CORE_STACK_DEV_V1` unchanged:

- VT08 reference-H4 midpoint as EQ50 structural bank;
- VT08 opposite reference-H4 extreme as structural destination;
- 50% bank at EQ when the forward structural ladder exists;
- pre-existing VT08 CIBO aggressive stop ratchets;
- stop can improve or hold, never widen;
- original target and lifecycle remain in force;
- no runner;
- no capital weighting;
- no market/anchor/side filtering;
- no new threshold or parameter scan.

The management layer may change realized R only. It may not change trade
identity, entry, initial stop, target, market inclusion or profile admission.

## Reporting

For every market/profile:
- terminal trade count;
- raw equal-risk PF / total R / DD;
- Core Stack managed-R PF / total R / DD;
- delta PF, total R and DD;
- exact trade-cardinality reconciliation.

A later candidate may advance only as one globally frozen profile across all
five markets. Per-market profile cherry-picking from consumed outcomes is
prohibited.

## Authority

research_only=true
consumed_development=true
profiles_combined=false
market_filtering=false
capital_weighting=false
demo_eligible=false
live_authorized=false
production_authorized=false
real_capital_authorized=false
