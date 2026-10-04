from __future__ import annotations

from copy import deepcopy

import pytest

from qore.infrastructure.core_stack_v2.shared_b_metals_reference_boundary import (
    SharedBMetalsReferenceBoundaryError,
    build_metals_reference_identity_boundary,
)

SYMBOLS = (
    "XAGAUD",
    "XAGEUR",
    "XAGUSD",
    "XAUAUD",
    "XAUCHF",
    "XAUEUR",
    "XAUGBP",
    "XAUJPY",
    "XAUUSD",
    "XPDUSD",
    "XPTUSD",
)


def _pack() -> dict[str, object]:
    records = []
    for index, symbol in enumerate(SYMBOLS, start=1):
        records.append({
            "asset_world": "METALS",
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


def test_exact_eleven_metals_preserve_unknown_identity() -> None:
    payload = build_metals_reference_identity_boundary(_pack())
    assert payload["metals_sensor_count"] == 11
    assert payload["provider_reference_object_verified_count"] == 11
    assert payload["provider_neutral_reference_identity_verified_count"] == 0
    assert payload["unknown_provider_neutral_identity_count"] == 11
    assert payload["tradable_product_identity_verified_count"] == 0
    assert payload["exchange_venue_identity_verified_count"] == 0
    assert payload["front_contract_identity_verified_count"] == 0
    assert payload["continuous_series_identity_verified_count"] == 0
    assert payload["roll_semantics_verified_count"] == 0
    assert payload["automatic_spot_benchmark_mapping"] is False
    assert payload["automatic_futures_mapping"] is False
    assert payload["unknown_identity_preserved"] is True
    assert payload["b15_complete"] is False
    assert all(
        row["provider_neutral_reference_identity"] is None
        and row["unknown_identity_preserved"] is True
        for row in payload["records"]
    )


def test_reference_identity_guess_fails_closed() -> None:
    pack = deepcopy(_pack())
    rows = pack["records"]
    assert isinstance(rows, list)
    rows[0]["current_reference_identity"] = "SILVER_SPOT"
    with pytest.raises(
        SharedBMetalsReferenceBoundaryError,
        match="reference identity unexpectedly present",
    ):
        build_metals_reference_identity_boundary(pack)


def test_futures_promotion_fails_closed() -> None:
    pack = deepcopy(_pack())
    rows = pack["records"]
    assert isinstance(rows, list)
    rows[8]["tradable_product_identity_verified"] = True
    with pytest.raises(
        SharedBMetalsReferenceBoundaryError,
        match="tradable product authority widened",
    ):
        build_metals_reference_identity_boundary(pack)
