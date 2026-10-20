from datetime import UTC, datetime

import pytest

from qore.infrastructure.traders.crt_pure_key_level_context import (
    CrtPureKeyLevelEvidence,
    CrtPureKeyLevelFamily,
    CrtPureKeyLevelInteraction,
    CrtPureKeyLevelReadiness,
    assess_key_level_context,
    key_level_absence_is_universal_veto,
    source_native_key_level_families,
)


def test_source_native_key_level_families_exclude_level_b_taxonomy() -> None:
    assert source_native_key_level_families() == (
        CrtPureKeyLevelFamily.OLD_CRTH,
        CrtPureKeyLevelFamily.OLD_CRTL,
        CrtPureKeyLevelFamily.MOB,
    )


def test_no_key_level_is_context_unknown_not_universal_veto() -> None:
    result = assess_key_level_context((), execution_timeframe_seconds=900)
    assert result.interaction is CrtPureKeyLevelInteraction.UNKNOWN
    assert result.families == ()
    assert result.hard_veto_if_absent is False
    assert CrtPureKeyLevelReadiness.TAXONOMY_UNRESOLVED in result.readiness
    assert key_level_absence_is_universal_veto() is False


def test_old_crth_reaction_is_retained_as_htf_context_only() -> None:
    evidence = CrtPureKeyLevelEvidence(
        evidence_id="old-crth-001",
        level_token="CRTH:prior-parent",
        observed_at=datetime(2026, 1, 2, 12, 0, tzinfo=UTC),
        interaction=CrtPureKeyLevelInteraction.REACTION_FROM,
        family=CrtPureKeyLevelFamily.OLD_CRTH,
        level_timeframe_seconds=14400,
    )
    result = assess_key_level_context((evidence,), execution_timeframe_seconds=900)
    assert result.interaction is CrtPureKeyLevelInteraction.REACTION_FROM
    assert result.families == (CrtPureKeyLevelFamily.OLD_CRTH,)
    assert result.higher_timeframe_context_present is True
    assert result.grants_entry_authority is False
    assert result.grants_capital_authority is False


def test_mixed_interactions_fail_to_unknown_instead_of_inventing_priority() -> None:
    now = datetime(2026, 1, 2, 12, 0, tzinfo=UTC)
    evidence = (
        CrtPureKeyLevelEvidence(
            evidence_id="journey",
            level_token="CRTH:target",
            observed_at=now,
            interaction=CrtPureKeyLevelInteraction.JOURNEY_TO,
            family=CrtPureKeyLevelFamily.OLD_CRTH,
        ),
        CrtPureKeyLevelEvidence(
            evidence_id="mob",
            level_token="MOB:1",
            observed_at=now,
            interaction=CrtPureKeyLevelInteraction.MAKE_OR_BREAK,
            family=CrtPureKeyLevelFamily.MOB,
        ),
    )
    result = assess_key_level_context(evidence, execution_timeframe_seconds=900)
    assert result.interaction is CrtPureKeyLevelInteraction.UNKNOWN


def test_key_level_context_cannot_grant_authority() -> None:
    with pytest.raises(ValueError, match="cannot independently grant entry"):
        from qore.infrastructure.traders.crt_pure_key_level_context import (
            CrtPureKeyLevelAssessment,
        )

        CrtPureKeyLevelAssessment(
            interaction=CrtPureKeyLevelInteraction.REACTION_FROM,
            families=(CrtPureKeyLevelFamily.OLD_CRTL,),
            evidence_ids=("x",),
            readiness=(CrtPureKeyLevelReadiness.ROLE_SOURCE_CLOSED,),
            higher_timeframe_context_present=True,
            grants_entry_authority=True,
        )
