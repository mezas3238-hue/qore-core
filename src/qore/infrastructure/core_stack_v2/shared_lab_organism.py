"""Cognitive organism trace assembly for QORE Shared Lab L9.

Reconstructs a chain from exact runtime fingerprints. It does not infer missing
links: any broken parent lineage keeps the organism unproven.
"""

from __future__ import annotations

from dataclasses import dataclass

from qore.infrastructure.core_stack_v2.shared_lab_runtime_probe import (
    DownstreamConsumptionTrace,
    NativeInvocationTrace,
)


@dataclass(frozen=True, slots=True)
class OrganismTraceNode:
    capability_id: str
    input_fingerprint: str
    output_fingerprint: str
    native_engine_called: bool
    output_type: str


@dataclass(frozen=True, slots=True)
class OrganismTraceEdge:
    producer: str
    consumer: str
    producer_output_fingerprint: str
    consumer_input_fingerprint: str
    lineage_exact: bool
    consumed: bool
    downstream_changed: bool


@dataclass(frozen=True, slots=True)
class OrganismTraceAssessment:
    node_count: int
    edge_count: int
    broken_edges: tuple[tuple[str, str], ...]
    uncalled_nodes: tuple[str, ...]
    terminal_output_fingerprint: str | None
    l9_end_to_end_proven: bool


def build_organism_trace(
    invocations: tuple[NativeInvocationTrace, ...],
    consumptions: tuple[DownstreamConsumptionTrace, ...],
) -> OrganismTraceAssessment:
    if not invocations:
        raise ValueError("organism trace requires native invocations")
    ids = tuple(item.capability_id for item in invocations)
    if len(ids) != len(set(ids)):
        raise ValueError("organism trace capability identities must be unique")

    node_map = {
        item.capability_id: OrganismTraceNode(
            capability_id=item.capability_id,
            input_fingerprint=item.input_fingerprint,
            output_fingerprint=item.output_fingerprint,
            native_engine_called=item.native_receipt.native_engine_called,
            output_type=item.output_type,
        )
        for item in invocations
    }
    edges: list[OrganismTraceEdge] = []
    broken: list[tuple[str, str]] = []
    consumers: set[str] = set()
    producers: set[str] = set()

    for item in consumptions:
        producers.add(item.producer_capability_id)
        consumers.add(item.consumer_capability_id)
        lineage_exact = (
            item.producer_output_fingerprint == item.consumer_input_fingerprint
            and item.cable_receipt.lineage_exact
        )
        if not lineage_exact or not item.consumer_invoked:
            broken.append((item.producer_capability_id, item.consumer_capability_id))
        edges.append(
            OrganismTraceEdge(
                producer=item.producer_capability_id,
                consumer=item.consumer_capability_id,
                producer_output_fingerprint=item.producer_output_fingerprint,
                consumer_input_fingerprint=item.consumer_input_fingerprint,
                lineage_exact=lineage_exact,
                consumed=item.consumer_invoked,
                downstream_changed=item.consumer_changed_output,
            )
        )

    uncalled = tuple(
        sorted(node.capability_id for node in node_map.values() if not node.native_engine_called)
    )
    terminal_ids = sorted(set(node_map).difference(producers))
    terminal_fp = node_map[terminal_ids[-1]].output_fingerprint if len(terminal_ids) == 1 else None
    all_consumers_known = consumers.issubset(node_map)
    proven = (
        bool(edges)
        and not broken
        and not uncalled
        and all_consumers_known
        and terminal_fp is not None
    )
    return OrganismTraceAssessment(
        node_count=len(node_map),
        edge_count=len(edges),
        broken_edges=tuple(sorted(broken)),
        uncalled_nodes=uncalled,
        terminal_output_fingerprint=terminal_fp,
        l9_end_to_end_proven=proven,
    )
