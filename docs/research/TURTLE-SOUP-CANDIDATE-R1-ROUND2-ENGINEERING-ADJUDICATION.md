# Turtle Soup Candidate R1 — Round 2 Engineering Adjudication

Status: SOURCE ENTRY/INITIAL-STOP CONTRACT CLOSED ENOUGH FOR DEVELOPMENT REPLAY; ECONOMIC EXIT CONTRACT NOT SOURCE-MECHANICAL.

Research identity: `turtle-soup-candidate-r1`
Canonical trader code: `CODE_UNASSIGNED`
Issue: #551
Authoritative PR: #553

## 1. DeepSeek Round 2 disposition

DeepSeek Round 2 materially improves the source reconstruction, but its final `qore_next_path = SOURCE_BOUND_REPLAY` is rejected as too strong for economic P&L.

The recovered *Street Smarts* text explicitly states that these strategies are not mechanical systems and that exact exit timing is subjective. Chapter 3 says all patterns share the same money-management principles, including entering the entire position, using an initial protective stop, and scaling out as the market moves favorably; it explicitly says the exact timing to exit is subjective. Chapter 4 Turtle Soup then instructs a trailing stop as the position becomes profitable but gives no deterministic trail formula. Chapter 5 Plus One says to take partial profits within two to six bars and trail the balance, again without a partial fraction, price trigger, bar-selection rule, or trail formula.

Therefore QORE MUST NOT claim a fully source-bound economic replay from entry through realized P&L.

Engineering path is frozen as:

`SOURCE-BOUND ENTRY/INITIAL-STOP REPLAY -> PREDECLARED QORE EXPERIMENTAL MANAGEMENT GRID -> DEVELOPMENT CHARACTERIZATION -> CANDIDATE/CONFIG FREEZE -> FRESH OOS`

The experimental management grid is not canonical Turtle Soup and must have a separate configuration fingerprint/provenance namespace.

## 2. Classic source contract — closed findings

- 20-period prior extreme.
- Prior extreme at least 4 trading sessions earlier.
- Same-session reversal stop entry after the market trades beyond the prior extreme.
- Long entry: 5–10 ticks above prior 20-period low; short symmetric.
- Order good for current day/session only.
- Initial protective stop: 1 tick beyond today's breakout-session extreme.
- As profit develops, use a trailing stop; exact trail algorithm is not specified mechanically.
- Re-entry is explicitly source-authorized: if stopped out on trade day 1 or day 2, may re-enter at the original entry price, on day 1/day 2 only.

### Re-entry boundary

Tier-A text closes eligibility, price, and calendar boundary, but does NOT close:

- maximum number of re-entry attempts;
- whether repeated re-entry after multiple stop-outs is allowed;
- exact protective-stop recalculation after a re-entry when a new extreme forms;
- whether a fresh sweep is required.

Accordingly, `CLASSIC_REENTRY = SOURCE_AUTHORIZED_PARTIAL`, not a fully deterministic state machine.

## 3. Plus One source contract — closed findings

- 20-period prior extreme.
- Prior extreme at least 3 trading sessions earlier.
- Breakout bar closes at/beyond earlier 20-period extreme.
- Entry next day/bar at the earlier 20-period extreme.
- Cancel if not filled on day/bar 2.
- Initial stop 1 tick beyond the lower/higher of day-1 and day-2 extremes.
- Take partial profits within 2–6 bars and trail a stop on the balance.

The management sentence is source-authentic but mechanically incomplete. It cannot be converted into one deterministic P&L path without an explicit QORE experimental policy.

## 4. Intraday scope

The source explicitly says Plus One can be traded in all markets and all time frames. The book introduction also says most setups can be traded on any market/time frame. Intraday examples exist.

However, the exact mapping of the printed 3/4 `trading sessions` age rule into an intraday bar-age test remains unresolved. R1 must continue to fail closed for non-D1 source bars until this is resolved or a clearly labeled QORE transfer rule is predeclared and tested separately from canonical source fidelity.

## 5. Session/night data

UNRESOLVED. No Turtle-Soup-specific direct-author rule has been recovered that proves whether 20-period references for futures must use RTH-only versus full-session data. Do not silently choose one and call it canonical.

## 6. Gap semantics

UNRESOLVED as an author rule. QORE may use a conservative execution-model convention for backtesting, but it must be labeled `QORE_EXECUTION_MODEL`, not `SOURCE_RULE`.

## 7. Canonical vs experimental boundary

### Canonical/source-bound

- setup detection;
- 20-period reference;
- Classic age 4 / Plus One age 3;
- entry timing and source price level/band;
- initial stop;
- order expiry;
- Classic re-entry eligibility at original entry through day 2 (partial state semantics);
- qualitative management instructions.

### Not mechanically source-bound

- exact trailing formula;
- exact partial fraction;
- exact partial bar inside 2–6;
- exact profit trigger;
- exact final exit;
- gap fill convention;
- intraday age translation;
- session/night-data convention.

## 8. Required QORE management research protocol

Before any fresh holdout, QORE may define a finite, predeclared experimental grid for management. Every axis must be labeled `QORE_EXPERIMENTAL`, never canonical.

A valid grid must:

1. preserve source entry and initial stop;
2. contain a small finite set of deterministic exit policies selected before results are inspected;
3. use development data only for characterization/selection;
4. freeze one candidate configuration before fresh OOS;
5. prohibit post-holdout retuning;
6. retain a distinct methodology/config fingerprint for each policy;
7. report results by Classic and Plus One separately before any combined portfolio view.

No particular experimental exit policy is authorized by this adjudication yet.

## 9. DeepSeek Round 2 corrections

- `SOURCE_BOUND_REPLAY` as a complete realized-P&L path: REJECTED.
- `READY_FOR_ENGINEERING_WITH_PARAMETERS`: ACCEPTED only for source detector/entry/initial stop and for a separately declared experimental-management research program.
- Classic re-entry Tier status: upgraded from secondary-only to DIRECT SOURCE AUTHORITY for eligibility/original-entry/day1-day2 boundary, while repeated-attempt mechanics remain unresolved.
- Fixed 5-period target: REJECTED as canonical.
- 2R target: REJECTED as canonical.
- 25%/50% partial fractions: NOT SOURCE RULES; may only appear in a predeclared experimental grid if separately justified as research axes.

## 10. Frozen next path

`ROUND2_SOURCE_ADJUDICATION -> EXPERIMENTAL_MANAGEMENT_SPEC -> IMPLEMENTATION + ADVERSARIAL TESTS -> DEVELOPMENT REPLAY -> MANAGEMENT SELECTION -> CANDIDATE/CONFIG FREEZE -> FRESH OOS -> STRESS -> MONTE CARLO -> RISK REVIEW -> CIBO REVIEW -> INDEPENDENT VALIDATION -> ECONOMIC EVIDENCE`

No DEMO/LIVE/production/real-capital authority is granted by this document.
