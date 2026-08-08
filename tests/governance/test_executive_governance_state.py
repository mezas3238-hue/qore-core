from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID

import pytest

from qore.domain.events import CorrelationId
from qore.governance.executive_control import (
    ExecutiveControlTarget,
    ExecutiveControlTargetKind,
)
from qore.governance.executive_governance_state import (
    ExecutiveActiveRestriction,
    ExecutiveGovernancePolicyVersion,
    ExecutiveGovernanceStateError,
    ExecutiveGovernanceStateRequest,
    ExecutiveGovernanceStateRequestId,
    ExecutiveGovernanceStateSnapshot,
    ExecutiveGovernanceStateSnapshotId,
    ExecutiveGovernanceStateSource,
    ExecutiveGovernanceStateValidationError,
    ExecutiveGovernanceStateVersion,
    ExecutiveNewTradingState,
    ExecutiveRestrictionId,
    ExecutiveSystemRunState,
)
from qore.governance.executive_ports import ExecutiveEvidenceRef, ExecutiveReceiptId
from qore.kernel.result import Result, Success

_NOW = datetime(2026, 8, 8, 22, 45, tzinfo=UTC)
_CORRELATION = CorrelationId(UUID("33000000-0000-0000-0000-000000000001"))


def _restriction(
    *,
    restriction_id: str,
    receipt_id: str,
    kind: ExecutiveControlTargetKind,
    target_value: str,
    applied_at: datetime | None = None,
) -> ExecutiveActiveRestriction:
    return ExecutiveActiveRestriction(
        restriction_id=ExecutiveRestrictionId(UUID(restriction_id)),
        target=ExecutiveControlTarget(kind=kind, value=target_value),
        applied_at=_NOW - timedelta(seconds=1) if applied_at is None else applied_at,
        source_receipt_id=ExecutiveReceiptId(UUID(receipt_id)),
        policy_version=ExecutiveGovernancePolicyVersion("governance.v1"),
        reason_codes=("risk.limit",),
        evidence_refs=(ExecutiveEvidenceRef("evidence:governance/restriction-001"),),
    )


def _market_restriction(
    *,
    restriction_id: str = "33000000-0000-0000-0000-000000000010",
    receipt_id: str = "33000000-0000-0000-0000-000000000020",
    target_value: str = "market:eur_usd",
) -> ExecutiveActiveRestriction:
    return _restriction(
        restriction_id=restriction_id,
        receipt_id=receipt_id,
        kind=ExecutiveControlTargetKind.MARKET,
        target_value=target_value,
    )


def _account_restriction(
    *,
    restriction_id: str = "33000000-0000-0000-0000-000000000011",
    receipt_id: str = "33000000-0000-0000-0000-000000000021",
    target_value: str = "proprietary-account:alpha",
) -> ExecutiveActiveRestriction:
    return _restriction(
        restriction_id=restriction_id,
        receipt_id=receipt_id,
        kind=ExecutiveControlTargetKind.ACCOUNT,
        target_value=target_value,
    )


def _snapshot(
    *,
    market_restrictions: tuple[ExecutiveActiveRestriction, ...] = (),
    account_restrictions: tuple[ExecutiveActiveRestriction, ...] = (),
) -> ExecutiveGovernanceStateSnapshot:
    return ExecutiveGovernanceStateSnapshot(
        snapshot_id=ExecutiveGovernanceStateSnapshotId(
            UUID("33000000-0000-0000-0000-000000000030")
        ),
        state_version=ExecutiveGovernanceStateVersion("governance-state.v1"),
        observed_at=_NOW,
        system_run_state=ExecutiveSystemRunState.ACTIVE,
        new_trading_state=ExecutiveNewTradingState.PERMITTED,
        market_restrictions=market_restrictions,
        account_restrictions=account_restrictions,
    )


def test_materialized_state_is_deterministic_and_target_partitioned() -> None:
    later_market = _market_restriction(
        restriction_id="33000000-0000-0000-0000-000000000012",
        receipt_id="33000000-0000-0000-0000-000000000022",
        target_value="market:gbp_usd",
    )
    first_market = _market_restriction()
    account = _account_restriction()

    snapshot = _snapshot(
        market_restrictions=(later_market, first_market),
        account_restrictions=(account,),
    )

    assert snapshot.market_restrictions == (first_market, later_market)
    assert snapshot.account_restrictions == (account,)
    assert snapshot.logical_values() == snapshot.logical_values()


def test_snapshot_rejects_wrong_restriction_partition() -> None:
    with pytest.raises(ExecutiveGovernanceStateValidationError):
        _snapshot(market_restrictions=(_account_restriction(),))

    with pytest.raises(ExecutiveGovernanceStateValidationError):
        _snapshot(account_restrictions=(_market_restriction(),))


