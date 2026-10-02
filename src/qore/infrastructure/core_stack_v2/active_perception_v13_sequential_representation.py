"""Frozen source-only sequential microstructure representation for WP-05 V13."""

from __future__ import annotations

import hashlib
import json
from typing import Final

from qore.infrastructure.core_stack_v2.active_perception_v12_microstructure_representation import (
    EXPECTED_ANCHOR_OBSERVABILITY_SHA256,
    EXPECTED_GLOBAL_DATASET_SHA256,
    EXPECTED_SOURCE_ANCHOR_SHA256,
    FROZEN_STALENESS_LIMIT_MS,
    FROZEN_WINDOWS_MS,
    v12_microstructure_candidate_fields,
)

V13_REPRESENTATION_IDENTITY: Final = (
    "QORE_SHARED_WP05_SEQUENTIAL_ACTIVE_PERCEPTION_V13_REPRESENTATION_001"
)
V13_CHECKPOINTS_MINUTES: Final = (0, 3, 5, 10, 15)
V13_MIN_CHECKPOINT_COVERAGE_BPS: Final = 9_500
V13_BASE_FEATURES: Final = v12_microstructure_candidate_fields()[
    "M3_FULL_CAUSAL_MICROSTRUCTURE"
]
EXPECTED_V13_ROW_COUNT: Final = 6_804


def v13_flat_feature_names() -> tuple[str, ...]:
    return tuple(
        f"t{minute}_{field}"
        for minute in V13_CHECKPOINTS_MINUTES
        for field in V13_BASE_FEATURES
    )


def v13_representation_contract_payload() -> dict[str, object]:
    return {
        "identity": V13_REPRESENTATION_IDENTITY,
        "checkpoints_minutes": list(V13_CHECKPOINTS_MINUTES),
        "base_representation": "M3_FULL_CAUSAL_MICROSTRUCTURE",
        "base_feature_count": len(V13_BASE_FEATURES),
        "trajectory_feature_count": len(v13_flat_feature_names()),
        "base_feature_names": list(V13_BASE_FEATURES),
        "flat_feature_names": list(v13_flat_feature_names()),
        "staleness_limit_ms": FROZEN_STALENESS_LIMIT_MS,
        "microstructure_windows_ms": list(FROZEN_WINDOWS_MS),
        "minimum_checkpoint_coverage_bps": V13_MIN_CHECKPOINT_COVERAGE_BPS,
        "source_anchor_sha256": EXPECTED_SOURCE_ANCHOR_SHA256,
        "anchor_observability_sha256": EXPECTED_ANCHOR_OBSERVABILITY_SHA256,
        "global_dataset_sha256": EXPECTED_GLOBAL_DATASET_SHA256,
        "checkpoint_event_law": "PROVIDER_EVENT_AT_LTE_CHECKPOINT",
        "missingness": "EXPLICIT_INDICATORS_NULL_NUMERICS_NO_IMPUTATION",
        "bid_ask_pairing": "LATEST_INDEPENDENT_CAUSAL_ASOF_NO_NEAREST_NEIGHBOR",
        "target_or_outcome_read": False,
        "r6_r5_read": False,
        "fresh_holdout_opened": False,
        "shared_methodology_authority": False,
        "shared_sizing_authority": False,
        "shared_risk_authority": False,
        "shared_order_authority": False,
        "shared_execution_authority": False,
    }


def v13_representation_contract_fingerprint() -> str:
    return hashlib.sha256(
        json.dumps(
            v13_representation_contract_payload(),
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        ).encode("utf-8")
    ).hexdigest()


def v13_rows_sha256(rows: tuple[dict[str, object], ...]) -> str:
    return hashlib.sha256(
        json.dumps(
            rows,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        ).encode("utf-8")
    ).hexdigest()


def v13_artifact_fingerprint(
    *,
    contract_fingerprint: str,
    rows_sha256: str,
    checkpoint_coverage_bps: tuple[int, ...],
) -> str:
    if len(checkpoint_coverage_bps) != len(V13_CHECKPOINTS_MINUTES):
        raise ValueError("V13 checkpoint coverage width drift")
    payload = {
        "identity": V13_REPRESENTATION_IDENTITY,
        "contract_fingerprint_sha256": contract_fingerprint,
        "rows_sha256": rows_sha256,
        "checkpoint_coverage_bps": checkpoint_coverage_bps,
        "source_anchor_sha256": EXPECTED_SOURCE_ANCHOR_SHA256,
        "anchor_observability_sha256": EXPECTED_ANCHOR_OBSERVABILITY_SHA256,
        "global_dataset_sha256": EXPECTED_GLOBAL_DATASET_SHA256,
        "row_count": EXPECTED_V13_ROW_COUNT,
    }
    return hashlib.sha256(
        json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        ).encode("utf-8")
    ).hexdigest()
