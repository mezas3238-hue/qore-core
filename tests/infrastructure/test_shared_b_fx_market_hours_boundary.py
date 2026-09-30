from __future__ import annotations

from copy import deepcopy

import pytest

from qore.infrastructure.core_stack_v2.shared_b_fx_market_hours_boundary import (
    SharedBFxMarketHoursError,
    build_fx_market_hours_boundary,
)


def _fixtures() -> tuple[dict[str, object], dict[str, object]]:
    symbols = [
        {
            "provider": "CTRADER_DEMO",
            "provider_symbol": f"FX{index:02d}",
            "provider_symbol_id": 1000 + index,
            "provider_asset_class_name": "Forex",
            "provider_schedule_available": True,
            "provider_schedule_timezone": "UTC",
        }
        for index in range(60)
    ]
    provider: dict[str, object] = {
        "identity": "QORE_SHARED_GEN2_CTRADER_PROVIDER_SCHEDULE_CATALOG_001",
        "symbols": symbols,
    }
    authority: dict[str, object] = {
        "identity": "SHARED_B_FX_MARKET_HOURS_AUTHORITY_EVIDENCE_001",
        "authorities": [
            {
                "authority_id": "A",
                "source_url": "https://example.com/a",
            },
            {
                "authority_id": "B",
                "source_url": "https://example.com/b",
            },
            {
                "authority_id": "C",
                "source_url": "https://example.com/c",
            },
        ],
        "frozen_conclusions": {
            "canonical_market_structure": "DISTRIBUTED_OTC",
            "single_canonical_venue_exists": False,
            "daily_24_hour_operation_supported": True,
            "exact_universal_weekly_boundary_verified": False,
            "provider_schedule_is_canonical_market_hours": False,
            "canonical_market_closed_state_derivable_from_provider_schedule": False,
            "unknown_required_when_global_market_state_unresolved": True,
        },
    }
    return provider, authority


def test_fx_boundary_freezes_60_without_fabricating_calendar() -> None:
    provider, authority = _fixtures()
    payload = build_fx_market_hours_boundary(
        provider_schedule=provider,
        authority_evidence=authority,
    )

    assert payload["fx_sensor_count"] == 60
    assert payload["canonical_market_structure"] == "DISTRIBUTED_OTC"
    assert payload["single_canonical_venue_count"] == 0
    assert payload["daily_24_hour_operation_supported"] is True
    assert payload["exact_universal_weekly_boundary_verified"] is False
    assert payload["canonical_calendar_verified_count"] == 0
    assert payload["provider_schedule_is_canonical_market_hours"] is False
    assert (
        payload["canonical_market_closed_state_derivable_from_provider_schedule"]
        is False
    )
    assert payload["unknown_required_when_global_market_state_unresolved"] is True
    assert payload["calendar_mapping_complete"] is False
    assert payload["relational_claims_authorized"] is False
    assert all(
        row["canonical_market_structure"] == "DISTRIBUTED_OTC"
        and row["canonical_single_venue"] is None
        and row["market_closed_if_provider_closed"] is False
        and row["calendar_binding_authorized"] is False
        and row["relational_comparability_authorized"] is False
        for row in payload["records"]
    )


def test_provider_schedule_cannot_promote_canonical_market_close() -> None:
    provider, authority = _fixtures()
    changed = deepcopy(provider)
    symbols = changed["symbols"]
    assert isinstance(symbols, list)
    symbols[0]["provider_schedule_available"] = False
    symbols[0]["provider_schedule_timezone"] = "America/New_York"

    payload = build_fx_market_hours_boundary(
        provider_schedule=changed,
        authority_evidence=authority,
    )

    first = payload["records"][0]
    assert first["provider_schedule_available"] is False
    assert first["provider_schedule_timezone"] == "America/New_York"
    assert first["provider_schedule_role"] == "PROVIDER_OBSERVABILITY_ONLY"
    assert first["market_closed_if_provider_closed"] is False
    assert first["canonical_calendar_status"] == "UNRESOLVED"


def test_exact_weekly_boundary_cannot_be_silently_promoted() -> None:
    provider, authority = _fixtures()
    authority = deepcopy(authority)
    conclusions = authority["frozen_conclusions"]
    assert isinstance(conclusions, dict)
    conclusions["exact_universal_weekly_boundary_verified"] = True

    with pytest.raises(
        SharedBFxMarketHoursError,
        match="exact_universal_weekly_boundary_verified",
    ):
        build_fx_market_hours_boundary(
            provider_schedule=provider,
            authority_evidence=authority,
        )


def test_fx_boundary_rejects_incomplete_provider_population() -> None:
    provider, authority = _fixtures()
    provider = deepcopy(provider)
    symbols = provider["symbols"]
    assert isinstance(symbols, list)
    symbols.pop()

    with pytest.raises(
        SharedBFxMarketHoursError,
        match="expected exact 60",
    ):
        build_fx_market_hours_boundary(
            provider_schedule=provider,
            authority_evidence=authority,
        )
