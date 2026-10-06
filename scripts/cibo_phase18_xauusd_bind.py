"""Bind XAUUSD R34 Phase-18 geometry to immutable authoritative evidence."""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

EXPECTED_TRADES = 921
EXPECTED_PF = "1.529741881717934130030753380"
EXPECTED_TOTAL_R = "103.6427513069166048428626309"
EXPECTED_DD_R = "9.19605447572090219358745533"


def _jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(x) for x in path.read_text(encoding="utf-8").splitlines() if x.strip()]


def bind(
    *,
    geometry_path: Path,
    r34_path: Path,
    r34_report_path: Path,
    output_dir: Path,
) -> dict[str, Any]:
    generated = _jsonl(geometry_path)
    authoritative = _jsonl(r34_path)
    if not len(generated) == len(authoritative) == EXPECTED_TRADES:
        raise ValueError("XAUUSD Phase-18 population drift")

    bound: list[dict[str, Any]] = []
    for index, (geometry, source) in enumerate(zip(generated, authoritative, strict=True)):
        for key, value in source.items():
            if geometry[key] != value:
                raise ValueError(f"R34 parity drift at {index}:{key}")

        signal_at = datetime.fromisoformat(str(geometry["signal_at"]))
        entry_at = datetime.fromisoformat(str(geometry["entry_at"]))
        if signal_at > entry_at:
            raise ValueError("signal occurs after entry")
        entry = Decimal(str(geometry["entry_price"]))
        stop = Decimal(str(geometry["structural_stop"]))
        target = Decimal(str(geometry["technical_target"]))
        side = str(geometry["side"])
        if side == "long":
            valid = stop < entry < target
        elif side == "short":
            valid = target < entry < stop
        else:
            valid = False
        if not valid:
            raise ValueError("invalid technical geometry")

        raw = Decimal(str(geometry["raw_net_010_r"]))
        scale = Decimal(str(geometry["risk_scale"]))
        scaled = Decimal(str(geometry["scaled_net_010_r"]))
        if raw * scale != scaled:
            raise ValueError("R34 risk arithmetic drift")

        row = dict(geometry)
        row["legacy_r34_final_risk_scale"] = geometry["risk_scale"]
        row["legacy_r34_scaled_net_010_r"] = geometry["scaled_net_010_r"]
        row["economics_status"] = "R_DENOMINATED_ONLY"
        bound.append(row)

    report_source = json.loads(r34_report_path.read_text(encoding="utf-8"))
    result = report_source["result"]
    expected = {
        "trades": EXPECTED_TRADES,
        "profit_factor_scaled_net_010": EXPECTED_PF,
        "total_scaled_net_010_r": EXPECTED_TOTAL_R,
        "max_drawdown_scaled_r": EXPECTED_DD_R,
        "positive_annual_blocks": 4,
        "acceptance_pass": True,
    }
    for key, value in expected.items():
        if result[key] != value:
            raise ValueError(f"R34 metric drift: {key}")

    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "phase18-xauusd-r34-bound-trades.jsonl").write_text(
        "".join(json.dumps(row, sort_keys=True) + "\n" for row in bound),
        encoding="utf-8",
    )
    report = {
        "schema": "qore.cibo.phase18.xauusd_r34_bound_replay.v1",
        "identity": "CIBO_PHASE18_XAUUSD_R34_BOUND_REPLAY_V1",
        "status": "R_DENOMINATED_GEOMETRY_REPLAY_GREEN_PROVIDER_CALIBRATION_REQUIRED",
        "rows": len(bound),
        "parity": {
            "r34_row_for_row": True,
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
            "xauusd_source_code_sha": "56ef138ee5ea1cde6d0bcf4c9e25e8b661c04e84",
            "raw_run_id": 35166210458,
            "raw_artifact_id": 10476557530,
            "target_run_id": 35204892665,
            "target_artifact_id": 10489343458,
            "r28_run_id": 35305338898,
            "r33_freeze_run_id": 35308395893,
            "r34_run_id": 35308785945,
            "r34_artifact_id": 10532254052,
        },
        "legacy_r34_result_5y": result,
        "governance": {
            "research_only": True,
            "demo_execution_authorized": False,
            "live_authorized": False,
            "real_capital_authorized": False,
            "merge_authorized": False,
        },
    }
    (output_dir / "phase18-xauusd-r34-bound-report.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--geometry", type=Path, required=True)
    parser.add_argument("--r34", type=Path, required=True)
    parser.add_argument("--r34-report", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(bind(
        geometry_path=args.geometry,
        r34_path=args.r34,
        r34_report_path=args.r34_report,
        output_dir=args.output,
    ), sort_keys=True))


if __name__ == "__main__":
    main()
