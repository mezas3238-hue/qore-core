from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID

import pytest

from qore.domain.events import CorrelationId
from qore.governance.executive_control import (
    AuthorizedExecutiveControlIntent,
    ExecutiveAuthorityGrant,
    ExecutiveAuthorityVersion,
    ExecutiveControlAction,
    ExecutiveControlIntent,
    ExecutiveControlTarget,
    ExecutiveControlTargetKind,
    ExecutiveGrantId,
    ExecutiveIntentId,
    ExecutivePrincipalId,
    ExecutiveReadScope,
)
from qore.governance.executive_governance_mutation import (
    ExecutiveGovernanceMutationError,
    ExecutiveGovernanceMutationId,
    ExecutiveGovernanceMutationPort,
    ExecutiveGovernanceMutationReceipt,
    ExecutiveGovernanceMutationRequest,
    ExecutiveGovernanceMutationStatus,
    ExecutiveGovernanceMutationValidationError,
    build_executive_governance_mutation_receipt,
)
from qore.governance.executive_governance_state import (
    ExecutiveActiveRestriction,
    ExecutiveGovernancePolicyVersion,
    ExecutiveGovernanceStateSnapshot,
    ExecutiveGovernanceStateSnapshotId,
    ExecutiveGovernanceStateVersion,
    ExecutiveNewTradingState,
    ExecutiveRestrictionId,
    ExecutiveSystemRunState,
)
from qore.governance.executive_ports import ExecutiveEvidenceRef, ExecutiveReceiptId
from qore.kernel.result import Result, Success

_NOW = datetime(2026, 8, 9, 4, 0, tzinfo=UTC)
_PRINCIPAL = ExecutivePrincipalId("ceo.primary")
_SOURCE_RECEIPT = ExecutiveReceiptId(
    UUID("46000000-0000-0000-0000-000000000010")
)


def _authorized(
    action: ExecutiveControlAction,
    *,
    target: ExecutiveControlTarget | None = None,
) -> AuthorizedExecutiveControlIntent:
    grant = ExecutiveAuthorityGrant(
        grant_id=ExecutiveGrantId(UUID("46000000-0000-0000-0000-000000000001")),
        principal_id=_PRINCIPAL,
        authority_version=ExecutiveAuthorityVersion("authority.v1"),
        allowed_actions=(action,),
        allowed_read_scopes=(ExecutiveReadScope.GOVERNANCE,),
        issued_at=_NOW,
        expires_at=_NOW + timedelta(minutes=20),
        reason="mission04 governance mutation",
    )
    intent = ExecutiveControlIntent(
        intent_id=ExecutiveIntentId(UUID("46000000-0000-0000-0000-000000000002")),
        principal_id=_PRINCIPAL,
        action=action,
        requested_at=_NOW + timedelta(minutes=1),
        correlation_id=CorrelationId(
            UUID("46000000-0000-0000-0000-000000000003")
        ),
        reason="CEO governed state mutation",
        target=target,
    )
    return AuthorizedExecutiveControlIntent(
        intent=intent,
        grant=grant,
        authorized_at=_NOW + timedelta(minutes=2),
    )


def _restriction(
    *,
    restriction_id: UUID,
    target: ExecutiveControlTarget,
    source_receipt_id: ExecutiveReceiptId,
) -> ExecutiveActiveRestriction:
    return ExecutiveActiveRestriction(
        restriction_id=ExecutiveRestrictionId(restriction_id),
        target=target,
        applied_at=_NOW + timedelta(minutes=3),
        source_receipt_id=source_receipt_id,
        policy_version=ExecutiveGovernancePolicyVersion("policy.v1"),
        reason_codes=("governance.restricted",),
        evidence_refs=(ExecutiveEvidenceRef("audit:restriction/46000000"),),
    )


