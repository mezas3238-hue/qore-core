"""Operating boundary between provider rules, QORE Risk, and execution routing.

This module deliberately does not issue a RiskAuthorization. It prepares the
provider budget and execution capability that QORE Risk must consume before a
CIBO request can become an executable order.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum

from qore.infrastructure.provider_contracts import (
    CHALLENGE_CONTRACTS,
    AutomationMode,
    ChallengeProgram,
    ChallengeStage,
    Provider,
    ProviderAccountSnapshot,
    ProviderContract,
    ProviderContractError,
    ProviderExecutionCapability,
    ProviderRiskBudget,
    RuleAuthority,
    TradingPlatform,
    evaluate_provider_budget,
    execution_capability,
)


class ExecutionRoute(StrEnum):
    AUTOMATED = "automated"
    MANUAL_HANDOFF = "manual-handoff"
    REJECT = "reject"


class BudgetRequestStatus(StrEnum):
    WITHIN_BUDGET = "within-budget"
    EXCEEDS_QORE_BUDGET = "exceeds-qore-budget"
    PROVIDER_BREACH = "provider-breach"
    ZERO_BUDGET = "zero-budget"


@dataclass(frozen=True, slots=True)
class QoreRiskOverlayPolicy:
    """Internal reserves that may only reduce provider-authorizable headroom."""

    policy_id: str
    daily_reserve_fraction: Decimal = Decimal(0)
    overall_reserve_fraction: Decimal = Decimal(0)

    def __post_init__(self) -> None:
        if not self.policy_id:
            raise ProviderContractError("QORE overlay policy_id must be non-empty")
        for name, value in (
            ("daily_reserve_fraction", self.daily_reserve_fraction),
            ("overall_reserve_fraction", self.overall_reserve_fraction),
        ):
            if not isinstance(value, Decimal) or not value.is_finite():
                raise ProviderContractError(f"{name} must be a finite Decimal")
            if not Decimal(0) <= value < Decimal(1):
                raise ProviderContractError(f"{name} must be in [0, 1)")


@dataclass(frozen=True, slots=True)
class EffectiveRiskBudget:
    """Provider hard budget after a QORE-only conservative reserve is applied."""

    contract_id: str
    provider_authority: RuleAuthority
    qore_authority: RuleAuthority
    provider_headroom: Decimal
    provider_daily_headroom: Decimal
    provider_overall_headroom: Decimal
    qore_daily_reserve: Decimal
    qore_overall_reserve: Decimal
    qore_daily_headroom: Decimal
    qore_overall_headroom: Decimal
    authorizable_headroom: Decimal
    provider_hard_breach: bool
    qore_suspended: bool

    def __post_init__(self) -> None:
        if self.provider_authority is not RuleAuthority.PROVIDER_RULE:
            raise ProviderContractError("provider authority provenance is invalid")
        if self.qore_authority is not RuleAuthority.QORE_POLICY:
            raise ProviderContractError("QORE authority provenance is invalid")
        values = (
            self.provider_headroom,
            self.provider_daily_headroom,
            self.provider_overall_headroom,
            self.qore_daily_reserve,
            self.qore_overall_reserve,
            self.qore_daily_headroom,
            self.qore_overall_headroom,
            self.authorizable_headroom,
        )
        if any(not isinstance(value, Decimal) or not value.is_finite() for value in values):
            raise ProviderContractError("effective risk values must be finite Decimal")
        if any(value < 0 for value in values):
            raise ProviderContractError("effective risk values cannot be negative")
        if self.authorizable_headroom > self.provider_headroom:
            raise ProviderContractError("QORE cannot enlarge provider headroom")
        if self.qore_daily_headroom > self.provider_daily_headroom:
            raise ProviderContractError("QORE cannot enlarge provider daily headroom")
        if self.qore_overall_headroom > self.provider_overall_headroom:
            raise ProviderContractError("QORE cannot enlarge provider overall headroom")


@dataclass(frozen=True, slots=True)
class ProviderAccountBinding:
    """Non-secret immutable identity required before an account can be routed."""

    binding_id: str
    contract_id: str
    provider: Provider
    program: ChallengeProgram
    stage: ChallengeStage
    platform: TradingPlatform
    initial_balance: Decimal
    rules_verified_on: str
    fundednext_ea_addon_enabled: bool = False
    enabled: bool = True

    def __post_init__(self) -> None:
        if not self.binding_id:
            raise ProviderContractError("binding_id must be non-empty")
        if self.contract_id not in CHALLENGE_CONTRACTS:
            raise ProviderContractError("unknown provider contract_id")
        if not isinstance(self.initial_balance, Decimal) or not self.initial_balance.is_finite():
            raise ProviderContractError("binding initial_balance must be finite Decimal")
        if self.initial_balance <= 0:
            raise ProviderContractError("binding initial_balance must be positive")
        if not self.rules_verified_on:
            raise ProviderContractError("binding requires provider rule verification date")
        contract = CHALLENGE_CONTRACTS[self.contract_id]
        if contract.provider is not self.provider:
            raise ProviderContractError("binding provider does not match contract")
        if contract.program is not self.program:
            raise ProviderContractError("binding program does not match contract")
        if contract.stage is not self.stage:
            raise ProviderContractError("binding stage does not match contract")
        if any(source.verified_on != self.rules_verified_on for source in contract.sources):
            raise ProviderContractError("binding rule version does not match contract sources")


@dataclass(frozen=True, slots=True)
class ProviderRouteDecision:
    binding_id: str
    contract_id: str
    route: ExecutionRoute
    capability: ProviderExecutionCapability
    reason: str
    activation_reverification_required: bool = True

    def __post_init__(self) -> None:
        if not self.reason:
            raise ProviderContractError("route decision requires a reason")
        if self.route is ExecutionRoute.AUTOMATED:
            if not self.capability.automated_order_submission_allowed:
                raise ProviderContractError("automated route requires automation capability")
        if self.route is ExecutionRoute.REJECT:
            if self.capability.automated_order_submission_allowed:
                raise ProviderContractError("reject route cannot expose automated capability")


@dataclass(frozen=True, slots=True)
class BudgetRequestCheck:
    status: BudgetRequestStatus
    requested_worst_case_loss: Decimal
    authorizable_headroom: Decimal
    within_provider_headroom: bool
    within_qore_headroom: bool
    reason: str

    def __post_init__(self) -> None:
        if not self.reason:
            raise ProviderContractError("budget request check requires a reason")
        if self.requested_worst_case_loss < 0:
            raise ProviderContractError("requested loss cannot be negative")
        if self.authorizable_headroom < 0:
            raise ProviderContractError("authorizable headroom cannot be negative")


def apply_qore_risk_overlay(
    provider_budget: ProviderRiskBudget,
    snapshot: ProviderAccountSnapshot,
    policy: QoreRiskOverlayPolicy,
) -> EffectiveRiskBudget:
    """Apply internal reserves without mutating or enlarging provider limits."""

    if not isinstance(provider_budget, ProviderRiskBudget):
        raise ProviderContractError("provider_budget must be ProviderRiskBudget")
    if not isinstance(snapshot, ProviderAccountSnapshot):
        raise ProviderContractError("snapshot must be ProviderAccountSnapshot")
    if not isinstance(policy, QoreRiskOverlayPolicy):
        raise ProviderContractError("policy must be QoreRiskOverlayPolicy")

    daily_reserve = snapshot.initial_balance * policy.daily_reserve_fraction
    overall_reserve = snapshot.initial_balance * policy.overall_reserve_fraction
    daily_headroom = max(Decimal(0), provider_budget.daily_headroom - daily_reserve)
    overall_headroom = max(Decimal(0), provider_budget.overall_headroom - overall_reserve)
    authorizable = min(daily_headroom, overall_headroom)
    if provider_budget.hard_breach:
        authorizable = Decimal(0)

    return EffectiveRiskBudget(
        contract_id=provider_budget.contract_id,
        provider_authority=RuleAuthority.PROVIDER_RULE,
        qore_authority=RuleAuthority.QORE_POLICY,
        provider_headroom=provider_budget.provider_headroom,
        provider_daily_headroom=provider_budget.daily_headroom,
        provider_overall_headroom=provider_budget.overall_headroom,
        qore_daily_reserve=daily_reserve,
        qore_overall_reserve=overall_reserve,
        qore_daily_headroom=daily_headroom,
        qore_overall_headroom=overall_headroom,
        authorizable_headroom=authorizable,
        provider_hard_breach=provider_budget.hard_breach,
        qore_suspended=authorizable <= 0,
    )


def evaluate_requested_loss_budget(
    provider_budget: ProviderRiskBudget,
    effective_budget: EffectiveRiskBudget,
    requested_worst_case_loss: Decimal,
) -> BudgetRequestCheck:
    """Budget gate for Risk consumption; this is explicitly not RiskAuthorization."""

    if not isinstance(requested_worst_case_loss, Decimal):
        raise ProviderContractError("requested_worst_case_loss must be Decimal")
    if not requested_worst_case_loss.is_finite() or requested_worst_case_loss < 0:
        raise ProviderContractError("requested_worst_case_loss must be finite and non-negative")
    if provider_budget.contract_id != effective_budget.contract_id:
        raise ProviderContractError("provider/effective budget contract mismatch")

    if provider_budget.hard_breach:
        return BudgetRequestCheck(
            status=BudgetRequestStatus.PROVIDER_BREACH,
            requested_worst_case_loss=requested_worst_case_loss,
            authorizable_headroom=Decimal(0),
            within_provider_headroom=False,
            within_qore_headroom=False,
            reason="provider-hard-loss-boundary-breached",
        )

    within_provider = requested_worst_case_loss <= provider_budget.provider_headroom
    within_qore = requested_worst_case_loss <= effective_budget.authorizable_headroom
    if effective_budget.authorizable_headroom <= 0:
        status = BudgetRequestStatus.ZERO_BUDGET
        reason = "qore-risk-headroom-exhausted"
    elif not within_qore:
        status = BudgetRequestStatus.EXCEEDS_QORE_BUDGET
        reason = "requested-loss-exceeds-effective-risk-headroom"
    else:
        status = BudgetRequestStatus.WITHIN_BUDGET
        reason = "request-fits-provider-and-qore-headroom"

    return BudgetRequestCheck(
        status=status,
        requested_worst_case_loss=requested_worst_case_loss,
        authorizable_headroom=effective_budget.authorizable_headroom,
        within_provider_headroom=within_provider,
        within_qore_headroom=within_qore,
        reason=reason,
    )


def resolve_contract(binding: ProviderAccountBinding) -> ProviderContract:
    """Resolve the exact frozen contract bound to an account."""

    return CHALLENGE_CONTRACTS[binding.contract_id]


def evaluate_bound_provider_budget(
    binding: ProviderAccountBinding,
    snapshot: ProviderAccountSnapshot,
) -> ProviderRiskBudget:
    """Evaluate provider budget only when account identity matches the snapshot."""

    if snapshot.initial_balance != binding.initial_balance:
        raise ProviderContractError("snapshot initial balance does not match binding")
    return evaluate_provider_budget(resolve_contract(binding), snapshot)


def resolve_execution_route(binding: ProviderAccountBinding) -> ProviderRouteDecision:
    """Resolve automatic/manual/reject route under current frozen provider rules."""

    contract = resolve_contract(binding)
    if not binding.enabled:
        capability = _rejected_capability(contract.provider, binding.platform, "binding-disabled")
        return ProviderRouteDecision(
            binding_id=binding.binding_id,
            contract_id=binding.contract_id,
            route=ExecutionRoute.REJECT,
            capability=capability,
            reason="provider-account-binding-disabled",
        )

    if contract.provider is Provider.FTMO:
        if binding.platform not in (
            TradingPlatform.CTRADER,
            TradingPlatform.MT4,
            TradingPlatform.MT5,
        ):
            capability = _rejected_capability(
                contract.provider,
                binding.platform,
                "ftmo-platform-not-frozen-for-qore-automation",
            )
            return ProviderRouteDecision(
                binding_id=binding.binding_id,
                contract_id=binding.contract_id,
                route=ExecutionRoute.REJECT,
                capability=capability,
                reason="unsupported-ftmo-qore-platform",
            )

    if contract.provider is Provider.FUNDEDNEXT:
        if binding.platform is TradingPlatform.UNKNOWN:
            capability = _rejected_capability(
                contract.provider,
                binding.platform,
                "fundednext-platform-unknown",
            )
            return ProviderRouteDecision(
                binding_id=binding.binding_id,
                contract_id=binding.contract_id,
                route=ExecutionRoute.REJECT,
                capability=capability,
                reason="unknown-fundednext-platform",
            )
        if binding.platform in (TradingPlatform.CTRADER, TradingPlatform.MATCH_TRADER):
            if binding.initial_balance >= Decimal("100000"):
                capability = _rejected_capability(
                    contract.provider,
                    binding.platform,
                    "fundednext-platform-account-size-unavailable",
                )
                return ProviderRouteDecision(
                    binding_id=binding.binding_id,
                    contract_id=binding.contract_id,
                    route=ExecutionRoute.REJECT,
                    capability=capability,
                    reason="fundednext-platform-unavailable-for-account-size",
                )
            capability = ProviderExecutionCapability(
                provider=contract.provider,
                platform=binding.platform,
                mode=AutomationMode.MANUAL_ONLY,
                automated_order_submission_allowed=False,
                reason="fundednext-platform-automation-prohibited",
            )
            return ProviderRouteDecision(
                binding_id=binding.binding_id,
                contract_id=binding.contract_id,
                route=ExecutionRoute.MANUAL_HANDOFF,
                capability=capability,
                reason="fundednext-provider-rules-require-manual-execution",
            )
        if binding.platform in (TradingPlatform.MT4, TradingPlatform.MT5):
            capability = ProviderExecutionCapability(
                provider=contract.provider,
                platform=binding.platform,
                mode=AutomationMode.CONDITIONAL,
                automated_order_submission_allowed=False,
                reason="fundednext-product-specific-automation-authority-unresolved",
            )
            return ProviderRouteDecision(
                binding_id=binding.binding_id,
                contract_id=binding.contract_id,
                route=ExecutionRoute.MANUAL_HANDOFF,
                capability=capability,
                reason="fundednext-exact-product-rule-reverification-required",
            )
        capability = _rejected_capability(
            contract.provider,
            binding.platform,
            "unsupported-fundednext-platform",
        )
        return ProviderRouteDecision(
            binding_id=binding.binding_id,
            contract_id=binding.contract_id,
            route=ExecutionRoute.REJECT,
            capability=capability,
            reason="unsupported-fundednext-platform",
        )

    capability = execution_capability(
        contract,
        platform=binding.platform,
        initial_balance=binding.initial_balance,
        fundednext_ea_addon_enabled=binding.fundednext_ea_addon_enabled,
    )
    if capability.automated_order_submission_allowed:
        route = ExecutionRoute.AUTOMATED
        reason = "provider-contract-allows-automated-submission"
    elif capability.mode in (AutomationMode.MANUAL_ONLY, AutomationMode.CONDITIONAL):
        route = ExecutionRoute.MANUAL_HANDOFF
        reason = "provider-contract-requires-manual-execution"
    else:
        route = ExecutionRoute.REJECT
        reason = "provider-platform-capability-fails-closed"

    return ProviderRouteDecision(
        binding_id=binding.binding_id,
        contract_id=binding.contract_id,
        route=route,
        capability=capability,
        reason=reason,
    )


def _rejected_capability(
    provider: Provider,
    platform: TradingPlatform,
    reason: str,
) -> ProviderExecutionCapability:
    return ProviderExecutionCapability(
        provider=provider,
        platform=platform,
        mode=AutomationMode.FAIL_CLOSED,
        automated_order_submission_allowed=False,
        reason=reason,
    )
