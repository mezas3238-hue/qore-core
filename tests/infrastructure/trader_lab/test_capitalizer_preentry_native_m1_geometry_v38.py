from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

import pytest

from qore.infrastructure.trader_lab import (
    capitalizer_owner_h1_m3_m1_causal_reversal_1y_v3 as v3,
)
from qore.infrastructure.trader_lab import (
    capitalizer_preentry_native_m1_geometry_v38 as v38,
)
from qore.infrastructure.trader_lab.capitalizer_exposure_graph import (
    CapitalizerSide,
)


def _mss() -> v3.M3MssEvent:
    return v3.M3MssEvent(
        side=CapitalizerSide.LONG,
        confirmed_at=datetime(2026, 1, 5, 10, 3, tzinfo=UTC),
        displacement_opened_at=datetime(2026, 1, 5, 10, 0, tzinfo=UTC),
        displacement_closed_at=datetime(2026, 1, 5, 10, 3, tzinfo=UTC),
        broken_swing_price=Decimal("99.8"),
        cisd_boundary=Decimal("100"),
        body_ratio=Decimal("0.8"),
        atr14=Decimal("0.5"),
        displacement_range=Decimal("0.6"),
    )


def _zone() -> v3.M1EntryZone:
    return v3.M1EntryZone(
        ob_opened_at=datetime(2026, 1, 5, 9, 59, tzinfo=UTC),
        ob_low=Decimal("99.6"),
        ob_high=Decimal("99.9"),
        fvg_confirmed_at=datetime(2026, 1, 5, 10, 2, tzinfo=UTC),
        fvg_low=Decimal("100.0"),
        fvg_high=Decimal("100.2"),
        overlap_low=None,
        overlap_high=None,
    )


def test_geometry_is_strictly_preentry_and_risk_normalized() -> None:
    row = v38.build_geometry(
        symbol="EURUSD",
        side="LONG",
        entry_at=datetime(2026, 1, 5, 10, 5, tzinfo=UTC),
        entry_price=Decimal("100.1"),
        stop_price=Decimal("99.5"),
        stop_buffer_price=Decimal("0.05"),
        m5_closeback_at=datetime(2026, 1, 5, 9, 58, tzinfo=UTC),
        mss=_mss(),
        zone=_zone(),
    )

    assert row.feature_names == v38.FEATURE_NAMES
    assert row.feature_count == len(v38.FEATURE_NAMES) == 12
    assert row.feature_timestamp_le_entry is True
    assert row.future_bar_used is False
    assert row.outcome_used is False
    assert row.mae_mfe_used is False
    assert row.exit_reason_used is False
    assert row.vector[0] == "0.8"
    assert Decimal(row.vector[1]) == Decimal("1")
    assert Decimal(row.vector[7]) == Decimal("5")
    assert Decimal(row.vector[8]) == Decimal("1")
    assert Decimal(row.vector[9]) == Decimal("3")
    assert Decimal(row.vector[10]) == Decimal("7")


def test_post_entry_mss_fails_closed() -> None:
    late = v3.M3MssEvent(
        side=CapitalizerSide.LONG,
        confirmed_at=datetime(2026, 1, 5, 10, 6, tzinfo=UTC),
        displacement_opened_at=datetime(2026, 1, 5, 10, 3, tzinfo=UTC),
        displacement_closed_at=datetime(2026, 1, 5, 10, 6, tzinfo=UTC),
        broken_swing_price=Decimal("99.8"),
        cisd_boundary=Decimal("100"),
        body_ratio=Decimal("0.8"),
        atr14=Decimal("0.5"),
        displacement_range=Decimal("0.6"),
    )

    with pytest.raises(ValueError, match="post-entry"):
        v38.build_geometry(
            symbol="EURUSD",
            side="LONG",
            entry_at=datetime(2026, 1, 5, 10, 5, tzinfo=UTC),
            entry_price=Decimal("100.1"),
            stop_price=Decimal("99.5"),
            stop_buffer_price=Decimal("0.05"),
            m5_closeback_at=datetime(2026, 1, 5, 9, 58, tzinfo=UTC),
            mss=late,
            zone=_zone(),
        )


def test_fvg_after_mss_confirmation_fails_closed() -> None:
    zone = v3.M1EntryZone(
        ob_opened_at=datetime(2026, 1, 5, 9, 59, tzinfo=UTC),
        ob_low=Decimal("99.6"),
        ob_high=Decimal("99.9"),
        fvg_confirmed_at=datetime(2026, 1, 5, 10, 4, tzinfo=UTC),
        fvg_low=Decimal("100.0"),
        fvg_high=Decimal("100.2"),
        overlap_low=None,
        overlap_high=None,
    )

    with pytest.raises(ValueError, match="FVG cannot follow"):
        v38.build_geometry(
            symbol="EURUSD",
            side="LONG",
            entry_at=datetime(2026, 1, 5, 10, 5, tzinfo=UTC),
            entry_price=Decimal("100.1"),
            stop_price=Decimal("99.5"),
            stop_buffer_price=Decimal("0.05"),
            m5_closeback_at=datetime(2026, 1, 5, 9, 58, tzinfo=UTC),
            mss=_mss(),
            zone=zone,
        )


def test_nonpositive_risk_fails_closed() -> None:
    with pytest.raises(ValueError, match="risk"):
        v38.build_geometry(
            symbol="EURUSD",
            side="LONG",
            entry_at=datetime(2026, 1, 5, 10, 5, tzinfo=UTC),
            entry_price=Decimal("100"),
            stop_price=Decimal("100"),
            stop_buffer_price=Decimal("0.05"),
            m5_closeback_at=datetime(2026, 1, 5, 9, 58, tzinfo=UTC),
            mss=_mss(),
            zone=_zone(),
        )
