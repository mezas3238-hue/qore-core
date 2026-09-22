"""Live MT5 adapter for certified TURTLE_SOUP_GBPJPY_R38.

This adapter preserves the exact GBPJPY candidate certified by R39:
- R35_RANGE_DIRECTION_MINIMAL_ROBUST hierarchy;
- CONFIDENCE_100_050_010 base risk policy;
- R38 GBPJPY-specific pre-entry structural-fragility overlay;
- exact C2 / causal CISD / Protected Swing;
- NEXT_SOURCE_OPEN entry and real active CIBO DOL;
- STATIC / PROTECT lifecycle with DOL lock and causal M5 swing trail;
- structural rearm, single-position busy and 24H maximum lifecycle.

The immutable live memory is derived only from the official GBPJPY R27
Cognitive V2 observations used by the certified research lineage. Broker
granularity and entry drift are fail-closed; certified risk is never rounded
upward to reach a broker minimum lot.
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
from typing import Any

from qore.infrastructure.account_wide_risk import CiboRiskRequest, TraderLineage
from qore.infrastructure.fundednext_live_guard import FOREX_OPEN_COMMISSION_PER_LOT_USD
from qore.infrastructure.fundednext_mt5 import Mt5SymbolSpecification
from qore.infrastructure.fundednext_mt5_clock import (
    NEW_YORK_TZ,
    normalise_fundednext_server_epoch,
)
from qore.infrastructure.m5_boundary_cache import M5BoundaryCache, M5BoundarySnapshot
from qore.infrastructure.trader_execution_profile import M5_PROFILE
from qore.infrastructure.trader_lab import cibo_gbpjpy_native_market_decision_memory_v2 as native
from qore.infrastructure.trader_lab import cibo_market_atlas_target_destination_v2 as td
from qore.infrastructure.trader_lab import turtle_soup_gbpjpy_r1 as r1
from qore.infrastructure.trader_lab import turtle_soup_gbpjpy_r2_cibo_full as r2
from qore.infrastructure.trader_lab import turtle_soup_gbpjpy_r3_cibo_journey as r3
from qore.infrastructure.trader_lab import turtle_soup_gbpjpy_r26_specialist_memory_brain as r26
from qore.infrastructure.trader_lab import turtle_soup_gbpjpy_r34_coarse_causal_memory as r34
from qore.infrastructure.trader_lab import turtle_soup_gbpjpy_r35_confidence_tier_ensemble as r35
from qore.infrastructure.trader_lab import (
    turtle_soup_gbpjpy_r38_5y_structural_fragility_correction as r38,
)
from qore.infrastructure.trader_lab import turtle_soup_gbpjpy_specialist_cognitive_memory_v2 as v2
from qore.infrastructure.trader_lab import turtle_soup_gbpjpy_specialist_memory_v1 as v1
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

IDENTITY = "TURTLE_SOUP_GBPJPY_R38"
CERTIFICATION_IDENTITY = "TURTLE_SOUP_GBPJPY_R39_FINAL_CERTIFICATION_SUITE_V1"
CERTIFICATION_RUN_ID = 35374273254
CERTIFICATION_ARTIFACT_ID = 10559463231
CERTIFICATION_ARTIFACT_DIGEST = (
    "sha256:ff388da8e29866bca831a75b3edcc4f30c5ba3b1f6229c88f85896f86bfcc12e"
)
CERTIFICATION_REPORT_SHA256 = "a51cd25520fbd9d182315e56a36cf5c6301560499ea94bf48f04a3c40168a364"
CERTIFICATION_MANIFEST_SHA256 = "a6ac26d0af0be2613eff172a96421dc6ffc4e8516af2a4978bfcca5e2afce6a0"
R38_SOURCE_RUN_ID = 35373705221
R38_SOURCE_ARTIFACT_ID = 10559845896
R38_SOURCE_ARTIFACT_DIGEST = (
    "sha256:862bd7951806e17d62dddafb800ac18f19a600b5b9dfcb7b16bc79703ca1fd1f"
)
R38_SOURCE_REPORT_SHA256 = "9e0d30d4ba6553439ec675077e05c1579a65b6c32476ac0b616427f0663c802c"
R38_SOURCE_TRADES_SHA256 = "0021b69adf8862178915b68c5208bc9b409b533c8a123e35642443bbad257e8c"

SYMBOL = "GBPJPY"
SELECTED_ENSEMBLE = "R35_RANGE_DIRECTION_MINIMAL_ROBUST"
SELECTED_POLICY = "CONFIDENCE_100_050_010"
LAYERS = r35.ENSEMBLES[SELECTED_ENSEMBLE]
RISK_POLICY = r35.RISK_POLICIES[SELECTED_POLICY]
MEMORY_IDENTITY = "TURTLE_SOUP_GBPJPY_R38_LIVE_MEMORY_V1"
MEMORY_SHA256 = "16a369e8457394642642ca2c7331e32b05644a5656d339cbba06db089f44211f"
MEMORY_SOURCE_RUN_ID = 35349300927
MEMORY_SOURCE_ARTIFACT_ID = 10549575964
MEMORY_SOURCE_ARTIFACT_DIGEST = (
    "sha256:9e9b57f3a108d4f26b3e0b3600705859dc2491dd735972d563f7a350fe0798d2"
)
MEMORY_SOURCE_OBSERVATIONS_SHA256 = (
    "6b3c7ecf75616ba6d428d23286ec2d9c525aca50ee090c687b9c91e9b2b63066"
)
MEMORY_PROFILE_COUNTS = {
    "R34_RANGE_ROUTE_TYPES": 911,
    "R34_DIRECTION_REGIME_ROUTE_TYPES": 3694,
    "R34_MINIMAL_ROUTE_TYPES": 315,
}
BASE_RISK_FRACTION = Decimal("0.002")
MAX_SOURCE_ENTRY_DRIFT_R = Decimal("0.10")
BROKER_RISK_BUFFER = Decimal("1.02")
ANCHOR_GRACE = M5_PROFILE.decision_deadline
HISTORY_M5_BARS = 15_000
_STATE_SCHEMA = "qore.turtle_soup_gbpjpy.r38.live_state.v1"
_STRATEGY_TZ = NEW_YORK_TZ


@dataclass(frozen=True, slots=True)
class R38GbpJpyDol:
    rank: int
    level: str
    route: str


@dataclass(frozen=True, slots=True)
class R38GbpJpyLiveSignal:
    signal_fingerprint: str
    entry_at: datetime
    timeframe: str
    side: str
    certified_entry: Decimal
    stop_loss: Decimal
    take_profit: Decimal
    target_rank: int
    target_route: str
    source_scheme: str
    authority_tier: str
    classification: str
    posture: str
    base_risk_scale: Decimal
    fragility_flags: tuple[str, ...]
    structural_overlay_scale: Decimal
    risk_scale: Decimal
    ladder: tuple[R38GbpJpyDol, ...]

    def __post_init__(self) -> None:
        if len(self.signal_fingerprint) != 64:
            raise ValueError("GBPJPY R38 signal fingerprint must be SHA-256")
        if self.timeframe not in {"H1", "H4"}:
            raise ValueError("GBPJPY R38 timeframe must be H1/H4")
        if self.side not in {"long", "short"}:
            raise ValueError("GBPJPY R38 side must be long/short")
        if self.posture not in native.POSTURES:
            raise ValueError("GBPJPY R38 posture drift")
        if self.source_scheme not in MEMORY_PROFILE_COUNTS:
            raise ValueError("GBPJPY R38 source-scheme drift")
        if self.authority_tier not in {"CORE", "EXPANSION"}:
            raise ValueError("GBPJPY R38 authority-tier drift")
        if self.base_risk_scale not in {
            Decimal("1"),
            Decimal("0.50"),
            Decimal("0.10"),
        }:
            raise ValueError("GBPJPY R38 base risk scale drift")
        if self.structural_overlay_scale not in set(r38.FRAGILITY_POLICY):
            raise ValueError("GBPJPY R38 fragility overlay drift")
        if self.risk_scale != self.base_risk_scale * self.structural_overlay_scale:
            raise ValueError("GBPJPY R38 final risk arithmetic drift")
        if not Decimal("0") < self.risk_scale <= Decimal("1"):
            raise ValueError("GBPJPY R38 risk scale drift")


@dataclass(frozen=True, slots=True)
class R38GbpJpyOpenTrade:
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
    ladder: tuple[R38GbpJpyDol, ...]
    base_risk_usd: str
    risk_scale: str


@dataclass(frozen=True, slots=True)
class R38GbpJpyLiveState:
    open_trade: R38GbpJpyOpenTrade | None = None
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
            raise ValueError("GBPJPY R38 trailing-exit timestamp must be timezone-aware")
        return value

    @property
    def drawdown_r(self) -> Decimal:
        equity = Decimal(self.strategy_equity_r)
        peak = Decimal(self.strategy_peak_r)
        if peak < equity:
            raise ValueError("GBPJPY R38 strategy peak cannot be below equity")
        return peak - equity


class R38GbpJpyLiveStateStore:
    def __init__(self, path: Path) -> None:
        self._path = path

    def load(self) -> R38GbpJpyLiveState:
        if not self._path.exists():
            return R38GbpJpyLiveState()
        raw = json.loads(self._path.read_text(encoding="utf-8"))
        if raw.get("schema") != _STATE_SCHEMA:
            raise ValueError("GBPJPY R38 live-state schema mismatch")
        open_raw = raw.get("open_trade")
        open_trade: R38GbpJpyOpenTrade | None = None
        if open_raw is not None:
            open_copy = dict(open_raw)
            ladder = tuple(R38GbpJpyDol(**item) for item in open_copy.pop("ladder"))
            open_trade = R38GbpJpyOpenTrade(**open_copy, ladder=ladder)
        return R38GbpJpyLiveState(
            open_trade=open_trade,
            closed_signal_fingerprints=tuple(raw.get("closed_signal_fingerprints", ())),
            last_trailing_exit_at=raw.get("last_trailing_exit_at"),
            strategy_equity_r=str(raw.get("strategy_equity_r", "0")),
            strategy_peak_r=str(raw.get("strategy_peak_r", "0")),
        )

    def store(self, state: R38GbpJpyLiveState) -> None:
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
        signal: R38GbpJpyLiveSignal,
        base_risk_usd: Decimal,
    ) -> R38GbpJpyLiveState:
        state = self.load()
        if state.open_trade is not None:
            raise ValueError("GBPJPY R38 single-position-busy")
        opened = R38GbpJpyOpenTrade(
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
        next_state = R38GbpJpyLiveState(
            open_trade=opened,
            closed_signal_fingerprints=state.closed_signal_fingerprints,
            last_trailing_exit_at=state.last_trailing_exit_at,
            strategy_equity_r=state.strategy_equity_r,
            strategy_peak_r=state.strategy_peak_r,
        )
        self.store(next_state)
        return next_state

    def update_stop(self, new_stop: Decimal) -> R38GbpJpyLiveState:
        state = self.load()
        opened = state.open_trade
        if opened is None:
            raise ValueError("GBPJPY R38 cannot update stop without open trade")
        updated = R38GbpJpyOpenTrade(
            **{
                **asdict(opened),
                "ladder": opened.ladder,
                "current_stop": str(new_stop),
            }
        )
        next_state = R38GbpJpyLiveState(
            open_trade=updated,
            closed_signal_fingerprints=state.closed_signal_fingerprints,
            last_trailing_exit_at=state.last_trailing_exit_at,
            strategy_equity_r=state.strategy_equity_r,
            strategy_peak_r=state.strategy_peak_r,
        )
        self.store(next_state)
        return next_state

    def reconcile(self, api: Any, *, now: datetime) -> R38GbpJpyLiveState:
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
            if int(getattr(item, "entry", -1)) == int(getattr(api, "DEAL_ENTRY_OUT", -2))
        ]
        if not exits:
            return state
        last = max(exits, key=lambda item: int(getattr(item, "time", 0)))
        closed_at = normalise_fundednext_server_epoch(int(last.time))
        trailing_exit = state.last_trailing_exit_at
        moved = Decimal(opened.current_stop) != Decimal(opened.initial_stop)
        if moved and int(getattr(last, "reason", -1)) == int(getattr(api, "DEAL_REASON_SL", -2)):
            trailing_exit = closed_at.isoformat()

        realized_usd = sum(
            (
                Decimal(str(getattr(item, "profit", 0)))
                + Decimal(str(getattr(item, "commission", 0)))
                + Decimal(str(getattr(item, "swap", 0)))
                + Decimal(str(getattr(item, "fee", 0)))
                for item in matching
            ),
            Decimal(0),
        )
        base_risk = Decimal(opened.base_risk_usd)
        if base_risk <= 0:
            raise ValueError("GBPJPY R38 base risk must be positive")
        realized_r = realized_usd / base_risk
        equity = Decimal(state.strategy_equity_r) + realized_r
        peak = max(Decimal(state.strategy_peak_r), equity)

        closed = tuple((*state.closed_signal_fingerprints, opened.signal_fingerprint))[-256:]
        next_state = R38GbpJpyLiveState(
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
    """Return the current GBPJPY R38 H1 anchor on the New York strategy clock."""
    local = now.astimezone(_STRATEGY_TZ)
    anchor_local = local.replace(minute=0, second=0, microsecond=0)
    if local < anchor_local or local - anchor_local > ANCHOR_GRACE:
        return None
    return anchor_local.astimezone(UTC)


def mt5_evidence(api: Any, *, now: datetime) -> tuple[Evidence, Decimal]:
    rows = api.copy_rates_from_pos(SYMBOL, api.TIMEFRAME_M5, 0, HISTORY_M5_BARS)
    if rows is None or len(rows) < 2_000:
        raise RuntimeError("GBPJPY R38 M5 history unavailable")
    info = api.symbol_info(SYMBOL)
    if info is None:
        raise RuntimeError("GBPJPY R38 GBPJPY symbol info unavailable")
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
            raise RuntimeError("GBPJPY R38 contradictory MT5 M5 bar")
        retained[opened] = bar
    bars = tuple(retained[key] for key in sorted(retained))
    latest = bars[-1].opened_at
    if abs((now.astimezone(UTC) - latest).total_seconds()) > 600:
        raise RuntimeError("GBPJPY R38 MT5 clock normalization stale")
    return (
        Evidence(symbol=SYMBOL, digits=int(info.digits), bars=bars),
        Decimal(str(rows[-1]["open"])),
    )


def load_memory(
    path: Path,
) -> dict[
    str,
    tuple[
        tuple[str, ...],
        str,
        dict[tuple[str, str], r34.Profile],
        dict[str, Any],
    ],
]:
    raw = path.read_bytes()
    canonical = raw
    while b"\r\n" in canonical:
        canonical = canonical.replace(b"\r\n", b"\n")
    canonical = canonical.replace(b"\r", b"\n")
    if hashlib.sha256(canonical).hexdigest() != MEMORY_SHA256:
        raise ValueError("GBPJPY R38 live memory hash drift")
    payload = json.loads(canonical)
    if not isinstance(payload, dict) or payload.get("identity") != MEMORY_IDENTITY:
        raise ValueError("GBPJPY R38 live memory identity drift")
    source = payload.get("source")
    if not isinstance(source, dict):
        raise ValueError("GBPJPY R38 live memory source missing")
    expected_source = {
        "run_id": MEMORY_SOURCE_RUN_ID,
        "artifact_id": MEMORY_SOURCE_ARTIFACT_ID,
        "artifact_digest": MEMORY_SOURCE_ARTIFACT_DIGEST,
        "observations_sha256": MEMORY_SOURCE_OBSERVATIONS_SHA256,
    }
    for source_key, value in expected_source.items():
        if source.get(source_key) != value:
            raise ValueError(f"GBPJPY R38 live memory source {source_key} drift")
    if payload.get("selected_ensemble") != SELECTED_ENSEMBLE:
        raise ValueError("GBPJPY R38 ensemble drift")
    if payload.get("selected_policy") != SELECTED_POLICY:
        raise ValueError("GBPJPY R38 risk-policy drift")

    layer_rows = payload.get("layers")
    expected_layers = [
        {
            "scheme": scheme,
            "allowed_validation_classes": list(classes),
        }
        for scheme, classes in LAYERS
    ]
    if layer_rows != expected_layers:
        raise ValueError("GBPJPY R38 live memory layer-order drift")

    scheme_rows = payload.get("schemes")
    if not isinstance(scheme_rows, dict) or set(scheme_rows) != set(MEMORY_PROFILE_COUNTS):
        raise ValueError("GBPJPY R38 live memory scheme-set drift")

    memories: dict[
        str,
        tuple[
            tuple[str, ...],
            str,
            dict[tuple[str, str], r34.Profile],
            dict[str, Any],
        ],
    ] = {}
    for scheme, expected_count in MEMORY_PROFILE_COUNTS.items():
        body = scheme_rows.get(scheme)
        if not isinstance(body, dict):
            raise ValueError(f"GBPJPY R38 live memory {scheme} missing")
        expected_fields, expected_route_mode = r34.SCHEMES[scheme]
        fields = tuple(str(item) for item in body.get("fields", ()))
        if fields != expected_fields:
            raise ValueError(f"GBPJPY R38 {scheme} fields drift")
        route_mode = str(body.get("route_mode"))
        if route_mode != expected_route_mode:
            raise ValueError(f"GBPJPY R38 {scheme} route-mode drift")
        rows = body.get("profiles")
        if not isinstance(rows, list) or len(rows) != expected_count:
            raise ValueError(f"GBPJPY R38 {scheme} profile-count drift")
        memory: dict[tuple[str, str], r34.Profile] = {}
        for row in rows:
            if not isinstance(row, dict):
                raise ValueError(f"GBPJPY R38 {scheme} profile type drift")
            profile_key = (
                str(row["signature"]),
                str(row["target_family"]),
            )
            if profile_key in memory:
                raise ValueError(f"GBPJPY R38 {scheme} duplicate profile")
            memory[profile_key] = r34.Profile(
                observations=int(row["observations"]),
                distinct_quarters=int(row["distinct_quarters"]),
                reach_rate=Decimal(str(row["reach_rate"])),
                posture=str(row["posture"]),
                classification=str(row["classification"]),
                validated=bool(row["validated"]),
            )
        summary = body.get("summary")
        if not isinstance(summary, dict):
            raise ValueError(f"GBPJPY R38 {scheme} summary missing")
        memories[scheme] = (fields, route_mode, memory, summary)
    return memories


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
        fvg_before_entry=("yes" if r2._fvg_before_entry(c2.m5, raid_at, anchor, side) else "no"),
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
    memory_bundle: dict[
        str,
        tuple[
            tuple[str, ...],
            str,
            dict[tuple[str, str], r34.Profile],
            dict[str, Any],
        ],
    ],
    current_open: Decimal,
    prepared_snapshot: M5BoundarySnapshot | None = None,
) -> tuple[r35.Decision, tuple[native.NativeTarget, ...], dict[str, str]] | None:
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
                "touch_m5_opened_at": (None if touched is None else touched.opened_at.isoformat()),
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
    decision = r35._choose(
        setup=setup,
        ladder=ladder,
        regime=regime,
        layers=LAYERS,
        memories=memory_bundle,
    )
    if decision is None:
        return None
    return decision, ladder, regime


def _risk_scale_for(
    *,
    setup: r3.Setup,
    regime: dict[str, str],
    decision: r35.Decision,
) -> tuple[Decimal, tuple[str, ...], Decimal, Decimal]:
    base = r35._risk_scale(decision, SELECTED_POLICY)
    row: dict[str, Any] = {
        "authority_tier": decision.authority_tier,
        "target_route": decision.target.route,
        "setup_context": v1._setup_context(setup),
        "regime": regime,
    }
    flags = r38._fragility_flags(row)
    overlay = r38._overlay_scale(len(flags))
    final = base * overlay
    if final <= 0:
        raise ValueError("GBPJPY R38 risk overlay must remain non-zero")
    return base, flags, overlay, final


def build_live_signal(
    api: Any,
    *,
    now: datetime,
    memory_bundle: dict[
        str,
        tuple[
            tuple[str, ...],
            str,
            dict[tuple[str, str], r34.Profile],
            dict[str, Any],
        ],
    ],
    state: R38GbpJpyLiveState,
    boundary_snapshot: M5BoundarySnapshot | None = None,
) -> tuple[R38GbpJpyLiveSignal | None, str]:
    anchor = current_anchor(now)
    if anchor is None:
        return None, "not-gbpjpy-r38-entry-anchor"
    if state.open_trade is not None:
        return None, "single-position-busy"
    if boundary_snapshot is None:
        evidence, _latest_open = mt5_evidence(api, now=now)
    else:
        if boundary_snapshot.symbol != SYMBOL or boundary_snapshot.anchor != anchor:
            raise ValueError("GBPJPY R38 boundary snapshot drift")
        if boundary_snapshot.observed_at > anchor + M5_PROFILE.order_send_deadline:
            raise TimeoutError("GBPJPY R38 hard 2s SLA expired before signal build")
        evidence = boundary_snapshot.evidence
    current = next(
        (bar for bar in reversed(evidence.bars) if bar.opened_at == anchor),
        None,
    )
    if current is None:
        raise RuntimeError("GBPJPY R38 current M5 boundary not yet available")
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
            prepared_snapshot=boundary_snapshot,
        )
        if resolved is None:
            continue
        decision, ladder, regime = resolved
        signal = setup.context.signal
        base_scale, fragility_flags, overlay, risk_scale = _risk_scale_for(
            setup=setup,
            regime=regime,
            decision=decision,
        )
        material = "|".join(
            (
                IDENTITY,
                CERTIFICATION_ARTIFACT_DIGEST,
                R38_SOURCE_ARTIFACT_DIGEST,
                signal.entry_at.isoformat(),
                timeframe,
                signal.side.value,
                str(current.open),
                str(signal.protected_swing),
                str(decision.target.level),
                str(decision.target.rank),
                decision.target.route,
                decision.source_scheme,
                decision.authority_tier,
                decision.classification,
                decision.posture,
                str(base_scale),
                ",".join(fragility_flags),
                str(overlay),
                str(risk_scale),
                MEMORY_SHA256,
            )
        )
        fingerprint = hashlib.sha256(material.encode("utf-8")).hexdigest()
        if fingerprint in state.closed_signal_fingerprints:
            return None, "signal-already-closed"
        return (
            R38GbpJpyLiveSignal(
                signal_fingerprint=fingerprint,
                entry_at=anchor,
                timeframe=timeframe,
                side=signal.side.value,
                certified_entry=current.open,
                stop_loss=signal.protected_swing,
                take_profit=decision.target.level,
                target_rank=decision.target.rank,
                target_route=decision.target.route,
                source_scheme=decision.source_scheme,
                authority_tier=decision.authority_tier,
                classification=decision.classification,
                posture=decision.posture,
                base_risk_scale=base_scale,
                fragility_flags=fragility_flags,
                structural_overlay_scale=overlay,
                risk_scale=risk_scale,
                ladder=tuple(
                    R38GbpJpyDol(
                        rank=item.rank,
                        level=str(item.level),
                        route=item.route,
                    )
                    for item in ladder
                ),
            ),
            "gbpjpy-r38-certified-signal",
        )
    if rearm_blocked:
        return None, "structural-rearm-required"
    return None, "no-gbpjpy-r38-certified-signal"


def _floor_to_step(value: Decimal, step: Decimal) -> Decimal:
    units = (value / step).to_integral_value(rounding=ROUND_FLOOR)
    return units * step


def build_r38_gbpjpy_risk_request(
    *,
    request_id: str,
    signal: R38GbpJpyLiveSignal,
    provider_spec: Mt5SymbolSpecification,
    account_equity: Decimal,
    now: datetime,
) -> tuple[CiboRiskRequest, Decimal]:
    for name, value in (
        ("volume_min", provider_spec.minimum_volume),
        ("volume_step", provider_spec.volume_step),
        ("volume_max", provider_spec.maximum_volume),
        ("tick_size", provider_spec.tick_size),
        ("tick_value", provider_spec.tick_value),
        ("contract_size", provider_spec.contract_size),
        ("point", provider_spec.point),
    ):
        if value <= 0:
            raise ValueError(f"GBPJPY R38 broker {name} invalid")
    if provider_spec.maximum_volume < provider_spec.minimum_volume:
        raise ValueError("GBPJPY R38 broker volume range invalid")
    if provider_spec.spread_points < 0:
        raise ValueError("GBPJPY R38 broker spread invalid")
    if provider_spec.minimum_stop_distance_points < 0:
        raise ValueError("GBPJPY R38 broker stops level invalid")
    if not provider_spec.trade_enabled or not provider_spec.session_open:
        raise ValueError("GBPJPY R38 broker trading unavailable")

    executable = provider_spec.ask if signal.side == "long" else provider_spec.bid
    certified_risk = abs(signal.certified_entry - signal.stop_loss)
    if certified_risk <= 0:
        raise ValueError("GBPJPY R38 certified risk invalid")
    adverse = (
        max(Decimal(0), executable - signal.certified_entry)
        if signal.side == "long"
        else max(Decimal(0), signal.certified_entry - executable)
    )
    if adverse / certified_risk > MAX_SOURCE_ENTRY_DRIFT_R:
        raise ValueError("GBPJPY R38 source-open entry drift exceeds certified stress")

    if signal.side == "long" and not signal.stop_loss < executable < signal.take_profit:
        raise ValueError("GBPJPY R38 live long geometry invalid")
    if signal.side == "short" and not signal.take_profit < executable < signal.stop_loss:
        raise ValueError("GBPJPY R38 live short geometry invalid")

    stop_points = abs(executable - signal.stop_loss) / provider_spec.point
    target_points = abs(signal.take_profit - executable) / provider_spec.point
    if stop_points < provider_spec.minimum_stop_distance_points:
        raise ValueError("GBPJPY R38 stop is inside broker stops level")
    if target_points < provider_spec.minimum_stop_distance_points:
        raise ValueError("GBPJPY R38 target is inside broker stops level")

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
        raise ValueError("GBPJPY R38 risk maps below broker minimum volume")
    request = CiboRiskRequest(
        request_id=request_id,
        trader_id=TraderLineage.R38_GBPJPY,
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
    opened: R38GbpJpyOpenTrade,
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
        raise ValueError("GBPJPY R38 open entry timestamp must be aware")
    side = _side(opened.side)
    entry = Decimal(opened.entry_price)
    initial_stop = Decimal(opened.initial_stop)
    current_stop = initial_stop
    target = Decimal(opened.take_profit)
    ladder = opened.ladder
    path = [
        bar
        for bar in evidence.bars
        if entry_at <= bar.opened_at < entry_at + timedelta(hours=24) and bar.closed_at <= now
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
                raise RuntimeError("GBPJPY R38 broker position survived certified stop")
            if bar.open >= target or bar.high >= target:
                raise RuntimeError("GBPJPY R38 broker position survived certified target")
        else:
            if bar.open >= current_stop or bar.high >= current_stop:
                raise RuntimeError("GBPJPY R38 broker position survived certified stop")
            if bar.open <= target or bar.low <= target:
                raise RuntimeError("GBPJPY R38 broker position survived certified target")

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
                            level if pending is None else native._better_stop(side, pending, level)
                        )

        if opened.posture == native.POSTURE_PROTECT:
            swing = native._swing_candidate(
                side=side,
                bars=observed,
                entry=entry,
                target=target,
            )
            if swing is not None and native._improves_stop(
                side=side,
                previous=current_stop,
                candidate=swing,
                target=target,
            ):
                pending = swing if pending is None else native._better_stop(side, pending, swing)

    if pending is not None and native._improves_stop(
        side=side,
        previous=current_stop,
        candidate=pending,
        target=target,
    ):
        current_stop = pending
    return current_stop


def manage_open_position(
    api: Any,
    *,
    now: datetime,
    store: R38GbpJpyLiveStateStore,
    mutations_enabled: bool = True,
    cache: M5BoundaryCache | None = None,
) -> tuple[R38GbpJpyLiveState, str]:
    state = store.reconcile(api, now=now)
    opened = state.open_trade
    if opened is None:
        return state, "no-open-gbpjpy-r38-position"
    magic = _magic(opened.client_order_id)
    positions = [item for item in (api.positions_get() or ()) if int(item.magic) == magic]
    if len(positions) != 1:
        if not positions:
            return state, "gbpjpy-r38-position-awaiting-reconcile"
        raise RuntimeError("GBPJPY R38 magic resolved to multiple positions")
    position = positions[0]
    entry_at = datetime.fromisoformat(opened.entry_at)
    if now >= entry_at + timedelta(hours=24):
        return state, "gbpjpy-r38-24h-exit-due"
    evidence = cache.evidence() if cache is not None else mt5_evidence(api, now=now)[0]
    expected = certified_stop_for_open_trade(opened, evidence, now=now)
    broker_stop = Decimal(str(position.sl))
    stored_stop = Decimal(opened.current_stop)
    target = Decimal(opened.take_profit)
    side = _side(opened.side)
    if broker_stop <= 0:
        raise RuntimeError("GBPJPY R38 broker position has no stop")
    tick_size = Decimal(str(api.symbol_info(SYMBOL).trade_tick_size))
    if abs(broker_stop - stored_stop) > tick_size:
        raise RuntimeError("GBPJPY R38 broker stop/state drift")
    if not native._improves_stop(
        side=side,
        previous=broker_stop,
        candidate=expected,
        target=target,
    ):
        return state, "gbpjpy-r38-stop-unchanged"
    request = {
        "action": api.TRADE_ACTION_SLTP,
        "symbol": SYMBOL,
        "position": int(position.ticket),
        "sl": float(expected),
        "tp": float(target),
        "magic": int(position.magic),
        "comment": f"qore-gbpjpy-r38-trail-{int(position.ticket)}"[:29],
    }
    checked = api.order_check(request)
    if checked is None or int(checked.retcode) != 0:
        raise RuntimeError("GBPJPY R38 certified stop modification order_check rejected")
    if not mutations_enabled:
        return state, f"gbpjpy-r38-shadow-stop-check-pass:{expected}"
    result = api.order_send(request)
    if result is None or int(result.retcode) not in {
        int(api.TRADE_RETCODE_DONE),
        int(api.TRADE_RETCODE_PLACED),
    }:
        raise RuntimeError("GBPJPY R38 certified stop modification rejected")
    state = store.update_stop(expected)
    return state, f"gbpjpy-r38-stop-advanced:{expected}"
