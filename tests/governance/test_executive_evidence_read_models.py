from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID

import pytest

import qore.governance.executive_evidence_read_models as evidence_models
from qore.governance.executive_control import ExecutiveReadScope
from qore.governance.executive_ports import ExecutiveEvidenceRef
from qore.governance.executive_read_models import (
    ExecutiveAttentionLevel,
    ExecutivePolicyVersionRef,
    ExecutiveProjectionId,
    ExecutiveProjectionMetadata,
    ExecutiveProjectionVersion,
    ExecutiveReadModelValidationError,
    ExecutiveSourceFreshness,
)

_NOW = datetime(2026, 8, 8, 21, 30, tzinfo=UTC)


def _metadata(scope: ExecutiveReadScope) -> ExecutiveProjectionMetadata:
    return ExecutiveProjectionMetadata(
        projection_id=ExecutiveProjectionId(
            UUID("2b000000-0000-0000-0000-000000000001")
        ),
        projection_version=ExecutiveProjectionVersion("executive-evidence.v1"),
        scope=scope,
        source_observed_at=_NOW,
        projected_at=_NOW + timedelta(seconds=1),
        freshness=ExecutiveSourceFreshness.FRESH,
        evidence_refs=(ExecutiveEvidenceRef("evidence:executive/root-002"),),
    )


def _validation_summary(
    assessment_id: str,
) -> evidence_models.ExecutiveValidationAssessmentSummary:
    return evidence_models.ExecutiveValidationAssessmentSummary(
        assessment_ref=evidence_models.ExecutiveValidationAssessmentRef(
            UUID(assessment_id)
        ),
        subject_ref=evidence_models.ExecutiveValidationSubjectRef("analysis:opaque-001"),
        policy_version=ExecutivePolicyVersionRef("validation.v3"),
        verdict=evidence_models.ExecutiveValidationVerdict.PASSED,
        observed_confidence=evidence_models.ExecutiveValidationConfidence(0.9),
        reason_codes=("confidence.sufficient",),
        evidence_refs=(ExecutiveEvidenceRef("evidence:validation/001"),),
    )


def test_validation_lab_projection_does_not_expose_internal_analysis() -> None:
    model = evidence_models.ExecutiveValidationLabReadModel(
        metadata=_metadata(ExecutiveReadScope.VALIDATION_LAB),
        attention=ExecutiveAttentionLevel.INFORMATION,
        assessments=(
            _validation_summary("2b000000-0000-0000-0000-000000000003"),
            _validation_summary("2b000000-0000-0000-0000-000000000002"),
        ),
    )

    assert tuple(str(item.assessment_ref.value) for item in model.assessments) == (
        "2b000000-0000-0000-0000-000000000002",
        "2b000000-0000-0000-0000-000000000003",
    )
    assert not hasattr(model.assessments[0], "source_analysis")
    assert not hasattr(model.assessments[0], "validation_policy")
    assert model.logical_values() == model.logical_values()


def test_validation_lab_projection_is_scope_bound() -> None:
    with pytest.raises(ExecutiveReadModelValidationError):
        evidence_models.ExecutiveValidationLabReadModel(
            metadata=_metadata(ExecutiveReadScope.AUDIT),
            attention=ExecutiveAttentionLevel.ATTENTION,
            assessments=(),
        )


