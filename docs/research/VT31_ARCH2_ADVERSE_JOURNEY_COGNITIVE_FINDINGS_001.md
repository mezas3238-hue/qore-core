# VT31 NAS100 — Adverse Journey Cognitive Findings 001

**Owner:** Sergio Meza  
**Status:** CONSUMED-EVIDENCE DEVELOPMENT FINDINGS / NOT PROMOTED  
**Branch:** `agent/vt31-edge-position-cert-b-001`

## 1. False exhaustion defect closed

The pre-DOL1 live-cognition frontier exposed a semantic bug:

`NO_CONFIRMED_EXHAUSTION`

was being matched by the generic `EXHAUST` token and therefore incorrectly
became:

`EXIT_ON_CONFIRMED_EXHAUSTION`.

That made the earlier live-cognitive run appear inert: dozens of valid
pre-DOL1 observations were classified as confirmed exhaustion before the
HOLD/TRAIL decision could execute.

The parser now explicitly recognizes negative exhaustion semantics before
positive exhaustion tokens. Regression tests require:

- `NO_CONFIRMED_EXHAUSTION` -> not exhausted;
- material adverse open-R can remain `PRESERVE_DOL1`;
- a valid causal protective swing can reach `TRAIL`.

## 2. Live Breaker trailing after the fix

Workflow `37469132665` completed SUCCESS.

The corrected cognition did authorize real trailing, proving the runtime path
is active. However, no trailing variant survived cross-fold adjudication.

Example `COG_SWING_PS1`:

- R6 improved slightly;
- R8 improved slightly;
- R5 lost expectancy/winner-R;
- recent consumed degraded materially:
  - PF about 1.5537 -> 1.4687;
  - DD about 10.57R -> 13.35R;
  - MC positive about 81.54% -> 76.33%.

Conclusion: an improving M1 swing plus merely non-LOW protection urgency is not
sufficient authority for universal Breaker trailing.

## 3. Causal adverse-journey exit

Workflow `37468952126` completed SUCCESS.

The predeclared material adverse state is:

`current_open_r <= -0.50R`

computed only from frozen entry geometry, frozen initial structural risk, side
and fully closed causal M1 prices.

### Development survivors

Two equivalent variants survived all current development gates:

- `COG_EXIT_CAUTION`;
- `COG_EXIT_CAUTION_WEAK_PATH`.

They are identical on the tested population because the one CAUTIOUS recent
material-adverse path also satisfied the weak-path observation.

For `COG_EXIT_CAUTION`:

- PF non-degrading: 4/4;
- mean-R non-degrading: 4/4;
- observed DD non-degrading: 4/4;
- winner preservation: PASS 4/4;
- half-year mean/DD non-degradation: PASS;
- maximum-intelligence blockers at evaluated actions: none.

Recent consumed changed exactly one trade:

- PF: 1.55369 -> 1.57443;
- mean: +0.44921R -> +0.45990R;
- DD: 10.57140R -> 10.15473R;
- MC positive: 81.54% -> 82.51%;
- MC p95 DD: 19.70R -> 19.07R;
- winner count preservation: 100%;
- winner-R preservation: 100%.

Historical R5/R6/R8 were unchanged, so this mechanism did not destroy
historical winners.

## 4. Broad MIXED exit rejected

`COG_EXIT_NONSUPPORTIVE` exits every material-adverse MIXED/CAUTIOUS path.

It is rejected.

It destroyed historical and recent winners and increased drawdown in multiple
folds. Therefore:

> MIXED is not an exit signal.

The remaining problem is to discriminate a causal negative subclass inside
material-adverse MIXED states.

## 5. Current research question

Current recent DD remains about 10.15R after the safe CAUTIOUS exit, above the
sovereign <=6R certification gate.

The next work is observation-only attribution of the **first material-adverse
state per trade** using fields already observable at that instant:

- management context;
- weak-path state;
- H4/H1/M15;
- current reasoning action;
- destination state;
- support/caution margin;
- current open-R band;
- reclaim age;
- latest structure event.

Terminal outcome may be used only for retrospective forensic attribution on
consumed evidence. It has zero runtime authority.

Any candidate conjunction discovered from these forensics must then be
predeclared and replayed cross-fold before it can become a development
survivor.

## 6. Governance

VT31 remains NOT CERTIFIED.

The hard certification gate remains observed DD <=6R.

No sizing, dynamic sizing, leverage, compounding, portfolio/capital weighting,
fresh holdout, candidate freeze, LIVE, real capital or production authority is
introduced by these findings.
