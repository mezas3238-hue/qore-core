# ICT Turtle Soup R4 — consumed-holdout deep forensics freeze

Date: 2026-09-16

Parent result: `ICT-TURTLE-SOUP-R4-FRESH-HOLDOUT-RESULT.md`

Parent identity:
`ICT_TURTLE_SOUP_R4_D1_IDEAL_C2_H1_CISD__H4_IDEAL_C2_M15_CISD__POSITIONAL_DAILY_DOL`

Parent authoritative run: `35052152001`
Parent authoritative SHA: `8c076a714098704237a97fe992e2e01bf9c69bf0`
Parent aggregate artifact: `10429651883`

## Purpose

Use the now-consumed 2018-2020 holdout only for diagnosis. No result from this forensics may mutate R4 or be presented as fresh validation.

The forensic objective is to explain why the source-exact reconstruction reduced same-window frequency from 2,424 legacy-R3-like signals to 298 R4 trades but still returned gross PF 0.9006 and primary PF 0.8180.

## Frozen analyses

1. Winner / loser / time-exit / target / stop decomposition.
2. Pre-stop MFE and MAE for stopped trades.
3. Post-stop recovery to entry, +0.25R, +0.50R, +1.00R and original target using only bars after the stop-containing M5.
4. Target continuation after target touch through the remaining Daily C3.
5. CISD latency and persistence:
   - H4 C2 open -> M15 CISD;
   - CISD -> H4 C3 entry;
   - favorable excursion before invalidation.
6. Protected-swing geometry:
   - entry-to-PS risk distance;
   - C2 range normalized risk;
   - sweep depth / reclaim depth as diagnostics only.
7. DOL geometry:
   - projected R;
   - target distance;
   - target age;
   - relationship between farther DOL and realized outcome.
8. Daily-level context:
   - Daily C2 range / reclaim;
   - H1 CISD timing;
   - Daily C3 outcome.
9. Temporal stability by quarter / half-year.
10. Cross-symbol simultaneous-entry clusters and common USD-direction concentration.
11. Side/session/symbol results are diagnostics only and may not authorize filters.
12. Concentration of positive and negative tails.
13. Leave-one-symbol-out diagnostics without selecting a symbol.

## Prohibited conclusions

- no pair deletion;
- no long/short deletion;
- no session/hour filter;
- no projected-R threshold;
- no stop widening;
- no DOL distance threshold;
- no reclaim-depth threshold;
- no re-entry;
- no BE/trailing/partials;
- no mechanical change under the same R4 identity.

Any causal repair suggested by forensics requires a new identity and a different untouched evidence window.

`DEMO_ELIGIBLE=false`
`LIVE_AUTHORIZED=false`
`REAL_CAPITAL_AUTHORIZED=false`
`PRODUCTION_AUTHORIZED=false`
