# QORE Shared WP-05 — V9 Causal Trajectory Discrimination Preregistration

**Program:** QORE Meta-Cognitive Scientific Intelligence  
**PR:** #635  
**Issue:** #643 — WP-05 Temporal Hierarchical Brain  
**Identity:** `QORE_SHARED_WP05_CAUSAL_TRAJECTORY_DISCRIMINATION_V9_001`  
**Target contract:** `HIGHER_TIMEFRAME_STRUCTURAL_FAILURE_V2`  
**Status:** PREREGISTERED / PRE-OUTCOME  
**Fresh holdout:** CLOSED  
**Governance:** DRAFT / no LIVE / no production / no real-capital / no merge authority

## 1. Scientific reason for V9

V8 is permanently falsified.

Authoritative V8 evidence showed that explicit censoring fixed the V7 ontology
failure and preserved terminal detections, but the static source-state event
manifold suppressed too few false structural-failure declarations:

- R6 false reduction: 146 bps; terminal preservation: 9784 bps;
- R5 false reduction: 214 bps; terminal preservation: 9784 bps.

V9 does not retune V8.

The new hypothesis is that terminal failure and recoverable adversity can occupy
similar source snapshots while differing in the *causal path that produced the
snapshot*. V9 therefore changes the representation from a static source vector
to a source-time trajectory signature.

## 2. Frozen hypothesis

> The path into a Target-V2 frontier contains discriminating information that is
> lost by static source-state geometry. A causal pre-source trajectory model,
> combined with an explicit event-vs-censored gate, can identify a larger safe
> recovery subset without sacrificing terminal preservation.

V9 has two distinct questions:

1. `EVENTNESS`: does the source trajectory resemble a matured structural event
   family (terminal or verified recovery), rather than a censored/ambiguous path?
2. `RECOVERY_CONTRAST`: conditional on event-like trajectory evidence, does the
   causal path resemble verified recovery more than terminal failure?

This is not V7's complement-label dual-head model:

- the recovery contrast is trained ONLY on
  `TERMINAL_EVENT` vs `VERIFIED_RECOVERY_EVENT`;
- censored observations never become recovery labels;
- the eventness head explicitly separates event families from
  `CENSORED_UNKNOWN`.

## 3. Event ontology

V9 inherits the frozen V8 offline ontology unchanged:

```text
TERMINAL_EVENT
VERIFIED_RECOVERY_EVENT
CENSORED_UNKNOWN
```

Terminal event remains exactly Target V2.

Verified recovery remains exactly the V8 definition:

- Target-V2 terminal event is false;
- the frontier is challenged during the matured 30m future horizon;
- after final adverse contact, at least 3 consecutive M1 closes reclaim the safe
  side;
- the final 30m close is safe.

Future data are offline labels only and never source/runtime features.

## 4. Causal source trajectory

V9 source-time representation is built from information available at the source
timestamp only.

The fixed source anchor is:

```text
sign(mean(H1.direction, H4.direction, D1.direction))
```

Neutral anchor remains:

```text
anchor == 0 -> DIRECTIONALLY UNIDENTIFIABLE -> ABSTAIN
```

The Target-V2 source frontier is the prior 20 closed NAS100 M1 bars at the source
timestamp.

The trajectory representation uses the 30 closed M1 bars ending at the source,
partitioned into six chronological 5-minute blocks.

For each 5-minute block, freeze these source-time features:

1. NAS100 mean signed close distance to the fixed source frontier, normalized by
   the source 20-bar mean range;
2. NAS100 minimum signed distance in the block;
3. fraction of bars touching the adverse frontier;
4. fraction of closes beyond the adverse frontier;
5. anchor-signed NAS100 block return;
6. mean normalized NAS100 range;
7. anchor-adverse SP500 block return;
8. anchor-adverse US30 block return.

This creates 48 ordered trajectory coordinates.

Add 12 frozen transition coordinates:

- distance velocity across the last two blocks;
- distance acceleration across the last three blocks;
- touch-rate velocity;
- breach-close-rate velocity;
- NAS adverse-return acceleration;
- SP500 adverse-return acceleration;
- US30 adverse-return acceleration;
- peer breadth in the last block;
- peer breadth change;
- count of frontier touch-state transitions across six blocks;
- count of breach-close-state transitions across six blocks;
- last-block rejection/reclaim fraction.

Total V9 representation width is frozen at **60 features**.

No feature may read a bar after the source timestamp.

## 5. Model architecture

V9 fits two regularized logistic components on R8 discovery only.

### Eventness head

Training population: all discovery episodes.

Target:

```text
1 = TERMINAL_EVENT or VERIFIED_RECOVERY_EVENT
0 = CENSORED_UNKNOWN
```

