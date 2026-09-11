from __future__ import annotations

from dataclasses import fields
from datetime import UTC, datetime, timedelta
from uuid import UUID
from zoneinfo import ZoneInfo

import pytest

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
from qore.infrastructure.traders.contracts import DemoTradingDecision, DemoTradingSetupSide
from qore.infrastructure.traders.vt31_silver_bullet_v2 import (
    Vt31SilverBulletV2AbstainReason,
    Vt31SilverBulletV2Config,
    Vt31SilverBulletV2EntryModel,
    Vt31SilverBulletV2Evaluation,
    Vt31SilverBulletV2Input,
    Vt31SilverBulletV2ValidationError,
    evaluate_vt31_silver_bullet_v2,
)

_NY = ZoneInfo("America/New_York")
_SOURCE = ExternalSourceDescriptor(
    adapter_id=AdapterId(UUID("73100000-0000-0000-0000-000000000001")),
    source_id=SourceId(UUID("73100000-0000-0000-0000-000000000002")),
    port_name=PortName("market-data.vt31-v2-fidelity-test"),
)


def _snapshot(
    *,
    suffix: int,
    instrument: str,
    opened_at: datetime,
    open_price: float,
    high: float,
    low: float,
    close: float,
    seconds: int = 60,
) -> OhlcSnapshot:
    return OhlcSnapshot(
        snapshot_id=MarketDataSnapshotId(
            UUID(f"73100000-0000-0000-0000-{suffix:012d}")
        ),
        instrument=Instrument(instrument),
        source=_SOURCE,
        timeframe=Timeframe(seconds),
        opened_at=opened_at.astimezone(UTC),
        closed_at=(opened_at + timedelta(seconds=seconds)).astimezone(UTC),
        open=open_price,
        high=high,
        low=low,
        close=close,
    )


def _reference_hour(
    *,
    day: datetime,
    instrument: str = "NAS100",
) -> tuple[OhlcSnapshot, ...]:
    start = day.replace(hour=9, minute=0, second=0, microsecond=0)
    bars: list[OhlcSnapshot] = []
    for minute in range(60):
        bars.append(
            _snapshot(
                suffix=minute + 1,
                instrument=instrument,
                opened_at=start + timedelta(minutes=minute),
                open_price=105.0,
                high=110.0 if minute == 10 else 109.0,
                low=100.0 if minute == 20 else 101.0,
                close=105.0,
            )
        )
    return tuple(bars)


def _short_fvg_only(day: datetime) -> tuple[OhlcSnapshot, ...]:
    start = day.replace(hour=10, minute=0, second=0, microsecond=0)
    return (
        _snapshot(
            suffix=101,
            instrument="NAS100",
            opened_at=start,
            open_price=109.5,
            high=111.0,
            low=108.8,
            close=109.0,
        ),
        _snapshot(
            suffix=102,
            instrument="NAS100",
            opened_at=start + timedelta(minutes=1),
            open_price=109.0,
            high=109.2,
            low=108.0,
            close=108.5,
        ),
        _snapshot(
            suffix=103,
            instrument="NAS100",
            opened_at=start + timedelta(minutes=2),
            open_price=108.5,
            high=108.7,
            low=107.8,
            close=108.0,
        ),
    )


def _long_fvg_only(day: datetime) -> tuple[OhlcSnapshot, ...]:
    start = day.replace(hour=10, minute=0, second=0, microsecond=0)
    return (
        _snapshot(
            suffix=201,
            instrument="NAS100",
            opened_at=start,
            open_price=100.5,
            high=101.2,
            low=99.0,
            close=101.0,
        ),
        _snapshot(
            suffix=202,
            instrument="NAS100",
            opened_at=start + timedelta(minutes=1),
            open_price=101.0,
            high=102.0,
            low=100.8,
            close=101.5,
        ),
        _snapshot(
            suffix=203,
            instrument="NAS100",
            opened_at=start + timedelta(minutes=2),
            open_price=101.5,
            high=102.5,
            low=101.3,
            close=102.0,
        ),
    )


