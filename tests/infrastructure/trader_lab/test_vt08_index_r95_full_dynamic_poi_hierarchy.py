from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

from qore.infrastructure.trader_lab import (
    vt08_index_r94_ttrades_timeframe_hierarchy_freeze as r94,
)
from qore.infrastructure.trader_lab import (
    vt08_index_r95_full_dynamic_poi_hierarchy as r95,
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


def test_r95_priority_uses_fvg_before_swing_and_cisd() -> None:
    t0 = datetime(2026, 1, 1, tzinfo=UTC)
    bar = _bar(
        t0 + timedelta(minutes=45),
        open_="103",
        high="104",
        low="101",
        close="103.5",
    )
    candidates = (
        r95.DynamicPoi(
            v6.SourcePoi(
                v6.PoiKind.CISD,
                Decimal("102"),
                Decimal("102"),
                t0,
            ),
            0,
        ),
        r95.DynamicPoi(
            v6.SourcePoi(
                v6.PoiKind.RELEVANT_SWING,
                Decimal("101.5"),
                Decimal("101.5"),
                t0,
            ),
            0,
        ),
        r95.DynamicPoi(
            v6.SourcePoi(
                v6.PoiKind.FVG,
                Decimal("101"),
                Decimal("102.5"),
                t0,
            ),
            0,
        ),
    )
    chosen = r95._priority_poi_at_touch(
        candidates,
        bar=bar,
        touch_index=3,
        side=DemoTradingSetupSide.LONG,
        protected_swing=Decimal("100"),
    )
    assert chosen is not None
    assert chosen.poi.kind is v6.PoiKind.FVG


def test_r95_same_family_chooses_first_level_from_protected_swing() -> None:
    t0 = datetime(2026, 1, 1, tzinfo=UTC)
    bar = _bar(
        t0 + timedelta(minutes=45),
        open_="104",
        high="105",
        low="101",
        close="104.5",
    )
    near = r95.DynamicPoi(
        v6.SourcePoi(
            v6.PoiKind.RELEVANT_SWING,
            Decimal("101"),
            Decimal("101"),
            t0,
        ),
        0,
    )
    far = r95.DynamicPoi(
        v6.SourcePoi(
            v6.PoiKind.RELEVANT_SWING,
            Decimal("103"),
            Decimal("103"),
            t0,
        ),
        0,
    )
    chosen = r95._priority_poi_at_touch(
        (far, near),
        bar=bar,
        touch_index=3,
        side=DemoTradingSetupSide.LONG,
        protected_swing=Decimal("100"),
    )
    assert chosen == near


def test_r95_poi_must_be_observed_before_touch() -> None:
    t0 = datetime(2026, 1, 1, tzinfo=UTC)
    bar = _bar(
        t0 + timedelta(minutes=15),
        open_="101",
        high="102",
        low="100.5",
        close="101.5",
    )
    same_bar_observation = r95.DynamicPoi(
        v6.SourcePoi(
            v6.PoiKind.CISD,
            Decimal("101"),
            Decimal("101"),
            bar.closed_at,
        ),
        1,
    )
    assert r95._priority_poi_at_touch(
        (same_bar_observation,),
        bar=bar,
        touch_index=1,
        side=DemoTradingSetupSide.LONG,
        protected_swing=Decimal("99"),
    ) is None


def test_r95_seed_advances_with_new_protected_swing() -> None:
    row = r95.HierarchyRearm(
        poi=v6.SourcePoi(
            v6.PoiKind.CISD,
            Decimal("100"),
            Decimal("100"),
            datetime(2026, 1, 1, tzinfo=UTC),
        ),
        poi_observed_index=2,
        touch_index=3,
        family="LIQUIDITY_SWEEP",
        protected_swing=Decimal("98"),
        series_open=Decimal("100"),
        confirm_index=5,
        continuation_index=6,
        continuation_at=datetime(2026, 1, 1, 1, 45, tzinfo=UTC),
        entry=Decimal("103"),
    )
    assert row.as_seed() == r95.JourneySeed(
        ps_confirm_index=5,
        continuation_index=6,
        protected_swing=Decimal("98"),
    )


def test_r95_timeframe_freeze_is_primary_model_only() -> None:
    hierarchy = r94.payload()["frozen_hierarchy"]
    assert hierarchy["vt08_primary_model"]["bias_timeframe"] == "D1"
    assert hierarchy["vt08_primary_model"]["structure_timeframe"] == "H4"
    assert hierarchy["vt08_primary_model"]["entry_timeframe"] == "M15"
    assert (
        hierarchy["alternate_pairings"]["H1_M5"][
            "independent_additive_layer_to_H4_M15"
        ]
        is False
    )
