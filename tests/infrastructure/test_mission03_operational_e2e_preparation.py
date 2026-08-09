from __future__ import annotations

import json
from typing import cast

import pytest

from qore.infrastructure.mission03_operational_e2e_preparation import (
    Mission03E2EEvidenceRef,
    Mission03E2EGate,
    Mission03E2EPreparationStatus,
    Mission03ExternalPrerequisiteState,
    Mission03GatePreparationRecord,
    Mission03GatePreparationStatus,
    Mission03OperationalE2EPreparationValidationError,
    build_mission03_operational_e2e_preparation_evidence,
)
from qore.kernel.result import Failure, Success

_GATES = tuple(Mission03E2EGate)
_PRE_E2E = _GATES[:-1]


def _record(
    gate: Mission03E2EGate,
    *,
    status: Mission03GatePreparationStatus = Mission03GatePreparationStatus.READY,
) -> Mission03GatePreparationRecord:
    return Mission03GatePreparationRecord(
        gate=gate,
        status=status,
        evidence_refs=(Mission03E2EEvidenceRef(f"repo:mission03/{gate.value}"),),
    )


def _records(
    *,
    not_ready: Mission03E2EGate | None = None,
) -> tuple[Mission03GatePreparationRecord, ...]:
    return tuple(
        _record(
            gate,
            status=(
                Mission03GatePreparationStatus.NOT_READY
                if gate is not_ready
                else Mission03GatePreparationStatus.READY
            ),
        )
        for gate in _GATES
    )


def test_current_unprovisioned_state_can_be_offline_ready_but_not_operational() -> None:
    prerequisites = Mission03ExternalPrerequisiteState(
        practice_account_provisioned=False,
        practice_token_provisioned=False,
    )
    result = build_mission03_operational_e2e_preparation_evidence(
        tuple(reversed(_records())),
        external_prerequisites=prerequisites,
    )

    assert isinstance(result, Success)
    evidence = result.value
    assert evidence.status is Mission03E2EPreparationStatus.READY
    assert evidence.offline_preparation_ready is True
    assert evidence.operational_e2e_attempt_permitted is False
    assert evidence.operationally_completed is False
    assert tuple(record.gate for record in evidence.gates) == _GATES
    assert prerequisites.missing_operational_gates == _PRE_E2E
    assert prerequisites.blocker_codes[:2] == (
        "oanda.practice.account.not-provisioned",
        "oanda.practice.token.not-provisioned",
    )
    assert len(prerequisites.blocker_codes) == 2 + len(_PRE_E2E)


def test_full_pre_e2e_operational_sequence_can_permit_attempt_but_not_fake_completion() -> None:
    prerequisites = Mission03ExternalPrerequisiteState(
        practice_account_provisioned=True,
        practice_token_provisioned=True,
        completed_operational_gates=_PRE_E2E,
    )
    result = build_mission03_operational_e2e_preparation_evidence(
        _records(),
        external_prerequisites=prerequisites,
    )

    assert isinstance(result, Success)
    evidence = result.value
    assert prerequisites.missing_operational_gates == ()
    assert prerequisites.blocker_codes == ()
    assert evidence.operational_e2e_attempt_permitted is True
    assert evidence.operationally_completed is False


def test_not_ready_offline_gate_blocks_e2e_attempt_even_after_upstream_completion() -> None:
    prerequisites = Mission03ExternalPrerequisiteState(
        practice_account_provisioned=True,
        practice_token_provisioned=True,
        completed_operational_gates=_PRE_E2E,
    )
    result = build_mission03_operational_e2e_preparation_evidence(
        _records(not_ready=Mission03E2EGate.REAL_MARKET_OPERATIONAL_E2E),
        external_prerequisites=prerequisites,
    )

    assert isinstance(result, Success)
    assert result.value.status is Mission03E2EPreparationStatus.BLOCKED
    assert result.value.offline_preparation_ready is False
    assert result.value.operational_e2e_attempt_permitted is False


