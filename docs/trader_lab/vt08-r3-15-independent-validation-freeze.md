# VT-08 R3.15 — Final Independent Validation / DEMO Eligibility Freeze

Status: PRE-HOLDOUT FREEZE. This file is committed before any access to the protected R3.15 holdout.

## Parent evidence

- Parent: VT-08 R3.14 exact green HEAD `266fa60df2654ffcbce3a89569295bb19f791022`.
- Official R3.14 run: `34737134896` — SUCCESS.
- R3.14 artifact: `10311039498`.
- R3.14 artifact digest: `sha256:4745b610b4fe590b94dd715ef2e31d878971d768e96cf84ad6883a2d98869ac8`.
- Source video SHA256: `bfe76fa4346ec4d7442886c21834aa26f0d82172bdb55666e8c77226cdf83271`.
- Source case: `VT08_SOURCE_CASE_CLOSED_WITH_PERMANENT_CONTAINMENTS`.

## Frozen Trader / methodology

No strategy, market, direction, entry, stop, target, lifecycle, execution-model or portfolio choice may be changed after this commit based on R3.15 results.

- Trader: VT-08 B01 R3.8 executable methodology.
- H4 anchors: 01/05/09 New York; 13 excluded.
- Markets: AUDJPY, AUDUSD, EURUSD, GBPJPY, GBPUSD, USDCAD, USDJPY.
- Completed-C2 reversal subset; C3 excluded.
- One-side sweep, close-inside, Protected Swing/CISD.
- Entry: current/new H4 open.
- Stop: Protected Swing.
- Target: fixed 2R.
- H4 boundary containment.
- Execution model: `b01-open-fill-ps-no-offset-2r-h4-close-containment-v1`.
- Frozen portfolio for certification: B COMBINED = A CORE (AUDJPY SHORT + GBPUSD SHORT) + GBPJPY RETURN ENHANCER (GBPJPY LONG + GBPJPY SHORT).

## Frozen Risk role

The temporary R3.14 Challenge Risk is NOT the funded/DEMO operating policy and cannot be used to obtain R3.15 admission.

Funded/DEMO Risk remains R3.12 `balanced-adaptive-v1`:
- A base: 25 bps (0.25%).
- GBPJPY base: 20 bps (0.20%).
- Challenge risk state is discarded before funded/DEMO operation.

The governed Risk Trader-Lab review for R3.15 is frozen before holdout access as:
- policy id: `vt08-r315-final-demo-v1`;
- minimum independent sample size: 30 completed return observations;
- maximum population variance: 0.01 return-units squared.

These thresholds may not be weakened after holdout access.

## Protected independent holdout

One-time protected window: `[2020-07-01, 2022-07-01)`.

Rules:
1. This window has not been accessed by R3.11–R3.14 and is opened only after this freeze commit.
2. No parameter search, market filtering, direction change, Risk-threshold change or rule tuning is permitted after viewing it.
3. Results are retained whether favorable or unfavorable.
4. R3.15 is the independent-validation use of this window; after access it becomes consumed evidence.

## Formal promotion contract

VT-08 is declared `DEMO_ELIGIBLE` only if the repository's canonical authority chain succeeds without bypass:

`REPLAY -> FAST_FORWARD -> OOS -> STRESS -> MONTE_CARLO -> RISK_REVIEW -> CIBO_REVIEW -> INDEPENDENT_VALIDATION -> ECONOMIC_EVIDENCE -> evaluate_demo_eligibility`

Required outcomes:
- exact frozen candidate/run/strategy lineage;
- fresh holdout evidence retained;
- Risk owner APPROVED under the frozen policy above;
- CIBO owner APPROVED;
- Independent Validation owner APPROVED;
- exact `ECONOMIC_EVALUATION` evidence bound to the candidate;
- canonical `evaluate_demo_eligibility` returns `demo_eligible`;
- full quality gate passes on the exact evidence-producing HEAD.

If any mandatory authority rejects or the holdout cannot provide the frozen minimum sample, R3.15 fails closed. The failure may not be converted into approval by editing this freeze after observing the holdout.

## Authority boundary

R3.15 may grant cTrader DEMO eligibility only. `LIVE_AUTHORIZED=false`, Production/real capital remain prohibited. PR remains DRAFT and unmerged unless separately authorized by the Human Owner.
