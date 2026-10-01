from __future__ import annotations

from copy import deepcopy

import pytest

from qore.infrastructure.core_stack_v2.shared_b_crypto_identity_worklist import (
    SharedBCryptoIdentityWorklistError,
    build_crypto_canonical_identity_worklist,
)


def _row(
    *,
    index: int,
    symbol: str,
    base: str,
    description: str,
    unit_kind: str = "DIRECT_PROVIDER_BASE_UNIT",
    multiplier: int = 1,
    underlying: str | None = None,
) -> dict[str, object]:
    return {
        "provider": "CTRADER_DEMO",
        "provider_symbol_id": 10000 + index,
        "provider_symbol": symbol,
        "provider_description": description,
        "provider_base_asset_name": base,
        "provider_quote_asset_name": "USD",
        "provider_unit_kind": unit_kind,
        "provider_unit_multiplier": multiplier,
        "provider_underlying_label": underlying or base,
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
    }


def _units() -> dict[str, object]:
    records: list[dict[str, object]] = []
    for index in range(13):
        base = f"SELF{index}"
        records.append(
            _row(
                index=index,
                symbol=f"{base}USD",
                base=base,
                description=base.lower(),
            )
        )
    for index in range(13, 71):
        base = f"C{index}"
        records.append(
            _row(
                index=index,
                symbol=f"{base}USD",
                base=base,
                description=f"Provider Asset {index}",
            )
        )
    records.extend(
        [
            _row(
                index=71,
                symbol="1000xSHIB",
                base="1000xSHIB",
                description="Shiba Inu",
                unit_kind="SCALED_PROVIDER_BASE_UNIT",
                multiplier=1000,
                underlying="SHIB",
            ),
            _row(
                index=72,
                symbol="1000xPEPE",
                base="1000xPEPE",
                description="Pepe",
                unit_kind="SCALED_PROVIDER_BASE_UNIT",
                multiplier=1000,
                underlying="PEPE",
            ),
        ]
    )
    return {
        "identity": "SHARED_B_CRYPTO_PROVIDER_UNIT_SEMANTICS_001",
        "crypto_sensor_count": 73,
        "provider_unit_semantics_complete": True,
        "canonical_economic_identity_complete": False,
        "records": records,
    }


def test_freezes_exact_external_authority_worklist() -> None:
    payload = build_crypto_canonical_identity_worklist(
        provider_units=_units()
    )
    assert payload["crypto_sensor_count"] == 73
    assert payload["resolution_category_counts"] == {
        "SCALED_PROVIDER_UNIT_UNDERLYING_AUTHORITY_REQUIRED": 2,
        "DIRECT_PROVIDER_SELF_LABEL_EXTERNAL_AUTHORITY_REQUIRED": 13,
        "DIRECT_PROVIDER_DESCRIPTOR_CROSSWALK_REQUIRED": 58,
    }
    assert payload["external_authority_required_count"] == 73
    assert payload["canonical_economic_identity_verified_count"] == 0
    assert payload["provider_neutral_reference_identity_verified_count"] == 0
    assert payload["canonical_calendar_binding_verified_count"] == 0
    assert payload["automatic_asset_alias_inference"] is False
    assert payload["b06_complete"] is False
    assert all(
        row["external_authority_required"] is True
        and row["canonical_economic_identity_verified"] is False
        for row in payload["records"]
    )


def test_provider_label_cannot_be_promoted_upstream() -> None:
    units = deepcopy(_units())
    rows = units["records"]
    assert isinstance(rows, list)
    rows[0]["canonical_economic_identity_verified"] = True
    with pytest.raises(
        SharedBCryptoIdentityWorklistError,
        match="canonical_economic_identity_verified",
    ):
        build_crypto_canonical_identity_worklist(provider_units=units)


def test_scaled_unit_population_must_remain_explicit() -> None:
    units = deepcopy(_units())
    rows = units["records"]
    assert isinstance(rows, list)
    rows[-1]["provider_unit_kind"] = "DIRECT_PROVIDER_BASE_UNIT"
    rows[-1]["provider_unit_multiplier"] = 1
    with pytest.raises(
        SharedBCryptoIdentityWorklistError,
        match="resolution population drift",
    ):
        build_crypto_canonical_identity_worklist(provider_units=units)
