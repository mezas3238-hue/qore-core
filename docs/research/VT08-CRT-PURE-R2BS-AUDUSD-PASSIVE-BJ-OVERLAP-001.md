# VT08 CRT PURE — R2-BS AUDUSD Passive/BJ Overlap

Identity: `VT08_CRT_PURE_R2BS_AUDUSD_PASSIVE_BJ_OVERLAP_001`

Status: completed research decomposition. No combined candidate promoted.

## Question

Does the frozen R2-BJ `REF_DELAY_DIRECTION` selector contain information that remains useful when the execution is the corrected R2-BM `CONF_RANGE_MID` passive entry?

## Common OOS population

- BJ OOS baseline signals: 2,733.
- BJ retained: 2,014.
- BJ rejected: 719.
- Passive fills in the common OOS window: 1,776.
- Passive fills among BJ retained: 1,294.
- Passive fills among BJ rejected: 482.

Fill rates were similar:
- BJ retained signals: 64.25%.
- BJ rejected signals: 67.04%.

Therefore BJ is not merely selecting higher passive fill probability.

## Corrected passive economics

### All common OOS passive fills

- 1,776 trades.
- PF 0.97837.
- -17.94R.
- mean -0.01010R/trade.
- DD 44.45R.
- cost 0.02R: PF 0.93715 / -53.46R.
- cost 0.05R: PF 0.87907 / -106.74R.

### BJ-retained passive fills

- 1,294 trades.
- PF 1.01676.
- +10.02R.
- mean +0.00774R/trade.
- DD 27.06R.
- cost 0.02R: PF 0.97411 / -15.86R.
- cost 0.05R: PF 0.91398 / -54.68R.

### BJ-rejected passive fills

- 482 trades.
- PF 0.87945.
- -27.96R.
- mean -0.05800R/trade.
- DD 34.54R.
- cost 0.02R: PF 0.84194 / -37.60R.
- cost 0.05R: PF 0.78920 / -52.06R.

## Adjudication

R2-BJ contains real directional information: its rejected population is materially worse than its retained population even under corrected passive execution.

However, the retained population remains economically insufficient and fails reasonable friction. Therefore BJ must not be promoted as a combined passive candidate.

The next causal experiment is R2-BT: train Expected-R on the passive opportunity itself (filled passive R, otherwise 0R) instead of applying a next-open-trained label to passive execution.

Governance remains research-only.
