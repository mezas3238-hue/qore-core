# VT31 NAS100 — Architect B Journey Quality Frontier 001

Status: **FALSIFIED EXTENSION / SURVIVOR UNCHANGED**

Run: `37379713816`  
Head: `7d8f2831573d4b8db195e041baf88cdea0dd9c5e`  
Conclusion: **SUCCESS**

Artifacts:

- R5: `11372883031`
- R6: `11372743467`
- R8: `11372713285`
- consumed 2Y: `11374000290`

## Question

Can the 4/4 `LBB_PATH_SHALLOW_PS1` survivor be extended with a +0.25R
whole-position lock on other Breaker SHALLOW trades after a closed +1R
checkpoint?

A prior VT31 journey hypothesis also tested whether checkpoint overlap <25%
should gate that lock.

## Result

### Consumed 2Y

The broader composition improves materially:

- baseline PF 0.7413;
- survivor-only PF 0.7721;
- survivor + all remaining Breaker SHALLOW lock PF **0.8105**;
- DD **59.28R**;
- total **-40.81R**;
- winner count preservation **100%**;
- winner-R preservation **100%**.

The overlap <25% gate is weaker in consumed:

- PF 0.7950;
- DD 63.28R.

### R6

Both lock compositions improve economics; broad lock reaches PF **1.6743**.

### R8

Overlap <25% is better than the broad lock:

- PF **1.0334**;
- DD **36.69R**;
- winner-R preservation **99.60%**.

### R5 — decisive falsification

Both lock extensions degrade the already-positive R5 fold.

Broad composition:

- PF **1.0293** vs baseline 1.0938;
- total **+7.00R** vs +22.96R;
- DD **65.49R** vs 61.30R;
- winner-R preservation **90.59%**.

Overlap <25%:

- PF **1.0463**;
- total **+11.09R**;
- DD **65.74R**.

Therefore neither composition is a stable 4/4 improvement.

## Decision

- `SURVIVOR_PLUS_BREAKER_SHALLOW_ALL_LOCK025`: **REJECTED**.
- `SURVIVOR_PLUS_BREAKER_SHALLOW_OVERLAP_LT025_LOCK025`: **REJECTED**.
- prior `overlap < 25%` hypothesis: **not sufficient for promotion**.
- `LBB_PATH_SHALLOW_PS1`: remains the current Architect B development survivor.

No runtime policy, fresh holdout, merge, LIVE, real-capital or production
authority is granted.
