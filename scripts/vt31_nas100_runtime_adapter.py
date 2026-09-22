"""Resident VT31 NAS100 adapter for the single-writer FundedNext runtime.

The certified strategy is not recalibrated here. This adapter owns only:
- M1 cache/boundary orchestration;
- Account-Wide Risk authorization;
- broker order_check / canonical submission;
- durable virtual basket and broker-pending state;
- fill reconciliation;
- certified Execution Binding V4 target/journey management.

Admission and journey execution remain separate code paths but share the same
resident single writer, broker checks, durable state and Account-Wide Risk.
"""
# ruff: noqa: I001
from __future__ import annotations

import hashlib
from datetime import UTC, datetime, timedelta
from decimal import ROUND_FLOOR, Decimal
from collections.abc import Callable
from typing import Any

from qore.infrastructure.account_wide_risk import (
    AccountRiskSnapshot,
    RiskDecision,
)
from qore.infrastructure.account_wide_risk_ledger import (
    DurableAccountWideRiskEngine,
)
from qore.infrastructure.fundednext_live_mt5 import (
    FundedNextLiveMt5ExecutionGateway,
    MetaTrader5FundedNextLiveTransport,
)
from qore.infrastructure.fundednext_mt5 import Mt5ProviderOutcome
from qore.infrastructure.fundednext_mt5_clock import normalise_fundednext_server_epoch
from qore.infrastructure.fundednext_operational import build_account_bound_submission
from qore.infrastructure.pretrade_safety import (
    ExecutionSafetySwitchSnapshot,
    ExecutionSwitchState,
)
from qore.infrastructure.vt31_nas100_live import (
    CIBO_MEMORY_FINGERPRINT,
    COGNITIVE_MEMORY_FINGERPRINT,
    CERTIFICATION_REPORT_SHA256,
    DECISION_DEADLINE,
    EXECUTION_BINDING_FINGERPRINT,
    EXECUTION_BINDING_ID,
    MAX_BROKER_TICK_AGE,
    PROVIDER_SYMBOL,
    SERVICE_24_7,
    SILVER_BULLET_SOURCE_FINGERPRINT,
    TARGET_ARCHITECTURE_ID,
    STRATEGY_IDENTITY,
    STRATEGY_MEMORY_FINGERPRINT,
    TRADER_EXPERIENCE_FINGERPRINT,
    Vt31Nas100LiveError,
    Vt31Nas100M1Cache,
    Vt31RiskContext,
    Vt31VirtualCandidate,
    assert_deadline,
    build_risk_request,
    resolve_certified_risk,
    virtual_oco_trigger,
)
from qore.infrastructure.vt31_nas100_state import (
    Vt31Nas100LiveStateStore,
    Vt31OpenTradeState,
    Vt31PendingBrokerOrderState,
    Vt31VirtualBasketState,
    Vt31VirtualOrderState,
)

from vt31_nas100_live_policy import evaluate_live_basket

SYMBOL = "NAS100"


def runtime_started_fields() -> dict[str, object]:
    return {
        "vt31_nas100_enabled": True,
        "vt31_nas100_identity": STRATEGY_IDENTITY,
        "vt31_nas100_lineage": "VT31_NAS100",
        "vt31_nas100_provider_symbol": PROVIDER_SYMBOL,
        "vt31_nas100_execution_binding": EXECUTION_BINDING_ID,
        "vt31_nas100_execution_binding_fingerprint": EXECUTION_BINDING_FINGERPRINT,
        "vt31_nas100_strategy_memory_sha256": STRATEGY_MEMORY_FINGERPRINT,
        "vt31_nas100_cibo_memory_sha256": CIBO_MEMORY_FINGERPRINT,
        "vt31_nas100_trader_experience_sha256": TRADER_EXPERIENCE_FINGERPRINT,
        "vt31_nas100_cognitive_memory_sha256": COGNITIVE_MEMORY_FINGERPRINT,
        "vt31_nas100_memory_sha256": COGNITIVE_MEMORY_FINGERPRINT,
        "vt31_nas100_certification_report_sha256": CERTIFICATION_REPORT_SHA256,
        "vt31_nas100_silver_bullet_source_sha256": SILVER_BULLET_SOURCE_FINGERPRINT,
        "vt31_nas100_service_24_7": SERVICE_24_7,
        "vt31_nas100_timeframe": "M1",
        "vt31_nas100_decision_deadline_seconds": str(
            DECISION_DEADLINE.total_seconds()
        ),
        "vt31_nas100_tick_max_age_seconds": str(
            MAX_BROKER_TICK_AGE.total_seconds()
        ),
        "vt31_nas100_boundary_arm_lead_seconds": "10.0",
        "vt31_nas100_feed_refresh_seconds": "1.0",
        "vt31_nas100_boundary_retry_ms": 75,
        "vt31_nas100_history_preload_once": True,
        "vt31_nas100_incremental_cache": True,
        "vt31_nas100_single_position_busy": True,
    }


def evaluate_boundary(
    *,
    closed_m1: tuple[Any, ...],
    evidence_fingerprint: str,
    store: Vt31Nas100LiveStateStore,
) -> tuple[Vt31VirtualBasketState | None, str]:
    state = store.load()
    if state.open_trade is not None:
        return None, "SINGLE_POSITION_BUSY"
    if state.pending_broker_order is not None:
        return None, "BROKER_PENDING_BUSY"
    basket, reason = evaluate_live_basket(
        closed_m1=closed_m1,
        evidence_fingerprint=evidence_fingerprint,
        live_state=state,
    )
    if basket is not None:
        if any(
            item.signal_fingerprint in state.closed_signal_fingerprints
            for item in basket.candidates
        ):
            return None, "SIGNAL_ALREADY_CLOSED"
        store.mark_basket(basket)
    return basket, reason


