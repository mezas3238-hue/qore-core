"""Source route classification must never authorize trading or source fidelity."""

from __future__ import annotations

from dataclasses import replace

import pytest

from qore.infrastructure.trader_lab.capitalizer_scalper_author_route_audit_v1 import (
    IDENTITY,
    SOURCES,
    AuthorRoute,
    FidelityVerdict,
    SourceRouteDifferential,
    audit_frozen_v49_route_claims,
)


def test_all_six_documented_first_party_routes_are_present() -> None:
    assert {item.route for item in SOURCES} == set(AuthorRoute)
    assert len(SOURCES) == 6
    assert all(item.primary_url.startswith("https://ttrades.com/") for item in SOURCES)
    assert all(item.author == "TTrades" and item.source_section for item in SOURCES)


def test_no_route_claim_is_misrepresented_as_full_author_fidelity() -> None:
    decisions = audit_frozen_v49_route_claims()
    assert {row.route for row in decisions} == set(AuthorRoute)
    assert all(row.identity == IDENTITY for row in decisions)
    assert all(row.qore_decision_roles == ("H1", "M15", "M1") for row in decisions)
    assert all(row.reason_codes for row in decisions)
    assert all(not row.author_fidelity_certified for row in decisions)
    assert all(not row.label_as_literal_author_route for row in decisions)
    assert all(not row.alters_source_admission for row in decisions)


def test_generic_scalp_is_partially_aligned_not_an_unqualified_clone() -> None:
    rows = {row.route: row for row in audit_frozen_v49_route_claims()}
    generic = rows[AuthorRoute.GENERIC_SCALPING]
    assert generic.verdict is FidelityVerdict.PARTIAL_GENERIC_ALIGNMENT
    assert "DAILY_CONTEXT" in generic.source_roles
    assert "DAILY_BROADER_CONTEXT_NOT_USED_BY_QORE" in generic.reason_codes


@pytest.mark.parametrize(
    "route",
    [
        AuthorRoute.ASIA_POSITIONAL,
        AuthorRoute.ASIA_H4_M15_FRACTAL,
        AuthorRoute.LONDON_DAILY_H4_M15,
    ],
)
def test_literal_session_routes_conflict_with_frozen_qore_stack(
    route: AuthorRoute,
) -> None:
    rows = {row.route: row for row in audit_frozen_v49_route_claims()}
    assert rows[route].verdict is FidelityVerdict.CONFLICT_LITERAL_SESSION_ROUTE


@pytest.mark.parametrize(
    "route",
    [AuthorRoute.NEW_YORK_MANIPULATION, AuthorRoute.FAILURE_TO_MANIPULATE],
)
def test_session_profile_and_ftm_require_caller_level_evidence(
    route: AuthorRoute,
) -> None:
    rows = {row.route: row for row in audit_frozen_v49_route_claims()}
    assert rows[route].verdict is FidelityVerdict.UNRESOLVED_ROUTE_EXECUTION


def test_new_york_entry_models_are_explicit_alternatives_not_super_and() -> None:
    ny = next(row for row in SOURCES if row.route is AuthorRoute.NEW_YORK_MANIPULATION)
    assert "FVG_ENTRY" in ny.source_alternatives
    assert "OB_ENTRY" in ny.source_alternatives
    assert "OTHER_EXPLICIT_ENTRY_MODEL" in ny.source_alternatives
    assert "CISD" in ny.mandatory_source_concepts


def test_audit_result_cannot_be_forged_as_certification_or_admission() -> None:
    row = audit_frozen_v49_route_claims()[0]
    with pytest.raises(ValueError, match="cannot certify"):
        replace(row, author_fidelity_certified=True)
    with pytest.raises(ValueError, match="no authority"):
        replace(row, alters_source_admission=True)
    with pytest.raises(ValueError, match="no authority"):
        replace(row, label_as_literal_author_route=True)


def test_source_differential_cannot_use_wrong_identity() -> None:
    row = audit_frozen_v49_route_claims()[0]
    assert isinstance(row, SourceRouteDifferential)
    with pytest.raises(ValueError, match="identity"):
        replace(row, identity="FORGED_CERTIFICATE")
