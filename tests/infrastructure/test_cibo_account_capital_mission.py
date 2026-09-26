# ruff: noqa: I001
from qore.infrastructure.cibo_account_capital_mission import (
    Ce2iActivationScope,
    CiboAccountCapitalIdentity,
    CiboCapitalMission,
    CiboCapitalObjective,
    ce2i_tool_allowed_for_mission,
    derive_cibo_capital_mission,
    fundednext_stellar_instant_identity,
    identity_from_market_test_account,
)
from qore.infrastructure.cibo_ce2i_tool_registry import (
    CE2I_TOOL_REGISTRY,
    ToolMaturity,
)
from qore.infrastructure.market_test_environment import (
    MarketRuntimeEnvironment,
    MarketTestAccountIdentity,
)


def _tool(code: str):
    return next(item for item in CE2I_TOOL_REGISTRY if item.code == code)


def test_fundednext_production_derives_survival_compound_automatically() -> None:
    policy = derive_cibo_capital_mission(
        CiboAccountCapitalIdentity(
            provider_key="fundednext",
            account_ref="stellar-instant-2k",
            environment=MarketRuntimeEnvironment.PRODUCTION,
            provider_program="stellar-instant",
        )
    )

    assert policy.mission is CiboCapitalMission.FUNDED_SURVIVAL_COMPOUND
    assert policy.primary_objective is CiboCapitalObjective.SURVIVAL_FIRST
    assert policy.ce2i_scope is Ce2iActivationScope.EXTERNAL_CAPITAL_GATED
    assert policy.allow_research_tool_execution is False
    assert policy.allow_original_base_capital_reallocation is False
    assert policy.preserve_optionality_priority is True


def test_ctrader_demo_derives_capability_discovery_without_issue_flag() -> None:
    policy = derive_cibo_capital_mission(
        CiboAccountCapitalIdentity(
            provider_key="ctrader-demo",
            account_ref="demo-free",
            environment=MarketRuntimeEnvironment.DEMO,
        )
    )

    assert policy.mission is CiboCapitalMission.DEMO_CAPABILITY_DISCOVERY
    assert policy.primary_objective is CiboCapitalObjective.CAPABILITY_DISCOVERY
    assert policy.ce2i_scope is Ce2iActivationScope.ALL_EXECUTABLE_RESEARCH
    assert policy.allow_research_tool_execution is True
    assert policy.allow_multi_tool_experiments is True
    assert policy.allow_original_base_capital_reallocation is True
    assert policy.capability_measurement_enabled is True


def test_demo_still_requires_risk_provider_and_durable_accounting() -> None:
    policy = derive_cibo_capital_mission(
        CiboAccountCapitalIdentity(
            provider_key="ctrader-demo",
            account_ref="demo-free",
            environment=MarketRuntimeEnvironment.DEMO,
        )
    )

    assert policy.sovereign_risk_required is True
    assert policy.provider_constraints_required is True
    assert policy.durable_capital_accounting_required is True


def test_funded_core_tools_can_execute_but_unvalidated_advanced_tools_cannot() -> None:
    policy = derive_cibo_capital_mission(
        CiboAccountCapitalIdentity(
            provider_key="fundednext",
            account_ref="stellar-instant-2k",
            environment=MarketRuntimeEnvironment.PRODUCTION,
            provider_program="stellar-instant",
        )
    )

    assert ce2i_tool_allowed_for_mission(_tool("T01"), policy) is True
    assert ce2i_tool_allowed_for_mission(_tool("T19"), policy) is True
    assert ce2i_tool_allowed_for_mission(_tool("T20"), policy) is True
    assert ce2i_tool_allowed_for_mission(_tool("T06"), policy) is False


def test_demo_can_execute_every_implemented_non_rejected_tool() -> None:
    policy = derive_cibo_capital_mission(
        CiboAccountCapitalIdentity(
            provider_key="ctrader-demo",
            account_ref="demo-free",
            environment=MarketRuntimeEnvironment.DEMO,
        )
    )

    for tool in CE2I_TOOL_REGISTRY:
        if tool.maturity in {
            ToolMaturity.CONTRACT_IMPLEMENTED,
            ToolMaturity.RESEARCH_VALIDATED,
            ToolMaturity.HOLDOUT_VALIDATED,
            ToolMaturity.SHADOW_VALIDATED,
        }:
            assert ce2i_tool_allowed_for_mission(tool, policy) is True
        elif tool.maturity is ToolMaturity.ARCHITECTURE_ONLY:
            assert ce2i_tool_allowed_for_mission(tool, policy) is False


def test_unknown_production_provider_fails_to_conservative_production_mission() -> None:
    policy = derive_cibo_capital_mission(
        CiboAccountCapitalIdentity(
            provider_key="broker-x",
            account_ref="production-1",
            environment=MarketRuntimeEnvironment.PRODUCTION,
        )
    )

    assert policy.mission is CiboCapitalMission.PRODUCTION_SURVIVAL_COMPOUND
    assert policy.allow_research_tool_execution is False
    assert policy.preserve_optionality_priority is True



def test_ctrader_demo_binding_identity_maps_directly_to_capability_mission() -> None:
    identity = identity_from_market_test_account(
        MarketTestAccountIdentity(
            provider_key="ctrader-demo",
            account_ref="demo-free",
            environment=MarketRuntimeEnvironment.DEMO,
        )
    )
    policy = derive_cibo_capital_mission(identity)

    assert identity.provider_key == "ctrader-demo"
    assert policy.mission is CiboCapitalMission.DEMO_CAPABILITY_DISCOVERY


def test_fundednext_identity_maps_directly_to_survival_mission() -> None:
    identity = fundednext_stellar_instant_identity(
        account_ref="stellar-instant-2k"
    )
    policy = derive_cibo_capital_mission(identity)

    assert identity.provider_key == "fundednext"
    assert identity.provider_program == "stellar-instant"
    assert identity.environment is MarketRuntimeEnvironment.PRODUCTION
    assert policy.mission is CiboCapitalMission.FUNDED_SURVIVAL_COMPOUND
