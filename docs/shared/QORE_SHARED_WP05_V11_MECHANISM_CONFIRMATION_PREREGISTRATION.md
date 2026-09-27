# QORE Shared WP-05 — V11 Sequential Mechanism Confirmation Preregistration

**Program:** QORE Meta-Cognitive Scientific Intelligence  
**PR:** #635  
**Issue:** #643 — WP-05 Temporal Hierarchical Brain  
**Identity:** `QORE_SHARED_WP05_SEQUENTIAL_MECHANISM_CONFIRMATION_V11_001`  
**Target contract:** `HIGHER_TIMEFRAME_STRUCTURAL_FAILURE_V2`  
**Status:** PREREGISTERED / PRE-OUTCOME  
**Fresh holdout:** CLOSED  
**Governance:** DRAFT / no LIVE / no production / no real-capital / no merge authority

## 1. Authorization

V10 is permanently falsified on the consumed 2000/9500 development gate, but
its sequential evidence produced material incremental observability above the
pre-frozen 500-bps criterion independently on R6 and R5:

- R6: +727 bps incremental false-declaration reduction, 9810 bps terminal preservation;
- R5: +721 bps incremental false-declaration reduction, 9858 bps terminal preservation.

Therefore the anti-loop transition law authorizes exactly one structurally new
sequential-state hypothesis before Active Perception.

V11 is not V10.1. No V10 threshold, density, feature or R6/R5 result is retuned.

## 2. Structural failure diagnosed in V10

V10's declaration rule is effectively:

`max(checkpoint terminal LLR) crosses threshold -> absorbing terminal declaration`.

That architecture cannot distinguish:

- one transient early evidence spike;
- persistent frontier deterioration;
- simultaneous cross-market confirmation;
- a structural prior that agrees or disagrees with the path.

A false early spike is irreversible even when later causal evidence contradicts it.

V10 detection latency also shows that almost all useful terminal information is
available by 3-5 minutes. Extending the horizon is therefore not the V11 hypothesis.

## 3. Frozen V11 hypothesis

A genuine higher-timeframe structural failure should become **mechanistically
confirmed**, not merely score-high once.

V11 separates three evidence mechanisms:

1. **FRONTIER_PATH**
   - fixed-frontier distance;
   - breach depth;
   - adverse-distance integral;
   - consecutive breach closes;
   - breach-close fraction;
   - breach/reclaim transitions;
   - reclaim distance;
   - adverse/favorable velocity;
   - realized range expansion.

2. **CROSS_MARKET**
   - SP500/US30 adverse move;
   - adverse breadth;
   - peer contradiction.

3. **SOURCE_HIERARCHY_PRIOR**
   - source hierarchy depth;
   - higher fragility minus resilience;
   - higher resilience minus fragility.

These groups are frozen before V11 execution.

## 4. Sensor universe and checkpoint semantics

V11 reuses the exact V10 causal sensor universe and wall-clock semantics to
isolate the sequential state-machine hypothesis:

- NAS100/SP500/US30 M1 retained evidence only;
- checkpoints 0/3/5/10/15 minutes;
- each market uses latest closed observation at-or-before checkpoint;
- N>0 requires a new observation since source;
- no post-checkpoint evidence;
- Target-V2 frontier remains fixed from the 20 closed NAS100 M1 bars ending at source;
- neutral higher-timeframe anchor abstains.

No new sensor is introduced in V11.

## 5. Mechanism likelihoods

R8 discovery fits robust terminal vs non-terminal class-conditional densities
separately for every mechanism at every checkpoint.

For each mechanism, checkpoint evidence is converted into a normalized
log-likelihood ratio:

`LLR_mechanism(t) = log P(features_t | terminal) - log P(features_t | nonterminal)`.

The same robust median/MAD family and clipping law is used consistently inside
V11. Parameters are fit on R8 discovery only.

## 6. Persistence and concordance

For every checkpoint after t0:

`PERSISTENT_FRONTIER(t) = min(FRONTIER_PATH_LLR(t-1), FRONTIER_PATH_LLR(t))`

`CROSS_CONFIRMATION(t) = CROSS_MARKET_LLR(t)`

