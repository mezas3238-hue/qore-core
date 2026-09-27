# QORE Shared WP-05 — V7 Competing Survival Hypotheses Preregistration

**Program:** QORE Meta-Cognitive Scientific Intelligence  
**Primary PR:** #635  
**Work package:** #643 — WP-05 Temporal Hierarchical Brain  
**Identity:** `QORE_SHARED_WP05_COMPETING_SURVIVAL_HYPOTHESES_V7_001`  
**Target:** `HIGHER_TIMEFRAME_STRUCTURAL_FAILURE_V2`  
**Status:** PREREGISTERED / NOT YET CONSUMED  
**Fresh holdout:** CLOSED  
**Governance:** DRAFT / no LIVE / no production / no real-capital / no merge authority

## 1. Scientific motivation

V3 demonstrated that stronger recovery discrimination can destroy terminal recall.
V5 demonstrated that terminal-safe veto logic can preserve terminal recall while
almost never removing false structural-failure declarations.
V6 improved the trade-off but remained materially below the frozen false-
declaration-reduction gate while preserving terminals.

V7 therefore tests a structurally different hypothesis:

> recoverability and terminality are not opposite ends of one scalar. They are
> competing mechanisms whose evidence may be simultaneously weak or
> contradictory.

V7 is explicitly forbidden from becoming another one-score / one-threshold
variant of V6.

## 2. Frozen scientific question

For a source-time episode where local M1/M3/M5/M15 pressure opposes the
higher-timeframe H1/H4/D1 anchor, determine whether source-time evidence
supports:

- `H_TERMINAL`: pressure is becoming structurally irreversible;
- `H_RECOVERY`: pressure is being absorbed/rejected and higher structure is
  surviving;
- `H_UNRESOLVED`: available evidence does not discriminate the mechanisms.

The model never emits BUY, SELL, BLOCK, CLOSE, RESIZE or any broker mutation.

## 3. Target and population

The target contract is frozen as:

`HIGHER_TIMEFRAME_STRUCTURAL_FAILURE_V2`

Higher-timeframe anchor:

`sign(mean(H1.direction, H4.direction, D1.direction))`

`anchor == 0` is directionally unidentifiable and MUST abstain from the
identified V7 evaluation universe.

Structural frontier and matured offline terminal label remain exactly those in
`QORE_SHARED_WP05_STRUCTURAL_FAILURE_TARGET_CONTRACT_V2.md`.

## 4. Partition law

- R8: discovery / fit / chronological calibration only.
- R6: consumed falsification only.
- R5: consumed falsification only.
- R6/R5: no refit, no threshold retuning, no feature selection, no
  architecture changes.
- Fresh holdout: CLOSED until the exact frozen V7 candidate passes BOTH R6 and
  R5 consumed gates.

The existing temporal non-overlap law remains mandatory:

`R8.target_max < R6.source_min`

`R6.target_max < R5.source_min`

Within R8, every discovery label must mature strictly before the first
calibration source timestamp.

## 5. Frozen development gate

On BOTH R6 and R5:

- false structural-failure declaration reduction >= 2000 bps;
- terminal detection preservation >= 9500 bps.

No averaging across partitions. No gate lowering.

## 6. V7 representation — dual mechanism state

V7 will produce three independent source-time quantities:

- `terminal_hazard` in [0,1];
- `recovery_support` in [0,1];
- `mechanism_conflict` in [0,1].

`mechanism_conflict` is not a third fitted outcome model. It is a deterministic
function of the two mechanism scores and evidence sufficiency.

Final cognitive state:

- `TERMINAL_SUPPORTED`
- `RECOVERY_SUPPORTED`
- `UNRESOLVED`

Baseline structural-failure declaration is suppressed ONLY when
`RECOVERY_SUPPORTED`.

`TERMINAL_SUPPORTED` and `UNRESOLVED` preserve the baseline declaration.
This asymmetry is preregistered to protect terminal detections.

## 7. Frozen source-time feature families

V7 may use only source-time market observations and derived causal history.

### 7.1 Frontier state

- normalized distance to Target-V2 frontier;
- distance 1m, 5m, 15m and 30m ago;
- first derivative of distance over 1m/5m/15m;
- second derivative / acceleration over 5m and 15m;
- source-time breach depth;
- source-time reclaim distance;
- number of source-time frontier touches in 15m and 30m;
- number of source-time breach/reclaim transitions in 15m and 30m.

### 7.2 Acceptance versus rejection sequence

- adverse-close persistence 5m/15m;
- favorable-close persistence 5m/15m;
- consecutive adverse closes;
- consecutive favorable closes;
- rejection wick/range fraction 5m/15m;
- close-location recovery relative to the frontier;
- recovery velocity after the worst source-time excursion;
- time since worst source-time excursion;
- source-time acceptance duration beyond the frontier, if already breached.

### 7.3 Hierarchical transition state

For M1/M3/M5/M15/H1/H4/D1 source-time hierarchy:

- fixed-anchor penetration depth;
- recession count;
- advance count;
- depth velocity;
- higher-timeframe resilience minus fragility;
- change in higher-timeframe resilience minus fragility over 15m and 30m;
- transition-pressure delta over 15m and 30m;
- coherence delta over 15m and 30m.

The same fixed Target-V2 anchor must interpret the full pre-source trajectory.

### 7.4 Cross-market mechanism evidence

NAS100 is the target market. SP500 and US30 may contribute only source-time
market evidence:

