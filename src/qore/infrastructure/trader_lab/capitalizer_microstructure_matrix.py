"""Aggregate QORE Capitalizer per-market M5 microstructure summaries.

Research-only matrix. It compares the exact same descriptive scanner across all frozen
session-market cells. It does not rank markets, select a strategy, or authorize promotion.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from decimal import Decimal
from pathlib import Path
from typing import Any

from qore.infrastructure.trader_lab.capitalizer_contract import (
    CapitalizerSession,
    allowed_markets,
)
from qore.infrastructure.trader_lab.capitalizer_microstructure_discovery import (
    CapitalizerMicrostructureEvent,
)


@dataclass(frozen=True, slots=True)
class CapitalizerMicrostructureCell:
    session: CapitalizerSession
    symbol: str
    observations: int
    event_counts: dict[str, int]
    event_rates: dict[str, str]
    median_range_price: str
    median_body_fraction: str
    median_previous_range_ratio: str | None


@dataclass(frozen=True, slots=True)
class CapitalizerMicrostructureMatrix:
    identity: str
    cells: tuple[CapitalizerMicrostructureCell, ...]
    total_observations: int
    session_observations: dict[str, int]
    complete_frozen_universe: bool
    research_only: bool = True
    rule_promotion_allowed: bool = False


def _load_summary(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"microstructure summary must be object: {path}")
    if payload.get("identity") != "QORE_CAPITALIZER_M5_MICROSTRUCTURE_DISCOVERY_V1":
        raise ValueError(f"unexpected microstructure identity: {path}")
    if payload.get("research_only") is not True:
        raise ValueError(f"microstructure source must remain research-only: {path}")
    if payload.get("rule_promotion_allowed") is not False:
        raise ValueError(f"microstructure source cannot allow rule promotion: {path}")
    return payload


def build_microstructure_matrix(root: Path) -> CapitalizerMicrostructureMatrix:
    """Aggregate one exact summary for every frozen session-market cell."""

    paths = sorted(root.rglob("capitalizer-*-microstructure-v1.json"))
    if not paths:
        raise ValueError("no Capitalizer microstructure summaries found")

    cells: list[CapitalizerMicrostructureCell] = []
    seen: set[tuple[CapitalizerSession, str]] = set()
    for path in paths:
        payload = _load_summary(path)
        symbol = payload.get("symbol")
        session_raw = payload.get("session")
        if not isinstance(symbol, str) or not isinstance(session_raw, str):
            raise ValueError("microstructure summary requires symbol/session")
        session = CapitalizerSession(session_raw)
        if symbol not in allowed_markets(session):
            raise ValueError(f"summary cell outside frozen universe: {session.value}:{symbol}")
        key = (session, symbol)
        if key in seen:
            raise ValueError(f"duplicate microstructure cell: {session.value}:{symbol}")
        seen.add(key)

        event_counts_raw = payload.get("event_counts")
        event_rates_raw = payload.get("event_rates")
        if not isinstance(event_counts_raw, dict) or not isinstance(event_rates_raw, dict):
            raise ValueError("summary requires event counts/rates")
        expected_events = {event.value for event in CapitalizerMicrostructureEvent}
        if set(event_counts_raw) != expected_events or set(event_rates_raw) != expected_events:
            raise ValueError("summary event universe must be exact")

        observations = int(payload.get("observations", 0))
        if observations <= 0:
            raise ValueError(f"summary must contain observations: {session.value}:{symbol}")
        for event in expected_events:
            count = int(event_counts_raw[event])
            rate = Decimal(str(event_rates_raw[event]))
            if count < 0 or not Decimal("0") <= rate <= Decimal("1"):
                raise ValueError("event count/rate outside legal bounds")
            expected_rate = Decimal(count) / Decimal(observations)
            if rate != expected_rate:
                raise ValueError("event rate must exactly equal count / observations")

        cells.append(
            CapitalizerMicrostructureCell(
                session=session,
                symbol=symbol,
                observations=observations,
                event_counts={key: int(value) for key, value in event_counts_raw.items()},
                event_rates={key: str(value) for key, value in event_rates_raw.items()},
                median_range_price=str(payload.get("median_range_price")),
                median_body_fraction=str(payload.get("median_body_fraction")),
                median_previous_range_ratio=(
                    None
                    if payload.get("median_previous_range_ratio") is None
                    else str(payload.get("median_previous_range_ratio"))
                ),
            )
        )

    expected = {
        (session, symbol)
        for session in CapitalizerSession
        for symbol in allowed_markets(session)
    }
    complete = seen == expected
    if not complete:
        missing = sorted(f"{session.value}:{symbol}" for session, symbol in expected - seen)
        extra = sorted(f"{session.value}:{symbol}" for session, symbol in seen - expected)
        raise ValueError(f"microstructure matrix coverage mismatch missing={missing} extra={extra}")

    canonical = tuple(sorted(cells, key=lambda item: (item.session.value, item.symbol)))
    session_observations = {
        session.value: sum(
            cell.observations for cell in canonical if cell.session is session
        )
        for session in CapitalizerSession
    }
    return CapitalizerMicrostructureMatrix(
        identity="QORE_CAPITALIZER_MICROSTRUCTURE_MATRIX_V1",
        cells=canonical,
        total_observations=sum(cell.observations for cell in canonical),
        session_observations=session_observations,
        complete_frozen_universe=True,
    )


def write_microstructure_matrix(
    matrix: CapitalizerMicrostructureMatrix,
    output: Path,
) -> None:
    output.mkdir(parents=True, exist_ok=True)
    json_path = output / "capitalizer-microstructure-matrix-v1.json"
    md_path = output / "capitalizer-microstructure-matrix-v1.md"
    payload = asdict(matrix)
    for cell in payload["cells"]:
        cell["session"] = cell["session"].value
    json_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    lines = [
        "# QORE Capitalizer — Microstructure Matrix V1",
        "",
        f"- Cells: {len(matrix.cells)}",
        f"- Total observations: {matrix.total_observations:,}",
        "- Evidence status: CONSUMED_RESEARCH_EVIDENCE",
        "- Rule promotion allowed: NO",
        "",
        "| Session | Market | Observations | High raid rejection | Low raid rejection | High acceptance | Low acceptance |",
        "|---|---|---:|---:|---:|---:|---:|",
    ]
    for cell in matrix.cells:
        rates = cell.event_rates
        lines.append(
            f"| {cell.session.value} | {cell.symbol} | {cell.observations:,} | "
            f"{rates['HIGH_RAID_REJECTION']} | {rates['LOW_RAID_REJECTION']} | "
            f"{rates['HIGH_ACCEPTANCE']} | {rates['LOW_ACCEPTANCE']} |"
        )
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Capitalizer 9-cell microstructure matrix")
    parser.add_argument("input_root", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    matrix = build_microstructure_matrix(args.input_root)
    write_microstructure_matrix(matrix, args.output)
    print(json.dumps({"identity": matrix.identity, "cells": len(matrix.cells), "total_observations": matrix.total_observations}, sort_keys=True))


if __name__ == "__main__":
    main()
