"""Live MT5 adapter for certified TURTLE_SOUP_GBPUSD_R43.

R43 preserves the frozen GBPUSD five-year contract certified by R45.  It uses
the immutable R32_REGIME_ROUTE_TYPES memory snapshot derived from the official
R27 artifact, the frozen R37 G25 structural families, SQ3 structural sizing,
the R43 SHORT/rank-2 overlays, and the causal DD_1_3 risk governor.

FundedNext server timestamps are normalized to UTC; strategy context is New
York time.  Broker granularity is fail-closed: the adapter never rounds a
certified risk budget upward merely to reach the broker minimum lot.

Certified lifecycle:
- exact C2 / causal CISD / Protected Swing;
- R32 regime-route core + R37 F2/F5 expansion;
- SQ3_H1_BALANCED structural risk scale;
- SHORT overlay 0.005 and rank-2 overlay 0.25;
- DD_1_3_SCALE_075_025 causal strategy drawdown governor;
- STATIC / PROTECT posture exactly as resolved by memory;
- DOL lock for non-static rank>1 targets;
- confirmed M5 swing trail only for PROTECT;
- structural rearm after a trailing-stop exit;
- 24H maximum lifecycle;
- single-position busy within R43.
"""
from __future__ import annotations

import hashlib
import json
import os
import tempfile
from dataclasses import asdict, dataclass
from datetime import UTC, datetime, timedelta
from decimal import ROUND_FLOOR, Decimal
from pathlib import Path
from typing import Any, cast

from qore.infrastructure.account_wide_risk import CiboRiskRequest, TraderLineage
from qore.infrastructure.fundednext_live_guard import FOREX_OPEN_COMMISSION_PER_LOT_USD
from qore.infrastructure.fundednext_mt5 import Mt5SymbolSpecification
from qore.infrastructure.fundednext_mt5_clock import (
    NEW_YORK_TZ,
    normalise_fundednext_server_epoch,
)
from qore.infrastructure.trader_lab import cibo_market_atlas_target_destination_v2 as td
from qore.infrastructure.trader_lab import cibo_gbpusd_native_market_decision_memory_v2 as native
from qore.infrastructure.trader_lab import turtle_soup_gbpusd_r1 as r1
from qore.infrastructure.trader_lab import turtle_soup_gbpusd_r2_cibo_full as r2
from qore.infrastructure.trader_lab import turtle_soup_gbpusd_r3_cibo_journey as r3
from qore.infrastructure.trader_lab import turtle_soup_gbpusd_r26_specialist_memory_brain as r26
from qore.infrastructure.trader_lab import (
    turtle_soup_gbpusd_r32_causal_memory_defragmentation as r32,
)
from qore.infrastructure.trader_lab import (
    turtle_soup_gbpusd_r37_structural_quality_governor as r37,
)
from qore.infrastructure.trader_lab import turtle_soup_gbpusd_specialist_cognitive_memory_v2 as v2
from qore.infrastructure.trader_lab import turtle_soup_gbpusd_specialist_memory_v1 as v1
from qore.infrastructure.trader_lab.ict_turtle_soup_r4_source_exact import (
    Bar,
    Evidence,
    Side,
    SourceCandle,
    _h4_open_for,
    build_daily,
    build_h1,
    build_h4,
    build_m15,
    causal_cisd,
)

IDENTITY = "TURTLE_SOUP_GBPUSD_R43"
CERTIFICATION_IDENTITY = "TURTLE_SOUP_GBPUSD_R45_FINAL_CERTIFICATION_SUITE_V1"
CERTIFICATION_RUN_ID = 35358106508
CERTIFICATION_ARTIFACT_ID = 10552752028
CERTIFICATION_ARTIFACT_DIGEST = (
    "sha256:e0ec17f8ac57a4997a65fc48e9d756925aecf8ee442a210451bb75918d1628e2"
)
SYMBOL = "GBPUSD"
FAMILY_SET = "R37_G25_FIXED"
ALLOWED_FAMILIES = r37.FAMILY_SETS[FAMILY_SET]
STRUCTURAL_POLICY = "SQ3_H1_BALANCED"
STRUCTURAL_POLICY_RULE = r37.STRUCTURAL_POLICIES[STRUCTURAL_POLICY]
DRAWDOWN_GOVERNOR = "DD_1_3_SCALE_075_025"
DRAWDOWN_GOVERNOR_RULE = r37.GOVERNORS[DRAWDOWN_GOVERNOR]
SHORT_OVERLAY_SCALE = Decimal("0.005")
RANK2_OVERLAY_SCALE = Decimal("0.25")
MEMORY_IDENTITY = "TURTLE_SOUP_GBPUSD_R43_LIVE_MEMORY_V1"
MEMORY_SHA256 = "e4a79978c0144e0b97c19ce3ee18040e62a02efe891b204fc724e4a0016734ae"
MEMORY_PROFILE_COUNT = 4246
BASE_RISK_FRACTION = Decimal("0.002")
MAX_SOURCE_ENTRY_DRIFT_R = Decimal("0.10")
BROKER_RISK_BUFFER = Decimal("1.02")
ANCHOR_GRACE = timedelta(seconds=45)
HISTORY_M5_BARS = 15_000
_STATE_SCHEMA = "qore.turtle_soup_gbpusd.r43.live_state.v1"
_STRATEGY_TZ = NEW_YORK_TZ


