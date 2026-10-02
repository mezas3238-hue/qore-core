from datetime import UTC, datetime

import pytest

from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)
from qore.infrastructure.cibo_ce2i_t02_terminal_reason_evidence import (
    T02TerminalReason,
    T02TerminalReasonEvidence,
    T02TerminalReasonSource,
    t02_terminal_reason_from_qore_lifecycle,
)
from qore.infrastructure.client_position_lifecycle import (
    ClientPositionExitReason,
)

T0 = datetime(2026, 9, 30, 21, 45, tzinfo=UTC)


def _evidence(reason: T02TerminalReason) -> T02TerminalReasonEvidence:
    return T02TerminalReasonEvidence(
        evidence_id="terminal-1",
        decision_evidence_sha256="sha256:" + "1" * 64,
        signal_fingerprint="signal-1",
        position_id=1,
        settlement_deal_ids=(10,),
        reason=reason,
        source=T02TerminalReasonSource.PROVIDER_NATIVE_EXPLICIT,
        source_ref="provider-explicit:10",
        observed_at=T0,
    )


def test_only_explicit_structural_stop_counts_as_stop() -> None:
    assert _evidence(T02TerminalReason.STRUCTURAL_STOP).stopped_at_structural_stop
    assert not _evidence(T02TerminalReason.TAKE_PROFIT).stopped_at_structural_stop
    assert not _evidence(T02TerminalReason.PROVIDER_STOP_OUT).stopped_at_structural_stop


def test_qore_lifecycle_stop_loss_maps_to_structural_stop() -> None:
    evidence = t02_terminal_reason_from_qore_lifecycle(
        evidence_id="terminal-qore",
        decision_evidence_sha256="sha256:" + "2" * 64,
        signal_fingerprint="signal-2",
        position_id=2,
        settlement_deal_ids=(20,),
        exit_reason=ClientPositionExitReason.STOP_LOSS,
        lifecycle_evidence_ref="lifecycle:action:20",
        observed_at=T0,
    )

    assert evidence.reason is T02TerminalReason.STRUCTURAL_STOP
    assert evidence.stopped_at_structural_stop is True
    assert evidence.inferred_from_pnl is False
    assert evidence.inferred_from_price is False
    assert evidence.fingerprint().startswith("sha256:")


def test_take_profit_never_maps_to_stop() -> None:
    evidence = t02_terminal_reason_from_qore_lifecycle(
        evidence_id="terminal-tp",
        decision_evidence_sha256="sha256:" + "3" * 64,
        signal_fingerprint="signal-3",
        position_id=3,
        settlement_deal_ids=(30,),
        exit_reason=ClientPositionExitReason.TAKE_PROFIT,
        lifecycle_evidence_ref="lifecycle:action:30",
        observed_at=T0,
    )

    assert evidence.reason is T02TerminalReason.TAKE_PROFIT
    assert evidence.stopped_at_structural_stop is False


def test_pnl_or_price_inference_is_forbidden() -> None:
    with pytest.raises(
        CiboCapitalManagementError,
        match="cannot be inferred",
    ):
        T02TerminalReasonEvidence(
            evidence_id="terminal-invalid",
            decision_evidence_sha256="sha256:" + "4" * 64,
            signal_fingerprint="signal-4",
            position_id=4,
            settlement_deal_ids=(40,),
            reason=T02TerminalReason.STRUCTURAL_STOP,
            source=T02TerminalReasonSource.PROVIDER_NATIVE_EXPLICIT,
            source_ref="inferred",
            observed_at=T0,
            inferred_from_pnl=True,
        )
