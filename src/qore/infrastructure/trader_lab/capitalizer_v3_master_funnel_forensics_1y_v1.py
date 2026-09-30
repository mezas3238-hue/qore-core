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

IDENTITY = "QORE_CAPITALIZER_V3_MASTER_FUNNEL_FORENSICS_1Y_V1"
MATRIX_IDENTITY = "QORE_CAPITALIZER_NINE_MARKET_V3_MASTER_FUNNEL_FORENSICS_1Y_V1"
ARCHITECTURE = "V3_FROZEN_DIAGNOSTIC_ONLY_POST_MSS_TO_FVG_FILL"
D1_OVERLAY_IDENTITY = "V3_N1_OR_N2_OBSERVATIONAL_OVERLAY"

EXPECTED_V3_MAX3_TRADES = 226
EXPECTED_D1_MAX3_TRADES = 398


@dataclass(frozen=True, slots=True)
class ForensicRow:
    symbol: str
    session: str
    operating_date: str
    side: str
    h1_open: str
    h1_deadline: str
    sweep_at: str
    closeback_at: str
    v3_mss_at: str | None
    closeback_to_mss_minutes: int | None
    mss_minute_in_h1: int | None
    minutes_remaining_at_mss: int | None
    fvg_confirmed_at: str | None
    fvg_age_at_mss_minutes: int | None
    ob_fvg_overlap: bool | None
    fill_at: str | None
    mss_to_fill_minutes: int | None
    entry_mode: str | None
    valid_stop_geometry: bool | None
    v3_executable: bool
    v3_entry_price: str | None
    v3_stop_price: str | None
    v3_target_price: str | None
    v3_realized_r: str | None
    v3_exit_reason: str | None
    delayed_n2_mss_at: str | None
    delayed_minutes_after_h1_deadline: int | None
    delayed_fvg_confirmed_at: str | None
    delayed_fill_at: str | None
    delayed_entry_mode: str | None
    delayed_valid_stop_geometry: bool | None
    delayed_executable: bool
    delayed_entry_price: str | None
    delayed_stop_price: str | None
    delayed_target_price: str | None
    delayed_realized_r: str | None
    delayed_exit_reason: str | None
    outcome_used_for_admission: bool = False


def _aware(value: str) -> datetime:
    return datetime.fromisoformat(value)


