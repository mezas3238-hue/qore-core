"""Read-only cTrader DEMO LIVE behavior laboratory.

The laboratory observes and classifies runtime evidence. It has no authority to
change strategy decisions, CIBO sizing, Risk allocations, broker orders, stops,
targets or position lifecycle. Its only purpose is to preserve enough evidence
to explain what each trader did in LIVE DEMO and which management behavior was
or was not observed.
"""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from enum import StrEnum
from pathlib import Path
from threading import Lock


class BehaviorStage(StrEnum):
    SIGNAL = "SIGNAL"
    CIBO = "CIBO"
    RISK = "RISK"
    EXECUTION = "EXECUTION"
    POSITION = "POSITION"
    MANAGEMENT = "MANAGEMENT"
    EXIT = "EXIT"
    FAULT = "FAULT"
    OTHER = "OTHER"


@dataclass(frozen=True, slots=True)
class TraderBehaviorContract:
    trader: str
    management_contract: str
    sizing_path: str


TRADER_BEHAVIOR_CONTRACTS: dict[str, TraderBehaviorContract] = {
    "VT08_FOREX": TraderBehaviorContract(
        trader="VT08_FOREX",
        management_contract="STATIC_SL_TP_PLUS_H4_CONTAINMENT_EXIT",
        sizing_path="VT08_CIBO_AUTHORIZATION_PLUS_DEMO_NATIVE_RISK_SIZING",
    ),
    "R34_XAUUSD": TraderBehaviorContract(
        trader="R34_XAUUSD",
        management_contract="STATIC_SL_TP_PLUS_24H_EXIT",
        sizing_path="R34_BASE_RISK_X_GOVERNOR_SCALE_THEN_DEMO_NATIVE_VOLUME",
    ),
    "R38_EURUSD": TraderBehaviorContract(
        trader="R38_EURUSD",
        management_contract="DOL_LOCK_M5_SWING_TRAIL_PLUS_24H_EXIT",
        sizing_path="R38_EURUSD_BASE_RISK_X_COGNITIVE_SCALE_THEN_DEMO_NATIVE_VOLUME",
    ),
    "R43_GBPUSD": TraderBehaviorContract(
        trader="R43_GBPUSD",
        management_contract="DOL_LOCK_M5_SWING_TRAIL_PLUS_24H_EXIT",
        sizing_path="R43_GBPUSD_BASE_RISK_X_COGNITIVE_SCALE_THEN_DEMO_NATIVE_VOLUME",
    ),
    "R38_GBPJPY": TraderBehaviorContract(
        trader="R38_GBPJPY",
        management_contract="DOL_LOCK_M5_SWING_TRAIL_PLUS_24H_EXIT",
        sizing_path="R38_GBPJPY_BASE_RISK_X_COGNITIVE_SCALE_THEN_DEMO_NATIVE_VOLUME",
    ),
    "R42_AUDJPY": TraderBehaviorContract(
        trader="R42_AUDJPY",
        management_contract="DOL_LOCK_M5_SWING_TRAIL_PLUS_24H_EXIT",
        sizing_path="R42_AUDJPY_BASE_RISK_X_COGNITIVE_SCALE_THEN_DEMO_NATIVE_VOLUME",
    ),
    "VT31_NAS100": TraderBehaviorContract(
        trader="VT31_NAS100",
        management_contract="V4_PARTIAL_BE_DOL1_RUNNER_PS2_STOP_ADVANCE",
        sizing_path="VT31_CERTIFIED_RISK_RESOLUTION_THEN_DEMO_NATIVE_VOLUME",
    ),
}


