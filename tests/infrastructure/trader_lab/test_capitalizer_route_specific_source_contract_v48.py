from qore.infrastructure.trader_lab.capitalizer_route_specific_source_contract_v48 import (
    V48_ROUTE_CONTRACT_REGISTRY,
    V48RouteContractDecision,
    assess_route_contract,
    contract_for,
)
from qore.infrastructure.trader_lab.capitalizer_source_native_route_registry_v48 import (
    V48RouteId,
)


def test_new_york_accepts_one_valid_entry_model_not_all_three() -> None:
    facts = {
        "LONDON_CONTEXT_RESOLVED": True,
        "NY_LIQUIDITY_SWEEP_CONFIRMED": True,
        "NY_CISD_CONFIRMED": True,
        "STRUCTURAL_INVALIDATION_AVAILABLE": True,
        "STRUCTURAL_TARGET_AVAILABLE": True,
        "FVG_ENTRY_AVAILABLE": True,
        "ORDER_BLOCK_ENTRY_AVAILABLE": False,
        "OTHER_SOURCE_VALID_ENTRY_AVAILABLE": False,
    }
    result = assess_route_contract(V48RouteId.TTRADES_NEW_YORK_MANIPULATION, facts)
    assert result.decision is V48RouteContractDecision.SOURCE_COMPLETE_PRE_ECONOMIC


def test_generic_scalp_does_not_require_m1_mss_fvg_and_ob_superintersection() -> None:
    contract = contract_for(V48RouteId.TTRADES_GENERIC_SCALP_H1_M15_M1)
    all_facts = set(contract.required_fact_ids)
    all_options = {
        option
        for group in contract.alternative_groups
        for option in group.option_fact_ids
    }

    assert "M1_MSS_CONFIRMED" not in all_facts
    assert "M1_ORDER_BLOCK_CONFIRMED" not in all_facts
    assert "M1_FVG_INTERACTION_CONFIRMED" in all_options


def test_generic_scalp_requires_at_least_one_source_execution_behavior() -> None:
    base = {
        "DAILY_CONTEXT_RESOLVED": True,
        "H1_SCALP_BIAS_CONFIRMED": True,
        "M15_SWING_STRUCTURE_CONFIRMED": True,
        "LOGICAL_PROTECTED_SWING_STOP_AVAILABLE": True,
        "STRUCTURAL_TARGET_AVAILABLE": True,
    }
    result = assess_route_contract(V48RouteId.TTRADES_GENERIC_SCALP_H1_M15_M1, base)
    assert result.decision is V48RouteContractDecision.WAIT
    assert result.unresolved_alternative_groups == ("M1_EXECUTION_BEHAVIOR",)

    with_cisd = {**base, "M1_CISD_CONFIRMED": True}
    result = assess_route_contract(
        V48RouteId.TTRADES_GENERIC_SCALP_H1_M15_M1,
        with_cisd,
    )
    assert result.decision is V48RouteContractDecision.SOURCE_COMPLETE_PRE_ECONOMIC


def test_ftm_contract_contains_core_failure_then_continuation_only() -> None:
    contract = contract_for(V48RouteId.TTRADES_FAILURE_TO_MANIPULATE)
    assert {
        "LIQUIDITY_LEVEL_TAKEN",
        "EXPECTED_REVERSAL_FAILED_TO_CONFIRM",
        "CONTINUATION_STRUCTURE_CONFIRMED",
        "CONTINUATION_PROTECTED_SWING_CONFIRMED",
    }.issubset(set(contract.required_fact_ids))
    assert "M1_ORDER_BLOCK_CONFIRMED" not in contract.required_fact_ids
    assert "M1_FVG_CONFIRMED" not in contract.required_fact_ids
    assert "ICT_DISPLACEMENT_SIGNIFICANT" not in contract.required_fact_ids


def test_ict_route_contract_is_absent_until_timestamp_binding_is_closed() -> None:
    route_ids = {contract.route_id for contract in V48_ROUTE_CONTRACT_REGISTRY.contracts}
    assert V48RouteId.ICT_2022_EXECUTION not in route_ids
    assert V48_ROUTE_CONTRACT_REGISTRY.fresh_holdout_authorized is False
    assert V48_ROUTE_CONTRACT_REGISTRY.economics_authorized is False