@dataclass(frozen=True, slots=True)
class R43Dol:
    rank: int
    level: str
    route: str


@dataclass(frozen=True, slots=True)
class R43LiveSignal:
    signal_fingerprint: str
    entry_at: datetime
    timeframe: str
    side: str
    certified_entry: Decimal
    stop_loss: Decimal
    take_profit: Decimal
    target_rank: int
    target_route: str
    decision_source: str
    family: str | None
    classification: str
    posture: str
    structural_scale: Decimal
    side_overlay_scale: Decimal
    rank_overlay_scale: Decimal
    drawdown_scale: Decimal
    risk_scale: Decimal
    ladder: tuple[R43Dol, ...]

    def __post_init__(self) -> None:
        if len(self.signal_fingerprint) != 64:
            raise ValueError("R43 signal fingerprint must be SHA-256")
        if self.timeframe not in {"H1", "H4"}:
            raise ValueError("R43 timeframe must be H1/H4")
        if self.side not in {"long", "short"}:
            raise ValueError("R43 side must be long/short")
        if self.posture not in native.POSTURES:
            raise ValueError("R43 posture drift")
        for name, scale in (
            ("structural_scale", self.structural_scale),
            ("side_overlay_scale", self.side_overlay_scale),
            ("rank_overlay_scale", self.rank_overlay_scale),
            ("drawdown_scale", self.drawdown_scale),
            ("risk_scale", self.risk_scale),
        ):
            if not Decimal("0") < scale <= Decimal("1"):
                raise ValueError(f"R43 {name} drift")


@dataclass(frozen=True, slots=True)
class R43OpenTrade:
    client_order_id: str
    signal_fingerprint: str
    entry_at: str
    side: str
    entry_price: str
    initial_stop: str
    current_stop: str
    take_profit: str
    posture: str
    target_rank: int
    target_route: str
    ladder: tuple[R43Dol, ...]
    base_risk_usd: str
    risk_scale: str


@dataclass(frozen=True, slots=True)
class R43LiveState:
    open_trade: R43OpenTrade | None = None
    closed_signal_fingerprints: tuple[str, ...] = ()
    last_trailing_exit_at: str | None = None
    strategy_equity_r: str = "0"
    strategy_peak_r: str = "0"

    @property
    def trailing_exit_at(self) -> datetime | None:
        if self.last_trailing_exit_at is None:
            return None
        value = datetime.fromisoformat(self.last_trailing_exit_at)
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("R43 trailing-exit timestamp must be timezone-aware")
        return value

    @property
    def drawdown_r(self) -> Decimal:
        equity = Decimal(self.strategy_equity_r)
        peak = Decimal(self.strategy_peak_r)
        if peak < equity:
            raise ValueError("R43 strategy peak cannot be below equity")
        return peak - equity