@dataclass(frozen=True, slots=True)
class LiveBehaviorEvent:
    case_id: str
    observed_at: datetime
    source: str
    stage: BehaviorStage
    event: str
    trader: str | None
    symbol: str | None
    signal_fingerprint: str | None
    position_id: int | None
    payload: dict[str, object]

    def as_json(self) -> dict[str, object]:
        return {
            "case_id": self.case_id,
            "observed_at": self.observed_at.astimezone(UTC).isoformat(),
            "source": self.source,
            "stage": self.stage.value,
            "event": self.event,
            "trader": self.trader,
            "symbol": self.symbol,
            "signal_fingerprint": self.signal_fingerprint,
            "position_id": self.position_id,
            "payload": self.payload,
        }

    @classmethod
    def from_json(cls, value: Mapping[str, object]) -> LiveBehaviorEvent:
        observed = datetime.fromisoformat(str(value["observed_at"]))
        if observed.tzinfo is None or observed.utcoffset() is None:
            raise ValueError("behavior event observed_at must be timezone-aware")
        raw_position = value.get("position_id")
        if raw_position is None or not str(raw_position).strip():
            position_id = None
        elif isinstance(raw_position, (int, str)):
            position_id = int(raw_position)
        else:
            raise ValueError("behavior event position_id must be int/string/null")
        payload = value.get("payload")
        if not isinstance(payload, dict):
            raise ValueError("behavior event payload must be object")
        return cls(
            case_id=str(value["case_id"]),
            observed_at=observed,
            source=str(value["source"]),
            stage=BehaviorStage(str(value["stage"])),
            event=str(value["event"]),
            trader=_optional_text(value.get("trader")),
            symbol=_optional_text(value.get("symbol")),
            signal_fingerprint=_optional_text(value.get("signal_fingerprint")),
            position_id=position_id,
            payload=dict(payload),
        )


@dataclass(frozen=True, slots=True)
class LiveBehaviorCaseReport:
    case_id: str
    trader: str | None
    symbol: str | None
    first_observed_at: datetime
    last_observed_at: datetime
    event_count: int
    stages: dict[str, int]
    event_names: tuple[str, ...]
    requested_volumes: tuple[str, ...]
    requested_stop_risks: tuple[str, ...]
    protection_events: tuple[str, ...]
    partial_close_events: tuple[str, ...]
    exit_events: tuple[str, ...]
    fault_events: tuple[str, ...]
    settlement_events: tuple[str, ...]
    realized_net_pnl: str | None
    settlement_prices: tuple[str, ...]
    settled_source_volumes: tuple[str, ...]
    estimated_initial_risk_pnl: str | None
    estimated_remaining_stop_pnl: str | None
    estimated_economic_floor_pnl: str | None
    estimated_economic_floor_r: str | None
    path_sample_count: int
    max_unrealized_pnl: str | None
    min_unrealized_pnl: str | None
    max_favorable_price_delta: str | None
    max_adverse_price_delta: str | None
    stop_history: tuple[str, ...]
    volume_history: tuple[str, ...]
    observations: tuple[str, ...]

    def as_json(self) -> dict[str, object]:
        return {
            "case_id": self.case_id,
            "trader": self.trader,
            "symbol": self.symbol,
            "first_observed_at": self.first_observed_at.astimezone(UTC).isoformat(),
            "last_observed_at": self.last_observed_at.astimezone(UTC).isoformat(),
            "event_count": self.event_count,
            "stages": self.stages,
            "event_names": list(self.event_names),
            "requested_volumes": list(self.requested_volumes),
            "requested_stop_risks": list(self.requested_stop_risks),
            "protection_events": list(self.protection_events),
            "partial_close_events": list(self.partial_close_events),
            "exit_events": list(self.exit_events),
            "fault_events": list(self.fault_events),
            "settlement_events": list(self.settlement_events),
            "realized_net_pnl": self.realized_net_pnl,
            "settlement_prices": list(self.settlement_prices),
            "settled_source_volumes": list(self.settled_source_volumes),
            "estimated_initial_risk_pnl": self.estimated_initial_risk_pnl,
            "estimated_remaining_stop_pnl": self.estimated_remaining_stop_pnl,
            "estimated_economic_floor_pnl": self.estimated_economic_floor_pnl,
            "estimated_economic_floor_r": self.estimated_economic_floor_r,
            "path_sample_count": self.path_sample_count,
            "max_unrealized_pnl": self.max_unrealized_pnl,
            "min_unrealized_pnl": self.min_unrealized_pnl,
            "max_favorable_price_delta": self.max_favorable_price_delta,
            "max_adverse_price_delta": self.max_adverse_price_delta,
            "stop_history": list(self.stop_history),
            "volume_history": list(self.volume_history),
            "observations": list(self.observations),
        }