def test_incomplete_and_duplicate_gate_matrices_fail_closed() -> None:
    prerequisites = Mission03ExternalPrerequisiteState(
        practice_account_provisioned=False,
        practice_token_provisioned=False,
    )
    incomplete = build_mission03_operational_e2e_preparation_evidence(
        _records()[:-1],
        external_prerequisites=prerequisites,
    )
    duplicate_records = (*_records(), _records()[0])
    duplicate = build_mission03_operational_e2e_preparation_evidence(
        duplicate_records,
        external_prerequisites=prerequisites,
    )

    assert isinstance(incomplete, Failure)
    assert isinstance(duplicate, Failure)
    assert isinstance(
        incomplete.error,
        Mission03OperationalE2EPreparationValidationError,
    )
    assert isinstance(
        duplicate.error,
        Mission03OperationalE2EPreparationValidationError,
    )


def test_operational_gate_completion_requires_credentials_and_strict_sequence() -> None:
    with pytest.raises(Mission03OperationalE2EPreparationValidationError):
        Mission03ExternalPrerequisiteState(
            practice_account_provisioned=False,
            practice_token_provisioned=False,
            completed_operational_gates=(Mission03E2EGate.LIVE_MARKET_FEED,),
        )

    with pytest.raises(Mission03OperationalE2EPreparationValidationError):
        Mission03ExternalPrerequisiteState(
            practice_account_provisioned=True,
            practice_token_provisioned=True,
            completed_operational_gates=(
                Mission03E2EGate.LIVE_MARKET_FEED,
                Mission03E2EGate.DEMO_ACCOUNT_ACTIVATION,
            ),
        )

    with pytest.raises(Mission03OperationalE2EPreparationValidationError):
        Mission03ExternalPrerequisiteState(
            practice_account_provisioned=True,
            practice_token_provisioned=True,
            completed_operational_gates=(*_PRE_E2E, Mission03E2EGate.REAL_MARKET_OPERATIONAL_E2E),
        )


def test_provisioning_flags_are_strict_bool() -> None:
    with pytest.raises(Mission03OperationalE2EPreparationValidationError):
        Mission03ExternalPrerequisiteState(
            practice_account_provisioned=cast(bool, 1),
            practice_token_provisioned=False,
        )

    with pytest.raises(Mission03OperationalE2EPreparationValidationError):
        Mission03ExternalPrerequisiteState(
            practice_account_provisioned=False,
            practice_token_provisioned=cast(bool, 1),
        )


def test_evidence_refs_are_sanitized_sorted_and_deduplicated() -> None:
    record = Mission03GatePreparationRecord(
        gate=Mission03E2EGate.LIVE_MARKET_FEED,
        status=Mission03GatePreparationStatus.READY,
        evidence_refs=(
            Mission03E2EEvidenceRef("repo:mission03/z"),
            Mission03E2EEvidenceRef("repo:mission03/a"),
        ),
    )
    assert tuple(item.value for item in record.evidence_refs) == (
        "repo:mission03/a",
        "repo:mission03/z",
    )

    with pytest.raises(Mission03OperationalE2EPreparationValidationError):
        Mission03E2EEvidenceRef("repo:token=secret")

    with pytest.raises(Mission03OperationalE2EPreparationValidationError):
        Mission03GatePreparationRecord(
            gate=Mission03E2EGate.LIVE_MARKET_FEED,
            status=Mission03GatePreparationStatus.READY,
            evidence_refs=(
                Mission03E2EEvidenceRef("repo:mission03/a"),
                Mission03E2EEvidenceRef("repo:mission03/a"),
            ),
        )


def test_public_payload_is_deterministic_and_secret_free() -> None:
    result = build_mission03_operational_e2e_preparation_evidence(
        _records(),
        external_prerequisites=Mission03ExternalPrerequisiteState(
            practice_account_provisioned=False,
            practice_token_provisioned=False,
        ),
    )
    assert isinstance(result, Success)

    first = result.value.to_json()
    second = result.value.to_json()
    payload = json.loads(first)

    assert first == second
    assert payload["provider"] == "oanda-v20"
    assert payload["environment"] == "demo"
    assert payload["operational_e2e_attempt_permitted"] is False
    assert payload["operationally_completed"] is False
    assert "bearer " not in first.lower()
    assert "authorization:" not in first.lower()
    assert "token=" not in first.lower()