def shadow_basket(
    *,
    basket: Vt31VirtualBasketState,
    boundary_at: datetime,
    gateway: FundedNextLiveMt5ExecutionGateway,
    risk: DurableAccountWideRiskEngine,
    snapshot: AccountRiskSnapshot,
    account_equity: Decimal,
    store: Vt31Nas100LiveStateStore,
    log: Callable[[dict[str, object]], None],
) -> None:
    for order in basket.candidates:
        _authorize_and_check(
            order=order,
            trigger_at=boundary_at,
            mode="shadow",
            gateway=gateway,
            risk=risk,
            snapshot=snapshot,
            account_equity=account_equity,
            store=store,
            log=log,
        )
    store.clear_virtual_basket()


def submit_single_live(
    *,
    basket: Vt31VirtualBasketState,
    boundary_at: datetime,
    gateway: FundedNextLiveMt5ExecutionGateway,
    risk: DurableAccountWideRiskEngine,
    snapshot: AccountRiskSnapshot,
    account_equity: Decimal,
    store: Vt31Nas100LiveStateStore,
    log: Callable[[dict[str, object]], None],
) -> None:
    if len(basket.candidates) != 1:
        raise Vt31Nas100LiveError(
            "VT31 multi-candidate basket must remain virtual OCO"
        )
    _authorize_and_check(
        order=basket.candidates[0],
        trigger_at=boundary_at,
        mode="live",
        gateway=gateway,
        risk=risk,
        snapshot=snapshot,
        account_equity=account_equity,
        store=store,
        log=log,
    )


def process_virtual_oco(
    *,
    mt5_api: Any,
    now: datetime,
    gateway: FundedNextLiveMt5ExecutionGateway,
    risk: DurableAccountWideRiskEngine,
    snapshot: AccountRiskSnapshot,
    account_equity: Decimal,
    store: Vt31Nas100LiveStateStore,
    log: Callable[[dict[str, object]], None],
) -> None:
    state = store.load()
    basket = state.virtual_basket
    if basket is None or len(basket.candidates) <= 1:
        return
    tick = mt5_api.symbol_info_tick(PROVIDER_SYMBOL)
    if tick is None:
        raise Vt31Nas100LiveError("VT31 OCO broker tick unavailable")
    tick_at = _tick_at(tick)
    candidates = tuple(_virtual_candidate(item) for item in basket.candidates)
    chosen = virtual_oco_trigger(
        candidates,
        bid=Decimal(str(tick.bid)),
        ask=Decimal(str(tick.ask)),
        tick_at=tick_at,
        now=now,
    )
    if chosen is None:
        if all(now > item.expires_at for item in candidates):
            store.clear_virtual_basket()
            log({
                "event": "VT31_NAS100_VIRTUAL_OCO_EXPIRED",
                "basket_id": basket.basket_id,
            })
        return
    raw = next(
        item
        for item in basket.candidates
        if item.candidate_id == chosen.candidate_id
    )
    # The trigger is the new execution boundary for the approved M1 5s profile.
    _authorize_and_check(
        order=raw,
        trigger_at=now,
        mode="live",
        gateway=gateway,
        risk=risk,
        snapshot=snapshot,
        account_equity=account_equity,
        store=store,
        log=log,
    )


def reconcile_pending(
    *,
    mt5_api: Any,
    transport: MetaTrader5FundedNextLiveTransport,
    risk: DurableAccountWideRiskEngine,
    store: Vt31Nas100LiveStateStore,
    now: datetime,
    log: Callable[[dict[str, object]], None],
) -> None:
    state = store.load()
    pending = state.pending_broker_order
    if pending is None:
        return

    positions = mt5_api.positions_get(symbol=PROVIDER_SYMBOL)
    if positions is None:
        raise Vt31Nas100LiveError("VT31 position reconciliation unavailable")
    magic = _magic(pending.client_order_id)
    position = next(
        (
            item
            for item in positions
            if int(getattr(item, "magic", -1)) == magic
        ),
        None,
    )
    if position is not None:
        try:
            risk.record_full_fill(pending.risk_authorization_id)
        except Exception as error:
            # A restart may restore the reservation already in the
            # FILLED_UNRECONCILED state. Do not create a second mutation.
            if "filled-unreconciled" not in str(error).lower():
                raise
        filled_at = _position_time(position, now)
        entry = Decimal(str(position.price_open))
        volume = Decimal(str(position.volume))
        stop = Decimal(str(getattr(position, "sl", pending.stop_loss)))
        if stop <= 0:
            stop = Decimal(pending.stop_loss)
        opened = Vt31OpenTradeState(
            client_order_id=pending.client_order_id,
            signal_fingerprint=pending.signal_fingerprint,
            local_date=pending.local_date,
            tier=pending.tier,
            authorization_reason=pending.authorization_reason,
            family=pending.family,
            side=pending.side,
            filled_at=filled_at.isoformat(),
            entry_price=format(entry, "f"),
            initial_stop=pending.stop_loss,
            current_stop=format(stop, "f"),
            dol1=pending.dol1,
            three_r=pending.three_r,
            requested_risk_r=pending.requested_risk_r,
            initial_volume=format(volume, "f"),
            remaining_volume=format(volume, "f"),
            reference_high=pending.reference_high,
            reference_low=pending.reference_low,
            reference_volatility_state=pending.reference_volatility_state,
            h1_state=pending.h1_state,
            premarket_state=pending.premarket_state,
            cash_open_state=pending.cash_open_state,
            confirmation_latency_minutes=pending.confirmation_latency_minutes,
            risk_ref=pending.risk_ref,
            current_path_vs_previous=pending.current_path_vs_previous,
            rearm_quality=pending.rearm_quality,
            lifecycle_exit_due_at=_lifecycle_exit(pending.local_date).isoformat(),
            target_plan=pending.target_plan,
        )
        store.mark_open(opened)
        log({
            "event": "VT31_NAS100_FILL_CONFIRMED",
            "signal_fingerprint": pending.signal_fingerprint,
            "position_ticket": int(position.ticket),
            "filled_at": filled_at.isoformat(),
        })
        return

    expires = datetime.fromisoformat(pending.expires_at)
    discovered = transport.discover_order(pending.client_order_id)
    if now <= expires:
        if discovered is None:
            raise Vt31Nas100LiveError(
                "VT31 broker pending order missing before expiry"
            )
        if discovered.outcome is Mt5ProviderOutcome.REJECTED:
            risk.cancel(pending.risk_authorization_id)
            store.replace(pending_broker_order=None)
            log({
                "event": "VT31_NAS100_PENDING_REJECTED",
                "signal_fingerprint": pending.signal_fingerprint,
            })
        return

    if pending.provider_order_ref is not None:
        result = transport.cancel_order(
            pending.provider_order_ref,
            client_order_id=pending.client_order_id,
            cancelled_at=now,
        )
        if result.outcome not in {
            Mt5ProviderOutcome.CANCELLED,
            Mt5ProviderOutcome.REJECTED,
        }:
            raise Vt31Nas100LiveError(
                "VT31 expired pending cancellation outcome unresolved"
            )
    risk.cancel(pending.risk_authorization_id)
    store.replace(pending_broker_order=None, virtual_basket=None)
    log({
        "event": "VT31_NAS100_PENDING_EXPIRED",
        "signal_fingerprint": pending.signal_fingerprint,
        "expires_at": pending.expires_at,
    })



