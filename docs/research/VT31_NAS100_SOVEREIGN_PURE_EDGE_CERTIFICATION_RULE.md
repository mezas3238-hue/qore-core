# VT31 NAS100 — Sovereign Pure-Edge Certification Rule

**Owner:** Sergio Meza  
**Status:** SOVEREIGN / NON-NEGOTIABLE  
**Scope:** VT31 NAS100 optimization, runtime behavior and certification

## Certification identity

VT31 is certified only by:

`ENTRY EDGE + EXIT EDGE + WINNER PRESERVATION`

The trader must create the same market decision independently of selected
volume.

## Forbidden as certification or runtime rescue

VT31 may not improve its certification result by using:

- sizing;
- dynamic position sizing;
- leverage;
- compounding;
- CIBO capital rescue;
- risk-based volume reduction;
- volume escalation after losses;
- risk budgeting;
- portfolio allocation;
- capital weighting;
- any rule that decides how much to trade from an R value.

## R boundary

R is an **evaluation metric only**.

R may be calculated after or alongside a completed replay for:

- expectancy;
- drawdown;
- payoff;
- MAE;
- MFE;
- profit/loss normalization;
- temporal stability;
- Monte Carlo;
- certification scorecards.

R may **not** trigger or select:

- entry;
- WAIT / EXECUTE / ABSTAIN;
- entry price;
- initial invalidation;
- target;
- partial target;
- breakeven move;
- trailing action;
- exit;
- rearm;
- volume.

Therefore runtime rules such as:

- exit at +0.50R / +0.75R / +1.00R;
- partial at 1.25R;
- move stop at 3R;
- protect because MFE reached N R;
- scratch because close is <= -N R;

are non-certifiable and cannot be promoted.

Historical burned studies using such thresholds remain evidence only.

## Market-native entry authority

Entry decisions must derive from causal market information, including:

- market structure;
- liquidity;
- context;
- regime;
- volatility;
- timing;
- H1;
- M15;
- M1;
- full VT31 cognition;
- opportunity quality;
- execution precision.

If geometry is poor, VT31 must repair:

- entry timing;
- entry location;
- confirmation;
- M1 translation;
- invalidation placement;
- stale opportunity handling;
- context interpretation.

It may not hide poor geometry by reducing trade size.

## Market-native exit authority

Exit/management decisions must derive from the market itself:

- structural destination;
- liquidity delivery or failure;
- confirmed exhaustion;
- regime change;
- momentum deterioration;
- structural invalidation;
- confirmed protective swing;
- structural trailing;
- target intelligence.

No fixed R cap is an exit authority.

## Universal volume invariance

VT31 must remain logically identical at:

`0.01, 0.02, 0.05, 0.10, 1.00, ...`

Volume only scales the economic value of the already-created operation.

Formally:

`MARKET STATE -> VT31 DECISION`

must be independent of:

`volume / lot size / leverage / account balance / risk budget`.

## Certification consequence

A trade that is bad at 0.01 is a bad trade.

A trade that is good at 0.01 must represent the same opportunity at any other
permitted volume.

The certification path is:

`MARKET -> ENTRY -> MARKET-NATIVE MANAGEMENT -> EXIT -> POST-TRADE R METRICS -> EDGE CERTIFICATION`

not:

`MARKET -> CAPITAL ADAPTATION -> SAVED RESULT`.

## Current research disposition

The following Architect-B studies remain useful only as burned diagnostics and
are not promotable runtime authorities because they used R thresholds:

- deep-giveback rescue R frontiers;
- fixed +0.25R / +0.50R / +0.75R / +1.00R locks;
- closed +1R journey checkpoints;
- MFE-R / close-R early-no-progress scratches;
- inherited 3R breakeven;
- inherited 1.25R partial target.

Future research may reuse the market observations discovered by those studies
only after translating them into causal price/structure/liquidity/volatility
states that do not depend on R.

## Governance

- fresh holdout remains sealed until a pure-edge candidate is frozen;
- no merge without Owner instruction;
- no LIVE;
- no real capital;
- no production authorization.