class CTraderDemoLiveBehaviorLedger:
    """Append-only evidence ledger used only by the DEMO behavior laboratory."""

    def __init__(self, path: Path) -> None:
        if not isinstance(path, Path):
            raise TypeError("behavior ledger path must be Path")
        self._path = path
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = Lock()

    @property
    def path(self) -> Path:
        return self._path

    def record_raw(
        self,
        raw: Mapping[str, object],
        *,
        source: str,
        observed_at: datetime | None = None,
    ) -> LiveBehaviorEvent:
        event = normalize_runtime_event(raw, source=source, observed_at=observed_at)
        self.append(event)
        return event

    def append(self, event: LiveBehaviorEvent) -> None:
        row = json.dumps(
            event.as_json(),
            sort_keys=True,
            separators=(",", ":"),
            default=str,
        )
        with self._lock:
            with self._path.open("a", encoding="utf-8") as handle:
                handle.write(row + "\n")

    def events(self) -> tuple[LiveBehaviorEvent, ...]:
        if not self._path.exists():
            return ()
        rows: list[LiveBehaviorEvent] = []
        with self._lock:
            with self._path.open("r", encoding="utf-8") as handle:
                for line in handle:
                    stripped = line.strip()
                    if not stripped:
                        continue
                    parsed = json.loads(stripped)
                    if not isinstance(parsed, dict):
                        raise ValueError("behavior ledger row must be object")
                    rows.append(LiveBehaviorEvent.from_json(parsed))
        return tuple(sorted(rows, key=lambda item: item.observed_at))


def settlement_observation_payload(
    *,
    trader: str,
    symbol: str,
    signal_fingerprint: str,
    position_id: int,
    deal_id: int,
    order_id: int,
    side: str,
    execution_price: Decimal,
    filled_units: Decimal,
    source_volume: Decimal,
    net_profit: Decimal,
    gross_profit: Decimal,
    commission: Decimal,
    swap: Decimal,
    pnl_conversion_fee: Decimal,
    balance_after: Decimal | None,
    executed_at: datetime,
    position_open_after: bool,
) -> dict[str, object]:
    """Build one immutable broker settlement observation."""

    if side not in {"long", "short"}:
        raise ValueError("settlement side must be long/short")
    if min(position_id, deal_id, order_id) <= 0:
        raise ValueError("settlement ids must be positive")
    if executed_at.tzinfo is None or executed_at.utcoffset() is None:
        raise ValueError("settlement executed_at must be timezone-aware")
    for name, value in (
        ("execution_price", execution_price),
        ("filled_units", filled_units),
        ("source_volume", source_volume),
        ("net_profit", net_profit),
        ("gross_profit", gross_profit),
        ("commission", commission),
        ("swap", swap),
        ("pnl_conversion_fee", pnl_conversion_fee),
    ):
        if not isinstance(value, Decimal) or not value.is_finite():
            raise ValueError(f"settlement {name} must be finite Decimal")
    if execution_price <= 0 or filled_units <= 0 or source_volume <= 0:
        raise ValueError("settlement price/volume values must be positive")
    if balance_after is not None and (
        not isinstance(balance_after, Decimal) or not balance_after.is_finite()
    ):
        raise ValueError("settlement balance_after must be finite Decimal/null")

    return {
        "event": (
            "CTRADER_DEMO_PARTIAL_SETTLEMENT"
            if position_open_after
            else "CTRADER_DEMO_EXIT_SETTLEMENT"
        ),
        "trader": trader,
        "symbol": symbol,
        "signal_fingerprint": signal_fingerprint,
        "position_id": position_id,
        "deal_id": deal_id,
        "order_id": order_id,
        "side": side,
        "execution_price": format(execution_price, "f"),
        "filled_units": format(filled_units, "f"),
        "source_volume": format(source_volume, "f"),
        "net_profit": format(net_profit, "f"),
        "gross_profit": format(gross_profit, "f"),
        "commission": format(commission, "f"),
        "swap": format(swap, "f"),
        "pnl_conversion_fee": format(pnl_conversion_fee, "f"),
        "balance_after": (
            None if balance_after is None else format(balance_after, "f")
        ),
        "position_open_after": position_open_after,
        "executed_at": executed_at.astimezone(UTC).isoformat(),
    }


