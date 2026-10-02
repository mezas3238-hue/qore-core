from __future__ import annotations

import pytest

from qore.infrastructure.core_stack_v2.active_perception_post_v14_sensor_catalog import (
    PostV14ProviderCatalogError,
    freeze_enabled_provider_catalog,
    normalize_provider_symbol,
    provider_catalog_sha256,
)


def test_post_v14_catalog_is_enabled_only_and_deterministic() -> None:
    entries = freeze_enabled_provider_catalog(
        (
            (10015, "US30", True),
            (99999, "DISABLED", False),
            (10013, "US500", True),
            (10015, "US30", True),
        )
    )

    assert [item.provider_symbol for item in entries] == ["US30", "US500"]
    assert [item.provider_symbol_id for item in entries] == [10015, 10013]
    assert all(item.normalized_symbol == item.provider_symbol for item in entries)
    assert len(provider_catalog_sha256(entries)) == 64


def test_post_v14_catalog_normalization_preserves_identity_without_semantics() -> None:
    assert normalize_provider_symbol("US 10Y.cash") == "US10YCASH"


def test_post_v14_catalog_rejects_conflicting_provider_id() -> None:
    with pytest.raises(
        PostV14ProviderCatalogError,
        match="conflicting names",
    ):
        freeze_enabled_provider_catalog(
            (
                (10013, "US500", True),
                (10013, "SP500", True),
            )
        )


def test_post_v14_catalog_rejects_conflicting_provider_name() -> None:
    with pytest.raises(
        PostV14ProviderCatalogError,
        match="conflicting ids",
    ):
        freeze_enabled_provider_catalog(
            (
                (10013, "US500", True),
                (10014, "US500", True),
            )
        )
