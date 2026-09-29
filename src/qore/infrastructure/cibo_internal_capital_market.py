"""GEN-C6 QORE CIBO Internal Capital Market shadow policy.

This module implements the preregistered, pre-outcome
CIBO_GENC6_ROBUST_PARETO_MARGINAL_CAPITAL_MARKET_SHADOW_V1 policy.

One clearing allocates at most one next marginal legal action. Control is the
current T09/T18-style adjusted expected value per risk-minute baseline.
Treatment is a non-compensatory robust Pareto comparison with
RESERVE_NO_DEPLOYMENT as a real alternative.

Research-only. No sizing, Risk, execution, LIVE, real-capital or merge
authority is granted.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from enum import StrEnum
from itertools import combinations

from qore.infrastructure.account_wide_risk import TraderLineage
from qore.infrastructure.cibo_account_capital_mission import (
    CiboAccountCapitalIdentity,
)
from qore.infrastructure.cibo_ce2i_portfolio_allocation_ledger import (
    PortfolioAllocationLedger,
)
from qore.infrastructure.cibo_compound_capital import (
    CiboCompoundCapitalError,
)
from qore.infrastructure.cibo_core_compound_portfolio import (
    AccountCoreCompoundPortfolio,
)
from qore.infrastructure.cibo_marginal_capital_utility_evidence import (
    MarginalCapitalUtilityEvidence,
    marginal_capital_utility_evidence_sha256,
)
from qore.infrastructure.cibo_sequential_compounding_shadow_store import (
    Genc5ShadowDecisionSeal,
)

GENC6_MARKET_ID = "QORE_CIBO_INTERNAL_CAPITAL_MARKET"
GENC6_POLICY_ID = (
    "CIBO_GENC6_ROBUST_PARETO_MARGINAL_CAPITAL_MARKET_SHADOW_V1"
)
GENC6_POLICY_FROZEN_AT = datetime(2026, 9, 29, 20, 0, tzinfo=UTC)
GENC6_CONTROL_POLICY_ID = "CURRENT_T09_T18_STYLE_RISK_TIME_BASELINE_V1"
GENC6_TREATMENT_POLICY_ID = "ROBUST_PARETO_MARGINAL_WITH_RESERVE_V1"
GENC6_RESERVE_ID = "RESERVE_NO_DEPLOYMENT"


class Genc6EvidenceUse(StrEnum):
    CAPITAL_ELIGIBLE = "CAPITAL_ELIGIBLE"
    OBSERVE_ONLY = "OBSERVE_ONLY"


class Genc6EvidenceDirection(StrEnum):
    HIGHER_IS_BETTER = "HIGHER_IS_BETTER"
    LOWER_IS_BETTER = "LOWER_IS_BETTER"


class Genc6EvidenceKind(StrEnum):
    EXPECTED_NET_VALUE_PER_CAPITAL = "EXPECTED_NET_VALUE_PER_CAPITAL"
    EPISTEMIC_UNCERTAINTY = "EPISTEMIC_UNCERTAINTY"
    FAILURE_HAZARD = "FAILURE_HAZARD"
    POSITIVE_TAIL_POTENTIAL = "POSITIVE_TAIL_POTENTIAL"
    CAPITAL_DURATION_MINUTES = "CAPITAL_DURATION_MINUTES"
    MARGIN_PER_CAPITAL = "MARGIN_PER_CAPITAL"
    EXECUTION_COST_PER_CAPITAL = "EXECUTION_COST_PER_CAPITAL"
    CONCENTRATION_RISK_PER_CAPITAL = "CONCENTRATION_RISK_PER_CAPITAL"
    DRAWDOWN_RISK_PER_CAPITAL = "DRAWDOWN_RISK_PER_CAPITAL"
    OPTIONALITY_CONSUMED_PER_CAPITAL = "OPTIONALITY_CONSUMED_PER_CAPITAL"
    FACTOR_CONCENTRATION = "FACTOR_CONCENTRATION"
    TAIL_DEPENDENCE = "TAIL_DEPENDENCE"
    PROVIDER_CONSTRAINT_PRESSURE = "PROVIDER_CONSTRAINT_PRESSURE"
    SYSTEMIC_STRESS = "SYSTEMIC_STRESS"
    REGIME_STABILITY = "REGIME_STABILITY"
    CROSS_MARKET_COHERENCE = "CROSS_MARKET_COHERENCE"
    CONTINUATION_SUPPORT = "CONTINUATION_SUPPORT"
    OPPORTUNITY_QUALITY = "OPPORTUNITY_QUALITY"
    RESERVE_VALUE = "RESERVE_VALUE"
    FLOOR_DISTANCE = "FLOOR_DISTANCE"
    COMPOUND_DD = "COMPOUND_DD"
    BASE_DD = "BASE_DD"
    RISK_HEADROOM = "RISK_HEADROOM"


class Genc6Action(StrEnum):
    ALLOCATE_MARGINAL_UNIT = "ALLOCATE_MARGINAL_UNIT"
    RESERVE_NO_DEPLOYMENT = "RESERVE_NO_DEPLOYMENT"


_MANDATORY_KINDS = (
    Genc6EvidenceKind.EXPECTED_NET_VALUE_PER_CAPITAL,
    Genc6EvidenceKind.EPISTEMIC_UNCERTAINTY,
    Genc6EvidenceKind.CAPITAL_DURATION_MINUTES,
    Genc6EvidenceKind.MARGIN_PER_CAPITAL,
    Genc6EvidenceKind.EXECUTION_COST_PER_CAPITAL,
    Genc6EvidenceKind.CONCENTRATION_RISK_PER_CAPITAL,
    Genc6EvidenceKind.DRAWDOWN_RISK_PER_CAPITAL,
    Genc6EvidenceKind.OPTIONALITY_CONSUMED_PER_CAPITAL,
)

_OPTIONAL_COMPARABLE_KINDS = (
    Genc6EvidenceKind.FAILURE_HAZARD,
    Genc6EvidenceKind.POSITIVE_TAIL_POTENTIAL,
    Genc6EvidenceKind.FACTOR_CONCENTRATION,
    Genc6EvidenceKind.TAIL_DEPENDENCE,
    Genc6EvidenceKind.PROVIDER_CONSTRAINT_PRESSURE,
    Genc6EvidenceKind.SYSTEMIC_STRESS,
    Genc6EvidenceKind.REGIME_STABILITY,
    Genc6EvidenceKind.CROSS_MARKET_COHERENCE,
    Genc6EvidenceKind.CONTINUATION_SUPPORT,
    Genc6EvidenceKind.OPPORTUNITY_QUALITY,
)

_EXPECTED_DIRECTIONS = {
    Genc6EvidenceKind.EXPECTED_NET_VALUE_PER_CAPITAL:
        Genc6EvidenceDirection.HIGHER_IS_BETTER,
    Genc6EvidenceKind.EPISTEMIC_UNCERTAINTY:
        Genc6EvidenceDirection.LOWER_IS_BETTER,
    Genc6EvidenceKind.FAILURE_HAZARD:
        Genc6EvidenceDirection.LOWER_IS_BETTER,
    Genc6EvidenceKind.POSITIVE_TAIL_POTENTIAL:
        Genc6EvidenceDirection.HIGHER_IS_BETTER,
    Genc6EvidenceKind.CAPITAL_DURATION_MINUTES:
        Genc6EvidenceDirection.LOWER_IS_BETTER,
    Genc6EvidenceKind.MARGIN_PER_CAPITAL:
        Genc6EvidenceDirection.LOWER_IS_BETTER,
    Genc6EvidenceKind.EXECUTION_COST_PER_CAPITAL:
        Genc6EvidenceDirection.LOWER_IS_BETTER,
    Genc6EvidenceKind.CONCENTRATION_RISK_PER_CAPITAL:
        Genc6EvidenceDirection.LOWER_IS_BETTER,
    Genc6EvidenceKind.DRAWDOWN_RISK_PER_CAPITAL:
        Genc6EvidenceDirection.LOWER_IS_BETTER,
    Genc6EvidenceKind.OPTIONALITY_CONSUMED_PER_CAPITAL:
        Genc6EvidenceDirection.LOWER_IS_BETTER,
    Genc6EvidenceKind.FACTOR_CONCENTRATION:
        Genc6EvidenceDirection.LOWER_IS_BETTER,
    Genc6EvidenceKind.TAIL_DEPENDENCE:
        Genc6EvidenceDirection.LOWER_IS_BETTER,
    Genc6EvidenceKind.PROVIDER_CONSTRAINT_PRESSURE:
        Genc6EvidenceDirection.LOWER_IS_BETTER,
    Genc6EvidenceKind.SYSTEMIC_STRESS:
        Genc6EvidenceDirection.LOWER_IS_BETTER,
    Genc6EvidenceKind.REGIME_STABILITY:
        Genc6EvidenceDirection.HIGHER_IS_BETTER,
    Genc6EvidenceKind.CROSS_MARKET_COHERENCE:
        Genc6EvidenceDirection.HIGHER_IS_BETTER,
    Genc6EvidenceKind.CONTINUATION_SUPPORT:
        Genc6EvidenceDirection.HIGHER_IS_BETTER,
    Genc6EvidenceKind.OPPORTUNITY_QUALITY:
        Genc6EvidenceDirection.HIGHER_IS_BETTER,
    Genc6EvidenceKind.RESERVE_VALUE:
        Genc6EvidenceDirection.HIGHER_IS_BETTER,
    Genc6EvidenceKind.FLOOR_DISTANCE:
        Genc6EvidenceDirection.HIGHER_IS_BETTER,
    Genc6EvidenceKind.COMPOUND_DD:
        Genc6EvidenceDirection.LOWER_IS_BETTER,
    Genc6EvidenceKind.BASE_DD:
        Genc6EvidenceDirection.LOWER_IS_BETTER,
    Genc6EvidenceKind.RISK_HEADROOM:
        Genc6EvidenceDirection.HIGHER_IS_BETTER,
}


@dataclass(frozen=True, slots=True)
class Genc6CapitalEvidenceFact:
    fact_id: str
    kind: Genc6EvidenceKind
    value: Decimal
    direction: Genc6EvidenceDirection
    evidence_sha256: str
    produced_at: datetime
    observed_at: datetime
    source: str
    policy_version: str
    calibration_lineage: str
    use: Genc6EvidenceUse
    model_identity: str | None = None
    calibrated: bool = False
    oos_validated: bool = False

    def __post_init__(self) -> None:
        if not self.fact_id or not self.source or not self.policy_version:
            raise CiboCompoundCapitalError(
                "GEN-C6 evidence fact identity/source/policy is required"
            )
        if not self.calibration_lineage:
            raise CiboCompoundCapitalError(
                "GEN-C6 evidence calibration lineage is required"
            )
        if type(self.kind) is not Genc6EvidenceKind:
            raise CiboCompoundCapitalError(
                "GEN-C6 evidence kind is invalid"
            )
        if type(self.direction) is not Genc6EvidenceDirection:
            raise CiboCompoundCapitalError(
                "GEN-C6 evidence direction is invalid"
            )
        if self.direction is not _EXPECTED_DIRECTIONS[self.kind]:
            raise CiboCompoundCapitalError(
                "GEN-C6 evidence direction conflicts with policy semantics"
            )
        if (
            not isinstance(self.value, Decimal)
            or not self.value.is_finite()
        ):
            raise CiboCompoundCapitalError(
                "GEN-C6 evidence value must be finite Decimal"
            )
        _sha(self.evidence_sha256, "evidence_sha256")
        _aware(self.produced_at, "produced_at")
        _aware(self.observed_at, "observed_at")
        if self.produced_at < self.observed_at:
            raise CiboCompoundCapitalError(
                "GEN-C6 evidence cannot be produced before observation"
            )
        if type(self.use) is not Genc6EvidenceUse:
            raise CiboCompoundCapitalError(
                "GEN-C6 evidence use is invalid"
            )
        for name in ("calibrated", "oos_validated"):
            if type(getattr(self, name)) is not bool:
                raise CiboCompoundCapitalError(
                    f"GEN-C6 evidence {name} must be bool"
                )
        if (
            self.kind
            in {
                Genc6EvidenceKind.EXPECTED_NET_VALUE_PER_CAPITAL,
                Genc6EvidenceKind.RESERVE_VALUE,
            }
            and self.use is Genc6EvidenceUse.CAPITAL_ELIGIBLE
        ):
            if not self.model_identity:
                raise CiboCompoundCapitalError(
                    "capital-eligible expected/reserve value requires model identity"
                )
            if not self.calibrated or not self.oos_validated:
                raise CiboCompoundCapitalError(
                    "capital-eligible expected/reserve value requires calibration/OOS"
                )

    @property
    def eligible_for_capital_use(self) -> bool:
        return self.use is Genc6EvidenceUse.CAPITAL_ELIGIBLE

    @property
    def observe_only(self) -> bool:
        return self.use is Genc6EvidenceUse.OBSERVE_ONLY


@dataclass(frozen=True, slots=True)
class Genc6ProviderCapitalActionEvidence:
    evidence_id: str
    evidence_sha256: str
    produced_at: datetime
    observed_at: datetime
    source: str
    policy_version: str
    account_identity: CiboAccountCapitalIdentity
    qore_symbol: str
    provider_symbol: str
    requested_capital_usd: Decimal
    executable_volume: Decimal
    minimum_executable_volume: Decimal
    maximum_volume: Decimal
    volume_step: Decimal
    minimum_execution_steps: int
    projected_stop_risk_usd: Decimal
    minimum_stop_risk_usd: Decimal
    projected_margin_usd: Decimal
    minimum_margin_usd: Decimal
    projected_execution_cost_usd: Decimal
    feasible: bool
    use: Genc6EvidenceUse
    reason: str

    def __post_init__(self) -> None:
        if not self.evidence_id or not self.source or not self.policy_version:
            raise CiboCompoundCapitalError(
                "GEN-C6 provider action evidence identity/source/policy is required"
            )
        _sha(self.evidence_sha256, "provider action evidence_sha256")
        _aware(self.produced_at, "provider action produced_at")
        _aware(self.observed_at, "provider action observed_at")
        if self.produced_at < self.observed_at:
            raise CiboCompoundCapitalError(
                "GEN-C6 provider action cannot be produced before observation"
            )
        if not isinstance(
            self.account_identity,
            CiboAccountCapitalIdentity,
        ):
            raise CiboCompoundCapitalError(
                "GEN-C6 provider action account identity is invalid"
            )
        if not self.qore_symbol or not self.provider_symbol or not self.reason:
            raise CiboCompoundCapitalError(
                "GEN-C6 provider action symbol/reason is required"
            )
        for name in (
            "requested_capital_usd",
            "executable_volume",
            "minimum_executable_volume",
            "maximum_volume",
            "volume_step",
            "projected_stop_risk_usd",
            "minimum_stop_risk_usd",
            "projected_margin_usd",
            "minimum_margin_usd",
            "projected_execution_cost_usd",
        ):
            value = getattr(self, name)
            if (
                not isinstance(value, Decimal)
                or not value.is_finite()
                or value < 0
            ):
                raise CiboCompoundCapitalError(
                    f"GEN-C6 provider action {name} must be finite non-negative"
                )
        for name in (
            "requested_capital_usd",
            "executable_volume",
            "minimum_executable_volume",
            "maximum_volume",
            "volume_step",
            "projected_stop_risk_usd",
            "projected_margin_usd",
        ):
            if getattr(self, name) <= 0:
                raise CiboCompoundCapitalError(
                    f"GEN-C6 provider action {name} must be positive"
                )
        if (
            not isinstance(self.minimum_execution_steps, int)
            or isinstance(self.minimum_execution_steps, bool)
            or self.minimum_execution_steps < 1
        ):
            raise CiboCompoundCapitalError(
                "GEN-C6 provider minimum execution steps must be positive int"
            )
        if self.maximum_volume < self.minimum_executable_volume:
            raise CiboCompoundCapitalError(
                "GEN-C6 provider volume bounds are invalid"
            )
        if self.executable_volume < self.minimum_executable_volume:
            raise CiboCompoundCapitalError(
                "GEN-C6 provider action is below minimum executable volume"
            )
        if self.executable_volume > self.maximum_volume:
            raise CiboCompoundCapitalError(
                "GEN-C6 provider action exceeds maximum volume"
            )
        steps = self.executable_volume / self.volume_step
        if steps != steps.to_integral_value():
            raise CiboCompoundCapitalError(
                "GEN-C6 provider action volume is not step aligned"
            )
        if self.projected_stop_risk_usd < self.minimum_stop_risk_usd:
            raise CiboCompoundCapitalError(
                "GEN-C6 provider action understates minimum stop risk"
            )
        if self.projected_margin_usd < self.minimum_margin_usd:
            raise CiboCompoundCapitalError(
                "GEN-C6 provider action understates minimum margin"
            )
        if type(self.feasible) is not bool:
            raise CiboCompoundCapitalError(
                "GEN-C6 provider action feasible must be bool"
            )
        if type(self.use) is not Genc6EvidenceUse:
            raise CiboCompoundCapitalError(
                "GEN-C6 provider action evidence use is invalid"
            )

    @property
    def eligible_for_capital_use(self) -> bool:
        return self.use is Genc6EvidenceUse.CAPITAL_ELIGIBLE


@dataclass(frozen=True, slots=True)
class Genc6PortfolioStateSnapshot:
    snapshot_id: str
    decision_at: datetime
    account_identity: CiboAccountCapitalIdentity
    portfolio_sha256: str
    t19_ledger_sha256: str
    current_compound_capacity_usd: Decimal
    available_compound_capital_usd: Decimal
    protected_floor_usd: Decimal
    strategic_reserve_usd: Decimal
    opportunity_reserve_usd: Decimal
    deployed_compound_capital_usd: Decimal
    t19_stop_risk_headroom_usd: Decimal
    t19_margin_headroom_usd: Decimal
    t19_concentration_headroom: tuple[tuple[str, Decimal], ...]
    active_t19_reservation_count: int
    context_facts: tuple[Genc6CapitalEvidenceFact, ...] = ()
    runtime_authority: bool = False
    risk_authority: bool = False
    execution_authority: bool = False

    def __post_init__(self) -> None:
        if not self.snapshot_id:
            raise CiboCompoundCapitalError(
                "GEN-C6 portfolio snapshot identity is required"
            )
        _aware(self.decision_at, "portfolio decision_at")
        if not isinstance(
            self.account_identity,
            CiboAccountCapitalIdentity,
        ):
            raise CiboCompoundCapitalError(
                "GEN-C6 portfolio account identity is invalid"
            )
        _sha(self.portfolio_sha256, "portfolio_sha256")
        _sha(self.t19_ledger_sha256, "t19_ledger_sha256")
        for name in (
            "current_compound_capacity_usd",
            "available_compound_capital_usd",
            "protected_floor_usd",
            "strategic_reserve_usd",
            "opportunity_reserve_usd",
            "deployed_compound_capital_usd",
            "t19_stop_risk_headroom_usd",
            "t19_margin_headroom_usd",
        ):
            _nonnegative(getattr(self, name), name)
        if self.available_compound_capital_usd > self.current_compound_capacity_usd:
            raise CiboCompoundCapitalError(
                "GEN-C6 available compound capital exceeds current capacity"
            )
        if (
            not isinstance(self.active_t19_reservation_count, int)
            or isinstance(self.active_t19_reservation_count, bool)
            or self.active_t19_reservation_count < 0
        ):
            raise CiboCompoundCapitalError(
                "GEN-C6 active T19 reservation count is invalid"
            )
        groups = tuple(item[0] for item in self.t19_concentration_headroom)
        if len(groups) != len(set(groups)):
            raise CiboCompoundCapitalError(
                "GEN-C6 concentration headroom groups must be unique"
            )
        for group, amount in self.t19_concentration_headroom:
            if not group:
                raise CiboCompoundCapitalError(
                    "GEN-C6 concentration group cannot be blank"
                )
            _nonnegative(amount, "concentration headroom")
        _unique_fact_kinds(self.context_facts)
        for fact in self.context_facts:
            if (
                fact.observed_at > self.decision_at
                or fact.produced_at > self.decision_at
            ):
                raise CiboCompoundCapitalError(
                    "GEN-C6 portfolio context fact arrives from future"
                )
        for name in (
            "runtime_authority",
            "risk_authority",
            "execution_authority",
        ):
            if type(getattr(self, name)) is not bool or getattr(self, name):
                raise CiboCompoundCapitalError(
                    "GEN-C6 portfolio snapshot cannot carry runtime authority"
                )

    def concentration_headroom(self, group: str) -> Decimal | None:
        for name, value in self.t19_concentration_headroom:
            if name == group:
                return value
        return None


@dataclass(frozen=True, slots=True)
class Genc6MarginalCapitalCandidate:
    candidate_id: str
    account_identity: CiboAccountCapitalIdentity
    trader_id: TraderLineage
    qore_symbol: str
    provider_symbol: str
    signal_fingerprint: str
    decision_at: datetime
    valid_from: datetime
    valid_until: datetime
    technical_valid: bool
    cancelled: bool
    marginal_unit_index: int
    concentration_group: str
    marginal_evidence: MarginalCapitalUtilityEvidence
    genc5_seal: Genc5ShadowDecisionSeal
    provider_action: Genc6ProviderCapitalActionEvidence
    comparable_facts: tuple[Genc6CapitalEvidenceFact, ...]

    def __post_init__(self) -> None:
        for name in (
            "candidate_id",
            "qore_symbol",
            "provider_symbol",
            "signal_fingerprint",
            "concentration_group",
        ):
            if not getattr(self, name):
                raise CiboCompoundCapitalError(
                    f"GEN-C6 candidate {name} is required"
                )
        if not isinstance(
            self.account_identity,
            CiboAccountCapitalIdentity,
        ):
            raise CiboCompoundCapitalError(
                "GEN-C6 candidate account identity is invalid"
            )
        if type(self.trader_id) is not TraderLineage:
            raise CiboCompoundCapitalError(
                "GEN-C6 candidate Trader identity is invalid"
            )
        for name in ("decision_at", "valid_from", "valid_until"):
            _aware(getattr(self, name), f"candidate {name}")
        if self.valid_until < self.valid_from:
            raise CiboCompoundCapitalError(
                "GEN-C6 candidate validity window is reversed"
            )
        if (
            not isinstance(self.marginal_unit_index, int)
            or isinstance(self.marginal_unit_index, bool)
            or self.marginal_unit_index < 1
        ):
            raise CiboCompoundCapitalError(
                "GEN-C6 marginal unit index must be positive int"
            )
        for name in ("technical_valid", "cancelled"):
            if type(getattr(self, name)) is not bool:
                raise CiboCompoundCapitalError(
                    f"GEN-C6 candidate {name} must be bool"
                )
        if not isinstance(
            self.provider_action,
            Genc6ProviderCapitalActionEvidence,
        ):
            raise CiboCompoundCapitalError(
                "GEN-C6 candidate requires canonical provider action evidence"
            )
        if not isinstance(
            self.marginal_evidence,
            MarginalCapitalUtilityEvidence,
        ):
            raise CiboCompoundCapitalError(
                "GEN-C6 candidate requires canonical GEN-C4 evidence"
            )
        if not isinstance(self.genc5_seal, Genc5ShadowDecisionSeal):
            raise CiboCompoundCapitalError(
                "GEN-C6 candidate requires durable GEN-C5 seal"
            )
        if self.marginal_evidence.account_identity != self.account_identity:
            raise CiboCompoundCapitalError(
                "GEN-C6 candidate GEN-C4 account binding drift"
            )
        if self.marginal_evidence.trader_id is not self.trader_id:
            raise CiboCompoundCapitalError(
                "GEN-C6 candidate GEN-C4 Trader binding drift"
            )
        if self.marginal_evidence.signal_fingerprint != self.signal_fingerprint:
            raise CiboCompoundCapitalError(
                "GEN-C6 candidate GEN-C4 signal binding drift"
            )
        if self.marginal_evidence.decision_at != self.decision_at:
            raise CiboCompoundCapitalError(
                "GEN-C6 candidate GEN-C4 decision-time binding drift"
            )
        c4_sha = marginal_capital_utility_evidence_sha256(
            self.marginal_evidence
        )
        if self.genc5_seal.marginal_evidence_sha256 != c4_sha:
            raise CiboCompoundCapitalError(
                "GEN-C6 candidate GEN-C5/GEN-C4 digest binding drift"
            )
        if (
            self.genc5_seal.account_provider_key
            != self.account_identity.provider_key
            or self.genc5_seal.account_ref
            != self.account_identity.account_ref
        ):
            raise CiboCompoundCapitalError(
                "GEN-C6 candidate GEN-C5 account binding drift"
            )
        if self.genc5_seal.decision_at != self.decision_at:
            raise CiboCompoundCapitalError(
                "GEN-C6 candidate GEN-C5 decision-time binding drift"
            )
        if self.provider_action.account_identity != self.account_identity:
            raise CiboCompoundCapitalError(
                "GEN-C6 candidate provider action account binding drift"
            )
        if (
            self.provider_action.qore_symbol != self.qore_symbol
            or self.provider_action.provider_symbol != self.provider_symbol
        ):
            raise CiboCompoundCapitalError(
                "GEN-C6 candidate provider action symbol binding drift"
            )
        if (
            self.provider_action.requested_capital_usd
            != self.requested_capital_usd
        ):
            raise CiboCompoundCapitalError(
                "GEN-C6 candidate provider action capital binding drift"
            )
        if (
            self.provider_action.projected_stop_risk_usd
            != self.marginal_evidence.incremental_stop_risk_usd
            or self.provider_action.projected_margin_usd
            != self.marginal_evidence.incremental_margin_usd
            or self.provider_action.projected_execution_cost_usd
            != self.marginal_evidence.incremental_execution_cost_usd
        ):
            raise CiboCompoundCapitalError(
                "GEN-C6 candidate provider economics/GEN-C4 binding drift"
            )
        if (
            self.provider_action.observed_at > self.decision_at
            or self.provider_action.produced_at > self.decision_at
        ):
            raise CiboCompoundCapitalError(
                "GEN-C6 provider action evidence arrives from future"
            )
        _unique_fact_kinds(self.comparable_facts)
        for fact in self.comparable_facts:
            if (
                fact.observed_at > self.decision_at
                or fact.produced_at > self.decision_at
            ):
                raise CiboCompoundCapitalError(
                    "GEN-C6 candidate fact arrives from future"
                )
        self._validate_mandatory_fact_values()

    @property
    def requested_capital_usd(self) -> Decimal:
        return self.marginal_evidence.requested_incremental_capital_usd

    @property
    def stop_risk_usd(self) -> Decimal:
        return self.marginal_evidence.incremental_stop_risk_usd

    @property
    def margin_usd(self) -> Decimal:
        return self.marginal_evidence.incremental_margin_usd

    @property
    def concentration_risk_usd(self) -> Decimal:
        return self.marginal_evidence.incremental_concentration_risk_usd

    @property
    def adjusted_expected_net_value_usd(self) -> Decimal:
        return (
            self.marginal_evidence.expected_incremental_return_usd
            - self.marginal_evidence.incremental_execution_cost_usd
            - self.marginal_evidence.incremental_optionality_consumed_usd
        )

    @property
    def control_risk_time_score(self) -> Decimal:
        return self.adjusted_expected_net_value_usd / (
            self.stop_risk_usd
            * self.marginal_evidence.expected_capital_minutes
        )

    @property
    def control_value_per_risk(self) -> Decimal:
        return self.adjusted_expected_net_value_usd / self.stop_risk_usd

    @property
    def valid_at_decision(self) -> bool:
        return (
            self.valid_from <= self.decision_at <= self.valid_until
            and self.technical_valid
            and not self.cancelled
        )

    def fact(self, kind: Genc6EvidenceKind) -> Genc6CapitalEvidenceFact | None:
        rows = tuple(item for item in self.comparable_facts if item.kind is kind)
        return rows[0] if rows else None

    def mandatory_facts_capital_eligible(self) -> bool:
        return all(
            (fact := self.fact(kind)) is not None
            and fact.eligible_for_capital_use
            for kind in _MANDATORY_KINDS
        )

    def genc5_forwarded_exact_amount(self) -> bool:
        return (
            self.genc5_seal.treatment_differs_from_control
            and self.genc5_seal.treatment_requested_risk_review_usd
            == self.requested_capital_usd
        )

    def _validate_mandatory_fact_values(self) -> None:
        amount = self.requested_capital_usd
        expected = {
            Genc6EvidenceKind.EXPECTED_NET_VALUE_PER_CAPITAL:
                self.adjusted_expected_net_value_usd / amount,
            Genc6EvidenceKind.EPISTEMIC_UNCERTAINTY:
                self.marginal_evidence.epistemic_uncertainty,
            Genc6EvidenceKind.CAPITAL_DURATION_MINUTES:
                self.marginal_evidence.expected_capital_minutes,
            Genc6EvidenceKind.MARGIN_PER_CAPITAL:
                self.marginal_evidence.incremental_margin_usd / amount,
            Genc6EvidenceKind.EXECUTION_COST_PER_CAPITAL:
                self.marginal_evidence.incremental_execution_cost_usd
                / amount,
            Genc6EvidenceKind.CONCENTRATION_RISK_PER_CAPITAL:
                self.marginal_evidence.incremental_concentration_risk_usd
                / amount,
            Genc6EvidenceKind.DRAWDOWN_RISK_PER_CAPITAL:
                self.marginal_evidence.incremental_drawdown_risk_proxy_usd
                / amount,
            Genc6EvidenceKind.OPTIONALITY_CONSUMED_PER_CAPITAL:
                self.marginal_evidence.incremental_optionality_consumed_usd
                / amount,
        }
        for kind, value in expected.items():
            fact = self.fact(kind)
            if fact is None:
                raise CiboCompoundCapitalError(
                    f"GEN-C6 candidate missing mandatory {kind.value}"
                )
            if fact.value != value:
                raise CiboCompoundCapitalError(
                    f"GEN-C6 candidate {kind.value} does not reproduce GEN-C4"
                )


@dataclass(frozen=True, slots=True)
class Genc6ReserveAlternative:
    alternative_id: str
    account_identity: CiboAccountCapitalIdentity
    decision_at: datetime
    evidence_facts: tuple[Genc6CapitalEvidenceFact, ...] = ()

    def __post_init__(self) -> None:
        if self.alternative_id != GENC6_RESERVE_ID:
            raise CiboCompoundCapitalError(
                "GEN-C6 reserve alternative identity drift"
            )
        if not isinstance(
            self.account_identity,
            CiboAccountCapitalIdentity,
        ):
            raise CiboCompoundCapitalError(
                "GEN-C6 reserve account identity is invalid"
            )
        _aware(self.decision_at, "reserve decision_at")
        _unique_fact_kinds(self.evidence_facts)
        for fact in self.evidence_facts:
            if (
                fact.observed_at > self.decision_at
                or fact.produced_at > self.decision_at
            ):
                raise CiboCompoundCapitalError(
                    "GEN-C6 reserve fact arrives from future"
                )


@dataclass(frozen=True, slots=True)
class CapitalScarcityEvent:
    event_id: str
    account_identity: CiboAccountCapitalIdentity
    decision_at: datetime
    portfolio_state: Genc6PortfolioStateSnapshot
    candidates: tuple[Genc6MarginalCapitalCandidate, ...]
    reserve_alternative: Genc6ReserveAlternative
    candidate_set_sha256: str
    simultaneously_valid_count: int
    eligible_candidate_count: int
    available_capital_usd: Decimal
    total_requested_capital_usd: Decimal
    capital_shortfall_usd: Decimal
    mutually_fundable_candidate_count: int
    competition_intensity: Decimal
    true_scarcity: bool

    def __post_init__(self) -> None:
        if not self.event_id:
            raise CiboCompoundCapitalError(
                "GEN-C6 scarcity event identity is required"
            )
        if not isinstance(
            self.account_identity,
            CiboAccountCapitalIdentity,
        ):
            raise CiboCompoundCapitalError(
                "GEN-C6 scarcity account identity is invalid"
            )
        _aware(self.decision_at, "scarcity decision_at")
        if self.decision_at < GENC6_POLICY_FROZEN_AT:
            raise CiboCompoundCapitalError(
                "GEN-C6 cannot collect pre-freeze scarcity event"
            )
        if self.portfolio_state.account_identity != self.account_identity:
            raise CiboCompoundCapitalError(
                "GEN-C6 scarcity portfolio account drift"
            )
        if self.portfolio_state.decision_at != self.decision_at:
            raise CiboCompoundCapitalError(
                "GEN-C6 scarcity portfolio decision-time drift"
            )
        if self.reserve_alternative.account_identity != self.account_identity:
            raise CiboCompoundCapitalError(
                "GEN-C6 reserve account drift"
            )
        if self.reserve_alternative.decision_at != self.decision_at:
            raise CiboCompoundCapitalError(
                "GEN-C6 reserve decision-time drift"
            )
        ids = tuple(item.candidate_id for item in self.candidates)
        if len(ids) != len(set(ids)):
            raise CiboCompoundCapitalError(
                "GEN-C6 scarcity candidate ids must be unique"
            )
        signals = tuple(item.signal_fingerprint for item in self.candidates)
        if len(signals) != len(set(signals)):
            raise CiboCompoundCapitalError(
                "GEN-C6 scarcity event exposes more than next unit per signal"
            )
        for candidate in self.candidates:
            if candidate.account_identity != self.account_identity:
                raise CiboCompoundCapitalError(
                    "GEN-C6 cross-account candidate is forbidden"
                )
            if candidate.decision_at != self.decision_at:
                raise CiboCompoundCapitalError(
                    "GEN-C6 candidates must share exact decision epoch"
                )
        _sha(self.candidate_set_sha256, "candidate_set_sha256")
        if self.candidate_set_sha256 != genc6_candidate_set_sha256(
            self.candidates
        ):
            raise CiboCompoundCapitalError(
                "GEN-C6 candidate-set digest drift"
            )
        for name in (
            "simultaneously_valid_count",
            "eligible_candidate_count",
            "mutually_fundable_candidate_count",
        ):
            value = getattr(self, name)
            if (
                not isinstance(value, int)
                or isinstance(value, bool)
                or value < 0
            ):
                raise CiboCompoundCapitalError(
                    f"GEN-C6 {name} must be non-negative int"
                )
        for name in (
            "available_capital_usd",
            "total_requested_capital_usd",
            "capital_shortfall_usd",
            "competition_intensity",
        ):
            _nonnegative(getattr(self, name), name)
        if self.competition_intensity > 1:
            raise CiboCompoundCapitalError(
                "GEN-C6 competition intensity must be in [0,1]"
            )
        valid = tuple(item for item in self.candidates if item.valid_at_decision)
        if self.simultaneously_valid_count != len(valid):
            raise CiboCompoundCapitalError(
                "GEN-C6 simultaneous valid count drift"
            )
        if self.available_capital_usd != (
            self.portfolio_state.available_compound_capital_usd
        ):
            raise CiboCompoundCapitalError(
                "GEN-C6 available capital/portfolio drift"
            )
        eligible = tuple(
            item
            for item in valid
            if not _candidate_blockers(item, self.portfolio_state)
        )
        if self.eligible_candidate_count != len(eligible):
            raise CiboCompoundCapitalError(
                "GEN-C6 eligible candidate count drift"
            )
        expected_requested = sum(
            (item.requested_capital_usd for item in eligible),
            Decimal(0),
        )
        if self.total_requested_capital_usd != expected_requested:
            raise CiboCompoundCapitalError(
                "GEN-C6 requested capital arithmetic drift"
            )
        expected_shortfall = max(
            Decimal(0),
            expected_requested - self.available_capital_usd,
        )
        if self.capital_shortfall_usd != expected_shortfall:
            raise CiboCompoundCapitalError(
                "GEN-C6 capital shortfall arithmetic drift"
            )
        expected_intensity = (
            Decimal(0)
            if expected_requested <= 0
            else expected_shortfall / expected_requested
        )
        if self.competition_intensity != expected_intensity:
            raise CiboCompoundCapitalError(
                "GEN-C6 competition intensity arithmetic drift"
            )
        expected_true = (
            len(eligible) >= 2
            and expected_requested > self.available_capital_usd
        )
        if self.true_scarcity != expected_true:
            raise CiboCompoundCapitalError(
                "GEN-C6 true-scarcity classification drift"
            )
        expected_mutually_fundable = _max_mutually_fundable_count(
            eligible,
            self.portfolio_state,
        )
        if (
            self.mutually_fundable_candidate_count
            != expected_mutually_fundable
        ):
            raise CiboCompoundCapitalError(
                "GEN-C6 mutually fundable count drift"
            )


@dataclass(frozen=True, slots=True)
class Genc6InternalCapitalMarketDecision:
    market_id: str
    policy_id: str
    policy_sha256: str
    policy_frozen_at: datetime
    decision_id: str
    scarcity_event_id: str
    decision_at: datetime
    account_provider_key: str
    account_ref: str
    candidate_set_sha256: str
    candidate_evidence_sha256s: tuple[str, ...]
    genc5_decision_sha256s: tuple[str, ...]
    portfolio_state_sha256: str
    t19_ledger_sha256: str
    available_capital_usd: Decimal
    true_scarcity: bool
    control_action: Genc6Action
    control_candidate_id: str | None
    control_amount_usd: Decimal
    treatment_action: Genc6Action
    treatment_candidate_id: str | None
    treatment_amount_usd: Decimal
    reserve_amount_usd: Decimal
    active_comparable_dimensions: tuple[Genc6EvidenceKind, ...]
    control_reason: str
    treatment_reason: str
    blocker_codes: tuple[str, ...]
    treatment_differs_from_control: bool
    outcome_present_at_seal: bool = False
    runtime_authority: bool = False
    risk_authority: bool = False
    execution_authority: bool = False
    live_authority: bool = False
    real_capital_authority: bool = False

    def __post_init__(self) -> None:
        if self.market_id != GENC6_MARKET_ID:
            raise CiboCompoundCapitalError(
                "GEN-C6 market identity drift"
            )
        if self.policy_id != GENC6_POLICY_ID:
            raise CiboCompoundCapitalError(
                "GEN-C6 policy identity drift"
            )
        if self.policy_sha256 != genc6_policy_sha256():
            raise CiboCompoundCapitalError(
                "GEN-C6 policy digest drift"
            )
        if self.policy_frozen_at != GENC6_POLICY_FROZEN_AT:
            raise CiboCompoundCapitalError(
                "GEN-C6 policy freeze drift"
            )
        if not self.decision_id or not self.scarcity_event_id:
            raise CiboCompoundCapitalError(
                "GEN-C6 decision/scarcity identity is required"
            )
        _aware(self.decision_at, "decision_at")
        if self.decision_at < self.policy_frozen_at:
            raise CiboCompoundCapitalError(
                "GEN-C6 decision cannot predate policy freeze"
            )
        if not self.account_provider_key or not self.account_ref:
            raise CiboCompoundCapitalError(
                "GEN-C6 account identity is required"
            )
        for name in (
            "candidate_set_sha256",
            "portfolio_state_sha256",
            "t19_ledger_sha256",
        ):
            _sha(getattr(self, name), name)
        for value in (
            *self.candidate_evidence_sha256s,
            *self.genc5_decision_sha256s,
        ):
            _sha(value, "bound evidence SHA")
        if len(self.candidate_evidence_sha256s) != len(
            set(self.candidate_evidence_sha256s)
        ):
            raise CiboCompoundCapitalError(
                "GEN-C6 candidate evidence SHA list must be unique"
            )
        if len(self.genc5_decision_sha256s) != len(
            set(self.genc5_decision_sha256s)
        ):
            raise CiboCompoundCapitalError(
                "GEN-C6 GEN-C5 SHA list must be unique"
            )
        for name in (
            "available_capital_usd",
            "control_amount_usd",
            "treatment_amount_usd",
            "reserve_amount_usd",
        ):
            _nonnegative(getattr(self, name), name)
        if type(self.true_scarcity) is not bool:
            raise CiboCompoundCapitalError(
                "GEN-C6 true_scarcity must be bool"
            )
        _validate_action(
            action=self.control_action,
            candidate_id=self.control_candidate_id,
            amount=self.control_amount_usd,
            label="control",
        )
        _validate_action(
            action=self.treatment_action,
            candidate_id=self.treatment_candidate_id,
            amount=self.treatment_amount_usd,
            label="treatment",
        )
        if len(self.active_comparable_dimensions) != len(
            set(self.active_comparable_dimensions)
        ):
            raise CiboCompoundCapitalError(
                "GEN-C6 active dimensions must be unique"
            )
        if any(not item for item in (self.control_reason, self.treatment_reason)):
            raise CiboCompoundCapitalError(
                "GEN-C6 control/treatment reason is required"
            )
        if len(self.blocker_codes) != len(set(self.blocker_codes)):
            raise CiboCompoundCapitalError(
                "GEN-C6 blocker codes must be unique"
            )
        expected_diff = (
            self.control_action != self.treatment_action
            or self.control_candidate_id != self.treatment_candidate_id
            or self.control_amount_usd != self.treatment_amount_usd
        )
        if self.treatment_differs_from_control != expected_diff:
            raise CiboCompoundCapitalError(
                "GEN-C6 treatment/control divergence flag drift"
            )
        for name in (
            "outcome_present_at_seal",
            "runtime_authority",
            "risk_authority",
            "execution_authority",
            "live_authority",
            "real_capital_authority",
        ):
            if type(getattr(self, name)) is not bool or getattr(self, name):
                raise CiboCompoundCapitalError(
                    "GEN-C6 shadow decision cannot contain outcome/authority"
                )


def genc6_policy_sha256() -> str:
    payload = {
        "market_id": GENC6_MARKET_ID,
        "policy_id": GENC6_POLICY_ID,
        "frozen_at": GENC6_POLICY_FROZEN_AT.isoformat(),
        "control": GENC6_CONTROL_POLICY_ID,
        "treatment": GENC6_TREATMENT_POLICY_ID,
        "reserve": GENC6_RESERVE_ID,
        "mandatory_dimensions": [item.value for item in _MANDATORY_KINDS],
        "optional_dimensions": [
            item.value for item in _OPTIONAL_COMPARABLE_KINDS
        ],
        "control_rule": (
            "max adjusted expected value per stop-risk-minute; "
            "tie value/risk then adjusted value then signal fingerprint"
        ),
        "treatment_rule": (
            "unique non-compensatory Pareto dominator across active dimensions "
            "AND expected net value per capital > capital-eligible reserve value; "
            "else RESERVE_NO_DEPLOYMENT"
        ),
        "one_marginal_action_per_clearing": True,
        "trader_identity_priority": False,
        "equal_budget_rule": False,
        "cross_account_transfer": False,
        "outcome_aware": False,
        "runtime_authority": False,
        "risk_authority": False,
        "execution_authority": False,
    }
    raw = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
    ).encode()
    return "sha256:" + hashlib.sha256(raw).hexdigest()


def build_genc6_portfolio_state(
    *,
    snapshot_id: str,
    decision_at: datetime,
    portfolio: AccountCoreCompoundPortfolio,
    t19_ledger: PortfolioAllocationLedger,
    context_facts: tuple[Genc6CapitalEvidenceFact, ...] = (),
) -> Genc6PortfolioStateSnapshot:
    if not isinstance(portfolio, AccountCoreCompoundPortfolio):
        raise CiboCompoundCapitalError(
            "GEN-C6 requires canonical Core Compound Portfolio"
        )
    if not isinstance(t19_ledger, PortfolioAllocationLedger):
        raise CiboCompoundCapitalError(
            "GEN-C6 requires canonical T19 allocation ledger"
        )
    remaining = t19_ledger.remaining_budget()
    current_capacity = (
        portfolio.compoundable_usd
        + portfolio.active_compound_capacity_usd
        + portfolio.released_compound_capital_usd
    )
    return Genc6PortfolioStateSnapshot(
        snapshot_id=snapshot_id,
        decision_at=decision_at,
        account_identity=portfolio.account_identity,
        portfolio_sha256=_portfolio_sha256(portfolio),
        t19_ledger_sha256=_t19_ledger_sha256(t19_ledger),
        current_compound_capacity_usd=current_capacity,
        available_compound_capital_usd=current_capacity,
        protected_floor_usd=(
            portfolio.protected_floor_ledger.policy_protected_floor_usd
        ),
        strategic_reserve_usd=portfolio.strategic_reserve_usd,
        opportunity_reserve_usd=portfolio.opportunity_reserve_usd,
        deployed_compound_capital_usd=(
            portfolio.deployed_compound_capital_usd
        ),
        t19_stop_risk_headroom_usd=remaining.stop_risk_headroom_usd,
        t19_margin_headroom_usd=remaining.margin_headroom_usd,
        t19_concentration_headroom=remaining.concentration_limit_by_group,
        active_t19_reservation_count=len(t19_ledger.active_reservations),
        context_facts=context_facts,
        runtime_authority=False,
        risk_authority=False,
        execution_authority=False,
    )


def build_capital_scarcity_event(
    *,
    event_id: str,
    decision_at: datetime,
    portfolio_state: Genc6PortfolioStateSnapshot,
    candidates: tuple[Genc6MarginalCapitalCandidate, ...],
    reserve_alternative: Genc6ReserveAlternative,
) -> CapitalScarcityEvent:
    valid = tuple(item for item in candidates if item.valid_at_decision)
    eligible = tuple(
        item
        for item in valid
        if not _candidate_blockers(item, portfolio_state)
    )
    total_requested = sum(
        (item.requested_capital_usd for item in eligible),
        Decimal(0),
    )
    shortfall = max(
        Decimal(0),
        total_requested - portfolio_state.available_compound_capital_usd,
    )
    intensity = (
        Decimal(0)
        if total_requested <= 0
        else shortfall / total_requested
    )
    return CapitalScarcityEvent(
        event_id=event_id,
        account_identity=portfolio_state.account_identity,
        decision_at=decision_at,
        portfolio_state=portfolio_state,
        candidates=candidates,
        reserve_alternative=reserve_alternative,
        candidate_set_sha256=genc6_candidate_set_sha256(candidates),
        simultaneously_valid_count=len(valid),
        eligible_candidate_count=len(eligible),
        available_capital_usd=(
            portfolio_state.available_compound_capital_usd
        ),
        total_requested_capital_usd=total_requested,
        capital_shortfall_usd=shortfall,
        mutually_fundable_candidate_count=_max_mutually_fundable_count(
            eligible,
            portfolio_state,
        ),
        competition_intensity=intensity,
        true_scarcity=(
            len(eligible) >= 2
            and total_requested
            > portfolio_state.available_compound_capital_usd
        ),
    )


def evaluate_genc6_internal_capital_market_shadow(
    *,
    event: CapitalScarcityEvent,
    decision_id: str,
) -> Genc6InternalCapitalMarketDecision:
    if not isinstance(event, CapitalScarcityEvent):
        raise CiboCompoundCapitalError(
            "GEN-C6 requires canonical scarcity event"
        )
    if not decision_id:
        raise CiboCompoundCapitalError(
            "GEN-C6 decision id is required"
        )

    legal: list[Genc6MarginalCapitalCandidate] = []
    blockers: list[str] = []
    for candidate in event.candidates:
        reasons = _candidate_blockers(candidate, event.portfolio_state)
        if reasons:
            blockers.extend(
                f"{candidate.candidate_id}:{reason}" for reason in reasons
            )
        else:
            legal.append(candidate)

    control_candidate = _control_choice(tuple(legal))
    active_dimensions = _active_treatment_dimensions(tuple(legal))
    treatment_candidate, treatment_reason = _treatment_choice(
        tuple(legal),
        active_dimensions=active_dimensions,
        reserve_alternative=event.reserve_alternative,
    )

    if control_candidate is None:
        control_action = Genc6Action.RESERVE_NO_DEPLOYMENT
        control_id = None
        control_amount = Decimal(0)
        control_reason = "NO_POSITIVE_LEGAL_T09_T18_STYLE_CANDIDATE"
    else:
        control_action = Genc6Action.ALLOCATE_MARGINAL_UNIT
        control_id = control_candidate.candidate_id
        control_amount = control_candidate.requested_capital_usd
        control_reason = "T09_T18_STYLE_MAX_ADJUSTED_VALUE_PER_RISK_MINUTE"

    if treatment_candidate is None:
        treatment_action = Genc6Action.RESERVE_NO_DEPLOYMENT
        treatment_id = None
        treatment_amount = Decimal(0)
    else:
        treatment_action = Genc6Action.ALLOCATE_MARGINAL_UNIT
        treatment_id = treatment_candidate.candidate_id
        treatment_amount = treatment_candidate.requested_capital_usd

    reserve_amount = _reserve_atomic_amount(event)
    candidate_shas = tuple(
        marginal_capital_utility_evidence_sha256(
            item.marginal_evidence
        )
        for item in sorted(event.candidates, key=lambda row: row.candidate_id)
    )
    genc5_shas = tuple(
        item.genc5_seal.decision_sha256
        for item in sorted(event.candidates, key=lambda row: row.candidate_id)
    )
    return Genc6InternalCapitalMarketDecision(
        market_id=GENC6_MARKET_ID,
        policy_id=GENC6_POLICY_ID,
        policy_sha256=genc6_policy_sha256(),
        policy_frozen_at=GENC6_POLICY_FROZEN_AT,
        decision_id=decision_id,
        scarcity_event_id=event.event_id,
        decision_at=event.decision_at,
        account_provider_key=event.account_identity.provider_key,
        account_ref=event.account_identity.account_ref,
        candidate_set_sha256=event.candidate_set_sha256,
        candidate_evidence_sha256s=candidate_shas,
        genc5_decision_sha256s=genc5_shas,
        portfolio_state_sha256=genc6_portfolio_state_sha256(
            event.portfolio_state
        ),
        t19_ledger_sha256=event.portfolio_state.t19_ledger_sha256,
        available_capital_usd=event.available_capital_usd,
        true_scarcity=event.true_scarcity,
        control_action=control_action,
        control_candidate_id=control_id,
        control_amount_usd=control_amount,
        treatment_action=treatment_action,
        treatment_candidate_id=treatment_id,
        treatment_amount_usd=treatment_amount,
        reserve_amount_usd=reserve_amount,
        active_comparable_dimensions=active_dimensions,
        control_reason=control_reason,
        treatment_reason=treatment_reason,
        blocker_codes=tuple(sorted(set(blockers))),
        treatment_differs_from_control=(
            control_action != treatment_action
            or control_id != treatment_id
            or control_amount != treatment_amount
        ),
        outcome_present_at_seal=False,
        runtime_authority=False,
        risk_authority=False,
        execution_authority=False,
        live_authority=False,
        real_capital_authority=False,
    )


def genc6_candidate_set_sha256(
    candidates: tuple[Genc6MarginalCapitalCandidate, ...],
) -> str:
    payload = [
        {
            "candidate_id": item.candidate_id,
            "account": {
                "provider_key": item.account_identity.provider_key,
                "account_ref": item.account_identity.account_ref,
            },
            "trader_id": item.trader_id.value,
            "qore_symbol": item.qore_symbol,
            "provider_symbol": item.provider_symbol,
            "signal_fingerprint": item.signal_fingerprint,
            "decision_at": item.decision_at.isoformat(),
            "valid_from": item.valid_from.isoformat(),
            "valid_until": item.valid_until.isoformat(),
            "technical_valid": item.technical_valid,
            "cancelled": item.cancelled,
            "marginal_unit_index": item.marginal_unit_index,
            "concentration_group": item.concentration_group,
            "marginal_evidence_sha256": (
                marginal_capital_utility_evidence_sha256(
                    item.marginal_evidence
                )
            ),
            "genc5_decision_sha256": item.genc5_seal.decision_sha256,
            "provider_action": _provider_action_payload(
                item.provider_action
            ),
            "facts": [_fact_payload(fact) for fact in item.comparable_facts],
        }
        for item in sorted(candidates, key=lambda row: row.candidate_id)
    ]
    raw = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
    ).encode()
    return "sha256:" + hashlib.sha256(raw).hexdigest()


def genc6_portfolio_state_sha256(
    state: Genc6PortfolioStateSnapshot,
) -> str:
    payload = {
        "snapshot_id": state.snapshot_id,
        "decision_at": state.decision_at.isoformat(),
        "account": {
            "provider_key": state.account_identity.provider_key,
            "account_ref": state.account_identity.account_ref,
            "environment": state.account_identity.environment.value,
            "provider_program": state.account_identity.provider_program,
        },
        "portfolio_sha256": state.portfolio_sha256,
        "t19_ledger_sha256": state.t19_ledger_sha256,
        "current_compound_capacity_usd": str(
            state.current_compound_capacity_usd
        ),
        "available_compound_capital_usd": str(
            state.available_compound_capital_usd
        ),
        "protected_floor_usd": str(state.protected_floor_usd),
        "strategic_reserve_usd": str(state.strategic_reserve_usd),
        "opportunity_reserve_usd": str(state.opportunity_reserve_usd),
        "deployed_compound_capital_usd": str(
            state.deployed_compound_capital_usd
        ),
        "t19_stop_risk_headroom_usd": str(
            state.t19_stop_risk_headroom_usd
        ),
        "t19_margin_headroom_usd": str(
            state.t19_margin_headroom_usd
        ),
        "t19_concentration_headroom": [
            [name, str(value)]
            for name, value in state.t19_concentration_headroom
        ],
        "active_t19_reservation_count": state.active_t19_reservation_count,
        "context_facts": [
            _fact_payload(item) for item in state.context_facts
        ],
    }
    raw = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
    ).encode()
    return "sha256:" + hashlib.sha256(raw).hexdigest()


def _candidate_blockers(
    candidate: Genc6MarginalCapitalCandidate,
    state: Genc6PortfolioStateSnapshot,
) -> tuple[str, ...]:
    reasons: list[str] = []
    if not candidate.valid_at_decision:
        reasons.append("OPPORTUNITY_NOT_VALID_AT_DECISION")
    if not candidate.provider_action.eligible_for_capital_use:
        reasons.append("PROVIDER_FEASIBILITY_EVIDENCE_NOT_CAPITAL_ELIGIBLE")
    elif not candidate.provider_action.feasible:
        reasons.append("PROVIDER_ACTION_NOT_FEASIBLE")
    if not candidate.mandatory_facts_capital_eligible():
        reasons.append("MANDATORY_CAPITAL_EVIDENCE_NOT_ELIGIBLE")
    if not candidate.genc5_forwarded_exact_amount():
        reasons.append("GENC5_EXACT_AMOUNT_NOT_FORWARDED")
    if candidate.requested_capital_usd > state.available_compound_capital_usd:
        reasons.append("ACCOUNT_LOCAL_COMPOUND_CAPITAL_INSUFFICIENT")
    if candidate.stop_risk_usd > state.t19_stop_risk_headroom_usd:
        reasons.append("T19_STOP_RISK_HEADROOM_INSUFFICIENT")
    if candidate.margin_usd > state.t19_margin_headroom_usd:
        reasons.append("T19_MARGIN_HEADROOM_INSUFFICIENT")
    group_headroom = state.concentration_headroom(
        candidate.concentration_group
    )
    if (
        group_headroom is not None
        and candidate.concentration_risk_usd > group_headroom
    ):
        reasons.append("T19_CONCENTRATION_HEADROOM_INSUFFICIENT")
    provider_fact = candidate.fact(
        Genc6EvidenceKind.PROVIDER_CONSTRAINT_PRESSURE
    )
    if (
        provider_fact is None
        or not provider_fact.eligible_for_capital_use
        or provider_fact.evidence_sha256
        != candidate.provider_action.evidence_sha256
    ):
        reasons.append("PROVIDER_PRESSURE_EVIDENCE_BINDING_DRIFT")
    return tuple(reasons)


def _control_choice(
    candidates: tuple[Genc6MarginalCapitalCandidate, ...],
) -> Genc6MarginalCapitalCandidate | None:
    positive = tuple(
        item for item in candidates if item.adjusted_expected_net_value_usd > 0
    )
    if not positive:
        return None
    return sorted(
        positive,
        key=lambda item: (
            -item.control_risk_time_score,
            -item.control_value_per_risk,
            -item.adjusted_expected_net_value_usd,
            item.signal_fingerprint,
        ),
    )[0]


def _active_treatment_dimensions(
    candidates: tuple[Genc6MarginalCapitalCandidate, ...],
) -> tuple[Genc6EvidenceKind, ...]:
    active = list(_MANDATORY_KINDS)
    if not candidates:
        return tuple(active)
    for kind in _OPTIONAL_COMPARABLE_KINDS:
        facts = tuple(item.fact(kind) for item in candidates)
        if all(
            fact is not None and fact.eligible_for_capital_use
            for fact in facts
        ):
            active.append(kind)
    return tuple(active)


def _treatment_choice(
    candidates: tuple[Genc6MarginalCapitalCandidate, ...],
    *,
    active_dimensions: tuple[Genc6EvidenceKind, ...],
    reserve_alternative: Genc6ReserveAlternative,
) -> tuple[Genc6MarginalCapitalCandidate | None, str]:
    reserve_value = _capital_eligible_reserve_value(reserve_alternative)
    if reserve_value is None:
        return None, "RESERVE_VALUE_NOT_CAPITAL_ELIGIBLE_KEEP_RESERVE"

    positive = tuple(
        item for item in candidates if item.adjusted_expected_net_value_usd > 0
    )
    if not positive:
        return None, "NO_POSITIVE_LEGAL_CANDIDATE_KEEP_RESERVE"

    if len(positive) == 1:
        winner = positive[0]
    else:
        winners = tuple(
            left
            for left in positive
            if all(
                left is right
                or _dominates(
                    left,
                    right,
                    active_dimensions=active_dimensions,
                )
                for right in positive
            )
        )
        if len(winners) != 1:
            return None, "NO_UNIQUE_ROBUST_PARETO_DOMINATOR_KEEP_RESERVE"
        winner = winners[0]

    expected_value_fact = winner.fact(
        Genc6EvidenceKind.EXPECTED_NET_VALUE_PER_CAPITAL
    )
    if (
        expected_value_fact is None
        or not expected_value_fact.eligible_for_capital_use
    ):
        return None, "WINNER_EXPECTED_VALUE_NOT_CAPITAL_ELIGIBLE_KEEP_RESERVE"
    if expected_value_fact.value <= reserve_value:
        return None, "RESERVE_VALUE_NOT_BEATEN_KEEP_RESERVE"
    return winner, "UNIQUE_ROBUST_PARETO_DOMINATOR_BEATS_RESERVE_VALUE"


def _capital_eligible_reserve_value(
    reserve: Genc6ReserveAlternative,
) -> Decimal | None:
    rows = tuple(
        item
        for item in reserve.evidence_facts
        if item.kind is Genc6EvidenceKind.RESERVE_VALUE
    )
    if not rows:
        return None
    fact = rows[0]
    if not fact.eligible_for_capital_use:
        return None
    return fact.value


def _dominates(
    left: Genc6MarginalCapitalCandidate,
    right: Genc6MarginalCapitalCandidate,
    *,
    active_dimensions: tuple[Genc6EvidenceKind, ...],
) -> bool:
    strict = False
    for kind in active_dimensions:
        left_fact = left.fact(kind)
        right_fact = right.fact(kind)
        if left_fact is None or right_fact is None:
            return False
        if left_fact.direction is Genc6EvidenceDirection.HIGHER_IS_BETTER:
            if left_fact.value < right_fact.value:
                return False
            if left_fact.value > right_fact.value:
                strict = True
        else:
            if left_fact.value > right_fact.value:
                return False
            if left_fact.value < right_fact.value:
                strict = True
    return strict


def _reserve_atomic_amount(event: CapitalScarcityEvent) -> Decimal:
    valid_amounts = tuple(
        item.requested_capital_usd
        for item in event.candidates
        if item.valid_at_decision and item.requested_capital_usd > 0
    )
    if not valid_amounts:
        return event.available_capital_usd
    return min(event.available_capital_usd, min(valid_amounts))


def _max_mutually_fundable_count(
    candidates: tuple[Genc6MarginalCapitalCandidate, ...],
    state: Genc6PortfolioStateSnapshot,
) -> int:
    best = 0
    for size in range(1, len(candidates) + 1):
        for subset in combinations(candidates, size):
            capital = sum(
                (item.requested_capital_usd for item in subset),
                Decimal(0),
            )
            stop_risk = sum(
                (item.stop_risk_usd for item in subset),
                Decimal(0),
            )
            margin = sum(
                (item.margin_usd for item in subset),
                Decimal(0),
            )
            if capital > state.available_compound_capital_usd:
                continue
            if stop_risk > state.t19_stop_risk_headroom_usd:
                continue
            if margin > state.t19_margin_headroom_usd:
                continue
            groups: dict[str, Decimal] = {}
            feasible = True
            for item in subset:
                groups[item.concentration_group] = (
                    groups.get(item.concentration_group, Decimal(0))
                    + item.concentration_risk_usd
                )
            for group, used in groups.items():
                limit = state.concentration_headroom(group)
                if limit is not None and used > limit:
                    feasible = False
                    break
            if feasible:
                best = max(best, size)
    return best


def _portfolio_sha256(portfolio: AccountCoreCompoundPortfolio) -> str:
    payload = {
        "account": {
            "provider_key": portfolio.account_identity.provider_key,
            "account_ref": portfolio.account_identity.account_ref,
            "environment": portfolio.account_identity.environment.value,
            "provider_program": portfolio.account_identity.provider_program,
        },
        "partition_usd": str(portfolio.current_partition_usd),
        "economic_value_usd": str(portfolio.current_economic_value_usd),
        "compoundable_usd": str(portfolio.compoundable_usd),
        "active_compound_capacity_usd": str(
            portfolio.active_compound_capacity_usd
        ),
        "released_compound_capital_usd": str(
            portfolio.released_compound_capital_usd
        ),
        "deployed_compound_capital_usd": str(
            portfolio.deployed_compound_capital_usd
        ),
        "strategic_reserve_usd": str(portfolio.strategic_reserve_usd),
        "opportunity_reserve_usd": str(portfolio.opportunity_reserve_usd),
        "policy_protected_floor_usd": str(
            portfolio.protected_floor_ledger.policy_protected_floor_usd
        ),
    }
    raw = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
    ).encode()
    return "sha256:" + hashlib.sha256(raw).hexdigest()


def _t19_ledger_sha256(ledger: PortfolioAllocationLedger) -> str:
    payload = {
        "total_stop_risk_capacity_usd": str(
            ledger.total_stop_risk_capacity_usd
        ),
        "total_margin_capacity_usd": str(
            ledger.total_margin_capacity_usd
        ),
        "concentration_limit_by_group": [
            [name, str(value)]
            for name, value in ledger.concentration_limit_by_group
        ],
        "reservations": [
            {
                "signal_fingerprint": item.signal_fingerprint,
                "trader_id": item.trader_id.value,
                "qore_symbol": item.qore_symbol,
                "stop_risk_usd": str(item.stop_risk_usd),
                "margin_usd": str(item.margin_usd),
                "concentration_group": item.concentration_group,
                "concentration_risk_usd": str(
                    item.concentration_risk_usd
                ),
                "state": item.state.value,
            }
            for item in ledger.reservations
        ],
    }
    raw = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
    ).encode()
    return "sha256:" + hashlib.sha256(raw).hexdigest()


def _provider_action_payload(
    evidence: Genc6ProviderCapitalActionEvidence,
) -> dict[str, object]:
    return {
        "evidence_id": evidence.evidence_id,
        "evidence_sha256": evidence.evidence_sha256,
        "produced_at": evidence.produced_at.isoformat(),
        "observed_at": evidence.observed_at.isoformat(),
        "source": evidence.source,
        "policy_version": evidence.policy_version,
        "account": {
            "provider_key": evidence.account_identity.provider_key,
            "account_ref": evidence.account_identity.account_ref,
        },
        "qore_symbol": evidence.qore_symbol,
        "provider_symbol": evidence.provider_symbol,
        "requested_capital_usd": str(evidence.requested_capital_usd),
        "executable_volume": str(evidence.executable_volume),
        "minimum_executable_volume": str(
            evidence.minimum_executable_volume
        ),
        "maximum_volume": str(evidence.maximum_volume),
        "volume_step": str(evidence.volume_step),
        "minimum_execution_steps": evidence.minimum_execution_steps,
        "projected_stop_risk_usd": str(
            evidence.projected_stop_risk_usd
        ),
        "minimum_stop_risk_usd": str(evidence.minimum_stop_risk_usd),
        "projected_margin_usd": str(evidence.projected_margin_usd),
        "minimum_margin_usd": str(evidence.minimum_margin_usd),
        "projected_execution_cost_usd": str(
            evidence.projected_execution_cost_usd
        ),
        "feasible": evidence.feasible,
        "use": evidence.use.value,
        "reason": evidence.reason,
    }


def _fact_payload(fact: Genc6CapitalEvidenceFact) -> dict[str, object]:
    return {
        "fact_id": fact.fact_id,
        "kind": fact.kind.value,
        "value": str(fact.value),
        "direction": fact.direction.value,
        "evidence_sha256": fact.evidence_sha256,
        "produced_at": fact.produced_at.isoformat(),
        "observed_at": fact.observed_at.isoformat(),
        "source": fact.source,
        "policy_version": fact.policy_version,
        "calibration_lineage": fact.calibration_lineage,
        "use": fact.use.value,
        "model_identity": fact.model_identity,
        "calibrated": fact.calibrated,
        "oos_validated": fact.oos_validated,
    }


def _unique_fact_kinds(
    facts: tuple[Genc6CapitalEvidenceFact, ...],
) -> None:
    if any(
        not isinstance(item, Genc6CapitalEvidenceFact) for item in facts
    ):
        raise CiboCompoundCapitalError(
            "GEN-C6 facts must be canonical evidence facts"
        )
    kinds = tuple(item.kind for item in facts)
    if len(kinds) != len(set(kinds)):
        raise CiboCompoundCapitalError(
            "GEN-C6 evidence fact kinds must be unique"
        )


def _validate_action(
    *,
    action: Genc6Action,
    candidate_id: str | None,
    amount: Decimal,
    label: str,
) -> None:
    if type(action) is not Genc6Action:
        raise CiboCompoundCapitalError(
            f"GEN-C6 {label} action is invalid"
        )
    if action is Genc6Action.ALLOCATE_MARGINAL_UNIT:
        if not candidate_id or amount <= 0:
            raise CiboCompoundCapitalError(
                f"GEN-C6 {label} allocation requires candidate/amount"
            )
    else:
        if candidate_id is not None or amount != 0:
            raise CiboCompoundCapitalError(
                f"GEN-C6 {label} reserve must have no candidate/amount"
            )


def _sha(value: str, name: str) -> None:
    if (
        not isinstance(value, str)
        or not value.startswith("sha256:")
        or len(value) != 71
        or any(char not in "0123456789abcdef" for char in value[7:])
    ):
        raise CiboCompoundCapitalError(
            f"GEN-C6 {name} must be canonical SHA-256"
        )


def _aware(value: datetime, name: str) -> None:
    if (
        not isinstance(value, datetime)
        or value.tzinfo is None
        or value.utcoffset() is None
    ):
        raise CiboCompoundCapitalError(
            f"GEN-C6 {name} must be timezone-aware"
        )


def _nonnegative(value: Decimal, name: str) -> None:
    if (
        not isinstance(value, Decimal)
        or not value.is_finite()
        or value < 0
    ):
        raise CiboCompoundCapitalError(
            f"GEN-C6 {name} must be finite non-negative Decimal"
        )
