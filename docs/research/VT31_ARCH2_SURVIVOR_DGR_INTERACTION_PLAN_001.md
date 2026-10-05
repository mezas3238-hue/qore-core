# VT31 NAS100 — Architect B Survivor + DGR Interaction Plan 001

**Status:** PREDECLARED CONSUMED-EVIDENCE EXPERIMENT / NOT EXECUTED  
**Owner:** Sergio Meza  
**Branch:** `agent/vt31-edge-position-cert-b-001`

## 1. Purpose

Test whether two independently supported post-admission mechanisms can coexist
without hiding admission defects or destroying the NAS100 runner tail.

Mechanism A — cognitive structural survivor:

`LBB_PATH_SHALLOW_PS1`

Eligibility:

- last observed structure family = breaker;
- `CURRENT_PATH_NOT_COMPRESSED` contradiction present;
- destination state = SHALLOW.

Action:

- one confirmed protective M1 swing;
- effective next M1;
- stop improvement only;
- no widening.

Mechanism B — deep giveback rescue research witness:

`DGR_CURRENT_CLOSE_MAX_0_25`

Eligibility is post-entry only:

- observed MFE >= 1.50R;
- peak-close giveback >= 1.00R;
- current closed price <= +0.25R;
- recent 5-bar path efficiency <= 0.10;
- confirmed protective M1 swing.

Action:

- one rescue move maximum;
- effective next M1;
- stop improvement only;
- no widening.

## 2. Why this experiment is predeclared now

The following broader journey-lock families were already falsified:

- generic +0.25R lock after a closed +1R;
- Breaker SHALLOW +0.25R lock;
- Breaker SHALLOW + overlap<25% +0.25R lock.

They improved some folds but degraded R5.

DGR differs causally because it does not protect merely because +1R was earned.
It waits until the closed-price journey has subsequently deteriorated deeply
back toward entry and a fresh structural swing exists.

The interaction therefore must be tested directly rather than inferred from
either prior study.

## 3. Frozen experiment variants

Only these four variants are authorized for this experiment:

### V0 — BASELINE

Current admitted population and current baseline lifecycle.

### V1 — SURVIVOR_PS1_ONLY

Apply `LBB_PATH_SHALLOW_PS1` exactly as already defined.

No DGR.

### V2 — DGR025_SINGLE_ONLY

Apply the single-move DGR witness to the admitted population.

No cognition-based PS1 selection.

### V3 — SURVIVOR_PS1_PLUS_DGR025_FALLBACK

Mutually exclusive management authority per trade:

1. if the trade is `LBB_PATH_SHALLOW_PS1` eligible, use survivor PS1;
2. otherwise the trade may use single-move DGR025 if its later causal journey
   qualifies;
3. never stack two Architect-B structural protection moves on one trade.

This mutual exclusion is deliberate. The first interaction test must not
confound edge attribution with multiple sequential stop moves.

## 4. Frozen invariants

All variants must preserve:

- identical trade admission;
- identical entry;
- identical initial stop;
- identical structural destination;
- identical lifecycle;
- identical friction convention;
- equal normalized R;
- no sizing;
- no leverage;
- no compounding;
- no capital weighting;
- no absolute volume dependency;
- no partial exit requirement;
- no provider-specific volume rule;
- no terminal-PnL runtime input;
- no future journey runtime label;
- no fold identity runtime input.

Universal execution compatibility from 0.01 remains a provider/adaptor
capability and is not an edge variable.

## 5. Evidence

Consumed evidence only:

- R5;
- R6;
- R8;
- consumed 2Y.

No fresh holdout may be opened by this experiment.

## 6. Primary attribution gates

V3 may survive only if all of the following are true.

### Cross-fold economics

Against V0:

- PF non-degrading in 4/4 folds;
- mean R non-degrading in 4/4 folds;
- max DD non-degrading in 4/4 folds.

Against V1:

- PF and/or mean R must improve in at least 3/4 folds;
- neither PF nor mean R may materially deteriorate in any fold;
- DD may not materially deteriorate in any fold.

A composition that merely redistributes benefit between folds is rejected.

### Winner preservation

Per fold:

- winner-count preservation >= 80%;
- winner-R preservation >= 90%.

Preferred:

- winner-count >= 90%;
- winner-R >= 95%.

Any severe runner destruction is automatic rejection.

### Temporal robustness

For R5/R6/R8, report every half-year.

V3 must not obtain its aggregate benefit by sacrificing an entire chronological
half-year. Any negative management delta must be explicitly attributed and
adjudicated before further promotion.

### Side robustness

Report LONG and SHORT independently.

This is diagnostic, not permission to delete a side.

## 7. Required telemetry

Every changed trade must expose:

- trade_id;
- local_date;
- side;
- entry_family;
- cognition survivor eligibility;
- DGR eligibility;
- protection mechanism actually selected;
- observed MFE at DGR trigger;
- current close R at trigger;
- peak-close giveback R;
- recent path efficiency;
- protective swing level;
- effective next-bar timestamp;
- baseline R;
- managed R;
- delta R;
- exit reason;
- whether a baseline winner was changed.

## 8. Adjudication meanings

Possible results:

- `INTERACTION_SURVIVOR`
- `DGR_REDUNDANT_WITH_COGNITION`
- `COGNITIVE_SURVIVOR_DOMINATES`
- `INTERACTION_DESTROYS_WINNERS`
- `INTERACTION_TEMPORALLY_UNSTABLE`
- `NOT_SUPPORTED`

No result from consumed evidence can mean:

- candidate frozen;
- edge certified;
- holdout authorized;
- LIVE authorized.

## 9. Next action after this experiment

Only if V3 survives all frozen gates should Architect B consider wiring the
mechanism into `vt31_nas100_position_intelligence.py` as a calibrated
development policy.

Otherwise:

- retain the independent surviving mechanism(s);
- document the falsification;
- continue causal journey research.

Fresh holdout remains sealed.
