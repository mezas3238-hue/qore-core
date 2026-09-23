"""2Y outcome-free census of next-H1 supersession before clean LATE60 fills.

Frozen population: the 376 structurally clean late fills from the completed
SOURCE_FIRST fill-miss anatomy.

For each frozen old setup, observe only information available before its late fill
and classify whether the next H1 generation has already produced:
- no new sweep;
- a new sweep without closeback;
- a new M5 closeback without SOURCE_FIRST MSS;
- a new SOURCE_FIRST MSS.

New closeback/MSS direction is recorded relative to the old setup side.

No PnL, exit, target or future outcome is used. No strategy rule is changed.
"""

from __future__ import annotations

import argparse
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
from qore.infrastructure.trader_lab.capitalizer_contract import CapitalizerSession
from qore.infrastructure.trader_lab.capitalizer_exposure_graph import CapitalizerSide
from qore.infrastructure.trader_lab.capitalizer_full_ict_density_scanner_1y_v1 import (
    _aggregate_h1,
)
from qore.infrastructure.trader_lab.capitalizer_strict_htf_gate_1y_v1 import (
    TFBar,
    _aggregate_tf,
    _index_day_inputs,
    _pivots,
)
from qore.infrastructure.trader_lab.capitalizer_v3_source_first_cisd_v1 import (
    find_source_first_m3_mss,
)

IDENTITY = "QORE_CAPITALIZER_V3_SOURCE_FIRST_LATE60_SUPERSESSION_CENSUS_2Y_V1"
MATRIX_IDENTITY = (
    "QORE_CAPITALIZER_NINE_MARKET_V3_SOURCE_FIRST_"
    "LATE60_SUPERSESSION_CENSUS_2Y_V1"
)
EXPECTED_CLEAN_LATE = 376

NO_NEW_SWEEP = "NO_NEW_SWEEP"
NEW_SWEEP_ONLY = "NEW_SWEEP_ONLY"
NEW_CLOSEBACK_NO_MSS = "NEW_CLOSEBACK_NO_MSS"
NEW_MSS = "NEW_MSS"


@dataclass(frozen=True, slots=True)
class SupersessionRow:
    symbol: str
    session: str
    operating_date: str
    old_side: str
    old_h1_deadline: str
    old_mss_at: str
    late_fill_at: str
    late_fill_mode: str
    new_state: str
    new_closeback_side_relation: str | None
    new_mss_side_relation: str | None
    new_sweep_at: str | None
    new_closeback_at: str | None
    new_mss_at: str | None
    outcome_used_for_admission: bool = False


