from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

from qore.infrastructure.trader_lab import vt08_index_cibo_2y_density_round4 as mod
from qore.infrastructure.trader_lab import vt08_index_v6_ttrades_source_faithful as v6
from qore.infrastructure.traders.contracts import DemoTradingSetupSide
from qore.infrastructure.traders.vt08_index_c2_positional_r1 import Vt08IndexC2R1Bar


def _bar(at: datetime, o: str, h: str, low: str, c: str) -> Vt08IndexC2R1Bar:
    return Vt08IndexC2R1Bar(
        opened_at=at,
        closed_at=at + timedelta(minutes=15),
        open=Decimal(o),
        high=Decimal(h),
        low=Decimal(low),
        close=Decimal(c),
    )


def test_density_gate_is_600() -> None:
    assert mod.DENSITY_HARD_GATE == 600


def test_plus_14_research_anchor_does_not_mutate_v7() -> None:
    assert 14 in mod.PLUS_14_ANCHORS
    assert 14 not in mod.V7_ANCHORS
    assert mod.V7_ANCHORS == (22, 2, 6, 10)


def test_multi_poi_can_retain_multiple_valid_families() -> None:
    base = datetime(2017, 1, 1, 0, 0, tzinfo=UTC)
    h4 = {
        base: _bar(base, "100", "105", "99", "104"),
        base + timedelta(hours=4): _bar(
            base + timedelta(hours=4), "104", "106", "98", "105"
        ),
        base + timedelta(hours=8): _bar(
            base + timedelta(hours=8), "110", "112", "109", "111"
        ),
    }
    indexed: dict[datetime, Vt08IndexC2R1Bar] = {}
    for opened, bar in h4.items():
        indexed[opened] = bar

    pois = mod._source_pois_for_h4(
        indexed,
        h4,
        h4_opened_at=base + timedelta(hours=12),
        side=DemoTradingSetupSide.LONG,
    )
    kinds = {poi.kind.value for poi in pois}
    assert v6.PoiKind.FVG.value in kinds
    assert v6.PoiKind.RELEVANT_SWING.value in kinds


def test_touch_indices_require_observed_poi_and_actual_touch() -> None:
    base = datetime(2017, 1, 1, 0, 0, tzinfo=UTC)
    bars = (
        _bar(base, "100", "101", "99", "100"),
        _bar(base + timedelta(minutes=15), "100", "102", "99", "101"),
    )
    poi = v6.SourcePoi(
        v6.PoiKind.CISD,
        Decimal("101.5"),
        Decimal("101.5"),
        base + timedelta(minutes=10),
    )
    assert mod._touch_indices(bars, poi, start_index=0) == (1,)


def test_overlap_diagnostics_counts_one_active_position_per_symbol() -> None:
    base = datetime(2017, 1, 1, 0, 0, tzinfo=UTC)

    def signal(at: datetime) -> v6.CandidateSignal:
        poi = v6.SourcePoi(v6.PoiKind.CISD, Decimal("100"), Decimal("100"), at)
        return v6.CandidateSignal(
            symbol="NAS100",
            side=DemoTradingSetupSide.LONG,
            model_kind=v6.H4ModelKind.SAME_C2,
            h4_opened_at=at,
            signal_at=at,
            entry=Decimal("100"),
            stop=Decimal("99"),
            target=Decimal("102"),
            poi=poi,
            cisd_level=Decimal("100"),
            cisd_confirmed_at=at,
            protected_swing_extreme=Decimal("99"),
        )

    trades = (
        v6.ModeledV6Trade(
            signal(base),
            base + timedelta(hours=2),
            Decimal("102"),
            "target",
            Decimal("2"),
        ),
        v6.ModeledV6Trade(
            signal(base + timedelta(hours=1)),
            base + timedelta(hours=3),
            Decimal("102"),
            "target",
            Decimal("2"),
        ),
        v6.ModeledV6Trade(
            signal(base + timedelta(hours=3)),
            base + timedelta(hours=4),
            Decimal("102"),
            "target",
            Decimal("2"),
        ),
    )
    result = mod._overlap_diagnostics(trades)
    assert result["independent_trade_count"] == 3
    assert result["same_symbol_overlap_count"] == 1
    assert result["one_active_position_per_symbol_count"] == 2


def test_variant_settings_are_explicit() -> None:
    anchors, multi, rearm = mod._variant_settings(
        mod.ExpansionVariant.MULTI_POI_REARM_PLUS_14
    )
    assert anchors == (14, 22, 2, 6, 10)
    assert multi is True
    assert rearm is True