`HIERARCHY_CONFIRMATION = SOURCE_HIERARCHY_PRIOR_LLR(0)`

V11 forms the **2-of-3 mechanism confirmation score** as the second-largest of:

- PERSISTENT_FRONTIER(t);
- CROSS_CONFIRMATION(t);
- HIERARCHY_CONFIRMATION.

This gives an explicit meaning:

> at least two distinct mechanisms must support terminality at the frozen
> confirmation boundary.

No weighted sum is fitted.

## 7. State machine

Frozen states:

- `UNRESOLVED`;
- `TERMINAL_WATCH`;
- `TERMINAL_CONFIRMED`;
- `RECOVERY_SUPPORTED`.

Rules:

1. t0 can never emit `TERMINAL_CONFIRMED`.
2. t0 may emit `TERMINAL_WATCH` when source mechanisms support terminality.
3. From t+3m onward, `TERMINAL_CONFIRMED` requires the 2-of-3 confirmation score
   to cross the frozen confirmation threshold.
4. `TERMINAL_CONFIRMED` is absorbing for evaluation.
5. Before confirmation, an explicit V10-style safe-side reclaim
   (breach observed + >=3 safe-side consecutive closes) may emit
   `RECOVERY_SUPPORTED`.
6. `TERMINAL_WATCH` and `RECOVERY_SUPPORTED` are not structural-failure declarations.
7. No state may read the matured target at runtime.

## 8. R8 discovery/calibration

Frozen chronological split:

```text
R8 discovery   = first 70%
R8 calibration = last 30%
```

Matured-label purge is mandatory:

`max(discovery.observed_at) < min(calibration.source_at)`.

The mechanism densities are fit only on discovery.

The **single confirmation threshold** is selected on R8 calibration as the
highest observed confirmation score that still preserves at least:

`9800 bps terminal detection by the 15m deadline`.

No separate R6/R5 threshold exists.

If no legal R8 threshold reaches 9800 bps preservation, V11 falsifies inside R8
and R6/R5 must not be read scientifically.

## 9. Consumed development gate

The WP-05 gate remains unchanged independently on BOTH R6 and R5:

```text
false structural-failure declaration reduction >= 2000 bps
AND
terminal detection preservation by 15m >= 9500 bps
```

No averaging and no gate weakening.

Mandatory reporting:

- false declarations;
- missed terminals;
- false-declaration reduction;
- terminal preservation;
- p50/p95 confirmation latency;
- confirmations at 3/5/10/15m;
- WATCH / RECOVERY / UNRESOLVED final counts;
- mechanism-support composition at confirmation;
- exact model/representation fingerprints.

## 10. Required comparisons

V11 must report, on the same population:

- source-only V10-style evidence;
- V10 max-checkpoint sequential comparator using R8-frozen V11 mechanism data;
- V11 mechanism-confirmed result.

This comparison is diagnostic only. V11 is judged solely by the frozen WP-05
2000/9500 gate.

## 11. Anti-leakage and anti-retuning

Tests must prove:

- t0 cannot confirm terminal;
- mutating any observation after checkpoint t cannot change state at t;
- persistence uses adjacent frozen checkpoints only;
- mechanism groups are disjoint and frozen;
- mechanism density fitting is R8 discovery only;
- confirmation threshold is R8 calibration only;
- changing R6/R5 cannot change model or threshold fingerprints;
- no trader/setup/symbol shortcut, PnL or trade outcome is used;
- no Shared methodology/sizing/Risk/order/Execution authority exists.

## 12. Deterministic transition after V11

If V11 passes consumed R6 and R5:

- freeze exact V11 identity/code/model/threshold;
- preregister one independent fresh holdout before acquisition.

If V11 fails:

- V11 is permanently falsified;
- no V11.1 or threshold/feature repair;
- classifier iteration over the current OHLC sensor universe stops;
- activate the already prepared Active Perception/new-sensor branch as V12.

## 13. Sovereignty

Shared remains read-only. V11 cannot enter, exit, size, allocate capital,
authorize risk, mutate broker state, alter stops/targets or force/block a Trader.
