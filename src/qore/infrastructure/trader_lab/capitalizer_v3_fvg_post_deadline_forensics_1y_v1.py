"""Observe post-H1 retests for V3 FVGs that did not fill in the frozen lifecycle."""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from datetime import date, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any

from qore.infrastructure.trader_lab import (
    capitalizer_owner_h1_m3_m1_causal_reversal_1y_v3 as v3,
)
from qore.infrastructure.trader_lab.capitalizer_cibo_m1_reader_v1 import (
    CapitalizerM1Bar,
    iter_cibo_m1,
)
from qore.infrastructure.trader_lab.capitalizer_contract import (
    MAX_EXECUTIONS_PER_SESSION,
    CapitalizerSession,
)
from qore.infrastructure.trader_lab.capitalizer_exposure_graph import (
    CapitalizerSide,
)
from qore.infrastructure.trader_lab.capitalizer_full_ict_density_scanner_1y_v1 import (
    _aggregate_h1,
)
from qore.infrastructure.trader_lab.capitalizer_ict_2022_m1_entry_1y_replay_v1 import (
    WINDOW_END,
    WINDOW_START,
)
from qore.infrastructure.trader_lab.capitalizer_strict_htf_gate_1y_v1 import (
    Pivot,
    ReferenceLiquidity,
    TFBar,
    _aggregate_tf,
    _index_day_inputs,
    _pivots,
)

IDENTITY = "QORE_CAPITALIZER_V3_FVG_POST_DEADLINE_FORENSICS_1Y_V1"
MATRIX_IDENTITY = (
    "QORE_CAPITALIZER_NINE_MARKET_V3_FVG_POST_DEADLINE_FORENSICS_1Y_V1"
)
ARCHITECTURE = "V3_FROZEN_FVG_NO_FILL_POST_H1_OBSERVATION_ONLY"
EXPECTED_V3_NO_FILL_COHORT = 258
EXPECTED_V3_MAX3 = 226
OBSERVATION_MINUTES = 60


@dataclass(frozen=True, slots=True)
class V3EntryReference:
    symbol: str
    session: str
    operating_date: str
    side: str
    entry_at: str


@dataclass(frozen=True, slots=True)
class PostDeadlineRow:
    symbol: str
    session: str
    operating_date: str
    side: str
    h1_open: str
    h1_deadline: str
    mss_at: str
    fvg_confirmed_at: str
    fvg_low: str
    fvg_high: str
    overlap_low: str | None
    overlap_high: str | None
    broken_swing_price: str
    buffered_stop_price: str
    session_minutes_available_after_deadline: int
    delayed_touch_at: str | None
    delayed_touch_minutes: int | None
    delayed_touch_mode: str | None
    delayed_entry_price: str | None
    delayed_stop_geometry_valid: bool | None
    pre_deadline_broken_swing_breach: bool
    pre_deadline_buffered_stop_breach: bool
    post_deadline_pre_touch_broken_swing_breach: bool
    post_deadline_pre_touch_buffered_stop_breach: bool
    touch_bar_broken_swing_breach: bool | None
    touch_bar_buffered_stop_breach: bool | None
    observational_clean_touch: bool
    outcome_used_for_admission: bool = False


def _aware(value: str) -> datetime:
    return datetime.fromisoformat(value)


