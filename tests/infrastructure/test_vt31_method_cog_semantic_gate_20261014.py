"""Contract fixtures only; no live proof or real VT31 source replay."""
from dataclasses import replace

import pytest

from scripts.vt31_method_cog_semantic_gate_20261014 import (
    COG_NATIVE, PROFILE_ICT, PROFILE_QORE, PROFILE_TTRADES,
    SOURCE_AMBIGUOUS, SOURCE_AUTHOR, SOURCE_QORE, SemanticCase,
    SemanticState, dossier_verdict, inspect_semantic_case,
)


def case(**kw):
    base = dict(
        gate="M2", profile=PROFILE_TTRADES,
        case_id="FIXTURE_ONLY_NOT_NATIVE_REPLAY",
        doctrine_ref="PROFILE_SOURCE_WITNESS_PR929",
        source_class=SOURCE_AUTHOR,
        expected="WAIT", actual_cog_decision="WAIT",
        cog_provenance=COG_NATIVE, cognized_asof_verified=True,
        independent_witness=True, negative_no_trade_case=True,
    )
    base.update(kw)
    return SemanticCase(**base)


def test_correct_wait_counts_as_semantic_case_not_profit():
    result = inspect_semantic_case(case())
    assert result.state is SemanticState.CONFIRMED_IN_SCOPE
    assert not result.method_certified
    assert not result.cognition_certified


def test_wrong_cog_action_is_contradicted_even_with_perfect_pnl():
    result = inspect_semantic_case(case(actual_cog_decision="TRADE_INTENT"))
    assert result.state is SemanticState.CONTRADICTED


@pytest.mark.parametrize("profile", [PROFILE_ICT, PROFILE_TTRADES])
def test_qore_proxy_does_not_prove_author_method(profile):
    result = inspect_semantic_case(case(
        profile=profile, source_class=SOURCE_QORE,
    ))
    assert result.state is SemanticState.PROFILE_CONTAMINATION


def test_qore_can_only_conform_to_its_own_explicit_policy():
    a = inspect_semantic_case(case(
        profile=PROFILE_QORE, source_class=SOURCE_QORE,
    ))
    b = inspect_semantic_case(case(
        profile=PROFILE_QORE, source_class=SOURCE_AUTHOR,
    ))
    assert a.state is SemanticState.CONFIRMED_IN_SCOPE
    assert b.state is SemanticState.PROFILE_CONTAMINATION
    assert not a.trader_certified


def test_author_ambiguity_prevents_method_promotion():
    r = inspect_semantic_case(case(source_class=SOURCE_AMBIGUOUS))
    assert r.state is SemanticState.UNKNOWN_SOURCE


def test_conflicting_source_is_not_silenced():
    r = inspect_semantic_case(replace(case(), source_conflict_noted=True))
    assert r.state is SemanticState.UNKNOWN_SOURCE


def test_fake_cog_dto_must_not_be_method_certified():
    r = inspect_semantic_case(case(cog_provenance="SYNTHETIC_DTO"))
    assert r.state is SemanticState.NOT_AUTHENTIC_COG


@pytest.mark.parametrize("field", [
    "cognized_asof_verified", "independent_witness",
])
def test_clock_or_source_unverified_is_not_pass(field):
    r = inspect_semantic_case(case(**{field: False}))
    assert r.state is SemanticState.PENDING_CAUSAL_WITNESS


def test_independent_COG_OPS_signatures_cannot_be_faked_by_case():
    r = inspect_semantic_case(case(gate="M6"))
    assert r.state is SemanticState.PENDING_INDEPENDENT_REVIEW


def test_untrusted_negative_expected_intent_rejected():
    with pytest.raises(ValueError, match="NEGATIVE_CASE_EXPECTED"):
        inspect_semantic_case(case(expected="TRADE_INTENT"))


def test_dossier_does_not_average_away_failed_method():
    results = dossier_verdict((
        case(), case(actual_cog_decision="TRADE_INTENT"),
        case(source_class=SOURCE_AMBIGUOUS),
    ))
    assert [r.state for r in results] == [
        SemanticState.CONFIRMED_IN_SCOPE,
        SemanticState.CONTRADICTED, SemanticState.UNKNOWN_SOURCE,
    ]
    assert all(not r.method_certified for r in results)
