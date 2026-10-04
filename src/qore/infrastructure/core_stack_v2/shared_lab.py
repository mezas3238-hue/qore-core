"""QORE Shared Lab core primitives.

Independent validation authority for Shared. This module is intentionally
authority-free: it can prove/falsify capability behavior and wiring, but it
cannot promote runtime, open protected holdouts, size, trade, or certify.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from enum import StrEnum


class SharedLabLevel(StrEnum):
    L0_STRUCTURAL_REALITY = "L0_STRUCTURAL_REALITY"
    L1_SENSOR_REALITY = "L1_SENSOR_REALITY"
    L2_REPRESENTATION_REALITY = "L2_REPRESENTATION_REALITY"
    L3_COGNITIVE_REALITY = "L3_COGNITIVE_REALITY"
    L4_COGNITIVE_INTERACTION = "L4_COGNITIVE_INTERACTION"
    L5_CAUSAL_CONTRIBUTION = "L5_CAUSAL_CONTRIBUTION"
    L6_SCIENTIFIC_REALITY = "L6_SCIENTIFIC_REALITY"
    L7_ADVERSARIAL_LAB = "L7_ADVERSARIAL_LAB"
    L8_SEVEN_TRADER_REALITY = "L8_SEVEN_TRADER_REALITY"
    L9_FULL_ORGANISM_END_TO_END = "L9_FULL_ORGANISM_END_TO_END"
    L10_LABORATORY_INTEGRITY = "L10_LABORATORY_INTEGRITY"


class EngineKind(StrEnum):
    NATIVE = "NATIVE"
    ADAPTER = "ADAPTER"
    BRIDGE = "BRIDGE"
    WRAPPER = "WRAPPER"
    SHADOW = "SHADOW"
    MOCK = "MOCK"
    FALLBACK = "FALLBACK"


class LabFault(StrEnum):
    DEAD_NATIVE_ENGINE = "DEAD_NATIVE_ENGINE"
    ADAPTER_SUBSTITUTED_FOR_ENGINE = "ADAPTER_SUBSTITUTED_FOR_ENGINE"
    FAKE_CONSUMER = "FAKE_CONSUMER"
    FUTURE_LEAKAGE = "FUTURE_LEAKAGE"
    STALE_SENSOR = "STALE_SENSOR"
    WRONG_SYMBOL_IDENTITY = "WRONG_SYMBOL_IDENTITY"
    BROKEN_TIMESTAMP = "BROKEN_TIMESTAMP"
    DUPLICATED_OUTPUT = "DUPLICATED_OUTPUT"
    IGNORED_COGNITION = "IGNORED_COGNITION"
    FAKE_PASS = "FAKE_PASS"


@dataclass(frozen=True, slots=True)
class NativeEngineReceipt:
    capability_id: str
    engine_id: str
    engine_kind: EngineKind
    real_input: bool
    native_engine_exists: bool
    native_engine_called: bool
    typed_output_emitted: bool
    adapter_only: bool = False
    shadow_only: bool = False
    mock_used: bool = False
    fallback_used: bool = False
    downstream_native_consumer: str | None = None

    @property
    def passed(self) -> bool:
        return (
            self.real_input
            and self.engine_kind is EngineKind.NATIVE
            and self.native_engine_exists
            and self.native_engine_called
            and self.typed_output_emitted
            and not self.adapter_only
            and not self.shadow_only
            and not self.mock_used
            and self.downstream_native_consumer is not None
        )


@dataclass(frozen=True, slots=True)
class CableRealityReceipt:
    producer: str
    consumer: str
    producer_output_sha256: str
    consumer_input_parent_sha256: str
    observed: bool
    consumed: bool
    decision_changed: bool

    @property
    def lineage_exact(self) -> bool:
        return self.producer_output_sha256 == self.consumer_input_parent_sha256

    @property
    def passed(self) -> bool:
        return self.observed and self.consumed and self.lineage_exact


@dataclass(frozen=True, slots=True)
class EfficiencyReceipt:
    capability_id: str
    invocation_count: int
    meaningful_output_count: int
    downstream_consumed_count: int
    downstream_changed_count: int
    no_change_count: int
    abstention_count: int
    contradiction_count: int
    incremental_value: float
    incremental_risk_reduction: float
    incremental_information_gain: float
    latency_p99_ms: float
    decision_deadline_ms: float

    def __post_init__(self) -> None:
        values = (
            self.invocation_count,
            self.meaningful_output_count,
            self.downstream_consumed_count,
            self.downstream_changed_count,
            self.no_change_count,
            self.abstention_count,
            self.contradiction_count,
        )
        if any(value < 0 for value in values):
            raise ValueError("counts cannot be negative")
        if self.meaningful_output_count > self.invocation_count:
            raise ValueError("meaningful outputs cannot exceed invocations")
        if self.downstream_consumed_count > self.meaningful_output_count:
            raise ValueError("consumption cannot exceed meaningful outputs")
        if self.downstream_changed_count > self.downstream_consumed_count:
            raise ValueError("changes cannot exceed consumption")

    @property
    def useful_action_rate(self) -> float:
        return 0.0 if self.invocation_count == 0 else self.downstream_changed_count / self.invocation_count

    @property
    def cognitively_live(self) -> bool:
        return (
            self.downstream_changed_count > 0
            or self.incremental_value > 0
            or self.incremental_risk_reduction > 0
            or self.incremental_information_gain > 0
        )

    @property
    def deadline_pass(self) -> bool:
        return self.latency_p99_ms <= self.decision_deadline_ms


@dataclass(frozen=True, slots=True)
class TemporalDatumReceipt:
    datum_id: str
    observed_at_ns: int
    available_at_ns: int
    decision_at_ns: int
    consumed_at_ns: int

    @property
    def leakage_free(self) -> bool:
        return (
            self.observed_at_ns <= self.available_at_ns
            and self.available_at_ns <= self.decision_at_ns
            and self.decision_at_ns <= self.consumed_at_ns
        )


@dataclass(frozen=True, slots=True)
class InfluenceEdge:
    producer: str
    consumer: str
    real: bool
    tested: bool
    observed: bool
    consumed: bool
    value_proven: bool
    fingerprint_match: bool

    @property
    def dead(self) -> bool:
        return not (self.real and self.tested and self.observed and self.consumed and self.fingerprint_match)


@dataclass(frozen=True, slots=True)
class CapabilityLabRecord:
    capability_id: str
    engineering_green: bool
    required_levels: tuple[SharedLabLevel, ...]
    passed_levels: tuple[SharedLabLevel, ...]
    native_engine: NativeEngineReceipt
    cables: tuple[CableRealityReceipt, ...]
    efficiency: EfficiencyReceipt
    temporal_data: tuple[TemporalDatumReceipt, ...]
    mutation_pass: bool
    metamorphic_pass: bool
    ablation_pass: bool

    @property
    def leakage_free(self) -> bool:
        return all(item.leakage_free for item in self.temporal_data)

    @property
    def required_levels_pass(self) -> bool:
        return set(self.required_levels).issubset(self.passed_levels)

    @property
    def cable_reality_pass(self) -> bool:
        return bool(self.cables) and all(item.passed for item in self.cables)

    @property
    def phase_proven(self) -> bool:
        return (
            self.engineering_green
            and self.native_engine.passed
            and self.required_levels_pass
            and self.cable_reality_pass
            and self.efficiency.cognitively_live
            and self.efficiency.deadline_pass
            and self.leakage_free
            and self.mutation_pass
            and self.metamorphic_pass
            and self.ablation_pass
        )

    def fingerprint(self) -> str:
        raw = json.dumps(asdict(self), sort_keys=True, separators=(",", ":"), default=str)
        return hashlib.sha256(raw.encode()).hexdigest()


@dataclass(frozen=True, slots=True)
class LabIntegrityReceipt:
    injected_faults: tuple[LabFault, ...]
    detected_faults: tuple[LabFault, ...]

    @property
    def missing_detections(self) -> tuple[LabFault, ...]:
        detected = set(self.detected_faults)
        return tuple(item for item in self.injected_faults if item not in detected)

    @property
    def passed(self) -> bool:
        return bool(self.injected_faults) and not self.missing_detections


@dataclass(frozen=True, slots=True)
class SharedLabAssessment:
    capability_count: int
    phase_proven_count: int
    failed_capability_ids: tuple[str, ...]
    dead_edge_count: int
    l10_pass: bool
    all_required_capabilities_proven: bool
    pre_certification_authorized: bool = False
    protected_holdout_opening_authorized: bool = False
    productive_authority: bool = False

    def __post_init__(self) -> None:
        if self.pre_certification_authorized:
            raise ValueError("Shared Lab cannot authorize pre-certification")
        if self.protected_holdout_opening_authorized:
            raise ValueError("Shared Lab cannot open protected holdout")
        if self.productive_authority:
            raise ValueError("Shared Lab grants no productive authority")


def assess_shared_lab(
    records: tuple[CapabilityLabRecord, ...],
    edges: tuple[InfluenceEdge, ...],
    l10: LabIntegrityReceipt,
) -> SharedLabAssessment:
    failed = tuple(sorted(item.capability_id for item in records if not item.phase_proven))
    dead_edges = sum(edge.dead for edge in edges)
    all_proven = bool(records) and not failed and dead_edges == 0 and l10.passed
    return SharedLabAssessment(
        capability_count=len(records),
        phase_proven_count=len(records) - len(failed),
        failed_capability_ids=failed,
        dead_edge_count=dead_edges,
        l10_pass=l10.passed,
        all_required_capabilities_proven=all_proven,
    )
