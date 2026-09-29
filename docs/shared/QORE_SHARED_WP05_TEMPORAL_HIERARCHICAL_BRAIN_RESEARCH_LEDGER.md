# QORE Shared WP-05 — Temporal Hierarchical Brain Research Ledger

**Program:** QORE Meta-Cognitive Scientific Intelligence  
**Primary PR:** #635  
**Work package:** #643 — WP-05 Temporal Hierarchical Brain  
**Status:** ACTIVE / consumed development  
**Fresh holdout:** CLOSED  
**Governance:** DRAFT / no LIVE / no production / no real-capital / no merge authority

## 1. Scientific question

WP-05 asks whether local adverse pressure is only a recoverable pullback or has
become a genuine higher-timeframe structural failure.

The frozen consumed-development gate is unchanged:

- false structural-failure declaration reduction >= 2000 bps;
- terminal detection preservation >= 9500 bps;
- BOTH R6 and R5 must pass;
- R8 may be used for discovery / fit / chronological calibration only;
- R6 and R5 are consumed falsification only;
- no fresh holdout may open before a frozen candidate passes both consumed gates.

## 1.1 Immutable consumed market partitions

The V6 workflow recovers these retained evidence artifacts and verifies their
embedded SHA256 manifests before use:

| Partition | Artifact ID | Raw M1 coverage (NAS100/SP500/US30) |
| --- | ---: | --- |
| R8 | `10402199719` | 2016-04-19 00:00 UTC -> 2018-05-18 20:55 UTC |
| R6 | `10389112524` | 2018-05-20 22:00 UTC -> 2020-06-17 00:00 UTC |
| R5 | `10380044761` | 2020-06-17 00:00 UTC -> 2022-07-15 20:59 UTC |

All three symbols inside each artifact share the same raw coverage boundaries.
R8 and R6 are separated by a market-closure gap. R6 ends exactly where R5 raw
coverage begins; the WP-05 episode builder requires historical lookback plus a
matured future target, so V6 additionally enforces at the episode level:

```text
R8.target_max < R6.source_min
R6.target_max < R5.source_min
```

Any future evidence replacement that violates this ordered non-overlap gate
fails the V6 protocol closed.

## 2. Immutable experiment chain

### V1 — single-snapshot temporal hierarchy

Authoritative run: `36249925483`  
Git SHA: `f47f4e6079c0154e29b51e9f0bd5f16acd0dac2c`  
Status: `WP05_V1_HIERARCHY_FALSIFIED`

- R6: false reduction 443 bps; terminal preservation 9886 bps.
- R5: false reduction 420 bps; terminal preservation 9861 bps.

Interpretation: strong terminal preservation, insufficient discrimination of
recoverable adversity.

### V2 — temporal propagation

Authoritative run: `36251403048`  
Git SHA: `bc78d90f137cd1cfcb8c204ee1f7819ad3280365`  
Status: `WP05_V2_PROPAGATION_MODEL_FALSIFIED`

- R6: false reduction 270 bps; terminal preservation 9887 bps.
- R5: false reduction 277 bps; terminal preservation 9887 bps.

Mechanism: source-only t-60m -> t-30m -> t propagation / resilience model.

### V3 — semi-Markov hierarchy absorption

Authoritative run: `36255882478`  
Git SHA: `73717a5fad9ad03a9459169c80b305c184b71360`  
Status: `WP05_V3_ABSORPTION_MODEL_FALSIFIED`

- R6: false reduction 1119 bps; terminal preservation 9016 bps.
- R5: false reduction 1110 bps; terminal preservation 8871 bps.

Interpretation: materially more false-declaration reduction, but terminal recall
collapsed below the frozen 95% gate.

### V4 — terminal-safe recovery veto

Authoritative run: `36258021907`  
Git SHA: `25651b0f9017fc24a6b7f57023037424db8b9d64`  
Status: `WP05_V4_RECOVERY_VETO_FALSIFIED`

- R6: false reduction 102 bps; terminal preservation 9878 bps.
- R5: false reduction 115 bps; terminal preservation 9905 bps.

V1-V4 are immutable falsification history of the original M15-oriented terminal
proxy. They must not be retroactively relabeled as Target V2 evidence.

## 3. Target semantics audit

Authoritative activation audit: `36259738096`  
Git SHA: `d7b6830d957a6dee12959236b6cef42d3b162f96`  
Status: `WP05_TARGET_CONTRACT_DIRECTIONALLY_INCONSISTENT`

The old proxy was directionally inverted against the higher-timeframe
structural-failure question on the majority of identifiable baseline episodes:

- R8 inversion: 5452 bps.
- R6 inversion: 5432 bps.
- R5 inversion: 5419 bps.

Therefore the preregistered
`HIGHER_TIMEFRAME_STRUCTURAL_FAILURE_V2` contract became active for new
experiments. V1-V4 remain untouched historical evidence.

Target V2 higher-timeframe anchor:

```text
sign(mean(H1.direction, H4.direction, D1.direction))
```

Target V2 structural frontier:

```text
prior 20 closed NAS100 M1 bars
```

The next 30 closed M1 bars may mature the historical label offline only. Future
market information is forbidden from runtime cognition.

### Neutral-anchor law

`anchor == 0` means directionally unidentifiable.

It must not be interpreted as recoverable, non-terminal or safe. New
recoverable-vs-terminal experiments must abstain/exclude those episodes from
their directionally identified universe and report the count.

## 4. Corrected-target experiments

### Target V2 Absorption V1

Authoritative run: `36262640528`  
Git SHA: `e82491b1f920c885e14e491aaa840abd5fda1047`  
Status: `WP05_TARGET_V2_ABSORPTION_V1_FALSIFIED`

- R6: false reduction 1271 bps; terminal preservation 9307 bps.
- R5: false reduction 1199 bps; terminal preservation 9286 bps.

This approached the discrimination requirement more closely than V1/V2 but
still failed both the 2000-bps reduction gate and the 9500-bps terminal
preservation gate.

### V5 — Target V2 terminal-safe recovery veto

