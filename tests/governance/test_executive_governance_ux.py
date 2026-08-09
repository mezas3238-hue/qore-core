from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime, timedelta
from uuid import UUID

from qore.domain.events import CorrelationId
from qore.governance.executive_client_surface import ExecutiveClientSurfaceId
from qore.governance.executive_control import (
    AuthorizedExecutiveControlIntent,
    ExecutiveAuthorityGrant,
    ExecutiveAuthorityVersion,
    ExecutiveControlAction,
    ExecutiveControlIntent,
    ExecutiveGrantId,
    ExecutiveIntentId,
    ExecutivePrincipalId,
    ExecutiveReadScope,
)
from qore.governance.executive_governance_ux import (
    ExecutiveGovernanceUxPhase,
    ExecutiveGovernanceUxStateId,
    build_executive_governance_pending_state,
    build_executive_governance_result_state,
    build_executive_governance_unknown_outcome_state,
)
from qore.governance.executive_ports import (
    ExecutiveControlReceipt,
    ExecutiveControlReceiptStatus,
    ExecutiveEvidenceRef,
    ExecutiveReceiptId,
    build_executive_control_receipt,
)
from qore.governance.executive_replay_idempotency import (
    ExecutiveReplayClaimReceipt,
    ExecutiveReplayClaimStatus,
    build_executive_control_replay_claim,
    build_executive_replay_claim_receipt,
)
from qore.kernel.result import Failure, Success

_NOW = datetime(2026, 8, 9, 16, 0, tzinfo=UTC)
_SURFACE = ExecutiveClientSurfaceId(UUID("59000000-0000-0000-0000-000000000001"))
_PRINCIPAL = ExecutivePrincipalId("ceo.primary")


def _authorized() -> AuthorizedExecutiveControlIntent:
    grant = ExecutiveAuthorityGrant(
        grant_id=ExecutiveGrantId(UUID("59000000-0000-0000-0000-000000000002")),
        principal_id=_PRINCIPAL,
        authority_version=ExecutiveAuthorityVersion("authority.v4"),
        allowed_actions=(ExecutiveControlAction.PAUSE_SYSTEM,),
        allowed_read_scopes=(ExecutiveReadScope.GOVERNANCE,),
        issued_at=_NOW,
        expires_at=_NOW + timedelta(minutes=30),
        reason="mission05 governance UX",
    )
    intent = ExecutiveControlIntent(
        intent_id=ExecutiveIntentId(UUID("59000000-0000-0000-0000-000000000003")),
        principal_id=_PRINCIPAL,
        action=ExecutiveControlAction.PAUSE_SYSTEM,
        requested_at=_NOW + timedelta(minutes=1),
        correlation_id=CorrelationId(
            UUID("59000000-0000-0000-0000-000000000004")
        ),
        reason="CEO governed pause",
    )
    return AuthorizedExecutiveControlIntent(
        intent=intent,
        grant=grant,
        authorized_at=_NOW + timedelta(minutes=2),
    )


def _receipt(
    authorized: AuthorizedExecutiveControlIntent,
    status: ExecutiveControlReceiptStatus,
) -> ExecutiveControlReceipt:
    result = build_executive_control_receipt(
        authorized,
        receipt_id=ExecutiveReceiptId(
            UUID("59000000-0000-0000-0000-000000000005")
        ),
        received_at=_NOW + timedelta(minutes=3),
        completed_at=_NOW + timedelta(minutes=4),
        status=status,
        reason_code=f"governance.{status.value}",
        evidence_refs=(ExecutiveEvidenceRef("audit:governance/59000000"),),
    )
    assert isinstance(result, Success)
    return result.value


def _acquired_replay(
    authorized: AuthorizedExecutiveControlIntent,
) -> ExecutiveReplayClaimReceipt:
    request_result = build_executive_control_replay_claim(
        authorized,
        requested_at=_NOW + timedelta(minutes=2, seconds=1),
    )
    assert isinstance(request_result, Success)
    receipt_result = build_executive_replay_claim_receipt(
        request_result.value,
        observed_fingerprint=request_result.value.fingerprint,
        completed_at=_NOW + timedelta(minutes=2, seconds=2),
        status=ExecutiveReplayClaimStatus.ACQUIRED,
    )
    assert isinstance(receipt_result, Success)
    return receipt_result.value


def test_pending_never_claims_applied_without_receipt() -> None:
    authorized = _authorized()
    result = build_executive_governance_pending_state(
        state_id=ExecutiveGovernanceUxStateId(UUID(int=6)),
        surface_id=_SURFACE,
        authorized=authorized,
        observed_at=_NOW + timedelta(minutes=2),
    )

    assert isinstance(result, Success)
    assert result.value.phase is ExecutiveGovernanceUxPhase.PENDING
    assert result.value.receipt is None
    assert not result.value.is_confirmed_applied
    assert not result.value.automatic_redispatch_allowed


