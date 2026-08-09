from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID

import pytest

import qore.infrastructure.client_accounts as accounts
import qore.infrastructure.hosting_reliability_incident as incident
import qore.infrastructure.hosting_reliability_lab as lab
import qore.kernel.result as result

_NOW = datetime(2026, 8, 10, 7, 0, tzinfo=UTC)
_ACCOUNT = accounts.TradingAccountId(UUID("59000000-0000-0000-0000-000000000003"))
_RUNTIME = accounts.ExecutionRuntimeReference(
    UUID("59000000-0000-0000-0000-000000000004")
)


def _uuid(suffix: int) -> UUID:
    return UUID(f"59000000-0000-0000-0000-{suffix:012d}")


def _observation(
    *,
    suffix: int,
    severity: lab.HostingReliabilitySeverity,
) -> lab.HostingReliabilityObservation:
    return lab.HostingReliabilityObservation(
        observation_id=lab.HostingReliabilityObservationId(_uuid(suffix)),
        account_id=_ACCOUNT,
        runtime_ref=_RUNTIME,
        boundary=lab.HostingReliabilityBoundary.NETWORK_EGRESS,
        condition=lab.HostingReliabilityCondition.ANOMALOUS,
        severity=severity,
        observed_at=_NOW,
        evidence_ref=lab.HostingReliabilityEvidenceReference(_uuid(suffix + 1)),
    )


def _policy(
    action: lab.HostingReliabilityInfrastructureAction,
    *,
    suffix: int,
) -> lab.HostingReliabilityPolicySnapshot:
    actions = (
        (lab.HostingReliabilityInfrastructureAction.NO_ACTION,)
        if action is lab.HostingReliabilityInfrastructureAction.NO_ACTION
        else (lab.HostingReliabilityInfrastructureAction.NO_ACTION, action)
    )
    return lab.HostingReliabilityPolicySnapshot(
        policy_ref=lab.HostingReliabilityPolicyReference(_uuid(suffix)),
        version=1,
        allowed_actions=actions,
        effective_at=_NOW - timedelta(minutes=1),
        expires_at=None,
    )


def _assessment(
    action: lab.HostingReliabilityInfrastructureAction,
    *,
    suffix: int,
    severity: lab.HostingReliabilitySeverity = lab.HostingReliabilitySeverity.DEGRADED,
) -> tuple[lab.HostingReliabilityObservation, lab.HostingReliabilityAssessment]:
    observation = _observation(suffix=suffix, severity=severity)
    assessed = lab.assess_hosting_reliability_observation(
        observation,
        _policy(action, suffix=suffix + 10),
        assessment_id=lab.HostingReliabilityAssessmentId(_uuid(suffix + 20)),
        authorized_action=action,
        rationale_code=lab.HostingReliabilityRationaleCode("egress.reliability"),
        assessed_at=_NOW + timedelta(seconds=1),
        supporting_evidence_refs=(
            lab.HostingReliabilityEvidenceReference(_uuid(suffix + 21)),
        ),
    )
    assert isinstance(assessed, result.Success)
    return observation, assessed.value


def _anomaly_report(
    action: lab.HostingReliabilityInfrastructureAction,
    *,
    suffix: int,
    severity: lab.HostingReliabilitySeverity = lab.HostingReliabilitySeverity.DEGRADED,
) -> incident.HostingReliabilityAnomalyReport:
    observation, assessment = _assessment(
        action,
        suffix=suffix,
        severity=severity,
    )
    built = incident.build_hosting_reliability_anomaly_report(
        observation,
        assessment,
        report_id=incident.HostingReliabilityAnomalyReportId(_uuid(suffix + 30)),
        metric_name=incident.HostingReliabilityMetricName("network_egress.p99"),
        threshold_evidence_ref=lab.HostingReliabilityEvidenceReference(
            _uuid(suffix + 31)
        ),
        generated_at=_NOW + timedelta(seconds=2),
        evidence_ref=lab.HostingReliabilityEvidenceReference(_uuid(suffix + 32)),
    )
    assert isinstance(built, result.Success)
    return built.value


