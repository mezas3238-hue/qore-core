# Turtle Soup Candidate R1 — Round 2 Engineering Adjudication

Status: SOURCE ENTRY/INITIAL-STOP CONTRACT CLOSED ENOUGH FOR DEVELOPMENT REPLAY; ECONOMIC EXIT CONTRACT NOT SOURCE-MECHANICAL.

Research identity: `turtle-soup-candidate-r1`
Canonical trader code: `CODE_UNASSIGNED`
Issue: #551
Authoritative PR: #553

## 1. DeepSeek Round 2 disposition

DeepSeek Round 2 materially improves the reconstruction, but its final `qore_next_path = SOURCE_BOUND_REPLAY` is rejected as too strong for realized P&L.

Recovered *Street Smarts* text explicitly states that the strategies are not mechanical systems and that exact exit timing is subjective. Chapter 3 applies common money-management principles to all patterns: enter the entire position, place an initial protective stop, scale out as the market moves favorably, and protect gains. The exact timing to exit is explicitly subjective. Chapter 4 Turtle Soup instructs a trailing stop as profits develop but gives no deterministic trail formula. Chapter 5 Plus One says to take partial profits within two to six bars and trail the balance, without specifying fraction, exact bar, price trigger, or trail formula.

Therefore QORE MUST NOT claim a fully source-bound realized-P&L replay.

Frozen path:

`SOURCE-BOUND ENTRY/INITIAL-STOP REPLAY -> PREDECLARED QORE EXPERIMENTAL MANAGEMENT GRID -> DEVELOPMENT CHARACTERIZATION -> MANAGEMENT SELECTION -> CANDIDATE/CONFIG FREEZE -> FRESH OOS`

Experimental management is never canonical Turtle Soup and requires separate fingerprints/provenance.

## 2. Classic source contract — closed findings

- 20-period prior extreme.
- Prior extreme at least 4 trading sessions earlier on daily source bars.
- Same-session reversal stop entry after trading beyond the prior extreme.
- Long: 5–10 ticks above prior 20-period low; short symmetric.
- Order good for current day/session only.
- Initial protective stop: 1 tick beyond current breakout-session extreme.
- As profit develops, use a trailing stop; exact trail algorithm is subjective/not mechanical.
- Re-entry is directly source-authorized: if stopped out on trade day 1 or day 2, may re-enter at the original entry price on day 1/day 2 only.

### Re-entry boundary

Tier-A text closes eligibility, original re-entry price, and the day-1/day-2 boundary. It does NOT close:

- maximum number of re-entry attempts;
- whether repeated same-day re-entry after multiple stop-outs is allowed;
- exact stop recalculation after re-entry if a new extreme forms;
- whether a fresh sweep is required.

`CLASSIC_REENTRY = SOURCE_AUTHORIZED_PARTIAL`.

## 3. Plus One source contract — closed findings

- 20-period prior extreme.
- Prior extreme at least 3 trading sessions earlier on daily source bars.
- Breakout bar closes at/beyond earlier 20-period extreme.
- Entry next day/bar at the earlier 20-period extreme.
- Cancel if not filled on day/bar 2.
- Initial stop 1 tick beyond lower/higher of day-1 and day-2 extremes.
- Take partial profits within 2–6 bars and trail the balance.

Management is source-authentic but mechanically incomplete.

## 4. Intraday scope and age semantics

The source explicitly states Turtle Soup and Plus One work in all time frames and gives 10-minute examples. It also explicitly says intraday entries are placed one tick beyond the previous 20-bar high/low in reversal direction.

A 10-minute Plus One example states that the previous 20-bar low was made in the first 20 minutes of trading and a later 20-bar low/reversal setup occurs within the same trading day. This rules out a literal requirement that the prior extreme be 3 whole trading days/sessions old for intraday execution.

Engineering adjudication:

- unit for intraday age is strongly evidenced as **bars**, not calendar trading days;
- the source does not print the sentence `Classic >= 4 bars / Plus One >= 3 bars` explicitly;
- applying the published Classic/Plus-One age constants to the source-authorized intraday bar framework is therefore classified as `SOURCE_CONSISTENT_INTERPRETATION`, not a verbatim source rule.

Current status:

`CLASSIC_INTRADAY_AGE = >=4 BARS (SOURCE_CONSISTENT_INTERPRETATION, MEDIUM confidence)`

`PLUS_ONE_INTRADAY_AGE = >=3 BARS (SOURCE_CONSISTENT_INTERPRETATION, MEDIUM confidence)`

