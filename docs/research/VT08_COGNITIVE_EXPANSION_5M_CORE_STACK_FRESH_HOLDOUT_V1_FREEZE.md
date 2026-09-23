# VT08 Cognitive Expansion 5M — Core Stack Fresh Holdout V1 Freeze

Status: **PRE-ECONOMIC FRESH VALIDATION FREEZE**

This freeze is committed before collecting or inspecting the 1095-day evidence
used for the first fresh backward temporal validation of Core Stack DEV V1.

## Candidate under test

The candidate is immutable for this holdout:

1. Frozen VT08 signal admission.
2. Original VT08 entry.
3. Original structural initial stop.
4. Original fixed 2R target.
5. Original next-H4 lifecycle.
6. VT08 reference-H4 midpoint: bank 50% when reached.
7. VT08 opposite reference-H4 extreme: bank all remaining exposure when reached.
8. Pre-existing VT08 CIBO `aggressive` stop family while exposure remains:
   - +0.50R observed -> stop 0.00R from next M15;
   - +1.00R observed -> stop +0.50R from next M15;
   - +1.50R observed -> stop +1.00R from next M15.
9. Active stop is evaluated before favorable events on the same M15.
10. No runner.
11. No market/anchor/side filtering.
12. No parameter change based on this holdout.

## Consumed boundary

All bars at or after:

`2024-08-25T21:00:00Z`

are consumed development evidence and are excluded from the fresh result.

A fresh trade must satisfy both:

- signal_at < consumed boundary;
- exited_at < consumed boundary.

## Acquisition

Use the existing read-only cTrader DEMO long-horizon collector with:

- requested lookback: 1095 days;
- M15 chronological evidence;
- DEMO only;
- read_only=true;
- account_is_live=false.

This should expose approximately the year immediately before the consumed
760-day corpus without changing provider or execution semantics.

## Fresh screen gates

This is a first temporal falsification screen, not final certification.

Per market:

- fresh sample >= 20 terminal trades;
- Core Stack PF > 1.00;
- Core Stack total R > 0;
- Core Stack PF > equal-rule baseline PF on the exact same fresh trades;
- Core Stack max DD < baseline max DD on the exact same fresh trades.

A market that misses sample is INCONCLUSIVE.
A market with sufficient sample that misses any economic screen is
FALSIFIED_FOR_THIS_STACK_V1.
A market satisfying every screen is FRESH_SCREEN_PASS only and still requires
longer robustness/WFO/MC before any promotion.

No pooled result can rescue a market-specific failure.

## Authority

- research_only=true
- fresh_holdout=true
- demo_eligible=false
- live_authorized=false
- production_authorized=false
- real_capital_authorized=false
