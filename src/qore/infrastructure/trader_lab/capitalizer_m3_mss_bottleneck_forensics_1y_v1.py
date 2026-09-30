"""Forensics for the V3 M3 MSS bottleneck.

This lab does not change trading rules, thresholds, session windows, or outcomes.
It reproduces the V3 close-back population and decomposes M3 rejection causes.

Population:
    H1 sweep -> M5 close-back events seen by frozen V3 before MAX3 ceiling.
Expected nine-market baseline:
    4,039 M5 close-backs
    621 valid M3 MSS/CISD events

Independent failure flags may overlap.
A separate sequential first-blocker view is disjoint.
Late-MSS evidence is diagnostic only and is never used to admit a trade.
"""

from __future__ import annotations

import argparse
import bisect
import json
from collections import Counter
from dataclasses import asdict, dataclass
from datetime import date, datetime, timedelta
from decimal import Decimal
from itertools import combinations
from pathlib import Path
from typing import Any

from qore.infrastructure.trader_lab.capitalizer_cibo_m1_reader_v1 import (
    CapitalizerM1Bar,
    iter_cibo_m1,
)
from qore.infrastructure.trader_lab.capitalizer_contract import (
    MAX_EXECUTIONS_PER_SESSION,
    CapitalizerSession,
)
from qore.infrastructure.trader_lab.capitalizer_exposure_graph import CapitalizerSide
from qore.infrastructure.trader_lab.capitalizer_full_ict_density_scanner_1y_v1 import (
    _aggregate_h1,
)
from qore.infrastructure.trader_lab.capitalizer_ict_2022_m1_entry_1y_replay_v1 import (
    WINDOW_END,
    WINDOW_START,
)
from qore.infrastructure.trader_lab.capitalizer_owner_h1_m3_m1_causal_reversal_1y_v3 import (
    ATR_MULTIPLIER,
    BODY_RATIO_MIN,
    EXPECTED_SYMBOLS,
    LOOKBACK_START,
    H1Swing,
    M3MssEvent,
    SweepCloseback,
    _atr14,
    _build_h1_swings,
    _find_m1_fill,
    _find_sweep_closeback,
    _h1_windows,
    _latest_pivot,
    _liquidity_levels,
    _m1_causal_zone,
    _opposing_series_boundary,
    _previous_day_range,
    _stop_buffer,
)
from qore.infrastructure.trader_lab.capitalizer_strict_htf_gate_1y_v1 import (
    Pivot,
    ReferenceLiquidity,
    TFBar,
    _aggregate_tf,
    _index_day_inputs,
    _pivots,
)

IDENTITY = "QORE_CAPITALIZER_M3_MSS_BOTTLENECK_FORENSICS_1Y_V1"
MATRIX_IDENTITY = (
    "QORE_CAPITALIZER_NINE_MARKET_M3_MSS_BOTTLENECK_FORENSICS_1Y_V1"
)
FAILURE_NAMES = (
    "DIRECTION",
    "SWING_BREAK",
    "CISD",
    "BODY_LT_60",
    "ATR_LE_1_2",
)
EXPECTED_CLOSEBACKS = 4039
EXPECTED_VALID_M3 = 621


@dataclass(frozen=True, slots=True)
class ClosebackDiagnostic:
    symbol: str
    session: str
    operating_date: str
    closeback_at: str
    h1_deadline: str
    side: str
    liquidity_source: str
    valid_m3_within_h1: bool
    first_blocker: str
    direction_failed: bool
    swing_break_failed: bool
    cisd_failed: bool
    body_failed: bool
    atr_failed: bool
    window_expired_late_mss: bool
    directional_bars: int
    swing_break_bars: int
    cisd_bars: int
    body_pass_bars: int
    atr_pass_bars: int
    joint_valid_bars: int
    minutes_remaining_after_closeback: str
    late_mss_at: str | None


