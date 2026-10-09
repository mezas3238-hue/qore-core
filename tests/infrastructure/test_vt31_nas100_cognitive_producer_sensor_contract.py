"""The VT31 sensor must distinguish unknown producers and missing actuators."""
from __future__ import annotations

import json
from dataclasses import dataclass, replace
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace

import pytest

from qore.infrastructure.traders.vt31_nas100_causal_fact_producers import (
    produce_market_native_facts,
)
from qore.infrastructure.traders.vt31_nas100_cognitive_telemetry import (
    _unresolved_string,
    capture_post_entry_cognitive_sensor,
)
from qore.infrastructure.traders.vt31_nas100_position_intelligence import (
    PositionAction,
)
from scripts.vt31_nas100_cognitive_sensor_audit_v1 import (
    PREPARED_SCHEMA,
    audit,
)

T = datetime(2026, 1, 5, 15, 0, tzinfo=UTC)


@dataclass(frozen=True)
class Observation:
    as_of: str


@dataclass(frozen=True)
class Market:
    structure_invalidated: bool
    liquidity_failure_confirmed: bool
    regime_changed_against_thesis: bool
    next_structural_target: object | None = None


def decision():
    cognition = SimpleNamespace(
        observed_domains=("reasoning",),
        actuated_situation_fields=("h1_state",),
        observation_only_situation_fields=(),
        cognitive_coverage_ratio=Decimal("1"),
        full_cognitive_accounting_verified=True,
        maximum_cognition_verified=True,
        reasoning_max_intelligence_blockers=(),
    )
    position = SimpleNamespace(
        action=PositionAction.HOLD,
        reason="TEST_HOLD",
        next_stop=None,
        next_target=None,
    )
    return SimpleNamespace(
        cognition=cognition,
        position=position,
        entry_situation_fingerprint="frozen-entry",
        current_situation_fingerprint="current",
        current_reasoning_situation_fingerprint="current-reasoning",
        entry_reasoning_action="EXECUTE",
        current_reasoning_action="EXECUTE",
    )


def producer():
    return produce_market_native_facts(
        bars_since_fill=(),
        as_of=T,
        side="long",
        structural_invalidation_level=None,
        liquidity_failure_boundary=None,
        reference_reclaim_confirmed_at_entry=None,
        entry_regime="mixed",
        current_regime="bullish",
        regime_observed_at=T,
        primary_target=Decimal("110"),
        primary_target_reached=False,
        primary_target_accepted=False,
    )


def test_unwired_producer_is_never_painted_green() -> None:
    frame = capture_post_entry_cognitive_sensor(
        observation=Observation(T.isoformat()),
        market=Market(False, False, False),
        decision=decision(),
    )
    assert set(frame.native_fact_statuses.values()) == {"UNWIRED"}
    assert frame.native_fact_evidence == {}


def test_native_fact_sensor_preserves_na_provenance_and_datetime_json() -> None:
    frame = capture_post_entry_cognitive_sensor(
        observation=Observation(T.isoformat()),
        market=Market(False, False, False),
        decision=decision(),
        producer_report=producer(),
    )
    assert frame.native_fact_statuses["structure_invalidated"] == (
        "NOT_EVALUABLE"
    )
    assert frame.native_fact_statuses["next_structural_target"] == (
        "NOT_APPLICABLE"
    )
    assert frame.native_fact_evidence["next_structural_target"]["reason"] == (
        "PRIMARY_TARGET_NOT_REACHED"
    )
    json.dumps(frame.payload())


def test_sensor_fails_on_causal_timestamp_disagreement() -> None:
    with pytest.raises(ValueError, match="as_of mismatch"):
        capture_post_entry_cognitive_sensor(
            observation=Observation("2026-01-05T15:01:00+00:00"),
            market=Market(False, False, False),
            decision=decision(),
            producer_report=producer(),
        )


def test_sensor_rejects_observed_producer_consumer_disagreement() -> None:
    from qore.infrastructure.traders.vt31_nas100_causal_fact_producers import (
        CausalBooleanFact,
    )
    facts = producer()
    altered = replace(
        facts,
        structure_invalidated=CausalBooleanFact(
            "structure_invalidated",
            "OBSERVED",
            True,
            T,
            "frozen-structure-level-closed-m1",
            "CLOSED_M1_ADVERSE_BOUNDARY_BREACH",
        ),
    )
    with pytest.raises(ValueError, match="structure_invalidated disagreement"):
        capture_post_entry_cognitive_sensor(
            observation=Observation(T.isoformat()),
            market=Market(False, False, False),
            decision=decision(),
            producer_report=altered,
        )


def test_audit_fails_closed_on_missing_required_action_route(tmp_path: Path) -> None:
    evidence = {
        "schema": PREPARED_SCHEMA,
        "control_rows": [{
            "cognitive_exit_evaluations": [{
                "cognitive_sensor": {
                    "missing_inputs": [],
                    "unresolved_inputs": [],
                    "maximum_intelligence_blockers": [],
                    "observation_only_situation_fields": [],
                    "native_fact_statuses": {
                        "structure_invalidated": "UNWIRED",
                        "liquidity_failure_confirmed": "UNWIRED",
                        "regime_changed_against_thesis": "UNWIRED",
                        "next_structural_target": "UNWIRED",
                    },
                    "current_reasoning_action": "EXECUTE",
                    "output_action": "EXIT",
                    "output_reason": "CAUSAL_EXIT",
                    "output_requires_actuation": True,
                    "full_cognitive_accounting_verified": True,
                    "maximum_cognition_verified": True,
                },
            }],
        }],
    }
    path = tmp_path / "prepared.json"
    path.write_text(json.dumps(evidence))
    result = audit({"three_year_control": path})
    integrity = result["sensor_integrity"]
    assert integrity["required_action_unobserved_count"] == 1
    assert integrity["missing_actuation_sensor_for_required_action_count"] == 1
    assert result["native_fact_sensor"]["status_counts"][
        "structure_invalidated:UNWIRED"
    ] == 1


def test_semantic_state_parser_handles_composites_without_false_positives() -> None:
    assert _unresolved_string("NOT_EVALUATED") is True
    assert _unresolved_string("M15_CONTEXT_UNWIRED") is True
    assert _unresolved_string("RESEARCH_ONLY_UNCALIBRATED") is True
    assert _unresolved_string("H4_CONTEXT_UNAVAILABLE") is True
    assert _unresolved_string("NO_CONFIRMED_EXHAUSTION") is False
    assert _unresolved_string("KNOWN_NOT_FAILED") is False
    assert _unresolved_string("CALIBRATED_PRE_DOL1_CURRENT_JOURNEY") is False
    assert _unresolved_string("NOT_EVALUATED:YET") is True
