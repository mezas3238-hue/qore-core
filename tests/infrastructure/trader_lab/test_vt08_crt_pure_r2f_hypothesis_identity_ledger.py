from __future__ import annotations

from datetime import UTC, datetime, timedelta

from qore.infrastructure.trader_lab.vt08_crt_pure_2y_replay import AggregatedCandle
from qore.infrastructure.trader_lab.vt08_crt_pure_r2_model1_reference_lab import (
    BreachGroup,
    M15Bar,
    OldLevel,
    ParentCrt,
    ReferenceKind,
    ReferencePolicy,
)
from qore.infrastructure.trader_lab.vt08_crt_pure_r2e_source_multiplicity_census import (
    ConfirmationState,
    SourceObservation,
)
from qore.infrastructure.trader_lab.vt08_crt_pure_r2f_hypothesis_identity_ledger import (
    LedgerState,
    _max_simultaneously_awaiting,
    _row,
    _stable_ids,
)
from qore.infrastructure.traders.crt_pure_identity import CrtPureMarket
from qore.infrastructure.traders.crt_pure_methodology_candidate import (
    CrtPureCandidateDirection,
)


def _candle(opened_at: datetime) -> AggregatedCandle:
    return AggregatedCandle(
        opened_at=opened_at,
        closed_at=opened_at + timedelta(hours=4),
        open_price=100,
        high_price=110,
        low_price=90,
        close_price=100,
        m5_count=48,
    )


def _parent() -> ParentCrt:
    opened_at = datetime(2026, 1, 1, 20, 0, tzinfo=UTC)
    return ParentCrt(
        market=CrtPureMarket.AUDUSD,
        direction=CrtPureCandidateDirection.BULLISH,
        triplet="1",
        c3_opened_at=opened_at,
        c3_closed_at=opened_at + timedelta(hours=4),
        c1=_candle(opened_at - timedelta(hours=8)),
        c2=_candle(opened_at - timedelta(hours=4)),
        c3_m5=(),
    )


def _observation(
    *,
    source_opened_at: datetime,
    evidence_offset: int,
    state: ConfirmationState,
    confirmation_opened_at: datetime | None,
) -> SourceObservation:
    source = M15Bar(
        opened_at=source_opened_at,
        open_price=100,
        high_price=103,
        low_price=95,
        close_price=98,
    )
    level = OldLevel(
        kind=ReferenceKind.OLD_LOW,
        price=96 - evidence_offset,
        pivot_opened_at=source_opened_at - timedelta(hours=1 + evidence_offset),
        confirmed_at=source_opened_at - timedelta(minutes=30),
        policy=ReferencePolicy.UNTOUCHED_SWING_STRENGTH_1,
    )
    group = BreachGroup(
        source_candle=source,
        kind=ReferenceKind.OLD_LOW,
        policy=ReferencePolicy.UNTOUCHED_SWING_STRENGTH_1,
        references=(level,),
    )
    return SourceObservation(
        group=group,
        source_index=evidence_offset,
        confirmation_state=state,
        confirmation_opened_at=confirmation_opened_at,
    )


def test_stable_ids_change_for_independent_source_reference() -> None:
    parent = _parent()
    first = _observation(
        source_opened_at=parent.c3_opened_at,
        evidence_offset=1,
        state=ConfirmationState.NO_BODY_CONFIRMATION,
        confirmation_opened_at=None,
    )
    second = _observation(
        source_opened_at=parent.c3_opened_at + timedelta(minutes=30),
        evidence_offset=2,
        state=ConfirmationState.NO_BODY_CONFIRMATION,
        confirmation_opened_at=None,
    )

    first_ids = _stable_ids(
        market=CrtPureMarket.AUDUSD,
        parent=parent,
        observation=first,
    )
    second_ids = _stable_ids(
        market=CrtPureMarket.AUDUSD,
        parent=parent,
        observation=second,
    )

    assert first_ids != second_ids


def test_row_never_grants_entry_or_capital_authority() -> None:
    parent = _parent()
    observation = _observation(
        source_opened_at=parent.c3_opened_at,
        evidence_offset=1,
        state=ConfirmationState.EXECUTABLE_CONFIRMATION,
        confirmation_opened_at=parent.c3_opened_at + timedelta(minutes=15),
    )

    row = _row(
        market=CrtPureMarket.AUDUSD,
        parent=parent,
        observation=observation,
        generation=1,
    )

    assert row.state_at_c3_close == LedgerState.CONFIRMED_ENTRY_SLOT_AVAILABLE.value
    assert row.confirmation_known_at == (
        parent.c3_opened_at + timedelta(minutes=30)
    ).isoformat()
    assert row.grants_entry_authority is False
    assert row.grants_capital_authority is False


def test_concurrency_counts_two_unresolved_hypotheses() -> None:
    parent = _parent()
    first = _row(
        market=CrtPureMarket.AUDUSD,
        parent=parent,
        observation=_observation(
            source_opened_at=parent.c3_opened_at,
            evidence_offset=1,
            state=ConfirmationState.NO_BODY_CONFIRMATION,
            confirmation_opened_at=None,
        ),
        generation=1,
    )
    second = _row(
        market=CrtPureMarket.AUDUSD,
        parent=parent,
        observation=_observation(
            source_opened_at=parent.c3_opened_at + timedelta(minutes=30),
            evidence_offset=2,
            state=ConfirmationState.EXECUTABLE_CONFIRMATION,
            confirmation_opened_at=parent.c3_opened_at + timedelta(minutes=45),
        ),
        generation=2,
    )

    assert _max_simultaneously_awaiting(parent=parent, rows=(first, second)) == 2
