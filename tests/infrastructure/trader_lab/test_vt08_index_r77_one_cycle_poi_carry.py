from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

from qore.infrastructure.trader_lab import (
    vt08_index_r76_strict_untouched_poi_memory as r76,
)
from qore.infrastructure.trader_lab import (
    vt08_index_r77_one_cycle_poi_carry as r77,
)
from qore.infrastructure.trader_lab import (
    vt08_index_v6_ttrades_source_faithful as v6,
)
from qore.infrastructure.traders.contracts import DemoTradingSetupSide


def _record(
    *,
    kind: v6.PoiKind,
    formed: datetime,
    observed: datetime,
    retouched: datetime | None = None,
) -> r76.PoiRecord:
    return r76.PoiRecord(
        side=DemoTradingSetupSide.LONG,
        poi=v6.SourcePoi(
            kind,
            Decimal("100"),
            Decimal("101"),
            observed,
        ),
        formed_h4_open=formed,
        first_retouched_at=retouched,
    )


def test_r77_selects_only_exact_age_two() -> None:
    t0 = datetime(2026, 1, 1, tzinfo=UTC)
    h4_index = {
        t0: 0,
        t0 + timedelta(hours=4): 1,
        t0 + timedelta(hours=8): 2,
    }
    opened = t0 + timedelta(hours=8)
    age_two = _record(
        kind=v6.PoiKind.RELEVANT_SWING,
        formed=t0,
        observed=t0 + timedelta(hours=4),
    )
    age_one = _record(
        kind=v6.PoiKind.FVG,
        formed=t0 + timedelta(hours=4),
        observed=t0 + timedelta(hours=8),
    )
    selected = r77._select_one_cycle_poi(
        (age_two, age_one),
        side=DemoTradingSetupSide.LONG,
        opened=opened,
        current_h4_index=2,
        h4_index=h4_index,
    )
    assert selected is age_two


def test_r77_rejects_retouch_before_anchor() -> None:
    t0 = datetime(2026, 1, 1, tzinfo=UTC)
    opened = t0 + timedelta(hours=8)
    row = _record(
        kind=v6.PoiKind.FVG,
        formed=t0,
        observed=t0 + timedelta(hours=4),
        retouched=t0 + timedelta(hours=6),
    )
    selected = r77._select_one_cycle_poi(
        (row,),
        side=DemoTradingSetupSide.LONG,
        opened=opened,
        current_h4_index=2,
        h4_index={t0: 0, opened: 2},
    )
    assert selected is None


def test_r77_hierarchy_prefers_fvg() -> None:
    t0 = datetime(2026, 1, 1, tzinfo=UTC)
    opened = t0 + timedelta(hours=8)
    swing = _record(
        kind=v6.PoiKind.RELEVANT_SWING,
        formed=t0,
        observed=t0 + timedelta(hours=4),
    )
    fvg = _record(
        kind=v6.PoiKind.FVG,
        formed=t0,
        observed=t0 + timedelta(hours=4),
    )
    selected = r77._select_one_cycle_poi(
        (swing, fvg),
        side=DemoTradingSetupSide.LONG,
        opened=opened,
        current_h4_index=2,
        h4_index={t0: 0, opened: 2},
    )
    assert selected is fvg


def test_r77_source_r76_evidence_is_pinned() -> None:
    assert r77.SOURCE_R76_RUN_ID == 35513608607
    assert r77.SOURCE_R76_ARTIFACT_ID == 10605463569
    assert r77.SOURCE_R76_ARTIFACT_DIGEST.startswith("sha256:")
