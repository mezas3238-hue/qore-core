"""2Y diagnostic atlas for V3 CISD boundary availability.

For every frozen V3 M5 closeback, this atlas scans the original N+1 M3 window and
identifies bars that already satisfy all non-CISD M3 requirements:
direction + swing break + body>=60% + range>1.2*ATR.

It then measures whether the V3 opposing-series CISD boundary is calculable on those
bars, why it is unavailable, and whether a later non-CISD-ready bar in the same N+1
eventually obtains a boundary.

Diagnostic only. No V3 admission rule is changed.
"""

from __future__ import annotations

import argparse
import bisect
import json
from collections import Counter
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any

from qore.infrastructure.trader_lab import (
    capitalizer_owner_h1_m3_m1_causal_reversal_1y_v3 as v3,
)
from qore.infrastructure.trader_lab.capitalizer_cibo_m1_reader_v1 import iter_cibo_m1
from qore.infrastructure.trader_lab.capitalizer_exposure_graph import CapitalizerSide
from qore.infrastructure.trader_lab.capitalizer_m3_mss_bottleneck_forensics_2y_v1 import (
    IDENTITY as BOTTLENECK_IDENTITY,
)
from qore.infrastructure.trader_lab.capitalizer_m3_mss_bottleneck_forensics_2y_v1 import (
    LOOKBACK_START,
    WINDOW_END,
)
from qore.infrastructure.trader_lab.capitalizer_strict_htf_gate_1y_v1 import (
    _aggregate_tf,
    _pivots,
)
from qore.infrastructure.trader_lab.capitalizer_v3_m5_directional_state_v1 import (
    CapitalizerM5DirectionalState,
    classify_m5_directional_state,
)

IDENTITY = "QORE_CAPITALIZER_V3_CISD_BOUNDARY_AVAILABILITY_ATLAS_2Y_V1"
MATRIX_IDENTITY = (
    "QORE_CAPITALIZER_NINE_MARKET_V3_CISD_BOUNDARY_AVAILABILITY_ATLAS_2Y_V1"
)
EXPECTED_CLOSEBACKS = 8099


@dataclass(frozen=True, slots=True)
class BoundaryAvailabilityRow:
    symbol: str
    session: str
    operating_date: str
    closeback_at: str
    h1_deadline: str
    side: str
    liquidity_source: str
    original_first_blocker: str
    original_valid_m3_within_h1: bool
    m5_state: str
    non_cisd_ready_bars: int
    boundary_available_bars: int
    boundary_missing_bars: int
    cisd_break_bars: int
    first_non_cisd_ready_at: str | None
    first_ready_boundary_available: bool | None
    first_ready_previous_bar_relation: str | None
    first_ready_opposing_run_length: int | None
    first_boundary_available_at: str | None
    boundary_missing_on_all_ready_bars: bool
    later_boundary_recovered_within_n1: bool
    outcome_used_for_admission: bool = False


