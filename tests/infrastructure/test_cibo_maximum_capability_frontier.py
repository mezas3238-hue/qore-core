from datetime import UTC, datetime, timedelta
from decimal import Decimal

from qore.infrastructure.cibo_maximum_capability_frontier import (
    FULL_LIFECYCLE_FEATURES,
    CausalFrontierOpportunity,
    EpochOption,
    LifecycleFeature,
    cognitive_multiplier_cap,
    optimize_epoch_multipliers,
    simulate_position_lifecycle,
)
from qore.infrastructure.trader_lab.ict_turtle_soup_r4_source_exact import Bar


def _cognitive() -> dict[str, object]:
    receipts = []
    utilization = {
        "risk_utilization": "0.10",
        "margin_utilization": "0.10",
        "drawdown_utilization": "0.05",
    }
    for index in range(1, 20):
        code = f"CF{index:02d}"
        input_payload: dict[str, object] = {"surface": code}
        if code == "CF02":
            input_payload = {
                "symbols": ["EURUSD"],
                "regime": {
                    "liquidity": "NORMAL",
                    "volatility": "NORMAL",
                    "correlation": "NORMAL",
                    "provider_condition": "HEALTHY",
                },
            }
        elif code == "CF06":
            input_payload = {
                "opportunity_count": 1,
                "utilization": utilization,
                "correlation": "NORMAL",
            }
        elif code == "CF07":
            input_payload = {
                "provider_symbols": ["EURUSD"],
                "provider_condition": "HEALTHY",
                "opportunity_geometry": [],
            }
        elif code == "CF10":
            input_payload = {
                "opportunity_count": 1,
                "utilization": utilization,
            }
        elif code == "CF12":
            input_payload = {
                "risk_authority": "external-qore-risk",
                "utilization": utilization,
            }
        receipts.append(
            {
                "function_code": code,
                "input_payload": input_payload,
                "output_payload": {
                    "native_engine_status": "SUCCESS",
                },
            }
        )
    return {"faculty_receipts": receipts}


def _opportunity() -> CausalFrontierOpportunity:
    start = datetime(2020, 1, 1, 10, tzinfo=UTC)
    return CausalFrontierOpportunity(
        signal_fingerprint="signal-1",
        trader_id="R38_EURUSD",
        qore_symbol="EURUSD",
        decision_at=start,
        entry_at=start + timedelta(minutes=5),
        horizon_at=start + timedelta(minutes=30),
        side="long",
        entry_price=Decimal("100"),
        structural_stop=Decimal("99"),
        technical_target=Decimal("102"),
        base_volume=Decimal("1"),
        volume_step=Decimal("1"),
        maximum_volume=Decimal("4"),
        stop_risk_per_volume_usd=Decimal("1"),
        margin_per_volume_usd=Decimal("2"),
        provider_cost_per_volume_usd=Decimal("0.05"),
        expected_net_value_usd=Decimal("0.20"),
        expected_capital_minutes=Decimal("20"),
        context_allowed=True,
        cognitive_multiplier_cap=4,
        fallback_gross_r=Decimal("-1"),
    )


def test_cognitive_cap_consumes_real_cf_inputs_without_outcomes() -> None:
    cap, codes, reason = cognitive_multiplier_cap(_cognitive())

    assert cap == 4
    assert codes == ("CF02", "CF06", "CF07", "CF10", "CF12")
    assert "cognitive cap=4" in reason


def test_optimizer_prefers_higher_causal_expected_value_within_capacity() -> None:
    options = (
        EpochOption(
            signal_fingerprint="a",
            multiplier_cap=4,
            expected_net_value_usd=Decimal("0.20"),
            expected_capital_minutes=Decimal("10"),
            risk_per_multiplier_usd=Decimal("1"),
            margin_per_multiplier_usd=Decimal("1"),
        ),
        EpochOption(
            signal_fingerprint="b",
            multiplier_cap=4,
            expected_net_value_usd=Decimal("0.05"),
            expected_capital_minutes=Decimal("30"),
            risk_per_multiplier_usd=Decimal("1"),
            margin_per_multiplier_usd=Decimal("1"),
        ),
    )

    result = optimize_epoch_multipliers(
        options,
        risk_headroom_usd=Decimal("4"),
        margin_headroom_usd=Decimal("4"),
    )

    assert result == (4, 0)


def test_optimizer_never_allocates_nonpositive_expectancy() -> None:
    option = EpochOption(
        signal_fingerprint="a",
        multiplier_cap=4,
        expected_net_value_usd=Decimal("-0.01"),
        expected_capital_minutes=Decimal("10"),
        risk_per_multiplier_usd=Decimal("1"),
        margin_per_multiplier_usd=Decimal("1"),
    )

    assert optimize_epoch_multipliers(
        (option,),
        risk_headroom_usd=Decimal("100"),
        margin_headroom_usd=Decimal("100"),
    ) == (0,)


def test_position_lifecycle_uses_closed_post_entry_bars_and_releases_risk() -> None:
    opportunity = _opportunity()
    bars = (
        Bar(
            opened_at=opportunity.entry_at,
            closed_at=opportunity.entry_at + timedelta(minutes=5),
            open=Decimal("100"),
            high=Decimal("101.2"),
            low=Decimal("99.8"),
            close=Decimal("101"),
        ),
        Bar(
            opened_at=opportunity.entry_at + timedelta(minutes=5),
            closed_at=opportunity.entry_at + timedelta(minutes=10),
            open=Decimal("101"),
            high=Decimal("101.6"),
            low=Decimal("100.4"),
            close=Decimal("101.4"),
        ),
    )

    result = simulate_position_lifecycle(
        opportunity,
        bars,
        features=frozenset(
            {
                LifecycleFeature.BREAKEVEN,
                LifecycleFeature.PARTIAL_REALIZATION,
                LifecycleFeature.PROFIT_LOCK,
            }
        ),
    )

    assert result.data_available is True
    assert "PARTIAL_REALIZATION_1R" in result.actions
    assert "MOVE_TO_BREAKEVEN" in result.actions
    assert result.risk_released_before_exit_fraction > 0


def test_same_bar_stop_is_conservative_before_favorable_trigger() -> None:
    opportunity = _opportunity()
    bar = Bar(
        opened_at=opportunity.entry_at,
        closed_at=opportunity.entry_at + timedelta(minutes=5),
        open=Decimal("100"),
        high=Decimal("102.5"),
        low=Decimal("98.8"),
        close=Decimal("102"),
    )

    result = simulate_position_lifecycle(
        opportunity,
        (bar,),
        features=FULL_LIFECYCLE_FEATURES,
    )

    assert result.actions[0] == "STOP_OR_PROTECTED_STOP"
    assert result.gross_r == Decimal("-1")
