from __future__ import annotations

from collections import Counter
from datetime import UTC, datetime, timedelta

from qore.infrastructure.trader_lab.vt08_crt_pure_r2_model1_reference_lab import (
    BreachGroup,
    M15Bar,
    OldLevel,
    ReferenceKind,
    ReferencePolicy,
)
from qore.infrastructure.trader_lab.vt08_crt_pure_r2e_source_multiplicity_census import (
    ConfirmationState,
    SourceObservation,
    _confirmation_state,
    _count_wait_parent,
)
from qore.infrastructure.traders.crt_pure_methodology_candidate import (
    CrtPureCandidateDirection,
)


def _bar(
    minute: int,
    open_price: int,
    high_price: int,
    low_price: int,
    close_price: int,
) -> M15Bar:
    return M15Bar(
        opened_at=datetime(2026, 1, 1, 12, minute, tzinfo=UTC),
        open_price=open_price,
        high_price=high_price,
        low_price=low_price,
        close_price=close_price,
    )


def _group(
    *,
    opened_at: datetime,
    kind: ReferenceKind,
    evidence_offset: int,
) -> BreachGroup:
    level = OldLevel(
        kind=kind,
        price=100 + evidence_offset,
        pivot_opened_at=opened_at - timedelta(hours=1 + evidence_offset),
        confirmed_at=opened_at - timedelta(minutes=30),
        policy=ReferencePolicy.UNTOUCHED_SWING_STRENGTH_1,
    )
    source = M15Bar(
        opened_at=opened_at,
        open_price=100,
        high_price=105,
        low_price=95,
        close_price=99 if kind is ReferenceKind.OLD_LOW else 101,
    )
    return BreachGroup(
        source_candle=source,
        kind=kind,
        policy=ReferencePolicy.UNTOUCHED_SWING_STRENGTH_1,
        references=(level,),
    )


def test_confirmation_state_requires_next_contiguous_bar() -> None:
    source = _bar(0, 100, 101, 96, 97)
    confirmation = _bar(15, 97, 103, 97, 102)
    entry = _bar(30, 102, 104, 101, 103)

    state, opened_at = _confirmation_state(
        source=source,
        subsequent=(confirmation, entry),
        direction=CrtPureCandidateDirection.BULLISH,
    )

    assert state is ConfirmationState.EXECUTABLE_CONFIRMATION
    assert opened_at == confirmation.opened_at


def test_confirmation_state_splits_last_bar_body_close() -> None:
    source = _bar(0, 100, 101, 96, 97)
    confirmation = _bar(15, 97, 103, 97, 102)

    state, opened_at = _confirmation_state(
        source=source,
        subsequent=(confirmation,),
        direction=CrtPureCandidateDirection.BULLISH,
    )

    assert state is ConfirmationState.BODY_CONFIRMED_NO_NEXT_BAR
    assert opened_at == confirmation.opened_at


def test_wait_counter_distinguishes_independent_later_source() -> None:
    opened_at = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)
    first = SourceObservation(
        group=_group(
            opened_at=opened_at,
            kind=ReferenceKind.OLD_LOW,
            evidence_offset=1,
        ),
        source_index=0,
        confirmation_state=ConfirmationState.NO_BODY_CONFIRMATION,
        confirmation_opened_at=None,
    )
    later = SourceObservation(
        group=_group(
            opened_at=opened_at + timedelta(minutes=30),
            kind=ReferenceKind.OLD_LOW,
            evidence_offset=2,
        ),
        source_index=2,
        confirmation_state=ConfirmationState.EXECUTABLE_CONFIRMATION,
        confirmation_opened_at=opened_at + timedelta(minutes=45),
    )
    counter: Counter[str] = Counter()

    _count_wait_parent(observations=(first, later), counter=counter)

    assert counter["wait_parent_count"] == 1
    assert counter["wait_with_later_aligned_source"] == 1
    assert counter["wait_with_later_executable_confirmation"] == 1
    assert counter["wait_with_later_reference_reuse"] == 0
