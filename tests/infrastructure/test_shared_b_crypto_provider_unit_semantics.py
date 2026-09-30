from __future__ import annotations

from copy import deepcopy

import pytest

from qore.infrastructure.core_stack_v2.shared_b_crypto_provider_unit_semantics import (
    SharedBCryptoProviderUnitError,
    build_crypto_provider_unit_semantics,
)


def _attested() -> dict[str, object]:
    records: list[dict[str, object]] = []
    for index in range(71):
        records.append({
            "provider": "CTRADER_DEMO",
            "provider_symbol_id": 10000 + index,
            "provider_symbol": f"C{index}USD",
            "provider_description": f"Crypto {index}",
            "provider_asset_class_name": "Cryptocurrencies",
            "provider_base_asset_name": f"C{index}",
            "provider_quote_asset_name": "USD",
        })
    records.extend([
        {
            "provider": "CTRADER_DEMO",
            "provider_symbol_id": 20001,
            "provider_symbol": "1000xSHIB",
            "provider_description": "Shiba Inu",
            "provider_asset_class_name": "Cryptocurrencies",
            "provider_base_asset_name": "1000xSHIB",
            "provider_quote_asset_name": "USD",
        },
        {
            "provider": "CTRADER_DEMO",
            "provider_symbol_id": 20002,
            "provider_symbol": "1000xPEPE",
            "provider_description": "Pepe",
            "provider_asset_class_name": "Cryptocurrencies",
            "provider_base_asset_name": "1000xPEPE",
            "provider_quote_asset_name": "USD",
        },
    ])
    return {
        "identity": (
            "SHARED_B_PROVIDER_ATTESTED_ECONOMIC_IDENTITY_BOUNDARY_001"
        ),
        "records": records,
    }


def test_freezes_exact_crypto_unit_semantics_without_asset_inference() -> None:
    payload = build_crypto_provider_unit_semantics(
        provider_attested=_attested()
    )
    assert payload["crypto_sensor_count"] == 73
    assert payload["direct_provider_base_unit_count"] == 71
    assert payload["scaled_provider_base_unit_count"] == 2
    assert payload["provider_unit_semantics_complete"] is True
    assert payload["provider_neutral_reference_identity_complete"] is False
    assert payload["canonical_economic_identity_complete"] is False
    assert payload["automatic_asset_alias_inference"] is False
    assert payload["b06_complete"] is False
    scaled = [
        row for row in payload["records"]
        if row["provider_unit_kind"] == "SCALED_PROVIDER_BASE_UNIT"
    ]
    assert {
        (row["provider_symbol"], row["provider_unit_multiplier"])
        for row in scaled
    } == {("1000xSHIB", 1000), ("1000xPEPE", 1000)}
    assert all(
        row["underlying_label_is_canonical_identity"] is False
        for row in scaled
    )


def test_rejects_scaled_population_drift() -> None:
    attested = deepcopy(_attested())
    rows = attested["records"]
    assert isinstance(rows, list)
    rows[-1]["provider_base_asset_name"] = "PEPE"
    with pytest.raises(
        SharedBCryptoProviderUnitError,
        match="expected exact 2 scaled provider units",
    ):
        build_crypto_provider_unit_semantics(provider_attested=attested)


def test_rejects_missing_provider_identity() -> None:
    attested = deepcopy(_attested())
    rows = attested["records"]
    assert isinstance(rows, list)
    rows[0]["provider_description"] = ""
    with pytest.raises(
        SharedBCryptoProviderUnitError,
        match="crypto provider identity incomplete",
    ):
        build_crypto_provider_unit_semantics(provider_attested=attested)
