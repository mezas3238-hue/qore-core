"""Final robustness suite for VT31 NAS100 physical execution binding V2.

No parameter search or retuning. Strategy identity/economics remain
VT31_NAS100_STRUCTURAL_TARGET_V1. This suite falsifies only the frozen physical
execution precedence binding through rolling 2Y stability, Monte Carlo,
execution-cost stress and extreme-winner removal over consumed 5Y evidence.
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
import vt31_nas100_structural_target_final_certification_suite_v1 as oldfinal

from qore.infrastructure.trader_lab.vt31_silver_bullet_r2_5_multi_index_research import _day

SCHEMA = "qore.vt31.nas100.structural_target_execution_binding_final.v2"
START_DATE = date(2017, 7, 1)
END_EXCLUSIVE_DATE = date(2022, 7, 1)


def _d(value: object) -> Decimal:
    return Decimal(str(value))


def certify(*, r8_path: Path, r6_path: Path, r5_path: Path) -> dict[str, object]:
    (
        series,
        account,
        evidence_fingerprint,
        checked_at,
        software_sha,
        provider,
        records,
    ) = old5y._stitch((r8_path, r6_path, r5_path))

    def stitched_loader(_path: Path):
        return (
            series,
            account,
            evidence_fingerprint,
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
        local_day: tuple(sorted(items, key=lambda item: item.opened_at))
        for local_day, items in raw.items()
    }
    adjusted, path_diag = pathcausal._apply_path_causal(rows, by_day=by_day)
    selected = [
        row
        for row in adjusted
        if START_DATE
        <= date.fromisoformat(cast(str, row["local_date"]))
        < END_EXCLUSIVE_DATE
    ]
    metrics = oldfinal._metrics(selected)
    mc = engine._monte_carlo(
        selected,
        variant=f"{frozen.EXECUTION_BINDING_ID}:FINAL_5Y",
    )
    annual = [
        oldfinal._block(
            selected,
            start=date(year, 7, 1),
            end=date(year + 1, 7, 1),
        )
        for year in range(2017, 2022)
    ]
    wfo = oldfinal._rolling_windows(selected)

    stress: dict[str, object] = {}
    for cost in oldfinal.EXTRA_COSTS:
        tag = format(cost, "f")
        stressed = oldfinal._stress_rows(
            selected,
            extra_source_cost_r=cost,
        )
        stress[tag] = {
            "metrics": oldfinal._metrics(stressed),
            "monte_carlo": engine._monte_carlo(
                stressed,
                variant=f"{frozen.EXECUTION_BINDING_ID}:STRESS:{tag}",
            ),
        }

    top1 = oldfinal._metrics(oldfinal._remove_top_winners(selected, 1))
    top5 = oldfinal._metrics(oldfinal._remove_top_winners(selected, 5))
    s1 = cast(dict[str, object], stress["0.01"])["metrics"]
    s2 = cast(dict[str, object], stress["0.02"])["metrics"]
    s5 = cast(dict[str, object], stress["0.05"])["metrics"]
    assert isinstance(s1, dict) and isinstance(s2, dict) and isinstance(s5, dict)

    gates = {
        "frozen_strategy_identity_exact": (
            frozen.STRATEGY_IDENTITY == "VT31_NAS100_STRUCTURAL_TARGET_V1"
        ),
        "binding_fingerprint_exact": (
            frozen.binding_fingerprint()
            == "604f8b06fbbb6d808da6389d9abf02a498612d7dc8a735de886eb174f54cab8c"
        ),
        "trade_count_800_to_900": 800 <= len(selected) <= 900,
        "profit_factor_at_least_1_50": (
            metrics["profit_factor"] is not None
            and _d(metrics["profit_factor"]) >= Decimal("1.50")
        ),
        "total_positive": _d(metrics["total_r"]) > 0,
        "observed_dd_at_most_6r": _d(metrics["max_drawdown_r"]) <= Decimal("6"),
        "all_five_year_blocks_positive": all(bool(x["positive"]) for x in annual),
        "all_rolling_2y_windows_pass": all(bool(x["passes"]) for x in wfo),
        "mc_positive_at_least_0_90": (
            _d(mc["positive_terminal_probability"]) >= Decimal("0.90")
        ),
        "mc_p95_dd_at_most_15r": (
            _d(mc["p95_max_drawdown_r"]) <= Decimal("15")
        ),
        "stress_001_positive_pf_1_40_dd_6_5": (
            _d(s1["total_r"]) > 0
            and s1["profit_factor"] is not None
            and _d(s1["profit_factor"]) >= Decimal("1.40")
            and _d(s1["max_drawdown_r"]) <= Decimal("6.50")
        ),
        "stress_002_positive_pf_1_30_dd_7": (
            _d(s2["total_r"]) > 0
            and s2["profit_factor"] is not None
            and _d(s2["profit_factor"]) >= Decimal("1.30")
            and _d(s2["max_drawdown_r"]) <= Decimal("7.00")
        ),
        "stress_005_remains_positive": (
            _d(s5["total_r"]) > 0
            and s5["profit_factor"] is not None
            and _d(s5["profit_factor"]) > Decimal("1.00")
        ),
        "remove_top_1_remains_positive": (
            _d(top1["total_r"]) > 0
            and top1["profit_factor"] is not None
            and _d(top1["profit_factor"]) > Decimal("1.25")
        ),
        "remove_top_5_remains_positive": (
            _d(top5["total_r"]) > 0
            and top5["profit_factor"] is not None
            and _d(top5["profit_factor"]) > Decimal("1.10")
        ),
    }
    passed = all(gates.values())
    return {
        "schema": SCHEMA,
        "strategy_identity": frozen.STRATEGY_IDENTITY,
        "certified_strategy_fingerprint": frozen.CERTIFIED_STRATEGY_FINGERPRINT,
        "execution_binding_id": frozen.EXECUTION_BINDING_ID,
        "execution_binding_fingerprint": frozen.binding_fingerprint(),
        "evidence_status": {
            "window_start": START_DATE.isoformat(),
            "window_end_exclusive": END_EXCLUSIVE_DATE.isoformat(),
            "status": "CONSUMED_EXTENDED_VALIDATION",
            "fresh": False,
            "source_records": records,
            "evidence_fingerprint": evidence_fingerprint,
        },
        "result": {
            "trade_count": len(selected),
            "metrics": metrics,
            "monte_carlo": mc,
            "annual_blocks": annual,
            "rolling_2y_windows": wfo,
            "execution_stress": stress,
            "extreme_trade_dependence": {
                "remove_top_1": {"metrics": top1},
                "remove_top_5": {"metrics": top5},
            },
            "by_side": oldfinal._group_metrics(selected, "side"),
            "by_tier": oldfinal._group_metrics(selected, "tier"),
            "by_entry_family": oldfinal._group_metrics(selected, "entry_family"),
            "path_diagnostics": path_diag,
        },
        "certification_gates": gates,
        "execution_binding_certified": passed,
        "decision": (
            "EXECUTION_BINDING_CERTIFIED"
            if passed
            else "REJECTED_EXECUTION_BINDING_ROBUSTNESS"
        ),
        "governance": {
            "parameter_scan_inside_suite": False,
            "variant_comparison_inside_suite": False,
            "retuning_after_5y": False,
            "strategy_economics_changed": False,
            "fresh_holdout_claimed": False,
            "live_authorized": False,
            "real_capital_authorized": False,
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
    payload = certify(r8_path=args.r8, r6_path=args.r6, r5_path=args.r5)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "strategy_identity": payload["strategy_identity"],
                "binding_fingerprint": payload["execution_binding_fingerprint"],
                "result": payload["result"],
                "gates": payload["certification_gates"],
                "decision": payload["decision"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
