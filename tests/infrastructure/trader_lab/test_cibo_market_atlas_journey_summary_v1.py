from qore.infrastructure.trader_lab.cibo_market_atlas_journey_summary_v1 import (
    _latency_summary,
    _quantile,
    _rate,
)


def test_quantile_interpolates_deterministically() -> None:
    assert _quantile([0.0, 10.0], 0.25) == 2.5
    assert _quantile([5.0], 0.90) == 5.0
    assert _quantile([], 0.50) is None


def test_latency_summary_retains_distribution_shape() -> None:
    summary = _latency_summary([0, 5, 10, 15, 20])
    assert summary["n"] == 5
    assert summary["p25"] == 5.0
    assert summary["median"] == 10.0
    assert summary["p75"] == 15.0
    assert summary["p90"] == 18.0


def test_rate_fails_closed_on_empty_sample() -> None:
    assert _rate([]) is None
    assert _rate([True, False, True, True]) == 0.75
