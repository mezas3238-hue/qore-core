"""Architect-B energy reference-object identity boundary.

Locks the exact three energy observations already sealed by B-15 to their
proven reference-object scope. It prevents spot-like/provider symbols from
being silently promoted to exchange-listed futures, front contracts or
continuous series.
"""

from __future__ import annotations

import hashlib
import json
from typing import cast

IDENTITY = "SHARED_B_ENERGY_REFERENCE_IDENTITY_BOUNDARY_001"
EXPECTED_PACK = "SHARED_B_COMMODITY_OBSERVATION_IDENTITY_PACK_001"
_EXPECTED = {
    "XBRUSD": "BRENT_CRUDE_OIL_BENCHMARK_FAMILY",
    "XTIUSD": "WTI_LIGHT_SWEET_CRUDE_OIL",
    "XNGUSD": "GENERIC_NATURAL_GAS",
}


class SharedBEnergyReferenceBoundaryError(ValueError):
    """Energy reference identity boundary failed closed."""


def _fingerprint(value: object) -> str:
    return hashlib.sha256(
        json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        ).encode("utf-8")
    ).hexdigest()


def build_energy_reference_identity_boundary(
    commodity_pack: dict[str, object],
) -> dict[str, object]:
    if commodity_pack.get("identity") != EXPECTED_PACK:
        raise SharedBEnergyReferenceBoundaryError(
            "unexpected commodity pack identity"
        )
    records = commodity_pack.get("records")
    if not isinstance(records, list):
        raise SharedBEnergyReferenceBoundaryError(
            "commodity records missing"
        )

    output: list[dict[str, object]] = []
    seen: set[str] = set()
    for raw in records:
        if not isinstance(raw, dict):
            raise SharedBEnergyReferenceBoundaryError(
                "commodity row invalid"
            )
        row = cast(dict[str, object], raw)
        if row.get("asset_world") != "ENERGY":
            continue
        symbol = row.get("provider_symbol")
        if not isinstance(symbol, str) or symbol not in _EXPECTED:
            raise SharedBEnergyReferenceBoundaryError(
                "unexpected energy provider symbol"
            )
        if symbol in seen:
            raise SharedBEnergyReferenceBoundaryError(
                "duplicate energy provider symbol"
            )
        seen.add(symbol)
        if row.get("identity_kind") != "REFERENCE_OBJECT":
            raise SharedBEnergyReferenceBoundaryError(
                "energy sensor is not reference-only"
            )
        if row.get("current_reference_identity") != _EXPECTED[symbol]:
            raise SharedBEnergyReferenceBoundaryError(
                "energy reference identity drift"
            )
        for field in (
            "tradable_product_identity_verified",
            "front_contract_identity_verified",
            "continuous_series_identity_verified",
            "roll_semantics_verified",
        ):
            if row.get(field) is not False:
                raise SharedBEnergyReferenceBoundaryError(
                    f"energy authority widening: {field}"
                )
        output.append(
            {
                "provider": row.get("provider"),
                "provider_symbol_id": row.get("provider_symbol_id"),
                "provider_symbol": symbol,
                "current_reference_identity": row.get(
                    "current_reference_identity"
                ),
                "identity_kind": "REFERENCE_OBJECT",
                "reference_identity_verified": True,
                "tradable_product_identity_verified": False,
                "exchange_venue_identity_verified": False,
                "front_contract_identity_verified": False,
                "continuous_series_identity_verified": False,
                "roll_semantics_verified": False,
                "reference_object_can_be_used_as_futures_identity": False,
                "reference_object_can_define_futures_calendar": False,
                "reference_object_can_define_roll_semantics": False,
                "execution_authority": False,
            }
        )

    output.sort(key=lambda row: str(row["provider_symbol"]))
    if seen != set(_EXPECTED) or len(output) != 3:
        raise SharedBEnergyReferenceBoundaryError(
            "expected exact XBRUSD/XTIUSD/XNGUSD energy set"
        )

    payload: dict[str, object] = {
        "identity": IDENTITY,
        "status": "EXACT_ENERGY_REFERENCE_ONLY_BOUNDARY_FROZEN",
        "energy_sensor_count": 3,
        "reference_identity_verified_count": 3,
        "tradable_product_identity_verified_count": 0,
        "exchange_venue_identity_verified_count": 0,
        "front_contract_identity_verified_count": 0,
        "continuous_series_identity_verified_count": 0,
        "roll_semantics_verified_count": 0,
        "records": output,
        "provider_symbol_similarity_used_as_futures_proof": False,
        "automatic_futures_mapping": False,
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
