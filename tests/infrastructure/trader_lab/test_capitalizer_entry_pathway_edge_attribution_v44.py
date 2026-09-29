from __future__ import annotations

from qore.infrastructure.trader_lab import (
    capitalizer_entry_pathway_edge_attribution_v44 as v44,
)


def _row(
    provenance: str,
    *,
    trades: int = 40,
    wins: int = 20,
    losses: int = 20,
    pf: str = "1.2",
    expectancy: str = "0.1",
) -> v44.PathwayMetrics:
    return v44.PathwayMetrics(
        period="P",
        window_start="2020-01-01",
        window_end_exclusive="2022-01-01",
        provenance=provenance,
        trades=trades,
        wins=wins,
        losses=losses,
        flats=trades - wins - losses,
        gross_positive_r="20",
        gross_negative_r_abs="10",
        total_r="10",
        expectancy_r_per_trade=expectancy,
        profit_factor=pf,
        average_winner_r="1",
        average_loser_r_abs="0.5",
        payoff_ratio="2",
        stops=losses,
        stop_rate="0.5",
        targets=wins,
        target_rate="0.5",
        other_exits=0,
        entrant_share="0.3",
        portfolio_gross_positive_share="0.3",
        portfolio_gross_negative_share="0.3",
        portfolio_total_r_share="0.3",
        diagnostic_sample_sufficient=(
            trades >= v44.MIN_TRADES
            and wins >= v44.MIN_WINS
            and losses >= v44.MIN_LOSSES
        ),
    )


def test_classification_positive_requires_all_three_eras() -> None:
    rows = tuple(_row("A") for _ in range(3))
    result = v44._classify("A", rows)
    assert result.classification == "CONSISTENT_EDGE_POSITIVE"


def test_classification_negative_requires_all_three_eras() -> None:
    rows = tuple(
        _row("A", pf="0.8", expectancy="-0.1")
        for _ in range(3)
    )
    result = v44._classify("A", rows)
    assert result.classification == "CONSISTENT_EDGE_NEGATIVE"


def test_mixed_pathway_is_not_auto_filtered() -> None:
    rows = (
        _row("A", pf="1.2", expectancy="0.1"),
        _row("A", pf="0.8", expectancy="-0.1"),
        _row("A", pf="1.1", expectancy="0.05"),
    )
    result = v44._classify("A", rows)
    assert result.classification == "MIXED_OR_NONSTATIONARY"


def test_insufficient_sample_fails_closed() -> None:
    rows = (
        _row("A"),
        _row("A", trades=20, wins=10, losses=10),
        _row("A"),
    )
    result = v44._classify("A", rows)
    assert result.classification == "INSUFFICIENT_STRUCTURAL_SAMPLE"


def test_next_phase_redesigns_single_negative_only_with_positive_control() -> None:
    negative = v44._classify(
        "NEG",
        tuple(_row("NEG", pf="0.8", expectancy="-0.1") for _ in range(3)),
    )
    positive = v44._classify(
        "POS",
        tuple(_row("POS", pf="1.2", expectancy="0.1") for _ in range(3)),
    )
    assert v44._next_phase((negative, positive)) == (
        "REDESIGN_NEGATIVE_ENTRY_PATHWAY_WITH_COMMON_GRAMMAR_CONTROL"
    )


def test_next_phase_inconclusive_when_any_pathway_lacks_structural_sample() -> None:
    insufficient = v44._classify(
        "SMALL",
        (
            _row("SMALL"),
            _row("SMALL", trades=20, wins=10, losses=10),
            _row("SMALL"),
        ),
    )
    positive = v44._classify(
        "POS",
        tuple(_row("POS") for _ in range(3)),
    )
    assert v44._next_phase((insufficient, positive)) == (
        "PATHWAY_ATTRIBUTION_INCONCLUSIVE"
    )


def test_anniversary_windows_are_exact_two_years() -> None:
    from datetime import date

    assert v44._anniversary_windows(
        date(2022, 9, 17),
        date(2024, 9, 17),
    ) == (
        (date(2022, 9, 17), date(2023, 9, 17)),
        (date(2023, 9, 17), date(2024, 9, 17)),
    )
