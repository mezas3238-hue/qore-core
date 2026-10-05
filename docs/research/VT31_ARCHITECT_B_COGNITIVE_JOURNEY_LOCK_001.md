# VT31 NAS100 — Architect B Cognitive Journey Lock 001

Status: **DEVELOPMENT SURVIVOR FOUND / NOT FROZEN / NOT CERTIFIED**

Owner: Sergio Meza  
Branch: `agent/vt31-edge-position-cert-b-001`

## Run binding

Run: `37379249394`  
Head: `8a8f43c4880c0fb3af57f1d4734e231a3ef46fb2`  
Conclusion: **SUCCESS**

Artifacts:

- R5: `11373122282`
- R6: `11373925084`
- R8: `11373415409`
- consumed 2Y: `11373880247`

## Test design

The frontier kept unchanged:

- Silver Bullet;
- trade admission;
- entry;
- initial invalidation;
- structural target;
- normalized equal-risk economics.

Journey locks were allowed only after a **closed M1 earned +1R** and became
effective on the following M1. No partial exit or absolute volume was required.

## Key falsifications

### BREAKER_SHALLOW_LOCK025_100

Improves R6, R8 and consumed but materially damages R5.

Result: **REJECTED AS GLOBAL POLICY**.

### LBB_PATH_LOCK025_100

Strong R8 result but worsens consumed.

Result: **REJECTED AS GLOBAL POLICY**.

### LBB_PATH_SHALLOW_LOCK025_100

Positive but inferior to PS1 in the most important consumed case.

Result: **NOT SELECTED**.

## Development survivor: LBB_PATH_SHALLOW_PS1

Eligibility:

```
last_structure_event_family == breaker
AND current path is not compressed
AND destination_state == SHALLOW
```

Action:

- keep original initial stop;
- wait for first confirmed protective M1 swing;
- activate protection only from the next M1;
- improve stop only;
- never widen;
- no volume split.

### R5

- Baseline PF: 1.0938
- Survivor PF: **1.1201**
- Baseline total: +22.96R
- Survivor total: **+28.94R**
- Baseline DD: 61.30R
- Survivor DD: **57.70R**
- Winner count preservation: **100%**
- Winner-R preservation: **100%**

### R6

- Baseline PF: 1.5857
- Survivor PF: **1.6200**
- Baseline total: +125.43R
- Survivor total: **+130.67R**
- Baseline DD: 29.06R
- Survivor DD: **28.40R**
- Winner count preservation: **100%**
- Winner-R preservation: **100%**

### R8

- Baseline PF: 0.9988
- Survivor PF: **1.0113**
- Baseline total: -0.25R
- Survivor total: **+2.24R**
- Baseline DD: 43.43R
- Survivor DD: **40.94R**
- Winner count preservation: **97.62%**
- Winner-R preservation: **99.60%**

### Consumed 2Y

- Baseline PF: 0.7413
- Survivor PF: **0.7721**
- Baseline total: -58.14R
- Survivor total: **-50.81R**
- Baseline DD: 74.59R
- Survivor DD: **68.03R**
- Winner count preservation: **100%**
- Winner-R preservation: **100%**

## Decision

`LBB_PATH_SHALLOW_PS1` is a **development survivor only**.

It improves PF, total R and DD in all four consumed folds while satisfying
winner-preservation requirements, but it is far from sufficient for final
certification because consumed 2Y remains negative and drawdown remains far
above the Owner gates.

The next research stage must attack the remaining `GIVEBACK_AFTER_1R` and
dead-on-arrival populations with richer causal journey features, without
turning this survivor into an outcome-aware filter.

No fresh holdout, merge, LIVE, real capital or production authority is granted.
