from datetime import UTC, datetime

import pytest

from qore.infrastructure.traders.vt08_cognitive_hypothesis import (
    Vt08Hypothesis,
    advance_hypothesis,
    new_rearm_hypothesis,
)
from qore.infrastructure.traders.vt08_cognitive_orchestrator import (
    evaluate_cognitive_hypothesis,
)
from qore.infrastructure.traders.vt08_cognitive_situation_model import (
    Vt08ForexSituationModel,
)
from qore.infrastructure.traders.vt08_cognitive_strategy_identity_memory import (
    strategy_identity_fingerprint,
    strategy_identity_payload,
    validate_strategy_identity,
)
from qore.infrastructure.traders.vt08_cognitive_v1_contracts import (
    Vt08CognitiveAction,
    Vt08HypothesisState,
    Vt08KnowledgeState,
)


def _situation(**overrides: object) -> Vt08ForexSituationModel:
    payload: dict[str, object] = {
        "as_of": datetime(2026, 9, 23, 9, 15, tzinfo=UTC),
        "market": "GBPUSD",
        "anchor_hour_ny": 5,
        "side": "long",
        "ltf_profile": "m15-standard",
        "methodology_valid": True,
        "source_identity_complete": True,
        "h4_lifecycle_valid": True,
        "bias_state": "RESOLVED",
        "scenario_state": "C2",
        "poi_state": "CONFIRMED",
        "protected_swing_state": "CONFIRMED",
        "cisd_state": "CONFIRMED",
        "displacement_state": "CONFIRMED",
        "entry_state": "ACTIONABLE",
        "entry_freshness_state": "CURRENT",
        "liquidity_state": "OBSERVED",
        "range_state": "KNOWN",
        "volatility_state": "KNOWN",
        "journey_stage": "PRE_ENTRY",
        "structural_destination_state": "SUPPORTED",
        "exhaustion_state": "NOT_OBSERVED",
        "risk_geometry_state": "VALID",
        "position_state": "FLAT",
        "supporting_evidence": ("SOURCE:CISD_CONFIRMED", "SOURCE:PS_CONFIRMED"),
    }
    payload.update(overrides)
    return Vt08ForexSituationModel(**payload)  # type: ignore[arg-type]


def test_strategy_identity_is_bound_to_owner_anchor_subset() -> None:
    validate_strategy_identity()
    payload = strategy_identity_payload()
    assert tuple(payload["owner_operational_h4_anchors_ny"]) == (1, 5, 9)
    assert len(strategy_identity_fingerprint()) == 64


def test_supported_complete_situation_executes() -> None:
    result = evaluate_cognitive_hypothesis(
        situation=_situation(),
        source_fingerprint="source-a",
    )
    assert result.decision.action is Vt08CognitiveAction.EXECUTE
    assert result.decision.metacognition.state is Vt08KnowledgeState.SUPPORTED
    assert len(result.decision.cognitive_memory_fingerprint) == 64
    assert len(result.decision.market_anchor_context_fingerprint) == 64
    assert result.hypothesis.state is Vt08HypothesisState.EXECUTABLE


def test_material_contradiction_abstains_and_kills_source() -> None:
    result = evaluate_cognitive_hypothesis(
        situation=_situation(
            material_contradictions=("MARKET:THESIS_INVALIDATED",),
        ),
        source_fingerprint="source-a",
    )
    assert result.decision.action is Vt08CognitiveAction.ABSTAIN
    assert result.decision.metacognition.state is Vt08KnowledgeState.CONTRADICTED
    assert result.hypothesis.state is Vt08HypothesisState.KILLED


def test_material_uncertainty_waits() -> None:
    result = evaluate_cognitive_hypothesis(
        situation=_situation(
            material_uncertainties=("MARKET:POI_CONTEXT_UNRESOLVED",),
        ),
        source_fingerprint="source-a",
    )
    assert result.decision.action is Vt08CognitiveAction.WAIT
    assert result.decision.metacognition.state is Vt08KnowledgeState.AMBIGUOUS
    assert result.hypothesis.state is Vt08HypothesisState.WAITING


def test_incomplete_confirmation_waits() -> None:
    result = evaluate_cognitive_hypothesis(
        situation=_situation(cisd_state="PENDING"),
        source_fingerprint="source-a",
    )
    assert result.decision.action is Vt08CognitiveAction.WAIT


def test_killed_source_cannot_be_resurrected() -> None:
    killed = Vt08Hypothesis(
        source_fingerprint="source-a",
        state=Vt08HypothesisState.KILLED,
    )
    with pytest.raises(ValueError, match="cannot be resurrected"):
        evaluate_cognitive_hypothesis(
            situation=_situation(),
            source_fingerprint="source-a",
            hypothesis=killed,
        )


def test_rearm_requires_new_source_identity() -> None:
    killed = Vt08Hypothesis(
        source_fingerprint="source-a",
        state=Vt08HypothesisState.KILLED,
    )
    with pytest.raises(ValueError, match="cannot reuse"):
        new_rearm_hypothesis(killed, new_source_fingerprint="source-a")
    renewed = new_rearm_hypothesis(
        killed,
        new_source_fingerprint="source-b",
    )
    assert renewed.generation == 2
    assert renewed.state is Vt08HypothesisState.FORMING