def _short_breaker_confluence(day: datetime) -> tuple[OhlcSnapshot, ...]:
    start = day.replace(hour=10, minute=0, second=0, microsecond=0)
    return (
        _snapshot(
            suffix=301,
            instrument="NAS100",
            opened_at=start,
            open_price=108.0,
            high=112.0,
            low=107.0,
            close=111.0,
        ),
        _snapshot(
            suffix=302,
            instrument="NAS100",
            opened_at=start + timedelta(minutes=1),
            open_price=111.0,
            high=111.5,
            low=106.0,
            close=106.5,
        ),
    )


def _short_order_block_only(day: datetime) -> tuple[OhlcSnapshot, ...]:
    start = day.replace(hour=10, minute=0, second=0, microsecond=0)
    return (
        _snapshot(
            suffix=401,
            instrument="NAS100",
            opened_at=start,
            open_price=111.0,
            high=112.0,
            low=107.0,
            close=108.0,
        ),
        _snapshot(
            suffix=402,
            instrument="NAS100",
            opened_at=start + timedelta(minutes=1),
            open_price=108.0,
            high=109.0,
            low=107.5,
            close=108.8,
        ),
        _snapshot(
            suffix=403,
            instrument="NAS100",
            opened_at=start + timedelta(minutes=2),
            open_price=108.8,
            high=108.9,
            low=106.0,
            close=106.5,
        ),
    )


def _ambiguous_breaker_and_fvg(day: datetime) -> tuple[OhlcSnapshot, ...]:
    start = day.replace(hour=10, minute=0, second=0, microsecond=0)
    return (
        _snapshot(
            suffix=501,
            instrument="NAS100",
            opened_at=start,
            open_price=108.0,
            high=112.0,
            low=107.0,
            close=111.0,
        ),
        _snapshot(
            suffix=502,
            instrument="NAS100",
            opened_at=start + timedelta(minutes=1),
            open_price=111.0,
            high=111.2,
            low=108.0,
            close=109.0,
        ),
        _snapshot(
            suffix=503,
            instrument="NAS100",
            opened_at=start + timedelta(minutes=2),
            open_price=106.4,
            high=106.5,
            low=105.5,
            close=106.0,
        ),
    )


def _evaluate(
    day: datetime,
    session: tuple[OhlcSnapshot, ...],
    *,
    config: Vt31SilverBulletV2Config | None = None,
) -> Vt31SilverBulletV2Evaluation:
    evidence = (*_reference_hour(day=day), *session)
    return evaluate_vt31_silver_bullet_v2(
        Vt31SilverBulletV2Input(
            instrument=Instrument("NAS100"),
            as_of=session[-1].closed_at,
            m1_candles=evidence,
        ),
        config,
    )


def test_source_short_after_strict_high_raid_targets_opposite_h1_side() -> None:
    day = datetime(2026, 7, 8, tzinfo=_NY)
    result = _evaluate(day, _short_fvg_only(day))

    assert result.decision is DemoTradingDecision.SETUP
    assert result.reason_code == "setup"
    assert result.setup is not None
    assert result.setup.side is DemoTradingSetupSide.SHORT
    assert result.setup.entry_model is Vt31SilverBulletV2EntryModel.FAIR_VALUE_GAP
    assert result.setup.reference_range.high == 110
    assert result.setup.reference_range.low == 100
    assert result.setup.take_profit_price == 100
    assert result.setup.invalidation_price == 111
    assert result.setup.methodological_stop_extreme == 111
    assert result.setup.technical_stop_buffer == 0
    assert result.setup.source_video == "youtube:o0v4KQxZbpU"
    assert result.setup.raid_at < result.setup.confirmation_at <= result.setup.decision_at


def test_source_long_after_strict_low_raid_targets_opposite_h1_side() -> None:
    day = datetime(2026, 7, 9, tzinfo=_NY)
    result = _evaluate(day, _long_fvg_only(day))

    assert result.decision is DemoTradingDecision.SETUP
    assert result.setup is not None
    assert result.setup.side is DemoTradingSetupSide.LONG
    assert result.setup.entry_model is Vt31SilverBulletV2EntryModel.FAIR_VALUE_GAP
    assert result.setup.invalidation_price == 99
    assert result.setup.take_profit_price == 110


