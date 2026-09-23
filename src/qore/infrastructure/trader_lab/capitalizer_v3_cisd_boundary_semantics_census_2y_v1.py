"""2Y structural census of three existing CISD-boundary semantics.

No outcomes are read and no V3 trading rule is changed.

Semantics compared on the exact frozen V3 closeback population:

CURRENT_V3_IMMEDIATE_EXTREME
    Frozen V3. For each candidate M3, walk backward from the immediately preceding
    M3 while candles are contiguous and opposing. Boundary is max(open) for LONG /
    min(open) for SHORT. If the immediately preceding M3 is not opposing, boundary
    is unavailable.

SOURCE_FIRST_OPPOSING_OPEN
    Source/TTrades-backed semantics. Starting after the actual V3 sweep, the first
    causal opposing candle series establishes a persistent boundary at the opening
    price of the first opposing candle. Subsequent candidate M3 bars may confirm
    through that fixed boundary even when the immediately previous M3 is no longer
    opposing.

PERSISTENT_EXTREME_OPEN
    Existing anticipation-state semantics adapted to the same M3 window. Starting
    after the actual V3 sweep, opposing candles establish a persistent boundary;
    later opposing candles update it to max(open) for LONG / min(open) for SHORT.
    Non-opposing bars do not clear it.

All three require the same V3 non-CISD candidate conditions:
direction + swing break + body>=60% + range>1.2*ATR.
"""

from __future__ import annotations