QORE may implement these only if provenance/fingerprint records the interpretation class. They must not be represented as a direct quote.

## 5. Session/night data — CLOSED

The recovered book states in Chapter 6: `as with all of the strategies presented, night data are ignored` and instructs that ranges use day-session data only. A later chapter again says that, as with every other strategy in the book, night sessions are omitted.

This is direct-author global-book language and is sufficient to close the futures session-data blocker for the historical source methodology.

`TURTLE_SOUP_FUTURES_NIGHT_DATA = EXCLUDE_CONFIRMED`

`REFERENCE_SESSION = DAY_SESSION_DATA_ONLY`

QORE still needs an instrument/session calendar mapping for modern markets, but that mapping is an execution/data-engineering concern, not an unresolved source claim.

## 6. Gap semantics

Still unresolved as an explicit author fill-price rule. Examples show orders becoming positions when the market opens beyond the trigger, but do not provide a sufficiently explicit universal fill-price convention.

QORE may use conservative stop-market execution semantics (gap-through filled at first observable executable price/open), but it must be labeled `QORE_EXECUTION_MODEL`, never `SOURCE_RULE`.

## 7. Canonical/source-consistent/experimental boundary

### DIRECT SOURCE

- 20-period setup family;
- Classic daily age 4;
- Plus One daily age 3;
- Classic/Plus-One entry timing and levels;
- initial stops;
- order expiry;
- Classic re-entry eligibility/original entry/day-1-day-2 boundary;
- qualitative management instructions;
- all-timeframe authority;
- intraday one-tick entry offset;
- futures night-data exclusion/day-session-only policy.

### SOURCE_CONSISTENT_INTERPRETATION

- Classic intraday age `>=4 bars`;
- Plus One intraday age `>=3 bars`.

### QORE_EXECUTION_MODEL

- gap-through fill at first observable executable price;
- intrabar ambiguity censorship where event order cannot be proven.

### QORE_EXPERIMENTAL MANAGEMENT

- exact trailing formula;
- exact partial fraction;
- exact partial bar inside 2–6;
- exact profit trigger;
- exact final exit.

## 8. Required QORE management research protocol

Before any fresh holdout, QORE may define a finite predeclared management grid. Every axis must be labeled `QORE_EXPERIMENTAL`.

The grid must:

1. preserve source entry and initial stop;
2. use only deterministic, causal exits;
3. be finite and declared before development results are inspected;
4. use development data only for characterization/selection;
5. freeze one candidate/config before fresh OOS;
6. prohibit post-holdout retuning;
7. fingerprint every management policy separately;
8. report Classic and Plus One separately before any combined view.

## 9. DeepSeek Round 2 corrections

- complete realized-P&L `SOURCE_BOUND_REPLAY`: REJECTED;
- `READY_FOR_ENGINEERING_WITH_PARAMETERS`: ACCEPTED only with strict provenance separation;
- Classic re-entry: upgraded to DIRECT SOURCE for eligibility/original-price/day-1-day-2 boundary;
- night-data/session blocker: CLOSED — day-session only for futures source methodology;
- intraday age: narrowed to bar semantics, 4/3 as source-consistent interpretation with MEDIUM confidence;
- fixed 5-period target: REJECTED as canonical;
- fixed 2R: REJECTED as canonical;
- 25%/50% partial fractions: NOT SOURCE RULES.

## 10. Remaining blockers before economic development replay

Source blockers no longer include session/night data.

Remaining material boundaries:

1. no mechanical source exit/trailing formula;
2. no exact Plus One partial fraction/trigger;
3. Classic repeated re-entry state mechanics remain partial;
4. gap fill price is an execution-model decision, not source-closed.

These do not prevent a **predeclared experimental-management development replay**, but they prevent claiming that realized P&L is purely canonical Turtle Soup.

## 11. Frozen next path

`ROUND2_SOURCE_ADJUDICATION -> EXPERIMENTAL_MANAGEMENT_SPEC -> IMPLEMENTATION + ADVERSARIAL TESTS -> DEVELOPMENT REPLAY -> MANAGEMENT SELECTION -> CANDIDATE/CONFIG FREEZE -> FRESH OOS -> STRESS -> MONTE CARLO -> RISK REVIEW -> CIBO REVIEW -> INDEPENDENT VALIDATION -> ECONOMIC EVIDENCE`

No DEMO/LIVE/production/real-capital authority is granted by this document.
