# Turtle Soup Candidate R1 — Classic + Plus One Loss Forensics Freeze

Status: **FROZEN BEFORE LOSS-CAUSE INTERPRETATION**

Research identity: `turtle-soup-candidate-r1`

Canonical trader code: `CODE_UNASSIGNED`

PR: #553

This document freezes how QORE will investigate losing trades from Turtle Soup Classic and Turtle Soup Plus One. Forensics is diagnostic research only. It may explain losses; it may not silently optimize the strategy, rewrite source rules, consume the protected fresh OOS, or grant FTMO/FundedNext/LIVE authority.

## 1. Required sequencing

Classic and Plus One are treated as two independent forensic populations.

The required sequence is:

`SOURCE-FAITHFUL ENTRY/INITIAL STOP -> FROZEN EXPERIMENTAL MANAGEMENT -> DEVELOPMENT ECONOMIC REPLAY -> LOSS FORENSICS -> CAUSE ADJUDICATION -> CONFIGURATION DECISION -> WALK FORWARD / FRESH VALIDATION`

A losing population does **not** proceed directly to parameter tuning.

Forensics must first determine whether observed losses are predominantly caused by:

1. source-method behavior that is economically weak in the observed market state;
2. QORE experimental management;
3. execution/cost assumptions;
4. causal-data ambiguity or missing evidence;
5. an implementation defect;
6. concentration in a market, side, calendar period, or volatility state.

## 2. Variant isolation

### Classic

Classic losses are analyzed only against the four already-frozen policies:

- `C_TRAIL1_H3`
- `C_TRAIL2_H3`
- `C_TRAIL1_H6`
- `C_TRAIL2_H6`

No additional Classic trail, target, entry offset, re-entry behavior, or filter may be introduced during forensic diagnosis.

### Plus One

Plus One losses are analyzed only against the six already-frozen policies:

- `P_B2_F50_TRAIL1_H10`
- `P_B2_F50_TRAIL2_H10`
- `P_B4_F50_TRAIL1_H10`
- `P_B4_F50_TRAIL2_H10`
- `P_B6_F50_TRAIL1_H10`
- `P_B6_F50_TRAIL2_H10`

No additional partial fraction, partial bar, trail, target, horizon, or filter may be introduced during forensic diagnosis.

## 3. Per-trade forensic record

Every closed losing trade must preserve at minimum:

- variant (`classic` or `plus-one`);
- policy ID and policy fingerprint;
- symbol and side;
- source signal timestamp;
- fill timestamp and fill price;
- source reference price and age;
- entry trigger;
- initial stop;
- initial risk in price units;
- exit timestamp, exit price, exit reason and holding bars;
- gross R;
- primary-cost net R;
- stress-cost net R;
- transaction-cost R drag;
- maximum favorable excursion (MFE) in R before exit;
- maximum adverse excursion (MAE) in R before exit;
- whether price ever reached +0.25R, +0.50R, +1.00R and +2.00R before the realized loss;
- whether the active stop was the initial source stop or an experimental trailing stop;
- whether a gap-through stop fill occurred;
- causal evidence quality and any ambiguity/censorship flags;
- market/year/side/fold membership.

For Plus One additionally record:

- scheduled partial bar;
- whether the partial executed;
- partial price and realized partial R when executed;
- whether the remaining balance later stopped;
- whether the scheduled partial was skipped because it was not profitable.

## 4. Frozen single-trade cause taxonomy

Exactly one **primary** cause and zero or more secondary contributors are assigned from the following taxonomy. Classification must be driven by observable replay state; unknown cases remain `UNRESOLVED` rather than being guessed.

### Data / implementation

- `INVALID_EVIDENCE`
- `CAUSAL_PATH_AMBIGUITY`
- `DATA_RESOLUTION_LIMITATION`
- `IMPLEMENTATION_DEFECT`
- `PROVENANCE_MISMATCH`

A trade with any of these as a material unresolved cause is not admissible as economic evidence until repaired/replayed.

### Source-entry / market response

- `IMMEDIATE_ADVERSE_CONTINUATION` — source-valid fill is followed by adverse movement without meaningful favorable excursion.
- `FAILED_REVERSAL_AFTER_RECOVERY` — reversal entry occurs and price initially moves favorably, but the reversal fails before management creates a protected gain.
- `GAP_ADVERSE_AFTER_ENTRY` — adverse gap materially worsens the source/QORE stop fill.

These categories diagnose source-pattern behavior; they do not authorize changing source rules.

### Experimental management