def manage_open_trade(
    *,
    mt5_api: Any,
    now: datetime,
    cache: Vt31Nas100M1Cache,
    store: Vt31Nas100LiveStateStore,
    mutations_enabled: bool,
    log: Callable[[dict[str, object]], None],
) -> tuple[object, str]:
    """Manage the frozen V4 target journey without changing admission economics."""
    state = store.load()
    opened = state.open_trade
    if opened is None:
        return state, "no-open-vt31-position"
    if opened.target_plan != TARGET_ARCHITECTURE_ID:
        raise Vt31Nas100LiveError("VT31 live target-plan binding drift")

    positions = mt5_api.positions_get(symbol=SYMBOL)
    if positions is None:
        raise Vt31Nas100LiveError("VT31 journey position snapshot unavailable")
    magic = _magic(opened.client_order_id)
    matches = [
        item for item in positions
        if int(getattr(item, "magic", -1)) == magic
    ]
    if len(matches) > 1:
        raise Vt31Nas100LiveError("VT31 magic resolved to multiple positions")
    if not matches:
        filled_at = datetime.fromisoformat(opened.filled_at)
        deals = mt5_api.history_deals_get(filled_at, now)
        if deals is not None and any(
            int(getattr(item, "magic", -1)) == magic
            and int(getattr(item, "entry", -1))
            != int(getattr(mt5_api, "DEAL_ENTRY_IN", 0))
            for item in deals
        ):
            state = store.mark_closed(
                closed_at=now,
                reason="broker-terminal-reconcile",
            )
            log({
                "event": "VT31_NAS100_POSITION_CLOSED_RECONCILED",
                "signal_fingerprint": opened.signal_fingerprint,
            })
            return state, "broker-terminal-reconciled"
        return state, "vt31-position-awaiting-reconcile"

    position = matches[0]
    tick = mt5_api.symbol_info_tick(PROVIDER_SYMBOL)
    if tick is None:
        raise Vt31Nas100LiveError("VT31 journey tick unavailable")
    tick_at = _tick_at(tick)
    tick_age = now.astimezone(UTC) - tick_at
    if tick_age < timedelta(seconds=-0.5):
        raise Vt31Nas100LiveError("VT31 journey tick is from the future")
    if tick_age > MAX_BROKER_TICK_AGE:
        raise Vt31Nas100LiveError("VT31 journey tick older than 2s")

    info = mt5_api.symbol_info(PROVIDER_SYMBOL)
    if info is None:
        raise Vt31Nas100LiveError("VT31 journey symbol info unavailable")
    step = Decimal(str(info.volume_step))
    tick_size = Decimal(str(info.trade_tick_size))
    actual_volume = Decimal(str(position.volume))
    stored_volume = Decimal(opened.remaining_volume)
    if abs(actual_volume - stored_volume) > step / Decimal("2"):
        raise Vt31Nas100LiveError("VT31 broker volume/state drift")

    entry = Decimal(opened.entry_price)
    initial_stop = Decimal(opened.initial_stop)
    current_stop = Decimal(opened.current_stop)
    dol1 = Decimal(opened.dol1)
    risk = abs(entry - initial_stop)
    if risk <= 0:
        raise Vt31Nas100LiveError("VT31 open trade risk geometry invalid")
    reference_high = Decimal(opened.reference_high)
    reference_low = Decimal(opened.reference_low)
    reference_width = reference_high - reference_low
    if reference_width <= 0:
        raise Vt31Nas100LiveError("VT31 frozen reference width invalid")
    equilibrium = (reference_high + reference_low) / Decimal("2")
    direction = Decimal("1") if opened.side == "long" else Decimal("-1")
    base_partial = entry + direction * risk * Decimal("1.25")
    dol2 = dol1 + direction * reference_width * Decimal("0.25")
    three_r = Decimal(opened.three_r)
    favorable = (
        Decimal(str(tick.bid))
        if opened.side == "long"
        else Decimal(str(tick.ask))
    )
    broker_stop = Decimal(str(position.sl))
    if broker_stop <= 0:
        raise Vt31Nas100LiveError("VT31 broker position has no stop")
    if abs(broker_stop - current_stop) > tick_size:
        raise Vt31Nas100LiveError("VT31 broker stop/state drift")

    lifecycle_due = (
        None
        if opened.lifecycle_exit_due_at is None
        else datetime.fromisoformat(opened.lifecycle_exit_due_at)
    )
    if lifecycle_due is not None and now >= lifecycle_due:
        mutated = _close_position(
            mt5_api,
            position=position,
            volume=actual_volume,
            reason="lifecycle",
            mutations_enabled=mutations_enabled,
        )
        if mutated:
            state = store.mark_closed(
                closed_at=now,
                reason="16:00-lifecycle",
            )
            log({
                "event": "VT31_NAS100_LIFECYCLE_EXIT_ACCEPTED",
                "signal_fingerprint": opened.signal_fingerprint,
            })
            return state, "vt31-16h-lifecycle-exit"
        return state, "vt31-shadow-lifecycle-check-pass"

    # Base BE/runner protection is applied only after its next-M1 arm time.
    if (
        opened.base_partial_arm_after is not None
        and now >= datetime.fromisoformat(opened.base_partial_arm_after)
        and (
            opened.base_partial_done
            or opened.base_three_r_be_armed
        )
        and not opened.base_runner_be_active
    ):
        if _improves_stop(
            side=opened.side,
            previous=broker_stop,
            candidate=entry,
            target=dol2,
        ):
            mutated = _advance_stop(
                mt5_api,
                position=position,
                stop=entry,
                target=dol2,
                mutations_enabled=mutations_enabled,
            )
            if mutated:
                state = store.update_open_trade(
                    current_stop=format(entry, "f"),
                    base_runner_be_active=True,
                )
                opened = state.open_trade
                assert opened is not None
                current_stop = entry
                broker_stop = entry
                log({
                    "event": "VT31_NAS100_BASE_BE_ADVANCED",
                    "signal_fingerprint": opened.signal_fingerprint,
                    "stop": format(entry, "f"),
                })

    # DOL1 acceptance is a physical V4 quarter-leg state.
    if opened.dol1_acceptance_pending:
        if opened.dol1_touch_closed_at is None:
            raise Vt31Nas100LiveError("VT31 DOL1 acceptance clock missing")
        touch_close = datetime.fromisoformat(opened.dol1_touch_closed_at)
        retraced = (
            favorable < dol1
            if opened.side == "long"
            else favorable > dol1
        )
        if now < touch_close and retraced:
            mutated = _close_position(
                mt5_api,
                position=position,
                volume=actual_volume,
                reason="dol1-retrace",
                mutations_enabled=mutations_enabled,
            )
            if mutated:
                state = store.mark_closed(
                    closed_at=now,
                    reason="dol1-nonaccept-retrace",
                )
                log({
                    "event": "VT31_NAS100_DOL1_NONACCEPT_RETRACE_EXIT",
                    "signal_fingerprint": opened.signal_fingerprint,
                })
                return state, "vt31-dol1-nonaccept-retrace"
            return state, "vt31-shadow-dol1-retrace-check-pass"

        if now >= touch_close:
            bar = next(
                (
                    item
                    for item in cache.closed_m1(through=now)
                    if item.closed_at == touch_close
                ),
                None,
            )
            if bar is None:
                raise Vt31Nas100LiveError(
                    "VT31 DOL1 touch M1 unavailable at acceptance boundary"
                )
            accepts = (
                Decimal(str(bar.close)) >= dol1
                if opened.side == "long"
                else Decimal(str(bar.close)) <= dol1
            )
            if accepts:
                state = store.update_open_trade(
                    dol1_acceptance_pending=False,
                    runner_active=True,
                    runner_target=format(dol2, "f"),
                )
                opened = state.open_trade
                assert opened is not None
                log({
                    "event": "VT31_NAS100_DOL1_ACCEPTED_RUNNER_ACTIVE",
                    "signal_fingerprint": opened.signal_fingerprint,
                    "runner_target": format(dol2, "f"),
                })
            else:
                mutated = _close_position(
                    mt5_api,
                    position=position,
                    volume=actual_volume,
                    reason="dol1-nonaccept",
                    mutations_enabled=mutations_enabled,
                )
                if mutated:
                    state = store.mark_closed(
                        closed_at=now,
                        reason="dol1-nonaccept-close",
                    )
                    log({
                        "event": "VT31_NAS100_DOL1_NONACCEPT_CLOSE",
                        "signal_fingerprint": opened.signal_fingerprint,
                    })
                    return state, "vt31-dol1-nonaccept-close"
                return state, "vt31-shadow-dol1-nonaccept-check-pass"

    state = store.load()
    opened = state.open_trade
    if opened is None:
        return state, "vt31-closed"
    if opened.runner_active:
        runner_target = (
            dol2
            if opened.runner_target is None
            else Decimal(opened.runner_target)
        )
        candidate, confirmations = _ps2_candidate(
            cache.closed_m1(through=now),
            opened=opened,
            target=runner_target,
        )
        if confirmations != opened.ps_confirmations:
            state = store.update_open_trade(ps_confirmations=confirmations)
            opened = state.open_trade
            assert opened is not None
        if (
            candidate is not None
            and _improves_stop(
                side=opened.side,
                previous=Decimal(opened.current_stop),
                candidate=candidate,
                target=runner_target,
            )
        ):
            mutated = _advance_stop(
                mt5_api,
                position=position,
                stop=candidate,
                target=runner_target,
                mutations_enabled=mutations_enabled,
            )
            if mutated:
                state = store.update_open_trade(
                    current_stop=format(candidate, "f"),
                    breaker_lock_armed=True,
                    ps_confirmations=max(2, confirmations),
                )
                log({
                    "event": "VT31_NAS100_PS2_STOP_ADVANCED",
                    "signal_fingerprint": opened.signal_fingerprint,
                    "stop": format(candidate, "f"),
                })
                return state, f"vt31-ps2-stop-advanced:{candidate}"
        return state, "vt31-runner-hold"

    # Once EQ wins the physical precedence race, V4 owns the remainder.
    if opened.equilibrium_overlay_active:
        if _target_reached(opened.side, favorable, dol1):
            compressed = (
                opened.reference_volatility_state.lower() == "compressed"
            )
            if compressed:
                leg = _leg_volume(
                    Decimal(opened.initial_volume),
                    Decimal("0.25"),
                    step,
                )
                if leg <= 0 or leg >= actual_volume:
                    raise Vt31Nas100LiveError(
                        "VT31 DOL1 quarter leg cannot be expressed"
                    )
                mutated = _close_position(
                    mt5_api,
                    position=position,
                    volume=leg,
                    reason="dol1-bank",
                    mutations_enabled=mutations_enabled,
                )
                if mutated:
                    arm_close = _m1_close_after(now)
                    remaining = actual_volume - leg
                    state = store.update_open_trade(
                        remaining_volume=format(remaining, "f"),
                        dol1_bank_done=True,
                        dol1_acceptance_pending=True,
                        dol1_touch_closed_at=arm_close.isoformat(),
                    )
                    log({
                        "event": "VT31_NAS100_DOL1_QUARTER_BANKED",
                        "signal_fingerprint": opened.signal_fingerprint,
                        "remaining_volume": format(remaining, "f"),
                        "acceptance_at": arm_close.isoformat(),
                    })
                    return state, "vt31-dol1-quarter-banked"
                return state, "vt31-shadow-dol1-quarter-check-pass"

            mutated = _close_position(
                mt5_api,
                position=position,
                volume=actual_volume,
                reason="dol1-full-remainder",
                mutations_enabled=mutations_enabled,
            )
            if mutated:
                state = store.mark_closed(
                    closed_at=now,
                    reason="eq50-dol1-full-remainder",
                )
                log({
                    "event": "VT31_NAS100_DOL1_FULL_REMAINDER_EXIT",
                    "signal_fingerprint": opened.signal_fingerprint,
                })
                return state, "vt31-dol1-full-remainder"
            return state, "vt31-shadow-dol1-full-check-pass"
        return state, "vt31-eq-overlay-hold"

    eq_forward = (
        equilibrium > entry
        if opened.side == "long"
        else equilibrium < entry
    )
    eq_hit = (
        eq_forward
        and _target_reached(opened.side, favorable, equilibrium)
    )
    partial_hit = _target_reached(opened.side, favorable, base_partial)
    dol1_hit = _target_reached(opened.side, favorable, dol1)
    noncompressed = opened.reference_volatility_state.lower() != "compressed"

    # Frozen V2/V4 precedence: CORE non-compressed base partial wins a
    # simultaneous observation; only an earlier EQ observation may reallocate.
    if (
        opened.tier == "CORE"
        and noncompressed
        and not opened.base_partial_done
    ):
        if partial_hit:
            leg = _leg_volume(
                Decimal(opened.initial_volume),
                Decimal("0.50"),
                step,
            )
            if leg <= 0 or leg >= actual_volume:
                if dol1_hit:
                    mutated = _close_position(
                        mt5_api,
                        position=position,
                        volume=actual_volume,
                        reason="base-dol1",
                        mutations_enabled=mutations_enabled,
                    )
                    if mutated:
                        return (
                            store.mark_closed(
                                closed_at=now,
                                reason="base-dol1-full",
                            ),
                            "vt31-base-dol1-full",
                        )
                raise Vt31Nas100LiveError(
                    "VT31 base partial cannot be expressed"
                )
            mutated = _close_position(
                mt5_api,
                position=position,
                volume=leg,
                reason="base-1p25",
                mutations_enabled=mutations_enabled,
            )
            if mutated:
                remaining = actual_volume - leg
                state = store.update_open_trade(
                    remaining_volume=format(remaining, "f"),
                    base_partial_done=True,
                    base_partial_first=True,
                    base_partial_arm_after=_m1_close_after(now).isoformat(),
                )
                log({
                    "event": "VT31_NAS100_BASE_PARTIAL_BANKED",
                    "signal_fingerprint": opened.signal_fingerprint,
                    "remaining_volume": format(remaining, "f"),
                })
                return state, "vt31-base-partial-first"
            return state, "vt31-shadow-base-partial-check-pass"
        if eq_hit:
            return _bank_equilibrium(
                mt5_api=mt5_api,
                position=position,
                opened=opened,
                store=store,
                step=step,
                now=now,
                mutations_enabled=mutations_enabled,
                log=log,
            )

    elif eq_hit:
        return _bank_equilibrium(
            mt5_api=mt5_api,
            position=position,
            opened=opened,
            store=store,
            step=step,
            now=now,
            mutations_enabled=mutations_enabled,
            log=log,
        )

    state = store.load()
    opened = state.open_trade
    if opened is None:
        return state, "vt31-closed"

    if opened.base_partial_done:
        if dol1_hit:
            mutated = _close_position(
                mt5_api,
                position=position,
                volume=actual_volume,
                reason="base-dol1-runner",
                mutations_enabled=mutations_enabled,
            )
            if mutated:
                return (
                    store.mark_closed(
                        closed_at=now,
                        reason="base-dol1-runner",
                    ),
                    "vt31-base-dol1-runner",
                )
            return state, "vt31-shadow-base-dol1-check-pass"
        return state, "vt31-base-runner-hold"

    if dol1_hit:
        mutated = _close_position(
            mt5_api,
            position=position,
            volume=actual_volume,
            reason="base-dol1",
            mutations_enabled=mutations_enabled,
        )
        if mutated:
            return (
                store.mark_closed(
                    closed_at=now,
                    reason="base-dol1",
                ),
                "vt31-base-dol1",
            )
        return state, "vt31-shadow-base-dol1-check-pass"

    if (
        not noncompressed
        and not opened.base_three_r_be_armed
        and _target_reached(opened.side, favorable, three_r)
    ):
        state = store.update_open_trade(
            base_three_r_be_armed=True,
            base_partial_arm_after=_m1_close_after(now).isoformat(),
        )
        return state, "vt31-base-3r-be-armed"

    return state, "vt31-journey-hold"


