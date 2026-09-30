"""V48 route-specific source contract for Capitalizer.

Each route owns its mandatory facts and any source-proven alternative groups. No fact is
inherited globally from another route or author. This replaces the V47 assumption that all
source concepts belong to one universal AND gate.

The contract only determines pre-economic source completeness. It cannot execute or size.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum

from qore.infrastructure.trader_lab.capitalizer_source_native_route_registry_v48 import (
    V48RouteId,
)

IDENTITY = "QORE_CAPITALIZER_V48_ROUTE_SPECIFIC_SOURCE_CONTRACT"


class V48RouteContractDecision(StrEnum):
    SOURCE_COMPLETE_PRE_ECONOMIC = "SOURCE_COMPLETE_PRE_ECONOMIC"
    WAIT = "WAIT"


@dataclass(frozen=True, slots=True)
class V48AlternativeGroup:
    group_id: str
    option_fact_ids: tuple[str, ...]
    minimum_true: int = 1

    def __post_init__(self) -> None:
        if not self.group_id or self.group_id != self.group_id.upper():
            raise ValueError("alternative group id must be non-empty uppercase")
        if not self.option_fact_ids:
            raise ValueError("alternative group requires options")
        if self.minimum_true < 1 or self.minimum_true > len(self.option_fact_ids):
            raise ValueError("invalid alternative-group minimum")
        if len(self.option_fact_ids) != len(set(self.option_fact_ids)):
            raise ValueError("alternative options must be unique")


@dataclass(frozen=True, slots=True)
class V48RouteContract:
    route_id: V48RouteId
    required_fact_ids: tuple[str, ...]
    alternative_groups: tuple[V48AlternativeGroup, ...] = ()
    global_dual_source_gate_required: bool = False

    def __post_init__(self) -> None:
        if not self.required_fact_ids:
            raise ValueError("route contract requires source facts")
        if len(self.required_fact_ids) != len(set(self.required_fact_ids)):
            raise ValueError("required source facts must be unique")
        if self.global_dual_source_gate_required:
            raise ValueError("V48 route contract cannot depend on old global dual-source gate")


CONTRACTS: tuple[V48RouteContract, ...] = (
    V48RouteContract(
        V48RouteId.TTRADES_ASIA_POSITIONAL,
        (
            "HTF_FRACTAL_BIAS_CONFIRMED",
            "LTF_PROTECTED_SWING_CONFIRMED_BY_CISD",
            "POSITIONAL_OPEN_AVAILABLE",
            "STRUCTURAL_TARGET_AVAILABLE",
        ),
    ),
    V48RouteContract(
        V48RouteId.TTRADES_ASIA_4H_15M,
        (
            "HTF_FRACTAL_BIAS_CONFIRMED",
            "H4_C2_CONFIRMATION",
            "M15_PROTECTED_SWING_CONFIRMED_BY_CISD",
            "STRUCTURAL_TARGET_AVAILABLE",
        ),
    ),
    V48RouteContract(
        V48RouteId.TTRADES_LONDON_DAILY_4H_15M,
        (
            "DAILY_BIAS_CONFIRMED",
            "H4_WICK_SWING_STRUCTURE_CONFIRMED",
            "M15_PROTECTED_SWING_CONFIRMED_BY_CISD",
            "M15_CONTINUATION_AVAILABLE",
            "STRUCTURAL_TARGET_AVAILABLE",
        ),
    ),
    V48RouteContract(
        V48RouteId.TTRADES_NEW_YORK_MANIPULATION,
        (
            "LONDON_CONTEXT_RESOLVED",
            "NY_LIQUIDITY_SWEEP_CONFIRMED",
            "NY_CISD_CONFIRMED",
            "STRUCTURAL_INVALIDATION_AVAILABLE",
            "STRUCTURAL_TARGET_AVAILABLE",
        ),
        (
            V48AlternativeGroup(
                "NY_ENTRY_MODEL",
                (
                    "FVG_ENTRY_AVAILABLE",
                    "ORDER_BLOCK_ENTRY_AVAILABLE",
                    "OTHER_SOURCE_VALID_ENTRY_AVAILABLE",
                ),
            ),
        ),
    ),
    V48RouteContract(
        V48RouteId.TTRADES_GENERIC_SCALP_H1_M15_M1,
        (
            "H1_SCALP_BIAS_CONFIRMED",
            "M15_PROTECTED_SWING_CONFIRMED_BY_CISD",
            "M1_CONTINUATION_CONFIRMED",
            "LOGICAL_PROTECTED_SWING_STOP_AVAILABLE",
            "STRUCTURAL_TARGET_AVAILABLE",
        ),
    ),
    V48RouteContract(
        V48RouteId.TTRADES_FAILURE_TO_MANIPULATE,
        (
            "HTF_BIAS_ALIGNED",
            "LIQUIDITY_LEVEL_TAKEN",
            "EXPECTED_REVERSAL_FAILED_TO_CONFIRM",
            "CONTINUATION_STRUCTURE_CONFIRMED",
            "CONTINUATION_PROTECTED_SWING_CONFIRMED",
            "STRUCTURAL_TARGET_AVAILABLE",
        ),
    ),
)


@dataclass(frozen=True, slots=True)
class V48RouteContractAssessment:
    route_id: V48RouteId
    decision: V48RouteContractDecision
    missing_required: tuple[str, ...]
    unresolved_alternative_groups: tuple[str, ...]
    outcome_used: bool = False
    executes_trade: bool = False
    sizes_position: bool = False
    grants_capital_authority: bool = False

    def __post_init__(self) -> None:
        complete = self.decision is V48RouteContractDecision.SOURCE_COMPLETE_PRE_ECONOMIC
        if complete != (not self.missing_required and not self.unresolved_alternative_groups):
            raise ValueError("route assessment decision/payload mismatch")
        if self.outcome_used:
            raise ValueError("source route assessment cannot use outcomes")
        if self.executes_trade or self.sizes_position or self.grants_capital_authority:
            raise ValueError("source route contract stops before capital/execution")


def contract_for(route_id: V48RouteId) -> V48RouteContract:
    matches = tuple(contract for contract in CONTRACTS if contract.route_id is route_id)
    if len(matches) != 1:
        raise ValueError(f"expected exactly one contract for {route_id}")
    return matches[0]


def assess_route_contract(
    route_id: V48RouteId,
    facts: Mapping[str, bool],
) -> V48RouteContractAssessment:
    contract = contract_for(route_id)

    missing_required = tuple(
        fact_id
        for fact_id in contract.required_fact_ids
        if facts.get(fact_id) is not True
    )
    unresolved_groups: list[str] = []
    for group in contract.alternative_groups:
        true_count = sum(facts.get(option) is True for option in group.option_fact_ids)
        if true_count < group.minimum_true:
            unresolved_groups.append(group.group_id)

    complete = not missing_required and not unresolved_groups
    return V48RouteContractAssessment(
        route_id=route_id,
        decision=(
            V48RouteContractDecision.SOURCE_COMPLETE_PRE_ECONOMIC
            if complete
            else V48RouteContractDecision.WAIT
        ),
        missing_required=missing_required,
        unresolved_alternative_groups=tuple(unresolved_groups),
    )


@dataclass(frozen=True, slots=True)
class V48RouteContractRegistry:
    identity: str = IDENTITY
    contracts: tuple[V48RouteContract, ...] = CONTRACTS
    fresh_holdout_authorized: bool = False
    economics_authorized: bool = False

    def __post_init__(self) -> None:
        if self.identity != IDENTITY:
            raise ValueError("V48 route contract registry identity is frozen")
        ids = tuple(contract.route_id for contract in self.contracts)
        if len(ids) != len(set(ids)):
            raise ValueError("route contracts must be unique")
        if V48RouteId.ICT_2022_EXECUTION in ids:
            raise ValueError("ICT contract remains blocked until timestamp source binding")
        if self.fresh_holdout_authorized or self.economics_authorized:
            raise ValueError("V48 route contracts are pre-economic")


V48_ROUTE_CONTRACT_REGISTRY = V48RouteContractRegistry()