def _load_bottleneck_rows(root: Path) -> tuple[dict[str, Any], ...]:
    summaries = sorted(
        root.rglob("capitalizer-*-m3-mss-bottleneck-forensics-2y-v1.json")
    )
    ledgers = sorted(
        root.rglob(
            "capitalizer-*-m3-mss-bottleneck-forensics-2y-v1-closebacks.jsonl"
        )
    )
    if len(summaries) != 1 or len(ledgers) != 1:
        raise ValueError("boundary atlas requires one bottleneck market artifact")
    summary = json.loads(summaries[0].read_text(encoding="utf-8"))
    if summary.get("identity") != BOTTLENECK_IDENTITY:
        raise ValueError("unexpected bottleneck identity")
    rows: list[dict[str, Any]] = []
    with ledgers[0].open(encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                raw = json.loads(line)
                if not isinstance(raw, dict):
                    raise ValueError("bottleneck row must be object")
                rows.append(raw)
    return tuple(rows)


def _load_m5_states(
    root: Path,
) -> dict[tuple[str, str], CapitalizerM5DirectionalState]:
    paths = sorted(
        root.rglob("capitalizer-*-v3-m3-microstructure-context-2y-v1-rows.jsonl")
    )
    if len(paths) != 1:
        raise ValueError("boundary atlas requires one microstructure ledger")
    result: dict[tuple[str, str], CapitalizerM5DirectionalState] = {}
    with paths[0].open(encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            raw = json.loads(line)
            if not isinstance(raw, dict):
                raise ValueError("microstructure row must be object")
            key = (str(raw["closeback_at"]), str(raw["side"]))
            result[key] = classify_m5_directional_state(
                side=CapitalizerSide(str(raw["side"])),
                microstructure_signature=str(raw["microstructure_signature"]),
            )
    return result


def _non_cisd_ready(
    bars: Any,
    pivots: Any,
    *,
    index: int,
    side: CapitalizerSide,
) -> bool:
    source = bars[index].source
    full_range = source.high - source.low
    if full_range <= 0:
        return False
    directional = (
        source.close > source.open
        if side is CapitalizerSide.LONG
        else source.close < source.open
    )
    if not directional:
        return False
    body_ratio = abs(source.close - source.open) / full_range
    if body_ratio < v3.BODY_RATIO_MIN:
        return False
    atr = v3._atr14(bars, index)
    if atr is None or full_range <= v3.ATR_MULTIPLIER * atr:
        return False
    break_kind = "HIGH" if side is CapitalizerSide.LONG else "LOW"
    broken = v3._latest_pivot(
        pivots,
        before=bars[index].opened_at,
        kind=break_kind,
    )
    if broken is None:
        return False
    return bool(
        source.close > broken.price
        if side is CapitalizerSide.LONG
        else source.close < broken.price
    )


def _previous_relation(
    bars: Any,
    *,
    index: int,
    side: CapitalizerSide,
) -> str:
    if index <= 0:
        return "NO_PREVIOUS_BAR"
    source = bars[index - 1].source
    if source.close == source.open:
        return "DOJI"
    opposing = (
        source.close < source.open
        if side is CapitalizerSide.LONG
        else source.close > source.open
    )
    return "OPPOSING" if opposing else "SAME_DIRECTION"


def _opposing_run_length(
    bars: Any,
    *,
    index: int,
    side: CapitalizerSide,
) -> int:
    length = 0
    current = index - 1
    while current >= 0:
        source = bars[current].source
        opposing = (
            source.close < source.open
            if side is CapitalizerSide.LONG
            else source.close > source.open
        )
        if not opposing:
            break
        length += 1
        current -= 1
    return length


def build_market_report(
    bottleneck_root: Path,
    micro_root: Path,
    m1_root: Path,
) -> tuple[dict[str, Any], tuple[BoundaryAvailabilityRow, ...]]:
    diagnostics = _load_bottleneck_rows(bottleneck_root)
    states = _load_m5_states(micro_root)
    native = tuple(
        bar
        for bar in iter_cibo_m1(m1_root)
        if LOOKBACK_START <= bar.opened_at < WINDOW_END + timedelta(days=1)
    )
    if not native:
        raise ValueError("boundary atlas found no native M1")
    symbol = native[0].symbol
    m3 = _aggregate_tf(native, minutes=3)
    closes = tuple(item.closed_at for item in m3)
    pivots = _pivots(m3)

    rows: list[BoundaryAvailabilityRow] = []
    for raw in diagnostics:
        after = datetime.fromisoformat(str(raw["closeback_at"]))
        before = datetime.fromisoformat(str(raw["h1_deadline"]))
        side = CapitalizerSide(str(raw["side"]))
        state = states.get((after.isoformat(), side.value))
        if state is None:
            raise ValueError("missing M5 state in boundary atlas")

        start = bisect.bisect_right(closes, after)
        end = bisect.bisect_right(closes, before)
        ready_indices: list[int] = []
        available_indices: list[int] = []
        missing_indices: list[int] = []
        cisd_break_indices: list[int] = []
        for index in range(start, end):
            if not _non_cisd_ready(m3, pivots, index=index, side=side):
                continue
            ready_indices.append(index)
            boundary = v3._opposing_series_boundary(
                m3,
                index=index,
                side=side,
            )
            if boundary is None:
                missing_indices.append(index)
                continue
            available_indices.append(index)
            source = m3[index].source
            cisd_break = (
                source.close > boundary
                if side is CapitalizerSide.LONG
                else source.close < boundary
            )
            if cisd_break:
                cisd_break_indices.append(index)

        first_index = ready_indices[0] if ready_indices else None
        first_available = (
            first_index in set(available_indices)
            if first_index is not None
            else None
        )
        later_recovered = bool(
            first_index is not None
            and first_available is False
            and any(index > first_index for index in available_indices)
        )
        rows.append(
            BoundaryAvailabilityRow(
                symbol=symbol,
                session=str(raw["session"]),
                operating_date=str(raw["operating_date"]),
                closeback_at=after.isoformat(),
                h1_deadline=before.isoformat(),
                side=side.value,
                liquidity_source=str(raw["liquidity_source"]),
                original_first_blocker=str(raw["first_blocker"]),
                original_valid_m3_within_h1=bool(raw["valid_m3_within_h1"]),
                m5_state=state.value,
                non_cisd_ready_bars=len(ready_indices),
                boundary_available_bars=len(available_indices),
                boundary_missing_bars=len(missing_indices),
                cisd_break_bars=len(cisd_break_indices),
                first_non_cisd_ready_at=(
                    None
                    if first_index is None
                    else m3[first_index].closed_at.isoformat()
                ),
                first_ready_boundary_available=first_available,
                first_ready_previous_bar_relation=(
                    None
                    if first_index is None
                    else _previous_relation(
                        m3,
                        index=first_index,
                        side=side,
                    )
                ),
                first_ready_opposing_run_length=(
                    None
                    if first_index is None
                    else _opposing_run_length(
                        m3,
                        index=first_index,
                        side=side,
                    )
                ),
                first_boundary_available_at=(
                    None
                    if not available_indices
                    else m3[available_indices[0]].closed_at.isoformat()
                ),
                boundary_missing_on_all_ready_bars=bool(
                    ready_indices and not available_indices
                ),
                later_boundary_recovered_within_n1=later_recovered,
            )
        )

    ordered = tuple(sorted(rows, key=lambda item: item.closeback_at))
    with_ready = tuple(item for item in ordered if item.non_cisd_ready_bars > 0)
    first_missing = tuple(
        item
        for item in with_ready
        if item.first_ready_boundary_available is False
    )
    all_missing = tuple(
        item for item in with_ready if item.boundary_missing_on_all_ready_bars
    )
    relation_counts = Counter(
        item.first_ready_previous_bar_relation
        for item in with_ready
        if item.first_ready_previous_bar_relation is not None
    )
    blocker_all_missing = Counter(
        item.original_first_blocker for item in all_missing
    )
    state_all_missing = Counter(item.m5_state for item in all_missing)

    report = {
        "identity": IDENTITY,
        "symbol": symbol,
        "session": ordered[0].session if ordered else None,
        "closebacks": len(ordered),
        "closebacks_with_non_cisd_ready_bar": len(with_ready),
        "first_ready_boundary_missing": len(first_missing),
        "boundary_missing_on_all_ready_bars": len(all_missing),
        "later_boundary_recovered_within_n1": sum(
            item.later_boundary_recovered_within_n1 for item in ordered
        ),
        "first_ready_previous_bar_relation": dict(
            sorted(relation_counts.items())
        ),
        "all_ready_boundary_missing_by_first_blocker": dict(
            sorted(blocker_all_missing.items())
        ),
        "all_ready_boundary_missing_by_m5_state": dict(
            sorted(state_all_missing.items())
        ),
        "strategy_mutated": False,
        "outcome_used_for_admission": False,
        "diagnostic_only": True,
        "economic_candidate": False,
    }
    return report, ordered


def write_market(
    report: dict[str, Any],
    rows: tuple[BoundaryAvailabilityRow, ...],
    output: Path,
) -> None:
    output.mkdir(parents=True, exist_ok=True)
    symbol = str(report["symbol"]).lower()
    stem = f"capitalizer-{symbol}-v3-cisd-boundary-availability-atlas-2y-v1"
    (output / f"{stem}.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    with (output / f"{stem}-rows.jsonl").open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(asdict(row), sort_keys=True) + "\n")


def _load_reports(root: Path) -> list[dict[str, Any]]:
    paths = sorted(
        root.rglob("capitalizer-*-v3-cisd-boundary-availability-atlas-2y-v1.json")
    )
    if len(paths) != 9:
        raise ValueError(f"boundary atlas matrix requires 9 reports, got {len(paths)}")
    return [dict(json.loads(path.read_text(encoding="utf-8"))) for path in paths]


def _sum_nested(
    reports: list[dict[str, Any]],
    key: str,
) -> dict[str, int]:
    counter: Counter[str] = Counter()
    for report in reports:
        raw = report[key]
        if not isinstance(raw, dict):
            raise ValueError(f"{key} must be mapping")
        for name, value in raw.items():
            counter[str(name)] += int(value)
    return dict(sorted(counter.items()))


def build_matrix(root: Path) -> dict[str, Any]:
    reports = _load_reports(root)
    closebacks = sum(int(item["closebacks"]) for item in reports)
    with_ready = sum(
        int(item["closebacks_with_non_cisd_ready_bar"]) for item in reports
    )
    first_missing = sum(
        int(item["first_ready_boundary_missing"]) for item in reports
    )
    all_missing = sum(
        int(item["boundary_missing_on_all_ready_bars"]) for item in reports
    )
    later_recovered = sum(
        int(item["later_boundary_recovered_within_n1"]) for item in reports
    )
    per_session: dict[str, Counter[str]] = {}
    for report in reports:
        session = str(report["session"])
        counter = per_session.setdefault(session, Counter())
        for key in (
            "closebacks",
            "closebacks_with_non_cisd_ready_bar",
            "first_ready_boundary_missing",
            "boundary_missing_on_all_ready_bars",
            "later_boundary_recovered_within_n1",
        ):
            counter[key] += int(report[key])

    return {
        "identity": MATRIX_IDENTITY,
        "market_count": 9,
        "closebacks": closebacks,
        "closeback_control_reproduced": closebacks == EXPECTED_CLOSEBACKS,
        "closebacks_with_non_cisd_ready_bar": with_ready,
        "first_ready_boundary_missing": first_missing,
        "first_ready_boundary_missing_rate": (
            None
            if with_ready == 0
            else str(Decimal(first_missing) / Decimal(with_ready))
        ),
        "boundary_missing_on_all_ready_bars": all_missing,
        "boundary_missing_on_all_ready_bars_rate": (
            None
            if with_ready == 0
            else str(Decimal(all_missing) / Decimal(with_ready))
        ),
        "later_boundary_recovered_within_n1": later_recovered,
        "first_ready_previous_bar_relation": _sum_nested(
            reports,
            "first_ready_previous_bar_relation",
        ),
        "all_ready_boundary_missing_by_first_blocker": _sum_nested(
            reports,
            "all_ready_boundary_missing_by_first_blocker",
        ),
        "all_ready_boundary_missing_by_m5_state": _sum_nested(
            reports,
            "all_ready_boundary_missing_by_m5_state",
        ),
        "per_session": {
            key: dict(value) for key, value in sorted(per_session.items())
        },
        "markets": sorted(reports, key=lambda item: str(item["symbol"])),
        "strategy_mutated": False,
        "outcome_used_for_admission": False,
        "diagnostic_only": True,
        "economic_candidate": False,
    }


def write_matrix(report: dict[str, Any], output: Path) -> None:
    output.mkdir(parents=True, exist_ok=True)
    path = (
        output
        / "capitalizer-nine-market-v3-cisd-boundary-availability-atlas-2y-v1.json"
    )
    path.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    market = sub.add_parser("market")
    market.add_argument("bottleneck_root", type=Path)
    market.add_argument("micro_root", type=Path)
    market.add_argument("m1_root", type=Path)
    market.add_argument("output", type=Path)
    matrix = sub.add_parser("matrix")
    matrix.add_argument("input_root", type=Path)
    matrix.add_argument("output", type=Path)
    args = parser.parse_args()

    if args.command == "market":
        report, rows = build_market_report(
            args.bottleneck_root,
            args.micro_root,
            args.m1_root,
        )
        write_market(report, rows, args.output)
        print(json.dumps(report, sort_keys=True))
        return

    report = build_matrix(args.input_root)
    write_matrix(report, args.output)
    print(json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    main()
