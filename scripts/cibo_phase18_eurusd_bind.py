"""Bind EURUSD Phase-18 geometry to the immutable R38 corrected ledger."""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

EXPECTED_TRADES = 863
EXPECTED_PF = "2.958703779880710298093151891"
EXPECTED_TOTAL_R = "294.8274112858301220583196574"
EXPECTED_DD_R = "5.824645307409961208739068649"


def _jsonl(path: Path) -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def bind(
    *,
    geometry_path: Path,
    r38_path: Path,
    r38_report_path: Path,
    output_dir: Path,
) -> dict[str, Any]:
    generated = _jsonl(geometry_path)
    authoritative = _jsonl(r38_path)
    if not len(generated) == len(authoritative) == EXPECTED_TRADES:
        raise ValueError("EURUSD Phase-18 population drift")

    bound: list[dict[str, Any]] = []
    for index, (geometry, source) in enumerate(
        zip(generated, authoritative, strict=True)
    ):
        for key, value in source.items():
            if geometry[key] != value:
                raise ValueError(f"R38 parity drift at {index}:{key}")

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

        risk_scale = Decimal(str(geometry["risk_scale"]))
        raw = Decimal(str(geometry["raw_net_010_r"]))
        scaled = Decimal(str(geometry["scaled_net_010_r"]))
        if raw * risk_scale != scaled:
            raise ValueError("R38 risk arithmetic drift")

        row = dict(geometry)
        row["legacy_r38_final_risk_scale"] = geometry["risk_scale"]
        row["legacy_r38_scaled_net_010_r"] = geometry["scaled_net_010_r"]
        row["economics_status"] = "R_DENOMINATED_ONLY"
        bound.append(row)

    report_source = json.loads(r38_report_path.read_text(encoding="utf-8"))
    result = report_source["result"]
    expected = {
        "trades": EXPECTED_TRADES,
        "profit_factor_scaled_net_010": EXPECTED_PF,
        "total_scaled_net_010_r": EXPECTED_TOTAL_R,
        "max_drawdown_scaled_r": EXPECTED_DD_R,
        "acceptance_pass": True,
    }
    for key, value in expected.items():
        if result[key] != value:
            raise ValueError(f"R38 final metric drift: {key}")

    output_dir.mkdir(parents=True, exist_ok=True)
    bound_path = output_dir / "phase18-eurusd-r38-bound-trades.jsonl"
    bound_path.write_text(
        "".join(json.dumps(row, sort_keys=True) + "\n" for row in bound),
        encoding="utf-8",
    )

    report: dict[str, Any] = {
        "schema": "qore.cibo.phase18.eurusd_r38_bound_replay.v1",
        "identity": "CIBO_PHASE18_EURUSD_R38_BOUND_REPLAY_V1",
        "status": (
            "R_DENOMINATED_GEOMETRY_REPLAY_GREEN_"
            "PROVIDER_CALIBRATION_REQUIRED"
        ),
        "rows": len(bound),
        "parity": {
            "r38_row_for_row": True,
            "same_signals": True,
            "same_entry": True,
            "same_structural_stop": True,
            "same_technical_target": True,
            "same_market_path": True,
            "same_final_risk_scale": True,
            "risk_arithmetic_reproduced": True,
        },
        "provider_economics": {
            "status": "CALIBRATION_REQUIRED",
            "usd_cibo_sizing_comparison_authorized": False,
        },
        "source_evidence": {
            "eurusd_source_code_sha": (
                "324fb91d44a6fa328e66de2e22ace7386630c7aa"
            ),
            "raw_run_id": 35166210458,
            "raw_artifact_id": 10475354631,
            "target_run_id": 35204892665,
            "target_artifact_id": 10489596583,
            "r28_run_id": 35319457546,
            "r28_artifact_id": 10536696948,
            "r36_freeze_run_id": 35326864091,
            "r36_freeze_artifact_id": 10539189859,
            "r38_run_id": 35327677519,
            "r38_artifact_id": 10539313228,
        },
        "legacy_r38_result_5y": result,
        "governance": {
            "research_only": True,
            "demo_execution_authorized": False,
            "live_authorized": False,
            "real_capital_authorized": False,
            "merge_authorized": False,
        },
    }
    (output_dir / "phase18-eurusd-r38-bound-report.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--geometry", type=Path, required=True)
    parser.add_argument("--r38", type=Path, required=True)
    parser.add_argument("--r38-report", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = bind(
        geometry_path=args.geometry,
        r38_path=args.r38,
        r38_report_path=args.r38_report,
        output_dir=args.output,
    )
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
