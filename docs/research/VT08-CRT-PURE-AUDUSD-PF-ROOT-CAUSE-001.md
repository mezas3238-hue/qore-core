# VT08 CRT PURE — AUDUSD PF ROOT-CAUSE ATTRIBUTION 001

**Checkpoint:** 2026-09-23  
**PR:** #626  
**R2-BF run:** `35905661816 — SUCCESS`  
**R2-BG run:** `35905945261 — SUCCESS`  
**Status:** ROOT CAUSE LOCALIZED TO PRE-ENTRY SELECTION

## R2-BF — 15Y PF loss attribution

Population: CONTROL_BE075, 2011-09-21 -> 2026-09-21.

- 3,727 trades
- PF 1.03599027
- +53.20596109R
- mean +0.01427581R/trade
- break-even all-in friction: only 0.01427581R/trade
- gross profit 1,531.54875534R
- gross loss 1,478.34279425R

Loss mechanism:
- 1,272 original full stops = -1,272R
- full stops account for ~86.04% of gross loss
- fixed 1.5R targets contribute +1,126.5R
- C3-close exits contribute +198.70596109R net

Important pre-entry contrasts:

### Timing
H4 slots 1-3:
- 1,897 trades
- PF 0.95030080
- -37.40379802R

H4 slots 4-6:
- 1,830 trades
- PF 1.12485169
- +90.60975911R

H4 slot 5 alone:
- 654 trades
- PF 1.27316538
- +68.54874187R

All other slots:
- 3,073 trades
- PF 0.98749978
- -15.34278078R

### Reference multiplicity
REF1:
- 2,501 trades
- PF 0.97869956
- -22.45220272R

REF2+:
- 1,226 trades
- PF 1.17832536
- +75.65816381R

### Confirmation delay
D2:
- 953 trades
- PF 0.94085113
- -23.82117227R

NOT_D2:
- 2,774 trades
- PF 1.07161249
- +77.02713336R

These are attribution clues, not promoted filters.

## R2-BG — full-stop trajectory forensics

Same CONTROL_BE075 population.

Full structural stops:
- 1,272 / 3,727 trades = 34.13%

Completed-M15-close trajectory before full stop:

### Selection-failure proxy
Never achieved a positive completed M15 close:
- 895 trades
- 70.36% of all full stops

Positive close but never +0.25R:
- 182 trades
- 14.31%

Combined pre-entry/entry failure proxy:
- 1,077 trades
- **84.67% of all full stops**

### Retention-failure proxy
Reached +0.25R but < +0.50R:
- 126 trades
- 9.91%

Reached +0.50R but < +0.75R:
- 69 trades
- 5.42%

Combined retention-failure proxy:
- 195 trades
- **15.33% of full stops**

Reached +0.75R before full stop:
- 0 trades

Median maximum completed-close progress among full stops:
- 0R

## Root-cause adjudication

The dominant PF failure is **pre-entry setup selection / entry viability**.

It is not primarily:
- C3 expiry: R2-BA NEXT_H4 worsened PF and DD;
- lack of BE protection: R2-AZ improved economics but did not solve PF;
- post-entry retention: only 15.33% of full stops first established >= +0.25R on a completed M15 close.

The next research layer must therefore predict setup viability using only information
known before the entry open.

No direct filter is promoted from timing, D2, REF1 or any single retrospective
bucket.

No merge / VPS / DEMO / LIVE / production / real capital.
