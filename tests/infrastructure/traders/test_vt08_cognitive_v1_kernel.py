from datetime import UTC, datetime

import pytest

from qore.infrastructure.traders.vt08_cognitive_hypothesis import (
    Vt08Hypothesis,
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