def test_future_or_post_outcome_fields_are_structurally_absent() -> None:
    model = _situation()
    payload = model.payload()
    assert payload["terminal_pnl_present"] is False
    assert payload["post_outcome_label_present"] is False


def test_invalid_anchor_fails_closed() -> None:
    with pytest.raises(ValueError, match="anchor"):
        _situation(anchor_hour_ny=13)


@pytest.mark.parametrize(
    ("overrides", "expected"),
    (
        ({"risk_geometry_state": "UNKNOWN"}, Vt08CognitiveAction.WAIT),
        ({"bias_state": "UNRESOLVED"}, Vt08CognitiveAction.WAIT),
        ({"protected_swing_state": "PENDING"}, Vt08CognitiveAction.WAIT),
        ({"entry_state": "PENDING"}, Vt08CognitiveAction.WAIT),
        ({"entry_freshness_state": "STALE"}, Vt08CognitiveAction.WAIT),
        ({"source_identity_complete": False}, Vt08CognitiveAction.WAIT),
        ({"methodology_valid": False}, Vt08CognitiveAction.ABSTAIN),
        ({"h4_lifecycle_valid": False}, Vt08CognitiveAction.ABSTAIN),
        ({"entry_state": "CONTRADICTED"}, Vt08CognitiveAction.ABSTAIN),
        (
            {"structural_destination_state": "CONTRADICTED"},
            Vt08CognitiveAction.ABSTAIN,
        ),
        ({"risk_geometry_state": "INVALID"}, Vt08CognitiveAction.ABSTAIN),
    ),
)
def test_every_material_preentry_veto_or_wait_is_enforced(
    overrides: dict[str, object], expected: Vt08CognitiveAction
) -> None:
    outcome = evaluate_cognitive_hypothesis(
        situation=_situation(**overrides),
        source_fingerprint="synthetic-matrix-event",
    )
    assert outcome.decision.action is expected
    assert outcome.hypothesis.state in {
        Vt08HypothesisState.WAITING,
        Vt08HypothesisState.FORMING,
        Vt08HypothesisState.KILLED,
    }


def test_metacognitive_unknown_cannot_be_executed_in_original_authorized_market() -> None:
    evaluation = evaluate_cognitive_hypothesis(
        situation=_situation(supporting_evidence=()),
        source_fingerprint="legacy-synthetic-unknown",
    )
    assert evaluation.decision.metacognition.state is Vt08KnowledgeState.UNKNOWN
    assert evaluation.decision.action is Vt08CognitiveAction.WAIT
    assert "REASONING:NO_EXECUTION_SUPPORT_EVIDENCE" in evaluation.decision.reason_codes


def test_hypothesis_wait_confirmation_and_invalid_execute_states() -> None:
    current = Vt08Hypothesis(
        source_fingerprint="state-transition",
        state=Vt08HypothesisState.FORMING,
    )
    still_forming = advance_hypothesis(
        current, action=Vt08CognitiveAction.WAIT, confirmation_complete=False
    )
    assert still_forming.state is Vt08HypothesisState.FORMING
    now_waiting = advance_hypothesis(
        current, action=Vt08CognitiveAction.WAIT, confirmation_complete=True
    )
    assert now_waiting.state is Vt08HypothesisState.WAITING
    with pytest.raises(ValueError, match="complete confirmation"):
        advance_hypothesis(
            current, action=Vt08CognitiveAction.EXECUTE, confirmation_complete=False
        )


def test_hypothesis_constructor_rejects_invalid_identity_generation_and_state() -> None:
    with pytest.raises(ValueError, match="requires source fingerprint"):
        Vt08Hypothesis(source_fingerprint="", state=Vt08HypothesisState.FORMING)
    with pytest.raises(ValueError, match="state must be exact"):
        Vt08Hypothesis(source_fingerprint="id", state="WAITING")  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="generation"):
        Vt08Hypothesis(
            source_fingerprint="id", state=Vt08HypothesisState.FORMING, generation=0
        )


def test_cognitive_situation_rejects_outcome_leakage_and_invalid_mutability() -> None:
    with pytest.raises(ValueError, match="timezone-aware"):
        _situation(as_of=datetime(2026, 9, 23, 9, 15))
    with pytest.raises(ValueError, match="post-outcome"):
        _situation(terminal_pnl="future-profit")
    with pytest.raises(ValueError, match="post-outcome"):
        _situation(post_outcome_label="winner")
    with pytest.raises(ValueError, match="immutable tuple"):
        _situation(supporting_evidence=["unfrozen"])
    with pytest.raises(ValueError, match="must not contain duplicates"):
        _situation(supporting_evidence=("X", "X"))
    with pytest.raises(ValueError, match="non-empty strings"):
        _situation(supporting_evidence=("",))


def test_strategy_identity_vetoes_unauthorized_runtime_elevation() -> None:
    from qore.infrastructure.traders.vt08_cognitive_v1_contracts import (
        Vt08CognitiveArchitectureFreeze,
    )

    with pytest.raises(ValueError, match="capital/order authority"):
        Vt08CognitiveArchitectureFreeze(capital_authority=True)
    with pytest.raises(ValueError, match="future information"):
        Vt08CognitiveArchitectureFreeze(future_information_allowed=True)
    with pytest.raises(ValueError, match="research/shadow only"):
        Vt08CognitiveArchitectureFreeze(production_authorized=True)