def _bank_equilibrium(
    *,
    mt5_api: Any,
    position: Any,
    opened: Vt31OpenTradeState,
    store: Vt31Nas100LiveStateStore,
    step: Decimal,
    now: datetime,
    mutations_enabled: bool,
    log: Callable[[dict[str, object]], None],
) -> tuple[object, str]:
    actual = Decimal(str(position.volume))
    leg = _leg_volume(
        Decimal(opened.initial_volume),
        Decimal("0.50"),
        step,
    )
    if leg <= 0 or leg >= actual:
        raise Vt31Nas100LiveError("VT31 EQ50 leg cannot be expressed")
    mutated = _close_position(
        mt5_api,
        position=position,
        volume=leg,
        reason="eq50",
        mutations_enabled=mutations_enabled,
    )
    if not mutated:
        return store.load(), "vt31-shadow-eq50-check-pass"
    remaining = actual - leg
    state = store.update_open_trade(
        remaining_volume=format(remaining, "f"),
        equilibrium_bank_done=True,
        equilibrium_overlay_active=True,
    )
    log({
        "event": "VT31_NAS100_EQ50_BANKED",
        "signal_fingerprint": opened.signal_fingerprint,
        "remaining_volume": format(remaining, "f"),
    })
    return state, "vt31-eq50-banked"


