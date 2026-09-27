"""Restart-safe cTrader DEMO settlement ingestion for CIBO/Phase20.

The observer reads broker closing deals, maps them to durable QORE registry
entries and appends canonical CMA settlement records.  It is read-only at the
broker boundary and uses a durable cursor with overlap so restart cannot create
missing terminal economics.

When several unobserved closing deals for one position are recovered together,
all but the last are partial settlements.  The last is terminal only when the
broker position is no longer open.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from threading import RLock
from typing import Protocol

from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)
from qore.infrastructure.cibo_cma_settlement_ledger import CmaSettlementRecord
from qore.infrastructure.cibo_cma_settlement_store import (
    DurableCmaSettlementStore,
)
from qore.infrastructure.ctrader_demo_free_position_service import (
    DemoDeal,
    DemoPosition,
)
from qore.infrastructure.ctrader_demo_trade_registry import (
    CTraderDemoTradeRegistry,
)

_SCHEMA = "CIBO_PHASE20D_DEMO_SETTLEMENT_CURSOR_V1"
_OVERLAP = timedelta(minutes=15)
_MAX_ROWS = 1000


class Phase20DemoSettlementSource(Protocol):
    def positions(self) -> tuple[DemoPosition, ...]: ...

    def deals(
        self,
        *,
        opened_at: datetime,
        closed_at: datetime,
        max_rows: int = 1000,
    ) -> tuple[DemoDeal, ...]: ...


@dataclass(frozen=True, slots=True)
class Phase20DemoSettlementCursor:
    cursor_at: datetime

    def __post_init__(self) -> None:
        _aware(self.cursor_at, name="cursor_at")


@dataclass(frozen=True, slots=True)
class Phase20DemoSettlementObservation:
    cursor_at: datetime
    open_position_ids: tuple[int, ...]
    applied_deal_ids: tuple[int, ...]
    entry_cost_deal_ids: tuple[int, ...]
    partial_deal_ids: tuple[int, ...]
    terminal_deal_ids: tuple[int, ...]

    def __post_init__(self) -> None:
        _aware(self.cursor_at, name="cursor_at")
        if (
            len(self.open_position_ids) != len(set(self.open_position_ids))
            or any(item <= 0 for item in self.open_position_ids)
        ):
            raise CiboCapitalManagementError(
                "Phase20D settlement open position ids must be unique positive"
            )
        combined = (
            self.entry_cost_deal_ids
            + self.partial_deal_ids
            + self.terminal_deal_ids
        )
        if self.applied_deal_ids != combined:
            raise CiboCapitalManagementError(
                "Phase20D settlement applied deal summary drift"
            )
        if len(combined) != len(set(combined)):
            raise CiboCapitalManagementError(
                "Phase20D settlement deals must be unique"
            )


class DurablePhase20DemoSettlementCursorStore:
    def __init__(self, path: Path) -> None:
        if not isinstance(path, Path):
            raise CiboCapitalManagementError(
                "Phase20D settlement cursor path must be pathlib.Path"
            )
        self._path = path
        self._lock = RLock()

    def load(self, *, initial_cursor: datetime) -> Phase20DemoSettlementCursor:
        _aware(initial_cursor, name="initial_cursor")
        with self._lock:
            if not self._path.exists():
                return Phase20DemoSettlementCursor(cursor_at=initial_cursor)
            try:
                raw = json.loads(self._path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError) as error:
                raise CiboCapitalManagementError(
                    "Phase20D settlement cursor is unreadable"
                ) from error
            if not isinstance(raw, dict) or raw.get("schema") != _SCHEMA:
                raise CiboCapitalManagementError(
                    "Phase20D settlement cursor schema mismatch"
                )
            try:
                cursor = datetime.fromisoformat(str(raw["cursor_at"]))
            except (KeyError, ValueError, TypeError) as error:
                raise CiboCapitalManagementError(
                    "Phase20D settlement cursor payload invalid"
                ) from error
            _aware(cursor, name="stored cursor_at")
            if cursor < initial_cursor:
                cursor = initial_cursor
            return Phase20DemoSettlementCursor(cursor_at=cursor)

    def store(self, cursor: Phase20DemoSettlementCursor) -> None:
        if not isinstance(cursor, Phase20DemoSettlementCursor):
            raise CiboCapitalManagementError(
                "Phase20D settlement cursor must be canonical"
            )
        payload = {
            "schema": _SCHEMA,
            "cursor_at": cursor.cursor_at.isoformat(),
        }
        self._path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self._path.with_name(f".{self._path.name}.tmp")
        with self._lock:
            try:
                with temporary.open("w", encoding="utf-8") as handle:
                    handle.write(
                        json.dumps(payload, sort_keys=True, separators=(",", ":"))
                    )
                    handle.flush()
                    os.fsync(handle.fileno())
                os.replace(temporary, self._path)
            except OSError as error:
                raise CiboCapitalManagementError(
                    "Phase20D settlement cursor write failed"
                ) from error
            finally:
                temporary.unlink(missing_ok=True)


def observe_ctrader_demo_phase20_settlements(
    *,
    source: Phase20DemoSettlementSource,
    registry: CTraderDemoTradeRegistry,
    settlement_store: DurableCmaSettlementStore,
    cursor_store: DurablePhase20DemoSettlementCursorStore,
    initial_cursor: datetime,
    observed_at: datetime,
) -> Phase20DemoSettlementObservation:
    """Ingest new QORE closing deals without broker mutation authority."""

    _aware(initial_cursor, name="initial_cursor")
    _aware(observed_at, name="observed_at")
    if observed_at <= initial_cursor:
        return Phase20DemoSettlementObservation(
            cursor_at=initial_cursor,
            open_position_ids=(),
            applied_deal_ids=(),
            entry_cost_deal_ids=(),
            partial_deal_ids=(),
            terminal_deal_ids=(),
        )
    if not isinstance(registry, CTraderDemoTradeRegistry):
        raise CiboCapitalManagementError(
            "Phase20D settlement observer requires canonical trade registry"
        )
    if not isinstance(settlement_store, DurableCmaSettlementStore):
        raise CiboCapitalManagementError(
            "Phase20D settlement observer requires canonical settlement store"
        )
    if not isinstance(cursor_store, DurablePhase20DemoSettlementCursorStore):
        raise CiboCapitalManagementError(
            "Phase20D settlement observer requires durable cursor store"
        )

    cursor = cursor_store.load(initial_cursor=initial_cursor)
    window_start = max(initial_cursor, cursor.cursor_at - _OVERLAP)
    deals = source.deals(
        opened_at=window_start,
        closed_at=observed_at,
        max_rows=_MAX_ROWS,
    )
    if len(deals) >= _MAX_ROWS:
        raise CiboCapitalManagementError(
            "Phase20D settlement deal page saturated; cursor cannot advance"
        )
    open_ids = {item.position_id for item in source.positions()}

    book = settlement_store.load()
    known_deal_ids = {
        record.deal_id
        for state in book.states
        for record in state.records
    }
    grouped: dict[int, list[tuple[DemoDeal, str]]] = {}
    unresolved_at: list[datetime] = []

    for deal in deals:
        if deal.executed_at < initial_cursor or deal.deal_id in known_deal_ids:
            continue
        registry_entries = registry.entries_by_position(deal.position_id)
        if not registry_entries:
            # Non-QORE account activity is outside the qualification population.
            continue
        if len(registry_entries) != 1:
            raise CiboCapitalManagementError(
                "Phase20D settlement cannot attribute a netted multi-leg position"
            )
        registry_entry = registry_entries[0]
        if deal.is_closing and deal.net_profit is None:
            unresolved_at.append(deal.executed_at)
            continue
        grouped.setdefault(deal.position_id, []).append(
            (deal, registry_entry.signal_fingerprint)
        )

    entry_costs: list[int] = []
    partials: list[int] = []
    terminals: list[int] = []
    current = book

    for position_id in sorted(grouped):
        rows = sorted(
            grouped[position_id],
            key=lambda item: (item[0].executed_at, item[0].deal_id),
        )
        existing_states = tuple(
            state for state in current.states if state.position_id == position_id
        )
        if any(state.position_closed for state in existing_states):
            raise CiboCapitalManagementError(
                "Phase20D settlement found new deal after terminal close"
            )
        closing_indexes = tuple(
            index for index, (deal, _) in enumerate(rows) if deal.is_closing
        )
        final_closing_index = (
            None
            if position_id in open_ids or not closing_indexes
            else closing_indexes[-1]
        )
        for index, (deal, signal_fingerprint) in enumerate(rows):
            if not deal.is_closing:
                event = "CTRADER_DEMO_ENTRY_COST_SETTLEMENT"
                net_profit = deal.commission
                position_open_after = True
            else:
                assert deal.net_profit is not None
                position_open_after = index != final_closing_index
                event = (
                    "CTRADER_DEMO_PARTIAL_SETTLEMENT"
                    if position_open_after
                    else "CTRADER_DEMO_EXIT_SETTLEMENT"
                )
                net_profit = deal.net_profit
            record = CmaSettlementRecord(
                event=event,
                deal_id=deal.deal_id,
                signal_fingerprint=signal_fingerprint,
                position_id=deal.position_id,
                net_profit_usd=net_profit,
                position_open_after=position_open_after,
            )
            current = settlement_store.apply(
                record,
                expected_generation=current.generation,
            )
            if event == "CTRADER_DEMO_ENTRY_COST_SETTLEMENT":
                entry_costs.append(deal.deal_id)
            elif position_open_after:
                partials.append(deal.deal_id)
            else:
                registry.mark_position_closed(
                    deal.position_id,
                    closed_at=deal.executed_at,
                )
                terminals.append(deal.deal_id)

    next_cursor = observed_at
    if unresolved_at:
        next_cursor = min(next_cursor, min(unresolved_at))
    cursor_store.store(Phase20DemoSettlementCursor(cursor_at=next_cursor))
    return Phase20DemoSettlementObservation(
        cursor_at=next_cursor,
        open_position_ids=tuple(sorted(open_ids)),
        applied_deal_ids=tuple(entry_costs + partials + terminals),
        entry_cost_deal_ids=tuple(entry_costs),
        partial_deal_ids=tuple(partials),
        terminal_deal_ids=tuple(terminals),
    )


def _aware(value: datetime, *, name: str) -> None:
    if value.tzinfo is None or value.utcoffset() is None:
        raise CiboCapitalManagementError(
            f"Phase20D settlement {name} must be timezone-aware"
        )
