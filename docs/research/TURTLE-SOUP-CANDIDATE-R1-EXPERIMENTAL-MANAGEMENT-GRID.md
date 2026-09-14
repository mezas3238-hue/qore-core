# Turtle Soup Candidate R1 — Predeclared QORE Experimental Management Grid

Status: FROZEN FOR DEVELOPMENT CHARACTERIZATION BEFORE ANY ECONOMIC RESULTS ARE INSPECTED.

Research identity: `turtle-soup-candidate-r1`
Canonical trader code: `CODE_UNASSIGNED`
Issue: #551
PR: #553

## 1. Purpose and provenance boundary

Connors/Raschke source closes setup, entry, initial stop and qualitative trade-management intent, but does not provide a deterministic realized-P&L exit algorithm. This document predeclares a deliberately small QORE research grid before development results are inspected.

Every policy in this document is:

`QORE_EXPERIMENTAL_MANAGEMENT`

and is NOT a canonical Turtle Soup rule.

No result produced by these policies may be described as the performance of unmodified/original Turtle Soup.

## 2. Invariants shared by every policy

1. Source-faithful setup, entry and initial stop remain unchanged.
2. No fixed 2R target.
3. No 5-period target.
4. No FVG/OB/EMA/ICT filters.
5. Stop may only tighten; it may never loosen.
6. Trail updates occur only after a bar is fully closed and apply to the next bar.
7. If the active stop is touched before a bar closes, the stop exit wins; a later close cannot retroactively update the stop.
8. Same-bar event order that cannot be established from available evidence is `AMBIGUOUS`, never favorable-first.
9. Time exits occur only at the close of the designated completed management bar if the position remains open.
10. Long/short rules are exact mirrors.
11. Each policy receives a distinct deterministic SHA-256 fingerprint.
12. Classic and Plus One are characterized separately.
13. Development characterization only; no fresh holdout may be opened until one candidate/config is frozen.
14. No post-holdout retuning.

## 3. Bar definition

`management_bar_index = 1` is the first fully completed source-timeframe bar after entry.

The entry/fill bar itself is not counted as management bar 1.

For a D1 source candidate, management bars are subsequent day-session D1 bars. Futures data use day-session data only under the adjudicated source policy.

## 4. Generic trailing formulas

### LONG one-bar trail

After management bar `k` closes and only if the position is still open:

`candidate_stop = low[k]`

`next_stop = max(current_stop, candidate_stop)`

### SHORT one-bar trail

`candidate_stop = high[k]`

`next_stop = min(current_stop, candidate_stop)`

### LONG two-bar trail

For `k >= 2`:

`candidate_stop = min(low[k-1], low[k])`

`next_stop = max(current_stop, candidate_stop)`

### SHORT two-bar trail

`candidate_stop = max(high[k-1], high[k])`

`next_stop = min(current_stop, candidate_stop)`

A two-bar trail does not update until two completed management bars exist.

## 5. Classic experimental policies

Classic source authorizes a trailing stop but gives no mechanical trail. QORE will test only these four predeclared policies.

| Policy ID | Trail | Hard time exit |
|---|---:|---:|
| `C_TRAIL1_H3` | previous completed bar extreme | close of bar 3 |
| `C_TRAIL2_H3` | two-bar extreme | close of bar 3 |
| `C_TRAIL1_H6` | previous completed bar extreme | close of bar 6 |
| `C_TRAIL2_H6` | two-bar extreme | close of bar 6 |

### Classic activation

Trail updates begin after the first completed management bar for one-bar policies and after the second completed management bar for two-bar policies.

No additional profit threshold or R-multiple trigger is introduced.

## 6. Plus One experimental policies

Source explicitly requires partial profits within 2–6 bars and trailing the balance but does not specify fraction, exact bar or trail formula.

To minimize degrees of freedom QORE freezes one partial fraction only:

`partial_fraction = 0.50`

The grid varies only:

- scheduled partial bar: 2, 4 or 6;
- remainder trail: one-bar or two-bar.

