"""Resident VT31 NAS100 adapter for the single-writer FundedNext runtime.

The certified strategy is not recalibrated here. This adapter owns only:
- M1 cache/boundary orchestration;
- Account-Wide Risk authorization;
- broker order_check / canonical submission;
- durable virtual basket and broker-pending state;
- fill reconciliation.

Target/journey management is deliberately separate from admission.
"""
# ruff: noqa: I001
from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from decimal import Decimal
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
    SERVICE_24_7,
    SILVER_BULLET_SOURCE_FINGERPRINT,
    STRATEGY_IDENTITY,
    STRATEGY_MEMORY_FINGERPRINT,
    TRADER_EXPERIENCE_FINGERPRINT,
    Vt31Nas100LiveError,
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
    tick = mt5_api.symbol_info_tick(SYMBOL)
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

    positions = mt5_api.positions_get(symbol=SYMBOL)
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
        take_profit=Decimal(order.dol1),
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
        return datetime.fromtimestamp(raw_msc / 1000, tz=UTC)
    raw = int(getattr(tick, "time", 0) or 0)
    if raw <= 0:
        raise Vt31Nas100LiveError("VT31 broker tick timestamp unavailable")
    return datetime.fromtimestamp(raw, tz=UTC)


def _position_time(position: Any, fallback: datetime) -> datetime:
    raw_msc = int(getattr(position, "time_msc", 0) or 0)
    if raw_msc > 0:
        return datetime.fromtimestamp(raw_msc / 1000, tz=UTC)
    raw = int(getattr(position, "time", 0) or 0)
    if raw > 0:
        return datetime.fromtimestamp(raw, tz=UTC)
    return fallback.astimezone(UTC)


def _lifecycle_exit(local_date: str) -> datetime:
    from zoneinfo import ZoneInfo

    day = datetime.fromisoformat(local_date)
    ny = ZoneInfo("America/New_York")
    local = datetime(day.year, day.month, day.day, 16, 0, tzinfo=ny)
    return local.astimezone(UTC)
