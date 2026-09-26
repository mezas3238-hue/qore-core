"""Independent QORE cTrader DEMO FREE-CIBO runtime.

Market data, account state, execution, position management, persistence and
watchdog ownership are cTrader DEMO-only. Traders retain market-methodology
authority; CIBO CMA owns sizing/capital management; QORE Risk remains the hard
survivability governor.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from importlib import import_module
from collections.abc import Callable
from concurrent.futures import (
    ThreadPoolExecutor,
)
from functools import partial
import time
from datetime import UTC, datetime, timedelta
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace
from typing import Any

mt5: Any = None

from qore.infrastructure.ctrader_demo_full_api import (
    CTraderDemoFullApi,
    CTraderDemoReadTransport,
)
from qore.infrastructure.ctrader_demo_free_sink import (
    CTraderDemoFreeSink,
    configure_global_sink,
    credentials_from_environment,
    demo_capital_for,
    submit_demo_request,
)
from qore.infrastructure.account_wide_risk import (
    AccountRiskSnapshot,
    TraderLineage,
)
from qore.infrastructure.broker_risk_sizing import BrokerMinimumVolumeRiskRejectError
from qore.infrastructure.account_wide_risk_ledger import (
    DurableAccountWideRiskEngine,
    DurableAccountWideRiskLedger,
)
from qore.infrastructure.ctrader_demo_compat import (
    CTraderDemoAccountState,
    CTraderDemoSymbolSpecification,
    NEW_YORK_TZ,
    causal_daily_candidate_allowed,
    h4_containment_exit_at,
    normalise_legacy_server_epoch,
)
from qore.infrastructure.ctrader_demo_cibo_pipeline import (
    cibo_setup_from_b01,
    request_cibo_posture,
)
from qore.infrastructure.ctrader_demo_runtime_state import (
    CTraderDemoRuntimeState,
    CTraderDemoSingleWriterLock,
    DurableCTraderDemoRuntimeStateStore,
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
    build_r34_opportunity,
    current_anchor as current_r34_anchor,
    load_cognitive as load_r34_cognitive,
)
from qore.infrastructure.r38_eurusd_live import (
    R38LiveSignal,
    R38LiveState,
    R38LiveStateStore,
    build_live_signal as build_r38_live_signal,
    build_r38_opportunity,
    current_anchor as current_r38_anchor,
    load_cognitive as load_r38_cognitive,
    manage_open_position as manage_r38_open_position,
)
from qore.infrastructure.r43_gbpusd_live import (
    R43LiveSignal,
    R43LiveState,
    R43LiveStateStore,
    build_live_signal as build_r43_live_signal,
    build_r43_opportunity,
    current_anchor as current_r43_anchor,
    load_memory as load_r43_memory,
    manage_open_position as manage_r43_open_position,
)
from qore.infrastructure.r38_gbpjpy_live import (
    R38GbpJpyLiveSignal,
    R38GbpJpyLiveState,
    R38GbpJpyLiveStateStore,
    build_live_signal as build_gbpjpy_r38_live_signal,
    build_r38_gbpjpy_opportunity,
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
    build_r42_audjpy_opportunity,
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
    evaluate_vt08_forex_cibo,
)
from qore.infrastructure.ctrader_demo_vt08_sizing import (
    build_ctrader_demo_vt08_opportunity,
)
from qore.infrastructure.cibo_cma_initial_seed import build_initial_seed_request
from qore.infrastructure.cibo_cma_lifecycle_store import DurableCmaLifecycleStore
from qore.infrastructure.cibo_cma_runtime_observer import (
    CmaRuntimePositionSnapshot,
    observe_runtime_position,
)
from qore.infrastructure.cibo_cma_settlement_store import DurableCmaSettlementStore
from qore.infrastructure.ctrader_demo_live_anomaly_supervisor import (
    run_with_bounded_repair,
)
from qore.infrastructure.ctrader_demo_live_behavior_lab import (
    CTraderDemoLiveBehaviorLedger,
    CTraderDemoMarketTape,
    management_observation_payload,
    position_path_observation_payload,
)

# Load only the cTrader DEMO VT31 adapter.  The frozen VT31 strategy remains
# unchanged; this adapter replaces broker/account transport and execution.
_vt31_adapter = import_module("vt31_nas100_ctrader_demo_adapter")
evaluate_vt31_boundary = _vt31_adapter.evaluate_boundary
prepare_vt31_boundary = _vt31_adapter.prepare_boundary
manage_vt31_open_trade = _vt31_adapter.manage_open_trade
process_vt31_virtual_oco = _vt31_adapter.process_virtual_oco
reconcile_vt31_pending = _vt31_adapter.reconcile_pending
vt31_runtime_started_fields = _vt31_adapter.runtime_started_fields
submit_vt31_single_live = _vt31_adapter.submit_single_live
warm_vt31_runtime = _vt31_adapter.warm_runtime

_NY = NEW_YORK_TZ
_MARKETS = ("AUDJPY", "GBPUSD", "GBPJPY")
_ACCOUNT_REF = "ctrader-demo-free"
_LOOP_SECONDS = AUDJPY_R42_FEED_REFRESH_SECONDS
_ANCHOR_GRACE = timedelta(seconds=30)
_HISTORY_DAYS = 14
_HISTORY_M15_BARS = _HISTORY_DAYS * 24 * 4 + 96
_BEHAVIOR_LEDGERS: dict[Path, CTraderDemoLiveBehaviorLedger] = {}


class _NoopExitLedger:
    @property
    def has_unresolved(self) -> bool:
        return False

    def mark_interrupted_unknown(self, *, now: datetime) -> None:
        del now


class CTraderDemoReadOnlyTransport:
    """Risk-observation surface backed only by cTrader DEMO."""

    def __init__(self, api: CTraderDemoFullApi) -> None:
        self._api = api

    def connected(self) -> bool:
        return self._api.terminal_info().connected

    def observed_now(self) -> datetime:
        return datetime.now(UTC)

    def account_state(self, account_ref: str) -> CTraderDemoAccountState | None:
        del account_ref
        return _account_state_from_demo_api(self._api, datetime.now(UTC))

    def symbol_info(self, provider_symbol: str) -> CTraderDemoSymbolSpecification | None:
        info = self._api.symbol_info(provider_symbol)
        tick = self._api.symbol_info_tick(provider_symbol)
        if info is None or tick is None:
            return None
        point = Decimal(str(info.point))
        spread_points = (
            (Decimal(str(tick.ask)) - Decimal(str(tick.bid))) / point
            if point > 0 else Decimal("0")
        )
        return CTraderDemoSymbolSpecification(
            qore_symbol="NAS100" if provider_symbol == "NDX100" else provider_symbol,
            provider_symbol=provider_symbol,
            digits=int(info.digits),
            point=point,
            tick_size=Decimal(str(info.trade_tick_size)),
            tick_value=Decimal(str(info.trade_tick_value)),
            contract_size=Decimal(str(info.trade_contract_size)),
            volume_min=Decimal(str(info.volume_min)),
            volume_max=Decimal(str(info.volume_max)),
            volume_step=Decimal(str(info.volume_step)),
            stops_level_points=Decimal(str(info.trade_stops_level)),
            freeze_level_points=Decimal(str(info.trade_freeze_level)),
            bid=Decimal(str(tick.bid)),
            ask=Decimal(str(tick.ask)),
            spread_points=spread_points,
            trade_enabled=True,
            session_open=True,
            observed_at=datetime.now(UTC),
        )

    def available_symbols(self) -> tuple[str, ...]:
        return tuple(item.name for item in self._api.symbols_get())

    def positions(self, account_ref: str) -> tuple[object, ...]:
        del account_ref
        return self._api.positions_get()

    def pending_orders(self, account_ref: str) -> tuple[object, ...]:
        del account_ref
        return self._api.orders_get()


class CTraderDemoReadOnlyGateway:
    """Legacy Trader gateway interface with no broker mutation methods."""

    def __init__(self, api: CTraderDemoFullApi) -> None:
        self._api = api

    @property
    def has_unresolved_mutations(self) -> bool:
        return False

    def reconcile_unknown(self, *, now: datetime) -> None:
        del now

    def read_account(self, *, now: datetime) -> CTraderDemoAccountState:
        return _account_state_from_demo_api(self._api, now)

    def read_symbol(self, qore_symbol: str, *, now: datetime) -> CTraderDemoSymbolSpecification:
        del now
        provider = "NDX100" if qore_symbol == "NAS100" else qore_symbol
        transport = CTraderDemoReadTransport(
            self._api,
            account_ref=_ACCOUNT_REF,
        )
        spec = transport.symbol_info(provider)
        if spec is None:
            raise RuntimeError(f"ctrader-demo-symbol-unavailable:{qore_symbol}")
        return spec

    def shadow_check(self, *args, **kwargs):
        raise RuntimeError("shadow order-check is not part of cTrader DEMO FREE")

    def submit_live(self, *args, **kwargs):
        raise RuntimeError("legacy broker submission is forbidden in cTrader DEMO FREE")


def _configure_ctrader_demo_free_sink(root: Path) -> CTraderDemoFreeSink:
    binding_path = root / "var" / "ctrader_demo_free" / "binding.json"
    raw = json.loads(binding_path.read_text(encoding="utf-8"))
    rows = raw.get("contracts", ())
    source_sizes = {
        str(row["qore_symbol"]): Decimal(str(row["source_contract_size_units"]))
        for row in rows
    }
    sink = CTraderDemoFreeSink(
        root=root,
        credentials=credentials_from_environment(),
        source_contract_sizes=source_sizes,
    )
    configure_global_sink(sink)
    return sink

def _account_state_from_demo_api(api: CTraderDemoFullApi, observed_at: datetime) -> CTraderDemoAccountState:
    info = api.account_info()
    if info is None:
        raise RuntimeError("cTrader DEMO account state unavailable")
    return CTraderDemoAccountState(
        balance=Decimal(str(info.balance)),
        equity=Decimal(str(info.equity)),
        margin=Decimal(str(info.margin)),
        free_margin=Decimal(str(info.margin_free)),
        observed_at=observed_at,
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
        opened = normalise_legacy_server_epoch(int(row["time"]))
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
    if local.hour not in OWNER_FOREX_ENTRY_ANCHORS:
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


def _behavior_ledger_for(path: Path) -> CTraderDemoLiveBehaviorLedger:
    normalized_path = (
        path.parent
        / "ctrader_demo_live_behavior_lab"
        / "runtime-events.normalized.jsonl"
    )
    ledger = _BEHAVIOR_LEDGERS.get(normalized_path)
    if ledger is None:
        ledger = CTraderDemoLiveBehaviorLedger(normalized_path)
        _BEHAVIOR_LEDGERS[normalized_path] = ledger
    return ledger


def _log(path: Path, event: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    value = dict(event)
    value["logged_at"] = datetime.now(UTC).isoformat()
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(value, sort_keys=True, default=str) + "\n")
    try:
        _behavior_ledger_for(path).record_raw(value, source="runtime")
    except Exception as error:
        # Observability must never acquire execution authority by failure.
        mirror_error = {
            "event": "BEHAVIOR_LAB_MIRROR_ERROR",
            "source_event": str(value.get("event", "UNKNOWN")),
            "reason": type(error).__name__,
            "message": str(error),
            "logged_at": datetime.now(UTC).isoformat(),
        }
        with path.open("a", encoding="utf-8") as handle:
            handle.write(
                json.dumps(mirror_error, sort_keys=True, default=str) + "\n"
            )


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
    if local.hour not in OWNER_FOREX_ENTRY_ANCHORS:
        raise RuntimeError("accepted-live-order-outside-causal-anchor")
    return local.astimezone(UTC)


def _process_candidate(
    *,
    candidate: Vt08B01Candidate,
    now: datetime,
    mode: str,
    gateway: CTraderDemoReadOnlyGateway,
    transport: CTraderDemoReadOnlyTransport,
    risk: DurableAccountWideRiskEngine,
    account_binding_id: str,
    provider_budget: Any,
    capital_budget: Any,
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
    posture_at = datetime.now(UTC)
    demo_capital = demo_capital_for(TraderLineage.VT08_FOREX)
    posture = request_cibo_posture(
        initial_balance=demo_capital,
        balance=demo_capital,
        equity=demo_capital,
        current_aggregate_risk=Decimal("0"),
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
    request_at = datetime.now(UTC)
    spec = gateway.read_symbol(candidate.symbol, now=request_at)
    account = gateway.read_account(now=request_at)
    opportunity = build_ctrader_demo_vt08_opportunity(
        cibo_authorization=cibo,
        provider_spec=spec,
    )
    seed = build_initial_seed_request(
        request_id=f"vt08-{setup.signal_fingerprint[:24]}",
        opportunity=opportunity,
        assigned_capital_usd=demo_capital,
        observed_free_margin_usd=account.free_margin,
        requested_at=request_at,
        expires_at=setup.expires_at,
    )
    request = seed.request
    demo_result = submit_demo_request(request)
    _log(
        log_path,
        {
            "event": "CTRADER_DEMO_FREE_EXECUTION",
            "trader": "VT08_FOREX",
            "symbol": request.qore_symbol,
            "state": demo_result.state,
            "requested_volume": str(request.requested_volume),
            "assigned_capital": str(demo_result.assigned_capital),
            "provider_order_ref": demo_result.provider_order_ref,
        },
    )
    return


def _process_r34_candidate(
    *,
    signal: R34LiveSignal,
    now: datetime,
    mode: str,
    gateway: CTraderDemoReadOnlyGateway,
    transport: CTraderDemoReadOnlyTransport,
    risk: DurableAccountWideRiskEngine,
    account_binding_id: str,
    provider_budget: Any,
    capital_budget: Any,
    account_equity: Decimal,
    r34_store: R34LiveStateStore,
    log_path: Path,
    preflight_snapshot: AccountRiskSnapshot | None = None,
    preflight_spec: CTraderDemoSymbolSpecification | None = None,
) -> None:
    request_at = datetime.now(UTC)
    spec = gateway.read_symbol("XAUUSD", now=request_at)
    account = gateway.read_account(now=request_at)
    opportunity = build_r34_opportunity(signal=signal, provider_spec=spec)
    seed = build_initial_seed_request(
        request_id=f"r34-{signal.signal_fingerprint[:24]}",
        opportunity=opportunity,
        assigned_capital_usd=demo_capital_for(TraderLineage.R34_XAUUSD),
        observed_free_margin_usd=account.free_margin,
        requested_at=request_at,
        expires_at=request_at + timedelta(seconds=30),
    )
    request = seed.request
    base_risk_usd = seed.plan.stop_risk_usd
    demo_result = submit_demo_request(request)
    if demo_result.state == "SUBMITTED" and demo_result.client_order_id is not None:
        r34_store.mark_open(
            client_order_id=demo_result.client_order_id,
            signal=signal,
            base_risk_usd=base_risk_usd,
        )
    _log(
        log_path,
        {
            "event": "CTRADER_DEMO_FREE_EXECUTION",
            "trader": "R34_XAUUSD",
            "symbol": request.qore_symbol,
            "state": demo_result.state,
            "requested_volume": str(request.requested_volume),
            "assigned_capital": str(demo_result.assigned_capital),
            "provider_order_ref": demo_result.provider_order_ref,
        },
    )
    return


def _process_r38_candidate(
    *,
    signal: R38LiveSignal,
    now: datetime,
    mode: str,
    gateway: CTraderDemoReadOnlyGateway,
    transport: CTraderDemoReadOnlyTransport,
    risk: DurableAccountWideRiskEngine,
    account_binding_id: str,
    provider_budget: Any,
    capital_budget: Any,
    account_equity: Decimal,
    r38_store: R38LiveStateStore,
    log_path: Path,
    preflight_snapshot: AccountRiskSnapshot | None = None,
    preflight_spec: CTraderDemoSymbolSpecification | None = None,
) -> None:
    request_at = datetime.now(UTC)
    spec = gateway.read_symbol("EURUSD", now=request_at)
    account = gateway.read_account(now=request_at)
    opportunity = build_r38_opportunity(signal=signal, provider_spec=spec)
    seed = build_initial_seed_request(
        request_id=f"r38-{signal.signal_fingerprint[:24]}",
        opportunity=opportunity,
        assigned_capital_usd=demo_capital_for(TraderLineage.R38_EURUSD),
        observed_free_margin_usd=account.free_margin,
        requested_at=request_at,
        expires_at=request_at + timedelta(seconds=30),
    )
    request = seed.request
    base_risk_usd = seed.plan.stop_risk_usd
    demo_result = submit_demo_request(request)
    if demo_result.state == "SUBMITTED" and demo_result.client_order_id is not None:
        r38_store.mark_open(
            client_order_id=demo_result.client_order_id,
            signal=signal,
            base_risk_usd=base_risk_usd,
        )
    _log(
        log_path,
        {
            "event": "CTRADER_DEMO_FREE_EXECUTION",
            "trader": "R38_EURUSD",
            "symbol": request.qore_symbol,
            "state": demo_result.state,
            "requested_volume": str(request.requested_volume),
            "assigned_capital": str(demo_result.assigned_capital),
            "provider_order_ref": demo_result.provider_order_ref,
        },
    )
    return


def _process_r43_candidate(
    *,
    signal: R43LiveSignal,
    now: datetime,
    mode: str,
    gateway: CTraderDemoReadOnlyGateway,
    transport: CTraderDemoReadOnlyTransport,
    risk: DurableAccountWideRiskEngine,
    account_binding_id: str,
    provider_budget: Any,
    capital_budget: Any,
    account_equity: Decimal,
    r43_store: R43LiveStateStore,
    log_path: Path,
    preflight_snapshot: AccountRiskSnapshot | None = None,
    preflight_spec: CTraderDemoSymbolSpecification | None = None,
) -> None:
    request_at = datetime.now(UTC)
    spec = gateway.read_symbol("GBPUSD", now=request_at)
    account = gateway.read_account(now=request_at)
    opportunity = build_r43_opportunity(signal=signal, provider_spec=spec)
    seed = build_initial_seed_request(
        request_id=f"r43-{signal.signal_fingerprint[:24]}",
        opportunity=opportunity,
        assigned_capital_usd=demo_capital_for(TraderLineage.R43_GBPUSD),
        observed_free_margin_usd=account.free_margin,
        requested_at=request_at,
        expires_at=request_at + timedelta(seconds=30),
    )
    request = seed.request
    base_risk_usd = seed.plan.stop_risk_usd
    demo_result = submit_demo_request(request)
    if demo_result.state == "SUBMITTED" and demo_result.client_order_id is not None:
        r43_store.mark_open(
            client_order_id=demo_result.client_order_id,
            signal=signal,
            base_risk_usd=base_risk_usd,
        )
    _log(
        log_path,
        {
            "event": "CTRADER_DEMO_FREE_EXECUTION",
            "trader": "R43_GBPUSD",
            "symbol": request.qore_symbol,
            "state": demo_result.state,
            "requested_volume": str(request.requested_volume),
            "assigned_capital": str(demo_result.assigned_capital),
            "provider_order_ref": demo_result.provider_order_ref,
        },
    )
    return


def _process_gbpjpy_r38_candidate(
    *,
    signal: R38GbpJpyLiveSignal,
    now: datetime,
    mode: str,
    gateway: CTraderDemoReadOnlyGateway,
    transport: CTraderDemoReadOnlyTransport,
    risk: DurableAccountWideRiskEngine,
    account_binding_id: str,
    provider_budget: Any,
    capital_budget: Any,
    account_equity: Decimal,
    gbpjpy_r38_store: R38GbpJpyLiveStateStore,
    log_path: Path,
    preflight_snapshot: AccountRiskSnapshot | None = None,
    preflight_spec: CTraderDemoSymbolSpecification | None = None,
) -> None:
    request_at = datetime.now(UTC)
    spec = gateway.read_symbol("GBPJPY", now=request_at)
    account = gateway.read_account(now=request_at)
    opportunity = build_r38_gbpjpy_opportunity(signal=signal, provider_spec=spec)
    seed = build_initial_seed_request(
        request_id=f"gbpjpy-r38-{signal.signal_fingerprint[:24]}",
        opportunity=opportunity,
        assigned_capital_usd=demo_capital_for(TraderLineage.R38_GBPJPY),
        observed_free_margin_usd=account.free_margin,
        requested_at=request_at,
        expires_at=request_at + timedelta(seconds=30),
    )
    request = seed.request
    base_risk_usd = seed.plan.stop_risk_usd
    demo_result = submit_demo_request(request)
    if demo_result.state == "SUBMITTED" and demo_result.client_order_id is not None:
        gbpjpy_r38_store.mark_open(
            client_order_id=demo_result.client_order_id,
            signal=signal,
            base_risk_usd=base_risk_usd,
        )
    _log(
        log_path,
        {
            "event": "CTRADER_DEMO_FREE_EXECUTION",
            "trader": "R38_GBPJPY",
            "symbol": request.qore_symbol,
            "state": demo_result.state,
            "requested_volume": str(request.requested_volume),
            "assigned_capital": str(demo_result.assigned_capital),
            "provider_order_ref": demo_result.provider_order_ref,
        },
    )
    return


def _process_audjpy_r42_candidate(
    *,
    signal: R42AudJpyLiveSignal,
    now: datetime,
    mode: str,
    gateway: CTraderDemoReadOnlyGateway,
    transport: CTraderDemoReadOnlyTransport,
    risk: DurableAccountWideRiskEngine,
    account_binding_id: str,
    provider_budget: Any,
    capital_budget: Any,
    account_equity: Decimal,
    audjpy_r42_store: R42AudJpyLiveStateStore,
    log_path: Path,
    preflight_snapshot: AccountRiskSnapshot | None = None,
    preflight_spec: CTraderDemoSymbolSpecification | None = None,
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
    spec = gateway.read_symbol("AUDJPY", now=processing_at)

    request_at = stage_time("before-risk-request")
    if request_at is None:
        return
    account = gateway.read_account(now=request_at)
    opportunity = build_r42_audjpy_opportunity(
        signal=signal,
        provider_spec=spec,
        now=request_at,
    )
    seed = build_initial_seed_request(
        request_id=f"audjpy-r42-{signal.signal_fingerprint[:24]}",
        opportunity=opportunity,
        assigned_capital_usd=demo_capital_for(TraderLineage.R42_AUDJPY),
        observed_free_margin_usd=account.free_margin,
        requested_at=request_at,
        expires_at=deadline,
    )
    request = seed.request
    base_risk_usd = seed.plan.stop_risk_usd

    demo_result = submit_demo_request(request)
    if demo_result.state == "SUBMITTED" and demo_result.client_order_id is not None:
        audjpy_r42_store.mark_open(
            client_order_id=demo_result.client_order_id,
            signal=signal,
            base_risk_usd=base_risk_usd,
        )
    _log(
        log_path,
        {
            "event": "CTRADER_DEMO_FREE_EXECUTION",
            "trader": "R42_AUDJPY",
            "symbol": request.qore_symbol,
            "state": demo_result.state,
            "requested_volume": str(request.requested_volume),
            "assigned_capital": str(demo_result.assigned_capital),
            "provider_order_ref": demo_result.provider_order_ref,
        },
    )
    return


def run(root: Path, *, mode: str, activation_path: Path) -> None:
    del activation_path
    global mt5
    sha = _git_sha(root)
    demo_sink = _configure_ctrader_demo_free_sink(root)
    binding_raw = json.loads(
        (root / "var" / "ctrader_demo_free" / "binding.json").read_text(encoding="utf-8")
    )
    demo_source_contract_sizes = {
        str(row["qore_symbol"]): Decimal(str(row["source_contract_size_units"]))
        for row in binding_raw["contracts"]
    }
    market_tape = CTraderDemoMarketTape(
        root
        / "artifacts"
        / "ctrader_demo_live_behavior_lab"
        / "market-tape.jsonl"
    )

    def record_market_tick(
        symbol: str,
        symbol_id: int,
        bid: Decimal,
        ask: Decimal,
        provider_at: datetime,
        received_at: datetime,
    ) -> None:
        market_tape.append(
            symbol=symbol,
            symbol_id=symbol_id,
            bid=bid,
            ask=ask,
            provider_at=provider_at,
            received_at=received_at,
        )

    demo_api = CTraderDemoFullApi(
        client=demo_sink.client,
        binding=demo_sink.binding,
        positions=demo_sink.position_service,
        registry=demo_sink.registry,
        binding_path=root / "var" / "ctrader_demo_free" / "binding.json",
        source_contract_sizes=demo_source_contract_sizes,
        spot_observer=record_market_tick,
    )
    if not demo_api.initialize():
        raise RuntimeError("cTrader DEMO independent market-data initialization failed")
    if not demo_api.warm_session_schedules():
        raise RuntimeError("cTrader DEMO broker session schedule unavailable")
    mt5 = demo_api
    demo_management_api = demo_api
    account_info = demo_api.account_info()
    if account_info is None:
        raise RuntimeError("ctrader-demo-account-info-unavailable")
    fingerprint = hashlib.sha256(
        f"ctrader-demo:{account_info.login}:{account_info.server}".encode("utf-8")
    ).hexdigest()
    account = MarketTestAccountIdentity(
        provider_key="ctrader-demo",
        account_ref=str(account_info.login),
        environment=MarketRuntimeEnvironment.DEMO,
    )
    state_dir = root / "var" / "ctrader_demo_signal_runtime"
    cma_settlement_store = DurableCmaSettlementStore(
        state_dir / "cibo-cma-settlements.json"
    )
    cma_lifecycle_store = DurableCmaLifecycleStore(
        state_dir / "cibo-cma-lifecycle.json"
    )
    # Fail startup if durable CMA evidence is corrupt. Observational CMA must
    # never manufacture fresh capacity by silently discarding restart state.
    cma_settlement_store.load()
    cma_lifecycle_store.load()
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
    r34_store.load()
    r38_store = R38LiveStateStore(state_dir / "r38-state.json")
    r38_store.load()
    r43_store = R43LiveStateStore(state_dir / "r43-state.json")
    r43_store.load()
    gbpjpy_r38_store = R38GbpJpyLiveStateStore(state_dir / "r38-gbpjpy-state.json")
    gbpjpy_r38_store.load()
    audjpy_r42_store = R42AudJpyLiveStateStore(state_dir / "r42-audjpy-state.json")
    audjpy_r42_store.load()
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
        cache.preload(demo_api, now=preload_at)
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
        return None

    # DEMO_FREE: no prop-firm policy, payout mission, MLL or provider rule refresh.
    # cTrader DEMO is fully independent from FundedNext after startup.
    # The legacy variable names remain only to satisfy frozen Trader function
    # signatures; every market/account read is backed by cTrader DEMO.
    transport = CTraderDemoReadTransport(demo_api, account_ref=_ACCOUNT_REF)
    risk_ledger = DurableAccountWideRiskLedger(state_dir / "demo-risk-observation.json")
    exit_ledger = _NoopExitLedger()
    risk = DurableAccountWideRiskEngine(risk_ledger)
    gateway = CTraderDemoReadOnlyGateway(demo_api)

    def recover_demo_market_state(
        *,
        symbol: str,
        cache: object | None = None,
    ) -> None:
        if not demo_api.repair_market_data_subscription():
            raise RuntimeError("ctrader-demo-spot-resubscribe-failed")
        observed = datetime.now(UTC)
        if cache is not None:
            refresh = getattr(cache, "refresh_incremental", None)
            if callable(refresh):
                refresh(demo_api, now=observed)
        _log(
            root / "artifacts" / "ctrader_demo_free_runtime_events.jsonl",
            {
                "event": "CTRADER_DEMO_TECHNICAL_RECOVERY_REFRESHED",
                "symbol": symbol,
                "observed_at": observed.isoformat(),
            },
        )

    store = DurableCTraderDemoRuntimeStateStore(
        state_dir / "runtime-state.json"
    )
    old = store.load()
    now = datetime.now(UTC)
    if old is not None:
        if old.git_sha != sha or old.account_identity_fingerprint != fingerprint:
            raise RuntimeError("ctrader-demo-runtime-state-binding-mismatch")
        state = old.restarted_at(now)
    else:
        state = CTraderDemoRuntimeState(
            git_sha=sha,
            account_identity_fingerprint=fingerprint,
            balance=str(account_info.balance),
            equity=str(account_info.equity),
            processed_anchors=(),
            heartbeat_at=now,
            last_reconciliation_at=now,
            service_started_at=now,
        )
    store.store(state)
    highest = Decimal(str(account_info.balance))
    previous_mll = Decimal(str(account_info.equity))
    log_path = root / "artifacts" / "ctrader_demo_free_runtime_events.jsonl"
    _log(
        log_path,
        {
            "event": "RUNTIME_STARTED",
            "mode": mode,
            "git_sha": sha,
            "news_policy": "provider-permitted-no-synthetic-qore-news-trade-or-filter",
            "vt08_strategy_timezone": "America/New_York",
            "vt08_entry_anchors_new_york": list(OWNER_FOREX_ENTRY_ANCHORS),
            "vt08_broker_clock_normalized": True,
            "r34_enabled": True,
            "r34_identity": "TURTLE_SOUP_XAUUSD_R34",
            "r34_strategy_timezone": "America/New_York",
            "r34_schedule": "EVERY_H1_H4_BOUNDARY_24_7_SERVICE",
            "r34_external_single_position_gate": False,
            "r34_lifecycle": "STATIC_SL_TP_PLUS_24H_EXIT",
            "r38_enabled": True,
            "r38_identity": "TURTLE_SOUP_EURUSD_R38",
            "r38_certification": "TURTLE_SOUP_EURUSD_R39_FINAL_CERTIFICATION_SUITE_V1",
            "r38_strategy_timezone": "America/New_York",
            "r38_schedule": "EVERY_H1_H4_BOUNDARY_24_7_SERVICE",
            "r38_external_single_position_gate": False,
            "r38_lifecycle": "STATIC_OR_PROTECT_DOL_LOCK_M5_SWING_TRAIL_PLUS_24H_EXIT",
            "r38_base_risk_fraction": "0.002",
            "r43_enabled": True,
            "r43_identity": "TURTLE_SOUP_GBPUSD_R43",
            "r43_certification": "TURTLE_SOUP_GBPUSD_R45_FINAL_CERTIFICATION_SUITE_V1",
            "r43_strategy_timezone": "America/New_York",
            "r43_schedule": "EVERY_H1_H4_BOUNDARY_24_7_SERVICE",
            "r43_external_single_position_gate": False,
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
            "execution_environment": "CTRADER_DEMO_FREE",
            "market_data_provider": "CTRADER_DEMO",
            "ctrader_demo_writer": True,
            "account_wide_risk_active": False,
            "risk_role": "CAPITAL_ALLOCATOR_ONLY",
            "prop_firm_policy_active": False,
            "gbpjpy_r38_enabled": True,
            "gbpjpy_r38_identity": "TURTLE_SOUP_GBPJPY_R38",
            "gbpjpy_r38_certification": "TURTLE_SOUP_GBPJPY_R39_FINAL_CERTIFICATION_SUITE_V1",
            "gbpjpy_r38_strategy_timezone": "America/New_York",
            "gbpjpy_r38_schedule": "EVERY_H1_H4_BOUNDARY_24_7_SERVICE",
            "gbpjpy_r38_external_single_position_gate": False,
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
            "audjpy_r42_external_single_position_gate": False,
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
            "ctrader_demo_execution_enabled": True,
            "behavior_lab_active": True,
            "behavior_lab_mode": "CONTINUOUS_SUPERVISION",
            "behavior_lab_runtime_ledger": (
                "artifacts/ctrader_demo_live_behavior_lab/"
                "runtime-events.normalized.jsonl"
            ),
            "behavior_lab_market_tape": (
                "artifacts/ctrader_demo_live_behavior_lab/market-tape.jsonl"
            ),
            "behavior_lab_market_tape_mode": "EVERY_VALID_BROKER_SPOT_EVENT",
            "risk_role": "CAPITAL_ALLOCATOR_ONLY",
        },
    )
    last_lifecycle: str | None = None
    last_management_observation: dict[str, str] = {}

    while True:
        cycle_started = time.monotonic()
        cycle_at = datetime.now(UTC)
        armed_m5_snapshots: dict[str, M5BoundarySnapshot] | None = None
        feed_trader = {
            "XAUUSD": "R34_XAUUSD",
            "EURUSD": "R38_EURUSD",
            "GBPUSD": "R43_GBPUSD",
            "GBPJPY": "R38_GBPJPY",
            "AUDJPY": "R42_AUDJPY",
        }
        for symbol, cache in m5_caches.items():
            try:
                run_with_bounded_repair(
                    trader=feed_trader[symbol],
                    operation=lambda cache=cache: cache.refresh_incremental(
                        mt5,
                        now=datetime.now(UTC),
                    ),
                    recover=lambda symbol=symbol: recover_demo_market_state(
                        symbol=symbol,
                    ),
                    emit=lambda event: _log(log_path, event),
                )
            except Exception as error:
                _log(
                    log_path,
                    {
                        "event": "M5_INCREMENTAL_FEED_FAIL_CLOSED",
                        "trader": feed_trader[symbol],
                        "symbol": symbol,
                        "reason": type(error).__name__,
                        "message": str(error),
                        "observed_at": datetime.now(UTC).isoformat(),
                    },
                )
        try:
            run_with_bounded_repair(
                trader="VT31_NAS100",
                operation=lambda: vt31_cache.refresh_incremental(
                    mt5,
                    now=datetime.now(UTC),
                ),
                recover=lambda: recover_demo_market_state(symbol="NAS100"),
                emit=lambda event: _log(log_path, event),
            )
        except Exception as error:
            _log(
                log_path,
                {
                    "event": "VT31_NAS100_INCREMENTAL_FEED_FAIL_CLOSED",
                    "trader": "VT31_NAS100",
                    "symbol": "NAS100",
                    "reason": type(error).__name__,
                    "message": str(error),
                    "observed_at": datetime.now(UTC).isoformat(),
                },
            )

        audjpy_arm_anchor = m5_boundary_to_arm(cycle_at)
        if audjpy_arm_anchor is not None:
            m5_anchor_keys = {
                "GBPUSD": f"R43_GBPUSD|{audjpy_arm_anchor.isoformat()}",
                "XAUUSD": f"R34_XAUUSD|{audjpy_arm_anchor.isoformat()}",
                "GBPJPY": f"R38_GBPJPY|{audjpy_arm_anchor.isoformat()}",
                "EURUSD": f"R38_EURUSD|{audjpy_arm_anchor.isoformat()}",
                "AUDJPY": f"R42_AUDJPY|{audjpy_arm_anchor.isoformat()}",
            }
            audjpy_anchor_key = m5_anchor_keys["AUDJPY"]
            if any(
                key not in state.processed_anchors
                for key in m5_anchor_keys.values()
            ):
                m5_fast_processed_keys: list[str] = []
                audjpy_anchor_processed = False
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
                    arm_account = _account_state_from_demo_api(demo_api, arm_started_at)
                    # DEMO_FREE: no external reconciliation.
                    arm_r42_state = audjpy_r42_store.load()
                    arm_r34_state = r34_store.load()
                    arm_r38_state = r38_store.load()
                    arm_r43_state = r43_store.load()
                    arm_gbpjpy_state = gbpjpy_r38_store.load()
                    arm_highest = max(highest, arm_account.balance)
                    arm_provider = SimpleNamespace()
                    arm_capital = SimpleNamespace(
                                                qore_authorizable_headroom=arm_account.equity,
                    )
                    arm_snapshot = None
                    arm_specs = {
                        symbol: gateway.read_symbol(symbol, now=arm_started_at)
                        for symbol in ("XAUUSD", "EURUSD", "GBPUSD", "GBPJPY", "AUDJPY")
                    }
                    arm_lifecycle = SimpleNamespace(value="DEMO_FREE")
                    arm_blocked = False
                    m5_session_open = {
                        symbol: demo_api.session_open(
                            symbol,
                            audjpy_arm_anchor,
                        )
                        for symbol in (
                            "XAUUSD",
                            "EURUSD",
                            "GBPUSD",
                            "GBPJPY",
                            "AUDJPY",
                        )
                    }

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
                    m5_deadline = audjpy_arm_anchor + M5_PROFILE.decision_deadline
                    fast_plan_by_identity = {
                        identity: (symbol, abstain_event, process_fast)
                        for identity, symbol, abstain_event, process_fast in fast_plan
                    }
                    ready_snapshots: dict[str, M5BoundarySnapshot] = {}
                    m5_terminal_identities: set[str] = set()
                    m5_ctx: dict[str, Any] = {
                        "anchor": audjpy_arm_anchor,
                        "deadline": m5_deadline,
                        "anchor_keys": m5_anchor_keys,
                        "state": state,
                        "processed_keys": m5_fast_processed_keys,
                        "ready_snapshots": ready_snapshots,
                        "terminal_ids": m5_terminal_identities,
                        "arm_blocked": arm_blocked,
                        "fast_plan": fast_plan_by_identity,
                        "arm_provider": arm_provider,
                        "arm_capital": arm_capital,
                        "arm_account": arm_account,
                        "arm_snapshot": arm_snapshot,
                        "arm_specs": arm_specs,
                    }

                    def mark_m5_terminal(
                        identity: str,
                        symbol: str,
                        _ctx: dict[str, Any] = m5_ctx,
                    ) -> None:
                        terminal_ids: set[str] = _ctx["terminal_ids"]
                        if identity in terminal_ids:
                            return
                        terminal_ids.add(identity)
                        if identity != "R42_AUDJPY":
                            anchor_keys: dict[str, str] = _ctx["anchor_keys"]
                            runtime_state: CTraderDemoRuntimeState = _ctx["state"]
                            processed_keys: list[str] = _ctx["processed_keys"]
                            key = anchor_keys[symbol]
                            if (
                                key not in runtime_state.processed_anchors
                                and key not in processed_keys
                            ):
                                processed_keys.append(key)

                    def log_m5_hard_fail(
                        identity: str,
                        symbol: str,
                        *,
                        reason: str,
                        observed_at: datetime,
                        message: str | None = None,
                        _ctx: dict[str, Any] = m5_ctx,
                    ) -> None:
                        boundary_anchor: datetime = _ctx["anchor"]
                        event = (
                            "AUDJPY_R42_BOUNDARY_FAIL_CLOSED"
                            if identity == "R42_AUDJPY"
                            else "M5_FAST_BOUNDARY_FAIL_CLOSED"
                        )
                        payload: dict[str, object] = {
                            "event": event,
                            "symbol": symbol,
                            "decision_at": boundary_anchor.isoformat(),
                            "reason": reason,
                            "observed_at": observed_at.isoformat(),
                            "latency_ms": int(
                                (observed_at - boundary_anchor).total_seconds() * 1000
                            ),
                            "hard_sla_seconds": M5_PROFILE.decision_deadline.total_seconds(),
                            "order_send_called": False,
                        }
                        if message is not None:
                            payload["message"] = message
                        _log(log_path, payload)
                        mark_m5_terminal(identity, symbol)

                    for identity, symbol in (
                        ("R43_GBPUSD", "GBPUSD"),
                        ("R34_XAUUSD", "XAUUSD"),
                        ("R38_GBPJPY", "GBPJPY"),
                        ("R38_EURUSD", "EURUSD"),
                        ("R42_AUDJPY", "AUDJPY"),
                    ):
                        if m5_session_open[symbol]:
                            continue
                        _log(
                            log_path,
                            {
                                "event": "M5_MARKET_SESSION_CLOSED",
                                "identity": identity,
                                "symbol": symbol,
                                "decision_at": audjpy_arm_anchor.isoformat(),
                                "observed_at": datetime.now(UTC).isoformat(),
                                "source": "CTRADER_BROKER_SCHEDULE",
                                "order_send_called": False,
                            },
                        )
                        mark_m5_terminal(identity, symbol)

                    with ResidentMarketActorPool(max_workers=5) as market_actors:

                        def submit_ready_market(
                            symbol: str,
                            snapshot: M5BoundarySnapshot,
                            r43_state: R43LiveState = arm_r43_state,
                            r34_state: R34LiveState = arm_r34_state,
                            gbpjpy_state: R38GbpJpyLiveState = arm_gbpjpy_state,
                            r38_state: R38LiveState = arm_r38_state,
                            r42_state: R42AudJpyLiveState = arm_r42_state,
                            _ctx: dict[str, Any] = m5_ctx,
                        ) -> None:
                            snapshots: dict[str, M5BoundarySnapshot] = _ctx["ready_snapshots"]
                            snapshots[symbol] = snapshot
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
                                raise RuntimeError(
                                    f"unsupported resident M5 market:{symbol}"
                                )
                            anchor_keys: dict[str, str] = _ctx["anchor_keys"]
                            runtime_state: CTraderDemoRuntimeState = _ctx["state"]
                            terminal_ids: set[str] = _ctx["terminal_ids"]
                            if anchor_keys[symbol] in runtime_state.processed_anchors:
                                terminal_ids.add(identity)
                                return
                            market_actors.submit(
                                MarketBoundaryJob(
                                    identity=identity,
                                    symbol=symbol,
                                    evaluate=evaluate,
                                )
                            )

                        def consume_market_result(
                            actor_result: MarketBoundaryResult,
                            _ctx: dict[str, Any] = m5_ctx,
                        ) -> None:
                            audjpy_arm_anchor: datetime = _ctx["anchor"]
                            m5_deadline: datetime = _ctx["deadline"]
                            m5_terminal_identities: set[str] = _ctx["terminal_ids"]
                            ready_snapshots: dict[str, M5BoundarySnapshot] = _ctx["ready_snapshots"]
                            arm_blocked: bool = _ctx["arm_blocked"]
                            fast_plan_by_identity: dict[str, Any] = _ctx["fast_plan"]
                            arm_provider: Any = _ctx["arm_provider"]
                            arm_capital: Any = _ctx["arm_capital"]
                            arm_account: Any = _ctx["arm_account"]
                            arm_snapshot: AccountRiskSnapshot = _ctx["arm_snapshot"]
                            arm_specs: dict[str, CTraderDemoSymbolSpecification] = _ctx["arm_specs"]
                            identity = actor_result.identity
                            symbol = actor_result.symbol
                            if identity in m5_terminal_identities:
                                return
                            snapshot = ready_snapshots[symbol]
                            _log_market_decision_telemetry(
                                log_path=log_path,
                                anchor=audjpy_arm_anchor,
                                snapshot=snapshot,
                                result=actor_result,
                            )
                            done = actor_result.strategy_finished_at
                            if arm_blocked:
                                log_m5_hard_fail(
                                    identity,
                                    symbol,
                                    reason="preflight-new-order-blocked",
                                    observed_at=done,
                                )
                                return
                            if actor_result.error is not None:
                                log_m5_hard_fail(
                                    identity,
                                    symbol,
                                    reason=type(actor_result.error).__name__,
                                    message=str(actor_result.error),
                                    observed_at=done,
                                )
                                return
                            if done > m5_deadline:
                                log_m5_hard_fail(
                                    identity,
                                    symbol,
                                    reason="decision-deadline-expired",
                                    observed_at=done,
                                )
                                return

                            signal = actor_result.signal
                            reason = actor_result.reason
                            latency_ms = int(
                                (done - audjpy_arm_anchor).total_seconds() * 1000
                            )
                            if signal is None:
                                if identity == "R42_AUDJPY":
                                    _log(
                                        log_path,
                                        {
                                            "event": "AUDJPY_R42_CAUSAL_ABSTAIN",
                                            "symbol": symbol,
                                            "decision_at": audjpy_arm_anchor.isoformat(),
                                            "reason": reason,
                                            "observed_at": done.isoformat(),
                                            "latency_ms": latency_ms,
                                            "hard_sla_seconds": (
                                                AUDJPY_R42_ENTRY_SLA.total_seconds()
                                            ),
                                            "strategy_started_at": (
                                                actor_result.strategy_started_at.isoformat()
                                            ),
                                            "strategy_finished_at": done.isoformat(),
                                            "strategy_latency_ms": (
                                                actor_result.strategy_latency_ms
                                            ),
                                        },
                                    )
                                else:
                                    _, abstain_event, _ = fast_plan_by_identity[identity]
                                    _log(
                                        log_path,
                                        {
                                            "event": abstain_event,
                                            "symbol": symbol,
                                            "decision_at": audjpy_arm_anchor.isoformat(),
                                            "observed_at": done.isoformat(),
                                            "latency_ms": latency_ms,
                                            "reason": reason,
                                            "fast_path": True,
                                            "strategy_started_at": (
                                                actor_result.strategy_started_at.isoformat()
                                            ),
                                            "strategy_finished_at": done.isoformat(),
                                            "strategy_latency_ms": (
                                                actor_result.strategy_latency_ms
                                            ),
                                        },
                                    )
                                mark_m5_terminal(identity, symbol)
                                return

                            try:
                                if identity == "R42_AUDJPY":
                                    _process_audjpy_r42_candidate(
                                        signal=signal,
                                        now=done,
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
                                else:
                                    _, _, process_fast = fast_plan_by_identity[identity]
                                    process_fast(signal=signal, now=done)
                            except BrokerMinimumVolumeRiskRejectError as risk_reject:
                                _log(
                                    log_path,
                                    {
                                        "event": "RISK_REJECT_MINIMUM_BROKER_VOLUME",
                                        "symbol": symbol,
                                        "decision_at": audjpy_arm_anchor.isoformat(),
                                        "candidate": True,
                                        "order_send_called": False,
                                        **risk_reject.telemetry(),
                                    },
                                )
                            except Exception as market_error:
                                log_m5_hard_fail(
                                    identity,
                                    symbol,
                                    reason=type(market_error).__name__,
                                    message=str(market_error),
                                    observed_at=datetime.now(UTC),
                                )
                                return
                            mark_m5_terminal(identity, symbol)

                        def drain_ready_market_results(_observed: datetime) -> None:
                            for result in market_actors.ready_results():
                                consume_market_result(result)

                        pending_m5_caches = {
                            symbol: cache
                            for symbol, cache in m5_caches.items()
                            if (
                                m5_anchor_keys[symbol]
                                not in state.processed_anchors
                                and m5_session_open[symbol]
                            )
                        }
                        try:
                            armed_m5_snapshots = await_m5_boundary_snapshots(
                                mt5,
                                caches=pending_m5_caches,
                                anchor=audjpy_arm_anchor,
                                on_snapshot=submit_ready_market,
                                on_poll=drain_ready_market_results,
                            )
                        except TimeoutError:
                            # Zero snapshots by the real deadline is handled below
                            # as one terminal HARD_FAIL per missing market.
                            armed_m5_snapshots = {}

                        while (
                            market_actors.pending_identities()
                            and datetime.now(UTC) <= m5_deadline
                        ):
                            drain_ready_market_results(datetime.now(UTC))
                            if market_actors.pending_identities():
                                remaining = (
                                    m5_deadline - datetime.now(UTC)
                                ).total_seconds()
                                if remaining > 0:
                                    time.sleep(min(0.005, remaining))
                        drain_ready_market_results(datetime.now(UTC))

                        expected_markets = {
                            "R43_GBPUSD": "GBPUSD",
                            "R34_XAUUSD": "XAUUSD",
                            "R38_GBPJPY": "GBPJPY",
                            "R38_EURUSD": "EURUSD",
                            "R42_AUDJPY": "AUDJPY",
                        }
                        final_observed = max(datetime.now(UTC), m5_deadline)
                        for identity, symbol in expected_markets.items():
                            key = m5_anchor_keys[symbol]
                            if (
                                key in state.processed_anchors
                                or identity in m5_terminal_identities
                            ):
                                continue
                            if symbol not in ready_snapshots:
                                log_m5_hard_fail(
                                    identity,
                                    symbol,
                                    reason="market-snapshot-unavailable-within-sla",
                                    observed_at=final_observed,
                                )
                            else:
                                log_m5_hard_fail(
                                    identity,
                                    symbol,
                                    reason="decision-deadline-expired",
                                    observed_at=final_observed,
                                )

                    boundary_observed = max(
                        (item.observed_at for item in ready_snapshots.values()),
                        default=datetime.now(UTC),
                    )
                    cycle_at = max(boundary_observed, datetime.now(UTC))
                    audjpy_anchor_processed = (
                        "R42_AUDJPY" in m5_terminal_identities
                    )
                except Exception as error:
                    _log(
                        log_path,
                        {
                            "event": "M5_PORTFOLIO_PREARM_NOT_READY",
                            "decision_at": audjpy_arm_anchor.isoformat(),
                            "observed_at": datetime.now(UTC).isoformat(),
                            "reason": type(error).__name__,
                            "message": str(error),
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
                if audjpy_anchor_processed:
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
        late_delta = cycle_at - current_hour
        m5_portfolio_keys = (
            f"R43_GBPUSD|{current_hour.isoformat()}",
            f"R34_XAUUSD|{current_hour.isoformat()}",
            f"R38_GBPJPY|{current_hour.isoformat()}",
            f"R38_EURUSD|{current_hour.isoformat()}",
            f"R42_AUDJPY|{current_hour.isoformat()}",
        )
        m5_portfolio_identities = (
            ("R43_GBPUSD", "GBPUSD"),
            ("R34_XAUUSD", "XAUUSD"),
            ("R38_GBPJPY", "GBPJPY"),
            ("R38_EURUSD", "EURUSD"),
            ("R42_AUDJPY", "AUDJPY"),
        )
        if armed_m5_snapshots is None and any(
            key not in state.processed_anchors for key in m5_portfolio_keys
        ):
            if (
                late_delta > M5_PROFILE.order_send_deadline
                and late_delta <= _ANCHOR_GRACE
            ):
                missed_keys: list[str] = []
                for identity, symbol in m5_portfolio_identities:
                    key = f"{identity}|{current_hour.isoformat()}"
                    if key in state.processed_anchors:
                        continue
                    event = (
                        "AUDJPY_R42_BOUNDARY_FAIL_CLOSED"
                        if identity == "R42_AUDJPY"
                        else "M5_FAST_BOUNDARY_FAIL_CLOSED"
                    )
                    _log(
                        log_path,
                        {
                            "event": event,
                            "symbol": symbol,
                            "decision_at": current_hour.isoformat(),
                            "observed_at": cycle_at.isoformat(),
                            "latency_ms": int(late_delta.total_seconds() * 1000),
                            "reason": "boundary-not-prearmed-within-sla",
                            "hard_sla_seconds": (
                                M5_PROFILE.order_send_deadline.total_seconds()
                            ),
                            "order_send_called": False,
                        },
                    )
                    missed_keys.append(key)
                if missed_keys:
                    missed_at = datetime.now(UTC)
                    for key in missed_keys:
                        state = state.with_cycle(
                            highest_closed_balance=str(highest),
                            active_mll=str(previous_mll),
                            processed_anchor=key,
                            reconciled_at=missed_at,
                            heartbeat_at=missed_at,
                        )
                    store.store(state)

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
                vt31_account = _account_state_from_demo_api(demo_api, vt31_arm_started_at)
                # DEMO_FREE: no external reconciliation.
                vt31_highest = max(highest, vt31_account.balance)
                vt31_provider = SimpleNamespace()
                vt31_capital = SimpleNamespace(
                                        qore_authorizable_headroom=vt31_account.equity,
                )
                vt31_snapshot = None
                vt31_lifecycle = SimpleNamespace(value="DEMO_FREE")
                vt31_blocked = False
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
                        vt31_snapshot = None
                        vt31_execution_equity = demo_capital_for(
                            TraderLineage.VT31_NAS100
                        )
                    else:
                        vt31_execution_equity = vt31_account.equity
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
                    elif len(vt31_basket.candidates) == 1:
                        submit_vt31_single_live(
                            basket=vt31_basket,
                            boundary_at=vt31_arm_anchor,
                            gateway=gateway,
                            risk=risk,
                            snapshot=vt31_snapshot,
                            account_equity=vt31_execution_equity,
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

        account_state = _account_state_from_demo_api(demo_api, cycle_at)
        # DEMO_FREE: no FundedNext reconciliation.
        # cTrader DEMO is the only mutation target in this account runtime.
        # The MT5-compatible adapter below translates the frozen Trader lifecycle
        # into cTrader position reads, partial closes and SL/TP amendments.
        demo_has_state = (
            bool(demo_sink.registry.entries())
            or vt31_store.load().pending_broker_order is not None
            or vt31_store.load().open_trade is not None
        )
        if demo_has_state:
            management_trader = "R34_XAUUSD"
            try:
                r34_live_state = run_with_bounded_repair(
                    trader="R34_XAUUSD",
                    operation=lambda: r34_store.reconcile(
                        demo_management_api,
                        now=datetime.now(UTC),
                    ),
                    recover=lambda: recover_demo_market_state(
                        symbol="XAUUSD",
                        cache=m5_caches["XAUUSD"],
                    ),
                    emit=lambda event: _log(log_path, event),
                )
                management_trader = "R38_EURUSD"
                r38_live_state, r38_manage_reason = run_with_bounded_repair(
                    trader="R38_EURUSD",
                    operation=lambda: manage_r38_open_position(
                        demo_management_api,
                        now=datetime.now(UTC),
                        store=r38_store,
                        cache=m5_caches["EURUSD"],
                    ),
                    recover=lambda: recover_demo_market_state(
                        symbol="EURUSD",
                        cache=m5_caches["EURUSD"],
                    ),
                    emit=lambda event: _log(log_path, event),
                )
                management_trader = "R43_GBPUSD"
                r43_live_state, r43_manage_reason = run_with_bounded_repair(
                    trader="R43_GBPUSD",
                    operation=lambda: manage_r43_open_position(
                        demo_management_api,
                        now=datetime.now(UTC),
                        store=r43_store,
                        cache=m5_caches["GBPUSD"],
                    ),
                    recover=lambda: recover_demo_market_state(
                        symbol="GBPUSD",
                        cache=m5_caches["GBPUSD"],
                    ),
                    emit=lambda event: _log(log_path, event),
                )
                management_trader = "R38_GBPJPY"
                gbpjpy_r38_live_state, gbpjpy_r38_manage_reason = run_with_bounded_repair(
                    trader="R38_GBPJPY",
                    operation=lambda: manage_gbpjpy_r38_open_position(
                        demo_management_api,
                        now=datetime.now(UTC),
                        store=gbpjpy_r38_store,
                        mutations_enabled=True,
                        cache=m5_caches["GBPJPY"],
                    ),
                    recover=lambda: recover_demo_market_state(
                        symbol="GBPJPY",
                        cache=m5_caches["GBPJPY"],
                    ),
                    emit=lambda event: _log(log_path, event),
                )
                management_trader = "R42_AUDJPY"
                audjpy_r42_live_state, audjpy_r42_manage_reason = run_with_bounded_repair(
                    trader="R42_AUDJPY",
                    operation=lambda: manage_audjpy_r42_open_position(
                        demo_management_api,
                        now=datetime.now(UTC),
                        store=audjpy_r42_store,
                        mutations_enabled=True,
                        cache=audjpy_r42_cache,
                    ),
                    recover=lambda: recover_demo_market_state(
                        symbol="AUDJPY",
                        cache=audjpy_r42_cache,
                    ),
                    emit=lambda event: _log(log_path, event),
                )
                management_trader = "VT31_NAS100"
                # VT31 reads a fresh broker tick inside reconcile/management.
                # Do not compare that tick with cycle_at captured several seconds
                # earlier after other trader management and API work.
                vt31_management_at = datetime.now(UTC)
                run_with_bounded_repair(
                    trader="VT31_NAS100",
                    operation=lambda: reconcile_vt31_pending(
                        mt5_api=demo_management_api,
                        transport=transport,
                        risk=risk,
                        store=vt31_store,
                        now=datetime.now(UTC),
                        log=lambda event: _log(log_path, event),
                    ),
                    recover=lambda: recover_demo_market_state(
                        symbol="NAS100",
                        cache=vt31_cache,
                    ),
                    emit=lambda event: _log(log_path, event),
                )
                vt31_live_state, vt31_manage_reason = run_with_bounded_repair(
                    trader="VT31_NAS100",
                    operation=lambda: manage_vt31_open_trade(
                        mt5_api=demo_management_api,
                        now=datetime.now(UTC),
                        cache=vt31_cache,
                        store=vt31_store,
                        mutations_enabled=True,
                        log=lambda event: _log(log_path, event),
                    ),
                    recover=lambda: recover_demo_market_state(
                        symbol="NAS100",
                        cache=vt31_cache,
                    ),
                    emit=lambda event: _log(log_path, event),
                )

                management_rows = (
                    (
                        "R34_XAUUSD",
                        "XAUUSD",
                        r34_live_state,
                        (
                            "r34-static-sl-tp-hold"
                            if r34_live_state.open_trade is not None
                            else "no-open-r34-position"
                        ),
                    ),
                    ("R38_EURUSD", "EURUSD", r38_live_state, r38_manage_reason),
                    ("R43_GBPUSD", "GBPUSD", r43_live_state, r43_manage_reason),
                    (
                        "R38_GBPJPY",
                        "GBPJPY",
                        gbpjpy_r38_live_state,
                        gbpjpy_r38_manage_reason,
                    ),
                    (
                        "R42_AUDJPY",
                        "AUDJPY",
                        audjpy_r42_live_state,
                        audjpy_r42_manage_reason,
                    ),
                    ("VT31_NAS100", "NAS100", vt31_live_state, vt31_manage_reason),
                )
                for (
                    management_trader,
                    management_symbol,
                    management_state,
                    management_reason,
                ) in management_rows:
                    observation = management_observation_payload(
                        trader=management_trader,
                        symbol=management_symbol,
                        state=management_state,
                        reason=management_reason,
                        observed_at=datetime.now(UTC),
                    )
                    stable_observation = {
                        key: value
                        for key, value in observation.items()
                        if key != "observed_at"
                    }
                    observation_fingerprint = hashlib.sha256(
                        json.dumps(
                            stable_observation,
                            sort_keys=True,
                            default=str,
                            separators=(",", ":"),
                        ).encode("utf-8")
                    ).hexdigest()
                    if (
                        last_management_observation.get(management_trader)
                        != observation_fingerprint
                    ):
                        _log(log_path, observation)
                        last_management_observation[management_trader] = (
                            observation_fingerprint
                        )

                # Certified 24h lifecycle for Turtle Soup lineages.
                for state_obj, reason, label in (
                    (r38_live_state, r38_manage_reason, "R38_EURUSD"),
                    (r43_live_state, r43_manage_reason, "R43_GBPUSD"),
                    (gbpjpy_r38_live_state, gbpjpy_r38_manage_reason, "R38_GBPJPY"),
                    (audjpy_r42_live_state, audjpy_r42_manage_reason, "R42_AUDJPY"),
                ):
                    opened = getattr(state_obj, "open_trade", None)
                    if opened is not None and "24h-exit-due" in reason:
                        if demo_management_api.close_position_for_magic(
                            _magic(opened.client_order_id)
                        ):
                            _log(
                                log_path,
                                {
                                    "event": "CTRADER_DEMO_24H_EXIT_ACCEPTED",
                                    "trader": label,
                                    "signal_fingerprint": opened.signal_fingerprint,
                                },
                            )

                r34_opened = r34_live_state.open_trade
                if (
                    r34_opened is not None
                    and cycle_at >= datetime.fromisoformat(r34_opened.entry_at) + timedelta(hours=24)
                    and demo_management_api.close_position_for_magic(
                        _magic(r34_opened.client_order_id)
                    )
                ):
                    _log(
                        log_path,
                        {
                            "event": "CTRADER_DEMO_24H_EXIT_ACCEPTED",
                            "trader": "R34_XAUUSD",
                            "signal_fingerprint": r34_opened.signal_fingerprint,
                        },
                    )

                # VT08 certified H4 containment exit has no lineage-specific store.
                demo_management_api.positions_get()
                for reg in demo_sink.registry.entries():
                    if reg.trader != TraderLineage.VT08_FOREX.value or reg.position_id is None:
                        continue
                    accepted_at = datetime.fromisoformat(reg.submitted_at)
                    try:
                        due = h4_containment_exit_at(_signal_anchor(accepted_at))
                    except RuntimeError:
                        continue
                    if cycle_at >= due and demo_management_api.close_position_for_magic(
                        _magic(reg.client_order_id)
                    ):
                        _log(
                            log_path,
                            {
                                "event": "CTRADER_DEMO_VT08_H4_EXIT_ACCEPTED",
                                "signal_fingerprint": reg.signal_fingerprint,
                            },
                        )
            except Exception as demo_management_error:
                fault_signal: str | None = None
                try:
                    fault_store = {
                        "R34_XAUUSD": r34_store,
                        "R38_EURUSD": r38_store,
                        "R43_GBPUSD": r43_store,
                        "R38_GBPJPY": gbpjpy_r38_store,
                        "R42_AUDJPY": audjpy_r42_store,
                        "VT31_NAS100": vt31_store,
                    }[management_trader]
                    fault_opened = getattr(fault_store.load(), "open_trade", None)
                    fault_signal = (
                        None
                        if fault_opened is None
                        else getattr(fault_opened, "signal_fingerprint", None)
                    )
                except Exception:
                    fault_signal = None
                failure_payload: dict[str, object] = {
                    "event": "CTRADER_DEMO_MANAGEMENT_FAIL_CLOSED",
                    "trader": management_trader,
                    "reason": type(demo_management_error).__name__,
                    "message": str(demo_management_error),
                }
                if fault_signal:
                    failure_payload["signal_fingerprint"] = fault_signal
                _log(log_path, failure_payload)
                r34_live_state = r34_store.load()
                r38_live_state = r38_store.load()
                r43_live_state = r43_store.load()
                gbpjpy_r38_live_state = gbpjpy_r38_store.load()
                audjpy_r42_live_state = audjpy_r42_store.load()
                vt31_live_state = vt31_store.load()
        else:
            r34_live_state = r34_store.load()
            r38_live_state = r38_store.load()
            r43_live_state = r43_store.load()
            gbpjpy_r38_live_state = gbpjpy_r38_store.load()
            audjpy_r42_live_state = audjpy_r42_store.load()
            vt31_live_state = vt31_store.load()

        try:
            for position in demo_management_api.positions_get():
                position_id = int(getattr(position, "ticket"))
                registry_entries = demo_sink.registry.entries_by_position(position_id)
                if not registry_entries:
                    continue
                registry_entry = registry_entries[0]
                symbol = str(getattr(position, "symbol"))
                tick = demo_management_api.symbol_info_tick(symbol)
                if tick is None:
                    continue
                observed_at = datetime.now(UTC)
                side = (
                    "long"
                    if int(getattr(position, "type"))
                    == int(demo_management_api.POSITION_TYPE_BUY)
                    else "short"
                )
                entry_price = Decimal(str(getattr(position, "price_open")))
                stop_loss = Decimal(str(getattr(position, "sl", 0)))
                remaining_volume = Decimal(str(getattr(position, "volume")))
                _log(
                    log_path,
                    position_path_observation_payload(
                        trader=registry_entry.trader,
                        symbol=symbol,
                        signal_fingerprint=registry_entry.signal_fingerprint,
                        position_id=position_id,
                        side=side,
                        entry_price=entry_price,
                        bid=Decimal(str(getattr(tick, "bid"))),
                        ask=Decimal(str(getattr(tick, "ask"))),
                        stop_loss=stop_loss,
                        take_profit=Decimal(str(getattr(position, "tp", 0))),
                        volume=remaining_volume,
                        unrealized_pnl=Decimal(str(getattr(position, "profit", 0))),
                        observed_at=observed_at,
                    ),
                )

                cma_spec = gateway.read_symbol(
                    registry_entry.qore_symbol,
                    now=observed_at,
                )
                cma_result = observe_runtime_position(
                    CmaRuntimePositionSnapshot(
                        trader_id=TraderLineage(registry_entry.trader),
                        signal_fingerprint=registry_entry.signal_fingerprint,
                        qore_symbol=registry_entry.qore_symbol,
                        position_id=position_id,
                        registry_leg_count=len(registry_entries),
                        side=side,
                        entry_price=entry_price,
                        current_stop=stop_loss,
                        initial_volume=Decimal(registry_entry.requested_volume),
                        remaining_volume=remaining_volume,
                        tick_size=cma_spec.tick_size,
                        tick_value=cma_spec.tick_value,
                        broker_position_reconciled=True,
                        broker_stop_reconciled=stop_loss > 0,
                        mutation_outcome_unknown=gateway.has_unresolved_mutations,
                        observed_at=observed_at,
                    ),
                    settlement_store=cma_settlement_store,
                    lifecycle_store=cma_lifecycle_store,
                )
                if cma_result.failure_payload is not None:
                    _log(log_path, cma_result.failure_payload)
                else:
                    assert cma_result.observation is not None
                    _log(log_path, cma_result.observation.as_payload())
        except Exception as behavior_sample_error:
            _log(
                log_path,
                {
                    "event": "BEHAVIOR_LAB_POSITION_SAMPLE_ERROR",
                    "reason": type(behavior_sample_error).__name__,
                    "message": str(behavior_sample_error),
                    "observed_at": datetime.now(UTC).isoformat(),
                },
            )

        # DEMO_FREE: no FundedNext trailing MLL, prop capital budget, or mission gate.
        highest = max(highest, account_state.balance)
        previous_mll = account_state.equity
        aggregate = Decimal("0")
        posture = request_cibo_posture(
            initial_balance=account_state.balance,
            balance=account_state.balance,
            equity=account_state.equity,
            current_aggregate_risk=Decimal("0"),
        )
        provider = SimpleNamespace()
        capital = SimpleNamespace(
                        qore_authorizable_headroom=account_state.equity,
        )
        lifecycle = SimpleNamespace(value="DEMO_FREE")
        last_lifecycle = "DEMO_FREE"

        anchor = _current_anchor(cycle_at)
        processed_anchor: str | None = None
        # cTrader DEMO FREE: FundedNext economics, inactivity and prop-policy
        # are observational only. Technical integrity is enforced inside the DEMO sink.
        new_order_blocked = False
        vt31_runtime_snapshot = None
        # DEMO_FREE: no prop-firm pending-order reconciliation.
        if not new_order_blocked:
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
                    r34_live_state = r34_store.load()
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
                    r38_live_state = r38_store.load()
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
                    r43_live_state = r43_store.load()
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
                    gbpjpy_r38_live_state = gbpjpy_r38_store.load()
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
    parser.add_argument("--mode", choices=("demo",), default="demo")
    parser.add_argument(
        "--activation",
        type=Path,
        default=Path("var/ctrader_demo_free/demo-runtime.json"),
    )
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    recovery_log = root / "artifacts" / "ctrader_demo_free_runtime_events.jsonl"
    lock = CTraderDemoSingleWriterLock(root / "var" / "ctrader_demo_signal_runtime" / "runtime.lock")
    try:
        with lock:
            run(
                root,
                mode=args.mode,
                activation_path=(root / args.activation),
            )
        raise RuntimeError("resident runtime returned unexpectedly")
    except KeyboardInterrupt:
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
        raise SystemExit(1) from error


if __name__ == "__main__":
    main()