@dataclass(frozen=True, slots=True)
class ForensicMarketReport:
    identity: str
    symbol: str
    session: str
    window_start: str
    window_end_exclusive: str
    m5_closebacks: int
    valid_m3_mss: int
    rejected_m3_mss: int
    independent_failures: dict[str, int]
    first_blockers: dict[str, int]
    pairwise_failure_overlaps: dict[str, int]
    failure_signatures: dict[str, int]
    window_expired_late_mss: int
    closebacks_with_zero_m3_bars_remaining: int
    thresholds_changed: bool = False
    session_windows_changed: bool = False
    outcome_aware_selection_used: bool = False
    late_mss_used_for_admission: bool = False
    methodology_research_only: bool = True


def _bar_components(
    bars: tuple[TFBar, ...],
    pivots: tuple[Pivot, ...],
    *,
    index: int,
    side: CapitalizerSide,
) -> tuple[bool, bool, bool, bool, bool]:
    source = bars[index].source
    full_range = source.high - source.low
    directional = (
        source.close > source.open
        if side is CapitalizerSide.LONG
        else source.close < source.open
    )
    if full_range <= 0 or not directional:
        return False, False, False, False, False

    break_kind = "HIGH" if side is CapitalizerSide.LONG else "LOW"
    broken = _latest_pivot(
        pivots,
        before=bars[index].opened_at,
        kind=break_kind,
    )
    swing_break = False
    if broken is not None:
        swing_break = (
            source.close > broken.price
            if side is CapitalizerSide.LONG
            else source.close < broken.price
        )

    boundary = _opposing_series_boundary(
        bars,
        index=index,
        side=side,
    )
    cisd = False
    if boundary is not None:
        cisd = (
            source.close > boundary
            if side is CapitalizerSide.LONG
            else source.close < boundary
        )

    body_ratio = abs(source.close - source.open) / full_range
    body_ok = body_ratio >= BODY_RATIO_MIN
    atr = _atr14(bars, index)
    atr_ok = atr is not None and full_range > ATR_MULTIPLIER * atr
    return True, swing_break, cisd, body_ok, atr_ok


def _event_from_index(
    bars: tuple[TFBar, ...],
    pivots: tuple[Pivot, ...],
    *,
    index: int,
    side: CapitalizerSide,
) -> M3MssEvent | None:
    directional, swing_break, cisd, body_ok, atr_ok = _bar_components(
        bars,
        pivots,
        index=index,
        side=side,
    )
    if not all((directional, swing_break, cisd, body_ok, atr_ok)):
        return None

    source = bars[index].source
    break_kind = "HIGH" if side is CapitalizerSide.LONG else "LOW"
    broken = _latest_pivot(
        pivots,
        before=bars[index].opened_at,
        kind=break_kind,
    )
    boundary = _opposing_series_boundary(
        bars,
        index=index,
        side=side,
    )
    atr = _atr14(bars, index)
    if broken is None or boundary is None or atr is None:
        return None

    full_range = source.high - source.low
    return M3MssEvent(
        side=side,
        confirmed_at=bars[index].closed_at,
        displacement_opened_at=bars[index].opened_at,
        displacement_closed_at=bars[index].closed_at,
        broken_swing_price=broken.price,
        cisd_boundary=boundary,
        body_ratio=abs(source.close - source.open) / full_range,
        atr14=atr,
        displacement_range=full_range,
    )


