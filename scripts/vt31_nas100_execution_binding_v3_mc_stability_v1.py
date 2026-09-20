"""Multi-seed Monte Carlo stability diagnostic for physical VT31 binding V3.

Diagnostic only. The trade sequence is the corrected causal V3 sequence.
No strategy, execution rule, trade, return or gate is modified.

Runs eight independent 10,000-path deterministic moving-block bootstraps plus
the canonical paired stream and reports the pooled positive-terminal rate.
"""
from __future__ import annotations

import argparse
import json
from collections import defaultdict
from datetime import date
from decimal import Decimal
from pathlib import Path

import vt31_nas100_alt_tier_bifurcation_forensics_v1 as alt
import vt31_nas100_causal_hybrid_rearm_v1 as engine
import vt31_nas100_execution_binding_v3 as v3

from qore.infrastructure.trader_lab.vt31_silver_bullet_r2_5_multi_index_research import (
    _day,
    load_market_evidence,
)

SCHEMA = "qore.vt31.nas100.execution_binding_v3_mc_stability.v1"


def replay(path: Path) -> dict[str, object]:
    rows, _evidence, _diagnostics, _stats = alt._current_rows(path)
    series, *_ = load_market_evidence(path)
    raw: dict[date, list[object]] = defaultdict(list)
    for bar in series:
        raw[_day(bar.opened_at)].append(bar)
    by_day = {
        day: tuple(sorted(items, key=lambda item: item.opened_at))
        for day, items in raw.items()
    }
    adjusted, diag = v3._physicalize(rows, by_day=by_day)

    streams: dict[str, object] = {}
    probabilities: list[Decimal] = []
    canonical = engine._monte_carlo(
        adjusted,
        variant="PATH_CAUSAL_TARGET:consumed_holdout",
    )
    streams["canonical"] = canonical
    probabilities.append(Decimal(str(canonical["positive_terminal_probability"])))

    for index in range(8):
        result = engine._monte_carlo(
            adjusted,
            variant=f"V3_MC_STABILITY:{index}",
        )
        streams[f"seed_{index}"] = result
        probabilities.append(
            Decimal(str(result["positive_terminal_probability"]))
        )

    mean_probability = sum(probabilities, Decimal(0)) / Decimal(len(probabilities))
    return {
        "schema": SCHEMA,
        "trade_count": len(adjusted),
        "streams": streams,
        "mean_positive_terminal_probability": format(mean_probability, "f"),
        "min_positive_terminal_probability": format(min(probabilities), "f"),
        "max_positive_terminal_probability": format(max(probabilities), "f"),
        "streams_at_or_above_0_90": sum(
            value >= Decimal("0.90") for value in probabilities
        ),
        "stream_count": len(probabilities),
        "binding_diagnostics": diag,
        "governance": {
            "diagnostic_only": True,
            "strategy_changed": False,
            "execution_binding_changed": False,
            "trades_changed": False,
            "returns_changed": False,
            "certification_gate_changed": False,
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("evidence", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    payload = replay(args.evidence)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(payload, sort_keys=True))


if __name__ == "__main__":
    main()
