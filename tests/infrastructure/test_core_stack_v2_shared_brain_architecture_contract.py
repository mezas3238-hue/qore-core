from __future__ import annotations

from qore.infrastructure.core_stack_v2.shared_brain_architecture_contract import (
    SHARED_BRAIN_ARCHITECTURE_VERSION,
    shared_brain_architecture_contract,
)


def test_shared_brain_architecture_preserves_sovereignty() -> None:
    contract = shared_brain_architecture_contract()

    assert contract["version"] == SHARED_BRAIN_ARCHITECTURE_VERSION
    sovereignty = contract["sovereignty_law"]
    assert sovereignty["shared_is_not_a_trader"] is True
    assert sovereignty["specialist_traders_remain_sovereign"] is True
    assert sovereignty["qore_risk_remains_sovereign"] is True
    assert sovereignty["execution_remains_sovereign"] is True
    assert sovereignty["shared_direct_order_authority"] is False
    assert sovereignty["shared_sizing_authority"] is False


def test_shared_brain_architecture_requires_cognitive_market_os() -> None:
    contract = shared_brain_architecture_contract()

    assert (
        contract["hierarchical_world_model_law"][
            "multiple_temporal_levels_required"
        ]
        is True
    )
    assert (
        contract["multi_world_law"]["multiple_internal_world_models_required"]
        is True
    )
    assert (
        contract["reasoning_law"]["multiple_competing_hypotheses_required"]
        is True
    )
    assert contract["reasoning_law"]["hypothesis_falsification_required"] is True
    assert contract["uncertainty_law"]["epistemic_uncertainty_required"] is True
    assert contract["uncertainty_law"]["aleatoric_uncertainty_required"] is True
    assert contract["autonomous_research_law"]["holdout_required"] is True
    assert contract["autonomous_research_law"]["replication_required"] is True


def test_experimental_knowledge_cannot_self_promote() -> None:
    contract = shared_brain_architecture_contract()

    continual = contract["continual_learning_law"]
    research = contract["autonomous_research_law"]
    assert (
        continual[
            "experimental_knowledge_cannot_replace_certified_knowledge_directly"
        ]
        is True
    )
    assert research["research_may_not_self_promote_to_runtime"] is True
    assert research["validated_to_certified_requires_owner_governed_gate"] is True
