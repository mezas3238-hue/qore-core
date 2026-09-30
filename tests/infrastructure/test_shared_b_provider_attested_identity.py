from __future__ import annotations

from copy import deepcopy
from datetime import UTC, datetime, timedelta

import pytest

from qore.infrastructure.core_stack_v2.shared_b_provider_attested_identity import (
    SharedBProviderAttestedIdentityError,
    build_provider_attested_identity_boundary,
)


def _schedule() -> dict[str, object]:
    symbols: list[dict[str, object]] = []
    symbol_id = 1
    for index in range(25):
        symbols.append(
            {
                "provider": "CTRADER_DEMO",
                "provider_symbol_id": symbol_id,
                "provider_symbol": f"IDX{index:02d}",
                "provider_asset_class_name": "Indices",
                "provider_description": f"Provider Index {index:02d}",
                "provider_base_asset_name": f"IDX{index:02d}",
                "provider_quote_asset_name": "USD",
            }
        )
        symbol_id += 1

    for index in range(73):
        symbols.append(
            {
                "provider": "CTRADER_DEMO",
                "provider_symbol_id": symbol_id,
                "provider_symbol": f"CRY{index:02d}USD",
                "provider_asset_class_name": "Cryptocurrencies",
                "provider_description": f"Provider Crypto {index:02d}",
                "provider_base_asset_name": f"CRY{index:02d}",
                "provider_quote_asset_name": "USD",
            }
        )
        symbol_id += 1

    while len(symbols) < 177:
        symbols.append(
            {
                "provider": "CTRADER_DEMO",
                "provider_symbol_id": symbol_id,
                "provider_symbol": f"OTHER{symbol_id}",
                "provider_asset_class_name": "Forex",
                "provider_description": f"Other {symbol_id}",
                "provider_base_asset_name": "AAA",
                "provider_quote_asset_name": "BBB",
            }
        )
        symbol_id += 1

    return {
        "identity": (
            "QORE_SHARED_GEN2_CTRADER_PROVIDER_SCHEDULE_CATALOG_001"
        ),
        "captured_at": "2026-09-30T07:00:00+00:00",
        "provider_schedule_catalog_fingerprint_sha256": "a" * 64,
        "symbols": symbols,
    }


def test_materializes_exact_provider_attested_boundary_without_widening() -> None:
    payload = build_provider_attested_identity_boundary(
        provider_schedule=_schedule(),
        known_at=datetime(2026, 9, 30, 20, 0, tzinfo=UTC),
    )

    assert payload["sensor_count"] == 98
    assert payload["index_sensor_count"] == 25
    assert payload["cryptocurrency_sensor_count"] == 73
    assert payload["provider_attested_economic_object_count"] == 98
    assert payload[
        "provider_neutral_reference_identity_verified_count"
    ] == 0
    assert payload["canonical_economic_identity_verified_count"] == 0
    assert payload["provider_metadata_is_canonical_proof"] is False
    assert payload["automatic_identity_inference"] is False
    assert payload["symbol_name_similarity_used"] is False
    assert payload["target_or_outcome_read"] is False
    assert payload["fresh_holdout_opened"] is False
    assert payload["broker_mutation"] is False
    assert payload["productive_authority"] is False
    assert len(payload["boundary_fingerprint_sha256"]) == 64

    rows = payload["records"]
    assert isinstance(rows, list)
    assert len(rows) == 98
    assert all(
        row["identity_stage"] == "PROVIDER_ATTESTED_ECONOMIC_OBJECT"
        for row in rows
    )
    assert all(
        row["evidence_kind"] == "FROZEN_PROVIDER_METADATA"
        for row in rows
    )
    assert all(
        row["provider_neutral_reference_identity_verified"] is False
        for row in rows
    )
    assert all(
        row["canonical_economic_identity_verified"] is False
        for row in rows
    )
    assert all(
        row["tradable_product_identity_verified"] is False
        for row in rows
    )
    assert all(
        row["listing_identity_verified"] is False
        for row in rows
    )
    assert all(
        row["canonical_calendar_binding_verified"] is False
        for row in rows
    )
    assert all(row["execution_authority"] is False for row in rows)


def test_rejects_frozen_population_drift() -> None:
    schedule = deepcopy(_schedule())
    symbols = schedule["symbols"]
    assert isinstance(symbols, list)
    symbols[0]["provider_asset_class_name"] = "Other"

    with pytest.raises(
        SharedBProviderAttestedIdentityError,
        match="unexpected index/crypto population",
    ):
        build_provider_attested_identity_boundary(
            provider_schedule=schedule,
            known_at=datetime(2026, 9, 30, 20, 0, tzinfo=UTC),
        )


def test_rejects_missing_provider_attestation() -> None:
    schedule = deepcopy(_schedule())
    symbols = schedule["symbols"]
    assert isinstance(symbols, list)
    symbols[0]["provider_description"] = ""

    with pytest.raises(
        SharedBProviderAttestedIdentityError,
        match="provider_description missing",
    ):
        build_provider_attested_identity_boundary(
            provider_schedule=schedule,
            known_at=datetime(2026, 9, 30, 20, 0, tzinfo=UTC),
        )


def test_rejects_knowledge_before_provider_capture() -> None:
    schedule = _schedule()
    captured = datetime.fromisoformat(str(schedule["captured_at"]))

    with pytest.raises(
        SharedBProviderAttestedIdentityError,
        match="cannot predate provider capture",
    ):
        build_provider_attested_identity_boundary(
            provider_schedule=schedule,
            known_at=captured - timedelta(seconds=1),
        )
