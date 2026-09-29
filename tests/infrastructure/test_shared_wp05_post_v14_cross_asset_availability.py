from __future__ import annotations

import pytest

from qore.infrastructure.core_stack_v2.active_perception_post_v14_cross_asset_availability import (
    FROZEN_CROSS_ASSET_CANDIDATES,
    validate_candidates_against_catalog,
)


def test_post_v14_cross_asset_candidates_are_exact_and_distinct() -> None:
    assert [
        (item.semantic_role, item.provider_symbol, item.provider_symbol_id)
        for item in FROZEN_CROSS_ASSET_CANDIDATES
    ] == [
        ("EQUITY_BREADTH_PROXY", "US2000", 10012),
        ("DEFENSIVE_ASSET_PROXY", "XAUUSD", 41),
        ("CYCLICAL_COMMODITY_PROXY", "XTIUSD", 10019),
    ]


def test_post_v14_cross_asset_candidates_must_exist_exactly_in_catalog() -> None:
    validate_candidates_against_catalog(
        [
            {"provider_symbol": "US2000", "provider_symbol_id": 10012},
            {"provider_symbol": "XAUUSD", "provider_symbol_id": 41},
            {"provider_symbol": "XTIUSD", "provider_symbol_id": 10019},
        ]
    )


def test_post_v14_cross_asset_catalog_drift_fails_closed() -> None:
    with pytest.raises(ValueError, match="provider catalog drift"):
        validate_candidates_against_catalog(
            [
                {"provider_symbol": "US2000", "provider_symbol_id": 99999},
                {"provider_symbol": "XAUUSD", "provider_symbol_id": 41},
                {"provider_symbol": "XTIUSD", "provider_symbol_id": 10019},
            ]
        )
