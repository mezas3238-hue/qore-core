"""Corrected V3 2Y CISD counterfactual census.

V1 treated boundary=None as cisd=False because the shared bottleneck helper exposed only
a boolean CISD result. That is acceptable for blocker attribution but not for claiming
that CISD was the *only* missing same-bar condition.

V2 separates:
- TRUE_SAME_BAR_CISD_ONLY: direction + swing break + body + ATR pass, CISD boundary exists,
  and the close does not break that boundary.
- SAME_BAR_CISD_BOUNDARY_MISSING: the same non-CISD conditions pass, but the CISD boundary
  is unavailable. This is not a CISD-only substitute candidate.
- OTHER_CISD_FIRST_BLOCKER: no same-bar non-CISD-ready bar exists.

This is diagnostic only and reconciles against the Step-4 literal OR experiment.
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
    WINDOW_START,
)
from qore.infrastructure.trader_lab.capitalizer_strict_htf_gate_1y_v1 import (
    _aggregate_tf,
    _pivots,
)
from qore.infrastructure.trader_lab.capitalizer_v3_m5_directional_state_v1 import (
    CapitalizerM5DirectionalState,
    classify_m5_directional_state,
)

IDENTITY = "QORE_CAPITALIZER_V3_CISD_COUNTERFACTUAL_CENSUS_2Y_V2"
MATRIX_IDENTITY = (
    "QORE_CAPITALIZER_NINE_MARKET_V3_CISD_COUNTERFACTUAL_CENSUS_2Y_V2"
)
EXPECTED_CISD_FIRST_BLOCKERS = 3007
STEP4_EXPECTED_ALIGNED_SUBSTITUTE_CONFIRMATIONS = 44


@dataclass(frozen=True, slots=True)
class CensusV2Row:
    symbol: str
    session: str
    operating_date: str
    closeback_at: str
    h1_deadline: str
    side: str
    liquidity_source: str
    m5_state: str
    non_cisd_ready_bars: int
    true_cisd_only_bars: int
    boundary_missing_bars: int
    true_same_bar_cisd_only: bool
    same_bar_boundary_missing_only: bool
    other_cisd_first_blocker: bool
    first_true_cisd_only_at: str | None
    first_boundary_missing_at: str | None
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
        raise ValueError("CISD census V2 requires one bottleneck market artifact")
    summary = json.loads(summaries[0].read_text(encoding="utf-8"))
    if summary.get("identity") != BOTTLENECK_IDENTITY:
        raise ValueError("unexpected bottleneck identity")
    rows: list[dict[str, Any]] = []
    with ledgers[0].open(encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            raw = json.loads(line)
            if not isinstance(raw, dict):
                raise ValueError("bottleneck row must be object")
            if raw.get("first_blocker") == "CISD":
                rows.append(raw)
    return tuple(rows)


def _load_m5_states(root: Path) -> dict[tuple[str, str], CapitalizerM5DirectionalState]:
    paths = sorted(
        root.rglob("capitalizer-*-v3-m3-microstructure-context-2y-v1-rows.jsonl")
    )
    if len(paths) != 1:
        raise ValueError("CISD census V2 requires one microstructure ledger")
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


def _bar_status(
    bars: Any,
    pivots: Any,
    *,
    index: int,
    side: CapitalizerSide,
) -> tuple[bool, bool, bool]:
    """Return non-CISD-ready, boundary-exists, CISD-break."""
    source = bars[index].source
    full_range = source.high - source.low
    if full_range <= 0:
        return False, False, False
    directional = (
        source.close > source.open
        if side is CapitalizerSide.LONG
        else source.close < source.open
    )
    if not directional:
        return False, False, False

    body_ratio = abs(source.close - source.open) / full_range
    if body_ratio < v3.BODY_RATIO_MIN:
        return False, False, False
    atr = v3._atr14(bars, index)
    if atr is None or full_range <= v3.ATR_MULTIPLIER * atr:
        return False, False, False

    break_kind = "HIGH" if side is CapitalizerSide.LONG else "LOW"
    broken = v3._latest_pivot(
        pivots,
        before=bars[index].opened_at,
        kind=break_kind,
    )
    if broken is None:
        return False, False, False
    structure_break = (
        source.close > broken.price
        if side is CapitalizerSide.LONG
        else source.close < broken.price
    )
    if not structure_break:
        return False, False, False

    boundary = v3._opposing_series_boundary(
        bars,
        index=index,
        side=side,
    )
    if boundary is None:
        return True, False, False
    cisd_break = (
        source.close > boundary
        if side is CapitalizerSide.LONG
        else source.close < boundary
    )
    return True, True, cisd_break


def build_market_report(
    bottleneck_root: Path,
    micro_root: Path,
    m1_root: Path,
) -> tuple[dict[str, Any], tuple[CensusV2Row, ...]]:
    source_rows = _load_bottleneck_rows(bottleneck_root)
    states = _load_m5_states(micro_root)
    bars = tuple(
        bar
        for bar in iter_cibo_m1(m1_root)
        if LOOKBACK_START <= bar.opened_at < WINDOW_END + timedelta(days=1)
    )
    if not bars:
        raise ValueError("CISD census V2 found no native M1")
    symbol = bars[0].symbol
    m3 = _aggregate_tf(bars, minutes=3)
    closes = tuple(item.closed_at for item in m3)
    pivots = _pivots(m3)

    rows: list[CensusV2Row] = []
    contradictions = 0
    for raw in source_rows:
        after = datetime.fromisoformat(str(raw["closeback_at"]))
        before = datetime.fromisoformat(str(raw["h1_deadline"]))
        side = CapitalizerSide(str(raw["side"]))
        state = states.get((after.isoformat(), side.value))
        if state is None:
            raise ValueError("missing frozen M5 state in CISD census V2")

        start = bisect.bisect_right(closes, after)
        end = bisect.bisect_right(closes, before)
        true_indices: list[int] = []
        missing_indices: list[int] = []
        ready = 0
        for index in range(start, end):
            non_cisd_ready, boundary_exists, cisd_break = _bar_status(
                m3,
                pivots,
                index=index,
                side=side,
            )
            if not non_cisd_ready:
                continue
            ready += 1
            if not boundary_exists:
                missing_indices.append(index)
                continue
            if cisd_break:
                # first_blocker=CISD guarantees no direction+swing+CISD bar.
                contradictions += 1
                continue
            true_indices.append(index)

        true_case = bool(true_indices)
        missing_only = bool(not true_case and missing_indices)
        other = not true_case and not missing_only
        rows.append(
            CensusV2Row(
                symbol=symbol,
                session=str(raw["session"]),
                operating_date=str(raw["operating_date"]),
                closeback_at=str(raw["closeback_at"]),
                h1_deadline=str(raw["h1_deadline"]),
                side=side.value,
                liquidity_source=str(raw["liquidity_source"]),
                m5_state=state.value,
                non_cisd_ready_bars=ready,
                true_cisd_only_bars=len(true_indices),
                boundary_missing_bars=len(missing_indices),
                true_same_bar_cisd_only=true_case,
                same_bar_boundary_missing_only=missing_only,
                other_cisd_first_blocker=other,
                first_true_cisd_only_at=(
                    None
                    if not true_indices
                    else m3[true_indices[0]].closed_at.isoformat()
                ),
                first_boundary_missing_at=(
                    None
                    if not missing_indices
                    else m3[missing_indices[0]].closed_at.isoformat()
                ),
            )
        )

    ordered = tuple(sorted(rows, key=lambda item: item.closeback_at))
    state_counts = Counter(
        item.m5_state
        for item in ordered
        if item.true_same_bar_cisd_only
    )
    report = {
        "identity": IDENTITY,
        "symbol": symbol,
        "session": ordered[0].session if ordered else None,
        "window_start": WINDOW_START.isoformat(),
        "window_end_exclusive": WINDOW_END.isoformat(),
        "cisd_first_blockers": len(ordered),
        "true_same_bar_cisd_only": sum(
            item.true_same_bar_cisd_only for item in ordered
        ),
        "same_bar_boundary_missing_only": sum(
            item.same_bar_boundary_missing_only for item in ordered
        ),
        "other_cisd_first_blocker": sum(
            item.other_cisd_first_blocker for item in ordered
        ),
        "true_cisd_only_by_m5_state": dict(sorted(state_counts.items())),
        "true_cisd_only_aligned": state_counts[
            CapitalizerM5DirectionalState.ALIGNED.value
        ],
        "boundary_cisd_contradictions": contradictions,
        "v1_reservoir_inflation_corrected": True,
        "cisd_boundary_required_for_true_cisd_only": True,
        "strategy_mutated": False,
        "outcome_used_for_admission": False,
        "diagnostic_only": True,
        "economic_candidate": False,
    }
    return report, ordered


def write_market(
    report: dict[str, Any],
    rows: tuple[CensusV2Row, ...],
    output: Path,
) -> None:
    output.mkdir(parents=True, exist_ok=True)
    symbol = str(report["symbol"]).lower()
    stem = f"capitalizer-{symbol}-v3-cisd-counterfactual-census-2y-v2"
    (output / f"{stem}.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    with (output / f"{stem}-rows.jsonl").open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(asdict(row), sort_keys=True) + "\n")


def _load_reports(root: Path) -> list[dict[str, Any]]:
    paths = sorted(
        root.rglob("capitalizer-*-v3-cisd-counterfactual-census-2y-v2.json")
    )
    if len(paths) != 9:
        raise ValueError(f"CISD census V2 matrix requires 9 reports, got {len(paths)}")
    return [dict(json.loads(path.read_text(encoding="utf-8"))) for path in paths]


def build_matrix(root: Path) -> dict[str, Any]:
    reports = _load_reports(root)
    total = sum(int(item["cisd_first_blockers"]) for item in reports)
    true_count = sum(int(item["true_same_bar_cisd_only"]) for item in reports)
    missing = sum(
        int(item["same_bar_boundary_missing_only"]) for item in reports
    )
    other = sum(int(item["other_cisd_first_blocker"]) for item in reports)
    aligned = sum(int(item["true_cisd_only_aligned"]) for item in reports)
    contradictions = sum(
        int(item["boundary_cisd_contradictions"]) for item in reports
    )
    per_session: dict[str, Counter[str]] = {}
    for report in reports:
        session = str(report["session"])
        counter = per_session.setdefault(session, Counter())
        for key in (
            "cisd_first_blockers",
            "true_same_bar_cisd_only",
            "same_bar_boundary_missing_only",
            "other_cisd_first_blocker",
            "true_cisd_only_aligned",
        ):
            counter[key] += int(report[key])

    return {
        "identity": MATRIX_IDENTITY,
        "market_count": 9,
        "cisd_first_blockers": total,
        "cisd_control_reproduced": total == EXPECTED_CISD_FIRST_BLOCKERS,
        "true_same_bar_cisd_only": true_count,
        "same_bar_boundary_missing_only": missing,
        "other_cisd_first_blocker": other,
        "partition_reproduced": total == true_count + missing + other,
        "true_cisd_only_aligned": aligned,
        "true_cisd_only_aligned_rate": (
            None
            if true_count == 0
            else str(Decimal(aligned) / Decimal(true_count))
        ),
        "step4_aligned_substitute_confirmations": (
            STEP4_EXPECTED_ALIGNED_SUBSTITUTE_CONFIRMATIONS
        ),
        "step4_reconciliation": (
            aligned == STEP4_EXPECTED_ALIGNED_SUBSTITUTE_CONFIRMATIONS
        ),
        "boundary_cisd_contradictions": contradictions,
        "per_session": {
            key: dict(value) for key, value in sorted(per_session.items())
        },
        "markets": sorted(reports, key=lambda item: str(item["symbol"])),
        "v1_reservoir_inflation_corrected": True,
        "cisd_boundary_required_for_true_cisd_only": True,
        "strategy_mutated": False,
        "outcome_used_for_admission": False,
        "diagnostic_only": True,
        "economic_candidate": False,
    }


def write_matrix(report: dict[str, Any], output: Path) -> None:
    output.mkdir(parents=True, exist_ok=True)
    path = (
        output
        / "capitalizer-nine-market-v3-cisd-counterfactual-census-2y-v2.json"
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
