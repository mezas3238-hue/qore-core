from datetime import UTC, datetime, timedelta

import pytest

from qore.infrastructure.traders.crt_pure_model1 import (
    MODEL1_EXECUTION_TIMEFRAME_SECONDS,
    MODEL1_PARENT_TIMEFRAME_SECONDS,
    CrtPureModel1Bar,
    CrtPureModel1Direction,
    CrtPureModel1Reference,
    CrtPureModel1ReferenceKind,
    CrtPureModel1State,
    assess_model1_confirmation,
    build_model1_entry,
    detect_model1_candidate,
)


def _bar(
    minute: int,
    opened: int,
    high: int,
    low: int,
    closed: int,
) -> CrtPureModel1Bar:
    return CrtPureModel1Bar(
        opened_at=datetime(2026, 1, 2, 10, minute, tzinfo=UTC),
        open_price=opened,
        high_price=high,
        low_price=low,
        close_price=closed,
    )


def test_source_alignment_is_h4_to_m15() -> None:
    assert MODEL1_PARENT_TIMEFRAME_SECONDS == 14400
    assert MODEL1_EXECUTION_TIMEFRAME_SECONDS == 900


def test_bearish_model1_requires_up_close_stab_of_old_high() -> None:
    reference = CrtPureModel1Reference(
        kind=CrtPureModel1ReferenceKind.OLD_HIGH,
        price=105,
        evidence_id="old-high-001",
    )
    candidate = detect_model1_candidate(
        reference=reference,
        candle=_bar(0, 104, 108, 103, 107),
    )
    assert candidate is not None
    assert candidate.direction is CrtPureModel1Direction.BEARISH
    assert candidate.confirmation_body_level == 104
    assert candidate.structural_stop == 108
    assert candidate.executable_authority is False


def test_bullish_model1_requires_down_close_stab_of_old_low() -> None:
    reference = CrtPureModel1Reference(
        kind=CrtPureModel1ReferenceKind.OLD_LOW,
        price=95,
        evidence_id="old-low-001",
    )
    candidate = detect_model1_candidate(
        reference=reference,
        candle=_bar(0, 96, 97, 92, 93),
    )
    assert candidate is not None
    assert candidate.direction is CrtPureModel1Direction.BULLISH
    assert candidate.confirmation_body_level == 96
    assert candidate.structural_stop == 92


def test_wrong_candle_direction_does_not_create_model1() -> None:
    reference = CrtPureModel1Reference(
        kind=CrtPureModel1ReferenceKind.OLD_HIGH,
        price=105,
        evidence_id="old-high-001",
    )
    assert detect_model1_candidate(
        reference=reference,
        candle=_bar(0, 107, 108, 103, 104),
    ) is None


def test_wick_below_body_level_does_not_confirm_bearish_model1() -> None:
    reference = CrtPureModel1Reference(
        kind=CrtPureModel1ReferenceKind.OLD_HIGH,
        price=105,
        evidence_id="old-high-001",
    )
    candidate = detect_model1_candidate(
        reference=reference,
        candle=_bar(0, 104, 108, 103, 107),
    )
    assert candidate is not None
    confirmation = assess_model1_confirmation(
        candidate=candidate,
        candle=_bar(15, 106, 107, 102, 105),
    )
    assert confirmation.state is CrtPureModel1State.AWAITING_CONFIRMATION


def test_body_close_confirms_and_next_m15_open_is_causal_replay_fill() -> None:
    reference = CrtPureModel1Reference(
        kind=CrtPureModel1ReferenceKind.OLD_HIGH,
        price=105,
        evidence_id="old-high-001",
    )
    candidate = detect_model1_candidate(
        reference=reference,
        candle=_bar(0, 104, 108, 103, 107),
    )
    assert candidate is not None
    confirmation = assess_model1_confirmation(
        candidate=candidate,
        candle=_bar(15, 105, 106, 100, 103),
    )
    assert confirmation.state is CrtPureModel1State.CONFIRMED
    assert confirmation.decision_at == datetime(2026, 1, 2, 10, 30, tzinfo=UTC)

    next_bar = _bar(30, 103, 104, 99, 100)
    entry = build_model1_entry(
        confirmation=confirmation,
        next_candle=next_bar,
    )
    assert entry.entry_price == 103
    assert entry.stop_price == 108
    assert entry.live_authorized is False


def test_non_contiguous_fill_is_rejected() -> None:
    reference = CrtPureModel1Reference(
        kind=CrtPureModel1ReferenceKind.OLD_LOW,
        price=95,
        evidence_id="old-low-001",
    )
    candidate = detect_model1_candidate(
        reference=reference,
        candle=_bar(0, 96, 97, 92, 93),
    )
    assert candidate is not None
    confirmation = assess_model1_confirmation(
        candidate=candidate,
        candle=_bar(15, 94, 98, 93, 97),
    )
    assert confirmation.state is CrtPureModel1State.CONFIRMED
    late = CrtPureModel1Bar(
        opened_at=confirmation.decision_at + timedelta(minutes=15),
        open_price=97,
        high_price=99,
        low_price=96,
        close_price=98,
    )
    with pytest.raises(ValueError, match="next M15 open"):
        build_model1_entry(confirmation=confirmation, next_candle=late)