def _state(
    *,
    snapshot_id: UUID,
    version: str,
    observed_at: datetime,
    system: ExecutiveSystemRunState = ExecutiveSystemRunState.ACTIVE,
    trading: ExecutiveNewTradingState = ExecutiveNewTradingState.PERMITTED,
    market_restrictions: tuple[ExecutiveActiveRestriction, ...] = (),
    account_restrictions: tuple[ExecutiveActiveRestriction, ...] = (),
) -> ExecutiveGovernanceStateSnapshot:
    return ExecutiveGovernanceStateSnapshot(
        snapshot_id=ExecutiveGovernanceStateSnapshotId(snapshot_id),
        state_version=ExecutiveGovernanceStateVersion(version),
        observed_at=observed_at,
        system_run_state=system,
        new_trading_state=trading,
        market_restrictions=market_restrictions,
        account_restrictions=account_restrictions,
    )


def _request(
    authorized: AuthorizedExecutiveControlIntent,
    expected: ExecutiveGovernanceStateSnapshot,
    next_state: ExecutiveGovernanceStateSnapshot,
    *,
    source_receipt_id: ExecutiveReceiptId = _SOURCE_RECEIPT,
) -> ExecutiveGovernanceMutationRequest:
    return ExecutiveGovernanceMutationRequest(
        mutation_id=ExecutiveGovernanceMutationId(
            UUID("46000000-0000-0000-0000-000000000004")
        ),
        authorized=authorized,
        expected_state=expected,
        next_state=next_state,
        source_receipt_id=source_receipt_id,
        requested_at=_NOW + timedelta(minutes=3),
    )


def test_pause_mutation_requires_new_version_and_exact_state_transition() -> None:
    authorized = _authorized(ExecutiveControlAction.PAUSE_SYSTEM)
    expected = _state(
        snapshot_id=UUID("46000000-0000-0000-0000-000000000005"),
        version="state.v1",
        observed_at=_NOW + timedelta(minutes=2),
    )
    next_state = _state(
        snapshot_id=UUID("46000000-0000-0000-0000-000000000006"),
        version="state.v2",
        observed_at=_NOW + timedelta(minutes=3),
        system=ExecutiveSystemRunState.PAUSED,
    )

    request = _request(authorized, expected, next_state)

    assert request.expected_state is expected
    assert request.next_state is next_state
    assert request.logical_values() == request.logical_values()

    wrong_state = _state(
        snapshot_id=UUID("46000000-0000-0000-0000-000000000007"),
        version="state.v3",
        observed_at=_NOW + timedelta(minutes=3),
        system=ExecutiveSystemRunState.ACTIVE,
    )
    with pytest.raises(ExecutiveGovernanceMutationValidationError):
        _request(authorized, expected, wrong_state)


def test_restrict_market_adds_exact_target_with_exact_source_receipt() -> None:
    target = ExecutiveControlTarget(
        kind=ExecutiveControlTargetKind.MARKET,
        value="market:eurusd",
    )
    authorized = _authorized(ExecutiveControlAction.RESTRICT_MARKET, target=target)
    expected = _state(
        snapshot_id=UUID("46000000-0000-0000-0000-000000000011"),
        version="state.v1",
        observed_at=_NOW + timedelta(minutes=2),
    )
    restriction = _restriction(
        restriction_id=UUID("46000000-0000-0000-0000-000000000012"),
        target=target,
        source_receipt_id=_SOURCE_RECEIPT,
    )
    next_state = _state(
        snapshot_id=UUID("46000000-0000-0000-0000-000000000013"),
        version="state.v2",
        observed_at=_NOW + timedelta(minutes=3),
        market_restrictions=(restriction,),
    )

    request = _request(authorized, expected, next_state)
    assert request.next_state.market_restrictions == (restriction,)

    wrong_receipt = ExecutiveReceiptId(
        UUID("46000000-0000-0000-0000-000000000014")
    )
    with pytest.raises(ExecutiveGovernanceMutationValidationError):
        _request(
            authorized,
            expected,
            next_state,
            source_receipt_id=wrong_receipt,
        )


