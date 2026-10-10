"""Cross-market matrix for the frozen Capitalizer/CIBO departure-alignment hypothesis.

The matrix aggregates independently generated per-market forensics. It reports stability and
contrast with no-exact-context/opposed departure observations, but does not rank markets,
select parameters, freeze a trading candidate, or authorize promotion.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from decimal import Decimal
from pathlib import Path
from statistics import median
from typing import Any

from qore.infrastructure.trader_lab.capitalizer_cibo_departure_hypothesis import (
    FROZEN_DEPARTURE_ALIGNMENT_HYPOTHESIS,
    HYPOTHESIS_ID,
)
from qore.infrastructure.trader_lab.capitalizer_contract import (
    CapitalizerSession,
    allowed_markets,
)

FORENSICS_IDENTITY = "QORE_CAPITALIZER_CIBO_ALIGNMENT_FORENSICS_V1"
MATRIX_IDENTITY = "QORE_CAPITALIZER_CIBO_DEPARTURE_ALIGNMENT_MATRIX_V1"


@dataclass(frozen=True, slots=True)
class CapitalizerDepartureAlignmentCell:
    session: CapitalizerSession
    symbol: str
    event: str
    aligned_observations: int
    aligned_positive_close_rate: str
    aligned_median_close_range_units: str
    baseline_observations: int
    baseline_positive_close_rate: str
    baseline_median_close_range_units: str
    opposed_observations: int | None
    opposed_positive_close_rate: str | None
    opposed_median_close_range_units: str | None
    annual_years_with_min_sample: int
    annual_years_positive_median: int


@dataclass(frozen=True, slots=True)
class CapitalizerDepartureAlignmentMatrix:
    identity: str
    hypothesis_id: str
    market_count: int
    event_cell_count: int
    complete_frozen_universe: bool
    cells: tuple[CapitalizerDepartureAlignmentCell, ...]
    aligned_total_observations: int
    aligned_market_event_cells_positive_median: int
    aligned_market_event_cells: int
    median_aligned_positive_close_rate: str
    median_baseline_positive_close_rate: str
    evidence_status: str = "CONSUMED_RESEARCH_EVIDENCE"
    economic_candidate: bool = False
    rule_promotion_allowed: bool = False
    fresh_holdout_claimed: bool = False


def _load_report(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"forensics report must be object: {path}")
    if payload.get("identity") != FORENSICS_IDENTITY:
        raise ValueError(f"unexpected forensics identity: {path}")
    if payload.get("evidence_status") != "CONSUMED_RESEARCH_EVIDENCE":
        raise ValueError(f"forensics evidence must remain consumed: {path}")
    if payload.get("context_fields_causal") is not True:
        raise ValueError(f"context must remain causal: {path}")
    if payload.get("outcome_fields_causal") is not False:
        raise ValueError(f"outcomes must remain non-causal: {path}")
    if payload.get("lookback_tuning_used") is not False:
        raise ValueError(f"lookback tuning is prohibited: {path}")
    if payload.get("rule_promotion_allowed") is not False:
        raise ValueError(f"rule promotion must remain false: {path}")
    return payload


def _row(
    payload: dict[str, Any],
    *,
    event: str,
    tag: str,
) -> dict[str, Any] | None:
    aggregates = payload.get("aggregates")
    if not isinstance(aggregates, list):
        raise ValueError("forensics aggregates must be a list")
    for raw in aggregates:
        if not isinstance(raw, dict):
            raise ValueError("forensics aggregate row must be an object")
        row: dict[str, Any] = raw
        if (
            row.get("event") == event
            and row.get("context_tag") == tag
            and int(row.get("horizon_minutes", 0)) == 15
        ):
            return row
    return None


def build_departure_alignment_matrix(
    root: Path,
    *,
    annual_min_sample: int = 20,
) -> CapitalizerDepartureAlignmentMatrix:
    if annual_min_sample != 20:
        raise ValueError("annual stability minimum sample is frozen at 20")

    FROZEN_DEPARTURE_ALIGNMENT_HYPOTHESIS.__post_init__()
    reports = sorted(root.rglob("capitalizer-*-cibo-alignment-v1.json"))
    if not reports:
        raise ValueError("no CIBO alignment reports found")

    seen_markets: set[tuple[CapitalizerSession, str]] = set()
    cells: list[CapitalizerDepartureAlignmentCell] = []
    aligned_rates: list[Decimal] = []
    baseline_rates: list[Decimal] = []

    for path in reports:
        payload = _load_report(path)
        symbol = str(payload["symbol"])
        session = CapitalizerSession(str(payload["session"]))
        if symbol not in allowed_markets(session):
            raise ValueError(f"market outside frozen universe: {session.value}:{symbol}")
        key = (session, symbol)
        if key in seen_markets:
            raise ValueError(f"duplicate market report: {session.value}:{symbol}")
        seen_markets.add(key)

        annual_rows = payload["annual"]
        for event in FROZEN_DEPARTURE_ALIGNMENT_HYPOTHESIS.capitalizer_event_family:
            aligned = _row(payload, event=event, tag="DEPARTURE_ALIGNED_H1")
            baseline = _row(payload, event=event, tag="NO_EXACT_CIBO_EVENT")
            opposed = _row(payload, event=event, tag="DEPARTURE_OPPOSED_H1")
            if aligned is None or baseline is None:
                raise ValueError(f"missing aligned/baseline row: {symbol}:{event}")

            annual = [
                row
                for row in annual_rows
                if row["event"] == event
                and row["context_tag"] == "DEPARTURE_ALIGNED_H1"
                and int(row["horizon_minutes"]) == 15
                and int(row["observations"]) >= annual_min_sample
            ]
            positive_years = sum(
                Decimal(str(row["median_close_displacement_range_units"])) > 0
                for row in annual
            )
            aligned_rate = Decimal(str(aligned["positive_close_rate"]))
            baseline_rate = Decimal(str(baseline["positive_close_rate"]))
            aligned_rates.append(aligned_rate)
            baseline_rates.append(baseline_rate)
            cells.append(
                CapitalizerDepartureAlignmentCell(
                    session=session,
                    symbol=symbol,
                    event=event,
                    aligned_observations=int(aligned["observations"]),
                    aligned_positive_close_rate=str(aligned_rate),
                    aligned_median_close_range_units=str(
                        aligned["median_close_displacement_range_units"]
                    ),
                    baseline_observations=int(baseline["observations"]),
                    baseline_positive_close_rate=str(baseline_rate),
                    baseline_median_close_range_units=str(
                        baseline["median_close_displacement_range_units"]
                    ),
                    opposed_observations=(
                        None if opposed is None else int(opposed["observations"])
                    ),
                    opposed_positive_close_rate=(
                        None if opposed is None else str(opposed["positive_close_rate"])
                    ),
                    opposed_median_close_range_units=(
                        None
                        if opposed is None
                        else str(opposed["median_close_displacement_range_units"])
                    ),
                    annual_years_with_min_sample=len(annual),
                    annual_years_positive_median=positive_years,
                )
            )

    expected = {
        (session, symbol)
        for session in CapitalizerSession
        for symbol in allowed_markets(session)
    }
    if seen_markets != expected:
        missing = sorted(f"{s.value}:{m}" for s, m in expected - seen_markets)
        extra = sorted(f"{s.value}:{m}" for s, m in seen_markets - expected)
        raise ValueError(f"matrix coverage mismatch missing={missing} extra={extra}")

    canonical = tuple(sorted(cells, key=lambda item: (item.session.value, item.symbol, item.event)))
    positive_cells = sum(
        Decimal(item.aligned_median_close_range_units) > 0 for item in canonical
    )
    return CapitalizerDepartureAlignmentMatrix(
        identity=MATRIX_IDENTITY,
        hypothesis_id=HYPOTHESIS_ID,
        market_count=len(seen_markets),
        event_cell_count=len(canonical),
        complete_frozen_universe=True,
        cells=canonical,
        aligned_total_observations=sum(item.aligned_observations for item in canonical),
        aligned_market_event_cells_positive_median=positive_cells,
        aligned_market_event_cells=len(canonical),
        median_aligned_positive_close_rate=str(median(aligned_rates)),
        median_baseline_positive_close_rate=str(median(baseline_rates)),
    )


def write_departure_alignment_matrix(
    matrix: CapitalizerDepartureAlignmentMatrix,
    output: Path,
) -> None:
    output.mkdir(parents=True, exist_ok=True)
    json_path = output / "capitalizer-cibo-departure-alignment-matrix-v1.json"
    md_path = output / "capitalizer-cibo-departure-alignment-matrix-v1.md"
    payload: dict[str, Any] = asdict(matrix)
    for cell in payload["cells"]:
        cell["session"] = cell["session"].value
    json_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    lines = [
        "# QORE Capitalizer — CIBO Departure Alignment Matrix V1",
        "",
        f"- Hypothesis: {matrix.hypothesis_id}",
        f"- Markets: {matrix.market_count}",
        f"- Market/event cells: {matrix.event_cell_count}",
        f"- Aligned observations: {matrix.aligned_total_observations:,}",
        (
            "- Positive aligned median cells: "
            f"{matrix.aligned_market_event_cells_positive_median}/"
            f"{matrix.aligned_market_event_cells}"
        ),
        "- Evidence: CONSUMED_RESEARCH_EVIDENCE",
        "- Economic candidate: NO",
        "- Rule promotion allowed: NO",
        "",
        "| Session | Market | Event | Aligned n | Aligned +close | Aligned median | "
        "Baseline +close | Baseline median | Annual +median |",
        "|---|---|---|---:|---:|---:|---:|---:|---:|",
    ]
    for cell in matrix.cells:
        lines.append(
            f"| {cell.session.value} | {cell.symbol} | {cell.event} | "
            f"{cell.aligned_observations} | {cell.aligned_positive_close_rate} | "
            f"{cell.aligned_median_close_range_units} | "
            f"{cell.baseline_positive_close_rate} | "
            f"{cell.baseline_median_close_range_units} | "
            f"{cell.annual_years_positive_median}/{cell.annual_years_with_min_sample} |"
        )
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Capitalizer 9-market CIBO departure matrix")
    parser.add_argument("input_root", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    matrix = build_departure_alignment_matrix(args.input_root)
    write_departure_alignment_matrix(matrix, args.output)
    print(
        json.dumps(
            {
                "identity": matrix.identity,
                "hypothesis_id": matrix.hypothesis_id,
                "market_count": matrix.market_count,
                "event_cell_count": matrix.event_cell_count,
                "aligned_total_observations": matrix.aligned_total_observations,
                "positive_median_cells": matrix.aligned_market_event_cells_positive_median,
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
