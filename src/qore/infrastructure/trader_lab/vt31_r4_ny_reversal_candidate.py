"""Frozen VT-31 R4 New York reversal candidate.

The candidate is a deterministic, pre-entry implementation of the TTrades
New York reversal profile. NAS100 is the source market. SP500 and US30 use
the identical Human Owner-authorized transfer configuration.
"""

from __future__ import annotations

import json
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from hashlib import sha256
from pathlib import Path
from typing import cast
from zoneinfo import ZoneInfo

CANDIDATE_ID = "VT31_R4_TTRADES_NY_REVERSAL_001"
SCHEMA = "qore.trader_lab.vt31_r4_candidate.v1"
EVIDENCE_SCHEMA = "qore.ctrader_demo.vt31_silver_bullet_v2_m1_evidence.v1"
MARKETS = ("NAS100", "SP500", "US30")
NY = ZoneInfo("America/New_York")


class Vt31R4CandidateError(ValueError):
    """Raised when evidence or candidate invariants fail."""


@dataclass(frozen=True, slots=True)
class Bar:
    opened_at: datetime
    closed_at: datetime
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal

    def __post_init__(self) -> None:
        if self.opened_at.tzinfo is None or self.closed_at.tzinfo is None:
            raise Vt31R4CandidateError("bar timestamps must be timezone-aware")
        if self.closed_at <= self.opened_at:
            raise Vt31R4CandidateError("bar chronology is invalid")
        if self.low > min(self.open, self.close) or self.high < max(
            self.open, self.close
        ):
            raise Vt31R4CandidateError("bar OHLC is invalid")


@dataclass(frozen=True, slots=True)
class Setup:
    market: str
    local_date: date
    side: str
    signal_at: datetime
    entry: Decimal
    initial_stop: Decimal
    target: Decimal
    directional_body_fraction: Decimal

    @property
    def risk(self) -> Decimal:
        return abs(self.entry - self.initial_stop)


@dataclass(frozen=True, slots=True)
class LoadedEvidence:
    market: str
    provider_symbol: str
    account_fingerprint: str
    software_sha: str
    checked_at: datetime
    bars: tuple[Bar, ...]


def _ts(value: object, field: str) -> datetime:
    if not isinstance(value, str):
        raise Vt31R4CandidateError(f"{field} must be a timestamp")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as error:
        raise Vt31R4CandidateError(f"{field} is invalid") from error
    if parsed.tzinfo is None:
        raise Vt31R4CandidateError(f"{field} must be timezone-aware")
    return parsed.astimezone(UTC)


def _decimal(value: object, field: str) -> Decimal:
    if isinstance(value, bool) or not isinstance(value, (int, float, str)):
        raise Vt31R4CandidateError(f"{field} must be numeric")
    try:
        return Decimal(str(value))
    except Exception as error:
        raise Vt31R4CandidateError(f"{field} must be numeric") from error


