# CIBO Architect 2 — Integrator Patch Request 008

## T11 market-impact runner contract remains fail-closed

Checkpoint: `2026-10-01`

Architect-2 branch:

`agent/cibo-external-scientific-closure-001`

Observed runner blob:

`f4f89aa7024082ad0718c537ee3cf1a5028ff61c`

The T11 market-impact workflow is intentionally failing in its **Quality before
broker mutation** step.  GitHub run `36943060044` confirms that credential
verification and the DEMO mutation step were skipped.

This is not an empirical T11 failure.  It is a runner-contract mismatch.

## Frozen scientific contract

The pre-evidence T11 freeze requires:

- cTrader DEMO only;
- six frozen symbols;
- provider-minimum child orders only;
- 1x versus 2x aggregate exposure;
- for 2x, both children open before either child is closed;
- realized all-in settlement cost in the USD deposit asset;
- balanced long/short matched pairs;
- alternating L1→L2 / L2→L1 pair ordering;
- eight calibration pairs per level per symbol;
- four temporally disjoint validation pairs/folds per level per symbol;
- no Phase22 V2 outcomes;
- no FundedNext, VPS, LIVE or real capital;
- no productive authority.

## Current runner mismatch

Against the executable runner source, the Architect-2 readiness audit finds
these required markers absent:

1. `T11_NONLINEAR_INPUT_FREEZE`
2. `def source_minimum_volume`
3. `def pair_plan`
4. `all children are open before any close begins`
5. `deposit_asset="USD"`
6. `"two_x_children_open_before_close": True`
7. `"metric": "ADVERSE_REALIZED_ALL_IN_SETTLEMENT_COST_USD"`

The source already contains the newer evaluator fields
`realized_settlement_cost_total_usd` and `level_order_position`, but that is
not enough to authorize the experiment.

## Requested disposition

Do **not** mark T11 terminal and do **not** treat a successful lint/type check as
market-impact evidence.

The authorized runner must first satisfy
`cibo_arch2_t11_runner_readiness.assess_t11_runner_source(...)` with
`RUNNER_CONTRACT_READY`. Only then may a separately authorized DEMO evidence
run produce the frozen 144-episode / 216-child population.

Architect 2 does not assign the canonical ledger disposition and does not grant
broker or productive authority.
