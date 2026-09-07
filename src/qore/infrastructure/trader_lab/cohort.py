"""Governed first-cohort admission and deterministic DEMO selection.

This module does not qualify Trader Lab stages and cannot mint governed evidence.
It consumes fully revalidated lifecycle/economic/performance evidence for exactly
VT-01, VT-08, VT-09, VT-17 and VT-31, applies an explicit economic policy, and
selects at most one already-``DEMO_ELIGIBLE`` Trader.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum

from qore.infrastructure.market_data import Instrument
from qore.infrastructure.research_performance_statistics import (
    ResearchPerformanceStatisticsSnapshot,
)
from qore.infrastructure.trader_lab.candidate import (
    TraderLabCandidateBinding,
    TraderLabValidationError,
)
from qore.infrastructure.trader_lab.lifecycle import (
    TraderLabLifecycle,
    validate_trader_lab_lifecycle,
)
from qore.infrastructure.trader_lab.promotion import (
    TraderLabPromotionDecision,
    TraderLabPromotionStatus,
    evaluate_demo_eligibility,
)
from qore.infrastructure.trader_lab.stage_evidence import (
    TraderLabEvidenceReference,
    validate_trader_lab_evidence_reference,
)
from qore.infrastructure.traders.contracts import (
    DemoTradingConfigFingerprint,
    DemoTradingMethodologyFingerprint,
    DemoTradingMethodologyId,
    DemoTradingMethodologyVersion,
    DemoTradingTraderCode,
    DemoTradingTraderVersion,
)

FIRST_DEMO_COHORT_CODES: tuple[str, ...] = (
    "vt-01",
    "vt-08",
    "vt-09",
    "vt-17",
    "vt-31",
)
_REQUIRED_STRATEGY_BINDING_PARAMETERS: tuple[str, ...] = (
    "trader.code",
    "trader.config_fingerprint",
    "trader.instrument",
    "trader.methodology_fingerprint",
    "trader.methodology_id",
    "trader.methodology_version",
)


class FirstCohortLabStatus(StrEnum):
    """Closed assessment outcomes for the first DEMO cohort."""

    SELECTABLE = "selectable"
    PROMOTION_BLOCKED = "promotion_blocked"
    ECONOMIC_POLICY_BLOCKED = "economic_policy_blocked"


@dataclass(frozen=True, slots=True)
class FirstCohortSelectionPolicy:
    """Explicit deployment policy; thresholds are specification data, not findings."""

    min_sample_size: int
    min_mean_return: Decimal
    min_win_rate: Decimal
    max_population_variance: Decimal

    def __post_init__(self) -> None:
        if type(self.min_sample_size) is not int or self.min_sample_size <= 0:
            raise TraderLabValidationError("min_sample_size must be a positive int")
        for name, value in (
            ("min_mean_return", self.min_mean_return),
            ("min_win_rate", self.min_win_rate),
            ("max_population_variance", self.max_population_variance),
        ):
            if type(value) is not Decimal or not value.is_finite():
                raise TraderLabValidationError(f"{name} must be a finite Decimal")
        if not Decimal("0") <= self.min_win_rate <= Decimal("1"):
            raise TraderLabValidationError("min_win_rate must be between zero and one")
        if self.max_population_variance < 0:
            raise TraderLabValidationError(
                "max_population_variance must be non-negative"
            )

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.min_sample_size,
            format(self.min_mean_return, "f"),
            format(self.min_win_rate, "f"),
            format(self.max_population_variance, "f"),
        )


@dataclass(frozen=True, slots=True)
class FirstCohortTraderLabEntry:
    """Exact Trader/instrument identity plus already-produced Lab/economic evidence."""

    trader_code: DemoTradingTraderCode
    trader_version: DemoTradingTraderVersion
    config_fingerprint: DemoTradingConfigFingerprint
    methodology_id: DemoTradingMethodologyId
    methodology_version: DemoTradingMethodologyVersion
    methodology_fingerprint: DemoTradingMethodologyFingerprint
    instrument: Instrument
    lifecycle: TraderLabLifecycle
    economic_evidence: TraderLabEvidenceReference
    performance: ResearchPerformanceStatisticsSnapshot

    def __post_init__(self) -> None:
        if type(self.trader_code) is not DemoTradingTraderCode:
            raise TraderLabValidationError("trader_code must be DemoTradingTraderCode")
        if self.trader_code.value not in FIRST_DEMO_COHORT_CODES:
            raise TraderLabValidationError("Trader is not a member of the first DEMO cohort")
        if type(self.trader_version) is not DemoTradingTraderVersion:
            raise TraderLabValidationError("trader_version must be DemoTradingTraderVersion")
        if type(self.config_fingerprint) is not DemoTradingConfigFingerprint:
            raise TraderLabValidationError(
                "config_fingerprint must be DemoTradingConfigFingerprint"
            )
        if type(self.methodology_id) is not DemoTradingMethodologyId:
            raise TraderLabValidationError("methodology_id must be DemoTradingMethodologyId")
        if type(self.methodology_version) is not DemoTradingMethodologyVersion:
            raise TraderLabValidationError(
                "methodology_version must be DemoTradingMethodologyVersion"
            )
        if type(self.methodology_fingerprint) is not DemoTradingMethodologyFingerprint:
            raise TraderLabValidationError(
                "methodology_fingerprint must be DemoTradingMethodologyFingerprint"
            )
        if type(self.instrument) is not Instrument:
            raise TraderLabValidationError("instrument must be canonical market-data Instrument")
        self.instrument.__post_init__()
        if not isinstance(self.lifecycle, TraderLabLifecycle):
            raise TraderLabValidationError("lifecycle must be TraderLabLifecycle")
        validate_trader_lab_lifecycle(self.lifecycle)
        validate_trader_lab_evidence_reference(self.economic_evidence)
        if not isinstance(self.performance, ResearchPerformanceStatisticsSnapshot):
            raise TraderLabValidationError(
                "performance must be ResearchPerformanceStatisticsSnapshot"
            )
        # Re-enter the performance trust boundary. A frozen value that was
        # reflectively modified must not remain selectable.
        self.performance.__post_init__()
        candidate = self.lifecycle.candidate
        if candidate.version.value != self.trader_version.value:
            raise TraderLabValidationError(
                "Lab candidate version must match the exact Trader version"
            )
        if self.performance.run != candidate.strategy_binding.run:
            raise TraderLabValidationError(
                "performance run must match the candidate research run"
            )
        if (
            self.economic_evidence.strategy_binding_fingerprint
            != candidate.strategy_binding.binding_fingerprint.value
        ):
            raise TraderLabValidationError(
                "economic evidence must match the candidate strategy lineage"
            )
        self._validate_strategy_manifest(candidate)

    def _validate_strategy_manifest(self, candidate: TraderLabCandidateBinding) -> None:
        parameters = candidate.strategy_binding.manifest.parameters
        values: dict[str, str] = {}
        for parameter in parameters:
            if parameter.name in _REQUIRED_STRATEGY_BINDING_PARAMETERS:
                if type(parameter.value) is not str:
                    raise TraderLabValidationError(
                        "first-cohort Trader binding parameters must be strings"
                    )
                values[parameter.name] = parameter.value
        if tuple(sorted(values)) != _REQUIRED_STRATEGY_BINDING_PARAMETERS:
            raise TraderLabValidationError(
                "strategy freeze is missing exact first-cohort Trader/instrument binding parameters"
            )
        expected = {
            "trader.code": self.trader_code.value,
            "trader.config_fingerprint": self.config_fingerprint.value,
            "trader.instrument": self.instrument.symbol,
            "trader.methodology_fingerprint": self.methodology_fingerprint.value,
            "trader.methodology_id": self.methodology_id.value,
            "trader.methodology_version": self.methodology_version.value,
        }
        if values != expected:
            raise TraderLabValidationError(
                "strategy freeze Trader identity/methodology/instrument binding does not match entry"
            )

    @property
    def candidate(self) -> TraderLabCandidateBinding:
        return self.lifecycle.candidate

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.trader_code.logical_values(),
            self.trader_version.logical_values(),
            self.config_fingerprint.logical_values(),
            self.methodology_id.logical_values(),
            self.methodology_version.logical_values(),
            self.methodology_fingerprint.logical_values(),
            self.instrument.symbol,
            self.lifecycle.logical_values(),
            self.economic_evidence.logical_values(),
            self.performance.logical_values(),
        )


@dataclass(frozen=True, slots=True)
class FirstCohortLabAssessment:
    entry: FirstCohortTraderLabEntry
    promotion: TraderLabPromotionDecision
    status: FirstCohortLabStatus
    reasons: tuple[str, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.entry, FirstCohortTraderLabEntry):
            raise TraderLabValidationError("assessment entry must be FirstCohortTraderLabEntry")
        if not isinstance(self.promotion, TraderLabPromotionDecision):
            raise TraderLabValidationError(
                "assessment promotion must be TraderLabPromotionDecision"
            )
        if self.promotion.candidate != self.entry.candidate:
            raise TraderLabValidationError(
                "assessment promotion must bind the exact candidate"
            )
        if type(self.status) is not FirstCohortLabStatus:
            raise TraderLabValidationError("assessment status must be FirstCohortLabStatus")
        if type(self.reasons) is not tuple or any(type(item) is not str for item in self.reasons):
            raise TraderLabValidationError("assessment reasons must be an immutable str tuple")


@dataclass(frozen=True, slots=True)
class FirstCohortDemoSelection:
    """Complete five-Trader Lab result with at most one selected DEMO candidate."""

    policy: FirstCohortSelectionPolicy
    assessments: tuple[FirstCohortLabAssessment, ...]
    selected: FirstCohortTraderLabEntry | None

    def __post_init__(self) -> None:
        if not isinstance(self.policy, FirstCohortSelectionPolicy):
            raise TraderLabValidationError("policy must be FirstCohortSelectionPolicy")
        if type(self.assessments) is not tuple or len(self.assessments) != 5:
            raise TraderLabValidationError("first cohort must contain exactly five assessments")
        if any(not isinstance(item, FirstCohortLabAssessment) for item in self.assessments):
            raise TraderLabValidationError(
                "assessments must contain FirstCohortLabAssessment values"
            )
        codes = tuple(item.entry.trader_code.value for item in self.assessments)
        if tuple(sorted(codes)) != FIRST_DEMO_COHORT_CODES:
            raise TraderLabValidationError(
                "first cohort must contain VT-01, VT-08, VT-09, VT-17 and VT-31 exactly once"
            )
        if self.selected is not None:
            selectable = tuple(
                item.entry
                for item in self.assessments
                if item.status is FirstCohortLabStatus.SELECTABLE
            )
            if self.selected not in selectable:
                raise TraderLabValidationError(
                    "selected Trader must be a selectable assessed cohort member"
                )

    @property
    def selectable(self) -> tuple[FirstCohortTraderLabEntry, ...]:
        return tuple(
            item.entry
            for item in self.assessments
            if item.status is FirstCohortLabStatus.SELECTABLE
        )


def _economic_policy_reasons(
    entry: FirstCohortTraderLabEntry,
    policy: FirstCohortSelectionPolicy,
) -> tuple[str, ...]:
    performance = entry.performance
    reasons: list[str] = []
    if performance.sample_size < policy.min_sample_size:
        reasons.append("sample_size_below_policy")
    if performance.mean_return < policy.min_mean_return:
        reasons.append("mean_return_below_policy")
    if performance.win_rate < policy.min_win_rate:
        reasons.append("win_rate_below_policy")
    if performance.population_variance > policy.max_population_variance:
        reasons.append("population_variance_above_policy")
    return tuple(reasons)


def assess_first_cohort_entry(
    entry: FirstCohortTraderLabEntry,
    policy: FirstCohortSelectionPolicy,
) -> FirstCohortLabAssessment:
    """Revalidate one candidate and apply Lab promotion plus explicit economics."""

    if not isinstance(entry, FirstCohortTraderLabEntry):
        raise TraderLabValidationError("entry must be FirstCohortTraderLabEntry")
    if not isinstance(policy, FirstCohortSelectionPolicy):
        raise TraderLabValidationError("policy must be FirstCohortSelectionPolicy")
    entry.__post_init__()
    promotion = evaluate_demo_eligibility(
        entry.lifecycle,
        economic_evidence=entry.economic_evidence,
    )
    if promotion.status is not TraderLabPromotionStatus.DEMO_ELIGIBLE:
        return FirstCohortLabAssessment(
            entry=entry,
            promotion=promotion,
            status=FirstCohortLabStatus.PROMOTION_BLOCKED,
            reasons=promotion.reasons,
        )
    economic_reasons = _economic_policy_reasons(entry, policy)
    if economic_reasons:
        return FirstCohortLabAssessment(
            entry=entry,
            promotion=promotion,
            status=FirstCohortLabStatus.ECONOMIC_POLICY_BLOCKED,
            reasons=economic_reasons,
        )
    return FirstCohortLabAssessment(
        entry=entry,
        promotion=promotion,
        status=FirstCohortLabStatus.SELECTABLE,
        reasons=(),
    )


def select_first_demo_trader(
    entries: tuple[FirstCohortTraderLabEntry, ...],
    *,
    policy: FirstCohortSelectionPolicy,
) -> FirstCohortDemoSelection:
    """Assess exactly five Traders and select one deterministic eligible winner.

    Ranking is lexicographic and evidence-only: higher mean return, then higher
    win rate, then lower population variance, then larger sample size. Trader code
    is the deterministic final tie-break and never makes an ineligible Trader
    selectable.
    """

    if type(entries) is not tuple or len(entries) != 5:
        raise TraderLabValidationError("first cohort requires exactly five entries")
    if any(not isinstance(item, FirstCohortTraderLabEntry) for item in entries):
        raise TraderLabValidationError(
            "first cohort entries must be FirstCohortTraderLabEntry values"
        )
    codes = tuple(sorted(item.trader_code.value for item in entries))
    if codes != FIRST_DEMO_COHORT_CODES:
        raise TraderLabValidationError(
            "first cohort must contain VT-01, VT-08, VT-09, VT-17 and VT-31 exactly once"
        )
    ordered_entries = tuple(sorted(entries, key=lambda item: item.trader_code.value))
    assessments = tuple(assess_first_cohort_entry(item, policy) for item in ordered_entries)
    selectable = [
        item.entry
        for item in assessments
        if item.status is FirstCohortLabStatus.SELECTABLE
    ]
    selected = None
    if selectable:
        selectable.sort(
            key=lambda item: (
                -item.performance.mean_return,
                -item.performance.win_rate,
                item.performance.population_variance,
                -item.performance.sample_size,
                item.trader_code.value,
            )
        )
        selected = selectable[0]
    return FirstCohortDemoSelection(
        policy=policy,
        assessments=assessments,
        selected=selected,
    )