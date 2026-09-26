"""Nine-market matrix for causal Target V2 capacity diagnostics.

This aggregation is descriptive consumed-evidence research. It does not introduce a minimum-R
threshold, rank markets, define a final stop, simulate execution, or create an economic candidate.
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
    HYPOTHESIS_ID,
)
from qore.infrastructure.trader_lab.capitalizer_contract import (
    CapitalizerSession,
    allowed_markets,
)
from qore.infrastructure.trader_lab.capitalizer_target_capacity_forensics import (
    IDENTITY as FORENSICS_IDENTITY,
)

IDENTITY = "QORE_CAPITALIZER_TARGET_CAPACITY_MATRIX_V1"


@dataclass(frozen=True, slots=True)
class CapitalizerTargetCapacityMatrixCell:
    session: CapitalizerSession
    symbol: str
    aligned_departure_events: int
    geometry_observations: int
    geometry_coverage: str
    median_active_candidate_count: str
    median_capacity_r: str
    p25_capacity_r: str
    p75_capacity_r: str


@dataclass(frozen=True, slots=True)
class CapitalizerTargetCapacityMatrix:
    identity: str
    hypothesis_id: str
    market_count: int
    complete_frozen_universe: bool
    cells: tuple[CapitalizerTargetCapacityMatrixCell, ...]
    aligned_departure_events: int
    geometry_observations: int
    median_market_geometry_coverage: str
    median_market_capacity_r: str
    evidence_status: str = "CONSUMED_RESEARCH_EVIDENCE"
    minimum_r_filter_defined: bool = False
    final_stop_contract_defined: bool = False
    target_outcomes_used: bool = False
    economic_candidate: bool = False
    rule_promotion_allowed: bool = False


def _load(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"target-capacity report must be object: {path}")
    if payload.get("identity") != FORENSICS_IDENTITY:
        raise ValueError(f"unexpected target-capacity identity: {path}")
    if payload.get("hypothesis_id") != HYPOTHESIS_ID:
        raise ValueError(f"unexpected hypothesis identity: {path}")
    if payload.get("evidence_status") != "CONSUMED_RESEARCH_EVIDENCE":
        raise ValueError(f"target-capacity evidence must remain consumed: {path}")
    for field in (
        "minimum_r_filter_defined",
        "final_stop_contract_defined",
        "target_outcomes_used",
        "economic_candidate",
        "rule_promotion_allowed",
    ):
        if payload.get(field) is not False:
            raise ValueError(f"{field} must remain false: {path}")
    return payload


def build_target_capacity_matrix(root: Path) -> CapitalizerTargetCapacityMatrix:
    paths = sorted(root.rglob("capitalizer-*-target-capacity-v1.json"))
    if not paths:
        raise ValueError("no target-capacity reports found")

    seen: set[tuple[CapitalizerSession, str]] = set()
    cells: list[CapitalizerTargetCapacityMatrixCell] = []
    for path in paths:
        payload = _load(path)
        symbol = str(payload["symbol"])
        session = CapitalizerSession(str(payload["session"]))
        if symbol not in allowed_markets(session):
            raise ValueError(f"market outside frozen universe: {session.value}:{symbol}")
        key = (session, symbol)
        if key in seen:
            raise ValueError(f"duplicate target-capacity market: {session.value}:{symbol}")
        seen.add(key)
        total = payload["total"]
        cells.append(
            CapitalizerTargetCapacityMatrixCell(
                session=session,
                symbol=symbol,
                aligned_departure_events=int(payload["aligned_departure_events"]),
                geometry_observations=int(payload["geometry_observations"]),
                geometry_coverage=str(payload["geometry_coverage"]),
                median_active_candidate_count=str(
                    total["median_active_candidate_count"]
                ),
                median_capacity_r=str(total["median_capacity_r"]),
                p25_capacity_r=str(total["p25_capacity_r"]),
                p75_capacity_r=str(total["p75_capacity_r"]),
            )
        )

    expected = {
        (session, symbol)
        for session in CapitalizerSession
        for symbol in allowed_markets(session)
    }
    if seen != expected:
        missing = sorted(f"{s.value}:{m}" for s, m in expected - seen)
        extra = sorted(f"{s.value}:{m}" for s, m in seen - expected)
        raise ValueError(f"target-capacity coverage mismatch missing={missing} extra={extra}")

    canonical = tuple(sorted(cells, key=lambda item: (item.session.value, item.symbol)))
    return CapitalizerTargetCapacityMatrix(
        identity=IDENTITY,
        hypothesis_id=HYPOTHESIS_ID,
        market_count=len(canonical),
        complete_frozen_universe=True,
        cells=canonical,
        aligned_departure_events=sum(item.aligned_departure_events for item in canonical),
        geometry_observations=sum(item.geometry_observations for item in canonical),
        median_market_geometry_coverage=str(
            median(Decimal(item.geometry_coverage) for item in canonical)
        ),
        median_market_capacity_r=str(
            median(Decimal(item.median_capacity_r) for item in canonical)
        ),
    )


def write_target_capacity_matrix(
    matrix: CapitalizerTargetCapacityMatrix,
    output: Path,
) -> None:
    output.mkdir(parents=True, exist_ok=True)
    json_path = output / "capitalizer-target-capacity-matrix-v1.json"
    md_path = output / "capitalizer-target-capacity-matrix-v1.md"
    payload: dict[str, Any] = asdict(matrix)
    for cell in payload["cells"]:
        cell["session"] = cell["session"].value
    json_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    lines = [
        "# QORE Capitalizer — Target Capacity Matrix V1",
        "",
        f"- Hypothesis: {matrix.hypothesis_id}",
        f"- Markets: {matrix.market_count}",
        f"- Aligned departures: {matrix.aligned_departure_events:,}",
        f"- Geometry observations: {matrix.geometry_observations:,}",
        f"- Median market capacity: {matrix.median_market_capacity_r}R",
        "- Minimum-R filter defined: NO",
        "- Final stop contract defined: NO",
        "- Target outcomes used: NO",
        "- Economic candidate: NO",
        "",
        "| Session | Market | Aligned | Geometry | Coverage | Median candidates | "
        "P25 R | Median R | P75 R |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for cell in matrix.cells:
        lines.append(
            f"| {cell.session.value} | {cell.symbol} | "
            f"{cell.aligned_departure_events} | {cell.geometry_observations} | "
            f"{cell.geometry_coverage} | {cell.median_active_candidate_count} | "
            f"{cell.p25_capacity_r} | {cell.median_capacity_r} | "
            f"{cell.p75_capacity_r} |"
        )
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Capitalizer nine-market target-capacity matrix")
    parser.add_argument("input_root", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    matrix = build_target_capacity_matrix(args.input_root)
    write_target_capacity_matrix(matrix, args.output)
    print(
        json.dumps(
            {
                "identity": matrix.identity,
                "market_count": matrix.market_count,
                "aligned_departure_events": matrix.aligned_departure_events,
                "geometry_observations": matrix.geometry_observations,
                "median_market_capacity_r": matrix.median_market_capacity_r,
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
