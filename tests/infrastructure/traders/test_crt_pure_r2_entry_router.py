from datetime import UTC, datetime

from qore.infrastructure.traders.crt_pure_cognitive_contract import (
    CrtPureReasoningAction,
)
from qore.infrastructure.traders.crt_pure_methodology_candidate import (
    CrtPureCandidateDirection,
)
from qore.infrastructure.traders.crt_pure_model1 import (
    CrtPureModel1Bar,
    CrtPureModel1Reference,
    CrtPureModel1ReferenceKind,
    assess_model1_confirmation,
    detect_model1_candidate,
)
from qore.infrastructure.traders.crt_pure_r2_entry_router import (
    CrtPureR2EntryFamily,
    CrtPureR2EntryState,
    assess_model1_entry_family,
    assess_unclosed_entry_family,
)


def _bar(minute: int, opened: int, high: int, low: int, closed: int) -> CrtPureModel1Bar:
    return CrtPureModel1Bar(
        opened_at=datetime(2026, 1, 2, 10, minute, tzinfo=UTC),
        open_price=opened,
        high_price=high,
        low_price=low,
        close_price=closed,
    )


def test_parent_crt_waits_when_model1_has_not_appeared() -> None:
    result = assess_model1_entry_family(
        parent_direction=CrtPureCandidateDirection.BULLISH,
        confirmation=None,
    )
    assert result.action is CrtPureReasoningAction.WAIT
    assert result.state is CrtPureR2EntryState.AWAITING_CONFIRMATION
    assert "NO_C3_OPEN_FALLBACK" in result.why


def test_unconfirmed_model1_remains_wait() -> None:
    candidate = detect_model1_candidate(
        reference=CrtPureModel1Reference(
            kind=CrtPureModel1ReferenceKind.OLD_LOW,
            price=95,
            evidence_id="old-low",
        ),
        candle=_bar(0, 96, 97, 92, 93),
    )
    assert candidate is not None
    confirmation = assess_model1_confirmation(
        candidate=candidate,
        candle=_bar(15, 94, 96, 93, 95),
    )
    result = assess_model1_entry_family(
        parent_direction=CrtPureCandidateDirection.BULLISH,
        confirmation=confirmation,
    )
    assert result.action is CrtPureReasoningAction.WAIT
    assert result.grants_execution_authority is False


def test_direction_aligned_confirmed_model1_reaches_entry_family_execute() -> None:
    candidate = detect_model1_candidate(
        reference=CrtPureModel1Reference(
            kind=CrtPureModel1ReferenceKind.OLD_LOW,
            price=95,
            evidence_id="old-low",
        ),
        candle=_bar(0, 96, 97, 92, 93),
    )
    assert candidate is not None
    confirmation = assess_model1_confirmation(
        candidate=candidate,
        candle=_bar(15, 94, 98, 93, 97),
    )
    result = assess_model1_entry_family(
        parent_direction=CrtPureCandidateDirection.BULLISH,
        confirmation=confirmation,
    )
    assert result.action is CrtPureReasoningAction.EXECUTE
    assert result.state is CrtPureR2EntryState.CONFIRMED
    assert result.grants_execution_authority is False
    assert result.grants_capital_authority is False


def test_opposing_model1_forces_abstain_and_bias_review() -> None:
    candidate = detect_model1_candidate(
        reference=CrtPureModel1Reference(
            kind=CrtPureModel1ReferenceKind.OLD_HIGH,
            price=105,
            evidence_id="old-high",
        ),
        candle=_bar(0, 104, 108, 103, 107),
    )
    assert candidate is not None
    confirmation = assess_model1_confirmation(
        candidate=candidate,
        candle=_bar(15, 105, 106, 100, 103),
    )
    result = assess_model1_entry_family(
        parent_direction=CrtPureCandidateDirection.BULLISH,
        confirmation=confirmation,
    )
    assert result.action is CrtPureReasoningAction.ABSTAIN
    assert result.state is CrtPureR2EntryState.CONFLICTED
    assert "BIAS_REEVALUATION_REQUIRED" in result.why


def test_ote_and_time_families_fail_closed_until_source_contract_closes() -> None:
    for family in (
        CrtPureR2EntryFamily.OTE,
        CrtPureR2EntryFamily.TIME_BASED,
        CrtPureR2EntryFamily.OTHER_SOURCE_AUTHORIZED,
    ):
        result = assess_unclosed_entry_family(family)
        assert result.action is CrtPureReasoningAction.WAIT
        assert result.state is CrtPureR2EntryState.UNRESOLVED
