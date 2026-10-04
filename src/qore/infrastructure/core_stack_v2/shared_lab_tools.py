"""Parameterized tool registry and L10 fault-injection helpers for QORE Shared Lab."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from enum import StrEnum
from itertools import product
from typing import Any

from qore.infrastructure.core_stack_v2.shared_lab import LabFault


class ToolFamily(StrEnum):
    SENSOR_DATA_INTEGRITY = "SENSOR_DATA_INTEGRITY"
    TIMESTAMP_PERTURBATION = "TIMESTAMP_PERTURBATION"
    SENSOR_FAILURE_INJECTOR = "SENSOR_FAILURE_INJECTOR"
    PROVIDER_DEGRADATION = "PROVIDER_DEGRADATION"
    IDENTITY_MUTATION = "IDENTITY_MUTATION"
    MARKET_HOURS_VALIDATION = "MARKET_HOURS_VALIDATION"
    DATA_COMPLETENESS = "DATA_COMPLETENESS"
    CROSS_ASSET_RELATION = "CROSS_ASSET_RELATION"
    REPRESENTATION_PERTURBATION = "REPRESENTATION_PERTURBATION"
    FEATURE_IMPORTANCE = "FEATURE_IMPORTANCE"
    LATENT_STATE_CALIBRATION = "LATENT_STATE_CALIBRATION"
    BELIEF_CALIBRATION = "BELIEF_CALIBRATION"
    WORLD_COMPETITION = "WORLD_COMPETITION"
    CONTRADICTION_INJECTION = "CONTRADICTION_INJECTION"
    MARKET_PHYSICS_CONSTRAINT = "MARKET_PHYSICS_CONSTRAINT"
    CAUSAL_DISCOVERY = "CAUSAL_DISCOVERY"
    CONFOUNDER_TEST = "CONFOUNDER_TEST"
    COUNTERFACTUAL_WORLD = "COUNTERFACTUAL_WORLD"
    TEMPORAL_REASONING = "TEMPORAL_REASONING"
    REGIME_TRANSITION = "REGIME_TRANSITION"
    MEMORY_RETRIEVAL = "MEMORY_RETRIEVAL"
    META_LEARNING = "META_LEARNING"
    CONTINUAL_LEARNING_STABILITY = "CONTINUAL_LEARNING_STABILITY"
    CATASTROPHIC_FORGETTING = "CATASTROPHIC_FORGETTING"
    OOD_NOVELTY = "OOD_NOVELTY"
    ACTIVE_PERCEPTION = "ACTIVE_PERCEPTION"
    VALUE_OF_INFORMATION = "VALUE_OF_INFORMATION"
    STI_OPPORTUNITY_DISCOVERY = "STI_OPPORTUNITY_DISCOVERY"
    THREAT_INTELLIGENCE = "THREAT_INTELLIGENCE"
    TRADER_ROUTING = "TRADER_ROUTING"
    DOWNSTREAM_CONSUMPTION = "DOWNSTREAM_CONSUMPTION"
    COGNITIVE_MUTATION = "COGNITIVE_MUTATION"
    CABLE_LINEAGE_BREAK = "CABLE_LINEAGE_BREAK"
    LEAKAGE_INJECTION = "LEAKAGE_INJECTION"
    DUPLICATE_OUTPUT_INJECTION = "DUPLICATE_OUTPUT_INJECTION"
    DOWNSTREAM_IGNORE_INJECTION = "DOWNSTREAM_IGNORE_INJECTION"
    ABLATION = "ABLATION"
    CONTROL_TREATMENT = "CONTROL_TREATMENT"
    STRESS = "STRESS"
    MONTE_CARLO = "MONTE_CARLO"
    WALK_FORWARD = "WALK_FORWARD"
    MULTI_ERA_REPLICATION = "MULTI_ERA_REPLICATION"
    FAILURE_INJECTION = "FAILURE_INJECTION"
    DETERMINISM_REPLAY = "DETERMINISM_REPLAY"
    LEAKAGE_DETECTION = "LEAKAGE_DETECTION"
    AUTHORITY_ISOLATION = "AUTHORITY_ISOLATION"
    RESOURCE_LATENCY = "RESOURCE_LATENCY"
    REDUNDANCY_RESILIENCE = "REDUNDANCY_RESILIENCE"


@dataclass(frozen=True, slots=True)
class LabToolSpec:
    tool_id: str
    family: ToolFamily
    description: str
    parameter_names: tuple[str, ...]

    def __post_init__(self) -> None:
        if not self.tool_id.strip() or not self.description.strip():
            raise ValueError("tool identity and description are required")
        if len(self.parameter_names) != len(set(self.parameter_names)):
            raise ValueError("tool parameters must be unique")


@dataclass(frozen=True, slots=True)
class ProbeCase:
    tool_id: str
    parameters: tuple[tuple[str, Any], ...]

    @property
    def case_id(self) -> str:
        payload = ",".join(f"{key}={value}" for key, value in self.parameters)
        return f"{self.tool_id}[{payload}]"


class SharedLabToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, LabToolSpec] = {}

    def register(self, spec: LabToolSpec) -> None:
        if spec.tool_id in self._tools:
            raise ValueError(f"duplicate Shared Lab tool: {spec.tool_id}")
        self._tools[spec.tool_id] = spec

    def get(self, tool_id: str) -> LabToolSpec:
        return self._tools[tool_id]

    def list_tools(self) -> tuple[LabToolSpec, ...]:
        return tuple(self._tools[key] for key in sorted(self._tools))

    def expand(
        self,
        tool_id: str,
        parameter_grid: Mapping[str, Iterable[Any]],
    ) -> tuple[ProbeCase, ...]:
        spec = self.get(tool_id)
        if set(parameter_grid) != set(spec.parameter_names):
            raise ValueError("parameter grid must exactly match tool specification")
        ordered_values = [tuple(parameter_grid[name]) for name in spec.parameter_names]
        if any(not values for values in ordered_values):
            raise ValueError("parameter grid values cannot be empty")
        return tuple(
            ProbeCase(
                tool_id=tool_id,
                parameters=tuple(zip(spec.parameter_names, values, strict=True)),
            )
            for values in product(*ordered_values)
        )


def _spec(
    tool_id: str,
    family: ToolFamily,
    description: str,
    parameter_names: tuple[str, ...],
) -> LabToolSpec:
    return LabToolSpec(tool_id, family, description, parameter_names)


def default_shared_lab_registry() -> SharedLabToolRegistry:
    registry = SharedLabToolRegistry()
    specs = (
        _spec(
            "sensor-data-integrity",
            ToolFamily.SENSOR_DATA_INTEGRITY,
            "Probe missing, duplicated, malformed and stale observations.",
            ("sensor", "asset", "fault", "regime"),
        ),
        _spec(
            "timestamp-perturbation",
            ToolFamily.TIMESTAMP_PERTURBATION,
            "Perturb chronology while preserving explicit provenance.",
            ("sensor", "asset", "offset", "regime"),
        ),
        _spec(
            "sensor-failure-injector",
            ToolFamily.SENSOR_FAILURE_INJECTOR,
            "Remove or degrade a sensor for bounded intervals.",
            ("sensor", "missing_pct", "duration", "regime", "asset"),
        ),
        _spec(
            "provider-degradation",
            ToolFamily.PROVIDER_DEGRADATION,
            "Inject stale, partial, delayed or conflicting provider evidence.",
            ("provider", "mode", "asset", "duration"),
        ),
        _spec(
            "identity-mutation",
            ToolFamily.IDENTITY_MUTATION,
            "Mutate symbol aliases or classification.",
            ("asset", "mutation"),
        ),
        _spec(
            "market-hours-validation",
            ToolFamily.MARKET_HOURS_VALIDATION,
            "Challenge open, close, holiday and session-boundary truth.",
            ("asset", "timestamp", "calendar_case"),
        ),
        _spec(
            "data-completeness",
            ToolFamily.DATA_COMPLETENESS,
            "Measure expected versus observed coverage.",
            ("sensor", "asset", "window", "gap_mode"),
        ),
        _spec(
            "cross-asset-relation",
            ToolFamily.CROSS_ASSET_RELATION,
            "Perturb cross-asset structure and relation stability.",
            ("source_asset", "target_asset", "relation", "regime"),
        ),
        _spec(
            "representation-perturbation",
            ToolFamily.REPRESENTATION_PERTURBATION,
            "Probe sensitivity to meaningful and irrelevant input change.",
            ("capability", "perturbation", "magnitude"),
        ),
        _spec(
            "feature-importance",
            ToolFamily.FEATURE_IMPORTANCE,
            "Measure dependency on candidate representation features.",
            ("capability", "feature", "intervention"),
        ),
        _spec(
            "latent-state-calibration",
            ToolFamily.LATENT_STATE_CALIBRATION,
            "Probe latent-state consistency and calibration.",
            ("capability", "state", "regime", "horizon"),
        ),
        _spec(
            "belief-calibration",
            ToolFamily.BELIEF_CALIBRATION,
            "Compare confidence against realized reliability.",
            ("capability", "confidence_bin", "era"),
        ),
        _spec(
            "world-competition",
            ToolFamily.WORLD_COMPETITION,
            "Challenge competing world hypotheses.",
            ("capability", "world_set", "evidence_case"),
        ),
        _spec(
            "contradiction-injection",
            ToolFamily.CONTRADICTION_INJECTION,
            "Inject conflicting evidence and require governed resolution.",
            ("capability", "source_pair", "conflict"),
        ),
        _spec(
            "market-physics-constraint",
            ToolFamily.MARKET_PHYSICS_CONSTRAINT,
            "Inject physically invalid world states.",
            ("capability", "constraint", "violation"),
        ),
        _spec(
            "causal-discovery",
            ToolFamily.CAUSAL_DISCOVERY,
            "Probe causal edge recovery under controlled interventions.",
            ("capability", "intervention", "graph_case"),
        ),
        _spec(
            "confounder-test",
            ToolFamily.CONFOUNDER_TEST,
            "Inject candidate confounders and test causal stability.",
            ("capability", "confounder", "strength"),
        ),
        _spec(
            "counterfactual-world",
            ToolFamily.COUNTERFACTUAL_WORLD,
            "Validate isolated counterfactual worlds without outcome leakage.",
            ("capability", "intervention", "world_case"),
        ),
        _spec(
            "temporal-reasoning",
            ToolFamily.TEMPORAL_REASONING,
            "Probe temporal ordering and horizon consistency.",
            ("capability", "sequence_case", "horizon"),
        ),
        _spec(
            "regime-transition",
            ToolFamily.REGIME_TRANSITION,
            "Challenge regime-boundary recognition.",
            ("capability", "from_regime", "to_regime", "speed"),
        ),
        _spec(
            "memory-retrieval",
            ToolFamily.MEMORY_RETRIEVAL,
            "Probe relevant memory retrieval and provenance.",
            ("capability", "query_case", "memory_class"),
        ),
        _spec(
            "meta-learning",
            ToolFamily.META_LEARNING,
            "Probe adaptation to novel but bounded regime evidence.",
            ("capability", "novelty_case", "adaptation_budget"),
        ),
        _spec(
            "continual-learning-stability",
            ToolFamily.CONTINUAL_LEARNING_STABILITY,
            "Probe continual-learning stability.",
            ("capability", "update_sequence", "era"),
        ),
        _spec(
            "catastrophic-forgetting",
            ToolFamily.CATASTROPHIC_FORGETTING,
            "Verify old knowledge survives governed updates.",
            ("capability", "baseline_skill", "new_skill"),
        ),
        _spec(
            "ood-novelty",
            ToolFamily.OOD_NOVELTY,
            "Probe OOD detection and abstention.",
            ("capability", "novelty_case", "severity"),
        ),
        _spec(
            "active-perception",
            ToolFamily.ACTIVE_PERCEPTION,
            "Probe sensor-selection and attention choices.",
            ("capability", "observation_budget", "world_case"),
        ),
        _spec(
            "value-of-information",
            ToolFamily.VALUE_OF_INFORMATION,
            "Measure whether acquired information changes useful behavior.",
            ("capability", "information_source", "cost"),
        ),
        _spec(
            "sti-opportunity-discovery",
            ToolFamily.STI_OPPORTUNITY_DISCOVERY,
            "Probe opportunity discovery under controlled worlds.",
            ("capability", "trader", "world_case"),
        ),
        _spec(
            "threat-intelligence",
            ToolFamily.THREAT_INTELLIGENCE,
            "Probe threat detection and false-veto behavior.",
            ("capability", "trader", "threat_case"),
        ),
        _spec(
            "trader-routing",
            ToolFamily.TRADER_ROUTING,
            "Verify intelligence reaches the intended trader only.",
            ("producer", "trader", "routing_case"),
        ),
        _spec(
            "downstream-consumption",
            ToolFamily.DOWNSTREAM_CONSUMPTION,
            "Verify native downstream consumption and decision effect.",
            ("producer", "consumer", "case"),
        ),
        _spec(
            "cognitive-mutation",
            ToolFamily.COGNITIVE_MUTATION,
            "Force material engine-state mutation and require downstream reaction.",
            ("capability", "field", "mutation"),
        ),
        _spec(
            "cable-lineage-break",
            ToolFamily.CABLE_LINEAGE_BREAK,
            "Replace producer fingerprint with a non-parent input.",
            ("producer", "consumer"),
        ),
        _spec(
            "future-leakage-injection",
            ToolFamily.LEAKAGE_INJECTION,
            "Move available_at beyond decision_at.",
            ("datum", "future_delta_ns"),
        ),
        _spec(
            "duplicate-output-injection",
            ToolFamily.DUPLICATE_OUTPUT_INJECTION,
            "Duplicate a supposedly unique engine emission.",
            ("capability", "count"),
        ),
        _spec(
            "downstream-ignore-injection",
            ToolFamily.DOWNSTREAM_IGNORE_INJECTION,
            "Invoke cognition while suppressing downstream use.",
            ("capability", "consumer"),
        ),
        _spec(
            "ablation",
            ToolFamily.ABLATION,
            "Remove a capability and measure causal contribution.",
            ("capability", "consumer", "scenario"),
        ),
        _spec(
            "control-treatment",
            ToolFamily.CONTROL_TREATMENT,
            "Compare control and Shared-assisted treatment.",
            ("trader", "era", "scenario"),
        ),
        _spec(
            "stress",
            ToolFamily.STRESS,
            "Apply bounded adversarial stress.",
            ("capability", "stress_case", "severity"),
        ),
        _spec(
            "monte-carlo",
            ToolFamily.MONTE_CARLO,
            "Run resampled path stress against preregistered gates.",
            ("capability", "seed", "path_count"),
        ),
        _spec(
            "walk-forward",
            ToolFamily.WALK_FORWARD,
            "Run preregistered walk-forward folds.",
            ("capability", "fold", "era"),
        ),
        _spec(
            "multi-era-replication",
            ToolFamily.MULTI_ERA_REPLICATION,
            "Require independent pass by era.",
            ("capability", "era", "replication"),
        ),
        _spec(
            "failure-injection",
            ToolFamily.FAILURE_INJECTION,
            "Inject known failures for laboratory self-validation.",
            ("fault", "target", "severity"),
        ),
        _spec(
            "determinism-replay",
            ToolFamily.DETERMINISM_REPLAY,
            "Repeat identical inputs and require identical outputs.",
            ("capability", "replay_id", "seed"),
        ),
        _spec(
            "leakage-detection",
            ToolFamily.LEAKAGE_DETECTION,
            "Audit temporal availability against decision time.",
            ("capability", "datum", "case"),
        ),
        _spec(
            "authority-isolation",
            ToolFamily.AUTHORITY_ISOLATION,
            "Probe forbidden execution, risk, sizing and promotion authority.",
            ("component", "authority", "case"),
        ),
        _spec(
            "resource-latency",
            ToolFamily.RESOURCE_LATENCY,
            "Measure decision deadline and resource cost.",
            ("capability", "load_case", "deadline"),
        ),
        _spec(
            "redundancy-resilience",
            ToolFamily.REDUNDANCY_RESILIENCE,
            "Remove redundant sources and measure safe degradation.",
            ("capability", "dependency_set", "failure_case"),
        ),
    )
    for spec in specs:
        registry.register(spec)
    return registry


FAULT_TO_REQUIRED_TOOL: dict[LabFault, ToolFamily] = {
    LabFault.DEAD_NATIVE_ENGINE: ToolFamily.COGNITIVE_MUTATION,
    LabFault.ADAPTER_SUBSTITUTED_FOR_ENGINE: ToolFamily.COGNITIVE_MUTATION,
    LabFault.FAKE_CONSUMER: ToolFamily.CABLE_LINEAGE_BREAK,
    LabFault.FUTURE_LEAKAGE: ToolFamily.LEAKAGE_INJECTION,
    LabFault.STALE_SENSOR: ToolFamily.PROVIDER_DEGRADATION,
    LabFault.WRONG_SYMBOL_IDENTITY: ToolFamily.IDENTITY_MUTATION,
    LabFault.BROKEN_TIMESTAMP: ToolFamily.TIMESTAMP_PERTURBATION,
    LabFault.DUPLICATED_OUTPUT: ToolFamily.DUPLICATE_OUTPUT_INJECTION,
    LabFault.IGNORED_COGNITION: ToolFamily.DOWNSTREAM_IGNORE_INJECTION,
    LabFault.FAKE_PASS: ToolFamily.FAILURE_INJECTION,
}


def validate_l10_tool_coverage(
    registry: SharedLabToolRegistry,
) -> tuple[LabFault, ...]:
    families = {spec.family for spec in registry.list_tools()}
    return tuple(
        fault
        for fault, required_family in FAULT_TO_REQUIRED_TOOL.items()
        if required_family not in families
    )


def registry_fingerprint(registry: SharedLabToolRegistry) -> str:
    payload = [
        {
            "tool_id": spec.tool_id,
            "family": spec.family.value,
            "description": spec.description,
            "parameter_names": spec.parameter_names,
        }
        for spec in registry.list_tools()
    ]
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode()).hexdigest()
