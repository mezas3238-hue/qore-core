"""Frozen source-only cross-peer M3 representation contract for WP-05 V14."""

from __future__ import annotations

import hashlib
import json
from typing import Final

from qore.infrastructure.core_stack_v2.active_perception_v12_microstructure_foundation import (
    V12CausalMicrostructureSnapshot,
    V12MicrostructureAvailability,
)
from qore.infrastructure.core_stack_v2.active_perception_v12_microstructure_representation import (
    FROZEN_WINDOWS_MS,
    v12_microstructure_candidate_fields,
)
from qore.infrastructure.core_stack_v2.active_perception_v14_observability import (
    V14_CHECKPOINTS_MINUTES,
    V14_EXPECTED_SOURCE_ANCHOR_SHA256,
    V14_EXPECTED_SOURCE_COUNT,
    V14_MIN_PEER_CHECKPOINT_COVERAGE_BPS,
    V14_STALENESS_CANDIDATES_MS,
)
from qore.infrastructure.core_stack_v2.active_perception_v14_peer_acquisition import (
    V14PeerFamily,
)

V14_REPRESENTATION_IDENTITY: Final = (
    "QORE_SHARED_WP05_V14_CROSS_MARKET_MICROSTRUCTURE_REPRESENTATION_001"
)
V14_BASE_FEATURES: Final = v12_microstructure_candidate_fields()[
    "M3_FULL_CAUSAL_MICROSTRUCTURE"
]


def v14_flat_feature_names() -> tuple[str, ...]:
    return tuple(
        f"{peer.value.lower()}_t{minute}_{field}"
        for peer in V14PeerFamily
        for minute in V14_CHECKPOINTS_MINUTES
        for field in V14_BASE_FEATURES
    )


def _trunc_ratio_bps(numerator: int, denominator: int) -> int:
    if denominator <= 0:
        return 0
    magnitude = abs(numerator) * 10_000 // denominator
    return magnitude if numerator >= 0 else -magnitude


