from __future__ import annotations

from uuid import UUID

import pytest

import qore.infrastructure.structured_hybrid_synthetic_semantics as structured
import qore.infrastructure.structured_note_payoff_semantics as note


def _feature_id(value: int) -> structured.StructuredFeatureId:
    return structured.StructuredFeatureId(UUID(int=value))


def test_redemption_rejects_conversion_material() -> None:
    with pytest.raises(
        note.StructuredNotePayoffValidationError,
        match="feature references",
    ):
        note.StructuredNotePayoffOutcome(
            kind=note.StructuredNoteOutcomeKind.REDEMPTION,
            redemption_feature_id=_feature_id(204),
            conversion_feature_id=_feature_id(206),
        )


def test_participation_rejects_redemption_material() -> None:
    with pytest.raises(
        note.StructuredNotePayoffValidationError,
        match="feature references",
    ):
        note.StructuredNotePayoffOutcome(
            kind=note.StructuredNoteOutcomeKind.PARTICIPATION,
            participation_feature_id=_feature_id(205),
            redemption_feature_id=_feature_id(204),
        )


def test_conversion_rejects_participation_material() -> None:
    with pytest.raises(
        note.StructuredNotePayoffValidationError,
        match="feature references",
    ):
        note.StructuredNotePayoffOutcome(
            kind=note.StructuredNoteOutcomeKind.CONVERSION,
            conversion_feature_id=_feature_id(206),
            participation_feature_id=_feature_id(205),
        )
