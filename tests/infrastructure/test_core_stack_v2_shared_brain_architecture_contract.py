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


def test_shared_brain_architecture_requires_falsifiable_world_model() -> None:
    contract = shared_brain_architecture_contract()

    assert contract["world_model_law"]["continuous_market_world_state_required"] is True
    assert contract["reasoning_law"]["multiple_competing_hypotheses_required"] is True
    assert contract["reasoning_law"]["hypothesis_falsification_required"] is True
    assert contract["metacognition_law"]["epistemic_uncertainty_required"] is True
    assert (\n        contract["scientific_discovery_law"][\n            "holdout_required_before_knowledge_promotion"\n        ]\n        is True\n    )
