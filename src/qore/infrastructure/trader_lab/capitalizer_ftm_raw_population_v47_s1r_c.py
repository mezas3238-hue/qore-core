"""V47-S1R-C raw historical support census for the separate FTM route.

The source grammar defines Failure-to-Manipulate as a route distinct from the
H1->M15->M1 fractal continuation. This module asks only whether provider-native
consumed history contains causal raw episodes where a taken liquidity level is
followed by continuation CISD before the expected reversal CISD.

It does not construct entries, fills, exits, economics or certification.

Frozen in PR #623 comment 5896470149.
"""

from __future__ import annotations

import argparse
import bisect
import json
from collections import Counter
from dataclasses import asdict, dataclass
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from enum import StrEnum
from pathlib import Path

from qore.infrastructure.trader_lab import (
    capitalizer_canonical_source_context_binders_v47_s0 as binders,
)
from qore.infrastructure.trader_lab import (
    capitalizer_owner_h1_m3_m1_causal_reversal_1y_v3 as v3_source,
)
from qore.infrastructure.trader_lab import (
    capitalizer_source_strategy_isolation_v47_s1 as s1,
)
from qore.infrastructure.trader_lab.capitalizer_cibo_m1_reader_v1 import (
    CapitalizerM1Bar,
    iter_cibo_m1,
)
from qore.infrastructure.trader_lab.capitalizer_contract import CapitalizerSession
from qore.infrastructure.trader_lab.capitalizer_full_ict_density_scanner_1y_v1 import (
    AggregatedBar,
)
from qore.infrastructure.trader_lab.capitalizer_source_cisd_ftm_v2 import detect_cisd
from qore.infrastructure.trader_lab.capitalizer_source_daily_bias_v2 import (
    CapitalizerDailyBiasResolution,
)
from qore.infrastructure.trader_lab.capitalizer_source_observation_detectors_v2 import (
    CapitalizerSourceBar,
    CapitalizerSourceClosureObservation,
    CapitalizerSourceDirection,
)

IDENTITY = "QORE_CAPITALIZER_FTM_RAW_POPULATION_SUPPORT_CENSUS_V47_S1R_C"
PREDECLARATION_COMMENT_ID = 5896470149


class FTMTakenSide(StrEnum):
    HIGH = "HIGH"
    LOW = "LOW"


class FTMRawClassification(StrEnum):
    HTF_CONTEXT_UNRESOLVED = "HTF_CONTEXT_UNRESOLVED"
    HTF_BIAS_NOT_CONTINUATION = "HTF_BIAS_NOT_CONTINUATION"
    EXPECTED_REVERSAL_CISD_FIRST = "EXPECTED_REVERSAL_CISD_FIRST"
    CONTINUATION_CISD_FIRST_RAW_SUPPORT = "CONTINUATION_CISD_FIRST_RAW_SUPPORT"
    CISD_SAME_TIMESTAMP_AMBIGUOUS = "CISD_SAME_TIMESTAMP_AMBIGUOUS"
    NO_STRUCTURAL_CISD_BEFORE_DEADLINE = "NO_STRUCTURAL_CISD_BEFORE_DEADLINE"


@dataclass(frozen=True, slots=True)
class FTMRawSweep:
    symbol: str
    session: CapitalizerSession
    operating_date: date
    taken_side: FTMTakenSide
    liquidity_source: str
    liquidity_price: Decimal
    sweep_at: datetime
    deadline: datetime

    def __post_init__(self) -> None:
        if not self.symbol or self.symbol != self.symbol.upper():
            raise ValueError("FTM raw sweep symbol must be uppercase")
        if self.liquidity_price <= 0:
            raise ValueError("FTM raw sweep liquidity price must be positive")
        if _aware(self.sweep_at) >= _aware(self.deadline):
            raise ValueError("FTM raw sweep must precede deadline")


