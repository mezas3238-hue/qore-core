from qore.infrastructure.traders.vt08_cognitive_v1_contracts import (
    OWNER_OPERATIONAL_ANCHORS_NY,
    Vt08CognitiveAction,
    Vt08CognitiveArchitectureFreeze,
    Vt08HypothesisState,
    Vt08KnowledgeState,
    Vt08PositionAction,
    architecture_fingerprint,
    architecture_payload,
)


def test_vt08_cognitive_v1_freeze_is_non_authoritative() -> None:
    freeze = Vt08CognitiveArchitectureFreeze()
    assert freeze.owner_operational_anchors_ny == (1, 5, 9)
    assert freeze.methodology_mutation_allowed is False
    assert freeze.runtime_self_training_allowed is False
    assert freeze.future_information_allowed is False
    assert freeze.capital_authority is False
    assert freeze.order_authority is False
    assert freeze.live_integration_authorized is False
    assert freeze.production_authorized is False
    assert freeze.real_capital_authorized is False


def test_vt08_cognitive_v1_vocabulary_is_frozen() -> None:
    assert tuple(item.value for item in Vt08CognitiveAction) == (
        "EXECUTE",
        "WAIT",
        "ABSTAIN",
    )
    assert tuple(item.value for item in Vt08HypothesisState) == (
        "FORMING",
        "CONFIRMED",
        "WAITING",
        "EXECUTABLE",
        "CONTRADICTED",
        "KILLED",
    )
    assert tuple(item.value for item in Vt08KnowledgeState) == (
        "KNOWN",
        "SUPPORTED",
        "AMBIGUOUS",
        "CONTRADICTED",
        "UNKNOWN",
    )
    assert tuple(item.value for item in Vt08PositionAction) == (
        "HOLD",
        "PROTECT",
        "REDUCE",
        "EXIT",
    )


def test_vt08_cognitive_v1_freeze_guards_cross_trader_copying() -> None:
    payload = architecture_payload()
    assert payload["abstain_sovereignty"] is True
    assert payload["killed_hypothesis_reuse_allowed"] is False
    assert payload["rearm_requires_new_structural_source"] is True
    assert payload["stop_widening_allowed"] is False
    assert payload["qore_risk_final_capital_authority"] is True
    assert payload["current_vt08_live_runtime_modified"] is False
    prohibited = payload["prohibited_cross_trader_imports"]
    assert "SILVER_BULLET_RULES" in prohibited
    assert "CAPITALIZER_ENTRY_LOGIC" in prohibited
    assert "TURTLE_SOUP_RULES" in prohibited
    assert len(architecture_fingerprint()) == 64
