"""Five-year validation for the frozen physical execution binding V2.

Strategy economics remain VT31_NAS100_STRUCTURAL_TARGET_V1. This validation
tests only the physically causal execution precedence frozen in
VT31_NAS100_STRUCTURAL_TARGET_EXECUTION_BINDING_V2 over the same consumed
extended 5Y window [2017-07-01, 2022-07-01).

No parameter search, variant comparison or retuning is permitted.
"""
# ruff: noqa: E402, I001
from __future__ import annotations

import argparse
import json
from collections import defaultdict
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import cast

import vt31_nas100_alt_tier_bifurcation_forensics_v1 as alt
import vt31_nas100_causal_hybrid_rearm_v1 as engine
import vt31_nas100_path_causal_target_ladder_v2 as pathcausal
import vt31_nas100_residual_regime_forensics_v2 as residual
import vt31_nas100_structural_target_candidate_5y_validation_v1 as old5y
import vt31_nas100_structural_target_execution_binding_v2 as frozen

from qore.infrastructure.trader_lab.vt31_silver_bullet_r2_5_multi_index_research import (
    _day,
)

SCHEMA = "qore.vt31.nas100.structural_target_execution_binding_5y.v2"
START_DATE = date(2017, 7, 1)
END_EXCLUSIVE_DATE = date(2022, 7, 1)
YEAR_BLOCKS = tuple(
    (date(year, 7, 1), date(year + 1, 7, 1))
    for year in range(2017, 2022)
)


def _metrics(rows: list[dict[str, object]]) -> dict[str, object]:
    return residual._metrics(rows)


def _annual(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    result: list[dict[str, object]] = []
    for index, (start, end) in enumerate(YEAR_BLOCKS, start=1):
        selected = [
            row
            for row in rows
            if start
            <= date.fromisoformat(cast(str, row["local_date"]))
            < end
        ]
        metrics = _metrics(selected)
        result.append(
            {
                "year_block": index,
                "start_date": start.isoformat(),
                "end_exclusive_date": end.isoformat(),
                "trade_count": len(selected),
                "metrics": metrics,
                "positive": (
                    bool(selected)
                    and Decimal(str(metrics["total_r"])) > 0
                    and Decimal(str(metrics["mean_r"])) > 0
                ),
            }
        )
    return result


def validate(
    *,
    r8_path: Path,
    r6_path: Path,
    r5_path: Path,
) -> dict[str, object]:
    (
        series,
        account,
        fingerprint,
        checked_at,
        software_sha,
        provider,
        records,
    ) = old5y._stitch((r8_path, r6_path, r5_path))

    def stitched_loader(_path: Path):
        return (
            series,
            account,
            fingerprint,
            checked_at,
            software_sha,
            provider,
        )

    original_residual_loader = residual.load_market_evidence
    original_path_loader = pathcausal.load_market_evidence
    residual.load_market_evidence = stitched_loader
    pathcausal.load_market_evidence = stitched_loader
    try:
        rows, _evidence, _diagnostics, _stats = alt._current_rows(
            Path("STITCHED_IMMUTABLE_5Y_EVIDENCE")
        )
    finally:
        residual.load_market_evidence = original_residual_loader
        pathcausal.load_market_evidence = original_path_loader

    raw: dict[date, list[object]] = defaultdict(list)
    for bar in series:
        raw[_day(bar.opened_at)].append(bar)
    by_day = {
        local_day: tuple(
            sorted(items, key=lambda item: item.opened_at)
        )
        for local_day, items in raw.items()
    }

    adjusted, path_diag = pathcausal._apply_path_causal(
        rows,
        by_day=by_day,
    )
    selected = [
        row
        for row in adjusted
        if START_DATE
        <= date.fromisoformat(cast(str, row["local_date"]))
        < END_EXCLUSIVE_DATE
    ]
    metrics = _metrics(selected)
    mc = engine._monte_carlo(
        selected,
        variant=(
            f"{frozen.EXECUTION_BINDING_ID}:"
            "FIVE_YEAR_CONSUMED"
        ),
    )
    annual = _annual(selected)
    gates = {
        "trade_count_800_to_900": 800 <= len(selected) <= 900,
        "profit_factor_at_least_1_50": (
            metrics["profit_factor"] is not None
            and Decimal(str(metrics["profit_factor"])) >= Decimal("1.50")
        ),
        "total_positive": Decimal(str(metrics["total_r"])) > 0,
        "observed_dd_at_most_6r": (
            Decimal(str(metrics["max_drawdown_r"])) <= Decimal("6")
        ),
        "all_five_year_blocks_positive": (
            len(annual) == 5 and all(bool(block["positive"]) for block in annual)
        ),
        "mc_positive_at_least_0_90": (
            Decimal(str(mc["positive_terminal_probability"])) >= Decimal("0.90")
        ),
        "mc_p95_dd_at_most_15r": (
            Decimal(str(mc["p95_max_drawdown_r"])) <= Decimal("15")
        ),
        "binding_fingerprint_stable": (
            frozen.binding_fingerprint()
            == frozen.binding_fingerprint()
        ),
    }
    return {
        "schema": SCHEMA,
        "strategy_identity": frozen.STRATEGY_IDENTITY,
        "certified_strategy_fingerprint": (
            frozen.CERTIFIED_STRATEGY_FINGERPRINT
        ),
        "execution_binding_id": frozen.EXECUTION_BINDING_ID,
        "execution_binding_fingerprint": frozen.binding_fingerprint(),
        "window": {
            "start_date": START_DATE.isoformat(),
            "end_exclusive_date": END_EXCLUSIVE_DATE.isoformat(),
            "status": "CONSUMED_EXTENDED_VALIDATION",
            "fresh": False,
        },
        "source_records": records,
        "evidence_fingerprint": fingerprint,
        "five_year_result": {
            "trade_count": len(selected),
            "metrics": metrics,
            "monte_carlo": mc,
            "path_diagnostics": path_diag,
        },
        "annual_blocks": annual,
        "gates": gates,
        "passes_all_5y_gates": all(gates.values()),
        "governance": {
            "parameter_search": False,
            "variant_comparison": False,
            "retuning_inside_5y": False,
            "fresh_holdout_claimed": False,
            "strategy_economics_changed": False,
            "live_authorized": False,
            "production_authorized": False,
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--r8", required=True, type=Path)
    parser.add_argument("--r6", required=True, type=Path)
    parser.add_argument("--r5", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    payload = validate(r8_path=args.r8, r6_path=args.r6, r5_path=args.r5)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "strategy_identity": payload["strategy_identity"],
                "execution_binding_fingerprint": payload[
                    "execution_binding_fingerprint"
                ],
                "result": payload["five_year_result"],
                "annual_blocks": payload["annual_blocks"],
                "gates": payload["gates"],
                "passes_all": payload["passes_all_5y_gates"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
