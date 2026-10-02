# QORE Shared WP-05 — V13 Sequential Active-Perception Preregistration

**Identity:** `QORE_SHARED_WP05_SEQUENTIAL_ACTIVE_PERCEPTION_V13_001`  
**Target:** `HIGHER_TIMEFRAME_STRUCTURAL_FAILURE_V2`  
**Baseline:** authoritative V11 two-of-three mechanism confirmation  
**New sensor:** cTrader historical USTEC BID/ASK  
**R6/R5:** CLOSED  
**Fresh holdout:** CLOSED

## 1. Scientific transition

V12 source-time active perception is permanently falsified by run
`36479457627`.

V12 tested whether a single causal BID/ASK state at the source timestamp could
act as a bounded veto on V11 terminal confirmation. The complete M0-M3 family
failed its preregistered R8 retention gates. No M4, V12.1, source-time feature
subset, staleness change, threshold rescue or target-aware missingness change is
authorized.

V13 is not a repair of that source-time classifier.

The independent scientific premise comes from the already frozen V10/V11
temporal law: WP-05 is a transition problem and causal evidence is observed at
0/3/5/10/15 minutes. V13 therefore asks a different question:

> Does persistent **sequential** microstructure evidence distinguish temporary
> local recovery from genuine higher-timeframe structural failure better than a
> source-time microstructure snapshot?

## 2. Immutable upstream sensor identity

V13 reuses only the already acquired immutable R8 provider evidence:

- full raw acquisition run: `36454372776`;
- global BID/ASK dataset SHA256:
  `ebbe30a887867bb917f0992b15e1600f9f06eccb07562b9625fcb9517fb381c8`;
- source-anchor run: `36466493930`;
- source-anchor SHA256:
  `d5dda96fbaab9506e77bd803cf8b542250288e7d46091db1630f1fd8fb91839e`;
- source-only integrity run: `36465280823` = GREEN;
- source-only staleness run: `36469085575`;
- frozen staleness: **30,000 ms**;
- frozen microstructure windows: **1s / 5s / 15s / 60s**.

No new provider retrieval is required for R8 because the original acquisition
was preregistered as source t-60m through source t+15m.

## 3. Frozen checkpoints

Exactly:

`0 / 3 / 5 / 10 / 15 minutes`

These are inherited from V10/V11 and are not selected from V12 outcomes.

For source time `s` and checkpoint `c`:

`evaluation_at = s + c`

A checkpoint may consume only provider events satisfying:

`provider_event_at <= evaluation_at`

Future interpolation and nearest-neighbor synchronization remain forbidden.

## 4. Source-only V13 representation freeze

Before any V13 target-aware model may run, build one deterministic row for every
one of the 6,804 frozen R8 source anchors.

At each checkpoint independently compute the exact V12
`M3_FULL_CAUSAL_MICROSTRUCTURE` snapshot fields, but V13 does **not** compare
M0-M3 and does not select a source-time candidate.

The 46 frozen fields per checkpoint are:

- explicit BID/ASK presence/freshness/pair/crossed indicators;
- BID/ASK age and age-skew ratios;
- causal spread;
- per 1s/5s/15s/60s window:
  - BID update rate;
  - ASK update rate;
  - total update rate;
  - update imbalance;
  - BID displacement;
  - ASK displacement;
  - BID path variation;
  - ASK path variation;
  - path-variation asymmetry.

Total scientific trajectory width:

`5 checkpoints × 46 fields = 230 fields`

No new feature may be added after this preregistration.

## 5. Source-only observability gate

For every checkpoint independently:

- causal BID/ASK pair usable coverage must be >= **9500 bps**;
- crossed causal quote count must be reported;
- missing/stale/crossed states remain explicit and are never repaired;
- no target/outcome may participate.

If any checkpoint is below 9500 bps:

`WP05_V13_SEQUENTIAL_REPRESENTATION_REJECTED`

and no V13 target-aware experiment is permitted.

If all five pass, freeze:

- complete 6,804-row trajectory artifact;
- contract fingerprint;
- row SHA256;
- artifact fingerprint;
- per-checkpoint coverage.

## 5A. Authoritative source-only trajectory freeze

The source-only V13 gate is now satisfied by:

- GitHub Actions run: `36480950714`;
- producer Git SHA: `dccbc2a646b9bc41a311db2dfe7b9453d09f4661`;
- artifact id: `10996912676`;
- status: `source_only_frozen`;
- rows: **6,804 / 6,804**;
- per-checkpoint usable coverage bps:
  **9860 / 9695 / 9672 / 9628 / 9603**;
- crossed causal quote counts: **0 / 0 / 0 / 0 / 0**;
- contract fingerprint:
  `4a519c4039a9aa2e5fca4256d2e9551afaf253ac909660ecb8a32be73637837e`;
- rows SHA256:
  `3e3c5dd9bac53902f95f3a6ce0b0aa35685a50b1396789f92e5e73fc1ff8b28a`;
- representation artifact fingerprint:
  `60e05ab6cb5dd38778c8d7055f44026f79b81c86e70cc4f6427c83e0291450ec`.

The V13 R8 target-aware experiment is authorized only against this exact
artifact fingerprint.

## 6. Target-aware V13 representation

