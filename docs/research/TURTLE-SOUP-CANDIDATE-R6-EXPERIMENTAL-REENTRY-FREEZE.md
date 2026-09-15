# Turtle Soup Candidate R6 — Experimental Re-entry Freeze

Status: **FROZEN BEFORE R6 ECONOMIC REPLAY**

Root research identity: `turtle-soup-candidate-r1`

R6 round identity: `turtle-soup-candidate-r6-reentry-exp1`

Canonical trader code: `CODE_UNASSIGNED`

Parent evidence round: R5 / PR #563

## 1. Purpose and provenance boundary

R6 tests one causal hypothesis only: whether the source-described Classic re-entry concept materially changes the already rejected R5 Classic development result.

Because the recovered source evidence does not fully specify re-entry mechanics, every unresolved axis below is explicitly `QORE_EXPERIMENTAL_REENTRY`. No experimental rule may be described as canonical Connors/Raschke Turtle Soup.

R6 does not change:

- 20-session source lookback;
- Classic minimum reference age = 4 sessions;
- Classic entry offset = 5 ticks;
- seven-market universe;
- original first-attempt entry and initial-stop construction;
- the four frozen Classic management policies;
- primary cost = 1.0 bp per completed full-position attempt;
- stress cost = 2.0 bp per completed full-position attempt;
- the six frozen walk-forward folds;
- the absolute R1/R5 advancement gate;
- fresh-OOS embargo at `2026-03-01T00:00:00Z`.

No side, market, year or prior outcome is filtered.

## 2. Single frozen re-entry mechanic

R6 has exactly one re-entry mechanic; there is no parameter grid.

### 2.1 Eligibility

A Classic source opportunity becomes re-entry eligible only after its first deterministic R5 fill subsequently closes at the active protective stop during research Day 1 or Day 2.

`Day 1` is defined for this experiment as the execution-qualified D1 source session containing the original fill.

`Day 2` is the immediately following D1 source session in the provider D1 stream, provided that the session is execution-qualified by the existing D1/M15 reconciliation contract. Missing or irreconcilable Day-2 evidence fails closed; QORE does not skip forward to a later session and relabel it Day 2.

This day definition is `QORE_EXPERIMENTAL_REENTRY`, not source authority.

### 2.2 Maximum attempts

Exactly one re-entry attempt is permitted after the original attempt.

Therefore one source opportunity has at most:

- Attempt 1: original Classic fill;
- Attempt 2: one experimental re-entry.

No third attempt exists, even if Attempt 2 stops out inside Day 1 or Day 2.

This limit is `QORE_EXPERIMENTAL_REENTRY`.

### 2.3 Re-entry price

The re-entry stop level is exactly the original executable entry-price level from Attempt 1. It is not recalculated from a later 20-session reference and the 5-tick offset is not re-optimized.

If Attempt 1 filled through an opening gap rather than exactly at its trigger, R6 re-entry uses the original Classic **entry trigger level**, not the gap fill price. This preserves the recovered source concept of the original entry-price level without rewarding an accidental gap fill.

### 2.4 No new-sweep requirement

R6 does not require a second sweep before the re-entry level may become active. Once Attempt 1 has stopped out, the experimental re-entry order may trigger on a later causal return through the original entry level while the Day-1/Day-2 window is open.

This is `QORE_EXPERIMENTAL_REENTRY` because the source adjudication did not close the new-sweep question.

### 2.5 Protective stop after re-entry

The re-entry initial stop is one tick beyond the most adverse causally observed price from the instant immediately after Attempt-1 stop-out through the instant of re-entry fill, inclusive of the fill observation:

- LONG: `reentry_stop = minimum_observed_price - 1 tick`;
- SHORT: `reentry_stop = maximum_observed_price + 1 tick`.

The stop must be strictly protective relative to the re-entry fill. Evidence that cannot establish the required adverse extreme is censored.