def contract_payload() -> dict[str, object]:
    """Return the immutable pre-fresh candidate contract."""
    return {
        "candidate_id": CANDIDATE_ID,
        "source_market": "NAS100",
        "owner_authorized_transfer_markets": ["SP500", "US30"],
        "identical_configuration_across_markets": True,
        "methodology_sources": [
            "https://ttrades.com/understanding-the-new-york-reversal-in-daily-profiles/",
            "https://ttrades.com/how-to-use-smt-divergence-ttrades-fractal-model/",
            "https://ttrades.com/relative-strength-weakness-smt-divergence-full-guide/",
            "https://ttrades.com/stop-loss-mastery-using-protected-swings-for-precise-invalidations/",
            "https://ttrades.com/protected-swings-and-cisd-how-to-trail-your-stop-loss/",
        ],
        "source_day": "18:00-to-17:00-America/New_York",
        "poi": "previous-complete-source-day-extreme",
        "london_failure": "02:00-to-05:00-does-not-reach-selected-POI",
        "ny_sweep_window": "08:30-to-10:30-America/New_York",
        "sweep": "first-eligible-previous-source-day-extreme",
        "both_extremes": "abstain",
        "confirmation": "M5-opposing-series-CISD",
        "confirmation_quality": (
            "direction-aligned-body-at-least-opposing-wick"
        ),
        "simultaneous_cross_index_selection": (
            "maximum-directional-body-fraction;exact-ties-abstain"
        ),
        "entry": "M5-CISD-confirmation-close",
        "initial_stop": "M5-protected-opposing-series-extreme",
        "management": (
            "trail-only-after-new-M1-protected-swing-confirmed-by-"
            "sweep-and-close-through-opposing-series"
        ),
        "initial_risk_denominator": "frozen-at-entry",
        "target": "opposite-London-session-extreme",
        "lifecycle": "16:00-America/New_York",
        "daily_selection": "first-eligible-event-per-market",
        "gap_policy": "censor-trade",
        "same_bar_policy": "censor-unknown-path",
        "friction_gate_r_per_trade": "0.05",
        "stress_research_r_per_trade": ["0.025", "0.05", "0.075", "0.10"],
        "minimum_aggregate_sample": 150,
        "minimum_sample_each_market": 30,
        "profit_factor_gate": ">=1.10",
        "max_drawdown_gate_r": "<=20",
        "quartile_gate": ">=3-of-4-positive",
        "market_gate": "every-market-stressed-mean-positive",
        "side_gate": "long-and-short-stressed-mean-positive",
        "temporal_gate": ">=2-of-3-eligible-blocks-positive",
        "monte_carlo": {
            "algorithm": "sha256-domain-separated-moving-block-bootstrap-v1",
            "paths": 10000,
            "block_length": 5,
            "positive_terminal_probability": ">=0.70",
            "p95_max_drawdown_r": "<=20",
        },
        "fresh_partition": (
            "earliest-unobserved-contiguous-cTrader-DEMO-history-strictly-"
            "before-2024-08-15;target-at-least-730-days;otherwise-forward-DEMO"
        ),
        "fresh_acquisition": "one-shot-after-freeze",
        "causal_equivalence_required": True,
        "retuning_after_fresh": False,
        "demo_only": True,
        "live_authorized": False,
        "real_capital_authorized": False,
        "production_authorized": False,
    }


def contract_fingerprint() -> str:
    encoded = json.dumps(
        contract_payload(), sort_keys=True, separators=(",", ":")
    ).encode()
    return sha256(encoded).hexdigest()


