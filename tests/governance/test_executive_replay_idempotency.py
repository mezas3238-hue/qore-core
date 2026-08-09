from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime, timedelta
from typing import cast
from uuid import UUID

import pytest

from qore.domain.events import CorrelationId
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
from qore.governance.executive_governance_mutation import (
    ExecutiveGovernanceMutationId,
    ExecutiveGovernanceMutationRequest,
)
from qore.governance.executive_governance_state import (
    ExecutiveGovernanceStateSnapshot,
    ExecutiveGovernanceStateSnapshotId,
    ExecutiveGovernanceStateVersion,
    ExecutiveNewTradingState,
    ExecutiveSystemRunState,
)
from qore.governance.executive_ports import ExecutiveReceiptId
from qore.governance.executive_replay_idempotency import (
    ExecutiveReplayBlockReason,
    ExecutiveReplayBlockedError,
    ExecutiveReplayClaimPort,
    ExecutiveReplayClaimReceipt,
    ExecutiveReplayClaimRequest,
    ExecutiveReplayClaimStatus,
    ExecutiveReplayFingerprint,
    ExecutiveReplayKey,
    ExecutiveReplayOperation,
    ExecutiveReplayProtectionError,
    ExecutiveReplayProtectionUnavailableError,
    ExecutiveReplayProtectionValidationError,
    ExecutiveReplayProtector,
    build_executive_control_replay_claim,
    build_executive_mutation_replay_claim,
    build_executive_replay_claim_receipt,
)
from qore.kernel.result import Failure, Result, Success

_NOW = datetime(2026, 8, 9, 6, 0, tzinfo=UTC)
_PRINCIPAL = ExecutivePrincipalId("ceo.primary")
_CORRELATION = CorrelationId(UUID("48000000-0000-0000-0000-000000000001"))


def _authorized() -> AuthorizedExecutiveControlIntent:
    grant = ExecutiveAuthorityGrant(
        grant_id=ExecutiveGrantId(UUID("48000000-0000-0000-0000-000000000002")),
        principal_id=_PRINCIPAL,
        authority_version=ExecutiveAuthorityVersion("authority.v3"),
        allowed_actions=(ExecutiveControlAction.PAUSE_SYSTEM,),
        allowed_read_scopes=(ExecutiveReadScope.GOVERNANCE,),
        issued_at=_NOW,
        expires_at=_NOW + timedelta(minutes=30),
        reason="mission04 replay protection",
    )
    intent = ExecutiveControlIntent(
        intent_id=ExecutiveIntentId(UUID("48000000-0000-0000-0000-000000000003")),
        principal_id=_PRINCIPAL,
        action=ExecutiveControlAction.PAUSE_SYSTEM,
        requested_at=_NOW + timedelta(minutes=1),
        correlation_id=_CORRELATION,
        reason="CEO governed pause",
    )
    return AuthorizedExecutiveControlIntent(
        intent=intent,
        grant=grant,
        authorized_at=_NOW + timedelta(minutes=2),
    )


def _state(snapshot: str, version: str, *, paused: bool) -> ExecutiveGovernanceStateSnapshot:
    return ExecutiveGovernanceStateSnapshot(
        snapshot_id=ExecutiveGovernanceStateSnapshotId(UUID(snapshot)),
        state_version=ExecutiveGovernanceStateVersion(version),
        observed_at=_NOW + timedelta(minutes=3 if paused else 2),
        system_run_state=(
            ExecutiveSystemRunState.PAUSED if paused else ExecutiveSystemRunState.ACTIVE
        ),
        new_trading_state=ExecutiveNewTradingState.PERMITTED,
        market_restrictions=(),
        account_restrictions=(),
    )


def _mutation() -> ExecutiveGovernanceMutationRequest:
    return ExecutiveGovernanceMutationRequest(
        mutation_id=ExecutiveGovernanceMutationId(
            UUID("48000000-0000-0000-0000-000000000004")
        ),
        authorized=_authorized(),
        expected_state=_state(
            "48000000-0000-0000-0000-000000000005",
            "state.v1",
            paused=False,
        ),
        next_state=_state(
            "48000000-0000-0000-0000-000000000006",
            "state.v2",
            paused=True,
        ),
        source_receipt_id=ExecutiveReceiptId(
            UUID("48000000-0000-0000-0000-000000000007")
        ),
        requested_at=_NOW + timedelta(minutes=2, seconds=1),
    )


