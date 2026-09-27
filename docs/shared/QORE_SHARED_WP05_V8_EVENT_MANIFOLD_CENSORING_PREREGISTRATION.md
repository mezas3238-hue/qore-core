# QORE Shared WP-05 — V8 Event Manifold with Censoring Preregistration

**Program:** QORE Meta-Cognitive Scientific Intelligence  
**PR:** #635  
**Issue:** #643 — WP-05 Temporal Hierarchical Brain  
**Identity:** `QORE_SHARED_WP05_EVENT_MANIFOLD_WITH_CENSORING_V8_001`  
**Target contract:** `HIGHER_TIMEFRAME_STRUCTURAL_FAILURE_V2`  
**Status:** PREREGISTERED / PRE-OUTCOME  
**Fresh holdout:** CLOSED  
**Governance:** DRAFT / no LIVE / no production / no real-capital / no merge authority

## 1. Scientific reason for V8

V7 is permanently falsified.

Authoritative V7 evidence showed:

- recovery support dominated almost the full R8 population;
- R8 calibration false-declaration reduction was 9629 bps;
- R8 calibration terminal preservation collapsed to 736 bps;
- R8 evaluation terminal preservation was 835 bps;
- R6/R5 were not read.

The failure is interpreted as an ontology failure, not a threshold failure:
V7 trained the recovery head on the complement of the terminal label, forcing
all non-terminal episodes to behave as if they were one coherent recovery
mechanism.

V8 removes that assumption.

## 2. Frozen hypothesis

The structural hypothesis is:

> Terminal structural failure and genuine structural recovery are distinct
> event manifolds. Episodes that exhibit neither event are censored unknowns
> and must not be forced into either class.

V8 therefore has three historical event states:

```text
TERMINAL_EVENT
VERIFIED_RECOVERY_EVENT
CENSORED_UNKNOWN
```

This is not a V7 threshold retune and not a new binary classifier over the same
labels.

## 3. Population and source-time cognition

The eligible source population remains WP-05 local-opposition episodes with:

- identifiable Target-V2 higher-timeframe anchor;
- complete source-time market evidence;
- the existing V7 causal source extractor;
- no future information in runtime/source features.

V8 intentionally reuses the frozen V7 source feature representation so that
the experiment isolates the ontology/model change rather than mining a new
feature family after seeing V7.

No trader identity, symbol identity, setup identity, direction shortcut, entry,
stop, target or PnL may be used as fitted shortcuts.

## 4. Target V2 remains unchanged

Higher-timeframe anchor:

```text
sign(mean(H1.direction, H4.direction, D1.direction))
```

Neutral anchor:

```text
anchor == 0 -> DIRECTIONALLY UNIDENTIFIABLE -> ABSTAIN
```

Structural frontier:

```text
prior 20 closed NAS100 M1 bars
```

Terminal event is exactly Target V2.

Bullish anchor:

```text
TERMINAL_EVENT =
future_low < prior_floor
AND
final_30m_close < prior_floor
```

Bearish anchor:

```text
TERMINAL_EVENT =
future_high > prior_peak
AND
final_30m_close > prior_peak
```

The future horizon is offline-label evidence only.

## 5. New VERIFIED_RECOVERY_EVENT ontology

A recovery event is not defined as `NOT terminal`.

A historical episode becomes `VERIFIED_RECOVERY_EVENT` only when ALL of the
following are true:

1. Target V2 terminal event is false.
2. During the same matured 30-minute future horizon, price makes an adverse
   contact with the Target-V2 frontier:
   - bullish anchor: `future_low <= prior_floor`;
   - bearish anchor: `future_high >= prior_peak`.
3. Let `last_contact` be the final future bar that makes that adverse frontier
   contact.
4. After `last_contact`, the path contains at least **3 consecutive closed M1
   bars** on the safe side of the frontier:
   - bullish anchor: close > prior_floor;
   - bearish anchor: close < prior_peak.
5. The final 30-minute close is also on the safe side of the frontier.

The 3-close persistence requirement is frozen here before V8 execution. It is
not tunable against R8/R6/R5.

This event encodes an actually challenged frontier that subsequently reclaimed
and remained structurally safe.

## 6. CENSORED_UNKNOWN

Every eligible non-terminal episode that does not satisfy the verified recovery
event becomes:

`CENSORED_UNKNOWN`

Examples include:

- no meaningful frontier challenge;
- ambiguous oscillation around the frontier;
- contact without persistent reclaim;
- paths that remain structurally unresolved by the 30-minute horizon.

Censored episodes do not define either event manifold.

They remain valid calibration/evaluation observations and preserve the baseline
declaration unless V8 has explicit high-confidence recovery support.