def _opened_incident(
    action: lab.HostingReliabilityInfrastructureAction,
    *,
    suffix: int,
) -> incident.HostingReliabilityIncident:
    anomaly = _anomaly_report(action, suffix=suffix)
    opened = incident.open_hosting_reliability_incident(
        anomaly,
        incident_id=incident.HostingReliabilityIncidentId(_uuid(suffix + 40)),
        opened_at=_NOW + timedelta(seconds=3),
        evidence_ref=lab.HostingReliabilityEvidenceReference(_uuid(suffix + 41)),
    )
    assert isinstance(opened, result.Success)
    return opened.value


def _action_record(
    opened: incident.HostingReliabilityIncident,
    *,
    suffix: int,
) -> lab.HostingReliabilityActionRecord:
    assessment = opened.anomaly_report.assessment
    recorded = lab.record_hosting_reliability_action(
        assessment,
        action_id=lab.HostingReliabilityActionId(_uuid(suffix)),
        action=assessment.authorized_action,
        outcome=lab.HostingReliabilityActionOutcome.SUCCEEDED,
        occurred_at=_NOW + timedelta(seconds=4),
        evidence_ref=lab.HostingReliabilityEvidenceReference(_uuid(suffix + 1)),
    )
    assert isinstance(recorded, result.Success)
    return recorded.value


def test_transient_anomaly_can_record_justified_no_action_without_incident() -> None:
    anomaly = _anomaly_report(
        lab.HostingReliabilityInfrastructureAction.NO_ACTION,
        suffix=10,
        severity=lab.HostingReliabilitySeverity.WARNING,
    )

    assert anomaly.is_justified_no_action is True
    assert anomaly.assessment.authorized_action is (
        lab.HostingReliabilityInfrastructureAction.NO_ACTION
    )
    assert anomaly.metric_name == incident.HostingReliabilityMetricName(
        "network_egress.p99"
    )

    opened = incident.open_hosting_reliability_incident(
        anomaly,
        incident_id=incident.HostingReliabilityIncidentId(_uuid(50)),
        opened_at=_NOW + timedelta(seconds=3),
        evidence_ref=lab.HostingReliabilityEvidenceReference(_uuid(51)),
    )
    assert isinstance(opened, result.Failure)
    assert isinstance(
        opened.error,
        incident.HostingReliabilityIncidentAuthorizationError,
    )


def test_intervention_incident_inherits_exact_lab_assessment_authority() -> None:
    opened = _opened_incident(
        lab.HostingReliabilityInfrastructureAction.RUN_STABILIZATION,
        suffix=100,
    )

    assert opened.authorized_action is (
        lab.HostingReliabilityInfrastructureAction.RUN_STABILIZATION
    )
    assert opened.anomaly_report.assessment.policy_ref == lab.HostingReliabilityPolicyReference(
        _uuid(110)
    )
    assert opened.anomaly_report.assessment.rationale_code == (
        lab.HostingReliabilityRationaleCode("egress.reliability")
    )


def test_failed_recovery_attempt_requires_explicit_failure_reason() -> None:
    opened = _opened_incident(
        lab.HostingReliabilityInfrastructureAction.RUN_STABILIZATION,
        suffix=200,
    )

    with pytest.raises(incident.HostingReliabilityIncidentValidationError):
        incident.HostingReliabilityRecoveryAttempt(
            attempt_id=incident.HostingReliabilityRecoveryAttemptId(_uuid(250)),
            incident_id=opened.incident_id,
            ordinal=1,
            procedure_ref=incident.HostingReliabilityProcedureReference(_uuid(251)),
            rationale_code=lab.HostingReliabilityRationaleCode("recovery.restart_channel"),
            started_at=_NOW + timedelta(seconds=5),
            completed_at=_NOW + timedelta(seconds=6),
            outcome=incident.HostingReliabilityRecoveryOutcome.FAILED,
            failure_reason=None,
            evidence_ref=lab.HostingReliabilityEvidenceReference(_uuid(252)),
        )