def _claim() -> ExecutiveReplayClaimRequest:
    result = build_executive_control_replay_claim(
        _authorized(),
        requested_at=_NOW + timedelta(minutes=2, seconds=1),
    )
    assert isinstance(result, Success)
    return result.value


def _receipt(
    request: ExecutiveReplayClaimRequest,
    status: ExecutiveReplayClaimStatus,
    *,
    observed: ExecutiveReplayFingerprint | None = None,
) -> ExecutiveReplayClaimReceipt:
    observed_fingerprint = observed or request.fingerprint
    result = build_executive_replay_claim_receipt(
        request,
        observed_fingerprint=observed_fingerprint,
        completed_at=request.requested_at + timedelta(seconds=1),
        status=status,
    )
    assert isinstance(result, Success)
    return result.value


class _FakeClaimPort:
    def __init__(
        self,
        *,
        receipt: ExecutiveReplayClaimReceipt | None = None,
        error: ExecutiveReplayProtectionError | None = None,
    ) -> None:
        self.receipt = receipt
        self.error = error
        self.requests: list[ExecutiveReplayClaimRequest] = []

    def claim(
        self,
        request: ExecutiveReplayClaimRequest,
    ) -> Result[ExecutiveReplayClaimReceipt, ExecutiveReplayProtectionError]:
        self.requests.append(request)
        if self.error is not None:
            return Failure(self.error)
        if self.receipt is None:
            return Failure(ExecutiveReplayProtectionUnavailableError("claim unavailable"))
        return Success(self.receipt)


def _blocked_reason(result: object) -> ExecutiveReplayBlockReason:
    assert isinstance(result, Failure)
    assert isinstance(result.error, ExecutiveReplayBlockedError)
    return result.error.reason


def test_control_claim_is_bound_to_safe_authorized_identity() -> None:
    authorized = _authorized()
    result = build_executive_control_replay_claim(
        authorized,
        requested_at=_NOW + timedelta(minutes=2, seconds=1),
    )

    assert isinstance(result, Success)
    claim = result.value
    assert claim.key == ExecutiveReplayKey(
        ExecutiveReplayOperation.CONTROL_DISPATCH,
        authorized.intent.intent_id.value,
    )
    assert claim.principal_id == authorized.intent.principal_id
    assert claim.authority_version == authorized.grant.authority_version
    assert claim.correlation_id == authorized.intent.correlation_id
    rendered = repr(claim.logical_values()).lower()
    assert "password" not in rendered
    assert "token" not in rendered
    assert authorized.intent.reason not in rendered
    assert authorized.grant.reason not in rendered


def test_control_claim_rejects_invalid_chronology_and_secret_fingerprint() -> None:
    early = build_executive_control_replay_claim(
        _authorized(),
        requested_at=_NOW + timedelta(minutes=1),
    )
    assert isinstance(early, Failure)

    with pytest.raises(ExecutiveReplayProtectionValidationError):
        ExecutiveReplayFingerprint(("token:private",))
    with pytest.raises(ExecutiveReplayProtectionValidationError):
        ExecutiveReplayKey(
            ExecutiveReplayOperation.CONTROL_DISPATCH,
            cast(UUID, "not-uuid"),
        )


def test_mutation_claim_prevents_reuse_of_mutation_identity_with_changed_state() -> None:
    request = _mutation()
    first = build_executive_mutation_replay_claim(
        request,
        requested_at=_NOW + timedelta(minutes=3),
    )
    changed = replace(
        request,
        next_state=_state(
            "48000000-0000-0000-0000-000000000008",
            "state.v9",
            paused=True,
        ),
    )
    second = build_executive_mutation_replay_claim(
        changed,
        requested_at=_NOW + timedelta(minutes=3),
    )

    assert isinstance(first, Success)
    assert isinstance(second, Success)
    assert first.value.key == second.value.key
    assert first.value.fingerprint != second.value.fingerprint
    values = first.value.fingerprint.logical_values()
    assert any(item.startswith("source-receipt:") for item in values)
    assert any(item.startswith("expected-snapshot:") for item in values)
    assert any(item.startswith("requested-snapshot:") for item in values)