Authoritative run: `36262494942`  
Git SHA: `1d62244a4ee974b06127bfa963d112ec454570bc`  
Status: `WP05_V5_STRUCTURAL_FAILURE_V2_FALSIFIED`

- R6: false reduction 25 bps; terminal preservation 9976 bps.
- R5: false reduction 27 bps; terminal preservation 9985 bps.

Interpretation: extremely terminal-safe, but nearly incapable of separating
recoverable adversity from structural failure.

## 5. V6 — Structural Frontier Survival

Scientific hypothesis:

A model that uses the exact Target V2 structural-price coordinate plus
source-time approach, rejection, adverse persistence, volatility, cross-market
confirmation and hierarchical survival may discriminate recoverable pullbacks
without paying the recall cost seen in V3.

### Pre-outcome corrections

The first V6 implementations produced no authoritative scientific payload due to
technical defects.

A later pre-outcome audit found two semantic implementation defects before any
V6 metric was accepted:

1. exact-neutral H1/H4/D1 anchors were raising an exception instead of
   abstaining;
2. hierarchy depth/recession inherited the V4 `recovery_motif_signature()`
   coordinate, which prioritizes D1 and therefore did not guarantee the same
   anchor as Target V2.

Those defects were corrected before accepting any V6 outcome.

The active representation is:

`STRUCTURAL_FRONTIER_SURVIVAL_V2_FIXED_ANCHOR`

Frozen geometry:

- source anchor = `sign(mean(H1,H4,D1))`;
- anchor zero => abstain;
- structural frontier = prior 20 closed M1 bars;
- one fixed source anchor interprets the entire pre-source causal hierarchy
  trajectory;
- distance / approach / rejection around the exact target frontier;
- local adverse-close persistence;
- 5m/20m volatility ratio;
- SP500 / US30 adverse confirmation at 5m and 15m;
- higher-timeframe resilience minus fragility;
- fixed-anchor hierarchy penetration depth;
- fixed-anchor recession versus advance;
- bounded second-order terms / interactions;
- R8 70% source-time discovery / 30% calibration boundary;
- chronological purge between discovery labels and calibration source: every discovery episode with `observed_at >= first_calibration_source_as_of` is excluded;
- threshold frozen on R8 calibration with >=98% terminal-preservation buffer;
- R6/R5 no refit and no threshold retuning.

Authoritative scientific candidate:
- model/source Git SHA: `f65aeb568a113148017e11429fb0a2370324fe17`;
- first protocol-valid scientific run: `36274152871`;
- clean archival validation Git SHA: `89f13a98ae10dbcbb99cbfa8b9dfb0b9a6a31409`;
- clean archival run: `36282138635`;
- retained artifact: `10919710889`;
- artifact digest:
  `sha256:4583706bb005066ffdda53ca213c60eca453c27d17112640fe66a511a9d3760b`.

Clean archival status: `WP05_V6_STRUCTURAL_FRONTIER_FALSIFIED`.

The corrected workflow passed technically with `protocol_pass=True` and
`development_gate_pass=False`. The archive reproduces the frozen scientific
outcome exactly:

- R8 evaluation: 874 bps false-declaration reduction; 9880 bps terminal
  preservation;
- R6: 888 / 9796 bps;
- R5: 825 / 9897 bps;
- R8 calibration: 911 / 9802 bps;
- frozen model fingerprint:
  `5846796895fbfdb33e0e86f24d87d17b4038f8bfbb55fe3d4a8c45e4d7158396`;
- `purged_discovery_count=0` is valid because discovery labels mature through
  `2017-11-03T19:00:00+00:00` and calibration source begins at
  `2017-11-03T19:30:00+00:00`;
- fresh holdout remained CLOSED.

The GREEN archival workflow is technical evidence integrity, not a scientific
pass. V6 remains permanently falsified and must not be retuned against R6/R5.

## 6. Scientific governance

No WP-05 experiment may:

- weaken the 2000/9500 gate to obtain a pass;
- use R6/R5 to refit or retune the current candidate;
- use future market data at runtime;
- use terminal outcome or PnL as a runtime feature;
- use trader identity, symbol identity or setup identity as a shortcut;
- open fresh holdout before consumed-development pass;
- self-promote research knowledge;
- obtain methodology, sizing, capital-allocation, Risk, order or Execution
  authority.

If V6 fails consumed development, its exact model is frozen as falsification
history and the next experiment must use a materially different structural
hypothesis with a new identity.

## 7. V7 — Competing Survival Hypotheses

Preregistered identity:

`QORE_SHARED_WP05_COMPETING_SURVIVAL_HYPOTHESES_V7_001`

Preregistration commit: `195a05aaaada0a222da6dbb6ed4d729b037c88f2`.

Pre-outcome causal-frontier clarification was frozen before any V7 R6/R5
consumption: exact source distance remains in the Target-V2 coordinate, while
historical breach/reclaim dynamics use the 20 bars strictly preceding each
historical evaluated bar. This prevents a mechanically degenerate "current
breach" feature caused by including the evaluated bar in its own frontier.

Scientific hypothesis:

- terminality and recoverability are competing mechanisms, not opposite ends of
  one scalar;
- one head estimates terminal hazard;
- one head estimates recovery support;
- conflicting or insufficient evidence returns `UNRESOLVED`;
- only `RECOVERY_SUPPORTED` may suppress the baseline structural-failure
  declaration;
- `TERMINAL_SUPPORTED` and `UNRESOLVED` preserve the baseline declaration.

Frozen development protocol:

- R8 = 70% chronological discovery / 30% calibration only;
- matured-label purge is mandatory;
- ridge = 4.0 for both heads;
- terminal/recovery thresholds come only from the preregistered R8 calibration
  grid 0.50..0.90 in 0.02 steps;
- R8 calibration terminal preservation must be >=9800 bps;
- R6/R5 = consumed falsification only, no refit, no threshold retuning and no
  feature selection;
- WP-05 gate remains >=2000 bps false-declaration reduction AND >=9500 bps
  terminal preservation on BOTH R6 and R5;
- fresh holdout remains CLOSED.

Foundation evidence:

