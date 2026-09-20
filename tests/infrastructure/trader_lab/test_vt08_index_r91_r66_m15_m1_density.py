from __future__ import annotations

from datetime import UTC, datetime, timedelta

from qore.infrastructure.trader_lab import (
    vt08_index_r91_r66_m15_m1_density as r91,
)
from qore.infrastructure.traders.contracts import DemoTradingSetupSide


def _payload(opened: datetime, price: int) -> r91.NativeM1Payload:
    return r91.NativeM1Payload(
        opened_at=opened,
        low_relative=price,
        delta_open=1,
        delta_high=4,
        delta_close=2,
    )


def test_r91_complete_m15_requires_all_fifteen_native_minutes() -> None:
    t0 = datetime(2018, 1, 2, 0, 0, tzinfo=UTC)
    raw = {
        t0 + timedelta(minutes=index): _payload(
            t0 + timedelta(minutes=index),
            100000 + index,
        )
        for index in range(15)
    }
    m15, components = r91._complete_m15(raw)
    assert tuple(m15) == (t0,)
    assert len(components[t0]) == 15

    incomplete = dict(raw)
    incomplete.pop(t0 + timedelta(minutes=7))
    m15_incomplete, components_incomplete = r91._complete_m15(incomplete)
    assert t0 not in m15_incomplete
    assert t0 not in components_incomplete


def test_r91_m15_source_poi_detects_three_bar_fvg() -> None:
    t0 = datetime(2018, 1, 2, 0, 0, tzinfo=UTC)
    raw: dict[datetime, r91.NativeM1Payload] = {}
    bases = (100000, 100020, 100100)
    for slot, base in enumerate(bases):
        opened = t0 + timedelta(minutes=15 * slot)
        for index in range(15):
            raw[opened + timedelta(minutes=index)] = _payload(
                opened + timedelta(minutes=index),
                base,
            )
    m15, components = r91._complete_m15(raw)
    keys = tuple(sorted(m15))
    pois = r91._m15_source_pois(
        m15=m15,
        m15_keys=keys,
        components=components,
        before=t0 + timedelta(minutes=45),
        side=DemoTradingSetupSide.LONG,
    )
    assert any(poi.kind.value == "fvg" for poi in pois)


def test_r91_native_payload_identity_is_exact() -> None:
    t0 = datetime(2018, 1, 2, tzinfo=UTC)
    row = _payload(t0, 100000)
    assert row.identity() == (100000, 1, 4, 2)


def test_r91_source_r90_evidence_and_scope_are_frozen() -> None:
    assert r91.SOURCE_R90_RUN_ID == 35527759264
    assert r91.SOURCE_R90_ARTIFACT_ID == 10609363779
    assert r91.PERIOD_M1 == 1
    assert r91.CHUNK_DAYS == 2
    assert 14 not in tuple(r91.r4.V7_ANCHORS)
    assert 18 not in tuple(r91.r4.V7_ANCHORS)