### Recovery-contrast head

Training population: discovery event-family episodes only.

Target:

```text
1 = VERIFIED_RECOVERY_EVENT
0 = TERMINAL_EVENT
```

Censored observations are excluded from the recovery-contrast fit.

Both heads use:

```text
ridge = 4.0
training steps = 500
learning rate = 0.05
```

No model family, ridge, feature family or optimizer parameter may be changed
after V9 evidence is observed.

## 6. Runtime cognitive states

V9 may emit:

```text
RECOVERY_SUPPORTED
TERMINAL_SUPPORTED
UNRESOLVED
```

Only `RECOVERY_SUPPORTED` may suppress the baseline structural-failure
declaration.

`TERMINAL_SUPPORTED` and `UNRESOLVED` preserve it.

V9 has no trading or capital authority.

## 7. Frozen R8 split and purge

```text
R8 discovery   = first 70%
R8 calibration = last 30%
```

Matured-label purge is mandatory:

```text
max(discovery.observed_at)
<
min(calibration.source.as_of)
```

R8 must be fully fitted and calibrated before scientific access to R6/R5.

## 8. Frozen calibration grid

R8 calibration only:

```text
eventness threshold:
0.50, 0.55, 0.60, 0.65, 0.70, 0.75, 0.80

recovery-contrast threshold:
0.55, 0.60, 0.65, 0.70, 0.75, 0.80, 0.85, 0.90
```

A source becomes `RECOVERY_SUPPORTED` only when:

```text
eventness >= eventness_threshold
AND
recovery_contrast >= recovery_threshold
```

A source becomes `TERMINAL_SUPPORTED` when:

```text
eventness >= eventness_threshold
AND
recovery_contrast <= (1 - recovery_threshold)
```

Everything else is `UNRESOLVED`.

Select the legal R8 calibration pair with MAXIMUM false-declaration reduction
subject to:

```text
terminal detection preservation >= 9800 bps
```

Frozen tie-break order:

1. higher false-declaration reduction;
2. higher terminal preservation;
3. higher eventness threshold;
4. higher recovery threshold.

If no legal R8 calibration pair exists, V9 is falsified inside R8 and R6/R5
must not be scientifically read.

## 9. R6/R5 consumed falsification

Only after the exact R8 representation, model and thresholds are frozen may V9
evaluate R6 then R5.

Forbidden after R8 freeze:

- refit;
- re-standardization;
- threshold retuning;
- feature selection;
- event ontology changes;
- block-size changes;
- target changes.

The same representation fingerprint and model fingerprint must be used across
R8/R6/R5.

## 10. Frozen WP-05 development gate

Unchanged:

```text
false structural-failure reduction >= 2000 bps
AND
terminal detection preservation >= 9500 bps
```

Required independently on BOTH:

```text
R6
R5
```

No averaging and no gate lowering.

## 11. Fresh holdout

Fresh holdout remains CLOSED.

It may be preregistered/opened only after one exact V9 identity passes the
consumed R6 and R5 development gate.

Before fresh acquisition freeze:

- Git SHA;
- representation fingerprint;
- model fingerprint;
- standardization;
- coefficients;
- thresholds;
- event ontology;
- target contract;
- holdout window;
- evidence-acquisition protocol;
- exit gate.

## 12. Required adversarial tests before evidence consumption

V9 implementation must prove:

- changing any bar after source cannot change the V9 source vector;
- changing source/past bars can change the source vector;
- exactly 60 frozen trajectory features exist;
- neutral anchor abstains;
- censored observations cannot become positive recovery labels;
- recovery contrast fits only terminal/recovery event families;
- R6/R5 cannot be scientifically opened before legal R8 freeze;
- no legal R8 pair causes fail-closed falsification before R6/R5;
- model and representation fingerprints are deterministic;
- modifying R6/R5 cannot change R8 model or thresholds;
- no trader/symbol/setup/entry/stop/target/PnL shortcuts exist;
- no methodology, sizing, CIBO, Risk, order or Execution authority exists.

## 13. Scientific interpretation

If V9 passes consumed development:

- freeze exact identity;
- do not retune;
- preregister one independent fresh holdout;
- open fresh evidence once.

If V9 fails:

- freeze evidence and artifact digest;
- document the failure mechanism;
- do not repair V9 with threshold or feature mining;
- design a structurally new V10.

## 14. Governance

Shared remains observation/cognition only.

V9 cannot:

```text
enter
exit
send_order
position_close
modify_stop
modify_tp
position_size
allocate_capital
authorize_risk
block_trade
force_trade
```

Trader, CIBO, QORE Risk and Execution sovereignty remain unchanged.
