# VT08 CRT PURE — USDJPY R2-AE CANDIDATE FREEZE 001

**Candidate:** `USD_EFF5D_010_020_EXCLUDE_RECLAIM_025_050`  
**Status:** FROZEN BEFORE OLDER VALIDATION

Base:
- `EFF5D 0.10 <= efficiency < 0.20`
- R2-G `NEWEST_SUPERSEDES_CONFIRMATION_FIRST`

Single additional engineering rule:
- reject parent CRT when pre-C3 reclaim depth is
  `0.25 <= reclaim_depth_to_c1 < 0.50`.

Reason for selecting this ablation from R2-AC:
- it is one dimension only;
- the removed bucket is negative over consumed 2018-2026 evidence;
- removing it makes every consumed annual slice positive;
- it preserves more density than the 1D-drift alternative;
- it avoids the manipulation-depth alternative that would delete a bucket that is
  profitable over the full consumed window.

No other R2-AC clue is combined with this candidate.

Validation is frozen on 2014-09-21 -> 2018-09-21.

Validation gate:
- >=12 trades over 4Y;
- PF >=1.05;
- Total-R >0;
- DD <=8R;
- every annual Sep-to-Sep slice >0R.

Failure reopens USDJPY research. Thresholds do not move after validation.
