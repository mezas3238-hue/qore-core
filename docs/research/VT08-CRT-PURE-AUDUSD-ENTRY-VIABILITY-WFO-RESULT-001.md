# VT08 CRT PURE — AUDUSD ENTRY VIABILITY WFO RESULT 001

**Checkpoint:** 2026-09-23  
**PR:** #626  
**Run:** `35915813351 — SUCCESS`  
**Status:** DOA CLASSIFIER ECONOMICALLY FALSIFIED

## Contract

- AUDUSD
- 2011-09-21 -> 2026-09-21
- 4Y train -> next 1Y OOS
- same high-density CRT / Model #1
- fixed 1.5R
- BE_CLOSE_075
- C3-close expiry
- pre-entry features only
- 10/15/20/25% training-selected abstention
- minimum structural retention 75%

## Combined OOS baseline

- 2,733 trades
- PF 1.02370047
- +26.17989102R
- mean +0.00957918R/trade
- DD 61.10521583R
- dead-on-arrival 807 = 29.53%

## Combined OOS retained

- 2,130 trades
- 193.64 trades/year
- retention 77.94%
- PF 1.01967519
- +15.69064014R
- mean +0.00736650R/trade
- DD 58.01735463R
- positive OOS years 72.73%
- dead-on-arrival 559 = 26.24%

## Checks

- density >=170/year: PASS
- dead-on-arrival rate reduced: PASS
- PF improved: **FAIL**
- Total-R improved: **FAIL**

## Interpretation

R2-BH successfully predicts some dead-on-arrival risk, but DOA probability is not
the same objective as economic expectancy.

The classifier removed many weak setups, but also removed enough high-payoff
setups that aggregate PF and Total-R deteriorated.

Therefore:

- DOA probability alone is not promotable as the selection objective.
- The root cause remains pre-entry selection.
- The next model must estimate **expected R / economic quality**, not merely stop
  probability.
- No BH threshold or abstention fraction may be tuned post-result.

No merge / VPS / DEMO / LIVE / production / real capital.
