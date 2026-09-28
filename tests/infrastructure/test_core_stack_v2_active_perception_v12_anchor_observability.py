from datetime import UTC, datetime, timedelta

from qore.infrastructure.core_stack_v2 import (
    active_perception_v12_anchor_observability as observability,
)


_BASE = datetime(2017, 1, 1, 14, 0, tzinfo=UTC)


def _state(index: int, *, age_ms: int, crossed: bool = False) -> observability.V12AnchorQuoteState:
    bid = 2_000_000_000 + index
    ask = bid - 1 if crossed else bid + 10_000
    return observability.V12AnchorQuoteState(
        evaluation_at=_BASE + timedelta(minutes=index),
        bid_age_ms=age_ms,
        ask_age_ms=age_ms,
        bid_relative_price=bid,
        ask_relative_price=ask,
    )


def test_staleness_freeze_selects_smallest_threshold_with_95pct_usable() -> None:
    states = tuple(
        _state(index, age_ms=900 if index < 95 else 1_500)
        for index in range(100)
    )

    report = observability.summarize_v12_anchor_observability(states)

    assert report["status"] == "frozen"
    assert report["selected_staleness_limit_ms"] == 1_000
    thresholds = {
        item["threshold_ms"]: item
        for item in report["threshold_reports"]
    }
    assert thresholds[500]["usable_coverage_bps"] == 0
    assert thresholds[1_000]["usable_coverage_bps"] == 9_500
    assert tuple(thresholds) == observability.STALENESS_CANDIDATES_MS
    assert len(observability.v12_anchor_observability_digest(report)) == 64


def test_crossed_quote_is_not_counted_as_usable() -> None:
    states = tuple(
        _state(index, age_ms=100, crossed=index < 6)
        for index in range(100)
    )

    report = observability.summarize_v12_anchor_observability(states)

    assert report["crossed_causal_quote_count"] == 6
    assert report["status"] == "rejected"
    assert report["selected_staleness_limit_ms"] is None


def test_missing_side_is_explicit_and_never_imputed() -> None:
    states = (
        observability.V12AnchorQuoteState(
            evaluation_at=_BASE,
            bid_age_ms=100,
            ask_age_ms=None,
            bid_relative_price=2_000_000_000,
            ask_relative_price=None,
        ),
        observability.V12AnchorQuoteState(
            evaluation_at=_BASE + timedelta(minutes=1),
            bid_age_ms=100,
            ask_age_ms=100,
            bid_relative_price=2_000_000_000,
            ask_relative_price=2_000_010_000,
        ),
    )

    report = observability.summarize_v12_anchor_observability(states)

    assert report["no_prior_bid_count"] == 0
    assert report["no_prior_ask_count"] == 1
    assert report["threshold_reports"][-1]["usable_count"] == 1
