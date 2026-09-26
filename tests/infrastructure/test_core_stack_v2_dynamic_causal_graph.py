# ruff: noqa: I001
from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from qore.infrastructure.core_stack_v2.dynamic_causal_graph import (
    CausalConcept,
    CausalEdgeEvidence,
    update_causal_graph,
)


NOW = datetime(2026, 9, 26, 3, 0, tzinfo=UTC)


def _edge(
    source: CausalConcept,
    target: CausalConcept,
    *,
    support: int,
    contradiction: int,
    group: str,
    seconds_ago: int = 0,
) -> CausalEdgeEvidence:
    return CausalEdgeEvidence(
        source=source,
        target=target,
        as_of=NOW - timedelta(seconds=seconds_ago),
        support_bps=support,
        contradiction_bps=contradiction,
        integrity_bps=10_000,
        independence_group=group,
    )


def test_independent_evidence_strengthens_causal_edge() -> None:
    graph = update_causal_graph(
        as_of=NOW,
        evidence=(
            _edge(
                CausalConcept.COMPRESSION,
                CausalConcept.LIQUIDITY_ACCUMULATION,
                support=8_000,
                contradiction=2_000,
                group="volatility",
            ),
            _edge(
                CausalConcept.COMPRESSION,
                CausalConcept.LIQUIDITY_ACCUMULATION,
                support=7_500,
                contradiction=2_500,
                group="liquidity",
            ),
        ),
    )

    assert graph.edge_probability_bps(
        CausalConcept.COMPRESSION,
        CausalConcept.LIQUIDITY_ACCUMULATION,
    ) > 5_000
    assert graph.execution_authority is False
    assert graph.future_market_used is False


def test_contradictory_evidence_can_falsify_edge() -> None:
    graph = update_causal_graph(
        as_of=NOW,
        evidence=tuple(
            _edge(
                CausalConcept.DISPLACEMENT,
                CausalConcept.CONTINUATION,
                support=1_000,
                contradiction=9_000,
                group=f"group-{index}",
            )
            for index in range(4)
        ),
    )

    assert (
        CausalConcept.DISPLACEMENT,
        CausalConcept.CONTINUATION,
    ) in graph.falsified_edges


def test_correlated_repetition_is_discounted() -> None:
    independent = update_causal_graph(
        as_of=NOW,
        evidence=(
            _edge(
                CausalConcept.ACCEPTANCE,
                CausalConcept.CONTINUATION,
                support=8_000,
                contradiction=2_000,
                group="structure",
            ),
            _edge(
                CausalConcept.ACCEPTANCE,
                CausalConcept.CONTINUATION,
                support=8_000,
                contradiction=2_000,
                group="cross_market",
            ),
        ),
    )
    correlated = update_causal_graph(
        as_of=NOW,
        evidence=(
            _edge(
                CausalConcept.ACCEPTANCE,
                CausalConcept.CONTINUATION,
                support=8_000,
                contradiction=2_000,
                group="structure",
            ),
            _edge(
                CausalConcept.ACCEPTANCE,
                CausalConcept.CONTINUATION,
                support=8_000,
                contradiction=2_000,
                group="structure",
            ),
        ),
    )

    assert independent.edge_probability_bps(
        CausalConcept.ACCEPTANCE,
        CausalConcept.CONTINUATION,
    ) > correlated.edge_probability_bps(
        CausalConcept.ACCEPTANCE,
        CausalConcept.CONTINUATION,
    )


def test_future_causal_evidence_fails_closed() -> None:
    with pytest.raises(ValueError):
        update_causal_graph(
            as_of=NOW,
            evidence=(
                CausalEdgeEvidence(
                    source=CausalConcept.ABSORPTION,
                    target=CausalConcept.REVERSAL,
                    as_of=NOW + timedelta(seconds=1),
                    support_bps=7_000,
                    contradiction_bps=3_000,
                    integrity_bps=10_000,
                    independence_group="future",
                ),
            ),
        )
