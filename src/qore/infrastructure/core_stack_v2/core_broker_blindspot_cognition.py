"""MC-28 cognitive bridge for Core/Broker observability and blindspots.

Architect A consumes opaque, immutable source-side observability evidence from
Architect B and combines it with A-owned second-order blindspot cognition.
It does not acquire sensors, diagnose broker state without evidence, or mutate
runtime/ontology/provider configuration.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from enum import StrEnum

from qore.infrastructure.core_stack_v2.second_order_blindspot_cognition import (
    SharedSecondOrderBlindspotAssessment,
)


class SystemBlindspotState(StrEnum):
    OBSERVED_GAPS = "OBSERVED_GAPS"
    SECOND_ORDER_RESEARCH_PRIORITY = "SECOND_ORDER_RESEARCH_PRIORITY"
    OBSERVABILITY_INCOMPLETE = "OBSERVABILITY_INCOMPLETE"
    INSUFFICIENT = "INSUFFICIENT"


@dataclass(frozen=True, slots=True)
class ExternalObservabilityEvidence:
    source_run_id: int
    artifact_id: int
    core_observability_contract_validated: bool
    broker_observability_contract_validated: bool
    sensor_blindspot_contract_validated: bool
    unknown_world_contract_validated: bool
    runtime_core_broker_replication_complete: bool
    second_order_inventory_complete: bool
    known_gap_refs: tuple[str, ...]
    mutation_authority: bool = False

    def __post_init__(self) -> None:
        if self.source_run_id <= 0 or self.artifact_id <= 0:
            raise ValueError("external observability requires run/artifact identity")
        if (
            not self.known_gap_refs
            or self.known_gap_refs != tuple(sorted(set(self.known_gap_refs)))
        ):
            raise ValueError("known gap refs must be non-empty and canonical")
        if self.mutation_authority:
            raise ValueError("observability evidence cannot mutate runtime")


@dataclass(frozen=True, slots=True)
class CoreBrokerBlindspotSituation:
    state: SystemBlindspotState
    source_run_id: int
    source_artifact_id: int
    blindspot_class: str
    research_priority_bps: int
    known_gap_refs: tuple[str, ...]
    reason_codes: tuple[str, ...]
    provider_mutation_authority: bool = False
    ontology_mutation_authority: bool = False
    broker_mutation_authority: bool = False
    execution_authority: bool = False

    def __post_init__(self) -> None:
        if not 0 <= self.research_priority_bps <= 10_000:
            raise ValueError("research priority must be within 0..10000")
        if (
            self.known_gap_refs != tuple(sorted(set(self.known_gap_refs)))
            or not self.known_gap_refs
        ):
            raise ValueError("blindspot situation gaps must be canonical")
        if (
            self.reason_codes != tuple(sorted(set(self.reason_codes)))
            or not self.reason_codes
        ):
            raise ValueError("blindspot situation reasons must be canonical")
        if (
            self.provider_mutation_authority
            or self.ontology_mutation_authority
            or self.broker_mutation_authority
            or self.execution_authority
        ):
            raise ValueError("MC-28 cognition cannot mutate observed systems")

    def fingerprint(self) -> str:
        payload = asdict(self)
        payload["state"] = self.state.value
        raw = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(raw.encode()).hexdigest()


def build_core_broker_blindspot_situation(
    external: ExternalObservabilityEvidence,
    cognition: SharedSecondOrderBlindspotAssessment,
) -> CoreBrokerBlindspotSituation:
    reasons = list(cognition.reason_codes)
    contracts_ready = all(
        (
            external.core_observability_contract_validated,
            external.broker_observability_contract_validated,
            external.sensor_blindspot_contract_validated,
            external.unknown_world_contract_validated,
        )
    )
    if not contracts_ready:
        state = SystemBlindspotState.INSUFFICIENT
        reasons.append("SOURCE_OBSERVABILITY_CONTRACT_INCOMPLETE")
    elif (
        not external.runtime_core_broker_replication_complete
        or not external.second_order_inventory_complete
    ):
        state = SystemBlindspotState.OBSERVABILITY_INCOMPLETE
        reasons.append("RUNTIME_OR_SECOND_ORDER_INVENTORY_OPEN")
    elif cognition.blindspot_class.value == "SECOND_ORDER_UNKNOWN_UNKNOWN":
        state = SystemBlindspotState.SECOND_ORDER_RESEARCH_PRIORITY
        reasons.append("SECOND_ORDER_BLINDSPOT_DETECTED")
    else:
        state = SystemBlindspotState.OBSERVED_GAPS
        reasons.append("KNOWN_OBSERVABILITY_GAPS_PRESERVED")

    return CoreBrokerBlindspotSituation(
        state=state,
        source_run_id=external.source_run_id,
        source_artifact_id=external.artifact_id,
        blindspot_class=cognition.blindspot_class.value,
        research_priority_bps=cognition.research_priority_bps,
        known_gap_refs=external.known_gap_refs,
        reason_codes=tuple(sorted(set(reasons))),
    )
