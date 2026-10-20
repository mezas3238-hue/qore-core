# VT08 CRT PURE — AUDUSD CONFIRMATION GEOMETRY FREEZE 001

**Frozen:** before R2-AX / R2-AY outcome inspection  
**PR:** #626  
**Scope:** AUDUSD high-density core only

## Base core

- ROLLING_H4
- FIXED_1_5R
- EFF OFF
- NEWEST_SUPERSEDES_CONFIRMATION_FIRST
- max one selected Model #1 hypothesis / parent
- source structural stop
- C3-close expiry
- STOP_FIRST

## R2-AX attribution family

Only information known by the next contiguous M15 entry open:

- confirmation body fraction
- direction-normalized confirmation close location
- confirmation range / source range
- confirmation range / C1 range
- direction-normalized confirmation displacement beyond source open
- confirmation/source range overlap
- confirmation close-through-source-extreme flag
- next-open gap / confirmation range

Frozen interactions:
- body x close-location
- displacement x overlap
- confirmation-range/source x close-through-source-extreme

R2-AX is attribution only. It cannot promote a filter.

## R2-AY causal walk-forward

- training: immediately preceding 3 years
- OOS: next 1 year
- one confirmation-state exclusion max
- state must be negative in all 3 training years
- >=8 removed trades in every training year
- >=75% training trades retained
- most negative aggregate qualifying state selected
- if none qualify: no exclusion
- selection frozen before OOS

## Advancement gate

All required:

- retained density >=170 trades/year
- PF >=1.05
- Total-R >0
- >=60% OOS years positive
- OOS max DD <= corresponding baseline OOS max DD

No threshold may be modified after R2-AX/R2-AY results.

## Governance

Research only.

No:
- merge
- VPS
- DEMO
- LIVE
- production
- real capital
