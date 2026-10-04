from __future__ import annotations

from copy import deepcopy

import pytest

from qore.infrastructure.core_stack_v2.shared_b_metals_component_semantics import (
    SharedBMetalsComponentSemanticsError,
    build_metals_economic_component_semantics,
)

PAIRS = {
    "XAGAUD": ("XAG", "AUD"),
    "XAGEUR": ("XAG", "EUR"),
    "XAGUSD": ("XAG", "USD"),
    "XAUAUD": ("XAU", "AUD"),
    "XAUCHF": ("XAU", "CHF"),
    "XAUEUR": ("XAU", "EUR"),
    "XAUGBP": ("XAU", "GBP"),
    "XAUJPY": ("XAU", "JPY"),
    "XAUUSD": ("XAU", "USD"),
    "XPDUSD": ("XPD", "USD"),
    "XPTUSD": ("XPT", "USD"),
}


def _pack() -> dict[str, object]:
    rows: list[dict[str, object]] = []
    for index, (symbol, pair) in enumerate(PAIRS.items(), start=1):
        metal, quote = pair
        rows.append(
            {
                "asset_world": "METALS",
                "provider": "CTRADER_DEMO",
                "provider_symbol_id": index,
                "provider_symbol": symbol,
                "identity_kind": "REFERENCE_OBJECT",
                "identity_status": "COMPONENT_VERIFIED_REFERENCE",
                "observation_identity": (
                    f"QORE:METAL_REFERENCE:{metal}/{quote}"
                ),
                "tradable_product_identity_verified": False,
                "front_contract_verified": False,
                "roll_semantics_verified": False,
                "continuous_series_verified": False,
                "relational_claims_authorized": False,
                "execution_authority": False,
            }
        )
    return {
        "identity": "SHARED_B_COMMODITY_OBSERVATION_IDENTITY_PACK_001",
        "records": rows,
    }


def test_exact_eleven_components_are_explicit_not_benchmarks() -> None:
    payload = build_metals_economic_component_semantics(_pack())
    assert payload["metals_sensor_count"] == 11
    assert payload["component_verified_sensor_count"] == 11
    assert payload["unique_economic_metal_codes"] == (
        "XAG",
        "XAU",
        "XPD",
        "XPT",
    )
    assert payload["unique_quote_currency_codes"] == (
        "AUD",
        "CHF",
        "EUR",
        "GBP",
        "JPY",
        "USD",
    )
    assert payload[
        "provider_neutral_benchmark_identity_verified_count"
    ] == 0
    assert payload["venue_identity_verified_count"] == 0
    assert payload["tradable_product_identity_verified_count"] == 0
    assert payload["component_identity_is_benchmark_identity"] is False
    assert payload["b06_complete"] is False
    assert payload["b15_complete"] is False
    assert all(
        row["economic_components_verified"] is True
        and row["provider_neutral_benchmark_identity"] is None
        and row["provider_neutral_benchmark_identity_verified"] is False
        for row in payload["records"]
    )


def test_observation_identity_drift_fails_closed() -> None:
    pack = deepcopy(_pack())
    rows = pack["records"]
    assert isinstance(rows, list)
    rows[0]["observation_identity"] = "QORE:METAL_REFERENCE:XAU/USD"
    with pytest.raises(
        SharedBMetalsComponentSemanticsError,
        match="observation identity drift",
    ):
        build_metals_economic_component_semantics(pack)


def test_product_authority_widening_fails_closed() -> None:
    pack = deepcopy(_pack())
    rows = pack["records"]
    assert isinstance(rows, list)
    rows[8]["tradable_product_identity_verified"] = True
    with pytest.raises(
        SharedBMetalsComponentSemanticsError,
        match="tradable_product_identity_verified",
    ):
        build_metals_economic_component_semantics(pack)