class R43LiveStateStore:
    def __init__(self, path: Path) -> None:
        self._path = path

    def load(self) -> R43LiveState:
        if not self._path.exists():
            return R43LiveState()
        raw = json.loads(self._path.read_text(encoding="utf-8"))
        if raw.get("schema") != _STATE_SCHEMA:
            raise ValueError("R43 live-state schema mismatch")
        open_raw = raw.get("open_trade")
        open_trade: R43OpenTrade | None = None
        if open_raw is not None:
            open_copy = dict(open_raw)
            ladder = tuple(R43Dol(**item) for item in open_copy.pop("ladder"))
            open_trade = R43OpenTrade(**open_copy, ladder=ladder)
        return R43LiveState(
            open_trade=open_trade,
            closed_signal_fingerprints=tuple(raw.get("closed_signal_fingerprints", ())),
            last_trailing_exit_at=raw.get("last_trailing_exit_at"),
            strategy_equity_r=str(raw.get("strategy_equity_r", "0")),
            strategy_peak_r=str(raw.get("strategy_peak_r", "0")),
        )

    def store(self, state: R43LiveState) -> None:
        payload = {
            "schema": _STATE_SCHEMA,
            "identity": IDENTITY,
            "open_trade": None if state.open_trade is None else asdict(state.open_trade),
            "closed_signal_fingerprints": list(state.closed_signal_fingerprints[-256:]),
            "last_trailing_exit_at": state.last_trailing_exit_at,
            "strategy_equity_r": state.strategy_equity_r,
            "strategy_peak_r": state.strategy_peak_r,
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
                json.dump(payload, handle, sort_keys=True, separators=(",", ":"))
                handle.write("\n")
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temp, self._path)
        finally:
            if temp.exists():
                temp.unlink()

    def mark_open(
        self,
        *,
        client_order_id: str,
        signal: R43LiveSignal,
        base_risk_usd: Decimal,
    ) -> R43LiveState:
        state = self.load()
        if state.open_trade is not None:
            raise ValueError("R43 single-position-busy")
        opened = R43OpenTrade(
            client_order_id=client_order_id,
            signal_fingerprint=signal.signal_fingerprint,
            entry_at=signal.entry_at.isoformat(),
            side=signal.side,
            entry_price=str(signal.certified_entry),
            initial_stop=str(signal.stop_loss),
            current_stop=str(signal.stop_loss),
            take_profit=str(signal.take_profit),
            posture=signal.posture,
            target_rank=signal.target_rank,
            target_route=signal.target_route,
            ladder=signal.ladder,
            base_risk_usd=str(base_risk_usd),
            risk_scale=str(signal.risk_scale),
        )
        next_state = R43LiveState(
            open_trade=opened,
            closed_signal_fingerprints=state.closed_signal_fingerprints,
            last_trailing_exit_at=state.last_trailing_exit_at,
            strategy_equity_r=state.strategy_equity_r,
            strategy_peak_r=state.strategy_peak_r,
        )
        self.store(next_state)
        return next_state

    def update_stop(self, new_stop: Decimal) -> R43LiveState:
        state = self.load()
        opened = state.open_trade
        if opened is None:
            raise ValueError("R43 cannot update stop without open trade")
        updated = R43OpenTrade(
            **{
                **asdict(opened),
                "ladder": opened.ladder,
                "current_stop": str(new_stop),
            }
        )
        next_state = R43LiveState(
            open_trade=updated,
            closed_signal_fingerprints=state.closed_signal_fingerprints,
            last_trailing_exit_at=state.last_trailing_exit_at,
            strategy_equity_r=state.strategy_equity_r,
            strategy_peak_r=state.strategy_peak_r,
        )
        self.store(next_state)
        return next_state

    def reconcile(self, api: Any, *, now: datetime) -> R43LiveState:
        state = self.load()
        opened = state.open_trade
        if opened is None:
            return state
        magic = _magic(opened.client_order_id)
        positions = api.positions_get() or ()
        if any(int(item.magic) == magic for item in positions):
            return state
        start = datetime.fromisoformat(opened.entry_at) - timedelta(hours=1)
        deals = api.history_deals_get(start, now) or ()
        matching = [item for item in deals if int(item.magic) == magic]
        if not matching:
            return state
        exits = [
            item
            for item in matching
            if int(getattr(item, "entry", -1))
            == int(getattr(api, "DEAL_ENTRY_OUT", -2))
        ]
        if not exits:
            return state
        last = max(exits, key=lambda item: int(getattr(item, "time", 0)))
        closed_at = normalise_fundednext_server_epoch(int(last.time))
        trailing_exit = state.last_trailing_exit_at
        moved = Decimal(opened.current_stop) != Decimal(opened.initial_stop)
        if (
            moved
            and int(getattr(last, "reason", -1))
            == int(getattr(api, "DEAL_REASON_SL", -2))
        ):
            trailing_exit = closed_at.isoformat()

        realized_usd = sum(
            (
                Decimal(str(getattr(item, "profit", 0)))
                + Decimal(str(getattr(item, "commission", 0)))
                + Decimal(str(getattr(item, "swap", 0)))
                + Decimal(str(getattr(item, "fee", 0)))
            )
            for item in matching
        , Decimal(0))
        base_risk = Decimal(opened.base_risk_usd)
        if base_risk <= 0:
            raise ValueError("R43 base risk must be positive")
        realized_r = realized_usd / base_risk
        equity = Decimal(state.strategy_equity_r) + realized_r
        peak = max(Decimal(state.strategy_peak_r), equity)

        closed = tuple(
            (*state.closed_signal_fingerprints, opened.signal_fingerprint)
        )[-256:]
        next_state = R43LiveState(
            open_trade=None,
            closed_signal_fingerprints=closed,
            last_trailing_exit_at=trailing_exit,
            strategy_equity_r=str(equity),
            strategy_peak_r=str(peak),
        )
        self.store(next_state)
        return next_state


def _magic(client_order_id: str) -> int:
    digest = hashlib.sha256(client_order_id.encode("utf-8")).digest()
    return int.from_bytes(digest[:4], "big") & 0x7FFFFFFF


def current_anchor(now: datetime) -> datetime | None:
    """Return the current R43 H1 anchor on the New York strategy clock."""
    local = now.astimezone(_STRATEGY_TZ)
    anchor_local = local.replace(minute=0, second=0, microsecond=0)
    if local < anchor_local or local - anchor_local > ANCHOR_GRACE:
        return None
    return anchor_local.astimezone(UTC)


