from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

import pytest

from qore.infrastructure.trader_lab import (
    capitalizer_owner_h1_m3_m1_causal_reversal_1y_v3 as v3,
)
from qore.infrastructure.trader_lab import (
    capitalizer_preentry_native_m1_geometry_collector_v38 as collector,
)
from qore.infrastructure.trader_lab import (
    capitalizer_preentry_native_m1_geometry_v38 as geometry,
)
from qore.infrastructure.trader_lab.capitalizer_exposure_graph import (
    CapitalizerSide,
)


def _geometry() -> geometry.PreentryNativeM1Geometry:
    mss = v3.M3MssEvent(
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
    zone = v3.M1EntryZone(
        ob_opened_at=datetime(2026, 1, 5, 9, 59, tzinfo=UTC),
        ob_low=Decimal("99.6"),
        ob_high=Decimal("99.9"),
        fvg_confirmed_at=datetime(2026, 1, 5, 10, 2, tzinfo=UTC),
        fvg_low=Decimal("100.0"),
        fvg_high=Decimal("100.2"),
        overlap_low=None,
        overlap_high=None,
    )
    return geometry.build_geometry(
        symbol="EURUSD",
        side="LONG",
        entry_at=datetime(2026, 1, 5, 10, 5, tzinfo=UTC),
        entry_price=Decimal("100.1"),
        stop_price=Decimal("99.5"),
        stop_buffer_price=Decimal("0.05"),
        m5_closeback_at=datetime(2026, 1, 5, 9, 58, tzinfo=UTC),
        mss=mss,
        zone=zone,
    )


def test_selected_geometry_requires_exact_authoritative_join() -> None:
    row = collector.SelectedGeometry(
        symbol="EURUSD",
        session="LONDON",
        operating_date="2026-01-05",
        side="LONG",
        h1_open="2026-01-05T10:00:00+00:00",
        entry_at="2026-01-05T10:05:00+00:00",
        provenance="CAUSAL_ARBITRATION_BASE",
        geometry=_geometry(),
    )

    assert row.authoritative_identity_joined is True
    assert row.outcome_used_for_geometry is False
    assert row.exit_used_for_geometry is False


def test_selected_geometry_rejects_symbol_drift() -> None:
    with pytest.raises(ValueError, match="symbol mismatch"):
        collector.SelectedGeometry(
            symbol="GBPUSD",
            session="LONDON",
            operating_date="2026-01-05",
            side="LONG",
            h1_open="2026-01-05T10:00:00+00:00",
            entry_at="2026-01-05T10:05:00+00:00",
            provenance="CAUSAL_ARBITRATION_BASE",
            geometry=_geometry(),
        )


def test_record_fails_on_conflicting_duplicate_identity() -> None:
    key = (
        "EURUSD",
        "LONDON",
        "2026-01-05",
        "LONG",
        "2026-01-05T10:00:00+00:00",
        "2026-01-05T10:05:00+00:00",
        "CAUSAL_ARBITRATION_BASE",
    )
    first = _geometry()
    sink: dict[
        collector.IdentityKey,
        geometry.PreentryNativeM1Geometry,
    ] = {}
    collector._record(sink, key=key, value=first)

    changed = geometry.PreentryNativeM1Geometry(
        **{
            field: getattr(first, field)
            for field in first.__dataclass_fields__
            if field != "vector"
        },
        vector=(
            "0.7",
            *first.vector[1:],
        ),
    )
    with pytest.raises(ValueError, match="collision"):
        collector._record(sink, key=key, value=changed)


def test_identity_key_contains_no_outcome_fields() -> None:
    key = collector._identity_from_parts(
        symbol="EURUSD",
        session="LONDON",
        operating_date="2026-01-05",
        side="LONG",
        h1_open=datetime(2026, 1, 5, 10, 0, tzinfo=UTC),
        entry_at=datetime(2026, 1, 5, 10, 5, tzinfo=UTC),
        provenance="CAUSAL_ARBITRATION_BASE",
    )

    assert key == (
        "EURUSD",
        "LONDON",
        "2026-01-05",
        "LONG",
        "2026-01-05T10:00:00+00:00",
        "2026-01-05T10:05:00+00:00",
        "CAUSAL_ARBITRATION_BASE",
    )
