"""Outcome-free anatomy of SOURCE_FIRST + WAIT5 invalid stop geometry.

Frozen population: the 111 STOP_INVALID_GEOMETRY rows from the completed
SOURCE_FIRST -> WAIT5 funnel atlas.

This diagnostic reconstructs each frozen M3 MSS and M1 fill from immutable native
M1, then compares two already-existing structural semantics without reading PnL:
- V3 stop: buffered broken swing (the pivot that the MSS displaced through);
- strict-HTF protected swing: latest causally confirmed opposite-kind pivot.

No stop rule is changed here. No trade is admitted. No outcome is read.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
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
from qore.infrastructure.trader_lab.capitalizer_contract import CapitalizerSession
from qore.infrastructure.trader_lab.capitalizer_exposure_graph import CapitalizerSide
from qore.infrastructure.trader_lab.capitalizer_strict_htf_gate_1y_v1 import (
    Pivot,
    TFBar,
    _aggregate_tf,
    _index_day_inputs,
    _latest_pivot,
    _pivots,
)
from qore.infrastructure.trader_lab.capitalizer_v3_source_first_cisd_v1 import (
    find_source_first_m3_mss,
)
from qore.infrastructure.trader_lab.capitalizer_v3_source_first_wait5_2y_v1 import (
    WAIT_MINUTES,
    _find_wait5_fill,
)

IDENTITY = (
    "QORE_CAPITALIZER_V3_SOURCE_FIRST_WAIT5_"
    "STOP_INVALID_GEOMETRY_ATLAS_2Y_V1"
)
MATRIX_IDENTITY = (
    "QORE_CAPITALIZER_NINE_MARKET_V3_SOURCE_FIRST_WAIT5_"
    "STOP_INVALID_GEOMETRY_ATLAS_2Y_V1"
)
EXPECTED_INVALID = 111
STOP_INVALID_GEOMETRY = "STOP_INVALID_GEOMETRY"


@dataclass(frozen=True, slots=True)
class StopInvalidGeometryRow:
    symbol: str
    session: str
    operating_date: str
    side: str
    source_first_mss_at: str
    displacement_opened_at: str
    final_fill_at: str
    final_entry_mode: str
    ob_fvg_overlap: bool
    wait5_armed: bool
    entry_price: str
    broken_swing_price: str
    original_stop_price: str
    original_stop_valid: bool
    original_stop_intersected_before_fill: bool
    fill_bar_contains_original_stop: bool
    fill_bar_entirely_beyond_original_stop: bool
    protected_at_mss_present: bool
    protected_at_mss_confirmed_at: str | None
    protected_at_mss_price: str | None
    protected_at_mss_stop_price: str | None
    protected_at_mss_stop_valid: bool | None
    protected_before_fill_present: bool
    protected_before_fill_confirmed_at: str | None
    protected_before_fill_price: str | None
    protected_before_fill_stop_price: str | None
    protected_before_fill_stop_valid: bool | None
    protected_updated_after_mss: bool
    outcome_used_for_classification: bool = False


def _load_invalid_rows(root: Path) -> tuple[dict[str, Any], ...]:
    paths = sorted(
        root.rglob(
            "capitalizer-*-v3-source-first-wait5-funnel-atlas-2y-v1-rows.jsonl"
        )
    )
    if len(paths) != 1:
        raise ValueError("stop-invalid atlas requires one market funnel ledger")
    rows: list[dict[str, Any]] = []
    with paths[0].open(encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            raw = json.loads(line)
            if not isinstance(raw, dict):
                raise ValueError("funnel row must be object")
            if raw.get("terminal_reason") == STOP_INVALID_GEOMETRY:
                rows.append(raw)
    return tuple(rows)


def _buffered_stop(
    *,
    side: CapitalizerSide,
    pivot_price: Decimal,
    buffer_price: Decimal,
) -> Decimal:
    return (
        pivot_price - buffer_price
        if side is CapitalizerSide.LONG
        else pivot_price + buffer_price
    )


def _valid_stop(
    *,
    side: CapitalizerSide,
    entry_price: Decimal,
    stop_price: Decimal,
) -> bool:
    if side is CapitalizerSide.LONG:
        return stop_price < entry_price
    return stop_price > entry_price


def _contains_level(bar: CapitalizerM1Bar, level: Decimal) -> bool:
    return bar.low <= level <= bar.high


def _entirely_beyond_stop(
    bar: CapitalizerM1Bar,
    *,
    side: CapitalizerSide,
    stop_price: Decimal,
) -> bool:
    if side is CapitalizerSide.LONG:
        return bar.high < stop_price
    return bar.low > stop_price


def _protected_pivot(
    pivots: tuple[Pivot, ...],
    *,
    before: datetime,
    side: CapitalizerSide,
) -> Pivot | None:
    kind = "LOW" if side is CapitalizerSide.LONG else "HIGH"
    return _latest_pivot(pivots, before=before, kind=kind)


def _reconstruct_row(
    *,
    raw: dict[str, Any],
    symbol: str,
    session: CapitalizerSession,
    execution: tuple[CapitalizerM1Bar, ...],
    m3: tuple[TFBar, ...],
    m3_closes: tuple[datetime, ...],
    m3_pivots: tuple[Pivot, ...],
    buffer_price: Decimal,
) -> StopInvalidGeometryRow:
    side = CapitalizerSide(str(raw["side"]))
    sweep_at = datetime.fromisoformat(str(raw["sweep_at"]))
    closeback_at = datetime.fromisoformat(str(raw["closeback_at"]))
    deadline = datetime.fromisoformat(str(raw["h1_deadline"]))
    frozen_mss_at = datetime.fromisoformat(str(raw["source_first_mss_at"]))

    event = find_source_first_m3_mss(
        m3,
        m3_closes,
        m3_pivots,
        sweep_at=sweep_at,
        after=closeback_at,
        before=deadline,
        side=side,
    )
    if event is None or event.confirmed_at != frozen_mss_at:
        raise ValueError("SOURCE_FIRST MSS reconstruction mismatch")

    zone = v3._m1_causal_zone(execution, event=event)
    if zone is None:
        raise ValueError("frozen stop-invalid row lost causal FVG")

    overlap = zone.overlap_low is not None and zone.overlap_high is not None
    normal_fill = v3._find_m1_fill(
        execution,
        event=event,
        zone=zone,
        deadline=deadline,
    )
    if normal_fill is None:
        raise ValueError("frozen stop-invalid row lost normal fill")

    normal_index, normal_price, normal_mode = normal_fill
    original_stop = _buffered_stop(
        side=side,
        pivot_price=event.broken_swing_price,
        buffer_price=buffer_price,
    )
    eligible_at = event.confirmed_at + timedelta(minutes=WAIT_MINUTES)
    wait_required = not overlap and execution[normal_index].opened_at < eligible_at

    final_index = normal_index
    final_price = normal_price
    final_mode = normal_mode
    if wait_required:
        wait_fill, wait_status = _find_wait5_fill(
            execution,
            event=event,
            zone=zone,
            stop_price=original_stop,
            deadline=deadline,
        )
        if wait_fill is None:
            raise ValueError(
                "frozen stop-invalid row unexpectedly lost WAIT5 refill: "
                f"{wait_status}"
            )
        final_index, final_price, final_mode = wait_fill

    frozen_fill_at = datetime.fromisoformat(str(raw["final_fill_at"]))
    frozen_mode = str(raw["final_entry_mode"])
    fill_bar = execution[final_index]
    if fill_bar.opened_at != frozen_fill_at or final_mode != frozen_mode:
        raise ValueError("frozen stop-invalid fill reconstruction mismatch")

    original_valid = _valid_stop(
        side=side,
        entry_price=final_price,
        stop_price=original_stop,
    )
    if original_valid:
        raise ValueError("frozen STOP_INVALID_GEOMETRY reconstructed as valid")

    protected_at_mss = _protected_pivot(
        m3_pivots,
        before=event.displacement_opened_at,
        side=side,
    )
    protected_before_fill = _protected_pivot(
        m3_pivots,
        before=fill_bar.opened_at,
        side=side,
    )

    def pivot_fields(
        pivot: Pivot | None,
    ) -> tuple[str | None, str | None, str | None, bool | None]:
        if pivot is None:
            return None, None, None, None
        stop = _buffered_stop(
            side=side,
            pivot_price=pivot.price,
            buffer_price=buffer_price,
        )
        return (
            pivot.confirmed_at.isoformat(),
            str(pivot.price),
            str(stop),
            _valid_stop(
                side=side,
                entry_price=final_price,
                stop_price=stop,
            ),
        )

    (
        mss_protected_at,
        mss_protected_price,
        mss_protected_stop,
        mss_protected_valid,
    ) = pivot_fields(protected_at_mss)
    (
        fill_protected_at,
        fill_protected_price,
        fill_protected_stop,
        fill_protected_valid,
    ) = pivot_fields(protected_before_fill)

    prefill_bars = tuple(
        bar
        for bar in execution
        if event.confirmed_at <= bar.opened_at < fill_bar.opened_at
    )
    intersected_before_fill = any(
        _contains_level(bar, original_stop) for bar in prefill_bars
    )

    return StopInvalidGeometryRow(
        symbol=symbol,
        session=session.value,
        operating_date=str(raw["operating_date"]),
        side=side.value,
        source_first_mss_at=event.confirmed_at.isoformat(),
        displacement_opened_at=event.displacement_opened_at.isoformat(),
        final_fill_at=fill_bar.opened_at.isoformat(),
        final_entry_mode=final_mode,
        ob_fvg_overlap=overlap,
        wait5_armed=wait_required,
        entry_price=str(final_price),
        broken_swing_price=str(event.broken_swing_price),
        original_stop_price=str(original_stop),
        original_stop_valid=original_valid,
        original_stop_intersected_before_fill=intersected_before_fill,
        fill_bar_contains_original_stop=_contains_level(fill_bar, original_stop),
        fill_bar_entirely_beyond_original_stop=_entirely_beyond_stop(
            fill_bar,
            side=side,
            stop_price=original_stop,
        ),
        protected_at_mss_present=protected_at_mss is not None,
        protected_at_mss_confirmed_at=mss_protected_at,
        protected_at_mss_price=mss_protected_price,
        protected_at_mss_stop_price=mss_protected_stop,
        protected_at_mss_stop_valid=mss_protected_valid,
        protected_before_fill_present=protected_before_fill is not None,
        protected_before_fill_confirmed_at=fill_protected_at,
        protected_before_fill_price=fill_protected_price,
        protected_before_fill_stop_price=fill_protected_stop,
        protected_before_fill_stop_valid=fill_protected_valid,
        protected_updated_after_mss=(
            protected_at_mss is not None
            and protected_before_fill is not None
            and protected_before_fill.confirmed_at
            > protected_at_mss.confirmed_at
        ),
    )


def build_market_report(
    funnel_root: Path,
    m1_root: Path,
    *,
    session: CapitalizerSession,
) -> tuple[dict[str, Any], tuple[StopInvalidGeometryRow, ...]]:
    frozen = _load_invalid_rows(funnel_root)
    if not frozen:
        raise ValueError("stop-invalid atlas found no frozen invalid rows")

    first_time = min(
        datetime.fromisoformat(str(row["source_first_mss_at"])) for row in frozen
    )
    last_time = max(
        datetime.fromisoformat(str(row["h1_deadline"])) for row in frozen
    )
    all_bars = tuple(
        bar
        for bar in iter_cibo_m1(m1_root)
        if first_time - timedelta(days=21)
        <= bar.opened_at
        <= last_time + timedelta(minutes=5)
    )
    if not all_bars:
        raise ValueError("stop-invalid atlas found no native M1")

    symbol = all_bars[0].symbol
    if any(bar.symbol != symbol for bar in all_bars):
        raise ValueError("stop-invalid atlas requires one symbol")
    if any(str(row["symbol"]) != symbol for row in frozen):
        raise ValueError("funnel/M1 symbol mismatch")

    m3 = _aggregate_tf(all_bars, minutes=3)
    m3_closes = tuple(bar.closed_at for bar in m3)
    m3_pivots = _pivots(m3)
    execution_by_day, _ = _index_day_inputs(all_bars, session=session)
    buffer_price = v3._stop_buffer(all_bars)

    rows: list[StopInvalidGeometryRow] = []
    for raw in frozen:
        operating_date = str(raw["operating_date"])
        execution = execution_by_day.get(operating_date, ())
        if not execution:
            raise ValueError("stop-invalid atlas missing execution bars")
        rows.append(
            _reconstruct_row(
                raw=raw,
                symbol=symbol,
                session=session,
                execution=execution,
                m3=m3,
                m3_closes=m3_closes,
                m3_pivots=m3_pivots,
                buffer_price=buffer_price,
            )
        )

    ordered = tuple(
        sorted(rows, key=lambda item: (item.final_fill_at, item.symbol))
    )
    by_mode = Counter(item.final_entry_mode for item in ordered)
    return {
        "identity": IDENTITY,
        "symbol": symbol,
        "session": session.value,
        "stop_invalid_geometry": len(ordered),
        "original_stop_valid": sum(item.original_stop_valid for item in ordered),
        "original_stop_intersected_before_fill": sum(
            item.original_stop_intersected_before_fill for item in ordered
        ),
        "fill_bar_contains_original_stop": sum(
            item.fill_bar_contains_original_stop for item in ordered
        ),
        "fill_bar_entirely_beyond_original_stop": sum(
            item.fill_bar_entirely_beyond_original_stop for item in ordered
        ),
        "protected_at_mss_present": sum(
            item.protected_at_mss_present for item in ordered
        ),
        "protected_at_mss_stop_valid": sum(
            item.protected_at_mss_stop_valid is True for item in ordered
        ),
        "protected_before_fill_present": sum(
            item.protected_before_fill_present for item in ordered
        ),
        "protected_before_fill_stop_valid": sum(
            item.protected_before_fill_stop_valid is True for item in ordered
        ),
        "protected_updated_after_mss": sum(
            item.protected_updated_after_mss for item in ordered
        ),
        "overlap_true": sum(item.ob_fvg_overlap for item in ordered),
        "wait5_armed": sum(item.wait5_armed for item in ordered),
        "entry_modes": dict(sorted(by_mode.items())),
        "protected_swing_semantics": (
            "STRICT_HTF_LATEST_OPPOSITE_PIVOT_CONFIRMED_BEFORE_DISPLACEMENT"
        ),
        "same_v3_buffer_applied_to_protected_counterfactual": True,
        "outcome_fields_read": False,
        "outcome_used_for_classification": False,
        "strategy_mutated": False,
        "diagnostic_only": True,
        "economic_candidate": False,
        "rule_promotion_allowed": False,
    }, ordered


def write_market(
    report: dict[str, Any],
    rows: tuple[StopInvalidGeometryRow, ...],
    output: Path,
) -> None:
    output.mkdir(parents=True, exist_ok=True)
    symbol = str(report["symbol"]).lower()
    stem = (
        f"capitalizer-{symbol}-v3-source-first-wait5-"
        "stop-invalid-geometry-atlas-2y-v1"
    )
    (output / f"{stem}.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    with (output / f"{stem}-rows.jsonl").open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(asdict(row), sort_keys=True) + "\n")


def _load_reports(root: Path) -> list[dict[str, Any]]:
    paths = sorted(
        root.rglob(
            "capitalizer-*-v3-source-first-wait5-"
            "stop-invalid-geometry-atlas-2y-v1.json"
        )
    )
    if len(paths) != 9:
        raise ValueError(f"stop-invalid matrix requires 9 reports, got {len(paths)}")
    return [dict(json.loads(path.read_text(encoding="utf-8"))) for path in paths]


def build_matrix(root: Path) -> dict[str, Any]:
    reports = _load_reports(root)
    total = sum(int(report["stop_invalid_geometry"]) for report in reports)
    modes: Counter[str] = Counter()
    per_session: dict[str, Counter[str]] = defaultdict(Counter)

    for report in reports:
        for key, value in dict(report["entry_modes"]).items():
            modes[str(key)] += int(value)
        bucket = per_session[str(report["session"])]
        for key in (
            "stop_invalid_geometry",
            "original_stop_intersected_before_fill",
            "fill_bar_contains_original_stop",
            "fill_bar_entirely_beyond_original_stop",
            "protected_at_mss_present",
            "protected_at_mss_stop_valid",
            "protected_before_fill_present",
            "protected_before_fill_stop_valid",
            "protected_updated_after_mss",
            "overlap_true",
            "wait5_armed",
        ):
            bucket[key] += int(report[key])

    def summed(key: str) -> int:
        return sum(int(report[key]) for report in reports)

    return {
        "identity": MATRIX_IDENTITY,
        "market_count": 9,
        "stop_invalid_geometry": total,
        "stop_invalid_control_reproduced": total == EXPECTED_INVALID,
        "original_stop_valid": summed("original_stop_valid"),
        "original_stop_intersected_before_fill": summed(
            "original_stop_intersected_before_fill"
        ),
        "fill_bar_contains_original_stop": summed(
            "fill_bar_contains_original_stop"
        ),
        "fill_bar_entirely_beyond_original_stop": summed(
            "fill_bar_entirely_beyond_original_stop"
        ),
        "protected_at_mss_present": summed("protected_at_mss_present"),
        "protected_at_mss_stop_valid": summed("protected_at_mss_stop_valid"),
        "protected_before_fill_present": summed("protected_before_fill_present"),
        "protected_before_fill_stop_valid": summed(
            "protected_before_fill_stop_valid"
        ),
        "protected_updated_after_mss": summed("protected_updated_after_mss"),
        "overlap_true": summed("overlap_true"),
        "wait5_armed": summed("wait5_armed"),
        "entry_modes": dict(sorted(modes.items())),
        "per_session": {
            key: dict(sorted(value.items()))
            for key, value in sorted(per_session.items())
        },
        "markets": sorted(reports, key=lambda item: str(item["symbol"])),
        "protected_swing_semantics": (
            "STRICT_HTF_LATEST_OPPOSITE_PIVOT_CONFIRMED_BEFORE_DISPLACEMENT"
        ),
        "same_v3_buffer_applied_to_protected_counterfactual": True,
        "outcome_fields_read": False,
        "outcome_used_for_classification": False,
        "strategy_mutated": False,
        "diagnostic_only": True,
        "economic_candidate": False,
        "rule_promotion_allowed": False,
        "fresh_holdout_claimed": False,
        "live_authorized": False,
        "real_capital_authorized": False,
    }


def write_matrix(report: dict[str, Any], output: Path) -> None:
    output.mkdir(parents=True, exist_ok=True)
    path = output / (
        "capitalizer-nine-market-v3-source-first-wait5-"
        "stop-invalid-geometry-atlas-2y-v1.json"
    )
    path.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)

    market = sub.add_parser("market")
    market.add_argument("funnel_root", type=Path)
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
            args.funnel_root,
            args.m1_root,
            session=CapitalizerSession(args.session),
        )
        write_market(report, rows, args.output)
        print(json.dumps(report, sort_keys=True))
        return

    report = build_matrix(args.input_root)
    write_matrix(report, args.output)
    print(json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    main()
