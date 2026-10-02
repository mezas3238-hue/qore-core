# QORE Shared WP-05 — V10 Causal Sequential Change-Point Preregistration

**Promotion provenance:** This V10 identity promotes the pre-outcome sequential candidate preregistered before the authoritative V9 result. The hypothesis, checkpoints, feature families, calibration law and gates are preserved. Promotion is authorized only because authoritative V9 Causal Trajectory was scientifically falsified.

**Promotion evidence:** authoritative V9 run `36288203952`, Git SHA
`4ab1a248e27c44e3a83abaf7dfde178ca86e14e7`, artifact `10921603629`,
digest `sha256:9a6106c0017b196e69f504891df59ac885a215bd391cdd3befe784bd2fd0e6de`.
V9 status is permanently `WP05_V9_CAUSAL_TRAJECTORY_FALSIFIED`.

**Program:**** QORE Meta-Cognitive Scientific Intelligence  
**PR:** #635  
**Issue:** #643 — WP-05 Temporal Hierarchical Brain  
**Identity:** `QORE_SHARED_WP05_CAUSAL_SEQUENTIAL_CHANGEPOINT_V10_001`  
**Target contract:** `HIGHER_TIMEFRAME_STRUCTURAL_FAILURE_V2`  
**Status:** PREREGISTERED / ACTIVE V10 / PRE-OUTCOME  
**Fresh holdout:** CLOSED  
**Governance:** DRAFT / no LIVE / no production / no real-capital / no merge authority

## 1. Why V10 is structurally different

V3-V8 show a stable frontier:

- aggressive source-time suppression destroys terminal preservation;
- conservative source-time suppression preserves terminals but removes too few false declarations;
- V8's corrected event ontology still found only 146 bps / 214 bps false-declaration reduction on R6/R5 while preserving 9784 bps terminals.

The scientific interpretation is that higher-timeframe structural failure may not be sufficiently observable at the initial source timestamp.

V10 therefore changes the question from:

`classify FAILURE vs RECOVERY at t0`

to:

`detect the earliest causal time at which terminal structural failure becomes sufficiently supported`.

## 2. Frozen hypothesis

Structural failure is a sequential change-point process.

At t0, local opposition may be genuinely unresolved. Shared must be allowed to return `UNRESOLVED` without converting uncertainty into a failure declaration.

New market observations may then move belief toward:

- `TERMINAL_SUPPORTED`;
- `RECOVERY_SUPPORTED`;
- `UNRESOLVED`.

Only observations available at the decision timestamp may be used.

## 3. Online observation schedule

Frozen checkpoints, measured from the source timestamp:

```text
0m
3m
5m
10m
15m
```

The maximum early-warning deadline is **15 minutes**.

No bar after a checkpoint may influence the checkpoint state.

The matured 30-minute future is used only for offline labels/evaluation.

### 3.1 Wall-clock as-of binding clarification

The checkpoint schedule is wall-clock time, not a row-offset contract.

For checkpoint `t = source_at + N minutes`:

- each market consumes the latest **closed** observation whose timestamp is
  `<= t`;
- for N > 0, each market must have produced at least one new observation after
  source time or the episode is incomplete for V10;
- no observation with timestamp `> t` may influence checkpoint-t evidence;
- the NAS100 3-minute velocity anchor consumes the latest closed NAS100
  observation at-or-before `max(source_at, t - 3 minutes)`;
- missing individual M1 rows are therefore handled causally as missing updates,
  never by shifting the decision timestamp or reading a later row.

This clarification changes no feature family, checkpoint, target, model,
threshold or gate. It repairs the implementation of the already-preregistered
phrase “measured from the source timestamp”.

The first promoted V10 consumed attempt (`36318361667`) failed closed at
`R8_SAMPLE_TARGET_GATE_FAILED` before any model fit/calibration and before
scientific R6/R5 access. The failure was traced to an implementation that used
`source_index + N` independently in each feed. Because the three retained M1
feeds have different missing-bar patterns, row offsets do not represent the
same wall-clock checkpoint. No scientific metric from that attempt is accepted.


## 4. Source population

The source population remains:

- WP-05 baseline local-opposition episodes;
- identifiable Target-V2 H1/H4/D1 anchor;
- complete NAS100/SP500/US30 M1 evidence;
- Target V2 structural frontier frozen from the 20 closed NAS100 M1 bars ending at source time.

Neutral higher-timeframe anchors abstain and are excluded from directional evaluation.

## 5. Causal sequential evidence

At each checkpoint V10 derives only causal information available by that checkpoint.

Frozen evidence families:

1. distance of NAS100 close from the fixed source frontier;
2. worst adverse excursion from the fixed frontier observed so far;
3. cumulative signed frontier-distance integral;
4. consecutive closes beyond the frontier;
5. fraction of post-source closes beyond the frontier;
6. count of breach/reclaim transitions;
7. current reclaim distance after worst excursion;
8. current adverse/favorable velocity;
9. realized post-source range expansion relative to the source 20m range;
10. SP500/US30 adverse move since source;
11. peer adverse breadth;
12. peer contradiction/recovery;
13. source-time higher-timeframe fragility/resilience prior;
14. source-time hierarchy propagation/depth prior.

No trader identity, symbol shortcut, setup identity, entry, stop, target, PnL or future market path is permitted.

## 6. Sequential model

V10 fits checkpoint-specific robust class-conditional densities on R8 discovery only:

```text
P(evidence_t | TERMINAL_EVENT)
P(evidence_t | NON_TERMINAL_BY_30M)
```

This does **not** assert that every non-terminal episode is a recovery mechanism.
The negative class exists only for discrimination of terminal early-warning evidence.

For each checkpoint V10 computes a terminal log-likelihood ratio (LLR).

The online state is:

- `TERMINAL_SUPPORTED` if LLR crosses the frozen terminal boundary;
- `RECOVERY_SUPPORTED` only when explicit safe-side reclaim evidence is present and terminal support has not fired;
- otherwise `UNRESOLVED`.

`UNRESOLVED` is a true abstention state and does not declare structural failure.

Once `TERMINAL_SUPPORTED` fires, the detection is absorbing for evaluation.

## 7. R8 discovery/calibration

Frozen chronological split:

```text
R8 discovery   = first 70%
R8 calibration = last 30%
```

Matured-label purge is mandatory:

```text
max(discovery.observed_at) < min(calibration.source_at)
```

Checkpoint density parameters are fitted only on discovery.

The terminal boundary is selected on R8 calibration as the **highest LLR threshold** that preserves at least:

```text
9800 bps of terminal episodes by the 15m deadline
```

This selection maximizes non-terminal abstention subject to the frozen terminal-preservation buffer.

No R6/R5 information may affect the model, threshold, features, checkpoints or deadline.

## 8. Source-time observability diagnostic

V10 must report two separate results:

- `SOURCE_ONLY_0M`;
- `SEQUENTIAL_BY_15M`.

This directly measures whether new causal observations add discrimination.

If sequential evidence does not materially improve over source-only evidence, the result is evidence of an observability/representation ceiling rather than a threshold defect.

## 9. Consumed development gate

The WP-05 gate is unchanged and applies independently on BOTH R6 and R5:

```text
false structural-failure declaration reduction >= 2000 bps
AND
terminal detection preservation by 15m >= 9500 bps
```

No averaging.

Additional mandatory reporting:

- p50 terminal detection latency;
- p95 terminal detection latency;
- terminal detections at 0/3/5/10/15m;
- unresolved count at each checkpoint;
- recovery-supported count;
- false declarations;
- missed terminals.

## 10. Fail-fast law

V10 may be falsified inside R8 if no legal calibration boundary preserves >=9800 bps terminal detection by 15m.

If this happens, R6/R5 must not be read scientifically.

## 11. Fresh holdout

Fresh holdout remains CLOSED.

It may open only if one exact frozen V10 identity passes the consumed R6 and R5 gate.

Before fresh acquisition freeze:

- source code SHA;
- target contract;
- checkpoint schedule;
- feature schema;
- density parameters;
- terminal threshold;
- representation fingerprint;
- model fingerprint;
- holdout window;
- data acquisition protocol;
- gate.

## 12. Anti-leakage invariants

Tests must prove:

- mutating bars after checkpoint t cannot change checkpoint-t evidence;
- mutating bars after 15m cannot change any V10 decision;
- matured target label never appears in runtime evidence;
- neutral anchor abstains;
- R6/R5 cannot be scientifically opened before legal R8 freeze;
- changing R6/R5 cannot alter the R8 model fingerprint;
- source-only and sequential metrics are computed separately;
- model/representation fingerprints are deterministic;
- no methodology/sizing/CIBO/Risk/order/Execution authority exists.

## 13. Scientific interpretation

If V10 passes, freeze exact identity and preregister one independent fresh holdout.

If V10 fails but sequential evidence materially dominates source-only evidence, the next hypothesis may improve the sequential state model without retuning V10.

If V10 fails and sequential evidence does not materially improve source-only discrimination, WP-05 must stop iterating classifiers and escalate to an observability/active-perception redesign.

## 14. Sovereignty

Shared remains read-only and cannot enter, exit, size, allocate capital, authorize Risk, mutate stops/targets or send orders.