def position_path_observation_payload(
    *,
    trader: str,
    symbol: str,
    signal_fingerprint: str,
    position_id: int,
    side: str,
    entry_price: Decimal,
    bid: Decimal,
    ask: Decimal,
    stop_loss: Decimal,
    take_profit: Decimal,
    volume: Decimal,
    unrealized_pnl: Decimal,
    observed_at: datetime,
) -> dict[str, object]:
    """Build one causal open-position path sample for the behavior lab."""

    if side not in {"long", "short"}:
        raise ValueError("position path side must be long/short")
    if position_id <= 0:
        raise ValueError("position path position_id must be positive")
    if observed_at.tzinfo is None or observed_at.utcoffset() is None:
        raise ValueError("position path observed_at must be timezone-aware")
    for name, value in (
        ("entry_price", entry_price),
        ("bid", bid),
        ("ask", ask),
        ("stop_loss", stop_loss),
        ("take_profit", take_profit),
        ("volume", volume),
        ("unrealized_pnl", unrealized_pnl),
    ):
        if not isinstance(value, Decimal) or not value.is_finite():
            raise ValueError(f"position path {name} must be finite Decimal")
    if min(entry_price, bid, ask, volume) <= 0:
        raise ValueError("position path market price/volume values must be positive")
    if stop_loss < 0 or take_profit < 0:
        raise ValueError("position path protection values cannot be negative")

    mark = bid if side == "long" else ask
    directional_delta = (
        mark - entry_price
        if side == "long"
        else entry_price - mark
    )
    return {
        "event": "CTRADER_DEMO_POSITION_PATH_SAMPLE",
        "trader": trader,
        "symbol": symbol,
        "signal_fingerprint": signal_fingerprint,
        "position_id": position_id,
        "side": side,
        "entry_price": format(entry_price, "f"),
        "bid": format(bid, "f"),
        "ask": format(ask, "f"),
        "mark_price": format(mark, "f"),
        "directional_price_delta": format(directional_delta, "f"),
        "stop_loss": format(stop_loss, "f"),
        "take_profit": format(take_profit, "f"),
        "volume": format(volume, "f"),
        "unrealized_pnl": format(unrealized_pnl, "f"),
        "observed_at": observed_at.astimezone(UTC).isoformat(),
    }


def normalize_runtime_event(
    raw: Mapping[str, object],
    *,
    source: str,
    observed_at: datetime | None = None,
) -> LiveBehaviorEvent:
    if not source:
        raise ValueError("behavior event source is required")
    event_name = str(raw.get("event") or "UNKNOWN")
    event_at = observed_at or _event_timestamp(raw)
    trader = _first_text(raw, "trader", "identity", "trader_id")
    symbol = _first_text(raw, "symbol", "qore_symbol")
    signal = _first_text(raw, "signal_fingerprint", "signal")
    position_id = _first_positive_int(raw, "position_id", "position_ticket", "position")
    case_id = _case_id(
        raw,
        trader=trader,
        symbol=symbol,
        signal_fingerprint=signal,
        position_id=position_id,
    )
    return LiveBehaviorEvent(
        case_id=case_id,
        observed_at=event_at,
        source=source,
        stage=classify_stage(event_name),
        event=event_name,
        trader=trader,
        symbol=symbol,
        signal_fingerprint=signal,
        position_id=position_id,
        payload=dict(raw),
    )