def _target_reached(side: str, price: Decimal, level: Decimal) -> bool:
    return price >= level if side == "long" else price <= level


def _improves_stop(
    *,
    side: str,
    previous: Decimal,
    candidate: Decimal,
    target: Decimal,
) -> bool:
    if side == "long":
        return previous < candidate < target
    return target < candidate < previous


def _leg_volume(
    initial_volume: Decimal,
    fraction: Decimal,
    step: Decimal,
) -> Decimal:
    if step <= 0:
        raise Vt31Nas100LiveError("VT31 broker volume step invalid")
    raw = initial_volume * fraction
    units = (raw / step).to_integral_value(rounding=ROUND_FLOOR)
    return units * step


def _m1_close_after(now: datetime) -> datetime:
    current = now.astimezone(UTC)
    return current.replace(second=0, microsecond=0) + timedelta(minutes=1)


def _close_position(
    api: Any,
    *,
    position: Any,
    volume: Decimal,
    reason: str,
    mutations_enabled: bool,
) -> bool:
    if volume <= 0:
        raise Vt31Nas100LiveError("VT31 close volume must be positive")
    tick = api.symbol_info_tick(SYMBOL)
    if tick is None:
        raise Vt31Nas100LiveError("VT31 close tick unavailable")
    closing_buy = int(position.type) != int(api.POSITION_TYPE_BUY)
    request = {
        "action": api.TRADE_ACTION_DEAL,
        "symbol": PROVIDER_SYMBOL,
        "position": int(position.ticket),
        "volume": float(volume),
        "type": api.ORDER_TYPE_BUY if closing_buy else api.ORDER_TYPE_SELL,
        "price": float(tick.ask if closing_buy else tick.bid),
        "magic": int(position.magic),
        "type_time": api.ORDER_TIME_GTC,
        "type_filling": _filling(api),
        "comment": f"qore-vt31-{reason}-{int(position.ticket)}"[:29],
    }
    checked = api.order_check(request)
    if checked is None or int(checked.retcode) != 0:
        raise Vt31Nas100LiveError(
            f"VT31 {reason} order_check rejected"
        )
    if not mutations_enabled:
        return False
    result = api.order_send(request)
    accepted = {
        int(api.TRADE_RETCODE_DONE),
        int(api.TRADE_RETCODE_DONE_PARTIAL),
        int(api.TRADE_RETCODE_PLACED),
    }
    if result is None or int(result.retcode) not in accepted:
        raise Vt31Nas100LiveError(f"VT31 {reason} close rejected")
    return True


