"""Aggregate nine-market economic falsification for QORE Capitalizer."""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from decimal import Decimal
from pathlib import Path
from statistics import median
from typing import Any

from qore.infrastructure.trader_lab.capitalizer_contract import (
    CapitalizerSession,
    allowed_markets,
)

IDENTITY = "QORE_CAPITALIZER_CROSS_MARKET_ECONOMIC_MATRIX_V1"
CELL_IDENTITY = "QORE_CAPITALIZER_CROSS_MARKET_ECONOMIC_FALSIFICATION_V1"
PROFIT_LOCK = "STRUCTURAL_V2_PROFITABLE_SWING_LOCK"
TIMING_LOCK = "DROP_NORECLAIM_CISD_CROSS_H1_PROFITABLE_SWING_LOCK"


@dataclass(frozen=True, slots=True)
class CapitalizerCrossMarketEconomicCell:
    symbol: str
    session: str
    structural_trades: int
    structural_profit_factor: str | None
    structural_max_drawdown_r: str
    profit_lock_profit_factor: str | None
    profit_lock_max_drawdown_r: str
    timing_lock_trades: int
    timing_excluded_trades: int
    timing_lock_profit_factor: str | None
    timing_lock_max_drawdown_r: str
    timing_lock_total_gross_r: str
    timing_lock_all_years_positive: bool


@dataclass(frozen=True, slots=True)
class CapitalizerCrossMarketEconomicMatrix:
    identity: str
    market_count: int
    complete_frozen_universe: bool
    cells: tuple[CapitalizerCrossMarketEconomicCell, ...]
    profit_lock_dd_improved_markets: int
    timing_lock_dd_improved_vs_profit_lock_markets: int
    timing_lock_pf_improved_vs_profit_lock_markets: int
    timing_lock_positive_total_markets: int
    timing_lock_all_years_positive_markets: int
    total_timing_excluded_trades: int
    median_profit_lock_pf: str
    median_profit_lock_dd_r: str
    median_timing_lock_pf: str
    median_timing_lock_dd_r: str
    evidence_status: str = "CONSUMED_RESEARCH_EVIDENCE"
    cross_market_falsification_only: bool = True
    market_specific_tuning_used: bool = False
    numeric_threshold_optimization_used: bool = False
    candidate_frozen: bool = False
    fresh_holdout_claimed: bool = False
    rule_selected: bool = False
    promotion_allowed: bool = False


