from __future__ import annotations

from copy import deepcopy
from datetime import UTC, datetime, timedelta

import pytest

from qore.infrastructure.core_stack_v2.shared_b_fx_reference_mapping import (
    SharedBFxReferenceMappingError,
    resolve_current_fx_reference_mappings,
)


def _fixtures() -> tuple[dict[str, object], dict[str, object]]:
    captured = "2026-09-29T19:59:30+00:00"
    symbols: list[dict[str, object]] = []
    pairs: list[dict[str, object]] = []
    currencies = (
        "AUD","CAD","CHF","CNH","CZK","DKK","EUR","GBP","HKD","HUF",
        "JPY","MXN","NOK","NZD","PLN","SEK","SGD","THB","TRY","USD","ZAR",
    )
    for index in range(60):
        base = currencies[index % len(currencies)]
        quote = currencies[(index * 7 + 1) % len(currencies)]
        if quote == base:
            quote = currencies[(currencies.index(base) + 1) % len(currencies)]
        symbol = f"{base}{quote}_{index:02d}"
        symbol_id = 1000 + index
        symbols.append(
            {
                "provider": "CTRADER_DEMO",
                "provider_symbol_id": symbol_id,
                "provider_symbol": symbol,
                "provider_native_symbol_name": symbol,
                "provider_base_asset_name": base,
                "provider_quote_asset_name": quote,
                "provider_asset_class_name": "Forex",
            }
        )
        pairs.append(
            {
                "provider": "CTRADER_DEMO",
                "provider_symbol_id": symbol_id,
                "provider_symbol": symbol,
                "base_currency_code": base,
                "quote_currency_code": quote,
                "currency_components_verified": True,
                "provider_neutral_reference_key": f"QORE:FX_REFERENCE:{base}/{quote}",
            }
        )

    provider_schedule: dict[str, object] = {
        "identity": "QORE_SHARED_GEN2_CTRADER_PROVIDER_SCHEDULE_CATALOG_001",
        "captured_at": captured,
        "provider_schedule_catalog_fingerprint_sha256": "a" * 64,
        "symbols": symbols,
    }
    component_resolution: dict[str, object] = {
        "identity": "SHARED_B_GW2_CNH_COMPONENT_IDENTITY_001",
        "currency_component_identity_verified_count": 21,
        "fx_pairs_with_all_currency_components_verified": 60,
        "provider_symbol_to_reference_mapping_authorized": False,
        "resolution_fingerprint_sha256": "b" * 64,
        "pairs": pairs,
    }
    return provider_schedule, component_resolution


def test_current_fx_reference_mapping_closes_exact_60_without_widening() -> None:
    schedule, components = _fixtures()
    known_at = datetime(2026, 9, 30, 17, 0, tzinfo=UTC)

    payload = resolve_current_fx_reference_mappings(
        provider_schedule=schedule,
        component_resolution=components,
        mapping_known_at=known_at,
    )

    assert payload["status"] == "CURRENT_FX_PROVIDER_TO_REFERENCE_MAPPING_COMPLETE"
    assert payload["provider_fx_symbol_count"] == 60
    assert payload["mapped_provider_fx_symbol_count"] == 60
    assert payload["provider_symbol_to_reference_mapping_authorized"] is True
    assert payload["mapping_authority_scope"] == "CURRENT_OBSERVATION_REFERENCE_ONLY"
    assert payload["historical_pre_freeze_mapping_authorized"] is False
    assert payload["canonical_tradable_identity_verified_count"] == 0
    assert payload["listing_identity_verified_count"] == 0
    assert payload["calendar_mapping_authorized"] is False
    assert payload["relational_claims_authorized"] is False
    assert payload["historical_market_data_read"] is False
    assert payload["target_or_outcome_read"] is False
    assert payload["r6_r5_read"] is False
    assert payload["fresh_holdout_opened"] is False
    assert payload["productive_authority"] is False
    assert len(payload["mapping_fingerprint_sha256"]) == 64
    assert all(
        row["effective_from"] == "2026-09-29T19:59:30.000000+00:00"
        and row["known_at"] == "2026-09-30T17:00:00.000000+00:00"
        and row["historical_pre_freeze_mapping_authorized"] is False
        and row["tradable_instrument_identity_verified"] is False
        for row in payload["mappings"]
    )


def test_fx_reference_mapping_rejects_provider_descriptor_drift() -> None:
    schedule, components = _fixtures()
    drifted = deepcopy(schedule)
    symbols = drifted["symbols"]
    assert isinstance(symbols, list)
    symbols[0]["provider_base_asset_name"] = "XXX"

    with pytest.raises(
        SharedBFxReferenceMappingError,
        match="provider descriptor drift",
    ):
        resolve_current_fx_reference_mappings(
            provider_schedule=drifted,
            component_resolution=components,
            mapping_known_at=datetime(2026, 9, 30, 17, 0, tzinfo=UTC),
        )


def test_fx_reference_mapping_rejects_knowledge_before_provider_capture() -> None:
    schedule, components = _fixtures()
    captured = datetime.fromisoformat(str(schedule["captured_at"]))

    with pytest.raises(
        SharedBFxReferenceMappingError,
        match="cannot predate provider freeze",
    ):
        resolve_current_fx_reference_mappings(
            provider_schedule=schedule,
            component_resolution=components,
            mapping_known_at=captured - timedelta(seconds=1),
        )


def test_fx_reference_mapping_rejects_upstream_authority_widening() -> None:
    schedule, components = _fixtures()
    components = deepcopy(components)
    components["provider_symbol_to_reference_mapping_authorized"] = True

    with pytest.raises(
        SharedBFxReferenceMappingError,
        match="widened authority",
    ):
        resolve_current_fx_reference_mappings(
            provider_schedule=schedule,
            component_resolution=components,
            mapping_known_at=datetime(2026, 9, 30, 17, 0, tzinfo=UTC),
        )
