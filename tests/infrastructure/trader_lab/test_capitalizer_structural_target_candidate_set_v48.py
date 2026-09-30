from decimal import Decimal

from qore.infrastructure.trader_lab.capitalizer_structural_target_candidate_set_v48 import (
    V48StructuralTargetCandidate,
    V48TargetDirection,
    build_target_candidate_set,
)


def _candidate(
    target_id: str,
    price: str,
    *,
    untouched: bool = True,
) -> V48StructuralTargetCandidate:
    return V48StructuralTargetCandidate(
        target_id=target_id,
        kind="HTF_HIGH",
        price=Decimal(price),
        known_at_iso="2026-01-02T10:00:00+00:00",
        untouched=untouched,
        higher_timeframe=True,
    )


def test_multiple_valid_targets_are_available_without_forcing_unique_resolution() -> None:
    result = build_target_candidate_set(
        (_candidate("T1", "1.1100"), _candidate("T2", "1.1200")),
        direction=V48TargetDirection.LONG,
        entry_reference=Decimal("1.1000"),
    )

    assert result.structural_target_available is True
    assert result.ambiguous_multiple_targets is True
    assert len(result.eligible) == 2
    assert result.exact_target_selected is False
    assert result.outcome_used is False
    assert result.reward_r_used is False


def test_taken_or_wrong_side_targets_do_not_count_as_available() -> None:
    result = build_target_candidate_set(
        (
            _candidate("TAKEN", "1.1100", untouched=False),
            _candidate("BEHIND", "1.0900"),
        ),
        direction=V48TargetDirection.LONG,
        entry_reference=Decimal("1.1000"),
    )

    assert result.structural_target_available is False
    assert not result.eligible
    assert len(result.rejected) == 2
