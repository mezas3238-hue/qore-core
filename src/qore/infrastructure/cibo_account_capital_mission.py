"""Account-aware capital mission intelligence for CIBO CMA.

CIBO derives its capital mission from authoritative account/provider context.
No issue, ticket, per-trade flag, or Trader sizing input selects the mission.

The mission changes CIBO's objective and CE2I activation envelope while keeping
provider constraints, capital accounting, anti-cheating laws and sovereign Risk
active in every environment.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from re import fullmatch

from qore.infrastructure.cibo_ce2i_tool_registry import (
    Ce2iToolContract,
    ToolMaturity,
)
from qore.infrastructure.market_test_environment import MarketRuntimeEnvironment


class CiboAccountMissionError(ValueError):
    """Account context cannot be mapped to a safe CIBO capital mission."""


class CiboCapitalMission(StrEnum):
    FUNDED_SURVIVAL_COMPOUND = "FUNDED_SURVIVAL_COMPOUND"
    PRODUCTION_SURVIVAL_COMPOUND = "PRODUCTION_SURVIVAL_COMPOUND"
    DEMO_CAPABILITY_DISCOVERY = "DEMO_CAPABILITY_DISCOVERY"
    TEST_VALIDATION = "TEST_VALIDATION"
    SANDBOX_SIMULATION = "SANDBOX_SIMULATION"


class CiboCapitalObjective(StrEnum):
    SURVIVAL_FIRST = "SURVIVAL_FIRST"
    ROBUST_COMPOUNDING = "ROBUST_COMPOUNDING"
    CAPABILITY_DISCOVERY = "CAPABILITY_DISCOVERY"
    VALIDATION = "VALIDATION"
    SIMULATION = "SIMULATION"


class Ce2iActivationScope(StrEnum):
    EXTERNAL_CAPITAL_GATED = "EXTERNAL_CAPITAL_GATED"
    ALL_EXECUTABLE_RESEARCH = "ALL_EXECUTABLE_RESEARCH"
    VALIDATION_ONLY = "VALIDATION_ONLY"
    SIMULATION_ONLY = "SIMULATION_ONLY"


@dataclass(frozen=True, slots=True)
class CiboAccountCapitalIdentity:
    provider_key: str
    account_ref: str
    environment: MarketRuntimeEnvironment
    provider_program: str | None = None

    def __post_init__(self) -> None:
        if fullmatch(r"[a-z][a-z0-9._-]*", self.provider_key) is None:
            raise CiboAccountMissionError(
                "provider_key must use canonical lowercase syntax"
            )
        if not self.account_ref:
            raise CiboAccountMissionError("account_ref is required")
        if type(self.environment) is not MarketRuntimeEnvironment:
            raise CiboAccountMissionError(
                "environment must be MarketRuntimeEnvironment"
            )
        if self.provider_program is not None and not self.provider_program.strip():
            raise CiboAccountMissionError(
                "provider_program cannot be blank"
            )


@dataclass(frozen=True, slots=True)
class CiboCapitalMissionPolicy:
    mission: CiboCapitalMission
    primary_objective: CiboCapitalObjective
    secondary_objective: CiboCapitalObjective
    ce2i_scope: Ce2iActivationScope
    minimum_seed_required: bool
    sovereign_risk_required: bool
    provider_constraints_required: bool
    durable_capital_accounting_required: bool
    allow_research_tool_execution: bool
    allow_multi_tool_experiments: bool
    allow_cross_trader_competition: bool
    allow_self_financing_expansion: bool
    allow_original_base_capital_reallocation: bool
    capability_measurement_enabled: bool
    preserve_optionality_priority: bool
    rationale: str

    def __post_init__(self) -> None:
        for name in (
            "minimum_seed_required",
            "sovereign_risk_required",
            "provider_constraints_required",
            "durable_capital_accounting_required",
            "allow_research_tool_execution",
            "allow_multi_tool_experiments",
            "allow_cross_trader_competition",
            "allow_self_financing_expansion",
            "allow_original_base_capital_reallocation",
            "capability_measurement_enabled",
            "preserve_optionality_priority",
        ):
            if type(getattr(self, name)) is not bool:
                raise CiboAccountMissionError(f"{name} must be bool")
        if not self.rationale:
            raise CiboAccountMissionError("mission policy rationale required")
        if (
            not self.sovereign_risk_required
            or not self.provider_constraints_required
            or not self.durable_capital_accounting_required
        ):
            raise CiboAccountMissionError(
                "no CIBO mission may disable Risk/provider/accounting controls"
            )


_FUNDED_PROVIDER_PROGRAMS: frozenset[tuple[str, str]] = frozenset(
    {
        ("fundednext", "stellar-instant"),
        ("fundednext", "stellar_instant"),
    }
)


def derive_cibo_capital_mission(
    identity: CiboAccountCapitalIdentity,
) -> CiboCapitalMissionPolicy:
    """Derive CIBO behavior from account facts, never from an issue/manual ticket."""

    if not isinstance(identity, CiboAccountCapitalIdentity):
        raise CiboAccountMissionError(
            "identity must be CiboAccountCapitalIdentity"
        )

    if identity.environment is MarketRuntimeEnvironment.DEMO:
        return _demo_capability_policy()

    if identity.environment is MarketRuntimeEnvironment.TEST:
        return _test_validation_policy()

    if identity.environment is MarketRuntimeEnvironment.SANDBOX:
        return _sandbox_policy()

    if identity.environment is MarketRuntimeEnvironment.PRODUCTION:
        normalized_program = (
            identity.provider_program.strip().lower()
            if identity.provider_program is not None
            else ""
        )
        if (
            identity.provider_key,
            normalized_program,
        ) in _FUNDED_PROVIDER_PROGRAMS or identity.provider_key == "fundednext":
            return _funded_survival_policy()
        return _production_survival_policy()

    raise CiboAccountMissionError("unsupported account environment")


def ce2i_tool_allowed_for_mission(
    tool: Ce2iToolContract,
    policy: CiboCapitalMissionPolicy,
) -> bool:
    """Return whether an implemented CE2I tool may execute under this mission."""

    if not isinstance(tool, Ce2iToolContract):
        raise CiboAccountMissionError("tool must be Ce2iToolContract")
    if not isinstance(policy, CiboCapitalMissionPolicy):
        raise CiboAccountMissionError(
            "policy must be CiboCapitalMissionPolicy"
        )

    if tool.maturity is ToolMaturity.REJECTED:
        return False
    if tool.maturity is ToolMaturity.ARCHITECTURE_ONLY:
        return False

    if policy.ce2i_scope is Ce2iActivationScope.ALL_EXECUTABLE_RESEARCH:
        return tool.maturity in {
            ToolMaturity.CONTRACT_IMPLEMENTED,
            ToolMaturity.RESEARCH_VALIDATED,
            ToolMaturity.HOLDOUT_VALIDATED,
            ToolMaturity.SHADOW_VALIDATED,
        }

    if policy.ce2i_scope is Ce2iActivationScope.EXTERNAL_CAPITAL_GATED:
        if tool.code in {"T01", "T19", "T20"}:
            return tool.maturity in {
                ToolMaturity.CONTRACT_IMPLEMENTED,
                ToolMaturity.RESEARCH_VALIDATED,
                ToolMaturity.HOLDOUT_VALIDATED,
                ToolMaturity.SHADOW_VALIDATED,
            }
        return tool.maturity is ToolMaturity.SHADOW_VALIDATED

    if policy.ce2i_scope is Ce2iActivationScope.VALIDATION_ONLY:
        return tool.maturity in {
            ToolMaturity.RESEARCH_VALIDATED,
            ToolMaturity.HOLDOUT_VALIDATED,
            ToolMaturity.SHADOW_VALIDATED,
        }

    if policy.ce2i_scope is Ce2iActivationScope.SIMULATION_ONLY:
        return True

    raise CiboAccountMissionError("unsupported CE2I activation scope")


def _funded_survival_policy() -> CiboCapitalMissionPolicy:
    return CiboCapitalMissionPolicy(
        mission=CiboCapitalMission.FUNDED_SURVIVAL_COMPOUND,
        primary_objective=CiboCapitalObjective.SURVIVAL_FIRST,
        secondary_objective=CiboCapitalObjective.ROBUST_COMPOUNDING,
        ce2i_scope=Ce2iActivationScope.EXTERNAL_CAPITAL_GATED,
        minimum_seed_required=True,
        sovereign_risk_required=True,
        provider_constraints_required=True,
        durable_capital_accounting_required=True,
        allow_research_tool_execution=False,
        allow_multi_tool_experiments=False,
        allow_cross_trader_competition=True,
        allow_self_financing_expansion=True,
        allow_original_base_capital_reallocation=False,
        capability_measurement_enabled=False,
        preserve_optionality_priority=True,
        rationale=(
            "external funded capital: preserve survival envelope first, "
            "compound only through sufficiently validated capital tools"
        ),
    )


def _production_survival_policy() -> CiboCapitalMissionPolicy:
    return CiboCapitalMissionPolicy(
        mission=CiboCapitalMission.PRODUCTION_SURVIVAL_COMPOUND,
        primary_objective=CiboCapitalObjective.SURVIVAL_FIRST,
        secondary_objective=CiboCapitalObjective.ROBUST_COMPOUNDING,
        ce2i_scope=Ce2iActivationScope.EXTERNAL_CAPITAL_GATED,
        minimum_seed_required=True,
        sovereign_risk_required=True,
        provider_constraints_required=True,
        durable_capital_accounting_required=True,
        allow_research_tool_execution=False,
        allow_multi_tool_experiments=False,
        allow_cross_trader_competition=True,
        allow_self_financing_expansion=True,
        allow_original_base_capital_reallocation=False,
        capability_measurement_enabled=False,
        preserve_optionality_priority=True,
        rationale=(
            "production capital: survival and robust compounding dominate "
            "capability exploration"
        ),
    )


def _demo_capability_policy() -> CiboCapitalMissionPolicy:
    return CiboCapitalMissionPolicy(
        mission=CiboCapitalMission.DEMO_CAPABILITY_DISCOVERY,
        primary_objective=CiboCapitalObjective.CAPABILITY_DISCOVERY,
        secondary_objective=CiboCapitalObjective.ROBUST_COMPOUNDING,
        ce2i_scope=Ce2iActivationScope.ALL_EXECUTABLE_RESEARCH,
        minimum_seed_required=True,
        sovereign_risk_required=True,
        provider_constraints_required=True,
        durable_capital_accounting_required=True,
        allow_research_tool_execution=True,
        allow_multi_tool_experiments=True,
        allow_cross_trader_competition=True,
        allow_self_financing_expansion=True,
        allow_original_base_capital_reallocation=True,
        capability_measurement_enabled=True,
        preserve_optionality_priority=False,
        rationale=(
            "DEMO capital exists to measure CIBO capability: exercise all "
            "implemented non-rejected CE2I tools under causal accounting and Risk"
        ),
    )


def _test_validation_policy() -> CiboCapitalMissionPolicy:
    return CiboCapitalMissionPolicy(
        mission=CiboCapitalMission.TEST_VALIDATION,
        primary_objective=CiboCapitalObjective.VALIDATION,
        secondary_objective=CiboCapitalObjective.SURVIVAL_FIRST,
        ce2i_scope=Ce2iActivationScope.VALIDATION_ONLY,
        minimum_seed_required=True,
        sovereign_risk_required=True,
        provider_constraints_required=True,
        durable_capital_accounting_required=True,
        allow_research_tool_execution=False,
        allow_multi_tool_experiments=False,
        allow_cross_trader_competition=True,
        allow_self_financing_expansion=True,
        allow_original_base_capital_reallocation=False,
        capability_measurement_enabled=True,
        preserve_optionality_priority=True,
        rationale="TEST environment validates evidence before broader deployment",
    )


def _sandbox_policy() -> CiboCapitalMissionPolicy:
    return CiboCapitalMissionPolicy(
        mission=CiboCapitalMission.SANDBOX_SIMULATION,
        primary_objective=CiboCapitalObjective.SIMULATION,
        secondary_objective=CiboCapitalObjective.CAPABILITY_DISCOVERY,
        ce2i_scope=Ce2iActivationScope.SIMULATION_ONLY,
        minimum_seed_required=False,
        sovereign_risk_required=True,
        provider_constraints_required=True,
        durable_capital_accounting_required=True,
        allow_research_tool_execution=True,
        allow_multi_tool_experiments=True,
        allow_cross_trader_competition=True,
        allow_self_financing_expansion=True,
        allow_original_base_capital_reallocation=True,
        capability_measurement_enabled=True,
        preserve_optionality_priority=False,
        rationale="SANDBOX permits simulation of the complete CIBO toolbox",
    )