def _minutes(start: datetime, end: datetime) -> int:
    return int((end - start).total_seconds() // 60)


def _economic_metrics(rows: tuple[dict[str, Any], ...], *, prefix: str) -> dict[str, Any] | None:
    usable = [
        row
        for row in rows
        if row.get(f"{prefix}_realized_r") is not None
        and row.get(f"{prefix}_fill_at") is not None
    ]
    if not usable:
        return None
    ordered = sorted(
        usable,
        key=lambda row: (
            _aware(str(row[f"{prefix}_fill_at"])),
            str(row["symbol"]),
        ),
    )
    values = [Decimal(str(row[f"{prefix}_realized_r"])) for row in ordered]
    gross_profit = sum((value for value in values if value > 0), Decimal("0"))
    gross_loss = -sum((value for value in values if value < 0), Decimal("0"))
    total = sum(values, Decimal("0"))
    equity = Decimal("0")
    peak = Decimal("0")
    max_dd = Decimal("0")
    streak = 0
    max_streak = 0
    wins = 0
    losses = 0
    flats = 0
    for value in values:
        equity += value
        peak = max(peak, equity)
        max_dd = max(max_dd, peak - equity)
        if value > 0:
            wins += 1
            streak = 0
        elif value < 0:
            losses += 1
            streak += 1
            max_streak = max(max_streak, streak)
        else:
            flats += 1
            streak = 0
    return {
        "trades": len(values),
        "wins": wins,
        "losses": losses,
        "flats": flats,
        "gross_profit_r": str(gross_profit),
        "gross_loss_r": str(gross_loss),
        "total_r": str(total),
        "mean_r": str(total / Decimal(len(values))),
        "profit_factor": (
            None if gross_loss == 0 else str(gross_profit / gross_loss)
        ),
        "max_drawdown_r": str(max_dd),
        "max_losing_streak": max_streak,
    }


def _trade_geometry(
    execution: tuple[CapitalizerM1Bar, ...],
    *,
    side: CapitalizerSide,
    mss: v3.M3MssEvent,
    zone: v3.M1EntryZone,
    deadline: datetime,
    buffer_price: Decimal,
) -> dict[str, Any]:
    fill = v3._find_m1_fill(
        execution,
        event=mss,
        zone=zone,
        deadline=deadline,
    )
    if fill is None:
        return {
            "fill_at": None,
            "entry_mode": None,
            "valid_stop_geometry": None,
            "executable": False,
            "entry_price": None,
            "stop_price": None,
            "target_price": None,
            "realized_r": None,
            "exit_reason": None,
            "mss_to_fill_minutes": None,
        }
    entry_index, entry_price, entry_mode = fill
    entry_at = execution[entry_index].opened_at
    stop_price = (
        mss.broken_swing_price - buffer_price
        if side is CapitalizerSide.LONG
        else mss.broken_swing_price + buffer_price
    )
    valid_stop = (
        stop_price < entry_price
        if side is CapitalizerSide.LONG
        else stop_price > entry_price
    )
    if not valid_stop:
        return {
            "fill_at": entry_at,
            "entry_mode": entry_mode,
            "valid_stop_geometry": False,
            "executable": False,
            "entry_price": entry_price,
            "stop_price": stop_price,
            "target_price": None,
            "realized_r": None,
            "exit_reason": None,
            "mss_to_fill_minutes": _minutes(mss.confirmed_at, entry_at),
        }
    risk = abs(entry_price - stop_price)
    target_price = (
        entry_price + Decimal("2") * risk
        if side is CapitalizerSide.LONG
        else entry_price - Decimal("2") * risk
    )
    realized, reason, _held, _ambiguous, _exit_at = v3._lifecycle(
        execution,
        entry_index=entry_index,
        side=side,
        entry_price=entry_price,
        stop_price=stop_price,
        target_price=target_price,
        deadline=deadline,
    )
    return {
        "fill_at": entry_at,
        "entry_mode": entry_mode,
        "valid_stop_geometry": True,
        "executable": True,
        "entry_price": entry_price,
        "stop_price": stop_price,
        "target_price": target_price,
        "realized_r": realized,
        "exit_reason": reason,
        "mss_to_fill_minutes": _minutes(mss.confirmed_at, entry_at),
    }


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
) -> tuple[ForensicRow, ...]:
    if len(execution) < 15:
        stages["EXECUTION_WINDOW_TOO_SPARSE"] += 1
        return ()
    previous_day = v3._previous_day_range(
        all_bars,
        operating_day=operating_day,
    )
    rows: list[ForensicRow] = []
    for h1_open, h1_deadline, hour_bars in v3._h1_windows(execution):
        stages["H1_HOUR_SCANNED"] += 1
        levels = v3._liquidity_levels(
            prior_session=prior_session,
            previous_day=previous_day,
            h1_swings=h1_swings,
            hour_open=h1_open,
        )
        if not levels:
            stages["H1_HOUR_NO_LIQUIDITY"] += 1
            continue
        stages["H1_HOUR_WITH_LIQUIDITY"] += 1
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
            if sweep_seen:
                stages["M5_CLOSEBACK_MISSING"] += 1
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

        v3_mss_at: str | None = None
        closeback_to_mss: int | None = None
        mss_minute: int | None = None
        minutes_remaining: int | None = None
        fvg_confirmed_at: str | None = None
        fvg_age: int | None = None
        overlap: bool | None = None
        fill_at: str | None = None
        mss_to_fill: int | None = None
        entry_mode: str | None = None
        valid_stop: bool | None = None
        executable = False
        entry_price: Decimal | None = None
        stop_price: Decimal | None = None
        target_price: Decimal | None = None
        realized: Decimal | None = None
        exit_reason: str | None = None

        delayed_mss_at: str | None = None
        delayed_after_deadline: int | None = None
        delayed_fvg_at: str | None = None
        delayed_fill_at: str | None = None
        delayed_entry_mode: str | None = None
        delayed_valid_stop: bool | None = None
        delayed_executable = False
        delayed_entry_price: Decimal | None = None
        delayed_stop_price: Decimal | None = None
        delayed_target_price: Decimal | None = None
        delayed_realized: Decimal | None = None
        delayed_exit_reason: str | None = None

        if mss is None:
            stages["V3_M3_MSS_MISSING"] += 1
            delayed_deadline = h1_deadline + timedelta(hours=1)
            delayed = v3._find_m3_mss(
                m3,
                m3_closes,
                m3_pivots,
                after=h1_deadline,
                before=delayed_deadline,
                side=closeback.side,
            )
            if delayed is not None:
                stages["N2_DELAYED_MSS_FOUND"] += 1
                delayed_mss_at = delayed.confirmed_at.isoformat()
                delayed_after_deadline = _minutes(
                    h1_deadline,
                    delayed.confirmed_at,
                )
                delayed_zone = v3._m1_causal_zone(execution, event=delayed)
                if delayed_zone is None:
                    stages["N2_DELAYED_FVG_MISSING"] += 1
                else:
                    stages["N2_DELAYED_FVG_CONFIRMED"] += 1
                    delayed_fvg_at = delayed_zone.fvg_confirmed_at.isoformat()
                    geometry = _trade_geometry(
                        execution,
                        side=closeback.side,
                        mss=delayed,
                        zone=delayed_zone,
                        deadline=delayed_deadline,
                        buffer_price=buffer_price,
                    )
                    delayed_fill_at = (
                        None
                        if geometry["fill_at"] is None
                        else geometry["fill_at"].isoformat()
                    )
                    delayed_entry_mode = geometry["entry_mode"]
                    delayed_valid_stop = geometry["valid_stop_geometry"]
                    delayed_executable = bool(geometry["executable"])
                    delayed_entry_price = geometry["entry_price"]
                    delayed_stop_price = geometry["stop_price"]
                    delayed_target_price = geometry["target_price"]
                    delayed_realized = geometry["realized_r"]
                    delayed_exit_reason = geometry["exit_reason"]
                    if geometry["fill_at"] is None:
                        stages["N2_DELAYED_FILL_MISSING"] += 1
                    elif geometry["valid_stop_geometry"] is False:
                        stages["N2_DELAYED_STOP_INVALID"] += 1
                    elif delayed_executable:
                        stages["N2_DELAYED_EXECUTABLE"] += 1
        else:
            stages["V3_M3_MSS_CONFIRMED"] += 1
            v3_mss_at = mss.confirmed_at.isoformat()
            closeback_to_mss = _minutes(
                closeback.closeback_at,
                mss.confirmed_at,
            )
            mss_minute = _minutes(h1_open, mss.confirmed_at)
            minutes_remaining = _minutes(mss.confirmed_at, h1_deadline)
            zone = v3._m1_causal_zone(execution, event=mss)
            if zone is None:
                stages["V3_FVG_MISSING"] += 1
            else:
                stages["V3_FVG_CONFIRMED"] += 1
                fvg_confirmed_at = zone.fvg_confirmed_at.isoformat()
                fvg_age = _minutes(zone.fvg_confirmed_at, mss.confirmed_at)
                overlap = (
                    zone.overlap_low is not None
                    and zone.overlap_high is not None
                )
                if overlap:
                    stages["V3_OB_FVG_OVERLAP"] += 1
                geometry = _trade_geometry(
                    execution,
                    side=closeback.side,
                    mss=mss,
                    zone=zone,
                    deadline=h1_deadline,
                    buffer_price=buffer_price,
                )
                fill_at = (
                    None
                    if geometry["fill_at"] is None
                    else geometry["fill_at"].isoformat()
                )
                mss_to_fill = geometry["mss_to_fill_minutes"]
                entry_mode = geometry["entry_mode"]
                valid_stop = geometry["valid_stop_geometry"]
                executable = bool(geometry["executable"])
                entry_price = geometry["entry_price"]
                stop_price = geometry["stop_price"]
                target_price = geometry["target_price"]
                realized = geometry["realized_r"]
                exit_reason = geometry["exit_reason"]
                if geometry["fill_at"] is None:
                    stages["V3_FILL_MISSING"] += 1
                elif geometry["valid_stop_geometry"] is False:
                    stages["V3_STOP_INVALID"] += 1
                elif executable:
                    stages["V3_EXECUTABLE"] += 1
                    if entry_mode == "OB_FVG_RETEST":
                        stages["V3_ENTRY_OB_FVG_RETEST"] += 1
                    elif entry_mode == "FVG_CE_50":
                        stages["V3_ENTRY_FVG_CE_50"] += 1

        rows.append(
            ForensicRow(
                symbol=symbol,
                session=session.value,
                operating_date=operating_day.isoformat(),
                side=closeback.side.value,
                h1_open=h1_open.isoformat(),
                h1_deadline=h1_deadline.isoformat(),
                sweep_at=closeback.sweep_at.isoformat(),
                closeback_at=closeback.closeback_at.isoformat(),
                v3_mss_at=v3_mss_at,
                closeback_to_mss_minutes=closeback_to_mss,
                mss_minute_in_h1=mss_minute,
                minutes_remaining_at_mss=minutes_remaining,
                fvg_confirmed_at=fvg_confirmed_at,
                fvg_age_at_mss_minutes=fvg_age,
                ob_fvg_overlap=overlap,
                fill_at=fill_at,
                mss_to_fill_minutes=mss_to_fill,
                entry_mode=entry_mode,
                valid_stop_geometry=valid_stop,
                v3_executable=executable,
                v3_entry_price=None if entry_price is None else str(entry_price),
                v3_stop_price=None if stop_price is None else str(stop_price),
                v3_target_price=None if target_price is None else str(target_price),
                v3_realized_r=None if realized is None else str(realized),
                v3_exit_reason=exit_reason,
                delayed_n2_mss_at=delayed_mss_at,
                delayed_minutes_after_h1_deadline=delayed_after_deadline,
                delayed_fvg_confirmed_at=delayed_fvg_at,
                delayed_fill_at=delayed_fill_at,
                delayed_entry_mode=delayed_entry_mode,
                delayed_valid_stop_geometry=delayed_valid_stop,
                delayed_executable=delayed_executable,
                delayed_entry_price=(
                    None
                    if delayed_entry_price is None
                    else str(delayed_entry_price)
                ),
                delayed_stop_price=(
                    None
                    if delayed_stop_price is None
                    else str(delayed_stop_price)
                ),
                delayed_target_price=(
                    None
                    if delayed_target_price is None
                    else str(delayed_target_price)
                ),
                delayed_realized_r=(
                    None
                    if delayed_realized is None
                    else str(delayed_realized)
                ),
                delayed_exit_reason=delayed_exit_reason,
            )
        )
    return tuple(rows)