def test_incident_report_preserves_failed_recovery_and_unresolved_post_certification() -> None:
    opened = _opened_incident(
        lab.HostingReliabilityInfrastructureAction.RUN_STABILIZATION,
        suffix=300,
    )
    action = _action_record(opened, suffix=350)
    recovery = incident.HostingReliabilityRecoveryAttempt(
        attempt_id=incident.HostingReliabilityRecoveryAttemptId(_uuid(360)),
        incident_id=opened.incident_id,
        ordinal=1,
        procedure_ref=incident.HostingReliabilityProcedureReference(_uuid(361)),
        rationale_code=lab.HostingReliabilityRationaleCode("recovery.restart_channel"),
        started_at=_NOW + timedelta(seconds=5),
        completed_at=_NOW + timedelta(seconds=6),
        outcome=incident.HostingReliabilityRecoveryOutcome.FAILED,
        failure_reason=incident.HostingReliabilityRecoveryReasonCode(
            "recovery.channel_still_degraded"
        ),
        evidence_ref=lab.HostingReliabilityEvidenceReference(_uuid(362)),
    )
    post = incident.HostingReliabilityPostActionCertification(
        certification_id=incident.HostingReliabilityPostCertificationId(_uuid(370)),
        incident_id=opened.incident_id,
        state=incident.HostingReliabilityPostCertificationState.NOT_CERTIFIED,
        certified_at=_NOW + timedelta(seconds=7),
        evidence_refs=(lab.HostingReliabilityEvidenceReference(_uuid(371)),),
    )
    report = incident.HostingReliabilityIncidentReport(
        report_id=incident.HostingReliabilityIncidentReportId(_uuid(380)),
        incident=opened,
        action_record=action,
        recovery_attempts=(recovery,),
        post_certification=post,
        generated_at=_NOW + timedelta(seconds=8),
        evidence_ref=lab.HostingReliabilityEvidenceReference(_uuid(381)),
    )

    assert report.final_state is incident.HostingReliabilityIncidentFinalState.UNRESOLVED
    assert report.recovery_attempts[0].failure_reason == (
        incident.HostingReliabilityRecoveryReasonCode(
            "recovery.channel_still_degraded"
        )
    )
    assert report.action_record.assessment_id == (
        opened.anomaly_report.assessment.assessment_id
    )


def test_certified_post_action_evidence_resolves_report_without_erasing_history() -> None:
    opened = _opened_incident(
        lab.HostingReliabilityInfrastructureAction.CONTAIN_NEW_WORK,
        suffix=400,
    )
    action = _action_record(opened, suffix=450)
    post = incident.HostingReliabilityPostActionCertification(
        certification_id=incident.HostingReliabilityPostCertificationId(_uuid(460)),
        incident_id=opened.incident_id,
        state=incident.HostingReliabilityPostCertificationState.CERTIFIED,
        certified_at=_NOW + timedelta(seconds=5),
        evidence_refs=(
            lab.HostingReliabilityEvidenceReference(_uuid(461)),
            lab.HostingReliabilityEvidenceReference(_uuid(462)),
        ),
    )
    report = incident.HostingReliabilityIncidentReport(
        report_id=incident.HostingReliabilityIncidentReportId(_uuid(470)),
        incident=opened,
        action_record=action,
        recovery_attempts=(),
        post_certification=post,
        generated_at=_NOW + timedelta(seconds=6),
        evidence_ref=lab.HostingReliabilityEvidenceReference(_uuid(471)),
    )

    assert report.final_state is incident.HostingReliabilityIncidentFinalState.RESOLVED
    assert report.incident.anomaly_report.observation.condition is (
        lab.HostingReliabilityCondition.ANOMALOUS
    )
    assert report.incident.anomaly_report.assessment.rationale_code == (
        lab.HostingReliabilityRationaleCode("egress.reliability")
    )