def test_equal_high_touch_is_not_a_source_valid_raid() -> None:
    day = datetime(2026, 7, 10, tzinfo=_NY)
    start = day.replace(hour=10, minute=0)
    session = (
        _snapshot(
            suffix=601,
            instrument="NAS100",
            opened_at=start,
            open_price=108.0,
            high=110.0,
            low=106.0,
            close=109.0,
        ),
    )
    result = _evaluate(day, session)

    assert result.decision is DemoTradingDecision.ABSTAIN
    assert result.abstain_reason is Vt31SilverBulletV2AbstainReason.NO_RAID


def test_range_raid_without_post_raid_displacement_structure_abstains() -> None:
    day = datetime(2026, 7, 13, tzinfo=_NY)
    start = day.replace(hour=10, minute=0)
    session = (
        _snapshot(
            suffix=701,
            instrument="NAS100",
            opened_at=start,
            open_price=108.0,
            high=112.0,
            low=107.0,
            close=111.0,
        ),
        _snapshot(
            suffix=702,
            instrument="NAS100",
            opened_at=start + timedelta(minutes=1),
            open_price=111.0,
            high=113.0,
            low=108.0,
            close=112.0,
        ),
    )
    result = _evaluate(day, session)

    assert result.decision is DemoTradingDecision.ABSTAIN
    assert (
        result.abstain_reason
        is Vt31SilverBulletV2AbstainReason.NO_POST_RAID_STRUCTURE_SHIFT
    )


def test_displacement_without_10_to_11_range_raid_abstains() -> None:
    day = datetime(2026, 7, 14, tzinfo=_NY)
    start = day.replace(hour=10, minute=0)
    session = (
        _snapshot(
            suffix=801,
            instrument="NAS100",
            opened_at=start,
            open_price=108.0,
            high=109.0,
            low=105.0,
            close=106.0,
        ),
        _snapshot(
            suffix=802,
            instrument="NAS100",
            opened_at=start + timedelta(minutes=1),
            open_price=106.0,
            high=106.5,
            low=103.0,
            close=104.0,
        ),
    )
    result = _evaluate(day, session)

    assert result.decision is DemoTradingDecision.ABSTAIN
    assert result.abstain_reason is Vt31SilverBulletV2AbstainReason.NO_RAID


def test_pre_10_sweep_does_not_enable_entry_automatically() -> None:
    day = datetime(2026, 7, 15, tzinfo=_NY)
    reference = list(_reference_hour(day=day))
    swept = reference[55]
    reference[55] = _snapshot(
        suffix=900,
        instrument="NAS100",
        opened_at=swept.opened_at.astimezone(_NY),
        open_price=105.0,
        high=115.0,
        low=101.0,
        close=105.0,
    )
    start = day.replace(hour=10, minute=0)
    session = (
        _snapshot(
            suffix=901,
            instrument="NAS100",
            opened_at=start,
            open_price=105.0,
            high=109.0,
            low=101.0,
            close=106.0,
        ),
    )
    result = evaluate_vt31_silver_bullet_v2(
        Vt31SilverBulletV2Input(
            instrument=Instrument("NAS100"),
            as_of=session[-1].closed_at,
            m1_candles=(*reference, *session),
        )
    )

    assert result.decision is DemoTradingDecision.ABSTAIN
    assert result.abstain_reason is Vt31SilverBulletV2AbstainReason.NO_RAID


def test_at_exact_10_no_post_open_causal_evidence_means_no_setup() -> None:
    day = datetime(2026, 7, 16, tzinfo=_NY)
    result = evaluate_vt31_silver_bullet_v2(
        Vt31SilverBulletV2Input(
            instrument=Instrument("NAS100"),
            as_of=day.replace(hour=10, minute=0),
            m1_candles=_reference_hour(day=day),
        )
    )

    assert result.decision is DemoTradingDecision.ABSTAIN
    assert result.abstain_reason is Vt31SilverBulletV2AbstainReason.NO_RAID


