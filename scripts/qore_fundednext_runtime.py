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
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from functools import partial
from importlib import import_module
import sys
import time
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any

import MetaTrader5 as mt5  # type: ignore

from qore.infrastructure.account_wide_risk import (
    AccountRiskSnapshot,
    ReservationState,
    RiskDecision,
    TraderLineage,
)
from qore.infrastructure.broker_risk_sizing import BrokerMinimumVolumeRiskRejectError
from qore.infrastructure.account_wide_risk_ledger import (
    DurableAccountWideRiskEngine,
    DurableAccountWideRiskLedger,
)
from qore.infrastructure.fundednext_capitalization_mission import (
    CapitalizationMissionSnapshot,
    CapitalizationMissionState,
    DurableCapitalizationMissionStore,
    build_5k_mission_config,
    evaluate_capitalization_mission,
)
from qore.infrastructure.fundednext_certified_policy import (
    CertifiedStellarInstantPolicyBundle,
    load_certified_stellar_instant_policy,
)
from qore.infrastructure.fundednext_live_activation import load_verified_live_activation
from qore.infrastructure.fundednext_live_guard import (
    LIVE_ENTRY_ANCHORS_NY,
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
from qore.infrastructure.fundednext_mt5 import Mt5SymbolSpecification
from qore.infrastructure.fundednext_mt5_clock import (
    NEW_YORK_TZ,
    normalise_fundednext_server_epoch,
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
    opening_commission_per_lot,
)
from qore.infrastructure.market_test_environment import (
    MarketRuntimeEnvironment,
    MarketTestAccountIdentity,
)
from qore.infrastructure.market_boundary_actor import (
    MarketBoundaryJob,
    MarketBoundaryResult,
    ResidentMarketActorPool,
)
from qore.infrastructure.pretrade_safety import (
    ExecutionSafetySwitchSnapshot,
    ExecutionSwitchState,
)
from qore.infrastructure.trader_execution_profile import M5_PROFILE
from qore.infrastructure.m5_boundary_cache import (
    M5BoundaryCache,
    M5BoundarySnapshot,
    await_boundary_snapshots as await_m5_boundary_snapshots,
    boundary_to_arm as m5_boundary_to_arm,
)
from qore.infrastructure.r34_xauusd_live import (
    R34LiveSignal,
    R34LiveState,
    R34LiveStateStore,
    build_live_signal as build_r34_live_signal,
    build_r34_risk_request,
    current_anchor as current_r34_anchor,
    load_cognitive as load_r34_cognitive,
)
from qore.infrastructure.r38_eurusd_live import (
    R38LiveSignal,
    R38LiveState,
    R38LiveStateStore,
    build_live_signal as build_r38_live_signal,
    build_r38_risk_request,
    current_anchor as current_r38_anchor,
    load_cognitive as load_r38_cognitive,
    manage_open_position as manage_r38_open_position,
)
from qore.infrastructure.r43_gbpusd_live import (
    R43LiveSignal,
    R43LiveState,
    R43LiveStateStore,
    build_live_signal as build_r43_live_signal,
    build_r43_risk_request,
    current_anchor as current_r43_anchor,
    load_memory as load_r43_memory,
    manage_open_position as manage_r43_open_position,
)
from qore.infrastructure.r38_gbpjpy_live import (
    R38GbpJpyLiveSignal,
    R38GbpJpyLiveState,
    R38GbpJpyLiveStateStore,
    build_live_signal as build_gbpjpy_r38_live_signal,
    build_r38_gbpjpy_risk_request,
    current_anchor as current_gbpjpy_r38_anchor,
    load_memory as load_gbpjpy_r38_memory,
    manage_open_position as manage_gbpjpy_r38_open_position,
)
from qore.infrastructure.r42_audjpy_live import (
    BOUNDARY_ARM_LEAD as AUDJPY_R42_BOUNDARY_ARM_LEAD,
    ENTRY_SLA as AUDJPY_R42_ENTRY_SLA,
    NORMAL_FEED_REFRESH_SECONDS as AUDJPY_R42_FEED_REFRESH_SECONDS,
    MEMORY_SHA256 as AUDJPY_R42_MEMORY_SHA256,
    R42AudJpyLiveSignal,
    R42AudJpyLiveState,
    R42AudJpyLiveStateStore,
    build_live_signal as build_audjpy_r42_live_signal,
    build_r42_audjpy_risk_request,
    load_memory as load_audjpy_r42_memory,
    manage_open_position as manage_audjpy_r42_open_position,
)
from qore.infrastructure.vt31_nas100_live import (
    DECISION_DEADLINE as VT31_DECISION_DEADLINE,
    Vt31Nas100M1Cache,
    await_boundary_snapshot as await_vt31_boundary_snapshot,
    boundary_to_arm as vt31_boundary_to_arm,
)
from qore.infrastructure.vt31_nas100_state import Vt31Nas100LiveStateStore
from qore.infrastructure.traders.vt08_b01_r3_8 import (
    OWNER_FOREX_ENTRY_ANCHORS,
    Vt08B01Bar,
    Vt08B01Candidate,
    evaluate_b01_at_entry,
)
from qore.infrastructure.vt08_forex_cibo_operational import (
    Vt08ForexCiboDecision,
    Vt08ForexCiboPosture,
    evaluate_vt08_forex_cibo,
)
from qore.infrastructure.vt08_forex_fundednext_sizing import (
    build_certified_vt08_forex_cibo_request,
)
from qore.kernel.result import Failure

# Load the script-layer VT31 adapter dynamically so existing trader mypy
# regressions do not type-check the historical research graph it reuses.
_vt31_adapter = import_module("vt31_nas100_runtime_adapter")
evaluate_vt31_boundary = _vt31_adapter.evaluate_boundary
prepare_vt31_boundary = _vt31_adapter.prepare_boundary
manage_vt31_open_trade = _vt31_adapter.manage_open_trade
process_vt31_virtual_oco = _vt31_adapter.process_virtual_oco
reconcile_vt31_pending = _vt31_adapter.reconcile_pending
vt31_runtime_started_fields = _vt31_adapter.runtime_started_fields
shadow_vt31_basket = _vt31_adapter.shadow_basket
submit_vt31_single_live = _vt31_adapter.submit_single_live
warm_vt31_runtime = _vt31_adapter.warm_runtime

_NY = NEW_YORK_TZ
_MARKETS = ("AUDJPY", "GBPUSD", "GBPJPY")
_EXCLUDED_LEGACY_TRADERS = ("VT09",)
_EXPECTED_SERVER = "FundedNext-Server"
_ACCOUNT_REF = "fundednext-stellar-instant-live"
_LOOP_SECONDS = AUDJPY_R42_FEED_REFRESH_SECONDS
_ANCHOR_GRACE = timedelta(seconds=30)
_HISTORY_DAYS = 14
_HISTORY_M15_BARS = _HISTORY_DAYS * 24 * 4 + 96
_DISCOVERY_DAYS = 7


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


def _vt31_entry_boundary(anchor: datetime) -> bool:
    """Only the certified 10:00-11:00 NY Silver Bullet admission window."""
    local = anchor.astimezone(_NY)
    return local.hour == 10 and 1 <= local.minute <= 59


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
        provider_symbol = str(order.symbol)
        qore_symbol = "NAS100" if provider_symbol == "NDX100" else provider_symbol
        commission_per_lot = opening_commission_per_lot(
            qore_symbol,
            executable_entry=entry,
            contract_size=spec.contract_size,
        )
        pending_stop += (
            abs(entry - stop) / spec.tick_size * spec.tick_value
            + commission_per_lot
        ) * volume
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


def _latency_ms(started_at: datetime, finished_at: datetime) -> int:
    return int((finished_at - started_at).total_seconds() * 1000)


def _log_market_decision_telemetry(
    *,
    log_path: Path,
    anchor: datetime,
    snapshot: M5BoundarySnapshot,
    result: MarketBoundaryResult,
) -> None:
    _log(
        log_path,
        {
            "event": "MARKET_BOUNDARY_DECISION_TELEMETRY",
            "trader": result.identity,
            "symbol": result.symbol,
            "boundary_at": anchor.isoformat(),
            "boundary_at_utc": anchor.astimezone(UTC).isoformat(),
            "boundary_at_new_york": anchor.astimezone(_NY).isoformat(),
            "new_bar_first_seen_at": snapshot.new_bar_first_seen_at.isoformat(),
            "new_bar_first_seen_at_utc": (
                snapshot.new_bar_first_seen_at.astimezone(UTC).isoformat()
            ),
            "new_bar_first_seen_at_new_york": (
                snapshot.new_bar_first_seen_at.astimezone(_NY).isoformat()
            ),
            "market_state_updated_at": snapshot.market_state_updated_at.isoformat(),
            "aggregate_finished_at": snapshot.aggregate_finished_at.isoformat(),
            "strategy_started_at": result.strategy_started_at.isoformat(),
            "strategy_finished_at": result.strategy_finished_at.isoformat(),
            "decision_at_utc": result.strategy_finished_at.astimezone(UTC).isoformat(),
            "decision_at_new_york": (
                result.strategy_finished_at.astimezone(_NY).isoformat()
            ),
            "strategy_timezone": "America/New_York",
            "feed_latency_ms": _latency_ms(
                anchor,
                snapshot.new_bar_first_seen_at,
            ),
            "market_state_latency_ms": _latency_ms(
                snapshot.new_bar_first_seen_at,
                snapshot.market_state_updated_at,
            ),
            "aggregate_latency_ms": _latency_ms(
                snapshot.market_state_updated_at,
                snapshot.aggregate_finished_at,
            ),
            "strategy_latency_ms": result.strategy_latency_ms,
            "decision_latency_ms": _latency_ms(
                anchor,
                result.strategy_finished_at,
            ),
            "candidate": result.signal is not None,
            "error": None if result.error is None else type(result.error).__name__,
        },
    )


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
        if lineage is TraderLineage.VT31_NAS100:
            # VT31 owns its 16:00 NY lifecycle and V4 partial/runner journey.
            continue
        if lineage in {
            TraderLineage.R34_XAUUSD,
            TraderLineage.R38_EURUSD,
            TraderLineage.R43_GBPUSD,
            TraderLineage.R38_GBPJPY,
            TraderLineage.R42_AUDJPY,
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
            elif lineage is TraderLineage.R38_GBPJPY:
                exit_label = "GBPJPY_R38_24H"
            else:
                exit_label = "AUDJPY_R42_24H"
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
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": _exit_filling(str(position.symbol)),
        }
        if exit_label == "VT08_H4":
            request |= {
                "comment": f"qore-h4-exit-{str(position.ticket)}"[:29],
            }
        else:
            request["comment"] = f"qore-exit-{exit_label}-{str(position.ticket)}"[:29]
        checked = mt5.order_check(request)
        if checked is None or int(checked.retcode) != 0:
            _log(
                log_path,
                {"event": "H4_EXIT_CHECK_REJECT", "position": int(position.ticket)},
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
    boundary_utc = candidate.decision_at.astimezone(UTC)
    observed_utc = now.astimezone(UTC)
    _log(
        log_path,
        {
            "event": "VT08_CANDLE_SEEN_STRATEGY_DECISION",
            "trader": "VT08_FOREX",
            "symbol": candidate.symbol,
            "boundary_at_utc": boundary_utc.isoformat(),
            "boundary_at_new_york": boundary_utc.astimezone(_NY).isoformat(),
            "new_bar_first_seen_at_utc": observed_utc.isoformat(),
            "new_bar_first_seen_at_new_york": observed_utc.astimezone(_NY).isoformat(),
            "decision_at_utc": observed_utc.isoformat(),
            "decision_at_new_york": observed_utc.astimezone(_NY).isoformat(),
            "strategy_timezone": "America/New_York",
            "anchor_new_york": candidate.entry_anchor_hour,
        },
    )
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
                "strategy_requested_risk_usd": str(
                    request.strategy_requested_risk_usd
                ),
                "minimum_volume_uplifted": request.minimum_volume_uplifted,
                "requested_stop_risk_usd": str(request.requested_stop_risk),
                "broker_min_volume": str(request.minimum_volume),
                "risk_at_broker_min_volume": str(
                    request.minimum_volume * request.stop_loss_per_volume
                ),
                "aggregate_pre_order_worst_case": str(
                    authorization.aggregate_pre_order_worst_case
                ),
                "provider_headroom": str(authorization.provider_headroom),
                "internal_qore_headroom": str(authorization.internal_qore_headroom),
            },
        )
        return
    if request.minimum_volume_uplifted:
        _log(
            log_path,
            {
                "event": "MINIMUM_BROKER_VOLUME_UPLIFT_AUTHORIZED",
                "symbol": request.qore_symbol,
                "strategy_requested_risk_usd": str(
                    request.strategy_requested_risk_usd
                ),
                "authorized_risk_usd": str(authorization.monetary_stop_loss),
                "authorized_volume": str(authorization.authorized_volume),
                "aggregate_pre_order_worst_case": str(
                    authorization.aggregate_pre_order_worst_case
                ),
                "aggregate_post_order_worst_case": str(
                    authorization.aggregate_post_order_worst_case
                ),
                "internal_qore_headroom": str(authorization.internal_qore_headroom),
            },
        )
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
    send_at = datetime.now(UTC)
    if send_at > setup.expires_at.astimezone(UTC):
        risk.cancel(authorization.authorization_id)
        _log(
            log_path,
            {
                "event": "VT08_LIVE_SEND_FAIL_CLOSED",
                "symbol": candidate.symbol,
                "reason": "setup-expired-before-order-send",
                "order_send_called": False,
            },
        )
        return
    provider_ref = gateway.submit_live(submission, now=send_at)
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
    preflight_snapshot: AccountRiskSnapshot | None = None,
    preflight_spec: Mt5SymbolSpecification | None = None,
) -> None:
    spec = preflight_spec or gateway.read_symbol("XAUUSD", now=now)
    request, base_risk_usd = build_r34_risk_request(
        request_id=f"r34-{signal.signal_fingerprint[:24]}",
        signal=signal,
        provider_spec=spec,
        account_equity=account_equity,
        now=now,
    )
    if preflight_snapshot is None:
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
    else:
        snapshot = preflight_snapshot
        if snapshot.account_binding_id != account_binding_id:
            raise RuntimeError("R34 preflight account binding drift")
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
                "strategy_requested_risk_usd": str(
                    request.strategy_requested_risk_usd
                ),
                "minimum_volume_uplifted": request.minimum_volume_uplifted,
                "requested_stop_risk_usd": str(request.requested_stop_risk),
                "broker_min_volume": str(request.minimum_volume),
                "risk_at_broker_min_volume": str(
                    request.minimum_volume * request.stop_loss_per_volume
                ),
                "aggregate_pre_order_worst_case": str(
                    authorization.aggregate_pre_order_worst_case
                ),
                "provider_headroom": str(authorization.provider_headroom),
                "internal_qore_headroom": str(authorization.internal_qore_headroom),
                "signal_fingerprint": signal.signal_fingerprint,
            },
        )
        return
    if request.minimum_volume_uplifted:
        _log(
            log_path,
            {
                "event": "MINIMUM_BROKER_VOLUME_UPLIFT_AUTHORIZED",
                "symbol": request.qore_symbol,
                "strategy_requested_risk_usd": str(
                    request.strategy_requested_risk_usd
                ),
                "authorized_risk_usd": str(authorization.monetary_stop_loss),
                "authorized_volume": str(authorization.authorized_volume),
                "aggregate_pre_order_worst_case": str(
                    authorization.aggregate_pre_order_worst_case
                ),
                "aggregate_post_order_worst_case": str(
                    authorization.aggregate_post_order_worst_case
                ),
                "internal_qore_headroom": str(authorization.internal_qore_headroom),
            },
        )
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
    send_at = datetime.now(UTC)
    deadline = signal.entry_at.astimezone(UTC) + M5_PROFILE.order_send_deadline
    if send_at > deadline:
        risk.cancel(authorization.authorization_id)
        _log(
            log_path,
            {
                "event": "R34_LIVE_SEND_FAIL_CLOSED",
                "symbol": "XAUUSD",
                "signal_fingerprint": signal.signal_fingerprint,
                "reason": "m5-order-send-deadline-expired",
                "deadline_at": deadline.isoformat(),
                "observed_at": send_at.isoformat(),
                "order_send_called": False,
            },
        )
        return
    provider_ref = gateway.submit_live(submission, now=send_at)
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
    preflight_snapshot: AccountRiskSnapshot | None = None,
    preflight_spec: Mt5SymbolSpecification | None = None,
) -> None:
    spec = preflight_spec or gateway.read_symbol("EURUSD", now=now)
    request, base_risk_usd = build_r38_risk_request(
        request_id=f"r38-{signal.signal_fingerprint[:24]}",
        signal=signal,
        provider_spec=spec,
        account_equity=account_equity,
        now=now,
    )
    if preflight_snapshot is None:
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
    else:
        snapshot = preflight_snapshot
        if snapshot.account_binding_id != account_binding_id:
            raise RuntimeError("R38 preflight account binding drift")
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
                "strategy_requested_risk_usd": str(
                    request.strategy_requested_risk_usd
                ),
                "minimum_volume_uplifted": request.minimum_volume_uplifted,
                "requested_stop_risk_usd": str(request.requested_stop_risk),
                "broker_min_volume": str(request.minimum_volume),
                "risk_at_broker_min_volume": str(
                    request.minimum_volume * request.stop_loss_per_volume
                ),
                "aggregate_pre_order_worst_case": str(
                    authorization.aggregate_pre_order_worst_case
                ),
                "provider_headroom": str(authorization.provider_headroom),
                "internal_qore_headroom": str(authorization.internal_qore_headroom),
                "signal_fingerprint": signal.signal_fingerprint,
            },
        )
        return
    if request.minimum_volume_uplifted:
        _log(
            log_path,
            {
                "event": "MINIMUM_BROKER_VOLUME_UPLIFT_AUTHORIZED",
                "symbol": request.qore_symbol,
                "strategy_requested_risk_usd": str(
                    request.strategy_requested_risk_usd
                ),
                "authorized_risk_usd": str(authorization.monetary_stop_loss),
                "authorized_volume": str(authorization.authorized_volume),
                "aggregate_pre_order_worst_case": str(
                    authorization.aggregate_pre_order_worst_case
                ),
                "aggregate_post_order_worst_case": str(
                    authorization.aggregate_post_order_worst_case
                ),
                "internal_qore_headroom": str(authorization.internal_qore_headroom),
            },
        )
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
    send_at = datetime.now(UTC)
    deadline = signal.entry_at.astimezone(UTC) + M5_PROFILE.order_send_deadline
    if send_at > deadline:
        risk.cancel(authorization.authorization_id)
        _log(
            log_path,
            {
                "event": "R38_LIVE_SEND_FAIL_CLOSED",
                "symbol": "EURUSD",
                "signal_fingerprint": signal.signal_fingerprint,
                "reason": "m5-order-send-deadline-expired",
                "deadline_at": deadline.isoformat(),
                "observed_at": send_at.isoformat(),
                "order_send_called": False,
            },
        )
        return
    provider_ref = gateway.submit_live(submission, now=send_at)
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
    preflight_snapshot: AccountRiskSnapshot | None = None,
    preflight_spec: Mt5SymbolSpecification | None = None,
) -> None:
    spec = preflight_spec or gateway.read_symbol("GBPUSD", now=now)
    request, base_risk_usd = build_r43_risk_request(
        request_id=f"r43-{signal.signal_fingerprint[:24]}",
        signal=signal,
        provider_spec=spec,
        account_equity=account_equity,
        now=now,
    )
    if preflight_snapshot is None:
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
    else:
        snapshot = preflight_snapshot
        if snapshot.account_binding_id != account_binding_id:
            raise RuntimeError("R43 preflight account binding drift")
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
                "strategy_requested_risk_usd": str(
                    request.strategy_requested_risk_usd
                ),
                "minimum_volume_uplifted": request.minimum_volume_uplifted,
                "requested_stop_risk_usd": str(request.requested_stop_risk),
                "broker_min_volume": str(request.minimum_volume),
                "risk_at_broker_min_volume": str(
                    request.minimum_volume * request.stop_loss_per_volume
                ),
                "aggregate_pre_order_worst_case": str(
                    authorization.aggregate_pre_order_worst_case
                ),
                "provider_headroom": str(authorization.provider_headroom),
                "internal_qore_headroom": str(authorization.internal_qore_headroom),
                "signal_fingerprint": signal.signal_fingerprint,
            },
        )
        return
    if request.minimum_volume_uplifted:
        _log(
            log_path,
            {
                "event": "MINIMUM_BROKER_VOLUME_UPLIFT_AUTHORIZED",
                "symbol": request.qore_symbol,
                "strategy_requested_risk_usd": str(
                    request.strategy_requested_risk_usd
                ),
                "authorized_risk_usd": str(authorization.monetary_stop_loss),
                "authorized_volume": str(authorization.authorized_volume),
                "aggregate_pre_order_worst_case": str(
                    authorization.aggregate_pre_order_worst_case
                ),
                "aggregate_post_order_worst_case": str(
                    authorization.aggregate_post_order_worst_case
                ),
                "internal_qore_headroom": str(authorization.internal_qore_headroom),
            },
        )
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
    send_at = datetime.now(UTC)
    deadline = signal.entry_at.astimezone(UTC) + M5_PROFILE.order_send_deadline
    if send_at > deadline:
        risk.cancel(authorization.authorization_id)
        _log(
            log_path,
            {
                "event": "R43_LIVE_SEND_FAIL_CLOSED",
                "symbol": "GBPUSD",
                "signal_fingerprint": signal.signal_fingerprint,
                "reason": "m5-order-send-deadline-expired",
                "deadline_at": deadline.isoformat(),
                "observed_at": send_at.isoformat(),
                "order_send_called": False,
            },
        )
        return
    provider_ref = gateway.submit_live(submission, now=send_at)
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
    preflight_snapshot: AccountRiskSnapshot | None = None,
    preflight_spec: Mt5SymbolSpecification | None = None,
) -> None:
    spec = preflight_spec or gateway.read_symbol("GBPJPY", now=now)
    request, base_risk_usd = build_r38_gbpjpy_risk_request(
        request_id=f"gbpjpy-r38-{signal.signal_fingerprint[:24]}",
        signal=signal,
        provider_spec=spec,
        account_equity=account_equity,
        now=now,
    )
    if preflight_snapshot is None:
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
    else:
        snapshot = preflight_snapshot
        if snapshot.account_binding_id != account_binding_id:
            raise RuntimeError("GBPJPY R38 preflight account binding drift")
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
                "strategy_requested_risk_usd": str(
                    request.strategy_requested_risk_usd
                ),
                "minimum_volume_uplifted": request.minimum_volume_uplifted,
                "requested_stop_risk_usd": str(request.requested_stop_risk),
                "broker_min_volume": str(request.minimum_volume),
                "risk_at_broker_min_volume": str(
                    request.minimum_volume * request.stop_loss_per_volume
                ),
                "aggregate_pre_order_worst_case": str(
                    authorization.aggregate_pre_order_worst_case
                ),
                "provider_headroom": str(authorization.provider_headroom),
                "internal_qore_headroom": str(authorization.internal_qore_headroom),
                "signal_fingerprint": signal.signal_fingerprint,
            },
        )
        return

    if request.minimum_volume_uplifted:
        _log(
            log_path,
            {
                "event": "MINIMUM_BROKER_VOLUME_UPLIFT_AUTHORIZED",
                "symbol": request.qore_symbol,
                "strategy_requested_risk_usd": str(
                    request.strategy_requested_risk_usd
                ),
                "authorized_risk_usd": str(authorization.monetary_stop_loss),
                "authorized_volume": str(authorization.authorized_volume),
                "aggregate_pre_order_worst_case": str(
                    authorization.aggregate_pre_order_worst_case
                ),
                "aggregate_post_order_worst_case": str(
                    authorization.aggregate_post_order_worst_case
                ),
                "internal_qore_headroom": str(authorization.internal_qore_headroom),
            },
        )
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

    send_at = datetime.now(UTC)
    deadline = signal.entry_at.astimezone(UTC) + M5_PROFILE.order_send_deadline
    if send_at > deadline:
        risk.cancel(authorization.authorization_id)
        _log(
            log_path,
            {
                "event": "GBPJPY_R38_LIVE_SEND_FAIL_CLOSED",
                "symbol": "GBPJPY",
                "signal_fingerprint": signal.signal_fingerprint,
                "reason": "m5-order-send-deadline-expired",
                "deadline_at": deadline.isoformat(),
                "observed_at": send_at.isoformat(),
                "order_send_called": False,
            },
        )
        return
    provider_ref = gateway.submit_live(submission, now=send_at)
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