def _advance_stop(
    api: Any,
    *,
    position: Any,
    stop: Decimal,
    target: Decimal,
    mutations_enabled: bool,
) -> bool:
    request = {
        "action": api.TRADE_ACTION_SLTP,
        "symbol": SYMBOL,
        "position": int(position.ticket),
        "sl": float(stop),
        "tp": float(target),
        "magic": int(position.magic),
        "comment": f"qore-vt31-stop-{int(position.ticket)}"[:29],
    }
    checked = api.order_check(request)
    if checked is None or int(checked.retcode) != 0:
        raise Vt31Nas100LiveError("VT31 stop modification order_check rejected")
    if not mutations_enabled:
        return False
    result = api.order_send(request)
    if result is None or int(result.retcode) not in {
        int(api.TRADE_RETCODE_DONE),
        int(api.TRADE_RETCODE_PLACED),
    }:
        raise Vt31Nas100LiveError("VT31 stop modification rejected")
    return True


def _filling(api: Any) -> int:
    info = api.symbol_info(PROVIDER_SYMBOL)
    if info is None:
        raise Vt31Nas100LiveError("VT31 filling policy unavailable")
    mode = int(info.filling_mode)
    if mode & 2:
        return int(api.ORDER_FILLING_IOC)
    if mode & 1:
        return int(api.ORDER_FILLING_FOK)
    if int(info.trade_exemode) != int(api.SYMBOL_TRADE_EXECUTION_MARKET):
        return int(api.ORDER_FILLING_RETURN)
    raise Vt31Nas100LiveError("VT31 filling policy unavailable")


