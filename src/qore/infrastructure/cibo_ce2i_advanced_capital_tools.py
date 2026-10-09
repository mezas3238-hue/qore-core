"""Executable fail-closed engines for the advanced CE2I toolbox.

This module implements the seven CE2I tools that were previously architecture-only:
T02 Structural Leverage, T03 Margin Efficiency, T04 Risk Efficiency,
T08 Portfolio Netting, T10 Capital Velocity, T16 Hedged Exposure / Risk Transfer,
and T17 Convex / Limited-Downside Exposure.

The engines are deterministic, causal, research-only, and broker-mutation free.
Missing or stale evidence never becomes permission to deploy capital.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import ROUND_FLOOR, Decimal
from enum import StrEnum

from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
    TraderOpportunityEnvelope,
)


class AdvancedToolDisposition(StrEnum):
    APPLIED = "APPLIED"
    ABSTAIN = "ABSTAIN"
    FAIL_CLOSED = "FAIL_CLOSED"


@dataclass(frozen=True, slots=True)
class AdvancedToolDecision:
    tool_code: str
    disposition: AdvancedToolDisposition
    reason: str
    selected_id: str | None = None
    approved_volume: Decimal = Decimal(0)
    released_capacity_usd: Decimal = Decimal(0)
    target_stop_risk_usd: Decimal | None = None
    target_margin_usd: Decimal | None = None
    score: Decimal | None = None

    def __post_init__(self) -> None:
        if self.tool_code not in {"T02", "T03", "T04", "T08", "T10", "T16", "T17"}:
            raise CiboCapitalManagementError("unsupported advanced CE2I tool code")
        if type(self.disposition) is not AdvancedToolDisposition:
            raise CiboCapitalManagementError(
                "advanced tool disposition must use canonical enum"
            )
        if not self.reason:
            raise CiboCapitalManagementError("advanced tool reason required")
        _nonnegative(self.approved_volume, "approved_volume")
        _nonnegative(self.released_capacity_usd, "released_capacity_usd")
        for name in ("target_stop_risk_usd", "target_margin_usd"):
            value = getattr(self, name)
            if value is not None:
                _nonnegative(value, name)
        if self.score is not None:
            _finite(self.score, "score")
        if self.disposition is AdvancedToolDisposition.APPLIED and self.selected_id is None:
            raise CiboCapitalManagementError(
                "applied advanced tool decision requires selected_id"
            )
        if self.disposition is not AdvancedToolDisposition.APPLIED and (
            self.approved_volume != 0
            or self.released_capacity_usd != 0
            or self.target_stop_risk_usd is not None
            or self.target_margin_usd is not None
        ):
            raise CiboCapitalManagementError(
                "non-applied advanced tool decision cannot authorize capacity"
            )


@dataclass(frozen=True, slots=True)
class StructuralLeverageEvidence:
    evidence_id: str
    structural_invalidation_id: str
    observed_at: datetime
    sample_size: int
    baseline_stop_rate: Decimal
    candidate_stop_rate: Decimal
    baseline_tail_loss_r: Decimal
    candidate_tail_loss_r: Decimal
    released_risk_capacity_usd: Decimal
    protected_capacity_usd: Decimal
    evidence_oos: bool
    structural_stop_verified: bool
    stop_geometry_unchanged: bool

    def __post_init__(self) -> None:
        _id(self.evidence_id, "evidence_id")
        _id(self.structural_invalidation_id, "structural_invalidation_id")
        _aware(self.observed_at, "observed_at")
        _positive_int(self.sample_size, "sample_size")
        for name in ("baseline_stop_rate", "candidate_stop_rate"):
            _fraction(getattr(self, name), name)
        for name in ("baseline_tail_loss_r", "candidate_tail_loss_r"):
            _nonnegative(getattr(self, name), name)
        for name in ("released_risk_capacity_usd", "protected_capacity_usd"):
            _nonnegative(getattr(self, name), name)
        for name in (
            "evidence_oos",
            "structural_stop_verified",
            "stop_geometry_unchanged",
        ):
            if type(getattr(self, name)) is not bool:
                raise CiboCapitalManagementError(f"{name} must be bool")


def evaluate_structural_leverage(
    *,
    opportunity: TraderOpportunityEnvelope,
    evidence: StructuralLeverageEvidence,
    current_volume: Decimal,
    maximum_additional_volume: Decimal,
    minimum_oos_sample: int = 30,
) -> AdvancedToolDecision:
    if not isinstance(opportunity, TraderOpportunityEnvelope):
        raise CiboCapitalManagementError("opportunity must be TraderOpportunityEnvelope")
    if not isinstance(evidence, StructuralLeverageEvidence):
        raise CiboCapitalManagementError(
            "evidence must be StructuralLeverageEvidence"
        )
    _nonnegative(current_volume, "current_volume")
    _nonnegative(maximum_additional_volume, "maximum_additional_volume")
    _positive_int(minimum_oos_sample, "minimum_oos_sample")
    if not evidence.evidence_oos:
        return _fail("T02", "structural leverage requires out-of-sample stop evidence")
    if not evidence.structural_stop_verified or not evidence.stop_geometry_unchanged:
        return _fail("T02", "structural invalidation is not verified unchanged")
    if evidence.sample_size < minimum_oos_sample:
        return _fail("T02", "out-of-sample stop evidence is insufficient")
    if evidence.candidate_stop_rate > evidence.baseline_stop_rate:
        return _abstain("T02", "structural precision does not improve stop incidence")
    if evidence.candidate_tail_loss_r > evidence.baseline_tail_loss_r:
        return _abstain("T02", "structural precision worsens tail loss")
    capacity = evidence.released_risk_capacity_usd + evidence.protected_capacity_usd
    if capacity <= 0 or maximum_additional_volume <= 0:
        return _abstain("T02", "no proven non-base risk capacity available")
    by_risk = capacity / opportunity.stop_loss_per_volume
    raw_additional = min(
        by_risk,
        maximum_additional_volume,
        max(Decimal(0), opportunity.maximum_volume - current_volume),
    )
    additional = _floor_step(raw_additional, opportunity.volume_step)
    if additional <= 0:
        return _abstain("T02", "proven capacity cannot express one provider volume step")
    return AdvancedToolDecision(
        tool_code="T02",
        disposition=AdvancedToolDisposition.APPLIED,
        selected_id=evidence.structural_invalidation_id,
        approved_volume=current_volume + additional,
        target_stop_risk_usd=(
            opportunity.stop_loss_per_volume * (current_volume + additional)
        ),
        reason="verified OOS structural precision supports bounded extra exposure",
    )


@dataclass(frozen=True, slots=True)
class MarginExpression:
    expression_id: str
    normalized_exposure: Decimal
    stop_risk_usd: Decimal
    margin_usd: Decimal
    all_in_cost_usd: Decimal
    executable: bool
    economics_verified: bool

    def __post_init__(self) -> None:
        _id(self.expression_id, "expression_id")
        _positive(self.normalized_exposure, "normalized_exposure")
        for name in ("stop_risk_usd", "margin_usd", "all_in_cost_usd"):
            _nonnegative(getattr(self, name), name)
        for name in ("executable", "economics_verified"):
            if type(getattr(self, name)) is not bool:
                raise CiboCapitalManagementError(f"{name} must be bool")


@dataclass(frozen=True, slots=True)
class MarginEfficiencyEvidence:
    evidence_id: str
    observed_at: datetime
    baseline_expression_id: str
    expressions: tuple[MarginExpression, ...]
    max_exposure_drift_fraction: Decimal = Decimal("0.001")
    fresh_oos_utility_demonstrated: bool = False
    policy_authorized: bool = False

    def __post_init__(self) -> None:
        _id(self.evidence_id, "evidence_id")
        _id(self.baseline_expression_id, "baseline_expression_id")
        _aware(self.observed_at, "observed_at")
        if not self.expressions:
            raise CiboCapitalManagementError("margin expressions are required")
        _fraction(self.max_exposure_drift_fraction, "max_exposure_drift_fraction")
        ids = tuple(item.expression_id for item in self.expressions)
        if len(ids) != len(set(ids)):
            raise CiboCapitalManagementError("margin expression ids must be unique")
        if self.baseline_expression_id not in ids:
            raise CiboCapitalManagementError("baseline margin expression is missing")
        for name in ("fresh_oos_utility_demonstrated", "policy_authorized"):
            if type(getattr(self, name)) is not bool:
                raise CiboCapitalManagementError(f"{name} must be bool")
        if self.policy_authorized and not self.fresh_oos_utility_demonstrated:
            raise CiboCapitalManagementError(
                "T03 policy authorization requires fresh OOS utility"
            )


def evaluate_margin_efficiency(
    evidence: MarginEfficiencyEvidence,
) -> AdvancedToolDecision:
    if not isinstance(evidence, MarginEfficiencyEvidence):
        raise CiboCapitalManagementError(
            "evidence must be MarginEfficiencyEvidence"
        )
    if len(evidence.expressions) == 1:
        return _abstain(
            "T03",
            "NO_ALTERNATIVE_EQUIVALENT_EXPRESSION",
        )
    if not evidence.fresh_oos_utility_demonstrated:
        return _fail("T03", "T03 fresh OOS utility is not demonstrated")
    if not evidence.policy_authorized:
        return _fail("T03", "T03 policy is not authorized")
    baseline = next(
        item
        for item in evidence.expressions
        if item.expression_id == evidence.baseline_expression_id
    )
    if not baseline.economics_verified or not baseline.executable:
        return _fail("T03", "baseline expression economics are not executable/verified")
    candidates: list[MarginExpression] = []
    for item in evidence.expressions:
        if item.expression_id == baseline.expression_id:
            continue
        if not item.executable or not item.economics_verified:
            continue
        drift = abs(item.normalized_exposure - baseline.normalized_exposure) / (
            baseline.normalized_exposure
        )
        if drift > evidence.max_exposure_drift_fraction:
            continue
        if item.stop_risk_usd > baseline.stop_risk_usd:
            continue
        if item.all_in_cost_usd > baseline.all_in_cost_usd:
            continue
        if item.margin_usd >= baseline.margin_usd:
            continue
        candidates.append(item)
    if not candidates:
        return _abstain("T03", "NO_ELIGIBLE_EQUIVALENT_EXPRESSION")
    selected = min(
        candidates,
        key=lambda item: (
            item.margin_usd,
            item.all_in_cost_usd,
            item.stop_risk_usd,
            item.expression_id,
        ),
    )
    released = baseline.margin_usd - selected.margin_usd
    return AdvancedToolDecision(
        tool_code="T03",
        disposition=AdvancedToolDisposition.APPLIED,
        selected_id=selected.expression_id,
        released_capacity_usd=released,
        target_margin_usd=selected.margin_usd,
        score=(baseline.margin_usd / selected.margin_usd)
        if selected.margin_usd > 0
        else None,
        reason="economically equivalent verified expression reduces margin without more risk/cost",
    )


@dataclass(frozen=True, slots=True)
class RiskEfficiencyCandidate:
    candidate_id: str
    expected_net_output_usd: Decimal
    true_stop_risk_usd: Decimal
    p95_drawdown_usd: Decimal
    tail_loss_usd: Decimal
    margin_usd: Decimal
    sample_size: int
    evidence_oos: bool

    def __post_init__(self) -> None:
        _id(self.candidate_id, "candidate_id")
        _finite(self.expected_net_output_usd, "expected_net_output_usd")
        for name in (
            "true_stop_risk_usd",
            "p95_drawdown_usd",
            "tail_loss_usd",
            "margin_usd",
        ):
            _positive(getattr(self, name), name)
        _positive_int(self.sample_size, "sample_size")
        if type(self.evidence_oos) is not bool:
            raise CiboCapitalManagementError("evidence_oos must be bool")


@dataclass(frozen=True, slots=True)
class RiskEfficiencyEvidence:
    evidence_id: str
    observed_at: datetime
    baseline_candidate_id: str
    candidates: tuple[RiskEfficiencyCandidate, ...]
    minimum_oos_sample: int = 30

    def __post_init__(self) -> None:
        _id(self.evidence_id, "evidence_id")
        _id(self.baseline_candidate_id, "baseline_candidate_id")
        _aware(self.observed_at, "observed_at")
        _positive_int(self.minimum_oos_sample, "minimum_oos_sample")
        if not self.candidates:
            raise CiboCapitalManagementError("risk candidates are required")
        ids = tuple(item.candidate_id for item in self.candidates)
        if len(ids) != len(set(ids)):
            raise CiboCapitalManagementError("risk candidate ids must be unique")
        if self.baseline_candidate_id not in ids:
            raise CiboCapitalManagementError("risk efficiency baseline is missing")


def evaluate_risk_efficiency(
    evidence: RiskEfficiencyEvidence,
) -> AdvancedToolDecision:
    if not isinstance(evidence, RiskEfficiencyEvidence):
        raise CiboCapitalManagementError(
            "evidence must be RiskEfficiencyEvidence"
        )
    baseline = next(
        item
        for item in evidence.candidates
        if item.candidate_id == evidence.baseline_candidate_id
    )
    if len(evidence.candidates) == 1:
        return _abstain("T04", "NO_ALTERNATIVE_RISK_POLICY")
    if not baseline.evidence_oos or baseline.sample_size < evidence.minimum_oos_sample:
        return _fail("T04", "baseline risk-efficiency evidence is not sufficiently OOS")
    eligible = tuple(
        item
        for item in evidence.candidates
        if item.evidence_oos
        and item.sample_size >= evidence.minimum_oos_sample
        and item.expected_net_output_usd > 0
        and item.p95_drawdown_usd <= baseline.p95_drawdown_usd
        and item.tail_loss_usd <= baseline.tail_loss_usd
    )
    if not eligible:
        return _abstain("T04", "no OOS candidate passes drawdown/tail gates")
    selected = max(
        eligible,
        key=lambda item: (
            item.expected_net_output_usd / item.true_stop_risk_usd,
            item.expected_net_output_usd,
            -item.true_stop_risk_usd,
            item.candidate_id,
        ),
    )
    score = selected.expected_net_output_usd / selected.true_stop_risk_usd
    baseline_score = baseline.expected_net_output_usd / baseline.true_stop_risk_usd
    if score <= baseline_score:
        return _abstain("T04", "risk efficiency does not strictly improve baseline")
    return AdvancedToolDecision(
        tool_code="T04",
        disposition=AdvancedToolDisposition.APPLIED,
        selected_id=selected.candidate_id,
        target_stop_risk_usd=selected.true_stop_risk_usd,
        target_margin_usd=selected.margin_usd,
        score=score,
        reason="OOS output per true stop-risk strictly improves without worse tail/DD",
    )


@dataclass(frozen=True, slots=True)
class FactorExposure:
    position_id: str
    factor_id: str
    signed_risk_usd: Decimal

    def __post_init__(self) -> None:
        _id(self.position_id, "position_id")
        _id(self.factor_id, "factor_id")
        _finite(self.signed_risk_usd, "signed_risk_usd")


@dataclass(frozen=True, slots=True)
class PortfolioNettingEvidence:
    evidence_id: str
    observed_at: datetime
    exposures: tuple[FactorExposure, ...]
    correlation_state_id: str
    correlation_stable: bool
    factor_map_verified: bool
    risk_mapping_evidence_id: str | None = None
    correlation_evidence_id: str | None = None
    netting_utility_evidence_id: str | None = None
    risk_mapping_verified: bool = False
    correlation_oos: bool = False
    correlation_sample_size: int = 0
    correlation_stability_folds: int = 0
    netting_utility_oos: bool = False
    netting_utility_sample_size: int = 0
    exact_instrument_identity_verified: bool = False
    exact_instrument_evidence_id: str | None = None
    minimum_correlation_sample: int = 30
    minimum_correlation_folds: int = 4
    minimum_netting_utility_sample: int = 30
    maximum_credit_fraction: Decimal = Decimal("0.50")

    def __post_init__(self) -> None:
        _id(self.evidence_id, "evidence_id")
        _id(self.correlation_state_id, "correlation_state_id")
        _aware(self.observed_at, "observed_at")
        if not self.exposures:
            raise CiboCapitalManagementError("portfolio exposures are required")
        for name in (
            "correlation_stable",
            "factor_map_verified",
            "risk_mapping_verified",
            "correlation_oos",
            "netting_utility_oos",
            "exact_instrument_identity_verified",
        ):
            if type(getattr(self, name)) is not bool:
                raise CiboCapitalManagementError(f"{name} must be bool")
        for name in (
            "correlation_sample_size",
            "correlation_stability_folds",
            "netting_utility_sample_size",
        ):
            value = getattr(self, name)
            if (
                not isinstance(value, int)
                or isinstance(value, bool)
                or value < 0
            ):
                raise CiboCapitalManagementError(
                    f"{name} must be non-negative int"
                )
        for name in (
            "minimum_correlation_sample",
            "minimum_correlation_folds",
            "minimum_netting_utility_sample",
        ):
            _positive_int(getattr(self, name), name)
        for flag, evidence_name in (
            ("risk_mapping_verified", "risk_mapping_evidence_id"),
            ("correlation_oos", "correlation_evidence_id"),
            ("netting_utility_oos", "netting_utility_evidence_id"),
            (
                "exact_instrument_identity_verified",
                "exact_instrument_evidence_id",
            ),
        ):
            evidence_id = getattr(self, evidence_name)
            if evidence_id is not None:
                _id(evidence_id, evidence_name)
            if getattr(self, flag) and evidence_id is None:
                raise CiboCapitalManagementError(
                    f"{flag} requires {evidence_name}"
                )
        _fraction(self.maximum_credit_fraction, "maximum_credit_fraction")


def evaluate_portfolio_netting(
    evidence: PortfolioNettingEvidence,
) -> AdvancedToolDecision:
    if not isinstance(evidence, PortfolioNettingEvidence):
        raise CiboCapitalManagementError(
            "evidence must be PortfolioNettingEvidence"
        )
    by_factor_signs: dict[str, set[int]] = {}
    for item in evidence.exposures:
        if item.signed_risk_usd == 0:
            continue
        by_factor_signs.setdefault(item.factor_id, set()).add(
            1 if item.signed_risk_usd > 0 else -1
        )
    offset_factors = tuple(
        factor_id
        for factor_id, signs in by_factor_signs.items()
        if len(signs) > 1
    )
    if not offset_factors:
        return _abstain("T08", "NO_POTENTIAL_FACTOR_OFFSET")
    exact_instrument_offset = (
        evidence.exact_instrument_identity_verified
        and evidence.exact_instrument_evidence_id is not None
        and all(
            factor_id.startswith("symbol:")
            for factor_id in offset_factors
        )
    )
    if exact_instrument_offset:
        if (
            not evidence.factor_map_verified
            or not evidence.risk_mapping_verified
            or evidence.risk_mapping_evidence_id is None
        ):
            return _fail(
                "T08",
                "exact-instrument netting requires verified symbol/risk mapping",
            )
        gross = sum(
            (abs(item.signed_risk_usd) for item in evidence.exposures),
            Decimal(0),
        )
        by_factor: dict[str, Decimal] = {}
        for item in evidence.exposures:
            by_factor[item.factor_id] = (
                by_factor.get(item.factor_id, Decimal(0))
                + item.signed_risk_usd
            )
        net = sum((abs(value) for value in by_factor.values()), Decimal(0))
        if gross <= 0 or net >= gross:
            return _abstain("T08", "no verified factor offset exists")
        theoretical = gross - net
        credit = min(
            theoretical,
            gross * evidence.maximum_credit_fraction,
        )
        if credit <= 0:
            return _abstain("T08", "netting credit is zero after safety cap")
        return AdvancedToolDecision(
            tool_code="T08",
            disposition=AdvancedToolDisposition.APPLIED,
            selected_id=evidence.correlation_state_id,
            released_capacity_usd=credit,
            score=net / gross,
            reason=(
                "exact same-instrument opposing exposures support deterministic "
                "capped netting credit without a correlation-model claim"
            ),
        )
    if not evidence.factor_map_verified:
        return _fail("T08", "factor map is not verified")
    if (
        not evidence.risk_mapping_verified
        or evidence.risk_mapping_evidence_id is None
    ):
        return _fail(
            "T08",
            "signed factor-risk mapping is not causally verified",
        )
    if not evidence.correlation_stable:
        return _fail(
            "T08",
            "correlation state is not stable enough for netting credit",
        )
    if (
        not evidence.correlation_oos
        or evidence.correlation_evidence_id is None
        or evidence.correlation_sample_size
        < evidence.minimum_correlation_sample
        or evidence.correlation_stability_folds
        < evidence.minimum_correlation_folds
    ):
        return _fail(
            "T08",
            "correlation state lacks sufficient causal OOS evidence",
        )
    if (
        not evidence.netting_utility_oos
        or evidence.netting_utility_evidence_id is None
        or evidence.netting_utility_sample_size
        < evidence.minimum_netting_utility_sample
    ):
        return _fail(
            "T08",
            "netting credit lacks sufficient fresh OOS utility evidence",
        )
    gross = sum((abs(item.signed_risk_usd) for item in evidence.exposures), Decimal(0))
    by_factor_oos: dict[str, Decimal] = {}
    for item in evidence.exposures:
        by_factor_oos[item.factor_id] = (
            by_factor_oos.get(item.factor_id, Decimal(0)) + item.signed_risk_usd
        )
    net = sum((abs(value) for value in by_factor_oos.values()), Decimal(0))
    if gross <= 0 or net >= gross:
        return _abstain("T08", "no verified factor offset exists")
    theoretical = gross - net
    credit = min(theoretical, gross * evidence.maximum_credit_fraction)
    if credit <= 0:
        return _abstain("T08", "netting credit is zero after safety cap")
    return AdvancedToolDecision(
        tool_code="T08",
        disposition=AdvancedToolDisposition.APPLIED,
        selected_id=evidence.correlation_state_id,
        released_capacity_usd=credit,
        score=net / gross,
        reason="verified stable factor offsets support capped true-portfolio-netting credit",
    )


@dataclass(frozen=True, slots=True)
class CapitalVelocityPolicy:
    policy_id: str
    realized_net_output_usd: Decimal
    capital_minutes: Decimal
    p95_drawdown_usd: Decimal
    tail_loss_usd: Decimal
    sample_size: int
    evidence_oos: bool

    def __post_init__(self) -> None:
        _id(self.policy_id, "policy_id")
        _finite(self.realized_net_output_usd, "realized_net_output_usd")
        for name in ("capital_minutes", "p95_drawdown_usd", "tail_loss_usd"):
            _positive(getattr(self, name), name)
        _positive_int(self.sample_size, "sample_size")
        if type(self.evidence_oos) is not bool:
            raise CiboCapitalManagementError("evidence_oos must be bool")


@dataclass(frozen=True, slots=True)
class CapitalVelocityEvidence:
    evidence_id: str
    observed_at: datetime
    baseline_policy_id: str
    policies: tuple[CapitalVelocityPolicy, ...]
    minimum_oos_sample: int = 30

    def __post_init__(self) -> None:
        _id(self.evidence_id, "evidence_id")
        _id(self.baseline_policy_id, "baseline_policy_id")
        _aware(self.observed_at, "observed_at")
        _positive_int(self.minimum_oos_sample, "minimum_oos_sample")
        if not self.policies:
            raise CiboCapitalManagementError("capital velocity policies are required")
        ids = tuple(item.policy_id for item in self.policies)
        if len(ids) != len(set(ids)):
            raise CiboCapitalManagementError("capital velocity policy ids must be unique")
        if self.baseline_policy_id not in ids:
            raise CiboCapitalManagementError("capital velocity baseline is missing")


def evaluate_capital_velocity(
    evidence: CapitalVelocityEvidence,
) -> AdvancedToolDecision:
    if not isinstance(evidence, CapitalVelocityEvidence):
        raise CiboCapitalManagementError(
            "evidence must be CapitalVelocityEvidence"
        )
    baseline = next(
        item for item in evidence.policies
        if item.policy_id == evidence.baseline_policy_id
    )
    if len(evidence.policies) == 1:
        return _abstain("T10", "NO_ALTERNATIVE_VELOCITY_POLICY")
    if not baseline.evidence_oos or baseline.sample_size < evidence.minimum_oos_sample:
        return _fail("T10", "capital velocity baseline is not sufficiently OOS")
    baseline_score = baseline.realized_net_output_usd / baseline.capital_minutes
    eligible = tuple(
        item
        for item in evidence.policies
        if item.evidence_oos
        and item.sample_size >= evidence.minimum_oos_sample
        and item.realized_net_output_usd > 0
        and item.p95_drawdown_usd <= baseline.p95_drawdown_usd
        and item.tail_loss_usd <= baseline.tail_loss_usd
    )
    if not eligible:
        return _abstain("T10", "no OOS velocity policy passes tail/DD gates")
    selected = max(
        eligible,
        key=lambda item: (
            item.realized_net_output_usd / item.capital_minutes,
            item.realized_net_output_usd,
            -item.capital_minutes,
            item.policy_id,
        ),
    )
    score = selected.realized_net_output_usd / selected.capital_minutes
    if score <= baseline_score:
        return _abstain("T10", "capital-time productivity does not improve baseline")
    return AdvancedToolDecision(
        tool_code="T10",
        disposition=AdvancedToolDisposition.APPLIED,
        selected_id=selected.policy_id,
        score=score,
        reason="OOS net output per capital-minute strictly improves without worse tail/DD",
    )


@dataclass(frozen=True, slots=True)
class HedgeInstrumentEvidence:
    instrument_id: str
    target_factor_id: str
    correlation_abs: Decimal
    correlation_stability: Decimal
    gross_risk_reduction_usd: Decimal
    basis_risk_usd: Decimal
    hedge_cost_usd: Decimal
    margin_usd: Decimal
    instrument_certified: bool
    execution_supported: bool

    def __post_init__(self) -> None:
        _id(self.instrument_id, "instrument_id")
        _id(self.target_factor_id, "target_factor_id")
        _fraction(self.correlation_abs, "correlation_abs")
        _fraction(self.correlation_stability, "correlation_stability")
        for name in (
            "gross_risk_reduction_usd",
            "basis_risk_usd",
            "hedge_cost_usd",
            "margin_usd",
        ):
            _nonnegative(getattr(self, name), name)
        for name in ("instrument_certified", "execution_supported"):
            if type(getattr(self, name)) is not bool:
                raise CiboCapitalManagementError(f"{name} must be bool")


@dataclass(frozen=True, slots=True)
class HedgedExposureEvidence:
    evidence_id: str
    observed_at: datetime
    instruments: tuple[HedgeInstrumentEvidence, ...]
    minimum_correlation_abs: Decimal = Decimal("0.70")
    minimum_correlation_stability: Decimal = Decimal("0.70")
    fresh_oos_utility_demonstrated: bool = False
    policy_authorized: bool = False

    def __post_init__(self) -> None:
        _id(self.evidence_id, "evidence_id")
        _aware(self.observed_at, "observed_at")
        _fraction(self.minimum_correlation_abs, "minimum_correlation_abs")
        _fraction(
            self.minimum_correlation_stability,
            "minimum_correlation_stability",
        )
        ids = tuple(item.instrument_id for item in self.instruments)
        if len(ids) != len(set(ids)):
            raise CiboCapitalManagementError("hedge instrument ids must be unique")
        for name in ("fresh_oos_utility_demonstrated", "policy_authorized"):
            if type(getattr(self, name)) is not bool:
                raise CiboCapitalManagementError(f"{name} must be bool")
        if self.policy_authorized and not self.fresh_oos_utility_demonstrated:
            raise CiboCapitalManagementError(
                "T16 policy authorization requires fresh OOS utility"
            )


def evaluate_hedged_exposure(
    evidence: HedgedExposureEvidence,
) -> AdvancedToolDecision:
    if not isinstance(evidence, HedgedExposureEvidence):
        raise CiboCapitalManagementError(
            "evidence must be HedgedExposureEvidence"
        )
    if not evidence.instruments:
        return _abstain("T16", "NO_HEDGE_INSTRUMENT_AVAILABLE")
    if not evidence.fresh_oos_utility_demonstrated:
        return _fail("T16", "T16 fresh OOS hedge utility is not demonstrated")
    if not evidence.policy_authorized:
        return _fail("T16", "T16 policy is not authorized")
    eligible: list[tuple[Decimal, HedgeInstrumentEvidence]] = []
    for item in evidence.instruments:
        if not item.instrument_certified or not item.execution_supported:
            continue
        if item.correlation_abs < evidence.minimum_correlation_abs:
            continue
        if item.correlation_stability < evidence.minimum_correlation_stability:
            continue
        net_benefit = (
            item.gross_risk_reduction_usd
            - item.basis_risk_usd
            - item.hedge_cost_usd
        )
        if net_benefit <= 0:
            continue
        eligible.append((net_benefit, item))
    if not eligible:
        return _abstain("T16", "NO_CERTIFIED_HEDGE_INSTRUMENT")
    benefit, selected = max(
        eligible,
        key=lambda pair: (
            pair[0],
            -pair[1].margin_usd,
            pair[1].instrument_id,
        ),
    )
    return AdvancedToolDecision(
        tool_code="T16",
        disposition=AdvancedToolDisposition.APPLIED,
        selected_id=selected.instrument_id,
        released_capacity_usd=benefit,
        score=(
            benefit / selected.gross_risk_reduction_usd
            if selected.gross_risk_reduction_usd > 0
            else None
        ),
        reason="certified hedge has positive risk-transfer benefit after basis risk and cost",
    )


@dataclass(frozen=True, slots=True)
class ConvexInstrumentEvidence:
    instrument_id: str
    bounded_downside_usd: Decimal
    premium_and_cost_usd: Decimal
    expected_upside_usd: Decimal
    pricing_fresh: bool
    settlement_certified: bool
    execution_supported: bool
    instrument_certified: bool

    def __post_init__(self) -> None:
        _id(self.instrument_id, "instrument_id")
        for name in ("bounded_downside_usd", "premium_and_cost_usd"):
            _positive(getattr(self, name), name)
        _finite(self.expected_upside_usd, "expected_upside_usd")
        for name in (
            "pricing_fresh",
            "settlement_certified",
            "execution_supported",
            "instrument_certified",
        ):
            if type(getattr(self, name)) is not bool:
                raise CiboCapitalManagementError(f"{name} must be bool")


@dataclass(frozen=True, slots=True)
class ConvexExposureEvidence:
    evidence_id: str
    observed_at: datetime
    available_limited_downside_capacity_usd: Decimal
    instruments: tuple[ConvexInstrumentEvidence, ...]
    fresh_oos_utility_demonstrated: bool = False
    policy_authorized: bool = False

    def __post_init__(self) -> None:
        _id(self.evidence_id, "evidence_id")
        _aware(self.observed_at, "observed_at")
        _nonnegative(
            self.available_limited_downside_capacity_usd,
            "available_limited_downside_capacity_usd",
        )
        ids = tuple(item.instrument_id for item in self.instruments)
        if len(ids) != len(set(ids)):
            raise CiboCapitalManagementError("convex instrument ids must be unique")
        for name in ("fresh_oos_utility_demonstrated", "policy_authorized"):
            if type(getattr(self, name)) is not bool:
                raise CiboCapitalManagementError(f"{name} must be bool")
        if self.policy_authorized and not self.fresh_oos_utility_demonstrated:
            raise CiboCapitalManagementError(
                "T17 policy authorization requires fresh OOS utility"
            )


def evaluate_convex_exposure(
    evidence: ConvexExposureEvidence,
) -> AdvancedToolDecision:
    if not isinstance(evidence, ConvexExposureEvidence):
        raise CiboCapitalManagementError(
            "evidence must be ConvexExposureEvidence"
        )
    if (
        not evidence.instruments
        or evidence.available_limited_downside_capacity_usd <= 0
    ):
        return _abstain(
            "T17",
            "NO_CERTIFIED_LIMITED_DOWNSIDE_INSTRUMENT_AVAILABLE",
        )
    if not evidence.fresh_oos_utility_demonstrated:
        return _fail("T17", "T17 fresh OOS utility is not demonstrated")
    if not evidence.policy_authorized:
        return _fail("T17", "T17 policy is not authorized")
    eligible = tuple(
        item
        for item in evidence.instruments
        if item.instrument_certified
        and item.execution_supported
        and item.pricing_fresh
        and item.settlement_certified
        and item.bounded_downside_usd
        <= evidence.available_limited_downside_capacity_usd
        and item.expected_upside_usd > item.premium_and_cost_usd
    )
    if not eligible:
        return _abstain("T17", "NO_CERTIFIED_LIMITED_DOWNSIDE_INSTRUMENT")
    selected = max(
        eligible,
        key=lambda item: (
            (item.expected_upside_usd - item.premium_and_cost_usd)
            / item.bounded_downside_usd,
            item.expected_upside_usd - item.premium_and_cost_usd,
            -item.bounded_downside_usd,
            item.instrument_id,
        ),
    )
    score = (
        selected.expected_upside_usd - selected.premium_and_cost_usd
    ) / selected.bounded_downside_usd
    return AdvancedToolDecision(
        tool_code="T17",
        disposition=AdvancedToolDisposition.APPLIED,
        selected_id=selected.instrument_id,
        target_stop_risk_usd=selected.bounded_downside_usd,
        score=score,
        reason=(
            "certified executable convex expression has bounded downside "
            "and positive net upside"
        ),
    )


@dataclass(frozen=True, slots=True)
class AdvancedCe2iEvidenceBundle:
    structural_leverage: StructuralLeverageEvidence | None = None
    margin_efficiency: MarginEfficiencyEvidence | None = None
    risk_efficiency: RiskEfficiencyEvidence | None = None
    portfolio_netting: PortfolioNettingEvidence | None = None
    capital_velocity: CapitalVelocityEvidence | None = None
    hedged_exposure: HedgedExposureEvidence | None = None
    convex_exposure: ConvexExposureEvidence | None = None


def evaluate_advanced_ce2i_surface(
    *,
    enabled_tools: tuple[str, ...],
    opportunity: TraderOpportunityEnvelope | None,
    evidence: AdvancedCe2iEvidenceBundle,
    current_volume: Decimal = Decimal(0),
    maximum_additional_volume: Decimal = Decimal(0),
) -> tuple[AdvancedToolDecision, ...]:
    """Evaluate the full formerly-missing CE2I surface deterministically.

    An enabled tool with missing evidence fails closed. An unavailable provider
    instrument is an explicit abstention, not an invented capability.
    """

    if not isinstance(evidence, AdvancedCe2iEvidenceBundle):
        raise CiboCapitalManagementError(
            "evidence must be AdvancedCe2iEvidenceBundle"
        )
    enabled = set(enabled_tools)
    out: list[AdvancedToolDecision] = []

    if "T02" in enabled:
        if opportunity is None:
            out.append(_fail("T02", "MISSING_TRADER_OPPORTUNITY"))
        elif evidence.structural_leverage is None:
            out.append(_fail("T02", "MISSING_STRUCTURAL_LEVERAGE_EVIDENCE"))
        else:
            out.append(
                evaluate_structural_leverage(
                    opportunity=opportunity,
                    evidence=evidence.structural_leverage,
                    current_volume=current_volume,
                    maximum_additional_volume=maximum_additional_volume,
                )
            )
    if "T03" in enabled:
        out.append(
            evaluate_margin_efficiency(evidence.margin_efficiency)
            if evidence.margin_efficiency is not None
            else _fail("T03", "MISSING_MARGIN_EFFICIENCY_EVIDENCE")
        )
    if "T04" in enabled:
        out.append(
            evaluate_risk_efficiency(evidence.risk_efficiency)
            if evidence.risk_efficiency is not None
            else _fail("T04", "MISSING_RISK_EFFICIENCY_EVIDENCE")
        )
    if "T08" in enabled:
        out.append(
            evaluate_portfolio_netting(evidence.portfolio_netting)
            if evidence.portfolio_netting is not None
            else _fail("T08", "MISSING_PORTFOLIO_NETTING_EVIDENCE")
        )
    if "T10" in enabled:
        out.append(
            evaluate_capital_velocity(evidence.capital_velocity)
            if evidence.capital_velocity is not None
            else _fail("T10", "MISSING_CAPITAL_VELOCITY_EVIDENCE")
        )
    if "T16" in enabled:
        out.append(
            evaluate_hedged_exposure(evidence.hedged_exposure)
            if evidence.hedged_exposure is not None
            else _fail("T16", "MISSING_HEDGE_EVIDENCE")
        )
    if "T17" in enabled:
        out.append(
            evaluate_convex_exposure(evidence.convex_exposure)
            if evidence.convex_exposure is not None
            else _fail("T17", "MISSING_CONVEX_INSTRUMENT_EVIDENCE")
        )
    return tuple(out)


def advanced_ce2i_engine_codes() -> tuple[str, ...]:
    return ("T02", "T03", "T04", "T08", "T10", "T16", "T17")


def assert_complete_advanced_ce2i_surface() -> None:
    if advanced_ce2i_engine_codes() != (
        "T02",
        "T03",
        "T04",
        "T08",
        "T10",
        "T16",
        "T17",
    ):
        raise CiboCapitalManagementError("advanced CE2I engine surface drift")


def _floor_step(value: Decimal, step: Decimal) -> Decimal:
    _nonnegative(value, "value")
    _positive(step, "step")
    steps = (value / step).to_integral_value(rounding=ROUND_FLOOR)
    return steps * step


def _fail(code: str, reason: str) -> AdvancedToolDecision:
    return AdvancedToolDecision(
        tool_code=code,
        disposition=AdvancedToolDisposition.FAIL_CLOSED,
        reason=reason,
    )


def _abstain(code: str, reason: str) -> AdvancedToolDecision:
    return AdvancedToolDecision(
        tool_code=code,
        disposition=AdvancedToolDisposition.ABSTAIN,
        reason=reason,
    )


def _id(value: str, field: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise CiboCapitalManagementError(f"{field} must be non-empty")


def _aware(value: datetime, field: str) -> None:
    if (
        not isinstance(value, datetime)
        or value.tzinfo is None
        or value.utcoffset() is None
    ):
        raise CiboCapitalManagementError(f"{field} must be timezone-aware")
    if value.astimezone(UTC) > datetime.now(UTC):
        raise CiboCapitalManagementError(f"{field} cannot be future-dated")


def _finite(value: Decimal, field: str) -> None:
    if not isinstance(value, Decimal) or not value.is_finite():
        raise CiboCapitalManagementError(f"{field} must be finite Decimal")


def _positive(value: Decimal, field: str) -> None:
    _finite(value, field)
    if value <= 0:
        raise CiboCapitalManagementError(f"{field} must be positive")


def _nonnegative(value: Decimal, field: str) -> None:
    _finite(value, field)
    if value < 0:
        raise CiboCapitalManagementError(f"{field} must be non-negative")


def _fraction(value: Decimal, field: str) -> None:
    _finite(value, field)
    if value < 0 or value > 1:
        raise CiboCapitalManagementError(f"{field} must be in [0,1]")


def _positive_int(value: int, field: str) -> None:
    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
        raise CiboCapitalManagementError(f"{field} must be positive int")
