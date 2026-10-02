# CIBO Phase22 — Holdout V1 burn forensics

Status: V1 REJECTED / PRIOR OUTCOME BURN CONFIRMED

## Finding

The candidate `CIBO_USD60_6M_HOLDOUT_2017H1_V1` is not fresh for all
lineages.

Immutable VT31 R8 artifact `10402199719` contains M1 market evidence spanning
`2016-04-19T00:00:00Z` through `2018-05-18T20:55:00Z` and the R8 fresh
validation executed Trader outcomes across that interval.

The retained R8 outcome set contains **12 trades inside 2017H1**:

- NAS100: **7**
- US30 transfer-market evidence under the same VT31 R8 candidate: **5**

Examples begin on 2017-01-31 and continue through June 2017. Therefore the
interval was outcome-consumed before Phase22 even though the R8 candidate was
ultimately rejected.

Candidate rejection does not restore statistical freshness.

## Governance consequence

- V1 2017H1 is marked `BURNED`.
- Its old pre-holdout freeze is revoked.
- Its source receipt remains useful only as immutable source-provenance evidence
  and is marked `REJECTED_PRIOR_OUTCOME_BURN`.
- No additional V1 Trader outcomes may be executed for certification.
- No result from V1 may be used for retuning.

## Next preregistered candidate

Without inspecting candidate outcomes, the next deterministic interval is the
latest exact six-calendar-month block ending at the earliest now-confirmed burn
boundary:

`2015-10-19T00:00:00Z → 2016-04-19T00:00:00Z`

Candidate id:

`CIBO_USD60_6M_HOLDOUT_2015-10-19_2016-04-19_V2`

Its status is `SOURCE_VALIDATION_PENDING`. Source availability must be proven
read-only before any Trader logic is allowed to run.

## Authority

No LIVE, production, VPS, FundedNext, real-capital, merge or outcome-mining
authority is granted.
