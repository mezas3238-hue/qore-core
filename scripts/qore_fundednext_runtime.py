"""Resident QORE FundedNext runtime for all certified live adapters.

The VPS/MT5 installation is assumed to exist already. This is the single-writer
24/7 execution loop. VT08 evaluates 01:00/05:00/09:00 New York anchors; Turtle
Soup XAUUSD R34, EURUSD R38, GBPUSD R43 and GBPJPY R38 evaluate every New York
H1/H4 boundary using broker-to-UTC normalization. Sovereign Account-Wide Risk
remains above all traders.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import time
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path

import MetaTrader5 as mt5  # type: ignore

from qore.infrastructure.account_wide_risk import (
    AccountRiskSnapshot,
    ReservationState,
    RiskDecision,
    TraderLineage,
)
from qore.infrastructure.account_wide_risk_ledger import (
    DurableAccountWideRiskEngine,
    DurableAccountWideRiskLedger,
)
from qore.infrastructure.fundednext_live_activation import load_verified_live_activation
from qore.infrastructure.fundednext_live_guard import (
    LIVE_ENTRY_ANCHORS_NY,
    FOREX_OPEN_COMMISSION_PER_LOT_USD,
    DurableFundedNextLiveCapitalStore,
    FundedNextLiveCapitalCheckpoint,
    InactivityState,
    causal_daily_candidate_allowed,
    h4_containment_exit_at,
    inactivity_state,
)
from qore.infrastructure.fundednext_live_mt5 import (
    FundedNextLiveMt5ExecutionGateway,
    MetaTrader5FundedNextLiveTransport,
)
from qore.infrastructure.fundednext_mt5_clock import (
    NEW_YORK_TZ,
    normalise_fundednext_server_epoch,
)
from qore.infrastructure.fundednext_realtime_market_data import (
    MARKET_DATA_SLA_SECONDS,
    FundedNextRealtimeMarketData,
    MarketDataSlaError,
)
from qore.infrastructure.fundednext_vt08_realtime_market_data import (
    vt08_boundary_ready as _vt08_boundary_ready,
)
from qore.infrastructure.fundednext_rule_refresh import RollingStellarInstantRuleVerification
from qore.infrastructure.fundednext_live_safety import (
    JsonFileLiveOperationalSafetyBoundary,
    load_live_safety_state,
)
from qore.infrastructure.fundednext_mt5_mutation_ledger import (
    FundedNextMt5MutationState,
    JsonFileFundedNextMt5MutationLedger,
)
from qore.infrastructure.fundednext_operational import build_account_bound_submission
from qore.infrastructure.fundednext_operational_risk_policy import (
    CapitalBudgetDecision,
    QoreOperationalCapitalBudget,
    evaluate_qore_operational_capital_budget,
)
from qore.infrastructure.fundednext_position_exit_ledger import (
    JsonFileFundedNextPositionExitLedger,
    PositionExitRecord,
    PositionExitState,
)
from qore.infrastructure.fundednext_runtime_pipeline import (
    cibo_setup_from_b01,
    request_cibo_posture,
)
from qore.infrastructure.fundednext_runtime_state import (
    DurableFundedNextRuntimeStateStore,
    FundedNextRuntimeState,
    SingleWriterRuntimeLock,
)
from qore.infrastructure.fundednext_stellar_instant import (
    PILOT_INITIAL_BALANCE,
    StellarInstantAccountSnapshot,
    StellarInstantRiskBudget,
    evaluate_stellar_instant_budget,
)
from qore.infrastructure.market_test_environment import (
    MarketRuntimeEnvironment,
    MarketTestAccountIdentity,
)
from qore.infrastructure.pretrade_safety import (
    ExecutionSafetySwitchSnapshot,
    ExecutionSwitchState,
)
from qore.infrastructure.r34_xauusd_live import (
    HISTORY_M5_BARS as R34_HISTORY_M5_BARS,
    R34LiveSignal,
    R34LiveStateStore,
    build_live_signal as build_r34_live_signal,
    build_r34_risk_request,
    current_anchor as current_r34_anchor,
    load_cognitive as load_r34_cognitive,
)
from qore.infrastructure.r38_eurusd_live import (
    HISTORY_M5_BARS as R38_HISTORY_M5_BARS,
    R38LiveSignal,
    R38LiveStateStore,
    build_live_signal as build_r38_live_signal,
    build_r38_risk_request,
    current_anchor as current_r38_anchor,
    load_cognitive as load_r38_cognitive,
    manage_open_position as manage_r38_open_position,
)
from qore.infrastructure.r43_gbpusd_live import (
    HISTORY_M5_BARS as R43_HISTORY_M5_BARS,
    R43LiveSignal,
    R43LiveStateStore,
    build_live_signal as build_r43_live_signal,
    build_r43_risk_request,
    current_anchor as current_r43_anchor,
    load_memory as load_r43_memory,
    manage_open_position as manage_r43_open_position,
)
from qore.infrastructure.r38_gbpjpy_live import (
    HISTORY_M5_BARS as GBPJPY_R38_HISTORY_M5_BARS,
    R38GbpJpyLiveSignal,
    R38GbpJpyLiveStateStore,
    build_live_signal as build_gbpjpy_r38_live_signal,
    build_r38_gbpjpy_risk_request,
    current_anchor as current_gbpjpy_r38_anchor,
    load_memory as load_gbpjpy_r38_memory,
    manage_open_position as manage_gbpjpy_r38_open_position,
)
from qore.infrastructure.traders.vt08_b01_r3_8 import (
    OWNER_FOREX_ENTRY_ANCHORS,
    Vt08B01Bar,
    Vt08B01Candidate,
    evaluate_b01_at_entry,
)
from qore.infrastructure.vt08_forex_cibo_operational import (
    Vt08ForexCiboDecision,
    evaluate_vt08_forex_cibo,
)
from qore.infrastructure.vt08_forex_fundednext_sizing import (
    build_certified_vt08_forex_cibo_request,
)

_NY = NEW_YORK_TZ
_MARKETS = ("AUDJPY", "GBPUSD", "GBPJPY")
_EXCLUDED_LEGACY_TRADERS = ("VT09",)
_EXPECTED_SERVER = "FundedNext-Server"
_ACCOUNT_REF = "fundednext-stellar-instant-live"
_IDLE_LOOP_SECONDS = 1.0
_BOUNDARY_ARM_SECONDS = 10.0
_BOUNDARY_POLL_SECONDS = 0.10
_ANCHOR_GRACE = timedelta(seconds=2)
_HISTORY_DAYS = 14
_HISTORY_M15_BARS = _HISTORY_DAYS * 24 * 4 + 96
_DISCOVERY_DAYS = 7


def _arm_to_hour_boundary(now: datetime) -> datetime:
    """Wake on the H1 boundary before any slower reconciliation work begins."""
    observed = now.astimezone(UTC)
    top = observed.replace(minute=0, second=0, microsecond=0)
    if (observed - top).total_seconds() <= MARKET_DATA_SLA_SECONDS:
        return observed
    next_top = top + timedelta(hours=1)
    until_top = (next_top - observed).total_seconds()
    if 0 < until_top <= _BOUNDARY_ARM_SECONDS:
        time.sleep(until_top)
        return datetime.now(UTC)
    return observed


def _runtime_sleep_seconds(now: datetime) -> float:
    """Sleep coarsely off-boundary and arm at 100 ms around each H1 boundary."""
    observed = now.astimezone(UTC)
    top = observed.replace(minute=0, second=0, microsecond=0)
    since_top = (observed - top).total_seconds()
    if since_top <= MARKET_DATA_SLA_SECONDS:
        return _BOUNDARY_POLL_SECONDS
    next_top = top + timedelta(hours=1)
    until_top = (next_top - observed).total_seconds()
    if until_top <= _BOUNDARY_ARM_SECONDS:
        return _BOUNDARY_POLL_SECONDS
    return min(
        _IDLE_LOOP_SECONDS,
        max(_BOUNDARY_POLL_SECONDS, until_top - 1.0),
    )


def _git_sha(root: Path) -> str:
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    )
    value = result.stdout.strip()
    if len(value) != 40:
        raise RuntimeError("runtime-git-sha-invalid")
    return value


def _account_fingerprint(account: object) -> str:
    material = "|".join(
        (
            str(getattr(account, "login")),
            str(getattr(account, "server")),
            str(getattr(account, "company")),
            str(getattr(account, "currency")),
        )
    )
    return hashlib.sha256(material.encode("utf-8")).hexdigest()


def _magic(client_order_id: str) -> int:
    digest = hashlib.sha256(client_order_id.encode("utf-8")).digest()
    return int.from_bytes(digest[:4], "big") & 0x7FFFFFFF


def _m15_bars(symbol: str, decision_at: datetime) -> tuple[Vt08B01Bar, ...]:
    """Read broker M15 and normalize FundedNext server time before VT08 sees it."""
    start = decision_at - timedelta(days=_HISTORY_DAYS)
    end = decision_at + timedelta(minutes=1)
    rows = mt5.copy_rates_from_pos(
        symbol,
        mt5.TIMEFRAME_M15,
        0,
        _HISTORY_M15_BARS,
    )
    if rows is None or len(rows) == 0:
        raise RuntimeError(f"m15-data-unavailable-{symbol}")
    retained: dict[datetime, Vt08B01Bar] = {}
    for row in rows:
        opened = normalise_fundednext_server_epoch(int(row["time"]))
        if opened < start or opened > end:
            continue
        bar = Vt08B01Bar(
            opened_at=opened,
            closed_at=opened + timedelta(minutes=15),
            open=Decimal(str(row["open"])),
            high=Decimal(str(row["high"])),
            low=Decimal(str(row["low"])),
            close=Decimal(str(row["close"])),
        )
        prior = retained.get(opened)
        if prior is not None and prior != bar:
            raise RuntimeError(f"contradictory-m15-bar-{symbol}")
        retained[opened] = bar
    bars = tuple(retained[key] for key in sorted(retained))
    if not bars:
        raise RuntimeError(f"m15-data-unavailable-after-clock-normalization-{symbol}")
    expected_current = decision_at.astimezone(UTC)
    expected_closed = expected_current - timedelta(minutes=15)
    if expected_current not in retained:
        raise RuntimeError(f"vt08-current-m15-unavailable-{symbol}")
    if expected_closed not in retained:
        raise RuntimeError(f"vt08-latest-closed-m15-unavailable-{symbol}")
    return bars


def _current_anchor(now: datetime) -> datetime | None:
    local = now.astimezone(_NY)
    if local.hour not in LIVE_ENTRY_ANCHORS_NY:
        return None
    anchor = local.replace(minute=0, second=0, microsecond=0).astimezone(UTC)
    current = now.astimezone(UTC)
    if current < anchor or current - anchor > _ANCHOR_GRACE:
        return None
    return anchor


def _causal_candidate(symbol: str, anchor: datetime) -> tuple[Vt08B01Candidate | None, str]:
    bars = _m15_bars(symbol, anchor)
    anchor_local = anchor.astimezone(_NY)
    candidate_hours: list[int] = []
    current: Vt08B01Candidate | None = None
    for hour in OWNER_FOREX_ENTRY_ANCHORS:
        if hour > anchor_local.hour:
            continue
        decision_local = anchor_local.replace(hour=hour, minute=0, second=0, microsecond=0)
        decision = decision_local.astimezone(UTC)
        evaluation = evaluate_b01_at_entry(
            symbol=symbol,
            m15_bars=bars,
            decision_at=decision,
        )
        if evaluation.candidate is not None:
            candidate_hours.append(hour)
            if hour == anchor_local.hour:
                current = evaluation.candidate
    allowed = causal_daily_candidate_allowed(
        candidate_anchor_hours=tuple(candidate_hours),
        current_anchor_hour=anchor_local.hour,
    )
    if current is None:
        return None, f"no-{anchor_local.hour:02d}-candidate"
    if not allowed:
        return None, f"daily-cardinality-causal-abstain:{','.join(map(str, candidate_hours))}"
    return current, f"causal-{anchor_local.hour:02d}-candidate"


def _broker_risk(
    transport: MetaTrader5FundedNextLiveTransport,
) -> tuple[Decimal, Decimal, Decimal]:
    positions = mt5.positions_get()
    orders = mt5.orders_get()
    if positions is None or orders is None:
        raise RuntimeError("broker-exposure-snapshot-unavailable")
    open_stop = Decimal(0)
    floating_loss = Decimal(0)
    pending_stop = Decimal(0)
    for position in positions:
        stop = Decimal(str(position.sl))
        if stop <= 0:
            raise RuntimeError("open-position-without-stop-fails-closed")
        spec = transport.symbol_info(str(position.symbol))
        tick = mt5.symbol_info_tick(str(position.symbol))
        if spec is None or tick is None:
            raise RuntimeError("open-position-symbol-economics-unavailable")
        current = (
            Decimal(str(tick.bid))
            if int(position.type) == int(mt5.POSITION_TYPE_BUY)
            else Decimal(str(tick.ask))
        )
        volume = Decimal(str(position.volume))
        remaining = (
            max(Decimal(0), current - stop)
            if int(position.type) == int(mt5.POSITION_TYPE_BUY)
            else max(Decimal(0), stop - current)
        )
        open_stop += remaining / spec.tick_size * spec.tick_value * volume
        floating_loss += max(Decimal(0), -Decimal(str(position.profit)))
    for order in orders:
        stop = Decimal(str(order.sl))
        if stop <= 0:
            raise RuntimeError("pending-order-without-stop-fails-closed")
        spec = transport.symbol_info(str(order.symbol))
        if spec is None:
            raise RuntimeError("pending-order-symbol-economics-unavailable")
        entry = Decimal(str(order.price_open))
        volume = Decimal(str(order.volume_current))
        pending_stop += (
            abs(entry - stop) / spec.tick_size * spec.tick_value * volume
            + FOREX_OPEN_COMMISSION_PER_LOT_USD * volume
        )
    return open_stop, floating_loss, pending_stop


def _reconcile_filled_reservations(
    *,
    risk: DurableAccountWideRiskEngine,
    risk_ledger: DurableAccountWideRiskLedger,
    mutation_ledger: JsonFileFundedNextMt5MutationLedger,
    now: datetime,
) -> None:
    positions = mt5.positions_get()
    orders = mt5.orders_get()
    deals = mt5.history_deals_get(now - timedelta(days=_DISCOVERY_DAYS), now)
    if positions is None or orders is None or deals is None:
        raise RuntimeError("fill-reconciliation-broker-state-unavailable")
    observed_magics = {int(item.magic) for item in (*positions, *orders, *deals)}
    mutations = {
        item.risk_authorization_id: item
        for item in mutation_ledger.records()
        if item.state is FundedNextMt5MutationState.ACCEPTED
    }
    for reservation in risk_ledger.load():
        if reservation.state is not ReservationState.FILLED_UNRECONCILED:
            continue
        mutation = mutations.get(reservation.authorization.authorization_id)
        if mutation is None:
            continue
        if _magic(mutation.client_order_id) in observed_magics:
            risk.reconcile_fill(reservation.authorization.authorization_id)


def _log(path: Path, event: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    value = dict(event)
    value["logged_at"] = datetime.now(UTC).isoformat()
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(value, sort_keys=True, default=str) + "\n")


def _signal_anchor(accepted_at: datetime) -> datetime:
    local = accepted_at.astimezone(_NY).replace(minute=0, second=0, microsecond=0)
    if local.hour not in LIVE_ENTRY_ANCHORS_NY:
        raise RuntimeError("accepted-live-order-outside-causal-anchor")
    return local.astimezone(UTC)


def _exit_filling(symbol: str) -> int:
    info = mt5.symbol_info(symbol)
    if info is None:
        raise RuntimeError("exit-symbol-info-unavailable")
    mode = int(info.filling_mode)
    if mode & 2:
        return int(mt5.ORDER_FILLING_IOC)
    if mode & 1:
        return int(mt5.ORDER_FILLING_FOK)
    if int(info.trade_exemode) != int(mt5.SYMBOL_TRADE_EXECUTION_MARKET):
        return int(mt5.ORDER_FILLING_RETURN)
    raise RuntimeError("exit-filling-policy-unavailable")


def _reconcile_exit_ledger(
    ledger: JsonFileFundedNextPositionExitLedger,
    *,
    now: datetime,
) -> None:
    positions = mt5.positions_get()
    deals = mt5.history_deals_get(now - timedelta(days=_DISCOVERY_DAYS), now)
    if positions is None or deals is None:
        raise RuntimeError("exit-reconciliation-broker-state-unavailable")
    active_tickets = {str(item.ticket) for item in positions}
    deal_magics = {int(item.magic) for item in deals}
    for record in ledger.records():
        if record.state not in {
            PositionExitState.ATTEMPT_STARTED,
            PositionExitState.OUTCOME_UNKNOWN,
        }:
            continue
        if record.provider_position_ref not in active_tickets and record.magic in deal_magics:
            ledger.upsert(
                record.transition(
                    state=PositionExitState.ACCEPTED,
                    transitioned_at=now,
                    reason="broker-history-confirms-position-absent-after-exit",
                )
            )
        elif now - record.transitioned_at > timedelta(minutes=2):
            ledger.upsert(
                record.transition(
                    state=PositionExitState.REJECTED,
                    transitioned_at=now,
                    reason="broker-discovery-confirms-position-still-open",
                )
            )


def _manage_h4_exits(
    *,
    mutation_ledger: JsonFileFundedNextMt5MutationLedger,
    risk_ledger: DurableAccountWideRiskLedger,
    exit_ledger: JsonFileFundedNextPositionExitLedger,
    now: datetime,
    log_path: Path,
    mutations_enabled: bool = True,
) -> None:
    _reconcile_exit_ledger(exit_ledger, now=now)
    positions = mt5.positions_get()
    if positions is None:
        raise RuntimeError("position-management-state-unavailable")
    accepted = {
        _magic(record.client_order_id): record
        for record in mutation_ledger.records()
        if record.state is FundedNextMt5MutationState.ACCEPTED
    }
    existing = {record.key: record for record in exit_ledger.records()}
    lineages = {
        item.authorization.authorization_id: item.authorization.trader_id
        for item in risk_ledger.load()
    }
    for position in positions:
        source = accepted.get(int(position.magic))
        if source is None:
            continue
        lineage = lineages.get(source.risk_authorization_id)
        if lineage in {
            TraderLineage.R34_XAUUSD,
            TraderLineage.R38_EURUSD,
            TraderLineage.R43_GBPUSD,
            TraderLineage.R38_GBPJPY,
        }:
            signal_anchor = source.transitioned_at.astimezone(UTC).replace(
                minute=0, second=0, microsecond=0
            )
            due = signal_anchor + timedelta(hours=24)
            if lineage is TraderLineage.R34_XAUUSD:
                exit_label = "R34_24H"
            elif lineage is TraderLineage.R38_EURUSD:
                exit_label = "R38_24H"
            elif lineage is TraderLineage.R43_GBPUSD:
                exit_label = "R43_24H"
            else:
                exit_label = "GBPJPY_R38_24H"
        else:
            due = h4_containment_exit_at(_signal_anchor(source.transitioned_at))
            exit_label = "VT08_H4"
        if now < due:
            continue
        key = f"{source.client_order_id}|{position.ticket}"
        prior = existing.get(key)
        if prior is not None and prior.state in {
            PositionExitState.ATTEMPT_STARTED,
            PositionExitState.OUTCOME_UNKNOWN,
            PositionExitState.ACCEPTED,
        }:
            continue
        tick = mt5.symbol_info_tick(str(position.symbol))
        if tick is None:
            raise RuntimeError("h4-exit-tick-unavailable")
        closing_buy = int(position.type) != int(mt5.POSITION_TYPE_BUY)
        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": str(position.symbol),
            "position": int(position.ticket),
            "volume": float(position.volume),
            "type": mt5.ORDER_TYPE_BUY if closing_buy else mt5.ORDER_TYPE_SELL,
            "price": float(tick.ask if closing_buy else tick.bid),
            "magic": int(position.magic),
            "comment": f"qore-exit-{exit_label}-{str(position.ticket)}"[:29],
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": _exit_filling(str(position.symbol)),
        }
        checked = mt5.order_check(request)
        if checked is None or int(checked.retcode) != 0:
            _log(
                log_path,
                {"event": "H4_EXIT_CHECK_REJECT", "position": int(position.ticket)},
            )
            continue
        if not mutations_enabled:
            _log(
                log_path,
                {
                    "event": f"{exit_label}_SHADOW_EXIT_CHECK_PASS",
                    "position": int(position.ticket),
                    "due_at": due.isoformat(),
                },
            )
            continue
        attempt = PositionExitRecord(
            source_client_order_id=source.client_order_id,
            provider_position_ref=str(position.ticket),
            symbol=str(position.symbol),
            magic=int(position.magic),
            due_at=due,
            state=PositionExitState.ATTEMPT_STARTED,
            transitioned_at=now,
        )
        exit_ledger.upsert(attempt)
        result = mt5.order_send(request)
        recorded = datetime.now(UTC)
        if result is not None and int(result.retcode) in {
            int(mt5.TRADE_RETCODE_DONE),
            int(mt5.TRADE_RETCODE_PLACED),
        }:
            deal_ref = str(getattr(result, "deal", 0) or getattr(result, "order", 0))
            exit_ledger.upsert(
                attempt.transition(
                    state=PositionExitState.ACCEPTED,
                    transitioned_at=recorded,
                    provider_deal_ref=deal_ref if deal_ref != "0" else None,
                    reason=f"certified-{exit_label.lower()}-exit-accepted",
                )
            )
            _log(
                log_path,
                {
                    "event": f"{exit_label}_EXIT_ACCEPTED",
                    "position": int(position.ticket),
                },
            )
        elif result is not None and int(result.retcode) not in {
            int(mt5.TRADE_RETCODE_TIMEOUT),
            int(mt5.TRADE_RETCODE_CONNECTION),
            int(mt5.TRADE_RETCODE_DONE_PARTIAL),
        }:
            exit_ledger.upsert(
                attempt.transition(
                    state=PositionExitState.REJECTED,
                    transitioned_at=recorded,
                    reason=f"provider-rejected-{result.retcode}",
                )
            )
        else:
            exit_ledger.upsert(
                attempt.transition(
                    state=PositionExitState.OUTCOME_UNKNOWN,
                    transitioned_at=recorded,
                    reason="provider-exit-outcome-unknown",
                )
            )


def _process_candidate(
    *,
    candidate: Vt08B01Candidate,
    now: datetime,
    mode: str,
    gateway: FundedNextLiveMt5ExecutionGateway,
    transport: MetaTrader5FundedNextLiveTransport,
    risk: DurableAccountWideRiskEngine,
    account_binding_id: str,
    provider_budget: StellarInstantRiskBudget,
    capital_budget: QoreOperationalCapitalBudget,
    account_equity: Decimal,
    log_path: Path,
) -> None:
    setup = cibo_setup_from_b01(candidate)
    posture = request_cibo_posture(
        initial_balance=PILOT_INITIAL_BALANCE,
        balance=Decimal(str(gateway.read_account(now=now).balance)),
        equity=account_equity,
        current_aggregate_risk=risk.active_reserved_stop_risk(),
    )
    cibo = evaluate_vt08_forex_cibo(
        setup,
        enabled=True,
        certification_current=True,
        now=now,
        requested_posture=posture,
    )
    if cibo.decision is not Vt08ForexCiboDecision.ALLOW:
        _log(log_path, {"event": "CIBO_DENY", "symbol": candidate.symbol, "reason": cibo.reason})
        return
    spec = gateway.read_symbol(candidate.symbol, now=now)
    request = build_certified_vt08_forex_cibo_request(
        request_id=f"vt08-{setup.signal_fingerprint[:24]}",
        cibo_authorization=cibo,
        provider_spec=spec,
        account_equity=account_equity,
    )
    open_stop, floating_loss, pending_stop = _broker_risk(transport)
    account_state = gateway.read_account(now=now)
    snapshot = AccountRiskSnapshot(
        account_binding_id=account_binding_id,
        equity=account_equity,
        margin_used=account_state.margin,
        free_margin=account_state.free_margin,
        open_stop_worst_case_loss=open_stop,
        open_floating_loss=floating_loss,
        pending_broker_worst_case_loss=pending_stop,
        qore_authorizable_headroom=capital_budget.qore_authorizable_headroom,
        provider_budget=provider_budget,
        reconciled_at=now,
    )
    if risk.recovery_required:
        risk.complete_boot_reconciliation(snapshot, now=now)
    authorization = risk.authorize(request, snapshot, now=now)
    if authorization.decision is RiskDecision.REJECT:
        _log(
            log_path,
            {
                "event": "RISK_REJECT",
                "symbol": candidate.symbol,
                "reason": authorization.reason,
            },
        )
        return
    submission = build_account_bound_submission(
        authorization,
        switch=ExecutionSafetySwitchSnapshot(
            state=ExecutionSwitchState.ENABLED,
            observed_at=now,
            reason="qore fundednext resident runtime safety gate enabled",
        ),
        authorized_at=now,
        submitted_at=now,
    )
    shadow = gateway.shadow_check(submission, now=now)
    if not shadow.broker_valid:
        risk.cancel(authorization.authorization_id)
        _log(
            log_path,
            {
                "event": "SHADOW_REJECT",
                "symbol": candidate.symbol,
                "reason": shadow.reason,
            },
        )
        return
    if mode == "shadow":
        risk.cancel(authorization.authorization_id)
        _log(
            log_path,
            {
                "event": "SHADOW_PASS",
                "symbol": candidate.symbol,
                "signal_fingerprint": setup.signal_fingerprint,
                "risk_usd": str(authorization.monetary_stop_loss),
                "volume": str(authorization.authorized_volume),
                "retcode": shadow.retcode,
            },
        )
        return
    provider_ref = gateway.submit_live(submission, now=now)
    risk.record_full_fill(authorization.authorization_id)
    _log(
        log_path,
        {
            "event": "LIVE_SUBMIT_ACCEPTED",
            "symbol": candidate.symbol,
            "signal_fingerprint": setup.signal_fingerprint,
            "risk_authorization": authorization.authorization_id,
            "provider_order_ref": provider_ref,
            "risk_usd": str(authorization.monetary_stop_loss),
            "volume": str(authorization.authorized_volume),
        },
    )


def _process_r34_candidate(
    *,
    signal: R34LiveSignal,
    now: datetime,
    mode: str,
    gateway: FundedNextLiveMt5ExecutionGateway,
    transport: MetaTrader5FundedNextLiveTransport,
    risk: DurableAccountWideRiskEngine,
    account_binding_id: str,
    provider_budget: StellarInstantRiskBudget,
    capital_budget: QoreOperationalCapitalBudget,
    account_equity: Decimal,
    r34_store: R34LiveStateStore,
    log_path: Path,
) -> None:
    spec = gateway.read_symbol("XAUUSD", now=now)
    request, base_risk_usd = build_r34_risk_request(
        request_id=f"r34-{signal.signal_fingerprint[:24]}",
        signal=signal,
        provider_spec=spec,
        account_equity=account_equity,
        now=now,
    )
    open_stop, floating_loss, pending_stop = _broker_risk(transport)
    account_state = gateway.read_account(now=now)
    snapshot = AccountRiskSnapshot(
        account_binding_id=account_binding_id,
        equity=account_equity,
        margin_used=account_state.margin,
        free_margin=account_state.free_margin,
        open_stop_worst_case_loss=open_stop,
        open_floating_loss=floating_loss,
        pending_broker_worst_case_loss=pending_stop,
        qore_authorizable_headroom=capital_budget.qore_authorizable_headroom,
        provider_budget=provider_budget,
        reconciled_at=now,
    )
    if risk.recovery_required:
        risk.complete_boot_reconciliation(snapshot, now=now)
    authorization = risk.authorize(request, snapshot, now=now)
    if authorization.decision is RiskDecision.REJECT:
        _log(
            log_path,
            {
                "event": "R34_RISK_REJECT",
                "symbol": "XAUUSD",
                "reason": authorization.reason,
                "signal_fingerprint": signal.signal_fingerprint,
            },
        )
        return
    submission = build_account_bound_submission(
        authorization,
        switch=ExecutionSafetySwitchSnapshot(
            state=ExecutionSwitchState.ENABLED,
            observed_at=now,
            reason="qore R34 certified runtime safety gate enabled",
        ),
        authorized_at=now,
        submitted_at=now,
    )
    shadow = gateway.shadow_check(submission, now=now)
    if not shadow.broker_valid:
        risk.cancel(authorization.authorization_id)
        _log(
            log_path,
            {
                "event": "R34_SHADOW_REJECT",
                "symbol": "XAUUSD",
                "reason": shadow.reason,
                "signal_fingerprint": signal.signal_fingerprint,
            },
        )
        return
    if mode == "shadow":
        risk.cancel(authorization.authorization_id)
        _log(
            log_path,
            {
                "event": "R34_SHADOW_PASS",
                "symbol": "XAUUSD",
                "signal_fingerprint": signal.signal_fingerprint,
                "timeframe": signal.timeframe,
                "target_rank": signal.target_rank,
                "target_route": signal.target_route,
                "decision_source": signal.decision_source,
                "family": signal.family,
                "risk_scale": str(signal.risk_scale),
                "risk_usd": str(authorization.monetary_stop_loss),
                "volume": str(authorization.authorized_volume),
                "retcode": shadow.retcode,
            },
        )
        return
    provider_ref = gateway.submit_live(submission, now=now)
    risk.record_full_fill(authorization.authorization_id)
    client_order_id = f"qore-{submission.idempotency_key.value.hex[:24]}"
    r34_store.mark_open(
        client_order_id=client_order_id,
        signal=signal,
        base_risk_usd=base_risk_usd,
    )
    _log(
        log_path,
        {
            "event": "R34_LIVE_SUBMIT_ACCEPTED",
            "symbol": "XAUUSD",
            "signal_fingerprint": signal.signal_fingerprint,
            "timeframe": signal.timeframe,
            "target_rank": signal.target_rank,
            "target_route": signal.target_route,
            "decision_source": signal.decision_source,
            "family": signal.family,
            "risk_scale": str(signal.risk_scale),
            "risk_authorization": authorization.authorization_id,
            "provider_order_ref": provider_ref,
            "risk_usd": str(authorization.monetary_stop_loss),
            "volume": str(authorization.authorized_volume),
        },
    )


def _process_r38_candidate(
    *,
    signal: R38LiveSignal,
    now: datetime,
    mode: str,
    gateway: FundedNextLiveMt5ExecutionGateway,
    transport: MetaTrader5FundedNextLiveTransport,
    risk: DurableAccountWideRiskEngine,
    account_binding_id: str,
    provider_budget: StellarInstantRiskBudget,
    capital_budget: QoreOperationalCapitalBudget,
    account_equity: Decimal,
    r38_store: R38LiveStateStore,
    log_path: Path,
) -> None:
    spec = gateway.read_symbol("EURUSD", now=now)
    request, base_risk_usd = build_r38_risk_request(
        request_id=f"r38-{signal.signal_fingerprint[:24]}",
        signal=signal,
        provider_spec=spec,
        account_equity=account_equity,
        now=now,
    )
    open_stop, floating_loss, pending_stop = _broker_risk(transport)
    account_state = gateway.read_account(now=now)
    snapshot = AccountRiskSnapshot(
        account_binding_id=account_binding_id,
        equity=account_equity,
        margin_used=account_state.margin,
        free_margin=account_state.free_margin,
        open_stop_worst_case_loss=open_stop,
        open_floating_loss=floating_loss,
        pending_broker_worst_case_loss=pending_stop,
        qore_authorizable_headroom=capital_budget.qore_authorizable_headroom,
        provider_budget=provider_budget,
        reconciled_at=now,
    )
    if risk.recovery_required:
        risk.complete_boot_reconciliation(snapshot, now=now)
    authorization = risk.authorize(request, snapshot, now=now)
    if authorization.decision is RiskDecision.REJECT:
        _log(
            log_path,
            {
                "event": "R38_RISK_REJECT",
                "symbol": "EURUSD",
                "reason": authorization.reason,
                "signal_fingerprint": signal.signal_fingerprint,
            },
        )
        return
    submission = build_account_bound_submission(
        authorization,
        switch=ExecutionSafetySwitchSnapshot(
            state=ExecutionSwitchState.ENABLED,
            observed_at=now,
            reason="qore R38 certified runtime safety gate enabled",
        ),
        authorized_at=now,
        submitted_at=now,
    )
    shadow = gateway.shadow_check(submission, now=now)
    if not shadow.broker_valid:
        risk.cancel(authorization.authorization_id)
        _log(
            log_path,
            {
                "event": "R38_SHADOW_REJECT",
                "symbol": "EURUSD",
                "reason": shadow.reason,
                "signal_fingerprint": signal.signal_fingerprint,
            },
        )
        return
    event = {
        "symbol": "EURUSD",
        "signal_fingerprint": signal.signal_fingerprint,
        "timeframe": signal.timeframe,
        "target_rank": signal.target_rank,
        "target_route": signal.target_route,
        "decision_source": signal.decision_source,
        "family": signal.family,
        "posture": signal.posture,
        "fragility_flags": list(signal.fragility_flags),
        "base_fragility_scale": str(signal.base_fragility_scale),
        "structural_overlay_scale": str(signal.structural_overlay_scale),
        "risk_scale": str(signal.risk_scale),
        "risk_usd": str(authorization.monetary_stop_loss),
        "volume": str(authorization.authorized_volume),
    }
    if mode == "shadow":
        risk.cancel(authorization.authorization_id)
        _log(
            log_path,
            {
                "event": "R38_SHADOW_PASS",
                **event,
                "retcode": shadow.retcode,
            },
        )
        return
    provider_ref = gateway.submit_live(submission, now=now)
    risk.record_full_fill(authorization.authorization_id)
    client_order_id = f"qore-{submission.idempotency_key.value.hex[:24]}"
    r38_store.mark_open(
        client_order_id=client_order_id,
        signal=signal,
        base_risk_usd=base_risk_usd,
    )
    _log(
        log_path,
        {
            "event": "R38_LIVE_SUBMIT_ACCEPTED",
            **event,
            "risk_authorization": authorization.authorization_id,
            "provider_order_ref": provider_ref,
        },
    )



def _process_r43_candidate(
    *,
    signal: R43LiveSignal,
    now: datetime,
    mode: str,
    gateway: FundedNextLiveMt5ExecutionGateway,
    transport: MetaTrader5FundedNextLiveTransport,
    risk: DurableAccountWideRiskEngine,
    account_binding_id: str,
    provider_budget: StellarInstantRiskBudget,
    capital_budget: QoreOperationalCapitalBudget,
    account_equity: Decimal,
    r43_store: R43LiveStateStore,
    log_path: Path,
) -> None:
    spec = gateway.read_symbol("GBPUSD", now=now)
    request, base_risk_usd = build_r43_risk_request(
        request_id=f"r43-{signal.signal_fingerprint[:24]}",
        signal=signal,
        provider_spec=spec,
        account_equity=account_equity,
        now=now,
    )
    open_stop, floating_loss, pending_stop = _broker_risk(transport)
    account_state = gateway.read_account(now=now)
    snapshot = AccountRiskSnapshot(
        account_binding_id=account_binding_id,
        equity=account_equity,
        margin_used=account_state.margin,
        free_margin=account_state.free_margin,
        open_stop_worst_case_loss=open_stop,
        open_floating_loss=floating_loss,
        pending_broker_worst_case_loss=pending_stop,
        qore_authorizable_headroom=capital_budget.qore_authorizable_headroom,
        provider_budget=provider_budget,
        reconciled_at=now,
    )
    if risk.recovery_required:
        risk.complete_boot_reconciliation(snapshot, now=now)
    authorization = risk.authorize(request, snapshot, now=now)
    if authorization.decision is RiskDecision.REJECT:
        _log(
            log_path,
            {
                "event": "R43_RISK_REJECT",
                "symbol": "GBPUSD",
                "reason": authorization.reason,
                "signal_fingerprint": signal.signal_fingerprint,
            },
        )
        return
    submission = build_account_bound_submission(
        authorization,
        switch=ExecutionSafetySwitchSnapshot(
            state=ExecutionSwitchState.ENABLED,
            observed_at=now,
            reason="qore R43 certified runtime safety gate enabled",
        ),
        authorized_at=now,
        submitted_at=now,
    )
    shadow = gateway.shadow_check(submission, now=now)
    if not shadow.broker_valid:
        risk.cancel(authorization.authorization_id)
        _log(
            log_path,
            {
                "event": "R43_SHADOW_REJECT",
                "symbol": "GBPUSD",
                "reason": shadow.reason,
                "signal_fingerprint": signal.signal_fingerprint,
            },
        )
        return
    event = {
        "symbol": "GBPUSD",
        "signal_fingerprint": signal.signal_fingerprint,
        "timeframe": signal.timeframe,
        "target_rank": signal.target_rank,
        "target_route": signal.target_route,
        "decision_source": signal.decision_source,
        "family": signal.family,
        "classification": signal.classification,
        "posture": signal.posture,
        "structural_scale": str(signal.structural_scale),
        "side_overlay_scale": str(signal.side_overlay_scale),
        "rank_overlay_scale": str(signal.rank_overlay_scale),
        "drawdown_scale": str(signal.drawdown_scale),
        "risk_scale": str(signal.risk_scale),
        "risk_usd": str(authorization.monetary_stop_loss),
        "volume": str(authorization.authorized_volume),
    }
    if mode == "shadow":
        risk.cancel(authorization.authorization_id)
        _log(
            log_path,
            {
                "event": "R43_SHADOW_PASS",
                **event,
                "retcode": shadow.retcode,
            },
        )
        return
    provider_ref = gateway.submit_live(submission, now=now)
    risk.record_full_fill(authorization.authorization_id)
    client_order_id = f"qore-{submission.idempotency_key.value.hex[:24]}"
    r43_store.mark_open(
        client_order_id=client_order_id,
        signal=signal,
        base_risk_usd=base_risk_usd,
    )
    _log(
        log_path,
        {
            "event": "R43_LIVE_SUBMIT_ACCEPTED",
            **event,
            "risk_authorization": authorization.authorization_id,
            "provider_order_ref": provider_ref,
        },
    )


def _process_gbpjpy_r38_candidate(
    *,
    signal: R38GbpJpyLiveSignal,
    now: datetime,
    mode: str,
    gateway: FundedNextLiveMt5ExecutionGateway,
    transport: MetaTrader5FundedNextLiveTransport,
    risk: DurableAccountWideRiskEngine,
    account_binding_id: str,
    provider_budget: StellarInstantRiskBudget,
    capital_budget: QoreOperationalCapitalBudget,
    account_equity: Decimal,
    gbpjpy_r38_store: R38GbpJpyLiveStateStore,
    log_path: Path,
) -> None:
    spec = gateway.read_symbol("GBPJPY", now=now)
    request, base_risk_usd = build_r38_gbpjpy_risk_request(
        request_id=f"gbpjpy-r38-{signal.signal_fingerprint[:24]}",
        signal=signal,
        provider_spec=spec,
        account_equity=account_equity,
        now=now,
    )
    open_stop, floating_loss, pending_stop = _broker_risk(transport)
    account_state = gateway.read_account(now=now)
    snapshot = AccountRiskSnapshot(
        account_binding_id=account_binding_id,
        equity=account_equity,
        margin_used=account_state.margin,
        free_margin=account_state.free_margin,
        open_stop_worst_case_loss=open_stop,
        open_floating_loss=floating_loss,
        pending_broker_worst_case_loss=pending_stop,
        qore_authorizable_headroom=capital_budget.qore_authorizable_headroom,
        provider_budget=provider_budget,
        reconciled_at=now,
    )
    if risk.recovery_required:
        risk.complete_boot_reconciliation(snapshot, now=now)
    authorization = risk.authorize(request, snapshot, now=now)
    if authorization.decision is RiskDecision.REJECT:
        _log(
            log_path,
            {
                "event": "GBPJPY_R38_RISK_REJECT",
                "symbol": "GBPJPY",
                "reason": authorization.reason,
                "signal_fingerprint": signal.signal_fingerprint,
            },
        )
        return

    submission = build_account_bound_submission(
        authorization,
        switch=ExecutionSafetySwitchSnapshot(
            state=ExecutionSwitchState.ENABLED,
            observed_at=now,
            reason="qore GBPJPY R38 certified runtime safety gate enabled",
        ),
        authorized_at=now,
        submitted_at=now,
    )
    shadow = gateway.shadow_check(submission, now=now)
    if not shadow.broker_valid:
        risk.cancel(authorization.authorization_id)
        _log(
            log_path,
            {
                "event": "GBPJPY_R38_SHADOW_REJECT",
                "symbol": "GBPJPY",
                "reason": shadow.reason,
                "signal_fingerprint": signal.signal_fingerprint,
            },
        )
        return

    event = {
        "symbol": "GBPJPY",
        "signal_fingerprint": signal.signal_fingerprint,
        "timeframe": signal.timeframe,
        "target_rank": signal.target_rank,
        "target_route": signal.target_route,
        "source_scheme": signal.source_scheme,
        "authority_tier": signal.authority_tier,
        "classification": signal.classification,
        "posture": signal.posture,
        "base_risk_scale": str(signal.base_risk_scale),
        "fragility_flags": list(signal.fragility_flags),
        "structural_overlay_scale": str(signal.structural_overlay_scale),
        "risk_scale": str(signal.risk_scale),
        "risk_usd": str(authorization.monetary_stop_loss),
        "volume": str(authorization.authorized_volume),
    }
    if mode == "shadow":
        risk.cancel(authorization.authorization_id)
        _log(
            log_path,
            {
                "event": "GBPJPY_R38_SHADOW_PASS",
                **event,
                "retcode": shadow.retcode,
            },
        )
        return

    provider_ref = gateway.submit_live(submission, now=now)
    risk.record_full_fill(authorization.authorization_id)
    client_order_id = f"qore-{submission.idempotency_key.value.hex[:24]}"
    gbpjpy_r38_store.mark_open(
        client_order_id=client_order_id,
        signal=signal,
        base_risk_usd=base_risk_usd,
    )
    _log(
        log_path,
        {
            "event": "GBPJPY_R38_LIVE_SUBMIT_ACCEPTED",
            **event,
            "risk_authorization": authorization.authorization_id,
            "provider_order_ref": provider_ref,
        },
    )


def run(root: Path, *, mode: str, activation_path: Path) -> None:
    sha = _git_sha(root)
    if not mt5.initialize():
        raise RuntimeError(f"mt5-initialize-failed-{mt5.last_error()}")
    account_info = mt5.account_info()
    if account_info is None:
        raise RuntimeError("mt5-account-info-unavailable")
    if str(account_info.server) != _EXPECTED_SERVER:
        raise RuntimeError("mt5-server-mismatch")
    fingerprint = _account_fingerprint(account_info)
    account = MarketTestAccountIdentity(
        provider_key="fundednext-stellar-instant-mt5",
        account_ref=_ACCOUNT_REF,
        environment=MarketRuntimeEnvironment.PRODUCTION,
    )
    activation = load_verified_live_activation(
        root=root,
        activation_path=activation_path,
        account=account,
        runtime_git_sha=sha,
        account_identity_fingerprint=fingerprint,
        server=_EXPECTED_SERVER,
    )
    if mode == "live":
        activation.authorization.assert_can_submit(
            account=account,
            git_sha=sha,
            account_identity_fingerprint=fingerprint,
            server=_EXPECTED_SERVER,
        )
    state_dir = root / "var" / "fundednext"
    r34_cognitive = load_r34_cognitive(
        root
        / "var"
        / "r34"
        / "cognitive-v3"
        / "turtle-soup-xauusd-specialist-cognitive-memory-v3.json"
    )
    r34_store = R34LiveStateStore(state_dir / "r34-state.json")
    r34_store.reconcile(mt5, now=datetime.now(UTC))
    r38_cognitive = load_r38_cognitive(
        root
        / "var"
        / "r38"
        / "cognitive-v3"
        / "turtle-soup-eurusd-specialist-cognitive-memory-v3.json"
    )
    r38_store = R38LiveStateStore(state_dir / "r38-state.json")
    r38_store.reconcile(mt5, now=datetime.now(UTC))
    r43_memory = load_r43_memory(
        root
        / "runtime_data"
        / "gbpusd"
        / "r43-r32-regime-memory.json"
    )
    r43_store = R43LiveStateStore(state_dir / "r43-state.json")
    r43_store.reconcile(mt5, now=datetime.now(UTC))
    gbpjpy_r38_memory = load_gbpjpy_r38_memory(
        root
        / "runtime_data"
        / "gbpjpy"
        / "r38-confidence-tier-memory.json"
    )
    gbpjpy_r38_store = R38GbpJpyLiveStateStore(
        state_dir / "r38-gbpjpy-state.json"
    )
    gbpjpy_r38_store.reconcile(mt5, now=datetime.now(UTC))

    turtle_history_bars = {
        "XAUUSD": R34_HISTORY_M5_BARS,
        "EURUSD": R38_HISTORY_M5_BARS,
        "GBPUSD": R43_HISTORY_M5_BARS,
        "GBPJPY": GBPJPY_R38_HISTORY_M5_BARS,
    }
    turtle_market_data = FundedNextRealtimeMarketData()
    turtle_market_data.warm_many(
        mt5,
        symbols=turtle_history_bars,
    )

    def refresh_provider_rules_before_submission() -> None:
        result = subprocess.run(
            [
                sys.executable,
                str(root / "scripts" / "qore_fundednext_rules_refresh.py"),
                "--root",
                str(root),
            ],
            cwd=root,
            check=False,
            capture_output=True,
            text=True,
            timeout=25,
        )
        if result.returncode != 0:
            detail = (result.stderr or result.stdout or "provider-rule-refresh-failed").strip()
            raise RuntimeError(detail[:500])
    safety_path = state_dir / "live-safety.json"
    load_live_safety_state(safety_path)
    safety = JsonFileLiveOperationalSafetyBoundary(safety_path)
    transport = MetaTrader5FundedNextLiveTransport(
        api=mt5,
        qore_account_ref=_ACCOUNT_REF,
        expected_login=int(account_info.login),
        expected_server=_EXPECTED_SERVER,
    )
    mutation_ledger = JsonFileFundedNextMt5MutationLedger(state_dir / "mt5-mutations.json")
    risk_ledger = DurableAccountWideRiskLedger(state_dir / "risk-reservations.json")
    exit_ledger = JsonFileFundedNextPositionExitLedger(state_dir / "position-exits.json")
    exit_ledger.mark_interrupted_unknown(now=datetime.now(UTC))
    risk = DurableAccountWideRiskEngine(risk_ledger)
    gateway = FundedNextLiveMt5ExecutionGateway(
        account=account,
        transport=transport,
        mutation_ledger=mutation_ledger,
        rule_verification=RollingStellarInstantRuleVerification(
            baseline=activation.rules,
            refresh_path=state_dir / "provider-rules-refresh.json",
            expected_provider_rules_fingerprint=activation.authorization.provider_rules_fingerprint,
            refresh_action=refresh_provider_rules_before_submission,
        ),
        live_authorization=activation.authorization,
        safety=safety,
        runtime_git_sha=sha,
        account_identity_fingerprint=fingerprint,
        expected_server=_EXPECTED_SERVER,
        submission_enabled=mode == "live",
    )
    gateway.reconcile_unknown(now=datetime.now(UTC))

    capital_store = DurableFundedNextLiveCapitalStore(
        state_dir / "capital-checkpoint.json",
        state_dir / "capital-checkpoint.backup.json",
    )
    try:
        checkpoint = capital_store.load_required()
    except Exception:
        if (
            mode == "shadow"
            and not activation.authorization.service_24_7_verified
            and not activation.authorization.order_submission_authorized
        ):
            started = datetime.now(UTC)
            highest = max(PILOT_INITIAL_BALANCE, Decimal(str(account_info.balance)))
            checkpoint = FundedNextLiveCapitalCheckpoint(
                git_sha=sha,
                account_identity_fingerprint=fingerprint,
                highest_closed_balance=highest,
                active_mll=PILOT_INITIAL_BALANCE * Decimal("0.94"),
                created_at=started,
                updated_at=started,
            )
            capital_store.initialize_once(checkpoint)
        else:
            raise
    if checkpoint.git_sha != sha or checkpoint.account_identity_fingerprint != fingerprint:
        raise RuntimeError("capital-checkpoint-binding-mismatch")

    store = DurableFundedNextRuntimeStateStore(state_dir / "runtime-state.json")
    old = store.load()
    now = datetime.now(UTC)
    if old is not None:
        if old.git_sha != sha or old.account_identity_fingerprint != fingerprint:
            raise RuntimeError("runtime-state-binding-mismatch")
        state = old.restarted_at(now)
    else:
        state = FundedNextRuntimeState(
            git_sha=sha,
            account_identity_fingerprint=fingerprint,
            highest_closed_balance=str(checkpoint.highest_closed_balance),
            active_mll=str(checkpoint.active_mll),
            processed_anchors=(),
            heartbeat_at=now,
            last_reconciliation_at=now,
            service_started_at=now,
        )
    store.store(state)
    highest = checkpoint.highest_closed_balance
    previous_mll = checkpoint.active_mll
    log_path = root / "artifacts" / "fundednext_runtime_events.jsonl"
    _log(
        log_path,
        {
            "event": "RUNTIME_STARTED",
            "mode": mode,
            "git_sha": sha,
            "news_policy": "provider-permitted-no-synthetic-qore-news-trade-or-filter",
            "vt08_strategy_timezone": "America/New_York",
            "vt08_entry_anchors_new_york": list(LIVE_ENTRY_ANCHORS_NY),
            "vt08_broker_clock_normalized": True,
            "r34_enabled": True,
            "r34_identity": "TURTLE_SOUP_XAUUSD_R34",
            "r34_strategy_timezone": "America/New_York",
            "r34_schedule": "EVERY_H1_H4_BOUNDARY_24_7_SERVICE",
            "r34_single_position_busy": True,
            "r34_lifecycle": "STATIC_SL_TP_PLUS_24H_EXIT",
            "r38_enabled": True,
            "r38_identity": "TURTLE_SOUP_EURUSD_R38",
            "r38_certification": "TURTLE_SOUP_EURUSD_R39_FINAL_CERTIFICATION_SUITE_V1",
            "r38_strategy_timezone": "America/New_York",
            "r38_schedule": "EVERY_H1_H4_BOUNDARY_24_7_SERVICE",
            "r38_single_position_busy": True,
            "r38_lifecycle": "STATIC_OR_PROTECT_DOL_LOCK_M5_SWING_TRAIL_PLUS_24H_EXIT",
            "r38_base_risk_fraction": "0.002",
            "r43_enabled": True,
            "r43_identity": "TURTLE_SOUP_GBPUSD_R43",
            "r43_certification": "TURTLE_SOUP_GBPUSD_R45_FINAL_CERTIFICATION_SUITE_V1",
            "r43_strategy_timezone": "America/New_York",
            "r43_schedule": "EVERY_H1_H4_BOUNDARY_24_7_SERVICE",
            "r43_single_position_busy": True,
            "r43_lifecycle": "STATIC_OR_PROTECT_DOL_LOCK_M5_SWING_TRAIL_PLUS_24H_EXIT",
            "r43_base_risk_fraction": "0.002",
            "r43_short_overlay_scale": "0.005",
            "r43_rank2_overlay_scale": "0.25",
            "r43_memory_sha256": "e4a79978c0144e0b97c19ce3ee18040e62a02efe891b204fc724e4a0016734ae",
            "loaded_traders": [
                "VT08",
                "TURTLE_SOUP_XAUUSD_R34",
                "TURTLE_SOUP_EURUSD_R38",
                "TURTLE_SOUP_GBPUSD_R43",
                "TURTLE_SOUP_GBPJPY_R38",
            ],
            "single_mt5_writer": True,
            "account_wide_risk_active": True,
            "market_data_sla_seconds": MARKET_DATA_SLA_SECONDS,
            "market_data_cache": "WARM_ONCE_INCREMENTAL_M5",
            "market_data_boundary_policy": "EXACT_CLOSED_AND_CURRENT_M5",
            "gbpjpy_r38_enabled": True,
            "gbpjpy_r38_identity": "TURTLE_SOUP_GBPJPY_R38",
            "gbpjpy_r38_certification": "TURTLE_SOUP_GBPJPY_R39_FINAL_CERTIFICATION_SUITE_V1",
            "gbpjpy_r38_strategy_timezone": "America/New_York",
            "gbpjpy_r38_schedule": "EVERY_H1_H4_BOUNDARY_24_7_SERVICE",
            "gbpjpy_r38_single_position_busy": True,
            "gbpjpy_r38_lifecycle": "STATIC_OR_PROTECT_DOL_LOCK_M5_SWING_TRAIL_PLUS_24H_EXIT",
            "gbpjpy_r38_base_risk_fraction": "0.002",
            "gbpjpy_r38_ensemble": "R35_RANGE_DIRECTION_MINIMAL_ROBUST",
            "gbpjpy_r38_policy": "CONFIDENCE_100_050_010",
            "gbpjpy_r38_fragility_policy": ["1", "0.25", "0.10", "0.05"],
            "gbpjpy_r38_memory_sha256": "16a369e8457394642642ca2c7331e32b05644a5656d339cbba06db089f44211f",
            "order_submission_authorized": activation.authorization.order_submission_authorized,
        },
    )
    last_lifecycle: str | None = None
    logged_market_data_boundaries: set[tuple[str, str]] = set()
    last_boundary_capture: datetime | None = None
    vt08_boundary_results: dict[
        str,
        tuple[Vt08B01Candidate | None, str],
    ] = {}
    vt08_boundary_failures: dict[str, str] = {}

    while True:
        cycle_at = _arm_to_hour_boundary(datetime.now(UTC))
        turtle_anchor = current_r34_anchor(cycle_at)
        if turtle_anchor is None:
            turtle_market_data.refresh_many(
                mt5,
                symbols=tuple(turtle_history_bars),
                now=cycle_at,
            )
        elif turtle_anchor != last_boundary_capture:
            vt08_anchor = _current_anchor(cycle_at)
            vt08_boundary_results = {}
            vt08_boundary_failures = {}
            vt08_pending = set(_MARKETS) if vt08_anchor is not None else set()
            vt08_pending_reason: dict[str, str] = {}
            deadline = turtle_anchor + timedelta(seconds=MARKET_DATA_SLA_SECONDS)

            while True:
                turtle_pending = set(
                    turtle_market_data.prime_anchor_once(
                        mt5,
                        anchor=turtle_anchor,
                        symbols=turtle_history_bars,
                    )
                )
                for symbol in tuple(vt08_pending):
                    ready, pending_reason = _vt08_boundary_ready(
                        mt5,
                        symbol=symbol,
                        anchor=(
                            vt08_anchor
                            if vt08_anchor is not None
                            else turtle_anchor
                        ),
                    )
                    if not ready:
                        if pending_reason is not None:
                            vt08_pending_reason[symbol] = pending_reason
                        continue
                    try:
                        vt08_boundary_results[symbol] = _causal_candidate(
                            symbol,
                            vt08_anchor if vt08_anchor is not None else turtle_anchor,
                        )
                    except Exception as error:
                        vt08_boundary_failures[symbol] = (
                            f"{type(error).__name__}: {error}"
                        )
                    vt08_pending.remove(symbol)

                if not turtle_pending and not vt08_pending:
                    break
                remaining = (deadline - datetime.now(UTC)).total_seconds()
                if remaining <= 0:
                    break
                time.sleep(min(_BOUNDARY_POLL_SECONDS, remaining))

            market_status = turtle_market_data.finalize_anchor_group(
                anchor=turtle_anchor,
                symbols=turtle_history_bars,
            )
            for symbol in vt08_pending:
                detail = vt08_pending_reason.get(
                    symbol,
                    f"{symbol} VT08 boundary evidence unavailable",
                )
                vt08_boundary_failures[symbol] = (
                    f"{detail}; hard_sla={MARKET_DATA_SLA_SECONDS:.1f}s"
                )

            for symbol, failure in market_status.items():
                log_key = (symbol, turtle_anchor.isoformat())
                if log_key in logged_market_data_boundaries:
                    continue
                if failure is not None:
                    _log(
                        log_path,
                        {
                            "event": "TURTLE_MARKET_DATA_SLA_FAIL_CLOSED",
                            "symbol": symbol,
                            "decision_at": turtle_anchor.isoformat(),
                            "sla_seconds": MARKET_DATA_SLA_SECONDS,
                            "message": failure,
                        },
                    )
                else:
                    snapshot = turtle_market_data.snapshot(
                        mt5,
                        symbol=symbol,
                        anchor=turtle_anchor,
                        history_bars=turtle_history_bars[symbol],
                    )
                    _log(
                        log_path,
                        {
                            "event": "TURTLE_MARKET_DATA_BOUNDARY_READY",
                            "symbol": symbol,
                            "decision_at": turtle_anchor.isoformat(),
                            "capture_latency_ms": round(
                                (snapshot.captured_at - turtle_anchor).total_seconds()
                                * 1_000,
                                3,
                            ),
                            "tick_age_ms": round(
                                snapshot.tick_age_seconds * 1_000,
                                3,
                            ),
                            "latest_closed_m5": (
                                snapshot.closed_rates[-1].opened_at.isoformat()
                            ),
                            "current_m5": snapshot.current_rate.opened_at.isoformat(),
                        },
                    )
                logged_market_data_boundaries.add(log_key)

            if vt08_anchor is not None:
                for symbol in _MARKETS:
                    failure = vt08_boundary_failures.get(symbol)
                    if failure is not None:
                        _log(
                            log_path,
                            {
                                "event": "VT08_MARKET_DATA_SLA_FAIL_CLOSED",
                                "symbol": symbol,
                                "decision_at": vt08_anchor.isoformat(),
                                "sla_seconds": MARKET_DATA_SLA_SECONDS,
                                "message": failure,
                            },
                        )
                    elif symbol in vt08_boundary_results:
                        _log(
                            log_path,
                            {
                                "event": "VT08_MARKET_DATA_BOUNDARY_READY",
                                "symbol": symbol,
                                "decision_at": vt08_anchor.isoformat(),
                                "sla_seconds": MARKET_DATA_SLA_SECONDS,
                            },
                        )
            last_boundary_capture = turtle_anchor

        account_state = gateway.read_account(now=cycle_at)
        gateway.reconcile_unknown(now=cycle_at)
        _manage_h4_exits(
            mutation_ledger=mutation_ledger,
            risk_ledger=risk_ledger,
            exit_ledger=exit_ledger,
            now=cycle_at,
            log_path=log_path,
            mutations_enabled=mode == "live",
        )
        _reconcile_filled_reservations(
            risk=risk,
            risk_ledger=risk_ledger,
            mutation_ledger=mutation_ledger,
            now=cycle_at,
        )
        r34_live_state = r34_store.reconcile(mt5, now=cycle_at)
        try:
            r38_live_state, r38_manage_reason = manage_r38_open_position(
                mt5,
                now=cycle_at,
                store=r38_store,
                market_data=turtle_market_data,
                mutations_enabled=mode == "live",
            )
        except MarketDataSlaError as error:
            r38_live_state = r38_store.reconcile(mt5, now=cycle_at)
            r38_manage_reason = "r38-market-data-fail-closed"
            _log(
                log_path,
                {
                    "event": "R38_MANAGEMENT_DATA_FAIL_CLOSED",
                    "symbol": "EURUSD",
                    "message": str(error),
                },
            )
        if r38_manage_reason not in {
            "no-open-r38-position",
            "r38-stop-unchanged",
            "r38-position-awaiting-reconcile",
            "r38-24h-exit-due",
        }:
            _log(
                log_path,
                {
                    "event": "R38_POSITION_MANAGEMENT",
                    "symbol": "EURUSD",
                    "reason": r38_manage_reason,
                    "new_york_time": cycle_at.astimezone(_NY).isoformat(),
                },
            )
        try:
            r43_live_state, r43_manage_reason = manage_r43_open_position(
                mt5,
                now=cycle_at,
                store=r43_store,
                market_data=turtle_market_data,
                mutations_enabled=mode == "live",
            )
        except MarketDataSlaError as error:
            r43_live_state = r43_store.reconcile(mt5, now=cycle_at)
            r43_manage_reason = "r43-market-data-fail-closed"
            _log(
                log_path,
                {
                    "event": "R43_MANAGEMENT_DATA_FAIL_CLOSED",
                    "symbol": "GBPUSD",
                    "message": str(error),
                },
            )
        if r43_manage_reason not in {
            "no-open-r43-position",
            "r43-stop-unchanged",
            "r43-position-awaiting-reconcile",
            "r43-24h-exit-due",
        }:
            _log(
                log_path,
                {
                    "event": "R43_POSITION_MANAGEMENT",
                    "symbol": "GBPUSD",
                    "reason": r43_manage_reason,
                    "strategy_drawdown_r": str(r43_live_state.drawdown_r),
                    "new_york_time": cycle_at.astimezone(_NY).isoformat(),
                },
            )
        try:
            gbpjpy_r38_live_state, gbpjpy_r38_manage_reason = (
                manage_gbpjpy_r38_open_position(
                    mt5,
                    now=cycle_at,
                    store=gbpjpy_r38_store,
                    market_data=turtle_market_data,
                    mutations_enabled=mode == "live",
                )
            )
        except MarketDataSlaError as error:
            gbpjpy_r38_live_state = gbpjpy_r38_store.reconcile(mt5, now=cycle_at)
            gbpjpy_r38_manage_reason = "gbpjpy-r38-market-data-fail-closed"
            _log(
                log_path,
                {
                    "event": "GBPJPY_R38_MANAGEMENT_DATA_FAIL_CLOSED",
                    "symbol": "GBPJPY",
                    "message": str(error),
                },
            )
        if gbpjpy_r38_manage_reason not in {
            "no-open-gbpjpy-r38-position",
            "gbpjpy-r38-stop-unchanged",
            "gbpjpy-r38-position-awaiting-reconcile",
            "gbpjpy-r38-24h-exit-due",
        }:
            _log(
                log_path,
                {
                    "event": "GBPJPY_R38_POSITION_MANAGEMENT",
                    "symbol": "GBPJPY",
                    "reason": gbpjpy_r38_manage_reason,
                    "strategy_drawdown_r": str(
                        gbpjpy_r38_live_state.drawdown_r
                    ),
                    "new_york_time": cycle_at.astimezone(_NY).isoformat(),
                },
            )
        highest = max(highest, account_state.balance)
        provider = evaluate_stellar_instant_budget(
            StellarInstantAccountSnapshot(
                initial_balance=PILOT_INITIAL_BALANCE,
                balance=account_state.balance,
                equity=account_state.equity,
                highest_closed_balance=highest,
                previous_active_mll=previous_mll,
            )
        )
        previous_mll = provider.active_mll
        checkpoint = checkpoint.advance(
            highest_closed_balance=highest,
            active_mll=previous_mll,
            updated_at=cycle_at,
        )
        capital_store.store(checkpoint)

        open_stop, floating_loss, pending_stop = _broker_risk(transport)
        aggregate = open_stop + pending_stop + risk.active_reserved_stop_risk()
        posture = request_cibo_posture(
            initial_balance=PILOT_INITIAL_BALANCE,
            balance=account_state.balance,
            equity=account_state.equity,
            current_aggregate_risk=aggregate,
        )
        capital = evaluate_qore_operational_capital_budget(
            provider_budget=provider,
            initial_balance=PILOT_INITIAL_BALANCE,
            balance=account_state.balance,
            equity=account_state.equity,
            highest_closed_balance=highest,
            current_aggregate_stop_risk=aggregate,
            requested_posture=posture,
        )
        accepted_times = [
            item.transitioned_at
            for item in mutation_ledger.records()
            if item.state is FundedNextMt5MutationState.ACCEPTED
        ]
        last_activity = max(
            accepted_times,
            default=activation.authorization.activation_timestamp,
        )
        lifecycle = inactivity_state(last_activity_at=last_activity, now=cycle_at)
        if lifecycle.value != last_lifecycle:
            _log(
                log_path,
                {
                    "event": "ACCOUNT_INACTIVITY_STATE",
                    "state": lifecycle.value,
                    "last_genuine_activity_at": last_activity.isoformat(),
                    "synthetic_trade_forbidden": True,
                },
            )
            last_lifecycle = lifecycle.value

        anchor = _current_anchor(cycle_at)
        processed_anchor: str | None = None
        new_order_blocked = (
            capital.decision is CapitalBudgetDecision.REJECT
            or lifecycle is InactivityState.BLOCKED
            or exit_ledger.has_unresolved
            or gateway.has_unresolved_mutations
        )
        if anchor is not None and not new_order_blocked:
            for symbol in _MARKETS:
                anchor_key = f"{symbol}|{anchor.isoformat()}"
                if anchor_key in state.processed_anchors:
                    continue
                try:
                    failure = vt08_boundary_failures.get(symbol)
                    captured = vt08_boundary_results.get(symbol)
                    if failure is not None:
                        candidate = None
                        reason = f"market-data-sla-fail:{failure}"
                    elif captured is None:
                        raise RuntimeError("vt08-boundary-capture-missing")
                    else:
                        candidate, reason = captured
                    if candidate is None:
                        _log(
                            log_path,
                            {
                                "event": (
                                    "VT08_MARKET_DATA_SLA_FAIL_CLOSED"
                                    if reason.startswith("market-data-sla-fail:")
                                    else "VT08_CAUSAL_ABSTAIN"
                                ),
                                "symbol": symbol,
                                "decision_at": anchor.isoformat(),
                                "reason": reason,
                            },
                        )
                    else:
                        _process_candidate(
                            candidate=candidate,
                            now=cycle_at,
                            mode=mode,
                            gateway=gateway,
                            transport=transport,
                            risk=risk,
                            account_binding_id=fingerprint,
                            provider_budget=provider,
                            capital_budget=capital,
                            account_equity=account_state.equity,
                            log_path=log_path,
                        )
                    processed_anchor = anchor_key
                    state = state.with_cycle(
                        highest_closed_balance=str(highest),
                        active_mll=str(previous_mll),
                        processed_anchor=anchor_key,
                        reconciled_at=cycle_at,
                        heartbeat_at=cycle_at,
                    )
                    store.store(state)
                except Exception as error:
                    _log(
                        log_path,
                        {
                            "event": "ANCHOR_FAIL_CLOSED",
                            "symbol": symbol,
                            "reason": type(error).__name__,
                            "message": str(error),
                        },
                    )

        r34_anchor = current_r34_anchor(cycle_at)
        if r34_anchor is not None and not new_order_blocked:
            r34_anchor_key = f"R34_XAUUSD|{r34_anchor.isoformat()}"
            if r34_anchor_key not in state.processed_anchors:
                try:
                    r34_live_state = r34_store.reconcile(mt5, now=cycle_at)
                    r34_signal, reason = build_r34_live_signal(
                        mt5,
                        now=cycle_at,
                        cognitive=r34_cognitive,
                        state=r34_live_state,
                        market_data=turtle_market_data,
                    )
                    if r34_signal is None:
                        _log(
                            log_path,
                            {
                                "event": "R34_CAUSAL_ABSTAIN",
                                "symbol": "XAUUSD",
                                "decision_at": r34_anchor.isoformat(),
                                "new_york_time": cycle_at.astimezone(_NY).isoformat(),
                                "reason": reason,
                                "strategy_drawdown_r": str(r34_live_state.drawdown_r),
                                "risk_scale": str(r34_live_state.risk_scale),
                            },
                        )
                    else:
                        _process_r34_candidate(
                            signal=r34_signal,
                            now=cycle_at,
                            mode=mode,
                            gateway=gateway,
                            transport=transport,
                            risk=risk,
                            account_binding_id=fingerprint,
                            provider_budget=provider,
                            capital_budget=capital,
                            account_equity=account_state.equity,
                            r34_store=r34_store,
                            log_path=log_path,
                        )
                    processed_anchor = r34_anchor_key
                    state = state.with_cycle(
                        highest_closed_balance=str(highest),
                        active_mll=str(previous_mll),
                        processed_anchor=r34_anchor_key,
                        reconciled_at=cycle_at,
                        heartbeat_at=cycle_at,
                    )
                    store.store(state)
                except Exception as error:
                    _log(
                        log_path,
                        {
                            "event": "R34_ANCHOR_FAIL_CLOSED",
                            "symbol": "XAUUSD",
                            "decision_at": r34_anchor.isoformat(),
                            "new_york_time": cycle_at.astimezone(_NY).isoformat(),
                            "reason": type(error).__name__,
                            "message": str(error),
                        },
                    )
        r38_anchor = current_r38_anchor(cycle_at)
        if r38_anchor is not None and not new_order_blocked:
            r38_anchor_key = f"R38_EURUSD|{r38_anchor.isoformat()}"
            if r38_anchor_key not in state.processed_anchors:
                try:
                    r38_live_state = r38_store.reconcile(mt5, now=cycle_at)
                    r38_signal, reason = build_r38_live_signal(
                        mt5,
                        now=cycle_at,
                        cognitive=r38_cognitive,
                        state=r38_live_state,
                        market_data=turtle_market_data,
                    )
                    if r38_signal is None:
                        _log(
                            log_path,
                            {
                                "event": "R38_CAUSAL_ABSTAIN",
                                "symbol": "EURUSD",
                                "decision_at": r38_anchor.isoformat(),
                                "new_york_time": cycle_at.astimezone(_NY).isoformat(),
                                "reason": reason,
                                "last_trailing_exit_at": (
                                    None
                                    if r38_live_state.trailing_exit_at is None
                                    else r38_live_state.trailing_exit_at.isoformat()
                                ),
                            },
                        )
                    else:
                        _process_r38_candidate(
                            signal=r38_signal,
                            now=cycle_at,
                            mode=mode,
                            gateway=gateway,
                            transport=transport,
                            risk=risk,
                            account_binding_id=fingerprint,
                            provider_budget=provider,
                            capital_budget=capital,
                            account_equity=account_state.equity,
                            r38_store=r38_store,
                            log_path=log_path,
                        )
                    processed_anchor = r38_anchor_key
                    state = state.with_cycle(
                        highest_closed_balance=str(highest),
                        active_mll=str(previous_mll),
                        processed_anchor=r38_anchor_key,
                        reconciled_at=cycle_at,
                        heartbeat_at=cycle_at,
                    )
                    store.store(state)
                except Exception as error:
                    _log(
                        log_path,
                        {
                            "event": "R38_ANCHOR_FAIL_CLOSED",
                            "symbol": "EURUSD",
                            "decision_at": r38_anchor.isoformat(),
                            "new_york_time": cycle_at.astimezone(_NY).isoformat(),
                            "reason": type(error).__name__,
                            "message": str(error),
                        },
                    )

        r43_anchor = current_r43_anchor(cycle_at)
        if r43_anchor is not None and not new_order_blocked:
            r43_anchor_key = f"R43_GBPUSD|{r43_anchor.isoformat()}"
            if r43_anchor_key not in state.processed_anchors:
                try:
                    r43_live_state = r43_store.reconcile(mt5, now=cycle_at)
                    r43_signal, reason = build_r43_live_signal(
                        mt5,
                        now=cycle_at,
                        memory_bundle=r43_memory,
                        state=r43_live_state,
                        market_data=turtle_market_data,
                    )
                    if r43_signal is None:
                        _log(
                            log_path,
                            {
                                "event": "R43_CAUSAL_ABSTAIN",
                                "symbol": "GBPUSD",
                                "decision_at": r43_anchor.isoformat(),
                                "new_york_time": cycle_at.astimezone(_NY).isoformat(),
                                "reason": reason,
                                "strategy_drawdown_r": str(r43_live_state.drawdown_r),
                                "last_trailing_exit_at": (
                                    None
                                    if r43_live_state.trailing_exit_at is None
                                    else r43_live_state.trailing_exit_at.isoformat()
                                ),
                            },
                        )
                    else:
                        _process_r43_candidate(
                            signal=r43_signal,
                            now=cycle_at,
                            mode=mode,
                            gateway=gateway,
                            transport=transport,
                            risk=risk,
                            account_binding_id=fingerprint,
                            provider_budget=provider,
                            capital_budget=capital,
                            account_equity=account_state.equity,
                            r43_store=r43_store,
                            log_path=log_path,
                        )
                    processed_anchor = r43_anchor_key
                    state = state.with_cycle(
                        highest_closed_balance=str(highest),
                        active_mll=str(previous_mll),
                        processed_anchor=r43_anchor_key,
                        reconciled_at=cycle_at,
                        heartbeat_at=cycle_at,
                    )
                    store.store(state)
                except Exception as error:
                    _log(
                        log_path,
                        {
                            "event": "R43_ANCHOR_FAIL_CLOSED",
                            "symbol": "GBPUSD",
                            "decision_at": r43_anchor.isoformat(),
                            "new_york_time": cycle_at.astimezone(_NY).isoformat(),
                            "reason": type(error).__name__,
                            "message": str(error),
                        },
                    )


        gbpjpy_r38_anchor = current_gbpjpy_r38_anchor(cycle_at)
        if gbpjpy_r38_anchor is not None and not new_order_blocked:
            gbpjpy_r38_anchor_key = (
                f"R38_GBPJPY|{gbpjpy_r38_anchor.isoformat()}"
            )
            if gbpjpy_r38_anchor_key not in state.processed_anchors:
                try:
                    gbpjpy_r38_live_state = gbpjpy_r38_store.reconcile(
                        mt5,
                        now=cycle_at,
                    )
                    gbpjpy_r38_signal, reason = build_gbpjpy_r38_live_signal(
                        mt5,
                        now=cycle_at,
                        memory_bundle=gbpjpy_r38_memory,
                        state=gbpjpy_r38_live_state,
                        market_data=turtle_market_data,
                    )
                    if gbpjpy_r38_signal is None:
                        _log(
                            log_path,
                            {
                                "event": "GBPJPY_R38_CAUSAL_ABSTAIN",
                                "symbol": "GBPJPY",
                                "decision_at": gbpjpy_r38_anchor.isoformat(),
                                "new_york_time": cycle_at.astimezone(_NY).isoformat(),
                                "reason": reason,
                                "strategy_drawdown_r": str(
                                    gbpjpy_r38_live_state.drawdown_r
                                ),
                                "last_trailing_exit_at": (
                                    None
                                    if gbpjpy_r38_live_state.trailing_exit_at is None
                                    else gbpjpy_r38_live_state.trailing_exit_at.isoformat()
                                ),
                            },
                        )
                    else:
                        _process_gbpjpy_r38_candidate(
                            signal=gbpjpy_r38_signal,
                            now=cycle_at,
                            mode=mode,
                            gateway=gateway,
                            transport=transport,
                            risk=risk,
                            account_binding_id=fingerprint,
                            provider_budget=provider,
                            capital_budget=capital,
                            account_equity=account_state.equity,
                            gbpjpy_r38_store=gbpjpy_r38_store,
                            log_path=log_path,
                        )
                    processed_anchor = gbpjpy_r38_anchor_key
                    state = state.with_cycle(
                        highest_closed_balance=str(highest),
                        active_mll=str(previous_mll),
                        processed_anchor=gbpjpy_r38_anchor_key,
                        reconciled_at=cycle_at,
                        heartbeat_at=cycle_at,
                    )
                    store.store(state)
                except Exception as error:
                    _log(
                        log_path,
                        {
                            "event": "GBPJPY_R38_ANCHOR_FAIL_CLOSED",
                            "symbol": "GBPJPY",
                            "decision_at": gbpjpy_r38_anchor.isoformat(),
                            "new_york_time": cycle_at.astimezone(_NY).isoformat(),
                            "reason": type(error).__name__,
                            "message": str(error),
                        },
                    )

        if processed_anchor is None:
            state = state.with_cycle(
                highest_closed_balance=str(highest),
                active_mll=str(previous_mll),
                processed_anchor=None,
                reconciled_at=cycle_at,
                heartbeat_at=cycle_at,
            )
            store.store(state)
        time.sleep(_runtime_sleep_seconds(datetime.now(UTC)))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=("shadow", "live"), default="shadow")
    parser.add_argument(
        "--activation",
        type=Path,
        default=Path("var/fundednext/live-activation.json"),
    )
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    lock = SingleWriterRuntimeLock(root / "var" / "fundednext" / "runtime.lock")
    try:
        with lock:
            run(root, mode=args.mode, activation_path=(root / args.activation))
    finally:
        mt5.shutdown()


if __name__ == "__main__":
    main()
