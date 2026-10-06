# VT31 NAS100 — Stale-Sequence Cognitive Exit Findings 001

**Owner:** Sergio Meza  
**Status:** CONSUMED-EVIDENCE DEVELOPMENT FINDINGS  
**Workflow:** `37470039752` — SUCCESS

## Stable discovery

Observation-only first-material-adverse forensics found:

`current_open_r <= -0.50R + MIXED context + reclaim age 8-14m`

with zero recoveries in every consumed fold:

- R5: 3/3 losses;
- R6: 2/2 losses;
- R8: 3/3 losses;
- recent: 5/5 losses.

Total: `13/13` losses.

The 8-14 minute sequence state predates this experiment in VT31 reasoning as
`EXPERIENCE:SEQUENCE_STALE_8_14_REQUIRES_REEVALUATION`, so the replay did not
invent a new threshold after reading those outcomes.

## Causal replay

The predeclared `COG_EXIT_STALE_MIXED` executes at the next M1 open, never
the signal M1 close.

It survived PF / mean / DD / winner-preservation / temporal development gates
4/4.

Recent:

- DD: `10.5714R -> 9.7564R`;
- PF: `1.5537 -> 1.6340`;
- mean: `+0.4492R -> +0.4891R`;
- MC positive: `81.54% -> 84.04%`;
- winner count: 100% preserved;
- winner-R: 100% preserved.

## Stronger composition

The union:

`COG_EXIT_CAUTION_OR_STALE_MIXED`

also survived all current development gates and is the preferred research
comparator.

Recent:

- observed DD: `9.3398R`;
- PF: `1.6569`;
- mean: `+0.4998R`;
- MC positive: `84.74%`;
- MC p95 DD: `17.77R`;
- winners and winner-R: preserved.

## What remains

VT31 is still **NOT CERTIFIED**.

The hard blocker remains observed DD above `6R`; Monte Carlo robustness is
also below the current standard.

The next work is residual first-material-adverse attribution **after excluding
trades already changed by Comparator 002**, with richer causal interactions
among:

- entry family / side;
- entry vs current H1/M15 transition;
- prior-day / location;
- reference volatility;
- path efficiency / overlap;
- structure-event family and age;
- confirmation / evidence age;
- reclaim age.

Outcome remains retrospective attribution only and has zero runtime authority.

Fresh holdout remains sealed.
