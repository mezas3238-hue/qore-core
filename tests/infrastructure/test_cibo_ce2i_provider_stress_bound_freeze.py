from datetime import UTC, datetime

from qore.infrastructure.cibo_ce2i_provider_stress_bound_freeze import (
    EMPIRICAL_INVENTORY_ARTIFACT_ID,
    build_provider_stress_bound_freeze,
    provider_stress_matrix_sha256,
)


def _inventory() -> dict[str, object]:
    return {
        "schema": "qore.cibo.ctrader_demo.empirical_slippage.v1",
        "status": "EMPIRICAL_SLIPPAGE_NOT_READY",
        "provider_key": "ctrader-demo",
        "environment": "demo",
        "account_entry_deals_found": 3,
        "market_entry_deals_found": 1,
        "qore_deals_found": 1,
        "empirical_slippage_calibrated": False,
        "execution_model_ready": False,
        "broker_mutation_performed": False,
        "holdout_outcomes_used": False,
        "historical_2017_exact_claimed": False,
        "target_aware": False,
        "productive_authority": False,
    }


def test_predeclared_stress_bound_closes_core_not_deployment() -> None:
    freeze = build_provider_stress_bound_freeze(
        empirical_inventory=_inventory(),
        frozen_at=datetime(2026, 10, 1, 14, 0, tzinfo=UTC),
    )

    assert freeze.empirical_inventory_artifact_id == EMPIRICAL_INVENTORY_ARTIFACT_ID
    assert freeze.empirical_population_sufficient is False
    assert freeze.empirical_slippage_claimed is False
    assert freeze.core_pre_holdout_ready is True
    assert freeze.provider_deployment_ready is False
    assert freeze.core_blockers == ()
    assert freeze.deployment_blockers
    assert len(freeze.scenario_ids) == 9
    assert freeze.scenario_matrix_sha256 == provider_stress_matrix_sha256()
    assert freeze.outcome_tuned is False
    assert freeze.policy_pass_tuned is False
    assert freeze.historical_provider_economics_claimed is False
    assert freeze.holdout_outcomes_used is False