def test_restore_restriction_removes_exact_restriction_id_only() -> None:
    market_target = ExecutiveControlTarget(
        kind=ExecutiveControlTargetKind.MARKET,
        value="market:gbpusd",
    )
    old_receipt = ExecutiveReceiptId(
        UUID("46000000-0000-0000-0000-000000000020")
    )
    restriction_id = UUID("46000000-0000-0000-0000-000000000021")
    restriction = _restriction(
        restriction_id=restriction_id,
        target=market_target,
        source_receipt_id=old_receipt,
    )
    restore_target = ExecutiveControlTarget(
        kind=ExecutiveControlTargetKind.RESTRICTION,
        value=str(restriction_id),
    )
    authorized = _authorized(
        ExecutiveControlAction.RESTORE_RESTRICTION,
        target=restore_target,
    )
    expected = _state(
        snapshot_id=UUID("46000000-0000-0000-0000-000000000022"),
        version="state.v8",
        observed_at=_NOW + timedelta(minutes=3),
        market_restrictions=(restriction,),
    )
    next_state = _state(
        snapshot_id=UUID("46000000-0000-0000-0000-000000000023"),
        version="state.v9",
        observed_at=_NOW + timedelta(minutes=4),
    )

    request = ExecutiveGovernanceMutationRequest(
        mutation_id=ExecutiveGovernanceMutationId(
            UUID("46000000-0000-0000-0000-000000000024")
        ),
        authorized=authorized,
        expected_state=expected,
        next_state=next_state,
        source_receipt_id=_SOURCE_RECEIPT,
        requested_at=_NOW + timedelta(minutes=3, seconds=1),
    )

    assert request.next_state.market_restrictions == ()


def test_non_materialized_actions_cannot_fabricate_snapshot_mutations() -> None:
    authorized = _authorized(ExecutiveControlAction.ACKNOWLEDGE_INCIDENT)
    expected = _state(
        snapshot_id=UUID("46000000-0000-0000-0000-000000000030"),
        version="state.v1",
        observed_at=_NOW + timedelta(minutes=2),
    )
    next_state = _state(
        snapshot_id=UUID("46000000-0000-0000-0000-000000000031"),
        version="state.v2",
        observed_at=_NOW + timedelta(minutes=3),
    )

    with pytest.raises(ExecutiveGovernanceMutationValidationError):
        _request(authorized, expected, next_state)


def test_mutation_rejects_same_identity_same_version_and_no_change_pause() -> None:
    authorized = _authorized(ExecutiveControlAction.PAUSE_SYSTEM)
    expected = _state(
        snapshot_id=UUID("46000000-0000-0000-0000-000000000040"),
        version="state.v1",
        observed_at=_NOW + timedelta(minutes=2),
    )
    same_id = _state(
        snapshot_id=expected.snapshot_id.value,
        version="state.v2",
        observed_at=_NOW + timedelta(minutes=3),
        system=ExecutiveSystemRunState.PAUSED,
    )
    same_version = _state(
        snapshot_id=UUID("46000000-0000-0000-0000-000000000041"),
        version="state.v1",
        observed_at=_NOW + timedelta(minutes=3),
        system=ExecutiveSystemRunState.PAUSED,
    )

    with pytest.raises(ExecutiveGovernanceMutationValidationError):
        _request(authorized, expected, same_id)
    with pytest.raises(ExecutiveGovernanceMutationValidationError):
        _request(authorized, expected, same_version)

    paused_expected = _state(
        snapshot_id=UUID("46000000-0000-0000-0000-000000000042"),
        version="state.v4",
        observed_at=_NOW + timedelta(minutes=2),
        system=ExecutiveSystemRunState.PAUSED,
    )
    paused_next = _state(
        snapshot_id=UUID("46000000-0000-0000-0000-000000000043"),
        version="state.v5",
        observed_at=_NOW + timedelta(minutes=3),
        system=ExecutiveSystemRunState.PAUSED,
    )
    with pytest.raises(ExecutiveGovernanceMutationValidationError):
        _request(authorized, paused_expected, paused_next)