## 7. Event-manifold model

V8 does not fit two complement logistic heads.

Using R8 discovery only:

1. standardize the frozen source representation;
2. fit a robust terminal-event manifold from `TERMINAL_EVENT` observations;
3. fit a robust recovery-event manifold from `VERIFIED_RECOVERY_EVENT`
   observations;
4. use median centers and MAD-like diagonal scales, with deterministic minimum
   scale protection;
5. do not use `CENSORED_UNKNOWN` observations to define either manifold.

For each source state, calculate:

```text
D_terminal
D_recovery
recovery_advantage = D_terminal - D_recovery
```

Lower distance means greater similarity to that event manifold.

## 8. Runtime cognitive states

V8 may emit:

```text
RECOVERY_SUPPORTED
TERMINAL_SUPPORTED
UNRESOLVED
```

Only `RECOVERY_SUPPORTED` may suppress the baseline structural-failure
declaration.

`TERMINAL_SUPPORTED` and `UNRESOLVED` preserve the baseline declaration.

No output has trading, sizing, Risk, order or Execution authority.

## 9. R8-only discovery and calibration

Frozen split:

```text
R8 chronological discovery = first 70%
R8 calibration            = last 30%
```

Matured-label purge is mandatory:

```text
max(discovery.observed_at)
<
min(calibration.source.as_of)
```

R8 discovery fits both robust manifolds.

R8 calibration selects only the legal selective-recovery region.

## 10. Frozen calibration grid

V8 calibrates two source-space thresholds on R8 calibration only:

```text
recovery_radius_quantile in:
0.10, 0.15, 0.20, 0.25, 0.30, 0.35, 0.40, 0.45, 0.50

recovery_advantage_margin in standardized-distance units:
0.00, 0.25, 0.50, 0.75, 1.00, 1.25, 1.50, 2.00
```

A source may be `RECOVERY_SUPPORTED` only if:

```text
D_recovery <= calibrated recovery radius
AND
D_terminal - D_recovery >= calibrated advantage margin
```

Among legal R8 calibration pairs, choose the pair with maximum false-declaration
reduction subject to:

```text
terminal detection preservation >= 9800 bps
```

Tie-break order is frozen:

1. higher terminal preservation;
2. higher false-declaration reduction;
3. smaller recovery radius;
4. larger recovery advantage margin.

If no pair satisfies 9800 bps terminal preservation, V8 is falsified inside R8
and R6/R5 must not be read.

## 11. R6/R5 one-way falsification

Only after a legal R8 model and threshold pair are frozen may V8 read R6/R5.

R6/R5 are strictly:

```text
consumed falsification only
```

Forbidden after R8 freeze:

- manifold refit;
- center/scale refit;
- threshold retuning;
- feature selection;
- event-label redefinition;
- ontology revision.

The exact same model and representation fingerprints must be used on R8, R6
and R5.

## 12. Frozen WP-05 development gate

Unchanged:

```text
false structural-failure reduction >= 2000 bps
AND
terminal detection preservation >= 9500 bps
```

Required independently on:

```text
R6 AND R5
```

No averaging.

No gate lowering.

## 13. Fresh holdout law

Fresh holdout remains CLOSED.

It may open only if one frozen V8 candidate passes the consumed R6 and R5 gate.

Before fresh acquisition, freeze:

- code SHA;
- target contract;
- event ontology;
- representation fingerprint;
- model fingerprint;
- robust manifold parameters;
- calibration thresholds;
- holdout window;
- data acquisition protocol;
- exit gate.

## 14. Required adversarial tests before evidence consumption

V8 implementation must prove:

- future bars cannot change source features;
- terminal/recovery labels cannot appear in runtime source state;
- neutral anchor abstains;
- censored episodes cannot define event manifolds;
- R6/R5 cannot be loaded before legal R8 calibration;
- no legal R8 pair => immediate V8 falsification without R6/R5 access;
- model fingerprint is deterministic;
- representation fingerprint is deterministic and independent from fitted model;
- modifying R6/R5 cannot change frozen R8 model;
- no methodology/sizing/Risk/order/Execution authority exists.

## 15. Scientific interpretation rules

If V8 passes:

- freeze exact identity;
- do not tune against R6/R5;
- preregister independent fresh holdout;
- open fresh evidence once.

If V8 fails:

- freeze evidence;
- document cause;
- do not repair V8 with thresholds or feature mining;
- design V9 as a structurally new hypothesis.

## 16. Governance

Shared remains read-only.

V8 cannot:

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

CIBO, Risk, Trader and Execution sovereignties remain unchanged.
