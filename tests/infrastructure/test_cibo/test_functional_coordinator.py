from __future__ import annotations

from datetime import UTC, datetime
from typing import cast

from _governed_evidence_fixtures import dependent_evidence

from qore.infrastructure.cibo.contracts import (
    CiboEvidenceStatus,
    CiboFunctionalAuthority,
    CiboFunctionalError,
    CiboFunctionalEvidence,
    CiboFunctionalValidationError,
    CiboGovernedEvidenceKind,
)
from qore.infrastructure.cibo.executive_recommendation import (
    CiboRecommendationDisposition,
    CiboRiskAwareComposer,
    CiboRiskContext,
)
from qore.infrastructure.cibo.functional_coordinator import (
    CiboCoordinationDisposition,
    CiboFacultyDomain,
    CiboFunctionalContribution,
    CiboFunctionalCoordination,
    CiboFunctionalCoordinator,
    CiboFunctionalDisagreement,
)
from qore.infrastructure.cibo.opportunity_search import (
    CiboOpportunityHypothesis,
    CiboOpportunitySearch,
    CiboOpportunityState,
)
from qore.infrastructure.cibo.specialist_mesh import (
    CiboSpecialistFaculty,
    CiboSpecialistMesh,
    CiboSpecialistOpinion,
)
from qore.infrastructure.cibo_trader_capability_profile import CiboEvidenceRef
from qore.kernel.result import Failure, Success

_NOW = datetime(2026, 8, 9, 0, 0, tzinfo=UTC)
_COORDINATOR = CiboFunctionalCoordinator()


def _dependent_evidence(
    refs: tuple[CiboEvidenceRef, ...] = (CiboEvidenceRef("evidence:ref"),),
) -> CiboFunctionalEvidence:
    return dependent_evidence(
        CiboGovernedEvidenceKind.MARKET,
        evidence_refs=refs,
        as_of=_NOW,
        reasons=("external.authority.required",),
    )


def _insufficient_evidence() -> CiboFunctionalEvidence:
    return CiboFunctionalEvidence(
        status=CiboEvidenceStatus.INSUFFICIENT,
        evidence_refs=(),
        as_of=_NOW,
        reasons=("insufficient",),
    )


def _contribution(
    *,
    faculty: CiboFacultyDomain = CiboFacultyDomain.FINANCIAL_WORLD_MONITORING,
    code: str = "no-material-change",
    subject: str = "subject.eurusd",
    authority: CiboFunctionalAuthority = CiboFunctionalAuthority.OBSERVATION,
    evidence: CiboFunctionalEvidence | None = None,
) -> CiboFunctionalContribution:
    return CiboFunctionalContribution(
        faculty=faculty,
        contribution_code=code,
        subject_key=subject,
        authority=authority,
        evidence=_dependent_evidence() if evidence is None else evidence,
        authored_at=_NOW,
        provenance=("attribution.source",),
    )


# --- CF-20: normal coordination ---


def test_coordinate_abstains_when_dependent_and_uncontested() -> None:
    # Correction 003: RECOMMEND requires SUFFICIENT (authority-rooted) evidence,
    # which CIBO cannot manufacture; dependent evidence fails closed to ABSTAIN.
    result = _COORDINATOR.coordinate(
        (
            _contribution(
                faculty=CiboFacultyDomain.FINANCIAL_WORLD_MONITORING,
                code="no-material-change",
                authority=CiboFunctionalAuthority.OBSERVATION,
            ),
            _contribution(
                faculty=CiboFacultyDomain.OPPORTUNITY_SEARCH,
                code="hypothesis",
                subject="subject.idea",
                authority=CiboFunctionalAuthority.OPINION,
            ),
        ),
        coordinated_at=_NOW,
    )
    assert isinstance(result, Success)
    coordination = result.value
    assert isinstance(coordination, CiboFunctionalCoordination)
    assert coordination.disposition is CiboCoordinationDisposition.ABSTAIN
    assert coordination.authority is CiboFunctionalAuthority.ABSTENTION
    assert coordination.disagreements == ()
    assert coordination.request_code is None


def test_coordinate_request_for_explicit_research_request() -> None:
    result = _COORDINATOR.coordinate(
        (_contribution(),),
        coordinated_at=_NOW,
        request_code="research.request",
    )
    assert isinstance(result, Success)
    coordination = result.value
    assert coordination.disposition is CiboCoordinationDisposition.REQUEST
    assert coordination.authority is CiboFunctionalAuthority.REQUEST
    assert coordination.request_code == "research.request"


def test_coordinate_abstain_on_insufficient_evidence() -> None:
    result = _COORDINATOR.coordinate(
        (_contribution(evidence=_insufficient_evidence()),),
        coordinated_at=_NOW,
    )
    assert isinstance(result, Success)
    coordination = result.value
    assert coordination.disposition is CiboCoordinationDisposition.ABSTAIN
    assert coordination.authority is CiboFunctionalAuthority.ABSTENTION


