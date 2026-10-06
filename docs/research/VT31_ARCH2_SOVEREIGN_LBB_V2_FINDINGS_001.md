# VT31 NAS100 — Sovereign LBB Structural Survivor V2 Findings 001

**Owner:** Sergio Meza  
**Status:** NO EFFECT ON SOVEREIGN POPULATION / NOT A SURVIVOR  
**Run:** `37400273303` — SUCCESS  
**Tested head:** `edb0328b793af6d436449404ca96b9a794e7fc7b`  
**Aggregate artifact:** `11385176702`

## Purpose

Revalidate the former `LBB_PATH_SHALLOW_PS1` mechanism on the exact current
VT31 cognition-admitted population, not on the old dense OCO population.

The V2 experiment correctly used `specialist.replay()` as admission
authority and asserted identical trade identities between baseline and
candidate.

## Result

Across all four consumed folds:

- R5: 54 trades, 0 eligible, 0 changed;
- R6: 37 trades, 0 eligible, 0 changed;
- R8: 33 trades, 0 eligible, 0 changed;
- recent consumed 2Y: 48 trades, 0 eligible, 0 changed.

Therefore every candidate metric is identical to baseline.

The first aggregate implementation labeled this
`PURE_EDGE_STRUCTURAL_SURVIVOR` because all non-degradation gates passed.
That label was **vacuous**: a mechanism that never triggers cannot prove edge.

Commit `7639f8d32baf28317d79fd3f745917094ae95708` hardens the aggregate so
a survivor requires at least one changed trade. Zero changed trades are now
adjudicated as:

`NO_EFFECT`

## Scientific conclusion

`LBB_PATH_SHALLOW_PS1` is not part of the current sovereign VT31 opportunity
population and provides no current certification value.

It is retained only as historical research provenance.

This finding also confirms that conclusions from the old 328/299/257 dense OCO
population cannot be carried into the current 54/37/33/48 cognition-admitted
candidate without exact population revalidation.

## Governance

- runtime R authority: false;
- runtime volume authority: false;
- sizing: false;
- leverage: false;
- compounding: false;
- capital weighting: false;
- fresh holdout: sealed;
- policy promoted: false;
- candidate certified: false;
- merge: not authorized;
- LIVE / real capital / production: not authorized.
