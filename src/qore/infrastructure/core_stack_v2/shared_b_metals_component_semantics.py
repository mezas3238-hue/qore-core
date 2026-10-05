"""Architect-B metals economic-component semantics.

The sealed commodity pack already contains component-verified metal/currency
reference keys. This layer makes that fact explicit without promoting the
reference object to a provider-neutral benchmark, venue, tradable product,
front contract or continuous series.
"""

from __future__ import annotations

import hashlib
import json
from typing import cast

IDENTITY = "SHARED_B_METALS_ECONOMIC_COMPONENT_SEMANTICS_001"
EXPECTED_PACK = "SHARED_B_COMMODITY_OBSERVATION_IDENTITY_PACK_001"

_EXPECTED_REFERENCE_BY_SYMBOL = {
    "XAGAUD": ("XAG", "AUD"),
    "XAGEUR": ("XAG", "EUR"),
    "XAGUSD": ("XAG", "USD"),
    "XAUAUD": ("XAU", "AUD"),
    "XAUCHF": ("XAU", "CHF"),
    "XAUEUR": ("XAU", "EUR"),
    "XAUGBP": ("XAU", "GBP"),
    "XAUJPY": ("XAU", "JPY"),
    "XAUUSD": ("XAU", "USD"),
    "XPDUSD": ("XPD", "USD"),
    "XPTUSD": ("XPT", "USD"),
}


class SharedBMetalsComponentSemanticsError(ValueError):
    """Metals component semantics failed closed."""


def _fingerprint(value: object) -> str:
    return hashlib.sha256(
        json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        ).encode("utf-8")
    ).hexdigest()


def build_metals_economic_component_semantics(
    commodity_pack: dict[str, object],
) -> dict[str, object]:
    if commodity_pack.get("identity") != EXPECTED_PACK:
        raise SharedBMetalsComponentSemanticsError(
            "unexpected commodity pack identity"
        )
    records = commodity_pack.get("records")
    if not isinstance(records, list):
        raise SharedBMetalsComponentSemanticsError(
            "commodity records missing"
        )

    output: list[dict[str, object]] = []
    seen: set[str] = set()
    metal_codes: set[str] = set()
    quote_codes: set[str] = set()

    for raw in records:
        if not isinstance(raw, dict):
            raise SharedBMetalsComponentSemanticsError(
                "commodity row invalid"
            )
        row = cast(dict[str, object], raw)
        if row.get("asset_world") != "METALS":
            continue

        symbol = row.get("provider_symbol")
        if (
            not isinstance(symbol, str)
            or symbol not in _EXPECTED_REFERENCE_BY_SYMBOL
        ):
            raise SharedBMetalsComponentSemanticsError(
                "unexpected metals provider symbol"
            )
        if symbol in seen:
            raise SharedBMetalsComponentSemanticsError(
                "duplicate metals provider symbol"
            )
        seen.add(symbol)

        if row.get("identity_kind") != "REFERENCE_OBJECT":
            raise SharedBMetalsComponentSemanticsError(
                "metals row is not reference object"
            )
        if row.get("identity_status") != "COMPONENT_VERIFIED_REFERENCE":
            raise SharedBMetalsComponentSemanticsError(
                "metals component status is not verified"
            )

        metal_code, quote_code = _EXPECTED_REFERENCE_BY_SYMBOL[symbol]
        expected_identity = (
            f"QORE:METAL_REFERENCE:{metal_code}/{quote_code}"
        )
        if row.get("observation_identity") != expected_identity:
            raise SharedBMetalsComponentSemanticsError(
                f"metals observation identity drift: {symbol}"
            )

        for field in (
            "tradable_product_identity_verified",
            "front_contract_verified",
            "roll_semantics_verified",
            "continuous_series_verified",
            "relational_claims_authorized",
            "execution_authority",
        ):
            if row.get(field) is not False:
                raise SharedBMetalsComponentSemanticsError(
                    f"forbidden authority widened: {field}"
                )

        metal_codes.add(metal_code)
        quote_codes.add(quote_code)
        output.append(
            {
                "provider": row.get("provider"),
                "provider_symbol_id": row.get("provider_symbol_id"),
                "provider_symbol": symbol,
                "observation_identity": expected_identity,
                "economic_metal_code": metal_code,
                "quote_currency_code": quote_code,
                "economic_components_verified": True,
                "provider_reference_object_verified": True,
                "provider_neutral_benchmark_identity": None,
                "provider_neutral_benchmark_identity_verified": False,
                "venue_identity_verified": False,
                "tradable_product_identity_verified": False,
                "front_contract_identity_verified": False,
                "continuous_series_identity_verified": False,
                "roll_semantics_verified": False,
                "benchmark_inferred_from_symbol": False,
                "venue_inferred_from_symbol": False,
                "execution_authority": False,
            }
        )

    output.sort(key=lambda row: str(row["provider_symbol"]))
    if seen != set(_EXPECTED_REFERENCE_BY_SYMBOL) or len(output) != 11:
        raise SharedBMetalsComponentSemanticsError(
            "expected exact 11 metals component-verified references"
        )

    payload: dict[str, object] = {
        "identity": IDENTITY,
        "status": "EXACT_METALS_COMPONENT_SEMANTICS_FROZEN",
        "metals_sensor_count": 11,
        "component_verified_sensor_count": 11,
        "unique_economic_metal_codes": tuple(sorted(metal_codes)),
        "unique_quote_currency_codes": tuple(sorted(quote_codes)),
        "provider_neutral_benchmark_identity_verified_count": 0,
        "venue_identity_verified_count": 0,
        "tradable_product_identity_verified_count": 0,
        "records": output,
        "component_identity_is_benchmark_identity": False,
        "symbol_similarity_used_as_benchmark_proof": False,
        "target_or_outcome_read": False,
        "r6_r5_read": False,
        "fresh_holdout_opened": False,
        "historical_market_data_read": False,
        "broker_mutation": False,
        "relational_claims_authorized": False,
        "productive_authority": False,
        "b06_complete": False,
        "b15_complete": False,
    }
    payload["semantics_fingerprint_sha256"] = _fingerprint(payload)
    return payload
