# VT31 NAS100 — Architect B Full Cognition Attribution 001

Status: **CONSUMED-EVIDENCE RESEARCH / EDGE-ONLY / NO POLICY PROMOTION**

Owner: Sergio Meza  
Repository: `mezas3238-hue/qore-core`  
Branch: `agent/vt31-edge-position-cert-b-001`

## Evidence binding

Workflow run: `37377854347`  
Run conclusion: **SUCCESS**

Artifacts:

- R5: `11372358480`
- R6: `11373155036`
- R8: `11372551270`
- consumed 2Y: `11372028552`

The four runs used the immutable evidence artifacts and hashes already bound by
the prior VT31 research workflows. No fresh holdout was opened.

## Governance

This study:

- changed no trade admission;
- changed no entry;
- changed no position policy;
- used equal normalized R per terminal trade;
- did not use `capital_weighted_net_r`;
- used no sizing, leverage, compounding or portfolio allocation;
- used no absolute trade volume;
- used no provider volume rule;
- used no terminal PnL or future journey label as a runtime input.

## Equal-risk baseline

| Fold | Trades | PF | Mean R | Total R | Max DD |
| --- | ---: | ---: | ---: | ---: | ---: |
| R5 | 328 | 1.0938 | +0.0700 | +22.9569R | 61.3009R |
| R6 | 299 | 1.5857 | +0.4195 | +125.4269R | 29.0551R |
| R8 | 257 | 0.9988 | -0.0010 | -0.2460R | 43.4301R |
| Consumed 2Y | 290 | 0.7413 | -0.2005 | -58.1357R | 74.5853R |

Conclusion: the current admitted population is **not certifiable on edge-only
economics**. The strong historical capital-weighted results cannot be used as
the new certification authority.

## Stable positive cognition signatures — 4/4 folds

### FVG + DEEP destination state

PF by fold:

- R5: 1.6276
- R6: 1.2842
- R8: 1.0300
- Consumed: 1.3955

Mean R is positive in all four folds.

### FVG + NEUTRAL destination state

PF by fold:

- R5: 1.4202
- R6: 1.4617
- R8: 1.0429
- Consumed: 1.0322

Mean R is positive in all four folds.

### Latest structure = fair-value-gap

PF by fold:

- R5: 1.0938
- R6: 1.2189
- R8: 1.0330
- Consumed: 1.0719

This is positive 4/4 but remains weaker than the family × destination
interactions.

## Stable negative cognition signatures — 4/4 folds

### Breaker + NEUTRAL

PF:

- R5: 0.3833
- R6: 0.5015
- R8: 0.9542
- Consumed: 0.4580

### Breaker + SHALLOW

PF:

- R5: 0.6213
- R6: 0.5477
- R8: 0.8083
- Consumed: 0.0000

This interaction is strongly negative 4/4.

### Last structure breaker + breaker entry

PF:

- R5: 0.4400
- R6: 0.6645
- R8: 0.5914
- Consumed: 0.0000

Strongly negative 4/4.

### Latest structure = breaker

PF:

- R5: 0.9598
- R6: 0.8492
- R8: 0.5109
- Consumed: 0.3184

Negative 4/4.

### Reasoning contradiction: current path not compressed

PF:

- R5: 0.7119
- R6: 0.8626
- R8: 0.7514
- Consumed: 0.9638

Negative 4/4.

## Non-promotable association

An exact recent-overlap value of
`0.9285714285714285714285714286` was negative 4/4. It is **not** eligible
for runtime promotion because an exact continuous-value bin is not a robust
mechanism.

## Architect B decision

These findings are not entry filters.

Architect B will use them only for **post-admission management research**:

1. preserve FVG DEEP/NEUTRAL journeys from premature protection;
2. test earlier causal structural protection for admitted Breaker
   NEUTRAL/SHALLOW states;
3. test protection for the stable `CURRENT_PATH_NOT_COMPRESSED` contradiction;
4. keep the initial methodological stop unchanged;
5. allow only stop improvement, never widening;
6. keep targets unchanged in the first protection frontier;
7. measure all variants on equal normalized R;
8. reject any DD improvement that destroys winner preservation.

No runtime policy is promoted by this record.
