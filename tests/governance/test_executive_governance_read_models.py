from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID

import pytest

from qore.governance.executive_control import ExecutiveReadScope
from qore.governance.executive_governance_read_models import (
    ExecutiveGovernanceActionCode,
    ExecutiveGovernanceAuthoritySummary,
    ExecutiveGovernanceAuthorityVersionRef,
    ExecutiveGovernanceControlReceiptSummary,
    ExecutiveGovernanceCorrelationRef,
    ExecutiveGovernanceGrantRef,
    ExecutiveGovernanceIntentRef,
    ExecutiveGovernancePrincipalRef,
    ExecutiveGovernanceReadModel,
    ExecutiveGovernanceReadScopeCode,
    ExecutiveGovernanceReceiptRef,
    ExecutiveGovernanceReceiptStatusCode,
)
from qore.governance.executive_ports import ExecutiveEvidenceRef
from qore.governance.executive_read_models import (
    ExecutiveAttentionLevel,
    ExecutiveProjectionId,
    ExecutiveProjectionMetadata,
    ExecutiveProjectionVersion,
    ExecutiveReadModelValidationError,
    ExecutiveSourceFreshness,
)

_NOW = datetime(2026, 8, 8, 23, 15, tzinfo=UTC)


def _metadata(scope: ExecutiveReadScope = ExecutiveReadScope.GOVERNANCE) -> ExecutiveProjectionMetadata:
    return ExecutiveProjectionMetadata(
        projection_id=ExecutiveProjectionId(
            UUID("31000000-0000-0000-0000-000000000001")
        ),
        projection_version=ExecutiveProjectionVersion("executive-governance.v1"),
        scope=scope,
        source_observed_at=_NOW,
        projected_at=_NOW + timedelta(seconds=1),
        freshness=ExecutiveSourceFreshness.FRESH,
        evidence_refs=(ExecutiveEvidenceRef("evidence:governance/root-001"),),
    )


def _authority(
    grant_id: str = "31000000-0000-0000-0000-000000000010",
) -> ExecutiveGovernanceAuthoritySummary:
    return ExecutiveGovernanceAuthoritySummary(
        grant_ref=ExecutiveGovernanceGrantRef(UUID(grant_id)),
        principal_ref=ExecutiveGovernancePrincipalRef("ceo.primary"),
        authority_version=ExecutiveGovernanceAuthorityVersionRef("executive.v2"),
        issued_at=_NOW,
        expires_at=_NOW + timedelta(minutes=15),
        allowed_actions=(
            ExecutiveGovernanceActionCode("update-governance-policy"),
            ExecutiveGovernanceActionCode("pause-system"),
        ),
        allowed_read_scopes=(
            ExecutiveGovernanceReadScopeCode("system-health"),
            ExecutiveGovernanceReadScopeCode("governance"),
        ),
        reason_codes=("authority.authenticated",),
        evidence_refs=(ExecutiveEvidenceRef("evidence:governance/grant-001"),),
    )


def _receipt(
    receipt_id: str = "31000000-0000-0000-0000-000000000020",
    completed_at: datetime = _NOW + timedelta(seconds=4),
) -> ExecutiveGovernanceControlReceiptSummary:
    return ExecutiveGovernanceControlReceiptSummary(
        receipt_ref=ExecutiveGovernanceReceiptRef(UUID(receipt_id)),
        intent_ref=ExecutiveGovernanceIntentRef(
            UUID("31000000-0000-0000-0000-000000000030")
        ),
        principal_ref=ExecutiveGovernancePrincipalRef("ceo.primary"),
        action=ExecutiveGovernanceActionCode("pause-system"),
        authority_version=ExecutiveGovernanceAuthorityVersionRef("executive.v2"),
        correlation_ref=ExecutiveGovernanceCorrelationRef(
            UUID("31000000-0000-0000-0000-000000000040")
        ),
        received_at=_NOW + timedelta(seconds=2),
        completed_at=completed_at,
        status=ExecutiveGovernanceReceiptStatusCode("applied"),
        reason_codes=("control.applied",),
        evidence_refs=(ExecutiveEvidenceRef("evidence:governance/receipt-001"),),
    )


def test_governance_projection_is_scope_bound_and_deterministic() -> None:
    later_authority = _authority("31000000-0000-0000-0000-000000000011")
    first_authority = _authority("31000000-0000-0000-0000-000000000010")
    later_receipt = _receipt(
        "31000000-0000-0000-0000-000000000021",
        _NOW + timedelta(seconds=5),
    )
    first_receipt = _receipt(
        "31000000-0000-0000-0000-000000000020",
        _NOW + timedelta(seconds=4),
    )

    model = ExecutiveGovernanceReadModel(
        metadata=_metadata(),
        attention=ExecutiveAttentionLevel.INFORMATION,
        authorities=(later_authority, first_authority),
        control_receipts=(later_receipt, first_receipt),
    )

    assert model.authorities == (first_authority, later_authority)
    assert model.control_receipts == (first_receipt, later_receipt)
    assert model.logical_values() == model.logical_values()


