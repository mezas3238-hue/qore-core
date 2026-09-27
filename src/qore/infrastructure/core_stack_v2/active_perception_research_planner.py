"""Outcome-free R8 research planning for Shared Active Perception.

The runtime active-perception planner says which latent uncertainty would be
valuable to reduce. Sensor governance says whether a concrete observation is
causally admissible. This module joins those two contracts without using
targets, outcomes, PnL, R6/R5 or fresh-holdout evidence.

It does not fetch sensors and carries no trading authority.
"""

from __future__ import annotations

from dataclasses import dataclass

from qore.infrastructure.core_stack_v2.active_perception import (
    ActivePerceptionPlan,
)
from qore.infrastructure.core_stack_v2.active_perception_sensor_governance import (
    ActivePerceptionSensorContract,
    SensorAdmissionStatus,
    SensorObservationKind,
    active_perception_sensor_fingerprint,
    admit_active_perception_sensor,
)
from qore.infrastructure.core_stack_v2.latent_market_state_engine import (
    LatentMarketFactor,
)


@dataclass(frozen=True, slots=True)
class ActivePerceptionResearchCandidate:
    contract: ActivePerceptionSensorContract
    supported_factors: tuple[LatentMarketFactor, ...]
    source_family_tags: tuple[str, ...]
    acquisition_cost_bps: int = 0

    def __post_init__(self) -> None:
        if not self.supported_factors:
            raise ValueError("research sensor must support at least one latent factor")
        if len(set(self.supported_factors)) != len(self.supported_factors):
            raise ValueError("research sensor factors must be unique")
        if not self.source_family_tags:
            raise ValueError("research sensor requires source-family tags")
        if any(not item.strip() for item in self.source_family_tags):
            raise ValueError("research sensor source-family tags must be non-empty")
        if not 0 <= self.acquisition_cost_bps <= 10_000:
            raise ValueError("acquisition_cost_bps must be within 0..10000")


@dataclass(frozen=True, slots=True)
class RankedActivePerceptionSensor:
    sensor_key: str
    contract_fingerprint_sha256: str
    matched_factors: tuple[LatentMarketFactor, ...]
    matched_source_families: tuple[str, ...]
    information_need_bps: int
    direct_observation_bonus_bps: int
    acquisition_cost_bps: int
    priority_bps: int

    def __post_init__(self) -> None:
        if len(self.contract_fingerprint_sha256) != 64:
            raise ValueError("ranked sensor fingerprint must be sha256 hex")
        if not self.matched_factors:
            raise ValueError("ranked sensor requires matched factors")
        for name in (
            "information_need_bps",
            "direct_observation_bonus_bps",
            "acquisition_cost_bps",
            "priority_bps",
        ):
            if not 0 <= int(getattr(self, name)) <= 10_000:
                raise ValueError(f"{name} must be within 0..10000")


@dataclass(frozen=True, slots=True)
class ActivePerceptionResearchPlan:
    ranked_sensors: tuple[RankedActivePerceptionSensor, ...]
    rejected_sensor_keys: tuple[str, ...]
    unresolved_information_need_bps: int
    selection_partition: str = "r8"
    target_outcome_used: bool = False
    pnl_used: bool = False
    r6_r5_consumed_for_selection: bool = False
    fresh_holdout_opened: bool = False
    methodology_authority: bool = False
    sizing_authority: bool = False
    risk_authority: bool = False
    order_authority: bool = False
    execution_authority: bool = False

    def __post_init__(self) -> None:
        if self.selection_partition != "r8":
            raise ValueError("active-perception sensor selection is R8-only")
        if not 0 <= self.unresolved_information_need_bps <= 10_000:
            raise ValueError("unresolved information need must be within 0..10000")
        if (
            self.target_outcome_used
            or self.pnl_used
            or self.r6_r5_consumed_for_selection
            or self.fresh_holdout_opened
            or self.methodology_authority
            or self.sizing_authority
            or self.risk_authority
            or self.order_authority
            or self.execution_authority
        ):
            raise ValueError(
                "active-perception research plan carries forbidden evidence "
                "or authority"
            )


def _priority(
    *,
    information_need_bps: int,
    direct_bonus_bps: int,
    acquisition_cost_bps: int,
) -> int:
    value = information_need_bps + direct_bonus_bps - acquisition_cost_bps
    return max(0, min(10_000, value))


def plan_active_perception_sensor_research(
    *,
    perception_plan: ActivePerceptionPlan,
    candidates: tuple[ActivePerceptionResearchCandidate, ...],
    maximum_sensors: int = 8,
) -> ActivePerceptionResearchPlan:
    """Rank causally admitted sensors from epistemic need only.

    No label, target outcome or holdout result is an input to this function.
    """

    if maximum_sensors < 1:
        raise ValueError("maximum_sensors must be positive")
    if len({item.contract.sensor_key for item in candidates}) != len(candidates):
        raise ValueError("research candidate sensor keys must be unique")

    need_by_factor = {
        request.factor: request.information_need_bps
        for request in perception_plan.requests
    }
    requested_sources = {
        request.factor: set(request.suggested_source_families)
        for request in perception_plan.requests
    }

    ranked: list[RankedActivePerceptionSensor] = []
    rejected: list[str] = []
    for candidate in candidates:
        decision = admit_active_perception_sensor(candidate.contract)
        if decision.status is SensorAdmissionStatus.REJECTED:
            rejected.append(candidate.contract.sensor_key)
            continue

        matched = tuple(
            factor
            for factor in candidate.supported_factors
            if need_by_factor.get(factor, 0) > 0
        )
        if not matched:
            continue

        information_need = max(need_by_factor[factor] for factor in matched)
        source_matches = tuple(
            sorted(
                {
                    tag
                    for factor in matched
                    for tag in candidate.source_family_tags
                    if tag in requested_sources.get(factor, set())
                }
            )
        )
        direct_bonus = (
            500
            if candidate.contract.observation_kind
            is SensorObservationKind.DIRECT_OBSERVATION
            else 250
            if candidate.contract.observation_kind
            is SensorObservationKind.PROVIDER_DERIVED_OBSERVATION
            else 0
        )
        ranked.append(
            RankedActivePerceptionSensor(
                sensor_key=candidate.contract.sensor_key,
                contract_fingerprint_sha256=active_perception_sensor_fingerprint(
                    candidate.contract
                ),
                matched_factors=matched,
                matched_source_families=source_matches,
                information_need_bps=information_need,
                direct_observation_bonus_bps=direct_bonus,
                acquisition_cost_bps=candidate.acquisition_cost_bps,
                priority_bps=_priority(
                    information_need_bps=information_need,
                    direct_bonus_bps=direct_bonus,
                    acquisition_cost_bps=candidate.acquisition_cost_bps,
                ),
            )
        )

    ranked.sort(
        key=lambda item: (
            -item.priority_bps,
            -item.information_need_bps,
            item.sensor_key,
        )
    )
    return ActivePerceptionResearchPlan(
        ranked_sensors=tuple(ranked[:maximum_sensors]),
        rejected_sensor_keys=tuple(sorted(rejected)),
        unresolved_information_need_bps=(
            perception_plan.unresolved_information_need_bps
        ),
    )
