# CIBO Provider Economics — Stress-Bound Alternative V1

Status: **CORE PRE-HOLDOUT LANE / PROVIDER DEPLOYMENT REMAINS GATED**

CIBO certification and provider deployment are separate questions.

The authorized cTrader DEMO account currently contains an insufficient
execution sample for a statistically meaningful empirical slippage model.
The immutable read-only inventory contains only three entry deals across the
six CIBO symbols, one MARKET entry and one QORE-labelled MARKET entry.

CIBO Core therefore uses the already-existing Phase20C predeclared adverse
matrix as its pre-holdout provider-uncertainty bound.  No parameter is selected
after observing the shadow outcomes.  The matrix includes baseline, spread x2,
commission x2, USD 4 slippage floor, margin x2, 2-second delay, explicit
liquidity-unavailable and minimum-volume-cliff fail-closed cases, plus the
combined adverse scenario.

This lane proves **Core uncertainty governance**, not broker execution quality.
It may satisfy the Core pre-holdout provider-economics prerequisite only when
current provider terms are frozen and the stress matrix remains immutable,
non-improving, outcome-untuned and policy-pass-untuned.

It does not claim:

- empirical slippage calibration;
- cTrader DEMO deployment readiness;
- FundedNext deployment readiness;
- historical 2017 provider economics;
- LIVE or real-capital authority.

Before any provider is used productively, that provider still needs its own
provider/account calibration and sovereign QORE Risk approval.