def mt5_evidence(api: Any, *, now: datetime) -> tuple[Evidence, Decimal]:
    rows = api.copy_rates_from_pos(SYMBOL, api.TIMEFRAME_M5, 0, HISTORY_M5_BARS)
    if rows is None or len(rows) < 2_000:
        raise RuntimeError("R43 M5 history unavailable")
    info = api.symbol_info(SYMBOL)
    if info is None:
        raise RuntimeError("R43 GBPUSD symbol info unavailable")
    retained: dict[datetime, Bar] = {}
    for row in rows:
        opened = normalise_fundednext_server_epoch(int(row["time"]))
        bar = Bar(
            opened_at=opened,
            closed_at=opened + timedelta(minutes=5),
            open=Decimal(str(row["open"])),
            high=Decimal(str(row["high"])),
            low=Decimal(str(row["low"])),
            close=Decimal(str(row["close"])),
        )
        prior = retained.get(opened)
        if prior is not None and prior != bar:
            raise RuntimeError("R43 contradictory MT5 M5 bar")
        retained[opened] = bar
    bars = tuple(retained[key] for key in sorted(retained))
    latest = bars[-1].opened_at
    if abs((now.astimezone(UTC) - latest).total_seconds()) > 600:
        raise RuntimeError("R43 MT5 clock normalization stale")
    return (
        Evidence(symbol=SYMBOL, digits=int(info.digits), bars=bars),
        Decimal(str(rows[-1]["open"])),
    )


def load_memory(
    path: Path,
) -> tuple[tuple[str, ...], str, dict[tuple[str, str], r32.Profile]]:
    raw = path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != MEMORY_SHA256:
        raise ValueError("R43 live memory hash drift")
    payload = json.loads(raw)
    if not isinstance(payload, dict) or payload.get("identity") != MEMORY_IDENTITY:
        raise ValueError("R43 live memory identity drift")
    source = payload.get("source")
    if not isinstance(source, dict):
        raise ValueError("R43 live memory source missing")
    if int(source.get("run_id", -1)) != 35339237432:
        raise ValueError("R43 live memory run binding drift")
    if int(source.get("artifact_id", -1)) != 10544098544:
        raise ValueError("R43 live memory artifact binding drift")
    if source.get("observations_sha256") != (
        "cc9176146a6d20b27ae8c55d0ec807156c7de3a82f651a9c2bca308d733b719c"
    ):
        raise ValueError("R43 live memory observations binding drift")
    if payload.get("scheme") != "R32_REGIME_ROUTE_TYPES":
        raise ValueError("R43 live memory scheme drift")
    fields = tuple(str(item) for item in payload.get("fields", ()))
    expected_fields, expected_route_mode = r32.SCHEMES["R32_REGIME_ROUTE_TYPES"]
    if fields != expected_fields:
        raise ValueError("R43 live memory fields drift")
    route_mode = str(payload.get("route_mode"))
    if route_mode != expected_route_mode:
        raise ValueError("R43 live memory route mode drift")
    rows = payload.get("profiles")
    if not isinstance(rows, list) or len(rows) != MEMORY_PROFILE_COUNT:
        raise ValueError("R43 live memory profile count drift")
    memory: dict[tuple[str, str], r32.Profile] = {}
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError("R43 live memory profile type drift")
        key = (str(row["signature"]), str(row["target_family"]))
        if key in memory:
            raise ValueError("R43 live memory duplicate profile")
        memory[key] = r32.Profile(
            observations=int(row["observations"]),
            distinct_quarters=int(row["distinct_quarters"]),
            reach_rate=Decimal(str(row["reach_rate"])),
            posture=str(row["posture"]),
            classification=str(row["classification"]),
            validated=bool(row["validated"]),
        )
    return fields, route_mode, memory