- core dual-mechanism foundation GREEN: run `36282492657`, SHA
  `82060ffc89ee283d1278db24c5304aa1d5e3fe69`;
- causal source extractor / anti-future validation GREEN after the lint-only
  repair: run `36282748747`, SHA
  `0354ed3982d0d3ebe3ca6b80a01d80cec8f1acbb`;
- post-fit incomplete-evidence exclusion remained GREEN: run
  `36282793116`, SHA
  `e697cca8186238b548d7ba1765474464f3142915`.

Additional pre-consumption invariants frozen before accepting a V7 outcome:

- canonical historical harness: `scripts/shared_wp05_competing_survival_v7.py`;
- a duplicate V7 historical runner was removed before any accepted consumed
  result so there is one scientific execution path;
- the harness prepares, fits and calibrates R8 first;
- if the R8 sample/target gate fails, R6/R5 are not read by the scientific
  model;
- if no legal R8 threshold pair satisfies the preregistered 9800-bps
  calibration preservation buffer, V7 is falsified at R8 and R6/R5 are not
  read/evaluated by the scientific model;
- only after a legal R8 model + thresholds are frozen may the harness prepare
  R6 then R5 for one-way consumed falsification;
- model and representation fingerprints are retained independently;
- regression tests in
  `tests/infrastructure/test_shared_wp05_competing_survival_v7_protocol.py`
  fail closed if R6/R5 are opened before the legal R8 freeze point;
- immutable R6/R5 artifact download/SHA verification by CI is transport
  validation only and must never be interpreted as model consumption,
  calibration or tuning.

Latest clean pre-consumption foundation evidence at this checkpoint:

- run `36283137659` — GREEN;
- Git SHA `d713bc7e9d491721b052996e0e7ec732a24d5008`;
- dual heads, canonical causal extractor, historical harness static validation,
  R8-only fit/calibration invariants, chronological purge, deterministic
  fingerprint, UNRESOLVED abstention, anti-future leakage and sovereignty tests
  all passed.

No V7 R6/R5 scientific result has been accepted at this ledger checkpoint.
Fresh evidence remains sealed.



### Authoritative V7 result

Authoritative run: `36283312326`  
Git SHA: `771bfe4249987dc299e4e0259e712f7cf4e794ab`  
Status: `WP05_V7_COMPETING_SURVIVAL_FALSIFIED`  
Protocol: PASS  
Development gate: FAIL  
Fresh holdout: CLOSED

Frozen identities:

- model fingerprint:
  `55a1257bf2e924b5dbf56343ecd6f3adc17c061a001b5d45221a880698b6a3a8`;
- representation fingerprint:
  `4e0f92489ca11ec1f0b500edf030c19e18f2caa53220332a4cf5437ea15e5de2`.

V7 failed inside R8 calibration before scientific consumption of R6/R5:

- R8 calibration false-declaration reduction: **9629 bps**;
- R8 calibration terminal preservation: **736 bps**;
- R8 evaluation false reduction: **9626 bps**;
- R8 evaluation terminal preservation: **835 bps**;
- recovery-supported episodes: **6201**;
- unresolved episodes: **333**;
- terminal-supported episodes: **0**;
- incomplete source evidence: **0**.

Interpretation:

The V7 recovery head was trained on the complement of the same matured terminal
label used by the terminal head. The empirical result shows the two heads did
not become independent competing mechanisms: the recovery head dominated almost
the entire R8 population and destroyed terminal preservation.

This identity is permanently falsified. It must not be repaired by threshold
retuning, feature selection or R8/R6/R5 mining. The next experiment must remove
the complement-label dual-head assumption rather than adjust it.


## 8. V8 — Event Manifold with Censoring

Preregistered identity:

`QORE_SHARED_WP05_EVENT_MANIFOLD_WITH_CENSORING_V8_001`

V8 removed the V7 complement-label assumption and introduced explicit offline
states:

- `TERMINAL_EVENT`;
- `VERIFIED_RECOVERY_EVENT`;
- `CENSORED_UNKNOWN`.

The source representation remained frozen from V7 while the model changed to
robust terminal/recovery event manifolds. Censored observations defined neither
manifold and could only be suppressed by explicit high-confidence recovery
support.

### Authoritative V8 result

Authoritative run: `36285517957`  
Git SHA: `0f3e8bc491a09a80f4cfb37f99038599c665da65`  
Status: `WP05_V8_EVENT_MANIFOLD_FALSIFIED`  
Protocol: PASS  
Development gate: FAIL  
Fresh holdout: CLOSED

Artifact:

- artifact id: `10920970525`;
- digest:
  `sha256:2754e34fb92f8d132dc7bdc98eea3f54b11cfb1725af7b0f56f72427e4123ef5`.

Frozen identities:

- model fingerprint:
  `fa2a32ac85ee8d6209b53a8acc6c747b8cd5026a899bae06ac4c5726210cb188`;
- representation fingerprint:
  `261ae682de42ff6c67cd4a60686fa23dd01120bc72218862f7535a5ea26d0f7a`.

R8 calibration:

- false-declaration reduction: **156 bps**;
- terminal preservation: **9838 bps**;
- recovery radius quantile: **2500 bps**;
- recovery advantage margin: **250000 micros**.

Consumed evaluation:

- R8: false reduction **110 bps**, terminal preservation **9875 bps**;
- R6: false reduction **146 bps**, terminal preservation **9784 bps**;
- R5: false reduction **214 bps**, terminal preservation **9784 bps**.

Interpretation:

V8 corrected the event ontology and retained high terminal safety, but its
static source-state manifold was too selective. Most episodes remained
`UNRESOLVED`, so false structural-failure declarations were barely reduced.
The frozen WP-05 gate of >=2000 bps false reduction and >=9500 bps terminal
preservation on BOTH R6 and R5 was not approached.

V8 is permanently falsified. It must not be repaired by radius/margin retuning,
feature mining against R6/R5 or gate weakening. The next hypothesis must test
whether the missing information is in the *causal path into the source state*,
rather than another static geometry around the same source snapshot.


## 9. V9 — Causal Trajectory Discrimination