def _load_clean_late_rows(root: Path) -> tuple[dict[str, Any], ...]:
    paths = sorted(
        root.rglob(
            "capitalizer-*-v3-source-first-fill-miss-anatomy-2y-v1-rows.jsonl"
        )
    )
    if len(paths) != 1:
        raise ValueError("supersession census requires one anatomy ledger")
    rows: list[dict[str, Any]] = []
    with paths[0].open(encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            raw = json.loads(line)
            if not isinstance(raw, dict):
                raise ValueError("anatomy row must be object")
            if raw.get("late_status") == "LATE_FILL_WITHIN_60M_CLEAN":
                rows.append(raw)
    return tuple(rows)


def _side_relation(
    new_side: CapitalizerSide,
    old_side: CapitalizerSide,
) -> str:
    return "SAME_SIDE" if new_side is old_side else "OPPOSED_SIDE"


def _next_window(
    execution: tuple[CapitalizerM1Bar, ...],
    *,
    opened_at: datetime,
    before: datetime,
) -> tuple[CapitalizerM1Bar, ...]:
    return tuple(
        bar
        for bar in execution
        if opened_at <= bar.opened_at < before
    )


def _classify(
    *,
    raw: dict[str, Any],
    symbol: str,
    session: CapitalizerSession,
    execution: tuple[CapitalizerM1Bar, ...],
    all_bars: tuple[CapitalizerM1Bar, ...],
    h1_swings: Any,
    m5: tuple[TFBar, ...],
    m5_closes: tuple[datetime, ...],
    m3: tuple[TFBar, ...],
    m3_closes: tuple[datetime, ...],
    m3_pivots: Any,
    prior_session: Any,
) -> SupersessionRow:
    operating_day = date.fromisoformat(str(raw["operating_date"]))
    old_side = CapitalizerSide(str(raw["side"]))
    old_deadline = datetime.fromisoformat(str(raw["h1_deadline"]))
    old_mss_at = datetime.fromisoformat(str(raw["source_first_mss_at"]))
    late_fill_at = datetime.fromisoformat(str(raw["late_fill_at"]))
    if not old_deadline <= late_fill_at <= old_deadline + timedelta(minutes=60):
        raise ValueError("clean late fill is outside frozen LATE60 window")

    hour_bars = _next_window(
        execution,
        opened_at=old_deadline,
        before=late_fill_at,
    )
    if not hour_bars:
        return SupersessionRow(
            symbol=symbol,
            session=session.value,
            operating_date=operating_day.isoformat(),
            old_side=old_side.value,
            old_h1_deadline=old_deadline.isoformat(),
            old_mss_at=old_mss_at.isoformat(),
            late_fill_at=late_fill_at.isoformat(),
            late_fill_mode=str(raw["late_fill_mode"]),
            new_state=NO_NEW_SWEEP,
            new_closeback_side_relation=None,
            new_mss_side_relation=None,
            new_sweep_at=None,
            new_closeback_at=None,
            new_mss_at=None,
        )

    previous_day = v3._previous_day_range(
        all_bars,
        operating_day=operating_day,
    )
    levels = v3._liquidity_levels(
        prior_session=prior_session,
        previous_day=previous_day,
        h1_swings=h1_swings,
        hour_open=old_deadline,
    )
    if not levels:
        return SupersessionRow(
            symbol=symbol,
            session=session.value,
            operating_date=operating_day.isoformat(),
            old_side=old_side.value,
            old_h1_deadline=old_deadline.isoformat(),
            old_mss_at=old_mss_at.isoformat(),
            late_fill_at=late_fill_at.isoformat(),
            late_fill_mode=str(raw["late_fill_mode"]),
            new_state=NO_NEW_SWEEP,
            new_closeback_side_relation=None,
            new_mss_side_relation=None,
            new_sweep_at=None,
            new_closeback_at=None,
            new_mss_at=None,
        )

    sweep_seen, closeback = v3._find_sweep_closeback(
        hour_bars,
        levels=levels,
        m5=m5,
        m5_closes=m5_closes,
        h1_open=old_deadline,
        h1_deadline=late_fill_at,
    )
    if not sweep_seen:
        state = NO_NEW_SWEEP
        sweep_at = None
    elif closeback is None:
        state = NEW_SWEEP_ONLY
        sweep_at = min(
            bar.opened_at
            for bar in hour_bars
            if any(
                (
                    bar.high >= level.price
                    if level.side is CapitalizerSide.SHORT
                    else bar.low <= level.price
                )
                for level in levels
            )
        )
    else:
        state = NEW_CLOSEBACK_NO_MSS
        sweep_at = closeback.sweep_at

    closeback_relation: str | None = None
    mss_relation: str | None = None
    new_mss_at: datetime | None = None

    if closeback is not None:
        closeback_relation = _side_relation(closeback.side, old_side)
        mss = find_source_first_m3_mss(
            m3,
            m3_closes,
            m3_pivots,
            sweep_at=closeback.sweep_at,
            after=closeback.closeback_at,
            before=late_fill_at,
            side=closeback.side,
        )
        if mss is not None:
            state = NEW_MSS
            mss_relation = _side_relation(mss.side, old_side)
            new_mss_at = mss.confirmed_at

    return SupersessionRow(
        symbol=symbol,
        session=session.value,
        operating_date=operating_day.isoformat(),
        old_side=old_side.value,
        old_h1_deadline=old_deadline.isoformat(),
        old_mss_at=old_mss_at.isoformat(),
        late_fill_at=late_fill_at.isoformat(),
        late_fill_mode=str(raw["late_fill_mode"]),
        new_state=state,
        new_closeback_side_relation=closeback_relation,
        new_mss_side_relation=mss_relation,
        new_sweep_at=None if sweep_at is None else sweep_at.isoformat(),
        new_closeback_at=(
            None if closeback is None else closeback.closeback_at.isoformat()
        ),
        new_mss_at=None if new_mss_at is None else new_mss_at.isoformat(),
    )


def build_market_report(
    anatomy_root: Path,
    m1_root: Path,
    *,
    session: CapitalizerSession,
) -> tuple[dict[str, Any], tuple[SupersessionRow, ...]]:
    frozen = _load_clean_late_rows(anatomy_root)
    if not frozen:
        raise ValueError("supersession census found no clean late rows")

    first_time = min(
        datetime.fromisoformat(str(row["source_first_mss_at"])) for row in frozen
    )
    last_time = max(
        datetime.fromisoformat(str(row["late_fill_at"])) for row in frozen
    )
    all_bars = tuple(
        bar
        for bar in iter_cibo_m1(m1_root)
        if first_time - timedelta(days=2)
        <= bar.opened_at
        <= last_time + timedelta(minutes=5)
    )
    if not all_bars:
        raise ValueError("supersession census found no M1")
    symbol = all_bars[0].symbol
    if any(bar.symbol != symbol for bar in all_bars):
        raise ValueError("supersession census requires one symbol")
    if any(str(row["symbol"]) != symbol for row in frozen):
        raise ValueError("anatomy/M1 symbol mismatch")

    h1 = _aggregate_h1(all_bars)
    h1_swings = v3._build_h1_swings(h1)
    m5 = _aggregate_tf(all_bars, minutes=5)
    m5_closes = tuple(item.closed_at for item in m5)
    m3 = _aggregate_tf(all_bars, minutes=3)
    m3_closes = tuple(item.closed_at for item in m3)
    m3_pivots = _pivots(m3)
    execution_by_day, reference_by_day = _index_day_inputs(
        all_bars,
        session=session,
    )

    rows: list[SupersessionRow] = []
    for raw in frozen:
        operating_date = str(raw["operating_date"])
        execution = execution_by_day.get(operating_date, ())
        if not execution:
            raise ValueError("supersession census missing execution bars")
        rows.append(
            _classify(
                raw=raw,
                symbol=symbol,
                session=session,
                execution=execution,
                all_bars=all_bars,
                h1_swings=h1_swings,
                m5=m5,
                m5_closes=m5_closes,
                m3=m3,
                m3_closes=m3_closes,
                m3_pivots=m3_pivots,
                prior_session=reference_by_day.get(operating_date),
            )
        )

    ordered = tuple(
        sorted(rows, key=lambda item: (item.late_fill_at, item.symbol))
    )
    states = Counter(item.new_state for item in ordered)
    by_mode: dict[str, Counter[str]] = {}
    by_relation: Counter[str] = Counter()
    for item in ordered:
        by_mode.setdefault(item.late_fill_mode, Counter())[item.new_state] += 1
        if item.new_mss_side_relation is not None:
            by_relation[item.new_mss_side_relation] += 1

    return {
        "identity": IDENTITY,
        "symbol": symbol,
        "session": session.value,
        "clean_late_population": len(ordered),
        "state_counts": dict(sorted(states.items())),
        "new_mss_side_relation": dict(sorted(by_relation.items())),
        "state_by_late_fill_mode": {
            key: dict(sorted(value.items()))
            for key, value in sorted(by_mode.items())
        },
        "outcome_used_for_admission": False,
        "strategy_mutated": False,
        "diagnostic_only": True,
        "economic_candidate": False,
        "rule_promotion_allowed": False,
    }, ordered


def write_market(
    report: dict[str, Any],
    rows: tuple[SupersessionRow, ...],
    output: Path,
) -> None:
    output.mkdir(parents=True, exist_ok=True)
    symbol = str(report["symbol"]).lower()
    stem = (
        f"capitalizer-{symbol}-v3-source-first-late60-"
        "supersession-census-2y-v1"
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
            "capitalizer-*-v3-source-first-late60-supersession-census-2y-v1.json"
        )
    )
    if len(paths) != 9:
        raise ValueError(f"supersession matrix requires 9 reports, got {len(paths)}")
    return [dict(json.loads(path.read_text(encoding="utf-8"))) for path in paths]


