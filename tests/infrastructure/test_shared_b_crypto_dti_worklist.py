from __future__ import annotations

from copy import deepcopy

import pytest

from qore.infrastructure.core_stack_v2.shared_b_crypto_dti_worklist import (
    SharedBCryptoDtiWorklistError,
    build_crypto_dti_resolution_worklist,
)


def _policy() -> dict[str, object]:
    return {
        "identity": "SHARED_B_CRYPTO_DTI_AUTHORITY_POLICY_001",
        "standards": [
            {"authority_id": "A", "source_url": "https://www.iso.org/a"},
            {"authority_id": "B", "source_url": "https://www.iso.org/b"},
            {"authority_id": "C", "source_url": "https://dtif.org/c"},
            {"authority_id": "D", "source_url": "https://registry.dtif.org/asset"},
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


def _units() -> dict[str, object]:
    rows: list[dict[str, object]] = []
    for index in range(71):
        base = f"T{index}"
        rows.append(
            {
                "provider": "CTRADER_DEMO",
                "provider_symbol_id": index + 1,
                "provider_symbol": f"{base}USD",
                "provider_description": f"Token {index}",
                "provider_base_asset_name": base,
                "provider_underlying_label": base,
                "provider_unit_kind": "DIRECT_PROVIDER_BASE_UNIT",
                "provider_unit_multiplier": 1,
            }
        )
    for offset, underlying in enumerate(("SHIB", "PEPE"), start=72):
        rows.append(
            {
                "provider": "CTRADER_DEMO",
                "provider_symbol_id": offset,
                "provider_symbol": f"1000x{underlying}",
                "provider_description": underlying,
                "provider_base_asset_name": f"1000x{underlying}",
                "provider_underlying_label": underlying,
                "provider_unit_kind": "SCALED_PROVIDER_BASE_UNIT",
                "provider_unit_multiplier": 1000,
            }
        )
    return {
        "identity": "SHARED_B_CRYPTO_PROVIDER_UNIT_SEMANTICS_001",
        "crypto_sensor_count": 73,
        "direct_provider_base_unit_count": 71,
        "scaled_provider_base_unit_count": 2,
        "records": rows,
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


def test_exact_73_crypto_rows_remain_unpromoted() -> None:
    payload = build_crypto_dti_resolution_worklist(
        unit_semantics=_units(),
        authority_policy=_policy(),
    )
    assert payload["crypto_sensor_count"] == 73
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
        unit_semantics=_units(),
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
            unit_semantics=_units(),
            authority_policy=policy,
        )