def _diagnose_closeback(
    *,
    symbol: str,
    session: CapitalizerSession,
    operating_day: date,
    closeback: SweepCloseback,
    m3: tuple[TFBar, ...],
    m3_closes: tuple[datetime, ...],
    m3_pivots: tuple[Pivot, ...],
) -> tuple[ClosebackDiagnostic, M3MssEvent | None]:
    start = bisect.bisect_right(m3_closes, closeback.closeback_at)
    end = bisect.bisect_right(m3_closes, closeback.h1_deadline)

    independent_pass = {
        "DIRECTION": False,
        "SWING_BREAK": False,
        "CISD": False,
        "BODY_LT_60": False,
        "ATR_LE_1_2": False,
    }
    directional_bars = 0
    swing_break_bars = 0
    cisd_bars = 0
    body_pass_bars = 0
    atr_pass_bars = 0
    joint_valid_bars = 0

    directional_indices: list[int] = []
    swing_indices: list[int] = []
    cisd_indices: list[int] = []
    body_indices: list[int] = []
    atr_indices: list[int] = []
    first_event: M3MssEvent | None = None

    for index in range(start, end):
        directional, swing_break, cisd, body_ok, atr_ok = _bar_components(
            m3,
            m3_pivots,
            index=index,
            side=closeback.side,
        )
        if directional:
            independent_pass["DIRECTION"] = True
            directional_bars += 1
            directional_indices.append(index)
        if directional and swing_break:
            independent_pass["SWING_BREAK"] = True
            swing_break_bars += 1
            swing_indices.append(index)
        if directional and cisd:
            independent_pass["CISD"] = True
            cisd_bars += 1
        if directional and body_ok:
            independent_pass["BODY_LT_60"] = True
            body_pass_bars += 1
        if directional and atr_ok:
            independent_pass["ATR_LE_1_2"] = True
            atr_pass_bars += 1

        if directional and swing_break and cisd:
            cisd_indices.append(index)
        if directional and swing_break and cisd and body_ok:
            body_indices.append(index)
        if directional and swing_break and cisd and body_ok and atr_ok:
            atr_indices.append(index)
            joint_valid_bars += 1
            if first_event is None:
                first_event = _event_from_index(
                    m3,
                    m3_pivots,
                    index=index,
                    side=closeback.side,
                )

    if not directional_indices:
        first_blocker = "DIRECTION"
    elif not swing_indices:
        first_blocker = "SWING_BREAK"
    elif not cisd_indices:
        first_blocker = "CISD"
    elif not body_indices:
        first_blocker = "BODY_LT_60"
    elif not atr_indices:
        first_blocker = "ATR_LE_1_2"
    else:
        first_blocker = "VALID"

    late_event: M3MssEvent | None = None
    if first_event is None:
        late_start = bisect.bisect_right(
            m3_closes,
            closeback.h1_deadline,
        )
        late_end = bisect.bisect_right(
            m3_closes,
            closeback.h1_deadline + timedelta(hours=1),
        )
        for index in range(late_start, late_end):
            late_event = _event_from_index(
                m3,
                m3_pivots,
                index=index,
                side=closeback.side,
            )
            if late_event is not None:
                break

    failures = {
        name: not independent_pass[name]
        for name in FAILURE_NAMES
    }
    remaining = closeback.h1_deadline - closeback.closeback_at
    diagnostic = ClosebackDiagnostic(
        symbol=symbol,
        session=session.value,
        operating_date=operating_day.isoformat(),
        closeback_at=closeback.closeback_at.isoformat(),
        h1_deadline=closeback.h1_deadline.isoformat(),
        side=closeback.side.value,
        liquidity_source=closeback.reference.source,
        valid_m3_within_h1=first_event is not None,
        first_blocker=first_blocker,
        direction_failed=failures["DIRECTION"],
        swing_break_failed=failures["SWING_BREAK"],
        cisd_failed=failures["CISD"],
        body_failed=failures["BODY_LT_60"],
        atr_failed=failures["ATR_LE_1_2"],
        window_expired_late_mss=late_event is not None,
        directional_bars=directional_bars,
        swing_break_bars=swing_break_bars,
        cisd_bars=cisd_bars,
        body_pass_bars=body_pass_bars,
        atr_pass_bars=atr_pass_bars,
        joint_valid_bars=joint_valid_bars,
        minutes_remaining_after_closeback=str(
            Decimal(str(remaining.total_seconds())) / Decimal("60")
        ),
        late_mss_at=(
            None
            if late_event is None
            else late_event.confirmed_at.isoformat()
        ),
    )
    return diagnostic, first_event


def _entry_equivalent(
    *,
    event: M3MssEvent,
    closeback: SweepCloseback,
    execution: tuple[CapitalizerM1Bar, ...],
    buffer_price: Decimal,
) -> bool:
    zone = _m1_causal_zone(execution, event=event)
    if zone is None:
        return False
    fill = _find_m1_fill(
        execution,
        event=event,
        zone=zone,
        deadline=closeback.h1_deadline,
    )
    if fill is None:
        return False
    _, entry_price, _ = fill
    stop_price = (
        event.broken_swing_price - buffer_price
        if closeback.side is CapitalizerSide.LONG
        else event.broken_swing_price + buffer_price
    )
    return (
        stop_price < entry_price
        if closeback.side is CapitalizerSide.LONG
        else stop_price > entry_price
    )


