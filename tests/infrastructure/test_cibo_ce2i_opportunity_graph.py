# ruff: noqa: I001
from decimal import Decimal

import pytest

from qore.infrastructure.account_wide_risk import TraderLineage
from qore.infrastructure.cibo_capital_management_authority import (
    CapitalSource,
    CiboCapitalManagementError,
)
from qore.infrastructure.cibo_capital_source_ledger import CapitalSourceLedger
from qore.infrastructure.cibo_ce2i_opportunity_competition import (
    CapitalOpportunityCandidate,
)
from qore.infrastructure.cibo_ce2i_opportunity_graph import (
    OpportunityGraphEdgeKind,
    OpportunityInteractionEvidence,
    OpportunityGraphNodeKind,
    build_capital_opportunity_graph,
)


def _candidate(
    fingerprint: str,
    trader: TraderLineage,
    *,
    group: str,
) -> CapitalOpportunityCandidate:
    return CapitalOpportunityCandidate(
        signal_fingerprint=fingerprint,
        trader_id=trader,
        qore_symbol=fingerprint.upper(),
        provider_symbol=fingerprint.upper(),
        expected_net_value_usd=Decimal("10"),
        stop_risk_usd=Decimal("5"),
        margin_usd=Decimal("8"),
        expected_capital_minutes=Decimal("10"),
        concentration_group=group,
        concentration_risk_usd=Decimal("4"),
    )


def test_graph_contains_opportunities_sources_and_groups() -> None:
    ledger = (
        CapitalSourceLedger()
        .add_source(
            source_id="profit-1",
            source=CapitalSource.REALIZED_PROFIT,
            proven_amount_usd=Decimal("12"),
        )
        .add_source(
            source_id="margin-1",
            source=CapitalSource.RELEASED_MARGIN_CAPACITY,
            proven_amount_usd=Decimal("50"),
        )
    )
    graph = build_capital_opportunity_graph(
        candidates=(
            _candidate("eur", TraderLineage.R38_EURUSD, group="USD"),
            _candidate("nas", TraderLineage.VT31_NAS100, group="INDEX"),
        ),
        capital_sources=ledger.accounts,
    )

    kinds = tuple(item.kind for item in graph.nodes)
    assert kinds.count(OpportunityGraphNodeKind.OPPORTUNITY) == 2
    assert kinds.count(OpportunityGraphNodeKind.CAPITAL_SOURCE) == 2
    assert kinds.count(OpportunityGraphNodeKind.CONCENTRATION_GROUP) == 2


def test_only_economic_profit_capital_gets_can_fund_edges() -> None:
    ledger = (
        CapitalSourceLedger()
        .add_source(
            source_id="profit-1",
            source=CapitalSource.REALIZED_PROFIT,
            proven_amount_usd=Decimal("12"),
        )
        .add_source(
            source_id="margin-1",
            source=CapitalSource.RELEASED_MARGIN_CAPACITY,
            proven_amount_usd=Decimal("50"),
        )
    )
    graph = build_capital_opportunity_graph(
        candidates=(
            _candidate("eur", TraderLineage.R38_EURUSD, group="USD"),
        ),
        capital_sources=ledger.accounts,
    )

    funding = graph.edges_of_kind(OpportunityGraphEdgeKind.CAN_FUND)
    assert len(funding) == 1
    assert funding[0].source_node_id == "capital:profit-1"


def test_simultaneous_opportunities_have_risk_and_margin_competition_edges() -> None:
    graph = build_capital_opportunity_graph(
        candidates=(
            _candidate("a", TraderLineage.R38_EURUSD, group="USD"),
            _candidate("b", TraderLineage.R43_GBPUSD, group="USD"),
        ),
        capital_sources=(),
    )

    assert len(
        graph.edges_of_kind(OpportunityGraphEdgeKind.COMPETES_FOR_RISK)
    ) == 1
    assert len(
        graph.edges_of_kind(OpportunityGraphEdgeKind.COMPETES_FOR_MARGIN)
    ) == 1
    assert len(
        graph.edges_of_kind(OpportunityGraphEdgeKind.SHARES_CONCENTRATION)
    ) == 2



def test_graph_adds_causal_factor_correlation_provider_and_temporal_edges() -> None:
    graph = build_capital_opportunity_graph(
        candidates=(
            _candidate("a", TraderLineage.R38_EURUSD, group="USD"),
            _candidate("b", TraderLineage.R43_GBPUSD, group="USD"),
        ),
        capital_sources=(),
        interaction_evidence=(
            OpportunityInteractionEvidence(
                left_signal_fingerprint="a",
                right_signal_fingerprint="b",
                factor_overlap=Decimal("0.70"),
                observed_abs_correlation=Decimal("0.80"),
                same_provider_group=True,
                temporal_overlap=Decimal("0.50"),
                hedge_offset=Decimal("0.10"),
            ),
        ),
    )

    assert len(graph.edges_of_kind(OpportunityGraphEdgeKind.FACTOR_OVERLAP)) == 1
    assert len(
        graph.edges_of_kind(OpportunityGraphEdgeKind.CORRELATED_EXPOSURE)
    ) == 1
    assert len(
        graph.edges_of_kind(OpportunityGraphEdgeKind.PROVIDER_CONCENTRATION)
    ) == 1
    assert len(
        graph.edges_of_kind(OpportunityGraphEdgeKind.TEMPORAL_OVERLAP)
    ) == 1
    assert len(graph.edges_of_kind(OpportunityGraphEdgeKind.HEDGE_OFFSET)) == 1


def test_interaction_evidence_must_reference_current_causal_candidates() -> None:
    with pytest.raises(
        CiboCapitalManagementError,
        match="references missing candidate",
    ):
        build_capital_opportunity_graph(
            candidates=(
                _candidate("a", TraderLineage.R38_EURUSD, group="USD"),
            ),
            capital_sources=(),
            interaction_evidence=(
                OpportunityInteractionEvidence(
                    left_signal_fingerprint="a",
                    right_signal_fingerprint="missing",
                    observed_abs_correlation=Decimal("0.50"),
                ),
            ),
        )


def test_duplicate_unordered_interaction_pair_fails_closed() -> None:
    candidates = (
        _candidate("a", TraderLineage.R38_EURUSD, group="USD"),
        _candidate("b", TraderLineage.R43_GBPUSD, group="USD"),
    )
    with pytest.raises(
        CiboCapitalManagementError,
        match="duplicate interaction evidence pair",
    ):
        build_capital_opportunity_graph(
            candidates=candidates,
            capital_sources=(),
            interaction_evidence=(
                OpportunityInteractionEvidence(
                    left_signal_fingerprint="a",
                    right_signal_fingerprint="b",
                    factor_overlap=Decimal("0.20"),
                ),
                OpportunityInteractionEvidence(
                    left_signal_fingerprint="b",
                    right_signal_fingerprint="a",
                    factor_overlap=Decimal("0.30"),
                ),
            ),
        )