@dataclass(frozen=True, slots=True)
class FTMRawPeriodMarketReport:
    identity: str
    period: str
    symbol: str
    session: str
    raw_liquidity_sweeps: int
    classification_counts: dict[str, int]
    continuation_first_raw_support: int
    current_reversal_stream_required: bool = False
    full_ftm_entry_constructed: bool = False
    protected_swing_required_for_raw_support: bool = False
    m1_entry_triad_required_for_raw_support: bool = False
    exact_provider_fill_queried: bool = False
    terminal_outcome_read: bool = False
    economics_calculated: bool = False
    fresh_holdout_opened: bool = False
    admission_changed: bool = False
    trader_certified: bool = False

    def __post_init__(self) -> None:
        if self.identity != IDENTITY:
            raise ValueError("FTM raw census identity drift")
        if self.period not in s1.PERIODS:
            raise ValueError("FTM raw census period drift")
        if sum(self.classification_counts.values()) != self.raw_liquidity_sweeps:
            raise ValueError("FTM raw census classification coverage drift")
        if self.continuation_first_raw_support != self.classification_counts.get(
            FTMRawClassification.CONTINUATION_CISD_FIRST_RAW_SUPPORT.value,
            0,
        ):
            raise ValueError("FTM raw support count drift")
        if (
            self.current_reversal_stream_required
            or self.full_ftm_entry_constructed
            or self.protected_swing_required_for_raw_support
            or self.m1_entry_triad_required_for_raw_support
            or self.exact_provider_fill_queried
            or self.terminal_outcome_read
            or self.economics_calculated
            or self.fresh_holdout_opened
            or self.admission_changed
            or self.trader_certified
        ):
            raise ValueError("FTM raw census governance drift")


