"""Architect-B cryptocurrency provider-unit semantics.

Separates provider denomination mechanics from canonical asset identity.
Scaled provider units such as 1000xSHIB are represented explicitly without
claiming the provider-neutral identity of the underlying cryptoasset.
"""

from __future__ import annotations

import hashlib
import json
import re
from typing import cast

IDENTITY = "SHARED_B_CRYPTO_PROVIDER_UNIT_SEMANTICS_001"
EXPECTED_ATTESTED_IDENTITY = (
    "SHARED_B_PROVIDER_ATTESTED_ECONOMIC_IDENTITY_BOUNDARY_001"
)
_SCALE_RE = re.compile(r"^(?P<scale>[1-9][0-9]*)x(?P<label>[A-Za-z0-9]+)$")


class SharedBCryptoProviderUnitError(ValueError):
    """Crypto provider-unit semantics failed closed."""


def _fingerprint(value: object) -> str:
    return hashlib.sha256(
        json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        ).encode("utf-8")
    ).hexdigest()


def build_crypto_provider_unit_semantics(
    *,
    provider_attested: dict[str, object],
) -> dict[str, object]:
    if provider_attested.get("identity") != EXPECTED_ATTESTED_IDENTITY:
        raise SharedBCryptoProviderUnitError(
            "unexpected provider-attested identity"
        )

    records = provider_attested.get("records")
    if not isinstance(records, list):
        raise SharedBCryptoProviderUnitError("attested records missing")

    output: list[dict[str, object]] = []
    scaled_count = 0
    for raw in records:
        if not isinstance(raw, dict):
            raise SharedBCryptoProviderUnitError("attested row invalid")
        row = cast(dict[str, object], raw)
        if (
            str(row.get("provider_asset_class_name", "")).casefold()
            != "cryptocurrencies"
        ):
            continue

        provider = row.get("provider")
        symbol_id = row.get("provider_symbol_id")
        symbol = row.get("provider_symbol")
        description = row.get("provider_description")
        base = row.get("provider_base_asset_name")
        quote = row.get("provider_quote_asset_name")
        if (
            not isinstance(provider, str)
            or not provider
            or type(symbol_id) is not int
            or symbol_id <= 0
            or not isinstance(symbol, str)
            or not symbol
            or not isinstance(description, str)
            or not description
            or not isinstance(base, str)
            or not base
            or not isinstance(quote, str)
            or not quote
        ):
            raise SharedBCryptoProviderUnitError(
                "crypto provider identity incomplete"
            )

        match = _SCALE_RE.fullmatch(base)
        if match is None:
            unit_kind = "DIRECT_PROVIDER_BASE_UNIT"
            scale = 1
            provider_underlying_label = base
        else:
            unit_kind = "SCALED_PROVIDER_BASE_UNIT"
            scale = int(match.group("scale"))
            provider_underlying_label = match.group("label")
            scaled_count += 1

        output.append({
            "provider": provider,
            "provider_symbol_id": symbol_id,
            "provider_symbol": symbol,
            "provider_description": description,
            "provider_base_asset_name": base,
            "provider_quote_asset_name": quote,
            "provider_unit_kind": unit_kind,
            "provider_unit_multiplier": scale,
            "provider_underlying_label": provider_underlying_label,
            "provider_unit_semantics_verified": True,
            "underlying_label_is_canonical_identity": False,
            "provider_neutral_reference_identity_verified": False,
            "canonical_economic_identity_verified": False,
            "tradable_product_identity_verified": False,
            "listing_identity_verified": False,
            "canonical_calendar_binding_verified": False,
            "historical_pre_freeze_mapping_authorized": False,
            "sensor_admission_authorized": False,
            "relational_claims_authorized": False,
            "execution_authority": False,
        })

    output.sort(
        key=lambda item: (
            str(item["provider"]),
            int(cast(int, item["provider_symbol_id"])),
        )
    )
    if len(output) != 73:
        raise SharedBCryptoProviderUnitError(
            f"expected exact 73 crypto sensors, got {len(output)}"
        )
    if scaled_count != 2:
        raise SharedBCryptoProviderUnitError(
            f"expected exact 2 scaled provider units, got {scaled_count}"
        )
    scaled = [
        row for row in output
        if row["provider_unit_kind"] == "SCALED_PROVIDER_BASE_UNIT"
    ]
    if {
        (row["provider_symbol"], row["provider_unit_multiplier"])
        for row in scaled
    } != {("1000xSHIB", 1000), ("1000xPEPE", 1000)}:
        raise SharedBCryptoProviderUnitError(
            "scaled crypto provider-unit population drift"
        )

    payload: dict[str, object] = {
        "identity": IDENTITY,
        "status": "EXACT_CRYPTO_PROVIDER_UNIT_SEMANTICS_FROZEN",
        "crypto_sensor_count": 73,
        "direct_provider_base_unit_count": 71,
        "scaled_provider_base_unit_count": 2,
        "records": output,
        "provider_unit_semantics_complete": True,
        "provider_neutral_reference_identity_complete": False,
        "canonical_economic_identity_complete": False,
        "provider_underlying_label_is_canonical_proof": False,
        "automatic_asset_alias_inference": False,
        "target_or_outcome_read": False,
        "r6_r5_read": False,
        "fresh_holdout_opened": False,
        "historical_market_data_read": False,
        "broker_mutation": False,
        "productive_authority": False,
        "b06_complete": False,
    }
    payload["semantics_fingerprint_sha256"] = _fingerprint(payload)
    return payload
