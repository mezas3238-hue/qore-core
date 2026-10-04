"""Capability Influence Graph for QORE Shared Lab.

Detects dead nodes, dead edges, decorative modules, duplicate intelligence and
cycles from observed capability-to-capability evidence.
"""

from __future__ import annotations

from dataclasses import dataclass

from qore.infrastructure.core_stack_v2.shared_lab import InfluenceEdge


@dataclass(frozen=True, slots=True)
class CapabilityNode:
    capability_id: str
    invoked: bool
    meaningful_output: bool
    downstream_consumed: bool
    downstream_changed: bool
    intelligence_fingerprint: str | None = None

    @property
    def dead_node(self) -> bool:
        return not self.invoked or not self.meaningful_output or not self.downstream_consumed

    @property
    def decorative(self) -> bool:
        return self.invoked and self.meaningful_output and self.downstream_consumed and not self.downstream_changed


@dataclass(frozen=True, slots=True)
class InfluenceGraphAssessment:
    dead_nodes: tuple[str, ...]
    decorative_nodes: tuple[str, ...]
    duplicate_intelligence_groups: tuple[tuple[str, ...], ...]
    dead_edges: tuple[tuple[str, str], ...]
    cycle_paths: tuple[tuple[str, ...], ...]
    graph_proven: bool


def _find_cycles(edges: tuple[InfluenceEdge, ...]) -> tuple[tuple[str, ...], ...]:
    adjacency: dict[str, set[str]] = {}
    for edge in edges:
        adjacency.setdefault(edge.producer, set()).add(edge.consumer)
        adjacency.setdefault(edge.consumer, set())

    cycles: set[tuple[str, ...]] = set()

    def visit(node: str, path: tuple[str, ...]) -> None:
        if node in path:
            start = path.index(node)
            cycle = path[start:] + (node,)
            core = cycle[:-1]
            if core:
                rotations = [core[index:] + core[:index] for index in range(len(core))]
                canonical = min(rotations)
                cycles.add(canonical + (canonical[0],))
            return
        if len(path) > len(adjacency):
            return
        for nxt in sorted(adjacency.get(node, ())):
            visit(nxt, path + (node,))

    for node in sorted(adjacency):
        visit(node, ())
    return tuple(sorted(cycles))


def _duplicate_intelligence(nodes: tuple[CapabilityNode, ...]) -> tuple[tuple[str, ...], ...]:
    groups: dict[str, list[str]] = {}
    for node in nodes:
        if node.intelligence_fingerprint:
            groups.setdefault(node.intelligence_fingerprint, []).append(node.capability_id)
    return tuple(
        sorted(
            tuple(sorted(ids))
            for ids in groups.values()
            if len(ids) > 1
        )
    )


def assess_influence_graph(
    nodes: tuple[CapabilityNode, ...],
    edges: tuple[InfluenceEdge, ...],
) -> InfluenceGraphAssessment:
    node_ids = tuple(node.capability_id for node in nodes)
    if len(node_ids) != len(set(node_ids)):
        raise ValueError("capability graph node identities must be unique")
    known = set(node_ids)
    for edge in edges:
        if edge.producer not in known or edge.consumer not in known:
            raise ValueError("influence edge references unknown capability node")

    dead_nodes = tuple(sorted(node.capability_id for node in nodes if node.dead_node))
    decorative = tuple(sorted(node.capability_id for node in nodes if node.decorative))
    duplicates = _duplicate_intelligence(nodes)
    dead_edges = tuple(
        sorted((edge.producer, edge.consumer) for edge in edges if edge.dead)
    )
    cycles = _find_cycles(edges)
    proven = (
        bool(nodes)
        and not dead_nodes
        and not decorative
        and not duplicates
        and not dead_edges
        and not cycles
    )
    return InfluenceGraphAssessment(
        dead_nodes=dead_nodes,
        decorative_nodes=decorative,
        duplicate_intelligence_groups=duplicates,
        dead_edges=dead_edges,
        cycle_paths=cycles,
        graph_proven=proven,
    )
