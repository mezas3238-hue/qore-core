from __future__ import annotations

from copy import deepcopy

import pytest

from qore.infrastructure.core_stack_v2.shared_b_energy_reference_boundary import (
    SharedBEnergyReferenceBoundaryError,
    build_energy_reference_identity_boundary,
)


def _pack() -> dict[str, object]:
    records = []
    for index, symbol in enumerate(("XBRUSD", "XTIUSD", "XNGUSD"), start=1):
        records.append({
            "asset_world": "ENERGY",
            "provider": "CTRADER_DEMO",
            "provider_symbol_id": index,
            "provider_symbol": symbol,
            "identity_kind": "REFERENCE_OBJECT",
            "current_reference_identity": None,
            "tradable_product_identity_verified": False,
            "front_contract_identity_verified": None,
            "continuous_series_identity_verified": None,
            "roll_semantics_verified": False,
        })
    return {
        "identity": "SHARED_B_COMMODITY_OBSERVATION_IDENTITY_PACK_001",
        "records": records,
    }


def test_exact_three_energy_rows_preserve_unknown_reference_identity() -> None:
    payload = build_energy_reference_identity_boundary(_pack())
    assert payload["energy_sensor_count"] == 3
    assert payload["provider_reference_object_verified_count"] == 3
    assert payload["provider_neutral_reference_identity_verified_count"] == 0
    assert payload["unknown_provider_neutral_identity_count"] == 3
    assert payload["tradable_product_identity_verified_count"] == 0
    assert payload["exchange_venue_identity_verified_count"] == 0
    assert payload["front_contract_identity_verified_count"] == 0
    assert payload["continuous_series_identity_verified_count"] == 0
    assert payload["roll_semantics_verified_count"] == 0
    assert payload["automatic_futures_mapping"] is False
    assert payload["unknown_identity_preserved"] is True
    assert payload["b15_complete"] is False
    assert all(
        row["provider_neutral_reference_identity"] is None
        and row["provider_neutral_reference_identity_verified"] is False
        and row["unknown_identity_preserved"] is True
        for row in payload["records"]
    )


def test_tradable_product_promotion_fails_closed() -> None:
    pack = deepcopy(_pack())
    rows = pack["records"]
    assert isinstance(rows, list)
    rows[0]["tradable_product_identity_verified"] = True
    with pytest.raises(
        SharedBEnergyReferenceBoundaryError,
        match="tradable product authority widened",
    ):
        build_energy_reference_identity_boundary(pack)


def test_unsealed_reference_identity_fails_closed() -> None:
    pack = deepcopy(_pack())
    rows = pack["records"]
    assert isinstance(rows, list)
    rows[1]["current_reference_identity"] = "WTI_LIGHT_SWEET_CRUDE_OIL"
    with pytest.raises(
        SharedBEnergyReferenceBoundaryError,
        match="reference identity unexpectedly present",
    ):
        build_energy_reference_identity_boundary(pack)


def test_front_contract_promotion_fails_closed() -> None:
    pack = deepcopy(_pack())
    rows = pack["records"]
    assert isinstance(rows, list)
    rows[2]["front_contract_identity_verified"] = True
    with pytest.raises(
        SharedBEnergyReferenceBoundaryError,
        match="front-contract authority widened",
    ):
        build_energy_reference_identity_boundary(pack)
