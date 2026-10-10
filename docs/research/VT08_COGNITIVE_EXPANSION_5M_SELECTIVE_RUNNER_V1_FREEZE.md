# VT08 Cognitive Expansion 5M — Selective Runner V1 Freeze

Status: **PRE-ECONOMIC RESEARCH FREEZE / CONSUMED DEVELOPMENT ONLY**

This freeze is written after Stage B structural-banking results were consumed and
before the Selective Runner V1 economic outcome is observed.

## Parent

- Program: `VT08_COGNITIVE_EXPANSION_5M_V1`
- Stage B: VT08-native structural banking
- Stage B evidence run: `35929841567`
- Stage B status: DD-compression mechanism observed; not promoted

The current 760-day evidence and its 70/30 temporal segments are now consumed
development evidence. No result from this stage may be called a fresh holdout.

## Hypothesis

VT31's certified stack shows that banking alone is not the full mechanism. A
small residual runner can preserve convexity when a structural destination is
not merely touched but **accepted**.

For VT08, the transferred concept must use VT08-native geometry.

## Frozen VT08-native path

1. Entry/initial stop/2R target remain the frozen VT08 setup.
2. Intermediate level = midpoint of the VT08 reference H4.
3. Structural destination = opposite reference-H4 extreme in trade direction.
4. The managed ladder is valid only when:
   `entry -> equilibrium -> destination` is ordered forward.
5. 50% banks at equilibrium.
6. When destination is touched on a strictly later M15:
   - if the touch M15 **closes beyond the destination in trade direction** and
     the original 2R target remains farther forward, bank 25% at destination
     and retain a 25% runner;
   - otherwise bank the remaining 50% at destination.
7. Runner becomes active only from the next M15.
8. Runner target = the original VT08 fixed 2R target.
9. Runner initial stop remains the original VT08 structural stop in this stage.
   No trailing/protection rule is added yet.
10. At the H4 lifecycle boundary, an unresolved runner exits at the H4 close.
11. Active stop precedes favorable events on the same M15.
12. No future journey label, terminal PnL, fold identity, or calendar-date edge
    feature is a runtime input.

## Why 25% runner

After the already frozen 50% equilibrium bank, the residual 50% is divided
equally between destination realization and continuation. This is a single
predeclared transfer arm, not a parameter scan. It is not promoted by this
freeze.

## Explicit exclusions

- no NAS100 09:00-10:00 reference;
- no VT31 DOL1/DOL2 definitions;
- no +0.25 NAS100 reference-width extension;
- no VT31 COMPRESSED selector;
- no VT31 PS2 rule;
- no VT31 allocation/shield multipliers;
- no market/anchor/side deletion.

## Decision after replay

The mechanism is retained for further research only if it improves the
PF/DD tradeoff without changing trade count and without relying on outcome
labels. Any candidate still requires an unseen temporal validation.

Authority remains:
- DEMO_ELIGIBLE=false
- LIVE_AUTHORIZED=false
- PRODUCTION_AUTHORIZED=false
- REAL_CAPITAL_AUTHORIZED=false
