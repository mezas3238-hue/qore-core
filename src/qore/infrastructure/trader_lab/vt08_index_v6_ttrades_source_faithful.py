"""VT-08 Index V6 source-faithful TTrades Fractal Model candidate.

V6 intentionally does not inherit V3 geometry, daily uniqueness, D1 peer-count
admission, positional-only execution, 2.5R, or a one-H4 forced lifecycle.
The contract is frozen in VT08-INDEX-V6-TTRADES-SOURCE-FAITHFUL-FREEZE-001.md.
"""
from __future__ import annotations

import argparse
import json
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, date, datetime
from decimal import Decimal
from enum import StrEnum
from hashlib import sha256
from pathlib import Path
from typing import cast
from zoneinfo import ZoneInfo

from qore.infrastructure.trader_lab.vt08_index_v2_candidate import (
    _gap_exit,
    _in_partition,
    _intrabar_exit,
    _load_candidate_market,
)
from qore.infrastructure.traders.contracts import DemoTradingSetupSide
from qore.infrastructure.traders.vt08_index_c2_positional_r1 import (
    Vt08IndexC2R1Bar,
    _aggregate_contiguous_m15,
    _latest_complete_source_days,
    resolve_daily_bias,
)
from qore.kernel.errors import InfrastructureError

SCHEMA = "qore.trader_lab.vt08_index_v6_ttrades_source_faithful.v1"
CANDIDATE_ID = "VT08_INDEX_V6_TTRADES_SOURCE_FAITHFUL_001"
PRIMARY_SOURCE_SHA256 = (
    "bfe76fa4346ec4d7442886c21834aa26f0d82172bdb55666e8c77226cdf83271"
)
AUTHORIZED_MARKETS = ("NAS100", "SP500", "US30")
H4_ANCHORS_NY = (18, 22, 2, 6, 10, 14)
TARGET_R_MULTIPLE = Decimal("2")
PRIMARY_STRESS_R = Decimal("0.05")
SECONDARY_STRESS_R = Decimal("0.10")
_NY = ZoneInfo("America/New_York")

SOURCE_REFS = (
    "ttrades:h4-power-of-three:2025-09-20",
    "ttrades:only-trading-strategy-2026:2026-01-03",
    "ttrades:best-timeframes-fractal-model:2026-01-31",
    "ttrades:relevant-swings:2026-03-21",
    "ttrades:intracandle-cisd:2026-06-13",
    "ttrades:points-of-interest:2026-07-18",
    "ttrades:positional-entries:2026-08-08",
    "ttrades:internal-external-liquidity:2026-08-22",
    "ttrades:let-wick-form-trade-body:2026-08-29",
)

