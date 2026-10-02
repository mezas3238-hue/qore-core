# QORE Shared WP-05 — V14 Cross-Market Microstructure Confirmation Preregistration

**Program:** QORE Meta-Cognitive Scientific Intelligence  
**PR:** #635  
**Issue:** #643 — WP-05 Temporal Hierarchical Brain  
**Identity:** `QORE_SHARED_WP05_CROSS_MARKET_MICROSTRUCTURE_CONFIRMATION_V14_001`  
**Target:** `HIGHER_TIMEFRAME_STRUCTURAL_FAILURE_V2`  
**Status:** PREREGISTERED / PRE-OUTCOME  
**R6/R5:** CLOSED  
**Fresh WP-05 holdout:** CLOSED  
**Final Shared certification holdout:** CLOSED  
**Governance:** DRAFT / SHADOW / no LIVE / no production / no real capital / no merge authority

## 1. Scientific authorization

V11 exhausted the NAS100/SP500/US30 OHLC classifier universe and was
scientifically falsified because R5 missed the 2000-bps false-reduction gate by
4 bps.

V12 introduced genuinely new USTEC BID/ASK evidence, but source-time
microstructure destroyed terminal preservation.

V13 tested sequential USTEC BID/ASK and was also falsified:
pooled incremental false-confirmation veto was 466 bps versus a frozen
500-bps materiality floor, with F0/F1 failing terminal-preservation gates.

The post-V13 source-only availability audit
`QORE_SHARED_WP05_POST_V13_SENSOR_AVAILABILITY_AUDIT_001` then proved, without
reading Target-V2 outcomes, R6/R5 or any fresh holdout, exactly one enabled
cTrader DEMO peer candidate per frozen family with full BID+ASK history on the
five temporal pilot windows:

- SP500 peer: provider `US500`, symbol id 10013, digits 2;
- US30 peer: provider `US30`, symbol id 10015, digits 2.

Authoritative availability run: `36493895462`.
Artifact: `11002743011`.

This authorizes one structurally new hypothesis based on cross-market
microstructure. Availability evidence is not scientific admission.

## 2. V14 hypothesis

A genuine higher-timeframe structural failure should not merely look terminal
inside USTEC. At the causal time at which V11 confirms terminality, broad-index
peer microstructure should independently support the same terminal mechanism.

A false NAS100 structural-failure declaration caused by local/idiosyncratic
adversity is expected to show weaker peer-microstructure concordance.

Therefore V14 is a **confirmation veto** over V11:

```text
V11 TERMINAL_CONFIRMED
AND
US500 microstructure supports terminality
AND
US30 microstructure supports terminality
=> V14 retains the V11 declaration

otherwise
=> V14 vetoes the V11 declaration
```

V14 can never create a terminal declaration that V11 did not create.

## 3. New sensor identity

Frozen new provider evidence:

| Peer family | Provider symbol | Provider symbol id | Digits | Canonical instrument |
|---|---|---:|---:|---|
| SP500_PEER | US500 | 10013 | 2 | SP500 |
| US30_PEER | US30 | 10015 | 2 | US30 |

Provider: authenticated cTrader DEMO account already used by V12.

The exact provider account fingerprint, raw symbol identity and full acquisition
hashes must be present in the source-only evidence pack.

If provider symbol identity changes before acquisition, fail closed. Do not
silently remap a symbol.

## 4. Source population and acquisition

V14 reuses the already frozen R8 source-only acquisition manifest:

`2f18b9f11d5893effa46ac85c712edd6646d1d90a9de521b235143e42155d191`

Population:

- 6,804 source anchors;
- 2,948 merged acquisition windows;
- source range 2016-04-20T14:00:00Z through 2018-05-18T19:30:00Z;
- acquisition context source-60m through source+15m.

US500 and US30 BID and ASK are acquired as independent provider-event streams.
No force-pairing by timestamp is permitted.

Full source acquisition must be completed and integrity-audited before any
Target-V2 outcome is opened for V14.

## 5. Checkpoints

Frozen causal checkpoints:

- 0m;
- 3m;
- 5m;
- 10m;
- 15m.

At checkpoint t, only provider events with:

`provider_event_at <= checkpoint_at`

may be consumed.

No future quote may be nearest-neighbor paired backwards into a checkpoint.

## 6. Source-only staleness law

Staleness is not selected from target outcomes.

Candidate grid, frozen now:

- 5s;
- 10s;
- 30s;
- 60s;
- 120s.

One shared cross-market staleness limit is selected as the **smallest** candidate
for which BOTH peers have causal BID+ASK usable coverage >=9500 bps at EVERY
checkpoint.

