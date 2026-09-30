"""Bind AUDJPY Phase-18 geometry to immutable R40 and R41/R42 ledgers."""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

EXPECTED_TRADES = 1039
EXPECTED_PF = "1.957251590510384151212372667"
EXPECTED_TOTAL_R = "68.02344279137424925740640205"
EXPECTED_DD_R = "5.293573269867727808258117465"


def _jsonl(path: Path) -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def bind(
    *,
    geometry_path: Path,
    r40_path: Path,
    r41_path: Path,
    r41_report_path: Path,
    output_dir: Path,
) -> dict[str, Any]:
    generated = _jsonl(geometry_path)
    r40 = _jsonl(r40_path)
    r41 = _jsonl(r41_path)
    if not len(generated) == len(r40) == len(r41) == EXPECTED_TRADES:
        raise ValueError("AUDJPY Phase-18 population drift")

    bound: list[dict[str, Any]] = []
    invariant_keys = (
        "entry_at",
        "exit_at",
        "side",
        "source_scheme",
        "authority_tier",
        "validation_class",
        "target_rank",
        "target_route",
        "exit_reason",
        "raw_net_010_r",
    )
    for index, (geometry, base, final) in enumerate(
        zip(generated, r40, r41, strict=True)
    ):
        for key, value in base.items():
            if geometry[key] != value:
                raise ValueError(f"R40 parity drift at {index}:{key}")
        for key in invariant_keys:
            if final[key] != base[key]:
                raise ValueError(f"R41 population drift at {index}:{key}")

        if final["base_risk_scale"] != base["risk_scale"]:
            raise ValueError("R41 base risk scale drift")
        if final["base_scaled_net_010_r"] != base["scaled_net_010_r"]:
            raise ValueError("R41 base result drift")

        overlay = Decimal(final["second_layer_overlay_scale"])
        expected_scale = Decimal(base["risk_scale"]) * overlay
        expected_result = Decimal(base["scaled_net_010_r"]) * overlay
        if Decimal(final["final_risk_scale"]) != expected_scale:
            raise ValueError("R41 final risk arithmetic drift")
        if Decimal(final["corrected_scaled_net_010_r"]) != expected_result:
            raise ValueError("R41 corrected result arithmetic drift")

        signal_at = datetime.fromisoformat(str(geometry["signal_at"]))
        entry_at = datetime.fromisoformat(str(geometry["entry_at"]))
        if signal_at > entry_at:
            raise ValueError("signal occurs after entry")
        entry = Decimal(str(geometry["entry_price"]))
        stop = Decimal(str(geometry["structural_stop"]))
        target = Decimal(str(geometry["technical_target"]))
        side = str(geometry["side"])
        if side == "long":
            valid_geometry = stop < entry < target
        elif side == "short":
            valid_geometry = target < entry < stop
        else:
            raise ValueError(f"unexpected side: {side}")
        if not valid_geometry:
            raise ValueError("invalid technical geometry")

        row = dict(geometry)
        row.update(
            {
                "legacy_r42_final_risk_scale": final["final_risk_scale"],
                "legacy_r42_corrected_scaled_net_010_r": final[
                    "corrected_scaled_net_010_r"
                ],
                "legacy_r42_second_layer_overlay_scale": final[
                    "second_layer_overlay_scale"
                ],
                "legacy_r42_second_layer_fragility_flags": final[
                    "second_layer_fragility_flags"
                ],
                "economics_status": "R_DENOMINATED_ONLY",
            }
        )
        bound.append(row)

    final_report = json.loads(r41_report_path.read_text(encoding="utf-8"))
    result = final_report["result_5y"]
    expected = {
        "trades": EXPECTED_TRADES,
        "profit_factor_scaled_net_010": EXPECTED_PF,
        "total_scaled_net_010_r": EXPECTED_TOTAL_R,
        "max_drawdown_r": EXPECTED_DD_R,
        "positive_annual_blocks": 5,
        "acceptance_pass": True,
    }
    for key, value in expected.items():
        if result[key] != value:
            raise ValueError(f"R42 final metric drift: {key}")

    output_dir.mkdir(parents=True, exist_ok=True)
    bound_path = output_dir / "phase18-audjpy-r42-bound-trades.jsonl"
    bound_path.write_text(
        "".join(json.dumps(row, sort_keys=True) + "\n" for row in bound),
        encoding="utf-8",
    )
    report: dict[str, Any] = {
        "schema": "qore.cibo.phase18.audjpy_r42_bound_replay.v1",
        "identity": "CIBO_PHASE18_AUDJPY_R42_BOUND_REPLAY_V1",
        "status": (
            "R_DENOMINATED_GEOMETRY_REPLAY_GREEN_"
            "PROVIDER_CALIBRATION_REQUIRED"
        ),
        "rows": len(bound),
        "parity": {
            "r40_row_for_row": True,
            "r41_population_row_for_row": True,
            "same_signals": True,
            "same_entry": True,
            "same_structural_stop": True,
            "same_technical_target": True,
            "same_market_path": True,
            "same_r40_base_risk_scale": True,
            "r41_second_layer_overlay_reproduced": True,
        },
        "provider_economics": {
            "status": "CALIBRATION_REQUIRED",
            "usd_cibo_sizing_comparison_authorized": False,
        },
        "source_evidence": {
            "audjpy_source_code_sha": (
                "a332b077598e070a42b2497b3766d55e731f7dca"
            ),
            "raw_run_id": 35166210458,
            "target_run_id": 35204892665,
            "v2_run_id": 35383377176,
            "r39_freeze_run_id": 35397198837,
            "r40_run_id": 35397390781,
            "r41_run_id": 35399430491,
        },
        "legacy_r42_result_5y": result,
        "governance": {
            "research_only": True,
            "demo_execution_authorized": False,
            "live_authorized": False,
            "real_capital_authorized": False,
            "merge_authorized": False,
        },
    }
    (output_dir / "phase18-audjpy-r42-bound-report.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--geometry", type=Path, required=True)
    parser.add_argument("--r40", type=Path, required=True)
    parser.add_argument("--r41", type=Path, required=True)
    parser.add_argument("--r41-report", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(bind(
        geometry_path=args.geometry,
        r40_path=args.r40,
        r41_path=args.r41,
        r41_report_path=args.r41_report,
        output_dir=args.output,
    ), sort_keys=True))


if __name__ == "__main__":
    main()