_RULE_MATERIAL = {
    "candidate_id": CANDIDATE_ID,
    "markets": AUTHORIZED_MARKETS,
    "h4_source_cycle_new_york": H4_ANCHORS_NY,
    "daily_bias": "previous-day-close-continuation-or-sweep-reversal",
    "poi_priority": ("fvg", "relevant-swing", "cisd"),
    "relevant_swing_window_h4": 3,
    "c2": "sweep-prior-extreme-close-back-inside",
    "c3": "body-engulf-without-directional-extreme-sweep-after-c2-failure",
    "wick_confirmation": "m15-cisd-protected-swing-no-numeric-wick-threshold",
    "execution": "first-causal-m15-continuation-closure",
    "entry": "continuation-close",
    "stop": "protected-swing-extreme",
    "target_r": "2",
    "same_bar_ambiguity": "stop-first",
    "forced_h4_lifecycle": False,
    "daily_unique_only": False,
    "v3_geometry": False,
    "d1_peer_count_gate": False,
    "smt_mandatory": False,
    "source_refs": SOURCE_REFS,
}
RULE_FINGERPRINT = sha256(
    json.dumps(
        _RULE_MATERIAL,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("utf-8")
).hexdigest()


class Vt08IndexV6Error(InfrastructureError):
    __slots__ = ()


class PoiKind(StrEnum):
    FVG = "fvg"
    RELEVANT_SWING = "relevant-swing"
    CISD = "cisd"


class H4ModelKind(StrEnum):
    SAME_C2 = "same-c2-intracandle"
    C2_EXPANSION = "c2-closure-next-h4-expansion"
    C3_EXPANSION = "c3-closure-next-h4-expansion"


@dataclass(frozen=True, slots=True)
class SourcePoi:
    kind: PoiKind
    low: Decimal
    high: Decimal
    observed_at: datetime

    def __post_init__(self) -> None:
        if self.low <= 0 or self.high <= 0 or self.low > self.high:
            raise Vt08IndexV6Error("invalid POI geometry")
        if self.observed_at.tzinfo is None or self.observed_at.utcoffset() is None:
            raise Vt08IndexV6Error("POI timestamp must be aware")

    def touched_by(self, bar: Vt08IndexC2R1Bar) -> bool:
        return bar.low <= self.high and bar.high >= self.low

    def payload(self) -> dict[str, str]:
        return {
            "kind": self.kind.value,
            "low": format(self.low, "f"),
            "high": format(self.high, "f"),
            "observed_at": self.observed_at.astimezone(UTC).isoformat(),
        }


@dataclass(frozen=True, slots=True)
class CandidateSignal:
    symbol: str
    side: DemoTradingSetupSide
    model_kind: H4ModelKind
    h4_opened_at: datetime
    signal_at: datetime
    entry: Decimal
    stop: Decimal
    target: Decimal
    poi: SourcePoi
    cisd_level: Decimal
    cisd_confirmed_at: datetime
    protected_swing_extreme: Decimal

    def payload(self) -> dict[str, object]:
        return {
            "symbol": self.symbol,
            "side": self.side.value,
            "model_kind": self.model_kind.value,
            "h4_opened_at": self.h4_opened_at.astimezone(UTC).isoformat(),
            "anchor_hour_new_york": self.h4_opened_at.astimezone(_NY).hour,
            "signal_at": self.signal_at.astimezone(UTC).isoformat(),
            "entry": format(self.entry, "f"),
            "stop": format(self.stop, "f"),
            "target": format(self.target, "f"),
            "poi": self.poi.payload(),
            "cisd_level": format(self.cisd_level, "f"),
            "cisd_confirmed_at": self.cisd_confirmed_at.astimezone(UTC).isoformat(),
            "protected_swing_extreme": format(self.protected_swing_extreme, "f"),
        }


@dataclass(frozen=True, slots=True)
class ModeledV6Trade:
    signal: CandidateSignal
    exited_at: datetime
    exit_price: Decimal
    exit_reason: str
    r_multiple: Decimal

    def payload(self) -> dict[str, object]:
        result = self.signal.payload()
        result.update(
            {
                "exited_at": self.exited_at.astimezone(UTC).isoformat(),
                "exit_price": format(self.exit_price, "f"),
                "exit_reason": self.exit_reason,
                "r_multiple": format(self.r_multiple, "f"),
            }
        )
        return result


def _metrics(
    trades: Sequence[ModeledV6Trade], *, stress: Decimal = Decimal()
) -> dict[str, object]:
    values = tuple(item.r_multiple - stress for item in trades)
    total = sum(values, Decimal())
    gains = sum((value for value in values if value > 0), Decimal())
    losses = -sum((value for value in values if value < 0), Decimal())
    equity = Decimal()
    peak = Decimal()
    drawdown = Decimal()
    losing_streak = 0
    max_losing_streak = 0
    for value in values:
        equity += value
        peak = max(peak, equity)
        drawdown = max(drawdown, peak - equity)
        if value < 0:
            losing_streak += 1
            max_losing_streak = max(max_losing_streak, losing_streak)
        else:
            losing_streak = 0
    return {
        "sample": len(values),
        "wins": sum(value > 0 for value in values),
        "losses": sum(value < 0 for value in values),
        "flats": sum(value == 0 for value in values),
        "total_r": str(total),
        "mean_r": str(total / len(values)) if values else "0",
        "profit_factor": str(gains / losses) if losses else None,
        "max_drawdown_r": str(drawdown),
        "max_losing_streak": max_losing_streak,
        "stress_r_per_trade": str(stress),
    }


def _breakdown(
    trades: Sequence[ModeledV6Trade], *, key: str, stress: Decimal
) -> dict[str, object]:
    def value(item: ModeledV6Trade) -> str:
        if key == "symbol":
            return item.signal.symbol
        if key == "side":
            return item.signal.side.value
        if key == "anchor":
            return str(item.signal.h4_opened_at.astimezone(_NY).hour)
        if key == "model_kind":
            return item.signal.model_kind.value
        raise Vt08IndexV6Error(f"unsupported breakdown key: {key}")

    labels = sorted({value(item) for item in trades})
    return {
        label: _metrics(
            tuple(item for item in trades if value(item) == label),
            stress=stress,
        )
        for label in labels
    }


def _build_h4(
    indexed: dict[datetime, Vt08IndexC2R1Bar],
) -> dict[datetime, Vt08IndexC2R1Bar]:
    result: dict[datetime, Vt08IndexC2R1Bar] = {}
    for opened in sorted(indexed):
        local = opened.astimezone(_NY)
        if local.minute != 0 or local.second != 0 or local.hour not in H4_ANCHORS_NY:
            continue
        aggregate = _aggregate_contiguous_m15(
            indexed,
            opened_at_local=local,
            count=16,
        )
        if aggregate is not None:
            result[opened.astimezone(UTC)] = aggregate
    return result


def _bars_between(
    indexed: dict[datetime, Vt08IndexC2R1Bar], *, start: datetime, end: datetime
) -> tuple[Vt08IndexC2R1Bar, ...]:
    return tuple(
        bar
        for opened, bar in sorted(indexed.items())
        if start.astimezone(UTC) <= opened.astimezone(UTC) < end.astimezone(UTC)
    )


def _daily_bias(
    indexed: dict[datetime, Vt08IndexC2R1Bar], *, before: datetime
) -> DemoTradingSetupSide | None:
    source_days = _latest_complete_source_days(
        indexed,
        before_local=before.astimezone(_NY),
    )
    if source_days is None:
        return None
    return resolve_daily_bias(
        previous_day=source_days[0],
        current_day=source_days[1],
    )


def _c2_side(
    reference: Vt08IndexC2R1Bar, candle2: Vt08IndexC2R1Bar
) -> DemoTradingSetupSide | None:
    bullish = candle2.low < reference.low and reference.low < candle2.close < reference.high
    bearish = candle2.high > reference.high and reference.low < candle2.close < reference.high
    if bullish == bearish:
        return None
    return DemoTradingSetupSide.LONG if bullish else DemoTradingSetupSide.SHORT


def _c3_side(
    candle1: Vt08IndexC2R1Bar,
    candle2: Vt08IndexC2R1Bar,
    candle3: Vt08IndexC2R1Bar,
) -> DemoTradingSetupSide | None:
    body_low = min(candle2.open, candle2.close)
    body_high = max(candle2.open, candle2.close)
    c2_bull = _c2_side(candle1, candle2) is DemoTradingSetupSide.LONG
    c2_bear = _c2_side(candle1, candle2) is DemoTradingSetupSide.SHORT
    bullish = (
        not c2_bull
        and candle3.low >= candle2.low
        and candle3.open <= body_low
        and candle3.close > body_high
    )
    bearish = (
        not c2_bear
        and candle3.high <= candle2.high
        and candle3.open >= body_high
        and candle3.close < body_low
    )
    if bullish == bearish:
        return None
    return DemoTradingSetupSide.LONG if bullish else DemoTradingSetupSide.SHORT


def _first_cisd(
    bars: Sequence[Vt08IndexC2R1Bar],
    *,
    side: DemoTradingSetupSide,
    start_index: int,
) -> tuple[int, Decimal, Decimal] | None:
    sequence_open: Decimal | None = None
    extreme: Decimal | None = None
    in_sequence = False
    for index in range(start_index, len(bars)):
        bar = bars[index]
        opposing = (
            bar.close < bar.open
            if side is DemoTradingSetupSide.LONG
            else bar.close > bar.open
        )
        if opposing:
            if not in_sequence:
                sequence_open = bar.open
                extreme = bar.low if side is DemoTradingSetupSide.LONG else bar.high
            else:
                assert extreme is not None
                extreme = (
                    min(extreme, bar.low)
                    if side is DemoTradingSetupSide.LONG
                    else max(extreme, bar.high)
                )
            in_sequence = True
            continue
        if in_sequence and sequence_open is not None and extreme is not None:
            confirmed = (
                bar.close > sequence_open
                if side is DemoTradingSetupSide.LONG
                else bar.close < sequence_open
            )
            if confirmed:
                return index, sequence_open, extreme
        sequence_open = None
        extreme = None
        in_sequence = False
    return None


def _last_cisd_poi(
    bars: Sequence[Vt08IndexC2R1Bar], *, side: DemoTradingSetupSide
) -> SourcePoi | None:
    found: tuple[int, Decimal, Decimal] | None = None
    cursor = 0
    while cursor < len(bars):
        current = _first_cisd(bars, side=side, start_index=cursor)
        if current is None:
            break
        found = current
        cursor = current[0] + 1
    if found is None:
        return None
    index, level, _ = found
    return SourcePoi(PoiKind.CISD, level, level, bars[index].closed_at)


def _prior_h4_keys(
    h4: dict[datetime, Vt08IndexC2R1Bar], *, before: datetime, count: int
) -> tuple[datetime, ...]:
    keys = tuple(key for key in sorted(h4) if key < before.astimezone(UTC))
    return keys[-count:]


def _source_poi_for_h4(
    indexed: dict[datetime, Vt08IndexC2R1Bar],
    h4: dict[datetime, Vt08IndexC2R1Bar],
    *,
    h4_opened_at: datetime,
    side: DemoTradingSetupSide,
) -> SourcePoi | None:
    prior_keys = _prior_h4_keys(h4, before=h4_opened_at, count=3)
    if len(prior_keys) < 3:
        return None
    a, b, c = (h4[key] for key in prior_keys)

    if side is DemoTradingSetupSide.LONG and a.high < c.low:
        return SourcePoi(PoiKind.FVG, a.high, c.low, c.closed_at)
    if side is DemoTradingSetupSide.SHORT and a.low > c.high:
        return SourcePoi(PoiKind.FVG, c.high, a.low, c.closed_at)

    if side is DemoTradingSetupSide.LONG and b.low < a.low and b.low < c.low:
        return SourcePoi(PoiKind.RELEVANT_SWING, b.low, b.low, c.closed_at)
    if side is DemoTradingSetupSide.SHORT and b.high > a.high and b.high > c.high:
        return SourcePoi(PoiKind.RELEVANT_SWING, b.high, b.high, c.closed_at)

    last_key = prior_keys[-1]
    last_bars = _bars_between(
        indexed,
        start=last_key,
        end=h4[last_key].closed_at,
    )
    return _last_cisd_poi(last_bars, side=side)


def _poi_touch_index(
    bars: Sequence[Vt08IndexC2R1Bar], poi: SourcePoi
) -> int | None:
    for index, bar in enumerate(bars):
        if poi.observed_at.astimezone(UTC) > bar.opened_at.astimezone(UTC):
            continue
        if poi.touched_by(bar):
            return index
    return None


def _first_continuation(
    bars: Sequence[Vt08IndexC2R1Bar],
    *,
    side: DemoTradingSetupSide,
    start_index: int,
    protected_swing: Decimal,
) -> int | None:
    for index in range(start_index, len(bars)):
        bar = bars[index]
        invalidated = (
            bar.low <= protected_swing
            if side is DemoTradingSetupSide.LONG
            else bar.high >= protected_swing
        )
        if invalidated:
            return None
        if index == 0:
            continue
        previous = bars[index - 1]
        continuation = (
            bar.high > previous.high and bar.close > previous.high
            if side is DemoTradingSetupSide.LONG
            else bar.low < previous.low and bar.close < previous.low
        )
        if continuation:
            return index
    return None


def _completed_h4_model(
    indexed: dict[datetime, Vt08IndexC2R1Bar],
    h4: dict[datetime, Vt08IndexC2R1Bar],
    *,
    current_h4_open: datetime,
    side: DemoTradingSetupSide,
) -> H4ModelKind | None:
    keys = _prior_h4_keys(h4, before=current_h4_open, count=3)
    if len(keys) < 2:
        return None
    if _c2_side(h4[keys[-2]], h4[keys[-1]]) is side:
        poi = _source_poi_for_h4(
            indexed,
            h4,
            h4_opened_at=keys[-1],
            side=side,
        )
        bars = _bars_between(indexed, start=keys[-1], end=h4[keys[-1]].closed_at)
        if poi is not None and _poi_touch_index(bars, poi) is not None:
            return H4ModelKind.C2_EXPANSION
    if len(keys) == 3 and _c3_side(
        h4[keys[-3]], h4[keys[-2]], h4[keys[-1]]
    ) is side:
        poi = _source_poi_for_h4(
            indexed,
            h4,
            h4_opened_at=keys[-1],
            side=side,
        )
        bars = _bars_between(indexed, start=keys[-1], end=h4[keys[-1]].closed_at)
        if poi is not None and _poi_touch_index(bars, poi) is not None:
            return H4ModelKind.C3_EXPANSION
    return None


def _signal_for_h4(
    *,
    symbol: str,
    indexed: dict[datetime, Vt08IndexC2R1Bar],
    h4: dict[datetime, Vt08IndexC2R1Bar],
    h4_opened_at: datetime,
) -> CandidateSignal | None:
    h4_bar = h4.get(h4_opened_at.astimezone(UTC))
    if h4_bar is None:
        return None
    side = _daily_bias(indexed, before=h4_opened_at)
    if side is None:
        return None
    poi = _source_poi_for_h4(
        indexed,
        h4,
        h4_opened_at=h4_opened_at,
        side=side,
    )
    if poi is None:
        return None
    bars = _bars_between(indexed, start=h4_opened_at, end=h4_bar.closed_at)
    if not bars:
        return None
    touch_index = _poi_touch_index(bars, poi)
    if touch_index is None:
        return None

    model_kind = _completed_h4_model(
        indexed,
        h4,
        current_h4_open=h4_opened_at,
        side=side,
    )
    if model_kind is None:
        model_kind = H4ModelKind.SAME_C2

    cisd = _first_cisd(bars, side=side, start_index=touch_index)
    if cisd is None:
        return None
    cisd_index, cisd_level, protected_swing = cisd
    continuation_index = _first_continuation(
        bars,
        side=side,
        start_index=cisd_index + 1,
        protected_swing=protected_swing,
    )
    if continuation_index is None:
        return None
    continuation = bars[continuation_index]
    entry = continuation.close
    risk = (
        entry - protected_swing
        if side is DemoTradingSetupSide.LONG
        else protected_swing - entry
    )
    if risk <= 0:
        return None
    target = (
        entry + TARGET_R_MULTIPLE * risk
        if side is DemoTradingSetupSide.LONG
        else entry - TARGET_R_MULTIPLE * risk
    )
    if target <= 0:
        return None
    return CandidateSignal(
        symbol=symbol,
        side=side,
        model_kind=model_kind,
        h4_opened_at=h4_opened_at,
        signal_at=continuation.closed_at,
        entry=entry,
        stop=protected_swing,
        target=target,
        poi=poi,
        cisd_level=cisd_level,
        cisd_confirmed_at=bars[cisd_index].closed_at,
        protected_swing_extreme=protected_swing,
    )


def _boundary_utc(end_date_exclusive: date) -> datetime:
    return datetime(
        end_date_exclusive.year,
        end_date_exclusive.month,
        end_date_exclusive.day,
        tzinfo=_NY,
    ).astimezone(UTC)


def _model_trade(
    signal: CandidateSignal,
    *,
    indexed: dict[datetime, Vt08IndexC2R1Bar],
    end_date_exclusive: date,
) -> ModeledV6Trade | None:
    boundary = _boundary_utc(end_date_exclusive)
    ordered = tuple(
        bar
        for opened, bar in sorted(indexed.items())
        if opened.astimezone(UTC) >= signal.signal_at.astimezone(UTC)
        and opened.astimezone(UTC) < boundary
    )
    last: Vt08IndexC2R1Bar | None = None
    for bar in ordered:
        last = bar
        resolved = _gap_exit(
            side=signal.side,
            bar=bar,
            stop=signal.stop,
            target=signal.target,
        )
        if resolved is None:
            resolved = _intrabar_exit(
                bar=bar,
                stop=signal.stop,
                target=signal.target,
            )
        if resolved is not None:
            exit_price, reason = resolved
            pnl = (
                exit_price - signal.entry
                if signal.side is DemoTradingSetupSide.LONG
                else signal.entry - exit_price
            )
            risk = abs(signal.entry - signal.stop)
            return ModeledV6Trade(
                signal,
                bar.closed_at,
                exit_price,
                reason,
                pnl / risk,
            )
    if last is None:
        return None
    exit_price = last.close
    pnl = (
        exit_price - signal.entry
        if signal.side is DemoTradingSetupSide.LONG
        else signal.entry - exit_price
    )
    risk = abs(signal.entry - signal.stop)
    return ModeledV6Trade(
        signal,
        last.closed_at,
        exit_price,
        "boundary-mark",
        pnl / risk,
    )


def _market_report(
    *,
    symbol: str,
    bars: Sequence[Vt08IndexC2R1Bar],
    start_date: date,
    end_date_exclusive: date,
) -> dict[str, object]:
    indexed = {bar.opened_at.astimezone(UTC): bar for bar in bars}
    h4 = _build_h4(indexed)
    signals: list[CandidateSignal] = []
    for opened in sorted(h4):
        if not _in_partition(
            opened,
            start_date=start_date,
            end_date_exclusive=end_date_exclusive,
        ):
            continue
        signal = _signal_for_h4(
            symbol=symbol,
            indexed=indexed,
            h4=h4,
            h4_opened_at=opened,
        )
        if signal is not None:
            signals.append(signal)

    ordered_signals = tuple(
        sorted(signals, key=lambda item: (item.signal_at, item.symbol))
    )
    trades = tuple(
        trade
        for signal in ordered_signals
        if (
            trade := _model_trade(
                signal,
                indexed=indexed,
                end_date_exclusive=end_date_exclusive,
            )
        )
        is not None
    )
    return {
        "h4_complete_bars": len(h4),
        "signals": [item.payload() for item in ordered_signals],
        "trades": trades,
    }


def _quartile_means(
    trades: Sequence[ModeledV6Trade], *, stress: Decimal
) -> list[str]:
    n = len(trades)
    result: list[str] = []
    for index in range(4):
        part = trades[(n * index) // 4 : (n * (index + 1)) // 4]
        values = tuple(item.r_multiple - stress for item in part)
        result.append(str(sum(values, Decimal()) / len(values)) if values else "0")
    return result


def build_report(
    *,
    nas100: Path,
    sp500: Path,
    us30: Path,
    start_date: date,
    end_date_exclusive: date,
    expected_software_sha: str,
    minimum_evidence_days: int,
) -> dict[str, object]:
    paths = {"NAS100": nas100, "SP500": sp500, "US30": us30}
    provenance: dict[str, object] = {}
    all_trades: list[ModeledV6Trade] = []
    market_reports: dict[str, object] = {}
    for symbol in AUTHORIZED_MARKETS:
        fingerprint, provider, checked_at, bars = _load_candidate_market(
            paths[symbol],
            expected_symbol=symbol,
            expected_software_sha=expected_software_sha,
            minimum_evidence_days=minimum_evidence_days,
        )
        market_report = _market_report(
            symbol=symbol,
            bars=bars,
            start_date=start_date,
            end_date_exclusive=end_date_exclusive,
        )
        trades = cast(tuple[ModeledV6Trade, ...], market_report["trades"])
        all_trades.extend(trades)
        signals = cast(list[object], market_report["signals"])
        market_reports[symbol] = {
            "h4_complete_bars": market_report["h4_complete_bars"],
            "signal_count": len(signals),
        }
        provenance[symbol] = {
            "provider_symbol": provider,
            "account_fingerprint": fingerprint,
            "checked_at": checked_at.astimezone(UTC).isoformat(),
            "software_sha": expected_software_sha,
            "m15_bars": len(bars),
        }

    ordered = tuple(
        sorted(all_trades, key=lambda item: (item.signal.signal_at, item.signal.symbol))
    )
    n = len(ordered)
    return {
        "schema": SCHEMA,
        "candidate_id": CANDIDATE_ID,
        "rule_fingerprint": RULE_FINGERPRINT,
        "rules": _RULE_MATERIAL,
        "partition": {
            "start_date": start_date.isoformat(),
            "end_date_exclusive": end_date_exclusive.isoformat(),
        },
        "provenance": provenance,
        "market_reports": market_reports,
        "metrics_raw": _metrics(ordered),
        "metrics_primary_stress": _metrics(ordered, stress=PRIMARY_STRESS_R),
        "metrics_secondary_stress": _metrics(ordered, stress=SECONDARY_STRESS_R),
        "by_market_primary_stress": _breakdown(
            ordered, key="symbol", stress=PRIMARY_STRESS_R
        ),
        "by_side_primary_stress": _breakdown(
            ordered, key="side", stress=PRIMARY_STRESS_R
        ),
        "by_anchor_primary_stress": _breakdown(
            ordered, key="anchor", stress=PRIMARY_STRESS_R
        ),
        "by_model_primary_stress": _breakdown(
            ordered, key="model_kind", stress=PRIMARY_STRESS_R
        ),
        "halves_primary_stress": [
            _metrics(ordered[: n // 2], stress=PRIMARY_STRESS_R),
            _metrics(ordered[n // 2 :], stress=PRIMARY_STRESS_R),
        ],
        "quartile_mean_r_primary_stress": _quartile_means(
            ordered, stress=PRIMARY_STRESS_R
        ),
        "boundary_mark_count": sum(
            item.exit_reason == "boundary-mark" for item in ordered
        ),
        "trades": [item.payload() for item in ordered],
        "governance": {
            "research_only": True,
            "fresh_holdout_required": True,
            "live_authorized": False,
            "real_capital_authorized": False,
            "production_authorized": False,
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--nas100", type=Path, required=True)
    parser.add_argument("--sp500", type=Path, required=True)
    parser.add_argument("--us30", type=Path, required=True)
    parser.add_argument("--start-date", type=date.fromisoformat, required=True)
    parser.add_argument("--end-date-exclusive", type=date.fromisoformat, required=True)
    parser.add_argument("--expected-software-sha", required=True)
    parser.add_argument("--minimum-evidence-days", type=int, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    report = build_report(
        nas100=args.nas100,
        sp500=args.sp500,
        us30=args.us30,
        start_date=args.start_date,
        end_date_exclusive=args.end_date_exclusive,
        expected_software_sha=args.expected_software_sha,
        minimum_evidence_days=args.minimum_evidence_days,
    )
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(
        json.dumps(report, sort_keys=True, separators=(",", ":"), allow_nan=False)
        + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "candidate_id": CANDIDATE_ID,
                "rule_fingerprint": RULE_FINGERPRINT,
                "sample": cast(dict[str, object], report["metrics_raw"])["sample"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
