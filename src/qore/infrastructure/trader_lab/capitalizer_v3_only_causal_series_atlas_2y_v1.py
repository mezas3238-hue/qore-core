"""Outcome-free anatomy of the 87 V3-only MSS lost by SOURCE_FIRST.

Population is frozen from the completed CISD boundary-semantics census:
SOURCE_FIRST relation vs V3 == LOSES_V3_MSS.

This atlas does not add V3 OR SOURCE_FIRST. It explains why CURRENT_V3 can
confirm while SOURCE_FIRST cannot by reconstructing the immediate opposing M3
series at the exact frozen V3 confirmation.

Key causal distinction:
- SOURCE_BOUNDARY_NOT_YET_AVAILABLE: CURRENT_V3 is using an immediate opposing
  series before SOURCE_FIRST has established a post-sweep causal boundary.
- NEW_POST_SWEEP_SERIES_RESET: SOURCE_FIRST already has its original post-sweep
  boundary, but CURRENT_V3 is using a later immediate opposing series whose
  boundary is different. This is a candidate rearm phenomenon, not automatic
  coexistence.
- OTHER_DIVERGENCE: invariant/debug bucket.

No outcomes or future V3/SOURCE_FIRST events are used for classification.
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
from qore.infrastructure.trader_lab.capitalizer_cibo_m1_reader_v1 import (
    iter_cibo_m1,
)
from qore.infrastructure.trader_lab.capitalizer_exposure_graph import CapitalizerSide
from qore.infrastructure.trader_lab.capitalizer_strict_htf_gate_1y_v1 import (
    TFBar,
    _aggregate_tf,
)

IDENTITY = "QORE_CAPITALIZER_V3_ONLY_CAUSAL_SERIES_ATLAS_2Y_V1"
MATRIX_IDENTITY = "QORE_CAPITALIZER_NINE_MARKET_V3_ONLY_CAUSAL_SERIES_ATLAS_2Y_V1"
EXPECTED_V3_ONLY = 87

SOURCE_NOT_AVAILABLE = "SOURCE_BOUNDARY_NOT_YET_AVAILABLE"
NEW_POST_SWEEP_RESET = "NEW_POST_SWEEP_SERIES_RESET"
OTHER_DIVERGENCE = "OTHER_DIVERGENCE"


@dataclass(frozen=True, slots=True)
class V3OnlyCausalSeriesRow:
    symbol: str
    session: str
    operating_date: str
    side: str
    sweep_at: str
    closeback_at: str
    h1_deadline: str
    current_v3_mss_at: str
    m5_state: str
    current_v3_boundary: str
    immediate_series_started_at: str
    immediate_series_ended_at: str
    immediate_series_bars: int
    immediate_series_vs_sweep: str
    source_first_boundary: str | None
    source_first_boundary_started_at: str | None
    source_boundary_available_at_v3: bool
    current_close_crosses_source_boundary: bool | None
    current_boundary_vs_source: str | None
    boundary_gap_atr: str | None
    source_to_immediate_series_minutes: int | None
    causal_class: str
    outcome_used_for_classification: bool = False
    future_event_used_for_classification: bool = False


def _load_v3_only(root: Path) -> tuple[dict[str, Any], ...]:
    paths = sorted(
        root.rglob(
            "capitalizer-*-v3-cisd-boundary-semantics-census-2y-v1-rows.jsonl"
        )
    )
    if len(paths) != 1:
        raise ValueError("V3-only atlas requires one semantics ledger")
    rows: list[dict[str, Any]] = []
    with paths[0].open(encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            raw = json.loads(line)
            if not isinstance(raw, dict):
                raise ValueError("semantics row must be object")
            if raw.get("source_first_relation_vs_v3") == "LOSES_V3_MSS":
                if raw.get("current_v3_mss_at") is None:
                    raise ValueError("V3-only row missing CURRENT_V3 confirmation")
                if raw.get("source_first_mss_at") is not None:
                    raise ValueError("V3-only row unexpectedly has SOURCE_FIRST MSS")
                rows.append(raw)
    return tuple(rows)


def _is_opposing(bar: TFBar, side: CapitalizerSide) -> bool:
    source = bar.source
    return bool(
        source.close < source.open
        if side is CapitalizerSide.LONG
        else source.close > source.open
    )


def _immediate_series(
    bars: tuple[TFBar, ...],
    *,
    index: int,
    side: CapitalizerSide,
) -> tuple[TFBar, ...]:
    selected: list[TFBar] = []
    current = index - 1
    while current >= 0 and _is_opposing(bars[current], side):
        selected.append(bars[current])
        current -= 1
    selected.reverse()
    return tuple(selected)


def _source_first_boundary_at(
    bars: tuple[TFBar, ...],
    closes: tuple[datetime, ...],
    *,
    sweep_at: datetime,
    before_index: int,
    side: CapitalizerSide,
) -> tuple[Decimal, datetime] | None:
    start = bisect.bisect_right(closes, sweep_at)
    for current in range(start, before_index):
        bar = bars[current]
        if _is_opposing(bar, side):
            return bar.source.open, bar.closed_at
    return None


def _series_vs_sweep(
    series: tuple[TFBar, ...],
    *,
    sweep_at: datetime,
) -> str:
    if not series:
        return "NO_IMMEDIATE_SERIES"
    if series[-1].closed_at <= sweep_at:
        return "PRE_SWEEP_ONLY"
    if series[0].opened_at <= sweep_at < series[-1].closed_at:
        return "STRADDLES_SWEEP"
    return "POST_SWEEP_ONLY"


def _breaks(
    close: Decimal,
    boundary: Decimal,
    side: CapitalizerSide,
) -> bool:
    return bool(
        close > boundary
        if side is CapitalizerSide.LONG
        else close < boundary
    )


def _boundary_relation(
    current: Decimal,
    source: Decimal,
    side: CapitalizerSide,
) -> str:
    if current == source:
        return "SAME"
    current_easier = (
        current < source
        if side is CapitalizerSide.LONG
        else current > source
    )
    return "CURRENT_EASIER" if current_easier else "CURRENT_STRICTER"


def _classify(
    *,
    source_started: datetime | None,
    current_mss: datetime,
    immediate_started: datetime,
    current_crosses_source: bool | None,
) -> str:
    if source_started is None or source_started > current_mss:
        return SOURCE_NOT_AVAILABLE
    if (
        immediate_started > source_started
        and current_crosses_source is False
    ):
        return NEW_POST_SWEEP_RESET
    return OTHER_DIVERGENCE


def _build_row(
    raw: dict[str, Any],
    *,
    m3: tuple[TFBar, ...],
    closes: tuple[datetime, ...],
    by_close: dict[datetime, int],
) -> V3OnlyCausalSeriesRow:
    side = CapitalizerSide(str(raw["side"]))
    current_mss = datetime.fromisoformat(str(raw["current_v3_mss_at"]))
    sweep_at = datetime.fromisoformat(str(raw["sweep_at"]))
    index = by_close.get(current_mss)
    if index is None:
        raise ValueError("V3-only confirmation missing from reconstructed M3")

    series = _immediate_series(m3, index=index, side=side)
    if not series:
        raise ValueError("CURRENT_V3 MSS must have immediate opposing series")

    current_boundary = v3._opposing_series_boundary(
        m3,
        index=index,
        side=side,
    )
    if current_boundary is None:
        raise ValueError("CURRENT_V3 MSS lost its immediate boundary")
    close = m3[index].source.close
    if not _breaks(close, current_boundary, side):
        raise ValueError("frozen CURRENT_V3 MSS does not cross reconstructed boundary")

    source_pair = _source_first_boundary_at(
        m3,
        closes,
        sweep_at=sweep_at,
        before_index=index,
        side=side,
    )
    source: Decimal | None = None
    source_started: datetime | None = None
    if source_pair is not None:
        source, source_started = source_pair

    frozen_started_raw = raw.get("source_first_boundary_started_at")
    if frozen_started_raw is not None:
        frozen_started = datetime.fromisoformat(str(frozen_started_raw))
        if frozen_started <= current_mss:
            if source_started != frozen_started:
                raise ValueError(
                    "reconstructed decision-time SOURCE_FIRST boundary mismatch"
                )
        elif source_started is not None:
            raise ValueError(
                "decision-time SOURCE_FIRST boundary exists before frozen future start"
            )

    source_available = (
        source is not None
        and source_started is not None
        and source_started <= current_mss
    )
    crosses_source: bool | None = None
    relation: str | None = None
    gap_atr: str | None = None
    source_to_immediate: int | None = None

    if source_available:
        assert source is not None
        assert source_started is not None
        crosses_source = _breaks(close, source, side)
        relation = _boundary_relation(current_boundary, source, side)
        atr = v3._atr14(m3, index)
        if atr is not None and atr > 0:
            gap_atr = str(abs(current_boundary - source) / atr)
        source_to_immediate = int(
            (series[0].closed_at - source_started).total_seconds() // 60
        )

    causal_class = _classify(
        source_started=source_started,
        current_mss=current_mss,
        immediate_started=series[0].closed_at,
        current_crosses_source=crosses_source,
    )

    return V3OnlyCausalSeriesRow(
        symbol=str(raw["symbol"]),
        session=str(raw["session"]),
        operating_date=str(raw["operating_date"]),
        side=side.value,
        sweep_at=sweep_at.isoformat(),
        closeback_at=str(raw["closeback_at"]),
        h1_deadline=str(raw["h1_deadline"]),
        current_v3_mss_at=current_mss.isoformat(),
        m5_state=str(raw["m5_state"]),
        current_v3_boundary=str(current_boundary),
        immediate_series_started_at=series[0].closed_at.isoformat(),
        immediate_series_ended_at=series[-1].closed_at.isoformat(),
        immediate_series_bars=len(series),
        immediate_series_vs_sweep=_series_vs_sweep(series, sweep_at=sweep_at),
        source_first_boundary=(None if source is None else str(source)),
        source_first_boundary_started_at=(
            None if source_started is None else source_started.isoformat()
        ),
        source_boundary_available_at_v3=source_available,
        current_close_crosses_source_boundary=crosses_source,
        current_boundary_vs_source=relation,
        boundary_gap_atr=gap_atr,
        source_to_immediate_series_minutes=source_to_immediate,
        causal_class=causal_class,
    )


def build_market_report(
    semantics_root: Path,
    m1_root: Path,
) -> tuple[dict[str, Any], tuple[V3OnlyCausalSeriesRow, ...]]:
    frozen = _load_v3_only(semantics_root)
    if not frozen:
        raise ValueError("V3-only atlas found no frozen rows")

    first = min(datetime.fromisoformat(str(row["sweep_at"])) for row in frozen)
    last = max(
        datetime.fromisoformat(str(row["current_v3_mss_at"])) for row in frozen
    )
    native = tuple(
        bar
        for bar in iter_cibo_m1(m1_root)
        if first - timedelta(days=2)
        <= bar.opened_at
        <= last + timedelta(minutes=3)
    )
    if not native:
        raise ValueError("V3-only atlas found no native M1")
    symbol = native[0].symbol
    if any(bar.symbol != symbol for bar in native):
        raise ValueError("V3-only atlas requires one symbol")
    if any(str(row["symbol"]) != symbol for row in frozen):
        raise ValueError("V3-only semantics/M1 symbol mismatch")

    m3 = _aggregate_tf(native, minutes=3)
    closes = tuple(bar.closed_at for bar in m3)
    by_close = {bar.closed_at: index for index, bar in enumerate(m3)}
    rows = tuple(
        sorted(
            (
                _build_row(
                    raw,
                    m3=m3,
                    closes=closes,
                    by_close=by_close,
                )
                for raw in frozen
            ),
            key=lambda item: item.current_v3_mss_at,
        )
    )

    classes = Counter(item.causal_class for item in rows)
    sweep_relation = Counter(item.immediate_series_vs_sweep for item in rows)
    m5_by_class: dict[str, Counter[str]] = {}
    for item in rows:
        m5_by_class.setdefault(item.causal_class, Counter())[item.m5_state] += 1

    return {
        "identity": IDENTITY,
        "symbol": symbol,
        "session": rows[0].session,
        "v3_only_rows": len(rows),
        "causal_classes": dict(sorted(classes.items())),
        "immediate_series_vs_sweep": dict(sorted(sweep_relation.items())),
        "source_boundary_available_at_v3": sum(
            item.source_boundary_available_at_v3 for item in rows
        ),
        "current_close_crosses_source_boundary": sum(
            item.current_close_crosses_source_boundary is True for item in rows
        ),
        "new_post_sweep_series_reset": sum(
            item.causal_class == NEW_POST_SWEEP_RESET for item in rows
        ),
        "m5_state_by_causal_class": {
            key: dict(sorted(value.items()))
            for key, value in sorted(m5_by_class.items())
        },
        "outcome_fields_read": False,
        "outcome_used_for_classification": False,
        "future_event_used_for_classification": False,
        "strategy_mutated": False,
        "diagnostic_only": True,
        "economic_candidate": False,
        "rule_promotion_allowed": False,
    }, rows


def write_market(
    report: dict[str, Any],
    rows: tuple[V3OnlyCausalSeriesRow, ...],
    output: Path,
) -> None:
    output.mkdir(parents=True, exist_ok=True)
    symbol = str(report["symbol"]).lower()
    stem = f"capitalizer-{symbol}-v3-only-causal-series-atlas-2y-v1"
    (output / f"{stem}.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    with (output / f"{stem}-rows.jsonl").open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(asdict(row), sort_keys=True) + "\n")


def _load_reports(root: Path) -> list[dict[str, Any]]:
    paths = sorted(
        root.rglob("capitalizer-*-v3-only-causal-series-atlas-2y-v1.json")
    )
    if len(paths) != 9:
        raise ValueError(f"V3-only matrix requires 9 reports, got {len(paths)}")
    return [dict(json.loads(path.read_text(encoding="utf-8"))) for path in paths]


def build_matrix(root: Path) -> dict[str, Any]:
    reports = _load_reports(root)
    classes: Counter[str] = Counter()
    sweep_relation: Counter[str] = Counter()
    m5_by_class: dict[str, Counter[str]] = {}
    for report in reports:
        for key, value in dict(report["causal_classes"]).items():
            classes[str(key)] += int(value)
        for key, value in dict(report["immediate_series_vs_sweep"]).items():
            sweep_relation[str(key)] += int(value)
        raw_m5 = report["m5_state_by_causal_class"]
        if not isinstance(raw_m5, dict):
            raise ValueError("m5_state_by_causal_class must be mapping")
        for causal_class, mapping in raw_m5.items():
            if not isinstance(mapping, dict):
                raise ValueError("M5 class mapping must be mapping")
            bucket = m5_by_class.setdefault(str(causal_class), Counter())
            for state, count in mapping.items():
                bucket[str(state)] += int(count)

    total = sum(int(report["v3_only_rows"]) for report in reports)
    return {
        "identity": MATRIX_IDENTITY,
        "market_count": 9,
        "v3_only_rows": total,
        "v3_only_control_reproduced": total == EXPECTED_V3_ONLY,
        "causal_classes": dict(sorted(classes.items())),
        "immediate_series_vs_sweep": dict(sorted(sweep_relation.items())),
        "source_boundary_available_at_v3": sum(
            int(report["source_boundary_available_at_v3"]) for report in reports
        ),
        "current_close_crosses_source_boundary": sum(
            int(report["current_close_crosses_source_boundary"]) for report in reports
        ),
        "new_post_sweep_series_reset": sum(
            int(report["new_post_sweep_series_reset"]) for report in reports
        ),
        "m5_state_by_causal_class": {
            key: dict(sorted(value.items()))
            for key, value in sorted(m5_by_class.items())
        },
        "markets": sorted(reports, key=lambda item: str(item["symbol"])),
        "outcome_fields_read": False,
        "outcome_used_for_classification": False,
        "future_event_used_for_classification": False,
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
    path = output / "capitalizer-nine-market-v3-only-causal-series-atlas-2y-v1.json"
    path.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)

    market = sub.add_parser("market")
    market.add_argument("semantics_root", type=Path)
    market.add_argument("m1_root", type=Path)
    market.add_argument("output", type=Path)

    matrix = sub.add_parser("matrix")
    matrix.add_argument("input_root", type=Path)
    matrix.add_argument("output", type=Path)

    args = parser.parse_args()
    if args.command == "market":
        report, rows = build_market_report(
            args.semantics_root,
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
