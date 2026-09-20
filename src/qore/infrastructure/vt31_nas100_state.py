"""Durable live state for VT31 NAS100.

The state is independent from every other trader lineage and separates:
1. virtual OCO authorization waiting for a fresh broker tick trigger;
2. a broker LIMIT accepted but not yet filled;
3. an open position with its certified structural journey.

No credentials or account secrets are persisted.
"""
from __future__ import annotations

import json
import os
import tempfile
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

_SCHEMA = "qore.vt31.nas100.live_state.v1"


@dataclass(frozen=True, slots=True)
class Vt31VirtualOrderState:
    candidate_id: str
    signal_fingerprint: str
    local_date: str
    tier: str
    authorization_reason: str
    family: str
    side: str
    formed_at: str
    decision_at: str
    expires_at: str
    entry_price: str
    stop_loss: str
    dol1: str
    three_r: str
    nominal_risk_r: str
    reference_high: str
    reference_low: str
    reference_volatility_state: str
    h1_state: str
    premarket_state: str
    cash_open_state: str
    confirmation_latency_minutes: int | None
    risk_ref: str | None
    current_path_vs_previous: str | None
    rearm_quality: str | None = None
    target_plan: str = "UNAVAILABLE"


@dataclass(frozen=True, slots=True)
class Vt31VirtualBasketState:
    basket_id: str
    local_date: str
    tier: str
    authorization_reason: str
    authorized_at: str
    candidates: tuple[Vt31VirtualOrderState, ...]


@dataclass(frozen=True, slots=True)
class Vt31PendingBrokerOrderState:
    client_order_id: str
    risk_authorization_id: str
    signal_fingerprint: str
    local_date: str
    tier: str
    authorization_reason: str
    family: str
    side: str
    decision_at: str
    trigger_at: str
    expires_at: str
    entry_price: str
    stop_loss: str
    dol1: str
    three_r: str
    requested_risk_r: str
    authorized_volume: str
    reference_high: str
    reference_low: str
    reference_volatility_state: str
    h1_state: str
    premarket_state: str
    cash_open_state: str
    confirmation_latency_minutes: int | None
    risk_ref: str | None
    current_path_vs_previous: str | None
    rearm_quality: str | None = None
    target_plan: str = "UNAVAILABLE"
    provider_order_ref: str | None = None


@dataclass(frozen=True, slots=True)
class Vt31OpenTradeState:
    client_order_id: str
    signal_fingerprint: str
    local_date: str
    tier: str
    authorization_reason: str
    family: str
    side: str
    filled_at: str
    entry_price: str
    initial_stop: str
    current_stop: str
    dol1: str
    three_r: str
    requested_risk_r: str
    initial_volume: str
    remaining_volume: str
    reference_high: str
    reference_low: str
    reference_volatility_state: str
    h1_state: str
    premarket_state: str
    cash_open_state: str
    confirmation_latency_minutes: int | None
    risk_ref: str | None
    current_path_vs_previous: str | None
    rearm_quality: str | None
    equilibrium_bank_done: bool = False
    base_partial_done: bool = False
    base_partial_first: bool = False
    dol1_bank_done: bool = False
    runner_active: bool = False
    runner_target: str | None = None
    breaker_lock_armed: bool = False
    ps_confirmations: int = 0
    lifecycle_exit_due_at: str | None = None
    target_plan: str = "UNAVAILABLE"
    base_three_r_be_armed: bool = False
    base_runner_be_active: bool = False
    base_partial_arm_after: str | None = None
    equilibrium_overlay_active: bool = False
    dol1_acceptance_pending: bool = False
    dol1_touch_closed_at: str | None = None


@dataclass(frozen=True, slots=True)
class Vt31Nas100LiveState:
    virtual_basket: Vt31VirtualBasketState | None = None
    pending_broker_order: Vt31PendingBrokerOrderState | None = None
    open_trade: Vt31OpenTradeState | None = None
    closed_signal_fingerprints: tuple[str, ...] = ()
    first_trade_dates: tuple[str, ...] = ()
    rearm_used_dates: tuple[str, ...] = ()
    processed_baskets: tuple[str, ...] = ()
    alt_budget_remaining: tuple[tuple[str, str], ...] = ()
    rearm_budget_remaining: tuple[tuple[str, str], ...] = ()
    last_exit_at: str | None = None
    last_exit_reason: str | None = None

    def alt_budget_map(self) -> dict[str, str]:
        return dict(self.alt_budget_remaining)

    def rearm_budget_map(self) -> dict[str, str]:
        return dict(self.rearm_budget_remaining)