Authoritative preregistered identity:

`QORE_SHARED_WP05_CAUSAL_TRAJECTORY_DISCRIMINATION_V9_001`

Preregistration:

- commit: `565ae37fa24dcae3cf1f28b07932e744642d07db`;
- timestamp: `2026-09-27T02:07:31Z`;
- document:
  `docs/shared/QORE_SHARED_WP05_V9_CAUSAL_TRAJECTORY_DISCRIMINATION_PREREGISTRATION.md`.

Scientific hypothesis:

V8 showed that explicit event censoring can preserve terminal detections but a
static source-state manifold suppresses too few false structural-failure
declarations. V9 tests whether the discriminating information is contained in
the causal path into the source state.

Frozen representation:

- 30 closed source-time M1 bars ending at the source timestamp;
- six chronological 5-minute blocks;
- exactly 60 features;
- fixed Target-V2 source frontier;
- NAS100 path geometry plus SP500/US30 causal peer motion;
- no bar after source may influence the representation.

Frozen model:

- eventness head: terminal/recovery event families vs censored unknown;
- recovery-contrast head: verified recovery vs terminal event ONLY;
- censored unknowns are excluded from recovery-head normalization and fitting;
- R8 discovery/calibration only;
- maximum false-declaration reduction subject to >=9800 bps R8 calibration
  terminal preservation;
- unchanged consumed gate: >=2000 bps false reduction AND >=9500 bps terminal
  preservation independently on BOTH R6 and R5;
- fresh holdout remains CLOSED.

Pre-consumption technical history:

- initial consumed run `36287907877` failed before evidence recovery because a
  test regex expected different wording for the frozen-R8 exception; 19 other
  tests passed and no scientific payload was produced;
- the assertion text was corrected without changing any feature, parameter,
  label, threshold or gate;
- foundation run `36288084590` is GREEN at
  `c2f0d104ae9ba4c550bc69dad25fdd0f621386fe`;
- the consumed workflow received an isolated concurrency group at
  `4ab1a248e27c44e3a83abaf7dfde178ca86e14e7` so unrelated experiments cannot
  cancel the authoritative V9 run.

### Identity-collision resolution

A second independent hypothesis was preregistered concurrently as
`QORE_SHARED_WP05_CAUSAL_SEQUENTIAL_CHANGEPOINT_V9_001` at commit
`24b57d69c7f05e3cf4ba03863e689c5bcdd89b23` with timestamp
`2026-09-27T02:09:56Z`.

Because the Causal Trajectory V9 preregistration at 02:07:31Z predates it, the
Causal Trajectory identity retains V9 authority.

The later sequential change-point hypothesis is retained as a structurally
distinct **V10 candidate**. It has no authority to produce an accepted V9
scientific result. Its superseded V9 consumed workflow is quarantined
fail-closed.

At this ledger checkpoint, the authoritative isolated Causal Trajectory V9
consumed run is `36288203952`. No scientific conclusion is recorded here
until protocol validation and artifact binding complete.


### Hard discrimination budget

The frozen 2000/9500 gate is also tracked as exact episode budgets on the
authoritative Target-V2 consumed populations. This is diagnostic only and does
not change the gate.

R6:

- baseline false declarations: 5,820;
- baseline terminals: 2,555;
- minimum false suppressions for >=2000 bps reduction: **1,164**;
- maximum missed terminals compatible with >=9500 bps preservation: **127**.

R5:

- baseline false declarations: 6,518;
- baseline terminals: 2,832;
- minimum false suppressions for >=2000 bps reduction: **1,304**;
- maximum missed terminals compatible with >=9500 bps preservation: **141**.

For comparison, V8 produced only:

- R6: 85 false suppressions with 55 missed terminals;
- R5: 140 false suppressions with 61 missed terminals.

Therefore WP-05 requires an order-of-magnitude increase in useful false
suppression without spending terminal-loss budget proportionally. Marginal bps
improvements are not sufficient evidence of structural progress.

### Anti-loop transition law

The experiment transition is deterministic:

1. authoritative V9 is Causal Trajectory Discrimination only;
2. if V9 passes BOTH R6 and R5, freeze exact identity and preregister one fresh
   holdout with no consumed retuning;
3. if V9 fails, freeze artifact/digest/failure mechanism and do not create
   V9.1, threshold repair, feature mining, ridge changes or gate lowering;
4. promote the already reserved sequential change-point hypothesis as a new V10
   identity, preserving its pre-outcome scientific design;
5. if V10 fails without material source-to-sequential observability gain, stop
   classifier iteration and escalate WP-05 to Active Perception / new-sensor
   observability engineering.

Fresh holdout remains CLOSED until the corresponding consumed-development gate
is passed.


### Authoritative V9 result

Authoritative run: `36288203952`  
Git SHA: `4ab1a248e27c44e3a83abaf7dfde178ca86e14e7`  
Status: `WP05_V9_CAUSAL_TRAJECTORY_FALSIFIED`  
Protocol: PASS  
Development gate: FAIL  
Fresh holdout: CLOSED

Frozen identities:

- model fingerprint:
  `54053ab1613a3337b8297aaf27f82a324b8e0fde9a441cdc57778453f9045c2e`;
- representation fingerprint:
  `6d0b918c0925159b83103da75620b0e2c516fe30bc70dc0091735fb167a1ce6c`;
- artifact: `10921603629`;
- artifact digest:
  `sha256:9a6106c0017b196e69f504891df59ac885a215bd391cdd3befe784bd2fd0e6de`.

R8 calibration:

- false-declaration reduction: **99 bps**;
- terminal preservation: **9856 bps**.

Consumed evaluation:

- R8: false reduction **58 bps**; terminal preservation **9958 bps**;
- R6: false reduction **77 bps**; terminal preservation **9863 bps**;
- R5: false reduction **95 bps**; terminal preservation **9844 bps**.

V9 preserved terminal events well but produced even less useful false suppression
than V8. The causal 30m pre-source trajectory therefore did not recover the
missing discrimination. This is evidence against continuing source-time
classifier engineering.

