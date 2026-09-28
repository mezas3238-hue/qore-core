"""Build CIBO burned-only calibration evidence without touching 2017H1."""

from __future__ import annotations

import argparse
import hashlib
import json
import zipfile
from pathlib import Path
from typing import Any

from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)
from qore.infrastructure.cibo_ce2i_calibration_matrix import (
    CIBO_T01_T20_CALIBRATION_MATRIX,
)
from qore.infrastructure.cibo_ce2i_pre_holdout_freeze import (
    CURRENT_HOLDOUT_SEAL_STATE,
    CiboHoldoutSealState,
)

_PHASE19_ARTIFACT_ID = 10972948493
_PHASE19_ARTIFACT_DIGEST = (
    "sha256:e2fcf03ac78e278a22ec53f4f4d6b419"
    "ae4d9f5f7a9c674c23fd18c3a4e95527"
)
_PHASE19_HEAD = "69288ce31c746c6b0e354b45bdb051d45aa3009d"


def _read_json(archive: zipfile.ZipFile, name: str) -> dict[str, Any]:
    try:
        raw = archive.read(name)
    except KeyError as exc:
        raise CiboCapitalManagementError(
            f"burned Phase19 artifact missing {name}"
        ) from exc
    payload = json.loads(raw)
    if not isinstance(payload, dict):
        raise CiboCapitalManagementError(
            f"burned Phase19 payload {name} must be object"
        )
    return payload


