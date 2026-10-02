from __future__ import annotations

import pytest

from qore.infrastructure.core_stack_v2.drawdown_phenotype_memory import (
    DrawdownPhenotype,
    DrawdownPhenotypeComposition,
    DrawdownPhenotypeQuery,
    DrawdownPhenotypeRecognition,
    UniversalDrawdownPhenotypeMemory,
)


def _phenotype(
    view: str,
    signature: str,
    *,
    losses: int,
    winners: int,
) -> DrawdownPhenotype:
    sample = losses + winners
    if losses > 0 and winners == 0:
        composition = DrawdownPhenotypeComposition.PURE_LOSS
    elif losses > winners:
        composition = DrawdownPhenotypeComposition.LOSS_DOMINANT
    elif losses == winners:
        composition = DrawdownPhenotypeComposition.MIXED_BALANCED
    else:
        composition = DrawdownPhenotypeComposition.WINNER_DOMINANT
    return DrawdownPhenotype(
        view=view,
        signature=signature,
        composition=composition,
        historical_sample=sample,
        historical_losses=losses,
        historical_winners=winners,
        fold_presence="BOTH_FOLDS",
        temporal_stability="LOSS_PRESENT_ALL_HALVES",
    )


def test_unknown_form_is_explicit_and_has_no_authority() -> None:
    memory = UniversalDrawdownPhenotypeMemory(
        (
            _phenotype("PRESSURE", "RISING", losses=8, winners=0),
        )
    )
    result = memory.assess(
        DrawdownPhenotypeQuery(
            signatures=(("ENVIRONMENT", "UNSEEN"),),
        )
    )

    assert result.recognition is DrawdownPhenotypeRecognition.UNKNOWN
    assert result.matched == ()
    assert result.unknown_views == ("ENVIRONMENT",)
    assert result.confidence_bps == 0
    assert result.order_authority is False
    assert result.risk_authority is False
    assert result.sizing_authority is False
    assert result.execution_authority is False
    assert result.stop_authority is False
    assert result.target_authority is False


def test_pure_loss_form_is_knowledge_not_a_trade_decision() -> None:
    memory = UniversalDrawdownPhenotypeMemory(
        (
            _phenotype(
                "PRESSURE_CONFIRMATION_PATH",
                "PRESSURE_UP_OPPOSITE_UP_CONFIRM_MIXED",
                losses=18,
                winners=0,
            ),
        )
    )
    result = memory.assess(
        DrawdownPhenotypeQuery(
            signatures=(
                (
                    "PRESSURE_CONFIRMATION_PATH",
                    "PRESSURE_UP_OPPOSITE_UP_CONFIRM_MIXED",
                ),
            ),
        )
    )

    assert result.recognition is DrawdownPhenotypeRecognition.KNOWN_PURE_LOSS
    assert result.pure_loss_matches == 1
    assert result.confidence_bps == 10_000
    assert result.sizing_authority is False
    assert result.order_authority is False
    assert result.stop_authority is False
    assert result.target_authority is False


def test_mixed_current_evidence_keeps_winner_overlap_explicit() -> None:
    memory = UniversalDrawdownPhenotypeMemory(
        (
            _phenotype("ENVIRONMENT", "FRAGILE", losses=12, winners=0),
            _phenotype("RECOVERY_BALANCE", "RECOVERY_DOMINANT", losses=2, winners=9),
        )
    )
    result = memory.assess(
        DrawdownPhenotypeQuery(
            signatures=(
                ("ENVIRONMENT", "FRAGILE"),
                ("RECOVERY_BALANCE", "RECOVERY_DOMINANT"),
            ),
        )
    )

    assert (
        result.recognition
        is DrawdownPhenotypeRecognition.KNOWN_WINNER_OVERLAP
    )
    assert result.pure_loss_matches == 1
    assert result.winner_dominant_matches == 1
    assert result.confidence_bps == 10_000


def test_partial_coverage_reports_unknown_views_instead_of_guessing() -> None:
    memory = UniversalDrawdownPhenotypeMemory(
        (
            _phenotype("ENVIRONMENT", "FRAGILE", losses=9, winners=0),
        )
    )
    result = memory.assess(
        DrawdownPhenotypeQuery(
            signatures=(
                ("ENVIRONMENT", "FRAGILE"),
                ("RELATIONAL_RECOVERY", "UNSEEN"),
            ),
        )
    )

    assert result.recognition is DrawdownPhenotypeRecognition.KNOWN_PURE_LOSS
    assert result.known_views == ("ENVIRONMENT",)
    assert result.unknown_views == ("RELATIONAL_RECOVERY",)
    assert result.confidence_bps == 5_000


def test_historical_composition_must_match_closed_counts() -> None:
    with pytest.raises(ValueError, match="composition"):
        DrawdownPhenotype(
            view="ENVIRONMENT",
            signature="FRAGILE",
            composition=DrawdownPhenotypeComposition.PURE_LOSS,
            historical_sample=4,
            historical_losses=2,
            historical_winners=2,
            fold_presence="BOTH_FOLDS",
            temporal_stability="MULTIPLE_HALVES",
        )


def test_query_is_canonical_and_does_not_accept_duplicate_views() -> None:
    with pytest.raises(ValueError, match="canonical"):
        DrawdownPhenotypeQuery(
            signatures=(("Z_VIEW", "A"), ("A_VIEW", "B")),
        )

    with pytest.raises(ValueError, match="unique"):
        DrawdownPhenotypeQuery(
            signatures=(("VIEW", "A"), ("VIEW", "B")),
        )
