"""Architect-B cryptocurrency DTI resolution worklist.

Creates an exact 73-sensor provider-neutral identity worklist. Provider labels
remain evidence only. Canonical economic identity requires a governed DTI asset
record; no ticker, description or string-similarity alias is promoted.
"""

from __future__ import annotations

import hashlib
import json
from typing import cast

IDENTITY = "SHARED_B_CRYPTO_DTI_RESOLUTION_WORKLIST_001"
EXPECTED_UNITS = "SHARED_B_CRYPTO_PROVIDER_UNIT_SEMANTICS_001"
EXPECTED_POLICY = "SHARED_B_CRYPTO_DTI_AUTHORITY_POLICY_001"


class SharedBCryptoDtiWorklistError(ValueError):
    """Crypto DTI worklist evidence failed closed."""


def _fingerprint(value: object) -> str:
    return hashlib.sha256(
        json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        ).encode("utf-8")
    ).hexdigest()


def build_crypto_dti_resolution_worklist(
    *,
    unit_semantics: dict[str, object],
    authority_policy: dict[str, object],
) -> dict[str, object]:
    if unit_semantics.get("identity") != EXPECTED_UNITS:
        raise SharedBCryptoDtiWorklistError(
            "unexpected crypto unit-semantics identity"
        )
    if authority_policy.get("identity") != EXPECTED_POLICY:
        raise SharedBCryptoDtiWorklistError(
            "unexpected DTI authority-policy identity"
        )

    if unit_semantics.get("crypto_sensor_count") != 73:
        raise SharedBCryptoDtiWorklistError(
            "crypto sensor population drift"
        )
    if unit_semantics.get("direct_provider_base_unit_count") != 71:
        raise SharedBCryptoDtiWorklistError(
            "direct provider-unit population drift"
        )
    if unit_semantics.get("scaled_provider_base_unit_count") != 2:
        raise SharedBCryptoDtiWorklistError(
            "scaled provider-unit population drift"
        )
    for field in (
        "provider_neutral_reference_identity_complete",
        "canonical_economic_identity_complete",
        "provider_underlying_label_is_canonical_proof",
        "automatic_asset_alias_inference",
        "target_or_outcome_read",
        "r6_r5_read",
        "fresh_holdout_opened",
        "historical_market_data_read",
        "broker_mutation",
        "productive_authority",
        "b06_complete",
    ):
        if unit_semantics.get(field) is not False:
            raise SharedBCryptoDtiWorklistError(
                f"unit-semantics governance drift: {field}"
            )

    policy = authority_policy.get("resolution_policy")
    if not isinstance(policy, dict):
        raise SharedBCryptoDtiWorklistError(
            "DTI resolution policy missing"
        )
    required_policy: dict[str, object] = {
        "provider_symbol_is_canonical_proof": False,
        "provider_base_asset_name_is_canonical_proof": False,
        "provider_description_is_canonical_proof": False,
        "symbol_similarity_alias_inference": False,
        "asset_level_dti_record_required_for_provider_neutral_economic_identity": True,
        "scaled_provider_units_require_underlying_asset_identity_plus_explicit_multiplier": True,
        "dti_asset_identity_is_tradable_product_identity": False,
        "dti_asset_identity_is_provider_listing_identity": False,
        "dti_asset_identity_is_calendar_binding": False,
        "registry_acquisition_policy": (
            "PERMITTED_MACHINE_READABLE_DOWNLOAD_OR_AUTHORIZED_API_ONLY"
        ),
        "automated_html_registry_scraping_authorized": False,
    }
    for key, expected in required_policy.items():
        if policy.get(key) != expected:
            raise SharedBCryptoDtiWorklistError(
                f"DTI authority policy drift: {key}"
            )

    authorities = authority_policy.get("standards")
    if not isinstance(authorities, list) or len(authorities) < 4:
        raise SharedBCryptoDtiWorklistError(
            "DTI authority chain incomplete"
        )
    authority_ids: list[str] = []
    for raw in authorities:
        if not isinstance(raw, dict):
            raise SharedBCryptoDtiWorklistError(
                "DTI authority row invalid"
            )
        authority_id = raw.get("authority_id")
        source_url = raw.get("source_url")
        if (
            not isinstance(authority_id, str)
            or not authority_id
            or not isinstance(source_url, str)
            or not source_url.startswith("https://")
        ):
            raise SharedBCryptoDtiWorklistError(
                "DTI authority id/url invalid"
            )
        authority_ids.append(authority_id)
    if len(authority_ids) != len(set(authority_ids)):
        raise SharedBCryptoDtiWorklistError(
            "DTI authority ids must be unique"
        )

    rows_raw = unit_semantics.get("records")
    if not isinstance(rows_raw, list) or len(rows_raw) != 73:
        raise SharedBCryptoDtiWorklistError(
            "crypto unit records must contain exact 73 rows"
        )

    output: list[dict[str, object]] = []
    seen_keys: set[tuple[str, int]] = set()
    scaled_symbols: set[str] = set()
    for raw in rows_raw:
        if not isinstance(raw, dict):
            raise SharedBCryptoDtiWorklistError(
                "crypto unit row invalid"
            )
        row = cast(dict[str, object], raw)
        provider = row.get("provider")
        symbol_id = row.get("provider_symbol_id")
        symbol = row.get("provider_symbol")
        base = row.get("provider_base_asset_name")
        description = row.get("provider_description")
        underlying = row.get("provider_underlying_label")
        multiplier = row.get("provider_unit_multiplier")
        kind = row.get("provider_unit_kind")
        if (
            not isinstance(provider, str)
            or type(symbol_id) is not int
            or not isinstance(symbol, str)
            or not isinstance(base, str)
            or not isinstance(description, str)
            or not isinstance(underlying, str)
            or type(multiplier) is not int
            or multiplier <= 0
        ):
            raise SharedBCryptoDtiWorklistError(
                "crypto provider identity incomplete"
            )
        key = (provider, symbol_id)
        if key in seen_keys:
            raise SharedBCryptoDtiWorklistError(
                "duplicate crypto provider key"
            )
        seen_keys.add(key)

        blockers = ["DTI_ASSET_RECORD_REQUIRED"]
        if kind == "SCALED_PROVIDER_BASE_UNIT":
            scaled_symbols.add(symbol)
            blockers.append("SCALED_UNIT_UNDERLYING_DTI_BINDING_REQUIRED")
        elif kind != "DIRECT_PROVIDER_BASE_UNIT":
            raise SharedBCryptoDtiWorklistError(
                "unknown provider-unit kind"
            )

        output.append(
            {
                "provider": provider,
                "provider_symbol_id": symbol_id,
                "provider_symbol": symbol,
                "provider_description": description,
                "provider_base_asset_name": base,
                "provider_underlying_label": underlying,
                "provider_unit_kind": kind,
                "provider_unit_multiplier": multiplier,
                "required_provider_neutral_authority": "ISO_24165_DTI_ASSET",
                "dti_asset_identifier": None,
                "dti_asset_identity_verified": False,
                "canonical_economic_identity_verified": False,
                "tradable_product_identity_verified": False,
                "provider_listing_identity_verified": False,
                "canonical_calendar_binding_verified": False,
                "provider_label_used_as_canonical_proof": False,
                "symbol_similarity_alias_inference_used": False,
                "resolution_status": "AUTHORITY_RECORD_REQUIRED",
                "blockers": tuple(sorted(blockers)),
                "sensor_admission_authorized": False,
                "relational_claims_authorized": False,
                "execution_authority": False,
            }
        )

    output.sort(
        key=lambda item: (
            str(item["provider"]),
            int(cast(int, item["provider_symbol_id"])),
        )
    )
    if scaled_symbols != {"1000xSHIB", "1000xPEPE"}:
        raise SharedBCryptoDtiWorklistError(
            "scaled crypto population drift"
        )

    payload: dict[str, object] = {
        "identity": IDENTITY,
        "status": "EXACT_73_CRYPTO_DTI_AUTHORITY_WORKLIST_FROZEN",
        "crypto_sensor_count": 73,
        "dti_asset_identity_verified_count": 0,
        "dti_asset_record_required_count": 73,
        "direct_provider_unit_count": 71,
        "scaled_provider_unit_count": 2,
        "scaled_underlying_binding_required_count": 2,
        "records": output,
        "provider_label_is_canonical_proof": False,
        "automatic_alias_inference": False,
        "registry_html_scraping_authorized": False,
        "registry_machine_readable_or_api_evidence_required": True,
        "provider_neutral_crypto_identity_complete": False,
        "target_or_outcome_read": False,
        "r6_r5_read": False,
        "fresh_holdout_opened": False,
        "historical_market_data_read": False,
        "broker_mutation": False,
        "relational_claims_authorized": False,
        "productive_authority": False,
        "b06_complete": False,
    }
    payload["worklist_fingerprint_sha256"] = _fingerprint(payload)
    return payload