def build_market_report(
    m1_root: Path,
    *,
    session: CapitalizerSession,
) -> tuple[dict[str, Any], tuple[ForensicRow, ...]]:
    all_bars = tuple(
        bar
        for bar in iter_cibo_m1(m1_root)
        if v3.LOOKBACK_START
        <= bar.opened_at
        < WINDOW_END + timedelta(days=1)
    )
    if not all_bars:
        raise ValueError("master forensics found no native M1")
    symbol = all_bars[0].symbol
    if any(bar.symbol != symbol for bar in all_bars):
        raise ValueError("master forensics requires one symbol per M1 root")
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
    rows: list[ForensicRow] = []
    for value in grouped_dates:
        operating_day = date.fromisoformat(value)
        rows.extend(
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
                stages=stages,
            )
        )
    ordered = tuple(
        sorted(
            rows,
            key=lambda item: (
                item.operating_date,
                item.h1_open,
                item.symbol,
            ),
        )
    )
    row_dicts = tuple(asdict(item) for item in ordered)
    primary_exec = tuple(
        item for item in row_dicts if bool(item["v3_executable"])
    )
    delayed_exec = tuple(
        item for item in row_dicts if bool(item["delayed_executable"])
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
        "closeback_rows": len(ordered),
        "v3_executable_raw": len(primary_exec),
        "v3_raw_metrics": _economic_metrics(primary_exec, prefix="v3"),
        "n2_delayed_executable_raw": len(delayed_exec),
        "n2_delayed_raw_metrics": _economic_metrics(
            delayed_exec,
            prefix="delayed",
        ),
        "diagnostic_only": True,
        "strategy_mutated": False,
        "v3_thresholds_mutated": False,
        "entry_trigger_mutated": False,
        "outcome_used_for_admission": False,
        "portfolio_max3_applied_only_in_aggregate": True,
        "max3_is_ceiling_not_quota": True,
        "fresh_holdout_claimed": False,
        "economic_candidate": False,
        "trader_certified": False,
        "live_authorized": False,
        "real_capital_authorized": False,
    }
    return report, ordered


