from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

from qore.infrastructure.trader_lab import (
    vt08_index_r84_source_exact_ps_event_census as r84,
)
from qore.infrastructure.trader_lab import (
    vt08_index_r86_dynamic_m15_fvg_rearm as r86,
)
from qore.infrastructure.trader_lab import (
    vt08_index_r98_ps_density_bottleneck_attribution as r98,
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
    open_: str,
    high: str,
    low: str,
    close: str,
) -> Vt08IndexC2R1Bar:
    return Vt08IndexC2R1Bar(
        opened_at=opened,
        closed_at=opened + timedelta(minutes=15),
        open=Decimal(open_),
        high=Decimal(high),
        low=Decimal(low),
        close=Decimal(close),
    )


def test_r98_dynamic_m15_fvg_must_be_known_before_reaction() -> None:
    t0 = datetime(2026, 1, 1, tzinfo=UTC)
    bars = (
        _bar(t0, open_="100", high="101", low="99", close="100.5"),
        _bar(
            t0 + timedelta(minutes=15),
            open_="100.5",
            high="101",
            low="100",
            close="100.2",
        ),
        _bar(
            t0 + timedelta(minutes=30),
            open_="102",
            high="103",
            low="102",
            close="102.5",
        ),
        _bar(
            t0 + timedelta(minutes=45),
            open_="102.5",
            high="103",
            low="100.5",
            close="101",
        ),
        _bar(
            t0 + timedelta(minutes=60),
            open_="101",
            high="104",
            low="100.8",
            close="103.5",
        ),
    )
    fvgs = r86._directional_fvgs(
        bars,
        side=DemoTradingSetupSide.LONG,
        earliest_formed_index=2,
    )
    assert fvgs
    series = r84.ConfirmedSeries(
        start_index=3,
        end_index=3,
        confirm_index=4,
        series_open=Decimal("102.5"),
        extreme=Decimal("100.5"),
        extreme_index=3,
    )
    assert r98._causal_m15_fvg_reaction(
        bars,
        side=DemoTradingSetupSide.LONG,
        series=series,
        h4_touch_index=0,
    )


def test_r98_dynamic_m15_fvg_does_not_use_same_bar_formation_touch() -> None:
    t0 = datetime(2026, 1, 1, tzinfo=UTC)
    bars = (
        _bar(t0, open_="100", high="101", low="99", close="100.5"),
        _bar(
            t0 + timedelta(minutes=15),
            open_="100.5",
            high="101",
            low="100",
            close="100.2",
        ),
        _bar(
            t0 + timedelta(minutes=30),
            open_="102",
            high="103",
            low="102",
            close="102.5",
        ),
        _bar(
            t0 + timedelta(minutes=45),
            open_="103",
            high="104",
            low="102.2",
            close="102.8",
        ),
    )
    series = r84.ConfirmedSeries(
        start_index=2,
        end_index=2,
        confirm_index=3,
        series_open=Decimal("102"),
        extreme=Decimal("102"),
        extreme_index=2,
    )
    assert not r98._causal_m15_fvg_reaction(
        bars,
        side=DemoTradingSetupSide.LONG,
        series=series,
        h4_touch_index=0,
    )


def test_r98_executable_control_preserves_same_c2_body_rule() -> None:
    t0 = datetime(2026, 1, 1, tzinfo=UTC)
    bars = (
        _bar(t0, open_="100", high="101", low="99", close="100.5"),
        _bar(
            t0 + timedelta(minutes=15),
            open_="100.5",
            high="102",
            low="100",
            close="101.8",
        ),
    )
    series = r84.ConfirmedSeries(
        start_index=0,
        end_index=0,
        confirm_index=0,
        series_open=Decimal("100"),
        extreme=Decimal("99"),
        extreme_index=0,
    )
    h4 = Vt08IndexC2R1Bar(
        opened_at=t0,
        closed_at=t0 + timedelta(hours=4),
        open=Decimal("102"),
        high=Decimal("105"),
        low=Decimal("98"),
        close=Decimal("103"),
    )
    assert r98._executable_from_series(
        bars,
        h4_bar=h4,
        model_kind=v6.H4ModelKind.SAME_C2,
        side=DemoTradingSetupSide.LONG,
        series=series,
    ) is None


def test_r98_r97_evidence_is_pinned() -> None:
    assert r98.SOURCE_R97_RUN_ID == 35535136703
    assert r98.SOURCE_R97_ARTIFACT_ID == 10613125272
    assert r98.SOURCE_R97_ARTIFACT_DIGEST == (
        "sha256:97864b91f41ff6578d5c16ebb98a88559795e2698110cb7297d4afad949eebf7"
    )