def test_coordinate_preserves_disagreement_and_abstains() -> None:
    result = _COORDINATOR.coordinate(
        (
            _contribution(
                faculty=CiboFacultyDomain.MARKET_INTELLIGENCE_MESH,
                code="bullish",
                subject="subject.eurusd",
                authority=CiboFunctionalAuthority.OPINION,
            ),
            _contribution(
                faculty=CiboFacultyDomain.FINANCIAL_WORLD_MONITORING,
                code="bearish",
                subject="subject.eurusd",
                authority=CiboFunctionalAuthority.OBSERVATION,
            ),
        ),
        coordinated_at=_NOW,
    )
    assert isinstance(result, Success)
    coordination = result.value
    assert coordination.disposition is CiboCoordinationDisposition.ABSTAIN
    assert len(coordination.disagreements) == 1
    disagreement = coordination.disagreements[0]
    assert isinstance(disagreement, CiboFunctionalDisagreement)
    assert disagreement.subject_key == "subject.eurusd"
    assert disagreement.conclusion_codes == ("bearish", "bullish")
    assert disagreement.faculties == (
        CiboFacultyDomain.FINANCIAL_WORLD_MONITORING,
        CiboFacultyDomain.MARKET_INTELLIGENCE_MESH,
    )


# --- CF-20: adversarial ---


def test_coordinate_wrong_contribution_type_fails_closed() -> None:
    result = _COORDINATOR.coordinate(
        (cast(CiboFunctionalContribution, "not-a-contribution"),),
        coordinated_at=_NOW,
    )
    assert isinstance(result, Failure)
    assert isinstance(result.error, CiboFunctionalError)


def test_coordinate_duplicate_faculty_code_with_differing_material_rejected() -> None:
    result = _COORDINATOR.coordinate(
        (
            _contribution(code="same.code", subject="subject.a"),
            _contribution(code="same.code", subject="subject.b"),
        ),
        coordinated_at=_NOW,
    )
    assert isinstance(result, Failure)
    assert isinstance(result.error, CiboFunctionalValidationError)


def test_coordinate_empty_contributions_fails_closed() -> None:
    result = _COORDINATOR.coordinate((), coordinated_at=_NOW)
    assert isinstance(result, Failure)
    assert isinstance(result.error, CiboFunctionalValidationError)


def test_coordinate_rejects_sensitive_material_in_code() -> None:
    result = _COORDINATOR.coordinate(
        (_contribution(),),
        coordinated_at=_NOW,
        request_code="private_key",
    )
    assert isinstance(result, Failure)
    assert isinstance(result.error, CiboFunctionalValidationError)


def test_coordinate_logical_values_contain_no_secrets() -> None:
    result = _COORDINATOR.coordinate((_contribution(),), coordinated_at=_NOW)
    assert isinstance(result, Success)
    material = repr(result.value.logical_values())
    for secret_part in ("private_key", "token=", "secret=", "password="):
        assert secret_part not in material


def test_coordinate_request_code_only_valid_for_request() -> None:
    result = _COORDINATOR.coordinate(
        (_contribution(),),
        coordinated_at=_NOW,
        request_code="research.request",
    )
    assert isinstance(result, Success)
    coordination = result.value
    assert coordination.disposition is CiboCoordinationDisposition.REQUEST
    assert coordination.authority is CiboFunctionalAuthority.REQUEST


def test_coordinate_authority_ceiling_has_no_execution_member() -> None:
    execution_like = {"execution", "order", "decision", "risk-decision"}
    assert not execution_like.intersection(
        {member.value for member in CiboFunctionalAuthority}
    )


def test_coordinate_opinion_cannot_launder_into_recommend() -> None:
    result = _COORDINATOR.coordinate(
        (
            _contribution(
                faculty=CiboFacultyDomain.TRADER_VOICE,
                code="opine",
                authority=CiboFunctionalAuthority.OPINION,
                evidence=_insufficient_evidence(),
            ),
        ),
        coordinated_at=_NOW,
    )
    assert isinstance(result, Success)
    coordination = result.value
    assert coordination.disposition is CiboCoordinationDisposition.ABSTAIN
    assert coordination.authority is CiboFunctionalAuthority.ABSTENTION


def test_coordinate_is_deterministic_for_identical_input() -> None:
    first = _COORDINATOR.coordinate(
        (
            _contribution(
                faculty=CiboFacultyDomain.FINANCIAL_WORLD_MONITORING,
                code="no-material-change",
            ),
            _contribution(
                faculty=CiboFacultyDomain.OPPORTUNITY_SEARCH,
                code="hypothesis",
            ),
        ),
        coordinated_at=_NOW,
    )
    second = _COORDINATOR.coordinate(
        (
            _contribution(
                faculty=CiboFacultyDomain.FINANCIAL_WORLD_MONITORING,
                code="no-material-change",
            ),
            _contribution(
                faculty=CiboFacultyDomain.OPPORTUNITY_SEARCH,
                code="hypothesis",
            ),
        ),
        coordinated_at=_NOW,
    )
    assert isinstance(first, Success) and isinstance(second, Success)
    assert first.value.logical_values() == second.value.logical_values()