def build_matrix(root: Path) -> dict[str, Any]:
    reports = _load_reports(root)
    states: Counter[str] = Counter()
    relations: Counter[str] = Counter()
    by_mode: dict[str, Counter[str]] = {}
    per_session: dict[str, Counter[str]] = {}

    for report in reports:
        for key, value in dict(report["state_counts"]).items():
            states[str(key)] += int(value)
        for key, value in dict(report["new_mss_side_relation"]).items():
            relations[str(key)] += int(value)
        raw_modes = report["state_by_late_fill_mode"]
        if not isinstance(raw_modes, dict):
            raise ValueError("state_by_late_fill_mode must be mapping")
        for mode, mapping in raw_modes.items():
            if not isinstance(mapping, dict):
                raise ValueError("fill mode state counts must be mapping")
            bucket = by_mode.setdefault(str(mode), Counter())
            for state, count in mapping.items():
                bucket[str(state)] += int(count)
        session_bucket = per_session.setdefault(str(report["session"]), Counter())
        session_bucket["clean_late"] += int(report["clean_late_population"])
        for key, value in dict(report["state_counts"]).items():
            session_bucket[str(key)] += int(value)

    population = sum(int(item["clean_late_population"]) for item in reports)
    return {
        "identity": MATRIX_IDENTITY,
        "market_count": 9,
        "clean_late_population": population,
        "clean_late_control_reproduced": population == EXPECTED_CLEAN_LATE,
        "state_counts": dict(sorted(states.items())),
        "new_mss_side_relation": dict(sorted(relations.items())),
        "state_by_late_fill_mode": {
            key: dict(sorted(value.items()))
            for key, value in sorted(by_mode.items())
        },
        "per_session": {
            key: dict(value) for key, value in sorted(per_session.items())
        },
        "markets": sorted(reports, key=lambda item: str(item["symbol"])),
        "state_partition_reproduced": sum(states.values()) == population,
        "outcome_used_for_admission": False,
        "strategy_mutated": False,
        "diagnostic_only": True,
        "economic_candidate": False,
        "rule_promotion_allowed": False,
    }


def write_matrix(report: dict[str, Any], output: Path) -> None:
    output.mkdir(parents=True, exist_ok=True)
    path = (
        output
        / "capitalizer-nine-market-v3-source-first-late60-"
        "supersession-census-2y-v1.json"
    )
    path.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)

    market = sub.add_parser("market")
    market.add_argument("anatomy_root", type=Path)
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
            args.anatomy_root,
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
