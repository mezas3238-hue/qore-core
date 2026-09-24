# VT08 CRT PURE — R2-BN USDJPY Root-Cause Expected-R WFO

Identity: `VT08_CRT_PURE_R2BN_USDJPY_ROOT_CAUSE_EXPECTED_R_WF_001`

Status: economic hypothesis FAILED. Research only. No certification, runtime, DEMO, LIVE, production, merge, or capital authority.

## Frozen contract

- Market: USDJPY only.
- Source population: exact R2-BL 2014-2026 high-density population.
- WFO: prior 4Y -> next 1Y.
- Objective: Expected-R.
- Fixed training-score abstention: 20%.
- Empirical-Bayes shrinkage; minimum cell support 30; prior strength 100.
- Small causal memories only:
  - REF_DELAY
  - REF_DELAY_DIRECTION
  - TIMING_REF_DELAY
- No AUDUSD outcomes or learned states transferred.

## Combined OOS result

Baseline: 1,968 trades, PF 0.88942, -97.55R, mean -0.04957R, DD 107.53R.

| Head | Trades | Trades/y | PF | Total R | Mean R | DD R | Positive OOS years |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| REF_DELAY | 1331 | 166.38 | 0.91298 | -50.96 | -0.03829 | 64.18 | 25% |
| REF_DELAY_DIRECTION | 1429 | 178.63 | 0.89284 | -67.02 | -0.04690 | 79.02 | 25% |
| TIMING_REF_DELAY | 1553 | 194.13 | 0.90771 | -61.84 | -0.03982 | 73.61 | 25% |

All cost-stressed variants remain negative.

## Adjudication

The small Expected-R memories reduce portions of the loss but do not create positive expectancy. This family is frozen as failed for USDJPY and must not be promoted or tuned further by adding dimensions.

Per the continuity contract, the next USDJPY line is passive-entry research learned independently from USDJPY. No AUDUSD winning entry arm is transferred.
