# VT31 NAS100 — Post-1R Full-Cognition Management Findings 001

**Owner:** Sergio Meza  
**Status:** CROSS-FOLD RESEARCH SURVIVOR / NOT CANDIDATE-FROZEN  
**Branch:** `agent/vt31-edge-position-cert-b-001`  
**Workflow:** `37405258891` — SUCCESS  
**Head:** `f1fd784acfaec238157548a8a233b19011aa915b`

## Sovereign constraints

The replay used the same sovereign VT31 admission population and kept:

- entry unchanged;
- initial structural invalidation unchanged;
- primary structural target unchanged;
- lifecycle unchanged;
- equal/neutral certification exposure;
- no position sizing;
- no leverage;
- no compounding;
- no capital weighting;
- no volume-dependent decision;
- no fresh holdout.

R remained allowed as trader logic.

## Architectural repair before the replay

VT31 now distinguishes:

- `reason()` — admission reasoning: should a **new** trade be opened?
- `reason_position()` — live-position reasoning: how should an **already
  admitted** trade be interpreted now?

Admission-only predicates such as:

- late entry cutoff;
- current-path compression required for a new entry;
- low-DD reference entry gate;

remain visible in the audit trail but no longer become automatic exit/protection
authority after a trade is already open.

Current position reasoning still consumes the complete causal context and may
retain true position-authoritative contradictions such as calibrated journey
depletion.

## Experiment

After the first unambiguous +1R event, VT31 reassessed at:

- H2 = 2 closed M1 bars;
- H3 = 3 closed M1 bars;
- H5 = 5 closed M1 bars.

At each horizon the experiment rebuilt current causal cognition and preserved
the original structural baseline unless cognition justified an action.

Observed journey states:

- `PERSISTENT_1R_FLOOR`
- `RECOVERED_1R_FLOOR`
- `POSITIVE_BELOW_1R`
- `ENTRY_OR_WORSE`

## Cross-fold adjudication

All three variants were research survivors:

| Variant | PF nondegrade | Mean-R nondegrade | DD nondegrade | Winner count | Winner-R | Half-years |
|---|---:|---:|---:|---:|---:|---:|
| H2 full cognition | 4/4 | 4/4 | 4/4 | 100% all folds | 100% all folds | nondegrade |
| H3 full cognition | 4/4 | 4/4 | 4/4 | 100% all folds | 100% all folds | nondegrade |
| H5 full cognition | 4/4 | 4/4 | 4/4 | 100% all folds | 100% all folds | nondegrade |

This is materially stronger than the earlier persistence-only and
efficiency-only variants, which damaged winner-R or individual chronological
blocks.

## H3 — leading balanced research witness

H3 is currently the best-balanced consumed-evidence witness. It is not frozen
as policy.

### R5

Baseline:

- PF 1.916915
- mean +0.748814R
- total +40.435968R
- DD 12.600000R

H3:

- PF **2.025267**
- mean **+0.792506R**
- total **+42.795317R**
- DD **11.907317R**
- winner count preservation **100%**
- winner-R preservation **100%**

### R6

Baseline:

- PF 2.303462
- mean +1.109704R
- total +41.059062R
- DD 12.744444R

H3:

- PF **2.378986**
- mean **+1.136731R**
- total **+42.059062R**
- DD **12.744444R**
- winner count preservation **100%**
- winner-R preservation **100%**

### R8

H3 correctly elected not to interfere economically.

Baseline = H3:

- PF **2.670846**
- mean **+1.329082R**
- total **+43.859711R**
- DD **11.661905R**
- winner preservation **100% / 100%**

This is important: full cognition learned that "doing nothing" can be the
correct management action.

### Consumed recent 2Y

Baseline:

- PF 1.046435
- mean +0.040631R
- total +1.950268R
- DD 13.834146R

H3:

- PF **1.069586**
- mean **+0.059570R**
- total **+2.859359R**
- DD **12.925055R**
- winner count preservation **100%**
- winner-R preservation **100%**

Every half-year is non-degrading.

## Mechanism interpretation

The improvement is sparse and selective rather than aggressive.

Examples of H3 action counts:

- R5: 1 BE arm, 2 depleted exits, 30 runner holds;
- R6: 1 BE arm, 14 runner holds;
- R8: 19 runner holds and **zero economic modification**;
- consumed: 1 depleted exit, 24 runner holds.

That behavior is aligned with the Owner directive: use intelligence to decide
when intervention is warranted, not impose a universal management rule.

## Important limitation

This result calibrates a **contextual post-1R management mechanism**, but does
not yet finish maximum-intelligence certification.

The trader still needs deeper target/journey intelligence:

- whether a strong winner should stop at DOL1;
- when DOL1 acceptance justifies extension;
- which structural DOL/target is the next valid destination;
- when a retest should be tolerated rather than protected;
- how much extension can be preserved without destroying winner-R.

Therefore:

- contextual management has a 4/4 consumed-evidence survivor;
- target-extension depth remains an explicit certification blocker;
- recent consumed 2Y PF 1.069586 is still far below final certification gates;
- no candidate freeze;
- no holdout opening;
- no merge;
- no LIVE / real-capital / production authority.
