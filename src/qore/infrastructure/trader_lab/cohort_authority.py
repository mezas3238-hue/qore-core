"""Governed authority completion for the first cTrader DEMO Trader cohort.

Inputs must already have completed the in-Lab chain through MONTE_CARLO with
real retained research/robustness evidence.  This module then runs the three
owning authorities in order:

RISK_REVIEW -> CIBO_REVIEW -> INDEPENDENT_VALIDATION

and materializes their verified references into the immutable Trader Lab
lifecycle.  No authority is skipped and no synthetic proof is produced inside
Trader Lab.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import NAMESPACE_URL, uuid5

from qore.infrastructure.cibo_trader_lab_authority import (
    issue_cibo_trader_lab_approval,
    review_trader_lab_candidate_cibo,
)
from qore.infrastructure.independent_trader_lab_validation import (
    issue_independent_trader_lab_approval,
    review_trader_lab_candidate_independently,
)
from qore.infrastructure.market_data import Instrument
from qore.infrastructure.research_performance_statistics import (
    ResearchPerformanceStatisticsSnapshot,
)
from qore.infrastructure.risk_trader_lab_authority import (
    RiskTraderLabPolicy,
    issue_risk_trader_lab_approval,
    review_trader_lab_candidate_risk,
)
from qore.infrastructure.trader_lab.candidate import TraderLabValidationError
from qore.infrastructure.trader_lab.cohort import (
    FIRST_DEMO_COHORT_CODES,
    FirstCohortDemoSelection,
    FirstCohortSelectionPolicy,
    FirstCohortTraderLabEntry,
    select_first_demo_trader,
)
from qore.infrastructure.trader_lab.lifecycle import (
    TraderLabLifecycle,
    TraderLabPromotionRequest,
    TraderLabState,
    apply_trader_lab_promotion,
    validate_trader_lab_lifecycle,
)
from qore.infrastructure.trader_lab.promotion import (
    TraderLabPromotionStatus,
    evaluate_demo_eligibility,
)
from qore.infrastructure.trader_lab.stage_evidence import (
    TraderLabEvidenceReference,
    TraderLabStage,
    TraderLabStageEvidenceId,
    build_trader_lab_stage_evidence,
)
from qore.infrastructure.traders.contracts import (
    DemoTradingConfigFingerprint,
    DemoTradingMethodologyFingerprint,
    DemoTradingMethodologyId,
    DemoTradingMethodologyVersion,
    DemoTradingTraderCode,
    DemoTradingTraderVersion,
)
from qore.kernel.errors import InfrastructureError
from qore.kernel.result import Failure, Result, Success


class FirstCohortAuthorityError(InfrastructureError):
    """Base error for first-cohort governed authority completion."""

    __slots__ = ()


class FirstCohortAuthorityValidationError(FirstCohortAuthorityError):
    """Authority completion input violates exact cohort invariants."""

    __slots__ = ()


class FirstCohortAuthorityBlockedError(FirstCohortAuthorityError):
    """A mandatory authority refused or failed to qualify the candidate."""

    __slots__ = ()


@dataclass(frozen=True, slots=True)
class FirstCohortAuthorityInput:
    """Exact post-MONTE_CARLO material for one first-cohort Trader."""

    lifecycle: TraderLabLifecycle
    performance: ResearchPerformanceStatisticsSnapshot
    economic_evidence: TraderLabEvidenceReference
    qualified_timeframes: tuple[str, ...]
    risk_policy: RiskTraderLabPolicy
    risk_reviewed_at: datetime
    cibo_reviewed_at: datetime
    independent_validated_at: datetime

    def __post_init__(self) -> None:
        if not isinstance(self.lifecycle, TraderLabLifecycle):
            raise FirstCohortAuthorityValidationError(
                "authority input lifecycle must be TraderLabLifecycle"
            )
        validate_trader_lab_lifecycle(self.lifecycle)
        if self.lifecycle.state is not TraderLabState.MONTE_CARLO_QUALIFIED:
            raise FirstCohortAuthorityValidationError(
                "authority input must start at MONTE_CARLO_QUALIFIED"
            )
        if not isinstance(self.performance, ResearchPerformanceStatisticsSnapshot):
            raise FirstCohortAuthorityValidationError(
                "authority input requires performance statistics"
            )
        self.performance.__post_init__()
        if self.performance.run != self.lifecycle.candidate.strategy_binding.run:
            raise FirstCohortAuthorityValidationError(
                "performance run must bind the exact candidate"
            )
        if not isinstance(self.economic_evidence, TraderLabEvidenceReference):
            raise FirstCohortAuthorityValidationError(
                "authority input requires economic evidence"
            )
        if type(self.qualified_timeframes) is not tuple or not self.qualified_timeframes:
            raise FirstCohortAuthorityValidationError(
                "authority input requires qualified timeframes"
            )
        if any(type(item) is not str or not item for item in self.qualified_timeframes):
            raise FirstCohortAuthorityValidationError(
                "qualified timeframes must be non-empty strings"
            )
        if not isinstance(self.risk_policy, RiskTraderLabPolicy):
            raise FirstCohortAuthorityValidationError(
                "authority input requires RiskTraderLabPolicy"
            )
        self.risk_policy.__post_init__()
        for field_name, value in (
            ("risk_reviewed_at", self.risk_reviewed_at),
            ("cibo_reviewed_at", self.cibo_reviewed_at),
            ("independent_validated_at", self.independent_validated_at),
        ):
            if (
                type(value) is not datetime
                or value.tzinfo is None
                or value.utcoffset() is None
            ):
                raise FirstCohortAuthorityValidationError(
                    f"{field_name} must be timezone-aware"
                )
        latest_prior = max(
            self.lifecycle.qualifications[-1].qualified_at,
            self.performance.observed_at,
        )
        if self.risk_reviewed_at < latest_prior:
            raise FirstCohortAuthorityValidationError(
                "Risk review cannot predate post-Monte-Carlo/performance evidence"
            )
        if self.cibo_reviewed_at < self.risk_reviewed_at:
            raise FirstCohortAuthorityValidationError(
                "CIBO review cannot predate Risk review"
            )
        if self.independent_validated_at < self.cibo_reviewed_at:
            raise FirstCohortAuthorityValidationError(
                "independent validation cannot predate CIBO review"
            )
        values = _manifest_values(self.lifecycle)
        if values["trader.code"] not in FIRST_DEMO_COHORT_CODES:
            raise FirstCohortAuthorityValidationError(
                "authority input candidate is not a first DEMO cohort Trader"
            )


def _manifest_values(lifecycle: TraderLabLifecycle) -> dict[str, str]:
    candidate = lifecycle.candidate
    wanted = {
        "trader.code",
        "trader.config_fingerprint",
        "trader.instrument",
        "trader.methodology_fingerprint",
        "trader.methodology_id",
        "trader.methodology_version",
    }
    values: dict[str, str] = {}
    for parameter in candidate.strategy_binding.manifest.parameters:
        if parameter.name not in wanted:
            continue
        if type(parameter.value) is not str:
            raise FirstCohortAuthorityValidationError(
                "first-cohort manifest trader bindings must be strings"
            )
        values[parameter.name] = parameter.value
    if set(values) != wanted:
        raise FirstCohortAuthorityValidationError(
            "first-cohort manifest is missing exact Trader bindings"
        )
    return values


def _promote_external_stage(
    lifecycle: TraderLabLifecycle,
    *,
    stage: TraderLabStage,
    reference: TraderLabEvidenceReference,
    produced_at: datetime,
) -> TraderLabLifecycle:
    candidate = lifecycle.candidate
    evidence_id = TraderLabStageEvidenceId(
        uuid5(
            NAMESPACE_URL,
            "qore:first-demo:external-stage:"
            f"{candidate.fingerprint.value}:{stage.value}:"
            f"{produced_at.astimezone(UTC).isoformat(timespec='microseconds')}",
        )
    )
    built = build_trader_lab_stage_evidence(
        evidence_id=evidence_id,
        stage=stage,
        candidate=candidate,
        source_reference=reference,
        produced_at=produced_at,
    )
    if isinstance(built, Failure):
        raise FirstCohortAuthorityBlockedError(
            f"{stage.value} stage evidence construction failed: {built.error}"
        )
    promoted = apply_trader_lab_promotion(
        lifecycle,
        TraderLabPromotionRequest(stage=stage, evidence=built.value),
    )
    if isinstance(promoted, Failure):
        raise FirstCohortAuthorityBlockedError(
            f"{stage.value} lifecycle promotion failed: {promoted.error}"
        )
    return promoted.value


def complete_first_cohort_authority_chain(
    authority_input: FirstCohortAuthorityInput,
) -> Result[FirstCohortTraderLabEntry, FirstCohortAuthorityError]:
    """Complete Risk, CIBO, and independent validation for one cohort candidate."""

    try:
        if not isinstance(authority_input, FirstCohortAuthorityInput):
            raise FirstCohortAuthorityValidationError(
                "authority_input must be FirstCohortAuthorityInput"
            )
        authority_input.__post_init__()
        lifecycle = authority_input.lifecycle

        risk_review = review_trader_lab_candidate_risk(
            lifecycle,
            authority_input.performance,
            policy=authority_input.risk_policy,
            reviewed_at=authority_input.risk_reviewed_at,
        )
        if isinstance(risk_review, Failure):
            raise FirstCohortAuthorityBlockedError(
                f"Risk review failed: {risk_review.error}"
            )
        risk_issuance = issue_risk_trader_lab_approval(risk_review.value)
        if isinstance(risk_issuance, Failure):
            raise FirstCohortAuthorityBlockedError(
                f"Risk issuance failed: {risk_issuance.error}"
            )
        lifecycle = _promote_external_stage(
            lifecycle,
            stage=TraderLabStage.RISK_REVIEW,
            reference=risk_issuance.value.reference,
            produced_at=authority_input.risk_reviewed_at,
        )

        cibo_review = review_trader_lab_candidate_cibo(
            lifecycle,
            economic_evidence=authority_input.economic_evidence,
            qualified_timeframes=authority_input.qualified_timeframes,
            reviewed_at=authority_input.cibo_reviewed_at,
        )
        if isinstance(cibo_review, Failure):
            raise FirstCohortAuthorityBlockedError(
                f"CIBO review failed: {cibo_review.error}"
            )
        cibo_issuance = issue_cibo_trader_lab_approval(
            lifecycle,
            cibo_review.value,
        )
        if isinstance(cibo_issuance, Failure):
            raise FirstCohortAuthorityBlockedError(
                f"CIBO issuance failed: {cibo_issuance.error}"
            )
        lifecycle = _promote_external_stage(
            lifecycle,
            stage=TraderLabStage.CIBO_REVIEW,
            reference=cibo_issuance.value.reference,
            produced_at=authority_input.cibo_reviewed_at,
        )

        independent_review = review_trader_lab_candidate_independently(
            lifecycle,
            economic_evidence=authority_input.economic_evidence,
            performance=authority_input.performance,
            validated_at=authority_input.independent_validated_at,
        )
        if isinstance(independent_review, Failure):
            raise FirstCohortAuthorityBlockedError(
                f"independent validation failed: {independent_review.error}"
            )
        independent_issuance = issue_independent_trader_lab_approval(
            independent_review.value
        )
        if isinstance(independent_issuance, Failure):
            raise FirstCohortAuthorityBlockedError(
                f"independent issuance failed: {independent_issuance.error}"
            )
        lifecycle = _promote_external_stage(
            lifecycle,
            stage=TraderLabStage.INDEPENDENT_VALIDATION,
            reference=independent_issuance.value.reference,
            produced_at=authority_input.independent_validated_at,
        )

        promotion = evaluate_demo_eligibility(
            lifecycle,
            economic_evidence=authority_input.economic_evidence,
        )
        if promotion.status is not TraderLabPromotionStatus.DEMO_ELIGIBLE:
            raise FirstCohortAuthorityBlockedError(
                "completed governed chain did not reach DEMO_ELIGIBLE"
            )

        values = _manifest_values(lifecycle)
        entry = FirstCohortTraderLabEntry(
            trader_code=DemoTradingTraderCode(values["trader.code"]),
            trader_version=DemoTradingTraderVersion(
                lifecycle.candidate.version.value
            ),
            config_fingerprint=DemoTradingConfigFingerprint(
                values["trader.config_fingerprint"]
            ),
            methodology_id=DemoTradingMethodologyId(
                values["trader.methodology_id"]
            ),
            methodology_version=DemoTradingMethodologyVersion(
                values["trader.methodology_version"]
            ),
            methodology_fingerprint=DemoTradingMethodologyFingerprint(
                values["trader.methodology_fingerprint"]
            ),
            instrument=Instrument(values["trader.instrument"]),
            lifecycle=lifecycle,
            economic_evidence=authority_input.economic_evidence,
            performance=authority_input.performance,
        )
        return Success(entry)
    except InfrastructureError as error:
        if isinstance(error, FirstCohortAuthorityError):
            return Failure(error)
        return Failure(FirstCohortAuthorityValidationError(str(error)))


def complete_and_select_first_demo_cohort(
    authority_inputs: tuple[FirstCohortAuthorityInput, ...],
    *,
    selection_policy: FirstCohortSelectionPolicy,
) -> Result[FirstCohortDemoSelection, FirstCohortAuthorityError]:
    """Complete all five target Traders and select one from authentic Lab results."""

    try:
        if type(authority_inputs) is not tuple or len(authority_inputs) != 5:
            raise FirstCohortAuthorityValidationError(
                "first DEMO authority cohort requires exactly five inputs"
            )
        codes = tuple(
            sorted(_manifest_values(item.lifecycle)["trader.code"] for item in authority_inputs)
        )
        if codes != FIRST_DEMO_COHORT_CODES:
            raise FirstCohortAuthorityValidationError(
                "authority cohort must contain VT-01, VT-08, VT-09, VT-17 and VT-31"
            )
        entries: list[FirstCohortTraderLabEntry] = []
        for item in authority_inputs:
            completed = complete_first_cohort_authority_chain(item)
            if isinstance(completed, Failure):
                raise FirstCohortAuthorityBlockedError(str(completed.error))
            entries.append(completed.value)
        selection = select_first_demo_trader(
            tuple(entries),
            policy=selection_policy,
        )
        if selection.selected is None:
            raise FirstCohortAuthorityBlockedError(
                "no first-cohort Trader is selectable after authentic Lab completion"
            )
        return Success(selection)
    except FirstCohortAuthorityError as error:
        return Failure(error)