def _ps2_candidate(
    bars: tuple[Any, ...],
    *,
    opened: Vt31OpenTradeState,
    target: Decimal,
) -> tuple[Decimal | None, int]:
    if opened.dol1_touch_closed_at is None:
        return None, opened.ps_confirmations
    start = datetime.fromisoformat(opened.dol1_touch_closed_at)
    path = [
        bar
        for bar in bars
        if bar.closed_at >= start
    ]
    if len(path) < 3:
        return None, 0
    working = Decimal(opened.initial_stop)
    confirmations = 0
    selected: Decimal | None = None
    for index in range(2, len(path)):
        left = path[index - 2]
        middle = path[index - 1]
        right = path[index]
        if opened.side == "long":
            candidate = Decimal(str(middle.low))
            valid = (
                candidate < Decimal(str(left.low))
                and candidate < Decimal(str(right.low))
            )
        else:
            candidate = Decimal(str(middle.high))
            valid = (
                candidate > Decimal(str(left.high))
                and candidate > Decimal(str(right.high))
            )
        if not valid:
            continue
        if _improves_stop(
            side=opened.side,
            previous=working,
            candidate=candidate,
            target=target,
        ):
            confirmations += 1
            if confirmations >= 2:
                selected = candidate
                break
    return selected, confirmations


def _authorize_and_check(
    *,
    order: Vt31VirtualOrderState,
    trigger_at: datetime,
    mode: str,
    gateway: FundedNextLiveMt5ExecutionGateway,
    risk: DurableAccountWideRiskEngine,
    snapshot: AccountRiskSnapshot,
    account_equity: Decimal,
    store: Vt31Nas100LiveStateStore,
    log: Callable[[dict[str, object]], None],
) -> None:
    trigger_at = trigger_at.astimezone(UTC)
    expires_at = datetime.fromisoformat(order.expires_at)
    def stage(stage_name: str) -> datetime:
        observed = datetime.now(UTC)
        assert_deadline(anchor=trigger_at, now=observed, stage=stage_name)
        return observed

    spec_at = stage("before-symbol-read")
    spec = gateway.read_symbol(SYMBOL, now=spec_at)
    context = Vt31RiskContext(
        tier=order.tier,
        entry_family=order.family,
        side=order.side,
        nominal_risk_r=Decimal(order.nominal_risk_r),
        h1_state=order.h1_state,
        premarket_state=order.premarket_state,
        cash_open_state=order.cash_open_state,
        confirmation_latency_minutes=order.confirmation_latency_minutes,
        risk_ref=None if order.risk_ref is None else Decimal(order.risk_ref),
        current_path_vs_previous=(
            None
            if order.current_path_vs_previous is None
            else Decimal(order.current_path_vs_previous)
        ),
    )
    resolution = resolve_certified_risk(context)
    request_at = stage("before-risk-request")
    request, _one_r = build_risk_request(
        request_id=f"vt31-{order.signal_fingerprint[:24]}",
        signal_fingerprint=order.signal_fingerprint,
        side=order.side,
        entry=Decimal(order.entry_price),
        stop_loss=Decimal(order.stop_loss),
        take_profit=_broker_guard_target(order),
        certified_risk_r=resolution.final_risk_r,
        provider_spec=spec,
        account_equity=account_equity,
        decision_anchor=trigger_at,
        reservation_expires_at=expires_at,
        now=request_at,
    )
    auth_at = stage("before-account-wide-risk")
    if risk.recovery_required:
        risk.complete_boot_reconciliation(snapshot, now=auth_at)
    authorization = risk.authorize(request, snapshot, now=auth_at)
    if authorization.decision is RiskDecision.REJECT:
        log({
            "event": "VT31_NAS100_RISK_REJECT",
            "signal_fingerprint": order.signal_fingerprint,
            "reason": authorization.reason,
        })
        return

    submission_at = stage("before-submission-build")
    submission = build_account_bound_submission(
        authorization,
        switch=ExecutionSafetySwitchSnapshot(
            state=ExecutionSwitchState.ENABLED,
            observed_at=submission_at,
            reason="qore VT31 NAS100 certified runtime safety gate enabled",
        ),
        authorized_at=submission_at,
        submitted_at=submission_at,
    )
    check_at = stage("before-broker-order-check")
    shadow = gateway.shadow_check(submission, now=check_at)
    checked_at = stage("after-broker-order-check")
    if not shadow.broker_valid:
        risk.cancel(authorization.authorization_id)
        log({
            "event": "VT31_NAS100_SHADOW_REJECT",
            "signal_fingerprint": order.signal_fingerprint,
            "reason": shadow.reason,
        })
        return

    common = {
        "signal_fingerprint": order.signal_fingerprint,
        "tier": order.tier,
        "family": order.family,
        "side": order.side,
        "target_plan": order.target_plan,
        "risk_r": str(resolution.final_risk_r),
        "risk_usd": str(authorization.monetary_stop_loss),
        "volume": str(authorization.authorized_volume),
        "latency_ms": int((checked_at - trigger_at).total_seconds() * 1000),
        "decision_deadline_ms": int(DECISION_DEADLINE.total_seconds() * 1000),
    }
    if mode == "shadow":
        risk.cancel(authorization.authorization_id)
        log({"event": "VT31_NAS100_SHADOW_PASS", **common})
        return
    if mode != "live":
        risk.cancel(authorization.authorization_id)
        raise ValueError("VT31 runtime mode must be shadow or live")

    send_at = stage("before-order-send")
    provider_ref = gateway.submit_live(submission, now=send_at)
    client_order_id = f"qore-{submission.idempotency_key.value.hex[:24]}"
    pending = Vt31PendingBrokerOrderState(
        client_order_id=client_order_id,
        risk_authorization_id=authorization.authorization_id,
        signal_fingerprint=order.signal_fingerprint,
        local_date=order.local_date,
        tier=order.tier,
        authorization_reason=order.authorization_reason,
        family=order.family,
        side=order.side,
        decision_at=order.decision_at,
        trigger_at=trigger_at.isoformat(),
        expires_at=order.expires_at,
        entry_price=order.entry_price,
        stop_loss=order.stop_loss,
        dol1=order.dol1,
        three_r=order.three_r,
        requested_risk_r=format(resolution.final_risk_r, "f"),
        authorized_volume=str(authorization.authorized_volume),
        reference_high=order.reference_high,
        reference_low=order.reference_low,
        reference_volatility_state=order.reference_volatility_state,
        h1_state=order.h1_state,
        premarket_state=order.premarket_state,
        cash_open_state=order.cash_open_state,
        confirmation_latency_minutes=order.confirmation_latency_minutes,
        risk_ref=order.risk_ref,
        current_path_vs_previous=order.current_path_vs_previous,
        rearm_quality=order.rearm_quality,
        target_plan=order.target_plan,
        provider_order_ref=provider_ref,
    )
    store.mark_pending(pending)
    log({
        "event": "VT31_NAS100_LIVE_SUBMIT_ACCEPTED",
        **common,
        "risk_authorization": authorization.authorization_id,
        "provider_order_ref": provider_ref,
        "order_send_started_at": send_at.isoformat(),
        "send_started_latency_ms": int(
            (send_at - trigger_at).total_seconds() * 1000
        ),
    })


