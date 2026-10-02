"""Frozen source-only microstructure representation contract for WP-05 V12."""

from __future__ import annotations

import hashlib
import json
from datetime import UTC
from typing import Final

from qore.infrastructure.core_stack_v2.active_perception_v12_microstructure_foundation import (
    V12CausalMicrostructureSnapshot,
    V12MicrostructureAvailability,
)

REPRESENTATION_IDENTITY: Final = (
    "QORE_SHARED_WP05_ACTIVE_PERCEPTION_V12_MICROSTRUCTURE_REPRESENTATION_001"
)
FROZEN_STALENESS_LIMIT_MS: Final = 30_000
FROZEN_WINDOWS_MS: Final = (1_000, 5_000, 15_000, 60_000)
EXPECTED_SOURCE_ANCHOR_SHA256: Final = (
    "d5dda96fbaab9506e77bd803cf8b542250288e7d46091db1630f1fd8fb91839e"
)
EXPECTED_ANCHOR_OBSERVABILITY_SHA256: Final = (
    "fb81d247bd710bc0d544bd70c442d2ced7d494b7e2ff66a86aa0cbfb1268bc15"
)
EXPECTED_GLOBAL_DATASET_SHA256: Final = (
    "ebbe30a887867bb917f0992b15e1600f9f06eccb07562b9625fcb9517fb381c8"
)

M0_FIELDS: Final = (
    "bid_present",
    "ask_present",
    "bid_fresh",
    "ask_fresh",
    "causal_pair_available",
    "crossed_causal_quote",
    "bid_age_ratio_bps",
    "ask_age_ratio_bps",
    "age_skew_ratio_bps",
    "spread_bps",
)
M1_WINDOW_FIELDS: Final = (
    "bid_update_rate_x1000",
    "ask_update_rate_x1000",
    "total_update_rate_x1000",
    "update_imbalance_bps",
)
M2_WINDOW_FIELDS: Final = (
    "bid_displacement_bps",
    "ask_displacement_bps",
    "bid_path_variation_bps",
    "ask_path_variation_bps",
    "path_variation_asymmetry_bps",
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


def _candidate_fields() -> dict[str, tuple[str, ...]]:
    m1_extra = tuple(
        f"w{window_ms}_{field}"
        for window_ms in FROZEN_WINDOWS_MS
        for field in M1_WINDOW_FIELDS
    )
    m2_extra = tuple(
        f"w{window_ms}_{field}"
        for window_ms in FROZEN_WINDOWS_MS
        for field in M2_WINDOW_FIELDS
    )
    return {
        "M0_QUOTE_STATE": M0_FIELDS,
        "M1_QUOTE_STATE_UPDATE_INTENSITY": M0_FIELDS + m1_extra,
        "M2_QUOTE_STATE_PATH_RESPONSE": M0_FIELDS + m2_extra,
        "M3_FULL_CAUSAL_MICROSTRUCTURE": M0_FIELDS + m1_extra + m2_extra,
    }


def v12_microstructure_candidate_fields() -> dict[str, tuple[str, ...]]:
    """Return the exact preregistered first-experiment candidate columns."""

    return _candidate_fields()


def normalize_v12_microstructure_snapshot(
    snapshot: V12CausalMicrostructureSnapshot,
) -> dict[str, object]:
    """Normalize one causal snapshot using frozen integer-only semantics."""

    if snapshot.staleness_limit_ms != FROZEN_STALENESS_LIMIT_MS:
        raise ValueError("V12 representation staleness drift")
    if tuple(item.window_ms for item in snapshot.windows) != FROZEN_WINDOWS_MS:
        raise ValueError("V12 representation window drift")

    bid_present = snapshot.bid_age_ms is not None
    ask_present = snapshot.ask_age_ms is not None
    bid_fresh = (
        bid_present
        and snapshot.bid_age_ms is not None
        and snapshot.bid_age_ms <= FROZEN_STALENESS_LIMIT_MS
    )
    ask_fresh = (
        ask_present
        and snapshot.ask_age_ms is not None
        and snapshot.ask_age_ms <= FROZEN_STALENESS_LIMIT_MS
    )
    pair_available = (
        snapshot.availability is V12MicrostructureAvailability.AVAILABLE
        and snapshot.crossed_quote is False
    )
    crossed = snapshot.crossed_quote is True

    midpoint: int | None = None
    if pair_available:
        if snapshot.bid_relative_price is None or snapshot.ask_relative_price is None:
            raise ValueError("available pair lost quote prices")
        midpoint = (snapshot.bid_relative_price + snapshot.ask_relative_price) // 2
        if midpoint <= 0:
            raise ValueError("available pair midpoint must be positive")

    row: dict[str, object] = {
        "evaluation_at": snapshot.evaluation_at.astimezone(UTC).isoformat(
            timespec="microseconds"
        ),
        "bid_present": int(bid_present),
        "ask_present": int(ask_present),
        "bid_fresh": int(bid_fresh),
        "ask_fresh": int(ask_fresh),
        "causal_pair_available": int(pair_available),
        "crossed_causal_quote": int(crossed),
        "bid_age_ratio_bps": _ratio_bps(
            snapshot.bid_age_ms,
            FROZEN_STALENESS_LIMIT_MS,
        ),
        "ask_age_ratio_bps": _ratio_bps(
            snapshot.ask_age_ms,
            FROZEN_STALENESS_LIMIT_MS,
        ),
        "age_skew_ratio_bps": (
            None
            if snapshot.bid_age_ms is None or snapshot.ask_age_ms is None
            else min(
                10_000,
                abs(snapshot.bid_age_ms - snapshot.ask_age_ms)
                * 10_000
                // FROZEN_STALENESS_LIMIT_MS,
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
    return row


def v12_microstructure_representation_contract_payload() -> dict[str, object]:
    return {
        "identity": REPRESENTATION_IDENTITY,
        "staleness_limit_ms": FROZEN_STALENESS_LIMIT_MS,
        "windows_ms": list(FROZEN_WINDOWS_MS),
        "source_anchor_sha256": EXPECTED_SOURCE_ANCHOR_SHA256,
        "anchor_observability_sha256": EXPECTED_ANCHOR_OBSERVABILITY_SHA256,
        "global_dataset_sha256": EXPECTED_GLOBAL_DATASET_SHA256,
        "candidate_fields": {
            name: list(fields)
            for name, fields in _candidate_fields().items()
        },
        "arithmetic": "DETERMINISTIC_INTEGER_V1",
        "missingness": "EXPLICIT_INDICATORS_NULL_PAIR_NUMERICS_NO_IMPUTATION",
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


def v12_microstructure_representation_contract_fingerprint() -> str:
    return hashlib.sha256(
        json.dumps(
            v12_microstructure_representation_contract_payload(),
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        ).encode("utf-8")
    ).hexdigest()


def v12_microstructure_rows_sha256(rows: tuple[dict[str, object], ...]) -> str:
    return hashlib.sha256(
        json.dumps(
            rows,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        ).encode("utf-8")
    ).hexdigest()