def test_action_record_from_other_assessment_cannot_be_spliced_into_incident() -> None:
    opened = _opened_incident(
        lab.HostingReliabilityInfrastructureAction.CONTAIN_NEW_WORK,
        suffix=500,
    )
    other = _opened_incident(
        lab.HostingReliabilityInfrastructureAction.CONTAIN_NEW_WORK,
        suffix=600,
    )
    wrong_action = _action_record(other, suffix=650)
    post = incident.HostingReliabilityPostActionCertification(
        certification_id=incident.HostingReliabilityPostCertificationId(_uuid(660)),
        incident_id=opened.incident_id,
        state=incident.HostingReliabilityPostCertificationState.CERTIFIED,
        certified_at=_NOW + timedelta(seconds=5),
        evidence_refs=(lab.HostingReliabilityEvidenceReference(_uuid(661)),),
    )

    with pytest.raises(incident.HostingReliabilityIncidentValidationError):
        incident.HostingReliabilityIncidentReport(
            report_id=incident.HostingReliabilityIncidentReportId(_uuid(670)),
            incident=opened,
            action_record=wrong_action,
            recovery_attempts=(),
            post_certification=post,
            generated_at=_NOW + timedelta(seconds=6),
            evidence_ref=lab.HostingReliabilityEvidenceReference(_uuid(671)),
        )


def test_recovery_ordinals_must_be_contiguous_and_bound_to_same_incident() -> None:
    opened = _opened_incident(
        lab.HostingReliabilityInfrastructureAction.RUN_STABILIZATION,
        suffix=700,
    )
    action = _action_record(opened, suffix=750)
    recovery = incident.HostingReliabilityRecoveryAttempt(
        attempt_id=incident.HostingReliabilityRecoveryAttemptId(_uuid(760)),
        incident_id=opened.incident_id,
        ordinal=2,
        procedure_ref=incident.HostingReliabilityProcedureReference(_uuid(761)),
        rationale_code=lab.HostingReliabilityRationaleCode("recovery.second_attempt"),
        started_at=_NOW + timedelta(seconds=5),
        completed_at=_NOW + timedelta(seconds=6),
        outcome=incident.HostingReliabilityRecoveryOutcome.SUCCEEDED,
        failure_reason=None,
        evidence_ref=lab.HostingReliabilityEvidenceReference(_uuid(762)),
    )
    post = incident.HostingReliabilityPostActionCertification(
        certification_id=incident.HostingReliabilityPostCertificationId(_uuid(770)),
        incident_id=opened.incident_id,
        state=incident.HostingReliabilityPostCertificationState.CERTIFIED,
        certified_at=_NOW + timedelta(seconds=7),
        evidence_refs=(lab.HostingReliabilityEvidenceReference(_uuid(771)),),
    )

    with pytest.raises(incident.HostingReliabilityIncidentValidationError):
        incident.HostingReliabilityIncidentReport(
            report_id=incident.HostingReliabilityIncidentReportId(_uuid(780)),
            incident=opened,
            action_record=action,
            recovery_attempts=(recovery,),
            post_certification=post,
            generated_at=_NOW + timedelta(seconds=8),
            evidence_ref=lab.HostingReliabilityEvidenceReference(_uuid(781)),
        )


def test_genealogy_contracts_expose_no_trading_provider_or_direct_failover_authority() -> None:
    prohibited = {
        "acquire_lease",
        "buy",
        "core_decision",
        "failover",
        "provider_sdk",
        "redispatch",
        "retry_order",
        "sell",
        "submit_order",
        "switch_server",
    }
    for surface in (
        incident.HostingReliabilityAnomalyReport,
        incident.HostingReliabilityIncident,
        incident.HostingReliabilityRecoveryAttempt,
        incident.HostingReliabilityPostActionCertification,
        incident.HostingReliabilityIncidentReport,
    ):
        assert prohibited.isdisjoint(set(dir(surface)))
