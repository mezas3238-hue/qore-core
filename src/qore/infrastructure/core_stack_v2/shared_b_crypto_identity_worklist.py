"""Architect-B crypto canonical-identity resolution worklist.

Partitions the exact 73 provider crypto sensors using only already-sealed
provider-unit semantics. The worklist identifies which external evidence is
still required and never treats provider tickers, descriptions or underlying
labels as canonical asset proof.
"""

from __future__ import annotations

import hashlib
import json
from typing import cast

IDENTITY = "SHARED_B_CRYPTO_CANONICAL_IDENTITY_WORKLIST_001"
EXPECTED_INPUT = "SHARED_B_CRYPTO_PROVIDER_UNIT_SEMANTICS_001"


class SharedBCryptoIdentityWorklistError(ValueError):
    """Crypto canonical-identity worklist failed closed."""


def _fingerprint(value: object) -> str:
    return hashlib.sha256(
        json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        ).encode("utf-8")
    ).hexdigest()


def build_crypto_canonical_identity_worklist(
    *,
    provider_units: dict[str, object],
) -> dict[str, object]:
    if provider_units.get("identity") != EXPECTED_INPUT:
        raise SharedBCryptoIdentityWorklistError(
            "unexpected crypto provider-unit identity"
        )
    if provider_units.get("crypto_sensor_count") != 73:
        raise SharedBCryptoIdentityWorklistError(
            "expected exact 73 crypto sensors"
        )
    if provider_units.get("provider_unit_semantics_complete") is not True:
        raise SharedBCryptoIdentityWorklistError(
            "provider-unit semantics not complete"
        )
    if (
        provider_units.get("canonical_economic_identity_complete")
        is not False
    ):
        raise SharedBCryptoIdentityWorklistError(
            "upstream unexpectedly claims canonical identity"
        )

    records = provider_units.get("records")
    if not isinstance(records, list) or len(records) != 73:
        raise SharedBCryptoIdentityWorklistError(
            "crypto provider-unit records missing"
        )

    output: list[dict[str, object]] = []
    provider_keys: set[tuple[str, int]] = set()
    counts = {
        "SCALED_PROVIDER_UNIT_UNDERLYING_AUTHORITY_REQUIRED": 0,
        "DIRECT_PROVIDER_SELF_LABEL_EXTERNAL_AUTHORITY_REQUIRED": 0,
        "DIRECT_PROVIDER_DESCRIPTOR_CROSSWALK_REQUIRED": 0,
    }

    for raw in records:
        if not isinstance(raw, dict):
            raise SharedBCryptoIdentityWorklistError(
                "crypto provider-unit row invalid"
            )
        row = cast(dict[str, object], raw)
        provider = row.get("provider")
        symbol_id = row.get("provider_symbol_id")
        symbol = row.get("provider_symbol")
        description = row.get("provider_description")
        base = row.get("provider_base_asset_name")
        quote = row.get("provider_quote_asset_name")
        unit_kind = row.get("provider_unit_kind")
        multiplier = row.get("provider_unit_multiplier")
        underlying = row.get("provider_underlying_label")
        if (
            not isinstance(provider, str)
            or not provider
            or type(symbol_id) is not int
            or symbol_id <= 0
            or not isinstance(symbol, str)
            or not symbol
            or not isinstance(description, str)
            or not description.strip()
            or not isinstance(base, str)
            or not base
            or quote != "USD"
            or unit_kind not in {
                "DIRECT_PROVIDER_BASE_UNIT",
                "SCALED_PROVIDER_BASE_UNIT",
            }
            or type(multiplier) is not int
            or multiplier <= 0
            or not isinstance(underlying, str)
            or not underlying
        ):
            raise SharedBCryptoIdentityWorklistError(
                "crypto provider-unit row incomplete"
            )

        for field in (
            "provider_unit_semantics_verified",
        ):
            if row.get(field) is not True:
                raise SharedBCryptoIdentityWorklistError(
                    f"upstream unit invariant failed: {field}"
                )
        for field in (
            "underlying_label_is_canonical_identity",
            "provider_neutral_reference_identity_verified",
            "canonical_economic_identity_verified",
            "tradable_product_identity_verified",
            "listing_identity_verified",
            "canonical_calendar_binding_verified",
            "historical_pre_freeze_mapping_authorized",
            "sensor_admission_authorized",
            "relational_claims_authorized",
            "execution_authority",
        ):
            if row.get(field) is not False:
                raise SharedBCryptoIdentityWorklistError(
                    f"forbidden upstream authority widened: {field}"
                )

        key = (provider, symbol_id)
        if key in provider_keys:
            raise SharedBCryptoIdentityWorklistError(
                "duplicate crypto provider key"
            )
        provider_keys.add(key)

        description_self_labels_base = (
            description.strip().casefold() == base.casefold()
        )
        if unit_kind == "SCALED_PROVIDER_BASE_UNIT":
            category = (
                "SCALED_PROVIDER_UNIT_UNDERLYING_AUTHORITY_REQUIRED"
            )
            required_evidence = (
                "OFFICIAL_UNDERLYING_ASSET_IDENTITY",
                "OFFICIAL_UNIT_SCALE_OR_PROVIDER_TO_ASSET_CROSSWALK",
                "CANONICAL_ASSET_IDENTIFIER",
            )
        elif description_self_labels_base:
            category = (
                "DIRECT_PROVIDER_SELF_LABEL_EXTERNAL_AUTHORITY_REQUIRED"
            )
            required_evidence = (
                "OFFICIAL_ASSET_IDENTITY_INDEPENDENT_OF_PROVIDER_LABEL",
                "CANONICAL_ASSET_IDENTIFIER",
            )
        else:
            category = (
                "DIRECT_PROVIDER_DESCRIPTOR_CROSSWALK_REQUIRED"
            )
            required_evidence = (
                "OFFICIAL_PROVIDER_TICKER_TO_ASSET_CROSSWALK",
                "OFFICIAL_ASSET_IDENTITY",
                "CANONICAL_ASSET_IDENTIFIER",
            )
        counts[category] += 1

        symbol_stem = (
            symbol[:-3]
            if unit_kind == "DIRECT_PROVIDER_BASE_UNIT"
            and symbol.endswith("USD")
            else None
        )
        output.append(
            {
                "provider": provider,
                "provider_symbol_id": symbol_id,
                "provider_symbol": symbol,
                "provider_description": description.strip(),
                "provider_base_asset_name": base,
                "provider_quote_asset_name": "USD",
                "provider_unit_kind": unit_kind,
                "provider_unit_multiplier": multiplier,
                "provider_underlying_label": underlying,
                "provider_symbol_stem": symbol_stem,
                "provider_symbol_stem_matches_base": (
                    symbol_stem == base if symbol_stem is not None else False
                ),
                "provider_description_self_labels_base": (
                    description_self_labels_base
                ),
                "resolution_category": category,
                "required_evidence": required_evidence,
                "external_authority_required": True,
                "provider_ticker_is_canonical_proof": False,
                "provider_description_is_canonical_proof": False,
                "provider_underlying_label_is_canonical_proof": False,
                "canonical_economic_identity_verified": False,
                "provider_neutral_reference_identity_verified": False,
                "canonical_calendar_binding_verified": False,
                "sensor_admission_authorized": False,
                "relational_claims_authorized": False,
                "execution_authority": False,
            }
        )

    expected_counts = {
        "SCALED_PROVIDER_UNIT_UNDERLYING_AUTHORITY_REQUIRED": 2,
        "DIRECT_PROVIDER_SELF_LABEL_EXTERNAL_AUTHORITY_REQUIRED": 13,
        "DIRECT_PROVIDER_DESCRIPTOR_CROSSWALK_REQUIRED": 58,
    }
    if counts != expected_counts:
        raise SharedBCryptoIdentityWorklistError(
            f"crypto resolution population drift: {counts}"
        )

    output.sort(
        key=lambda item: (
            str(item["provider"]),
            int(cast(int, item["provider_symbol_id"])),
        )
    )
    payload: dict[str, object] = {
        "identity": IDENTITY,
        "status": "EXACT_73_CRYPTO_CANONICAL_IDENTITY_WORKLIST_FROZEN",
        "crypto_sensor_count": 73,
        "resolution_category_counts": counts,
        "external_authority_required_count": 73,
        "canonical_economic_identity_verified_count": 0,
        "provider_neutral_reference_identity_verified_count": 0,
        "canonical_calendar_binding_verified_count": 0,
        "records": output,
        "automatic_asset_alias_inference": False,
        "symbol_similarity_used_as_identity_proof": False,
        "provider_metadata_is_canonical_proof": False,
        "target_or_outcome_read": False,
        "r6_r5_read": False,
        "fresh_holdout_opened": False,
        "historical_market_data_read": False,
        "broker_mutation": False,
        "productive_authority": False,
        "b06_complete": False,
    }
    payload["worklist_fingerprint_sha256"] = _fingerprint(payload)
    return payload
