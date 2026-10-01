from __future__ import annotations

from qore.infrastructure.cibo_arch2_provider_economics_terminal_recommendation import (
    LEGACY_REQUIREMENT,
    RECOMMENDATION,
    SUPERSEDING_CONTRACT,
    build_provider_economics_terminal_recommendation,
)


def test_provider_economics_is_recommendable_as_proven_supersession() -> None:
    recommendation = build_provider_economics_terminal_recommendation()

    assert recommendation.workstream_id == "PROVIDER_ECONOMICS"
    assert recommendation.recommendation == RECOMMENDATION
    assert recommendation.recommendation == "SUPERSEDED_WITH_PROVEN_LINEAGE"
    assert recommendation.legacy_requirement == LEGACY_REQUIREMENT
    assert recommendation.superseding_contract == SUPERSEDING_CONTRACT
    assert recommendation.current_empirical_provider_plane_ready is True
    assert recommendation.historical_market_plane_required is True
    assert recommendation.predeclared_provider_cost_application_required is True
    assert recommendation.historical_provider_fill_claims_forbidden is True
    assert recommendation.historical_provider_order_refs_forbidden is True
    assert recommendation.historical_provider_deal_refs_forbidden is True
    assert recommendation.historical_provider_settlement_claims_forbidden is True
    assert recommendation.exact_historical_provider_economics_claimed is False
    assert recommendation.holdout_outcomes_used is False
    assert recommendation.terminal_disposition_assigned is False
    assert recommendation.productive_authority is False