def _minutes(start: datetime, end: datetime) -> int:
    return int((end - start).total_seconds() // 60)


def _stop_price(
    *,
    side: CapitalizerSide,
    mss: v3.M3MssEvent,
    buffer_price: Decimal,
) -> Decimal:
    if side is CapitalizerSide.LONG:
        return mss.broken_swing_price - buffer_price
    return mss.broken_swing_price + buffer_price


def _breached(
    bar: CapitalizerM1Bar,
    *,
    side: CapitalizerSide,
    level: Decimal,
) -> bool:
    if side is CapitalizerSide.LONG:
        return bar.low <= level
    return bar.high >= level


def _breach_between(
    execution: tuple[CapitalizerM1Bar, ...],
    *,
    side: CapitalizerSide,
    level: Decimal,
    start: datetime,
    end_exclusive: datetime,
) -> bool:
    return any(
        start <= bar.opened_at < end_exclusive
        and _breached(bar, side=side, level=level)
        for bar in execution
    )


def _bar_at(
    execution: tuple[CapitalizerM1Bar, ...],
    opened_at: datetime,
) -> CapitalizerM1Bar | None:
    for bar in execution:
        if bar.opened_at == opened_at:
            return bar
    return None


def _scan_day(
    *,
    symbol: str,
    session: CapitalizerSession,
    operating_day: date,
    prior_session: ReferenceLiquidity | None,
    execution: tuple[CapitalizerM1Bar, ...],
    all_bars: tuple[CapitalizerM1Bar, ...],
    h1_swings: tuple[v3.H1Swing, ...],
    m5: tuple[TFBar, ...],
    m5_closes: tuple[datetime, ...],
    m3: tuple[TFBar, ...],
    m3_closes: tuple[datetime, ...],
    m3_pivots: tuple[Pivot, ...],
    buffer_price: Decimal,
    stages: Counter[str],
) -> tuple[tuple[PostDeadlineRow, ...], tuple[V3EntryReference, ...]]:
    if len(execution) < 15:
        stages["EXECUTION_WINDOW_TOO_SPARSE"] += 1
        return (), ()
    previous_day = v3._previous_day_range(
        all_bars,
        operating_day=operating_day,
    )
    cohort: list[PostDeadlineRow] = []
    v3_entries: list[V3EntryReference] = []
    for h1_open, h1_deadline, hour_bars in v3._h1_windows(execution):
        stages["H1_HOUR_SCANNED"] += 1
        levels = v3._liquidity_levels(
            prior_session=prior_session,
            previous_day=previous_day,
            h1_swings=h1_swings,
            hour_open=h1_open,
        )
        if not levels:
            continue
        sweep_seen, closeback = v3._find_sweep_closeback(
            hour_bars,
            levels=levels,
            m5=m5,
            m5_closes=m5_closes,
            h1_open=h1_open,
            h1_deadline=h1_deadline,
        )
        if sweep_seen:
            stages["H1_SWEEP_DETECTED"] += 1
        if closeback is None:
            continue
        stages["M5_CLOSEBACK_CONFIRMED"] += 1
        mss = v3._find_m3_mss(
            m3,
            m3_closes,
            m3_pivots,
            after=closeback.closeback_at,
            before=h1_deadline,
            side=closeback.side,
        )
        if mss is None:
            continue
        stages["V3_MSS_CONFIRMED"] += 1
        zone = v3._m1_causal_zone(execution, event=mss)
        if zone is None:
            stages["V3_FVG_MISSING"] += 1
            continue
        stages["V3_FVG_CONFIRMED"] += 1
        frozen_fill = v3._find_m1_fill(
            execution,
            event=mss,
            zone=zone,
            deadline=h1_deadline,
        )
        stop_price = _stop_price(
            side=closeback.side,
            mss=mss,
            buffer_price=buffer_price,
        )
        if frozen_fill is not None:
            entry_index, entry_price, _entry_mode = frozen_fill
            valid_stop = (
                stop_price < entry_price
                if closeback.side is CapitalizerSide.LONG
                else stop_price > entry_price
            )
            if valid_stop:
                stages["V3_EXECUTABLE_RAW"] += 1
                v3_entries.append(
                    V3EntryReference(
                        symbol=symbol,
                        session=session.value,
                        operating_date=operating_day.isoformat(),
                        side=closeback.side.value,
                        entry_at=execution[entry_index].opened_at.isoformat(),
                    )
                )
            else:
                stages["V3_STOP_INVALID"] += 1
            continue

        stages["V3_FVG_NO_FILL_COHORT"] += 1
        observation_deadline = h1_deadline + timedelta(
            minutes=OBSERVATION_MINUTES
        )
        delayed_fill = v3._find_m1_fill(
            execution,
            event=mss,
            zone=zone,
            deadline=observation_deadline,
        )
        available_minutes = sum(
            h1_deadline <= bar.opened_at < observation_deadline
            for bar in execution
        )
        pre_broken = _breach_between(
            execution,
            side=closeback.side,
            level=mss.broken_swing_price,
            start=mss.confirmed_at,
            end_exclusive=h1_deadline,
        )
        pre_stop = _breach_between(
            execution,
            side=closeback.side,
            level=stop_price,
            start=mss.confirmed_at,
            end_exclusive=h1_deadline,
        )

        delayed_at: datetime | None = None
        delayed_minutes: int | None = None
        delayed_mode: str | None = None
        delayed_price: Decimal | None = None
        delayed_geometry: bool | None = None
        post_broken = False
        post_stop = False
        touch_broken: bool | None = None
        touch_stop: bool | None = None
        clean = False

        if delayed_fill is None:
            stages["NO_TOUCH_WITHIN_60M"] += 1
            post_broken = _breach_between(
                execution,
                side=closeback.side,
                level=mss.broken_swing_price,
                start=h1_deadline,
                end_exclusive=observation_deadline,
            )
            post_stop = _breach_between(
                execution,
                side=closeback.side,
                level=stop_price,
                start=h1_deadline,
                end_exclusive=observation_deadline,
            )
        else:
            entry_index, delayed_price, delayed_mode = delayed_fill
            delayed_at = execution[entry_index].opened_at
            delayed_minutes = _minutes(h1_deadline, delayed_at)
            stages["POST_DEADLINE_TOUCH"] += 1
            delayed_geometry = (
                stop_price < delayed_price
                if closeback.side is CapitalizerSide.LONG
                else stop_price > delayed_price
            )
            if delayed_geometry:
                stages["POST_DEADLINE_TOUCH_VALID_STOP_GEOMETRY"] += 1
            else:
                stages["POST_DEADLINE_TOUCH_INVALID_STOP_GEOMETRY"] += 1
            post_broken = _breach_between(
                execution,
                side=closeback.side,
                level=mss.broken_swing_price,
                start=h1_deadline,
                end_exclusive=delayed_at,
            )
            post_stop = _breach_between(
                execution,
                side=closeback.side,
                level=stop_price,
                start=h1_deadline,
                end_exclusive=delayed_at,
            )
            touch_bar = _bar_at(execution, delayed_at)
            if touch_bar is not None:
                touch_broken = _breached(
                    touch_bar,
                    side=closeback.side,
                    level=mss.broken_swing_price,
                )
                touch_stop = _breached(
                    touch_bar,
                    side=closeback.side,
                    level=stop_price,
                )
            clean = bool(
                delayed_geometry
                and not pre_broken
                and not pre_stop
                and not post_broken
                and not post_stop
                and touch_broken is False
                and touch_stop is False
            )
            if clean:
                stages["OBSERVATIONAL_CLEAN_TOUCH"] += 1
            if delayed_mode == "OB_FVG_RETEST":
                stages["POST_DEADLINE_OB_FVG_RETEST"] += 1
            elif delayed_mode == "FVG_CE_50":
                stages["POST_DEADLINE_FVG_CE_50"] += 1

        cohort.append(
            PostDeadlineRow(
                symbol=symbol,
                session=session.value,
                operating_date=operating_day.isoformat(),
                side=closeback.side.value,
                h1_open=h1_open.isoformat(),
                h1_deadline=h1_deadline.isoformat(),
                mss_at=mss.confirmed_at.isoformat(),
                fvg_confirmed_at=zone.fvg_confirmed_at.isoformat(),
                fvg_low=str(zone.fvg_low),
                fvg_high=str(zone.fvg_high),
                overlap_low=(
                    None if zone.overlap_low is None else str(zone.overlap_low)
                ),
                overlap_high=(
                    None if zone.overlap_high is None else str(zone.overlap_high)
                ),
                broken_swing_price=str(mss.broken_swing_price),
                buffered_stop_price=str(stop_price),
                session_minutes_available_after_deadline=available_minutes,
                delayed_touch_at=(
                    None if delayed_at is None else delayed_at.isoformat()
                ),
                delayed_touch_minutes=delayed_minutes,
                delayed_touch_mode=delayed_mode,
                delayed_entry_price=(
                    None if delayed_price is None else str(delayed_price)
                ),
                delayed_stop_geometry_valid=delayed_geometry,
                pre_deadline_broken_swing_breach=pre_broken,
                pre_deadline_buffered_stop_breach=pre_stop,
                post_deadline_pre_touch_broken_swing_breach=post_broken,
                post_deadline_pre_touch_buffered_stop_breach=post_stop,
                touch_bar_broken_swing_breach=touch_broken,
                touch_bar_buffered_stop_breach=touch_stop,
                observational_clean_touch=clean,
            )
        )
    return tuple(cohort), tuple(v3_entries)


def build_market_report(
    m1_root: Path,
    *,
    session: CapitalizerSession,
) -> tuple[
    dict[str, Any],
    tuple[PostDeadlineRow, ...],
    tuple[V3EntryReference, ...],
]:
    all_bars = tuple(
        bar
        for bar in iter_cibo_m1(m1_root)
        if v3.LOOKBACK_START <= bar.opened_at < WINDOW_END + timedelta(days=1)
    )
    if not all_bars:
        raise ValueError("post-deadline forensics found no native M1")
    symbol = all_bars[0].symbol
    if any(bar.symbol != symbol for bar in all_bars):
        raise ValueError("post-deadline forensics requires one symbol per M1 root")
    h1 = _aggregate_h1(all_bars)
    h1_swings = v3._build_h1_swings(h1)
    m5 = _aggregate_tf(all_bars, minutes=5)
    m3 = _aggregate_tf(all_bars, minutes=3)
    m3_pivots = _pivots(m3)
    m5_closes = tuple(item.closed_at for item in m5)
    m3_closes = tuple(item.closed_at for item in m3)
    buffer_price = v3._stop_buffer(all_bars)
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
    stages: Counter[str] = Counter()
    rows: list[PostDeadlineRow] = []
    entries: list[V3EntryReference] = []
    for value in grouped_dates:
        operating_day = date.fromisoformat(value)
        produced_rows, produced_entries = _scan_day(
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
            stages=stages,
        )
        rows.extend(produced_rows)
        entries.extend(produced_entries)
    ordered_rows = tuple(
        sorted(rows, key=lambda item: (item.operating_date, item.h1_open))
    )
    ordered_entries = tuple(
        sorted(entries, key=lambda item: (_aware(item.entry_at), item.symbol))
    )
    report: dict[str, Any] = {
        "identity": IDENTITY,
        "architecture": ARCHITECTURE,
        "symbol": symbol,
        "session": session.value,
        "window_start": WINDOW_START.isoformat(),
        "window_end_exclusive": WINDOW_END.isoformat(),
        "operating_sessions_scanned": len(grouped_dates),
        "stage_counts": dict(sorted(stages.items())),
        "no_fill_cohort": len(ordered_rows),
        "post_deadline_touches": sum(
            item.delayed_touch_at is not None for item in ordered_rows
        ),
        "observational_clean_touches": sum(
            item.observational_clean_touch for item in ordered_rows
        ),
        "v3_executable_raw": len(ordered_entries),
        "observation_minutes": OBSERVATION_MINUTES,
        "same_session_only": True,
        "diagnostic_only": True,
        "strategy_mutated": False,
        "lifecycle_mutated": False,
        "entry_trigger_mutated": False,
        "stop_mutated": False,
        "target_mutated": False,
        "max3_mutated": False,
        "outcome_used_for_admission": False,
        "fresh_holdout_claimed": False,
        "economic_candidate": False,
        "trader_certified": False,
        "live_authorized": False,
        "real_capital_authorized": False,
    }
    return report, ordered_rows, ordered_entries


def write_market(
    report: dict[str, Any],
    rows: tuple[PostDeadlineRow, ...],
    entries: tuple[V3EntryReference, ...],
    output: Path,
) -> None:
    output.mkdir(parents=True, exist_ok=True)
    symbol = str(report["symbol"]).lower()
    stem = f"capitalizer-{symbol}-v3-fvg-post-deadline-forensics-1y-v1"
    (output / f"{stem}.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    with (output / f"{stem}-rows.jsonl").open(
        "w",
        encoding="utf-8",
    ) as handle:
        for row in rows:
            handle.write(json.dumps(asdict(row), sort_keys=True) + "\n")
    with (output / f"{stem}-v3-entries.jsonl").open(
        "w",
        encoding="utf-8",
    ) as handle:
        for entry in entries:
            handle.write(json.dumps(asdict(entry), sort_keys=True) + "\n")


def _load_reports(root: Path) -> list[dict[str, Any]]:
    paths = sorted(
        root.rglob("capitalizer-*-v3-fvg-post-deadline-forensics-1y-v1.json")
    )
    if len(paths) != 9:
        raise ValueError(f"post-deadline matrix requires 9 reports, got {len(paths)}")
    reports = [
        dict(json.loads(path.read_text(encoding="utf-8")))
        for path in paths
    ]
    if {str(item["symbol"]) for item in reports} != v3.EXPECTED_SYMBOLS:
        raise ValueError("post-deadline universe mismatch")
    return reports


def _load_rows(root: Path) -> tuple[dict[str, Any], ...]:
    rows: list[dict[str, Any]] = []
    for path in sorted(
        root.rglob(
            "capitalizer-*-v3-fvg-post-deadline-forensics-1y-v1-rows.jsonl"
        )
    ):
        with path.open(encoding="utf-8") as handle:
            for line in handle:
                if line.strip():
                    rows.append(dict(json.loads(line)))
    return tuple(rows)


def _load_entries(root: Path) -> tuple[dict[str, Any], ...]:
    entries: list[dict[str, Any]] = []
    for path in sorted(
        root.rglob(
            "capitalizer-*-v3-fvg-post-deadline-forensics-1y-v1-v3-entries.jsonl"
        )
    ):
        with path.open(encoding="utf-8") as handle:
            for line in handle:
                if line.strip():
                    entries.append(dict(json.loads(line)))
    return tuple(entries)


def _portfolio_max3(
    entries: tuple[dict[str, Any], ...],
) -> tuple[dict[str, Any], ...]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for entry in entries:
        grouped[f'{entry["session"]}:{entry["operating_date"]}'].append(entry)
    selected: list[dict[str, Any]] = []
    for key in sorted(grouped):
        ordered = sorted(
            grouped[key],
            key=lambda item: (
                _aware(str(item["entry_at"])),
                str(item["symbol"]),
            ),
        )
        selected.extend(ordered[:MAX_EXECUTIONS_PER_SESSION])
    return tuple(
        sorted(
            selected,
            key=lambda item: (
                _aware(str(item["entry_at"])),
                str(item["symbol"]),
            ),
        )
    )


def _touch_bucket(minutes: int | None) -> str:
    if minutes is None:
        return "NO_TOUCH_60"
    if minutes <= 5:
        return "00_05"
    if minutes <= 15:
        return "06_15"
    if minutes <= 30:
        return "16_30"
    return "31_59"


def build_matrix(root: Path) -> dict[str, Any]:
    reports = _load_reports(root)
    rows = _load_rows(root)
    entries = _load_entries(root)
    selected_v3 = _portfolio_max3(entries)

    touch_buckets: Counter[str] = Counter()
    by_market: dict[str, Counter[str]] = defaultdict(Counter)
    by_session: dict[str, Counter[str]] = defaultdict(Counter)
    touches: list[dict[str, Any]] = []
    for row in rows:
        bucket = _touch_bucket(
            None
            if row["delayed_touch_minutes"] is None
            else int(row["delayed_touch_minutes"])
        )
        touch_buckets[bucket] += 1
        by_market[str(row["symbol"])][bucket] += 1
        by_session[str(row["session"])][bucket] += 1
        if row["delayed_touch_at"] is not None:
            touches.append(row)

    frozen_v3_by_key: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for entry in selected_v3:
        frozen_v3_by_key[
            f'{entry["session"]}:{entry["operating_date"]}'
        ].append(entry)

    slots_available = 0
    blocked_by_frozen_max3 = 0
    clean_with_slot = 0
    simultaneous_groups: Counter[str] = Counter()
    for row in touches:
        touch_at = _aware(str(row["delayed_touch_at"]))
        key = f'{row["session"]}:{row["operating_date"]}'
        used_before = sum(
            _aware(str(entry["entry_at"])) <= touch_at
            for entry in frozen_v3_by_key.get(key, [])
        )
        if used_before >= MAX_EXECUTIONS_PER_SESSION:
            blocked_by_frozen_max3 += 1
        else:
            slots_available += 1
            if bool(row["observational_clean_touch"]):
                clean_with_slot += 1
        minute_key = (
            f'{row["session"]}:{row["operating_date"]}:'
            f'{touch_at.isoformat(timespec="minutes")}'
        )
        simultaneous_groups[minute_key] += 1

    simultaneous_touch_groups = sum(
        count > 1 for count in simultaneous_groups.values()
    )
    rows_with_simultaneous_touch = sum(
        count for count in simultaneous_groups.values() if count > 1
    )

    cumulative = {
        "touch_within_5m": sum(
            row["delayed_touch_minutes"] is not None
            and int(row["delayed_touch_minutes"]) <= 5
            for row in rows
        ),
        "touch_within_15m": sum(
            row["delayed_touch_minutes"] is not None
            and int(row["delayed_touch_minutes"]) <= 15
            for row in rows
        ),
        "touch_within_30m": sum(
            row["delayed_touch_minutes"] is not None
            and int(row["delayed_touch_minutes"]) <= 30
            for row in rows
        ),
        "touch_within_60m": len(touches),
    }

    result: dict[str, Any] = {
        "identity": MATRIX_IDENTITY,
        "architecture": ARCHITECTURE,
        "window_start": WINDOW_START.isoformat(),
        "window_end_exclusive": WINDOW_END.isoformat(),
        "market_count": 9,
        "no_fill_cohort": len(rows),
        "expected_no_fill_cohort": EXPECTED_V3_NO_FILL_COHORT,
        "no_fill_control_reproduced": len(rows) == EXPECTED_V3_NO_FILL_COHORT,
        "v3_raw_executable": len(entries),
        "v3_max3_selected": len(selected_v3),
        "expected_v3_max3": EXPECTED_V3_MAX3,
        "v3_control_reproduced": len(selected_v3) == EXPECTED_V3_MAX3,
        "touch_buckets": dict(sorted(touch_buckets.items())),
        "cumulative_touches": cumulative,
        "post_deadline_touches": len(touches),
        "no_touch_within_60m": len(rows) - len(touches),
        "valid_stop_geometry_at_touch": sum(
            row["delayed_stop_geometry_valid"] is True for row in touches
        ),
        "pre_deadline_broken_swing_breach": sum(
            bool(row["pre_deadline_broken_swing_breach"]) for row in rows
        ),
        "pre_deadline_buffered_stop_breach": sum(
            bool(row["pre_deadline_buffered_stop_breach"]) for row in rows
        ),
        "post_deadline_pre_touch_broken_swing_breach": sum(
            bool(row["post_deadline_pre_touch_broken_swing_breach"])
            for row in rows
        ),
        "post_deadline_pre_touch_buffered_stop_breach": sum(
            bool(row["post_deadline_pre_touch_buffered_stop_breach"])
            for row in rows
        ),
        "observational_clean_touches": sum(
            bool(row["observational_clean_touch"]) for row in rows
        ),
        "touches_with_frozen_v3_max3_slot_available": slots_available,
        "touches_blocked_by_frozen_v3_max3": blocked_by_frozen_max3,
        "clean_touches_with_frozen_v3_slot_available": clean_with_slot,
        "simultaneous_touch_groups": simultaneous_touch_groups,
        "rows_in_simultaneous_touch_groups": rows_with_simultaneous_touch,
        "touch_modes": dict(
            Counter(
                str(row["delayed_touch_mode"])
                for row in touches
                if row["delayed_touch_mode"] is not None
            )
        ),
        "per_market_touch_buckets": {
            key: dict(sorted(value.items()))
            for key, value in sorted(by_market.items())
        },
        "per_session_touch_buckets": {
            key: dict(sorted(value.items()))
            for key, value in sorted(by_session.items())
        },
        "markets": reports,
        "observation_minutes": OBSERVATION_MINUTES,
        "same_session_only": True,
        "diagnostic_only": True,
        "strategy_mutated": False,
        "lifecycle_mutated": False,
        "entry_trigger_mutated": False,
        "stop_mutated": False,
        "target_mutated": False,
        "max3_mutated": False,
        "outcome_used_for_admission": False,
        "fresh_holdout_claimed": False,
        "economic_candidate": False,
        "trader_certified": False,
        "live_authorized": False,
        "real_capital_authorized": False,
    }
    return result


def write_matrix(report: dict[str, Any], output: Path) -> None:
    output.mkdir(parents=True, exist_ok=True)
    path = (
        output
        / "capitalizer-nine-market-v3-fvg-post-deadline-forensics-1y-v1.json"
    )
    path.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    market = sub.add_parser("market")
    market.add_argument("m1_root", type=Path)
    market.add_argument("output", type=Path)
    market.add_argument(
        "--session",
        required=True,
        choices=[item.value for item in CapitalizerSession],
    )
    matrix = sub.add_parser("matrix")
    matrix.add_argument("input_root", type=Path)
    matrix.add_argument("output", type=Path)
    args = parser.parse_args()

    if args.command == "market":
        report, rows, entries = build_market_report(
            args.m1_root,
            session=CapitalizerSession(args.session),
        )
        write_market(report, rows, entries, args.output)
        print(
            json.dumps(
                {
                    "symbol": report["symbol"],
                    "session": report["session"],
                    "no_fill_cohort": report["no_fill_cohort"],
                    "post_deadline_touches": report["post_deadline_touches"],
                    "observational_clean_touches": report[
                        "observational_clean_touches"
                    ],
                },
                sort_keys=True,
            )
        )
        return

    report = build_matrix(args.input_root)
    write_matrix(report, args.output)
    print(json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    main()