def test_signal_at_11_new_york_is_invalid() -> None:
    day = datetime(2026, 7, 17, tzinfo=_NY)
    session = _short_fvg_only(day)
    result = evaluate_vt31_silver_bullet_v2(
        Vt31SilverBulletV2Input(
            instrument=Instrument("NAS100"),
            as_of=day.replace(hour=11, minute=0),
            m1_candles=(*_reference_hour(day=day), *session),
        )
    )

    assert result.decision is DemoTradingDecision.ABSTAIN
    assert result.abstain_reason is Vt31SilverBulletV2AbstainReason.WINDOW_CLOSED


def test_breaker_block_is_causal_and_records_same_price_order_block_confluence() -> None:
    day = datetime(2026, 7, 20, tzinfo=_NY)
    result = _evaluate(day, _short_breaker_confluence(day))

    assert result.decision is DemoTradingDecision.SETUP
    assert result.setup is not None
    assert result.setup.entry_model is Vt31SilverBulletV2EntryModel.BREAKER_BLOCK
    assert result.setup.entry_models == (
        Vt31SilverBulletV2EntryModel.BREAKER_BLOCK,
        Vt31SilverBulletV2EntryModel.ORDER_BLOCK,
    )
    assert result.setup.entry_price_formalization == "entry-zone-body-midpoint-v1"
    assert result.setup.decision_at == result.setup.confirmation_at


def test_order_block_is_causal_and_uses_post_raid_reversal_sequence() -> None:
    day = datetime(2026, 7, 21, tzinfo=_NY)
    result = _evaluate(day, _short_order_block_only(day))

    assert result.decision is DemoTradingDecision.SETUP
    assert result.setup is not None
    assert result.setup.entry_model is Vt31SilverBulletV2EntryModel.ORDER_BLOCK
    assert result.setup.entry_models == (Vt31SilverBulletV2EntryModel.ORDER_BLOCK,)
    assert result.setup.decision_at >= result.setup.confirmation_at


def test_fvg_is_post_raid_post_confirmation_and_never_pre_raid_reused() -> None:
    day = datetime(2026, 7, 22, tzinfo=_NY)
    result = _evaluate(day, _short_fvg_only(day))

    assert result.decision is DemoTradingDecision.SETUP
    assert result.setup is not None
    assert result.setup.entry_model is Vt31SilverBulletV2EntryModel.FAIR_VALUE_GAP
    assert result.setup.decision_at > result.setup.confirmation_at
    assert result.setup.entry_price_formalization == "fvg-consequent-encroachment-v1"


def test_non_equivalent_simultaneous_models_fail_closed_without_hidden_priority() -> None:
    day = datetime(2026, 7, 23, tzinfo=_NY)
    result = _evaluate(day, _ambiguous_breaker_and_fvg(day))

    assert result.decision is DemoTradingDecision.ABSTAIN
    assert (
        result.abstain_reason
        is Vt31SilverBulletV2AbstainReason.AMBIGUOUS_ENTRY_MODEL_CONFLUENCE
    )


def test_explicit_versioned_model_selection_can_resolve_source_ambiguity() -> None:
    day = datetime(2026, 7, 24, tzinfo=_NY)
    result = _evaluate(
        day,
        _ambiguous_breaker_and_fvg(day),
        config=Vt31SilverBulletV2Config(
            preferred_entry_model=Vt31SilverBulletV2EntryModel.FAIR_VALUE_GAP
        ),
    )

    assert result.decision is DemoTradingDecision.SETUP
    assert result.setup is not None
    assert result.setup.entry_model is Vt31SilverBulletV2EntryModel.FAIR_VALUE_GAP
    assert len(result.setup.entry_models) >= 2


@pytest.mark.parametrize("month", [1, 7])
def test_new_york_wall_clock_window_is_dst_aware(month: int) -> None:
    day = datetime(2026, month, 15, tzinfo=_NY)
    result = _evaluate(day, _short_fvg_only(day))

    assert result.decision is DemoTradingDecision.SETUP
    assert result.setup is not None
    assert result.setup.expires_at.astimezone(_NY).hour == 11
    assert result.setup.expires_at.astimezone(_NY).minute == 0