def _live_setup(
    *,
    timeframe: str,
    candles: tuple[SourceCandle, ...],
    anchor: datetime,
    current_open: Decimal,
) -> r3.Setup | None:
    matches = [index for index, candle in enumerate(candles) if candle.closed_at == anchor]
    if len(matches) != 1:
        return None
    pos = matches[0]
    if pos < 21:
        return None
    c1, c2 = candles[pos - 1], candles[pos]
    side = r1.exact_c2_side(c1, c2)
    if side is None:
        return None
    raid_at = r1._raid_at(c2, c1, side)
    if raid_at is None:
        return None
    lower = r1._m5_sources(c2.m5) if timeframe == "H1" else build_m15(c2.m5)
    extreme = c2.low if side is Side.LONG else c2.high
    cisd = causal_cisd(lower, side=side, extreme=extreme)
    if cisd is None or cisd.confirmed_at > c2.closed_at:
        return None
    stop = cisd.protected_swing
    target = c1.high if side is Side.LONG else c1.low
    risk = current_open - stop if side is Side.LONG else stop - current_open
    reward = target - current_open if side is Side.LONG else current_open - target
    if risk <= 0 or reward <= 0 or not r1._target_untouched(c2, side, target):
        return None
    signal = r1.Signal(
        timeframe=timeframe,
        side=side,
        c1_opened_at=c1.opened_at,
        c2_opened_at=c2.opened_at,
        raid_at=raid_at,
        cisd_at=cisd.confirmed_at,
        entry_at=anchor,
        entry=current_open,
        protected_swing=stop,
        target=target,
        projected_r=reward / risk,
        session_bucket=r1._session_bucket(raid_at),
        prior_body_alignment=r1._prior_alignment(c1, side),
    )
    previous = candles[max(0, pos - 20):pos]
    mean_range = sum(
        (item.high - item.low for item in previous),
        Decimal(0),
    ) / Decimal(len(previous))
    source_range = c2.high - c2.low
    raid_level = c1.low if side is Side.LONG else c1.high
    raid_extreme = c2.low if side is Side.LONG else c2.high
    raid_units = None if mean_range <= 0 else abs(raid_extreme - raid_level) / mean_range
    reclaim = r2._first_reclaim_latency(c2, c1, side, raid_at)
    duration = Decimal(60 if timeframe == "H1" else 240)
    cisd_progress = (
        Decimal(str((cisd.confirmed_at - c2.opened_at).total_seconds() / 60))
        / duration
    )
    protected_ratio = None if source_range <= 0 else risk / source_range
    range_state = None if mean_range <= 0 else source_range / mean_range
    body, wick, close_location = r2._geometry(c2, side)
    target_ratio = None if source_range <= 0 else reward / source_range
    peers = [
        r2._same_boundary(item, side)
        for item in candles[max(0, pos - 21):pos - 1]
    ]
    equal = any(level == r2._same_boundary(c1, side) for level in peers)
    local = raid_at.astimezone(r2.NY)
    context = r2.ContextSignal(
        signal=signal,
        timeframe=timeframe,
        side=side.value,
        session=signal.session_bucket,
        weekday=local.strftime("%A"),
        prior_body_alignment=signal.prior_body_alignment,
        fvg_before_entry=(
            "yes"
            if r2._fvg_before_entry(c2.m5, raid_at, anchor, side)
            else "no"
        ),
        exact_equal_liquidity="yes" if equal else "no",
        raid_depth_range_bucket=r2._bucket(
            raid_units,
            (Decimal("0.05"), Decimal("0.10"), Decimal("0.25"), Decimal("0.50")),
        ),
        reclaim_latency_bucket=r2._latency_bucket(reclaim),
        cisd_progress_bucket=r2._bucket(
            cisd_progress,
            (Decimal("0.25"), Decimal("0.50"), Decimal("0.75")),
        ),
        protected_risk_range_bucket=r2._bucket(
            protected_ratio,
            (Decimal("0.25"), Decimal("0.50"), Decimal("1.0"), Decimal("2.0")),
        ),
        source_range_state_bucket=r2._bucket(
            range_state,
            (Decimal("0.75"), Decimal("1.0"), Decimal("1.5"), Decimal("2.0")),
        ),
        body_fraction_bucket=r2._bucket(
            body,
            (Decimal("0.25"), Decimal("0.50"), Decimal("0.75")),
        ),
        rejection_wick_bucket=r2._bucket(
            wick,
            (Decimal("0.10"), Decimal("0.25"), Decimal("0.50")),
        ),
        close_location_bucket=r2._bucket(
            close_location,
            (Decimal("0.25"), Decimal("0.50"), Decimal("0.75")),
        ),
        projected_r_bucket=r2._bucket(
            signal.projected_r,
            (Decimal("0.5"), Decimal("1.0"), Decimal("1.5"), Decimal("2.5")),
        ),
        target_distance_range_bucket=r2._bucket(
            target_ratio,
            (Decimal("0.5"), Decimal("1.0"), Decimal("2.0"), Decimal("4.0")),
        ),
    )
    return r3.Setup(context=context, source=c2, cisd_threshold=cisd.threshold)


