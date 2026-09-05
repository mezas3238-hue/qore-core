"""D4 closure: Dynamic Trader Team Formation (CF-03/CF-16/CF-20).

Exact-version membership + capability provenance; independent opinions with
hypothesis/confidence/uncertainty/objections; disagreement preservation (never
silent averaging); explicit contradictory-evidence comparison; deterministic
replay; reconfiguration/dissolution; and no authority increase from synthesis.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from qore.infrastructure.cibo.contracts import (
    CiboEvidenceStatus,
    CiboFunctionalAuthority,
    CiboFunctionalError,
    CiboFunctionalEvidence,
    CiboFunctionalValidationError,
    CiboGovernedEvidenceKind,
)
from qore.infrastructure.cibo.trader_team import (
    CiboConfidenceLevel,
    CiboTeamDisposition,
    CiboTeamNeed,
    CiboTeamSynthesisDisposition,
    CiboTraderTeam,
    CiboTraderTeamOpinion,
    CiboTraderTeamSynthesis,
    form_trader_team,
    synthesize_trader_team,
)
from qore.infrastructure.cibo_trader_capability_profile import (
    CiboCertificationState,
    CiboEvidenceFreshness,
    CiboEvidenceFreshnessState,
    CiboEvidenceRef,
    CiboLabEvidenceRef,
    CiboLabEvidenceStage,
    CiboSpecialtyCode,
    CiboTimeframeCode,
    CiboTradeableMarketRef,
    CiboTraderCapabilityProfile,
    CiboTraderConfigFingerprint,
    build_cibo_trader_capability_profile,
)
from qore.infrastructure.research_evaluator_identity import (
    ResearchDecisionEvaluatorFamily,
    ResearchDecisionEvaluatorIdentity,
    ResearchDecisionEvaluatorSchemaVersion,
)
from qore.infrastructure.research_run import ResearchSoftwareRevision
from qore.kernel.result import Failure, Result, Success

_NOW = datetime(2026, 8, 9, 0, 0, tzinfo=UTC)


def _ref(name: str) -> CiboEvidenceRef:
    return CiboEvidenceRef(f"evidence:{name}")


def _identity(suffix: str) -> ResearchDecisionEvaluatorIdentity:
    return ResearchDecisionEvaluatorIdentity(
        family=ResearchDecisionEvaluatorFamily(f"virtual.trader.{suffix}"),
        schema_version=ResearchDecisionEvaluatorSchemaVersion("v1"),
        software_revision=ResearchSoftwareRevision("rev-1"),
    )


def _profile(
    suffix: str,
    fingerprint: int,
    *,
    specialty: str = "trend-following",
) -> CiboTraderCapabilityProfile:
    result = build_cibo_trader_capability_profile(
        trader_identity=_identity(suffix),
        config_fingerprint=CiboTraderConfigFingerprint(f"{fingerprint:064x}"),
        specialty=CiboSpecialtyCode(specialty),
        qualified_markets=(CiboTradeableMarketRef("EUR/USD"),),
        qualified_timeframes=(CiboTimeframeCode("h1"),),
        certified_lab_evidence=(
            CiboLabEvidenceRef(stage=CiboLabEvidenceStage.OOS, ref=_ref(f"lab-{suffix}")),
        ),
        certification_state=CiboCertificationState.EVIDENCE_COLLECTED,
        freshness=CiboEvidenceFreshness(state=CiboEvidenceFreshnessState.CURRENT, as_of=_NOW),
    )
    assert isinstance(result, Success)
    return result.value


def _opinion(
    suffix: str,
    fingerprint: int,
    *,
    hypothesis: str = "long",
    evidence: CiboFunctionalEvidence | None = None,
) -> CiboTraderTeamOpinion:
    return CiboTraderTeamOpinion(
        trader_identity=_identity(suffix),
        config_fingerprint=CiboTraderConfigFingerprint(f"{fingerprint:064x}"),
        hypothesis_code=hypothesis,
        confidence=CiboConfidenceLevel.MEDIUM,
        uncertainty_codes=("tail",),
        objection_codes=(),
        evidence=evidence or _dependent(),
        voiced_at=_NOW,
        authority=CiboFunctionalAuthority.OPINION,
    )


def _dependent() -> CiboFunctionalEvidence:
    return CiboFunctionalEvidence(
        status=CiboEvidenceStatus.EVIDENCE_DEPENDENT,
        evidence_refs=(_ref("market"),),
        as_of=_NOW,
        dependency_kind=CiboGovernedEvidenceKind.MARKET,
        reasons=("external.authority.required",),
    )


def _form(
    *profiles: CiboTraderCapabilityProfile,
    disposition: CiboTeamDisposition = CiboTeamDisposition.FORMED,
) -> Result[CiboTraderTeam, CiboFunctionalError]:
    return form_trader_team(
        profiles,
        mission_code="mission-alpha",
        needs=(CiboTeamNeed.MARKET, CiboTeamNeed.UNCERTAINTY),
        disposition=disposition,
        formed_at=_NOW,
        provenance=("director",),
    )


# --- Formation ---


def test_form_team_with_exact_version_members() -> None:
    result = _form(_profile("vt01", 1), _profile("vt02", 2))
    assert isinstance(result, Success)
    team = result.value
    assert team.authority is CiboFunctionalAuthority.REQUEST
    assert team.disposition is CiboTeamDisposition.FORMED
    identities = {member.trader_identity for member in team.members}
    assert identities == {_identity("vt01"), _identity("vt02")}
    # capability provenance is derived from each profile's certified evidence.
    assert all(member.capability_provenance for member in team.members)


def test_dissolved_team_has_no_members() -> None:
    result = _form(disposition=CiboTeamDisposition.DISSOLVED)
    assert isinstance(result, Success)
    assert result.value.disposition is CiboTeamDisposition.DISSOLVED
    assert result.value.members == ()


def test_formed_team_requires_members() -> None:
    result = _form()
    assert isinstance(result, Failure)


def test_dissolved_team_rejects_members() -> None:
    formed = _form(_profile("vt01", 1))
    assert isinstance(formed, Success)
    with pytest.raises(CiboFunctionalValidationError):
        CiboTraderTeam(
            mission_code="mission-alpha",
            needs=(CiboTeamNeed.MARKET,),
            members=formed.value.members,
            disposition=CiboTeamDisposition.DISSOLVED,
            formed_at=_NOW,
            provenance=(),
            authority=CiboFunctionalAuthority.REQUEST,
        )


def test_duplicate_member_versions_rejected() -> None:
    result = _form(_profile("vt01", 1), _profile("vt01", 1))
    assert isinstance(result, Failure)


def test_value_equal_need_enum_laundering_rejected() -> None:
    class FakeNeed(str):
        pass

    formed = _form(_profile("vt01", 1))
    assert isinstance(formed, Success)
    with pytest.raises(CiboFunctionalValidationError):
        CiboTraderTeam(
            mission_code="mission-alpha",
            needs=(FakeNeed("market"),),  # type: ignore[arg-type]
            members=formed.value.members,
            disposition=CiboTeamDisposition.FORMED,
            formed_at=_NOW,
            provenance=(),
            authority=CiboFunctionalAuthority.REQUEST,
        )


def test_team_deterministic_replay() -> None:
    first = _form(_profile("vt02", 2), _profile("vt01", 1))
    second = _form(_profile("vt01", 1), _profile("vt02", 2))
    assert isinstance(first, Success) and isinstance(second, Success)
    assert first.value.logical_values() == second.value.logical_values()


# --- Synthesis ---


def test_disagreement_is_preserved_not_averaged() -> None:
    team = _form(_profile("vt01", 1), _profile("vt02", 2))
    assert isinstance(team, Success)
    result = synthesize_trader_team(
        team.value,
        (_opinion("vt01", 1, hypothesis="long"), _opinion("vt02", 2, hypothesis="short")),
        synthesized_at=_NOW,
    )
    assert isinstance(result, Success)
    synthesis = result.value
    assert synthesis.disposition is CiboTeamSynthesisDisposition.DIVERGED
    assert len(synthesis.disagreements) == 1
    assert set(synthesis.disagreements[0].hypothesis_codes) == {"long", "short"}
    # no silent averaging: the two hypotheses remain distinct.
    assert synthesis.authority is CiboFunctionalAuthority.OPINION


def test_agreeing_opinions_yield_insufficient_evidence() -> None:
    team = _form(_profile("vt01", 1), _profile("vt02", 2))
    assert isinstance(team, Success)
    result = synthesize_trader_team(
        team.value,
        (_opinion("vt01", 1, hypothesis="long"), _opinion("vt02", 2, hypothesis="long")),
        synthesized_at=_NOW,
    )
    assert isinstance(result, Success)
    assert result.value.disposition is CiboTeamSynthesisDisposition.INSUFFICIENT_EVIDENCE
    assert result.value.disagreements == ()


def test_opinion_from_non_member_rejected() -> None:
    team = _form(_profile("vt01", 1))
    assert isinstance(team, Success)
    result = synthesize_trader_team(
        team.value,
        (_opinion("vt99", 99, hypothesis="long"),),
        synthesized_at=_NOW,
    )
    assert isinstance(result, Failure)


def test_synthesis_cannot_raise_authority() -> None:
    team = _form(_profile("vt01", 1), _profile("vt02", 2))
    assert isinstance(team, Success)
    result = synthesize_trader_team(
        team.value,
        (_opinion("vt01", 1), _opinion("vt02", 2)),
        synthesized_at=_NOW,
    )
    assert isinstance(result, Success)
    assert result.value.authority is CiboFunctionalAuthority.OPINION
    # the synthesis constructor refuses any authority other than OPINION.
    with pytest.raises(CiboFunctionalValidationError):
        CiboTraderTeamSynthesis(
            team=result.value.team,
            opinions=result.value.opinions,
            disagreements=result.value.disagreements,
            evidence=result.value.evidence,
            disposition=result.value.disposition,
            synthesized_at=_NOW,
            authority=CiboFunctionalAuthority.RECOMMENDATION,
        )


def test_synthesis_deterministic_replay() -> None:
    team = _form(_profile("vt01", 1), _profile("vt02", 2))
    assert isinstance(team, Success)
    opinions = (_opinion("vt01", 1, hypothesis="long"), _opinion("vt02", 2, hypothesis="short"))
    first = synthesize_trader_team(team.value, opinions, synthesized_at=_NOW)
    second = synthesize_trader_team(team.value, opinions, synthesized_at=_NOW)
    assert isinstance(first, Success) and isinstance(second, Success)
    assert first.value.logical_values() == second.value.logical_values()


def test_no_secrets_in_team_logical_values() -> None:
    team = _form(_profile("vt01", 1))
    assert isinstance(team, Success)
    material = repr(team.value.logical_values())
    assert "token=" not in material
    assert "bearer " not in material