def test_receipt_builder_binds_request_chronology_and_applied_state() -> None:
    authorized = _authorized(ExecutiveControlAction.HALT_NEW_TRADING)
    expected = _state(
        snapshot_id=UUID("46000000-0000-0000-0000-000000000050"),
        version="state.v10",
        observed_at=_NOW + timedelta(minutes=2),
    )
    next_state = _state(
        snapshot_id=UUID("46000000-0000-0000-0000-000000000051"),
        version="state.v11",
        observed_at=_NOW + timedelta(minutes=3),
        trading=ExecutiveNewTradingState.HALTED,
    )
    request = _request(authorized, expected, next_state)

    result = build_executive_governance_mutation_receipt(
        request,
        observed_snapshot_id=next_state.snapshot_id,
        observed_state_version=next_state.state_version,
        completed_at=_NOW + timedelta(minutes=4),
        status=ExecutiveGovernanceMutationStatus.APPLIED,
    )

    assert isinstance(result, Success)
    assert result.value.status is ExecutiveGovernanceMutationStatus.APPLIED
    assert result.value.requested_state_version == next_state.state_version

    early = build_executive_governance_mutation_receipt(
        request,
        observed_snapshot_id=next_state.snapshot_id,
        observed_state_version=next_state.state_version,
        completed_at=request.requested_at - timedelta(microseconds=1),
        status=ExecutiveGovernanceMutationStatus.APPLIED,
    )
    assert not isinstance(early, Success)


def test_conflict_receipt_requires_observed_state_to_differ_from_expectation() -> None:
    authorized = _authorized(ExecutiveControlAction.PAUSE_SYSTEM)
    expected = _state(
        snapshot_id=UUID("46000000-0000-0000-0000-000000000060"),
        version="state.v1",
        observed_at=_NOW + timedelta(minutes=2),
    )
    next_state = _state(
        snapshot_id=UUID("46000000-0000-0000-0000-000000000061"),
        version="state.v2",
        observed_at=_NOW + timedelta(minutes=3),
        system=ExecutiveSystemRunState.PAUSED,
    )
    request = _request(authorized, expected, next_state)

    with pytest.raises(ExecutiveGovernanceMutationValidationError):
        ExecutiveGovernanceMutationReceipt(
            mutation_id=request.mutation_id,
            source_receipt_id=request.source_receipt_id,
            expected_snapshot_id=expected.snapshot_id,
            expected_state_version=expected.state_version,
            requested_snapshot_id=next_state.snapshot_id,
            requested_state_version=next_state.state_version,
            observed_snapshot_id=expected.snapshot_id,
            observed_state_version=expected.state_version,
            completed_at=_NOW + timedelta(minutes=4),
            status=ExecutiveGovernanceMutationStatus.CONFLICT,
        )


class _FakeMutationPort:
    def __init__(self, receipt: ExecutiveGovernanceMutationReceipt) -> None:
        self.receipt = receipt
        self.requests: list[ExecutiveGovernanceMutationRequest] = []

    def compare_and_set(
        self,
        request: ExecutiveGovernanceMutationRequest,
    ) -> Result[ExecutiveGovernanceMutationReceipt, ExecutiveGovernanceMutationError]:
        self.requests.append(request)
        return Success(self.receipt)


def _accept_port(port: ExecutiveGovernanceMutationPort) -> ExecutiveGovernanceMutationPort:
    return port


def test_mutation_port_is_structural_and_request_driven() -> None:
    authorized = _authorized(ExecutiveControlAction.PAUSE_SYSTEM)
    expected = _state(
        snapshot_id=UUID("46000000-0000-0000-0000-000000000070"),
        version="state.v1",
        observed_at=_NOW + timedelta(minutes=2),
    )
    next_state = _state(
        snapshot_id=UUID("46000000-0000-0000-0000-000000000071"),
        version="state.v2",
        observed_at=_NOW + timedelta(minutes=3),
        system=ExecutiveSystemRunState.PAUSED,
    )
    request = _request(authorized, expected, next_state)
    receipt_result = build_executive_governance_mutation_receipt(
        request,
        observed_snapshot_id=next_state.snapshot_id,
        observed_state_version=next_state.state_version,
        completed_at=_NOW + timedelta(minutes=4),
        status=ExecutiveGovernanceMutationStatus.APPLIED,
    )
    assert isinstance(receipt_result, Success)
    fake = _FakeMutationPort(receipt_result.value)

    port = _accept_port(fake)
    result = port.compare_and_set(request)

    assert isinstance(result, Success)
    assert result.value is receipt_result.value
    assert fake.requests == [request]