This is a preregistered `QORE_EXPERIMENTAL_REENTRY` stop rule and is not attributed to Connors/Raschke.

### 2.6 Causal ordering and ambiguity

Re-entry event order must be established from the highest already-acquired admissible evidence hierarchy used by R5:

`M15 -> exact M1 refinement -> provider-native BID ticks where already frozen and available`.

R6 does not acquire new data selected by R6 P&L.

If stop-out and possible re-entry are inside a bar/minute where event order remains unobservable, the re-entry opportunity is `AMBIGUOUS` / censored. Equal-timestamp critical tick events remain ambiguous. No favorable ordering is invented.

### 2.7 Gap semantics

A re-entry stop order crossed by an execution-qualified session opening gap fills at the first observable session price under the existing `QORE_EXECUTION_MODEL`. Protective-stop gap-through behavior remains the existing QORE model. These are execution-model semantics, not source authority.

### 2.8 Window expiry

If Attempt 1 stops out on Day 1, the re-entry order remains eligible through the remainder of Day 1 and Day 2 and expires at the end of Day 2.

If Attempt 1 stops out on Day 2, the re-entry order is eligible only through the remainder of Day 2.

No re-entry may fill on Day 3 or later.

## 3. Management after re-entry

After a deterministic re-entry fill, R6 applies the same four already-frozen Classic policies independently:

- `C_TRAIL1_H3`;
- `C_TRAIL2_H3`;
- `C_TRAIL1_H6`;
- `C_TRAIL2_H6`.

Management bar 1 is the first fully completed D1 management session after the re-entry fill session, exactly as in the frozen R1 management grid. The re-entry fill session is not management bar 1.

No BE, partial, fixed target, new trail, new horizon or new exit is introduced.

## 4. Economic accounting

Attempt 1 and Attempt 2 are distinct risk-bearing trades for research accounting.

Each attempt is normalized to its own initial stop risk and charged the frozen cost once if completed:

- primary: 1.0 bp round trip;
- stress: 2.0 bp round trip.

A source opportunity can therefore realize losses on both Attempt 1 and Attempt 2. R6 must report both attempt-level and opportunity-level results so repeated-entry risk is visible rather than hidden.

No portfolio/risk sizing approval is implied; account-level sizing belongs to later Risk/CIBO gates only if the economic gate is passed.

## 5. Frozen evidence boundary

R6 may consume only development evidence with `opened_at < 2026-03-01T00:00:00Z` and the immutable evidence already used by R5:

- corrected D1 run `34947549114`;
- corrected M15 run `34947548876`;
- targeted M1 run `34959770555`;
- R5 Wave 1 run `34969259616`;
- R5 Wave 1B run `34985374006`;
- R5 Wave 2 run `34986122071`.

No new fresh OOS access is authorized.

## 6. Advancement gate

The R1/R5 frozen absolute gate is reused without modification. A policy advances only if all are true on forward evidence:

1. at least 30 closed trades;
2. forward expectancy > 0 R/trade;
3. forward PF > 1.00;
4. at least 4/6 positive folds;
5. 2.0 bp stress expectancy >= 0 R/trade;
6. every seven-market leave-one-out total remains > 0;
7. no one market, year or side contributes >50% of gross positive gains;
8. causal/data integrity remains fail-closed.

R6 improvement relative to R5 is insufficient by itself.

If more than one of the four unchanged Classic management policies passes, reuse the existing deterministic selection rule: higher stress total, then higher primary total, then lower max drawdown, then higher minimum-fold result, then lexicographically smaller policy ID.

## 7. Stop rule

If no R6 policy passes the absolute development gate:

`R6_REENTRY_EXPERIMENT_REJECTED`

and fresh OOS remains closed. No additional re-entry parameter tuning is allowed from the R6 result.

If one or more pass, only then may the selected exact configuration be frozen for the single-use fresh OOS.

No approval, canonical trader identity, prop-firm qualification or LIVE authority exists at this freeze stage.
