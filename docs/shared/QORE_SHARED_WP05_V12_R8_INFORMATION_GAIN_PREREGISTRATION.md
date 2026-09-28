# QORE Shared WP-05 V12 — R8 Microstructure Information-Gain Preregistration

**Identity:** `QORE_SHARED_WP05_ACTIVE_PERCEPTION_V12_R8_INFORMATION_GAIN_001`  
**Target:** `HIGHER_TIMEFRAME_STRUCTURAL_FAILURE_V2`  
**Baseline architecture:** authoritative V11 two-of-three mechanism confirmation  
**Baseline authoritative run:** `36326684009`  
**Baseline model SHA256:** `cc74f7d3153dec34ebe8867efc27852ca8d5de95d471394f3d8ac9543147b01d`  
**Baseline representation SHA256:** `1f1f2bd97e2f3541c7e37aca5571717a9908618ad1be2b4fce57cb9a09970ce8`  
**R6/R5:** CLOSED  
**Fresh holdout:** CLOSED

## 1. Authorization boundary

This experiment may begin only after the V12 source-only microstructure
representation freeze is GREEN and its exact artifact fingerprint is recorded.

Until that condition is met, R8 target/outcome data remains closed to V12.

The representation itself is immutable during this experiment:

- 6,804 source-only evaluation anchors;
- BID/ASK historical dataset SHA256
  `ebbe30a887867bb917f0992b15e1600f9f06eccb07562b9625fcb9517fb381c8`;
- source-anchor SHA256
  `d5dda96fbaab9506e77bd803cf8b542250288e7d46091db1630f1fd8fb91839e`;
- observability SHA256
  `fb81d247bd710bc0d544bd70c442d2ced7d494b7e2ff66a86aa0cbfb1268bc15`;
- staleness = **30,000 ms**;
- windows = **1s / 5s / 15s / 60s**;
- missingness and deterministic integer normalization exactly as preregistered.

No feature, staleness, sampling or missingness change is permitted after V12
R8 targets are opened.

## 2. Frozen candidate family

Exactly four candidates exist:

1. `M0_QUOTE_STATE`
2. `M1_QUOTE_STATE_UPDATE_INTENSITY`
3. `M2_QUOTE_STATE_PATH_RESPONSE`
4. `M3_FULL_CAUSAL_MICROSTRUCTURE`

No M4, feature rescue or ad-hoc subset may be created from observed R8 results.

Candidate complexity order is frozen as M0 -> M1 -> M2 -> M3.

## 3. Alignment law

The frozen representation rows are joined to Target-V2 episodes only by exact
source/evaluation timestamp.

The join may not use target value, V11 prediction, trader identity, setup
identity, PnL or any future market observation.

Representation-only anchors without a complete matured Target-V2 episode are
reported and excluded from supervised fitting solely because the target is not
defined for them. Target rows without an exact representation row fail closed.

## 4. Missingness matrix law

Every candidate contains the explicit source-quality indicators preregistered in
M0.

Only after those indicators are retained may numerical `null` values be
converted deterministically to integer zero for the scientific model matrix.

No mean/median/statistical imputation, learned imputer or outcome-conditioned
missingness treatment is permitted.

## 5. Microstructure evidence model

Each candidate uses one robust class-conditional density model, structurally
matching the already audited V11 density family.

For every feature independently on training data:

- terminal center = median;
- nonterminal center = median;
- terminal scale = max(1e-4, MAD * 1.4826);
- nonterminal scale = max(1e-4, MAD * 1.4826).

For each feature, terminal-vs-nonterminal log-likelihood difference is clipped
to `[-20,+20]`.

Candidate score is the arithmetic mean of its feature LLRs.

The decision boundary is frozen at:

`microstructure_score >= 0 => NOT_VETOED`  
`microstructure_score < 0  => VETO_V11_CONFIRMATION`

There is **no fitted V12 score threshold**.

This removes threshold mining as a degree of freedom.

## 6. V12 decision architecture

V12 does not replace V11 and cannot create a new terminal declaration.

For an episode:

`V12_TERMINAL = V11_TERMINAL_CONFIRMED AND microstructure_score >= 0`

