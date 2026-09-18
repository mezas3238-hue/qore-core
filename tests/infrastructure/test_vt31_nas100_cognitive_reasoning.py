from __future__ import annotations

from decimal import Decimal

from qore.infrastructure.traders.vt31_nas100_cognitive_memory import (
    memory_fingerprint,
    memory_payload,
    validate_memory,
)
from qore.infrastructure.traders.vt31_nas100_episodic_memory import (
    episodic_memory_fingerprint,
    episodic_memory_payload,
)
from qore.infrastructure.traders.vt31_nas100_long_term_memory import (
    long_term_memory_fingerprint,
    long_term_memory_payload,
)
from qore.infrastructure.traders.vt31_nas100_reasoning_engine import reason
from qore.infrastructure.traders.vt31_nas100_working_memory import (
    Nas100WorkingMemory,
)


def _supported_state(
    *,
    reclaim_age: int = 3,
    reference_ratio: str = "0.68",
) -> Nas100WorkingMemory:
    return Nas100WorkingMemory(
        decision_minute_ny=10 * 60 + 12,
        last_structure_event_family="reference-liquidity-sweep",
        last_structure_event_age_minutes=2,
        reference_reclaim_age_minutes=reclaim_age,
        current_path_vs_previous=Decimal("0.62"),
        reference_width_vs_prior5=Decimal(reference_ratio),
    )


def test_three_memory_architecture_is_internal_and_causal() -> None:
    validate_memory()
    payload = memory_payload()
    assert payload["mind_model"] == "THREE_MEMORY_ARCHITECTURE"

    long_term = long_term_memory_payload()
    assert long_term["memory_class"] == "LONG_TERM_SEMANTIC"
    long_guards = long_term["guards"]
    assert isinstance(long_guards, dict)
    assert long_guards["external_cibo_runtime_dependency"] is False
    assert long_guards["per_date_outcome_memory"] is False

    episodic = episodic_memory_payload()
    assert episodic["memory_class"] == "EPISODIC_RESEARCH"
    episode_guards = episodic["guards"]
    assert isinstance(episode_guards, dict)
    assert episode_guards["contains_current_day_state"] is False
    assert episode_guards["contains_per_date_outcome_map"] is False

    working_contract = payload["working_memory_contract"]
    assert isinstance(working_contract, dict)
    assert working_contract["persistent"] is False
    assert working_contract["rebuilt_each_decision"] is True

    assert len(long_term_memory_fingerprint()) == 64
    assert len(episodic_memory_fingerprint()) == 64
    assert len(memory_fingerprint()) == 64


def test_working_memory_contains_only_current_causal_state() -> None:
    working = _supported_state()
    payload = working.payload()
    assert payload["memory_class"] == "WORKING_CAUSAL_RUNTIME"
    assert payload["causal_timestamp_state_only"] is True
    assert payload["historical_outcome_labels_present"] is False
    assert "cibo_source_binding" not in payload
    assert "laboratory_bindings" not in payload
    assert "r_multiple" not in payload
    assert len(working.fingerprint()) == 64


def test_reasoning_engine_executes_supported_double_compression_state() -> None:
    working = _supported_state()
    decision = reason(working)
    assert decision.action == "EXECUTE"
    assert decision.target_plan == "FULL_STRUCTURAL_BOUNDARY"
    assert decision.contradictions == ()
    assert "structure_knowledge" in decision.long_term_memory_used
    assert "reference_liquidity_state" in decision.episodic_memory_used
    assert decision.working_memory_fingerprint == working.fingerprint()
    assert (
        decision.long_term_memory_fingerprint
        == long_term_memory_fingerprint()
    )
    assert (
        decision.episodic_memory_fingerprint
        == episodic_memory_fingerprint()
    )
    assert decision.memory_fingerprint == memory_fingerprint()


def test_reasoning_engine_changes_management_using_memory_layers() -> None:
    working = _supported_state(reference_ratio="0.96")
    decision = reason(working)
    assert decision.action == "EXECUTE"
    assert decision.target_plan == "PARTIAL_1_25R_PLUS_BOUNDARY_RUNNER"
    assert "destination_knowledge" in decision.long_term_memory_used
    assert "dynamic_destination_management" in decision.episodic_memory_used
    assert "universal_target_plan" in decision.episodic_memory_used


def test_reasoning_engine_abstains_using_episodic_failure_memory() -> None:
    decision = reason(_supported_state(reclaim_age=10))
    assert decision.action == "ABSTAIN"
    assert (
        "EPISODIC:SEQUENCE_FRESHNESS_STALE_8_14"
        in decision.contradictions
    )
    assert "sequence_knowledge" in decision.long_term_memory_used
    assert "sequence_freshness" in decision.episodic_memory_used
