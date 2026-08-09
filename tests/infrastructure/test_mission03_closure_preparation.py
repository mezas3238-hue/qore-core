from __future__ import annotations

import json

import pytest

from qore.infrastructure.mission03_closure_preparation import (
    Mission03ClosurePreparationStatus,
    Mission03ClosurePreparationValidationError,
    Mission03OperationalGateClosureRecord,
    Mission03OperationalGateEvidenceRef,
    build_mission03_closure_preparation_evidence,
)
from qore.infrastructure.mission03_operational_e2e_preparation import Mission03E2EGate
from qore.kernel.result import Failure, Success

_GATES = tuple(Mission03E2EGate)


def _record(
    gate: Mission03E2EGate,
    *,
    completed: bool,
) -> Mission03OperationalGateClosureRecord:
    return Mission03OperationalGateClosureRecord(
        gate=gate,
        completed=completed,
        evidence_refs=(
            (Mission03OperationalGateEvidenceRef(f"artifact:mission03/{gate.value}"),)
            if completed
            else ()
        ),
    )


def _records(*, completed_count: int) -> tuple[Mission03OperationalGateClosureRecord, ...]:
    return tuple(
        _record(gate, completed=index < completed_count)
        for index, gate in enumerate(_GATES)
    )


def test_current_uncompleted_mission_is_blocked_and_never_falsely_closed() -> None:
    result = build_mission03_closure_preparation_evidence(
        tuple(reversed(_records(completed_count=0)))
    )

    assert isinstance(result, Success)
    evidence = result.value
    assert evidence.status is Mission03ClosurePreparationStatus.BLOCKED
    assert evidence.closure_attempt_permitted is False
    assert evidence.mission_closed is False
    assert evidence.missing_gates == _GATES
    assert tuple(record.gate for record in evidence.gates) == _GATES
    assert len(evidence.blocker_codes) == len(_GATES)


def test_all_operational_gates_can_make_closure_eligible_but_not_close_mission() -> None:
    result = build_mission03_closure_preparation_evidence(
        _records(completed_count=len(_GATES))
    )

    assert isinstance(result, Success)
    evidence = result.value
    assert evidence.status is Mission03ClosurePreparationStatus.ELIGIBLE
    assert evidence.closure_attempt_permitted is True
    assert evidence.missing_gates == ()
    assert evidence.blocker_codes == ()
    assert evidence.mission_closed is False


def test_partial_sequential_prefix_is_valid_but_blocked() -> None:
    result = build_mission03_closure_preparation_evidence(
        _records(completed_count=4)
    )

    assert isinstance(result, Success)
    assert result.value.status is Mission03ClosurePreparationStatus.BLOCKED
    assert result.value.missing_gates == _GATES[4:]
    assert result.value.closure_attempt_permitted is False


def test_gap_in_operational_sequence_fails_closed() -> None:
    records = list(_records(completed_count=2))
    records[3] = _record(_GATES[3], completed=True)

    result = build_mission03_closure_preparation_evidence(tuple(records))

    assert isinstance(result, Failure)
    assert isinstance(result.error, Mission03ClosurePreparationValidationError)
    assert "sequentially" in str(result.error)


def test_completed_gate_requires_evidence_and_incomplete_gate_rejects_it() -> None:
    with pytest.raises(Mission03ClosurePreparationValidationError):
        Mission03OperationalGateClosureRecord(
            gate=Mission03E2EGate.LIVE_MARKET_FEED,
            completed=True,
        )

    with pytest.raises(Mission03ClosurePreparationValidationError):
        Mission03OperationalGateClosureRecord(
            gate=Mission03E2EGate.LIVE_MARKET_FEED,
            completed=False,
            evidence_refs=(Mission03OperationalGateEvidenceRef("artifact:gate5/success"),),
        )


def test_completed_flag_is_strict_bool() -> None:
    with pytest.raises(Mission03ClosurePreparationValidationError):
        Mission03OperationalGateClosureRecord(
            gate=Mission03E2EGate.LIVE_MARKET_FEED,
            completed=1,
            evidence_refs=(Mission03OperationalGateEvidenceRef("artifact:gate5/success"),),
        )


def test_incomplete_and_duplicate_gate_matrices_fail_closed() -> None:
    incomplete = build_mission03_closure_preparation_evidence(
        _records(completed_count=0)[:-1]
    )
    records = _records(completed_count=0)
    duplicate = build_mission03_closure_preparation_evidence((*records, records[0]))

    assert isinstance(incomplete, Failure)
    assert isinstance(duplicate, Failure)
    assert isinstance(incomplete.error, Mission03ClosurePreparationValidationError)
    assert isinstance(duplicate.error, Mission03ClosurePreparationValidationError)


def test_operational_evidence_refs_are_sanitized_sorted_and_unique() -> None:
    record = Mission03OperationalGateClosureRecord(
        gate=Mission03E2EGate.LIVE_MARKET_FEED,
        completed=True,
        evidence_refs=(
            Mission03OperationalGateEvidenceRef("artifact:gate5/z"),
            Mission03OperationalGateEvidenceRef("artifact:gate5/a"),
        ),
    )
    assert tuple(item.value for item in record.evidence_refs) == (
        "artifact:gate5/a",
        "artifact:gate5/z",
    )

    with pytest.raises(Mission03ClosurePreparationValidationError):
        Mission03OperationalGateEvidenceRef("artifact:token=secret")

    with pytest.raises(Mission03ClosurePreparationValidationError):
        Mission03OperationalGateClosureRecord(
            gate=Mission03E2EGate.LIVE_MARKET_FEED,
            completed=True,
            evidence_refs=(
                Mission03OperationalGateEvidenceRef("artifact:gate5/a"),
                Mission03OperationalGateEvidenceRef("artifact:gate5/a"),
            ),
        )


def test_public_payload_is_deterministic_and_never_claims_mission_closed() -> None:
    result = build_mission03_closure_preparation_evidence(
        _records(completed_count=0)
    )
    assert isinstance(result, Success)

    first = result.value.to_json()
    second = result.value.to_json()
    payload = json.loads(first)

    assert first == second
    assert payload["provider"] == "oanda-v20"
    assert payload["environment"] == "demo"
    assert payload["closure_attempt_permitted"] is False
    assert payload["mission_closed"] is False
    assert "token=" not in first.lower()
    assert "bearer " not in first.lower()
    assert "authorization:" not in first.lower()
