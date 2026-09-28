from __future__ import annotations

import pytest

from qore.infrastructure.core_stack_v2.active_perception_post_v13_sensor_availability import (
    CrossMarketPeerFamily,
    HistoricalPeerCoverageStatus,
    HistoricalWindowCoverage,
    PostV13SensorAvailabilityError,
    classify_historical_peer_coverage,
    discover_cross_market_microstructure_candidates,
    normalize_provider_symbol,
)


def test_normalize_provider_symbol_preserves_only_provider_alphanumerics() -> None:
    assert normalize_provider_symbol("US500.cash") == "US500CASH"
    assert normalize_provider_symbol("US 30") == "US30"


def test_candidate_discovery_is_frozen_to_sp500_and_us30_peer_names() -> None:
    candidates = discover_cross_market_microstructure_candidates(
        ("USTEC", "US500.cash", "SPX500", "US30", "EURUSD")
    )
    assert [(item.family, item.provider_symbol) for item in candidates] == [
        (CrossMarketPeerFamily.SP500, "SPX500"),
        (CrossMarketPeerFamily.SP500, "US500.cash"),
        (CrossMarketPeerFamily.US30, "US30"),
    ]


def test_candidate_discovery_keeps_ambiguity_explicit() -> None:
    candidates = discover_cross_market_microstructure_candidates(
        ("US30", "US30.cash")
    )
    assert [item.provider_symbol for item in candidates] == ["US30", "US30.cash"]


@pytest.mark.parametrize(
    ("samples", "expected"),
    [
        (
            (
                HistoricalWindowCoverage(0, 10, 11),
                HistoricalWindowCoverage(1, 2, 3),
            ),
            HistoricalPeerCoverageStatus.FULL_BID_ASK_HISTORY,
        ),
        (
            (
                HistoricalWindowCoverage(0, 10, 0),
                HistoricalWindowCoverage(1, 0, 3),
            ),
            HistoricalPeerCoverageStatus.PARTIAL_BID_ASK_HISTORY,
        ),
        (
            (
                HistoricalWindowCoverage(0, 0, 0),
                HistoricalWindowCoverage(1, 0, 0),
            ),
            HistoricalPeerCoverageStatus.NO_HISTORY,
        ),
    ],
)
def test_coverage_classification_is_source_only_and_deterministic(
    samples: tuple[HistoricalWindowCoverage, ...],
    expected: HistoricalPeerCoverageStatus,
) -> None:
    assert classify_historical_peer_coverage(samples) is expected


def test_invalid_provider_symbol_fails_closed() -> None:
    with pytest.raises(PostV13SensorAvailabilityError):
        normalize_provider_symbol(" US500")