If no candidate through 120s satisfies that requirement, V14 sensor admission
fails before outcomes and V14 scientific evaluation does not open.

Crossed quotes are INSUFFICIENT and are never repaired.

## 7. Frozen source-only representation

For each peer and each checkpoint, use exactly the already defined V12
`M3_FULL_CAUSAL_MICROSTRUCTURE` field schema:

- quote state/freshness/spread/age;
- update intensity/imbalance over 1s/5s/15s/60s;
- bid/ask displacement and path variation over 1s/5s/15s/60s.

This is 46 fields per peer per checkpoint.

No M0/M1/M2/M3 selection exists in V14. M3 is fixed.

The source-only representation is therefore:

- 2 peers;
- 5 checkpoints;
- 46 fields per peer/checkpoint;
- 460 raw causal feature cells before the scientific density layer.

Missing values remain explicit. No target-aware imputation is allowed.

## 8. Scientific model family

R8 chronological development uses the same robust median/MAD
class-conditional density family already governed in V13, but fits each peer
independently at each checkpoint.

For peer p and checkpoint t:

`LLR_p(t) = log P(M3_p(t) | terminal) - log P(M3_p(t) | nonterminal)`.

The V14 cross-market confirmation score at the exact causal checkpoint T at
which V11 first confirms is:

`PEER_CONFIRMATION(T) = min(LLR_US500(T), LLR_US30(T))`.

The minimum is frozen because both peer mechanisms must agree. No weighted sum,
learned peer weights, majority vote or post-outcome peer selection is allowed.

If a required peer snapshot is insufficient at T, V14 cannot claim peer
confirmation and therefore vetoes the V11 declaration.

## 9. R8 folds and fit law

Frozen inner split:

- discovery = first 70% of each purged outer-training prefix;
- calibration = final 30%;
- matured-label purge requires discovery observed_at < calibration source_at;
- at least 50 true V11 terminal confirmations are required in calibration;
- the retained rule is score >= threshold.


Frozen validation protocol:

- four chronological expanding-window folds;
- each fold fits peer densities using only its past training segment;
- each fold calibrates exactly one peer-confirmation threshold using only the
  true terminals that V11 confirmed in the past calibration segment;
- matured-label chronology/purge must prevent overlap into validation.

The threshold is the highest observed peer-confirmation score that preserves at
least:

`9800 bps`

of V11 true terminal confirmations in calibration.

The threshold may **not** optimize false positives.

No global R8 refit may be chosen after seeing fold results.

## 10. R8 admission gate

Every validation fold must satisfy:

- V14 true-confirmation retention versus V11 >= 9800 bps;
- absolute terminal preservation >= 9500 bps;
- incremental false-confirmation veto > 0.

Pooled across the four validation folds:

- incremental false-confirmation veto >= 500 bps.

All four folds are required. No fold selection or averaging away a failure.

If R8 fails, V14 is permanently falsified and R6/R5 remain CLOSED.

## 11. R6/R5 development gate

Only if R8 passes and the exact representation/model/threshold law is frozen may
R6/R5 source-only peer evidence be acquired.

Then R6 and R5 are opened once under the unchanged WP-05 gate, independently:

```text
false structural-failure declaration reduction >= 2000 bps
AND
terminal detection preservation >= 9500 bps
```

BOTH R6 and R5 must pass.

## 12. Fresh holdout

Fresh WP-05 holdout remains CLOSED until V14 passes R8 and both consumed R6/R5
gates.

If R8, R6 or R5 fails, no fresh evidence is opened.

## 13. Anti-loop law

If V14 fails:

- no V14.1;
- no peer removal;
- no peer weight tuning;
- no min-to-mean/max change;
- no threshold rescue;
- no staleness rescue after outcomes;
- no M3 feature subset mining;
- no checkpoint selection;
- no fold selection;
- no gate lowering;
- no R6/R5 peek to rescue R8.

A subsequent hypothesis must introduce a materially new causal mechanism or
sensor family.

## 14. Sovereignty and anti-leakage

V14 may observe, infer, quantify uncertainty and veto a Shared structural
declaration.

It has no authority over:

- Trader setup/methodology/entry/stop/target;
- sizing or capital;
- CIBO;
- Risk ALLOW/REDUCE/REJECT;
- orders;
- Execution;
- broker mutation;
- position closure.

For every productive fact:

`FACT_TIMESTAMP <= EVALUATION_TIMESTAMP`.

Historical retrieval time remains distinct from provider event time.
