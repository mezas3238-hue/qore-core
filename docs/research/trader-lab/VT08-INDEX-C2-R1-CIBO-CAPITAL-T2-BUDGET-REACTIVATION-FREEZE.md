# VT-08 Index C2 R1 — CIBO Capital T2 Budget Reactivation Freeze

Checkpoint: 2026-09-13

Status: RESEARCH / CONSUMED-EVIDENCE ONLY

## Parent authority

- Parent capital study PR: #538
- Parent capital T1 HEAD: `0a07f6294d501613650f70fbf36e160606d62b47`
- Parent official run: `34774905465`
- Parent artifact: `10323490893`
- Parent signal stream: exact 152 VT08_INDEX_C2_POSITIONAL_R1 signals
- Parent signal identity SHA-256: `f29bb0c1877b38f535671730c34623df9210465ae7743b640dac2c2d2c8e7d7d`

This T2 freeze is created before observing any T2 economic outcome.

## Owner clarification

CIBO must not confuse BANK with LOCK.

When Risk has legitimate budget headroom, CIBO may request ATTACK so that profitable opportunity is not wasted. CIBO never authorizes exposure; Risk remains sovereign and may ALLOW, REDUCE, or REJECT every request.

## Frozen numerical contract

No T1 threshold is changed:

- BASE signal request: 1.00%
- BASE heat ceiling: 2.50%
- ATTACK signal request: 2.00%
- ATTACK heat ceiling: 4.50%
- BANK trigger: +2.00% peak profit
- BANK fraction/reference: 25%
- legacy minimum free-cushion marker: 0.50% (retained for provenance; not a hard Risk floor in T2)
- internal daily ceiling: 4.75%
- internal capital drawdown ceiling: 4.95%
- provider boundary: 5.00%
- FULL_GUARD reductions: DD 3.50% -> 0.75x, 4.25% -> 0.50x, 4.75% -> 0.25x

No index outcome selected any of these values.

## T2 semantic correction

### BANK_REFERENCE

The banked amount remains a monotonic strategic/accounting reference derived from the same BANK25 rule. It is not itself a sovereign execution floor.

It may influence CIBO posture and whether ATTACK is conceptually available, but it MUST NOT replace Risk's hard daily/capital/provider limits.

BANK_REFERENCE is never silently reset downward.

### Risk hard budget

At every day+anchor group, Risk independently computes:

- daily headroom from the 4.75% internal daily ceiling;
- capital headroom from the 4.95% internal peak-equity drawdown ceiling;
- heat headroom from the requested envelope;
- provider safety remains bounded below 5.00%.

Only those Risk limits can make executable budget zero.

### ATTACK

CIBO may request ATTACK only when:

1. BANK_REFERENCE has activated from the pre-existing +2% trigger; and
2. no FULL_GUARD reduction state has priority; and
3. Risk can authorize the FULL frozen ATTACK envelope for the simultaneous group under heat + daily + capital headroom.

If the full ATTACK envelope is not authorizable but BASE is authorizable, CIBO MUST fall back to PROTECT/BUILD and request BASE. It MUST NOT remain blocked merely because ATTACK does not fit.

Risk may still reduce or reject the BASE request if its own budget requires it.

### REDUCE

In `FULL_GUARD` T2, the inherited drawdown reduction schedule has priority over ATTACK. A crisis/reduction state cannot be bypassed by CIBO.

### SUSPEND

SUSPEND is transient. It applies when current Risk budget is zero because the daily envelope is exhausted while capital headroom still exists.

It is recomputed at every later decision and at the next trading-day reset.

### LOCK

LOCK is reserved for the stronger case where Risk capital headroom is zero and Risk cannot authorize even the BASE envelope.

LOCK is not an independent permanent CIBO latch. Every later decision recomputes Risk budget; if budget becomes authorizable, CIBO may reactivate.

### REACTIVATE

If the previous CIBO decision was SUSPEND/LOCK and a later decision has positive Risk-authorizable BASE budget, T2 records REACTIVATE and then selects BUILD / PROTECT / REDUCE / ATTACK according to the same current-state rules.

CIBO does not manufacture budget. Reactivation exists only because Risk says budget exists.

## Frozen comparison arms

For each unchanged parent stop stream (`off`, `soft`, `be050-lock050-at100`, `aggressive`):

1. `RISK_ONLY_R100` — unchanged control.
2. `CIBO_T1_ABSORBING_CONTROL` — exact T1 BANK-as-floor behavior reproduced.
3. `CIBO_T2_BUDGET_REACTIVATION` — BANK reference + Risk-budget reactivation.
4. `CIBO_T2_BUDGET_REACTIVATION_FULL_GUARD` — same T2 semantics plus inherited REDUCE schedule.

All arms consume the exact same 152 generated signal identities. No market, anchor, side, or stop stream may be selected retrospectively.

## Monte Carlo freeze

Paired comparison uses the same calendar and moving-block machinery as T1:

- retained source calendar: 2024-08-13 through 2026-09-11;
- preserve no-trade weekdays;
- preserve same-day/same-anchor cross-market groups;
- moving block length: 5 trading days;
- horizon: 60 trading days;
- 10,000 paths per stop stream x controller;
- same deterministic seed `2026091318` for paired comparability.

No economic threshold determines CI success.

## Required outputs

For every stop stream/controller report at least:

- terminal return;
- peak/min equity;
- max capital DD;
- max daily DD;
- generated signals;
- executed trades;
- Risk reductions/rejections;
- BANK decisions;
- ATTACK groups/trades;
- REDUCE groups;
- SUSPEND groups;
- LOCK groups;
- REACTIVATE groups;
- posture counts;
- 60-day MC return distribution;
- P(terminal > 0);
- P(touch +5%);
- P(touch +10%);
- drawdown distribution;
- provider-boundary breaches.

## Governance

This T2 study is consumed-evidence research only. It cannot authorize a stop stream or controller for DEMO/LIVE based on these outcomes.

Any further threshold change requires a distinct T3 identity and a new pre-economic freeze.

- `DEMO_ELIGIBLE=false`
- `LIVE_AUTHORIZED=false`
- `PRODUCTION_AUTHORIZED=false`

No merge. No READY. No real capital.