def _scan_day(
    *,
    symbol: str,
    session: CapitalizerSession,
    operating_day: date,
    prior_session: ReferenceLiquidity | None,
    execution: tuple[CapitalizerM1Bar, ...],
    all_bars: tuple[CapitalizerM1Bar, ...],
    h1_swings: tuple[H1Swing, ...],
    m5: tuple[TFBar, ...],
    m5_closes: tuple[datetime, ...],
    m3: tuple[TFBar, ...],
    m3_closes: tuple[datetime, ...],
    m3_pivots: tuple[Pivot, ...],
    buffer_price: Decimal,
) -> tuple[ClosebackDiagnostic, ...]:
    if len(execution) < 15:
        return ()

    previous_day = _previous_day_range(
        all_bars,
        operating_day=operating_day,
    )
    diagnostics: list[ClosebackDiagnostic] = []
    entry_equivalent_count = 0

    for h1_open, h1_deadline, hour_bars in _h1_windows(execution):
        if entry_equivalent_count >= MAX_EXECUTIONS_PER_SESSION:
            break
        levels = _liquidity_levels(
            prior_session=prior_session,
            previous_day=previous_day,
            h1_swings=h1_swings,
            hour_open=h1_open,
        )
        if not levels:
            continue

        _, closeback = _find_sweep_closeback(
            hour_bars,
            levels=levels,
            m5=m5,
            m5_closes=m5_closes,
            h1_open=h1_open,
            h1_deadline=h1_deadline,
        )
        if closeback is None:
            continue

        diagnostic, event = _diagnose_closeback(
            symbol=symbol,
            session=session,
            operating_day=operating_day,
            closeback=closeback,
            m3=m3,
            m3_closes=m3_closes,
            m3_pivots=m3_pivots,
        )
        diagnostics.append(diagnostic)

        if event is not None and _entry_equivalent(
            event=event,
            closeback=closeback,
            execution=execution,
            buffer_price=buffer_price,
        ):
            entry_equivalent_count += 1

    return tuple(diagnostics)


def _summarize(
    *,
    symbol: str,
    session: CapitalizerSession,
    diagnostics: tuple[ClosebackDiagnostic, ...],
) -> ForensicMarketReport:
    independent: Counter[str] = Counter()
    first: Counter[str] = Counter()
    signatures: Counter[str] = Counter()
    pairwise: Counter[str] = Counter()

    attr_map = {
        "DIRECTION": "direction_failed",
        "SWING_BREAK": "swing_break_failed",
        "CISD": "cisd_failed",
        "BODY_LT_60": "body_failed",
        "ATR_LE_1_2": "atr_failed",
    }

    for item in diagnostics:
        first[item.first_blocker] += 1
        failed = [
            name
            for name, attr in attr_map.items()
            if bool(getattr(item, attr))
        ]
        for name in failed:
            independent[name] += 1
        signatures[
            "+".join(failed) if failed else "NONE"
        ] += 1
        for left, right in combinations(failed, 2):
            pairwise[f"{left}&{right}"] += 1

    valid = sum(item.valid_m3_within_h1 for item in diagnostics)
    return ForensicMarketReport(
        identity=IDENTITY,
        symbol=symbol,
        session=session.value,
        window_start=WINDOW_START.isoformat(),
        window_end_exclusive=WINDOW_END.isoformat(),
        m5_closebacks=len(diagnostics),
        valid_m3_mss=valid,
        rejected_m3_mss=len(diagnostics) - valid,
        independent_failures={
            name: independent[name]
            for name in FAILURE_NAMES
        },
        first_blockers=dict(sorted(first.items())),
        pairwise_failure_overlaps=dict(sorted(pairwise.items())),
        failure_signatures=dict(
            sorted(
                signatures.items(),
                key=lambda item: (-item[1], item[0]),
            )
        ),
        window_expired_late_mss=sum(
            item.window_expired_late_mss
            for item in diagnostics
        ),
        closebacks_with_zero_m3_bars_remaining=sum(
            Decimal(item.minutes_remaining_after_closeback)
            < Decimal("3")
            for item in diagnostics
        ),
    )


