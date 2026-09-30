from datetime import UTC, datetime

from qore.infrastructure.cibo_ce2i_provider_economics_component_freeze import (
    freeze_current_ctrader_demo_provider_economics,
)


def test_current_provider_terms_freeze_without_overclaiming_slippage() -> None:
    freeze = freeze_current_ctrader_demo_provider_economics(
        frozen_at=datetime(2026, 9, 30, 20, 15, tzinfo=UTC)
    )

    assert freeze.point_in_time_terms_frozen is True
    assert freeze.spread_terms_frozen is True
    assert freeze.commission_terms_frozen is True
    assert freeze.expected_margin_terms_frozen is True
    assert freeze.volume_contract_terms_frozen is True
    assert freeze.empirical_slippage_frozen is False
    assert freeze.execution_model_frozen is False
    assert freeze.historical_2017_exact_claimed is False
    assert freeze.holdout_outcomes_used is False
    assert freeze.target_aware is False
    assert freeze.broker_mutation_performed is False
    assert freeze.pre_holdout_provider_economics_ready is False
    assert freeze.productive_authority is False
    assert freeze.blockers == (
        "EMPIRICAL_SLIPPAGE_NOT_FROZEN",
        "EXECUTION_MODEL_NOT_FROZEN",
    )
    assert "artifact:11104595302" in freeze.source_evidence_ref
