"""Burned-evidence non-promotion record for CE2I portfolio/regime tools.

This module freezes negative evidence from the already-burned Phase19 artifact.
It prevents descriptive dependence, temporal measurements, or failed WFO
policies from being silently relabeled as causal calibration.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any

SOURCE_PHASE19_ARTIFACT_ID = 10972948493
SOURCE_PHASE19_ARTIFACT_SHA256 = (
    "e2fcf03ac78e278a22ec53f4f4d6b419ae4d9f5f7a9c674c23fd18c3a4e95527"
)
SOURCE_PHASE19_GIT_SHA = "69288ce31c746c6b0e354b45bdb051d45aa3009d"

BURNED_NON_PROMOTION_REASONS: dict[str, tuple[str, ...]] = {
    "T08": (
        "OVERLAP_DEPENDENCE_DESCRIPTIVE_ONLY",
        "FACTOR_MAP_NOT_CERTIFIED",
        "CORRELATION_NOT_CLAIMED_BY_SOURCE_ARTIFACT",
        "MONETARY_NET_EXPOSURE_NOT_CALIBRATED",
    ),
    "T09": (
        "ZERO_WALK_FORWARD_POLICY_SURVIVORS",
        "NO_ROBUST_COMPETITION_POLICY_IDENTIFIED",
    ),
    "T12": (
        "TEMPORAL_STABILITY_OBSERVATIONAL_ONLY",
        "CAUSAL_REGIME_BOUNDARIES_NOT_IDENTIFIED",
    ),
    "T13": (
        "ZERO_WALK_FORWARD_POLICY_SURVIVORS",
        "NO_ROBUST_DRAWDOWN_RESERVE_POLICY_IDENTIFIED",
    ),
    "T18": (
        "ZERO_WALK_FORWARD_POLICY_SURVIVORS",
        "NO_ROBUST_CROSS_TRADER_ALLOCATION_POLICY_IDENTIFIED",
    ),
}


def burned_non_promotion_payload() -> dict[str, Any]:
    return {
        "schema": "qore.cibo.ce2i.burned_non_promotion.v1",
        "source": {
            "phase19_artifact_id": SOURCE_PHASE19_ARTIFACT_ID,
            "phase19_artifact_sha256": SOURCE_PHASE19_ARTIFACT_SHA256,
            "phase19_git_sha": SOURCE_PHASE19_GIT_SHA,
            "evidence_status": "BURNED_DEVELOPMENT",
        },
        "source_findings": {
            "overlap_dependence_status": (
                "TRAIN_VALIDATION_DEPENDENCE_MEASURED_DESCRIPTIVE_ONLY"
            ),
            "temporal_stability_status": "MEASURED_OBSERVATIONAL_ONLY",
            "walk_forward_status": "POST_FREEZE_FORWARD_VALIDATION_COMPLETE",
            "walk_forward_surviving_policy_count": 0,
            "correlation_claimed": False,
            "provider_economics_used": False,
        },
        "tools": {
            code: {
                "classification": "CALIBRATION_UNAVAILABLE",
                "reasons": list(reasons),
            }
            for code, reasons in BURNED_NON_PROMOTION_REASONS.items()
        },
        "governance": {
            "holdout_2017h1_used": False,
            "provider_usd_economics_claimed": False,
            "descriptive_evidence_promoted_to_causal": False,
            "failed_wfo_policy_promoted": False,
            "target_aware": False,
            "oos_ready": False,
            "certification_ready": False,
        },
    }


def burned_non_promotion_sha256() -> str:
    raw = json.dumps(
        burned_non_promotion_payload(),
        sort_keys=True,
        separators=(",", ":"),
    ).encode()
    return hashlib.sha256(raw).hexdigest()
