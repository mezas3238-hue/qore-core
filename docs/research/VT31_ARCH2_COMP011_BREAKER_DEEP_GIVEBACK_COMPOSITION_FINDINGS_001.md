# VT31 NAS100 — Comparator 011 Breaker Deep-Giveback Composition Findings 001

**Status:** FALSIFIED / DO NOT PROMOTE  
**Baseline:** `VT31_AB_COMP009_MAX_INTELLIGENCE_COMPOSED_SURVIVOR`  
**Workflow:** `37529796868` — SUCCESS  
**Tested head:** `6adf4d67f34c71481ac55fb16e86e42713c1c603`  
**Fresh Holdout:** SEALED

## Result

The predeclared conservative Breaker DGR composition is rejected.

Combined Comparator 009 baseline:

- PF: ~4.597921;
- mean: ~+2.131011R/trade;
- stitched observed DD: ~10.149655R;
- annualized Sharpe: ~1.276669;
- annualized Sortino: ~10.494734.

Comparator 011:

- PF: ~4.350947;
- mean: ~+1.975120R/trade;
- stitched observed DD: **10.149655R — unchanged / FAIL**;
- annualized Sharpe: **1.197776 — worse / FAIL**;
- annualized Sortino: ~9.858639;
- changed trades: 6;
- MC p95 DD gate: FAIL;
- Comparator-011 survivor: FALSE.

All four individual fold DD values remained <=6R, but the true chronological
stitched-DD blocker was not improved.

## Exact attribution

The DGR mechanism changed six trades.

### Beneficial changes

- R6 `2019-11-04T15:21:00Z`: -1.0000R -> -0.47619R,
  delta +0.52381R.
- R8 `2016-11-17T15:08:00Z`: -1.0000R -> -0.27273R,
  delta +0.72727R.
- Recent consumed `2024-01-30T15:05:00Z`: -1.0000R -> -0.85417R,
  delta +0.14583R.

### Destructive changes

R5 contained three large Comparator-009 winners that qualified for the same
DGR witness and were converted into small losing protective-stop exits:

- `2021-03-15T14:19:00Z`: +5.45385R -> -0.37692R,
  delta **-5.83077R**.
- `2021-06-23T14:02:00Z`: +6.80822R -> -0.49315R,
  delta **-7.30137R**.
- `2021-11-03T14:13:00Z`: +5.19266R -> -0.06422R,
  delta **-5.25688R**.

R5 therefore changed from:

- PF ~4.8979 -> ~3.7814;
- total +74.7258R -> +56.3368R;
- winners 12 -> 9;
- DD 5.0099R -> 5.6769R.

The mechanism violates the intended winner-tail preservation objective even
though the minimum global winner floor is not the sole reason for rejection.

## Why the old DGR witness did not transfer

The old `DGR_CURRENT_CLOSE_MAX_0_25` witness was established on a different
admitted population. Comparator 009 has materially different admission and
post-entry composition.

On this population the same causal journey pattern can represent either:

- a doomed structural reversal that benefits from rescue; or
- a temporary deep retest inside a large runner that later resumes.

Therefore:

> maximum cognition verified + MFE/giveback/path-efficiency + confirmed swing
> is not sufficient discrimination for Comparator 009.

This is a transfer failure, not evidence that DGR causality is invalid in the
population where it was originally supported.

## Critical stitched-DD finding

None of the six economically changed trades lies inside the existing stitched
maximum-DD interval from the 2022-02-08 peak to the 2023-05-01 trough.

That is why the stitched DD remained exactly:

`10.1496554650811747544085540R`.

The current hard blocker therefore cannot be solved by this DGR composition.

## Cognitive root-cause refinement

The forensic audit of Comparator 009 still exposes a real journey-memory gap:
the core position cognition directly actuates current open-R, path efficiency,
overlap and current context, but does not natively encode peak favorable
open-R / peak-close giveback as a persistent journey state.

Comparator 011 proves that simply bolting the old DGR rule onto the current
population is unsafe. The next solution must discriminate recoverable retests
from failed delivery rather than treating deep giveback itself as sufficient
exit/protection evidence.

## Stop rule

Do not:

- widen DGR from +0.25R;
- relax its efficiency threshold;
- search MFE/giveback thresholds against the known episode;
- generalize DGR to FVG;
- promote Breaker DGR globally;
- reopen Fresh Holdout.

Any next mechanism requires a separate predeclared causal hypothesis.

Comparator 009 remains the baseline.

VT31 remains not certified and has no LIVE, real-capital or production
authorization.
