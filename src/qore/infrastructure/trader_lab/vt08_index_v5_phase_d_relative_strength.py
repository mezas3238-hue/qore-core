"""VT-08 Index V5 Phase D preregistered relative-strength falsification."""
from __future__ import annotations

import argparse
import csv
import json
from collections.abc import Sequence
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

PRIMARY_FRICTION = Decimal("0.05")
SECONDARY_FRICTION = Decimal("0.10")
WINDOWS = ("2022_23", "2023_24", "2024_26")
MARKETS = ("NAS100", "SP500", "US30")
SIDES = ("long", "short")


def _r(row: dict[str, str]) -> Decimal:
    value = row.get("outcome_r")
    if value is None or value == "":
        raise ValueError("missing outcome_r")
    return Decimal(value)


def _retain_d1(row: dict[str, str]) -> bool:
    """Frozen D1 predicate: two same-side signals, zero opposite signals."""
    return (
        int(row["cross_index_simultaneous_same_side_signals"]) == 2
        and int(row["cross_index_simultaneous_opposite_side_signals"]) == 0
    )


def _max_drawdown(values: Sequence[Decimal]) -> Decimal:
    equity = Decimal(0)
    peak = Decimal(0)
    worst = Decimal(0)
    for value in values:
        equity += value
        if equity > peak:
            peak = equity
        drawdown = peak - equity
        if drawdown > worst:
            worst = drawdown
    return worst


def _profit_factor(values: Sequence[Decimal]) -> Decimal | None:
    gains = sum((value for value in values if value > 0), Decimal(0))
    losses = -sum((value for value in values if value < 0), Decimal(0))
    if losses == 0:
        return None
    return gains / losses


def _metrics(rows: Sequence[dict[str, str]], friction: Decimal) -> dict[str, Any]:
    values = [_r(row) - friction for row in rows]
    total = sum(values, Decimal(0))
    ordered = sorted(values)
    median: Decimal | None = None
    if ordered:
        middle = len(ordered) // 2
        if len(ordered) % 2:
            median = ordered[middle]
        else:
            median = (ordered[middle - 1] + ordered[middle]) / Decimal(2)
    pf = _profit_factor(values)
    return {
        "n": len(values),
        "wins": sum(value > 0 for value in values),
        "losses": sum(value < 0 for value in values),
        "flats": sum(value == 0 for value in values),
        "total_r": str(total),
        "mean_r": str(total / Decimal(len(values))) if values else None,
        "median_r": str(median) if median is not None else None,
        "profit_factor": str(pf) if pf is not None else None,
        "max_drawdown_r": str(_max_drawdown(values)),
    }


def _by_value(
    rows: Sequence[dict[str, str]], feature: str, friction: Decimal
) -> dict[str, Any]:
    values = sorted({row[feature] for row in rows})
    return {
        value: _metrics([row for row in rows if row[feature] == value], friction)
        for value in values
    }


def _chunks(
    rows: Sequence[dict[str, str]], parts: int
) -> list[list[dict[str, str]]]:
    if parts < 1:
        raise ValueError("parts must be positive")
    size = len(rows)
    chunks: list[list[dict[str, str]]] = []
    start = 0
    for index in range(parts):
        remaining_parts = parts - index
        remaining_rows = size - start
        take = (remaining_rows + remaining_parts - 1) // remaining_parts
        chunks.append(list(rows[start : start + take]))
        start += take
    return chunks


def _half_year(signal_at: str) -> str:
    timestamp = datetime.fromisoformat(signal_at.replace("Z", "+00:00"))
    return f"{timestamp.year}-H{1 if timestamp.month <= 6 else 2}"


def _positive_mean(metrics: dict[str, Any]) -> bool:
    value = metrics["mean_r"]
    return value is not None and Decimal(str(value)) > 0


def _pf_at_least(metrics: dict[str, Any], threshold: Decimal) -> bool:
    value = metrics["profit_factor"]
    return value is not None and Decimal(str(value)) >= threshold