def _decision_for_setup(
    *,
    setup: r3.Setup,
    evidence: Evidence,
    memory_bundle: tuple[
        tuple[str, ...],
        str,
        dict[tuple[str, str], r32.Profile],
    ],
    current_open: Decimal,
) -> tuple[r37.Decision, tuple[native.NativeTarget, ...], dict[str, str]] | None:
    bars = tuple(
        bar for bar in evidence.bars
        if bar.closed_at <= setup.context.signal.entry_at
    )
    opens = tuple(bar.opened_at for bar in bars)
    h4 = build_h4(bars)
    frames = {"H1": build_h1(bars), "H4": h4, "D1": build_daily(h4)}
    frame_opens = {
        name: tuple(item.opened_at for item in items)
        for name, items in frames.items()
    }
    frame_closes = {
        name: tuple(item.closed_at for item in items)
        for name, items in frames.items()
    }
    swings = {
        name: td._swing_candidates(items, name)
        for name, items in frames.items()
    }
    swing_known = {
        name: {
            side: tuple(item.known_at for item in by_side[side])
            for side in by_side
        }
        for name, by_side in swings.items()
    }
    signal = setup.context.signal
    departure = signal.cisd_at
    departure_anchor = td._departure_anchor(bars, opens, departure)
    if departure_anchor is None:
        return None
    source_row = {
        "liquidity_raid_at": signal.raid_at.isoformat(),
        "opposite_boundary": str(signal.target),
        "source_timeframe": setup.context.timeframe,
        "source_boundary_created_at": signal.c1_opened_at.isoformat(),
    }
    candidates = td._supported_candidates(
        source_row,
        departure=departure,
        anchor=departure_anchor,
        side=signal.side,
        bars=bars,
        bar_opens=opens,
        frames=frames,
        frame_opens=frame_opens,
        swings=swings,
        swing_known=swing_known,
    )
    target_rows: list[dict[str, Any]] = []
    for candidate in candidates:
        touched = td._first_touch(
            bars,
            opens,
            level=candidate.level,
            side=signal.side,
            start=departure,
            end=signal.entry_at,
        )
        target_rows.append(
            {
                "candidate_known_at": candidate.known_at.isoformat(),
                "touch_m5_opened_at": (
                    None if touched is None else touched.opened_at.isoformat()
                ),
                "candidate_price": str(candidate.level),
                "candidate_type": candidate.kind,
                "source_timeframe": candidate.timeframe,
            }
        )
    tick = Decimal(1).scaleb(-evidence.digits)
    ladder = tuple(
        v1._active_ladder(
            target_rows,
            at=signal.entry_at,
            side=signal.side,
            entry=current_open,
            tick=tick,
        )
    )
    if not ladder:
        return None
    regime = v2._regime_context(
        row={
            "strategy_entry_at": signal.entry_at.isoformat(),
            "side": signal.side.value,
        },
        bars=bars,
        opens=opens,
        frames=frames,
        frame_closes=frame_closes,
    )
    fields, route_mode, memory = memory_bundle
    decision = r37._choose(
        setup=setup,
        ladder=ladder,
        regime=regime,
        allowed_families=ALLOWED_FAMILIES,
        fields=fields,
        route_mode=route_mode,
        memory=memory,
    )
    if decision is None:
        return None
    return decision, ladder, regime


def _risk_scale_for(
    *,
    setup: r3.Setup,
    regime: dict[str, str],
    decision: r37.Decision,
    state: R43LiveState,
) -> tuple[Decimal, Decimal, Decimal, Decimal, Decimal]:
    ctx = v1._setup_context(setup)
    features = {
        "protected_risk_range_bucket": str(ctx["protected_risk_range_bucket"]),
        "h1_range_state": str(regime.get("h1_range_state", "na")),
        "close_location_bucket": str(ctx["close_location_bucket"]),
        "classification": decision.classification,
    }
    structural = r37._structural_scale(
        decision.source,
        decision.family,
        features,
        STRUCTURAL_POLICY_RULE,
    )
    side_overlay = (
        SHORT_OVERLAY_SCALE
        if setup.context.signal.side.value == "short"
        else Decimal("1")
    )
    rank_overlay = (
        RANK2_OVERLAY_SCALE
        if decision.target.rank == 2
        else Decimal("1")
    )
    drawdown = r37._risk_scale(state.drawdown_r, DRAWDOWN_GOVERNOR_RULE)
    overlay = min(side_overlay, rank_overlay)
    return structural, side_overlay, rank_overlay, drawdown, structural * overlay * drawdown