def test_missing_one_reference_minute_fails_closed() -> None:
    day = datetime(2026, 7, 27, tzinfo=_NY)
    session = _short_fvg_only(day)
    result = evaluate_vt31_silver_bullet_v2(
        Vt31SilverBulletV2Input(
            instrument=Instrument("NAS100"),
            as_of=session[-1].closed_at,
            m1_candles=(*_reference_hour(day=day)[:-1], *session),
        )
    )

    assert result.decision is DemoTradingDecision.ABSTAIN
    assert result.abstain_reason is Vt31SilverBulletV2AbstainReason.REFERENCE_RANGE_MISSING


def test_future_or_still_open_m1_evidence_is_rejected() -> None:
    day = datetime(2026, 7, 28, tzinfo=_NY)
    session = _short_fvg_only(day)
    with pytest.raises(Vt31SilverBulletV2ValidationError, match="future or still-open"):
        Vt31SilverBulletV2Input(
            instrument=Instrument("NAS100"),
            as_of=session[-2].closed_at,
            m1_candles=(*_reference_hour(day=day), *session),
        )


def test_duplicate_m1_evidence_is_rejected() -> None:
    day = datetime(2026, 7, 29, tzinfo=_NY)
    reference = _reference_hour(day=day)
    duplicate = reference[-1]
    with pytest.raises(Vt31SilverBulletV2ValidationError, match="duplicate"):
        Vt31SilverBulletV2Input(
            instrument=Instrument("NAS100"),
            as_of=day.replace(hour=10, minute=0),
            m1_candles=(*reference, duplicate),
        )


def test_out_of_order_m1_evidence_is_rejected() -> None:
    day = datetime(2026, 7, 30, tzinfo=_NY)
    reference = _reference_hour(day=day)
    with pytest.raises(Vt31SilverBulletV2ValidationError, match="chronological"):
        Vt31SilverBulletV2Input(
            instrument=Instrument("NAS100"),
            as_of=day.replace(hour=10, minute=0),
            m1_candles=(*reference[:-2], reference[-1], reference[-2]),
        )


def test_m5_cannot_be_substituted_for_required_m1_execution_evidence() -> None:
    day = datetime(2026, 7, 31, tzinfo=_NY)
    wrong = _snapshot(
        suffix=1001,
        instrument="NAS100",
        opened_at=day.replace(hour=10, minute=0),
        open_price=105.0,
        high=110.0,
        low=100.0,
        close=106.0,
        seconds=300,
    )
    with pytest.raises(Vt31SilverBulletV2ValidationError, match="exact M1"):
        Vt31SilverBulletV2Input(
            instrument=Instrument("NAS100"),
            as_of=wrong.closed_at,
            m1_candles=(wrong,),
        )


def test_non_nas100_market_is_explicitly_unsupported() -> None:
    day = datetime(2026, 8, 3, tzinfo=_NY)
    result = evaluate_vt31_silver_bullet_v2(
        Vt31SilverBulletV2Input(
            instrument=Instrument("EURUSD"),
            as_of=day.replace(hour=10, minute=30),
            m1_candles=(),
        )
    )

    assert result.decision is DemoTradingDecision.ABSTAIN
    assert result.abstain_reason is Vt31SilverBulletV2AbstainReason.UNSUPPORTED_METHOD_MARKET


def test_instrument_cannot_be_substituted_inside_consumed_evidence() -> None:
    day = datetime(2026, 8, 4, tzinfo=_NY)
    foreign = _snapshot(
        suffix=1101,
        instrument="EURUSD",
        opened_at=day.replace(hour=9, minute=0),
        open_price=1.1,
        high=1.2,
        low=1.0,
        close=1.1,
    )
    with pytest.raises(Vt31SilverBulletV2ValidationError, match="exact input instrument"):
        Vt31SilverBulletV2Input(
            instrument=Instrument("NAS100"),
            as_of=foreign.closed_at,
            m1_candles=(foreign,),
        )


