# QORE Shared WP-05 V12 — Provider History Coverage Pilot Preregistration

**Program:** QORE Meta-Cognitive Scientific Intelligence  
**PR:** #635  
**Issue:** #643  
**Identity:** `QORE_SHARED_WP05_ACTIVE_PERCEPTION_V12_COVERAGE_PILOT_001`  
**Status:** PREREGISTERED / R8 SOURCE-ONLY / OUTCOME-BLIND  
**Fresh holdout:** CLOSED

## 1. Purpose

Before spending the full V12 acquisition budget, determine whether the
authenticated cTrader DEMO provider retains historical BID and ASK events for
the frozen R8 source-era contexts required by WP-05.

This is an observability/coverage experiment, not a target-performance
experiment and not scientific sensor admission.

## 2. Frozen upstream manifest

The pilot is bound to the already source-only R8 acquisition manifest:

- identity:
  `QORE_SHARED_WP05_ACTIVE_PERCEPTION_V12_ACQUISITION_MANIFEST_001`;
- manifest SHA256:
  `2f18b9f11d5893effa46ac85c712edd6646d1d90a9de521b235143e42155d191`;
- source population: 6,804;
- merged source-context windows: 2,948;
- provider symbol identity requested: `USTEC`;
- context per source: t-60m through t+15m;
- no matured target/outcome was used to select windows.

Any manifest digest drift invalidates this pilot run.

## 3. Outcome-blind temporal selection

The pilot may inspect exactly five manifest positions when the manifest is
large enough:

```text
FIRST
Q1
MID
Q3
LAST
```

The exact integer indices are derived only from manifest ordinal position:

```text
0
(last // 4)
(last // 2)
((3 * last) // 4)
last
```

Duplicate indices are removed only for very small manifests.

No terminal label, recovery label, Trader PnL, trade outcome, R6, R5 or fresh
holdout may influence the selected windows.

## 4. Provider acquisition law

For each selected manifest window:

1. authenticate only to cTrader DEMO;
2. preserve explicit DEMO account classification;
3. resolve the exact enabled `USTEC` provider identity and digits;
4. pass all provider calls through
   `CTraderHistoricalReadOnlyMessageClient`;
5. request BID and ASK independently;
6. split any request interval to <=7 days;
7. paginate strictly backward while `hasMore=true`;
8. stay below the 5 historical requests/second connection limit;
9. preserve provider-event timestamp separately from retrieval time;
10. retain each page as an immutable quote-side shard before any analysis.

The existing repository trading-scope token may be used only behind the
read-only message firewall. This does not create order authority.

## 5. Measurements

For every pilot window report independently:

- BID tick count;
- ASK tick count;
- BID page count;
- ASK page count;
- first/last provider event timestamp per side;
- longest within-request quote-side gap;
- duplicate/conflict count;
- immutable shard count;
- content dataset SHA256.

The public issue report must remain sanitized and must not expose credential
material or the raw cTrader account id.

## 6. Frozen disposition rule

### FULL_BID_ASK_HISTORY

Every selected temporal window contains at least one BID and at least one ASK.

Disposition:

- provider historical modality remains viable;
- authorize full R8 acquisition using the already frozen 2,948-window manifest;
- do not read target outcomes yet.

### PARTIAL_BID_ASK_HISTORY

At least one pilot window contains provider history, but not every selected
window contains both sides.

Disposition:

- do not open target outcomes;
- do not immediately reject the sensor;
- first quantify source-only temporal coverage/missingness and determine whether
  an admissible R8 population can be frozen without target-aware selection.

### NO_HISTORY

No selected window contains BID or ASK history.

Disposition:

- reject cTrader historical ticks as the current V12 historical sensor source;
- do not retune the pilot;
- remain in Active Perception and move to another genuinely new sensor family
  or provider modality.

### TECHNICAL FAILURE

Authentication, protocol, CI, parsing, rate-limit implementation, artifact or
other technical failure before a valid report.

Disposition:

- fix the technical defect;
- rerun the exact same pilot identity/manifest/selection rule;
- no scientific conclusion may be drawn from the failed technical run.

## 7. Isolation

Throughout the pilot:

- R6 remains CLOSED;
- R5 remains CLOSED;
- WP-05 fresh holdout remains CLOSED;
- final 2Y Shared certification holdout remains untouched;
- no target/outcome is read;
- no feature selection occurs;
- no staleness threshold is selected;
- no Shared methodology, sizing, capital, Risk, order or Execution authority is
  introduced.

## 8. Next lawful step

Only after a valid coverage disposition is frozen may the next V12 acquisition
or sensor-family step be preregistered.
