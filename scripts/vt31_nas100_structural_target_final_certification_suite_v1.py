"""Final robustness/certification suite for VT31 NAS100 Structural Target V1.

Frozen candidate:
    VT31_NAS100_STRUCTURAL_TARGET_V1
    EQ50_COMPRESSED_ACCEPT_RUN25

The candidate was frozen before its five-year consumed validation and passed
all declared 5Y gates. This suite performs no parameter search or variant
comparison. It attempts to falsify the exact frozen identity through:

- exact frozen contract/fingerprint replay;
- five annual blocks, all positive;
- four overlapping rolling 2Y temporal/WFO-style windows;
- Monte Carlo on the complete 5Y window;
- execution/slippage stress at +0.01R, +0.02R and +0.05R source cost;
- removal of the largest 1 and largest 5 winning trades;
- side/tier/family diagnostics.

Evidence status remains CONSUMED_EXTENDED_VALIDATION. This suite never claims
freshness and grants no LIVE, production or real-capital authority.
"""
# ruff: noqa: B009, E402, I001
from __future__ import annotations

import argparse
import json
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import cast

import vt31_nas100_capacity_selective_target_ladder_v1 as frontier
import vt31_nas100_causal_hybrid_rearm_v1 as engine
import vt31_nas100_residual_regime_forensics_v2 as residual
import vt31_nas100_structural_target_candidate_5y_validation_v1 as fivey
import vt31_nas100_structural_target_candidate_v1 as candidate

SCHEMA = (
    "qore.vt31.nas100.structural_target_final_certification_suite.v1"
)
IDENTITY = "VT31_NAS100_STRUCTURAL_TARGET_FINAL_CERTIFICATION_V1"

EXPECTED_CONTRACT_FINGERPRINT = (
    "089c41f98a72295278063cfc29caf8419538f68315d9f5e57be144fbdae15e08"
)
FREEZE_RUN_ID = 35513305170
FREEZE_ARTIFACT_ID = 10605623133
FREEZE_ARTIFACT_DIGEST = (
    "sha256:46f157d912551bf4f75954df907d810f1e58705622d8c782161a53699ddb21f9"
)
FIVE_YEAR_RUN_ID = 35513474108
FIVE_YEAR_ARTIFACT_ID = 10605433453
FIVE_YEAR_ARTIFACT_DIGEST = (
    "sha256:9630a64496b3bdb9eafd29cde0d9a33d463cfb451bd56ba6a117188736e43502"
)

START_DATE = date(2017, 7, 1)
END_EXCLUSIVE_DATE = date(2022, 7, 1)
EXTRA_COSTS = (
    Decimal("0.01"),
    Decimal("0.02"),
    Decimal("0.05"),
)

ROLLING_2Y_WINDOWS = tuple(
    (
        date(year, 7, 1),
        date(year + 2, 7, 1),
    )
    for year in range(2017, 2021)
)


def _d(value: object) -> Decimal:
    return Decimal(str(value))


def _sorted(
    rows: list[dict[str, object]],
) -> list[dict[str, object]]:
    return sorted(
        rows,
        key=lambda row: cast(str, row["signal_at"]),
    )


def _metrics(
    rows: list[dict[str, object]],
) -> dict[str, object]:
    return residual._metrics(_sorted(rows))


def _stress_rows(
    rows: list[dict[str, object]],
    *,
    extra_source_cost_r: Decimal,
) -> list[dict[str, object]]:
    stressed: list[dict[str, object]] = []
    for row in rows:
        requested = _d(row["requested_risk_r"])
        net = _d(row["capital_weighted_net_r"])
        updated = dict(row)
        updated["capital_weighted_net_r"] = format(
            net - requested * extra_source_cost_r,
            "f",
        )
        updated["extra_source_cost_r"] = format(
            extra_source_cost_r,
            "f",
        )
        stressed.append(updated)
    return stressed


