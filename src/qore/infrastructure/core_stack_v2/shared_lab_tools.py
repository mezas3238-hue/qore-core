"""Parameterized tool registry and L10 fault-injection helpers for QORE Shared Lab."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from enum import StrEnum
from itertools import product
from typing import Any, Iterable, Mapping

from qore.infrastructure.core_stack_v2.shared_lab import LabFault


class ToolFamily(StrEnum):
    TIMESTAMP_PERTURBATION = "TIMESTAMP_PERTURBATION"
    SENSOR_FAILURE_INJECTOR = "SENSOR_FAILURE_INJECTOR"
    PROVIDER_DEGRADATION = "PROVIDER_DEGRADATION"
    IDENTITY_MUTATION = "IDENTITY_MUTATION"
    REPRESENTATION_PERTURBATION = "REPRESENTATION_PERTURBATION"
    COGNITIVE_MUTATION = "COGNITIVE_MUTATION"
    CABLE_LINEAGE_BREAK = "CABLE_LINEAGE_BREAK"
    LEAKAGE_INJECTION = "LEAKAGE_INJECTION"
    DUPLICATE_OUTPUT_INJECTION = "DUPLICATE_OUTPUT_INJECTION"
    DOWNSTREAM_IGNORE_INJECTION = "DOWNSTREAM_IGNORE_INJECTION"


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

    def expand(self, tool_id: str, parameter_grid: Mapping[str, Iterable[Any]]) -> tuple[ProbeCase, ...]:
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


def default_shared_lab_registry() -> SharedLabToolRegistry:
    registry = SharedLabToolRegistry()
    specs = (
        LabToolSpec(
            "timestamp-perturbation",
            ToolFamily.TIMESTAMP_PERTURBATION,
            "Perturb chronology while preserving explicit provenance.",
            ("sensor", "asset", "offset", "regime"),
        ),
        LabToolSpec(
            "sensor-failure-injector",
            ToolFamily.SENSOR_FAILURE_INJECTOR,
            "Remove or degrade a sensor for bounded intervals.",
            ("sensor", "missing_pct", "duration", "regime", "asset"),
        ),
        LabToolSpec(
            "provider-degradation",
            ToolFamily.PROVIDER_DEGRADATION,
            "Inject stale, partial, delayed or conflicting provider evidence.",
            ("provider", "mode", "asset", "duration"),
        ),
        LabToolSpec(
            "identity-mutation",
            ToolFamily.IDENTITY_MUTATION,
            "Mutate symbol aliases/classification to validate canonical identity.",
            ("asset", "mutation"),
        ),
        LabToolSpec(
            "cognitive-mutation",
            ToolFamily.COGNITIVE_MUTATION,
            "Force material internal engine-state mutation and require downstream reaction.",
            ("capability", "field", "mutation"),
        ),
        LabToolSpec(
            "cable-lineage-break",
            ToolFamily.CABLE_LINEAGE_BREAK,
            "Replace producer fingerprint with a non-parent consumer input.",
            ("producer", "consumer"),
        ),
        LabToolSpec(
            "future-leakage-injection",
            ToolFamily.LEAKAGE_INJECTION,
            "Move available_at beyond decision_at to validate leakage firewall.",
            ("datum", "future_delta_ns"),
        ),
        LabToolSpec(
            "duplicate-output-injection",
            ToolFamily.DUPLICATE_OUTPUT_INJECTION,
            "Duplicate a supposedly unique engine emission.",
            ("capability", "count"),
        ),
        LabToolSpec(
            "downstream-ignore-injection",
            ToolFamily.DOWNSTREAM_IGNORE_INJECTION,
            "Invoke cognition but deliberately suppress its downstream use.",
            ("capability", "consumer"),
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
    LabFault.FAKE_PASS: ToolFamily.COGNITIVE_MUTATION,
}


def validate_l10_tool_coverage(registry: SharedLabToolRegistry) -> tuple[LabFault, ...]:
    families = {spec.family for spec in registry.list_tools()}
    return tuple(
        fault for fault, required_family in FAULT_TO_REQUIRED_TOOL.items()
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