def load_evidence(path: Path, expected_market: str) -> LoadedEvidence:
    """Load and strictly validate one immutable cTrader DEMO M1 file."""
    try:
        decoded = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise Vt31R4CandidateError("cannot read evidence") from error
    if not isinstance(decoded, dict):
        raise Vt31R4CandidateError("evidence root must be an object")
    payload = cast(dict[str, object], decoded)
    if payload.get("schema") != EVIDENCE_SCHEMA:
        raise Vt31R4CandidateError("unexpected evidence schema")
    if payload.get("environment") != "demo" or payload.get("read_only") is not True:
        raise Vt31R4CandidateError("evidence must be read-only DEMO")
    if payload.get("account_is_live") is not False:
        raise Vt31R4CandidateError("LIVE evidence is prohibited")
    if payload.get("trading_permission_verified") is not True:
        raise Vt31R4CandidateError("DEMO permission must be verified")
    symbol = payload.get("symbol")
    if not isinstance(symbol, dict) or symbol.get("symbol_name") != expected_market:
        raise Vt31R4CandidateError("market identity mismatch")
    provider = payload.get("provider_symbol_name")
    account = payload.get("account_fingerprint")
    software_sha = payload.get("software_sha")
    if not isinstance(provider, str) or not provider:
        raise Vt31R4CandidateError("provider symbol is missing")
    if not isinstance(account, str) or len(account) != 64:
        raise Vt31R4CandidateError("account fingerprint is invalid")
    if not isinstance(software_sha, str) or len(software_sha) != 40:
        raise Vt31R4CandidateError("software SHA is invalid")
    checked_at = _ts(payload.get("checked_at"), "checked_at")
    periods = payload.get("periods")
    if not isinstance(periods, dict) or set(periods) != {"M1"}:
        raise Vt31R4CandidateError("evidence must contain only M1")
    raw_bars = periods["M1"]
    if not isinstance(raw_bars, list) or not raw_bars:
        raise Vt31R4CandidateError("M1 evidence is empty")
    bars: list[Bar] = []
    for raw in raw_bars:
        if not isinstance(raw, dict):
            raise Vt31R4CandidateError("M1 bar must be an object")
        bars.append(
            Bar(
                opened_at=_ts(raw.get("opened_at"), "opened_at"),
                closed_at=_ts(raw.get("closed_at"), "closed_at"),
                open=_decimal(raw.get("open"), "open"),
                high=_decimal(raw.get("high"), "high"),
                low=_decimal(raw.get("low"), "low"),
                close=_decimal(raw.get("close"), "close"),
            )
        )
    ordered = tuple(sorted(bars, key=lambda item: item.opened_at))
    if tuple(bars) != ordered:
        raise Vt31R4CandidateError("M1 evidence is not chronological")
    identities = {(bar.opened_at, bar.closed_at) for bar in bars}
    if len(identities) != len(bars):
        raise Vt31R4CandidateError("M1 evidence contains duplicates")
    if any(bar.closed_at > checked_at for bar in bars):
        raise Vt31R4CandidateError("future evidence is prohibited")
    return LoadedEvidence(
        expected_market, provider, account, software_sha, checked_at, tuple(bars)
    )


def _source_label(local: datetime) -> date:
    return local.date() + timedelta(days=1) if local.hour >= 18 else local.date()


