# CIBO Architect B — T02 Forward Structural OOS V1

Status: **FORWARD STRUCTURAL VALIDATION CONTRACT IMPLEMENTED / ECONOMIC ABLATION STILL REQUIRED**

T02 already has a frozen burned-data context calibration. This layer adds the
fresh-forward validation contract without changing those burned rules.

Key invariant: **negative PnL is not a structural-stop label**. Every stop/non-stop
classification requires an explicit terminal-reason evidence reference and must bind
to the canonical Phase20 outcome, execution-risk identity, settlement deals and
pre-decision provider evidence.

The audit:

- accepts only post-freeze `FORWARD_OBSERVED` decisions;
- uses the burned context rule fixed before the evaluated population;
- reads the matching context from the pre-decision Trader opportunity;
- requires at least 30 fresh candidate outcomes per eligible lineage;
- requires strict stop-incidence improvement and no worse p95 loss;
- requires provider/execution/settlement/terminal-reason binding;
- grants no sizing, leverage, Risk, execution, DEMO, LIVE or production authority.

Even if all structural gates pass, T02 remains open until a provider-bound causal
leverage ablation demonstrates economic value and safety. The sealed 2017H1 holdout
is not read by this contract.
