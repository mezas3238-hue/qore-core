"""Preregistered consumed-evidence Phase-B falsification for VT-08 Index V5."""

from __future__ import annotations

import argparse
import csv
import json
from collections.abc import Callable
from decimal import Decimal
from pathlib import Path

SCHEMA = "qore.trader_lab.vt08_index_v5_phase_b_ideal_formation.v1"
PRIMARY_STRESS_R = Decimal("0.05")


def _d(value: object) -> Decimal:
    return Decimal(str(value))


def _context_direction(row: dict[str, str]) -> str | None:
    sweep = row["current_day_sweep_type"]
    mapping = {
        "high_breakout": "long",
        "low_breakout": "short",
        "high_reclaim": "short",
        "low_reclaim": "long",
    }
    return mapping.get(sweep)


def _ideal(row: dict[str, str]) -> bool:
    latency = int(row["cisd_latency_m15"])
    return 0 <= latency <= 15 and int(row["protected_swing_count"]) >= 1


def _hypotheses() -> dict[str, Callable[[dict[str, str]], bool]]:
    return {
        "H1_ideal_formation": _ideal,
        "H2_c2_ideal_formation": lambda r: _ideal(r) and r["closure_family"] == "c2",
        "H3_c3_ideal_formation": lambda r: _ideal(r) and r["closure_family"] == "c3",
        "H4_ideal_with_source_direction": lambda r: (
            _ideal(r) and _context_direction(r) == r["side"]
        ),
    }


def _metrics(rows: list[dict[str, str]]) -> dict[str, object]:
    values = [_d(row["outcome_r"]) for row in rows]
    total = sum(values, Decimal())
    n = len(values)
    mean = total / n if n else Decimal()
    return {
        "n": n,
        "total_r": str(total),
        "mean_r": str(mean),
        "stressed_total_r": str(total - PRIMARY_STRESS_R * n),
        "stressed_mean_r": str(mean - PRIMARY_STRESS_R if n else Decimal()),
    }


def _decompose(rows: list[dict[str, str]], key: str) -> dict[str, object]:
    return {
        value: _metrics([row for row in rows if row[key] == value])
        for value in sorted({row[key] for row in rows})
    }


def _positive_strata(section: dict[str, object]) -> bool:
    return bool(section) and all(
        _d(item["stressed_mean_r"]) > 0
        for item in section.values()
        if isinstance(item, dict) and int(item["n"]) > 0
    )


def _report(rows: list[dict[str, str]]) -> dict[str, object]:
    hypotheses: dict[str, object] = {}
    for name, predicate in _hypotheses().items():
        retained = [row for row in rows if predicate(row)]
        windows = _decompose(retained, "window_id")
        markets = _decompose(retained, "symbol")
        sides = _decompose(retained, "side")
        anchors = _decompose(retained, "anchor")
        accepted = (
            len(windows) == 3
            and _positive_strata(windows)
            and len(markets) == 3
            and _positive_strata(markets)
            and len(sides) == 2
            and _positive_strata(sides)
            and _d(_metrics(retained)["stressed_mean_r"]) > 0
        )
        hypotheses[name] = {
            "metrics": _metrics(retained),
            "by_window": windows,
            "by_market": markets,
            "by_side": sides,
            "by_anchor": anchors,
            "consumed_gate_pass": accepted,
        }
    passing = [
        name
        for name, section in hypotheses.items()
        if isinstance(section, dict) and section["consumed_gate_pass"]
    ]
    return {
        "schema": SCHEMA,
        "contract": "consumed-evidence-only; sealed holdout; primary friction 0.05R/trade",
        "sample": len(rows),
        "primary_stress_r": str(PRIMARY_STRESS_R),
        "hypotheses": hypotheses,
        "passing_hypotheses": passing,
        "candidate_freeze_permitted": len(passing) == 1,
        "holdout_open_permitted": len(passing) == 1,
        "adjudication": (
            "PHASE_B_CONSUMED_GATE_PASS"
            if len(passing) == 1
            else "PHASE_B_FALSIFIED_OR_NONUNIQUE"
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--census-csv", required=True)
    parser.add_argument("--output-json", required=True)
    args = parser.parse_args()
    with Path(args.census_csv).open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    if len(rows) != 183:
        raise ValueError(f"frozen consumed census drifted: {len(rows)} != 183")
    report = _report(rows)
    output = Path(args.output_json)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
