"""D6 closure: Counterfactual Review + Economic Accountability + Attribution.

CF-07/08/09/17/18/19/20 ownership. Counterfactuals are evidence-bound and never
fabricated or hindsight-laundered; intervention attribution fails closed (a
profitable outcome is never sufficient proof of CIBO causation).
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from qore.infrastructure.cibo.accountability import (
    CiboAttributionState,
    CiboCounterfactualAssessment,
    CiboCounterfactualKind,
    CiboCounterfactualStatus,
    CiboInterventionAttribution,
    CiboInterventionLineage,
    assess_counterfactual,
    attribute_intervention,
)
from qore.infrastructure.cibo.contracts import (
    CiboFunctionalAuthority,
    CiboFunctionalValidationError,
)
from qore.infrastructure.cibo_trader_capability_profile import CiboEvidenceRef
from qore.infrastructure.research_evaluator_identity import (
    ResearchDecisionEvaluatorFamily,
    ResearchDecisionEvaluatorIdentity,
    ResearchDecisionEvaluatorSchemaVersion,
)
from qore.infrastructure.research_run import ResearchSoftwareRevision
from qore.kernel.result import Failure, Success

_NOW = datetime(2026, 8, 9, 0, 0, tzinfo=UTC)
_HORIZON = datetime(2026, 8, 8, 0, 0, tzinfo=UTC)


def _ref(name: str) -> CiboEvidenceRef:
    return CiboEvidenceRef(f"evidence:{name}")


def _identity(suffix: str) -> ResearchDecisionEvaluatorIdentity:
    return ResearchDecisionEvaluatorIdentity(
        family=ResearchDecisionEvaluatorFamily(f"virtual.trader.{suffix}"),
        schema_version=ResearchDecisionEvaluatorSchemaVersion("v1"),
        software_revision=ResearchSoftwareRevision("rev-1"),
    )


def _lineage() -> CiboInterventionLineage:
    return CiboInterventionLineage(
        situation_code="regime-transition",
        evidence_refs=(_ref("situation"),),
        trader_identities=(_identity("vt01"),),
        function_codes=("risk-aware-recommendation",),
        opinion_codes=("long",),
        synthesis_code="synthesis-alpha",
        recommendation_code="recommend-alpha",
        decision_code="governed-decision",
        outcome_ref=_ref("outcome"),
        learning_disposition_code="recalibrate",
        recorded_at=_NOW,
    )


# --- Counterfactual ---


def test_supported_counterfactual_requires_evidence_and_conclusion() -> None:
    result = assess_counterfactual(
        kind=CiboCounterfactualKind.ALTERNATE_TRADER,
        question_code="alternate-trader-vt02",
        status=CiboCounterfactualStatus.SUPPORTED,
        evidence_refs=(_ref("replay-vt02"),),
        conclusion_code="vt02-outperforms",
        evidence_horizon=_HORIZON,
        assessed_at=_NOW,
    )
    assert isinstance(result, Success)
    assert result.value.status is CiboCounterfactualStatus.SUPPORTED
    assert result.value.authority is CiboFunctionalAuthority.OPINION


def test_supported_counterfactual_without_evidence_rejected() -> None:
    result = assess_counterfactual(
        kind=CiboCounterfactualKind.ALTERNATE_TRADER,
        question_code="alternate-trader-vt02",
        status=CiboCounterfactualStatus.SUPPORTED,
        evidence_refs=(),
        conclusion_code="vt02-outperforms",
        evidence_horizon=_HORIZON,
        assessed_at=_NOW,
    )
    assert isinstance(result, Failure)


def test_unknowable_counterfactual_has_no_conclusion() -> None:
    result = assess_counterfactual(
        kind=CiboCounterfactualKind.UNKNOWABLE,
        question_code="counterfactual-unknowable",
        status=CiboCounterfactualStatus.UNKNOWABLE,
        evidence_refs=(),
        conclusion_code=None,
        evidence_horizon=_HORIZON,
        assessed_at=_NOW,
    )
    assert isinstance(result, Success)
    assert result.value.conclusion_code is None


def test_unsupported_counterfactual_rejects_conclusion() -> None:
    result = assess_counterfactual(
        kind=CiboCounterfactualKind.REGIME_LUCK_VS_SKILL,
        question_code="luck-vs-skill",
        status=CiboCounterfactualStatus.UNSUPPORTED,
        evidence_refs=(),
        conclusion_code="skill",  # no conclusion allowed
        evidence_horizon=_HORIZON,
        assessed_at=_NOW,
    )
    assert isinstance(result, Failure)


def test_unknowable_kind_requires_unknowable_status() -> None:
    result = assess_counterfactual(
        kind=CiboCounterfactualKind.UNKNOWABLE,
        question_code="unknowable",
        status=CiboCounterfactualStatus.SUPPORTED,
        evidence_refs=(_ref("x"),),
        conclusion_code="y",
        evidence_horizon=_HORIZON,
        assessed_at=_NOW,
    )
    assert isinstance(result, Failure)


def test_counterfactual_no_hindsight_laundering() -> None:
    future_horizon = datetime(2026, 8, 10, 0, 0, tzinfo=UTC)
    result = assess_counterfactual(
        kind=CiboCounterfactualKind.ABSTAIN_VS_ACT,
        question_code="abstain-vs-act",
        status=CiboCounterfactualStatus.SUPPORTED,
        evidence_refs=(_ref("post-outcome"),),
        conclusion_code="act-wins",
        evidence_horizon=future_horizon,  # postdates assessment
        assessed_at=_NOW,
    )
    assert isinstance(result, Failure)


def test_counterfactual_value_equal_enum_laundering_rejected() -> None:
    class FakeStatus(str):
        pass

    with pytest.raises(CiboFunctionalValidationError):
        CiboCounterfactualAssessment(
            kind=CiboCounterfactualKind.ABSTAIN_VS_ACT,
            question_code="q",
            status=FakeStatus("supported"),  # type: ignore[arg-type]
            evidence_refs=(_ref("x"),),
            conclusion_code="y",
            evidence_horizon=_HORIZON,
            assessed_at=_NOW,
            authority=CiboFunctionalAuthority.OPINION,
        )


def test_counterfactual_deterministic_replay() -> None:
    def build() -> object:
        return assess_counterfactual(
            kind=CiboCounterfactualKind.ALTERNATE_TIMING,
            question_code="timing",
            status=CiboCounterfactualStatus.SUPPORTED,
            evidence_refs=(_ref("replay"),),
            conclusion_code="earlier-entry",
            evidence_horizon=_HORIZON,
            assessed_at=_NOW,
        )

    first = build()
    second = build()
    assert isinstance(first, Success) and isinstance(second, Success)
    assert first.value.logical_values() == second.value.logical_values()


# --- Attribution ---


def test_no_post_evidence_is_insufficient() -> None:
    result = attribute_intervention(
        intervention_id="intervention-alpha",
        intervention_version="v1",
        lineage=_lineage(),
        pre_intervention_evidence=(_ref("pre"),),
        prescribed_development=("replay",),
        prescribed_research=("ab",),
        post_intervention_evidence=(),
        causal_isolation_evidence=(),
        confounded=False,
        assessed_at=_NOW,
    )
    assert isinstance(result, Success)
    assert result.value.attribution_state is CiboAttributionState.INSUFFICIENT_EVIDENCE


def test_profitable_outcome_without_causal_isolation_is_unattributed() -> None:
    result = attribute_intervention(
        intervention_id="intervention-alpha",
        intervention_version="v1",
        lineage=_lineage(),
        pre_intervention_evidence=(_ref("pre"),),
        prescribed_development=(),
        prescribed_research=(),
        post_intervention_evidence=(_ref("profitable-outcome"),),
        causal_isolation_evidence=(),
        confounded=False,
        assessed_at=_NOW,
    )
    assert isinstance(result, Success)
    # profit alone is never proof of CIBO causation.
    assert result.value.attribution_state is CiboAttributionState.UNATTRIBUTED


def test_causal_isolation_evidence_yields_attributed() -> None:
    result = attribute_intervention(
        intervention_id="intervention-alpha",
        intervention_version="v1",
        lineage=_lineage(),
        pre_intervention_evidence=(_ref("pre"),),
        prescribed_development=(),
        prescribed_research=(),
        post_intervention_evidence=(_ref("outcome"),),
        causal_isolation_evidence=(_ref("ab-delta"),),
        confounded=False,
        assessed_at=_NOW,
    )
    assert isinstance(result, Success)
    assert result.value.attribution_state is CiboAttributionState.ATTRIBUTED


def test_confounded_yields_confounded() -> None:
    result = attribute_intervention(
        intervention_id="intervention-alpha",
        intervention_version="v1",
        lineage=_lineage(),
        pre_intervention_evidence=(_ref("pre"),),
        prescribed_development=(),
        prescribed_research=(),
        post_intervention_evidence=(_ref("outcome"),),
        causal_isolation_evidence=(_ref("ab-delta"),),
        confounded=True,
        assessed_at=_NOW,
    )
    assert isinstance(result, Success)
    assert result.value.attribution_state is CiboAttributionState.CONFOUNDED


def test_attribution_cannot_self_declare() -> None:
    # Direct construction of ATTRIBUTED without causal isolation is rejected.
    with pytest.raises(CiboFunctionalValidationError):
        CiboInterventionAttribution(
            intervention_id="intervention-alpha",
            intervention_version="v1",
            lineage=_lineage(),
            pre_intervention_evidence=(_ref("pre"),),
            prescribed_development=(),
            prescribed_research=(),
            post_intervention_evidence=(_ref("outcome"),),
            causal_isolation_evidence=(),
            confounded=False,
            attribution_state=CiboAttributionState.ATTRIBUTED,
            assessed_at=_NOW,
            authority=CiboFunctionalAuthority.OPINION,
        )


def test_attribution_exact_version_binding() -> None:
    result = attribute_intervention(
        intervention_id="intervention-beta",
        intervention_version="v7",
        lineage=_lineage(),
        pre_intervention_evidence=(_ref("pre"),),
        prescribed_development=(),
        prescribed_research=(),
        post_intervention_evidence=(_ref("outcome"),),
        causal_isolation_evidence=(_ref("ab"),),
        confounded=False,
        assessed_at=_NOW,
    )
    assert isinstance(result, Success)
    assert result.value.intervention_id == "intervention-beta"
    assert result.value.intervention_version == "v7"
    assert result.value.authority is CiboFunctionalAuthority.OPINION


def test_attribution_bool_is_not_int() -> None:
    result = attribute_intervention(
        intervention_id="intervention-alpha",
        intervention_version="v1",
        lineage=_lineage(),
        pre_intervention_evidence=(_ref("pre"),),
        prescribed_development=(),
        prescribed_research=(),
        post_intervention_evidence=(_ref("outcome"),),
        causal_isolation_evidence=(),
        confounded=1,  # type: ignore[arg-type]
        assessed_at=_NOW,
    )
    assert isinstance(result, Failure)


def test_attribution_deterministic_replay() -> None:
    def build() -> object:
        return attribute_intervention(
            intervention_id="intervention-alpha",
            intervention_version="v1",
            lineage=_lineage(),
            pre_intervention_evidence=(_ref("pre"),),
            prescribed_development=(),
            prescribed_research=(),
            post_intervention_evidence=(_ref("outcome"),),
            causal_isolation_evidence=(_ref("ab"),),
            confounded=False,
            assessed_at=_NOW,
        )

    first = build()
    second = build()
    assert isinstance(first, Success) and isinstance(second, Success)
    assert first.value.logical_values() == second.value.logical_values()


def test_no_secrets_in_attribution_logical_values() -> None:
    result = attribute_intervention(
        intervention_id="intervention-alpha",
        intervention_version="v1",
        lineage=_lineage(),
        pre_intervention_evidence=(_ref("pre"),),
        prescribed_development=(),
        prescribed_research=(),
        post_intervention_evidence=(_ref("outcome"),),
        causal_isolation_evidence=(_ref("ab"),),
        confounded=False,
        assessed_at=_NOW,
    )
    assert isinstance(result, Success)
    material = repr(result.value.logical_values())
    assert "token=" not in material
    assert "bearer " not in material
