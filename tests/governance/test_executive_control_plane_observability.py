from __future__ import annotations

from dataclasses import FrozenInstanceError
from datetime import UTC, datetime, timedelta
from typing import cast
from uuid import UUID

import pytest

from qore.domain.events import CorrelationId
from qore.governance.executive_audit_evidence import (
    ExecutiveAuditEvidenceOutcome,
    ExecutiveAuditEvidenceRecord,
    ExecutiveAuditEvidenceRecordId,
    ExecutiveAuditEvidenceStage,
    ExecutiveAuditSourceKind,
    ExecutiveAuditSourceRef,
)
from qore.governance.executive_control import ExecutiveAuthorityVersion, ExecutivePrincipalId
from qore.governance.executive_control_plane_observability import (
    ExecutiveControlPlaneObservabilityError,
    ExecutiveControlPlaneObservabilityPort,
    ExecutiveControlPlaneObservabilityValidationError,
    ExecutiveControlPlaneObservation,
    ExecutiveControlPlaneObservationId,
    ExecutiveControlPlaneObservationOutcome,
    ExecutiveControlPlaneObservationStage,
    build_executive_audit_append_observation,
    build_executive_control_plane_observation,
)
from qore.governance.executive_ports import ExecutiveEvidenceRef
from qore.kernel.result import Result, Success

_NOW = datetime(2026, 8, 9, 8, 0, tzinfo=UTC)
_PRINCIPAL = ExecutivePrincipalId("ceo.primary")
_CORRELATION = CorrelationId(UUID("50000000-0000-0000-0000-000000000001"))


def _record(
    stage: ExecutiveAuditEvidenceStage,
    outcome: ExecutiveAuditEvidenceOutcome,
) -> ExecutiveAuditEvidenceRecord:
    return ExecutiveAuditEvidenceRecord(
        record_id=ExecutiveAuditEvidenceRecordId(
            UUID("50000000-0000-0000-0000-000000000002")
        ),
        stage=stage,
        outcome=outcome,
        principal_id=_PRINCIPAL,
        correlation_id=_CORRELATION,
        occurred_at=_NOW,
        reason_code="control-plane.observed",
        source_refs=(
            ExecutiveAuditSourceRef(
                ExecutiveAuditSourceKind.AUTHENTICATION_ASSERTION,
                "50000000-0000-0000-0000-000000000003",
            ),
        ),
        evidence_refs=(
            ExecutiveEvidenceRef("audit:z"),
            ExecutiveEvidenceRef("audit:a"),
        ),
        authority_version=ExecutiveAuthorityVersion("authority.v4"),
    )


class _FakeObservabilityPort:
    def __init__(self) -> None:
        self.observations: list[ExecutiveControlPlaneObservation] = []

    def emit(
        self,
        observation: ExecutiveControlPlaneObservation,
    ) -> Result[ExecutiveControlPlaneObservation, ExecutiveControlPlaneObservabilityError]:
        self.observations.append(observation)
        return Success(observation)


@pytest.mark.parametrize(
    ("audit_stage", "observation_stage"),
    [
        (
            ExecutiveAuditEvidenceStage.AUTHENTICATION,
            ExecutiveControlPlaneObservationStage.AUTHENTICATION,
        ),
        (
            ExecutiveAuditEvidenceStage.AUTHORITY,
            ExecutiveControlPlaneObservationStage.AUTHORITY,
        ),
        (
            ExecutiveAuditEvidenceStage.AUTHORIZATION,
            ExecutiveControlPlaneObservationStage.AUTHORIZATION,
        ),
        (
            ExecutiveAuditEvidenceStage.COMMAND_DISPATCH,
            ExecutiveControlPlaneObservationStage.COMMAND_DISPATCH,
        ),
        (
            ExecutiveAuditEvidenceStage.QUERY_DISPATCH,
            ExecutiveControlPlaneObservationStage.QUERY_DISPATCH,
        ),
        (
            ExecutiveAuditEvidenceStage.GOVERNANCE_MUTATION,
            ExecutiveControlPlaneObservationStage.GOVERNANCE_MUTATION,
        ),
    ],
)
def test_observation_preserves_every_audited_control_plane_stage(
    audit_stage: ExecutiveAuditEvidenceStage,
    observation_stage: ExecutiveControlPlaneObservationStage,
) -> None:
    result = build_executive_control_plane_observation(
        _record(audit_stage, ExecutiveAuditEvidenceOutcome.SUCCEEDED),
        observation_id=ExecutiveControlPlaneObservationId(UUID(int=10)),
        observed_at=_NOW + timedelta(seconds=1),
    )

    assert isinstance(result, Success)
    assert result.value.stage is observation_stage
    assert result.value.metric_name == (
        f"executive.control-plane.{observation_stage.value}.succeeded"
    )


