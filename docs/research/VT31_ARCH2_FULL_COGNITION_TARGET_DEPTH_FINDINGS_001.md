# VT31 NAS100 — Full-Cognition Target-Depth Findings 001

**Owner:** Sergio Meza  
**Status:** DOL2 + DOL3 CONSUMED CALIBRATION WITNESSES / ECONOMIC VALUE NOT YET PROVEN  
**Branch:** `agent/vt31-edge-position-cert-b-001`

## Evidence

Workflow:

- run `37440683395`
- head `52d7b443e15802250936e1a89db5a9b90fda3d91`
- conclusion **SUCCESS**

Aggregate artifact:

- `11401715062`

Exact sovereign terminal populations:

- R5: 54 trades
- R6: 37
- R8: 33
- recent consumed 2Y: 48

## Causal contract

DOL1 touch is not DOL1 acceptance.

Acceptance requires a **subsequent fully closed M1** to close beyond DOL1 in
trade direction.

Only after that accepted close may DOL2/DOL3/DOL4 be treated as future depth
labels.

H3 full-cognition attribution is used only if the H3 closed-bar state existed
no later than the DOL1 acceptance close.

No future DOL reach label is a runtime input.

## Overall calibration

### R5

- DOL1 accepted: 10
- DOL2 after acceptance: **90%**
- DOL3 after acceptance: **60%**
- DOL4 after acceptance: 20%
- close back inside DOL1 before DOL2: 50%

### R6

- DOL1 accepted: 6
- DOL2: **100%**
- DOL3: **83.33%**
- DOL4: 83.33%
- close back inside DOL1 before DOL2: 0%

### R8

- DOL1 accepted: 8
- DOL2: **100%**
- DOL3: **75%**
- DOL4: 37.5%
- close back inside DOL1 before DOL2: 37.5%

### Recent consumed 2Y

- DOL1 accepted: 7
- DOL2: **71.43%**
- DOL3: **57.14%**
- DOL4: 28.57%
- close back inside DOL1 before DOL2: 42.86%

## Predeclared calibration adjudication

DOL2 required >=70% reach after accepted DOL1 in every fold.

Result:

`DOL2_CALIBRATION_WITNESS = PASS`

DOL3 required >=50% reach after accepted DOL1 in every fold.

Result:

`DOL3_CALIBRATION_WITNESS = PASS`

There is non-zero DOL1 acceptance evidence in all four folds.

## Important interpretation

This is a **capacity calibration**, not an economic policy result.

It proves that after a causal DOL1 acceptance, the market frequently has enough
remaining depth to reach DOL2 and often DOL3.

It does **not** prove that the whole VT31 position should always be held from
DOL1 to DOL2/DOL3.

That economic question must separately measure:

- PF;
- mean R;
- total R;
- DD;
- Monte Carlo;
- winner count preservation;
- winner-R preservation;
- temporal robustness.

This separation is mandatory because waiting for DOL1 acceptance can itself
introduce giveback that did not exist in the DOL1-exit baseline.

## Next phase

The predeclared economic frontier is now authorized on consumed evidence:

- `DOL1_EXIT_BASELINE`
- `ACCEPTED_DOL1_EXTEND_DOL2`
- `ACCEPTED_DOL1_EXTEND_DOL2_STRUCTURAL_PROTECTION`
- `ACCEPTED_DOL1_EXTEND_DOL3`
- `ACCEPTED_DOL1_EXTEND_DOL3_STRUCTURAL_PROTECTION`

No fresh holdout, policy promotion, candidate freeze, merge, LIVE, real capital
or production authority is granted.