def build_market_report(
    m1_root: Path,
    *,
    session: CapitalizerSession,
) -> tuple[
    ForensicMarketReport,
    tuple[ClosebackDiagnostic, ...],
]:
    all_bars = tuple(
        bar
        for bar in iter_cibo_m1(m1_root)
        if LOOKBACK_START
        <= bar.opened_at
        < WINDOW_END + timedelta(days=1)
    )
    if not all_bars:
        raise ValueError("M3 forensics found no native M1")

    symbol = all_bars[0].symbol
    if any(bar.symbol != symbol for bar in all_bars):
        raise ValueError(
            "M3 forensics requires one symbol per M1 root"
        )

    h1 = _aggregate_h1(all_bars)
    h1_swings = _build_h1_swings(h1)
    m5 = _aggregate_tf(all_bars, minutes=5)
    m3 = _aggregate_tf(all_bars, minutes=3)
    m3_pivots = _pivots(m3)
    m5_closes = tuple(item.closed_at for item in m5)
    m3_closes = tuple(item.closed_at for item in m3)
    buffer_price = _stop_buffer(all_bars)

    execution_by_day, reference_by_day = _index_day_inputs(
        all_bars,
        session=session,
    )
    grouped_dates = sorted(
        key
        for key in execution_by_day
        if WINDOW_START.date().isoformat()
        <= key
        < WINDOW_END.date().isoformat()
    )

    diagnostics: list[ClosebackDiagnostic] = []
    for value in grouped_dates:
        operating_day = date.fromisoformat(value)
        diagnostics.extend(
            _scan_day(
                symbol=symbol,
                session=session,
                operating_day=operating_day,
                prior_session=reference_by_day.get(value),
                execution=execution_by_day.get(value, ()),
                all_bars=all_bars,
                h1_swings=h1_swings,
                m5=m5,
                m5_closes=m5_closes,
                m3=m3,
                m3_closes=m3_closes,
                m3_pivots=m3_pivots,
                buffer_price=buffer_price,
            )
        )

    ordered = tuple(
        sorted(
            diagnostics,
            key=lambda item: item.closeback_at,
        )
    )
    report = _summarize(
        symbol=symbol,
        session=session,
        diagnostics=ordered,
    )
    return report, ordered


