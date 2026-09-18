from __future__ import annotations

from decimal import Decimal

from qore.infrastructure.trader_lab import (
    turtle_soup_gbpusd_r42_annual_structural_contribution_forensics as r42,
)


def test_r42_is_diagnostic_only() -> None:
    assert r42.SHORT_SCALE == Decimal("0.005")
    assert r42.SOURCE_RUN_ID == 35353073610
    assert r42.SOURCE_ARTIFACT_ID == 10550866581


def test_r42_year_index_covers_exact_five_blocks() -> None:
    assert r42._year_index(r42.datetime(2021, 9, 17, tzinfo=r42.UTC)) == 1
    assert r42._year_index(r42.datetime(2025, 9, 17, tzinfo=r42.UTC)) == 5
