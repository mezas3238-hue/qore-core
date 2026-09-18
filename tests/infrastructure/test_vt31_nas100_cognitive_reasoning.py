from __future__ import annotations

from decimal import Decimal

from qore.infrastructure.traders.vt31_nas100_cognitive_memory import (
    memory_fingerprint,
    memory_payload,
    validate_memory,
)
from qore.infrastructure.traders.vt31_nas100_reasoning_engine import (
    Nas100ReasoningState,
    reason,
)


def test_cognitive_memory_is_internal_and_causal() -> None:
    validate_memory()
    payload = memory_payload()
    guards = payload["runtime_guards"]
    assert isinstance(guards, dict)
    assert guards["external_cibo_runtime_dependency"] is False
    assert guards["date_level_lookup_allowed"] is False
    assert guards["future_bar_lookup_allowed"] is False
    assert guards["post_outcome_lookup_allowed"] is False
    assert guards["memory_mutable_at_runtime"] is False
    assert len(memory_fingerprint()) == 64


def test_reasoning_engine_executes_supported_double_compression_state() -> None:
    decision = reason(
        Nas100ReasoningState(
            decision_minute_ny=10 * 60 + 12,
            last_structure_event_family="reference-liquidity-sweep",
            last_structure_event_age_minutes=2,
            reference_reclaim_age_minutes=3,
            current_path_vs_previous=Decimal("0.62"),
            reference_width_vs_prior5=Decimal("0.68"),
        )
    )
    assert decision.action == "EXECUTE"
    assert decision.target_plan == "FULL_STRUCTURAL_BOUNDARY"
    assert decision.contradictions == ()
    assert decision.memory_fingerprint == memory_fingerprint()


def test_reasoning_engine_changes_management_without_external_cibo_lookup() -> None:
    decision = reason(
        Nas100ReasoningState(
            decision_minute_ny=10 * 60 + 17,
            last_structure_event_family="reference-liquidity-sweep",
            last_structure_event_age_minutes=3,
            reference_reclaim_age_minutes=4,
            current_path_vs_previous=Decimal("0.70"),
            reference_width_vs_prior5=Decimal("0.96"),
        )
    )
    assert decision.action == "EXECUTE"
    assert decision.target_plan == "PARTIAL_1_25R_PLUS_BOUNDARY_RUNNER"


def test_reasoning_engine_abstains_on_known_stale_sequence() -> None:
    decision = reason(
        Nas100ReasoningState(
            decision_minute_ny=10 * 60 + 15,
            last_structure_event_family="reference-liquidity-sweep",
            last_structure_event_age_minutes=2,
            reference_reclaim_age_minutes=10,
            current_path_vs_previous=Decimal("0.66"),
            reference_width_vs_prior5=Decimal("0.71"),
        )
    )
    assert decision.action == "ABSTAIN"
    assert "MEMORY:SEQUENCE_FRESHNESS_STALE_8_14" in decision.contradictions