def classify_stage(event_name: str) -> BehaviorStage:
    name = event_name.upper()
    if any(token in name for token in ("FAIL", "ERROR", "REJECT", "DENY")):
        return BehaviorStage.FAULT
    if any(token in name for token in ("CLOSED", "EXIT", "TERMINAL")):
        return BehaviorStage.EXIT
    if any(
        token in name
        for token in (
            "STOP_ADVANCED",
            "_BE_",
            "TRAIL",
            "RUNNER",
            "PARTIAL",
            "BANKED",
            "DOL1",
            "EQ50",
            "MANAGEMENT",
            "PROTECT",
        )
    ):
        return BehaviorStage.MANAGEMENT
    if any(token in name for token in ("FILL", "POSITION")):
        return BehaviorStage.POSITION
    if any(
        token in name
        for token in ("SUBMIT", "EXECUTION", "PENDING", "ORDER_SEND", "ORDER_ACCEPT")
    ):
        return BehaviorStage.EXECUTION
    if "CIBO" in name:
        return BehaviorStage.CIBO
    if "RISK" in name or "ALLOCAT" in name or "SIZ" in name:
        return BehaviorStage.RISK
    if any(token in name for token in ("CANDIDATE", "STRATEGY_DECISION", "ABSTAIN", "SIGNAL")):
        return BehaviorStage.SIGNAL
    return BehaviorStage.OTHER


def build_case_reports(
    events: Iterable[LiveBehaviorEvent],
) -> tuple[LiveBehaviorCaseReport, ...]:
    grouped: dict[str, list[LiveBehaviorEvent]] = {}
    for event in events:
        grouped.setdefault(event.case_id, []).append(event)

    reports = [
        _build_case_report(case_id, tuple(sorted(rows, key=lambda item: item.observed_at)))
        for case_id, rows in grouped.items()
    ]
    return tuple(sorted(reports, key=lambda item: (item.first_observed_at, item.case_id)))


def _build_case_report(
    case_id: str,
    events: tuple[LiveBehaviorEvent, ...],
) -> LiveBehaviorCaseReport:
    if not events:
        raise ValueError("behavior case requires at least one event")
    stage_counts = Counter(item.stage.value for item in events)
    names = tuple(item.event for item in events)
    trader = next((item.trader for item in events if item.trader), None)
    symbol = next((item.symbol for item in events if item.symbol), None)
    requested_volumes = _payload_values(
        events,
        "requested_volume",
        "authorized_volume",
        "volume",
    )
    requested_stop_risks = _payload_values(
        events,
        "requested_stop_risk",
        "strategy_requested_risk_usd",
        "requested_risk_r",
    )
    protection = tuple(
        name
        for name in names
        if any(token in name.upper() for token in ("STOP_ADVANCED", "_BE_", "TRAIL", "PROTECT"))
    )
    partials = tuple(
        name
        for name in names
        if any(token in name.upper() for token in ("PARTIAL", "BANKED", "EQ50", "DOL1_QUARTER"))
    )
    exits = tuple(item.event for item in events if item.stage is BehaviorStage.EXIT)
    faults = tuple(item.event for item in events if item.stage is BehaviorStage.FAULT)
    settlements = tuple(
        item for item in events if "SETTLEMENT" in item.event.upper()
    )
    settlement_pnl = _decimal_payload_series(settlements, "net_profit")
    settlement_prices = _unique_payload_values(settlements, "execution_price")
    settled_source_volumes = _unique_payload_values(settlements, "source_volume")
    path_samples = tuple(
        item
        for item in events
        if item.event == "CTRADER_DEMO_POSITION_PATH_SAMPLE"
    )
    unrealized = _decimal_payload_series(path_samples, "unrealized_pnl")
    directional = _decimal_payload_series(path_samples, "directional_price_delta")
    stop_history = _unique_payload_values(path_samples, "stop_loss")
    volume_history = _unique_payload_values(path_samples, "volume")
    (
        estimated_initial_risk,
        estimated_remaining_stop,
        estimated_floor,
        estimated_floor_r,
    ) = _economic_floor_estimate(
        events=events,
        path_samples=path_samples,
        settlements=settlements,
        realized_pnl=sum(settlement_pnl, Decimal("0")),
    )
    observations = _observations(
        trader=trader,
        names=names,
        stages=stage_counts,
        protection=protection,
        exits=exits,
        requested_volumes=requested_volumes,
        settlements=settlements,
        settlement_pnl=settlement_pnl,
        estimated_floor=estimated_floor,
        estimated_floor_r=estimated_floor_r,
    )
    return LiveBehaviorCaseReport(
        case_id=case_id,
        trader=trader,
        symbol=symbol,
        first_observed_at=events[0].observed_at,
        last_observed_at=events[-1].observed_at,
        event_count=len(events),
        stages=dict(sorted(stage_counts.items())),
        event_names=names,
        requested_volumes=requested_volumes,
        requested_stop_risks=requested_stop_risks,
        protection_events=protection,
        partial_close_events=partials,
        exit_events=exits,
        fault_events=faults,
        settlement_events=tuple(item.event for item in settlements),
        realized_net_pnl=_format_optional_decimal(
            sum(settlement_pnl, Decimal("0")) if settlement_pnl else None
        ),
        settlement_prices=settlement_prices,
        settled_source_volumes=settled_source_volumes,
        estimated_initial_risk_pnl=_format_optional_decimal(estimated_initial_risk),
        estimated_remaining_stop_pnl=_format_optional_decimal(
            estimated_remaining_stop
        ),
        estimated_economic_floor_pnl=_format_optional_decimal(estimated_floor),
        estimated_economic_floor_r=_format_optional_decimal(estimated_floor_r),
        path_sample_count=len(path_samples),
        max_unrealized_pnl=_format_optional_decimal(max(unrealized) if unrealized else None),
        min_unrealized_pnl=_format_optional_decimal(min(unrealized) if unrealized else None),
        max_favorable_price_delta=_format_optional_decimal(
            max(directional) if directional else None
        ),
        max_adverse_price_delta=_format_optional_decimal(
            min(directional) if directional else None
        ),
        stop_history=stop_history,
        volume_history=volume_history,
        observations=observations,
    )