Per the frozen anti-loop law, V9 is permanently falsified. No V9.1, threshold
repair, feature mining, ridge change or gate lowering is permitted.

## 10. V10 — Causal Sequential Change-Point

Promoted identity:

`QORE_SHARED_WP05_CAUSAL_SEQUENTIAL_CHANGEPOINT_V10_001`

Promotion is scientifically authorized by the authoritative V9 falsification.
The sequential hypothesis was preregistered pre-outcome as a reserved candidate
before V9 completed; promotion changes identity/governance only and preserves
its frozen scientific design.

Frozen design:

- checkpoints: 0m / 3m / 5m / 10m / 15m;
- Target-V2 source frontier fixed at source time;
- checkpoint evidence may consume only bars available by that checkpoint;
- terminal detection is absorbing;
- `UNRESOLVED` is a true abstention/no-declaration state;
- source-only and sequential discrimination are reported separately;
- R8 discovery/calibration only;
- R6/R5 consumed falsification only;
- calibration requires >=9800 bps terminal preservation by the 15m deadline;
- WP-05 consumed gate remains >=2000 bps false reduction AND >=9500 bps
  terminal preservation independently on BOTH R6 and R5;
- fresh holdout remains CLOSED.

The purpose of V10 is not another threshold search. It measures whether new
causal observations after source materially increase observability. If V10
fails without material source-to-sequential discrimination gain, classifier
iteration stops and WP-05 escalates to Active Perception / new-sensor
observability engineering.


### Authoritative V10 result

Identity:

`QORE_SHARED_WP05_CAUSAL_SEQUENTIAL_CHANGEPOINT_V10_001`

Authoritative run: `36325040251`  
Scientific Git SHA: `58f06282b393f850ff2a0ddf377f92628ed85685`  
Status: `WP05_V10_CAUSAL_SEQUENTIAL_FALSIFIED`  
Protocol: PASS  
Development gate: FAIL  
Fresh holdout: CLOSED

Frozen identities:

- model fingerprint:
  `0ce2b73a0b4ece5cf74294b8c24138aaeae141d6967b7109ed8e660712f089c3`;
- representation fingerprint:
  `e28ca5c49be817090ddf7c615001246616521fe34055780bb59bd1643632f0b0`;
- artifact: `10934385098`;
- artifact digest:
  `sha256:0ebaf2f595509335c38a8049e3a1058a0b226ee151e9971d4b754de77709e930`.

R8 calibration:

- sequential terminal preservation: **9815 bps**;
- sequential false reduction: **1837 bps**;
- source-only false reduction: **878 bps**.

Consumed evaluation:

- R8: source-only **988/9856** bps reduction/preservation; sequential
  **1717/9830**; incremental observability **+729 bps**;
- R6: source-only **810/9901**; sequential **1537/9810**; incremental
  observability **+727 bps**;
- R5: source-only **814/9883**; sequential **1535/9858**; incremental
  observability **+721 bps**.

Terminal detection latency:

- R8 p50 **0m**, p95 **3m**;
- R6 p50 **0m**, p95 **3m**;
- R5 p50 **0m**, p95 **3m**.

Terminal detections by checkpoint:

- R8: 0m 1554, 3m 223, 5m 41, 10m 22, 15m 13;
- R6: 0m 2128, 3m 282, 5m 48, 10m 29, 15m 4;
- R5: 0m 2386, 3m 300, 5m 67, 10m 31, 15m 8.

Interpretation:

V10 proves that post-source sequential observations contain material new
information: incremental false-declaration reduction exceeds the pre-frozen
500-bps observability criterion independently in R6 and R5 while terminal
preservation remains above 9500 bps.

Therefore the current sensor universe is **not** declared observationally
exhausted. The reserved Active Perception branch does not activate yet.

V10 nevertheless fails the unchanged 2000/9500 WP-05 gate because false
reduction reaches only 1537 bps on R6 and 1535 bps on R5.

The key structural limitation is that V10 declares terminal support when the
maximum checkpoint LLR ever crosses one threshold and then makes that
declaration absorbing. A transient early evidence spike therefore cannot be
downgraded by later contradictory/recovery evidence. The detection distribution
also shows that nearly all useful terminal information arrives by 3-5 minutes,
so merely extending the horizon is not the next hypothesis.

Per the preregistered anti-loop law, V10 is permanently falsified. No V10.1,
threshold repair, density retuning or R6/R5 feature mining is permitted. Exactly
one structurally new sequential-state hypothesis is allowed before escalating
to Active Perception.


## 11. V11 — Sequential Mechanism Confirmation

Preregistered identity:

`QORE_SHARED_WP05_SEQUENTIAL_MECHANISM_CONFIRMATION_V11_001`

Preregistration:

- `docs/shared/QORE_SHARED_WP05_V11_MECHANISM_CONFIRMATION_PREREGISTRATION.md`.

V11 was the single structurally distinct sequential-state experiment authorized
after V10 demonstrated material post-source observability. It did not retune
V10. Instead it required cross-mechanism confirmation before terminal
absorption:

- `FRONTIER_PATH`;
- `CROSS_MARKET`;
- `SOURCE_HIERARCHY_PRIOR`;
- terminal support required 2-of-3 mechanisms plus adjacent-checkpoint
  persistence;
- t0 could not confirm terminal support.

### Authoritative V11 result

Authoritative run: `36326684009`  
Scientific Git SHA: `e75a55e18713b16f7cca507eb9823302811237e6`  
Status: `WP05_V11_MECHANISM_CONFIRMATION_FALSIFIED`  
Protocol: PASS  
Development gate: FAIL  
Fresh holdout: CLOSED

Frozen identities:

- model fingerprint:
  `cc74f7d3153dec34ebe8867efc27852ca8d5de95d471394f3d8ac9543147b01d`;
- representation fingerprint:
  `1f1f2bd97e2f3541c7e37aca5571717a9908618ad1be2b4fce57cb9a09970ce8`;
- artifact: `10934687498`;
- artifact digest:
  `sha256:62757d88a89156fbe64538c3e98e817c35f25cde80019413b1c8cc2fc8a1a8c8`.

