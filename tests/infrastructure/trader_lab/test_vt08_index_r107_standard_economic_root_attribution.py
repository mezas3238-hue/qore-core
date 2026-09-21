from __future__ import annotations

from decimal import Decimal

from qore.infrastructure.trader_lab import (
    vt08_index_r107_standard_economic_root_attribution as r107,
)


def test_r107_identity_and_source_are_frozen() -> None:
    assert r107.IDENTITY == (
        "VT08_INDEX_R107_STANDARD_ECONOMIC_ROOT_ATTRIBUTION_001"
    )
    assert r107.SOURCE_R106_RUN_ID == 35557035781
    assert r107.SOURCE_R106_ARTIFACT_ID == 10620887519
    assert r107.SOURCE_R106_ARTIFACT_DIGEST == (
        "sha256:6a58a578618ba34bdb960a08d12649220d457823b59e16d871e7cb6f31933efc"
    )


def test_r107_reuses_existing_floor_and_source_target() -> None:
    assert r107.FLOOR == Decimal("0.005")
    assert r107.r80.SOURCE_TARGET_R == Decimal("2")
    assert r107.r80.CANONICAL_TARGET_R == Decimal("2.5")


def test_r107_source_urls_are_primary_ttrades() -> None:
    assert "ttrades.com" in r107.TTRADES_2026_STRATEGY_URL
    assert "ttrades.com" in r107.TTRADES_CONTINUATION_URL


def test_r107_control_policy_is_r102_explicit_full() -> None:
    assert r107.CONTROL_POLICY_ID == "EXPLICIT_FULL_R58_STANDARD_BASE"