def _load(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("economic falsification report must be object")
    if payload.get("identity") != CELL_IDENTITY:
        raise ValueError("unexpected economic falsification identity")
    if payload.get("evidence_status") != "CONSUMED_RESEARCH_EVIDENCE":
        raise ValueError("economic falsification must remain consumed")
    if payload.get("cross_market_falsification_only") is not True:
        raise ValueError("cell must remain falsification-only")
    if payload.get("market_specific_tuning_used") is not False:
        raise ValueError("market-specific tuning is prohibited")
    if payload.get("numeric_threshold_optimization_used") is not False:
        raise ValueError("numeric threshold optimization is prohibited")
    if payload.get("candidate_frozen") is not False:
        raise ValueError("cell cannot freeze candidate")
    if payload.get("fresh_holdout_claimed") is not False:
        raise ValueError("cell cannot claim fresh holdout")
    if payload.get("rule_selected") is not False:
        raise ValueError("cell cannot select rule")
    if payload.get("promotion_allowed") is not False:
        raise ValueError("cell cannot promote")
    return payload


def _variant(payload: dict[str, Any], name: str) -> dict[str, Any]:
    raw = payload.get("variants")
    if not isinstance(raw, list):
        raise ValueError("variants must be list")
    for row in raw:
        if isinstance(row, dict) and row.get("name") == name:
            metrics = row.get("metrics")
            if isinstance(metrics, dict):
                return metrics
    raise ValueError(f"missing economic variant {name}")


def _pf(metrics: dict[str, Any]) -> Decimal:
    raw = metrics.get("profit_factor")
    if raw is None:
        raise ValueError("cross-market matrix requires finite profit factor")
    return Decimal(str(raw))


def _dd(metrics: dict[str, Any]) -> Decimal:
    return Decimal(str(metrics["max_drawdown_r"]))


def _all_years_positive(payload: dict[str, Any], name: str) -> bool:
    rows = [
        row
        for row in payload.get("annual", [])
        if isinstance(row, dict) and row.get("name") == name
    ]
    if not rows:
        raise ValueError("economic variant requires annual rows")
    return all(
        Decimal(str(row["metrics"]["total_gross_r"])) > 0
        for row in rows
    )


def build_cross_market_economic_matrix(root: Path) -> CapitalizerCrossMarketEconomicMatrix:
    reports = sorted(root.rglob("capitalizer-*-cross-market-economic-v1.json"))
    if not reports:
        raise ValueError("no cross-market economic reports found")

    expected = {
        (session.value, symbol)
        for session in CapitalizerSession
        for symbol in allowed_markets(session)
    }
    seen: set[tuple[str, str]] = set()
    cells: list[CapitalizerCrossMarketEconomicCell] = []
    profit_lock_pf: list[Decimal] = []
    profit_lock_dd: list[Decimal] = []
    timing_lock_pf: list[Decimal] = []
    timing_lock_dd: list[Decimal] = []

    for path in reports:
        payload = _load(path)
        symbol = str(payload["symbol"])
        session = str(payload["session"])
        key = (session, symbol)
        if key not in expected:
            raise ValueError(f"market outside frozen universe: {session}:{symbol}")
        if key in seen:
            raise ValueError(f"duplicate market: {session}:{symbol}")
        seen.add(key)

        structural = _variant(payload, "STRUCTURAL_V2")
        locked = _variant(payload, PROFIT_LOCK)
        timing = _variant(payload, TIMING_LOCK)
        locked_pf = _pf(locked)
        locked_dd = _dd(locked)
        timing_pf = _pf(timing)
        timing_dd = _dd(timing)
        profit_lock_pf.append(locked_pf)
        profit_lock_dd.append(locked_dd)
        timing_lock_pf.append(timing_pf)
        timing_lock_dd.append(timing_dd)

        cells.append(
            CapitalizerCrossMarketEconomicCell(
                symbol=symbol,
                session=session,
                structural_trades=int(structural["trades"]),
                structural_profit_factor=structural.get("profit_factor"),
                structural_max_drawdown_r=str(structural["max_drawdown_r"]),
                profit_lock_profit_factor=locked.get("profit_factor"),
                profit_lock_max_drawdown_r=str(locked["max_drawdown_r"]),
                timing_lock_trades=int(timing["trades"]),
                timing_excluded_trades=int(payload["timing_excluded_trades"]),
                timing_lock_profit_factor=timing.get("profit_factor"),
                timing_lock_max_drawdown_r=str(timing["max_drawdown_r"]),
                timing_lock_total_gross_r=str(timing["total_gross_r"]),
                timing_lock_all_years_positive=_all_years_positive(
                    payload,
                    TIMING_LOCK,
                ),
            )
        )

    if seen != expected:
        missing = sorted(f"{s}:{m}" for s, m in expected - seen)
        extra = sorted(f"{s}:{m}" for s, m in seen - expected)
        raise ValueError(f"cross-market coverage mismatch missing={missing} extra={extra}")

    canonical = tuple(sorted(cells, key=lambda row: (row.session, row.symbol)))
    return CapitalizerCrossMarketEconomicMatrix(
        identity=IDENTITY,
        market_count=len(canonical),
        complete_frozen_universe=True,
        cells=canonical,
        profit_lock_dd_improved_markets=sum(
            Decimal(row.profit_lock_max_drawdown_r)
            < Decimal(row.structural_max_drawdown_r)
            for row in canonical
        ),
        timing_lock_dd_improved_vs_profit_lock_markets=sum(
            Decimal(row.timing_lock_max_drawdown_r)
            < Decimal(row.profit_lock_max_drawdown_r)
            for row in canonical
        ),
        timing_lock_pf_improved_vs_profit_lock_markets=sum(
            row.timing_lock_profit_factor is not None
            and row.profit_lock_profit_factor is not None
            and Decimal(row.timing_lock_profit_factor)
            > Decimal(row.profit_lock_profit_factor)
            for row in canonical
        ),
        timing_lock_positive_total_markets=sum(
            Decimal(row.timing_lock_total_gross_r) > 0
            for row in canonical
        ),
        timing_lock_all_years_positive_markets=sum(
            row.timing_lock_all_years_positive
            for row in canonical
        ),
        total_timing_excluded_trades=sum(
            row.timing_excluded_trades
            for row in canonical
        ),
        median_profit_lock_pf=str(median(profit_lock_pf)),
        median_profit_lock_dd_r=str(median(profit_lock_dd)),
        median_timing_lock_pf=str(median(timing_lock_pf)),
        median_timing_lock_dd_r=str(median(timing_lock_dd)),
    )


def write_cross_market_economic_matrix(
    matrix: CapitalizerCrossMarketEconomicMatrix,
    output: Path,
) -> None:
    output.mkdir(parents=True, exist_ok=True)
    path = output / "capitalizer-cross-market-economic-matrix-v1.json"
    path.write_text(
        json.dumps(asdict(matrix), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Aggregate Capitalizer nine-market economic falsification"
    )
    parser.add_argument("input_root", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    matrix = build_cross_market_economic_matrix(args.input_root)
    write_cross_market_economic_matrix(matrix, args.output)
    print(json.dumps(asdict(matrix), sort_keys=True))


if __name__ == "__main__":
    main()