R8 calibration:

- false-declaration reduction: **2098 bps**;
- terminal preservation: **9815 bps**;
- frozen confirmation threshold: **-2794577 micros**.

Consumed evaluation:

- R6: false reduction **2070 bps**; terminal preservation **9684 bps**;
- R5: false reduction **1996 bps**; terminal preservation **9745 bps**.

R6 passed the complete frozen gate. R5 failed the false-reduction requirement by
exactly 4 bps. The result is therefore a scientific falsification. No rounding,
threshold repair, mechanism reweighting, feature mining or gate lowering is
permitted.

### Post-V11 anti-loop law

The current NAS100/SP500/US30 OHLC sensor universe is closed for further
classifier iteration:

```text
NO V11.1
NO THRESHOLD PATCH
NO NEW TRANSFORM OF THE SAME OHLC INFORMATION
NO R6/R5 FEATURE MINING
```

The next authorized step is Active Perception: obtain genuinely new causal
sensor information rather than another transform of already-consumed OHLC.

## 12. V12 — Active Perception / New-Sensor Observability

Status: **ACTIVE — SENSOR ADMISSION / HISTORICAL EVIDENCE ENGINEERING**.

Activation cause:

```text
V11 FALSIFIED
→ CURRENT OHLC CLASSIFIER ITERATION CLOSED
→ V12 ACTIVE PERCEPTION ACTIVATED
```

The V12 cTrader historical tick foundation is already technically GREEN:

- foundation run: `36327883783`;
- foundation Git SHA:
  `55e743ee4b264a387f7d3a349bd4b9e1d156fdaf`;
- provider contract:
  `docs/shared/QORE_SHARED_WP05_V12_CTRADER_HISTORICAL_TICK_SENSOR_CONTRACT.md`.

This foundation is infrastructure evidence only. It is not a scientific V12
pass and it did not consume V12 target outcomes.

### Frozen V12 scientific governance

- fresh holdout remains CLOSED;
- R8 is the only partition permitted for sensor information-gain discovery,
  preprocessing selection and representation fitting;
- R6/R5 remain CLOSED for sensor selection and may be opened only once after the
  exact V12 representation is frozen;
- Bid and Ask are independent provider event streams and must not be force-paired
  at identical timestamps;
- provider event time must remain distinct from historical retrieval/core
  ingestion time;
- downloaded historical evidence must never be relabeled as if Core observed it
  live at the historical timestamp;
- spread at evaluation time may use only the latest causal Bid and Ask
  at-or-before that timestamp under a preregistered staleness law;
- no fabricated order-book, implied-volatility, breadth or rate evidence;
- no Trader, CIBO, Risk, order or Execution authority.

The immediate engineering task is to create an explicit historical quote-side
evidence boundary that preserves provider-event provenance before any R8
historical BID/ASK dataset is admitted.


### V12 provider-history coverage pilot — preregistered

Before accepting any valid cTrader historical-coverage result, the following
pilot is frozen:

- identity:
  `QORE_SHARED_WP05_ACTIVE_PERCEPTION_V12_COVERAGE_PILOT_001`;
- preregistration:
  `docs/shared/QORE_SHARED_WP05_V12_PROVIDER_HISTORY_COVERAGE_PILOT_PREREGISTRATION.md`;
- upstream R8 source-only acquisition-manifest SHA256:
  `2f18b9f11d5893effa46ac85c712edd6646d1d90a9de521b235143e42155d191`;
- deterministic temporal sample:
  FIRST / Q1 / MID / Q3 / LAST manifest ordinal;
- sensor modality:
  cTrader DEMO `USTEC` historical BID + ASK;
- no target/outcome, R6, R5 or fresh holdout may influence selection.

Disposition is frozen pre-outcome:

- FULL BID+ASK history across the temporal pilot authorizes full R8 acquisition
  without target inspection;
- PARTIAL history requires source-only coverage/missingness characterization
  before any scientific sensor admission;
- NO history rejects this cTrader historical modality and returns Active
  Perception to another genuinely new sensor/provider family;
- TECHNICAL failure is repair-and-rerun under the exact same pilot identity.

A coverage pass is still not V12 scientific admission and does not close WP-05.

### Authoritative V12 completion and final disposition — 28-SEP-2026

The Active Perception BID/ASK branch completed its source-only evidence chain
before any target-aware scientific test:

- coverage pilot run 36452997906: full_bid_ask_history on deterministic
  FIRST/Q1/MID/Q3/LAST windows; BID 50,200; ASK 50,307; dataset SHA256
  06a145f763145eac5121878d4aa81c8c11bae86ea5a865eed9a7d6f5621d23e6;
- full R8 acquisition run 36454372776: 16/16 shards, 2,948/2,948
  manifest windows, BID 13,603,333, ASK 13,593,775, 6,781 provider pages,
  global dataset SHA256
  ebbe30a887867bb917f0992b15e1600f9f06eccb07562b9625fcb9517fb381c8;
- source-only raw-integrity run 36465280823:
  green_source_integrity with zero page-key duplicates, zero page-key conflicts,
  zero strict page-time overlaps and zero exact boundary-row repeats;
- source-anchor run 36466493930 froze the 6,804 causal source anchors;
- anchor-observability run 36469085575 froze staleness at 30,000 ms as the
  smallest preregistered threshold with at least 9,500 bps usable coverage;
- source-only representation run 36474746502 froze exactly M0/M1/M2/M3,
  6,804 rows, 6,709 usable causal pairs, contract fingerprint
  22c566501246030218be3d33ba54c3b6cc1574507357248e3baf0fcf6e47277b
  and representation artifact fingerprint
  cbc5b6d997c2a218df8aa76f489d408069ab36e4ccb67569172c92013221baf8.

Authoritative target-aware V12 result:

- run: 36479457627;
- scientific Git SHA:
  b5b0dbe5d02a22def076574a236eb7632b9a75cb;
- status: WP05_V12_R8_INFORMATION_GAIN_FALSIFIED;
- aligned Target-V2 population: 6,397;
- fixed microstructure veto threshold: 0 micros;
- selected candidate: none;
- R6/R5 read: false;
- fresh holdout opened: false.

