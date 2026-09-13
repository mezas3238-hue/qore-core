"""Formal fail-closed adjudication for the consumed VT-08 Index R1 evidence."""

from __future__ import annotations

import argparse
import json
from hashlib import sha256
from pathlib import Path
from typing import cast

from qore.kernel.errors import InfrastructureError

SCHEMA = "qore.trader_lab.vt08_index_r1_validation_rejection.v1"
R1_SCHEMA = "qore.trader_lab.vt08_index_c2_positional_r1_backtest.v1"
FORENSICS_SCHEMA = "qore.trader_lab.vt08_index_c2_positional_r1_forensics.v1"
R1_HEAD = "5232540cdb444473ddf0bfae01beb2e672cea344"
FORENSICS_HEAD = "93c233798a6836a387fc11f1cbee1906264967f0"
R1_ARTIFACT_ID = 10323025742
FORENSICS_ARTIFACT_ID = 10325599017
CONSUMED_START = "2024-08-13"
CONSUMED_END = "2026-09-11"


class Vt08IndexR1ValidationRejectionError(InfrastructureError):
    __slots__ = ()


def _load(path: Path, *, name: str) -> tuple[dict[str, object], str]:
    try:
        raw = path.read_bytes()
        decoded: object = json.loads(raw)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise Vt08IndexR1ValidationRejectionError(f"cannot read {name}") from error
    if type(decoded) is not dict or any(type(key) is not str for key in decoded):
        raise Vt08IndexR1ValidationRejectionError(f"{name} must be an object")
    return cast(dict[str, object], decoded), sha256(raw).hexdigest()


def _object(value: object, *, name: str) -> dict[str, object]:
    if type(value) is not dict or any(type(key) is not str for key in value):
        raise Vt08IndexR1ValidationRejectionError(f"{name} must be an object")
    return cast(dict[str, object], value)


def build_rejection(*, r1_path: Path, forensics_path: Path) -> dict[str, object]:
    r1, r1_sha = _load(r1_path, name="R1 artifact")
    forensics, forensics_sha = _load(forensics_path, name="forensics artifact")
    if r1.get("schema") != R1_SCHEMA:
        raise Vt08IndexR1ValidationRejectionError("R1 schema drifted")
    if forensics.get("schema") != FORENSICS_SCHEMA:
        raise Vt08IndexR1ValidationRejectionError("forensics schema drifted")
    if forensics.get("source_replay_head") != R1_HEAD:
        raise Vt08IndexR1ValidationRejectionError("source replay identity drifted")
    if forensics.get("source_freeze_commit") != (
        "31bee8643cb09659a66e9ed793c1cb2bf9ba6353"
    ):
        raise Vt08IndexR1ValidationRejectionError("source freeze identity drifted")
    r1_economics = _object(
        r1.get("aggregate_equal_risk_trade_economics"), name="R1 economics"
    )
    forensic_economics = _object(forensics.get("aggregate"), name="forensic aggregate")
    for field in (
        "sample_size",
        "winning_trades",
        "losing_trades",
        "flat_trades",
        "total_r",
        "mean_r",
        "profit_factor",
        "max_drawdown_r",
        "max_losing_streak",
    ):
        if r1_economics.get(field) != forensic_economics.get(field):
            raise Vt08IndexR1ValidationRejectionError(f"aggregate drifted: {field}")
    diagnostic = _object(
        forensics.get("diagnostic_adjudication"), name="forensic diagnostic"
    )
    if diagnostic.get("evidence_supports_robust_positive_edge") is not False:
        raise Vt08IndexR1ValidationRejectionError("rejection requires failed robustness")
    if forensics.get("methodology_mutation") is not False:
        raise Vt08IndexR1ValidationRejectionError("methodology mutation detected")

    return {
        "schema": SCHEMA,
        "decision": "R1_REJECTED_FOR_PROMOTION",
        "candidate_identity": "VT08_INDEX_C2_POSITIONAL_R1",
        "methodology_fingerprint": r1["methodology_fingerprint"],
        "universe": ["NAS100", "SP500", "US30"],
        "evidence": {
            "r1_head": R1_HEAD,
            "r1_run_id": 34772299203,
            "r1_artifact_id": R1_ARTIFACT_ID,
            "r1_json_sha256": r1_sha,
            "forensics_head": FORENSICS_HEAD,
            "forensics_run_id": 34783956768,
            "forensics_artifact_id": FORENSICS_ARTIFACT_ID,
            "forensics_json_sha256": forensics_sha,
        },
        "consumed_window": {
            "start": CONSUMED_START,
            "end": CONSUMED_END,
            "genuinely_fresh": False,
            "may_be_reused_as_independent_validation": False,
        },
        "economics": r1_economics,
        "failed_gates": [
            "ROBUST_POSITIVE_EDGE",
            "TEMPORAL_STABILITY",
            "CROSS_MARKET_ROBUSTNESS",
            "CROSS_ANCHOR_ROBUSTNESS",
            "BOOTSTRAP_DOWNSIDE_TAIL",
        ],
        "not_run_after_early_rejection": [
            "FRESH_HOLDOUT",
            "FRESH_EXECUTABLE_REPLAY",
            "STRESS_REVIEW",
            "MONTE_CARLO_REVIEW",
            "CIBO_CERTIFICATION_REVIEW",
            "RISK_CERTIFICATION_REVIEW",
            "INDEPENDENT_VALIDATION",
            "ECONOMIC_EVIDENCE_ACCEPTANCE",
        ],
        "source_adjudication": {
            "r1_source_defect_proven": False,
            "r2_authorized_from_r1_outcomes": False,
            "new_source_evidence_required_for_r2": True,
            "unresolved": [
                "universal-poi-selection",
                "protected-swing-selection-when-multiple",
                "universal-contextual-target-selection",
                "numeric-shallow-versus-large-wick-boundary",
            ],
        },
        "governance": {
            "retrospective_subset_selection": False,
            "market_selection_from_outcomes": False,
            "anchor_selection_from_outcomes": False,
            "side_selection_from_outcomes": False,
            "cibo_selection_from_consumed_outcomes": False,
            "fresh_holdout_preserved_unopened": True,
            "demo_eligible": False,
            "live_authorized": False,
            "production_authorized": False,
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--r1", type=Path, required=True)
    parser.add_argument("--forensics", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    payload = build_rejection(r1_path=args.r1, forensics_path=args.forensics)
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(encoded + "\n", encoding="utf-8")
    print(encoded)


if __name__ == "__main__":
    main()