def test_snapshot_rejects_duplicate_target_and_global_id_collisions() -> None:
    first = _market_restriction()
    same_target = _market_restriction(
        restriction_id="33000000-0000-0000-0000-000000000013",
        receipt_id="33000000-0000-0000-0000-000000000023",
    )
    with pytest.raises(ExecutiveGovernanceStateValidationError):
        _snapshot(market_restrictions=(first, same_target))

    duplicate_id = _account_restriction(
        restriction_id="33000000-0000-0000-0000-000000000010",
    )
    with pytest.raises(ExecutiveGovernanceStateValidationError):
        _snapshot(
            market_restrictions=(first,),
            account_restrictions=(duplicate_id,),
        )

    duplicate_receipt = _account_restriction(
        receipt_id="33000000-0000-0000-0000-000000000020",
    )
    with pytest.raises(ExecutiveGovernanceStateValidationError):
        _snapshot(
            market_restrictions=(first,),
            account_restrictions=(duplicate_receipt,),
        )


def test_snapshot_rejects_restriction_applied_after_observation() -> None:
    future = _restriction(
        restriction_id="33000000-0000-0000-0000-000000000014",
        receipt_id="33000000-0000-0000-0000-000000000024",
        kind=ExecutiveControlTargetKind.MARKET,
        target_value="market:eur_usd",
        applied_at=_NOW + timedelta(seconds=1),
    )

    with pytest.raises(ExecutiveGovernanceStateValidationError):
        _snapshot(market_restrictions=(future,))


def test_active_restriction_requires_market_or_account_evidence() -> None:
    with pytest.raises(ExecutiveGovernanceStateValidationError):
        _restriction(
            restriction_id="33000000-0000-0000-0000-000000000015",
            receipt_id="33000000-0000-0000-0000-000000000025",
            kind=ExecutiveControlTargetKind.RESTRICTION,
            target_value="restriction:old",
        )

    with pytest.raises(ExecutiveGovernanceStateValidationError):
        ExecutiveActiveRestriction(
            restriction_id=ExecutiveRestrictionId(
                UUID("33000000-0000-0000-0000-000000000016")
            ),
            target=ExecutiveControlTarget(
                kind=ExecutiveControlTargetKind.MARKET,
                value="market:eur_usd",
            ),
            applied_at=_NOW,
            source_receipt_id=ExecutiveReceiptId(
                UUID("33000000-0000-0000-0000-000000000026")
            ),
            policy_version=ExecutiveGovernancePolicyVersion("governance.v1"),
            reason_codes=(),
            evidence_refs=(),
        )


def test_state_contract_supports_explicit_unknown_without_inference() -> None:
    snapshot = ExecutiveGovernanceStateSnapshot(
        snapshot_id=ExecutiveGovernanceStateSnapshotId(
            UUID("33000000-0000-0000-0000-000000000031")
        ),
        state_version=ExecutiveGovernanceStateVersion("governance-state.v1"),
        observed_at=_NOW,
        system_run_state=ExecutiveSystemRunState.UNKNOWN,
        new_trading_state=ExecutiveNewTradingState.UNKNOWN,
        market_restrictions=(),
        account_restrictions=(),
    )

    assert snapshot.system_run_state is ExecutiveSystemRunState.UNKNOWN
    assert snapshot.new_trading_state is ExecutiveNewTradingState.UNKNOWN
    assert not hasattr(snapshot, "receipt_history")
    assert not hasattr(snapshot, "replay_receipts")


def test_governance_state_request_and_source_are_explicit() -> None:
    request = ExecutiveGovernanceStateRequest(
        request_id=ExecutiveGovernanceStateRequestId(
            UUID("33000000-0000-0000-0000-000000000040")
        ),
        requested_at=_NOW,
        correlation_id=_CORRELATION,
    )
    snapshot = _snapshot()

    class _Source:
        def read_current_state(
            self,
            received: ExecutiveGovernanceStateRequest,
        ) -> Result[ExecutiveGovernanceStateSnapshot, ExecutiveGovernanceStateError]:
            assert received == request
            return Success(snapshot)

    def _accept_source(source: ExecutiveGovernanceStateSource) -> None:
        result = source.read_current_state(request)
        assert isinstance(result, Success)
        assert result.value == snapshot

    _accept_source(_Source())


def test_governance_request_requires_timezone_aware_timestamp() -> None:
    with pytest.raises(ExecutiveGovernanceStateValidationError):
        ExecutiveGovernanceStateRequest(
            request_id=ExecutiveGovernanceStateRequestId(
                UUID("33000000-0000-0000-0000-000000000041")
            ),
            requested_at=datetime(2026, 8, 8, 22, 45),
            correlation_id=_CORRELATION,
        )
