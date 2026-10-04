"""A1 MC17 -> MC18 -> MC19 source-only cognitive chain.

This module binds existing Market Agency and Counterfactual World outputs into
Trajectory Intelligence.  It is deliberately research-only: the trajectory
state is an engineering classification, not a calibrated trading instruction.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from enum import StrEnum
from typing import Final

from qore.infrastructure.core_stack_v2.counterfactual_world_engine import (
    CounterfactualWorldDistribution,
    build_counterfactual_world_distribution,
)
from qore.infrastructure.core_stack_v2.market_agency_model import (
    SharedMarketAgencyAssessment,
    assess_market_agency,
)
from qore.infrastructure.core_stack_v2.shared_global_opportunity_discovery import (
    SharedOpportunitySourceObservation,
)
from qore.infrastructure.core_stack_v2.shared_trader_intelligence import (
    SharedTraderIntelligenceValidationError,
)


class SharedTrajectoryState(StrEnum):
    NORMAL_ADVERSITY = "NORMAL_ADVERSITY"
    RECOVERABLE_DETERIORATION = "RECOVERABLE_DETERIORATION"
    STRUCTURAL_FAILURE = "STRUCTURAL_FAILURE"
    INSUFFICIENT = "INSUFFICIENT"


@dataclass(frozen=True, slots=True)
class SharedTrajectoryEngineeringPolicy:
    policy_id: str
    structural_hazard_gate_bps: int
    deterioration_hazard_gate_bps: int
    counterfactual_failure_gate_bps: int
    minimum_recovery_bps: int
    source_only: bool = True
    calibrated_probability_claimed: bool = False
    productive_authority: bool = False

    def __post_init__(self) -> None:
        if not self.policy_id.strip():
            raise SharedTraderIntelligenceValidationError(
                "trajectory policy requires identity"
            )
        for name in (
            "structural_hazard_gate_bps",
            "deterioration_hazard_gate_bps",
            "counterfactual_failure_gate_bps",
            "minimum_recovery_bps",
        ):
            value = getattr(self, name)
            if type(value) is not int or not 0 <= value <= 10_000:
                raise SharedTraderIntelligenceValidationError(
                    f"{name} must be int within 0..10000"
                )
        if (
            self.deterioration_hazard_gate_bps
            >= self.structural_hazard_gate_bps
        ):
            raise SharedTraderIntelligenceValidationError(
                "trajectory hazard gates must be strictly ordered"
            )
        if (
            not self.source_only
            or self.calibrated_probability_claimed
            or self.productive_authority
        ):
            raise SharedTraderIntelligenceValidationError(
                "trajectory policy must remain source-only research engineering"
            )

    def fingerprint(self) -> str:
        raw = json.dumps(
            asdict(self),
            sort_keys=True,
            separators=(",", ":"),
        )
        return hashlib.sha256(raw.encode()).hexdigest()


DEFAULT_TRAJECTORY_POLICY: Final = SharedTrajectoryEngineeringPolicy(
    policy_id="A1_MC19_ENGINEERING_POLICY_V1_UNCALIBRATED",
    structural_hazard_gate_bps=7_000,
    deterioration_hazard_gate_bps=4_500,
    counterfactual_failure_gate_bps=5_500,
    minimum_recovery_bps=3_500,
)


@dataclass(frozen=True, slots=True)
class SharedTrajectoryIntelligenceAssessment:
    observation_id: str
    asset: str
    as_of_iso: str
    state: SharedTrajectoryState
    structural_hazard_bps: int
    recovery_capacity_bps: int
    counterfactual_failure_bps: int
    counterfactual_survivability_bps: int
    dominant_agency_mechanism: str | None
    mc17_fingerprint: str
    mc18_fingerprint: str
    policy_fingerprint: str
    evidence_refs: tuple[str, ...]
    mc17_output_consumed: bool = True
    mc18_output_consumed: bool = True
    source_only: bool = True
    future_market_used: bool = False
    future_outcome_used: bool = False
    creates_trader_setup: bool = False
    position_management_authority: bool = False
    execution_authority: bool = False
    risk_authority: bool = False
    sizing_authority: bool = False
    capital_authority: bool = False
    scientifically_calibrated: bool = False

    def __post_init__(self) -> None:
        if not self.observation_id.strip() or not self.asset.strip():
            raise SharedTraderIntelligenceValidationError(
                "trajectory assessment requires observation and asset identity"
            )
        for name in (
            "structural_hazard_bps",
            "recovery_capacity_bps",
            "counterfactual_failure_bps",
            "counterfactual_survivability_bps",
        ):
            value = getattr(self, name)
            if type(value) is not int or not 0 <= value <= 10_000:
                raise SharedTraderIntelligenceValidationError(
                    f"{name} must be int within 0..10000"
                )
        for name in (
            "mc17_fingerprint",
            "mc18_fingerprint",
            "policy_fingerprint",
        ):
            value = getattr(self, name)
            if len(value) != 64:
                raise SharedTraderIntelligenceValidationError(
                    f"{name} must be sha256 hex"
                )
        if (
            not self.evidence_refs
            or self.evidence_refs != tuple(sorted(set(self.evidence_refs)))
        ):
            raise SharedTraderIntelligenceValidationError(
                "trajectory evidence refs must be non-empty and canonical"
            )
        if (
            not self.mc17_output_consumed
            or not self.mc18_output_consumed
            or not self.source_only
            or self.future_market_used
            or self.future_outcome_used
            or self.creates_trader_setup
            or self.position_management_authority
            or self.execution_authority
            or self.risk_authority
            or self.sizing_authority
            or self.capital_authority
            or self.scientifically_calibrated
        ):
            raise SharedTraderIntelligenceValidationError(
                "trajectory intelligence violates A1 research governance"
            )

    def fingerprint(self) -> str:
        payload = asdict(self)
        payload["state"] = self.state.value
        raw = json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
        )
        return hashlib.sha256(raw.encode()).hexdigest()


def _mean(*values: int) -> int:
    return sum(values) // len(values)


def _weighted_metric(
    worlds: CounterfactualWorldDistribution,
    attribute: str,
) -> int:
    numerator = sum(
        path.probability_bps * int(getattr(path, attribute))
        for path in worlds.paths
    )
    return numerator // 10_000


def _trajectory_state(
    *,
    agency: SharedMarketAgencyAssessment,
    structural_hazard_bps: int,
    recovery_capacity_bps: int,
    counterfactual_failure_bps: int,
    policy: SharedTrajectoryEngineeringPolicy,
) -> SharedTrajectoryState:
    if agency.insufficient:
        return SharedTrajectoryState.INSUFFICIENT

    severe_hazard = (
        structural_hazard_bps >= policy.structural_hazard_gate_bps
    )
    elevated_hazard = (
        structural_hazard_bps >= policy.deterioration_hazard_gate_bps
    )
    elevated_counterfactual_failure = (
        counterfactual_failure_bps
        >= policy.counterfactual_failure_gate_bps
    )
    weak_recovery = recovery_capacity_bps < policy.minimum_recovery_bps

    if severe_hazard and (elevated_counterfactual_failure or weak_recovery):
        return SharedTrajectoryState.STRUCTURAL_FAILURE
    if elevated_hazard or elevated_counterfactual_failure:
        if weak_recovery:
            return SharedTrajectoryState.STRUCTURAL_FAILURE
        return SharedTrajectoryState.RECOVERABLE_DETERIORATION
    return SharedTrajectoryState.NORMAL_ADVERSITY


def assess_trajectory_intelligence(
    observation: SharedOpportunitySourceObservation,
    *,
    policy: SharedTrajectoryEngineeringPolicy = DEFAULT_TRAJECTORY_POLICY,
) -> SharedTrajectoryIntelligenceAssessment:
    """Consume MC17 and MC18 outputs into a bounded MC19 trajectory state."""

    agency = assess_market_agency(observation)
    worlds = build_counterfactual_world_distribution(observation)

    structural_hazard = _mean(
        observation.structural_fragility_bps,
        observation.liquidity_vacuum_bps,
        observation.regime_transition_bps,
        observation.anomaly_bps,
        observation.leader_divergence_bps,
    )
    recovery_capacity = _mean(
        observation.acceptance_bps,
        observation.absorption_bps,
        observation.leader_confirmation_bps,
        observation.momentum_persistence_bps,
        10_000 - observation.momentum_decay_bps,
    )
    counterfactual_failure = _weighted_metric(
        worlds,
        "failure_probability_bps",
    )
    counterfactual_survivability = _weighted_metric(
        worlds,
        "survivability_bps",
    )
    state = _trajectory_state(
        agency=agency,
        structural_hazard_bps=structural_hazard,
        recovery_capacity_bps=recovery_capacity,
        counterfactual_failure_bps=counterfactual_failure,
        policy=policy,
    )

    dominant = (
        None
        if agency.dominant_mechanism is None
        else agency.dominant_mechanism.value
    )
    refs = tuple(
        sorted(
            set(
                observation.provenance_refs
                + (
                    f"mc17:{agency.fingerprint()}",
                    f"mc18:{worlds.fingerprint()}",
                    f"mc19-policy:{policy.fingerprint()}",
                )
            )
        )
    )
    return SharedTrajectoryIntelligenceAssessment(
        observation_id=observation.observation_id,
        asset=observation.asset,
        as_of_iso=observation.as_of.isoformat(),
        state=state,
        structural_hazard_bps=structural_hazard,
        recovery_capacity_bps=recovery_capacity,
        counterfactual_failure_bps=counterfactual_failure,
        counterfactual_survivability_bps=counterfactual_survivability,
        dominant_agency_mechanism=dominant,
        mc17_fingerprint=agency.fingerprint(),
        mc18_fingerprint=worlds.fingerprint(),
        policy_fingerprint=policy.fingerprint(),
        evidence_refs=refs,
    )
