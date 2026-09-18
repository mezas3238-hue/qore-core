# TURTLE SOUP XAUUSD R1 — FROZEN CANDIDATE + SEALED HOLDOUT

Identity: `TURTLE_SOUP_XAUUSD_R1`

Holdout identity: `TURTLE_SOUP_XAUUSD_R1_FRESH_2015_2016`

Status before evidence access: **FROZEN / PREREGISTERED / NOT CERTIFIED**.

## 1. Purpose

This document freezes the first XAUUSD-specific Turtle Soup candidate produced after reading the consumed CIBO Market Intelligence Matrix. The matrix remains association-level research evidence. R1 deliberately does **not** promote the strongest E1 associations (`FVG after raid`, `prior-body alignment`, session buckets, exact equal liquidity) into operating filters.

The test is intended to answer one question only: does this fixed XAUUSD Turtle Soup mechanism survive a previously unconsumed one-year out-of-sample interval without changing the rules after observing outcome data?

## 2. Frozen evidence separation

Development/research evidence already consumed includes the CIBO ten-year corpus beginning in September 2016 and the documented historical Turtle Soup holdouts/development windows from 2016 onward.

The sealed R1 interval is intentionally earlier:

- acquisition/warm-up open: `2015-01-01T00:00:00Z`
- evaluation open: `2015-03-01T00:00:00Z`
- evaluation close, exclusive: `2016-03-01T00:00:00Z`
- symbol: `XAUUSD`
- source resolution: real provider M5 only

The evaluation interval ends before the documented R5 acquisition begins (`2016-03-01T22:00:00Z`). No outcome from this 2015-2016 interval may be inspected before the candidate and this preregistration are committed.

**No replacement interval is authorized after any holdout evidence access.** If the provider cannot supply this frozen interval, the workflow must fail closed. It must not silently substitute another year.

## 3. Frozen Turtle Soup R1 contract

### Scope

- Market: XAUUSD only.
- Directions: LONG and SHORT.
- Source timeframes: H1 and H4.
- Session inclusion: all sessions; session is diagnostic metadata only.
- One active XAUUSD position at a time.
- If H1 and H4 produce the same entry timestamp, deterministic priority is H4 then H1.

### Liquidity reference

Only the immediately prior completed source candle C1 is the frozen liquidity reference for R1.

For LONG, the raid level is C1 low and the opposite structural destination is C1 high.

For SHORT, the raid level is C1 high and the opposite structural destination is C1 low.

### Exact C2 reversal closure

LONG C2:

`C2.low < C1.low AND C2.close > C1.low`

SHORT C2:

`C2.high > C1.high AND C2.close < C1.high`

If both or neither condition is true, no signal is eligible.

The C2 closure itself is the frozen source-level reclaim. No separately optimized reclaim-latency threshold is permitted.

### Causal CISD

C2 must contain a causal CISD in the same direction and the confirmation must occur before C2 closes.

- H1 source -> M5 CISD evidence.
- H4 source -> M15 CISD evidence.

CISD uses the existing causal contiguous opposing-delivery-series implementation. The protected swing returned by that causal CISD is the structural invalidation.

### Entry

Entry is the open of the immediately following source candle after the completed C2.

This means C2 closure, the final C2 extreme, CISD confirmation and protected swing are all known before entry.

The following source candle is execution timing only. R1 does **not** claim a formal C3 pattern; C3 remains:

`UNRESOLVED_NO_FROZEN_C3_CONTRACT`

### Stop

Stop is the exact causal CISD Protected Swing, with **zero retrospective pip/tick/ATR offset**.

If entry is already through the protected swing, the setup is invalid and abstains.

### Target / DOL

Target is the opposite boundary of C1:

- LONG -> C1 high.
- SHORT -> C1 low.

The target must still be untouched throughout C2 before entry. If already touched, the setup abstains.

This is a deliberately bounded structural target family. It does not claim to exhaust all possible DOL families.

### Lifecycle and collision handling

- Maximum position lifetime: 24 hours from entry, capped by holdout end.
- Target or stop can end the trade earlier.
- If stop and target are both touched within the same M5 bar, STOP is assumed first.
- Gap through stop is marked to the observed M5 open.
- Gap beyond target is capped at the target.
- At the 24-hour boundary, the position is marked to the final available M5 close.

### Explicitly absent filters

R1 has no:

- session/killzone inclusion filter;
- prior-body alignment filter;
- FVG-required filter;
- equal-liquidity filter;
- raw raid-depth threshold;
- raw Protected Swing distance threshold;
- ATR stop;
- fixed-R target;
- minimum projected-R gate;
- market-side exclusion.

FVG and prior-body alignment remain diagnostics because the matrix evidence for them is E1 association and FVG may include post-raid information that would require stricter causal timing before promotion.

## 4. Frozen friction sensitivity

For research sensitivity only:

- gross: no R deduction;
- primary: `0.05R` deducted per trade;
- stress: `0.10R` deducted per trade.

These are not a claim about a future broker/account's exact transaction costs.

## 5. Preregistered holdout checks

The one-year R1 holdout is labelled `OOS_SURVIVED_RESEARCH_GATE_NOT_CERTIFIED` only when **all** of the following are true:

1. at least 30 executed trades;
2. primary total R > 0;
3. primary profit factor > 1;
4. stress total R > 0;
5. stress profit factor > 1;
6. primary max drawdown <= 20R;
7. second chronological half, split by ordered trade count, has positive primary mean R;
8. at least three calendar-quarter buckets have positive primary total R.

If any check fails, outcome is `R1_REJECTED_FOR_PROMOTION`.

Passing this research gate is **not certification** and is not sufficient to authorize demo, live, real capital, production, or a canonical trader code. It only permits further independent validation work.

## 6. Governance

At all times in this R1 workflow:

- `DEMO_ELIGIBLE = false`
- `LIVE_AUTHORIZED = false`
- `REAL_CAPITAL_AUTHORIZED = false`
- `PRODUCTION_AUTHORIZED = false`
- `CANONICAL_TRADER_CODE = CODE_UNASSIGNED`
- automatic certification is prohibited
- no merge is authorized by this experiment

Once the workflow accesses outcome-bearing M5 data from the sealed interval, the holdout is considered consumed for future model selection. A failed R1 may be diagnosed using the consumed evidence but must not be tuned and then re-labelled as fresh on the same interval.
