from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

from qore.infrastructure.trader_lab import (
    vt08_index_r84_source_exact_ps_event_census as r84,
)
from qore.infrastructure.trader_lab import (
    vt08_index_r85_source_exact_ps_continuation_rearm as r85,
)
from qore.infrastructure.trader_lab import (
    vt08_index_r96_ideal_formation_cross_h4_carry as r96,
)
from qore.infrastructure.trader_lab import (
    vt08_index_v6_ttrades_source_faithful as v6,
)
from qore.infrastructure.traders.contracts import DemoTradingSetupSide
from qore.infrastructure.traders.vt08_index_c2_positional_r1 import (
    Vt08IndexC2R1Bar,
)


def _bar(
    opened: datetime,
    *,
    hours: int = 4,
    open_: str,
    high: str,
    low: str,
    close: str,
) -> Vt08IndexC2R1Bar:
    return Vt08IndexC2R1Bar(
        opened_at=opened,
        closed_at=opened + timedelta(hours=hours),
        open=Decimal(open_),
        high=Decimal(high),
        low=Decimal(low),
        close=Decimal(close),
    )


def test_r96_detects_bullish_c2_formation() -> None:
    t0 = datetime(2026, 1, 1, tzinfo=UTC)
    first = _bar(
        t0,
        open_="105",
        high="110",
        low="100",
        close="106",
    )
    second = _bar(
        t0 + timedelta(hours=4),
        open_="106",
        high="109",
        low="99",
        close="105",
    )
    h4 = {
        first.opened_at: first,
        second.opened_at: second,
    }
    assert r96._closure_kind(
        h4,
        tuple(sorted(h4)),
        opened=second.opened_at,
        side=DemoTradingSetupSide.LONG,
    ) == "C2"


def test_r96_protected_swing_must_survive_formation_close() -> None:
    t0 = datetime(2026, 1, 1, tzinfo=UTC)
    inside = (
        _bar(
            t0,
            hours=0,
            open_="100",
            high="101",
            low="98",
            close="100.5",
        ),
        _bar(
            t0 + timedelta(minutes=15),
            hours=0,
            open_="100.5",
            high="102",
            low="99",
            close="101",
        ),
    )
    assert r96._survives_after_confirmation(
        inside,
        confirm_index=0,
        side=DemoTradingSetupSide.LONG,
        protected_swing=Decimal("98.5"),
    )
    assert not r96._survives_after_confirmation(
        inside,
        confirm_index=0,
        side=DemoTradingSetupSide.LONG,
        protected_swing=Decimal("99.5"),
    )


def test_r96_carry_uses_existing_ps_in_next_h4_continuation() -> None:
    t0 = datetime(2026, 1, 1, tzinfo=UTC)
    formation_inside = (
        Vt08IndexC2R1Bar(
            opened_at=t0,
            closed_at=t0 + timedelta(minutes=15),
            open=Decimal("100"),
            high=Decimal("102"),
            low=Decimal("98"),
            close=Decimal("101"),
        ),
    )
    execution_inside = (
        Vt08IndexC2R1Bar(
            opened_at=t0 + timedelta(hours=4),
            closed_at=t0 + timedelta(hours=4, minutes=15),
            open=Decimal("101"),
            high=Decimal("102"),
            low=Decimal("100"),
            close=Decimal("101.5"),
        ),
        Vt08IndexC2R1Bar(
            opened_at=t0 + timedelta(hours=4, minutes=15),
            closed_at=t0 + timedelta(hours=4, minutes=30),
            open=Decimal("101.5"),
            high=Decimal("103"),
            low=Decimal("101"),
            close=Decimal("102.5"),
        ),
    )
    event = r84.ProtectedSwingEvent(
        symbol="NAS100",
        h4_opened_at=t0,
        side=DemoTradingSetupSide.LONG,
        confirmed_at=t0 + timedelta(minutes=15),
        protected_swing=Decimal("98"),
        series_open=Decimal("100"),
        family=r84.FAMILY_LIQUIDITY,
        source_poi_kind=v6.PoiKind.RELEVANT_SWING.value,
        poi_touch_at=t0,
    )
    candidate = r85.SourcePsCandidate(
        event=event,
        source_poi=v6.SourcePoi(
            v6.PoiKind.RELEVANT_SWING,
            Decimal("99"),
            Decimal("99"),
            t0,
        ),
        confirm_index=0,
    )
    row = r96._carry_from_candidate(
        symbol="NAS100",
        formation_opened=t0,
        execution_opened=t0 + timedelta(hours=4),
        closure_kind="C2",
        candidate=candidate,
        formation_inside=formation_inside,
        execution_inside=execution_inside,
    )
    assert row is not None
    assert row.protected_swing == Decimal("98")
    assert row.continuation_index == 1
    assert row.entry == Decimal("102.5")


def test_r96_source_r95_evidence_is_pinned() -> None:
    assert r96.SOURCE_R95_RUN_ID == 35531957789
    assert r96.SOURCE_R95_ARTIFACT_ID == 10611990582
    assert r96.SOURCE_R95_ARTIFACT_DIGEST == (
        "sha256:1bfa717e1172768d00fc6e615cd8b37d58695fb7b41ba8fa83390cab2c3533c5"
    )
