from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from qore.infrastructure.trader_lab import (
    capitalizer_owner_h1_m3_m1_causal_reversal_1y_v3 as v3,
)
from qore.infrastructure.trader_lab.capitalizer_exposure_graph import CapitalizerSide
from qore.infrastructure.trader_lab.capitalizer_source_observation_detectors_v2 import (
    CapitalizerSourceBar,
)
from qore.infrastructure.trader_lab.capitalizer_strict_htf_gate_1y_v1 import (
    Pivot,
    TFBar,
)
from qore.infrastructure.trader_lab.capitalizer_v3_source_first_cisd_v1 import (
    BOUNDARY_SEMANTICS,
    IDENTITY,
    find_source_first_m3_mss,
)


def _bar(
    opened_at: datetime,
    open_: str,
    high: str,
    low: str,
    close: str,
) -> TFBar:
    return TFBar(
        opened_at=opened_at,
        closed_at=opened_at + timedelta(minutes=3),
        source=CapitalizerSourceBar(
            open=Decimal(open_),
            high=Decimal(high),
            low=Decimal(low),
            close=Decimal(close),
        ),
    )


def test_source_first_contract_identity_is_frozen() -> None:
    assert IDENTITY == "QORE_CAPITALIZER_V3_SOURCE_FIRST_CISD_V1"
    assert BOUNDARY_SEMANTICS == "FIRST_OPPOSING_OPEN_AFTER_SWEEP_PERSISTS"


def test_first_opposing_open_persists_until_post_closeback_confirmation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    base = datetime(2026, 1, 2, 12, 0, tzinfo=UTC)
    bars = (
        # First causal opposing candle: frozen boundary must become 100.
        _bar(base, "100", "100.2", "98.8", "99"),
        # Same-direction bar occurs before closeback and cannot confirm.
        _bar(base + timedelta(minutes=3), "99", "101", "98.9", "100.8"),
        # Later opposing candle has open 102; SOURCE_FIRST must NOT replace 100.
        _bar(base + timedelta(minutes=6), "102", "102.2", "100.8", "101"),
        # First eligible post-closeback confirmation candidate.
        _bar(base + timedelta(minutes=9), "101", "103.2", "100.7", "103"),
    )
    closes = tuple(item.closed_at for item in bars)
    pivot = Pivot(
        occurred_at=base,
        confirmed_at=base,
        price=Decimal("100.5"),
        kind="HIGH",
    )

    monkeypatch.setattr(
        v3,
        "_atr14",
        lambda _bars, _index: Decimal("1"),
    )
    monkeypatch.setattr(
        v3,
        "_latest_pivot",
        lambda _pivots, *, before, kind: pivot,
    )

    event = find_source_first_m3_mss(
        bars,
        closes,
        (pivot,),
        sweep_at=base - timedelta(minutes=1),
        after=base + timedelta(minutes=8),
        before=base + timedelta(minutes=15),
        side=CapitalizerSide.LONG,
    )

    assert event is not None
    assert event.confirmed_at == base + timedelta(minutes=12)
    assert event.cisd_boundary == Decimal("100")
    assert event.broken_swing_price == Decimal("100.5")


def test_closeback_exactly_at_deadline_fails_closed() -> None:
    base = datetime(2026, 1, 2, 12, 0, tzinfo=UTC)
    bars = (
        _bar(base, "100", "100.2", "98.8", "99"),
    )
    closes = tuple(item.closed_at for item in bars)

    event = find_source_first_m3_mss(
        bars,
        closes,
        (),
        sweep_at=base - timedelta(minutes=1),
        after=base + timedelta(minutes=3),
        before=base + timedelta(minutes=3),
        side=CapitalizerSide.LONG,
    )

    assert event is None
