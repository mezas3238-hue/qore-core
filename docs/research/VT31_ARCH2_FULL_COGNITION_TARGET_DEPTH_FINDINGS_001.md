# VT31 NAS100 — Full-Cognition Target-Depth Findings 001

**Owner:** Sergio Meza  
**Status:** DOL2 + DOL3 CALIBRATION WITNESS PASS / ECONOMIC EXTENSION NOT YET PROMOTED  
**Branch:** `agent/vt31-edge-position-cert-b-001`  
**Workflow:** `37440683395` — SUCCESS  
**Head tested:** `52d7b443e15802250936e1a89db5a9b90fda3d91`

Aggregate artifact: `11401715062`

## Sovereign constraints

The diagnostic used the exact sovereign terminal population:

- R5: 54 trades
- R6: 37
- R8: 33
- recent consumed 2Y: 48

No admission, entry, initial stop, sizing, leverage, compounding, capital
weighting, absolute volume, or fresh holdout was changed.

DOL1 touch was **not** treated as acceptance.

Acceptance required a subsequent fully closed M1 beyond DOL1 in trade
direction.

Future DOL2/DOL3/DOL4 reaches were research labels only.

## Fold results

### R5

- DOL1 accepted: 10 / 54
- DOL2 after acceptance: **90%**
- DOL3: **60%**
- DOL4: 20%

### R6

- DOL1 accepted: 6 / 37
- DOL2: **100%**
- DOL3: **83.33%**
- DOL4: 83.33%

### R8

- DOL1 accepted: 8 / 33
- DOL2: **100%**
- DOL3: **75%**
- DOL4: 37.5%

### Recent consumed 2Y

- DOL1 accepted: 7 / 48
- DOL2: **71.43%**
- DOL3: **57.14%**
- DOL4: 28.57%

## Predeclared gates

All pass:

- non-zero DOL1 acceptance in every fold: **PASS**
- DOL2 reach >=70% in every fold: **PASS**
- DOL3 reach >=50% in every fold: **PASS**

Therefore:

- `dol2_calibration_witness = true`
- `dol3_calibration_witness = true`

## H3 cognition

Where the H3 checkpoint existed before DOL1 acceptance, full cognition was
attributed without future leakage.

The DOL2 mechanism remains strong across persistent/recovered journey states,
but subgroup samples are small. Those subgroup observations are diagnostic and
are not independently promoted.

## Acceptance latency

Observed touch -> accepted-close latency is not constant:

- R5 median: 1 M1; one slow 93-minute acceptance
- R6 median: 3.5 M1; observations up to 17 minutes
- R8 median: 2 M1; observations up to 8 minutes
- consumed median: 2 M1; all accepted cases within 4 minutes

This creates a physical execution requirement.

A hard DOL1 take-profit cannot later decide to extend after acceptance because
the position would already be closed.

Therefore the economic frontier must test a **soft DOL1 checkpoint** with a
predeclared finite acceptance window.

## Economic next phase

Predeclare and compare finite causal acceptance windows rather than choosing one
from outcomes:

- next closed M1;
- within 3 closed M1;
- within 5 closed M1.

If acceptance does not occur inside the window, exit at the observed close.

If accepted, test whole-position extension to DOL2 and DOL3, with and without
confirmed structural protection.

This keeps the strategy executable for any provider-permitted volume.

## Certification boundary

Target depth is now statistically calibrated on consumed evidence, but target
**economics** are still unvalidated.

The DOL2/DOL3 certification blockers remain active until the economic frontier
shows that a causal executable extension preserves edge and winner-R.

No policy promotion, candidate freeze, fresh holdout, merge, LIVE, real-capital
or production authority is granted.