Pooled false-veto was large for every frozen source-time family, but terminal
retention failed badly in the chronological folds. The sensor therefore carried
information, but the source-time representation could not separate recovery
from true terminal failure while preserving terminals.

Permanent V12 anti-loop law:

- no V12.1;
- no M4;
- no post-outcome threshold rescue;
- no target-aware feature subset;
- no staleness retune;
- no target-aware missingness change;
- no R6/R5 opening.

V12 is permanently falsified.

## 13. V13 — Sequential Active Perception

Preregistered identity:

QORE_SHARED_WP05_SEQUENTIAL_ACTIVE_PERCEPTION_V13_001

V13 was a structurally distinct question, not a V12 repair. It inherited the
already frozen V10/V11 causal checkpoints 0/3/5/10/15 minutes and asked whether
persistent BID/ASK trajectory evidence could veto false V11 terminal
confirmations without destroying true terminals.

Exactly one representation was permitted:

FULL_CAUSAL_MICROSTRUCTURE_TRAJECTORY_V13

It contained 5 checkpoints x 46 frozen fields = 230 fields. No M0-M3 selection,
feature search or post-outcome sensor change was permitted.

### Authoritative V13 source-only freeze

Run: 36480950714
Git SHA: dccbc2a646b9bc41a311db2dfe7b9453d09f4661
Artifact: 10996912676
Status: source_only_frozen

- rows: 6,804 / 6,804;
- usable pair counts: 6,709 / 6,597 / 6,581 / 6,551 / 6,534;
- usable coverage bps: 9,860 / 9,695 / 9,672 / 9,628 / 9,603;
- crossed causal quotes: 0 / 0 / 0 / 0 / 0;
- contract fingerprint:
  4a519c4039a9aa2e5fca4256d2e9551afaf253ac909660ecb8a32be73637837e;
- rows SHA256:
  3e3c5dd9bac53902f95f3a6ce0b0aa35685a50b1396789f92e5e73fc1ff8b28a;
- representation artifact fingerprint:
  60e05ab6cb5dd38778c8d7055f44026f79b81c86e70cc4f6427c83e0291450ec;
- target/outcome read: false;
- R6/R5 read: false;
- fresh holdout opened: false.

### Authoritative V13 scientific result

Run: 36481988189
Git SHA: 9426924faaf7e654aa31502472188ed98e3134e0
Status: WP05_V13_SEQUENTIAL_ACTIVE_PERCEPTION_FALSIFIED

- aligned Target-V2 population: 6,397;
- V11 model fingerprint:
  cc74f7d3153dec34ebe8867efc27852ca8d5de95d471394f3d8ac9543147b01d;
- V13 representation fingerprint:
  60e05ab6cb5dd38778c8d7055f44026f79b81c86e70cc4f6427c83e0291450ec;
- pooled incremental false-confirmation veto: 466 bps;
- preregistered materiality floor: 500 bps.

Fold outcomes:

- F0: retention 9,164; absolute terminal 9,000; false veto 887 — FAIL;
- F1: retention 9,535; absolute terminal 9,407; false veto 478 — FAIL;
- F2: retention 9,941; absolute terminal 9,658; false veto 118 — PASS;
- F3: retention 9,895; absolute terminal 9,768; false veto 386 — PASS.

Two of four folds failed and pooled materiality missed the frozen floor by
34 bps. Near-pass semantics, rounding and rescue are forbidden.

Permanent V13 anti-loop law:

- no V13.1;
- no threshold change;
- no persistence-formula change;
- no feature add/remove;
- no fold selection;
- no calibration-split change;
- no gate lowering;
- no R6/R5 opening;
- no fresh-holdout opening.

V13 is permanently falsified.

## 14. Post-V13 transition — source availability before any V14

WP-05 remains ACTIVE and NOT CLOSED.

Consumed sensor universes now include:

1. NAS100/SP500/US30 OHLC mechanism/trajectory information through V11;
2. USTEC source-time BID/ASK through V12;
3. USTEC sequential BID/ASK through V13.

The next authorized action is not another classifier and is not V14 outcome
work. It is a source-only sensor-availability audit for genuinely new
information.

The first audited path is cross-market microstructure:

- cTrader DEMO enabled-symbol catalogue;
- SP500-equivalent BID/ASK candidates;
- US30-equivalent BID/ASK candidates;
- deterministic historical probes at the already frozen
  FIRST/Q1/MID/Q3/LAST R8 source-manifest windows;
- provider-event evidence only;
- no target/outcome read;
- no R6/R5 read;
- no fresh holdout;
- no scientific candidate selection from performance.

The preregistration is:

docs/shared/QORE_SHARED_WP05_POST_V13_SENSOR_AVAILABILITY_AUDIT_PREREGISTRATION.md

Only an unambiguous, replayable provider sensor can become the subject of a
later V14 scientific preregistration. Source availability does not itself
constitute V14, scientific admission or WP-05 progress against the 2000/9500
gate.

## 15. V14 — Cross-Market Microstructure Confirmation

Post-V13 source availability was audited before defining any new scientific
candidate.

Authoritative source-availability run:

- run: 36493895462;
- Git SHA: 54521667936a123f5eac305d3be430fe34551564;
- artifact: 11002743011;
- enabled cTrader DEMO symbols: 177;
- USTEC control present: true;
- frozen temporal pilot: manifest indices 0 / 736 / 1473 / 2210 / 2947;
- SP500 peer: exactly one candidate, US500, symbol id 10013, digits 2;
- US500 pilot coverage: full_bid_ask_history;
- US500 pilot totals: BID 11,397 / ASK 11,533;
- US30 peer: exactly one candidate, US30, symbol id 10015, digits 2;
- US30 pilot coverage: full_bid_ask_history;
- US30 pilot totals: BID 37,012 / ASK 37,399;
- target/outcome read: false;
- R6/R5 read: false;
- fresh holdout opened: false;
- V14 scientific outcomes opened: false.

