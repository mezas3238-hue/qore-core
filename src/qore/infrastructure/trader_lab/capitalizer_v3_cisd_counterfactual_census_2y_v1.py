"""Counterfactual census for V3 2Y CISD-first-blocker closebacks.

Diagnostic only. Measures the real same-bar reservoir where direction + swing break +
body>=60% + ATR>1.2x coexist on one M3 bar while CISD alone fails. It also separates
cross-bar desynchronization and incomplete non-CISD component cases.

M5 context is retained as the raw existing CORE microstructure signature only. It is not
mapped to ALIGNED/OPPOSED/NEUTRAL here because that mapping is a separate frozen contract.
"""

from __future__ import annotations

import argparse
import bisect
import json
from collections import Counter
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from qore.infrastructure.trader_lab.capitalizer_cibo_m1_reader_v1 import iter_cibo_m1
from qore.infrastructure.trader_lab.capitalizer_exposure_graph import CapitalizerSide
from qore.infrastructure.trader_lab.capitalizer_m3_mss_bottleneck_forensics_1y_v1 import (
    _bar_components,
)
from qore.infrastructure.trader_lab.capitalizer_m3_mss_bottleneck_forensics_2y_v1 import (
    IDENTITY as BOTTLENECK_IDENTITY,
    LOOKBACK_START,
    WINDOW_END,
    WINDOW_START,
)
from qore.infrastructure.trader_lab.capitalizer_strict_htf_gate_1y_v1 import (
    _aggregate_tf,
    _pivots,
)

IDENTITY = "QORE_CAPITALIZER_V3_CISD_COUNTERFACTUAL_CENSUS_2Y_V1"
MATRIX_IDENTITY = "QORE_CAPITALIZER_NINE_MARKET_V3_CISD_COUNTERFACTUAL_CENSUS_2Y_V1"
EXPECTED_CISD_FIRST_BLOCKERS = 3007


@dataclass(frozen=True, slots=True)
class CensusRow:
    symbol: str
    session: str
    operating_date: str
    closeback_at: str
    h1_deadline: str
    side: str
    liquidity_source: str
    same_bar_cisd_only: bool
    same_bar_cisd_only_bars: int
    first_same_bar_cisd_only_at: str | None
    cisd_present_elsewhere_n1: bool
    swing_cisd_desynchronized: bool
    distributed_non_cisd_components_only: bool
    non_cisd_component_incomplete: bool
    directional_swing_bars: int
    directional_cisd_bars: int
    directional_body_bars: int
    directional_atr_bars: int
    raw_m5_microstructure_signature: str
    m5_state_mapping_frozen: bool = False
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
        raise ValueError("census requires one frozen bottleneck market artifact")
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
                if raw.get("first_blocker") == "CISD":
                    rows.append(raw)
    return tuple(rows)


