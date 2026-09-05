from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from typing import cast

from _governed_evidence_fixtures import dependent_evidence

from qore.infrastructure.cibo.contracts import (
    CiboEvidenceStatus,
    CiboFunctionalError,
    CiboFunctionalEvidence,
    CiboFunctionalValidationError,
    CiboGovernedEvidenceKind,
)
from qore.infrastructure.cibo.decision_journal import (
    CiboDecisionEpisode,
    CiboDecisionJournal,
)
from qore.infrastructure.cibo.economic_intelligence import (
    CiboEconomicIntelligence,
    CiboEconomicStatus,
)
from qore.infrastructure.cibo.failure_intelligence import (
    CiboFailureClass,
    CiboFailureIntelligence,
)
from qore.infrastructure.cibo.outcome_journal import CiboOutcomeJournal, CiboOutcomeRecord
from qore.infrastructure.cibo_trader_capability_profile import (
    CiboEvidenceRef,
    CiboTraderConfigFingerprint,
)
from qore.infrastructure.research_evaluator_identity import (
    ResearchDecisionEvaluatorFamily,
    ResearchDecisionEvaluatorIdentity,
    ResearchDecisionEvaluatorSchemaVersion,
)
from qore.infrastructure.research_run import ResearchSoftwareRevision
from qore.kernel.result import Failure, Result, Success

_NOW = datetime(2026, 8, 9, 0, 0, tzinfo=UTC)
_ECONOMIC = CiboEconomicIntelligence()
_OUTCOME = CiboOutcomeJournal()
_FAILURE = CiboFailureIntelligence()
_DECISION = CiboDecisionJournal()


def _identity(suffix: str = "vt01") -> ResearchDecisionEvaluatorIdentity:
    return ResearchDecisionEvaluatorIdentity(
        family=ResearchDecisionEvaluatorFamily(f"virtual.trader.{suffix}"),
        schema_version=ResearchDecisionEvaluatorSchemaVersion("v1"),
        software_revision=ResearchSoftwareRevision("rev-1"),
    )


def _fingerprint(n: int = 1) -> CiboTraderConfigFingerprint:
    return CiboTraderConfigFingerprint(f"{n:064x}")


