"""CMA realized-settlement ledger invariants."""
# ruff: noqa: I001

from decimal import Decimal

import pytest

from qore.infrastructure.cibo_cma_settlement_ledger import (
    CmaSettlementLedgerError,
    CmaSettlementRecord,
    CmaSettlementState,
    apply_settlement,
    settlement_record_from_payload,
)


def _record(
    *,
    deal_id: int,
    pnl: str,
    exit_event: bool = False,
) -> CmaSettlementRecord:
    return CmaSettlementRecord(
        event=(
            "CTRADER_DEMO_EXIT_SETTLEMENT"
            if exit_event
            else "CTRADER_DEMO_PARTIAL_SETTLEMENT"
        ),
        deal_id=deal_id,
        signal_fingerprint="signal-1",
        position_id=101,
        net_profit_usd=Decimal(pnl),
        position_open_after=not exit_event,
    )


def test_partial_and_exit_accumulate_realized_net_pnl_once() -> None:
    state = CmaSettlementState(
        signal_fingerprint="signal-1",
        position_id=101,
    )
    state = apply_settlement(state, _record(deal_id=1, pnl="28.86"))
    state = apply_settlement(
        state,
        _record(deal_id=2, pnl="35.20", exit_event=True),
    )

    assert state.realized_net_pnl_usd == Decimal("64.06")
    assert state.position_closed is True


def test_identical_duplicate_deal_is_idempotent() -> None:
    state = CmaSettlementState(
        signal_fingerprint="signal-1",
        position_id=101,
    )
    record = _record(deal_id=1, pnl="28.86")
    once = apply_settlement(state, record)
    twice = apply_settlement(once, record)

    assert twice == once
    assert twice.realized_net_pnl_usd == Decimal("28.86")


def test_conflicting_duplicate_deal_fails_closed() -> None:
    state = CmaSettlementState(
        signal_fingerprint="signal-1",
        position_id=101,
    )
    state = apply_settlement(state, _record(deal_id=1, pnl="28.86"))

    with pytest.raises(CmaSettlementLedgerError, match="conflicting duplicate"):
        apply_settlement(state, _record(deal_id=1, pnl="99"))


def test_settlement_after_terminal_exit_fails_closed() -> None:
    state = CmaSettlementState(
        signal_fingerprint="signal-1",
        position_id=101,
    )
    state = apply_settlement(
        state,
        _record(deal_id=1, pnl="10", exit_event=True),
    )

    with pytest.raises(CmaSettlementLedgerError, match="after terminal exit"):
        apply_settlement(state, _record(deal_id=2, pnl="5"))


def test_payload_parser_preserves_net_settlement() -> None:
    record = settlement_record_from_payload(
        {
            "event": "CTRADER_DEMO_PARTIAL_SETTLEMENT",
            "signal_fingerprint": "signal-1",
            "position_id": 101,
            "deal_id": 5001,
            "net_profit": "-3.25",
            "position_open_after": True,
        }
    )

    assert record.deal_id == 5001
    assert record.net_profit_usd == Decimal("-3.25")


def test_payload_without_boolean_open_state_fails_closed() -> None:
    with pytest.raises(CmaSettlementLedgerError, match="position_open_after"):
        settlement_record_from_payload(
            {
                "event": "CTRADER_DEMO_PARTIAL_SETTLEMENT",
                "signal_fingerprint": "signal-1",
                "position_id": 101,
                "deal_id": 5001,
                "net_profit": "1",
                "position_open_after": "true",
            }
        )