def _gate_report(
    retained: Sequence[dict[str, str]], primary: dict[str, Any], secondary: dict[str, Any]
) -> dict[str, bool]:
    by_window = primary["by_window"]
    by_market = primary["by_market"]
    by_side = primary["by_side"]
    halves = primary["chronological_halves"]
    quartiles = primary["chronological_quartiles"]
    leave_one_out = primary["leave_one_market_out"]
    half_years = primary["half_year_blocks"]
    aggregate = primary["aggregate"]
    secondary_aggregate = secondary["aggregate"]

    gates = {
        "sample_at_least_60": len(retained) >= 60,
        "all_windows_supported_and_positive": all(
            by_window[window]["n"] >= 10 and _positive_mean(by_window[window])
            for window in WINDOWS
        ),
        "aggregate_mean_at_least_0_10r": Decimal(str(aggregate["mean_r"]))
        >= Decimal("0.10"),
        "aggregate_pf_at_least_1_20": _pf_at_least(aggregate, Decimal("1.20")),
        "aggregate_max_dd_at_most_10r": Decimal(str(aggregate["max_drawdown_r"]))
        <= Decimal("10"),
        "both_halves_positive": all(_positive_mean(item) for item in halves.values()),
        "three_of_four_quartiles_positive": sum(
            _positive_mean(item) for item in quartiles.values()
        )
        >= 3,
        "supported_markets_positive": all(
            item["n"] < 10 or _positive_mean(item) for item in by_market.values()
        ),
        "supported_sides_positive": all(
            item["n"] < 15 or _positive_mean(item) for item in by_side.values()
        ),
        "leave_one_market_out_positive": all(
            _positive_mean(item) for item in leave_one_out.values()
        ),
        "secondary_0_10r_positive": _positive_mean(secondary_aggregate)
        and _pf_at_least(secondary_aggregate, Decimal("1.0000000001")),
        "no_supported_negative_half_year": all(
            item["n"] < 10 or _positive_mean(item) for item in half_years.values()
        ),
    }
    return gates


def _analysis(
    retained: Sequence[dict[str, str]], friction: Decimal
) -> dict[str, Any]:
    ordered = sorted(retained, key=lambda row: row["signal_at"])
    halves = _chunks(ordered, 2)
    quartiles = _chunks(ordered, 4)
    half_year_labels = sorted({_half_year(row["signal_at"]) for row in ordered})
    return {
        "friction_r_per_trade": str(friction),
        "aggregate": _metrics(ordered, friction),
        "by_window": {
            window: _metrics(
                [row for row in ordered if row["window_id"] == window], friction
            )
            for window in WINDOWS
        },
        "by_market": _by_value(ordered, "symbol", friction),
        "by_side": _by_value(ordered, "side", friction),
        "by_anchor": _by_value(ordered, "anchor", friction),
        "by_closure": _by_value(ordered, "closure_family", friction),
        "chronological_halves": {
            f"half_{index + 1}": _metrics(chunk, friction)
            for index, chunk in enumerate(halves)
        },
        "chronological_quartiles": {
            f"quartile_{index + 1}": _metrics(chunk, friction)
            for index, chunk in enumerate(quartiles)
        },
        "half_year_blocks": {
            label: _metrics(
                [row for row in ordered if _half_year(row["signal_at"]) == label],
                friction,
            )
            for label in half_year_labels
        },
        "leave_one_market_out": {
            f"without_{market}": _metrics(
                [row for row in ordered if row["symbol"] != market], friction
            )
            for market in MARKETS
        },
    }


def run(census_csv: Path, output_json: Path) -> dict[str, Any]:
    with census_csv.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    if len(rows) != 183:
        raise ValueError("Phase D requires exactly the frozen 183-row census")
    if set(row["window_id"] for row in rows) != set(WINDOWS):
        raise ValueError("Phase D census windows drifted")
    if set(row["symbol"] for row in rows) != set(MARKETS):
        raise ValueError("Phase D market scope drifted")
    if set(row["side"] for row in rows) != set(SIDES):
        raise ValueError("Phase D side scope drifted")

    retained = [row for row in rows if _retain_d1(row)]
    primary = _analysis(retained, PRIMARY_FRICTION)
    secondary = _analysis(retained, SECONDARY_FRICTION)
    gates = _gate_report(retained, primary, secondary)
    passed = all(gates.values())
    report = {
        "schema": "qore.trader_lab.vt08_index_v5_phase_d_relative_strength.v1",
        "phase": "V5_PHASE_D_RELATIVE_STRENGTH",
        "hypothesis_id": "D1_PEER_CONFIRMATION_ONE_NONCONFIRMATION",
        "contract": "consumed-evidence-only; sealed holdout; preregistered predicate",
        "input_sample": len(rows),
        "retained_sample": len(retained),
        "predicate": {
            "cross_index_simultaneous_same_side_signals": 2,
            "cross_index_simultaneous_opposite_side_signals": 0,
        },
        "primary": primary,
        "secondary": secondary,
        "gates": gates,
        "adjudication": "PHASE_D_D1_PASS" if passed else "PHASE_D_D1_REJECT",
        "candidate_freeze_permitted": passed,
        "holdout_open_permitted": False,
        "live_authorized": False,
        "real_capital_authorized": False,
        "production_authorized": False,
    }
    output_json.parent.mkdir(parents=True, exist_ok=True)
    output_json.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--census-csv", type=Path, required=True)
    parser.add_argument("--output-json", type=Path, required=True)
    args = parser.parse_args()
    run(args.census_csv, args.output_json)


if __name__ == "__main__":
    main()
