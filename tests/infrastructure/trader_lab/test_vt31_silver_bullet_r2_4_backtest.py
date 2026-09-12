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
from qore.infrastructure.trader_lab.vt31_silver_bullet_r2_4_backtest import (
    Vt31R24BacktestReport,
    Vt31R24MarketDayLedger,
    _model_trade,
)
from qore.infrastructure.traders.contracts import DemoTradingSetupSide
from qore.infrastructure.traders.vt31_silver_bullet_r2_2 import (
    Vt31R22ReferenceRange,
    Vt31R22SourceSetup,
    Vt31R22StructureEvidence,
)
from qore.infrastructure.traders.vt31_silver_bullet_r2_4 import (
    Vt31R24ExactSetup,
    Vt31R24FvgConfluence,
    source_bundle_fingerprint,
)

_SOURCE = ExternalSourceDescriptor(
    adapter_id=AdapterId(UUID("74300000-0000-0000-0000-000000000001")),
    source_id=SourceId(UUID("74300000-0000-0000-0000-000000000002")),
    port_name=PortName("market-data.vt31-r2-4-backtest-test"),
)


def _bar(
    suffix: int,
    opened_at: datetime,
    *,
    high: float,
    low: float,
    close: float,
) -> OhlcSnapshot:
    return OhlcSnapshot(
        snapshot_id=MarketDataSnapshotId(
            UUID(f"74300000-0000-0000-0000-{suffix:012d}")
        ),
        instrument=Instrument("NAS100"),
        source=_SOURCE,
        timeframe=Timeframe(60),
        opened_at=opened_at,
        closed_at=opened_at + timedelta(minutes=1),
        open=close,
        high=high,
        low=low,
        close=close,
    )


def _setup(at: datetime) -> Vt31R24ExactSetup:
    reference = Vt31R22ReferenceRange(
        high=Decimal("110"),
        low=Decimal("100"),
        opened_at=at - timedelta(hours=1),
        closed_at=at,
    )
    structure = Vt31R22StructureEvidence(
        raid_at=at,
        confirmation_at=at + timedelta(minutes=1),
        side=DemoTradingSetupSide.SHORT,
        swing_extreme=Decimal("111"),
        structural_level=Decimal("109.8"),
        extreme_candle_open=Decimal("109.8"),
        extreme_candle_high=Decimal("111"),
        extreme_candle_low=Decimal("109.8"),
        extreme_candle_close=Decimal("110.8"),
    )
    source_setup = Vt31R22SourceSetup(
        side=DemoTradingSetupSide.SHORT,
        reference=reference,
        structure=structure,
        candidates=(),
        target_price=Decimal("100"),
        pending_expires_at=at + timedelta(hours=1),
        source_fingerprint="a" * 64,
        evidence_fingerprint="b" * 64,
    )
    confluence = Vt31R24FvgConfluence(
        first_opened_at=at,
        third_closed_at=at + timedelta(minutes=3),
        lower=Decimal("109.6"),
        upper=Decimal("109.8"),
        consequent_encroachment=Decimal("109.7"),
        midnight_open=Decimal("109.7"),
    )
    return Vt31R24ExactSetup(
        bundle_id="SB_AM_FVG_MIDNIGHT_CE_SHORT_R2_4_V1",
        side=DemoTradingSetupSide.SHORT,
        entry_price=Decimal("109.7"),
        stop_price=Decimal("111"),
        target_price=Decimal("100"),
        three_r_price=Decimal("105.8"),
        decision_at=at + timedelta(minutes=3),
        pending_expires_at=at + timedelta(hours=1),
        confluence=confluence,
        source_setup=source_setup,
        source_bundle_fingerprint=source_bundle_fingerprint(),
    )


def test_r2_4_replay_censors_fill_bar_path_ambiguity_instead_of_guessing() -> None:
    at = datetime(2026, 6, 16, 14, 0, tzinfo=UTC)
    setup = _setup(at)
    fill = _bar(1, at + timedelta(minutes=4), high=111.2, low=109.5, close=109.7)

    trade = _model_trade((fill,), fill_index=0, setup=setup)

    assert trade.outcome == "fill-bar-path-ambiguous"
    assert trade.r_multiple is None


def test_r2_4_replay_arms_breakeven_on_3r_touch_then_exits_at_entry() -> None:
    at = datetime(2026, 6, 16, 14, 0, tzinfo=UTC)
    setup = _setup(at)
    fill = _bar(1, at + timedelta(minutes=4), high=110.0, low=109.6, close=109.7)
    three_r = _bar(2, at + timedelta(minutes=5), high=109.8, low=105.7, close=106.0)
    be = _bar(3, at + timedelta(minutes=6), high=109.8, low=108.0, close=109.0)

    trade = _model_trade((fill, three_r, be), fill_index=0, setup=setup)

    assert trade.outcome == "breakeven"
    assert trade.r_multiple == Decimal(0)
    assert trade.breakeven_armed_at == three_r.closed_at


def test_r2_4_report_keeps_daily_cardinality_and_live_authority_closed() -> None:
    checked_at = datetime(2026, 6, 16, 20, 0, tzinfo=UTC)
    ledger = Vt31R24MarketDayLedger(
        local_date=checked_at.date(),
        eligible_day=True,
        reference_complete=True,
        session_complete=True,
        midnight_open_available=True,
        raid_high=True,
        raid_low=False,
        both_sides_swept=False,
        candidate_count=0,
        selected_setup=False,
        pending_order=False,
        filled=False,
        filled_at=None,
        three_r_reached=False,
        breakeven_armed=False,
        terminal_outcome=None,
        resolved_at=None,
        abstain_reason="no-exact-fvg-midnight-confluence",
        containment_reason=None,
        source_bundle_fingerprint=source_bundle_fingerprint(),
        evidence_fingerprint="c" * 64,
        software_sha="d" * 40,
    )
    report = Vt31R24BacktestReport(
        account_fingerprint="e" * 64,
        evidence_fingerprint="c" * 64,
        checked_at=checked_at,
        software_sha="d" * 40,
        ledgers=(ledger,),
        trades=(),
    ).payload()

    assert report["source_exact_historical_replay"] is True
    assert report["broker_source_complete"] is False
    assert report["daily_cardinality_violations"] == 0
    assert report["filled_count"] == 0