def build_live_signal(
    api: Any,
    *,
    now: datetime,
    memory_bundle: tuple[
        tuple[str, ...],
        str,
        dict[tuple[str, str], r32.Profile],
    ],
    state: R43LiveState,
) -> tuple[R43LiveSignal | None, str]:
    anchor = current_anchor(now)
    if anchor is None:
        return None, "not-r43-entry-anchor"
    if state.open_trade is not None:
        return None, "single-position-busy"
    evidence, _latest_open = mt5_evidence(api, now=now)
    current = next(
        (bar for bar in reversed(evidence.bars) if bar.opened_at == anchor),
        None,
    )
    if current is None:
        return None, "current-m5-open-unavailable"
    complete = tuple(bar for bar in evidence.bars if bar.closed_at <= anchor)
    frames: list[tuple[str, tuple[SourceCandle, ...]]] = []
    h4 = build_h4(complete)
    if _h4_open_for(anchor) == anchor:
        frames.append(("H4", h4))
    frames.append(("H1", build_h1(complete)))

    rearm_blocked = False
    for timeframe, candles in frames:
        setup = _live_setup(
            timeframe=timeframe,
            candles=candles,
            anchor=anchor,
            current_open=current.open,
        )
        if setup is None:
            continue
        if not r26._structurally_rearmed(setup, state.trailing_exit_at):
            rearm_blocked = True
            continue
        resolved = _decision_for_setup(
            setup=setup,
            evidence=evidence,
            memory_bundle=memory_bundle,
            current_open=current.open,
        )
        if resolved is None:
            continue
        decision, ladder, regime = resolved
        signal = setup.context.signal
        (
            structural_scale,
            side_overlay_scale,
            rank_overlay_scale,
            drawdown_scale,
            risk_scale,
        ) = _risk_scale_for(
            setup=setup,
            regime=regime,
            decision=decision,
            state=state,
        )
        material = "|".join(
            (
                IDENTITY,
                signal.entry_at.isoformat(),
                timeframe,
                signal.side.value,
                str(current.open),
                str(signal.protected_swing),
                str(decision.target.level),
                str(decision.target.rank),
                decision.target.route,
                decision.source,
                str(decision.family),
                decision.classification,
                decision.posture,
                str(structural_scale),
                str(side_overlay_scale),
                str(rank_overlay_scale),
                str(drawdown_scale),
                str(risk_scale),
                MEMORY_SHA256,
            )
        )
        fingerprint = hashlib.sha256(material.encode("utf-8")).hexdigest()
        if fingerprint in state.closed_signal_fingerprints:
            return None, "signal-already-closed"
        return (
            R43LiveSignal(
                signal_fingerprint=fingerprint,
                entry_at=anchor,
                timeframe=timeframe,
                side=signal.side.value,
                certified_entry=current.open,
                stop_loss=signal.protected_swing,
                take_profit=decision.target.level,
                target_rank=decision.target.rank,
                target_route=decision.target.route,
                decision_source=decision.source,
                family=decision.family,
                classification=decision.classification,
                posture=decision.posture,
                structural_scale=structural_scale,
                side_overlay_scale=side_overlay_scale,
                rank_overlay_scale=rank_overlay_scale,
                drawdown_scale=drawdown_scale,
                risk_scale=risk_scale,
                ladder=tuple(
                    R43Dol(rank=item.rank, level=str(item.level), route=item.route)
                    for item in ladder
                ),
            ),
            "r43-certified-signal",
        )
    if rearm_blocked:
        return None, "structural-rearm-required"
    return None, "no-r43-certified-signal"


def _floor_to_step(value: Decimal, step: Decimal) -> Decimal:
    units = (value / step).to_integral_value(rounding=ROUND_FLOOR)
    return units * step


def build_r43_risk_request(
    *,
    request_id: str,
    signal: R43LiveSignal,
    provider_spec: Mt5SymbolSpecification,
    account_equity: Decimal,
    now: datetime,
) -> tuple[CiboRiskRequest, Decimal]:
    executable = provider_spec.ask if signal.side == "long" else provider_spec.bid
    certified_risk = abs(signal.certified_entry - signal.stop_loss)
    if certified_risk <= 0:
        raise ValueError("R43 certified risk invalid")
    adverse = (
        max(Decimal(0), executable - signal.certified_entry)
        if signal.side == "long"
        else max(Decimal(0), signal.certified_entry - executable)
    )
    if adverse / certified_risk > MAX_SOURCE_ENTRY_DRIFT_R:
        raise ValueError("R43 source-open entry drift exceeds certified stress")
    if signal.side == "long" and not signal.stop_loss < executable < signal.take_profit:
        raise ValueError("R43 live long geometry invalid")
    if signal.side == "short" and not signal.take_profit < executable < signal.stop_loss:
        raise ValueError("R43 live short geometry invalid")
    ticks = abs(executable - signal.stop_loss) / provider_spec.tick_size
    stop_per_lot = (
        ticks * provider_spec.tick_value
        + FOREX_OPEN_COMMISSION_PER_LOT_USD
    ) * BROKER_RISK_BUFFER
    base_risk_usd = account_equity * BASE_RISK_FRACTION
    requested_risk = base_risk_usd * signal.risk_scale
    volume = _floor_to_step(
        requested_risk / stop_per_lot,
        provider_spec.volume_step,
    )
    volume = min(volume, provider_spec.maximum_volume)
    if volume < provider_spec.minimum_volume:
        raise ValueError("R43 risk maps below broker minimum volume")
    request = CiboRiskRequest(
        request_id=request_id,
        trader_id=TraderLineage.R43_GBPUSD,
        signal_fingerprint=signal.signal_fingerprint,
        qore_symbol=SYMBOL,
        provider_symbol=provider_spec.provider_symbol,
        side=signal.side,
        entry_type="market",
        intended_entry=executable,
        stop_loss=signal.stop_loss,
        take_profit=signal.take_profit,
        requested_volume=volume,
        volume_step=provider_spec.volume_step,
        minimum_volume=provider_spec.minimum_volume,
        stop_loss_per_volume=stop_per_lot,
        margin_per_volume=provider_spec.margin_per_volume,
        requested_at=now,
        expires_at=now + timedelta(seconds=30),
    )
    return request, base_risk_usd


def _side(text: str) -> Side:
    return Side.LONG if text == "long" else Side.SHORT


