from qore.infrastructure.core_stack_v2.shared_lab import InfluenceEdge
from qore.infrastructure.core_stack_v2.shared_lab_influence import (
    CapabilityNode,
    assess_influence_graph,
)


def _edge(a: str, b: str, *, live: bool = True) -> InfluenceEdge:
    return InfluenceEdge(
        producer=a,
        consumer=b,
        real=live,
        tested=live,
        observed=live,
        consumed=live,
        value_proven=live,
        fingerprint_match=live,
    )


def test_graph_detects_decorative_module():
    nodes = (
        CapabilityNode("MC09", True, True, True, False),
        CapabilityNode("MC10", True, True, True, True),
    )
    result = assess_influence_graph(nodes, (_edge("MC09", "MC10"),))
    assert result.decorative_nodes == ("MC09",)
    assert result.graph_proven is False


def test_graph_detects_dead_edge():
    nodes = (
        CapabilityNode("MC09", True, True, True, True),
        CapabilityNode("MC10", True, True, True, True),
    )
    result = assess_influence_graph(nodes, (_edge("MC09", "MC10", live=False),))
    assert result.dead_edges == (("MC09", "MC10"),)
    assert result.graph_proven is False


def test_graph_detects_cycle():
    nodes = tuple(CapabilityNode(name, True, True, True, True) for name in ("A", "B", "C"))
    result = assess_influence_graph(
        nodes,
        (_edge("A", "B"), _edge("B", "C"), _edge("C", "A")),
    )
    assert result.cycle_paths
    assert result.graph_proven is False


def test_acyclic_live_graph_passes():
    nodes = tuple(CapabilityNode(name, True, True, True, True) for name in ("A", "B", "C"))
    result = assess_influence_graph(nodes, (_edge("A", "B"), _edge("B", "C")))
    assert result.graph_proven is True
