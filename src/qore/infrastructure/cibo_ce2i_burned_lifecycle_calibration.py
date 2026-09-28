"""Burned causal lifecycle calibration for T05/T19/T20.

This calibration uses only already-burned Phase19 capital mechanics plus the
existing fail-closed ledger contracts. It freezes causal lifecycle rules, not
economic utility. No 2017H1 outcomes, historical USD execution economics, or
economic targets are used.
"""

from __future__ import annotations

import hashlib
import json

SOURCE_PHASE19_ARTIFACT_ID = 10972948493
SOURCE_PHASE19_ARTIFACT_SHA256 = (
    "e2fcf03ac78e278a22ec53f4f4d6b419ae4d9f5f7a9c674c23fd18c3a4e95527"
)
SOURCE_PHASE19_GIT_SHA = "69288ce31c746c6b0e354b45bdb051d45aa3009d"

T05_RECYCLE_RULES = (
    "CAPACITY_REUSABLE_ONLY_AFTER_AUTHORITATIVE_RELEASE",
    "NO_SAME_TIMESTAMP_EXIT_RECYCLING_WITHOUT_SETTLEMENT_EVIDENCE",
    "RECONCILIATION_PRECEDES_REDEPLOYMENT",
)

T19_RESERVATION_RULES = (
    "RESERVE_BEFORE_DEPLOYMENT",
    "RESERVATION_MUST_NAME_PROVEN_CAPITAL_SOURCE",
    "DUPLICATE_RESERVATION_FORBIDDEN",
    "CAPACITY_CONSERVATION_REQUIRED",
    "GENERATION_CAS_REQUIRED_FOR_DURABLE_UPDATE",
)

T20_RELEASE_RULES = (
    "RELEASE_REQUIRES_VALID_LIFECYCLE_EVENT",
    "DEPLOYED_CAPACITY_NOT_REUSABLE_BEFORE_RECONCILIATION",
    "RELEASE_RESTORES_ONLY_RECONCILED_RETURNED_CAPACITY",
    "PREMATURE_RELEASE_FORBIDDEN",
)


def burned_lifecycle_calibration_payload() -> dict[str, object]:
    return {
        "schema": "qore.cibo.ce2i.burned_lifecycle_calibration.v1",
        "source": {
            "phase19_artifact_id": SOURCE_PHASE19_ARTIFACT_ID,
            "phase19_artifact_sha256": SOURCE_PHASE19_ARTIFACT_SHA256,
            "phase19_git_sha": SOURCE_PHASE19_GIT_SHA,
            "evidence_status": "BURNED_DEVELOPMENT",
        },
        "tools": {
            "T05": {
                "classification": "CALIBRATED_CAUSAL",
                "calibration_space": "NORMALIZED_CAPITAL_LIFECYCLE",
                "rules": list(T05_RECYCLE_RULES),
                "incremental_economic_utility_calibrated": False,
            },
            "T19": {
                "classification": "CALIBRATED_CAUSAL",
                "calibration_space": "CAUSAL_CAPACITY_RESERVATION",
                "rules": list(T19_RESERVATION_RULES),
                "incremental_economic_utility_calibrated": False,
            },
            "T20": {
                "classification": "CALIBRATED_CAUSAL",
                "calibration_space": "CAUSAL_CAPITAL_RELEASE",
                "rules": list(T20_RELEASE_RULES),
                "incremental_economic_utility_calibrated": False,
            },
        },
        "governance": {
            "holdout_2017h1_used": False,
            "provider_usd_economics_claimed": False,
            "target_aware": False,
            "oos_ready": False,
            "certification_ready": False,
        },
    }


def burned_lifecycle_calibration_sha256() -> str:
    encoded = json.dumps(
        burned_lifecycle_calibration_payload(),
        sort_keys=True,
        separators=(",", ":"),
    ).encode()
    return hashlib.sha256(encoded).hexdigest()
