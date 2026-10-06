# VT31 NAS100 — Sovereign 6R Drawdown Certification Gate 001

**Owner / CEO:** Sergio Meza  
**Status:** CANONICAL CERTIFICATION REQUIREMENT  
**Scope:** VT31 NAS100 edge-only certification

## Sovereign rule

> VT31 may certify when its observed maximum drawdown is **6R or less**, provided all other certification gates are satisfied.

The observed drawdown gate for certification is therefore:

`MAX_DRAWDOWN_R <= 6R`

An observed drawdown above 6R fails the drawdown certification gate.

## Clarification

The historical 10R target is superseded for certification.

The 15R ceiling remains only a hard research / safety rejection boundary. It does **not** mean that a candidate with 7R, 10R, or 14R drawdown is certified.

## Edge-only sovereignty

This 6R requirement may not be achieved through:

- position sizing;
- leverage;
- compounding;
- portfolio allocation;
- capital weighting;
- dynamic risk scaling;
- CIBO capital rescue.

Drawdown must be produced by the trader's own market edge:

- better admission;
- better entry;
- better invalidation;
- better position management;
- better target intelligence;
- winner preservation.

## Runtime interpretation

The canonical certification engine must expose:

`drawdown_at_most_6r`

and bind its pass threshold to:

`GATES["max_drawdown_r_target"] = Decimal("6")`

No fresh holdout, candidate freeze, LIVE, real-capital or production authority follows from this rule alone.
