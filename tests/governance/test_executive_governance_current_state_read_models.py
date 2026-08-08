from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import cast
from uuid import UUID

import pytest

from qore.governance.executive_control import (
    ExecutiveControlTarget,
    ExecutiveControlTargetKind,
    ExecutiveReadScope,
)
from qore.governance.executive_governance_current_state_read_models import (
    ExecutiveGovernanceCurrentStateSummary,
    ExecutiveGovernanceNewTradingState,
    ExecutiveGovernanceRestrictionTargetKind,
    ExecutiveGovernanceSystemRunState,
    project_executive_governance_current_state,
)
from qore.governance.executive_governance_read_models import ExecutiveGovernanceReadModel
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
from qore.governance.executive_read_models import (
    ExecutiveAttentionLevel,
    ExecutiveProjectionId,
    ExecutiveProjectionMetadata,
    ExecutiveProjectionVersion,
    ExecutiveReadModelValidationError,
    ExecutiveSourceFreshness,
)

_NOW = datetime(2026, 8, 8, 23, 45, tzinfo=UTC)


def _restriction(
    *,
    restriction_id: str,
    receipt_id: str,
    kind: ExecutiveControlTargetKind,
    target_value: str,
) -> ExecutiveActiveRestriction:
    return ExecutiveActiveRestriction(
        restriction_id=ExecutiveRestrictionId(UUID(restriction_id)),
        target=ExecutiveControlTarget(kind=kind, value=target_value),
        applied_at=_NOW - timedelta(seconds=2),
        source_receipt_id=ExecutiveReceiptId(UUID(receipt_id)),
        policy_version=ExecutiveGovernancePolicyVersion("governance.v2"),
        reason_codes=("risk.threshold",),
        evidence_refs=(ExecutiveEvidenceRef("evidence:governance/state-001"),),
    )


def _snapshot(
    *,
    observed_at: datetime = _NOW,
    system_run_state: ExecutiveSystemRunState = ExecutiveSystemRunState.PAUSED,
    new_trading_state: ExecutiveNewTradingState = ExecutiveNewTradingState.HALTED,
) -> ExecutiveGovernanceStateSnapshot:
    return ExecutiveGovernanceStateSnapshot(
        snapshot_id=ExecutiveGovernanceStateSnapshotId(
            UUID("34000000-0000-0000-0000-000000000001")
        ),
        state_version=ExecutiveGovernanceStateVersion("governance-state.v1"),
        observed_at=observed_at,
        system_run_state=system_run_state,
        new_trading_state=new_trading_state,
        market_restrictions=(
            _restriction(
                restriction_id="34000000-0000-0000-0000-000000000010",
                receipt_id="34000000-0000-0000-0000-000000000020",
                kind=ExecutiveControlTargetKind.MARKET,
                target_value="market:eur_usd",
            ),
        ),
        account_restrictions=(
            _restriction(
                restriction_id="34000000-0000-0000-0000-000000000011",
                receipt_id="34000000-0000-0000-0000-000000000021",
                kind=ExecutiveControlTargetKind.ACCOUNT,
                target_value="proprietary-account:alpha",
            ),
        ),
    )


def _metadata(*, projected_at: datetime | None = None) -> ExecutiveProjectionMetadata:
    return ExecutiveProjectionMetadata(
        projection_id=ExecutiveProjectionId(
            UUID("34000000-0000-0000-0000-000000000030")
        ),
        projection_version=ExecutiveProjectionVersion("executive-governance.v2"),
        scope=ExecutiveReadScope.GOVERNANCE,
        source_observed_at=_NOW,
        projected_at=_NOW + timedelta(seconds=1)
        if projected_at is None
        else projected_at,
        freshness=ExecutiveSourceFreshness.FRESH,
        evidence_refs=(ExecutiveEvidenceRef("evidence:governance/projection-001"),),
    )


def test_canonical_snapshot_projects_exact_current_state() -> None:
    projected = project_executive_governance_current_state(_snapshot())

    assert isinstance(projected, ExecutiveGovernanceCurrentStateSummary)
    assert projected.system_run_state is ExecutiveGovernanceSystemRunState.PAUSED
    assert projected.new_trading_state is ExecutiveGovernanceNewTradingState.HALTED
    assert len(projected.active_market_restrictions) == 1
    assert len(projected.active_account_restrictions) == 1
    market = projected.active_market_restrictions[0]
    account = projected.active_account_restrictions[0]
    assert market.target_kind is ExecutiveGovernanceRestrictionTargetKind.MARKET
    assert market.target_ref.value == "market:eur_usd"
    assert account.target_kind is ExecutiveGovernanceRestrictionTargetKind.ACCOUNT
    assert account.target_ref.value == "proprietary-account:alpha"
    assert projected.logical_values() == projected.logical_values()


def test_current_state_projection_uses_projection_types_not_internal_objects() -> None:
    source = _snapshot()
    projected = project_executive_governance_current_state(source)

    assert isinstance(projected, ExecutiveGovernanceCurrentStateSummary)
    assert isinstance(
        projected.active_market_restrictions[0].target_kind,
        ExecutiveGovernanceRestrictionTargetKind,
    )
    assert not hasattr(projected, "read_current_state")
    assert not hasattr(projected, "receipt_history")
    assert not hasattr(projected, "replay_receipts")
    assert not hasattr(projected.active_market_restrictions[0], "target")


def test_unknown_states_are_projected_without_inference() -> None:
    projected = project_executive_governance_current_state(
        _snapshot(
            system_run_state=ExecutiveSystemRunState.UNKNOWN,
            new_trading_state=ExecutiveNewTradingState.UNKNOWN,
        )
    )

    assert projected.system_run_state is ExecutiveGovernanceSystemRunState.UNKNOWN
    assert projected.new_trading_state is ExecutiveGovernanceNewTradingState.UNKNOWN


def test_governance_read_model_accepts_explicit_current_state() -> None:
    current_state = project_executive_governance_current_state(_snapshot())

    model = ExecutiveGovernanceReadModel(
        metadata=_metadata(),
        attention=ExecutiveAttentionLevel.IMPORTANT,
        authorities=(),
        control_receipts=(),
        current_state=current_state,
    )

    assert model.current_state == current_state
    assert model.logical_values()[-1] == current_state.logical_values()


def test_governance_read_model_does_not_fabricate_missing_current_state() -> None:
    model = ExecutiveGovernanceReadModel(
        metadata=_metadata(),
        attention=ExecutiveAttentionLevel.INFORMATION,
        authorities=(),
        control_receipts=(),
    )

    assert model.current_state is None
    assert not hasattr(model, "system_paused")
    assert not hasattr(model, "new_trading_halted")


def test_governance_read_model_rejects_state_observed_after_projection() -> None:
    future_state = project_executive_governance_current_state(
        _snapshot(observed_at=_NOW + timedelta(seconds=2))
    )

    with pytest.raises(ExecutiveReadModelValidationError):
        ExecutiveGovernanceReadModel(
            metadata=_metadata(projected_at=_NOW + timedelta(seconds=1)),
            attention=ExecutiveAttentionLevel.ATTENTION,
            authorities=(),
            control_receipts=(),
            current_state=future_state,
        )


def test_projection_rejects_noncanonical_snapshot_input() -> None:
    invalid_snapshot = cast(ExecutiveGovernanceStateSnapshot, object())

    with pytest.raises(ExecutiveReadModelValidationError):
        project_executive_governance_current_state(invalid_snapshot)
