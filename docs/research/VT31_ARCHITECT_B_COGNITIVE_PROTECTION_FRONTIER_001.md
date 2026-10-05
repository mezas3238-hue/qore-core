# VT31 NAS100 — Architect B Cognitive Protection Frontier 001

Status: **FALSIFICATION COMPLETE / NO POLICY PROMOTED**

Owner: Sergio Meza  
Branch: `agent/vt31-edge-position-cert-b-001`

## Run binding

Run: `37378415728`  
Conclusion: **SUCCESS**

Artifacts:

- R5: `11373101041`
- R6: `11372468347`
- R8: `11371974218`
- consumed 2Y: `11373140993`

All four folds use immutable consumed evidence and equal normalized R.

## Baseline

| Fold | PF | Mean R | DD |
| --- | ---: | ---: | ---: |
| R5 | 1.0938 | +0.0700 | 61.30R |
| R6 | 1.5857 | +0.4195 | 29.06R |
| R8 | 0.9988 | -0.0010 | 43.43R |
| Consumed | 0.7413 | -0.2005 | 74.59R |

## Main falsification

No first-generation structural-protection variant survives all four folds plus
winner-preservation gates.

### BREAKER_NONDEEP_PS1

- improves R6 and consumed;
- consumed PF: 0.7413 -> 0.7953;
- consumed DD: 74.59R -> 60.96R;
- consumed winner count preservation: 97.14%;
- consumed winner-R preservation: 97.20%;
- but R5/R8 DD deteriorates.

Result: **REJECTED AS GLOBAL POLICY**.

### LAST_BREAKER_BREAKER_PS1

- improves R5/R6/consumed drawdown;
- preserves winners extremely well;
- slightly worsens R8 economics.

Result: **NOT PROMOTED; REQUIRES CAUSAL REFINEMENT**.

### PATH_NOT_COMPRESSED_PS1

- improves R5/R6/R8;
- damages consumed economics materially.

Result: **REJECTED AS GLOBAL POLICY**.

### NEGATIVE_UNION_PS1 / PS2

Broad unions reduce some drawdown but destroy too much winner-R, especially in
consumed evidence.

Result: **REJECTED**.

## Delta-forensics finding

Trade-level rerun: `37378672144`.

A refined intersection emerged:

`LAST_STRUCTURE=breaker AND CURRENT_PATH_NOT_COMPRESSED`

PS1 delta is positive across all four folds on changed trades.

The still safer subset:

`LAST_STRUCTURE=breaker AND CURRENT_PATH_NOT_COMPRESSED AND DESTINATION=SHALLOW`

preserves essentially all historical winner-R while improving the baseline
economics in all four folds.

This remains a development research finding, not an independent validation and
not a promoted runtime policy.

## Next Architect B experiment

The next frontier tests whole-position journey protection only after a **closed
M1 earns +1R**. Protection becomes effective on the following M1.

This directly targets the observed `GIVEBACK_AFTER_1R` defect without:

- filtering entry;
- changing target;
- changing initial invalidation;
- sizing;
- leverage;
- partial exits;
- absolute-volume assumptions;
- outcome-aware logic.

No merge, LIVE, production or fresh holdout is authorized by this record.