def test_methodology_and_evidence_fingerprints_are_deterministic() -> None:
    day = datetime(2026, 8, 5, tzinfo=_NY)
    session = _short_fvg_only(day)

    first = _evaluate(day, session)
    second = _evaluate(day, session)

    assert first == second
    assert first.config_fingerprint == second.config_fingerprint
    assert first.methodology_fingerprint == second.methodology_fingerprint
    assert first.evidence_fingerprint == second.evidence_fingerprint
    assert len(first.methodology_fingerprint) == 64


def test_trader_geometry_has_no_quantity_or_risk_authority() -> None:
    day = datetime(2026, 8, 6, tzinfo=_NY)
    result = _evaluate(day, _short_fvg_only(day))

    assert result.setup is not None
    assert not hasattr(result.setup, "quantity")
    assert not hasattr(result.setup, "lot_size")
    assert not hasattr(result.setup, "risk_authorization")


def test_no_daily_bias_or_indicators_are_part_of_v2_config_or_input_contract() -> None:
    config_fields = {item.name for item in fields(Vt31SilverBulletV2Config)}
    input_fields = {item.name for item in fields(Vt31SilverBulletV2Input)}

    prohibited = {
        "daily_bias",
        "h4_bias",
        "ema",
        "rsi",
        "volume",
        "premium_discount",
        "macro_filter",
    }
    assert config_fields.isdisjoint(prohibited)
    assert input_fields.isdisjoint(prohibited)


def test_source_does_not_impose_minimum_reward_to_risk_threshold() -> None:
    day = datetime(2026, 8, 7, tzinfo=_NY)
    result = _evaluate(day, _short_fvg_only(day))

    assert result.setup is not None
    assert result.setup.expected_r_multiple > 0
    assert result.setup.expected_r_multiple < 5


def test_source_does_not_impose_numeric_sweep_depth_threshold() -> None:
    day = datetime(2026, 8, 10, tzinfo=_NY)
    start = day.replace(hour=10, minute=0)
    shallow = (
        _snapshot(
            suffix=1201,
            instrument="NAS100",
            opened_at=start,
            open_price=109.8,
            high=110.01,
            low=109.5,
            close=109.6,
        ),
        _snapshot(
            suffix=1202,
            instrument="NAS100",
            opened_at=start + timedelta(minutes=1),
            open_price=109.6,
            high=109.7,
            low=109.3,
            close=109.4,
        ),
        _snapshot(
            suffix=1203,
            instrument="NAS100",
            opened_at=start + timedelta(minutes=2),
            open_price=109.4,
            high=109.45,
            low=109.0,
            close=109.1,
        ),
    )
    result = _evaluate(day, shallow)

    assert result.abstain_reason is not Vt31SilverBulletV2AbstainReason.NO_RAID


def test_video_winner_fixture_has_source_provenance_not_profitability_assumption() -> None:
    day = datetime(2026, 8, 11, tzinfo=_NY)
    result = _evaluate(day, _short_breaker_confluence(day))

    assert result.setup is not None
    assert "05:31-05:52" in result.setup.source_timestamps
    assert result.setup.take_profit_price == result.setup.reference_range.low


def test_video_loser_fixture_is_still_a_methodologically_valid_setup() -> None:
    day = datetime(2026, 8, 12, tzinfo=_NY)
    result = _evaluate(day, _short_order_block_only(day))

    assert result.decision is DemoTradingDecision.SETUP
    assert result.setup is not None
    assert "10:22-10:52" in result.setup.source_timestamps


def test_video_no_trade_fixture_remains_abstain_without_retrospective_entry() -> None:
    day = datetime(2026, 8, 13, tzinfo=_NY)
    start = day.replace(hour=10, minute=0)
    session = (
        _snapshot(
            suffix=1301,
            instrument="NAS100",
            opened_at=start,
            open_price=108.0,
            high=112.0,
            low=107.0,
            close=111.5,
        ),
        _snapshot(
            suffix=1302,
            instrument="NAS100",
            opened_at=start + timedelta(minutes=1),
            open_price=111.5,
            high=113.0,
            low=110.0,
            close=112.0,
        ),
    )
    result = _evaluate(day, session)

    assert result.decision is DemoTradingDecision.ABSTAIN
    assert result.setup is None