def _process_audjpy_r42_candidate(
    *,
    signal: R42AudJpyLiveSignal,
    now: datetime,
    mode: str,
    gateway: FundedNextLiveMt5ExecutionGateway,
    transport: MetaTrader5FundedNextLiveTransport,
    risk: DurableAccountWideRiskEngine,
    account_binding_id: str,
    provider_budget: StellarInstantRiskBudget,
    capital_budget: QoreOperationalCapitalBudget,
    account_equity: Decimal,
    audjpy_r42_store: R42AudJpyLiveStateStore,
    log_path: Path,
    preflight_snapshot: AccountRiskSnapshot | None = None,
    preflight_spec: Mt5SymbolSpecification | None = None,
) -> None:
    deadline = signal.entry_at.astimezone(UTC) + AUDJPY_R42_ENTRY_SLA

    def stage_time(stage: str) -> datetime | None:
        observed = datetime.now(UTC)
        if observed > deadline:
            _log(
                log_path,
                {
                    "event": "AUDJPY_R42_SLA_FAIL_CLOSED",
                    "symbol": "AUDJPY",
                    "stage": stage,
                    "signal_fingerprint": signal.signal_fingerprint,
                    "entry_at": signal.entry_at.isoformat(),
                    "deadline_at": deadline.isoformat(),
                    "observed_at": observed.isoformat(),
                    "latency_ms": int((observed - signal.entry_at).total_seconds() * 1000),
                    "order_send_called": False,
                },
            )
            return None
        return observed

    processing_at = stage_time("before-symbol-read")
    if processing_at is None:
        return
    spec = preflight_spec or gateway.read_symbol("AUDJPY", now=processing_at)

    request_at = stage_time("before-risk-request")
    if request_at is None:
        return
    request, base_risk_usd = build_r42_audjpy_risk_request(
        request_id=f"audjpy-r42-{signal.signal_fingerprint[:24]}",
        signal=signal,
        provider_spec=spec,
        account_equity=account_equity,
        now=request_at,
    )

    if preflight_snapshot is None:
        open_stop, floating_loss, pending_stop = _broker_risk(transport)
        account_state = gateway.read_account(now=request_at)
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
            reconciled_at=request_at,
        )
    else:
        snapshot = preflight_snapshot
        if snapshot.account_binding_id != account_binding_id:
            raise RuntimeError("AUDJPY R42 preflight account binding drift")

    authorize_at = stage_time("before-account-wide-risk")
    if authorize_at is None:
        return
    if risk.recovery_required:
        risk.complete_boot_reconciliation(snapshot, now=authorize_at)
    authorization = risk.authorize(request, snapshot, now=authorize_at)
    if authorization.decision is RiskDecision.REJECT:
        _log(
            log_path,
            {
                "event": "AUDJPY_R42_RISK_REJECT",
                "symbol": "AUDJPY",
                "reason": authorization.reason,
                "strategy_requested_risk_usd": str(
                    request.strategy_requested_risk_usd
                ),
                "minimum_volume_uplifted": request.minimum_volume_uplifted,
                "requested_stop_risk_usd": str(request.requested_stop_risk),
                "broker_min_volume": str(request.minimum_volume),
                "risk_at_broker_min_volume": str(
                    request.minimum_volume * request.stop_loss_per_volume
                ),
                "aggregate_pre_order_worst_case": str(
                    authorization.aggregate_pre_order_worst_case
                ),
                "provider_headroom": str(authorization.provider_headroom),
                "internal_qore_headroom": str(authorization.internal_qore_headroom),
                "signal_fingerprint": signal.signal_fingerprint,
                "latency_ms": int((authorize_at - signal.entry_at).total_seconds() * 1000),
            },
        )
        return

    submission_at = stage_time("before-submission-build")
    if submission_at is None:
        risk.cancel(authorization.authorization_id)
        return
    if request.minimum_volume_uplifted:
        _log(
            log_path,
            {
                "event": "MINIMUM_BROKER_VOLUME_UPLIFT_AUTHORIZED",
                "symbol": request.qore_symbol,
                "strategy_requested_risk_usd": str(
                    request.strategy_requested_risk_usd
                ),
                "authorized_risk_usd": str(authorization.monetary_stop_loss),
                "authorized_volume": str(authorization.authorized_volume),
                "aggregate_pre_order_worst_case": str(
                    authorization.aggregate_pre_order_worst_case
                ),
                "aggregate_post_order_worst_case": str(
                    authorization.aggregate_post_order_worst_case
                ),
                "internal_qore_headroom": str(authorization.internal_qore_headroom),
            },
        )
    submission = build_account_bound_submission(
        authorization,
        switch=ExecutionSafetySwitchSnapshot(
            state=ExecutionSwitchState.ENABLED,
            observed_at=submission_at,
            reason="qore AUDJPY R42 certified runtime safety gate enabled",
        ),
        authorized_at=submission_at,
        submitted_at=submission_at,
    )

    shadow_at = stage_time("before-broker-order-check")
    if shadow_at is None:
        risk.cancel(authorization.authorization_id)
        return
    shadow = gateway.shadow_check(submission, now=shadow_at)
    checked_at = stage_time("after-broker-order-check")
    if checked_at is None:
        risk.cancel(authorization.authorization_id)
        return
    if not shadow.broker_valid:
        risk.cancel(authorization.authorization_id)
        _log(
            log_path,
            {
                "event": "AUDJPY_R42_SHADOW_REJECT",
                "symbol": "AUDJPY",
                "reason": shadow.reason,
                "signal_fingerprint": signal.signal_fingerprint,
            },
        )
        return

    event = {
        "symbol": "AUDJPY",
        "signal_fingerprint": signal.signal_fingerprint,
        "timeframe": signal.timeframe,
        "target_rank": signal.target_rank,
        "target_route": signal.target_route,
        "source_scheme": signal.source_scheme,
        "authority_tier": signal.authority_tier,
        "classification": signal.classification,
        "posture": signal.posture,
        "base_risk_scale": str(signal.base_risk_scale),
        "first_layer_fragility_flags": list(signal.first_layer_fragility_flags),
        "first_layer_overlay_scale": str(signal.first_layer_overlay_scale),
        "second_layer_fragility_flags": list(signal.second_layer_fragility_flags),
        "second_layer_overlay_scale": str(signal.second_layer_overlay_scale),
        "risk_scale": str(signal.risk_scale),
        "risk_usd": str(authorization.monetary_stop_loss),
        "volume": str(authorization.authorized_volume),
        "boundary_tick_at": signal.boundary_tick_at.isoformat(),
        "latency_ms": int((checked_at - signal.entry_at).total_seconds() * 1000),
        "entry_sla_ms": int(AUDJPY_R42_ENTRY_SLA.total_seconds() * 1000),
    }
    if mode == "shadow":
        risk.cancel(authorization.authorization_id)
        _log(
            log_path,
            {
                "event": "AUDJPY_R42_SHADOW_PASS",
                **event,
                "retcode": shadow.retcode,
            },
        )
        return

    send_at = stage_time("before-order-send")
    if send_at is None:
        risk.cancel(authorization.authorization_id)
        return
    provider_ref = gateway.submit_live(submission, now=send_at)
    risk.record_full_fill(authorization.authorization_id)
    client_order_id = f"qore-{submission.idempotency_key.value.hex[:24]}"
    audjpy_r42_store.mark_open(
        client_order_id=client_order_id,
        signal=signal,
        base_risk_usd=base_risk_usd,
    )
    accepted_at = datetime.now(UTC)
    _log(
        log_path,
        {
            "event": "AUDJPY_R42_LIVE_SUBMIT_ACCEPTED",
            **event,
            "risk_authorization": authorization.authorization_id,
            "provider_order_ref": provider_ref,
            "order_send_started_at": send_at.isoformat(),
            "provider_ack_at": accepted_at.isoformat(),
            "send_started_latency_ms": int((send_at - signal.entry_at).total_seconds() * 1000),
            "provider_ack_latency_ms": int((accepted_at - signal.entry_at).total_seconds() * 1000),
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
    startup_memory = ThreadPoolExecutor(
        max_workers=6,
        thread_name_prefix="qore-startup-memory",
    )
    r34_cognitive_future = startup_memory.submit(
        load_r34_cognitive,
        root
        / "var"
        / "r34"
        / "cognitive-v3"
        / "turtle-soup-xauusd-specialist-cognitive-memory-v3.json",
    )
    r38_cognitive_future = startup_memory.submit(
        load_r38_cognitive,
        root
        / "var"
        / "r38"
        / "cognitive-v3"
        / "turtle-soup-eurusd-specialist-cognitive-memory-v3.json",
    )
    r43_memory_future = startup_memory.submit(
        load_r43_memory,
        root / "runtime_data" / "gbpusd" / "r43-r32-regime-memory.json",
    )
    gbpjpy_r38_memory_future = startup_memory.submit(
        load_gbpjpy_r38_memory,
        root / "runtime_data" / "gbpjpy" / "r38-confidence-tier-memory.json",
    )
    audjpy_r42_memory_future = startup_memory.submit(
        load_audjpy_r42_memory,
        root / "runtime_data" / "audjpy" / "r42-causal-authority-memory.json",
    )
    vt31_memory_future = startup_memory.submit(warm_vt31_runtime)
    r34_store = R34LiveStateStore(state_dir / "r34-state.json")
    r34_store.reconcile(mt5, now=datetime.now(UTC))
    r38_store = R38LiveStateStore(state_dir / "r38-state.json")
    r38_store.reconcile(mt5, now=datetime.now(UTC))
    r43_store = R43LiveStateStore(state_dir / "r43-state.json")
    r43_store.reconcile(mt5, now=datetime.now(UTC))
    gbpjpy_r38_store = R38GbpJpyLiveStateStore(state_dir / "r38-gbpjpy-state.json")
    gbpjpy_r38_store.reconcile(mt5, now=datetime.now(UTC))
    audjpy_r42_store = R42AudJpyLiveStateStore(state_dir / "r42-audjpy-state.json")
    audjpy_r42_store.reconcile(mt5, now=datetime.now(UTC))
    m5_caches: dict[str, M5BoundaryCache] = {
        "XAUUSD": M5BoundaryCache(
            symbol="XAUUSD",
            error_prefix="R34 XAUUSD",
        ),
        "EURUSD": M5BoundaryCache(
            symbol="EURUSD",
            error_prefix="R38 EURUSD",
        ),
        "GBPUSD": M5BoundaryCache(
            symbol="GBPUSD",
            error_prefix="R43 GBPUSD",
        ),
        "GBPJPY": M5BoundaryCache(
            symbol="GBPJPY",
            error_prefix="GBPJPY R38",
        ),
        "AUDJPY": M5BoundaryCache(
            symbol="AUDJPY",
            error_prefix="AUDJPY R42",
        ),
    }
    preload_at = datetime.now(UTC)
    for cache in m5_caches.values():
        cache.preload(mt5, now=preload_at)
    audjpy_r42_cache = m5_caches["AUDJPY"]
    vt31_store = Vt31Nas100LiveStateStore(state_dir / "vt31-nas100-state.json")
    vt31_cache = Vt31Nas100M1Cache()
    vt31_cache.preload(mt5, now=datetime.now(UTC))
    try:
        r34_cognitive = r34_cognitive_future.result()
        r38_cognitive = r38_cognitive_future.result()
        r43_memory = r43_memory_future.result()
        gbpjpy_r38_memory = gbpjpy_r38_memory_future.result()
        audjpy_r42_memory = audjpy_r42_memory_future.result()
        vt31_memory_fingerprint = vt31_memory_future.result()
        if vt31_memory_fingerprint != _vt31_adapter.CIBO_MEMORY_FINGERPRINT:
            raise RuntimeError("VT31 CIBO memory fingerprint drift")
    finally:
        startup_memory.shutdown(wait=True, cancel_futures=True)

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

    def load_current_certified_policy() -> CertifiedStellarInstantPolicyBundle:
        bundle = load_certified_stellar_instant_policy(
            refresh_path=state_dir / "provider-rules-refresh.json",
            account_binding_id=fingerprint,
            account_size=PILOT_INITIAL_BALANCE,
        )
        # The refresh subprocess records observed_at when it finishes.  Always
        # resolve against a clock sampled after reading that evidence; using
        # the cycle timestamp captured before refresh makes fresh evidence
        # appear to be from the future and creates an endless fail-closed loop.
        evaluated_at = datetime.now(UTC)
        resolved = bundle.resolve_for_risk(evaluated_at)
        if isinstance(resolved, Failure):
            raise RuntimeError(f"certified-prop-policy-unavailable:{resolved.error}")
        return bundle

    refresh_provider_rules_before_submission()
    certified_policy = load_current_certified_policy()
    certified_policy_last_reload = certified_policy.observed_at
    mission_store = DurableCapitalizationMissionStore(state_dir / "capitalization-mission.json")
    mission_config = build_5k_mission_config(
        account_identity_fingerprint=fingerprint,
        start_balance=PILOT_INITIAL_BALANCE,
        purchase_cash_required=(certified_policy.facts.stellar_instant_5k_purchase_price_usd),
        reward_split_fraction=certified_policy.facts.reward_split_tier_1_2,
    )
    mission_snapshot: CapitalizationMissionSnapshot = evaluate_capitalization_mission(
        config=mission_config,
        closed_balance=Decimal(str(account_info.balance)),
        equity=Decimal(str(account_info.equity)),
        now=datetime.now(UTC),
        previous=mission_store.load(),
        defend=False,
        payout_eligible=False,
    )
    mission_store.store(mission_snapshot)
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
            **vt31_runtime_started_fields(),
            "loaded_traders": [
                "VT08",
                "TURTLE_SOUP_XAUUSD_R34",
                "TURTLE_SOUP_EURUSD_R38",
                "TURTLE_SOUP_GBPUSD_R43",
                "TURTLE_SOUP_GBPJPY_R38",
                "TURTLE_SOUP_AUDJPY_R42",
                "VT31_NAS100",
            ],
            "single_mt5_writer": True,
            "account_wide_risk_active": True,
            "certified_prop_policy_active": True,
            "certified_prop_policy_observed_at": (certified_policy.observed_at.isoformat()),
            "certified_prop_policy_default_open_risk_fraction": str(
                certified_policy.facts.cumulative_open_risk_fraction
            ),
            "certified_prop_policy_reclassified_open_risk_fraction": str(
                certified_policy.facts.reclassified_open_risk_fraction
            ),
            "certified_prop_policy_stop_loss_required": (certified_policy.facts.stop_loss_required),
            "capitalization_mission_active": True,
            "capitalization_mission_id": mission_snapshot.mission_id,
            "capitalization_mission_state": mission_snapshot.state.value,
            "capitalization_purchase_cash_required": str(mission_snapshot.purchase_cash_required),
            "capitalization_gross_reward_required": str(mission_snapshot.gross_reward_required),
            "capitalization_post_withdrawal_reserve": str(mission_snapshot.post_withdrawal_reserve),
            "capitalization_bank_balance_threshold": str(mission_snapshot.bank_balance_threshold),
            "capitalization_balance_target": str(mission_snapshot.mission_balance_target),
            "capitalization_target_remaining": str(mission_snapshot.target_remaining),
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
            "gbpjpy_r38_memory_sha256": (
                "16a369e8457394642642ca2c7331e32b05644a5656d339cbba06db089f44211f"
            ),
            "audjpy_r42_enabled": True,
            "audjpy_r42_identity": "TURTLE_SOUP_AUDJPY_R42",
            "audjpy_r42_certification": "TURTLE_SOUP_AUDJPY_R43_FINAL_CERTIFICATION_SUITE_V1",
            "audjpy_r42_strategy_timezone": "America/New_York",
            "audjpy_r42_schedule": "EVERY_H1_H4_BOUNDARY_24_7_SERVICE",
            "audjpy_r42_single_position_busy": True,
            "audjpy_r42_lifecycle": "STATIC_OR_PROTECT_DOL_LOCK_M5_SWING_TRAIL_PLUS_24H_EXIT",
            "audjpy_r42_base_risk_fraction": "0.002",
            "audjpy_r42_ensemble": "R38_FROZEN_SIGNAL_BASELINE",
            "audjpy_r42_policy": "AUDJPY_CONFIDENCE_100_075_025",
            "audjpy_r42_first_fragility_policy": ["1", "0.20", "0.05", "0.01"],
            "audjpy_r42_second_fragility_policy": ["1", "0.50", "0.25", "0.10"],
            "audjpy_r42_memory_sha256": AUDJPY_R42_MEMORY_SHA256,
            "audjpy_r42_entry_sla_seconds": str(AUDJPY_R42_ENTRY_SLA.total_seconds()),
            "audjpy_r42_boundary_arm_lead_seconds": str(
                AUDJPY_R42_BOUNDARY_ARM_LEAD.total_seconds()
            ),
            "audjpy_r42_feed_refresh_seconds": str(AUDJPY_R42_FEED_REFRESH_SECONDS),
            "audjpy_r42_boundary_retry_ms": 75,
            "audjpy_r42_history_preload_once": True,
            "audjpy_r42_incremental_cache": True,
            "order_submission_authorized": activation.authorization.order_submission_authorized,
        },
    )
    last_lifecycle: str | None = None

    while True:
        cycle_started = time.monotonic()
        cycle_at = datetime.now(UTC)
        armed_m5_snapshots: dict[str, M5BoundarySnapshot] | None = None
        for symbol, cache in m5_caches.items():
            try:
                cache.refresh_incremental(mt5, now=cycle_at)
            except Exception as error:
                _log(
                    log_path,
                    {
                        "event": "M5_INCREMENTAL_FEED_FAIL_CLOSED",
                        "symbol": symbol,
                        "reason": type(error).__name__,
                        "message": str(error),
                        "observed_at": cycle_at.isoformat(),
                    },
                )
        try:
            vt31_cache.refresh_incremental(mt5, now=cycle_at)
        except Exception as error:
            _log(
                log_path,
                {
                    "event": "VT31_NAS100_INCREMENTAL_FEED_FAIL_CLOSED",
                    "symbol": "NAS100",
                    "reason": type(error).__name__,
                    "message": str(error),
                    "observed_at": cycle_at.isoformat(),
                },
            )

        audjpy_arm_anchor = m5_boundary_to_arm(cycle_at)
        certified_policy_ready = True
        policy_resolution = certified_policy.resolve_for_risk(cycle_at)
        if isinstance(policy_resolution, Failure):
            certified_policy_ready = False

        reload_due = cycle_at - certified_policy_last_reload >= timedelta(minutes=5)
        refresh_due = cycle_at - certified_policy.observed_at >= timedelta(hours=6)
        if audjpy_arm_anchor is None and (reload_due or not certified_policy_ready):
            try:
                if refresh_due:
                    refresh_provider_rules_before_submission()
                certified_policy = load_current_certified_policy()
                certified_policy_last_reload = cycle_at
                mission_config = build_5k_mission_config(
                    account_identity_fingerprint=fingerprint,
                    start_balance=PILOT_INITIAL_BALANCE,
                    purchase_cash_required=(
                        certified_policy.facts.stellar_instant_5k_purchase_price_usd
                    ),
                    reward_split_fraction=(certified_policy.facts.reward_split_tier_1_2),
                )
                certified_policy_ready = True
            except Exception as error:
                certified_policy_ready = False
                _log(
                    log_path,
                    {
                        "event": "CERTIFIED_PROP_POLICY_FAIL_CLOSED",
                        "reason": type(error).__name__,
                        "message": str(error),
                        "observed_at": cycle_at.isoformat(),
                    },
                )
        if audjpy_arm_anchor is not None:
            audjpy_anchor_key = f"R42_AUDJPY|{audjpy_arm_anchor.isoformat()}"
            if audjpy_anchor_key not in state.processed_anchors:
                m5_fast_processed_keys: list[str] = []
                arm_started_at = datetime.now(UTC)
                _log(
                    log_path,
                    {
                        "event": "AUDJPY_R42_BOUNDARY_ARMED",
                        "symbol": "AUDJPY",
                        "decision_at": audjpy_arm_anchor.isoformat(),
                        "armed_at": arm_started_at.isoformat(),
                        "lead_ms": int((audjpy_arm_anchor - arm_started_at).total_seconds() * 1000),
                        "maintenance_frozen": True,
                        "risk_preflight_only": True,
                    },
                )
                try:
                    arm_account = gateway.read_account(now=arm_started_at)
                    gateway.reconcile_unknown(now=arm_started_at)
                    arm_r42_state = audjpy_r42_store.reconcile(
                        mt5,
                        now=arm_started_at,
                    )
                    arm_r34_state = r34_store.reconcile(
                        mt5,
                        now=arm_started_at,
                    )
                    arm_r38_state = r38_store.reconcile(
                        mt5,
                        now=arm_started_at,
                    )
                    arm_r43_state = r43_store.reconcile(
                        mt5,
                        now=arm_started_at,
                    )
                    arm_gbpjpy_state = gbpjpy_r38_store.reconcile(
                        mt5,
                        now=arm_started_at,
                    )
                    arm_highest = max(highest, arm_account.balance)
                    arm_provider = evaluate_stellar_instant_budget(
                        StellarInstantAccountSnapshot(
                            initial_balance=PILOT_INITIAL_BALANCE,
                            balance=arm_account.balance,
                            equity=arm_account.equity,
                            highest_closed_balance=arm_highest,
                            previous_active_mll=previous_mll,
                        )
                    )
                    arm_open_stop, arm_floating_loss, arm_pending_stop = _broker_risk(transport)
                    arm_aggregate = (
                        arm_open_stop + arm_pending_stop + risk.active_reserved_stop_risk()
                    )
                    prior_mission_state = mission_snapshot.state
                    mission_snapshot = evaluate_capitalization_mission(
                        config=mission_config,
                        closed_balance=arm_account.balance,
                        equity=arm_account.equity,
                        now=arm_started_at,
                        previous=mission_snapshot,
                        defend=False,
                        payout_eligible=False,
                    )
                    arm_posture = request_cibo_posture(
                        initial_balance=PILOT_INITIAL_BALANCE,
                        balance=arm_account.balance,
                        equity=arm_account.equity,
                        current_aggregate_risk=arm_aggregate,
                    )
                    if mission_snapshot.state is CapitalizationMissionState.BANK:
                        arm_posture = Vt08ForexCiboPosture.BANK
                    arm_capital = evaluate_qore_operational_capital_budget(
                        provider_budget=arm_provider,
                        initial_balance=PILOT_INITIAL_BALANCE,
                        balance=arm_account.balance,
                        equity=arm_account.equity,
                        highest_closed_balance=arm_highest,
                        current_aggregate_stop_risk=arm_aggregate,
                        requested_posture=arm_posture,
                        certified_open_risk_fraction=(
                            certified_policy.facts.cumulative_open_risk_fraction
                        ),
                    )
                    mission_snapshot = evaluate_capitalization_mission(
                        config=mission_config,
                        closed_balance=arm_account.balance,
                        equity=arm_account.equity,
                        now=arm_started_at,
                        previous=mission_snapshot,
                        defend=(arm_capital.decision is CapitalBudgetDecision.REJECT),
                        payout_eligible=False,
                    )
                    mission_store.store(mission_snapshot)
                    if mission_snapshot.state is not prior_mission_state:
                        _log(
                            log_path,
                            {
                                "event": "CAPITALIZATION_MISSION_STATE_CHANGED",
                                "from_state": prior_mission_state.value,
                                "to_state": mission_snapshot.state.value,
                                "closed_balance": str(arm_account.balance),
                                "target_remaining": str(mission_snapshot.target_remaining),
                                "new_risk_allowed_by_mission": (
                                    mission_snapshot.new_risk_allowed_by_mission
                                ),
                            },
                        )
                    arm_snapshot = AccountRiskSnapshot(
                        account_binding_id=fingerprint,
                        equity=arm_account.equity,
                        margin_used=arm_account.margin,
                        free_margin=arm_account.free_margin,
                        open_stop_worst_case_loss=arm_open_stop,
                        open_floating_loss=arm_floating_loss,
                        pending_broker_worst_case_loss=arm_pending_stop,
                        qore_authorizable_headroom=(arm_capital.qore_authorizable_headroom),
                        provider_budget=arm_provider,
                        reconciled_at=arm_started_at,
                    )
                    arm_specs = {
                        symbol: gateway.read_symbol(symbol, now=arm_started_at)
                        for symbol in (
                            "XAUUSD",
                            "EURUSD",
                            "GBPUSD",
                            "GBPJPY",
                            "AUDJPY",
                        )
                    }
                    accepted_times = [
                        item.transitioned_at
                        for item in mutation_ledger.records()
                        if item.state is FundedNextMt5MutationState.ACCEPTED
                    ]
                    arm_last_activity = max(
                        accepted_times,
                        default=activation.authorization.activation_timestamp,
                    )
                    arm_lifecycle = inactivity_state(
                        last_activity_at=arm_last_activity,
                        now=arm_started_at,
                    )
                    arm_blocked = (
                        arm_capital.decision is CapitalBudgetDecision.REJECT
                        or arm_lifecycle is InactivityState.BLOCKED
                        or exit_ledger.has_unresolved
                        or gateway.has_unresolved_mutations
                        or not certified_policy_ready
                        or not mission_snapshot.new_risk_allowed_by_mission
                    )

                    fast_plan = (
                        (
                            "R43_GBPUSD",
                            "GBPUSD",
                            "R43_CAUSAL_ABSTAIN",
                            partial(
                                _process_r43_candidate,
                                mode=mode,
                                gateway=gateway,
                                transport=transport,
                                risk=risk,
                                account_binding_id=fingerprint,
                                provider_budget=arm_provider,
                                capital_budget=arm_capital,
                                account_equity=arm_account.equity,
                                r43_store=r43_store,
                                log_path=log_path,
                                preflight_snapshot=arm_snapshot,
                                preflight_spec=arm_specs["GBPUSD"],
                            ),
                        ),
                        (
                            "R34_XAUUSD",
                            "XAUUSD",
                            "R34_CAUSAL_ABSTAIN",
                            partial(
                                _process_r34_candidate,
                                mode=mode,
                                gateway=gateway,
                                transport=transport,
                                risk=risk,
                                account_binding_id=fingerprint,
                                provider_budget=arm_provider,
                                capital_budget=arm_capital,
                                account_equity=arm_account.equity,
                                r34_store=r34_store,
                                log_path=log_path,
                                preflight_snapshot=arm_snapshot,
                                preflight_spec=arm_specs["XAUUSD"],
                            ),
                        ),
                        (
                            "R38_GBPJPY",
                            "GBPJPY",
                            "GBPJPY_R38_CAUSAL_ABSTAIN",
                            partial(
                                _process_gbpjpy_r38_candidate,
                                mode=mode,
                                gateway=gateway,
                                transport=transport,
                                risk=risk,
                                account_binding_id=fingerprint,
                                provider_budget=arm_provider,
                                capital_budget=arm_capital,
                                account_equity=arm_account.equity,
                                gbpjpy_r38_store=gbpjpy_r38_store,
                                log_path=log_path,
                                preflight_snapshot=arm_snapshot,
                                preflight_spec=arm_specs["GBPJPY"],
                            ),
                        ),
                        (
                            "R38_EURUSD",
                            "EURUSD",
                            "R38_CAUSAL_ABSTAIN",
                            partial(
                                _process_r38_candidate,
                                mode=mode,
                                gateway=gateway,
                                transport=transport,
                                risk=risk,
                                account_binding_id=fingerprint,
                                provider_budget=arm_provider,
                                capital_budget=arm_capital,
                                account_equity=arm_account.equity,
                                r38_store=r38_store,
                                log_path=log_path,
                                preflight_snapshot=arm_snapshot,
                                preflight_spec=arm_specs["EURUSD"],
                            ),
                        ),
                    )
                    with ResidentMarketActorPool(max_workers=5) as market_actors:

                        def submit_ready_market(
                            symbol: str,
                            snapshot: M5BoundarySnapshot,
                            blocked: bool = arm_blocked,
                            r43_state: R43LiveState = arm_r43_state,
                            r34_state: R34LiveState = arm_r34_state,
                            gbpjpy_state: R38GbpJpyLiveState = arm_gbpjpy_state,
                            r38_state: R38LiveState = arm_r38_state,
                            r42_state: R42AudJpyLiveState = arm_r42_state,
                        ) -> None:
                            if blocked:
                                return
                            evaluate: Callable[[], tuple[Any | None, str]]
                            if symbol == "GBPUSD":
                                identity = "R43_GBPUSD"
                                evaluate = partial(
                                    build_r43_live_signal,
                                    mt5,
                                    now=snapshot.observed_at,
                                    memory_bundle=r43_memory,
                                    state=r43_state,
                                    boundary_snapshot=snapshot,
                                )
                            elif symbol == "XAUUSD":
                                identity = "R34_XAUUSD"
                                evaluate = partial(
                                    build_r34_live_signal,
                                    mt5,
                                    now=snapshot.observed_at,
                                    cognitive=r34_cognitive,
                                    state=r34_state,
                                    boundary_snapshot=snapshot,
                                )
                            elif symbol == "GBPJPY":
                                identity = "R38_GBPJPY"
                                evaluate = partial(
                                    build_gbpjpy_r38_live_signal,
                                    mt5,
                                    now=snapshot.observed_at,
                                    memory_bundle=gbpjpy_r38_memory,
                                    state=gbpjpy_state,
                                    boundary_snapshot=snapshot,
                                )
                            elif symbol == "EURUSD":
                                identity = "R38_EURUSD"
                                evaluate = partial(
                                    build_r38_live_signal,
                                    mt5,
                                    now=snapshot.observed_at,
                                    cognitive=r38_cognitive,
                                    state=r38_state,
                                    boundary_snapshot=snapshot,
                                )
                            elif symbol == "AUDJPY":
                                identity = "R42_AUDJPY"
                                evaluate = partial(
                                    build_audjpy_r42_live_signal,
                                    mt5,
                                    now=snapshot.observed_at,
                                    memory_bundle=audjpy_r42_memory,
                                    state=r42_state,
                                    boundary_snapshot=snapshot,
                                )
                            else:
                                raise RuntimeError(f"unsupported resident M5 market:{symbol}")
                            market_actors.submit(
                                MarketBoundaryJob(
                                    identity=identity,
                                    symbol=symbol,
                                    evaluate=evaluate,
                                )
                            )

                        armed_m5_snapshots = await_m5_boundary_snapshots(
                            mt5,
                            caches=m5_caches,
                            anchor=audjpy_arm_anchor,
                            on_snapshot=submit_ready_market,
                        )
                        boundary_results = {
                            result.identity: result for result in market_actors.results()
                        }
                    boundary_observed = max(
                        item.observed_at for item in armed_m5_snapshots.values()
                    )
                    cycle_at = boundary_observed
                    m5_deadline = audjpy_arm_anchor + M5_PROFILE.decision_deadline
                    for (
                        fast_identity,
                        fast_symbol,
                        abstain_event,
                        process_fast,
                    ) in fast_plan:
                        fast_key = f"{fast_identity}|{audjpy_arm_anchor.isoformat()}"
                        if fast_key in state.processed_anchors:
                            continue
                        m5_fast_processed_keys.append(fast_key)
                        if arm_blocked:
                            _log(
                                log_path,
                                {
                                    "event": "M5_FAST_BOUNDARY_FAIL_CLOSED",
                                    "symbol": fast_symbol,
                                    "decision_at": audjpy_arm_anchor.isoformat(),
                                    "reason": "preflight-new-order-blocked",
                                    "order_send_called": False,
                                },
                            )
                            continue
                        if fast_symbol not in armed_m5_snapshots:
                            _log(
                                log_path,
                                {
                                    "event": "M5_FAST_BOUNDARY_FAIL_CLOSED",
                                    "symbol": fast_symbol,
                                    "decision_at": audjpy_arm_anchor.isoformat(),
                                    "reason": "symbol-boundary-unavailable-within-feed-budget",
                                    "hard_sla_seconds": (
                                        M5_PROFILE.order_send_deadline.total_seconds()
                                    ),
                                    "order_send_called": False,
                                },
                            )
                            continue
                        try:
                            actor_result = boundary_results[fast_identity]
                            _log_market_decision_telemetry(
                                log_path=log_path,
                                anchor=audjpy_arm_anchor,
                                snapshot=armed_m5_snapshots[fast_symbol],
                                result=actor_result,
                            )
                            if actor_result.error is not None:
                                raise actor_result.error
                            fast_signal = actor_result.signal
                            fast_reason = actor_result.reason
                            fast_done = actor_result.strategy_finished_at
                            latency_ms = int((fast_done - audjpy_arm_anchor).total_seconds() * 1000)
                            if fast_done > m5_deadline:
                                _log(
                                    log_path,
                                    {
                                        "event": "M5_FAST_BOUNDARY_FAIL_CLOSED",
                                        "symbol": fast_symbol,
                                        "decision_at": (audjpy_arm_anchor.isoformat()),
                                        "reason": "decision-deadline-expired",
                                        "latency_ms": latency_ms,
                                        "order_send_called": False,
                                    },
                                )
                                continue
                            if fast_signal is None:
                                _log(
                                    log_path,
                                    {
                                        "event": abstain_event,
                                        "symbol": fast_symbol,
                                        "decision_at": (audjpy_arm_anchor.isoformat()),
                                        "observed_at": fast_done.isoformat(),
                                        "latency_ms": latency_ms,
                                        "reason": fast_reason,
                                        "fast_path": True,
                                        "strategy_started_at": (
                                            actor_result.strategy_started_at.isoformat()
                                        ),
                                        "strategy_finished_at": (
                                            actor_result.strategy_finished_at.isoformat()
                                        ),
                                        "strategy_latency_ms": (actor_result.strategy_latency_ms),
                                    },
                                )
                            else:
                                process_fast(signal=fast_signal, now=fast_done)
                        except BrokerMinimumVolumeRiskRejectError as risk_reject:
                            _log(
                                log_path,
                                {
                                    "event": "RISK_REJECT_MINIMUM_BROKER_VOLUME",
                                    "symbol": fast_symbol,
                                    "decision_at": audjpy_arm_anchor.isoformat(),
                                    "candidate": True,
                                    "order_send_called": False,
                                    **risk_reject.telemetry(),
                                },
                            )
                        except Exception as fast_error:
                            _log(
                                log_path,
                                {
                                    "event": "M5_FAST_BOUNDARY_FAIL_CLOSED",
                                    "symbol": fast_symbol,
                                    "decision_at": audjpy_arm_anchor.isoformat(),
                                    "reason": type(fast_error).__name__,
                                    "message": str(fast_error),
                                    "order_send_called": False,
                                },
                            )
                    if arm_blocked:
                        _log(
                            log_path,
                            {
                                "event": "AUDJPY_R42_BOUNDARY_FAIL_CLOSED",
                                "symbol": "AUDJPY",
                                "decision_at": audjpy_arm_anchor.isoformat(),
                                "reason": "preflight-new-order-blocked",
                                "observed_at": boundary_observed.isoformat(),
                                "latency_ms": int(
                                    (boundary_observed - audjpy_arm_anchor).total_seconds() * 1000
                                ),
                            },
                        )
                    elif "AUDJPY" not in armed_m5_snapshots:
                        _log(
                            log_path,
                            {
                                "event": "AUDJPY_R42_BOUNDARY_FAIL_CLOSED",
                                "symbol": "AUDJPY",
                                "decision_at": audjpy_arm_anchor.isoformat(),
                                "reason": "symbol-boundary-unavailable-within-feed-budget",
                                "observed_at": boundary_observed.isoformat(),
                                "latency_ms": int(
                                    (boundary_observed - audjpy_arm_anchor).total_seconds() * 1000
                                ),
                                "hard_sla_seconds": (
                                    AUDJPY_R42_ENTRY_SLA.total_seconds()
                                ),
                                "order_send_called": False,
                            },
                        )
                    else:
                        audjpy_result = boundary_results["R42_AUDJPY"]
                        _log_market_decision_telemetry(
                            log_path=log_path,
                            anchor=audjpy_arm_anchor,
                            snapshot=armed_m5_snapshots["AUDJPY"],
                            result=audjpy_result,
                        )
                        if audjpy_result.error is not None:
                            raise audjpy_result.error
                        audjpy_signal = audjpy_result.signal
                        reason = audjpy_result.reason
                        audjpy_done = audjpy_result.strategy_finished_at
                        audjpy_latency_ms = int(
                            (audjpy_done - audjpy_arm_anchor).total_seconds() * 1000
                        )
                        if audjpy_done > m5_deadline:
                            _log(
                                log_path,
                                {
                                    "event": "AUDJPY_R42_BOUNDARY_FAIL_CLOSED",
                                    "symbol": "AUDJPY",
                                    "decision_at": audjpy_arm_anchor.isoformat(),
                                    "reason": "decision-deadline-expired",
                                    "observed_at": audjpy_done.isoformat(),
                                    "latency_ms": audjpy_latency_ms,
                                    "hard_sla_seconds": (AUDJPY_R42_ENTRY_SLA.total_seconds()),
                                    "order_send_called": False,
                                },
                            )
                        elif audjpy_signal is None:
                            _log(
                                log_path,
                                {
                                    "event": "AUDJPY_R42_CAUSAL_ABSTAIN",
                                    "symbol": "AUDJPY",
                                    "decision_at": audjpy_arm_anchor.isoformat(),
                                    "reason": reason,
                                    "observed_at": audjpy_done.isoformat(),
                                    "latency_ms": audjpy_latency_ms,
                                    "hard_sla_seconds": (AUDJPY_R42_ENTRY_SLA.total_seconds()),
                                    "strategy_started_at": (
                                        audjpy_result.strategy_started_at.isoformat()
                                    ),
                                    "strategy_finished_at": (
                                        audjpy_result.strategy_finished_at.isoformat()
                                    ),
                                    "strategy_latency_ms": (audjpy_result.strategy_latency_ms),
                                },
                            )
                        else:
                            _process_audjpy_r42_candidate(
                                signal=audjpy_signal,
                                now=audjpy_done,
                                mode=mode,
                                gateway=gateway,
                                transport=transport,
                                risk=risk,
                                account_binding_id=fingerprint,
                                provider_budget=arm_provider,
                                capital_budget=arm_capital,
                                account_equity=arm_account.equity,
                                audjpy_r42_store=audjpy_r42_store,
                                log_path=log_path,
                                preflight_snapshot=arm_snapshot,
                                preflight_spec=arm_specs["AUDJPY"],
                            )
                except BrokerMinimumVolumeRiskRejectError as risk_reject:
                    _log(
                        log_path,
                        {
                            "event": "RISK_REJECT_MINIMUM_BROKER_VOLUME",
                            "symbol": "AUDJPY",
                            "decision_at": audjpy_arm_anchor.isoformat(),
                            "candidate": True,
                            "order_send_called": False,
                            **risk_reject.telemetry(),
                        },
                    )
                except Exception as error:
                    freeze_until = audjpy_arm_anchor + AUDJPY_R42_ENTRY_SLA
                    remaining = (freeze_until - datetime.now(UTC)).total_seconds()
                    if remaining > 0:
                        time.sleep(remaining)
                    _log(
                        log_path,
                        {
                            "event": "AUDJPY_R42_BOUNDARY_FAIL_CLOSED",
                            "symbol": "AUDJPY",
                            "decision_at": audjpy_arm_anchor.isoformat(),
                            "reason": type(error).__name__,
                            "message": str(error),
                            "hard_sla_seconds": AUDJPY_R42_ENTRY_SLA.total_seconds(),
                            "order_send_called": False,
                        },
                    )
                completed_at = datetime.now(UTC)
                for fast_processed_key in m5_fast_processed_keys:
                    state = state.with_cycle(
                        highest_closed_balance=str(highest),
                        active_mll=str(previous_mll),
                        processed_anchor=fast_processed_key,
                        reconciled_at=completed_at,
                        heartbeat_at=completed_at,
                    )
                state = state.with_cycle(
                    highest_closed_balance=str(highest),
                    active_mll=str(previous_mll),
                    processed_anchor=audjpy_anchor_key,
                    reconciled_at=completed_at,
                    heartbeat_at=completed_at,
                )
                store.store(state)

        current_hour = cycle_at.replace(
            minute=0,
            second=0,
            microsecond=0,
        )
        current_hour_key = f"R42_AUDJPY|{current_hour.isoformat()}"
        late_delta = cycle_at - current_hour
        if (
            timedelta(0) <= late_delta <= AUDJPY_R42_ENTRY_SLA
            and current_hour_key not in state.processed_anchors
        ):
            _log(
                log_path,
                {
                    "event": "AUDJPY_R42_SLA_FAIL_CLOSED",
                    "symbol": "AUDJPY",
                    "stage": "boundary-not-prearmed",
                    "decision_at": current_hour.isoformat(),
                    "observed_at": cycle_at.isoformat(),
                    "latency_ms": int(late_delta.total_seconds() * 1000),
                    "order_send_called": False,
                },
            )
            state = state.with_cycle(
                highest_closed_balance=str(highest),
                active_mll=str(previous_mll),
                processed_anchor=current_hour_key,
                reconciled_at=cycle_at,
                heartbeat_at=cycle_at,
            )
            store.store(state)

        m5_portfolio_keys = (
            f"R43_GBPUSD|{current_hour.isoformat()}",
            f"R34_XAUUSD|{current_hour.isoformat()}",
            f"R38_GBPJPY|{current_hour.isoformat()}",
            f"R38_EURUSD|{current_hour.isoformat()}",
            f"R42_AUDJPY|{current_hour.isoformat()}",
        )
        if armed_m5_snapshots is None and any(
            key not in state.processed_anchors for key in m5_portfolio_keys
        ):
            m5_late_delta = cycle_at - current_hour
            if timedelta(0) <= m5_late_delta <= M5_PROFILE.order_send_deadline:
                _log(
                    log_path,
                    {
                        "event": "M5_PORTFOLIO_BOUNDARY_FAIL_CLOSED",
                        "decision_at": current_hour.isoformat(),
                        "reason": "boundary-not-prearmed",
                        "hard_sla_seconds": (M5_PROFILE.order_send_deadline.total_seconds()),
                        "order_send_called": False,
                    },
                )

        vt31_arm_anchor = vt31_boundary_to_arm(cycle_at)
        if vt31_arm_anchor is not None and _vt31_entry_boundary(vt31_arm_anchor):
            vt31_arm_started_at = datetime.now(UTC)
            vt31_prepare_started_ns = time.perf_counter_ns()
            vt31_prepared_context = None
            try:
                vt31_cache.refresh_incremental(mt5, now=vt31_arm_started_at)
                vt31_prefix_fingerprint = vt31_cache.prepare_boundary(
                    anchor=vt31_arm_anchor
                )
                vt31_prepared_context = prepare_vt31_boundary(
                    closed_m1=vt31_cache.closed_m1(
                        through=vt31_arm_anchor - timedelta(minutes=1)
                    ),
                    evidence_fingerprint=vt31_prefix_fingerprint,
                )
                vt31_prepare_elapsed_ms = (
                    time.perf_counter_ns() - vt31_prepare_started_ns
                ) / 1_000_000
                _log(
                    log_path,
                    {
                        "event": "VT31_NAS100_BOUNDARY_PREPARED",
                        "boundary_at_utc": vt31_arm_anchor.isoformat(),
                        "boundary_at_new_york": (
                            vt31_arm_anchor.astimezone(_NY).isoformat()
                        ),
                        "elapsed_ms": round(vt31_prepare_elapsed_ms, 3),
                        "strategy_timezone": "America/New_York",
                    },
                )
            except Exception as preparation_error:
                _log(
                    log_path,
                    {
                        "event": "VT31_FAIL_CLOSED",
                        "boundary_at_utc": vt31_arm_anchor.isoformat(),
                        "boundary_at_new_york": (
                            vt31_arm_anchor.astimezone(_NY).isoformat()
                        ),
                        "stage": "prearm",
                        "reason": type(preparation_error).__name__,
                        "message": str(preparation_error),
                        "order_send_called": False,
                    },
                )
                continue
            _log(
                log_path,
                {
                    "event": "VT31_NAS100_BOUNDARY_ARMED",
                    "symbol": "NAS100",
                    "decision_at": vt31_arm_anchor.isoformat(),
                    "armed_at": vt31_arm_started_at.isoformat(),
                    "lead_ms": int((vt31_arm_anchor - vt31_arm_started_at).total_seconds() * 1000),
                    "maintenance_frozen": True,
                    "risk_preflight_only": True,
                },
            )
            try:
                vt31_account = gateway.read_account(now=vt31_arm_started_at)
                gateway.reconcile_unknown(now=vt31_arm_started_at)
                vt31_highest = max(highest, vt31_account.balance)
                vt31_provider = evaluate_stellar_instant_budget(
                    StellarInstantAccountSnapshot(
                        initial_balance=PILOT_INITIAL_BALANCE,
                        balance=vt31_account.balance,
                        equity=vt31_account.equity,
                        highest_closed_balance=vt31_highest,
                        previous_active_mll=previous_mll,
                    )
                )
                (
                    vt31_open_stop,
                    vt31_floating_loss,
                    vt31_pending_stop,
                ) = _broker_risk(transport)
                vt31_aggregate = (
                    vt31_open_stop + vt31_pending_stop + risk.active_reserved_stop_risk()
                )
                prior_mission_state = mission_snapshot.state
                mission_snapshot = evaluate_capitalization_mission(
                    config=mission_config,
                    closed_balance=vt31_account.balance,
                    equity=vt31_account.equity,
                    now=vt31_arm_started_at,
                    previous=mission_snapshot,
                    defend=False,
                    payout_eligible=False,
                )
                vt31_posture = request_cibo_posture(
                    initial_balance=PILOT_INITIAL_BALANCE,
                    balance=vt31_account.balance,
                    equity=vt31_account.equity,
                    current_aggregate_risk=vt31_aggregate,
                )
                if mission_snapshot.state is CapitalizationMissionState.BANK:
                    vt31_posture = Vt08ForexCiboPosture.BANK
                vt31_capital = evaluate_qore_operational_capital_budget(
                    provider_budget=vt31_provider,
                    initial_balance=PILOT_INITIAL_BALANCE,
                    balance=vt31_account.balance,
                    equity=vt31_account.equity,
                    highest_closed_balance=vt31_highest,
                    current_aggregate_stop_risk=vt31_aggregate,
                    requested_posture=vt31_posture,
                    certified_open_risk_fraction=(
                        certified_policy.facts.cumulative_open_risk_fraction
                    ),
                )
                mission_snapshot = evaluate_capitalization_mission(
                    config=mission_config,
                    closed_balance=vt31_account.balance,
                    equity=vt31_account.equity,
                    now=vt31_arm_started_at,
                    previous=mission_snapshot,
                    defend=(vt31_capital.decision is CapitalBudgetDecision.REJECT),
                    payout_eligible=False,
                )
                mission_store.store(mission_snapshot)
                if mission_snapshot.state is not prior_mission_state:
                    _log(
                        log_path,
                        {
                            "event": "CAPITALIZATION_MISSION_STATE_CHANGED",
                            "from_state": prior_mission_state.value,
                            "to_state": mission_snapshot.state.value,
                            "closed_balance": str(vt31_account.balance),
                            "target_remaining": str(mission_snapshot.target_remaining),
                            "new_risk_allowed_by_mission": (
                                mission_snapshot.new_risk_allowed_by_mission
                            ),
                        },
                    )
                vt31_snapshot = AccountRiskSnapshot(
                    account_binding_id=fingerprint,
                    equity=vt31_account.equity,
                    margin_used=vt31_account.margin,
                    free_margin=vt31_account.free_margin,
                    open_stop_worst_case_loss=vt31_open_stop,
                    open_floating_loss=vt31_floating_loss,
                    pending_broker_worst_case_loss=vt31_pending_stop,
                    qore_authorizable_headroom=(vt31_capital.qore_authorizable_headroom),
                    provider_budget=vt31_provider,
                    reconciled_at=vt31_arm_started_at,
                )
                vt31_accepted_times = [
                    item.transitioned_at
                    for item in mutation_ledger.records()
                    if item.state is FundedNextMt5MutationState.ACCEPTED
                ]
                vt31_last_activity = max(
                    vt31_accepted_times,
                    default=activation.authorization.activation_timestamp,
                )
                vt31_lifecycle = inactivity_state(
                    last_activity_at=vt31_last_activity,
                    now=vt31_arm_started_at,
                )
                vt31_blocked = (
                    vt31_capital.decision is CapitalBudgetDecision.REJECT
                    or vt31_lifecycle is InactivityState.BLOCKED
                    or exit_ledger.has_unresolved
                    or gateway.has_unresolved_mutations
                    or not certified_policy_ready
                    or not mission_snapshot.new_risk_allowed_by_mission
                )
                vt31_boundary = await_vt31_boundary_snapshot(
                    mt5,
                    cache=vt31_cache,
                    anchor=vt31_arm_anchor,
                )
                _log(
                    log_path,
                    {
                        "event": "VT31_M1_SEEN",
                        "boundary_at_utc": vt31_arm_anchor.isoformat(),
                        "boundary_at_new_york": (
                            vt31_arm_anchor.astimezone(_NY).isoformat()
                        ),
                        "observed_at_utc": vt31_boundary.observed_at.isoformat(),
                        "observed_at_new_york": (
                            vt31_boundary.observed_at.astimezone(_NY).isoformat()
                        ),
                        "feed_latency_ms": int(
                            (
                                vt31_boundary.observed_at - vt31_arm_anchor
                            ).total_seconds()
                            * 1000
                        ),
                        "strategy_timezone": "America/New_York",
                    },
                )
                if vt31_blocked:
                    _log(
                        log_path,
                        {
                            "event": "VT31_NAS100_BOUNDARY_FAIL_CLOSED",
                            "symbol": "NAS100",
                            "decision_at": vt31_arm_anchor.isoformat(),
                            "reason": "preflight-new-order-blocked",
                            "observed_at": vt31_boundary.observed_at.isoformat(),
                            "order_send_called": False,
                        },
                    )
                else:
                    vt31_strategy_started_ns = time.perf_counter_ns()
                    vt31_basket, vt31_reason = evaluate_vt31_boundary(
                        closed_m1=vt31_boundary.closed_m1,
                        evidence_fingerprint=(vt31_boundary.evidence_fingerprint),
                        store=vt31_store,
                        prepared_context=vt31_prepared_context,
                    )
                    vt31_strategy_elapsed_ms = (
                        time.perf_counter_ns() - vt31_strategy_started_ns
                    ) / 1_000_000
                    vt31_decided_at = datetime.now(UTC)
                    _log(
                        log_path,
                        {
                            "event": "VT31_STRATEGY_DECISION",
                            "boundary_at_utc": vt31_arm_anchor.isoformat(),
                            "boundary_at_new_york": (
                                vt31_arm_anchor.astimezone(_NY).isoformat()
                            ),
                            "decision_at_utc": vt31_decided_at.isoformat(),
                            "decision_at_new_york": (
                                vt31_decided_at.astimezone(_NY).isoformat()
                            ),
                            "elapsed_ms": round(vt31_strategy_elapsed_ms, 3),
                            "result": (
                                "CANDIDATE"
                                if vt31_basket is not None
                                else "ABSTAIN"
                            ),
                            "reason": vt31_reason,
                            "strategy_timezone": "America/New_York",
                        },
                    )
                    if vt31_basket is not None:
                        _log(
                            log_path,
                            {
                                "event": "VT31_CANDIDATE",
                                "boundary_at_utc": vt31_arm_anchor.isoformat(),
                                "boundary_at_new_york": (
                                    vt31_arm_anchor.astimezone(_NY).isoformat()
                                ),
                                "decision_at_utc": vt31_decided_at.isoformat(),
                                "decision_at_new_york": (
                                    vt31_decided_at.astimezone(_NY).isoformat()
                                ),
                                "elapsed_ms": round(
                                    vt31_strategy_elapsed_ms,
                                    3,
                                ),
                                "basket_id": vt31_basket.basket_id,
                                "tier": vt31_basket.tier,
                                "candidate_ids": [
                                    item.candidate_id
                                    for item in vt31_basket.candidates
                                ],
                                "signal_fingerprints": [
                                    item.signal_fingerprint
                                    for item in vt31_basket.candidates
                                ],
                            },
                        )
                    if vt31_basket is None:
                        _log(
                            log_path,
                            {
                                "event": "VT31_NAS100_CAUSAL_ABSTAIN",
                                "symbol": "NAS100",
                                "decision_at": vt31_arm_anchor.isoformat(),
                                "reason": vt31_reason,
                                "observed_at": (vt31_boundary.observed_at.isoformat()),
                            },
                        )
                    elif mode == "shadow":
                        shadow_vt31_basket(
                            basket=vt31_basket,
                            boundary_at=vt31_arm_anchor,
                            gateway=gateway,
                            risk=risk,
                            snapshot=vt31_snapshot,
                            account_equity=vt31_account.equity,
                            store=vt31_store,
                            log=lambda event: _log(log_path, event),
                        )
                    elif len(vt31_basket.candidates) == 1:
                        submit_vt31_single_live(
                            basket=vt31_basket,
                            boundary_at=vt31_arm_anchor,
                            gateway=gateway,
                            risk=risk,
                            snapshot=vt31_snapshot,
                            account_equity=vt31_account.equity,
                            store=vt31_store,
                            log=lambda event: _log(log_path, event),
                        )
                    else:
                        _log(
                            log_path,
                            {
                                "event": "VT31_NAS100_VIRTUAL_OCO_ARMED",
                                "symbol": "NAS100",
                                "decision_at": vt31_arm_anchor.isoformat(),
                                "basket_id": vt31_basket.basket_id,
                                "candidate_count": len(vt31_basket.candidates),
                            },
                        )
            except BrokerMinimumVolumeRiskRejectError as risk_reject:
                _log(
                    log_path,
                    {
                        "event": "RISK_REJECT_MINIMUM_BROKER_VOLUME",
                        "symbol": "NAS100",
                        "decision_at": vt31_arm_anchor.isoformat(),
                        "candidate": True,
                        "order_send_called": False,
                        **risk_reject.telemetry(),
                    },
                )
            except Exception as error:
                freeze_until = vt31_arm_anchor + VT31_DECISION_DEADLINE
                remaining = (freeze_until - datetime.now(UTC)).total_seconds()
                if remaining > 0:
                    time.sleep(remaining)
                _log(
                    log_path,
                    {
                        "event": "VT31_NAS100_BOUNDARY_FAIL_CLOSED",
                        "symbol": "NAS100",
                        "decision_at": vt31_arm_anchor.isoformat(),
                        "reason": type(error).__name__,
                        "message": str(error),
                        "decision_deadline_seconds": (VT31_DECISION_DEADLINE.total_seconds()),
                        "order_send_called": False,
                    },
                )
                failed_at = datetime.now(UTC)
                _log(
                    log_path,
                    {
                        "event": "VT31_FAIL_CLOSED",
                        "boundary_at_utc": vt31_arm_anchor.isoformat(),
                        "boundary_at_new_york": (
                            vt31_arm_anchor.astimezone(_NY).isoformat()
                        ),
                        "logged_at_utc": failed_at.isoformat(),
                        "logged_at_new_york": (
                            failed_at.astimezone(_NY).isoformat()
                        ),
                        "reason": type(error).__name__,
                        "message": str(error),
                        "order_send_called": False,
                    },
                )
            completed_at = datetime.now(UTC)
            state = state.with_cycle(
                highest_closed_balance=str(highest),
                active_mll=str(previous_mll),
                processed_anchor=None,
                reconciled_at=completed_at,
                heartbeat_at=completed_at,
            )
            store.store(state)
            continue

        account_state = gateway.read_account(now=cycle_at)
        gateway.reconcile_unknown(now=cycle_at)
        _manage_h4_exits(
            mutation_ledger=mutation_ledger,
            risk_ledger=risk_ledger,
            exit_ledger=exit_ledger,
            now=cycle_at,
            log_path=log_path,
        )
        _reconcile_filled_reservations(
            risk=risk,
            risk_ledger=risk_ledger,
            mutation_ledger=mutation_ledger,
            now=cycle_at,
        )
        r34_live_state = r34_store.reconcile(mt5, now=cycle_at)
        r38_live_state, r38_manage_reason = manage_r38_open_position(
            mt5,
            now=cycle_at,
            store=r38_store,
            cache=m5_caches["EURUSD"],
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
        r43_live_state, r43_manage_reason = manage_r43_open_position(
            mt5,
            now=cycle_at,
            store=r43_store,
            cache=m5_caches["GBPUSD"],
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
        gbpjpy_r38_live_state, gbpjpy_r38_manage_reason = manage_gbpjpy_r38_open_position(
            mt5,
            now=cycle_at,
            store=gbpjpy_r38_store,
            mutations_enabled=mode == "live",
            cache=m5_caches["GBPJPY"],
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
                    "strategy_drawdown_r": str(gbpjpy_r38_live_state.drawdown_r),
                    "new_york_time": cycle_at.astimezone(_NY).isoformat(),
                },
            )
        audjpy_r42_live_state, audjpy_r42_manage_reason = manage_audjpy_r42_open_position(
            mt5,
            now=cycle_at,
            store=audjpy_r42_store,
            mutations_enabled=mode == "live",
            cache=audjpy_r42_cache,
        )
        if audjpy_r42_manage_reason not in {
            "no-open-audjpy-r42-position",
            "audjpy-r42-stop-unchanged",
            "audjpy-r42-position-awaiting-reconcile",
            "audjpy-r42-24h-exit-due",
        }:
            _log(
                log_path,
                {
                    "event": "AUDJPY_R42_POSITION_MANAGEMENT",
                    "symbol": "AUDJPY",
                    "reason": audjpy_r42_manage_reason,
                    "strategy_drawdown_r": str(audjpy_r42_live_state.drawdown_r),
                    "new_york_time": cycle_at.astimezone(_NY).isoformat(),
                },
            )
        vt31_live_state, vt31_manage_reason = manage_vt31_open_trade(
            mt5_api=mt5,
            now=cycle_at,
            cache=vt31_cache,
            store=vt31_store,
            mutations_enabled=mode == "live",
            log=lambda event: _log(log_path, event),
        )
        if vt31_manage_reason not in {
            "no-open-vt31-position",
            "vt31-position-awaiting-reconcile",
            "vt31-journey-hold",
            "vt31-base-runner-hold",
            "vt31-eq-overlay-hold",
            "vt31-runner-hold",
        }:
            _log(
                log_path,
                {
                    "event": "VT31_NAS100_POSITION_MANAGEMENT",
                    "symbol": "NAS100",
                    "reason": vt31_manage_reason,
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
        prior_mission_state = mission_snapshot.state
        mission_snapshot = evaluate_capitalization_mission(
            config=mission_config,
            closed_balance=account_state.balance,
            equity=account_state.equity,
            now=cycle_at,
            previous=mission_snapshot,
            defend=False,
            payout_eligible=False,
        )
        posture = request_cibo_posture(
            initial_balance=PILOT_INITIAL_BALANCE,
            balance=account_state.balance,
            equity=account_state.equity,
            current_aggregate_risk=aggregate,
        )
        if mission_snapshot.state is CapitalizationMissionState.BANK:
            posture = Vt08ForexCiboPosture.BANK
        capital = evaluate_qore_operational_capital_budget(
            provider_budget=provider,
            initial_balance=PILOT_INITIAL_BALANCE,
            balance=account_state.balance,
            equity=account_state.equity,
            highest_closed_balance=highest,
            current_aggregate_stop_risk=aggregate,
            requested_posture=posture,
            certified_open_risk_fraction=(certified_policy.facts.cumulative_open_risk_fraction),
        )
        mission_snapshot = evaluate_capitalization_mission(
            config=mission_config,
            closed_balance=account_state.balance,
            equity=account_state.equity,
            now=cycle_at,
            previous=mission_snapshot,
            defend=(capital.decision is CapitalBudgetDecision.REJECT),
            payout_eligible=False,
        )
        mission_store.store(mission_snapshot)
        if mission_snapshot.state is not prior_mission_state:
            _log(
                log_path,
                {
                    "event": "CAPITALIZATION_MISSION_STATE_CHANGED",
                    "from_state": prior_mission_state.value,
                    "to_state": mission_snapshot.state.value,
                    "closed_balance": str(account_state.balance),
                    "realized_profit": str(mission_snapshot.realized_profit),
                    "target_remaining": str(mission_snapshot.target_remaining),
                    "bank_balance_threshold": str(mission_snapshot.bank_balance_threshold),
                    "mission_balance_target": str(mission_snapshot.mission_balance_target),
                    "new_risk_allowed_by_mission": (mission_snapshot.new_risk_allowed_by_mission),
                },
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
            or not certified_policy_ready
            or not mission_snapshot.new_risk_allowed_by_mission
        )
        vt31_runtime_snapshot = AccountRiskSnapshot(
            account_binding_id=fingerprint,
            equity=account_state.equity,
            margin_used=account_state.margin,
            free_margin=account_state.free_margin,
            open_stop_worst_case_loss=open_stop,
            open_floating_loss=floating_loss,
            pending_broker_worst_case_loss=pending_stop,
            qore_authorizable_headroom=capital.qore_authorizable_headroom,
            provider_budget=provider,
            reconciled_at=cycle_at,
        )
        reconcile_vt31_pending(
            mt5_api=mt5,
            transport=transport,
            risk=risk,
            store=vt31_store,
            now=cycle_at,
            log=lambda event: _log(log_path, event),
        )
        if mode == "live" and not new_order_blocked:
            process_vt31_virtual_oco(
                mt5_api=mt5,
                now=cycle_at,
                gateway=gateway,
                risk=risk,
                snapshot=vt31_runtime_snapshot,
                account_equity=account_state.equity,
                store=vt31_store,
                log=lambda event: _log(log_path, event),
            )

        if anchor is not None and not new_order_blocked:
            for symbol in _MARKETS:
                anchor_key = f"{symbol}|{anchor.isoformat()}"
                if anchor_key in state.processed_anchors:
                    continue
                try:
                    candidate, reason = _causal_candidate(symbol, anchor)
                    if candidate is None:
                        _log(
                            log_path,
                            {
                                "event": "VT08_CAUSAL_ABSTAIN",
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
        if r34_anchor is not None and armed_m5_snapshots is not None and not new_order_blocked:
            r34_anchor_key = f"R34_XAUUSD|{r34_anchor.isoformat()}"
            if r34_anchor_key not in state.processed_anchors:
                try:
                    r34_live_state = r34_store.reconcile(mt5, now=cycle_at)
                    r34_signal, reason = build_r34_live_signal(
                        mt5,
                        now=cycle_at,
                        cognitive=r34_cognitive,
                        state=r34_live_state,
                        boundary_snapshot=(
                            None if armed_m5_snapshots is None else armed_m5_snapshots.get("XAUUSD")
                        ),
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
        if r38_anchor is not None and armed_m5_snapshots is not None and not new_order_blocked:
            r38_anchor_key = f"R38_EURUSD|{r38_anchor.isoformat()}"
            if r38_anchor_key not in state.processed_anchors:
                try:
                    r38_live_state = r38_store.reconcile(mt5, now=cycle_at)
                    r38_signal, reason = build_r38_live_signal(
                        mt5,
                        now=cycle_at,
                        cognitive=r38_cognitive,
                        state=r38_live_state,
                        boundary_snapshot=(
                            None if armed_m5_snapshots is None else armed_m5_snapshots.get("EURUSD")
                        ),
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
        if r43_anchor is not None and armed_m5_snapshots is not None and not new_order_blocked:
            r43_anchor_key = f"R43_GBPUSD|{r43_anchor.isoformat()}"
            if r43_anchor_key not in state.processed_anchors:
                try:
                    r43_live_state = r43_store.reconcile(mt5, now=cycle_at)
                    r43_signal, reason = build_r43_live_signal(
                        mt5,
                        now=cycle_at,
                        memory_bundle=r43_memory,
                        state=r43_live_state,
                        boundary_snapshot=(
                            None if armed_m5_snapshots is None else armed_m5_snapshots.get("GBPUSD")
                        ),
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
        if (
            gbpjpy_r38_anchor is not None
            and armed_m5_snapshots is not None
            and not new_order_blocked
        ):
            gbpjpy_r38_anchor_key = f"R38_GBPJPY|{gbpjpy_r38_anchor.isoformat()}"
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
                        boundary_snapshot=(
                            None if armed_m5_snapshots is None else armed_m5_snapshots.get("GBPJPY")
                        ),
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
                                "strategy_drawdown_r": str(gbpjpy_r38_live_state.drawdown_r),
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
        cycle_elapsed = time.monotonic() - cycle_started
        time.sleep(max(0.05, _LOOP_SECONDS - cycle_elapsed))


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
    recovery_log = root / "artifacts" / "fundednext_runtime_events.jsonl"
    lock = SingleWriterRuntimeLock(root / "var" / "fundednext" / "runtime.lock")
    try:
        with lock:
            run(
                root,
                mode=args.mode,
                activation_path=(root / args.activation),
            )
        raise RuntimeError("resident runtime returned unexpectedly")
    except KeyboardInterrupt:
        mt5.shutdown()
        raise
    except Exception as error:
        _log(
            recovery_log,
            {
                "event": "RUNTIME_FATAL_EXIT",
                "reason": type(error).__name__,
                "message": str(error),
                "observed_at": datetime.now(UTC).isoformat(),
                "restart_owner": "external-watchdog-with-storm-fence",
            },
        )
        mt5.shutdown()
        raise SystemExit(1) from error


if __name__ == "__main__":
    main()
