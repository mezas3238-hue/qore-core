"""Bind VT31 NAS100 V4 Phase-18 rows to the immutable authoritative result."""

from __future__ import annotations

import argparse
import copy
import json
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

EXPECTED_TRADES = 806
EXPECTED_PF = "3.455321118486999415676978877"
EXPECTED_TOTAL_R = "61.38049535416448786455402411"
EXPECTED_DD_R = "3.70898490728154195122908861"
EXPECTED_BINDING = "e85ecc5d82f6c59061afd68863b0f641a3512b1cf132f3b8fb01be324ce7e842"
EXPECTED_STRATEGY = "089c41f98a72295278063cfc29caf8419538f68315d9f5e57be144fbdae15e08"


def _load(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("VT31 Phase-18 payload must be an object")
    return payload


def bind(
    *,
    regenerated_path: Path,
    authoritative_path: Path,
    output_dir: Path,
) -> dict[str, Any]:
    regenerated = _load(regenerated_path)
    authoritative = _load(authoritative_path)

    comparison = copy.deepcopy(regenerated)
    result = comparison["five_year_result"]
    rows = result.pop("trade_rows")
    if comparison != authoritative:
        raise ValueError("VT31 V4 deterministic authoritative parity drift")
    if not isinstance(rows, list) or len(rows) != EXPECTED_TRADES:
        raise ValueError("VT31 V4 trade-row population drift")

    metrics = authoritative["five_year_result"]["metrics"]
    expected_metrics = {
        "sample": EXPECTED_TRADES,
        "profit_factor": EXPECTED_PF,
        "total_r": EXPECTED_TOTAL_R,
        "max_drawdown_r": EXPECTED_DD_R,
    }
    for key, value in expected_metrics.items():
        if metrics[key] != value:
            raise ValueError(f"VT31 V4 metric drift: {key}")
    if authoritative["execution_binding_fingerprint"] != EXPECTED_BINDING:
        raise ValueError("VT31 V4 execution binding fingerprint drift")
    if authoritative["certified_strategy_fingerprint"] != EXPECTED_STRATEGY:
        raise ValueError("VT31 certified strategy fingerprint drift")
    if authoritative["passes_all_5y_gates"] is not True:
        raise ValueError("VT31 authoritative V4 gates are not green")

    bound: list[dict[str, Any]] = []
    prior_entry: datetime | None = None
    for index, source in enumerate(rows):
        if not isinstance(source, dict):
            raise ValueError(f"VT31 V4 row {index} is not an object")
        required = (
            "signal_at",
            "filled_at",
            "entry",
            "initial_stop",
            "structural_target",
            "side",
            "exit_at",
            "exit_reason",
            "r_multiple",
            "requested_risk_r",
            "capital_weighted_net_r",
        )
        missing = [key for key in required if source.get(key) is None]
        if missing:
            raise ValueError(f"VT31 V4 row {index} missing: {missing}")

        signal_at = datetime.fromisoformat(str(source["signal_at"]))
        entry_at = datetime.fromisoformat(str(source["filled_at"]))
        exit_at = datetime.fromisoformat(str(source["exit_at"]))
        if not signal_at <= entry_at <= exit_at:
            raise ValueError(f"VT31 V4 causal time drift at row {index}")
        if prior_entry is not None and entry_at < prior_entry:
            raise ValueError("VT31 V4 entry chronology drift")
        prior_entry = entry_at

        entry = Decimal(str(source["entry"]))
        stop = Decimal(str(source["initial_stop"]))
        target = Decimal(str(source["structural_target"]))
        side = str(source["side"])
        if side == "long":
            valid_geometry = stop < entry < target
        elif side == "short":
            valid_geometry = target < entry < stop
        else:
            raise ValueError(f"VT31 V4 unexpected side: {side}")
        if not valid_geometry:
            raise ValueError(f"VT31 V4 invalid geometry at row {index}")

        risk = Decimal(str(source["requested_risk_r"]))
        legacy_net = Decimal(str(source["capital_weighted_net_r"]))
        if risk <= 0:
            raise ValueError(f"VT31 V4 non-positive requested risk at row {index}")

        row = dict(source)
        row["entry_at"] = source["filled_at"]
        row["entry_price"] = source["entry"]
        row["structural_stop"] = source["initial_stop"]
        row["technical_target"] = source["structural_target"]
        row["legacy_vt31_requested_risk_r"] = source["requested_risk_r"]
        row["legacy_vt31_capital_weighted_net_r"] = source[
            "capital_weighted_net_r"
        ]
        row["legacy_vt31_net_r_per_requested_r"] = str(legacy_net / risk)
        row["economics_status"] = "R_DENOMINATED_ONLY"
        bound.append(row)

    output_dir.mkdir(parents=True, exist_ok=True)
    trades_path = output_dir / "phase18-vt31-v4-bound-trades.jsonl"
    trades_path.write_text(
        "".join(json.dumps(row, sort_keys=True) + "\n" for row in bound),
        encoding="utf-8",
    )
    report = {
        "schema": "qore.cibo.phase18.vt31_v4_bound_replay.v1",
        "identity": "CIBO_PHASE18_VT31_NAS100_V4_BOUND_REPLAY_V1",
        "status": (
            "R_DENOMINATED_GEOMETRY_REPLAY_GREEN_"
            "PROVIDER_CALIBRATION_REQUIRED"
        ),
        "rows": len(bound),
        "parity": {
            "authoritative_v4_json_exact_without_serialized_rows": True,
            "same_signals": True,
            "same_entry": True,
            "same_structural_stop": True,
            "same_technical_target": True,
            "same_market_path": True,
            "same_legacy_capital_weighted_result": True,
        },
        "provider_economics": {
            "status": "CALIBRATION_REQUIRED",
            "usd_cibo_sizing_comparison_authorized": False,
        },
        "source_evidence": {
            "vt31_source_code_sha": (
                "cac38ed14f20e066536910145027426fd23f5939"
            ),
            "r8_artifact_id": 10402199719,
            "r6_artifact_id": 10389112524,
            "r5_artifact_id": 10380044761,
            "authoritative_v4_run_id": 35530059080,
            "authoritative_v4_artifact_id": 10610673464,
            "authoritative_v4_artifact_digest": (
                "sha256:f811bf67db29a9fc0305d4b14e55dd5b33671df6b9ba3ae1c7173f3dd3d14f4d"
            ),
        },
        "legacy_v4_result_5y": authoritative["five_year_result"],
        "governance": {
            "research_only": True,
            "demo_execution_authorized": False,
            "live_authorized": False,
            "real_capital_authorized": False,
            "merge_authorized": False,
        },
    }
    (output_dir / "phase18-vt31-v4-bound-report.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--regenerated", type=Path, required=True)
    parser.add_argument("--authoritative", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = bind(
        regenerated_path=args.regenerated,
        authoritative_path=args.authoritative,
        output_dir=args.output,
    )
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
