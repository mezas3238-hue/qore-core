from decimal import Decimal

from qore.infrastructure.trader_lab import turtle_soup_xauusd_r3_causal_regime_forensics as f


def test_identity_and_governance_constants() -> None:
    assert f.IDENTITY == "TURTLE_SOUP_XAUUSD_R3_CAUSAL_REGIME_FORENSICS_V1"
    assert f.BASELINE_YEARS == frozenset({2016, 2017, 2018, 2019})
    assert f.RECENT_YEARS == frozenset({2024, 2025, 2026})


def test_trend_sign_and_alignment_are_causal_direction_labels() -> None:
    assert f._trend_sign(Decimal("0.01")) == "bull"
    assert f._trend_sign(Decimal("-0.01")) == "bear"
    assert f._trend_sign(Decimal("0")) == "flat"
    assert f._aligned_trend("long", Decimal("0.01")) == "with_trade"
    assert f._aligned_trend("short", Decimal("0.01")) == "against_trade"
    assert f._aligned_trend("short", Decimal("-0.01")) == "with_trade"


def test_stat_reports_target_and_stop_rates_without_rule_promotion() -> None:
    rows = [
        {"primary_net_r": "1.95", "exit_reason": "TARGET"},
        {"primary_net_r": "-1.05", "exit_reason": "STOP"},
        {"primary_net_r": "-0.05", "exit_reason": "TIME_24H"},
    ]
    result = f._stat(rows)
    assert result["trades"] == 3
    assert result["total_primary_r"] == "0.85"
    assert result["target_rate"] == str(Decimal(1) / Decimal(3))
    assert result["stop_rate"] == str(Decimal(1) / Decimal(3))