This availability audit proved that cross-market microstructure is a real,
historically replayable sensor family. It did not constitute scientific PASS.

### Frozen V14 hypothesis

Identity:

QORE_SHARED_WP05_CROSS_MARKET_MICROSTRUCTURE_CONFIRMATION_V14_001

V14 can only veto a V11 terminal confirmation. It can never create one.

At the exact causal checkpoint where V11 first confirms terminality:

PEER_CONFIRMATION(T) = min(LLR_US500(T), LLR_US30(T))

Both peers therefore must support terminality.

Frozen sensor universe:

- US500 BID/ASK;
- US30 BID/ASK;
- checkpoints 0 / 3 / 5 / 10 / 15m;
- M3_FULL_CAUSAL_MICROSTRUCTURE only;
- 46 fields per peer/checkpoint;
- 460 raw causal cells per source row;
- provider-event-at <= checkpoint only;
- independent BID/ASK as-of streams;
- no force-pairing.

Frozen source-only staleness grid:

5s / 10s / 30s / 60s / 120s

Selection law:

choose the smallest one shared threshold for which BOTH peers satisfy >=9500
bps causal BID+ASK usable coverage at EVERY checkpoint.

If no threshold through 120s passes, V14 stops before outcomes.

Frozen scientific protocol:

- 4 chronological expanding-window validation folds;
- outer matured-label purge;
- inner discovery/calibration = 70% / 30%;
- strict matured-label purge between discovery and calibration;
- robust median/MAD terminal-vs-nonterminal density per peer/checkpoint;
- 10 densities = 2 peers x 5 checkpoints;
- minimum 50 true V11 confirmations in calibration;
- one peer-confirmation threshold only;
- threshold selected only from true V11 terminal confirmations;
- calibration retention >=9800 bps;
- retained declaration iff PEER_CONFIRMATION >= threshold;
- no false-positive optimization during threshold calibration.

R8 fold gates:

- V14 true-confirmation retention vs V11 >=9800 bps;
- absolute terminal preservation >=9500 bps;
- incremental false-confirmation veto >0.

R8 pooled gate:

- incremental false-confirmation veto >=500 bps.

All four folds are required.

### Acquisition lineage

The first acquisition run 36494671881 at
a4b38555df77443f6c82d2539d9cb8674ff25ac6 is SUPERSEDED.

Reason:

the scientific evaluator was further preregistered/frozen before any V14
outcome was opened. Updating the preregistration document legitimately
re-triggered acquisition under workflow concurrency.

Never combine artifacts from the superseded run with the replacement lineage.

Authoritative replacement source acquisition:

- run: 36501289744;
- preregistration/source SHA:
  b8cae94dec9028acb5230cb25b034bc25040b920;
- target/outcome: CLOSED;
- R6/R5: CLOSED;
- fresh WP05 holdout: CLOSED.

Scientific evaluator contract validation completed GREEN before outcome opening.

The next legal sequence remains:

1. exact 32-shard source acquisition;
2. raw peer integrity audit;
3. shared cross-peer staleness freeze;
4. M3 source-only representation freeze;
5. freeze exact representation fingerprint;
6. only then open R8 Target-V2 outcomes once.

No V14.1 or post-outcome rescue is authorized.

## 16. V14 final — source-admission falsification

Identity:

`QORE_SHARED_WP05_CROSS_MARKET_MICROSTRUCTURE_CONFIRMATION_V14_001`

The authoritative source acquisition completed successfully:

- acquisition run: `36501289744`, attempt 2;
- scientific/source SHA:
  `b8cae94dec9028acb5230cb25b034bc25040b920`;
- global reduction artifact: `11010831194`;
- source-freeze run: `36516454382`;
- source-freeze artifact: `11011118662`;
- observability SHA256:
  `e94239fe9f60089a06994b77f4754e2dfb1dc41e9fd679969b8d648bdddfa24a`.

After correcting the pre-outcome pagination-order audit defect, both raw peer
datasets passed exact source integrity:

- SP500_PEER / US500: 5,959 pages, 3,152,794 BID, 3,148,120 ASK,
  duplicate/conflict/strict-overlap/boundary-repeat = 0/0/0/0;
- US30_PEER / US30: 6,376 pages, 10,731,151 BID, 10,729,451 ASK,
  duplicate/conflict/strict-overlap/boundary-repeat = 0/0/0/0.

The frozen source-only staleness grid was evaluated exactly:

5s / 10s / 30s / 60s / 120s.

No shared threshold satisfied >=9500 bps causal BID+ASK usable coverage for
BOTH peers at EVERY checkpoint.

At the maximum preregistered 120s threshold:

- SP500_PEER @ 0/3/5/10/15m:
  9994 / 9397 / 9281 / 9169 / 9178 bps;
- US30_PEER @ 0/3/5/10/15m:
  10000 / 9967 / 9967 / 9961 / 9936 bps.

Therefore:

- observability status = `source_only_rejected`;
- selected shared staleness = none;
- M3 V14 representation was not frozen;
- Target-V2 R8 outcomes were never opened;
- R6/R5 remained CLOSED;
- fresh holdout remained CLOSED.

V14 is permanently falsified at source admission. No V14.1, peer removal,
staleness extension, checkpoint rescue, source-gate lowering or R6/R5 peek is
authorized.

## 17. Post-V14 transition — full provider catalogue before V15

WP-05 remains ACTIVE and NOT CLOSED.

The next legal action is not an US30-only V14 rerun and is not V15 outcome
work. It is a provider-catalogue audit that persists the complete enabled
cTrader DEMO symbol universe with exact provider names and IDs.

Preregistration:

`docs/shared/QORE_SHARED_WP05_POST_V14_PROVIDER_CATALOG_AUDIT_PREREGISTRATION.md`

Frozen laws:

- provider catalogue only;
- no historical market-data query;
- no candidate selection;
- no target/outcome;
- no R6/R5;
- no fresh holdout;
- no V15 scientific identity yet.

Only after this catalogue is frozen may a genuinely new sensor family be
nominated by economic/market semantics and subjected to a separate source-only
historical availability audit before any V15 scientific preregistration or
outcome access.
