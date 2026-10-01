"""Architect-B cryptocurrency DTI authority worklist.

Refines the generic crypto canonical-identity worklist with the governed
provider-neutral authority selected for resolution: ISO 24165 / DTI Asset.
No provider ticker, description, label, or similarity heuristic is promoted.
"""

from __future__ import annotations

import hashlib
import json
from typing import cast

IDENTITY = "SHARED_B_CRYPTO_DTI_RESOLUTION_WORKLIST_001"
EXPECTED_WORKLIST = "SHARED_B_CRYPTO_CANONICAL_IDENTITY_WORKLIST_001"
EXPECTED_POLICY = "SHARED_B_CRYPTO_DTI_AUTHORITY_POLICY_001"


class SharedBCryptoDtiWorklistError(ValueError):
    """Crypto DTI authority worklist failed closed."""


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
    identity_worklist: dict[str, object],
    authority_policy: dict[str, object],
) -> dict[str, object]:
    if identity_worklist.get("identity") != EXPECTED_WORKLIST:
        raise SharedBCryptoDtiWorklistError(
            "unexpected crypto identity-worklist identity"
        )
    if authority_policy.get("identity") != EXPECTED_POLICY:
        raise SharedBCryptoDtiWorklistError(
            "unexpected DTI authority-policy identity"
        )

    expected_counts = {
        "SCALED_PROVIDER_UNIT_UNDERLYING_AUTHORITY_REQUIRED": 2,
        "DIRECT_PROVIDER_SELF_LABEL_EXTERNAL_AUTHORITY_REQUIRED": 13,
        "DIRECT_PROVIDER_DESCRIPTOR_CROSSWALK_REQUIRED": 58,
    }
    if identity_worklist.get("crypto_sensor_count") != 73:
        raise SharedBCryptoDtiWorklistError(
            "crypto sensor population drift"
        )
    if identity_worklist.get("resolution_category_counts") != expected_counts:
        raise SharedBCryptoDtiWorklistError(
            "crypto resolution-category population drift"
        )
    if identity_worklist.get("external_authority_required_count") != 73:
        raise SharedBCryptoDtiWorklistError(
            "external-authority population drift"
        )
    for field in (
        "automatic_asset_alias_inference",
        "symbol_similarity_used_as_identity_proof",
        "provider_metadata_is_canonical_proof",
        "target_or_outcome_read",
        "r6_r5_read",
        "fresh_holdout_opened",
        "historical_market_data_read",
        "broker_mutation",
        "productive_authority",
        "b06_complete",
    ):
        if identity_worklist.get(field) is not False:
            raise SharedBCryptoDtiWorklistError(
                f"identity-worklist governance drift: {field}"
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

    rows_raw = identity_worklist.get("records")
    if not isinstance(rows_raw, list) or len(rows_raw) != 73:
        raise SharedBCryptoDtiWorklistError(
            "crypto identity worklist must contain exact 73 rows"
        )

    output: list[dict[str, object]] = []
    seen_keys: set[tuple[str, int]] = set()
    scaled_symbols: set[str] = set()
    category_counts = {key: 0 for key in expected_counts}

    for raw in rows_raw:
        if not isinstance(raw, dict):
            raise SharedBCryptoDtiWorklistError(
                "crypto identity-worklist row invalid"
            )
        row = cast(dict[str, object], raw)
        provider = row.get("provider")
        symbol_id = row.get("provider_symbol_id")
        symbol = row.get("provider_symbol")
        category = row.get("resolution_category")
        multiplier = row.get("provider_unit_multiplier")
        kind = row.get("provider_unit_kind")
        if (
            not isinstance(provider, str)
            or type(symbol_id) is not int
            or not isinstance(symbol, str)
            or not isinstance(category, str)
            or category not in category_counts
            or type(multiplier) is not int
            or multiplier <= 0
        ):
            raise SharedBCryptoDtiWorklistError(
                "crypto identity-worklist row incomplete"
            )
        key = (provider, symbol_id)
        if key in seen_keys:
            raise SharedBCryptoDtiWorklistError(
                "duplicate crypto provider key"
            )
        seen_keys.add(key)
        category_counts[category] += 1

        for field in (
            "external_authority_required",
        ):
            if row.get(field) is not True:
                raise SharedBCryptoDtiWorklistError(
                    f"upstream authority requirement drift: {field}"
                )
        for field in (
            "provider_ticker_is_canonical_proof",
            "provider_description_is_canonical_proof",
            "provider_underlying_label_is_canonical_proof",
            "canonical_economic_identity_verified",
            "provider_neutral_reference_identity_verified",
            "canonical_calendar_binding_verified",
            "sensor_admission_authorized",
            "relational_claims_authorized",
            "execution_authority",
        ):
            if row.get(field) is not False:
                raise SharedBCryptoDtiWorklistError(
                    f"forbidden upstream authority widened: {field}"
                )

        blockers = ["DTI_ASSET_RECORD_REQUIRED"]
        if kind == "SCALED_PROVIDER_BASE_UNIT":
            scaled_symbols.add(symbol)
            blockers.append(
                "SCALED_UNIT_UNDERLYING_DTI_BINDING_REQUIRED"
            )
        elif kind != "DIRECT_PROVIDER_BASE_UNIT":
            raise SharedBCryptoDtiWorklistError(
                "unknown provider-unit kind"
            )

        output.append(
            {
                "provider": provider,
                "provider_symbol_id": symbol_id,
                "provider_symbol": symbol,
                "provider_description": row.get("provider_description"),
                "provider_base_asset_name": row.get(
                    "provider_base_asset_name"
                ),
                "provider_underlying_label": row.get(
                    "provider_underlying_label"
                ),
                "provider_unit_kind": kind,
                "provider_unit_multiplier": multiplier,
                "upstream_resolution_category": category,
                "upstream_required_evidence": row.get(
                    "required_evidence"
                ),
                "required_provider_neutral_authority": (
                    "ISO_24165_DTI_ASSET"
                ),
                "dti_asset_identifier": None,
                "dti_asset_identity_verified": False,
                "canonical_economic_identity_verified": False,
                "tradable_product_identity_verified": False,
                "provider_listing_identity_verified": False,
                "canonical_calendar_binding_verified": False,
                "provider_label_used_as_canonical_proof": False,
                "symbol_similarity_alias_inference_used": False,
                "resolution_status": "DTI_ASSET_RECORD_REQUIRED",
                "blockers": tuple(sorted(blockers)),
                "sensor_admission_authorized": False,
                "relational_claims_authorized": False,
                "execution_authority": False,
            }
        )

    if category_counts != expected_counts:
        raise SharedBCryptoDtiWorklistError(
            f"crypto category recount drift: {category_counts}"
        )
    if scaled_symbols != {"1000xSHIB", "1000xPEPE"}:
        raise SharedBCryptoDtiWorklistError(
            "scaled crypto population drift"
        )

    output.sort(
        key=lambda item: (
            str(item["provider"]),
            int(cast(int, item["provider_symbol_id"])),
        )
    )
    payload: dict[str, object] = {
        "identity": IDENTITY,
        "status": "EXACT_73_CRYPTO_DTI_AUTHORITY_WORKLIST_FROZEN",
        "crypto_sensor_count": 73,
        "upstream_resolution_category_counts": category_counts,
        "dti_asset_identity_verified_count": 0,
        "dti_asset_record_required_count": 73,
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