def _load_microstructure_rows(root: Path) -> dict[str, str]:
    paths = sorted(
        root.rglob("capitalizer-*-v3-m3-microstructure-context-2y-v1-rows.jsonl")
    )
    if len(paths) != 1:
        raise ValueError("census requires one V3 microstructure row ledger")
    result: dict[str, str] = {}
    with paths[0].open(encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            raw = json.loads(line)
            if not isinstance(raw, dict):
                raise ValueError("microstructure row must be object")
            key = str(raw["closeback_at"])
            result[key] = str(raw["microstructure_signature"])
    return result


def build_market_report(
    bottleneck_root: Path,
    microstructure_root: Path,
    m1_root: Path,
) -> tuple[dict[str, Any], tuple[CensusRow, ...]]:
    source_rows = _load_bottleneck_rows(bottleneck_root)
    micro = _load_microstructure_rows(microstructure_root)
    bars = tuple(
        bar
        for bar in iter_cibo_m1(m1_root)
        if LOOKBACK_START <= bar.opened_at < WINDOW_END + timedelta(days=1)
    )
    if not bars:
        raise ValueError("census found no native M1")
    symbol = bars[0].symbol
    if any(bar.symbol != symbol for bar in bars):
        raise ValueError("census requires one symbol per M1 root")
    m3 = _aggregate_tf(bars, minutes=3)
    m3_closes = tuple(item.closed_at for item in m3)
    pivots = _pivots(m3)

    rows: list[CensusRow] = []
    missing_micro = 0
    for raw in source_rows:
        closeback_at = datetime.fromisoformat(str(raw["closeback_at"]))
        deadline = datetime.fromisoformat(str(raw["h1_deadline"]))
        side = CapitalizerSide(str(raw["side"]))
        start = bisect.bisect_right(m3_closes, closeback_at)
        end = bisect.bisect_right(m3_closes, deadline)

        same_bar_indices: list[int] = []
        swing_indices: list[int] = []
        cisd_indices: list[int] = []
        body_indices: list[int] = []
        atr_indices: list[int] = []
        for index in range(start, end):
            directional, swing_break, cisd, body_ok, atr_ok = _bar_components(
                m3,
                pivots,
                index=index,
                side=side,
            )
            if directional and swing_break:
                swing_indices.append(index)
            if directional and cisd:
                cisd_indices.append(index)
            if directional and body_ok:
                body_indices.append(index)
            if directional and atr_ok:
                atr_indices.append(index)
            if (
                directional
                and swing_break
                and body_ok
                and atr_ok
                and not cisd
            ):
                same_bar_indices.append(index)

        same_bar = bool(same_bar_indices)
        cisd_elsewhere = bool(cisd_indices)
        desync = bool(swing_indices and cisd_indices)
        distributed_non_cisd = bool(
            not same_bar
            and swing_indices
            and body_indices
            and atr_indices
        )
        incomplete = bool(
            not same_bar and not distributed_non_cisd
        )
        signature = micro.get(str(raw["closeback_at"]))
        if signature is None:
            missing_micro += 1
            signature = "MISSING"

        rows.append(
            CensusRow(
                symbol=symbol,
                session=str(raw["session"]),
                operating_date=str(raw["operating_date"]),
                closeback_at=str(raw["closeback_at"]),
                h1_deadline=str(raw["h1_deadline"]),
                side=str(raw["side"]),
                liquidity_source=str(raw["liquidity_source"]),
                same_bar_cisd_only=same_bar,
                same_bar_cisd_only_bars=len(same_bar_indices),
                first_same_bar_cisd_only_at=(
                    None
                    if not same_bar_indices
                    else m3[same_bar_indices[0]].closed_at.isoformat()
                ),
                cisd_present_elsewhere_n1=cisd_elsewhere,
                swing_cisd_desynchronized=desync,
                distributed_non_cisd_components_only=distributed_non_cisd,
                non_cisd_component_incomplete=incomplete,
                directional_swing_bars=len(swing_indices),
                directional_cisd_bars=len(cisd_indices),
                directional_body_bars=len(body_indices),
                directional_atr_bars=len(atr_indices),
                raw_m5_microstructure_signature=signature,
            )
        )

    ordered = tuple(sorted(rows, key=lambda item: item.closeback_at))
    by_signature = Counter(item.raw_m5_microstructure_signature for item in ordered)
    same_bar_signatures = Counter(
        item.raw_m5_microstructure_signature
        for item in ordered
        if item.same_bar_cisd_only
    )
    report = {
        "identity": IDENTITY,
        "symbol": symbol,
        "session": ordered[0].session if ordered else None,
        "window_start": WINDOW_START.isoformat(),
        "window_end_exclusive": WINDOW_END.isoformat(),
        "cisd_first_blockers": len(ordered),
        "same_bar_cisd_only": sum(item.same_bar_cisd_only for item in ordered),
        "same_bar_cisd_only_with_cisd_elsewhere": sum(
            item.same_bar_cisd_only and item.cisd_present_elsewhere_n1
            for item in ordered
        ),
        "same_bar_cisd_only_without_cisd_elsewhere": sum(
            item.same_bar_cisd_only and not item.cisd_present_elsewhere_n1
            for item in ordered
        ),
        "swing_cisd_desynchronized": sum(
            item.swing_cisd_desynchronized for item in ordered
        ),
        "distributed_non_cisd_components_only": sum(
            item.distributed_non_cisd_components_only for item in ordered
        ),
        "non_cisd_component_incomplete": sum(
            item.non_cisd_component_incomplete for item in ordered
        ),
        "missing_microstructure_rows": missing_micro,
        "raw_m5_signatures": dict(by_signature.most_common()),
        "same_bar_cisd_only_raw_m5_signatures": dict(
            same_bar_signatures.most_common()
        ),
        "m5_state_mapping_frozen": False,
        "m5_state_mapping_deferred_to_step2": True,
        "strategy_mutated": False,
        "thresholds_mutated": False,
        "outcome_used_for_admission": False,
        "diagnostic_only": True,
        "economic_candidate": False,
    }
    return report, ordered


def write_market(
    report: dict[str, Any],
    rows: tuple[CensusRow, ...],
    output: Path,
) -> None:
    output.mkdir(parents=True, exist_ok=True)
    symbol = str(report["symbol"]).lower()
    stem = f"capitalizer-{symbol}-v3-cisd-counterfactual-census-2y-v1"
    (output / f"{stem}.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    with (output / f"{stem}-rows.jsonl").open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(asdict(row), sort_keys=True) + "\n")


def _load_reports(root: Path) -> list[dict[str, Any]]:
    paths = sorted(
        root.rglob("capitalizer-*-v3-cisd-counterfactual-census-2y-v1.json")
    )
    if len(paths) != 9:
        raise ValueError(f"CISD census matrix requires 9 reports, got {len(paths)}")
    return [dict(json.loads(path.read_text(encoding="utf-8"))) for path in paths]


def build_matrix(root: Path) -> dict[str, Any]:
    reports = _load_reports(root)
    per_session: dict[str, Counter[str]] = {}
    for report in reports:
        session = str(report["session"])
        counter = per_session.setdefault(session, Counter())
        for key in (
            "cisd_first_blockers",
            "same_bar_cisd_only",
            "same_bar_cisd_only_with_cisd_elsewhere",
            "same_bar_cisd_only_without_cisd_elsewhere",
            "swing_cisd_desynchronized",
            "distributed_non_cisd_components_only",
            "non_cisd_component_incomplete",
        ):
            counter[key] += int(report[key])

    total = sum(int(item["cisd_first_blockers"]) for item in reports)
    same_bar = sum(int(item["same_bar_cisd_only"]) for item in reports)
    return {
        "identity": MATRIX_IDENTITY,
        "window_start": WINDOW_START.isoformat(),
        "window_end_exclusive": WINDOW_END.isoformat(),
        "market_count": 9,
        "cisd_first_blockers": total,
        "expected_cisd_first_blockers": EXPECTED_CISD_FIRST_BLOCKERS,
        "cisd_control_reproduced": total == EXPECTED_CISD_FIRST_BLOCKERS,
        "same_bar_cisd_only": same_bar,
        "same_bar_reservoir_rate": (
            None if total == 0 else str(same_bar / total)
        ),
        "same_bar_cisd_only_with_cisd_elsewhere": sum(
            int(item["same_bar_cisd_only_with_cisd_elsewhere"])
            for item in reports
        ),
        "same_bar_cisd_only_without_cisd_elsewhere": sum(
            int(item["same_bar_cisd_only_without_cisd_elsewhere"])
            for item in reports
        ),
        "swing_cisd_desynchronized": sum(
            int(item["swing_cisd_desynchronized"]) for item in reports
        ),
        "distributed_non_cisd_components_only": sum(
            int(item["distributed_non_cisd_components_only"]) for item in reports
        ),
        "non_cisd_component_incomplete": sum(
            int(item["non_cisd_component_incomplete"]) for item in reports
        ),
        "missing_microstructure_rows": sum(
            int(item["missing_microstructure_rows"]) for item in reports
        ),
        "per_session": {
            key: dict(value) for key, value in sorted(per_session.items())
        },
        "markets": sorted(reports, key=lambda item: str(item["symbol"])),
        "m5_state_mapping_frozen": False,
        "m5_state_mapping_deferred_to_step2": True,
        "strategy_mutated": False,
        "thresholds_mutated": False,
        "outcome_used_for_admission": False,
        "diagnostic_only": True,
        "economic_candidate": False,
    }


def write_matrix(report: dict[str, Any], output: Path) -> None:
    output.mkdir(parents=True, exist_ok=True)
    path = output / "capitalizer-nine-market-v3-cisd-counterfactual-census-2y-v1.json"
    path.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    market = sub.add_parser("market")
    market.add_argument("bottleneck_root", type=Path)
    market.add_argument("microstructure_root", type=Path)
    market.add_argument("m1_root", type=Path)
    market.add_argument("output", type=Path)
    matrix = sub.add_parser("matrix")
    matrix.add_argument("input_root", type=Path)
    matrix.add_argument("output", type=Path)
    args = parser.parse_args()

    if args.command == "market":
        report, rows = build_market_report(
            args.bottleneck_root,
            args.microstructure_root,
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