@pytest.mark.parametrize(
    ("audit_outcome", "observation_outcome"),
    [
        (
            ExecutiveAuditEvidenceOutcome.SUCCEEDED,
            ExecutiveControlPlaneObservationOutcome.SUCCEEDED,
        ),
        (
            ExecutiveAuditEvidenceOutcome.NO_ACTION,
            ExecutiveControlPlaneObservationOutcome.NO_ACTION,
        ),
        (
            ExecutiveAuditEvidenceOutcome.BLOCKED,
            ExecutiveControlPlaneObservationOutcome.BLOCKED,
        ),
        (
            ExecutiveAuditEvidenceOutcome.FAILED,
            ExecutiveControlPlaneObservationOutcome.FAILED,
        ),
    ],
)
def test_observation_preserves_success_no_action_blocked_and_failed_outcomes(
    audit_outcome: ExecutiveAuditEvidenceOutcome,
    observation_outcome: ExecutiveControlPlaneObservationOutcome,
) -> None:
    record = _record(ExecutiveAuditEvidenceStage.COMMAND_DISPATCH, audit_outcome)
    result = build_executive_control_plane_observation(
        record,
        observation_id=ExecutiveControlPlaneObservationId(UUID(int=11)),
        observed_at=_NOW + timedelta(seconds=1),
    )

    assert isinstance(result, Success)
    observation = result.value
    assert observation.outcome is observation_outcome
    assert observation.audit_record_id == record.record_id
    assert observation.authority_version == record.authority_version
    assert observation.correlation_id == record.correlation_id
    assert tuple(item.value for item in observation.evidence_refs) == (
        "audit:a",
        "audit:z",
    )


def test_audit_append_has_dedicated_observable_stage() -> None:
    record = _record(
        ExecutiveAuditEvidenceStage.AUTHORIZATION,
        ExecutiveAuditEvidenceOutcome.BLOCKED,
    )
    result = build_executive_audit_append_observation(
        record,
        observation_id=ExecutiveControlPlaneObservationId(UUID(int=12)),
        observed_at=_NOW + timedelta(seconds=2),
    )

    assert isinstance(result, Success)
    assert result.value.stage is ExecutiveControlPlaneObservationStage.AUDIT
    assert result.value.outcome is ExecutiveControlPlaneObservationOutcome.SUCCEEDED
    assert result.value.audit_record_id == record.record_id


def test_observation_is_immutable_deterministic_and_contains_no_payload_or_reason() -> None:
    record = _record(
        ExecutiveAuditEvidenceStage.AUTHENTICATION,
        ExecutiveAuditEvidenceOutcome.SUCCEEDED,
    )
    result = build_executive_control_plane_observation(
        record,
        observation_id=ExecutiveControlPlaneObservationId(UUID(int=13)),
        observed_at=_NOW + timedelta(seconds=1),
    )
    assert isinstance(result, Success)
    observation = result.value

    assert observation.logical_values() == observation.logical_values()
    assert not hasattr(observation, "reason_code")
    assert not hasattr(observation, "metadata")
    assert not hasattr(observation, "payload")
    with pytest.raises(FrozenInstanceError):
        observation.__setattr__(
            "outcome",
            ExecutiveControlPlaneObservationOutcome.FAILED,
        )


def test_observation_rejects_implicit_identity_and_invalid_chronology() -> None:
    with pytest.raises(ExecutiveControlPlaneObservabilityValidationError):
        ExecutiveControlPlaneObservationId(cast(UUID, "observation"))

    result = build_executive_control_plane_observation(
        _record(
            ExecutiveAuditEvidenceStage.AUTHENTICATION,
            ExecutiveAuditEvidenceOutcome.SUCCEEDED,
        ),
        observation_id=ExecutiveControlPlaneObservationId(UUID(int=14)),
        observed_at=_NOW - timedelta(microseconds=1),
    )

    assert not isinstance(result, Success)


def test_observability_port_is_structural_and_does_not_aggregate_inside_core() -> None:
    record = _record(
        ExecutiveAuditEvidenceStage.AUTHORITY,
        ExecutiveAuditEvidenceOutcome.BLOCKED,
    )
    built = build_executive_control_plane_observation(
        record,
        observation_id=ExecutiveControlPlaneObservationId(UUID(int=15)),
        observed_at=_NOW + timedelta(seconds=1),
    )
    assert isinstance(built, Success)
    sink: ExecutiveControlPlaneObservabilityPort = _FakeObservabilityPort()

    emitted = sink.emit(built.value)

    assert isinstance(emitted, Success)