All Plus One policies use a common hard time exit at management-bar 10 for any remaining quantity.

| Policy ID | Partial | Trail remaining 50% | Hard time exit |
|---|---|---|---:|
| `P_B2_F50_TRAIL1_H10` | 50% at bar-2 close if profitable | one-bar | bar 10 close |
| `P_B2_F50_TRAIL2_H10` | 50% at bar-2 close if profitable | two-bar | bar 10 close |
| `P_B4_F50_TRAIL1_H10` | 50% at bar-4 close if profitable | one-bar | bar 10 close |
| `P_B4_F50_TRAIL2_H10` | 50% at bar-4 close if profitable | two-bar | bar 10 close |
| `P_B6_F50_TRAIL1_H10` | 50% at bar-6 close if profitable | one-bar | bar 10 close |
| `P_B6_F50_TRAIL2_H10` | 50% at bar-6 close if profitable | two-bar | bar 10 close |

### Plus One partial rule

For LONG on scheduled partial bar `p`:

`partial_is_profitable = close[p] > executable_entry_price`

For SHORT:

`partial_is_profitable = close[p] < executable_entry_price`

If profitable, close exactly 50% at that bar close, then trail the remaining 50%.

If the scheduled bar does not close profitably, the partial is skipped permanently. QORE does not move it to another bar after observing the path.

For one-bar trail policies, the balance trail may update from the scheduled partial bar close onward.

For two-bar trail policies, the balance trail uses the last two completed management bars and may update at the scheduled partial bar close if two bars are already available.

If the partial was skipped, the same trailing formula still activates at the scheduled partial bar and applies to the full remaining quantity. This keeps the policy deterministic and avoids an unbounded discretionary state.

## 7. Exit precedence

Within each management bar:

1. active protective/trailing stop from the prior completed bar;
2. if no stop exit, observe bar close;
3. scheduled partial at close if applicable;
4. trail update for the next bar;
5. hard time exit at close if the horizon is reached.

If partial and hard time exit are both scheduled at the same close, hard time exit closes all remaining quantity after recording the partial only if the policy explicitly requires both; no current policy has such a collision.

## 8. Price and cost semantics

This grid defines strategic management only. Fill-price/slippage/spread/commission policy belongs to the QORE replay execution-cost model and must be fingerprinted separately.

Gap-through protective stops use the explicit `QORE_EXECUTION_MODEL`, not source authority.

## 9. Candidate selection rule

Development data may be used to characterize all ten policies. Selection must be made by predeclared multi-metric gates rather than highest raw return alone.

At minimum report per variant/policy:

- trade count;
- fill count;
- censored/ambiguous count;
- total R;
- mean R;
- median R;
- win rate;
- profit factor;
- max drawdown in R;
- worst trade;
- longest losing sequence;
- exposure/holding bars;
- result concentration by market/year/side;
- cost sensitivity.

A management policy may advance only if it is not dominated by another policy across robustness metrics and does not depend on one market/year/side for the majority of gains.

One Classic policy and one Plus One policy may be frozen independently. Combining them is a later portfolio decision, not part of management selection.

## 10. Fresh holdout embargo

Until development characterization is complete and candidate fingerprints are frozen:

`FRESH_OOS_ACCESS = PROHIBITED`

After holdout is opened:

- no grid changes;
- no partial-fraction changes;
- no horizon changes;
- no trail-lookback changes;
- no entry-offset retuning;
- no market filtering based on holdout outcome.

## 11. Frozen grid fingerprint input

The grid fingerprint must bind at minimum:

- schema version;
- research identity;
- variant;
- policy ID;
- partial fraction;
- partial bar;
- trail lookback;
- hard holding horizon;
- exit precedence;
- source config fingerprint;
- execution-cost-model fingerprint;
- Git SHA.

## 12. Next engineering step

Implement these exact ten policies plus adversarial tests, then run development replay only.

No DEMO/LIVE/production/real-capital authority is granted by this grid.