def build_report(phase19_zip: Path) -> dict[str, object]:
    if CURRENT_HOLDOUT_SEAL_STATE is not CiboHoldoutSealState.SEALED_UNTOUCHED:
        raise CiboCapitalManagementError(
            "burned calibration requires 2017H1 SEALED_UNTOUCHED"
        )
    if not phase19_zip.is_file():
        raise CiboCapitalManagementError("burned Phase19 ZIP is required")

    archive_sha256 = hashlib.sha256(phase19_zip.read_bytes()).hexdigest()
    expected = _PHASE19_ARTIFACT_DIGEST.removeprefix("sha256:")
    if archive_sha256 != expected:
        raise CiboCapitalManagementError(
            "burned Phase19 artifact digest drift"
        )

    with zipfile.ZipFile(phase19_zip) as archive:
        git_sha = archive.read("git-sha.txt").decode().strip()
        if git_sha != _PHASE19_HEAD:
            raise CiboCapitalManagementError(
                "burned Phase19 artifact Git lineage drift"
            )
        provider = _read_json(
            archive,
            "phase19-provider-economics-inventory.json",
        )
        priors = _read_json(
            archive,
            "phase20-train-expectation-priors.json",
        )
        normalized = _read_json(
            archive,
            "phase19-normalized-capital-mechanics.json",
        )
        overlap = _read_json(
            archive,
            "phase19-overlap-dependence-validation.json",
        )
        wfo = _read_json(
            archive,
            "phase19-causal-walk-forward.json",
        )

    if provider.get("status") != "BLOCKED_PROVIDER_ECONOMICS":
        raise CiboCapitalManagementError(
            "Phase19 provider-economics blocker unexpectedly changed"
        )
    readiness = provider.get("readiness", {})
    if readiness.get("usd_portfolio_replay_authorized") is not False:
        raise CiboCapitalManagementError(
            "Phase19 cannot authorize historical USD replay"
        )
    if priors.get("status") != "FROZEN_TRAIN_ONLY_CAUSAL_PRIOR":
        raise CiboCapitalManagementError(
            "Phase19 train-only causal prior is not frozen"
        )
    prior_governance = priors.get("governance", {})
    if prior_governance.get("future_market_used_at_decision") is not False:
        raise CiboCapitalManagementError(
            "causal prior contains future-market leakage"
        )
    if prior_governance.get("phase19j_validation_rows_consumed_for_fit") != 0:
        raise CiboCapitalManagementError(
            "causal prior consumed validation outcomes"
        )
    if normalized.get("status") != "NORMALIZED_CAPITAL_MECHANICS_BOUND_7_OF_7":
        raise CiboCapitalManagementError(
            "normalized capital mechanics are not bound 7/7"
        )
    if overlap.get("governance", {}).get("descriptive_only") is not True:
        raise CiboCapitalManagementError(
            "overlap evidence must remain descriptive-only"
        )
    if overlap.get("governance", {}).get("provider_economics_used") is not False:
        raise CiboCapitalManagementError(
            "overlap evidence unexpectedly used provider economics"
        )
    if wfo.get("surviving_policy_count") != 0:
        raise CiboCapitalManagementError(
            "burned WFO policy-survival assumption drift"
        )

    matrix = [
        {
            "tool": row.tool_code,
            "implemented": row.implemented,
            "calibrated": row.calibrated,
            "calibration_source": list(row.calibration_source),
            "calibration_type": row.calibration_type.value,
            "provider_economics_required": row.provider_economics_required,
            "fail_closed_status": row.fail_closed,
            "oos_ready": row.oos_ready,
            "certification_ready": row.certification_ready,
            "state": row.classification.value,
            "blocker": list(row.blocker),
        }
        for row in CIBO_T01_T20_CALIBRATION_MATRIX
    ]

    causal_rows = priors.get("rows", {})
    if not isinstance(causal_rows, dict) or len(causal_rows) != 7:
        raise CiboCapitalManagementError(
            "train-only causal prior must cover seven lineages"
        )

    calibration_payload = {
        "T04_R_NORMALIZED": {
            "status": "CALIBRATED_CAUSAL",
            "training_rows": priors["training_rows"],
            "prior_digest_sha256": priors["prior_digest_sha256"],
            "lineages": {
                key: {
                    "expected_structural_r": value["expected_structural_r"],
                    "train_rows": value["train_rows"],
                }
                for key, value in sorted(causal_rows.items())
            },
            "usd_risk_dollar_claimed": False,
        },
        "T10_NORMALIZED_CAPITAL_TIME": {
            "status": "CALIBRATED_CAUSAL",
            "total_opportunities": normalized["total_opportunities"],
            "risk_capacity_minutes_ncu": normalized["risk_capacity_minutes_ncu"],
            "peak_reserved_risk_ncu": normalized["peak_reserved_risk_ncu"],
            "lineage_expected_capital_minutes": {
                key: value["expected_capital_minutes"]
                for key, value in sorted(causal_rows.items())
            },
            "usd_output_per_capital_hour_claimed": False,
        },
        "T08": {
            "status": "CALIBRATION_UNAVAILABLE",
            "reason": (
                "overlap/dependence evidence is descriptive-only; "
                "verified factor map and causal stable correlation are absent"
            ),
        },
        "T09_T18": {
            "status": "CALIBRATION_UNAVAILABLE",
            "reason": "no simple capital policy survived both burned WFO folds",
            "surviving_policy_count": wfo["surviving_policy_count"],
        },
    }
    canonical = json.dumps(
        calibration_payload,
        sort_keys=True,
        separators=(",", ":"),
    ).encode()
    return {
        "schema": "qore.cibo.ce2i.burned_calibration_pack.v1",
        "status": "BURNED_CAUSAL_CALIBRATION_PACK_SEALED",
        "source": {
            "phase19_artifact_id": _PHASE19_ARTIFACT_ID,
            "phase19_artifact_digest": _PHASE19_ARTIFACT_DIGEST,
            "phase19_git_sha": _PHASE19_HEAD,
        },
        "holdout": {
            "state": CURRENT_HOLDOUT_SEAL_STATE.value,
            "2017h1_read": False,
            "2017h1_outcomes_used": False,
            "2017h1_used_for_thresholds": False,
        },
        "economics": {
            "historical_usd_exact_available": False,
            "historical_usd_fabricated": False,
            "provider_status": provider["status"],
            "missing_fields": provider["required_exact_historical_fields"],
        },
        "calibrations": calibration_payload,
        "calibration_payload_sha256": hashlib.sha256(canonical).hexdigest(),
        "matrix": matrix,
        "governance": {
            "burned_evidence_only": True,
            "target_aware": False,
            "holdout_mined": False,
            "engineering_green_is_certification": False,
            "fail_closed_is_certification": False,
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--phase19-artifact", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = build_report(args.phase19_artifact)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report, sort_keys=True, separators=(",", ":")))


if __name__ == "__main__":
    main()