def test_validation_pass_or_fail_requires_observed_confidence_and_evidence() -> None:
    with pytest.raises(ExecutiveReadModelValidationError):
        evidence_models.ExecutiveValidationAssessmentSummary(
            assessment_ref=evidence_models.ExecutiveValidationAssessmentRef(
                UUID("2b000000-0000-0000-0000-000000000004")
            ),
            subject_ref=evidence_models.ExecutiveValidationSubjectRef(
                "analysis:opaque-002"
            ),
            policy_version=ExecutivePolicyVersionRef("validation.v3"),
            verdict=evidence_models.ExecutiveValidationVerdict.FAILED,
            observed_confidence=None,
            reason_codes=("confidence.insufficient",),
            evidence_refs=(ExecutiveEvidenceRef("evidence:validation/002"),),
        )

    with pytest.raises(ExecutiveReadModelValidationError):
        evidence_models.ExecutiveValidationAssessmentSummary(
            assessment_ref=evidence_models.ExecutiveValidationAssessmentRef(
                UUID("2b000000-0000-0000-0000-000000000005")
            ),
            subject_ref=evidence_models.ExecutiveValidationSubjectRef(
                "analysis:opaque-003"
            ),
            policy_version=ExecutivePolicyVersionRef("validation.v3"),
            verdict=evidence_models.ExecutiveValidationVerdict.UNKNOWN,
            observed_confidence=None,
            reason_codes=("evidence.missing",),
            evidence_refs=(),
        )


def test_trade_forensic_case_enforces_chronology_and_lifecycle() -> None:
    case = evidence_models.ExecutiveTradeForensicCase(
        case_id=evidence_models.ExecutiveTradeForensicCaseId(
            UUID("2b000000-0000-0000-0000-000000000006")
        ),
        trade_ref=evidence_models.ExecutiveTradeRef("trade:opaque-001"),
        opened_at=_NOW,
        concluded_at=_NOW + timedelta(minutes=10),
        state=evidence_models.ExecutiveTradeForensicState.CONCLUDED,
        outcome_code="execution.expected",
        reason_codes=("evidence.consistent",),
        evidence_refs=(ExecutiveEvidenceRef("evidence:forensics/support-001"),),
        counter_evidence_refs=(
            ExecutiveEvidenceRef("evidence:forensics/counter-001"),
        ),
    )

    assert case.state is evidence_models.ExecutiveTradeForensicState.CONCLUDED
    assert not hasattr(case, "broker_order")
    assert not hasattr(case, "account_number")

    with pytest.raises(ExecutiveReadModelValidationError):
        evidence_models.ExecutiveTradeForensicCase(
            case_id=evidence_models.ExecutiveTradeForensicCaseId(
                UUID("2b000000-0000-0000-0000-000000000007")
            ),
            trade_ref=evidence_models.ExecutiveTradeRef("trade:opaque-002"),
            opened_at=_NOW,
            concluded_at=_NOW + timedelta(minutes=1),
            state=evidence_models.ExecutiveTradeForensicState.OPEN,
            outcome_code="pending",
            reason_codes=("investigation.open",),
            evidence_refs=(ExecutiveEvidenceRef("evidence:forensics/open-001"),),
        )


def test_trade_forensics_projection_is_scope_bound_and_rejects_duplicate_cases() -> None:
    case = evidence_models.ExecutiveTradeForensicCase(
        case_id=evidence_models.ExecutiveTradeForensicCaseId(
            UUID("2b000000-0000-0000-0000-000000000008")
        ),
        trade_ref=evidence_models.ExecutiveTradeRef("trade:opaque-003"),
        opened_at=_NOW,
        concluded_at=None,
        state=evidence_models.ExecutiveTradeForensicState.OPEN,
        outcome_code="pending",
        reason_codes=("investigation.open",),
        evidence_refs=(ExecutiveEvidenceRef("evidence:forensics/open-002"),),
    )

    with pytest.raises(ExecutiveReadModelValidationError):
        evidence_models.ExecutiveTradeForensicsReadModel(
            metadata=_metadata(ExecutiveReadScope.AUDIT),
            attention=ExecutiveAttentionLevel.ATTENTION,
            cases=(case,),
        )

    with pytest.raises(ExecutiveReadModelValidationError):
        evidence_models.ExecutiveTradeForensicsReadModel(
            metadata=_metadata(ExecutiveReadScope.TRADE_FORENSICS),
            attention=ExecutiveAttentionLevel.IMPORTANT,
            cases=(case, case),
        )


