# VT08 CRT PURE — AUDUSD OVERLAP FRESH VALIDATION FREEZE 001

**Frozen before holdout outcome:** 2026-09-23  
**PR:** #626  
**Validation identity:** VT08_CRT_PURE_R2BB_AUDUSD_OVERLAP_FRESH_2011_2016_001

## Candidate provenance

Development evidence is fully consumed 2016-2026.

R2-AX strongest broad confirmation-overlap loss state:
- dimension: confirmation_source_overlap
- excluded state: CONFOVERLAP_0_50_TO_0_75
- state sample: 724 trades
- state PF: 0.88089225
- state Total-R: -38.38341189R
- negative in 8/10 years
- residual retention: 70.6645%

Development residual arithmetic before protection:
- 1,744 trades / 10Y
- 174.4 trades/year
- +48.60915616R
- 6/10 annual windows positive

## Frozen candidate

- AUDUSD only
- ROLLING_H4
- Model #1 unchanged
- NEWEST_SUPERSEDES_CONFIRMATION_FIRST
- one hypothesis max per parent
- fixed 1.5R
- structural source stop
- exclude only CONFOVERLAP_0_50_TO_0_75
- BE_CLOSE_075 protection
- C3-close expiry

No other state may be excluded after seeing the holdout.

## Untouched historical holdout

2011-09-21 -> 2016-09-21

This window was not used to select the confirmation-overlap candidate.

## Advancement gate

All required:
- >=170 trades/year
- PF >=1.05
- Total-R >0
- >=60% years positive
- DD <= unfiltered BE_CLOSE_075 control on the same holdout

A failure is terminal for this frozen candidate.

Research only.

No merge / VPS / DEMO / LIVE / production / real capital.