- `TRAIL_TOO_TIGHT_RELATIVE_TO_OBSERVED_PATH` — trade achieved favorable excursion, then an experimental trail exits at a loss while the initial source stop had not been hit at that instant.
- `TIME_EXIT_NEGATIVE` — frozen hard time exit realizes a loss before any protective stop.
- `PARTIAL_SKIPPED_THEN_LOSS` — Plus One scheduled partial is skipped under the frozen rule and the position later loses.
- `PARTIAL_TAKEN_BALANCE_LOSS` — Plus One realizes a profitable partial, but the remaining balance loses enough to make the whole trade net negative.
- `INITIAL_STOP_LOSS` — the active stop at loss exit is still the source initial stop; no experimental trail caused the exit.

`TRAIL_TOO_TIGHT_RELATIVE_TO_OBSERVED_PATH` is a diagnostic label only. It does not authorize widening the trail. Any such change would require a separately preregistered hypothesis and new validation.

### Execution / cost

- `COST_ERASED_GROSS_EDGE` — gross R is positive but primary-cost net R is non-positive.
- `COST_AMPLIFIED_LOSS` — trade is already gross-negative and transaction cost materially deepens the loss.
- `GAP_THROUGH_STOP_EXECUTION` — conservative QORE gap execution worsens the realized stop relative to the active stop level.

### Residual

- `UNRESOLVED`

## 5. Population-level forensic questions

Classic and Plus One must each answer:

1. What fraction of losses are initial-stop losses versus experimental-management losses?
2. How many losing trades had MFE >= +0.25R, +0.50R, +1R and +2R before ending negative?
3. Which frozen policies preserve favorable excursion best without hindsight?
4. Are losses concentrated by symbol, side, fold, year, volatility state, entry gap, reference age, or holding duration?
5. Does a single market/side/year explain a majority of negative R?
6. Does transaction cost change the sign of otherwise profitable trades?
7. Are Classic and Plus One failing for the same reason or for structurally different reasons?
8. Are differences between one-bar and two-bar trails causal and persistent across folds, or isolated to a small sample?
9. For Plus One, is loss behavior dominated by skipped partials, balance-after-partial losses, or initial-stop losses?
10. Are any losses actually artifacts of data/provenance/implementation and therefore inadmissible?

## 6. Counterfactual discipline

Forensics may compare only counterfactuals that were already frozen **before** outcomes:

- the four Classic policies against the same Classic source fills;
- the six Plus One policies against the same Plus One source fills;
- primary 1 bp cost versus frozen 2 bp stress;
- initial-stop path versus the actually activated frozen experimental trail state.

Forensics may **not** search arbitrary new targets, filters, stops, indicators, session windows, market subsets, re-entry rules, or parameter values and then report the best retrospective result.

## 7. Post-forensics adjudication

Each variant receives one of four outcomes:

- `IMPLEMENTATION_REPAIR_REQUIRED` — evidence shows a software/data/provenance defect. Repair, rerun the identical frozen experiment, then repeat forensics.
- `MANAGEMENT_HYPOTHESIS_REQUIRED` — source entry appears viable but losses are materially induced by QORE experimental management. A new management hypothesis may be proposed only with causal rationale and preregistration; it must restart development validation and cannot reuse fresh OOS for tuning.
- `SOURCE_METHOD_ECONOMIC_WEAKNESS` — losses arise mainly from source-valid setups reaching the source initial stop without sufficient favorable excursion. Do not disguise this with post-hoc filters; reject or retain only as an explicitly new hypothesis requiring independent validation.
- `FORENSICALLY_ACCEPTABLE` — loss distribution is compatible with a positive, robust edge under the frozen advancement gate. The variant may proceed to configuration freeze / Walk Forward according to governance.

Classic and Plus One are adjudicated independently. One may advance while the other is rejected.

## 8. Fresh OOS remains closed

`FRESH_OOS_ACCESS = PROHIBITED`

Loss forensics uses development evidence only. No bar with `opened_at >= 2026-03-01T00:00:00Z` may influence diagnosis, management selection, market selection, or hypothesis formation before a configuration is frozen.

## 9. Required forensic deliverable

The forensic report must contain:

- Classic loss-cause matrix by policy;
- Plus One loss-cause matrix by policy;
- per-market / per-side / per-fold loss decomposition;
- MFE/MAE distributions;
- cost-drag decomposition;
- trail versus initial-stop attribution;
- Plus One partial-state attribution;
- inadmissible evidence census;
- dominant-cause percentages;
- comparison of Classic versus Plus One;
- exact adjudication outcome for each variant;
- any proposed next hypothesis clearly separated from findings.

No strategy change is permitted merely because it would have improved the already-observed losing trades.