def _block(
    rows: list[dict[str, object]],
    *,
    start: date,
    end: date,
) -> dict[str, object]:
    selected = [
        row
        for row in rows
        if start
        <= date.fromisoformat(
            cast(str, row["local_date"])
        )
        < end
    ]
    metrics = _metrics(selected)
    return {
        "start_date": start.isoformat(),
        "end_exclusive_date": end.isoformat(),
        "trade_count": len(selected),
        "metrics": metrics,
        "positive": (
            bool(selected)
            and _d(metrics["total_r"]) > 0
            and _d(metrics["mean_r"]) > 0
        ),
    }


def _rolling_windows(
    rows: list[dict[str, object]],
) -> list[dict[str, object]]:
    windows: list[dict[str, object]] = []
    for index, (start, end) in enumerate(
        ROLLING_2Y_WINDOWS,
        start=1,
    ):
        item = _block(
            rows,
            start=start,
            end=end,
        )
        metrics = cast(
            dict[str, object],
            item["metrics"],
        )
        pf = metrics["profit_factor"]
        item["window"] = index
        item["gates"] = {
            "density_250_to_400": (
                250
                <= int(cast(int, item["trade_count"]))
                <= 400
            ),
            "profit_factor_at_least_1_50": (
                pf is not None
                and _d(pf) >= Decimal("1.50")
            ),
            "total_positive": (
                _d(metrics["total_r"]) > 0
            ),
            "dd_at_most_6r": (
                _d(metrics["max_drawdown_r"])
                <= Decimal("6")
            ),
        }
        item["passes"] = all(
            cast(
                dict[str, bool],
                item["gates"],
            ).values()
        )
        windows.append(item)
    return windows


def _group_metrics(
    rows: list[dict[str, object]],
    field: str,
) -> dict[str, object]:
    values = sorted(
        {
            str(row.get(field))
            for row in rows
        }
    )
    return {
        value: {
            "trade_count": len(
                selected := [
                    row
                    for row in rows
                    if str(row.get(field)) == value
                ]
            ),
            "metrics": _metrics(selected),
        }
        for value in values
    }


def _remove_top_winners(
    rows: list[dict[str, object]],
    count: int,
) -> list[dict[str, object]]:
    ranked = sorted(
        range(len(rows)),
        key=lambda index: _d(
            rows[index]["capital_weighted_net_r"]
        ),
        reverse=True,
    )
    removed = set(ranked[:count])
    return [
        dict(row)
        for index, row in enumerate(rows)
        if index not in removed
    ]


