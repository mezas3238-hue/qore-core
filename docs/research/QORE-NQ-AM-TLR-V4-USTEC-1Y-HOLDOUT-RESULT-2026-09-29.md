# QORE NQ AM TLR V4 — EXISTING CORE USTEC 1Y HOLDOUT RESULT

Date: 29-SEP-2026  
Issue: #657  
PR: #654  
Identity: `QORE_NQ_AM_TLR_V4_USTEC_CAPABILITY_001`

## Evidence source

Per Owner instruction, the test reused the USTEC/NAS100 M1 holdout already
retained by QORE Core instead of downloading a new three-year corpus.

Source:
- workflow run: `34981033027`
- artifact id: `10402199719`
- artifact:
  `qore-vt31-r8-fresh-validation-3e9efe7b47f645558926fb1c6f1dc32fe45f50d9`
- artifact digest:
  `sha256:9f5df4eba1882cb498b4e3657176f34a7c27083f3ac1af7856ebddf01447f34d`
- NAS100/USTEC evidence SHA-256:
  `4031c7e21bb311fdb99d7b1028fd9ff154ace1dc4886249ff978b700fdeeedcb`
- provider symbol: `USTEC`
- resolution: M1
- retained source coverage:
  `2016-04-19T00:00:00Z -> 2018-05-18T20:55:00Z`

Frozen methodology evaluation:
`2016-04-20 NY -> 2017-04-20 NY` (end exclusive)

The preceding retained day was used only as causal warm-up.

## Authoritative run

- workflow: `36508974521`
- git SHA: `563266ecafe0e5549a752a66d7343a67289cb258`
- result artifact: `11008296984`
- result artifact digest:
  `sha256:73e7ca4e3ac6aae7171493ab977bc23dd5a29c5325b6fa2f340f2f39fa473d2d`
- workflow conclusion: GREEN

Quality:
- Ruff GREEN
- mypy GREEN
- focused tests GREEN
- freeze assertions GREEN
- retained holdout identity/hash validation GREEN
- one-year study GREEN

## Primary candidate

`ROLLING_AM_LOW_M2`

Result:
- trades: **1**
- wins: **0**
- losses: **1**
- primary Total R: **-1.05R**
- primary PF: **0.00**
- max DD: **1.05R**
- stress Total R: **-1.10R**
- exit: stop
- mean MFE: **0.9424R**
- mean MAE: **1.1518R**

Funnel across the evaluated year:
- not gap-down: 120 sessions
- opening-delivery signature failed: 78
- no macro penetration: 30
- body accepted below reference: 5
- executable trades: 1

Adjudication:
`INSUFFICIENT_SAMPLE`

The frozen primary does not provide enough executions to establish USTEC
capability, and the only observed primary trade lost.

## Predeclared diagnostics

Diagnostics had zero promotion authority and cannot replace the frozen primary
after observing P&L.

Notable rows:

### ROLLING_AM_LOW_NONE
- trades: 4
- wins: 3
- losses: 1
- Total R: **+4.4588R**
- PF: **5.2464**
- max DD: **1.05R**
- stress Total R: **+4.2588R**
- PF stress: **4.8716**

### ROLLING_AM_LOW_M1
- trades: 2
- wins: 1
- losses: 1
- Total R: **+0.7739R**
- PF: **1.7371**
- max DD: **1.05R**

### NEAREST_PRIOR_DAILY_LOW_NONE
- trades: 2
- Total R: **-0.2594R**
- PF: **0.7530**

### TWO_SD_OPENING_GAP_EXTENSION family
- M1/M2/M5: **0 trades**
- NONE: **0 trades**

## Interpretation

The one-year USTEC holdout does not support the frozen M2 implementation because
it is too sparse to adjudicate and its sole trade lost.

The diagnostic matrix does show a potentially interesting signal: the
`ROLLING_AM_LOW` architecture becomes economically positive when the arbitrary
hard opening-signature gate is weakened or removed. However, that observation is
post-result diagnostic evidence. It cannot be promoted directly without creating
a new preregistered identity.

The strongest engineering conclusion from this holdout is therefore:

`ROLLING_AM_LOW` deserves a source-fidelity V5 investigation focused on how the
opening-delivery condition should be represented causally, while the fixed 2SD
reference family currently has no executable support in this USTEC year.

## Authority

Research only.

`DEMO_ELIGIBLE=false`  
`LIVE_AUTHORIZED=false`  
`REAL_CAPITAL_AUTHORIZED=false`  
`PRODUCTION_AUTHORIZED=false`

No merge without explicit Owner order.