def test_governance_authority_capabilities_are_projected_not_internal_objects() -> None:
    authority = _authority()

    assert tuple(item.value for item in authority.allowed_actions) == (
        "pause-system",
        "update-governance-policy",
    )
    assert tuple(item.value for item in authority.allowed_read_scopes) == (
        "governance",
        "system-health",
    )
    assert not hasattr(authority, "grant")
    assert not hasattr(authority, "raw_reason")
    assert not hasattr(authority, "credentials")


def test_governance_projection_rejects_wrong_scope_and_duplicate_refs() -> None:
    authority = _authority()
    receipt = _receipt()

    with pytest.raises(ExecutiveReadModelValidationError):
        ExecutiveGovernanceReadModel(
            metadata=_metadata(ExecutiveReadScope.AUDIT),
            attention=ExecutiveAttentionLevel.ATTENTION,
            authorities=(authority,),
            control_receipts=(receipt,),
        )

    with pytest.raises(ExecutiveReadModelValidationError):
        ExecutiveGovernanceReadModel(
            metadata=_metadata(),
            attention=ExecutiveAttentionLevel.IMPORTANT,
            authorities=(authority, authority),
            control_receipts=(),
        )

    with pytest.raises(ExecutiveReadModelValidationError):
        ExecutiveGovernanceReadModel(
            metadata=_metadata(),
            attention=ExecutiveAttentionLevel.IMPORTANT,
            authorities=(),
            control_receipts=(receipt, receipt),
        )


def test_governance_receipt_enforces_chronology_and_distinct_identity() -> None:
    with pytest.raises(ExecutiveReadModelValidationError):
        _receipt(completed_at=_NOW)

    shared = UUID("31000000-0000-0000-0000-000000000050")
    with pytest.raises(ExecutiveReadModelValidationError):
        ExecutiveGovernanceControlReceiptSummary(
            receipt_ref=ExecutiveGovernanceReceiptRef(shared),
            intent_ref=ExecutiveGovernanceIntentRef(shared),
            principal_ref=ExecutiveGovernancePrincipalRef("ceo.primary"),
            action=ExecutiveGovernanceActionCode("pause-system"),
            authority_version=ExecutiveGovernanceAuthorityVersionRef("executive.v2"),
            correlation_ref=ExecutiveGovernanceCorrelationRef(
                UUID("31000000-0000-0000-0000-000000000051")
            ),
            received_at=_NOW,
            completed_at=_NOW,
            status=ExecutiveGovernanceReceiptStatusCode("applied"),
            reason_codes=("control.applied",),
            evidence_refs=(ExecutiveEvidenceRef("evidence:governance/shared-id"),),
        )


def test_governance_authority_requires_capability_evidence_and_valid_window() -> None:
    with pytest.raises(ExecutiveReadModelValidationError):
        ExecutiveGovernanceAuthoritySummary(
            grant_ref=ExecutiveGovernanceGrantRef(
                UUID("31000000-0000-0000-0000-000000000060")
            ),
            principal_ref=ExecutiveGovernancePrincipalRef("ceo.primary"),
            authority_version=ExecutiveGovernanceAuthorityVersionRef("executive.v2"),
            issued_at=_NOW,
            expires_at=_NOW + timedelta(minutes=1),
            allowed_actions=(),
            allowed_read_scopes=(),
            reason_codes=("authority.empty",),
            evidence_refs=(ExecutiveEvidenceRef("evidence:governance/empty"),),
        )

    with pytest.raises(ExecutiveReadModelValidationError):
        ExecutiveGovernanceAuthoritySummary(
            grant_ref=ExecutiveGovernanceGrantRef(
                UUID("31000000-0000-0000-0000-000000000061")
            ),
            principal_ref=ExecutiveGovernancePrincipalRef("ceo.primary"),
            authority_version=ExecutiveGovernanceAuthorityVersionRef("executive.v2"),
            issued_at=_NOW,
            expires_at=_NOW,
            allowed_actions=(ExecutiveGovernanceActionCode("pause-system"),),
            allowed_read_scopes=(),
            reason_codes=("authority.invalid-window",),
            evidence_refs=(ExecutiveEvidenceRef("evidence:governance/window"),),
        )


def test_governance_projection_does_not_invent_materialized_restriction_state() -> None:
    model = ExecutiveGovernanceReadModel(
        metadata=_metadata(),
        attention=ExecutiveAttentionLevel.INFORMATION,
        authorities=(_authority(),),
        control_receipts=(_receipt(),),
    )

    assert not hasattr(model, "active_market_restrictions")
    assert not hasattr(model, "active_account_restrictions")
    assert not hasattr(model, "system_paused")
    assert not hasattr(model, "new_trading_halted")


def test_governance_projection_has_no_trading_execution_surface() -> None:
    model = ExecutiveGovernanceReadModel(
        metadata=_metadata(),
        attention=ExecutiveAttentionLevel.INFORMATION,
        authorities=(),
        control_receipts=(),
    )

    assert not hasattr(model, "buy")
    assert not hasattr(model, "sell")
    assert not hasattr(model, "submit_order")
    assert not hasattr(model, "close_position")
    assert not hasattr(model, "risk_bypass")


def test_governance_codes_reject_secret_like_or_free_form_values() -> None:
    with pytest.raises(ExecutiveReadModelValidationError):
        ExecutiveGovernanceActionCode("token=secret")

    with pytest.raises(ExecutiveReadModelValidationError):
        ExecutiveGovernanceReceiptStatusCode("Applied with explanation")
