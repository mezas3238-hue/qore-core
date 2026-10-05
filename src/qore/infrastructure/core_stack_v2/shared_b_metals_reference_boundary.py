"""Architect-B metals provider reference-object boundary.

The sealed B-15 commodity pack contains eleven METALS rows whose identity kind
is REFERENCE_OBJECT but whose provider-neutral current reference identity is
NULL. This module preserves that unknown state and forbids automatic promotion
to spot benchmarks, exchange products, futures, front contracts or continuous
series.
"""

from __future__ import annotations

import hashlib
import json
from typing import cast

IDENTITY = "SHARED_B_METALS_REFERENCE_IDENTITY_BOUNDARY_001"
EXPECTED_PACK = "SHARED_B_COMMODITY_OBSERVATION_IDENTITY_PACK_001"
_EXPECTED_SYMBOLS = {
    "XAGAUD",
    "XAGEUR",
    "XAGUSD",
    "XAUAUD",
    "XAUCHF",
    "XAUEUR",
    "XAUGBP",
    "XAUJPY",
    "XAUUSD",
    "XPDUSD",
    "XPTUSD",
}


class SharedBMetalsReferenceBoundaryError(ValueError):
    """Metals reference identity boundary failed closed."""


def _fingerprint(value: object) -> str:
    return hashlib.sha256(
        json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        ).encode("utf-8")
    ).hexdigest()


def build_metals_reference_identity_boundary(
    commodity_pack: dict[str, object],
) -> dict[str, object]:
    if commodity_pack.get("identity") != EXPECTED_PACK:
        raise SharedBMetalsReferenceBoundaryError(
            "unexpected commodity pack identity"
        )
    records = commodity_pack.get("records")
    if not isinstance(records, list):
        raise SharedBMetalsReferenceBoundaryError(
            "commodity records missing"
        )

    output: list[dict[str, object]] = []
    seen: set[str] = set()
    for raw in records:
        if not isinstance(raw, dict):
            raise SharedBMetalsReferenceBoundaryError(
                "commodity row invalid"
            )
        row = cast(dict[str, object], raw)
        if row.get("asset_world") != "METALS":
            continue

        symbol = row.get("provider_symbol")
        if not isinstance(symbol, str) or symbol not in _EXPECTED_SYMBOLS:
            raise SharedBMetalsReferenceBoundaryError(
                "unexpected metals provider symbol"
            )
        if symbol in seen:
            raise SharedBMetalsReferenceBoundaryError(
                "duplicate metals provider symbol"
            )
        seen.add(symbol)

        if row.get("identity_kind") != "REFERENCE_OBJECT":
            raise SharedBMetalsReferenceBoundaryError(
                "metals sensor is not reference-only"
            )
        if row.get("current_reference_identity") is not None:
            raise SharedBMetalsReferenceBoundaryError(
                "metals provider-neutral reference identity unexpectedly present"
            )
        if row.get("tradable_product_identity_verified") is not False:
            raise SharedBMetalsReferenceBoundaryError(
                "metals tradable product authority widened"
            )
        if row.get("roll_semantics_verified") is not False:
            raise SharedBMetalsReferenceBoundaryError(
                "metals roll semantics authority widened"
            )
        if row.get("front_contract_identity_verified") not in (None, False):
            raise SharedBMetalsReferenceBoundaryError(
                "metals front-contract authority widened"
            )
        if row.get("continuous_series_identity_verified") not in (None, False):
            raise SharedBMetalsReferenceBoundaryError(
                "metals continuous-series authority widened"
            )

        output.append(
            {
                "provider": row.get("provider"),
                "provider_symbol_id": row.get("provider_symbol_id"),
                "provider_symbol": symbol,
                "identity_kind": "REFERENCE_OBJECT",
                "provider_reference_object_verified": True,
                "provider_neutral_reference_identity": None,
                "provider_neutral_reference_identity_verified": False,
                "tradable_product_identity_verified": False,
                "exchange_venue_identity_verified": False,
                "front_contract_identity_verified": False,
                "continuous_series_identity_verified": False,
                "roll_semantics_verified": False,
                "unknown_identity_preserved": True,
                "automatic_spot_benchmark_mapping": False,
                "automatic_futures_mapping": False,
                "execution_authority": False,
            }
        )

    output.sort(key=lambda row: str(row["provider_symbol"]))
    if seen != _EXPECTED_SYMBOLS or len(output) != 11:
        raise SharedBMetalsReferenceBoundaryError(
            "expected exact 11 provider metals reference objects"
        )

    payload: dict[str, object] = {
        "identity": IDENTITY,
        "status": "EXACT_METALS_PROVIDER_REFERENCE_ONLY_BOUNDARY_FROZEN",
        "metals_sensor_count": 11,
        "provider_reference_object_verified_count": 11,
        "provider_neutral_reference_identity_verified_count": 0,
        "unknown_provider_neutral_identity_count": 11,
        "tradable_product_identity_verified_count": 0,
        "exchange_venue_identity_verified_count": 0,
        "front_contract_identity_verified_count": 0,
        "continuous_series_identity_verified_count": 0,
        "roll_semantics_verified_count": 0,
        "records": output,
        "symbol_similarity_used_as_identity_proof": False,
        "automatic_spot_benchmark_mapping": False,
        "automatic_futures_mapping": False,
        "unknown_identity_preserved": True,
        "target_or_outcome_read": False,
        "r6_r5_read": False,
        "fresh_holdout_opened": False,
        "historical_market_data_read": False,
        "broker_mutation": False,
        "productive_authority": False,
        "b15_complete": False,
    }
    payload["boundary_fingerprint_sha256"] = _fingerprint(payload)
    return payload