def test_control_receipt_is_only_source_of_terminal_presentation_outcome() -> None:
    authorized = _authorized()
    expectations = (
        (ExecutiveControlReceiptStatus.APPLIED, ExecutiveGovernanceUxPhase.APPLIED),
        (ExecutiveControlReceiptStatus.NO_CHANGE, ExecutiveGovernanceUxPhase.NO_ACTION),
        (ExecutiveControlReceiptStatus.BLOCKED, ExecutiveGovernanceUxPhase.BLOCKED),
        (ExecutiveControlReceiptStatus.FAILED, ExecutiveGovernanceUxPhase.FAILED),
    )

    for receipt_status, expected_phase in expectations:
        receipt = _receipt(authorized, receipt_status)
        result = build_executive_governance_result_state(
            state_id=ExecutiveGovernanceUxStateId(UUID(int=7)),
            surface_id=_SURFACE,
            authorized=authorized,
            receipt=receipt,
            observed_at=_NOW + timedelta(minutes=5),
        )
        assert isinstance(result, Success)
        assert result.value.phase is expected_phase
        assert result.value.receipt is receipt
        assert result.value.is_confirmed_applied is (
            expected_phase is ExecutiveGovernanceUxPhase.APPLIED
        )
        assert not result.value.automatic_redispatch_allowed


def test_mismatched_receipt_fails_closed() -> None:
    authorized = _authorized()
    receipt = _receipt(authorized, ExecutiveControlReceiptStatus.APPLIED)
    mismatched = replace(receipt, principal_id=ExecutivePrincipalId("ceo.other"))

    result = build_executive_governance_result_state(
        state_id=ExecutiveGovernanceUxStateId(UUID(int=8)),
        surface_id=_SURFACE,
        authorized=authorized,
        receipt=mismatched,
        observed_at=_NOW + timedelta(minutes=5),
    )

    assert isinstance(result, Failure)


def test_ambiguous_outcome_requires_acquired_replay_and_never_auto_redispatches() -> None:
    authorized = _authorized()
    replay = _acquired_replay(authorized)
    result = build_executive_governance_unknown_outcome_state(
        state_id=ExecutiveGovernanceUxStateId(UUID(int=9)),
        surface_id=_SURFACE,
        authorized=authorized,
        replay_claim=replay,
        observed_at=_NOW + timedelta(minutes=3),
    )

    assert isinstance(result, Success)
    assert result.value.phase is ExecutiveGovernanceUxPhase.OUTCOME_UNKNOWN
    assert result.value.receipt is None
    assert result.value.replay_claim is replay
    assert not result.value.is_confirmed_applied
    assert not result.value.automatic_redispatch_allowed


def test_duplicate_replay_cannot_masquerade_as_unknown_dispatched_outcome() -> None:
    authorized = _authorized()
    acquired = _acquired_replay(authorized)
    duplicate = replace(acquired, status=ExecutiveReplayClaimStatus.DUPLICATE)

    result = build_executive_governance_unknown_outcome_state(
        state_id=ExecutiveGovernanceUxStateId(UUID(int=10)),
        surface_id=_SURFACE,
        authorized=authorized,
        replay_claim=duplicate,
        observed_at=_NOW + timedelta(minutes=3),
    )

    assert isinstance(result, Failure)


def test_unknown_outcome_replay_must_match_exact_authorization() -> None:
    authorized = _authorized()
    replay = _acquired_replay(authorized)
    mismatched = replace(
        replay,
        correlation_id=CorrelationId(UUID(int=11)),
    )

    result = build_executive_governance_unknown_outcome_state(
        state_id=ExecutiveGovernanceUxStateId(UUID(int=12)),
        surface_id=_SURFACE,
        authorized=authorized,
        replay_claim=mismatched,
        observed_at=_NOW + timedelta(minutes=3),
    )

    assert isinstance(result, Failure)


def test_governance_ux_is_presentation_only() -> None:
    result = build_executive_governance_pending_state(
        state_id=ExecutiveGovernanceUxStateId(UUID(int=13)),
        surface_id=_SURFACE,
        authorized=_authorized(),
        observed_at=_NOW + timedelta(minutes=2),
    )
    assert isinstance(result, Success)
    state = result.value

    assert state.logical_values() == state.logical_values()
    assert not hasattr(state, "dispatch")
    assert not hasattr(state, "retry")
    assert not hasattr(state, "submit_order")
    assert not hasattr(state, "buy")
    assert not hasattr(state, "sell")
    assert not hasattr(state, "bypass_risk")