def test_trade_forensics_keeps_support_and_counter_evidence_distinct() -> None:
    shared = ExecutiveEvidenceRef("evidence:forensics/shared-001")

    with pytest.raises(ExecutiveReadModelValidationError):
        evidence_models.ExecutiveTradeForensicCase(
            case_id=evidence_models.ExecutiveTradeForensicCaseId(
                UUID("2b000000-0000-0000-0000-000000000009")
            ),
            trade_ref=evidence_models.ExecutiveTradeRef("trade:opaque-004"),
            opened_at=_NOW,
            concluded_at=_NOW,
            state=evidence_models.ExecutiveTradeForensicState.INCONCLUSIVE,
            outcome_code="evidence.conflict",
            reason_codes=("evidence.conflict",),
            evidence_refs=(shared,),
            counter_evidence_refs=(shared,),
        )


def _audit_record(
    record_id: str,
    occurred_at: datetime,
) -> evidence_models.ExecutiveAuditRecord:
    return evidence_models.ExecutiveAuditRecord(
        record_id=evidence_models.ExecutiveAuditRecordId(UUID(record_id)),
        occurred_at=occurred_at,
        correlation_id=evidence_models.ExecutiveAuditCorrelationId(
            UUID("2b000000-0000-0000-0000-000000000020")
        ),
        actor_code="cibo",
        category_code="decision",
        action_code="evaluate-opportunity",
        outcome=evidence_models.ExecutiveAuditOutcome.NO_ACTION,
        reason_codes=("evidence.insufficient",),
        evidence_refs=(ExecutiveEvidenceRef(f"evidence:audit/{record_id[-3:]}"),),
    )


def test_audit_projection_makes_no_action_explicit_and_deterministic() -> None:
    later = _audit_record(
        "2b000000-0000-0000-0000-000000000012",
        _NOW + timedelta(seconds=2),
    )
    earlier = _audit_record(
        "2b000000-0000-0000-0000-000000000011",
        _NOW + timedelta(seconds=1),
    )
    model = evidence_models.ExecutiveAuditReadModel(
        metadata=_metadata(ExecutiveReadScope.AUDIT),
        attention=ExecutiveAttentionLevel.INFORMATION,
        records=(later, earlier),
    )

    assert model.records == (earlier, later)
    assert all(
        item.outcome is evidence_models.ExecutiveAuditOutcome.NO_ACTION
        for item in model.records
    )
    assert not hasattr(model.records[0], "raw_log")
    assert not hasattr(model.records[0], "payload")
    assert model.logical_values() == model.logical_values()


def test_audit_projection_rejects_wrong_scope_duplicate_ids_and_secret_codes() -> None:
    record = _audit_record(
        "2b000000-0000-0000-0000-000000000013",
        _NOW,
    )

    with pytest.raises(ExecutiveReadModelValidationError):
        evidence_models.ExecutiveAuditReadModel(
            metadata=_metadata(ExecutiveReadScope.TRADE_FORENSICS),
            attention=ExecutiveAttentionLevel.ATTENTION,
            records=(record,),
        )

    with pytest.raises(ExecutiveReadModelValidationError):
        evidence_models.ExecutiveAuditReadModel(
            metadata=_metadata(ExecutiveReadScope.AUDIT),
            attention=ExecutiveAttentionLevel.CRITICAL,
            records=(record, record),
        )

    with pytest.raises(ExecutiveReadModelValidationError):
        evidence_models.ExecutiveAuditRecord(
            record_id=evidence_models.ExecutiveAuditRecordId(
                UUID("2b000000-0000-0000-0000-000000000014")
            ),
            occurred_at=_NOW,
            correlation_id=evidence_models.ExecutiveAuditCorrelationId(
                UUID("2b000000-0000-0000-0000-000000000021")
            ),
            actor_code="token=secret",
            category_code="decision",
            action_code="evaluate-opportunity",
            outcome=evidence_models.ExecutiveAuditOutcome.REJECTED,
            reason_codes=("policy.denied",),
            evidence_refs=(ExecutiveEvidenceRef("evidence:audit/denied-001"),),
        )
