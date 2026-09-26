"""Idempotent realized-settlement accumulator for CIBO CMA."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation


class CmaSettlementLedgerError(ValueError):
    """Settlement evidence is invalid, conflicting, or out of lifecycle order."""


@dataclass(frozen=True, slots=True)
class CmaSettlementRecord:
    event: str
    deal_id: int
    signal_fingerprint: str
    position_id: int
    net_profit_usd: Decimal
    position_open_after: bool

    def __post_init__(self) -> None:
        if self.event not in {
            "CTRADER_DEMO_PARTIAL_SETTLEMENT",
            "CTRADER_DEMO_EXIT_SETTLEMENT",
        }:
            raise CmaSettlementLedgerError("unsupported settlement event")
        for name in ("deal_id", "position_id"):
            value = getattr(self, name)
            if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
                raise CmaSettlementLedgerError(f"{name} must be positive int")
        if not self.signal_fingerprint:
            raise CmaSettlementLedgerError("signal_fingerprint is required")
        if (
            not isinstance(self.net_profit_usd, Decimal)
            or not self.net_profit_usd.is_finite()
        ):
            raise CmaSettlementLedgerError("net_profit_usd must be finite Decimal")
        if type(self.position_open_after) is not bool:
            raise CmaSettlementLedgerError("position_open_after must be bool")
        if self.event == "CTRADER_DEMO_EXIT_SETTLEMENT" and self.position_open_after:
            raise CmaSettlementLedgerError(
                "exit settlement cannot leave position open"
            )


@dataclass(frozen=True, slots=True)
class CmaSettlementState:
    signal_fingerprint: str
    position_id: int
    records: tuple[CmaSettlementRecord, ...] = ()
    position_closed: bool = False

    def __post_init__(self) -> None:
        if not self.signal_fingerprint:
            raise CmaSettlementLedgerError("signal_fingerprint is required")
        if (
            not isinstance(self.position_id, int)
            or isinstance(self.position_id, bool)
            or self.position_id <= 0
        ):
            raise CmaSettlementLedgerError("position_id must be positive int")
        ids = tuple(record.deal_id for record in self.records)
        if len(ids) != len(set(ids)):
            raise CmaSettlementLedgerError("duplicate deal_id in settlement state")
        if any(record.signal_fingerprint != self.signal_fingerprint for record in self.records):
            raise CmaSettlementLedgerError("settlement signal identity mismatch")
        if any(record.position_id != self.position_id for record in self.records):
            raise CmaSettlementLedgerError("settlement position identity mismatch")
        if self.position_closed and (
            not self.records
            or self.records[-1].event != "CTRADER_DEMO_EXIT_SETTLEMENT"
        ):
            raise CmaSettlementLedgerError(
                "closed settlement state requires terminal exit record"
            )

    @property
    def realized_net_pnl_usd(self) -> Decimal:
        return sum(
            (record.net_profit_usd for record in self.records),
            Decimal(0),
        )


def apply_settlement(
    state: CmaSettlementState,
    record: CmaSettlementRecord,
) -> CmaSettlementState:
    """Apply one settlement exactly once; conflicting duplicates fail closed."""

    if not isinstance(state, CmaSettlementState):
        raise CmaSettlementLedgerError("state must be CmaSettlementState")
    if not isinstance(record, CmaSettlementRecord):
        raise CmaSettlementLedgerError("record must be CmaSettlementRecord")
    if record.signal_fingerprint != state.signal_fingerprint:
        raise CmaSettlementLedgerError("settlement signal identity mismatch")
    if record.position_id != state.position_id:
        raise CmaSettlementLedgerError("settlement position identity mismatch")

    existing = next(
        (item for item in state.records if item.deal_id == record.deal_id),
        None,
    )
    if existing is not None:
        if existing == record:
            return state
        raise CmaSettlementLedgerError("conflicting duplicate settlement deal")

    if state.position_closed:
        raise CmaSettlementLedgerError(
            "settlement received after terminal exit"
        )

    records = state.records + (record,)
    return CmaSettlementState(
        signal_fingerprint=state.signal_fingerprint,
        position_id=state.position_id,
        records=records,
        position_closed=record.event == "CTRADER_DEMO_EXIT_SETTLEMENT",
    )


def settlement_record_from_payload(
    payload: Mapping[str, object],
) -> CmaSettlementRecord:
    """Parse one Behavior Lab settlement payload into CMA evidence."""

    if not isinstance(payload, Mapping):
        raise CmaSettlementLedgerError("settlement payload must be mapping")
    event = str(payload.get("event", ""))
    signal = str(payload.get("signal_fingerprint", ""))
    raw_deal_id = payload.get("deal_id")
    raw_position_id = payload.get("position_id")
    if (
        not isinstance(raw_deal_id, (int, str))
        or isinstance(raw_deal_id, bool)
        or not isinstance(raw_position_id, (int, str))
        or isinstance(raw_position_id, bool)
    ):
        raise CmaSettlementLedgerError("settlement ids must be int/string")
    try:
        deal_id = int(raw_deal_id)
        position_id = int(raw_position_id)
        net_profit = Decimal(str(payload["net_profit"]))
    except (KeyError, ValueError, InvalidOperation) as error:
        raise CmaSettlementLedgerError("settlement payload fields invalid") from error
    open_after = payload.get("position_open_after")
    if type(open_after) is not bool:
        raise CmaSettlementLedgerError(
            "settlement position_open_after must be bool"
        )
    return CmaSettlementRecord(
        event=event,
        deal_id=deal_id,
        signal_fingerprint=signal,
        position_id=position_id,
        net_profit_usd=net_profit,
        position_open_after=open_after,
    )
