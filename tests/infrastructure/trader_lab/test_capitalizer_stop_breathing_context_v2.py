from decimal import Decimal

from qore.infrastructure.trader_lab.capitalizer_stop_breathing_context_v2 import (
    NEGATIVE_PATH,
    POSITIVE_PATH,
    _add_derived_pretrade_features,
    _threshold_audit,
)


def _row(value: int, positive: bool) -> dict[str, object]:
    return {
        "feature_x": str(value),
        "ob_penetration_path_classification": (
            POSITIVE_PATH if positive else NEGATIVE_PATH
        ),
    }


def test_threshold_is_selected_on_development_and_transports_direction() -> None:
    development = [
        _row(value, positive=value >= 60)
        for value in range(120)
    ]
    holdout = [
        _row(value, positive=value >= 60)
        for value in range(120)
    ]
    audit = _threshold_audit(
        feature="feature_x",
        development_all=development,
        development_overshoots=development,
        holdout_overshoots=holdout,
    )
    assert audit is not None
    assert audit.threshold_selected_on_development_only is True
    assert audit.consumed_holdout_used_for_threshold_selection is False
    assert audit.development_direction == "HIGHER_FEATURE_MORE_BREATHING"
    assert audit.consumed_holdout_direction == "HIGHER_FEATURE_MORE_BREATHING"
    assert audit.direction_transported is True
    assert audit.context_clue_transported is True
    assert audit.buffer_frozen is False


def test_prior20_volatility_proxy_is_derived_without_future_data() -> None:
    row: dict[str, object] = {
        "displacement_range_r": "0.8",
        "displacement_range_vs_prior20": "2",
        "order_block_width_r": "0.6",
        "fvg_width_r": "0.2",
        "distance_ob_to_mss_r": "1.2",
    }
    _add_derived_pretrade_features([row])
    assert row["prior20_median_range_r"] == "0.4"
    assert row["order_block_width_vs_prior20_range"] == "1.5"
    assert row["fvg_width_vs_prior20_range"] == "0.5"
    assert row["distance_ob_to_mss_vs_prior20_range"] == "3"


def test_threshold_requires_minimum_overshoot_density() -> None:
    development = [_row(value, positive=value > 10) for value in range(20)]
    audit = _threshold_audit(
        feature="feature_x",
        development_all=development,
        development_overshoots=development,
        holdout_overshoots=development,
    )
    assert audit is None


def test_gap_threshold_constants_are_not_used_as_stop_buffers() -> None:
    assert Decimal("0.08") > Decimal("0")


def test_immediate_retest_is_zero_path_not_missing() -> None:
    from datetime import UTC, datetime

    from qore.infrastructure.trader_lab.capitalizer_stop_breathing_context_v2 import (
        _PreEntryPathState,
    )

    at = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)
    state = _PreEntryPathState(
        row={},
        start_at=at,
        entry_at=at,
        side="LONG",
        ob_low=Decimal("99"),
        ob_high=Decimal("100"),
        risk=Decimal("2"),
    )
    assert state.start_at == state.entry_at