def _observations(
    *,
    trader: str | None,
    names: tuple[str, ...],
    stages: Counter[str],
    protection: tuple[str, ...],
    exits: tuple[str, ...],
    requested_volumes: tuple[str, ...],
    settlements: tuple[LiveBehaviorEvent, ...],
    settlement_pnl: tuple[Decimal, ...],
    estimated_floor: Decimal | None,
    estimated_floor_r: Decimal | None,
) -> tuple[str, ...]:
    notes: list[str] = []
    contract = TRADER_BEHAVIOR_CONTRACTS.get(trader or "")
    if contract is not None:
        notes.append(f"declared_sizing_path={contract.sizing_path}")
        notes.append(f"declared_management_contract={contract.management_contract}")

    saw_execution = stages[BehaviorStage.EXECUTION.value] > 0
    saw_position = stages[BehaviorStage.POSITION.value] > 0
    saw_cibo = stages[BehaviorStage.CIBO.value] > 0
    if saw_execution and not requested_volumes:
        notes.append("requested_volume_not_observed")
    if trader == "VT31_NAS100" and saw_execution and not saw_cibo:
        notes.append("no_explicit_cibo_sizing_event_observed_for_vt31")
    if saw_position and not protection:
        notes.append("no_physical_stop_or_trailing_event_observed")
    if settlements:
        realized = sum(settlement_pnl, Decimal("0"))
        notes.append(f"realized_settlement_net_pnl={format(realized, 'f')}")
        if any("PARTIAL" in item.event.upper() for item in settlements):
            notes.append("realized_partial_settlement_observed")
    if estimated_floor is not None:
        notes.append(f"estimated_economic_floor_pnl={format(estimated_floor, 'f')}")
    if estimated_floor_r is not None:
        notes.append(f"estimated_economic_floor_r={format(estimated_floor_r, 'f')}")
    if exits and not protection:
        notes.append("position_exited_without_observed_protection_event")
    if stages[BehaviorStage.FAULT.value] > 0:
        notes.append("fault_or_rejection_present")
    if any("STOP" in name.upper() for name in exits):
        notes.append("stop_exit_observed")
    return tuple(notes)


