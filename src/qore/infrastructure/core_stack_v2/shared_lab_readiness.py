"""QORE Shared Lab readiness gate.

This gate answers only whether the laboratory itself is sufficiently built and
self-validated to begin validating Shared. It grants no Shared certification,
holdout-opening, trading, sizing, risk or productive authority.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class LabLaneStatus:
    lane_id: str
    built: bool
    tests_passed: bool
    l10_passed: bool
    evidence_ref: str

    def __post_init__(self) -> None:
        if not self.lane_id.strip() or not self.evidence_ref.strip():
            raise ValueError("lane status requires identity and evidence")

    @property
    def ready(self) -> bool:
        return self.built and self.tests_passed and self.l10_passed


@dataclass(frozen=True, slots=True)
class SharedLabReadinessInput:
    core_lane: LabLaneStatus
    data_sensor_lane: LabLaneStatus
    tool_registry_fingerprinted: bool
    deterministic_replay_proven: bool
    capability_ledger_proven: bool
    influence_graph_proven: bool
    mutation_metamorphic_ablation_proven: bool
    uncertainty_contradiction_proven: bool
    counterfactual_truth_proven: bool
    resource_latency_proven: bool
    information_value_proven: bool
    degraded_mode_proven: bool
    seven_trader_harness_built: bool
    organism_harness_built: bool
    global_l10_pass: bool
    authority_isolation_pass: bool


@dataclass(frozen=True, slots=True)
class SharedLabReadinessAssessment:
    blocker_ids: tuple[str, ...]
    laboratory_available_for_shared_validation: bool
    shared_pre_certification_authorized: bool = False
    protected_holdout_opening_authorized: bool = False
    productive_authority: bool = False

    def __post_init__(self) -> None:
        if self.shared_pre_certification_authorized:
            raise ValueError("lab readiness cannot authorize Shared pre-certification")
        if self.protected_holdout_opening_authorized:
            raise ValueError("lab readiness cannot open protected holdout")
        if self.productive_authority:
            raise ValueError("lab readiness grants no productive authority")


def assess_shared_lab_readiness(
    status: SharedLabReadinessInput,
) -> SharedLabReadinessAssessment:
    checks = {
        "CORE_LANE": status.core_lane.ready,
        "DATA_SENSOR_LANE": status.data_sensor_lane.ready,
        "TOOL_REGISTRY_FINGERPRINT": status.tool_registry_fingerprinted,
        "DETERMINISTIC_REPLAY": status.deterministic_replay_proven,
        "CAPABILITY_LEDGER": status.capability_ledger_proven,
        "INFLUENCE_GRAPH": status.influence_graph_proven,
        "MUTATION_METAMORPHIC_ABLATION": status.mutation_metamorphic_ablation_proven,
        "UNCERTAINTY_CONTRADICTION": status.uncertainty_contradiction_proven,
        "COUNTERFACTUAL_TRUTH": status.counterfactual_truth_proven,
        "RESOURCE_LATENCY": status.resource_latency_proven,
        "INFORMATION_VALUE": status.information_value_proven,
        "DEGRADED_MODE": status.degraded_mode_proven,
        "SEVEN_TRADER_HARNESS": status.seven_trader_harness_built,
        "ORGANISM_HARNESS": status.organism_harness_built,
        "GLOBAL_L10": status.global_l10_pass,
        "AUTHORITY_ISOLATION": status.authority_isolation_pass,
    }
    blockers = tuple(sorted(key for key, passed in checks.items() if not passed))
    return SharedLabReadinessAssessment(
        blocker_ids=blockers,
        laboratory_available_for_shared_validation=not blockers,
    )