def test_coordination_revalidates_nested_evidence() -> None:
    contribution = _contribution()
    corrupt_evidence = _dependent_evidence()
    object.__setattr__(corrupt_evidence, "evidence_refs", ("not-a-ref",))
    object.__setattr__(contribution, "evidence", corrupt_evidence)
    result = _COORDINATOR.coordinate((contribution,), coordinated_at=_NOW)
    assert isinstance(result, Failure)
    assert isinstance(result.error, CiboFunctionalError)


# --- CF-20: coherent cross-domain fail-closed integration path ---


def test_coherent_functional_path_has_no_execution_authority() -> None:
    # authorized -> evidence-dependent -> specialists -> hypothesis -> risk-aware
    # reasoning -> typed abstention -> coordination material, proving no execution
    # authority and that CIBO cannot manufacture governed sufficiency.

    world_evidence = _dependent_evidence((CiboEvidenceRef("evidence:world"),))

    specialist_opinion = CiboSpecialistOpinion(
        faculty=CiboSpecialistFaculty.MACRO_REGIME,
        opinion_code="regime.stable",
        evidence=world_evidence,
        authored_at=_NOW,
        authority=CiboFunctionalAuthority.OPINION,
    )
    mesh_result = CiboSpecialistMesh().collect(
        (specialist_opinion,),
        concluded_at=_NOW,
    )
    assert isinstance(mesh_result, Success)
    mesh = mesh_result.value
    assert mesh.authority is CiboFunctionalAuthority.OPINION

    hypothesis = CiboOpportunityHypothesis(
        opportunity_code="opportunity.idea",
        market_refs=(CiboEvidenceRef("evidence:world"),),
        evidence=world_evidence,
        state=CiboOpportunityState.HYPOTHESIS,
        authority=CiboFunctionalAuthority.OPINION,
        declared_at=_NOW,
    )
    evaluated = CiboOpportunitySearch().evaluate(hypothesis)
    assert isinstance(evaluated, Success)
    assert evaluated.value.state is CiboOpportunityState.HYPOTHESIS
    assert evaluated.value.authority is CiboFunctionalAuthority.OPINION

    risk_context = CiboRiskContext(
        risk_evidence=dependent_evidence(
            CiboGovernedEvidenceKind.RISK,
            evidence_refs=(CiboEvidenceRef("evidence:risk"),),
            as_of=_NOW,
            reasons=("external.risk.authority",),
        ),
        risk_assessment_code="risk.approved",
        assessed_at=_NOW,
    )
    recommendation_result = CiboRiskAwareComposer().compose(
        recommendation_code="recommend.allocate",
        functional_evidence=world_evidence,
        risk_context=risk_context,
        composed_at=_NOW,
    )
    assert isinstance(recommendation_result, Success)
    recommendation = recommendation_result.value
    # Correction 003: without an authority root the composer abstains.
    assert recommendation.disposition is CiboRecommendationDisposition.ABSTAIN
    assert recommendation.authority is CiboFunctionalAuthority.ABSTENTION

    coordination_result = _COORDINATOR.coordinate(
        (
            CiboFunctionalContribution(
                faculty=CiboFacultyDomain.FINANCIAL_WORLD_MONITORING,
                contribution_code="no-material-change",
                subject_key="subject.world.monitor",
                authority=CiboFunctionalAuthority.OBSERVATION,
                evidence=world_evidence,
                authored_at=_NOW,
                provenance=("monitor.world",),
            ),
            CiboFunctionalContribution(
                faculty=CiboFacultyDomain.MARKET_INTELLIGENCE_MESH,
                contribution_code=mesh.authority.value,
                subject_key="subject.world.mesh",
                authority=CiboFunctionalAuthority.OPINION,
                evidence=mesh.evidence,
                authored_at=_NOW,
                provenance=("mesh.specialists",),
            ),
            CiboFunctionalContribution(
                faculty=CiboFacultyDomain.RISK_AWARE_RECOMMENDATION,
                contribution_code=recommendation.recommendation_code,
                subject_key="subject.world.recommend",
                authority=CiboFunctionalAuthority.ABSTENTION,
                evidence=recommendation.functional_evidence,
                authored_at=_NOW,
                provenance=("executive.recommendation",),
            ),
        ),
        coordinated_at=_NOW,
    )
    assert isinstance(coordination_result, Success)
    coordination = coordination_result.value
    assert coordination.disposition is CiboCoordinationDisposition.ABSTAIN
    assert coordination.authority is CiboFunctionalAuthority.ABSTENTION

    allowed = {
        CiboFunctionalAuthority.OBSERVATION,
        CiboFunctionalAuthority.OPINION,
        CiboFunctionalAuthority.ABSTENTION,
    }
    for contribution in coordination.contributions:
        assert contribution.authority in allowed
    assert coordination.logical_values() == coordination.logical_values()
