from dataclasses import replace
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from uuid import UUID

import pytest

from qore.infrastructure.cibo_arch2_t02_lifecycle_intake import (
    build_t02_lifecycle_terminal_intake,
)
from qore.infrastructure.cibo_arch2_t02_provider_position_binding import (
    BINDING_ID,
    SOURCE_KIND,
    T02ProviderPositionBindingReceipt,
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
CLIENT_POSITION_ID = UUID("11111111-1111-4111-8111-111111111111")
ENTRY_RECEIPT_ID = UUID("22222222-2222-4222-8222-222222222222")
EXIT_RECEIPT_ID = UUID("33333333-3333-4333-8333-333333333333")
ACTION_ID = UUID("44444444-4444-4444-8444-444444444444")
EVIDENCE_ID = UUID("55555555-5555-4555-8555-555555555555")


def _sha(char: str) -> str:
    return "sha256:" + char * 64


def _binding() -> T02ProviderPositionBindingReceipt:
    return T02ProviderPositionBindingReceipt(
        binding_id=BINDING_ID,
        source_kind=SOURCE_KIND,
        source_evidence_sha256=_sha("a"),
        decision_evidence_sha256=_sha("1"),
        signal_fingerprint="signal-001",
        client_position_id=str(CLIENT_POSITION_ID),
        entry_execution_receipt_id=str(ENTRY_RECEIPT_ID),
        exit_execution_receipt_id=str(EXIT_RECEIPT_ID),
        provider_position_id=7001,
        execution_risk_evidence_id="risk-7001",
        executed_risk_sha256=_sha("5"),
        settlement_sha256=_sha("6"),
        settlement_deal_ids=(8001, 8002),
        canonical_ledger_modified=False,
        productive_authority=False,
    )


def _lifecycle(
    *,
    state: ClientPositionState = ClientPositionState.CLOSED,
    exit_reason: ClientPositionExitReason | None = ClientPositionExitReason.STOP_LOSS,
    client_position_id: UUID = CLIENT_POSITION_ID,
    entry_receipt_id: UUID = ENTRY_RECEIPT_ID,
    exit_receipt_id: UUID = EXIT_RECEIPT_ID,
) -> ClientPositionLifecycle:
    lifecycle = object.__new__(ClientPositionLifecycle)
    object.__setattr__(lifecycle, "state", state)
    object.__setattr__(lifecycle, "closed_at", T0)
    object.__setattr__(
        lifecycle,
        "position_id",
        SimpleNamespace(value=client_position_id),
    )
    opening = SimpleNamespace(
        kind=ClientPositionActionKind.OPEN,
        execution_receipt_id=SimpleNamespace(value=entry_receipt_id),
    )
    terminal = SimpleNamespace(
        kind=ClientPositionActionKind.EXIT,
        exit_reason=exit_reason,
        occurred_at=T0,
        evidence_ref=SimpleNamespace(value=EVIDENCE_ID),
        action_id=SimpleNamespace(value=ACTION_ID),
        execution_receipt_id=SimpleNamespace(value=exit_receipt_id),
    )
    object.__setattr__(lifecycle, "actions", (opening, terminal))
    return lifecycle


def test_t02_lifecycle_intake_preserves_explicit_stop_reason() -> None:
    binding = _binding()
    result = build_t02_lifecycle_terminal_intake(
        binding=binding,
        lifecycle=_lifecycle(),
        observed_at=T0 + timedelta(seconds=1),
    )

    assert result.lifecycle_evidence.reason is T02TerminalReason.STRUCTURAL_STOP
    assert result.lifecycle_evidence.position_id == 7001
    assert result.lifecycle_evidence.settlement_deal_ids == (8001, 8002)
    assert result.provider_position_binding_sha256 == binding.fingerprint()
    assert result.execution_risk_evidence_id == "risk-7001"
    assert result.executed_risk_sha256 == _sha("5")
    assert result.settlement_sha256 == _sha("6")
    assert result.lifecycle_evidence.inferred_from_pnl is False
    assert result.lifecycle_evidence.inferred_from_price is False
    assert result.productive_authority is False


def test_t02_lifecycle_intake_rejects_open_lifecycle() -> None:
    with pytest.raises(
        CiboCapitalManagementError,
        match="CLOSED lifecycle",
    ):
        build_t02_lifecycle_terminal_intake(
            binding=_binding(),
            lifecycle=_lifecycle(state=ClientPositionState.OPEN),
            observed_at=T0 + timedelta(seconds=1),
        )


def test_t02_lifecycle_intake_rejects_missing_explicit_reason() -> None:
    with pytest.raises(
        CiboCapitalManagementError,
        match="EXIT reason missing",
    ):
        build_t02_lifecycle_terminal_intake(
            binding=_binding(),
            lifecycle=_lifecycle(exit_reason=None),
            observed_at=T0 + timedelta(seconds=1),
        )


def test_t02_lifecycle_intake_rejects_client_position_drift() -> None:
    bad = replace(
        _binding(),
        client_position_id="66666666-6666-4666-8666-666666666666",
    )
    with pytest.raises(
        CiboCapitalManagementError,
        match="client/provider binding position drift",
    ):
        build_t02_lifecycle_terminal_intake(
            binding=bad,
            lifecycle=_lifecycle(),
            observed_at=T0 + timedelta(seconds=1),
        )


def test_t02_lifecycle_intake_rejects_execution_receipt_drift() -> None:
    bad = replace(
        _binding(),
        exit_execution_receipt_id="77777777-7777-4777-8777-777777777777",
    )
    with pytest.raises(
        CiboCapitalManagementError,
        match="exit execution receipt drift",
    ):
        build_t02_lifecycle_terminal_intake(
            binding=bad,
            lifecycle=_lifecycle(),
            observed_at=T0 + timedelta(seconds=1),
        )