V13 has exactly one representation:

`FULL_CAUSAL_MICROSTRUCTURE_TRAJECTORY_V13`

There is no candidate family and no feature selection.

At each checkpoint, one robust class-conditional density is fitted over the 46
frozen checkpoint fields:

- class center = median;
- class scale = max(1e-4, MAD × 1.4826);
- per-feature terminal-vs-nonterminal log-likelihood difference clipped to
  `[-20,+20]`;
- checkpoint microstructure LLR = mean feature LLR.

Null numerical fields are converted to integer zero only after the explicit
missingness indicators remain in the model matrix. No statistical imputation is
allowed.

## 7. Persistent recovery score

Positive microstructure LLR means terminal-supporting evidence. Negative means
nonterminal/recovery-supporting evidence.

For adjacent checkpoints `(t-1,t)` define:

`PAIR_RECOVERY_SCORE(t) = max(LLR(t-1), LLR(t))`

Both adjacent LLRs must therefore be low for the pair score to be low.

For an episode with a V11 confirmation at checkpoint `T`:

`PERSISTENT_RECOVERY_SCORE(T) = min(PAIR_RECOVERY_SCORE(t) for t <= T)`

Only evidence at-or-before the V11 confirmation may participate.

V13 can never create a terminal declaration that V11 did not create.

## 8. Threshold calibration law

The V13 recovery-veto threshold is not fixed from V12 and is not optimized on
false-positive outcomes.

Inside each training population:

1. fit checkpoint densities on chronological discovery only;
2. score chronological calibration;
3. consider only calibration episodes that are true terminals **and** V11
   confirms;
4. select the **largest** observed persistent-recovery threshold that retains at
   least **9800 bps** of those V11 true confirmations.

The threshold therefore uses terminal preservation only. It never selects a
threshold by maximizing false-veto performance.

If calibration contains fewer than **50** true V11 confirmations, the fold fails
closed. This minimum is frozen before V13 target-aware execution.

## 9. V13 decision law

For a V11-confirmed episode at checkpoint `T`:

`V13_TERMINAL = V11_TERMINAL AND PERSISTENT_RECOVERY_SCORE(T) > threshold`

Thus V13 may only veto a V11 terminal confirmation when at least one adjacent
causal microstructure pair up to the V11 decision shows sufficiently persistent
recovery evidence.

V13 never:

- creates a new terminal;
- changes V11 two-of-three mechanisms;
- changes the V11 confirmation threshold;
- changes Target-V2;
- consumes microstructure after the decision checkpoint.

## 10. Chronological R8 validation

Exactly five contiguous chronological blocks are formed over the authoritative
6,397 complete V11 R8 episodes.

Exactly four expanding validation folds are evaluated:

- fold 0: train block 0, validate block 1;
- fold 1: train blocks 0-1, validate block 2;
- fold 2: train blocks 0-2, validate block 3;
- fold 3: train blocks 0-3, validate block 4.

For every fold, any training episode whose matured `observed_at` is not
strictly earlier than the first validation `source_at` is purged.

Within each purged training prefix, chronological discovery/calibration is
**70/30** with another strict target-maturity purge at the split.

Validation is never used to fit density or recovery-veto threshold.

## 11. Frozen information-gain gates

Every validation fold independently must satisfy:

1. V13 terminal-confirmation retention vs V11 >= **9800 bps**;
2. V13 absolute terminal preservation >= **9500 bps**;
3. incremental false-confirmation veto vs V11 > **0 bps**.

Across all four validation folds pooled:

4. incremental false-confirmation veto vs V11 >= **500 bps**.

The 500-bps floor is the same pre-existing WP-05 material-observability floor
used before V12 and is not derived from V13 outcomes.

## 12. Final R8 freeze

If and only if all gates pass:

- fit the exact V13 checkpoint densities and preservation-only threshold on the
  full authoritative R8 population under the same 70/30 discovery/calibration
  law;
- verify the authoritative V11 model fingerprint:
  `cc74f7d3153dec34ebe8867efc27852ca8d5de95d471394f3d8ac9543147b01d`;
- bind the exact V13 source-only trajectory artifact fingerprint;
- emit one final V13 model fingerprint.

Only that exact frozen V13 model may authorize source-only sensor acquisition
for R6/R5.

If any fold fails:

`WP05_V13_SEQUENTIAL_ACTIVE_PERCEPTION_FALSIFIED`

R6/R5 remain closed and no V13.1 threshold/persistence/feature rescue is
permitted from consumed R8 outcomes.

## 13. R6/R5 and holdout law

R6/R5 remain closed during V13 R8 construction and evaluation.

A successful R8 V13 freeze authorizes only source-only BID/ASK acquisition and
representation freezing for R6/R5. Their Target-V2 outcomes may then be opened
once under the unchanged WP-05 gate:

- false structural-failure reduction >= 2000 bps;
- terminal detection preservation >= 9500 bps;
- BOTH R6 and R5 independently.

Fresh WP-05 holdout remains closed until that consumed gate passes.

## 14. Sovereignty

V13 is scientific observation/decision-support research only.

Shared gains no Trader methodology, CIBO sizing/capital, Risk, order or
Execution authority. No LIVE, production, real-capital or merge authority is
created.
