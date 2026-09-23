"""Outcome-free anatomy of the 322 SOURCE_FIRST FVG_MISSING cases.

The frozen funnel established that these setups have a valid SOURCE_FIRST M3 MSS
but no V3 M1 causal zone. This atlas explains the structural reason without
reading trade outcomes or inventing an entry.

It distinguishes:
- missing causal opposing M1 OB before displacement;
- absence of a same-side FVG confirmable by MSS time;
- FVG present despite missing OB;
- same-side/opposed FVG that appears only after MSS, before H1 deadline;
- same-side/opposed FVG that appears only after the H1 deadline (+60m observation).

This is diagnostic-only. No admission rule or economic candidate is created.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from qore.infrastructure.trader_lab import (
    capitalizer_owner_h1_m3_m1_causal_reversal_1y_v3 as v3,
)
from qore.infrastructure.trader_lab import (
    capitalizer_v3_source_first_wait5_funnel_atlas_2y_v1 as funnel,
)
from qore.infrastructure.trader_lab.capitalizer_cibo_m1_reader_v1 import (
    CapitalizerM1Bar,
    iter_cibo_m1,
)
from qore.infrastructure.trader_lab.capitalizer_contract import CapitalizerSession
from qore.infrastructure.trader_lab.capitalizer_exposure_graph import CapitalizerSide
from qore.infrastructure.trader_lab.capitalizer_strict_htf_gate_1y_v1 import (
    TFBar,
    _aggregate_tf,
    _index_day_inputs,
    _pivots,
)
from qore.infrastructure.trader_lab.capitalizer_v3_source_first_cisd_v1 import (
    find_source_first_m3_mss,
)

IDENTITY = "QORE_CAPITALIZER_V3_SOURCE_FIRST_FVG_MISSING_ATLAS_2Y_V1"
MATRIX_IDENTITY = "QORE_CAPITALIZER_NINE_MARKET_V3_SOURCE_FIRST_FVG_MISSING_ATLAS_2Y_V1"
EXPECTED_FVG_MISSING = 322

NO_DISPLACEMENT_M1 = "NO_DISPLACEMENT_M1"
NO_CAUSAL_OB = "NO_CAUSAL_OB"
NO_PRECONFIRM_SAME_SIDE_FVG = "NO_PRECONFIRM_SAME_SIDE_FVG"


@dataclass(frozen=True, slots=True)
class FvgMissingRow:
    symbol: str
    session: str
    operating_date: str
    side: str
    source_first_mss_at: str
    h1_deadline: str
    exact_root_reason: str
    causal_ob_present: bool
    preconfirm_same_side_fvg_count: int
    preconfirm_opposed_fvg_count: int
    fvg_exists_without_causal_ob: bool
    causal_ob_exists_without_same_side_fvg: bool
    same_side_fvg_after_mss_before_deadline_at: str | None
    opposed_fvg_after_mss_before_deadline_at: str | None
    same_side_fvg_after_deadline_plus60_at: str | None
    opposed_fvg_after_deadline_plus60_at: str | None
    outcome_fields_read: bool = False


def _load_fvg_missing(root: Path) -> tuple[dict[str, Any], ...]:
    paths = sorted(
        root.rglob(
            "capitalizer-*-v3-source-first-wait5-funnel-atlas-2y-v1-rows.jsonl"
        )
    )
    if len(paths) != 1:
        raise ValueError("FVG-missing atlas requires one frozen funnel ledger")
    rows: list[dict[str, Any]] = []
    with paths[0].open(encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            raw = json.loads(line)
            if not isinstance(raw, dict):
                raise ValueError("funnel row must be object")
            if raw.get("terminal_reason") == funnel.FVG_MISSING:
                rows.append(raw)
    return tuple(rows)


def _same_side_fvg(
    first: CapitalizerM1Bar,
    third: CapitalizerM1Bar,
    side: CapitalizerSide,
) -> bool:
    return bool(
        first.high < third.low
        if side is CapitalizerSide.LONG
        else first.low > third.high
    )


def _opposed_fvg(
    first: CapitalizerM1Bar,
    third: CapitalizerM1Bar,
    side: CapitalizerSide,
) -> bool:
    return bool(
        first.low > third.high
        if side is CapitalizerSide.LONG
        else first.high < third.low
    )


def _first_fvg_after(
    execution: tuple[CapitalizerM1Bar, ...],
    *,
    after: datetime,
    before_or_at: datetime,
    side: CapitalizerSide,
    opposed: bool,
) -> datetime | None:
    detector = _opposed_fvg if opposed else _same_side_fvg
    for center in range(1, len(execution) - 1):
        first = execution[center - 1]
        third = execution[center + 1]
        if third.closed_at <= after:
            continue
        if third.closed_at > before_or_at:
            break
        if detector(first, third, side):
            return third.closed_at
    return None


def _build_row(
    *,
    raw: dict[str, Any],
    execution: tuple[CapitalizerM1Bar, ...],
    m3: tuple[TFBar, ...],
    m3_closes: tuple[datetime, ...],
    m3_pivots: Any,
) -> FvgMissingRow:
    side = CapitalizerSide(str(raw["side"]))
    sweep_at = datetime.fromisoformat(str(raw["sweep_at"]))
    closeback_at = datetime.fromisoformat(str(raw["closeback_at"]))
    deadline = datetime.fromisoformat(str(raw["h1_deadline"]))
    frozen_mss = datetime.fromisoformat(str(raw["source_first_mss_at"]))

    event = find_source_first_m3_mss(
        m3,
        m3_closes,
        m3_pivots,
        sweep_at=sweep_at,
        after=closeback_at,
        before=deadline,
        side=side,
    )
    if event is None or event.confirmed_at != frozen_mss:
        raise ValueError("FVG-missing SOURCE_FIRST MSS reconstruction mismatch")
    if v3._m1_causal_zone(execution, event=event) is not None:
        raise ValueError("FVG-missing row unexpectedly has V3 causal zone")

    displacement = [
        index
        for index, bar in enumerate(execution)
        if event.displacement_opened_at <= bar.opened_at < event.displacement_closed_at
    ]

    causal_ob_present = False
    pre_same = 0
    pre_opposed = 0
    if displacement:
        first_index = displacement[0]
        for index in range(first_index - 1, -1, -1):
            bar = execution[index]
            opposing = (
                bar.close < bar.open
                if side is CapitalizerSide.LONG
                else bar.close > bar.open
            )
            if opposing:
                causal_ob_present = True
                break

        for center in displacement:
            if center <= 0 or center + 1 >= len(execution):
                continue
            first = execution[center - 1]
            third = execution[center + 1]
            if third.closed_at > event.confirmed_at:
                continue
            if _same_side_fvg(first, third, side):
                pre_same += 1
            if _opposed_fvg(first, third, side):
                pre_opposed += 1

    if not displacement:
        root = NO_DISPLACEMENT_M1
    elif not causal_ob_present:
        root = NO_CAUSAL_OB
    else:
        root = NO_PRECONFIRM_SAME_SIDE_FVG

    plus60 = deadline + timedelta(minutes=60)
    same_before = _first_fvg_after(
        execution,
        after=event.confirmed_at,
        before_or_at=deadline,
        side=side,
        opposed=False,
    )
    opposed_before = _first_fvg_after(
        execution,
        after=event.confirmed_at,
        before_or_at=deadline,
        side=side,
        opposed=True,
    )
    same_plus60 = _first_fvg_after(
        execution,
        after=deadline,
        before_or_at=plus60,
        side=side,
        opposed=False,
    )
    opposed_plus60 = _first_fvg_after(
        execution,
        after=deadline,
        before_or_at=plus60,
        side=side,
        opposed=True,
    )

    return FvgMissingRow(
        symbol=str(raw["symbol"]),
        session=str(raw["session"]),
        operating_date=str(raw["operating_date"]),
        side=side.value,
        source_first_mss_at=event.confirmed_at.isoformat(),
        h1_deadline=deadline.isoformat(),
        exact_root_reason=root,
        causal_ob_present=causal_ob_present,
        preconfirm_same_side_fvg_count=pre_same,
        preconfirm_opposed_fvg_count=pre_opposed,
        fvg_exists_without_causal_ob=(not causal_ob_present and pre_same > 0),
        causal_ob_exists_without_same_side_fvg=(causal_ob_present and pre_same == 0),
        same_side_fvg_after_mss_before_deadline_at=(
            None if same_before is None else same_before.isoformat()
        ),
        opposed_fvg_after_mss_before_deadline_at=(
            None if opposed_before is None else opposed_before.isoformat()
        ),
        same_side_fvg_after_deadline_plus60_at=(
            None if same_plus60 is None else same_plus60.isoformat()
        ),
        opposed_fvg_after_deadline_plus60_at=(
            None if opposed_plus60 is None else opposed_plus60.isoformat()
        ),
    )


def build_market_report(
    funnel_root: Path,
    m1_root: Path,
) -> tuple[dict[str, Any], tuple[FvgMissingRow, ...]]:
    frozen = _load_fvg_missing(funnel_root)
    if not frozen:
        raise ValueError("FVG-missing atlas found no rows")

    first_sweep = min(datetime.fromisoformat(str(row["sweep_at"])) for row in frozen)
    last_deadline = max(datetime.fromisoformat(str(row["h1_deadline"])) for row in frozen)
    scan_start = first_sweep - timedelta(days=2)
    scan_end = last_deadline + timedelta(minutes=61)
    all_bars = tuple(
        bar
        for bar in iter_cibo_m1(m1_root)
        if scan_start <= bar.opened_at <= scan_end
    )
    if not all_bars:
        raise ValueError("FVG-missing atlas found no native M1")
    symbol = all_bars[0].symbol
    if any(bar.symbol != symbol for bar in all_bars):
        raise ValueError("FVG-missing atlas requires one symbol per M1 root")
    if any(str(row["symbol"]) != symbol for row in frozen):
        raise ValueError("funnel/M1 symbol mismatch")

    m3 = _aggregate_tf(all_bars, minutes=3)
    m3_closes = tuple(item.closed_at for item in m3)
    m3_pivots = _pivots(m3)
    execution_by_day, _ = _index_day_inputs(
        all_bars,
        session=CapitalizerSession(str(frozen[0]["session"])),
    )

    rows: list[FvgMissingRow] = []
    for raw in frozen:
        execution = execution_by_day.get(str(raw["operating_date"]), ())
        if not execution:
            raise ValueError("missing execution bars for FVG-missing row")
        rows.append(
            _build_row(
                raw=raw,
                execution=execution,
                m3=m3,
                m3_closes=m3_closes,
                m3_pivots=m3_pivots,
            )
        )

    ordered = tuple(sorted(rows, key=lambda item: (item.source_first_mss_at, item.symbol)))
    reasons = Counter(item.exact_root_reason for item in ordered)
    return {
        "identity": IDENTITY,
        "symbol": symbol,
        "session": str(frozen[0]["session"]),
        "fvg_missing_rows": len(ordered),
        "root_reasons": dict(sorted(reasons.items())),
        "causal_ob_present": sum(item.causal_ob_present for item in ordered),
        "fvg_exists_without_causal_ob": sum(
            item.fvg_exists_without_causal_ob for item in ordered
        ),
        "causal_ob_exists_without_same_side_fvg": sum(
            item.causal_ob_exists_without_same_side_fvg for item in ordered
        ),
        "same_side_fvg_after_mss_before_deadline": sum(
            item.same_side_fvg_after_mss_before_deadline_at is not None
            for item in ordered
        ),
        "opposed_fvg_after_mss_before_deadline": sum(
            item.opposed_fvg_after_mss_before_deadline_at is not None
            for item in ordered
        ),
        "same_side_fvg_after_deadline_plus60": sum(
            item.same_side_fvg_after_deadline_plus60_at is not None
            for item in ordered
        ),
        "opposed_fvg_after_deadline_plus60": sum(
            item.opposed_fvg_after_deadline_plus60_at is not None
            for item in ordered
        ),
        "outcome_fields_read": False,
        "outcome_used_for_classification": False,
        "strategy_mutated": False,
        "diagnostic_only": True,
        "economic_candidate": False,
        "rule_promotion_allowed": False,
    }, ordered


def write_market(
    report: dict[str, Any],
    rows: tuple[FvgMissingRow, ...],
    output: Path,
) -> None:
    output.mkdir(parents=True, exist_ok=True)
    symbol = str(report["symbol"]).lower()
    stem = f"capitalizer-{symbol}-v3-source-first-fvg-missing-atlas-2y-v1"
    (output / f"{stem}.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    with (output / f"{stem}-rows.jsonl").open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(asdict(row), sort_keys=True) + "\n")


def _load_reports(root: Path) -> list[dict[str, Any]]:
    paths = sorted(
        root.rglob("capitalizer-*-v3-source-first-fvg-missing-atlas-2y-v1.json")
    )
    if len(paths) != 9:
        raise ValueError(f"FVG-missing matrix requires 9 reports, got {len(paths)}")
    return [dict(json.loads(path.read_text(encoding="utf-8"))) for path in paths]


def build_matrix(root: Path) -> dict[str, Any]:
    reports = _load_reports(root)
    reasons: Counter[str] = Counter()
    for report in reports:
        for key, value in dict(report["root_reasons"]).items():
            reasons[str(key)] += int(value)

    total = sum(int(report["fvg_missing_rows"]) for report in reports)
    return {
        "identity": MATRIX_IDENTITY,
        "market_count": 9,
        "fvg_missing_rows": total,
        "fvg_missing_control_reproduced": total == EXPECTED_FVG_MISSING,
        "root_reasons": dict(sorted(reasons.items())),
        "causal_ob_present": sum(int(r["causal_ob_present"]) for r in reports),
        "fvg_exists_without_causal_ob": sum(
            int(r["fvg_exists_without_causal_ob"]) for r in reports
        ),
        "causal_ob_exists_without_same_side_fvg": sum(
            int(r["causal_ob_exists_without_same_side_fvg"]) for r in reports
        ),
        "same_side_fvg_after_mss_before_deadline": sum(
            int(r["same_side_fvg_after_mss_before_deadline"]) for r in reports
        ),
        "opposed_fvg_after_mss_before_deadline": sum(
            int(r["opposed_fvg_after_mss_before_deadline"]) for r in reports
        ),
        "same_side_fvg_after_deadline_plus60": sum(
            int(r["same_side_fvg_after_deadline_plus60"]) for r in reports
        ),
        "opposed_fvg_after_deadline_plus60": sum(
            int(r["opposed_fvg_after_deadline_plus60"]) for r in reports
        ),
        "markets": sorted(reports, key=lambda item: str(item["symbol"])),
        "outcome_fields_read": False,
        "outcome_used_for_classification": False,
        "strategy_mutated": False,
        "diagnostic_only": True,
        "economic_candidate": False,
        "rule_promotion_allowed": False,
    }


def write_matrix(report: dict[str, Any], output: Path) -> None:
    output.mkdir(parents=True, exist_ok=True)
    path = output / "capitalizer-nine-market-v3-source-first-fvg-missing-atlas-2y-v1.json"
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

    matrix = sub.add_parser("matrix")
    matrix.add_argument("input_root", type=Path)
    matrix.add_argument("output", type=Path)

    args = parser.parse_args()
    if args.command == "market":
        report, rows = build_market_report(args.funnel_root, args.m1_root)
        write_market(report, rows, args.output)
        print(json.dumps(report, sort_keys=True))
        return

    report = build_matrix(args.input_root)
    write_matrix(report, args.output)
    print(json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    main()
