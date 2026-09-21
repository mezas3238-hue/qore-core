from decimal import Decimal

from qore.infrastructure.trader_lab.capitalizer_market_breathing_envelope_v1 import (
    NEGATIVE_PATH,
    POSITIVE_PATH,
    _envelope,
    _strict_inside,
)


def _row(
    overshoot_r: str,
    overshoot_abs: str,
    outcome: str,
) -> dict[str, object]:
    return {
        "max_ob_overshoot_r": overshoot_r,
        "max_ob_overshoot_pips": overshoot_abs,
        "max_ob_overshoot_beyond_distal_price": overshoot_abs,
        "max_ob_overshoot_provider_increments": str(
            Decimal(overshoot_abs) * Decimal("10")
        ),
        "ob_penetration_path_classification": outcome,
    }


def test_strict_inside_does_not_credit_touching_threshold() -> None:
    row = _row("0.50", "5", POSITIVE_PATH)
    assert _strict_inside(row, "max_ob_overshoot_r", Decimal("0.51")) is True
    assert _strict_inside(row, "max_ob_overshoot_r", Decimal("0.50")) is False


def test_development_envelope_reports_recovery_and_failure_survival() -> None:
    development = [
        _row("0.10", "1", POSITIVE_PATH),
        _row("0.20", "2", POSITIVE_PATH),
        _row("0.30", "3", POSITIVE_PATH),
        _row("0.40", "4", POSITIVE_PATH),
    ]
    hold_recovery = [
        _row("0.10", "1", POSITIVE_PATH),
        _row("0.35", "3.5", POSITIVE_PATH),
    ]
    hold_failure = [
        _row("0.15", "1.5", NEGATIVE_PATH),
        _row("0.80", "8", NEGATIVE_PATH),
    ]
    audit = _envelope(
        symbol="EURUSD",
        quantile_name="P75",
        fraction=Decimal("0.75"),
        development_recovered=development,
        holdout_recovered=hold_recovery,
        holdout_failed=hold_failure,
    )
    assert audit.development_threshold_r == "0.30"
    assert audit.development_threshold_absolute == "3"
    assert audit.absolute_unit == "PIPS"
    assert audit.consumed_holdout_recovery_coverage_r == "0.5"
    assert audit.consumed_holdout_failure_survival_rate_r == "0.5"
    assert audit.consumed_holdout_target_rate_inside_r_envelope == "0.5"
    assert audit.development_only_threshold is True
    assert audit.consumed_holdout_selected_threshold is False
    assert audit.executable_buffer_frozen is False


def test_non_fx_uses_price_distance_not_synthetic_pips() -> None:
    development = [
        _row("0.10", "10", POSITIVE_PATH),
        _row("0.20", "20", POSITIVE_PATH),
        _row("0.30", "30", POSITIVE_PATH),
        _row("0.40", "40", POSITIVE_PATH),
    ]
    audit = _envelope(
        symbol="NAS100",
        quantile_name="P50",
        fraction=Decimal("0.50"),
        development_recovered=development,
        holdout_recovered=[_row("0.10", "10", POSITIVE_PATH)],
        holdout_failed=[_row("0.50", "50", NEGATIVE_PATH)],
    )
    assert audit.absolute_unit == "PRICE_DISTANCE"
    assert audit.development_threshold_absolute == "20"
