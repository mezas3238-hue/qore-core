"""Live MT5 adapter for the frozen TURTLE_SOUP_XAUUSD_R34 contract.

The methodology is not reimplemented here: this adapter reuses the exact R34
research primitives, Cognitive V3, R30 nearest-DOL resolver and R33 five-family
expansion.  MT5 supplies M5 market evidence and broker execution only.
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
from zoneinfo import ZoneInfo

from qore.infrastructure.account_wide_risk import CiboRiskRequest, TraderLineage
from qore.infrastructure.fundednext_live_guard import FOREX_OPEN_COMMISSION_PER_LOT_USD
from qore.infrastructure.fundednext_mt5 import Mt5SymbolSpecification
from qore.infrastructure.m5_boundary_cache import M5BoundarySnapshot
from qore.infrastructure.trader_execution_profile import M5_PROFILE
from qore.infrastructure.trader_lab import cibo_market_atlas_target_destination_v2 as td
from qore.infrastructure.trader_lab import turtle_soup_xauusd_r1 as r1
from qore.infrastructure.trader_lab import turtle_soup_xauusd_r2_cibo_full as r2
from qore.infrastructure.trader_lab import turtle_soup_xauusd_r3_cibo_journey as r3
from qore.infrastructure.trader_lab import turtle_soup_xauusd_r33_subfamily_risk_governor as r33
from qore.infrastructure.trader_lab import turtle_soup_xauusd_specialist_cognitive_memory_v2 as v2
from qore.infrastructure.trader_lab import turtle_soup_xauusd_specialist_memory_v1 as v1
from qore.infrastructure.trader_lab.cibo_xauusd_native_market_decision_memory_v2 import (
    POSTURE_STATIC,
)
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

IDENTITY = "TURTLE_SOUP_XAUUSD_R34"
SYMBOL = "XAUUSD"
FAMILY_SET = "R33_FIVE_FAMILY"
GOVERNOR = "DD_2_4_SCALE_075_025"
ALLOWED_FAMILIES = r33.FAMILY_SETS[FAMILY_SET]
GOVERNOR_RULE = r33.GOVERNORS[GOVERNOR]
COGNITIVE_SHA256 = "95653ca2156b9d3efb1004cc1dd81f5968d37c7d2161b91eab3adc76af3d34fb"
BASE_RISK_FRACTION = Decimal("0.002")
MAX_SOURCE_ENTRY_DRIFT_R = Decimal("0.10")
BROKER_RISK_BUFFER = Decimal("1.02")
ANCHOR_GRACE = M5_PROFILE.decision_deadline
HISTORY_M5_BARS = 15_000
_BROKER_SERVER_TZ = ZoneInfo("Europe/Helsinki")
_STRATEGY_TZ = ZoneInfo("America/New_York")
_STATE_SCHEMA = "qore.turtle_soup_xauusd.r34.live_state.v1"


@dataclass(frozen=True, slots=True)
class R34LiveSignal:
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
    risk_scale: Decimal

    def __post_init__(self) -> None:
        if len(self.signal_fingerprint) != 64:
            raise ValueError("R34 signal fingerprint must be SHA-256")
        if self.timeframe not in {"H1", "H4"}:
            raise ValueError("R34 timeframe must be H1/H4")
        if self.side not in {"long", "short"}:
            raise ValueError("R34 side must be long/short")
        if self.risk_scale not in {Decimal("1"), Decimal("0.75"), Decimal("0.25")}:
            raise ValueError("R34 risk scale drift")


@dataclass(frozen=True, slots=True)
class R34OpenTrade:
    client_order_id: str
    signal_fingerprint: str
    entry_at: str
    base_risk_usd: str
    risk_scale: str


@dataclass(frozen=True, slots=True)
class R34LiveState:
    equity_r: str = "0"
    peak_r: str = "0"
    open_trade: R34OpenTrade | None = None
    closed_signal_fingerprints: tuple[str, ...] = ()

    @property
    def drawdown_r(self) -> Decimal:
        return Decimal(self.peak_r) - Decimal(self.equity_r)

    @property
    def risk_scale(self) -> Decimal:
        return r33._risk_scale(self.drawdown_r, GOVERNOR_RULE)


class R34LiveStateStore:
    def __init__(self, path: Path) -> None:
        self._path = path

    def load(self) -> R34LiveState:
        if not self._path.exists():
            return R34LiveState()
        raw = json.loads(self._path.read_text(encoding="utf-8"))
        if raw.get("schema") != _STATE_SCHEMA:
            raise ValueError("R34 live-state schema mismatch")
        open_raw = raw.get("open_trade")
        open_trade = None if open_raw is None else R34OpenTrade(**open_raw)
        return R34LiveState(
            equity_r=str(raw["equity_r"]),
            peak_r=str(raw["peak_r"]),
            open_trade=open_trade,
            closed_signal_fingerprints=tuple(raw.get("closed_signal_fingerprints", ())),
        )

    def store(self, state: R34LiveState) -> None:
        payload = {
            "schema": _STATE_SCHEMA,
            "identity": IDENTITY,
            "equity_r": state.equity_r,
            "peak_r": state.peak_r,
            "open_trade": None if state.open_trade is None else asdict(state.open_trade),
            "closed_signal_fingerprints": list(state.closed_signal_fingerprints[-256:]),
        }
        self._path.parent.mkdir(parents=True, exist_ok=True)
        fd, name = tempfile.mkstemp(
            prefix=f".{self._path.name}.", suffix=".tmp", dir=self._path.parent
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
        signal: R34LiveSignal,
        base_risk_usd: Decimal,
    ) -> R34LiveState:
        state = self.load()
        if state.open_trade is not None:
            raise ValueError("R34 single-position-busy")
        opened = R34OpenTrade(
            client_order_id=client_order_id,
            signal_fingerprint=signal.signal_fingerprint,
            entry_at=signal.entry_at.isoformat(),
            base_risk_usd=str(base_risk_usd),
            risk_scale=str(signal.risk_scale),
        )
        state = R34LiveState(
            equity_r=state.equity_r,
            peak_r=state.peak_r,
            open_trade=opened,
            closed_signal_fingerprints=state.closed_signal_fingerprints,
        )
        self.store(state)
        return state

    def reconcile(self, api: Any, *, now: datetime) -> R34LiveState:
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
        pnl = sum(
            (
                Decimal(str(getattr(item, "profit", 0)))
                + Decimal(str(getattr(item, "commission", 0)))
                + Decimal(str(getattr(item, "swap", 0)))
            )
            for item in matching
        )
        base_risk = Decimal(opened.base_risk_usd)
        if base_risk <= 0:
            raise ValueError("R34 base risk ledger invalid")
        contribution = pnl / base_risk
        equity = Decimal(state.equity_r) + contribution
        peak = max(Decimal(state.peak_r), equity)
        closed = tuple((*state.closed_signal_fingerprints, opened.signal_fingerprint))[-256:]
        state = R34LiveState(
            equity_r=str(equity),
            peak_r=str(peak),
            open_trade=None,
            closed_signal_fingerprints=closed,
        )
        self.store(state)
        return state


def _magic(client_order_id: str) -> int:
    digest = hashlib.sha256(client_order_id.encode("utf-8")).digest()
    return int.from_bytes(digest[:4], "big") & 0x7FFFFFFF


def current_anchor(now: datetime) -> datetime | None:
    """Return the current R34 H1 anchor on the New York strategy clock."""
    local = now.astimezone(_STRATEGY_TZ)
    anchor_local = local.replace(minute=0, second=0, microsecond=0)
    if local < anchor_local or local - anchor_local > ANCHOR_GRACE:
        return None
    return anchor_local.astimezone(UTC)


def _normalise_server_epoch(value: int) -> datetime:
    pseudo = datetime.fromtimestamp(value, tz=UTC).replace(tzinfo=None)
    return pseudo.replace(tzinfo=_BROKER_SERVER_TZ).astimezone(UTC)


def mt5_evidence(api: Any, *, now: datetime) -> tuple[Evidence, Decimal]:
    rows = api.copy_rates_from_pos(SYMBOL, api.TIMEFRAME_M5, 0, HISTORY_M5_BARS)
    if rows is None or len(rows) < 2_000:
        raise RuntimeError("R34 M5 history unavailable")
    info = api.symbol_info(SYMBOL)
    if info is None:
        raise RuntimeError("R34 XAUUSD symbol info unavailable")
    retained: dict[datetime, Bar] = {}
    for row in rows:
        opened = _normalise_server_epoch(int(row["time"]))
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
            raise RuntimeError("R34 contradictory MT5 M5 bar")
        retained[opened] = bar
    bars = tuple(retained[key] for key in sorted(retained))
    latest = bars[-1].opened_at
    if abs((now.astimezone(UTC) - latest).total_seconds()) > 600:
        raise RuntimeError("R34 MT5 clock normalization stale")
    return Evidence(symbol=SYMBOL, digits=int(info.digits), bars=bars), Decimal(
        str(rows[-1]["open"])
    )


def load_cognitive(path: Path) -> dict[str, Any]:
    raw = path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != COGNITIVE_SHA256:
        raise ValueError("R34 Cognitive V3 hash drift")
    payload = json.loads(raw)
    required = {
        "exact_regime",
        "causal_core_regime",
        "anatomy_regime",
        "regime_journey",
    }
    if not isinstance(payload, dict) or set(payload) != required:
        raise ValueError("R34 Cognitive V3 hierarchy drift")
    return cast(dict[str, Any], payload)


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
    previous = candles[max(0, pos - 20) : pos]
    mean_range = sum((item.high - item.low for item in previous), Decimal(0)) / Decimal(
        len(previous)
    )
    source_range = c2.high - c2.low
    raid_level = c1.low if side is Side.LONG else c1.high
    raid_extreme = c2.low if side is Side.LONG else c2.high
    raid_units = None if mean_range <= 0 else abs(raid_extreme - raid_level) / mean_range
    reclaim = r2._first_reclaim_latency(c2, c1, side, raid_at)
    duration = Decimal(60 if timeframe == "H1" else 240)
    cisd_progress = Decimal(str((cisd.confirmed_at - c2.opened_at).total_seconds() / 60)) / duration
    protected_ratio = None if source_range <= 0 else risk / source_range
    range_state = None if mean_range <= 0 else source_range / mean_range
    body, wick, close_location = r2._geometry(c2, side)
    target_ratio = None if source_range <= 0 else reward / source_range
    peers = [r2._same_boundary(item, side) for item in candles[max(0, pos - 21) : pos - 1]]
    equal = any(level == r2._same_boundary(c1, side) for level in peers)
    local = raid_at.astimezone(r2.NY)
    context = r2.ContextSignal(
        signal=signal,
        timeframe=timeframe,
        side=side.value,
        session=signal.session_bucket,
        weekday=local.strftime("%A"),
        prior_body_alignment=signal.prior_body_alignment,
        fvg_before_entry="yes" if r2._fvg_before_entry(c2.m5, raid_at, anchor, side) else "no",
        exact_equal_liquidity="yes" if equal else "no",
        raid_depth_range_bucket=r2._bucket(
            raid_units, (Decimal("0.05"), Decimal("0.10"), Decimal("0.25"), Decimal("0.50"))
        ),
        reclaim_latency_bucket=r2._latency_bucket(reclaim),
        cisd_progress_bucket=r2._bucket(
            cisd_progress, (Decimal("0.25"), Decimal("0.50"), Decimal("0.75"))
        ),
        protected_risk_range_bucket=r2._bucket(
            protected_ratio, (Decimal("0.25"), Decimal("0.50"), Decimal("1.0"), Decimal("2.0"))
        ),
        source_range_state_bucket=r2._bucket(
            range_state, (Decimal("0.75"), Decimal("1.0"), Decimal("1.5"), Decimal("2.0"))
        ),
        body_fraction_bucket=r2._bucket(body, (Decimal("0.25"), Decimal("0.50"), Decimal("0.75"))),
        rejection_wick_bucket=r2._bucket(wick, (Decimal("0.10"), Decimal("0.25"), Decimal("0.50"))),
        close_location_bucket=r2._bucket(
            close_location, (Decimal("0.25"), Decimal("0.50"), Decimal("0.75"))
        ),
        projected_r_bucket=r2._bucket(
            signal.projected_r, (Decimal("0.5"), Decimal("1.0"), Decimal("1.5"), Decimal("2.5"))
        ),
        target_distance_range_bucket=r2._bucket(
            target_ratio, (Decimal("0.5"), Decimal("1.0"), Decimal("2.0"), Decimal("4.0"))
        ),
    )
    return r3.Setup(context=context, source=c2, cisd_threshold=cisd.threshold)


def _decision_for_setup(
    *,
    setup: r3.Setup,
    evidence: Evidence,
    cognitive: dict[str, Any],
    current_open: Decimal,
    prepared_snapshot: M5BoundarySnapshot | None = None,
) -> tuple[Any, Any] | None:
    bars = (
        prepared_snapshot.complete_bars
        if prepared_snapshot is not None
        else tuple(bar for bar in evidence.bars if bar.closed_at <= setup.context.signal.entry_at)
    )
    opens = tuple(bar.opened_at for bar in bars)
    if prepared_snapshot is None:
        h4 = build_h4(bars)
        frames = {"H1": build_h1(bars), "H4": h4, "D1": build_daily(h4)}
    else:
        frames = {
            "H1": prepared_snapshot.h1,
            "H4": prepared_snapshot.h4,
            "D1": prepared_snapshot.d1,
        }
    frame_opens = {name: tuple(item.opened_at for item in items) for name, items in frames.items()}
    frame_closes = {name: tuple(item.closed_at for item in items) for name, items in frames.items()}
    swings = {name: td._swing_candidates(items, name) for name, items in frames.items()}
    swing_known = {
        name: {side: tuple(item.known_at for item in by_side[side]) for side in by_side}
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
                "touch_m5_opened_at": None if touched is None else touched.opened_at.isoformat(),
                "candidate_price": str(candidate.level),
                "candidate_type": candidate.kind,
                "source_timeframe": candidate.timeframe,
            }
        )
    tick = Decimal(1).scaleb(-evidence.digits)
    ladder = v1._active_ladder(
        target_rows,
        at=signal.entry_at,
        side=signal.side,
        entry=current_open,
        tick=tick,
    )
    if not ladder:
        return None
    regime = v2._regime_context(
        row={"strategy_entry_at": signal.entry_at.isoformat(), "side": signal.side.value},
        bars=bars,
        opens=opens,
        frames=frames,
        frame_closes=frame_closes,
    )
    decision = r33._choose(
        cognitive=cognitive,
        setup=setup,
        ladder=ladder,
        regime=regime,
        allowed_families=ALLOWED_FAMILIES,
    )
    if decision is None:
        return None
    if decision.posture != POSTURE_STATIC:
        raise RuntimeError("R34 live decision posture drift")
    return decision, ladder


def build_live_signal(
    api: Any,
    *,
    now: datetime,
    cognitive: dict[str, Any],
    state: R34LiveState,
    boundary_snapshot: M5BoundarySnapshot | None = None,
) -> tuple[R34LiveSignal | None, str]:
    anchor = current_anchor(now)
    if anchor is None:
        return None, "not-r34-entry-anchor"
    if state.open_trade is not None:
        return None, "single-position-busy"
    if boundary_snapshot is None:
        evidence, _latest_open = mt5_evidence(api, now=now)
    else:
        if boundary_snapshot.symbol != SYMBOL or boundary_snapshot.anchor != anchor:
            raise ValueError("R34 boundary snapshot drift")
        if boundary_snapshot.observed_at > anchor + M5_PROFILE.order_send_deadline:
            raise TimeoutError("R34 hard 2s SLA expired before signal build")
        evidence = boundary_snapshot.evidence
    current = next((bar for bar in reversed(evidence.bars) if bar.opened_at == anchor), None)
    if current is None:
        raise RuntimeError("R34 current M5 boundary not yet available")
    frames: list[tuple[str, tuple[SourceCandle, ...]]] = []
    if boundary_snapshot is None:
        complete = tuple(bar for bar in evidence.bars if bar.closed_at <= anchor)
        h4 = build_h4(complete)
        h1 = build_h1(complete)
    else:
        h4 = boundary_snapshot.h4
        h1 = boundary_snapshot.h1
    if _h4_open_for(anchor) == anchor:
        frames.append(("H4", h4))
    frames.append(("H1", h1))
    for timeframe, candles in frames:
        setup = _live_setup(
            timeframe=timeframe,
            candles=candles,
            anchor=anchor,
            current_open=current.open,
        )
        if setup is None:
            continue
        resolved = _decision_for_setup(
            setup=setup,
            evidence=evidence,
            cognitive=cognitive,
            current_open=current.open,
            prepared_snapshot=boundary_snapshot,
        )
        if resolved is None:
            continue
        decision, _ladder = resolved
        signal = setup.context.signal
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
            )
        )
        fingerprint = hashlib.sha256(material.encode("utf-8")).hexdigest()
        if fingerprint in state.closed_signal_fingerprints:
            return None, "signal-already-closed"
        return (
            R34LiveSignal(
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
                risk_scale=state.risk_scale,
            ),
            "r34-certified-signal",
        )
    return None, "no-r34-certified-signal"


def _floor_to_step(value: Decimal, step: Decimal) -> Decimal:
    units = (value / step).to_integral_value(rounding=ROUND_FLOOR)
    return units * step


def build_r34_risk_request(
    *,
    request_id: str,
    signal: R34LiveSignal,
    provider_spec: Mt5SymbolSpecification,
    account_equity: Decimal,
    now: datetime,
) -> tuple[CiboRiskRequest, Decimal]:
    executable = provider_spec.ask if signal.side == "long" else provider_spec.bid
    certified_risk = abs(signal.certified_entry - signal.stop_loss)
    if certified_risk <= 0:
        raise ValueError("R34 certified risk invalid")
    adverse = (
        max(Decimal(0), executable - signal.certified_entry)
        if signal.side == "long"
        else max(Decimal(0), signal.certified_entry - executable)
    )
    if adverse / certified_risk > MAX_SOURCE_ENTRY_DRIFT_R:
        raise ValueError("R34 source-open entry drift exceeds certified stress")
    if signal.side == "long" and not signal.stop_loss < executable < signal.take_profit:
        raise ValueError("R34 live long geometry invalid")
    if signal.side == "short" and not signal.take_profit < executable < signal.stop_loss:
        raise ValueError("R34 live short geometry invalid")
    ticks = abs(executable - signal.stop_loss) / provider_spec.tick_size
    stop_per_lot = (
        ticks * provider_spec.tick_value + FOREX_OPEN_COMMISSION_PER_LOT_USD
    ) * BROKER_RISK_BUFFER
    base_risk_usd = account_equity * BASE_RISK_FRACTION
    requested_risk = base_risk_usd * signal.risk_scale
    volume = _floor_to_step(
        requested_risk / stop_per_lot,
        provider_spec.volume_step,
    )
    volume = min(volume, provider_spec.maximum_volume)
    if volume < provider_spec.minimum_volume:
        raise ValueError("R34 risk maps below broker minimum volume")
    request = CiboRiskRequest(
        request_id=request_id,
        trader_id=TraderLineage.R34_XAUUSD,
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