def _aggregate_m5(bars: tuple[Bar, ...]) -> tuple[Bar, ...]:
    groups: dict[datetime, list[Bar]] = defaultdict(list)
    for bar in bars:
        local = bar.opened_at.astimezone(NY)
        minute = local.hour * 60 + local.minute
        if 510 <= minute < 630:
            key = local.replace(
                minute=(local.minute // 5) * 5, second=0, microsecond=0
            )
            groups[key].append(bar)
    result: list[Bar] = []
    for key in sorted(groups):
        group = groups[key]
        if len(group) != 5:
            continue
        result.append(
            Bar(
                group[0].opened_at,
                group[-1].closed_at,
                group[0].open,
                max(item.high for item in group),
                min(item.low for item in group),
                group[-1].close,
            )
        )
    return tuple(result)


def _opposing(bar: Bar, side: str) -> bool:
    return bar.close < bar.open if side == "long" else bar.close > bar.open


def _detect_setup(
    market: str,
    local_day: date,
    day_bars: tuple[Bar, ...],
    prior_bars: tuple[Bar, ...],
) -> Setup | None:
    pd_high = max(item.high for item in prior_bars)
    pd_low = min(item.low for item in prior_bars)
    london = tuple(
        item
        for item in day_bars
        if 120 <= (
            item.opened_at.astimezone(NY).hour * 60
            + item.opened_at.astimezone(NY).minute
        ) < 300
    )
    if len(london) < 150:
        return None
    london_high = max(item.high for item in london)
    london_low = min(item.low for item in london)
    allow_long = london_low > pd_low
    allow_short = london_high < pd_high
    if not allow_long and not allow_short:
        return None
    candles = _aggregate_m5(day_bars)
    side: str | None = None
    for index, candle in enumerate(candles):
        low_hit = allow_long and candle.low < pd_low
        high_hit = allow_short and candle.high > pd_high
        if side is None and low_hit and high_hit:
            return None
        if side is None and (low_hit or high_hit):
            side = "long" if low_hit else "short"
        if side is not None and (
            (side == "long" and candle.high > pd_high)
            or (side == "short" and candle.low < pd_low)
        ):
            return None
        if side is None or index == 0:
            continue
        start = index - 1
        if not _opposing(candles[start], side):
            continue
        while start > 0 and _opposing(candles[start - 1], side):
            start -= 1
        series = candles[start:index]
        level = pd_low if side == "long" else pd_high
        made_extreme = (
            min(item.low for item in series) <= level
            if side == "long"
            else max(item.high for item in series) >= level
        )
        crossed = (
            candle.close > series[0].open
            if side == "long"
            else candle.close < series[0].open
        )
        if not made_extreme or not crossed:
            continue
        body = abs(candle.close - candle.open)
        opposing_wick = (
            min(candle.open, candle.close) - candle.low
            if side == "long"
            else candle.high - max(candle.open, candle.close)
        )
        aligned = candle.close > candle.open if side == "long" else candle.close < candle.open
        if not aligned or body < opposing_wick:
            return None
        span = candle.high - candle.low
        if span <= 0:
            return None
        stop = (
            min(item.low for item in series)
            if side == "long"
            else max(item.high for item in series)
        )
        target = london_high if side == "long" else london_low
        entry = candle.close
        valid = (
            stop < entry < target
            if side == "long"
            else target < entry < stop
        )
        if not valid:
            return None
        return Setup(
            market,
            local_day,
            side,
            candle.closed_at,
            entry,
            stop,
            target,
            body / span,
        )
    return None


def select_simultaneous(setups: tuple[Setup, ...]) -> tuple[Setup, ...]:
    """Select one index per simultaneous event without using outcomes."""
    groups: dict[datetime, list[Setup]] = defaultdict(list)
    for setup in setups:
        groups[setup.signal_at].append(setup)
    selected: list[Setup] = []
    for stamp in sorted(groups):
        group = groups[stamp]
        best = max(item.directional_body_fraction for item in group)
        winners = [
            item for item in group if item.directional_body_fraction == best
        ]
        if len(winners) == 1:
            selected.append(winners[0])
    return tuple(selected)


def _new_protected_stop(
    bars: tuple[Bar, ...],
    index: int,
    side: str,
    current_stop: Decimal,
) -> Decimal:
    if index < 2:
        return current_stop
    start = index - 1
    if not _opposing(bars[start], side):
        return current_stop
    while start > 0 and _opposing(bars[start - 1], side):
        start -= 1
    if start == 0:
        return current_stop
    series = bars[start:index]
    swept = (
        min(item.low for item in series) < bars[start - 1].low
        if side == "long"
        else max(item.high for item in series) > bars[start - 1].high
    )
    crossed = (
        bars[index].close > series[0].open
        if side == "long"
        else bars[index].close < series[0].open
    )
    if not swept or not crossed:
        return current_stop
    proposed = (
        min(item.low for item in series)
        if side == "long"
        else max(item.high for item in series)
    )
    current_close = bars[index].close
    if side == "long" and current_stop < proposed < current_close:
        return proposed
    if side == "short" and current_close < proposed < current_stop:
        return proposed
    return current_stop


def _simulate(setup: Setup, day_bars: tuple[Bar, ...]) -> dict[str, object] | None:
    risk = setup.risk
    if risk <= 0:
        return None
    close_index = {bar.closed_at: index for index, bar in enumerate(day_bars)}
    current_stop = setup.initial_stop
    previous: Bar | None = None
    for bar in day_bars:
        local = bar.opened_at.astimezone(NY)
        if bar.opened_at < setup.signal_at or local.hour * 60 + local.minute >= 960:
            continue
        if previous is not None and bar.opened_at != previous.closed_at:
            return None
        previous = bar
        hit_stop = (
            bar.low <= current_stop
            if setup.side == "long"
            else bar.high >= current_stop
        )
        hit_target = (
            bar.high >= setup.target
            if setup.side == "long"
            else bar.low <= setup.target
        )
        if hit_stop and hit_target:
            return None
        if hit_stop:
            terminal = (
                (current_stop - setup.entry) / risk
                if setup.side == "long"
                else (setup.entry - current_stop) / risk
            )
            return _trade(setup, terminal, "protected-stop", bar.closed_at)
        if hit_target:
            terminal = abs(setup.target - setup.entry) / risk
            return _trade(setup, terminal, "target", bar.closed_at)
        index = close_index[bar.closed_at]
        if bar.closed_at > setup.signal_at:
            current_stop = _new_protected_stop(
                day_bars, index, setup.side, current_stop
            )
    eligible = [
        bar
        for bar in day_bars
        if bar.opened_at.astimezone(NY).hour * 60
        + bar.opened_at.astimezone(NY).minute
        < 960
    ]
    if not eligible:
        return None
    final = eligible[-1]
    terminal = (
        (final.close - setup.entry) / risk
        if setup.side == "long"
        else (setup.entry - final.close) / risk
    )
    return _trade(setup, terminal, "lifecycle", final.closed_at)


def _trade(
    setup: Setup, value: Decimal, reason: str, exit_at: datetime
) -> dict[str, object]:
    return {
        "market": setup.market,
        "local_date": setup.local_date.isoformat(),
        "side": setup.side,
        "signal_at": setup.signal_at.isoformat(),
        "exit_at": exit_at.isoformat(),
        "entry": format(setup.entry, "f"),
        "initial_stop": format(setup.initial_stop, "f"),
        "target": format(setup.target, "f"),
        "exit_reason": reason,
        "r_multiple": format(value, "f"),
    }


def _metrics(
    trades: tuple[dict[str, object], ...], friction: Decimal = Decimal(0)
) -> dict[str, object]:
    values = [
        Decimal(cast(str, item["r_multiple"])) - friction for item in trades
    ]
    gains = sum((value for value in values if value > 0), Decimal(0))
    losses = -sum((value for value in values if value < 0), Decimal(0))
    equity = peak = drawdown = Decimal(0)
    streak = max_streak = 0
    for value in values:
        equity += value
        peak = max(peak, equity)
        drawdown = max(drawdown, peak - equity)
        streak = streak + 1 if value < 0 else 0
        max_streak = max(max_streak, streak)
    total = sum(values, Decimal(0))
    return {
        "sample": len(values),
        "wins": sum(value > 0 for value in values),
        "losses": sum(value < 0 for value in values),
        "flats": sum(value == 0 for value in values),
        "total_r": format(total, "f"),
        "mean_r": format(total / len(values), "f") if values else "0",
        "profit_factor": format(gains / losses, "f") if losses else None,
        "max_drawdown_r": format(drawdown, "f"),
        "max_losing_streak": max_streak,
    }


def _quartiles(
    trades: tuple[dict[str, object], ...], friction: Decimal
) -> tuple[dict[str, object], ...]:
    return tuple(
        _metrics(
            trades[len(trades) * index // 4 : len(trades) * (index + 1) // 4],
            friction,
        )
        for index in range(4)
    )


def replay(evidence_paths: dict[str, Path]) -> dict[str, object]:
    """Replay the frozen candidate over exactly three market evidence files."""
    if set(evidence_paths) != set(MARKETS):
        raise Vt31R4CandidateError("all and only frozen markets are required")
    loaded = {
        market: load_evidence(evidence_paths[market], market)
        for market in MARKETS
    }
    accounts = {item.account_fingerprint for item in loaded.values()}
    if len(accounts) != 1:
        raise Vt31R4CandidateError("account fingerprints differ")
    provisional: list[Setup] = []
    day_maps: dict[str, dict[date, tuple[Bar, ...]]] = {}
    for market, item in loaded.items():
        by_calendar: dict[date, list[Bar]] = defaultdict(list)
        by_source: dict[date, list[Bar]] = defaultdict(list)
        for bar in item.bars:
            local = bar.opened_at.astimezone(NY)
            by_calendar[local.date()].append(bar)
            by_source[_source_label(local)].append(bar)
        complete = sorted(
            key for key, values in by_source.items() if len(values) >= 1000
        )
        previous = {complete[index]: complete[index - 1] for index in range(1, len(complete))}
        days = {key: tuple(values) for key, values in by_calendar.items()}
        day_maps[market] = days
        for local_day in sorted(days):
            prior_day = previous.get(local_day)
            if prior_day is None:
                continue
            setup = _detect_setup(
                market,
                local_day,
                days[local_day],
                tuple(by_source[prior_day]),
            )
            if setup is not None:
                provisional.append(setup)
    selected = select_simultaneous(tuple(provisional))
    trades = tuple(
        trade
        for setup in selected
        if (
            trade := _simulate(
                setup, day_maps[setup.market][setup.local_date]
            )
        )
        is not None
    )
    ordered = tuple(
        sorted(
            trades,
            key=lambda item: (
                cast(str, item["signal_at"]),
                cast(str, item["market"]),
            ),
        )
    )
    friction = Decimal("0.05")
    market_stress = {
        market: _metrics(
            tuple(item for item in ordered if item["market"] == market),
            friction,
        )
        for market in MARKETS
    }
    side_stress = {
        side: _metrics(
            tuple(item for item in ordered if item["side"] == side),
            friction,
        )
        for side in ("long", "short")
    }
    quartiles = _quartiles(ordered, friction)
    aggregate = _metrics(ordered)
    stress = _metrics(ordered, friction)
    temporal: dict[str, dict[str, object]] = {}
    for market in MARKETS:
        own = tuple(item for item in ordered if item["market"] == market)
        for year in sorted({cast(str, item["local_date"])[:4] for item in own}):
            temporal[f"{market}:{year}"] = _metrics(
                tuple(
                    item
                    for item in own
                    if cast(str, item["local_date"]).startswith(year)
                ),
                friction,
            )
    eligible = [value for value in temporal.values() if cast(int, value["sample"]) >= 10]
    gates = {
        "aggregate_sample_at_least_150": cast(int, aggregate["sample"]) >= 150,
        "each_market_sample_at_least_30": all(
            cast(int, value["sample"]) >= 30
            for value in market_stress.values()
        ),
        "aggregate_stressed_mean_positive": Decimal(cast(str, stress["mean_r"])) > 0,
        "aggregate_stressed_pf_at_least_1_10": (
            stress["profit_factor"] is not None
            and Decimal(cast(str, stress["profit_factor"])) >= Decimal("1.10")
        ),
        "aggregate_stressed_dd_at_most_20r": (
            Decimal(cast(str, stress["max_drawdown_r"])) <= Decimal(20)
        ),
        "every_market_stressed_mean_positive": all(
            Decimal(cast(str, value["mean_r"])) > 0
            for value in market_stress.values()
        ),
        "both_sides_stressed_mean_positive": all(
            cast(int, value["sample"]) > 0
            and Decimal(cast(str, value["mean_r"])) > 0
            for value in side_stress.values()
        ),
        "three_of_four_quartiles_positive": sum(
            Decimal(cast(str, value["mean_r"])) > 0 for value in quartiles
        )
        >= 3,
        "two_thirds_eligible_temporal_blocks_positive": bool(eligible)
        and sum(
            Decimal(cast(str, value["mean_r"])) > 0 for value in eligible
        )
        * 3
        >= len(eligible) * 2,
    }
    return {
        "schema": SCHEMA,
        "candidate_id": CANDIDATE_ID,
        "contract": contract_payload(),
        "contract_fingerprint": contract_fingerprint(),
        "aggregate": aggregate,
        "stress_0_05r": stress,
        "market_stress": market_stress,
        "side_stress": side_stress,
        "quartiles": quartiles,
        "temporal_blocks": temporal,
        "gates": gates,
        "passes_economic_gates": all(gates.values()),
        "trades": ordered,
        "environment": "demo",
        "read_only": True,
        "demo_eligible": False,
        "live_authorized": False,
        "real_capital_authorized": False,
        "production_authorized": False,
        "abstention_policy": dict(Counter({"deterministic": 1})),
    }

def causal_equivalence(evidence_paths: dict[str, Path]) -> dict[str, bool]:
    """Compare full replay with decision-time-truncated signal and exit replays."""
    full = replay(evidence_paths)
    loaded = {
        market: load_evidence(evidence_paths[market], market)
        for market in MARKETS
    }
    provisional: list[Setup] = []
    truncated: list[Setup] = []
    day_maps: dict[str, dict[date, tuple[Bar, ...]]] = {}
    for market, item in loaded.items():
        by_calendar: dict[date, list[Bar]] = defaultdict(list)
        by_source: dict[date, list[Bar]] = defaultdict(list)
        for bar in item.bars:
            local = bar.opened_at.astimezone(NY)
            by_calendar[local.date()].append(bar)
            by_source[_source_label(local)].append(bar)
        complete = sorted(
            key for key, values in by_source.items() if len(values) >= 1000
        )
        previous = {
            complete[index]: complete[index - 1]
            for index in range(1, len(complete))
        }
        days = {key: tuple(values) for key, values in by_calendar.items()}
        day_maps[market] = days
        for local_day in sorted(days):
            prior_day = previous.get(local_day)
            if prior_day is None:
                continue
            prior = tuple(by_source[prior_day])
            setup = _detect_setup(market, local_day, days[local_day], prior)
            if setup is None:
                continue
            provisional.append(setup)
            visible = tuple(
                bar
                for bar in days[local_day]
                if bar.closed_at <= setup.signal_at
            )
            decision_setup = _detect_setup(
                market, local_day, visible, prior
            )
            if decision_setup is not None:
                truncated.append(decision_setup)
    selected_full = select_simultaneous(tuple(provisional))
    selected_truncated = select_simultaneous(tuple(truncated))
    adjudication_equal = selected_full == selected_truncated
    setup_by_identity = {
        (setup.market, setup.signal_at.isoformat()): setup
        for setup in selected_full
    }
    trades_equal = True
    for trade in cast(tuple[dict[str, object], ...], full["trades"]):
        identity = (
            cast(str, trade["market"]),
            cast(str, trade["signal_at"]),
        )
        setup = setup_by_identity.get(identity)
        if setup is None:
            trades_equal = False
            break
        exit_at = _ts(trade["exit_at"], "exit_at")
        visible = tuple(
            bar
            for bar in day_maps[setup.market][setup.local_date]
            if bar.closed_at <= exit_at
        )
        if _simulate(setup, visible) != trade:
            trades_equal = False
            break
    gap_exit_semantics_equal = True
    for setup in selected_full:
        day_bars = day_maps[setup.market][setup.local_date]
        if _simulate(setup, day_bars) is not None:
            continue
        active = tuple(
            bar
            for bar in day_bars
            if bar.opened_at >= setup.signal_at
            and (
                bar.opened_at.astimezone(NY).hour * 60
                + bar.opened_at.astimezone(NY).minute
            )
            < 960
        )
        if not any(
            current.opened_at != previous.closed_at
            for previous, current in zip(active, active[1:], strict=False)
        ):
            gap_exit_semantics_equal = False
            break
    return {
        "trades_equal": trades_equal,
        "adjudication_equal": adjudication_equal,
        "gap_exit_semantics_equal": gap_exit_semantics_equal,
        "no_future_leakage": trades_equal and adjudication_equal,
    }
