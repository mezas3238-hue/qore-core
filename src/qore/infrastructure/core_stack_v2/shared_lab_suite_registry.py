"""Extensible native validation suite registry for QORE Shared Lab."""

from __future__ import annotations

import fnmatch
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from qore.infrastructure.core_stack_v2.shared_lab_native_model import (
    ExecutionMode,
    LabScope,
    RunRequest,
    TaskSpec,
    ValidationSuite,
)


@dataclass(frozen=True, slots=True)
class SuiteDefinition:
    task_id: str
    suite: ValidationSuite
    scope: LabScope
    dependencies: tuple[str, ...]
    command: tuple[str, ...]
    component_globs: tuple[str, ...]
    execution_origin: str = "HARNESS"
    dataset_id: str | None = None
    dataset_version: str | None = None


class NativeSuiteRegistry:
    def __init__(self) -> None:
        self._definitions: dict[str, SuiteDefinition] = {}

    def register(self, definition: SuiteDefinition) -> None:
        existing = self._definitions.get(definition.task_id)
        if existing is not None:
            if existing == definition:
                return
            raise ValueError(f"conflicting duplicate suite task: {definition.task_id}")
        self._definitions[definition.task_id] = definition

    def clone(self) -> NativeSuiteRegistry:
        result = NativeSuiteRegistry()
        for definition in self.definitions():
            result.register(definition)
        return result

    def definitions(self) -> tuple[SuiteDefinition, ...]:
        return tuple(self._definitions[key] for key in sorted(self._definitions))

    def get(self, task_id: str) -> SuiteDefinition:
        return self._definitions[task_id]

    def load_plugins(self, plugin_dir: Path) -> None:
        if not plugin_dir.exists():
            return
        for path in sorted(plugin_dir.glob("*.json")):
            payload: dict[str, Any] = json.loads(path.read_text())
            self.register(
                SuiteDefinition(
                    task_id=str(payload["task_id"]),
                    suite=ValidationSuite(str(payload["suite"])),
                    scope=LabScope(str(payload["scope"])),
                    dependencies=tuple(str(x) for x in payload.get("dependencies", [])),
                    command=tuple(str(x) for x in payload["command"]),
                    component_globs=tuple(
                        str(x) for x in payload.get("component_globs", [])
                    ),
                    execution_origin=str(
                        payload.get("execution_origin", "TARGET")
                    ).upper(),
                    dataset_id=(
                        None
                        if payload.get("dataset_id") is None
                        else str(payload["dataset_id"])
                    ),
                    dataset_version=(
                        None
                        if payload.get("dataset_version") is None
                        else str(payload["dataset_version"])
                    ),
                )
            )

    def impacted_task_ids(self, changed_paths: tuple[str, ...]) -> frozenset[str]:
        if not changed_paths:
            return frozenset()
        impacted: set[str] = set()
        for definition in self._definitions.values():
            if any(
                fnmatch.fnmatch(path, pattern)
                for path in changed_paths
                for pattern in definition.component_globs
            ):
                impacted.add(definition.task_id)
        return frozenset(impacted)

    def plan(
        self,
        request: RunRequest,
        changed_paths: tuple[str, ...],
    ) -> tuple[TaskSpec, ...]:
        selected = self._select_ids(request, changed_paths)
        selected = self._with_dependencies(selected)
        specs = tuple(
            TaskSpec(
                task_id=definition.task_id,
                suite=definition.suite,
                scope=definition.scope,
                dependencies=tuple(
                    dep for dep in definition.dependencies if dep in selected
                ),
                command=definition.command,
                component_globs=definition.component_globs,
                timeout_seconds=request.policy.timeout_seconds,
                retries=request.policy.retries,
                execution_origin=definition.execution_origin,
                dataset_id=definition.dataset_id,
                dataset_version=definition.dataset_version,
            )
            for definition in self.definitions()
            if definition.task_id in selected
        )
        if not specs:
            raise ValueError("validation plan is empty")
        return specs

    def _with_dependencies(self, selected: set[str]) -> set[str]:
        result = set(selected)
        changed = True
        while changed:
            changed = False
            for task_id in tuple(result):
                for dependency in self.get(task_id).dependencies:
                    if dependency not in result:
                        result.add(dependency)
                        changed = True
        return result

    def _select_ids(
        self,
        request: RunRequest,
        changed_paths: tuple[str, ...],
    ) -> set[str]:
        if request.mode is ExecutionMode.CERTIFICATION:
            return {item.task_id for item in self.definitions()}
        if request.mode is ExecutionMode.FULL:
            return {
                item.task_id
                for item in self.definitions()
                if item.suite is not ValidationSuite.CERTIFICATION
            }
        if request.mode is ExecutionMode.REPLAY:
            return {"replay", "determinism"}
        if request.mode is ExecutionMode.REGRESSION:
            return {"regression"}
        if request.mode is ExecutionMode.QUICK:
            selected = {"unit", "contract"}
            if request.scope is not LabScope.FULL_STACK:
                selected.update(self._scope_primary_ids(request.scope))
            return selected
        if request.mode is ExecutionMode.COMPONENT:
            impacted = set(self.impacted_task_ids(changed_paths))
            if impacted:
                return impacted | {"contract"}
            return self._scope_primary_ids(request.scope) | {"contract"}
        if request.mode is ExecutionMode.INTEGRATION:
            return self._scope_primary_ids(request.scope) | {
                "integration",
                "consumer-validation",
            }
        return self._scope_primary_ids(request.scope) | {
            "functional",
            "causality",
            "stress",
            "performance",
        }

    @staticmethod
    def _scope_primary_ids(scope: LabScope) -> set[str]:
        mapping = {
            LabScope.DATA: {"data-reality"},
            LabScope.SENSOR: {"sensor-reality"},
            LabScope.IDENTITY: {"identity-reality"},
            LabScope.TEMPORAL: {"temporal-reality"},
            LabScope.PROVIDER: {"provider-reality"},
            LabScope.COGNITION: {"functional", "causality"},
            LabScope.DECISION: {"consumer-validation", "end-to-end"},
            LabScope.MC18: {"mc18-functional", "causality"},
            LabScope.MC23: {"mc23-functional", "causality"},
            LabScope.FULL_STACK: {"full-stack"},
        }
        return set(mapping[scope])


