from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID

from qore.infrastructure.market_data import (
    Instrument,
    MarketDataSnapshotId,
    OhlcSnapshot,
    Timeframe,
)
from qore.infrastructure.ports import (
    AdapterId,
    ExternalSourceDescriptor,
    PortName,
    SourceId,
)
from qore.infrastructure.traders.contracts import DemoTradingSetupSide
from qore.infrastructure.traders.vt31_nas100_cibo_causal_structure import (
    pd_array_events,
    reference_sweep_events,
)
from qore.infrastructure.traders.vt31_silver_bullet_r2_2 import (
    Vt31R22EntryEvidence,
    Vt31R22EntryFamily,
    Vt31R22EvidenceClass,
    Vt31R22ReferenceRange,
    Vt31R22SourceSetup,
    Vt31R22StructureEvidence,
)

_SOURCE = ExternalSourceDescriptor(
    adapter_id=AdapterId(UUID("77300000-0000-0000-0000-000000000001")),
    source_id=SourceId(UUID("77300000-0000-0000-0000-000000000002")),
    port_name=PortName("market-data.vt31-causal-structure-test"),
)


def _bar(
    *,
    suffix: int,
    opened_at: datetime,
    open_price: float,
    high: float,
    low: float,
    close: float,
) -> OhlcSnapshot:
    return OhlcSnapshot(
        snapshot_id=MarketDataSnapshotId(
            UUID(f"77300000-0000-0000-0000-{suffix:012d}")
        ),
        instrument=Instrument("NAS100"),
        source=_SOURCE,
        timeframe=Timeframe(60),
        opened_at=opened_at,
        closed_at=opened_at + timedelta(minutes=1),
        open=open_price,
        high=high,
        low=low,
        close=close,
    )


def _source(
    *,
    raid_at: datetime,
    candidate: Vt31R22EntryEvidence | None = None,
) -> Vt31R22SourceSetup:
    reference = Vt31R22ReferenceRange(
        high=Decimal("110"),
        low=Decimal("100"),
        opened_at=raid_at - timedelta(hours=1),
        closed_at=raid_at,
    )
    structure = Vt31R22StructureEvidence(
        raid_at=raid_at,
        confirmation_at=raid_at + timedelta(minutes=1),
        side=DemoTradingSetupSide.SHORT,
        swing_extreme=Decimal("111"),
        structural_level=Decimal("109"),
        extreme_candle_open=Decimal("109.5"),
        extreme_candle_high=Decimal("111"),
        extreme_candle_low=Decimal("109"),
        extreme_candle_close=Decimal("110.5"),
    )
    if candidate is None:
        candidate = Vt31R22EntryEvidence(
            family=Vt31R22EntryFamily.BREAKER,
            formed_at=raid_at + timedelta(minutes=1),
            source_candle_open=Decimal("109.5"),
            source_candle_high=Decimal("111"),
            source_candle_low=Decimal("109"),
            source_candle_close=Decimal("110.5"),
            zone_lower=Decimal("109.5"),
            zone_upper=Decimal("110.5"),
            zone_class=Vt31R22EvidenceClass.SOURCE_FORMALIZATION,
            source_timestamps=(raid_at.isoformat(),),
        )
    return Vt31R22SourceSetup(
        side=DemoTradingSetupSide.SHORT,
        reference=reference,
        structure=structure,
        candidates=(candidate,),
        target_price=Decimal("100"),
        pending_expires_at=raid_at + timedelta(hours=1),
        source_fingerprint="a" * 64,
        evidence_fingerprint="b" * 64,
    )


def test_reference_reclaim_is_not_known_at_bar_open() -> None:
    opened = datetime(2026, 1, 2, 15, 10, tzinfo=UTC)
    bar = _bar(
        suffix=1,
        opened_at=opened,
        open_price=109.5,
        high=111.0,
        low=108.0,
        close=109.0,
    )
    source = _source(raid_at=opened)

    assert reference_sweep_events((bar,), source, opened) == ()

    observed = reference_sweep_events((bar,), source, bar.closed_at)
    assert len(observed) == 1
    assert observed[0].observed_at == bar.closed_at
    assert observed[0].family == "reference-liquidity-sweep"


def test_pd_array_overlap_never_backdates_before_formation() -> None:
    opened = datetime(2026, 1, 2, 15, 10, tzinfo=UTC)
    bar = _bar(
        suffix=2,
        opened_at=opened,
        open_price=109.0,
        high=110.0,
        low=108.0,
        close=109.5,
    )
    formed_at = bar.closed_at
    candidate = Vt31R22EntryEvidence(
        family=Vt31R22EntryFamily.FAIR_VALUE_GAP,
        formed_at=formed_at,
        source_candle_open=Decimal("109"),
        source_candle_high=Decimal("110"),
        source_candle_low=Decimal("108"),
        source_candle_close=Decimal("109.5"),
        zone_lower=Decimal("108.5"),
        zone_upper=Decimal("109.5"),
        zone_class=Vt31R22EvidenceClass.SOURCE_FORMALIZATION,
        source_timestamps=(opened.isoformat(),),
    )
    source = _source(raid_at=opened - timedelta(minutes=2), candidate=candidate)

    observed = pd_array_events((bar,), source, formed_at)
    assert len(observed) == 1
    assert observed[0].observed_at == formed_at
    assert observed[0].observed_at > bar.opened_at