import argparse
import bisect
import json
from collections import Counter
from dataclasses import asdict, dataclass
from datetime import date, datetime, timedelta
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
from qore.infrastructure.trader_lab.capitalizer_exposure_graph import CapitalizerSide
from qore.infrastructure.trader_lab.capitalizer_full_ict_density_scanner_1y_v1 import (
    _aggregate_h1,
)
from qore.infrastructure.trader_lab.capitalizer_m3_mss_bottleneck_forensics_1y_v1 import (
    _diagnose_closeback,
    _entry_equivalent,
)
from qore.infrastructure.trader_lab.capitalizer_m3_mss_bottleneck_forensics_2y_v1 import (
    IDENTITY as BOTTLENECK_IDENTITY,
)
from qore.infrastructure.trader_lab.capitalizer_m3_mss_bottleneck_forensics_2y_v1 import (
    LOOKBACK_START,
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
from qore.infrastructure.trader_lab.capitalizer_v3_m5_directional_state_v1 import (
    CapitalizerM5DirectionalState,
    classify_m5_directional_state,
)

IDENTITY = "QORE_CAPITALIZER_V3_CISD_BOUNDARY_SEMANTICS_CENSUS_2Y_V1"
MATRIX_IDENTITY = (
    "QORE_CAPITALIZER_NINE_MARKET_V3_CISD_BOUNDARY_SEMANTICS_CENSUS_2Y_V1"
)
EXPECTED_CLOSEBACKS = 8099
EXPECTED_V3_MSS = 1254

CURRENT = "CURRENT_V3_IMMEDIATE_EXTREME"
SOURCE_FIRST = "SOURCE_FIRST_OPPOSING_OPEN"
PERSISTENT_EXTREME = "PERSISTENT_EXTREME_OPEN"


@dataclass(frozen=True, slots=True)
class BoundarySemanticsRow:
    symbol: str
    session: str
    operating_date: str
    closeback_at: str
    sweep_at: str
    h1_deadline: str
    side: str
    liquidity_source: str
    original_first_blocker: str
    m5_state: str
    non_cisd_ready_bars: int
    current_v3_mss_at: str | None
    source_first_mss_at: str | None
    persistent_extreme_mss_at: str | None
    source_first_boundary: str | None
    source_first_boundary_started_at: str | None
    persistent_extreme_boundary_at_confirmation: str | None
    persistent_extreme_boundary_started_at: str | None
    source_first_relation_vs_v3: str
    persistent_extreme_relation_vs_v3: str
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
        raise ValueError("boundary semantics census requires one bottleneck artifact")
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
    if len(rows) != int(summary["m5_closebacks"]):
        raise ValueError("bottleneck row count mismatch")
    return tuple(rows)


def _load_m5_states(
    root: Path,
) -> dict[tuple[str, str], CapitalizerM5DirectionalState]:
    paths = sorted(
        root.rglob("capitalizer-*-v3-m3-microstructure-context-2y-v1-rows.jsonl")
    )
    if len(paths) != 1:
        raise ValueError("boundary semantics census requires one M5 context ledger")
    result: dict[tuple[str, str], CapitalizerM5DirectionalState] = {}
    with paths[0].open(encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            raw = json.loads(line)
            if not isinstance(raw, dict):
                raise ValueError("M5 context row must be object")
            key = (str(raw["closeback_at"]), str(raw["side"]))
            result[key] = classify_m5_directional_state(
                side=CapitalizerSide(str(raw["side"])),
                microstructure_signature=str(raw["microstructure_signature"]),
            )
    return result


def _reconstruct_closebacks(
    *,
    all_bars: tuple[CapitalizerM1Bar, ...],
    session: CapitalizerSession,
) -> dict[str, v3.SweepCloseback]:
    h1 = _aggregate_h1(all_bars)
    h1_swings = v3._build_h1_swings(h1)
    m5 = _aggregate_tf(all_bars, minutes=5)
    m3 = _aggregate_tf(all_bars, minutes=3)
    m5_closes = tuple(item.closed_at for item in m5)
    m3_closes = tuple(item.closed_at for item in m3)
    m3_pivots = _pivots(m3)
    buffer_price = v3._stop_buffer(all_bars)
    execution_by_day, reference_by_day = _index_day_inputs(
        all_bars,
        session=session,
    )

    result: dict[str, v3.SweepCloseback] = {}
    dates = sorted(
        key
        for key in execution_by_day
        if WINDOW_START.date().isoformat()
        <= key
        < WINDOW_END.date().isoformat()
    )
    for value in dates:
        operating_day = date.fromisoformat(value)
        execution = execution_by_day.get(value, ())
        if len(execution) < 15:
            continue
        prior_session = reference_by_day.get(value)
        previous_day = v3._previous_day_range(
            all_bars,
            operating_day=operating_day,
        )
        entry_equivalent_count = 0
        for h1_open, h1_deadline, hour_bars in v3._h1_windows(execution):
            if entry_equivalent_count >= MAX_EXECUTIONS_PER_SESSION:
                break
            levels = v3._liquidity_levels(
                prior_session=prior_session,
                previous_day=previous_day,
                h1_swings=h1_swings,
                hour_open=h1_open,
            )
            if not levels:
                continue
            _, closeback = v3._find_sweep_closeback(
                hour_bars,
                levels=levels,
                m5=m5,
                m5_closes=m5_closes,
                h1_open=h1_open,
                h1_deadline=h1_deadline,
            )
            if closeback is None:
                continue
            key = closeback.closeback_at.isoformat()
            if key in result:
                raise ValueError("duplicate reconstructed closeback timestamp")
            result[key] = closeback

            _, event = _diagnose_closeback(
                symbol=all_bars[0].symbol,
                session=session,
                operating_day=operating_day,
                closeback=closeback,
                m3=m3,
                m3_closes=m3_closes,
                m3_pivots=m3_pivots,
            )
            if event is not None and _entry_equivalent(
                event=event,
                closeback=closeback,
                execution=execution,
                buffer_price=buffer_price,
            ):
                entry_equivalent_count += 1
    return result


def _non_cisd_ready(
    bars: tuple[TFBar, ...],
    pivots: tuple[Pivot, ...],
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


def _opposing(bar: TFBar, side: CapitalizerSide) -> bool:
    source = bar.source
    return bool(
        source.close < source.open
        if side is CapitalizerSide.LONG
        else source.close > source.open
    )


def _breaks(
    *,
    close: Any,
    boundary: Any,
    side: CapitalizerSide,
) -> bool:
    return bool(
        close > boundary
        if side is CapitalizerSide.LONG
        else close < boundary
    )


def _persistent_events(
    bars: tuple[TFBar, ...],
    closes: tuple[datetime, ...],
    pivots: tuple[Pivot, ...],
    *,
    sweep_at: datetime,
    after: datetime,
    before: datetime,
    side: CapitalizerSide,
) -> tuple[
    datetime | None,
    Any | None,
    datetime | None,
    datetime | None,
    Any | None,
    datetime | None,
    int,
]:
    """Return SOURCE_FIRST and PERSISTENT_EXTREME confirmations/boundaries."""
    start = bisect.bisect_right(closes, sweep_at)
    end = bisect.bisect_right(closes, before)

    source_boundary: Any | None = None
    source_started_at: datetime | None = None
    extreme_boundary: Any | None = None
    extreme_started_at: datetime | None = None
    source_confirmed: datetime | None = None
    source_confirmed_boundary: Any | None = None
    extreme_confirmed: datetime | None = None
    extreme_confirmed_boundary: Any | None = None
    non_cisd_ready = 0

    for index in range(start, end):
        bar = bars[index]
        if _opposing(bar, side):
            if source_boundary is None:
                source_boundary = bar.source.open
                source_started_at = bar.closed_at
            if extreme_boundary is None:
                extreme_boundary = bar.source.open
                extreme_started_at = bar.closed_at
            elif side is CapitalizerSide.LONG:
                extreme_boundary = max(extreme_boundary, bar.source.open)
            else:
                extreme_boundary = min(extreme_boundary, bar.source.open)
            continue

        if bar.closed_at <= after:
            continue
        if not _non_cisd_ready(bars, pivots, index=index, side=side):
            continue
        non_cisd_ready += 1

        if (
            source_confirmed is None
            and source_boundary is not None
            and _breaks(
                close=bar.source.close,
                boundary=source_boundary,
                side=side,
            )
        ):
            source_confirmed = bar.closed_at
            source_confirmed_boundary = source_boundary

        if (
            extreme_confirmed is None
            and extreme_boundary is not None
            and _breaks(
                close=bar.source.close,
                boundary=extreme_boundary,
                side=side,
            )
        ):
            extreme_confirmed = bar.closed_at
            extreme_confirmed_boundary = extreme_boundary

    return (
        source_confirmed,
        source_confirmed_boundary,
        source_started_at,
        extreme_confirmed,
        extreme_confirmed_boundary,
        extreme_started_at,
        non_cisd_ready,
    )


def _relation(
    alternative: datetime | None,
    current: datetime | None,
) -> str:
    if alternative is None and current is None:
        return "BOTH_MISSING"
    if alternative is not None and current is None:
        return "RECOVERS_NO_V3_MSS"
    if alternative is None and current is not None:
        return "LOSES_V3_MSS"
    if alternative == current:
        return "SAME_CONFIRMATION"
    if alternative is not None and current is not None and alternative < current:
        return "PREEMPTS_V3_MSS"
    return "LATER_THAN_V3_MSS"


def build_market_report(
    bottleneck_root: Path,
    micro_root: Path,
    m1_root: Path,
    *,
    session: CapitalizerSession,
) -> tuple[dict[str, Any], tuple[BoundarySemanticsRow, ...]]:
    diagnostics = _load_bottleneck_rows(bottleneck_root)
    states = _load_m5_states(micro_root)
    all_bars = tuple(
        bar
        for bar in iter_cibo_m1(m1_root)
        if LOOKBACK_START <= bar.opened_at < WINDOW_END + timedelta(days=1)
    )
    if not all_bars:
        raise ValueError("boundary semantics census found no native M1")
    symbol = all_bars[0].symbol
    if any(bar.symbol != symbol for bar in all_bars):
        raise ValueError("boundary semantics census requires one symbol")

    closebacks = _reconstruct_closebacks(
        all_bars=all_bars,
        session=session,
    )
    diagnostic_keys = {str(item["closeback_at"]) for item in diagnostics}
    if set(closebacks) != diagnostic_keys:
        missing = diagnostic_keys - set(closebacks)
        extra = set(closebacks) - diagnostic_keys
        raise ValueError(
            f"reconstructed closeback mismatch missing={len(missing)} extra={len(extra)}"
        )

    m3 = _aggregate_tf(all_bars, minutes=3)
    closes = tuple(item.closed_at for item in m3)
    pivots = _pivots(m3)

    rows: list[BoundarySemanticsRow] = []
    for raw in diagnostics:
        closeback_at = datetime.fromisoformat(str(raw["closeback_at"]))
        closeback = closebacks[closeback_at.isoformat()]
        side = CapitalizerSide(str(raw["side"]))
        state = states.get((closeback_at.isoformat(), side.value))
        if state is None:
            raise ValueError("missing frozen M5 state")

        current = v3._find_m3_mss(
            m3,
            closes,
            pivots,
            after=closeback_at,
            before=closeback.h1_deadline,
            side=side,
        )
        (
            source_at,
            source_boundary,
            source_started_at,
            extreme_at,
            extreme_boundary,
            extreme_started_at,
            non_cisd_ready,
        ) = _persistent_events(
            m3,
            closes,
            pivots,
            sweep_at=closeback.sweep_at,
            after=closeback_at,
            before=closeback.h1_deadline,
            side=side,
        )

        rows.append(
            BoundarySemanticsRow(
                symbol=symbol,
                session=str(raw["session"]),
                operating_date=str(raw["operating_date"]),
                closeback_at=closeback_at.isoformat(),
                sweep_at=closeback.sweep_at.isoformat(),
                h1_deadline=closeback.h1_deadline.isoformat(),
                side=side.value,
                liquidity_source=str(raw["liquidity_source"]),
                original_first_blocker=str(raw["first_blocker"]),
                m5_state=state.value,
                non_cisd_ready_bars=non_cisd_ready,
                current_v3_mss_at=(
                    None if current is None else current.confirmed_at.isoformat()
                ),
                source_first_mss_at=(
                    None if source_at is None else source_at.isoformat()
                ),
                persistent_extreme_mss_at=(
                    None if extreme_at is None else extreme_at.isoformat()
                ),
                source_first_boundary=(
                    None if source_boundary is None else str(source_boundary)
                ),
                source_first_boundary_started_at=(
                    None
                    if source_started_at is None
                    else source_started_at.isoformat()
                ),
                persistent_extreme_boundary_at_confirmation=(
                    None if extreme_boundary is None else str(extreme_boundary)
                ),
                persistent_extreme_boundary_started_at=(
                    None
                    if extreme_started_at is None
                    else extreme_started_at.isoformat()
                ),
                source_first_relation_vs_v3=_relation(
                    source_at,
                    None if current is None else current.confirmed_at,
                ),
                persistent_extreme_relation_vs_v3=_relation(
                    extreme_at,
                    None if current is None else current.confirmed_at,
                ),
            )
        )

    ordered = tuple(sorted(rows, key=lambda item: item.closeback_at))
    current_count = sum(item.current_v3_mss_at is not None for item in ordered)
    source_count = sum(item.source_first_mss_at is not None for item in ordered)
    extreme_count = sum(
        item.persistent_extreme_mss_at is not None for item in ordered
    )
    source_rel = Counter(item.source_first_relation_vs_v3 for item in ordered)
    extreme_rel = Counter(
        item.persistent_extreme_relation_vs_v3 for item in ordered
    )
    report = {
        "identity": IDENTITY,
        "symbol": symbol,
        "session": session.value,
        "closebacks": len(ordered),
        "closebacks_with_non_cisd_ready_bar": sum(
            item.non_cisd_ready_bars > 0 for item in ordered
        ),
        "confirmed_mss": {
            CURRENT: current_count,
            SOURCE_FIRST: source_count,
            PERSISTENT_EXTREME: extreme_count,
        },
        "source_first_relation_vs_v3": dict(sorted(source_rel.items())),
        "persistent_extreme_relation_vs_v3": dict(sorted(extreme_rel.items())),
        "source_first_recovered_by_first_blocker": dict(
            sorted(
                Counter(
                    item.original_first_blocker
                    for item in ordered
                    if item.source_first_relation_vs_v3 == "RECOVERS_NO_V3_MSS"
                ).items()
            )
        ),
        "persistent_extreme_recovered_by_first_blocker": dict(
            sorted(
                Counter(
                    item.original_first_blocker
                    for item in ordered
                    if item.persistent_extreme_relation_vs_v3
                    == "RECOVERS_NO_V3_MSS"
                ).items()
            )
        ),
        "source_first_recovered_by_m5_state": dict(
            sorted(
                Counter(
                    item.m5_state
                    for item in ordered
                    if item.source_first_relation_vs_v3 == "RECOVERS_NO_V3_MSS"
                ).items()
            )
        ),
        "persistent_extreme_recovered_by_m5_state": dict(
            sorted(
                Counter(
                    item.m5_state
                    for item in ordered
                    if item.persistent_extreme_relation_vs_v3
                    == "RECOVERS_NO_V3_MSS"
                ).items()
            )
        ),
        "outcome_used_for_admission": False,
        "strategy_mutated": False,
        "diagnostic_only": True,
        "economic_candidate": False,
    }
    return report, ordered


def write_market(
    report: dict[str, Any],
    rows: tuple[BoundarySemanticsRow, ...],
    output: Path,
) -> None:
    output.mkdir(parents=True, exist_ok=True)
    symbol = str(report["symbol"]).lower()
    stem = f"capitalizer-{symbol}-v3-cisd-boundary-semantics-census-2y-v1"
    (output / f"{stem}.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    with (output / f"{stem}-rows.jsonl").open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(asdict(row), sort_keys=True) + "\n")


def _load_reports(root: Path) -> list[dict[str, Any]]:
    paths = sorted(
        root.rglob("capitalizer-*-v3-cisd-boundary-semantics-census-2y-v1.json")
    )
    if len(paths) != 9:
        raise ValueError(
            f"boundary semantics matrix requires 9 reports, got {len(paths)}"
        )
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
    ready = sum(
        int(item["closebacks_with_non_cisd_ready_bar"])
        for item in reports
    )
    confirmed = {
        CURRENT: sum(int(item["confirmed_mss"][CURRENT]) for item in reports),
        SOURCE_FIRST: sum(
            int(item["confirmed_mss"][SOURCE_FIRST]) for item in reports
        ),
        PERSISTENT_EXTREME: sum(
            int(item["confirmed_mss"][PERSISTENT_EXTREME]) for item in reports
        ),
    }
    per_session: dict[str, Counter[str]] = {}
    for report in reports:
        session = str(report["session"])
        counter = per_session.setdefault(session, Counter())
        counter["closebacks"] += int(report["closebacks"])
        counter["non_cisd_ready"] += int(
            report["closebacks_with_non_cisd_ready_bar"]
        )
        for semantic in (CURRENT, SOURCE_FIRST, PERSISTENT_EXTREME):
            counter[semantic] += int(report["confirmed_mss"][semantic])

    return {
        "identity": MATRIX_IDENTITY,
        "market_count": 9,
        "closebacks": closebacks,
        "closeback_control_reproduced": closebacks == EXPECTED_CLOSEBACKS,
        "closebacks_with_non_cisd_ready_bar": ready,
        "confirmed_mss": confirmed,
        "v3_mss_control_reproduced": confirmed[CURRENT] == EXPECTED_V3_MSS,
        "source_first_relation_vs_v3": _sum_nested(
            reports,
            "source_first_relation_vs_v3",
        ),
        "persistent_extreme_relation_vs_v3": _sum_nested(
            reports,
            "persistent_extreme_relation_vs_v3",
        ),
        "source_first_recovered_by_first_blocker": _sum_nested(
            reports,
            "source_first_recovered_by_first_blocker",
        ),
        "persistent_extreme_recovered_by_first_blocker": _sum_nested(
            reports,
            "persistent_extreme_recovered_by_first_blocker",
        ),
        "source_first_recovered_by_m5_state": _sum_nested(
            reports,
            "source_first_recovered_by_m5_state",
        ),
        "persistent_extreme_recovered_by_m5_state": _sum_nested(
            reports,
            "persistent_extreme_recovered_by_m5_state",
        ),
        "per_session": {
            key: dict(value) for key, value in sorted(per_session.items())
        },
        "markets": sorted(reports, key=lambda item: str(item["symbol"])),
        "source_first_semantics_frozen": (
            "FIRST_OPPOSING_OPEN_AFTER_SWEEP_PERSISTS"
        ),
        "persistent_extreme_semantics_frozen": (
            "OPPOSING_OPEN_EXTREME_AFTER_SWEEP_PERSISTS"
        ),
        "outcome_used_for_admission": False,
        "strategy_mutated": False,
        "diagnostic_only": True,
        "economic_candidate": False,
    }


def write_matrix(report: dict[str, Any], output: Path) -> None:
    output.mkdir(parents=True, exist_ok=True)
    path = (
        output
        / "capitalizer-nine-market-v3-cisd-boundary-semantics-census-2y-v1.json"
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
            args.bottleneck_root,
            args.micro_root,
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
