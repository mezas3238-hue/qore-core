"""D5 closure: Mission Director + Functional Readiness Map (CF-14/CF-20).

The mission turns an objective into a governed, replayable structure; readiness
distinguishes semantic capability from demonstrated economic usefulness and
fails closed against self-overstatement (CERTIFIED/DEMO_VALIDATING/QUALIFIED
require backing evidence).
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from qore.infrastructure.cibo.contracts import (
    CiboFunctionalAuthority,
    CiboFunctionalValidationError,
)
from qore.infrastructure.cibo.functional_coordinator import CiboFacultyDomain
from qore.infrastructure.cibo.functional_readiness import (
    CiboFunctionalReadinessEntry,
    CiboReadinessState,
    build_readiness_map,
    derive_readiness,
)
from qore.infrastructure.cibo.mission_director import (
    CiboMission,
    CiboMissionDirector,
    CiboMissionDisposition,
)
from qore.infrastructure.cibo_trader_capability_profile import (
    CiboEvidenceFreshnessState,
    CiboEvidenceRef,
)
from qore.infrastructure.research_evaluator_identity import (
    ResearchDecisionEvaluatorFamily,
    ResearchDecisionEvaluatorIdentity,
    ResearchDecisionEvaluatorSchemaVersion,
)
from qore.infrastructure.research_run import ResearchSoftwareRevision
from qore.kernel.result import Failure, Success

_NOW = datetime(2026, 8, 9, 0, 0, tzinfo=UTC)


def _ref(name: str) -> CiboEvidenceRef:
    return CiboEvidenceRef(f"evidence:{name}")


def _identity(suffix: str) -> ResearchDecisionEvaluatorIdentity:
    return ResearchDecisionEvaluatorIdentity(
        family=ResearchDecisionEvaluatorFamily(f"virtual.trader.{suffix}"),
        schema_version=ResearchDecisionEvaluatorSchemaVersion("v1"),
        software_revision=ResearchSoftwareRevision("rev-1"),
    )


_DIRECTOR = CiboMissionDirector()


def _direct(**overrides: object) -> object:
    kwargs: dict[str, object] = dict(
        mission_code="mission-demo",
        objective_code="demo-economic-validation",
        constraint_codes=("risk-only",),
        assigned_functions=(CiboFacultyDomain.TRADER_DIRECTOR,),
        assigned_traders=(_identity("vt01"),),
        readiness_codes=("trader-director",),
        missing_evidence_codes=(),
        unresolved_uncertainty_codes=(),
        assignment_codes=("research", "replay"),
        hypothesis_codes=("cibo-adds-value",),
        success_criteria=("positive-ab-delta",),
        failure_criteria=("negative-ab-delta",),
        training_codes=(),
        demo_observation_codes=("ab-window",),
        baseline_codes=("traders-risk-only",),
        counterfactual_codes=("cibo-managed",),
        disposition=CiboMissionDisposition.CONTINUE,
        lineage=("mission-demo",),
        unresolved_risk_codes=(),
        planned_at=_NOW,
    )
    kwargs.update(overrides)
    return _DIRECTOR.direct(**kwargs)  # type: ignore[arg-type]


# --- Mission ---


def test_mission_director_assembles_governed_mission() -> None:
    result = _direct()
    assert isinstance(result, Success)
    mission = result.value
    assert mission.authority is CiboFunctionalAuthority.REQUEST
    assert mission.disposition is CiboMissionDisposition.CONTINUE
    assert mission.assigned_traders == (_identity("vt01"),)
    assert mission.hypothesis_codes == ("cibo-adds-value",)


def test_mission_requires_hypothesis() -> None:
    result = _direct(hypothesis_codes=())
    assert isinstance(result, Failure)


def test_mission_requires_success_criteria() -> None:
    result = _direct(success_criteria=())
    assert isinstance(result, Failure)


def test_mission_duplicate_assigned_traders_rejected() -> None:
    result = _direct(assigned_traders=(_identity("vt01"), _identity("vt01")))
    assert isinstance(result, Failure)


def test_mission_value_equal_disposition_laundering_rejected() -> None:
    class FakeDisposition(str):
        pass

    with pytest.raises(CiboFunctionalValidationError):
        CiboMission(
            mission_code="mission-demo",
            objective_code="demo",
            constraint_codes=(),
            assigned_functions=(CiboFacultyDomain.TRADER_DIRECTOR,),
            assigned_traders=(_identity("vt01"),),
            readiness_codes=(),
            missing_evidence_codes=(),
            unresolved_uncertainty_codes=(),
            assignment_codes=(),
            hypothesis_codes=("h",),
            success_criteria=("s",),
            failure_criteria=(),
            training_codes=(),
            demo_observation_codes=(),
            baseline_codes=(),
            counterfactual_codes=(),
            disposition=FakeDisposition("continue"),  # type: ignore[arg-type]
            lineage=(),
            unresolved_risk_codes=(),
            planned_at=_NOW,
            authority=CiboFunctionalAuthority.REQUEST,
        )


def test_mission_constructor_rejects_non_request_authority() -> None:
    with pytest.raises(CiboFunctionalValidationError):
        CiboMission(
            mission_code="mission-demo",
            objective_code="demo",
            constraint_codes=(),
            assigned_functions=(),
            assigned_traders=(),
            readiness_codes=(),
            missing_evidence_codes=(),
            unresolved_uncertainty_codes=(),
            assignment_codes=(),
            hypothesis_codes=("h",),
            success_criteria=("s",),
            failure_criteria=(),
            training_codes=(),
            demo_observation_codes=(),
            baseline_codes=(),
            counterfactual_codes=(),
            disposition=CiboMissionDisposition.CONTINUE,
            lineage=(),
            unresolved_risk_codes=(),
            planned_at=_NOW,
            authority=CiboFunctionalAuthority.RECOMMENDATION,
        )


def test_mission_deterministic_replay() -> None:
    first = _direct()
    second = _direct()
    assert isinstance(first, Success) and isinstance(second, Success)
    assert first.value.logical_values() == second.value.logical_values()


# --- Readiness ---


def test_no_economic_evidence_is_insufficient() -> None:
    result = derive_readiness(
        function_code="trader-director",
        semantic_capability_code="coordinates-traders",
        demonstrated_economic_evidence=(),
        freshness_state=CiboEvidenceFreshnessState.CURRENT,
        assessed_at=_NOW,
    )
    assert isinstance(result, Success)
    assert result.value.state is CiboReadinessState.INSUFFICIENT_ECONOMIC_EVIDENCE


def test_economic_evidence_yields_qualified() -> None:
    result = derive_readiness(
        function_code="trader-director",
        semantic_capability_code="coordinates-traders",
        demonstrated_economic_evidence=(_ref("pnl"),),
        freshness_state=CiboEvidenceFreshnessState.CURRENT,
        assessed_at=_NOW,
    )
    assert isinstance(result, Success)
    assert result.value.state is CiboReadinessState.QUALIFIED


def test_certification_evidence_yields_certified() -> None:
    result = derive_readiness(
        function_code="trader-director",
        semantic_capability_code="coordinates-traders",
        demonstrated_economic_evidence=(_ref("pnl"),),
        certification_evidence=(_ref("cert"),),
        freshness_state=CiboEvidenceFreshnessState.CURRENT,
        assessed_at=_NOW,
    )
    assert isinstance(result, Success)
    assert result.value.state is CiboReadinessState.CERTIFIED


def test_demo_validation_evidence_yields_demo_validating() -> None:
    result = derive_readiness(
        function_code="trader-director",
        semantic_capability_code="coordinates-traders",
        demonstrated_economic_evidence=(_ref("pnl"),),
        demo_validation_evidence=(_ref("demo"),),
        freshness_state=CiboEvidenceFreshnessState.CURRENT,
        assessed_at=_NOW,
    )
    assert isinstance(result, Success)
    assert result.value.state is CiboReadinessState.DEMO_VALIDATING


def test_degraded_flag_yields_degraded() -> None:
    result = derive_readiness(
        function_code="trader-director",
        semantic_capability_code="coordinates-traders",
        demonstrated_economic_evidence=(_ref("pnl"),),
        degraded=True,
        freshness_state=CiboEvidenceFreshnessState.CURRENT,
        assessed_at=_NOW,
    )
    assert isinstance(result, Success)
    assert result.value.state is CiboReadinessState.DEGRADED


def test_blocked_flag_yields_blocked() -> None:
    result = derive_readiness(
        function_code="trader-director",
        semantic_capability_code="coordinates-traders",
        demonstrated_economic_evidence=(_ref("pnl"),),
        blocked=True,
        freshness_state=CiboEvidenceFreshnessState.CURRENT,
        assessed_at=_NOW,
    )
    assert isinstance(result, Success)
    assert result.value.state is CiboReadinessState.BLOCKED


def test_stale_freshness_yields_evidence_stale() -> None:
    result = derive_readiness(
        function_code="trader-director",
        semantic_capability_code="coordinates-traders",
        demonstrated_economic_evidence=(_ref("pnl"),),
        freshness_state=CiboEvidenceFreshnessState.STALE,
        assessed_at=_NOW,
    )
    assert isinstance(result, Success)
    assert result.value.state is CiboReadinessState.EVIDENCE_STALE


def test_readiness_cannot_self_overstate() -> None:
    # Direct construction of a CERTIFIED entry without certification evidence is
    # rejected: semantic capability alone can never manufacture CERTIFIED.
    with pytest.raises(CiboFunctionalValidationError):
        CiboFunctionalReadinessEntry(
            function_code="trader-director",
            semantic_capability_code="coordinates-traders",
            demonstrated_economic_evidence=(_ref("pnl"),),
            certification_evidence=(),
            demo_validation_evidence=(),
            degraded=False,
            blocked=False,
            freshness_state=CiboEvidenceFreshnessState.CURRENT,
            state=CiboReadinessState.CERTIFIED,
            assessed_at=_NOW,
        )


def test_readiness_bool_is_not_int() -> None:
    result = derive_readiness(
        function_code="trader-director",
        semantic_capability_code="coordinates-traders",
        demonstrated_economic_evidence=(_ref("pnl"),),
        degraded=1,  # type: ignore[arg-type]
        freshness_state=CiboEvidenceFreshnessState.CURRENT,
        assessed_at=_NOW,
    )
    assert isinstance(result, Failure)


def test_readiness_map_unique_codes_and_deterministic() -> None:
    entry = derive_readiness(
        function_code="trader-director",
        semantic_capability_code="coordinates-traders",
        demonstrated_economic_evidence=(_ref("pnl"),),
        freshness_state=CiboEvidenceFreshnessState.CURRENT,
        assessed_at=_NOW,
    )
    assert isinstance(entry, Success)
    first = build_readiness_map((entry.value,), assessed_at=_NOW)
    second = build_readiness_map((entry.value,), assessed_at=_NOW)
    assert isinstance(first, Success) and isinstance(second, Success)
    assert first.value.logical_values() == second.value.logical_values()
    assert first.value.authority is CiboFunctionalAuthority.OBSERVATION


def test_readiness_map_duplicate_codes_rejected() -> None:
    entry = derive_readiness(
        function_code="trader-director",
        semantic_capability_code="coordinates-traders",
        demonstrated_economic_evidence=(_ref("pnl"),),
        freshness_state=CiboEvidenceFreshnessState.CURRENT,
        assessed_at=_NOW,
    )
    assert isinstance(entry, Success)
    result = build_readiness_map((entry.value, entry.value), assessed_at=_NOW)
    assert isinstance(result, Failure)


def test_no_secrets_in_readiness_logical_values() -> None:
    entry = derive_readiness(
        function_code="trader-director",
        semantic_capability_code="coordinates-traders",
        demonstrated_economic_evidence=(_ref("pnl"),),
        freshness_state=CiboEvidenceFreshnessState.CURRENT,
        assessed_at=_NOW,
    )
    assert isinstance(entry, Success)
    material = repr(entry.value.logical_values())
    assert "token=" not in material
    assert "bearer " not in material