def _economic_floor_estimate(
    *,
    events: tuple[LiveBehaviorEvent, ...],
    path_samples: tuple[LiveBehaviorEvent, ...],
    settlements: tuple[LiveBehaviorEvent, ...],
    realized_pnl: Decimal,
) -> tuple[Decimal | None, Decimal | None, Decimal | None, Decimal | None]:
    if not path_samples:
        return None, None, None, None

    first = path_samples[0].payload
    latest = path_samples[-1].payload
    try:
        entry = Decimal(str(first["entry_price"]))
        initial_stop = Decimal(str(first["stop_loss"]))
        current_stop = Decimal(str(latest["stop_loss"]))
        current_volume = Decimal(str(latest["volume"]))
        current_unrealized = Decimal(str(latest["unrealized_pnl"]))
        current_delta = Decimal(str(latest["directional_price_delta"]))
    except (KeyError, InvalidOperation):
        return None, None, None, None
    side = str(first.get("side", ""))
    if side not in {"long", "short"}:
        return None, None, None, None
    if min(entry, initial_stop, current_stop, current_volume) <= 0:
        return None, None, None, None
    if current_delta == 0 or current_volume <= 0:
        return None, None, None, None

    requested_volume: Decimal | None = None
    for event in events:
        if event.event != "CTRADER_DEMO_FREE_SUBMIT":
            continue
        raw = event.payload.get("requested_volume")
        if raw is None:
            continue
        try:
            candidate = Decimal(str(raw))
        except InvalidOperation:
            continue
        if candidate.is_finite() and candidate > 0:
            requested_volume = candidate
            break
    if requested_volume is None:
        try:
            requested_volume = Decimal(str(first["volume"]))
        except (KeyError, InvalidOperation):
            return None, None, None, None

    money_per_price_per_volume = abs(
        current_unrealized / (current_delta * current_volume)
    )
    if not money_per_price_per_volume.is_finite() or money_per_price_per_volume <= 0:
        return None, None, None, None

    if side == "long":
        initial_stop_delta = initial_stop - entry
        current_stop_delta = current_stop - entry
    else:
        initial_stop_delta = entry - initial_stop
        current_stop_delta = entry - current_stop

    initial_risk = abs(
        initial_stop_delta * requested_volume * money_per_price_per_volume
    )
    if initial_risk <= 0:
        return None, None, None, None

    has_exit = any("EXIT_SETTLEMENT" in item.event.upper() for item in settlements)
    if has_exit:
        remaining_stop_pnl = Decimal("0")
        floor = realized_pnl
    else:
        remaining_stop_pnl = (
            current_stop_delta
            * current_volume
            * money_per_price_per_volume
        )
        floor = realized_pnl + remaining_stop_pnl
    return initial_risk, remaining_stop_pnl, floor, floor / initial_risk


def _decimal_payload_series(
    events: tuple[LiveBehaviorEvent, ...],
    key: str,
) -> tuple[Decimal, ...]:
    values: list[Decimal] = []
    for event in events:
        raw = event.payload.get(key)
        if raw is None:
            continue
        try:
            value = Decimal(str(raw))
        except InvalidOperation:
            continue
        if value.is_finite():
            values.append(value)
    return tuple(values)


def _unique_payload_values(
    events: tuple[LiveBehaviorEvent, ...],
    key: str,
) -> tuple[str, ...]:
    values: list[str] = []
    for event in events:
        raw = event.payload.get(key)
        if raw is None:
            continue
        value = str(raw)
        if value not in values:
            values.append(value)
    return tuple(values)


def _format_optional_decimal(value: Decimal | None) -> str | None:
    return None if value is None else format(value, "f")


def _payload_values(
    events: tuple[LiveBehaviorEvent, ...],
    *keys: str,
) -> tuple[str, ...]:
    values: list[str] = []
    for event in events:
        for key in keys:
            raw = event.payload.get(key)
            if raw is None:
                continue
            value = str(raw)
            if value not in values:
                values.append(value)
    return tuple(values)