class Vt31Nas100LiveStateStore:
    def __init__(self, path: Path) -> None:
        self._path = path

    def load(self) -> Vt31Nas100LiveState:
        if not self._path.exists():
            return Vt31Nas100LiveState()
        raw = json.loads(self._path.read_text(encoding="utf-8"))
        if raw.get("schema") != _SCHEMA:
            raise ValueError("VT31 NAS100 live-state schema mismatch")
        virtual_raw = raw.get("virtual_basket")
        virtual = None
        if virtual_raw is not None:
            items = tuple(
                Vt31VirtualOrderState(**item)
                for item in virtual_raw.pop("candidates")
            )
            virtual = Vt31VirtualBasketState(
                **virtual_raw,
                candidates=items,
            )
        pending_raw = raw.get("pending_broker_order")
        pending = (
            None
            if pending_raw is None
            else Vt31PendingBrokerOrderState(**pending_raw)
        )
        open_raw = raw.get("open_trade")
        opened = None if open_raw is None else Vt31OpenTradeState(**open_raw)
        return Vt31Nas100LiveState(
            virtual_basket=virtual,
            pending_broker_order=pending,
            open_trade=opened,
            closed_signal_fingerprints=tuple(
                raw.get("closed_signal_fingerprints", ())
            ),
            first_trade_dates=tuple(raw.get("first_trade_dates", ())),
            rearm_used_dates=tuple(raw.get("rearm_used_dates", ())),
            processed_baskets=tuple(raw.get("processed_baskets", ())),
            alt_budget_remaining=tuple(
                (str(k), str(v))
                for k, v in raw.get("alt_budget_remaining", {}).items()
            ),
            rearm_budget_remaining=tuple(
                (str(k), str(v))
                for k, v in raw.get("rearm_budget_remaining", {}).items()
            ),
            last_exit_at=raw.get("last_exit_at"),
            last_exit_reason=raw.get("last_exit_reason"),
        )

    def store(self, state: Vt31Nas100LiveState) -> None:
        payload = {
            "schema": _SCHEMA,
            "identity": "VT31_NAS100_STRUCTURAL_TARGET_V1",
            "virtual_basket": (
                None
                if state.virtual_basket is None
                else asdict(state.virtual_basket)
            ),
            "pending_broker_order": (
                None
                if state.pending_broker_order is None
                else asdict(state.pending_broker_order)
            ),
            "open_trade": (
                None if state.open_trade is None else asdict(state.open_trade)
            ),
            "closed_signal_fingerprints": list(
                state.closed_signal_fingerprints[-512:]
            ),
            "first_trade_dates": list(state.first_trade_dates[-180:]),
            "rearm_used_dates": list(state.rearm_used_dates[-180:]),
            "processed_baskets": list(state.processed_baskets[-512:]),
            "alt_budget_remaining": dict(state.alt_budget_remaining),
            "rearm_budget_remaining": dict(state.rearm_budget_remaining),
            "last_exit_at": state.last_exit_at,
            "last_exit_reason": state.last_exit_reason,
        }
        self._path.parent.mkdir(parents=True, exist_ok=True)
        fd, name = tempfile.mkstemp(
            prefix=f".{self._path.name}.",
            suffix=".tmp",
            dir=self._path.parent,
        )
        temp = Path(name)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                json.dump(
                    payload,
                    handle,
                    sort_keys=True,
                    separators=(",", ":"),
                )
                handle.write("\n")
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temp, self._path)
        finally:
            if temp.exists():
                temp.unlink()

    def replace(self, **changes: Any) -> Vt31Nas100LiveState:
        current = self.load()
        payload = {
            field: getattr(current, field)
            for field in current.__dataclass_fields__
        }
        payload.update(changes)
        state = Vt31Nas100LiveState(**payload)
        self.store(state)
        return state

    def mark_basket(
        self,
        basket: Vt31VirtualBasketState,
    ) -> Vt31Nas100LiveState:
        state = self.load()
        updated = Vt31Nas100LiveState(
            **{
                **{
                    field: getattr(state, field)
                    for field in state.__dataclass_fields__
                },
                "virtual_basket": basket,
            }
        )
        self.store(updated)
        return updated

    def clear_virtual_basket(self) -> Vt31Nas100LiveState:
        return self.replace(virtual_basket=None)

    def mark_pending(
        self,
        pending: Vt31PendingBrokerOrderState,
    ) -> Vt31Nas100LiveState:
        state = self.load()
        processed = tuple(
            (*state.processed_baskets, pending.signal_fingerprint)
        )[-512:]
        return self.replace(
            virtual_basket=None,
            pending_broker_order=pending,
            processed_baskets=processed,
        )

    def mark_open(
        self,
        opened: Vt31OpenTradeState,
    ) -> Vt31Nas100LiveState:
        state = self.load()
        first_dates = state.first_trade_dates
        if opened.tier != "REARM" and opened.local_date not in first_dates:
            first_dates = tuple((*first_dates, opened.local_date))[-180:]
        if opened.tier == "REARM":
            rearms = tuple(
                (*state.rearm_used_dates, opened.local_date)
            )[-180:]
        else:
            rearms = state.rearm_used_dates
        return self.replace(
            pending_broker_order=None,
            open_trade=opened,
            first_trade_dates=first_dates,
            rearm_used_dates=rearms,
        )

    def mark_closed(
        self,
        *,
        closed_at: datetime,
        reason: str,
    ) -> Vt31Nas100LiveState:
        if closed_at.tzinfo is None or closed_at.utcoffset() is None:
            raise ValueError("VT31 close timestamp must be timezone-aware")
        state = self.load()
        opened = state.open_trade
        closed = state.closed_signal_fingerprints
        if opened is not None:
            closed = tuple(
                (*closed, opened.signal_fingerprint)
            )[-512:]
        return self.replace(
            open_trade=None,
            pending_broker_order=None,
            virtual_basket=None,
            closed_signal_fingerprints=closed,
            last_exit_at=closed_at.astimezone(UTC).isoformat(),
            last_exit_reason=reason,
        )