def _dependent_evidence() -> CiboFunctionalEvidence:
    return dependent_evidence(
        CiboGovernedEvidenceKind.ECONOMIC,
        evidence_refs=(CiboEvidenceRef("evidence:ref"),),
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


# --- CF-07: economic intelligence ---


def test_assess_dependent_evidence_rejects_fabricated_pnl() -> None:
    # Correction 003: non-empty metrics require SUFFICIENT (authority-rooted)
    # evidence; evidence-dependent backing cannot certify P&L and fails closed.
    result = _ECONOMIC.assess(
        metrics={"gross_pnl": Decimal("12.50"), "net_pnl": Decimal("9.00")},
        evidence=_dependent_evidence(),
        attribution_refs=(CiboEvidenceRef("evidence:attribution"),),
        assessed_at=_NOW,
    )
    assert isinstance(result, Failure)
    assert isinstance(result.error, CiboFunctionalValidationError)


def test_assess_insufficient_evidence_has_no_metrics() -> None:
    result = _ECONOMIC.assess(
        metrics={},
        evidence=_insufficient_evidence(),
        attribution_refs=(),
        assessed_at=_NOW,
    )
    assert isinstance(result, Success)
    assessment = result.value
    assert assessment.status is CiboEconomicStatus.INSUFFICIENT_EVIDENCE
    assert assessment.gross_pnl is None
    assert assessment.net_pnl is None
    assert assessment.expectancy is None
    assert assessment.drawdown is None
    assert assessment.costs is None
    assert assessment.risk_adjusted is None


def test_assess_rejects_fabricated_pnl_without_authority_root() -> None:
    result = _ECONOMIC.assess(
        metrics={"gross_pnl": Decimal("12.50")},
        evidence=_dependent_evidence(),
        attribution_refs=(CiboEvidenceRef("evidence:attribution"),),
        assessed_at=_NOW,
    )
    assert isinstance(result, Failure)
    assert isinstance(result.error, CiboFunctionalValidationError)


def test_assess_rejects_unknown_metric_code() -> None:
    result = _ECONOMIC.assess(
        metrics={"alpha_secret": Decimal("1.0")},
        evidence=_dependent_evidence(),
        attribution_refs=(CiboEvidenceRef("evidence:attribution"),),
        assessed_at=_NOW,
    )
    assert isinstance(result, Failure)
    assert isinstance(result.error, CiboFunctionalValidationError)


def test_assess_rejects_wrong_type_evidence() -> None:
    result = _ECONOMIC.assess(
        metrics={"gross_pnl": Decimal("1.0")},
        evidence=cast(CiboFunctionalEvidence, object()),
        attribution_refs=(CiboEvidenceRef("evidence:attribution"),),
        assessed_at=_NOW,
    )
    assert isinstance(result, Failure)
    assert isinstance(result.error, CiboFunctionalValidationError)


def test_assess_repeated_identical_input_equal_logical_values() -> None:
    left = _ECONOMIC.assess(
        metrics={},
        evidence=_dependent_evidence(),
        attribution_refs=(),
        assessed_at=_NOW,
    )
    right = _ECONOMIC.assess(
        metrics={},
        evidence=_dependent_evidence(),
        attribution_refs=(),
        assessed_at=_NOW,
    )
    assert isinstance(left, Success)
    assert isinstance(right, Success)
    assert left.value == right.value
    assert left.value.logical_values() == right.value.logical_values()


# --- CF-08: outcome journal ---


def _record(
    *,
    trader_identity: ResearchDecisionEvaluatorIdentity | None = None,
    demo_fill_refs: tuple[CiboEvidenceRef, ...] | None = None,
) -> Result[CiboOutcomeRecord, CiboFunctionalError]:
    return _OUTCOME.record(
        trader_identity=_identity() if trader_identity is None else trader_identity,
        config_fingerprint=_fingerprint(),
        instrument_code="eur.usd",
        regime_code="favorable",
        decision_refs=(CiboEvidenceRef("evidence:decision"),),
        mode_code="demo",
        action_code="entry",
        risk_decision_ref=None,
        demo_fill_refs=(
            (CiboEvidenceRef("evidence:fill"),) if demo_fill_refs is None else demo_fill_refs
        ),
        reconciliation_refs=(),
        gross_pnl=Decimal("10.00"),
        net_pnl=Decimal("8.00"),
        mfe=Decimal("15.00"),
        mae=Decimal("-3.00"),
        exposure=Decimal("1000.00"),
        stop_target_lifecycle_code="stop.lifecycle.v1",
        recorded_at=_NOW,
    )


def test_record_with_fills_and_pnl() -> None:
    result = _record()
    assert isinstance(result, Success)
    record = result.value
    assert record.gross_pnl == Decimal("10.00")
    assert record.net_pnl == Decimal("8.00")
    assert record.demo_fill_refs == (CiboEvidenceRef("evidence:fill"),)


def test_record_rejects_pnl_without_fills() -> None:
    result = _record(demo_fill_refs=())
    assert isinstance(result, Failure)
    assert isinstance(result.error, CiboFunctionalValidationError)


def test_record_rejects_wrong_type_identity() -> None:
    result = _record(
        trader_identity=cast(ResearchDecisionEvaluatorIdentity, "not-an-identity")
    )
    assert isinstance(result, Failure)
    assert isinstance(result.error, CiboFunctionalValidationError)


def test_record_repeated_identical_input_equal_logical_values() -> None:
    left = _record()
    right = _record()
    assert isinstance(left, Success)
    assert isinstance(right, Success)
    assert left.value == right.value
    assert left.value.logical_values() == right.value.logical_values()


# --- CF-09: failure intelligence ---


def test_diagnose_risk_containment_requires_authority_root() -> None:
    # Correction 003: a failure classification other than INSUFFICIENT_EVIDENCE
    # requires SUFFICIENT (authority-rooted) evidence, so dependent evidence fails.
    result = _FAILURE.diagnose(
        CiboFailureClass.RISK_CONTAINMENT,
        evidence=_dependent_evidence(),
        hypothesis_code="risk.containment.hypothesis",
        diagnosed_at=_NOW,
    )
    assert isinstance(result, Failure)
    assert isinstance(result.error, CiboFunctionalValidationError)


def test_diagnose_insufficient_with_dependent_evidence_succeeds() -> None:
    result = _FAILURE.diagnose(
        CiboFailureClass.INSUFFICIENT_EVIDENCE,
        evidence=_dependent_evidence(),
        hypothesis_code="insufficient.hypothesis",
        diagnosed_at=_NOW,
    )
    assert isinstance(result, Success)
    assert result.value.classification is CiboFailureClass.INSUFFICIENT_EVIDENCE


def test_diagnose_insufficient_with_insufficient_evidence_opinion() -> None:
    result = _FAILURE.diagnose(
        CiboFailureClass.INSUFFICIENT_EVIDENCE,
        evidence=_insufficient_evidence(),
        hypothesis_code="insufficient.hypothesis",
        diagnosed_at=_NOW,
    )
    assert isinstance(result, Success)
    assert result.value.classification is CiboFailureClass.INSUFFICIENT_EVIDENCE


# --- CF-17: decision journal ---


def test_record_decision_episode() -> None:
    result = _DECISION.record(
        episode_code="episode.001",
        world_refs=(CiboEvidenceRef("evidence:world"),),
        core_refs=(CiboEvidenceRef("evidence:core"),),
        hypotheses=("hypothesis.b", "hypothesis.a"),
        alternatives=("alternative.x",),
        uncertainty_code="uncertainty.low",
        consulted_specialists=("macro", "fx"),
        consulted_traders=(_identity("vt02"), _identity("vt01")),
        evidence_refs=(CiboEvidenceRef("evidence:decision"),),
        recommendation_code="recommendation.hold",
        decision_code=None,
        expected_result_code="expected.result.v1",
        risk_assumption_codes=("assumption.risk",),
        actual_result_code=None,
        counterfactual_code=None,
        lesson_codes=(),
        recorded_at=_NOW,
    )
    assert isinstance(result, Success)
    episode = result.value
    assert isinstance(episode, CiboDecisionEpisode)
    assert episode.hypotheses == ("hypothesis.a", "hypothesis.b")
    assert episode.consulted_traders[0].family.value == "virtual.trader.vt01"
    assert episode.consulted_traders[1].family.value == "virtual.trader.vt02"


def test_record_decision_rejects_wrong_type_trader() -> None:
    result = _DECISION.record(
        episode_code="episode.002",
        world_refs=(),
        core_refs=(),
        hypotheses=(),
        alternatives=(),
        uncertainty_code="uncertainty.low",
        consulted_specialists=(),
        consulted_traders=(cast(ResearchDecisionEvaluatorIdentity, "not-an-identity"),),
        evidence_refs=(),
        recommendation_code="recommendation.hold",
        decision_code=None,
        expected_result_code="expected.result.v1",
        risk_assumption_codes=(),
        actual_result_code=None,
        counterfactual_code=None,
        lesson_codes=(),
        recorded_at=_NOW,
    )
    assert isinstance(result, Failure)
    assert isinstance(result.error, CiboFunctionalValidationError)


def test_record_decision_rejects_duplicate_hypotheses() -> None:
    result = _DECISION.record(
        episode_code="episode.002b",
        world_refs=(),
        core_refs=(),
        hypotheses=("hypothesis.a", "hypothesis.a"),
        alternatives=(),
        uncertainty_code="uncertainty.low",
        consulted_specialists=(),
        consulted_traders=(),
        evidence_refs=(),
        recommendation_code="recommendation.hold",
        decision_code=None,
        expected_result_code="expected.result.v1",
        risk_assumption_codes=(),
        actual_result_code=None,
        counterfactual_code=None,
        lesson_codes=(),
        recorded_at=_NOW,
    )
    assert isinstance(result, Failure)
    assert isinstance(result.error, CiboFunctionalValidationError)


def test_decision_repeated_identical_input_equal_logical_values() -> None:
    def build() -> Result[CiboDecisionEpisode, CiboFunctionalError]:
        return _DECISION.record(
            episode_code="episode.003",
            world_refs=(CiboEvidenceRef("evidence:world"),),
            core_refs=(),
            hypotheses=("hypothesis.a",),
            alternatives=(),
            uncertainty_code="uncertainty.low",
            consulted_specialists=(),
            consulted_traders=(_identity(),),
            evidence_refs=(),
            recommendation_code="recommendation.hold",
            decision_code="decision.go",
            expected_result_code="expected.result.v1",
            risk_assumption_codes=(),
            actual_result_code=None,
            counterfactual_code=None,
            lesson_codes=(),
            recorded_at=_NOW,
        )

    left = build()
    right = build()
    assert isinstance(left, Success)
    assert isinstance(right, Success)
    assert left.value == right.value
    assert left.value.logical_values() == right.value.logical_values()


def test_economic_journal_logical_values_contain_no_secrets() -> None:
    result = _ECONOMIC.assess(
        metrics={},
        evidence=_dependent_evidence(),
        attribution_refs=(),
        assessed_at=_NOW,
    )
    assert isinstance(result, Success)
    projection = repr(result.value.logical_values())
    for secret in ("secret", "token", "password", "private_key", "bearer"):
        assert secret not in projection

    outcome = _record()
    assert isinstance(outcome, Success)
    outcome_projection = repr(outcome.value.logical_values())
    for secret in ("secret", "token", "password", "private_key", "bearer"):
        assert secret not in outcome_projection


def test_authority_surface_is_recommendation_or_opinion_only() -> None:
    diagnosis = _FAILURE.diagnose(
        CiboFailureClass.INSUFFICIENT_EVIDENCE,
        evidence=_insufficient_evidence(),
        hypothesis_code="insufficient.hypothesis",
        diagnosed_at=_NOW,
    )
    assert isinstance(diagnosis, Success)
    assert not hasattr(diagnosis.value, "execute")
    assert not hasattr(diagnosis.value, "place_order")
    assert not hasattr(diagnosis.value, "authorize_risk")