- adverse return 1m/5m/15m;
- adverse acceleration 5m/15m;
- breadth: 0/1/2 peers confirming adverse pressure;
- contradiction: target adverse while peers recover;
- peer recovery velocity after source-time adverse excursion;
- lead/lag sign consistency using only past-to-source windows.

No symbol identity is a fitted shortcut. Peer roles are structural inputs fixed
by this experiment.

### 7.5 Volatility / pressure normalization

- 1m/5m/20m range ratios;
- expansion versus compression transition;
- source-time adverse move divided by recent range;
- source-time recovery move divided by recent range.

## 8. Separate mechanism heads

V7 uses two separately fitted bounded linear-logistic heads trained only on R8
discovery:

### Terminal head

Optimizes evidence for the matured Target-V2 terminal label using the terminal
mechanism feature subset:

- frontier penetration / acceptance;
- adverse persistence;
- terminal-side acceleration;
- hierarchy fragility transition;
- cross-market adverse confirmation;
- volatility expansion.

### Recovery head

Optimizes evidence for the complement label using the recovery mechanism subset:

- rejection/reclaim sequence;
- recovery velocity;
- favorable persistence;
- hierarchy resilience / recession;
- cross-market contradiction / peer recovery;
- volatility normalization after excursion.

Feature subsets are fixed by this preregistration. A feature may appear in both
heads only when its sign/meaning is explicitly mechanism-specific.

No nonlinear architecture search is permitted after R8 calibration.

## 9. Fit protocol

Frozen protocol:

- R8 chronological discovery fraction: 70%;
- R8 chronological calibration fraction: 30%;
- discovery/calibration purge by matured-label timestamp;
- standardization parameters fit on R8 discovery only;
- ridge penalty: 4.0 for both heads;
- deterministic optimizer / deterministic feature order;
- no R6/R5 fitting.

## 10. Calibration protocol

Thresholds are chosen on R8 calibration only.

Candidate threshold pairs are evaluated deterministically over a fixed grid:

- terminal threshold: 0.50 to 0.90 inclusive in 0.02 steps;
- recovery threshold: 0.50 to 0.90 inclusive in 0.02 steps.

A source episode becomes `RECOVERY_SUPPORTED` only if:

- `recovery_support >= recovery_threshold`;
- `terminal_hazard < terminal_threshold`;
- mechanism evidence sufficiency passes;
- no conflict rule is triggered.

All other identified episodes preserve the baseline structural-failure
declaration.

Threshold pair selection objective:

1. require R8 calibration terminal preservation >= 9800 bps;
2. among legal pairs maximize false-declaration reduction;
3. tie-break by higher terminal preservation;
4. then by wider threshold separation;
5. then lexicographically for deterministic replay.

This 9800-bps calibration buffer is internal. The external WP-05 consumed gate
remains 9500 bps.

## 11. Evidence sufficiency and conflict state

V7 MUST return `UNRESOLVED` rather than fabricate confidence when:

- anchor is unidentifiable;
- required frontier history is incomplete;
- required peer history is incomplete;
- mechanism scores are both above their thresholds;
- mechanism scores are both within 0.05 of their thresholds;
- essential hierarchy trajectory history is incomplete.

Unresolved identified episodes preserve the baseline declaration for evaluation.

## 12. Anti-leakage contract

Forbidden runtime/model inputs:

- future market bars;
- matured terminal target;
- trade outcome;
- trade PnL;
- trader identity;
- strategy/setup identity;
- trade direction;
- entry;
- stop;
- target;
- sizing;
- CIBO allocation;
- Risk decisions;
- order/execution result;
- broker mutation state as a target shortcut.

Future data are legal only for offline label maturation.

## 13. Required adversarial tests before consumed execution

Tests MUST prove:

1. changing future bars cannot change source-state features;
2. changing terminal labels cannot change source-state features;
3. changing trader/setup/PnL metadata cannot change V7 scores;
4. exact-neutral H1/H4/D1 anchor abstains;
5. one fixed source anchor interprets the entire hierarchy history;
6. discovery observed-at max is strictly earlier than calibration source min;
7. R6/R5 model fingerprints equal the frozen R8 model fingerprint;
8. R6/R5 thresholds are byte-identical to R8-frozen thresholds;
9. deterministic replay produces identical model fingerprint;
10. Shared exposes no methodology, sizing, Risk, order or Execution authority.

## 14. Result states

Legal experiment result states:

- `WP05_V7_PROTOCOL_FAILED`
- `WP05_V7_COMPETING_SURVIVAL_FALSIFIED`
- `WP05_V7_FROZEN_FOR_FRESH_HOLDOUT`

The final state may be `FROZEN_FOR_FRESH_HOLDOUT` only if protocol passes and
BOTH R6/R5 pass the unchanged 2000/9500 gate.

## 15. Fresh holdout law

This preregistration does NOT open fresh evidence.

If V7 survives consumed development, freeze before acquisition:

- source Git SHA;
- model fingerprint;
- representation fingerprint;
- feature list/order;
- standardization values;
- both heads' coefficients/intercepts;
- thresholds;
- Target V2 contract;
- exact holdout window;
- data acquisition protocol;
- scientific gate.

Then open one independent fresh holdout once.

## 16. Sovereignty

V7 is cognition only.

Shared retains zero authority to:

`enter`, `exit`, `send_order`, `position_close`, `modify_stop`,
`modify_tp`, `position_size`, `allocate_capital`, `authorize_risk`,
`block_trade` or `force_trade`.

Trader methodology, CIBO capital authority, QORE Risk and Execution sovereignty
remain unchanged.
