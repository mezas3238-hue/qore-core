# VT31 NAS100 — Sovereign Pure-Edge Certification Rule 001

**Owner:** Sergio Meza  
**Authority:** Owner sovereign directive  
**Source of truth:** GitHub `mezas3238-hue/qore-core`

## Canonical sentence

> **R IS NOT FORBIDDEN. SIZING TO OBTAIN CERTIFICATION IS FORBIDDEN.**

## Certification identity

VT31 may certify only through the quality of the trader itself:

`ENTRY EDGE + EXIT EDGE + WINNER PRESERVATION`

The certification exam must use neutral, equal trade weighting. Capital engineering
cannot improve, rescue, or manufacture the certification result.

## Forbidden for certification

The following may not be used to obtain, improve, or rescue certification:

- sizing;
- dynamic position sizing;
- reducing volume because a stop is wide;
- increasing volume to compensate prior losses;
- leverage as a certification improver;
- compounding as a certification improver;
- CIBO capital rescue;
- risk budgeting;
- portfolio allocation;
- route-dependent capital weighting;
- any capital rule that changes how much is traded in order to improve PF, DD,
  expectancy, survival, or another certification metric.

If a trade is too expensive, badly located, geometrically poor, or requires an
impractical stop, the trader must repair the trade itself. Lowering the lot is
not an edge repair.

## R is permitted inside the trader

R may be used freely when it is part of the trader's strategy and proves causal
edge.

Permitted examples include:

- entry logic expressed in R;
- stop movement after an R milestone;
- breakeven at +1R, +2R, +3R, or another tested level;
- partial exits by R;
- fixed or adaptive R targets;
- target extension from 2R to 3R, 5R, or beyond;
- R-based trailing;
- MFE/MAE rules expressed in R;
- combinations of market structure and R;
- profit protection by R multiples;
- cognition deciding whether an R rule should be used.

A rule is rejected because it damages edge, winner preservation, robustness, or
causality — **not merely because it is expressed in R**.

Therefore a rule such as `+3R -> breakeven` is eligible for research and
promotion if consumed-evidence tests show that it improves VT31 without
violating the certification gates.

## Exact separation

Forbidden:

> wide/expensive trade -> change lot size -> make the trade appear viable

Permitted:

> trade evolves -> use R, structure, liquidity, regime, volatility, M1 journey,
> or cognition to manage stop, target, trailing, partials, extension, or exit

## Universal volume invariance

VT31 must make the same market decision independently of absolute volume.

The market logic must not change between provider-permitted volumes such as:

`0.01`, `0.02`, `0.05`, `0.10`, `1.00`, etc.

VT31 produces the trade. Volume only scales the economic amount of that same
trade.

Provider minimums, maximums, lot steps, and rounding belong to the provider
adapter and cannot change VT31's market thesis.

## Certification economics

R remains the normalized language used to compare trades and calculate:

- expectancy;
- drawdown;
- payoff;
- MAE;
- MFE;
- PF;
- Monte Carlo;
- cost stress;
- winner preservation;
- temporal stability.

The certification harness must ignore sizing, volume, leverage, capital
weighting, compounding, and portfolio allocation.

## Final principle

> **DO NOT ADAPT CAPITAL TO SAVE THE TRADE.**
>
> **ADAPT THE TRADER — AND ALLOW THE TRADER TO USE R IF R IS PART OF ITS EDGE.**

This rule grants no merge, LIVE, real-capital, or production authority.