Therefore V12 can only veto a V11 terminal confirmation when genuinely new
microstructure evidence supports the nonterminal class.

It cannot:

- declare terminal when V11 did not;
- alter V11 checkpoint timing;
- modify the V11 confirmation threshold;
- change the two-of-three V11 mechanism law;
- change Target-V2.

This makes V12 a bounded new-information confirmation/veto layer rather than a
new unconstrained classifier.

## 7. Chronological R8 validation

Candidate admission uses exactly **four expanding-window validations** over five
contiguous chronological blocks of the aligned R8 population.

For validation fold `k = 1..4`:

- validation = chronological block `k`;
- raw training = all blocks strictly before `k`;
- any training episode whose matured `observed_at` is not strictly earlier
  than the first validation `source_at` is purged;
- no future block may enter fitting.

The V11 baseline for each fold is fitted only from that fold's purged training
prefix using the unchanged V11 architecture.

The microstructure density is fitted only on that same purged training prefix.

No validation fold is used to fit its own density or V11 threshold.

## 8. Frozen information-gain gates

For each validation fold report:

- aligned sample count;
- terminal / nonterminal counts;
- V11 true confirmations;
- V11 false confirmations;
- V12 retained true confirmations;
- V12 remaining false confirmations;
- V11 absolute terminal preservation;
- V12 absolute terminal preservation;
- terminal-confirmation retention vs V11;
- incremental false-confirmation veto bps vs V11;
- V12 absolute false-declaration reduction bps.

A candidate is eligible only if **every one of the four folds** satisfies:

1. terminal-confirmation retention vs V11 >= **9800 bps**;
2. absolute V12 terminal preservation >= **9500 bps**;
3. incremental false-confirmation veto is strictly positive.

Across all four validation folds pooled together it must also achieve:

4. incremental false-confirmation veto >= **500 bps**.

The 500-bps material-information floor is inherited from the pre-existing WP-05
material-observability criterion; it is not chosen after seeing V12 outcomes.

## 9. Deterministic candidate selection

Evaluate all four preregistered candidates for reporting.

Select the **lowest-complexity** candidate in frozen order M0 -> M1 -> M2 -> M3
that passes all gates in Section 8.

This is not best-score optimization.

If no candidate passes:

`WP05_V12_R8_INFORMATION_GAIN_FALSIFIED`

R6/R5 remain unopened and no V12.1 feature/threshold rescue is permitted from
the same BID/ASK representation.

## 10. Final R8 model freeze

If one candidate passes:

1. freeze its exact feature list;
2. reconstruct the authoritative V11 full-R8 model and require model fingerprint
   `cc74f7d3153dec34ebe8867efc27852ca8d5de95d471394f3d8ac9543147b01d`;
3. fit the selected microstructure density on the complete aligned R8 training
   population;
4. retain the fixed score boundary at zero;
5. bind the exact source-only representation artifact fingerprint;
6. emit a final V12 model fingerprint.

Only after this final fingerprint exists may R6/R5 sensor acquisition begin.

## 11. R6/R5 boundary after R8 success

R6/R5 target/outcomes remain closed during their sensor acquisition.

For each consumed partition, the same source-only procedure must:

- reconstruct causal source timestamps;
- acquire BID and ASK from the same provider family;
- apply the already frozen 30s staleness;
- apply the already frozen M0-M3 representation contract;
- apply only the single R8-selected candidate.

After exact evidence/representation fingerprints are frozen for R6 and R5,
their Target-V2 outcomes may be opened once.

The unchanged WP-05 development gate remains independently:

- false structural-failure reduction >= **2000 bps**;
- terminal detection preservation >= **9500 bps**.

No averaging across R6/R5.

## 12. Anti-loop law

After any R8 result is observed, forbidden changes include:

- staleness changes;
- window changes;
- adding/removing candidate features;
- score threshold changes;
- candidate M4/M5 creation;
- target changes;
- V11 threshold or mechanism changes;
- target-aware missingness treatment.

A failure requires either a genuinely distinct representation justified without
mining consumed outcomes or a genuinely new information family.

## 13. Sovereignty

This experiment is scientific evidence processing only.

Shared receives no Trader methodology authority, CIBO sizing/capital authority,
Risk authority, order authority or Execution authority.