def certify(
    *,
    r8_path: Path,
    r6_path: Path,
    r5_path: Path,
) -> dict[str, object]:
    (
        series,
        account,
        evidence_fingerprint,
        checked_at,
        software_sha,
        provider,
        records,
    ) = fivey._stitch(
        (r8_path, r6_path, r5_path)
    )

    def stitched_loader(
        _path: Path,
    ) -> tuple[
        tuple[object, ...],
        str,
        str,
        object,
        str,
        str,
    ]:
        return (
            series,
            account,
            evidence_fingerprint,
            checked_at,
            software_sha,
            provider,
        )

    original_residual_loader = (
        residual.load_market_evidence
    )
    original_frontier_loader = (
        frontier.load_market_evidence
    )
    residual.load_market_evidence = stitched_loader
    frontier.load_market_evidence = stitched_loader

    try:
        evaluation = candidate.evaluate(
            Path("STITCHED_IMMUTABLE_5Y_EVIDENCE"),
            partition="final_certification_5y",
            include_rows=True,
        )
    finally:
        residual.load_market_evidence = (
            original_residual_loader
        )
        frontier.load_market_evidence = (
            original_frontier_loader
        )

    fingerprint = cast(
        str,
        evaluation["contract_fingerprint"],
    )
    if fingerprint != EXPECTED_CONTRACT_FINGERPRINT:
        raise AssertionError(
            "frozen structural target fingerprint drift"
        )
    if fingerprint != candidate.contract_fingerprint():
        raise AssertionError(
            "candidate module contract fingerprint drift"
        )

    all_rows = cast(
        list[dict[str, object]],
        evaluation.pop("trade_rows"),
    )
    rows = [
        row
        for row in all_rows
        if START_DATE
        <= date.fromisoformat(
            cast(str, row["local_date"])
        )
        < END_EXCLUSIVE_DATE
    ]
    if not rows:
        raise ValueError("certification emitted no 5Y rows")

    metrics = _metrics(rows)
    mc = engine._monte_carlo(
        rows,
        variant=(
            f"{candidate.CANDIDATE_ID}:"
            "FINAL_CERTIFICATION_5Y"
        ),
    )
    annual = [
        _block(
            rows,
            start=date(year, 7, 1),
            end=date(year + 1, 7, 1),
        )
        for year in range(2017, 2022)
    ]
    wfo = _rolling_windows(rows)

    stress: dict[str, object] = {}
    for cost in EXTRA_COSTS:
        tag = format(cost, "f")
        stressed = _stress_rows(
            rows,
            extra_source_cost_r=cost,
        )
        stress[tag] = {
            "metrics": _metrics(stressed),
            "monte_carlo": engine._monte_carlo(
                stressed,
                variant=(
                    f"{candidate.CANDIDATE_ID}:"
                    f"FINAL_STRESS:{tag}"
                ),
            ),
        }

    remove_top1 = _remove_top_winners(
        rows,
        1,
    )
    remove_top5 = _remove_top_winners(
        rows,
        5,
    )
    extreme = {
        "remove_top_1": {
            "metrics": _metrics(remove_top1),
        },
        "remove_top_5": {
            "metrics": _metrics(remove_top5),
        },
    }

    stress_001 = cast(
        dict[str, object],
        cast(
            dict[str, object],
            stress["0.01"],
        )["metrics"],
    )
    stress_002 = cast(
        dict[str, object],
        cast(
            dict[str, object],
            stress["0.02"],
        )["metrics"],
    )
    stress_005 = cast(
        dict[str, object],
        cast(
            dict[str, object],
            stress["0.05"],
        )["metrics"],
    )
    top1_metrics = cast(
        dict[str, object],
        cast(
            dict[str, object],
            extreme["remove_top_1"],
        )["metrics"],
    )
    top5_metrics = cast(
        dict[str, object],
        cast(
            dict[str, object],
            extreme["remove_top_5"],
        )["metrics"],
    )

    gates = {
        "frozen_identity_exact": (
            candidate.CANDIDATE_ID
            == "VT31_NAS100_STRUCTURAL_TARGET_V1"
            and candidate.SELECTED_VARIANT
            == "EQ50_COMPRESSED_ACCEPT_RUN25"
            and fingerprint
            == EXPECTED_CONTRACT_FINGERPRINT
        ),
        "trade_count_800_to_900": (
            800 <= len(rows) <= 900
        ),
        "profit_factor_at_least_1_50": (
            metrics["profit_factor"] is not None
            and _d(metrics["profit_factor"])
            >= Decimal("1.50")
        ),
        "total_positive": (
            _d(metrics["total_r"]) > 0
        ),
        "observed_dd_at_most_6r": (
            _d(metrics["max_drawdown_r"])
            <= Decimal("6")
        ),
        "all_five_year_blocks_positive": (
            len(annual) == 5
            and all(
                bool(block["positive"])
                for block in annual
            )
        ),
        "all_rolling_2y_windows_pass": (
            len(wfo) == 4
            and all(
                bool(window["passes"])
                for window in wfo
            )
        ),
        "mc_positive_at_least_0_90": (
            _d(
                mc[
                    "positive_terminal_probability"
                ]
            )
            >= Decimal("0.90")
        ),
        "mc_p95_dd_at_most_15r": (
            _d(mc["p95_max_drawdown_r"])
            <= Decimal("15")
        ),
        "stress_001_positive_pf_1_40_dd_6_5": (
            _d(stress_001["total_r"]) > 0
            and stress_001["profit_factor"] is not None
            and _d(
                stress_001["profit_factor"]
            )
            >= Decimal("1.40")
            and _d(
                stress_001["max_drawdown_r"]
            )
            <= Decimal("6.50")
        ),
        "stress_002_positive_pf_1_30_dd_7": (
            _d(stress_002["total_r"]) > 0
            and stress_002["profit_factor"] is not None
            and _d(
                stress_002["profit_factor"]
            )
            >= Decimal("1.30")
            and _d(
                stress_002["max_drawdown_r"]
            )
            <= Decimal("7.00")
        ),
        "stress_005_remains_positive": (
            _d(stress_005["total_r"]) > 0
            and stress_005["profit_factor"] is not None
            and _d(
                stress_005["profit_factor"]
            )
            > Decimal("1.00")
        ),
        "remove_top_1_remains_positive": (
            _d(top1_metrics["total_r"]) > 0
            and top1_metrics["profit_factor"] is not None
            and _d(
                top1_metrics["profit_factor"]
            )
            > Decimal("1.25")
        ),
        "remove_top_5_remains_positive": (
            _d(top5_metrics["total_r"]) > 0
            and top5_metrics["profit_factor"] is not None
            and _d(
                top5_metrics["profit_factor"]
            )
            > Decimal("1.10")
        ),
    }
    certified = all(gates.values())

    return {
        "schema": SCHEMA,
        "identity": IDENTITY,
        "candidate_id": candidate.CANDIDATE_ID,
        "selected_variant": candidate.SELECTED_VARIANT,
        "contract_fingerprint": fingerprint,
        "development_binding": {
            "freeze_run_id": FREEZE_RUN_ID,
            "freeze_artifact_id": FREEZE_ARTIFACT_ID,
            "freeze_artifact_digest": (
                FREEZE_ARTIFACT_DIGEST
            ),
            "five_year_run_id": FIVE_YEAR_RUN_ID,
            "five_year_artifact_id": (
                FIVE_YEAR_ARTIFACT_ID
            ),
            "five_year_artifact_digest": (
                FIVE_YEAR_ARTIFACT_DIGEST
            ),
        },
        "evidence_status": {
            "window_start": START_DATE.isoformat(),
            "window_end_exclusive": (
                END_EXCLUSIVE_DATE.isoformat()
            ),
            "status": "CONSUMED_EXTENDED_VALIDATION",
            "fresh": False,
            "source_records": records,
            "evidence_fingerprint": (
                evidence_fingerprint
            ),
        },
        "result": {
            "trade_count": len(rows),
            "metrics": metrics,
            "monte_carlo": mc,
            "annual_blocks": annual,
            "rolling_2y_windows": wfo,
            "execution_stress": stress,
            "extreme_trade_dependence": extreme,
            "by_side": _group_metrics(
                rows,
                "side",
            ),
            "by_tier": _group_metrics(
                rows,
                "tier",
            ),
            "by_entry_family": _group_metrics(
                rows,
                "entry_family",
            ),
        },
        "certification_gates": gates,
        "trader_certified": certified,
        "certification_decision": (
            "TRADER_CERTIFIED"
            if certified
            else "REJECTED_CERTIFICATION_ROBUSTNESS"
        ),
        "governance": {
            "parameter_scan_inside_suite": False,
            "variant_comparison_inside_suite": False,
            "retuning_after_5y": False,
            "fresh_holdout_claimed": False,
            "source_evidence_consumed": True,
            "silver_bullet_changed": False,
            "live_authorized": False,
            "real_capital_authorized": False,
            "production_authorized": False,
            "order_submission_authorized": False,
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--r8",
        required=True,
        type=Path,
    )
    parser.add_argument(
        "--r6",
        required=True,
        type=Path,
    )
    parser.add_argument(
        "--r5",
        required=True,
        type=Path,
    )
    parser.add_argument(
        "--output",
        required=True,
        type=Path,
    )
    args = parser.parse_args()

    payload = certify(
        r8_path=args.r8,
        r6_path=args.r6,
        r5_path=args.r5,
    )
    args.output.parent.mkdir(
        parents=True,
        exist_ok=True,
    )
    args.output.write_text(
        json.dumps(
            payload,
            sort_keys=True,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "candidate_id": payload[
                    "candidate_id"
                ],
                "selected_variant": payload[
                    "selected_variant"
                ],
                "result": payload["result"],
                "certification_gates": payload[
                    "certification_gates"
                ],
                "trader_certified": payload[
                    "trader_certified"
                ],
                "certification_decision": payload[
                    "certification_decision"
                ],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
