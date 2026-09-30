from __future__ import annotations

from copy import deepcopy

import pytest

from qore.infrastructure.core_stack_v2.shared_b_energy_reference_boundary import (
    SharedBEnergyReferenceBoundaryError,
    build_energy_reference_identity_boundary,
)


def _pack() -> dict[str, object]:
    refs = {
        "XBRUSD": "BRENT_CRUDE_OIL_BENCHMARK_FAMILY",
        "XTIUSD": "WTI_LIGHT_SWEET_CRUDE_OIL",
        "XNGUSD": "GENERIC_NATURAL_GAS",
    }
    records = []
    for index, (symbol, identity) in enumerate(refs.items(), start=1):
        records.append({
            "asset_world": "ENERGY",
            "provider": "CTRADER_DEMO",
            "provider_symbol_id": index,
            "provider_symbol": symbol,
            "identity_kind": "REFERENCE_OBJECT",
            "current_reference_identity": identity,
            "tradable_product_identity_verified": False,
            "front_contract_identity_verified": False,
            "continuous_series_identity_verified": False,
            "roll_semantics_verified": False,
        })
    return {
        "identity": "SHARED_B_COMMODITY_OBSERVATION_IDENTITY_PACK_001",
        "records": records,
    }


def test_exact_three_energy_refs_remain_reference_only() -> None:
    payload = build_energy_reference_identity_boundary(_pack())
    assert payload["energy_sensor_count"] == 3
    assert payload["reference_identity_verified_count"] == 3
    assert payload["tradable_product_identity_verified_count"] == 0
    assert payload["exchange_venue_identity_verified_count"] == 0
    assert payload["front_contract_identity_verified_count"] == 0
    assert payload["continuous_series_identity_verified_count"] == 0
    assert payload["roll_semantics_verified_count"] == 0
    assert payload["automatic_futures_mapping"] is False
    assert payload["b15_complete"] is False
    assert all(
        row["reference_object_can_be_used_as_futures_identity"] is False
        for row in payload["records"]
    )


def test_tradable_product_promotion_fails_closed() -> None:
    pack = deepcopy(_pack())
    rows = pack["records"]
    assert isinstance(rows, list)
    rows[0]["tradable_product_identity_verified"] = True
    with pytest.raises(
        SharedBEnergyReferenceBoundaryError,
        match="tradable_product_identity_verified",
    ):
        build_energy_reference_identity_boundary(pack)


def test_reference_identity_drift_fails_closed() -> None:
    pack = deepcopy(_pack())
    rows = pack["records"]
    assert isinstance(rows, list)
    rows[1]["current_reference_identity"] = "NYMEX_CL_FRONT"
    with pytest.raises(
        SharedBEnergyReferenceBoundaryError,
        match="energy reference identity drift",
    ):
        build_energy_reference_identity_boundary(pack)
