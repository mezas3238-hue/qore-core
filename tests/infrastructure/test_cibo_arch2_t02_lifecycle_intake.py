from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from uuid import uuid4

import pytest

from qore.infrastructure.cibo_arch2_t02_lifecycle_intake import (
    build_t02_lifecycle_terminal_intake,
)
from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)
from qore.infrastructure.cibo_ce2i_t02_terminal_reason_evidence import (
    T02TerminalReason,
)
from qore.infrastructure.client_position_lifecycle import (
    ClientPositionActionKind,
    ClientPositionExitReason,
    ClientPositionLifecycle,
    ClientPositionState,
)

T0 = datetime(2026, 10, 2, 0, 0, tzinfo=UTC)


def _lifecycle(
    *,
    state: ClientPositionState = ClientPositionState.CLOSED,
    exit_reason: ClientPositionExitReason | None = ClientPositionExitReason.STOP_LOSS,
) -> ClientPositionLifecycle:
    lifecycle = object.__new__(ClientPositionLifecycle)
    object.__setattr__(lifecycle, "state", state)
    object.__setattr__(lifecycle, "closed_at", T0)
    object.__setattr__(
        lifecycle,
        "position_id",
        SimpleNamespace(value=uuid4()),
    )
    terminal = SimpleNamespace(
        kind=ClientPositionActionKind.EXIT,
        exit_reason=exit_reason,
        occurred_at=T0,
        evidence_ref=SimpleNamespace(value=uuid4()),
        action_id=SimpleNamespace(value=uuid4()),
    )
    object.__setattr__(lifecycle, "actions", (terminal,))
    return lifecycle


def test_t02_lifecycle_intake_preserves_explicit_stop_reason() -> None:
    result = build_t02_lifecycle_terminal_intake(
        decision_evidence_sha256="sha256:" + "1" * 64,
        signal_fingerprint="signal-001",
        provider_position_id=7001,
        settlement_deal_ids=(8001, 8002),
        lifecycle=_lifecycle(),
        provider_position_binding_ref="binding:7001:verified",
        provider_position_binding_verified=True,
        observed_at=T0 + timedelta(seconds=1),
    )

    assert result.lifecycle_evidence.reason is T02TerminalReason.STRUCTURAL_STOP
    assert result.lifecycle_evidence.position_id == 7001
    assert result.lifecycle_evidence.settlement_deal_ids == (8001, 8002)
    assert result.lifecycle_evidence.inferred_from_pnl is False
    assert result.lifecycle_evidence.inferred_from_price is False
    assert result.provider_position_binding_verified is True
    assert result.productive_authority is False


def test_t02_lifecycle_intake_rejects_open_lifecycle() -> None:
    with pytest.raises(
        CiboCapitalManagementError,
        match="CLOSED lifecycle",
    ):
        build_t02_lifecycle_terminal_intake(
            decision_evidence_sha256="sha256:" + "1" * 64,
            signal_fingerprint="signal-001",
            provider_position_id=7001,
            settlement_deal_ids=(8001,),
            lifecycle=_lifecycle(state=ClientPositionState.OPEN),
            provider_position_binding_ref="binding:7001:verified",
            provider_position_binding_verified=True,
            observed_at=T0 + timedelta(seconds=1),
        )


def test_t02_lifecycle_intake_rejects_missing_explicit_reason() -> None:
    with pytest.raises(
        CiboCapitalManagementError,
        match="EXIT reason missing",
    ):
        build_t02_lifecycle_terminal_intake(
            decision_evidence_sha256="sha256:" + "1" * 64,
            signal_fingerprint="signal-001",
            provider_position_id=7001,
            settlement_deal_ids=(8001,),
            lifecycle=_lifecycle(exit_reason=None),
            provider_position_binding_ref="binding:7001:verified",
            provider_position_binding_verified=True,
            observed_at=T0 + timedelta(seconds=1),
        )


def test_t02_lifecycle_intake_rejects_unverified_provider_binding() -> None:
    with pytest.raises(
        CiboCapitalManagementError,
        match="verified provider position binding",
    ):
        build_t02_lifecycle_terminal_intake(
            decision_evidence_sha256="sha256:" + "1" * 64,
            signal_fingerprint="signal-001",
            provider_position_id=7001,
            settlement_deal_ids=(8001,),
            lifecycle=_lifecycle(),
            provider_position_binding_ref="binding:7001",
            provider_position_binding_verified=False,
            observed_at=T0 + timedelta(seconds=1),
        )