def write_market(
    report: dict[str, Any],
    rows: tuple[ForensicRow, ...],
    output: Path,
) -> None:
    output.mkdir(parents=True, exist_ok=True)
    symbol = str(report["symbol"]).lower()
    stem = f"capitalizer-{symbol}-v3-master-funnel-forensics-1y-v1"
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


def _load_reports(root: Path) -> list[dict[str, Any]]:
    paths = sorted(
        root.rglob("capitalizer-*-v3-master-funnel-forensics-1y-v1.json")
    )
    if len(paths) != 9:
        raise ValueError(f"master forensics requires 9 reports, got {len(paths)}")
    reports = [
        dict(json.loads(path.read_text(encoding="utf-8")))
        for path in paths
    ]
    if {str(item["symbol"]) for item in reports} != v3.EXPECTED_SYMBOLS:
        raise ValueError("master forensics universe mismatch")
    return reports


def _load_rows(root: Path) -> tuple[dict[str, Any], ...]:
    rows: list[dict[str, Any]] = []
    for path in sorted(
        root.rglob(
            "capitalizer-*-v3-master-funnel-forensics-1y-v1-rows.jsonl"
        )
    ):
        with path.open(encoding="utf-8") as handle:
            for line in handle:
                if line.strip():
                    rows.append(dict(json.loads(line)))
    return tuple(rows)