def _event_timestamp(raw: Mapping[str, object]) -> datetime:
    for key in (
        "logged_at",
        "recorded_at",
        "observed_at",
        "decision_at_utc",
        "decision_at",
        "filled_at",
        "closed_at",
    ):
        value = raw.get(key)
        if not isinstance(value, str) or not value:
            continue
        try:
            parsed = datetime.fromisoformat(value)
        except ValueError:
            continue
        if parsed.tzinfo is not None and parsed.utcoffset() is not None:
            return parsed
    return datetime.now(UTC)


def _case_id(
    raw: Mapping[str, object],
    *,
    trader: str | None,
    symbol: str | None,
    signal_fingerprint: str | None,
    position_id: int | None,
) -> str:
    if signal_fingerprint:
        return f"signal:{signal_fingerprint}"
    if position_id is not None:
        return f"position:{position_id}"
    request_id = _first_text(raw, "request_id", "client_order_id", "basket_id")
    boundary = _first_text(
        raw,
        "boundary_at_utc",
        "boundary_at",
        "decision_at_utc",
        "decision_at",
    )
    material = "|".join(
        (
            trader or "unknown-trader",
            symbol or "unknown-symbol",
            request_id or "no-request",
            boundary or "no-boundary",
            str(raw.get("event") or "UNKNOWN"),
        )
    )
    digest = hashlib.sha256(material.encode("utf-8")).hexdigest()[:24]
    return f"event:{digest}"


def _first_text(raw: Mapping[str, object], *keys: str) -> str | None:
    for key in keys:
        value = raw.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def _optional_text(value: object) -> str | None:
    return value.strip() if isinstance(value, str) and value.strip() else None


def _first_positive_int(raw: Mapping[str, object], *keys: str) -> int | None:
    for key in keys:
        value = raw.get(key)
        if type(value) is int and value > 0:
            return value
        if isinstance(value, str) and value.isdigit() and int(value) > 0:
            return int(value)
    return None


def case_reports_as_json(
    reports: Iterable[LiveBehaviorCaseReport],
) -> list[dict[str, object]]:
    return [report.as_json() for report in reports]



_MANAGEMENT_STATE_FIELDS = (
    "client_order_id",
    "signal_fingerprint",
    "entry_at",
    "filled_at",
    "side",
    "entry_price",
    "initial_stop",
    "current_stop",
    "take_profit",
    "posture",
    "target_rank",
    "target_route",
    "base_risk_usd",
    "risk_scale",
    "initial_volume",
    "remaining_volume",
    "dol1",
    "three_r",
    "base_partial_done",
    "base_partial_first",
    "base_three_r_be_armed",
    "base_runner_be_active",
    "dol1_bank_done",
    "dol1_acceptance_pending",
    "dol1_touch_closed_at",
    "runner_active",
    "runner_target",
    "ps_confirmations",
    "breaker_lock_armed",
    "equilibrium_bank_done",
    "equilibrium_overlay_active",
    "target_plan",
)


def sizing_path_for(trader: str) -> str:
    contract = TRADER_BEHAVIOR_CONTRACTS.get(trader)
    return "UNDECLARED" if contract is None else contract.sizing_path


def management_observation_payload(
    *,
    trader: str,
    symbol: str,
    state: object,
    reason: str,
    observed_at: datetime | None = None,
) -> dict[str, object]:
    """Return passive management telemetry without invoking broker mutations."""

    now = observed_at or datetime.now(UTC)
    if now.tzinfo is None or now.utcoffset() is None:
        raise ValueError("management observation time must be timezone-aware")
    payload: dict[str, object] = {
        "event": "CTRADER_DEMO_MANAGEMENT_OBSERVATION",
        "trader": trader,
        "symbol": symbol,
        "reason": reason,
        "observed_at": now.astimezone(UTC).isoformat(),
    }
    contract = TRADER_BEHAVIOR_CONTRACTS.get(trader)
    if contract is not None:
        payload["management_contract"] = contract.management_contract
        payload["sizing_path"] = contract.sizing_path
    opened = getattr(state, "open_trade", None)
    payload["open_trade_present"] = opened is not None
    if opened is None:
        return payload
    for field in _MANAGEMENT_STATE_FIELDS:
        if not hasattr(opened, field):
            continue
        value = getattr(opened, field)
        if value is None:
            continue
        payload[field] = value
    return payload