def certified_stop_for_open_trade(
    opened: R43OpenTrade,
    evidence: Evidence,
    *,
    now: datetime,
) -> Decimal:
    """Replay only causal stop-management state up to now.

    The returned stop is the stop that the certified lifecycle permits at the
    current M5 boundary.  It never widens the previous stop.
    """
    entry_at = datetime.fromisoformat(opened.entry_at)
    if entry_at.tzinfo is None or entry_at.utcoffset() is None:
        raise ValueError("R43 open entry timestamp must be aware")
    side = _side(opened.side)
    entry = Decimal(opened.entry_price)
    initial_stop = Decimal(opened.initial_stop)
    current_stop = initial_stop
    target = Decimal(opened.take_profit)
    ladder = opened.ladder
    path = [
        bar
        for bar in evidence.bars
        if entry_at <= bar.opened_at < entry_at + timedelta(hours=24)
        and bar.closed_at <= now
    ]
    pending: Decimal | None = None
    observed: list[Bar] = []
    conquered: set[int] = set()
    for bar in path:
        if pending is not None and native._improves_stop(
            side=side,
            previous=current_stop,
            candidate=pending,
            target=target,
        ):
            current_stop = pending
        pending = None

        if side is Side.LONG:
            if bar.open <= current_stop or bar.low <= current_stop:
                raise RuntimeError("R43 broker position survived certified stop")
            if bar.open >= target or bar.high >= target:
                raise RuntimeError("R43 broker position survived certified target")
        else:
            if bar.open >= current_stop or bar.high >= current_stop:
                raise RuntimeError("R43 broker position survived certified stop")
            if bar.open <= target or bar.low <= target:
                raise RuntimeError("R43 broker position survived certified target")

        observed.append(bar)
        if opened.posture != native.POSTURE_STATIC and opened.target_rank > 1:
            for earlier in ladder:
                if earlier.rank >= opened.target_rank or earlier.rank in conquered:
                    continue
                level = Decimal(earlier.level)
                if native._target_touch(side, level, bar):
                    conquered.add(earlier.rank)
                    if native._improves_stop(
                        side=side,
                        previous=current_stop,
                        candidate=level,
                        target=target,
                    ):
                        pending = (
                            level
                            if pending is None
                            else native._better_stop(side, pending, level)
                        )

        if opened.posture == native.POSTURE_PROTECT:
            swing = native._swing_candidate(
                side=side,
                bars=observed,
                entry=entry,
                target=target,
            )
            if (
                swing is not None
                and native._improves_stop(
                    side=side,
                    previous=current_stop,
                    candidate=swing,
                    target=target,
                )
            ):
                pending = (
                    swing
                    if pending is None
                    else native._better_stop(side, pending, swing)
                )

    if (
        pending is not None
        and native._improves_stop(
            side=side,
            previous=current_stop,
            candidate=pending,
            target=target,
        )
    ):
        current_stop = pending
    return current_stop


def manage_open_position(
    api: Any,
    *,
    now: datetime,
    store: R43LiveStateStore,
) -> tuple[R43LiveState, str]:
    state = store.reconcile(api, now=now)
    opened = state.open_trade
    if opened is None:
        return state, "no-open-r43-position"
    magic = _magic(opened.client_order_id)
    positions = [
        item
        for item in (api.positions_get() or ())
        if int(item.magic) == magic
    ]
    if len(positions) != 1:
        if not positions:
            return state, "r43-position-awaiting-reconcile"
        raise RuntimeError("R43 magic resolved to multiple positions")
    position = positions[0]
    entry_at = datetime.fromisoformat(opened.entry_at)
    if now >= entry_at + timedelta(hours=24):
        return state, "r43-24h-exit-due"
    evidence, _ = mt5_evidence(api, now=now)
    expected = certified_stop_for_open_trade(opened, evidence, now=now)
    broker_stop = Decimal(str(position.sl))
    stored_stop = Decimal(opened.current_stop)
    target = Decimal(opened.take_profit)
    side = _side(opened.side)
    if broker_stop <= 0:
        raise RuntimeError("R43 broker position has no stop")
    tick_size = Decimal(str(api.symbol_info(SYMBOL).trade_tick_size))
    if abs(broker_stop - stored_stop) > tick_size:
        raise RuntimeError("R43 broker stop/state drift")
    if not native._improves_stop(
        side=side,
        previous=broker_stop,
        candidate=expected,
        target=target,
    ):
        return state, "r43-stop-unchanged"
    request = {
        "action": api.TRADE_ACTION_SLTP,
        "symbol": SYMBOL,
        "position": int(position.ticket),
        "sl": float(expected),
        "tp": float(target),
        "magic": int(position.magic),
        "comment": f"qore-r43-trail-{int(position.ticket)}"[:29],
    }
    checked = api.order_check(request)
    if checked is None or int(checked.retcode) != 0:
        raise RuntimeError("R43 certified stop modification order_check rejected")
    result = api.order_send(request)
    if result is None or int(result.retcode) not in {
        int(api.TRADE_RETCODE_DONE),
        int(api.TRADE_RETCODE_PLACED),
    }:
        raise RuntimeError("R43 certified stop modification rejected")
    state = store.update_stop(expected)
    return state, f"r43-stop-advanced:{expected}"
