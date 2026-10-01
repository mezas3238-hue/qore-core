from __future__ import annotations

from copy import deepcopy

import pytest

from qore.infrastructure.core_stack_v2.shared_b_crypto_dti_worklist import (
    SharedBCryptoDtiWorklistError,
    build_crypto_dti_resolution_worklist,
)


COUNTS = {
    "SCALED_PROVIDER_UNIT_UNDERLYING_AUTHORITY_REQUIRED": 2,
    "DIRECT_PROVIDER_SELF_LABEL_EXTERNAL_AUTHORITY_REQUIRED": 13,
    "DIRECT_PROVIDER_DESCRIPTOR_CROSSWALK_REQUIRED": 58,
}


def _policy() -> dict[str, object]:
    return {
        "identity": "SHARED_B_CRYPTO_DTI_AUTHORITY_POLICY_001",
        "standards": [
            {"authority_id": "A", "source_url": "https://www.iso.org/a"},
            {"authority_id": "B", "source_url": "https://www.iso.org/b"},
            {"authority_id": "C", "source_url": "https://dtif.org/c"},
            {
                "authority_id": "D",
                "source_url": "https://registry.dtif.org/asset",
            },
        ],
        "resolution_policy": {
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
        },
    }


def _row(
    *,
    index: int,
    category: str,
    scaled: bool = False,
) -> dict[str, object]:
    if scaled:
        underlying = "SHIB" if index == 71 else "PEPE"
        symbol = f"1000x{underlying}"
        kind = "SCALED_PROVIDER_BASE_UNIT"
        multiplier = 1000
    else:
        underlying = f"T{index}"
        symbol = f"{underlying}USD"
        kind = "DIRECT_PROVIDER_BASE_UNIT"
        multiplier = 1
    return {
        "provider": "CTRADER_DEMO",
        "provider_symbol_id": 10000 + index,
        "provider_symbol": symbol,
        "provider_description": f"Asset {index}",
        "provider_base_asset_name": (
            symbol if scaled else underlying
        ),
        "provider_underlying_label": underlying,
        "provider_unit_kind": kind,
        "provider_unit_multiplier": multiplier,
        "resolution_category": category,
        "required_evidence": ("OFFICIAL_ASSET_IDENTITY",),
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


def _worklist() -> dict[str, object]:
    records: list[dict[str, object]] = []
    for index in range(13):
        records.append(
            _row(
                index=index,
                category=(
                    "DIRECT_PROVIDER_SELF_LABEL_EXTERNAL_AUTHORITY_REQUIRED"
                ),
            )
        )
    for index in range(13, 71):
        records.append(
            _row(
                index=index,
                category=(
                    "DIRECT_PROVIDER_DESCRIPTOR_CROSSWALK_REQUIRED"
                ),
            )
        )
    for index in range(71, 73):
        records.append(
            _row(
                index=index,
                category=(
                    "SCALED_PROVIDER_UNIT_UNDERLYING_AUTHORITY_REQUIRED"
                ),
                scaled=True,
            )
        )
    return {
        "identity": "SHARED_B_CRYPTO_CANONICAL_IDENTITY_WORKLIST_001",
        "crypto_sensor_count": 73,
        "resolution_category_counts": COUNTS,
        "external_authority_required_count": 73,
        "records": records,
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


def test_refines_exact_73_crypto_rows_with_dti_authority() -> None:
    payload = build_crypto_dti_resolution_worklist(
        identity_worklist=_worklist(),
        authority_policy=_policy(),
    )
    assert payload["crypto_sensor_count"] == 73
    assert payload["upstream_resolution_category_counts"] == COUNTS
    assert payload["dti_asset_identity_verified_count"] == 0
    assert payload["dti_asset_record_required_count"] == 73
    assert payload["scaled_underlying_binding_required_count"] == 2
    assert payload["automatic_alias_inference"] is False
    assert payload["provider_neutral_crypto_identity_complete"] is False
    assert payload["b06_complete"] is False
    assert all(
        row["dti_asset_identifier"] is None
        and row["canonical_economic_identity_verified"] is False
        and row["provider_label_used_as_canonical_proof"] is False
        for row in payload["records"]
    )


def test_scaled_units_require_underlying_dti_binding() -> None:
    payload = build_crypto_dti_resolution_worklist(
        identity_worklist=_worklist(),
        authority_policy=_policy(),
    )
    scaled = [
        row
        for row in payload["records"]
        if row["provider_unit_kind"] == "SCALED_PROVIDER_BASE_UNIT"
    ]
    assert {row["provider_symbol"] for row in scaled} == {
        "1000xSHIB",
        "1000xPEPE",
    }
    assert all(
        "SCALED_UNIT_UNDERLYING_DTI_BINDING_REQUIRED"
        in row["blockers"]
        for row in scaled
    )


def test_ticker_similarity_cannot_be_enabled() -> None:
    policy = deepcopy(_policy())
    resolution = policy["resolution_policy"]
    assert isinstance(resolution, dict)
    resolution["symbol_similarity_alias_inference"] = True
    with pytest.raises(
        SharedBCryptoDtiWorklistError,
        match="symbol_similarity_alias_inference",
    ):
        build_crypto_dti_resolution_worklist(
            identity_worklist=_worklist(),
            authority_policy=policy,
        )