def _dedupe_rows(
    rows: tuple[dict[str, Any], ...],
    *,
    entry_field: str,
) -> tuple[dict[str, Any], ...]:
    seen: set[tuple[str, str, str, str]] = set()
    selected: list[dict[str, Any]] = []
    for row in sorted(
        rows,
        key=lambda item: (
            _aware(str(item[entry_field])),
            str(item["symbol"]),
        ),
    ):
        key = (
            str(row["symbol"]),
            str(row["operating_date"]),
            str(row[entry_field]),
            str(row["side"]),
        )
        if key in seen:
            continue
        seen.add(key)
        selected.append(row)
    return tuple(selected)


def _portfolio_max3(
    rows: tuple[dict[str, Any], ...],
    *,
    entry_field: str,
) -> tuple[dict[str, Any], ...]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[f'{row["session"]}:{row["operating_date"]}'].append(row)
    selected: list[dict[str, Any]] = []
    for key in sorted(grouped):
        ordered = sorted(
            grouped[key],
            key=lambda item: (
                _aware(str(item[entry_field])),
                str(item["symbol"]),
            ),
        )
        selected.extend(ordered[:MAX_EXECUTIONS_PER_SESSION])
    return tuple(
        sorted(
            selected,
            key=lambda item: (
                _aware(str(item[entry_field])),
                str(item["symbol"]),
            ),
        )
    )


def _distribution(
    rows: tuple[dict[str, Any], ...],
    field: str,
    *,
    bins: tuple[tuple[str, int | None], ...],
) -> dict[str, int]:
    result = {name: 0 for name, _ in bins}
    for row in rows:
        value = row.get(field)
        if value is None:
            continue
        number = int(value)
        lower = -10**9
        for name, upper in bins:
            if upper is None or lower <= number <= upper:
                result[name] += 1
                break
            lower = upper + 1
    return result