def _ratio_bps(value: int | None, denominator: int) -> int | None:
    if value is None:
        return None
    return min(10_000, value * 10_000 // denominator)


def normalize_v14_peer_snapshot(
    snapshot: V12CausalMicrostructureSnapshot,
    *,
    selected_staleness_limit_ms: int,
) -> dict[str, object]:
    """Normalize one peer/checkpoint with the exact M3 schema and frozen staleness."""

    if selected_staleness_limit_ms not in V14_STALENESS_CANDIDATES_MS:
        raise ValueError("V14 selected staleness outside preregistered grid")
    if snapshot.staleness_limit_ms != selected_staleness_limit_ms:
        raise ValueError("V14 snapshot staleness drift")
    if tuple(item.window_ms for item in snapshot.windows) != FROZEN_WINDOWS_MS:
        raise ValueError("V14 microstructure window drift")

    bid_present = snapshot.bid_age_ms is not None
    ask_present = snapshot.ask_age_ms is not None
    bid_fresh = (
        bid_present
        and snapshot.bid_age_ms is not None
        and snapshot.bid_age_ms <= selected_staleness_limit_ms
    )
    ask_fresh = (
        ask_present
        and snapshot.ask_age_ms is not None
        and snapshot.ask_age_ms <= selected_staleness_limit_ms
    )
    pair_available = (
        snapshot.availability is V12MicrostructureAvailability.AVAILABLE
        and snapshot.crossed_quote is False
    )
    crossed = snapshot.crossed_quote is True

    midpoint: int | None = None
    if pair_available:
        if snapshot.bid_relative_price is None or snapshot.ask_relative_price is None:
            raise ValueError("V14 available pair lost prices")
        midpoint = (snapshot.bid_relative_price + snapshot.ask_relative_price) // 2
        if midpoint <= 0:
            raise ValueError("V14 midpoint must be positive")

    row: dict[str, object] = {
        "bid_present": int(bid_present),
        "ask_present": int(ask_present),
        "bid_fresh": int(bid_fresh),
        "ask_fresh": int(ask_fresh),
        "causal_pair_available": int(pair_available),
        "crossed_causal_quote": int(crossed),
        "bid_age_ratio_bps": _ratio_bps(
            snapshot.bid_age_ms,
            selected_staleness_limit_ms,
        ),
        "ask_age_ratio_bps": _ratio_bps(
            snapshot.ask_age_ms,
            selected_staleness_limit_ms,
        ),
        "age_skew_ratio_bps": (
            None
            if snapshot.bid_age_ms is None or snapshot.ask_age_ms is None
            else min(
                10_000,
                abs(snapshot.bid_age_ms - snapshot.ask_age_ms)
                * 10_000
                // selected_staleness_limit_ms,
            )
        ),
        "spread_bps": (
            None
            if midpoint is None or snapshot.spread_relative_price is None
            else snapshot.spread_relative_price * 10_000 // midpoint
        ),
    }

    for window in snapshot.windows:
        prefix = f"w{window.window_ms}_"
        bid_rate = window.bid_update_count * 1_000_000 // window.window_ms
        ask_rate = window.ask_update_count * 1_000_000 // window.window_ms
        row[prefix + "bid_update_rate_x1000"] = bid_rate
        row[prefix + "ask_update_rate_x1000"] = ask_rate
        row[prefix + "total_update_rate_x1000"] = bid_rate + ask_rate
        row[prefix + "update_imbalance_bps"] = window.update_imbalance_bps

        if midpoint is None:
            row[prefix + "bid_displacement_bps"] = None
            row[prefix + "ask_displacement_bps"] = None
            row[prefix + "bid_path_variation_bps"] = None
            row[prefix + "ask_path_variation_bps"] = None
            row[prefix + "path_variation_asymmetry_bps"] = None
        else:
            row[prefix + "bid_displacement_bps"] = _trunc_ratio_bps(
                window.bid_displacement,
                midpoint,
            )
            row[prefix + "ask_displacement_bps"] = _trunc_ratio_bps(
                window.ask_displacement,
                midpoint,
            )
            row[prefix + "bid_path_variation_bps"] = (
                window.bid_path_variation * 10_000 // midpoint
            )
            row[prefix + "ask_path_variation_bps"] = (
                window.ask_path_variation * 10_000 // midpoint
            )
            row[prefix + "path_variation_asymmetry_bps"] = _trunc_ratio_bps(
                window.bid_path_variation - window.ask_path_variation,
                window.bid_path_variation + window.ask_path_variation,
            )

    if set(row) != set(V14_BASE_FEATURES):
        raise ValueError("V14 normalized M3 feature membership drift")
    return {field: row[field] for field in V14_BASE_FEATURES}


def v14_representation_contract_payload(
    *,
    selected_staleness_limit_ms: int,
    observability_sha256: str,
    peer_dataset_sha256: dict[str, str],
) -> dict[str, object]:
    if selected_staleness_limit_ms not in V14_STALENESS_CANDIDATES_MS:
        raise ValueError("V14 contract staleness outside frozen grid")
    if set(peer_dataset_sha256) != {peer.value for peer in V14PeerFamily}:
        raise ValueError("V14 contract requires both frozen peer datasets")
    for digest in (observability_sha256, *peer_dataset_sha256.values()):
        if len(digest) != 64:
            raise ValueError("V14 contract requires SHA-256 identities")
        int(digest, 16)
    return {
        "identity": V14_REPRESENTATION_IDENTITY,
        "peer_families": [peer.value for peer in V14PeerFamily],
        "checkpoints_minutes": list(V14_CHECKPOINTS_MINUTES),
        "base_representation": "M3_FULL_CAUSAL_MICROSTRUCTURE",
        "base_feature_count": len(V14_BASE_FEATURES),
        "raw_feature_cell_count": len(v14_flat_feature_names()),
        "flat_feature_names": list(v14_flat_feature_names()),
        "staleness_limit_ms": selected_staleness_limit_ms,
        "staleness_selection_rule": (
            "SMALLEST_SHARED_THRESHOLD_WITH_EVERY_PEER_CHECKPOINT_COVERAGE_GTE_9500_BPS"
        ),
        "microstructure_windows_ms": list(FROZEN_WINDOWS_MS),
        "minimum_peer_checkpoint_coverage_bps": (
            V14_MIN_PEER_CHECKPOINT_COVERAGE_BPS
        ),
        "source_count": V14_EXPECTED_SOURCE_COUNT,
        "source_anchor_sha256": V14_EXPECTED_SOURCE_ANCHOR_SHA256,
        "observability_sha256": observability_sha256,
        "peer_dataset_sha256": dict(sorted(peer_dataset_sha256.items())),
        "checkpoint_event_law": "PROVIDER_EVENT_AT_LTE_CHECKPOINT",
        "bid_ask_pairing": "LATEST_INDEPENDENT_CAUSAL_ASOF_NO_NEAREST_NEIGHBOR",
        "missingness": "EXPLICIT_INDICATORS_NULL_NUMERICS_NO_IMPUTATION",
        "target_or_outcome_read": False,
        "r6_r5_read": False,
        "fresh_holdout_opened": False,
        "scientific_v14_outcomes_opened": False,
        "shared_methodology_authority": False,
        "shared_sizing_authority": False,
        "shared_risk_authority": False,
        "shared_order_authority": False,
        "shared_execution_authority": False,
    }


def v14_representation_contract_fingerprint(payload: dict[str, object]) -> str:
    return hashlib.sha256(
        json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        ).encode("utf-8")
    ).hexdigest()


def v14_rows_sha256(rows: tuple[dict[str, object], ...]) -> str:
    return hashlib.sha256(
        json.dumps(
            rows,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        ).encode("utf-8")
    ).hexdigest()


def v14_representation_artifact_fingerprint(
    *,
    contract_fingerprint: str,
    rows_sha256: str,
    coverage_bps: dict[str, list[int]],
) -> str:
    payload = {
        "identity": V14_REPRESENTATION_IDENTITY,
        "contract_fingerprint_sha256": contract_fingerprint,
        "rows_sha256": rows_sha256,
        "peer_checkpoint_coverage_bps": coverage_bps,
        "source_anchor_sha256": V14_EXPECTED_SOURCE_ANCHOR_SHA256,
        "row_count": V14_EXPECTED_SOURCE_COUNT,
    }
    return hashlib.sha256(
        json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        ).encode("utf-8")
    ).hexdigest()
