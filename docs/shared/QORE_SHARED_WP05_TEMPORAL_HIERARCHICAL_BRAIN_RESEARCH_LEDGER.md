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
