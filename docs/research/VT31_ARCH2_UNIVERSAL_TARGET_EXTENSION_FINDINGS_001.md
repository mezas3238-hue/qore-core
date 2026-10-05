# VT31 NAS100 — Architect B Universal Target Extension Findings 001

**Status:** GLOBAL DOL2 VARIANTS FALSIFIED / CAUSAL SHORT-SIDE CLUE FOUND / NO PROMOTION  
**Owner:** Sergio Meza  
**Branch:** `agent/vt31-edge-position-cert-b-001`  
**Run:** `37382788110` — SUCCESS  
**Head tested:** `537894ad1467b765addc10638de385bf69054dad`

Aggregate artifact: `11376211715`

Fold artifacts:

- R5: `11375147795`
- R6: `11375887166`
- R8: `11375727149`
- consumed 2Y: `11374888018`

## 1. Purpose

Test target intelligence that is completely independent of absolute trade
volume.

No partial exit is required. The entire position either keeps DOL1 or selects
DOL2 before fill.

DOL2 is:

`DOL1 + 0.25 frozen 09:00 reference width in trade direction`

The choice is made from causal pre-entry cognition only.

## 2. Governance

All variants preserve:

- identical admission;
- identical entry;
- identical initial stop;
- identical baseline 3R breakeven;
- identical 16:00 lifecycle;
- equal normalized R;
- no sizing;
- no leverage;
- no compounding;
- no capital weighting;
- no absolute lot/volume;
- no provider-volume rule;
- no partial exit;
- no future-extension runtime label;
- no terminal-PnL oracle;
- no fresh holdout.

This architecture is therefore compatible with any provider-accepted volume
without changing trader edge logic.

## 3. Variants

- `BASELINE_DOL1`
- `DEEP_DOL2`
- `FVG_DEEP_DOL2`
- `FVG_DEEP_SUPPORTIVE_DOL2`

No variant survived the predeclared 4/4 non-degradation gates.

## 4. DEEP_DOL2

### R5

- extended trades: 70
- PF: 1.0938 -> **1.1425**
- mean: +0.0700 -> **+0.1068R**
- total: +22.96 -> **+35.03R**
- DD: 61.30 -> **57.84R**
- winner-R preservation: **104.92%**

### R6

- extended trades: 53
- PF: 1.5857 -> **1.5886**
- mean: +0.4195 -> **+0.4251R**
- total: +125.43 -> **+126.69R**
- DD unchanged at 29.06R
- winner-R preservation: **100.70%**

### R8

- extended trades: 49
- PF: 0.9988 -> **1.0508**
- mean: -0.0010 -> **+0.0393R**
- total: -0.25 -> **+10.09R**
- DD: 43.43 -> **41.42R**
- winner-R preservation: **105.23%**

### Consumed 2Y

- extended trades: 54
- PF: 0.7413 -> **0.7356**
- mean: -0.2005 -> **-0.2050R**
- total: -58.14 -> **-59.44R**
- DD: 74.59 -> **75.89R**

Result: **REJECTED**. Improvement in 3/4 does not authorize a policy that
degrades consumed 2Y.

## 5. FVG_DEEP_DOL2

This is the most interesting volume-agnostic target hypothesis.

### R5

- PF 1.0938 -> **1.1143**
- mean +0.0700 -> **+0.0856R**
- DD 61.30 -> **59.78R**

### R6

- PF 1.5857 -> **1.5685**
- mean +0.4195 -> **+0.4106R**
- total +125.43 -> **+122.36R**
- DD unchanged.

### R8

- PF 0.9988 -> **1.0111**
- mean -0.0010 -> **+0.0085R**
- DD 43.43 -> **42.15R**

### Consumed 2Y

- PF 0.7413 -> **0.7522**
- mean -0.2005 -> **-0.1920R**
- total -58.14 -> **-55.69R**
- DD 74.59 -> **72.14R**

Result: **REJECTED AS GLOBAL POLICY** because R6 degrades.

## 6. FVG_DEEP_SUPPORTIVE_DOL2

This narrower cognition state improves R5/R6/R8, but degrades consumed:

- consumed PF 0.7413 -> 0.7282;
- mean -0.2005 -> -0.2107R;
- DD 74.59 -> 77.54R.

Result: **REJECTED**.

## 7. Root-cause side attribution

After the global variants were adjudicated, changed-trade forensics found a
strong directional asymmetry inside `FVG_DEEP_DOL2`.

### SHORT FVG + DEEP extension delta

- R5: **+2.4601R**
- R6: **+2.3321R**
- R8: **+0.5654R**
- consumed: **+4.5617R**

Positive in 4/4 burned folds.

### LONG FVG + DEEP extension delta

- R5: +2.6627R
- R6: **-2.5154R**
- R8: +1.8775R
- consumed: **-2.1191R**

The transfer failure is concentrated in LONG extension, not in the entire
FVG-DEEP mechanism.

## 8. Scientific status of the SHORT clue

`FVG + DEEP + SHORT -> DOL2` is **post-hoc mechanism discovery**.

It is not eligible for direct runtime promotion because the side interaction
was selected after reading these consumed outcomes.

Permitted use:

- document it;
- compare it with existing CIBO DOL1 extension anatomy;
- predeclare it for an independent future validation after the integrated
  entry candidate is frozen.

Forbidden use:

- retrofit it into current runtime;
- claim 4/4 validation from the same burned evidence;
- open a fresh holdout now;
- use sizing to amplify it.

## 9. Decision

No whole-position DOL2 variant is promoted.

The target-intelligence line remains scientifically useful because:

1. DOL2 can improve both PF and winner-R without partial exits;
2. the extension mechanism clearly transfers in several folds;
3. the failure is localized enough to support a future causal side/context
   hypothesis rather than a generic rejection of extension.

The active Architect-B survivor remains:

`LBB_PATH_SHALLOW_PS1`

The current admitted population remains non-certifiable. Entry/admission repair
remains Architect 1's primary blocker.

No merge, fresh holdout, candidate freeze, LIVE, real capital or production
authority is granted.