def test_claim_receipt_requires_consistent_status_semantics() -> None:
    request = _claim()
    different = ExecutiveReplayFingerprint(("intent:other",))

    duplicate = build_executive_replay_claim_receipt(
        request,
        observed_fingerprint=request.fingerprint,
        completed_at=request.requested_at + timedelta(seconds=1),
        status=ExecutiveReplayClaimStatus.DUPLICATE,
    )
    conflict = build_executive_replay_claim_receipt(
        request,
        observed_fingerprint=different,
        completed_at=request.requested_at + timedelta(seconds=1),
        status=ExecutiveReplayClaimStatus.CONFLICT,
    )
    invalid_conflict = build_executive_replay_claim_receipt(
        request,
        observed_fingerprint=request.fingerprint,
        completed_at=request.requested_at + timedelta(seconds=1),
        status=ExecutiveReplayClaimStatus.CONFLICT,
    )

    assert isinstance(duplicate, Success)
    assert isinstance(conflict, Success)
    assert isinstance(invalid_conflict, Failure)


def test_protector_allows_only_newly_acquired_claim_and_calls_port_once() -> None:
    request = _claim()
    receipt = _receipt(request, ExecutiveReplayClaimStatus.ACQUIRED)
    port = _FakeClaimPort(receipt=receipt)

    result = ExecutiveReplayProtector(port).protect(request)

    assert isinstance(result, Success)
    assert result.value is receipt
    assert port.requests == [request]


@pytest.mark.parametrize(
    ("status", "reason"),
    [
        (ExecutiveReplayClaimStatus.DUPLICATE, ExecutiveReplayBlockReason.DUPLICATE),
        (ExecutiveReplayClaimStatus.CONFLICT, ExecutiveReplayBlockReason.CONFLICT),
    ],
)
def test_duplicate_or_conflicting_claim_fails_closed_without_second_call(
    status: ExecutiveReplayClaimStatus,
    reason: ExecutiveReplayBlockReason,
) -> None:
    request = _claim()
    observed = (
        request.fingerprint
        if status is ExecutiveReplayClaimStatus.DUPLICATE
        else ExecutiveReplayFingerprint(("intent:conflict",))
    )
    port = _FakeClaimPort(receipt=_receipt(request, status, observed=observed))

    result = ExecutiveReplayProtector(port).protect(request)

    assert _blocked_reason(result) is reason
    assert len(port.requests) == 1


def test_claim_boundary_failure_is_sanitized_and_never_retried() -> None:
    request = _claim()
    port = _FakeClaimPort(
        error=ExecutiveReplayProtectionUnavailableError(
            "database password=private bearer token"
        )
    )

    result = ExecutiveReplayProtector(port).protect(request)

    assert _blocked_reason(result) is ExecutiveReplayBlockReason.CLAIM_BOUNDARY_FAILED
    assert len(port.requests) == 1
    assert isinstance(result, Failure)
    assert "password" not in str(result.error).lower()
    assert "token" not in str(result.error).lower()


def test_mismatched_claim_receipt_fails_closed() -> None:
    request = _claim()
    valid = _receipt(request, ExecutiveReplayClaimStatus.ACQUIRED)
    mismatched = replace(valid, correlation_id=CorrelationId(UUID(int=99)))
    port = _FakeClaimPort(receipt=mismatched)

    result = ExecutiveReplayProtector(port).protect(request)

    assert _blocked_reason(result) is ExecutiveReplayBlockReason.CLAIM_RECEIPT_MISMATCH
    assert len(port.requests) == 1


def test_claim_port_is_structural() -> None:
    request = _claim()
    port: ExecutiveReplayClaimPort = _FakeClaimPort(
        receipt=_receipt(request, ExecutiveReplayClaimStatus.ACQUIRED)
    )

    result = port.claim(request)

    assert isinstance(result, Success)