def _matrix_metrics(
    rows: tuple[dict[str, Any], ...],
    *,
    prefix: str,
    key: str,
) -> dict[str, Any]:
    values = sorted({str(row[key]) for row in rows})
    output: dict[str, Any] = {}
    for value in values:
        subset = tuple(row for row in rows if str(row[key]) == value)
        output[value] = {
            "trades": len(subset),
            "metrics": _economic_metrics(subset, prefix=prefix),
        }
    return output


def build_matrix(root: Path) -> dict[str, Any]:
    reports = _load_reports(root)
    rows = _load_rows(root)

    primary_raw = _dedupe_rows(
        tuple(row for row in rows if bool(row["v3_executable"])),
        entry_field="fill_at",
    )
    primary_max3 = _portfolio_max3(primary_raw, entry_field="fill_at")

    d1_overlay_rows: list[dict[str, Any]] = []
    for row in rows:
        if bool(row["v3_executable"]):
            copy = dict(row)
            copy["overlay_fill_at"] = row["fill_at"]
            copy["overlay_realized_r"] = row["v3_realized_r"]
            d1_overlay_rows.append(copy)
        elif row["v3_mss_at"] is None and bool(row["delayed_executable"]):
            copy = dict(row)
            copy["overlay_fill_at"] = row["delayed_fill_at"]
            copy["overlay_realized_r"] = row["delayed_realized_r"]
            d1_overlay_rows.append(copy)
    d1_raw = _dedupe_rows(
        tuple(d1_overlay_rows),
        entry_field="overlay_fill_at",
    )
    d1_max3 = _portfolio_max3(d1_raw, entry_field="overlay_fill_at")

    primary_for_metrics = tuple(
        {
            **row,
            "selected_fill_at": row["fill_at"],
            "selected_realized_r": row["v3_realized_r"],
        }
        for row in primary_max3
    )
    d1_for_metrics = tuple(
        {
            **row,
            "selected_fill_at": row["overlay_fill_at"],
            "selected_realized_r": row["overlay_realized_r"],
        }
        for row in d1_max3
    )

    primary_mss_rows = tuple(
        row for row in rows if row["v3_mss_at"] is not None
    )
    fvg_rows = tuple(
        row for row in primary_mss_rows if row["fvg_confirmed_at"] is not None
    )
    fill_rows = tuple(
        row for row in fvg_rows if row["fill_at"] is not None
    )
    valid_stop_rows = tuple(
        row for row in fill_rows if row["valid_stop_geometry"] is True
    )

    stage_total: Counter[str] = Counter()
    for report in reports:
        for name, count in dict(report["stage_counts"]).items():
            stage_total[str(name)] += int(count)

    result = {
        "identity": MATRIX_IDENTITY,
        "architecture": ARCHITECTURE,
        "d1_overlay_identity": D1_OVERLAY_IDENTITY,
        "window_start": WINDOW_START.isoformat(),
        "window_end_exclusive": WINDOW_END.isoformat(),
        "market_count": 9,
        "assigned_session_count": 3,
        "assigned_market_session_pairs": 9,
        "stage_counts": dict(sorted(stage_total.items())),
        "funnel": {
            "m5_closebacks": stage_total["M5_CLOSEBACK_CONFIRMED"],
            "v3_mss": len(primary_mss_rows),
            "v3_fvg": len(fvg_rows),
            "v3_fill": len(fill_rows),
            "v3_valid_stop": len(valid_stop_rows),
            "v3_executable_raw_deduped": len(primary_raw),
            "v3_max3_selected": len(primary_max3),
            "v3_blocked_by_portfolio_max3": len(primary_raw) - len(primary_max3),
            "n2_delayed_mss": stage_total["N2_DELAYED_MSS_FOUND"],
            "n2_delayed_fvg": stage_total["N2_DELAYED_FVG_CONFIRMED"],
            "n2_delayed_executable": stage_total["N2_DELAYED_EXECUTABLE"],
        },
        "v3_max3_metrics": _economic_metrics(
            primary_for_metrics,
            prefix="selected",
        ),
        "d1_overlay_raw_trades": len(d1_raw),
        "d1_overlay_max3_trades": len(d1_max3),
        "d1_overlay_max3_metrics": _economic_metrics(
            d1_for_metrics,
            prefix="selected",
        ),
        "timing": {
            "closeback_to_mss_minutes": _distribution(
                primary_mss_rows,
                "closeback_to_mss_minutes",
                bins=(
                    ("0_5", 5),
                    ("6_15", 15),
                    ("16_30", 30),
                    ("31_45", 45),
                    ("46_60", 60),
                    ("61_plus", None),
                ),
            ),
            "mss_minute_in_h1": _distribution(
                primary_mss_rows,
                "mss_minute_in_h1",
                bins=(
                    ("00_14", 14),
                    ("15_29", 29),
                    ("30_44", 44),
                    ("45_60", 60),
                    ("61_plus", None),
                ),
            ),
            "minutes_remaining_at_mss": _distribution(
                primary_mss_rows,
                "minutes_remaining_at_mss",
                bins=(
                    ("0_5", 5),
                    ("6_15", 15),
                    ("16_30", 30),
                    ("31_45", 45),
                    ("46_60", 60),
                    ("61_plus", None),
                ),
            ),
            "fvg_age_at_mss_minutes": _distribution(
                fvg_rows,
                "fvg_age_at_mss_minutes",
                bins=(
                    ("0_1", 1),
                    ("2_3", 3),
                    ("4_plus", None),
                ),
            ),
            "mss_to_fill_minutes": _distribution(
                tuple(row for row in fill_rows if row["mss_to_fill_minutes"] is not None),
                "mss_to_fill_minutes",
                bins=(
                    ("0_1", 1),
                    ("2_5", 5),
                    ("6_15", 15),
                    ("16_30", 30),
                    ("31_plus", None),
                ),
            ),
            "delayed_minutes_after_h1_deadline": _distribution(
                tuple(
                    row
                    for row in rows
                    if row["delayed_n2_mss_at"] is not None
                ),
                "delayed_minutes_after_h1_deadline",
                bins=(
                    ("0_5", 5),
                    ("6_15", 15),
                    ("16_30", 30),
                    ("31_45", 45),
                    ("46_60", 60),
                    ("61_plus", None),
                ),
            ),
        },
        "entry_modes": dict(
            Counter(
                str(row["entry_mode"])
                for row in primary_raw
                if row["entry_mode"] is not None
            )
        ),
        "per_market_selected": _matrix_metrics(
            primary_for_metrics,
            prefix="selected",
            key="symbol",
        ),
        "per_session_selected": _matrix_metrics(
            primary_for_metrics,
            prefix="selected",
            key="session",
        ),
        "markets": reports,
        "v3_control_expected_max3_trades": EXPECTED_V3_MAX3_TRADES,
        "v3_control_reproduced": len(primary_max3) == EXPECTED_V3_MAX3_TRADES,
        "d1_control_expected_max3_trades": EXPECTED_D1_MAX3_TRADES,
        "d1_control_reproduced": len(d1_max3) == EXPECTED_D1_MAX3_TRADES,
        "diagnostic_only": True,
        "strategy_mutated": False,
        "thresholds_mutated": False,
        "outcome_used_for_admission": False,
        "cross_session_expansion_used": False,
        "assigned_killzones_preserved": True,
        "fresh_holdout_claimed": False,
        "economic_candidate": False,
        "trader_certified": False,
        "live_authorized": False,
        "real_capital_authorized": False,
    }
    return result


def write_matrix(report: dict[str, Any], output: Path) -> None:
    output.mkdir(parents=True, exist_ok=True)
    path = output / "capitalizer-nine-market-v3-master-funnel-forensics-1y-v1.json"
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
        report, rows = build_market_report(
            args.m1_root,
            session=CapitalizerSession(args.session),
        )
        write_market(report, rows, args.output)
        print(
            json.dumps(
                {
                    "symbol": report["symbol"],
                    "session": report["session"],
                    "closeback_rows": report["closeback_rows"],
                    "v3_executable_raw": report["v3_executable_raw"],
                    "n2_delayed_executable_raw": report[
                        "n2_delayed_executable_raw"
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