def _broker_guard_target(order: Vt31VirtualOrderState) -> Decimal:
    """Maximum certified route used only as the broker-side emergency TP."""
    dol1 = Decimal(order.dol1)
    width = Decimal(order.reference_high) - Decimal(order.reference_low)
    if width <= 0:
        raise Vt31Nas100LiveError("VT31 frozen reference width invalid")
    direction = Decimal("1") if order.side == "long" else Decimal("-1")
    return dol1 + direction * width * Decimal("0.25")


def _virtual_candidate(order: Vt31VirtualOrderState) -> Vt31VirtualCandidate:
    return Vt31VirtualCandidate(
        candidate_id=order.candidate_id,
        signal_fingerprint=order.signal_fingerprint,
        side=order.side,
        family=order.family,
        formed_at=datetime.fromisoformat(order.formed_at),
        decision_at=datetime.fromisoformat(order.decision_at),
        expires_at=datetime.fromisoformat(order.expires_at),
        entry_price=Decimal(order.entry_price),
        stop_loss=Decimal(order.stop_loss),
        take_profit=Decimal(order.dol1),
    )


def _magic(client_order_id: str) -> int:
    digest = hashlib.sha256(client_order_id.encode("utf-8")).digest()
    return int.from_bytes(digest[:4], "big") & 0x7FFFFFFF


def _tick_at(tick: Any) -> datetime:
    raw_msc = int(getattr(tick, "time_msc", 0) or 0)
    if raw_msc > 0:
        raw_seconds, millis = divmod(raw_msc, 1000)
        return normalise_fundednext_server_epoch(raw_seconds) + timedelta(
            milliseconds=millis
        )
    raw = int(getattr(tick, "time", 0) or 0)
    if raw <= 0:
        raise Vt31Nas100LiveError("VT31 broker tick timestamp unavailable")
    return normalise_fundednext_server_epoch(raw)


def _position_time(position: Any, fallback: datetime) -> datetime:
    raw_msc = int(getattr(position, "time_msc", 0) or 0)
    if raw_msc > 0:
        raw_seconds, millis = divmod(raw_msc, 1000)
        return normalise_fundednext_server_epoch(raw_seconds) + timedelta(
            milliseconds=millis
        )
    raw = int(getattr(position, "time", 0) or 0)
    if raw > 0:
        return normalise_fundednext_server_epoch(raw)
    return fallback.astimezone(UTC)


def _lifecycle_exit(local_date: str) -> datetime:
    from zoneinfo import ZoneInfo

    day = datetime.fromisoformat(local_date)
    ny = ZoneInfo("America/New_York")
    local = datetime(day.year, day.month, day.day, 16, 0, tzinfo=ny)
    return local.astimezone(UTC)