def _aware(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("FTM raw census requires aware timestamps")
    return value.astimezone(UTC)


def _source(bar: CapitalizerM1Bar) -> CapitalizerSourceBar:
    return CapitalizerSourceBar(
        open=bar.open,
        high=bar.high,
        low=bar.low,
        close=bar.close,
    )


def _opposing(
    bar: CapitalizerM1Bar,
    direction: CapitalizerSourceDirection,
) -> bool:
    if bar.close == bar.open:
        return False
    if direction is CapitalizerSourceDirection.BULLISH:
        return bar.close < bar.open
    return bar.close > bar.open


def _direction_pair(
    taken_side: FTMTakenSide,
) -> tuple[CapitalizerSourceDirection, CapitalizerSourceDirection]:
    if taken_side is FTMTakenSide.HIGH:
        return (
            CapitalizerSourceDirection.BEARISH,
            CapitalizerSourceDirection.BULLISH,
        )
    return (
        CapitalizerSourceDirection.BULLISH,
        CapitalizerSourceDirection.BEARISH,
    )


def first_structural_m1_cisd(
    bars: tuple[CapitalizerM1Bar, ...],
    *,
    direction: CapitalizerSourceDirection,
    after: datetime,
    before: datetime,
    htf_closure: CapitalizerSourceClosureObservation,
) -> datetime | None:
    """Return first structural CISD; HTF mismatch does not erase raw structure."""

    selected = tuple(
        row
        for row in bars
        if _aware(after) < row.closed_at <= _aware(before)
    )
    for index, confirmation in enumerate(selected):
        cursor = index - 1
        if cursor < 0 or not _opposing(selected[cursor], direction):
            continue
        start = cursor
        while start > 0 and _opposing(selected[start - 1], direction):
            start -= 1
        series_rows = selected[start:index]
        if not series_rows:
            continue
        observed = detect_cisd(
            causal_series=tuple(_source(row) for row in series_rows),
            confirmation_bar=_source(confirmation),
            direction=direction,
            important_level_reached=True,
            higher_timeframe_closure=htf_closure,
        )
        if observed.structural_confirmed:
            return confirmation.closed_at
    return None


def _classify_raw_sweep_with_context(
    bars: tuple[CapitalizerM1Bar, ...],
    *,
    sweep: FTMRawSweep,
    context: binders.S0HTFContext | None,
) -> FTMRawClassification:
    expected, continuation = _direction_pair(sweep.taken_side)
    if context is None:
        return FTMRawClassification.HTF_CONTEXT_UNRESOLVED
    if (
        context.daily_bias.resolution is not CapitalizerDailyBiasResolution.CONFIRMED
        or context.daily_bias.direction is not continuation
    ):
        return FTMRawClassification.HTF_BIAS_NOT_CONTINUATION

    reversal_at = first_structural_m1_cisd(
        bars,
        direction=expected,
        after=sweep.sweep_at,
        before=sweep.deadline,
        htf_closure=context.closure,
    )
    continuation_at = first_structural_m1_cisd(
        bars,
        direction=continuation,
        after=sweep.sweep_at,
        before=sweep.deadline,
        htf_closure=context.closure,
    )

    if reversal_at is None and continuation_at is None:
        return FTMRawClassification.NO_STRUCTURAL_CISD_BEFORE_DEADLINE
    if reversal_at is not None and continuation_at is not None:
        if reversal_at == continuation_at:
            return FTMRawClassification.CISD_SAME_TIMESTAMP_AMBIGUOUS
        if reversal_at < continuation_at:
            return FTMRawClassification.EXPECTED_REVERSAL_CISD_FIRST
        return FTMRawClassification.CONTINUATION_CISD_FIRST_RAW_SUPPORT
    if reversal_at is not None:
        return FTMRawClassification.EXPECTED_REVERSAL_CISD_FIRST
    return FTMRawClassification.CONTINUATION_CISD_FIRST_RAW_SUPPORT


def classify_raw_sweep(
    bars: tuple[CapitalizerM1Bar, ...],
    *,
    sweep: FTMRawSweep,
) -> FTMRawClassification:
    context = binders.bind_latest_h1_context(
        bars,
        decision_at=sweep.sweep_at,
    )
    return _classify_raw_sweep_with_context(
        bars,
        sweep=sweep,
        context=context,
    )


def _h1_context_rows(
    prepared: s1._PreparedSourceSeries,
    *,
    start: datetime,
    end: datetime,
) -> tuple[AggregatedBar, ...]:
    left = bisect.bisect_left(prepared.h1_opened, _aware(start))
    right = bisect.bisect_left(prepared.h1_opened, _aware(end))
    return tuple(
        row
        for row in prepared.h1[left:right]
        if row.closed_at <= _aware(end)
    )


def raw_sweeps_for_day(
    bars: tuple[CapitalizerM1Bar, ...],
    *,
    prepared: s1._PreparedSourceSeries,
    session: CapitalizerSession,
    operating_day: date,
) -> tuple[FTMRawSweep, ...]:
    source_start, source_end = s1.source_session_bounds(
        operating_day,
        session=session,
    )
    execution = s1._prepared_m1_between(
        prepared,
        start=source_start,
        end=source_end,
    )
    if len(execution) < 15:
        return ()

    previous_day = s1._prepared_previous_day_range(
        prepared,
        operating_day=operating_day,
    )
    prior_session = s1._reference_liquidity(
        bars,
        operating_day=operating_day,
        session=session,
        prepared=prepared,
    )
    h1 = _h1_context_rows(
        prepared,
        start=source_start - s1.LOOKBACK,
        end=source_end + timedelta(hours=1),
    )
    h1_swings = v3_source._build_h1_swings(h1)

    result: dict[tuple[datetime, str, Decimal], FTMRawSweep] = {}
    symbol = execution[0].symbol
    for h1_open, h1_deadline, hour_bars in v3_source._h1_windows(execution):
        deadline = min(h1_deadline, source_end)
        levels = v3_source._liquidity_levels(
            prior_session=prior_session,
            previous_day=previous_day,
            h1_swings=h1_swings,
            hour_open=h1_open,
        )
        for level in levels:
            swept = next(
                (
                    bar
                    for bar in hour_bars
                    if (
                        bar.high > level.price
                        if level.kind == "HIGH"
                        else bar.low < level.price
                    )
                    and bar.opened_at < deadline
                ),
                None,
            )
            if swept is None:
                continue
            taken_side = (
                FTMTakenSide.HIGH
                if level.kind == "HIGH"
                else FTMTakenSide.LOW
            )
            row = FTMRawSweep(
                symbol=symbol,
                session=session,
                operating_date=operating_day,
                taken_side=taken_side,
                liquidity_source=level.source,
                liquidity_price=level.price,
                sweep_at=swept.opened_at,
                deadline=deadline,
            )
            result[(row.sweep_at, level.kind, level.price)] = row

    return tuple(
        sorted(
            result.values(),
            key=lambda item: (
                item.sweep_at,
                item.taken_side.value,
                item.liquidity_price,
                item.liquidity_source,
            ),
        )
    )


def audit_period_market(
    bars: tuple[CapitalizerM1Bar, ...],
    *,
    symbol: str,
    session: CapitalizerSession,
    period: str,
) -> FTMRawPeriodMarketReport:
    start, end = s1.PERIODS[period]
    prepared = s1._prepare_source_series(bars)
    days = s1._operating_days(
        bars,
        session=session,
        period_start=start,
        period_end=end,
    )
    opened = prepared.opened
    counts: Counter[str] = Counter()
    raw_count = 0

    for day in days:
        local = s1._day_slice(
            bars,
            opened,
            operating_day=day,
            session=session,
        )
        if not local:
            continue
        sweeps = raw_sweeps_for_day(
            local,
            prepared=prepared,
            session=session,
            operating_day=day,
        )
        raw_count += len(sweeps)
        context_by_hour: dict[datetime, binders.S0HTFContext | None] = {}
        for sweep in sweeps:
            hour_open = sweep.sweep_at.replace(minute=0, second=0, microsecond=0)
            if hour_open not in context_by_hour:
                context_by_hour[hour_open] = binders.bind_latest_h1_context(
                    local,
                    decision_at=sweep.sweep_at,
                )
            classification = _classify_raw_sweep_with_context(
                local,
                sweep=sweep,
                context=context_by_hour[hour_open],
            )
            counts[classification.value] += 1

    return FTMRawPeriodMarketReport(
        identity=IDENTITY,
        period=period,
        symbol=symbol,
        session=session.value,
        raw_liquidity_sweeps=raw_count,
        classification_counts=dict(sorted(counts.items())),
        continuation_first_raw_support=counts[
            FTMRawClassification.CONTINUATION_CISD_FIRST_RAW_SUPPORT.value
        ],
    )


def _load_consumed(root: Path, symbol: str) -> tuple[CapitalizerM1Bar, ...]:
    rows = tuple(
        row
        for row in iter_cibo_m1(root)
        if s1.CONSUMED_LOAD_START <= row.opened_at < s1.CONSUMED_LOAD_END
    )
    if not rows:
        raise ValueError("FTM raw census provider-native M1 is empty")
    if any(row.symbol != symbol for row in rows):
        raise ValueError("FTM raw census symbol mismatch")
    return rows


def write_report(report: FTMRawPeriodMarketReport, output: Path) -> None:
    output.mkdir(parents=True, exist_ok=True)
    path = output / (
        f"capitalizer-v47-s1r-c-ftm-{report.period}-{report.symbol.lower()}.json"
    )
    path.write_text(
        json.dumps(asdict(report), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _json_int(row: dict[str, object], key: str) -> int:
    value = row.get(key)
    if type(value) is not int:
        raise ValueError(f"FTM aggregate field {key} must be int")
    return value


def aggregate(root: Path, output: Path) -> dict[str, object]:
    reports: list[dict[str, object]] = []
    for path in sorted(root.rglob("capitalizer-v47-s1r-c-ftm-*.json")):
        raw = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(raw, dict):
            raise ValueError("FTM raw report must be object")
        reports.append(raw)
    if len(reports) != 27:
        raise ValueError(f"FTM raw census requires 27 reports, got {len(reports)}")

    counts: Counter[str] = Counter()
    for report in reports:
        raw_counts = report.get("classification_counts")
        if not isinstance(raw_counts, dict):
            raise ValueError("FTM raw classification_counts must be object")
        for key, value in raw_counts.items():
            if type(value) is not int:
                raise ValueError("FTM raw classification count must be int")
            counts[str(key)] += value

    raw_sweeps = sum(_json_int(row, "raw_liquidity_sweeps") for row in reports)
    support = sum(
        _json_int(row, "continuation_first_raw_support")
        for row in reports
    )
    if sum(counts.values()) != raw_sweeps:
        raise ValueError("FTM raw aggregate classification coverage drift")

    decision = (
        "SEPARATE_FTM_STREAM_ENGINEERING_JUSTIFIED_PRE_ECONOMICALLY"
        if support > 0
        else "SEPARATE_FTM_HISTORICAL_SUPPORT_NOT_OBSERVED"
    )
    payload: dict[str, object] = {
        "identity": IDENTITY,
        "predeclaration_comment_id": PREDECLARATION_COMMENT_ID,
        "market_period_reports": len(reports),
        "market_count": len({str(row["symbol"]) for row in reports}),
        "raw_liquidity_sweeps": raw_sweeps,
        "classification_counts": dict(sorted(counts.items())),
        "continuation_first_raw_support": support,
        "current_reversal_stream_required": False,
        "full_ftm_entry_constructed": False,
        "protected_swing_required_for_raw_support": False,
        "m1_entry_triad_required_for_raw_support": False,
        "exact_provider_fill_queried": False,
        "terminal_outcome_read": False,
        "economics_calculated": False,
        "fresh_holdout_opened": False,
        "admission_changed": False,
        "trader_certified": False,
        "decision": decision,
    }
    output.mkdir(parents=True, exist_ok=True)
    (output / "capitalizer-v47-s1r-c-ftm-aggregate.json").write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return payload


def main() -> None:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)

    market = sub.add_parser("market")
    market.add_argument("m1_root", type=Path)
    market.add_argument("--symbol", required=True)
    market.add_argument("--session", required=True)
    market.add_argument("--output", type=Path, required=True)

    matrix = sub.add_parser("aggregate")
    matrix.add_argument("input", type=Path)
    matrix.add_argument("--output", type=Path, required=True)

    args = parser.parse_args()
    if args.command == "market":
        bars = _load_consumed(args.m1_root, args.symbol)
        for period in s1.PERIODS:
            report = audit_period_market(
                bars,
                symbol=args.symbol,
                session=CapitalizerSession(args.session),
                period=period,
            )
            write_report(report, args.output)
            print(json.dumps(asdict(report), sort_keys=True))
        return

    payload = aggregate(args.input, args.output)
    print(json.dumps(payload, sort_keys=True))


if __name__ == "__main__":
    main()
