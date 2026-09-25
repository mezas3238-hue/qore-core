# VT08 CRT PURE — AUDUSD LIFECYCLE EXTENSION FREEZE 001

**Frozen:** 2026-09-23 before R2-BA outcomes  
**PR:** #626

## Source population

Exact R2-AY OOS-retained entries:
- 1,463 trades
- 209 trades/year

Post-entry protection:
- R2-AZ BE_CLOSE_075
- protection only after completed M15 close
- effective from next M15 bar
- stop never widens

Destination:
- fixed 1.5R unchanged

## R2-BA single changed dimension

### CONTROL_C3_CLOSE
Position lifecycle ends at the original C3 close.

### NEXT_H4
If the position is still active at C3 close:
- permit exactly one additional contiguous H4 block;
- original fixed 1.5R destination remains;
- BE_CLOSE_075 remains active;
- STOP_FIRST remains active;
- no new entry or signal is created.

If the full 16-bar M15 extension is unavailable:
- fail closed to the C3-close control;
- do not synthesize data.

## Advancement gate

NEXT_H4 requires all:
- density >=170 trades/year
- PF >=1.05
- Total-R >0
- >=60% OOS years positive
- DD <= CONTROL_C3_CLOSE

No shorter/longer extension may be selected retrospectively from this result.

## Limitation

Portfolio overlap/concurrency caused by positions surviving past C3 is not yet
adjudicated. Even an economic PASS requires a separate overlap/OCO census before
any candidate advancement.

Research only.

No merge / VPS / DEMO / LIVE / production / real capital.
