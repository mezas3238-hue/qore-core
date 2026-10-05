"""L9 cognitive flight recorder for QORE Shared Lab."""

from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum


class FlightStage(IntEnum):
    PROVIDER = 1
    SENSOR = 2
    IDENTITY_TIME_PROVENANCE = 3
    NORMALIZATION = 4
    REPRESENTATION = 5
    RELATIONAL_GRAPH = 6
    WORLD_MODEL = 7
    LATENT_STATE = 8
    BELIEF_STATE = 9
    MARKET_PHYSICS = 10
    CAUSAL_MODEL = 11
    TEMPORAL_BRAIN = 12
    COUNTERFACTUAL = 13
    MEMORY_META_LEARNING = 14
    ACTIVE_PERCEPTION = 15
    OPPORTUNITY_THREAT = 16
    STI = 17
    TRADER_CONSUMPTION = 18
    OBSERVABLE_EFFECT = 19


@dataclass(frozen=True, slots=True)
class FlightNode:
    stage: FlightStage
    component_id: str
    timestamp_ns: int
    code_sha: str
    input_ids: tuple[str, ...]
    output_id: str
    confidence: float
    uncertainty: float
    provenance_ids: tuple[str, ...]
    consumer_ids: tuple[str, ...]

    def __post_init__(self) -> None:
        if not self.component_id.strip() or not self.code_sha.strip():
            raise ValueError("flight node requires component identity and code SHA")
        if not self.output_id.strip():
            raise ValueError("flight node requires output identity")
        if not (0.0 <= self.confidence <= 1.0):
            raise ValueError("confidence must be in [0,1]")
        if not (0.0 <= self.uncertainty <= 1.0):
            raise ValueError("uncertainty must be in [0,1]")
        if not self.provenance_ids:
            raise ValueError("flight node requires provenance")


@dataclass(frozen=True, slots=True)
class FlightTraceAssessment:
    node_count: int
    missing_stages: tuple[FlightStage, ...]
    duplicate_output_ids: tuple[str, ...]
    broken_parent_refs: tuple[str, ...]
    nonmonotonic_stage_pairs: tuple[tuple[FlightStage, FlightStage], ...]
    missing_consumer_links: tuple[str, ...]
    l9_flight_trace_proven: bool


def assess_flight_trace(
    nodes: tuple[FlightNode, ...],
    *,
    required_stages: frozenset[FlightStage] = frozenset(FlightStage),
) -> FlightTraceAssessment:
    if not nodes:
        raise ValueError("flight trace requires nodes")

    present_stages = {node.stage for node in nodes}
    missing = tuple(
        sorted(
            required_stages - present_stages,
            key=int,
        )
    )

    output_counts: dict[str, int] = {}
    for node in nodes:
        output_counts[node.output_id] = output_counts.get(node.output_id, 0) + 1
    duplicates = tuple(
        sorted(output_id for output_id, count in output_counts.items() if count > 1)
    )

    known_outputs: set[str] = set()
    broken_parents: list[str] = []
    missing_consumers: list[str] = []
    nonmonotonic: list[tuple[FlightStage, FlightStage]] = []
    ordered = sorted(nodes, key=lambda item: (item.timestamp_ns, int(item.stage)))

    previous: FlightNode | None = None
    for node in ordered:
        if node.stage is not FlightStage.PROVIDER:
            for parent in node.input_ids:
                if parent not in known_outputs:
                    broken_parents.append(f"{node.component_id}:{parent}")
        known_outputs.add(node.output_id)
        if node.stage is not FlightStage.OBSERVABLE_EFFECT and not node.consumer_ids:
            missing_consumers.append(node.component_id)
        if previous is not None and int(node.stage) < int(previous.stage):
            nonmonotonic.append((previous.stage, node.stage))
        previous = node

    proven = (
        not missing
        and not duplicates
        and not broken_parents
        and not missing_consumers
        and not nonmonotonic
    )
    return FlightTraceAssessment(
        node_count=len(nodes),
        missing_stages=missing,
        duplicate_output_ids=duplicates,
        broken_parent_refs=tuple(sorted(broken_parents)),
        nonmonotonic_stage_pairs=tuple(nonmonotonic),
        missing_consumer_links=tuple(sorted(missing_consumers)),
        l9_flight_trace_proven=proven,
    )
