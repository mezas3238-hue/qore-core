from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

from qore.infrastructure.trader_lab import (
    vt08_index_r110_standard_entry_ps_geometry_attribution as r110,
)
from qore.infrastructure.traders.vt08_index_c2_positional_r1 import (
    Vt08IndexC2R1Bar,
)


def _bar(opened: datetime) -> Vt08IndexC2R1Bar:
    return Vt08IndexC2R1Bar(
        opened_at=opened,
        closed_at=opened + timedelta(minutes=15),
        open=Decimal("100"),
        high=Decimal("102"),
        low=Decimal("99"),
        close=Decimal("101"),
    )


def test_r110_structural_bins_are_fixed_not_quantile_learned() -> None:
    assert r110._ratio_bucket(Decimal("0.24")) == "LT_0_25"
    assert r110._ratio_bucket(Decimal("0.25")) == "R_0_25_TO_0_50"
    assert r110._ratio_bucket(Decimal("0.50")) == "R_0_50_TO_1"
    assert r110._ratio_bucket(Decimal("1")) == "GE_1"

    assert r110._extension_bucket(Decimal("0.10")) == "LE_0_10R"
    assert r110._extension_bucket(Decimal("0.11")) == "R_0_10_TO_0_25"
    assert r110._extension_bucket(Decimal("0.30")) == "R_0_25_TO_0_50"
    assert r110._extension_bucket(Decimal("0.51")) == "GT_0_50R"

    assert r110._phase_bucket(3) == "H4_Q1"
    assert r110._phase_bucket(4) == "H4_Q2"
    assert r110._phase_bucket(8) == "H4_Q3"
    assert r110._phase_bucket(12) == "H4_Q4"


def test_r110_causal_bar_lookup_never_uses_bar_closing_after_cutoff() -> None:
    t0 = datetime(2026, 1, 1, tzinfo=UTC)
    bars = tuple(_bar(t0 + timedelta(minutes=15 * i)) for i in range(4))

    assert r110._bar_index_at_or_before(
        bars,
        t0 + timedelta(minutes=30),
    ) == 1
    assert r110._bar_index_at_or_before(
        bars,
        t0 + timedelta(minutes=14),
    ) is None


def test_r110_expected_standard_surface_is_frozen() -> None:
    assert r110.EXPECTED_STANDARD == {
        "5Y": 1756,
        "2Y": 746,
        "R66": 546,
    }


def test_r110_source_r109_is_pinned() -> None:
    assert r110.SOURCE_R109_RUN_ID == 35588958471
    assert r110.SOURCE_R109_ARTIFACT_ID == 10633686630
    assert r110.SOURCE_R109_ARTIFACT_DIGEST == (
        "sha256:8c964890737439fe5c9473bc9d0eb2de2645f5d359f8d7bb99f5b14fefad51e0"
    )