def write_market(
    report: ForensicMarketReport,
    diagnostics: tuple[ClosebackDiagnostic, ...],
    output: Path,
) -> None:
    output.mkdir(parents=True, exist_ok=True)
    stem = (
        f"capitalizer-{report.symbol.lower()}-"
        "m3-mss-bottleneck-forensics-1y-v1"
    )
    (output / f"{stem}.json").write_text(
        json.dumps(
            asdict(report),
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    with (output / f"{stem}-closebacks.jsonl").open(
        "w",
        encoding="utf-8",
    ) as handle:
        for item in diagnostics:
            handle.write(
                json.dumps(
                    asdict(item),
                    sort_keys=True,
                )
                + "\n"
            )


def _load_reports(root: Path) -> list[dict[str, Any]]:
    paths = sorted(
        root.rglob(
            "capitalizer-*-m3-mss-bottleneck-"
            "forensics-1y-v1.json"
        )
    )
    if len(paths) != 9:
        raise ValueError(
            f"M3 forensic matrix requires 9 reports, got {len(paths)}"
        )

    reports: list[dict[str, Any]] = []
    for path in paths:
        raw: Any = json.loads(
            path.read_text(encoding="utf-8")
        )
        if (
            not isinstance(raw, dict)
            or raw.get("identity") != IDENTITY
        ):
            raise ValueError(
                "unexpected M3 forensic market report"
            )
        reports.append(dict(raw))

    if {
        str(item["symbol"])
        for item in reports
    } != EXPECTED_SYMBOLS:
        raise ValueError(
            "M3 forensic universe mismatch"
        )
    return sorted(
        reports,
        key=lambda item: str(item["symbol"]),
    )


def _sum_nested(
    reports: list[dict[str, Any]],
    key: str,
) -> dict[str, int]:
    totals: Counter[str] = Counter()
    for report in reports:
        raw = report[key]
        if not isinstance(raw, dict):
            raise ValueError(
                f"{key} must be a dict"
            )
        for name, value in raw.items():
            totals[str(name)] += int(value)
    return dict(sorted(totals.items()))


def build_matrix(root: Path) -> dict[str, Any]:
    reports = _load_reports(root)
    closebacks = sum(
        int(item["m5_closebacks"])
        for item in reports
    )
    valid = sum(
        int(item["valid_m3_mss"])
        for item in reports
    )
    rejected = sum(
        int(item["rejected_m3_mss"])
        for item in reports
    )

    per_session: dict[str, dict[str, Any]] = {}
    for session in CapitalizerSession:
        members = [
            item
            for item in reports
            if item["session"] == session.value
        ]
        per_session[session.value] = {
            "m5_closebacks": sum(
                int(item["m5_closebacks"])
                for item in members
            ),
            "valid_m3_mss": sum(
                int(item["valid_m3_mss"])
                for item in members
            ),
            "rejected_m3_mss": sum(
                int(item["rejected_m3_mss"])
                for item in members
            ),
            "independent_failures": _sum_nested(
                members,
                "independent_failures",
            ),
            "first_blockers": _sum_nested(
                members,
                "first_blockers",
            ),
            "window_expired_late_mss": sum(
                int(item["window_expired_late_mss"])
                for item in members
            ),
        }

    return {
        "identity": MATRIX_IDENTITY,
        "window_start": WINDOW_START.isoformat(),
        "window_end_exclusive": WINDOW_END.isoformat(),
        "market_count": 9,
        "m5_closebacks": closebacks,
        "valid_m3_mss": valid,
        "rejected_m3_mss": rejected,
        "valid_retention": (
            0.0
            if closebacks == 0
            else valid / closebacks
        ),
        "independent_failures": _sum_nested(
            reports,
            "independent_failures",
        ),
        "first_blockers": _sum_nested(
            reports,
            "first_blockers",
        ),
        "pairwise_failure_overlaps": _sum_nested(
            reports,
            "pairwise_failure_overlaps",
        ),
        "failure_signatures": _sum_nested(
            reports,
            "failure_signatures",
        ),
        "window_expired_late_mss": sum(
            int(item["window_expired_late_mss"])
            for item in reports
        ),
        "closebacks_with_zero_m3_bars_remaining": sum(
            int(item["closebacks_with_zero_m3_bars_remaining"])
            for item in reports
        ),
        "per_session": per_session,
        "markets": reports,
        "baseline_expected_closebacks": EXPECTED_CLOSEBACKS,
        "baseline_expected_valid_m3": EXPECTED_VALID_M3,
        "baseline_reconciled": (
            closebacks == EXPECTED_CLOSEBACKS
            and valid == EXPECTED_VALID_M3
        ),
        "thresholds_changed": False,
        "session_windows_changed": False,
        "outcome_aware_selection_used": False,
        "late_mss_used_for_admission": False,
        "methodology_research_only": True,
    }


def write_matrix(
    report: dict[str, Any],
    output: Path,
) -> None:
    output.mkdir(
        parents=True,
        exist_ok=True,
    )
    path = output / (
        "capitalizer-nine-market-m3-mss-"
        "bottleneck-forensics-1y-v1.json"
    )
    path.write_text(
        json.dumps(
            report,
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(
        dest="command",
        required=True,
    )

    market = sub.add_parser("market")
    market.add_argument(
        "m1_root",
        type=Path,
    )
    market.add_argument(
        "output",
        type=Path,
    )
    market.add_argument(
        "--session",
        required=True,
        choices=[
            item.value
            for item in CapitalizerSession
        ],
    )

    matrix = sub.add_parser("matrix")
    matrix.add_argument(
        "input_root",
        type=Path,
    )
    matrix.add_argument(
        "output",
        type=Path,
    )
    args = parser.parse_args()

    if args.command == "market":
        report, diagnostics = build_market_report(
            args.m1_root,
            session=CapitalizerSession(
                args.session
            ),
        )
        write_market(
            report,
            diagnostics,
            args.output,
        )
        print(
            json.dumps(
                asdict(report),
                sort_keys=True,
            )
        )
        return

    matrix_report = build_matrix(
        args.input_root
    )
    write_matrix(
        matrix_report,
        args.output,
    )
    print(
        json.dumps(
            matrix_report,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