def _pytest(*paths: str) -> tuple[str, ...]:
    return (sys.executable, "-m", "pytest", "-q", *paths)


def default_native_suite_registry() -> NativeSuiteRegistry:
    registry = NativeSuiteRegistry()
    common = ("src/qore/infrastructure/core_stack_v2/shared_lab*.py",)
    definitions = (
        SuiteDefinition(
            "unit",
            ValidationSuite.UNIT,
            LabScope.FULL_STACK,
            (),
            _pytest("tests/infrastructure/test_core_stack_v2_shared_lab.py"),
            common + ("tests/infrastructure/test_core_stack_v2_shared_lab.py",),
        ),
        SuiteDefinition(
            "contract",
            ValidationSuite.CONTRACT,
            LabScope.FULL_STACK,
            ("unit",),
            _pytest(
                "tests/infrastructure/test_core_stack_v2_shared_lab_gate_policy.py",
                "tests/infrastructure/test_core_stack_v2_shared_lab_proof.py",
            ),
            common,
        ),
        SuiteDefinition(
            "data-reality",
            ValidationSuite.DATA_REALITY,
            LabScope.DATA,
            ("contract",),
            _pytest("tests/infrastructure/test_core_stack_v2_shared_lab_data_exam.py"),
            common + ("tests/infrastructure/test_core_stack_v2_shared_lab_data*.py",),
        ),
        SuiteDefinition(
            "sensor-reality",
            ValidationSuite.SENSOR_REALITY,
            LabScope.SENSOR,
            ("contract",),
            _pytest("tests/infrastructure/test_core_stack_v2_shared_lab_sensor_harness.py"),
            common + ("tests/infrastructure/test_core_stack_v2_shared_lab_sensor*.py",),
        ),
        SuiteDefinition(
            "identity-reality",
            ValidationSuite.IDENTITY_REALITY,
            LabScope.IDENTITY,
            ("contract",),
            _pytest(
                "tests/infrastructure/test_core_stack_v2_shared_lab_identity_harness.py",
                "tests/infrastructure/test_core_stack_v2_shared_lab_identity_multiasset.py",
            ),
            common + ("tests/infrastructure/test_core_stack_v2_shared_lab_identity*.py",),
        ),
        SuiteDefinition(
            "temporal-reality",
            ValidationSuite.TEMPORAL_REALITY,
            LabScope.TEMPORAL,
            ("contract",),
            _pytest(
                "tests/infrastructure/test_core_stack_v2_shared_lab_temporal_harness.py",
                "tests/infrastructure/test_core_stack_v2_shared_lab_temporal_context.py",
            ),
            common + ("tests/infrastructure/test_core_stack_v2_shared_lab_temporal*.py",),
        ),
        SuiteDefinition(
            "provider-reality",
            ValidationSuite.PROVIDER_REALITY,
            LabScope.PROVIDER,
            ("contract",),
            _pytest(
                "tests/infrastructure/test_core_stack_v2_shared_lab_provider_harness.py",
                "tests/infrastructure/test_core_stack_v2_shared_lab_provider_scenarios.py",
            ),
            common + ("tests/infrastructure/test_core_stack_v2_shared_lab_provider*.py",),
        ),
        SuiteDefinition(
            "integration",
            ValidationSuite.INTEGRATION,
            LabScope.FULL_STACK,
            (
                "data-reality",
                "sensor-reality",
                "identity-reality",
                "temporal-reality",
                "provider-reality",
            ),
            _pytest(
                "tests/infrastructure/test_core_stack_v2_shared_lab_runtime_probe.py",
                "tests/infrastructure/test_core_stack_v2_shared_lab_organism.py",
            ),
            common,
        ),
        SuiteDefinition(
            "functional",
            ValidationSuite.FUNCTIONAL,
            LabScope.COGNITION,
            ("integration",),
            _pytest(
                "tests/infrastructure/test_core_stack_v2_shared_lab_cognition.py",
                "tests/infrastructure/test_core_stack_v2_shared_lab_counterfactual.py",
                "tests/infrastructure/test_core_stack_v2_shared_lab_operational.py",
            ),
            common,
        ),
        SuiteDefinition(
            "mc18-functional",
            ValidationSuite.FUNCTIONAL,
            LabScope.MC18,
            ("integration",),
            _pytest(
                "tests/infrastructure/test_core_stack_v2_shared_lab_counterfactual.py",
                "tests/infrastructure/test_core_stack_v2_shared_lab_experiments.py",
            ),
            common,
        ),
        SuiteDefinition(
            "causality",
            ValidationSuite.CAUSALITY,
            LabScope.COGNITION,
            ("functional",),
            _pytest(
                "tests/infrastructure/test_core_stack_v2_shared_lab_causality.py",
                "tests/infrastructure/test_core_stack_v2_shared_lab_experiments.py",
            ),
            common,
        ),
        SuiteDefinition(
            "consumer-validation",
            ValidationSuite.CONSUMER_VALIDATION,
            LabScope.DECISION,
            ("functional",),
            _pytest(
                "tests/infrastructure/test_core_stack_v2_shared_lab_seven_trader.py",
                "tests/infrastructure/test_core_stack_v2_shared_lab_runtime_probe.py",
            ),
            common,
        ),
        SuiteDefinition(
            "end-to-end",
            ValidationSuite.END_TO_END,
            LabScope.DECISION,
            ("consumer-validation", "causality"),
            _pytest(
                "tests/infrastructure/test_core_stack_v2_shared_lab_flight_recorder.py",
                "tests/infrastructure/test_core_stack_v2_shared_lab_organism.py",
            ),
            common,
        ),
        SuiteDefinition(
            "replay",
            ValidationSuite.REPLAY,
            LabScope.FULL_STACK,
            ("contract",),
            (
                sys.executable,
                "-m",
                "qore.infrastructure.core_stack_v2.shared_lab_native_replay",
                "--scenario",
                "{scenario}",
            ),
            common,
        ),
        SuiteDefinition(
            "determinism",
            ValidationSuite.DETERMINISM,
            LabScope.FULL_STACK,
            ("replay",),
            _pytest("tests/infrastructure/test_core_stack_v2_shared_lab_replay.py"),
            common,
        ),
        SuiteDefinition(
            "regression",
            ValidationSuite.REGRESSION,
            LabScope.FULL_STACK,
            ("functional",),
            _pytest(
                "tests/infrastructure/test_core_stack_v2_shared_lab_influence.py",
                "tests/infrastructure/test_core_stack_v2_shared_lab_ledger.py",
            ),
            common,
        ),
        SuiteDefinition(
            "stress",
            ValidationSuite.STRESS,
            LabScope.FULL_STACK,
            ("functional",),
            _pytest(
                "tests/infrastructure/test_core_stack_v2_shared_lab_resilience.py",
                "tests/infrastructure/test_core_stack_v2_shared_lab_learning.py",
            ),
            common,
        ),
        SuiteDefinition(
            "monte-carlo",
            ValidationSuite.MONTE_CARLO,
            LabScope.FULL_STACK,
            ("functional",),
            _pytest("tests/infrastructure/test_core_stack_v2_shared_lab_statistics.py"),
            common,
        ),
        SuiteDefinition(
            "performance",
            ValidationSuite.PERFORMANCE,
            LabScope.FULL_STACK,
            ("functional",),
            _pytest("tests/infrastructure/test_core_stack_v2_shared_lab_operational.py"),
            common,
        ),
        SuiteDefinition(
            "failure-injection",
            ValidationSuite.FAILURE_INJECTION,
            LabScope.FULL_STACK,
            ("integration",),
            _pytest(
                "tests/infrastructure/test_core_stack_v2_shared_lab_integrity.py",
                "tests/infrastructure/test_core_stack_v2_shared_lab_data_l10.py",
            ),
            common,
        ),
        SuiteDefinition(
            "full-stack",
            ValidationSuite.FULL_STACK,
            LabScope.FULL_STACK,
            (
                "end-to-end",
                "stress",
                "monte-carlo",
                "performance",
                "determinism",
                "failure-injection",
                "regression",
            ),
            _pytest("tests/infrastructure/test_core_stack_v2_shared_lab_global_exam.py"),
            common,
        ),
        SuiteDefinition(
            "certification",
            ValidationSuite.CERTIFICATION,
            LabScope.FULL_STACK,
            ("full-stack",),
            _pytest(
                "tests/infrastructure/test_core_stack_v2_shared_lab_authority.py",
                "tests/infrastructure/test_core_stack_v2_shared_lab_readiness.py",
                "tests/infrastructure/test_core_stack_v2_shared_lab_global_exam.py",
            ),
            common,
        ),
    )
    for definition in definitions:
        registry.register(definition)
    return registry
