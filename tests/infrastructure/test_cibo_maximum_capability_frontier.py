from datetime import UTC, datetime, timedelta
from decimal import Decimal

from qore.infrastructure.cibo_maximum_capability_frontier import (
    CEILING_DISCOVERY_CLOSURE_ELIGIBLE,
    FRONTIER_ROLE,
    CausalFrontierOpportunity,
    EpochOption,
    cognitive_multiplier_cap,
    optimize_epoch_multipliers,
)
from qore.infrastructure.cibo_position_lifecycle import (
    CiboLifecycleFeature,
    CiboPositionLifecycleInput,
    run_cibo_position_lifecycle,
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


def _lifecycle_input() -> CiboPositionLifecycleInput:
    opportunity = _opportunity()
    return CiboPositionLifecycleInput(
        signal_fingerprint=opportunity.signal_fingerprint,
        side=opportunity.side,
        entry_at=opportunity.entry_at,
        horizon_at=opportunity.horizon_at,
        entry_price=opportunity.entry_price,
        structural_stop=opportunity.structural_stop,
        technical_target=opportunity.technical_target,
        provider_cost_per_volume_usd=(
            opportunity.provider_cost_per_volume_usd
        ),
        stop_risk_per_volume_usd=(
            opportunity.stop_risk_per_volume_usd
        ),
        original_settlement_gross_r=opportunity.fallback_gross_r,
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

    result = run_cibo_position_lifecycle(
        _lifecycle_input(),
        bars,
        features=frozenset(
            {
                CiboLifecycleFeature.BREAKEVEN,
                CiboLifecycleFeature.PARTIAL_REALIZATION,
                CiboLifecycleFeature.PROFIT_LOCK,
            }
        ),
    )

    assert result.data_available is True
    assert "PARTIAL_REALIZATION_AT_CLOSE" in result.actions
    assert "MOVE_TO_BREAKEVEN" in result.actions
    assert result.risk_released_before_exit_fraction > 0


def test_same_bar_ambiguous_base_path_does_not_invent_intrabar_order() -> None:
    opportunity = _opportunity()
    bar = Bar(
        opened_at=opportunity.entry_at,
        closed_at=opportunity.entry_at + timedelta(minutes=5),
        open=Decimal("100"),
        high=Decimal("102.5"),
        low=Decimal("98.8"),
        close=Decimal("102"),
    )

    result = run_cibo_position_lifecycle(
        _lifecycle_input(),
        (bar,),
        features=frozenset(CiboLifecycleFeature),
    )

    assert result.gross_r == opportunity.fallback_gross_r
    assert "STOP_OR_PROTECTED_STOP" not in result.actions
    assert result.actions[-1] == "HORIZON_ORIGINAL_SETTLEMENT"


def test_lifecycle_off_is_exact_original_settlement_identity() -> None:
    opportunity = _opportunity()
    bar = Bar(
        opened_at=opportunity.entry_at,
        closed_at=opportunity.entry_at + timedelta(minutes=5),
        open=Decimal("100"),
        high=Decimal("103"),
        low=Decimal("98"),
        close=Decimal("102.5"),
    )

    result = run_cibo_position_lifecycle(
        _lifecycle_input(),
        (bar,),
        features=frozenset(),
    )

    assert result.gross_r == opportunity.fallback_gross_r
    assert result.exit_at == opportunity.horizon_at
    assert result.actions == (
        "LIFECYCLE_OFF_ORIGINAL_SETTLEMENT",
    )


def test_new_breakeven_protection_only_applies_from_next_bar() -> None:
    opportunity = _opportunity()
    first = Bar(
        opened_at=opportunity.entry_at,
        closed_at=opportunity.entry_at + timedelta(minutes=5),
        open=Decimal("100"),
        high=Decimal("101.2"),
        low=Decimal("99.8"),
        close=Decimal("101"),
    )
    second = Bar(
        opened_at=opportunity.entry_at + timedelta(minutes=5),
        closed_at=opportunity.entry_at + timedelta(minutes=10),
        open=Decimal("101"),
        high=Decimal("101.1"),
        low=Decimal("99.9"),
        close=Decimal("100"),
    )

    result = run_cibo_position_lifecycle(
        _lifecycle_input(),
        (first, second),
        features=frozenset(
            {CiboLifecycleFeature.BREAKEVEN}
        ),
    )

    assert result.actions[:2] == (
        "MOVE_TO_BREAKEVEN",
        "STOP_OR_PROTECTED_STOP",
    )
    assert result.gross_r == Decimal("0.05")


def test_same_bar_new_protection_is_not_retroactive() -> None:
    opportunity = _opportunity()
    bar = Bar(
        opened_at=opportunity.entry_at,
        closed_at=opportunity.entry_at + timedelta(minutes=5),
        open=Decimal("100"),
        high=Decimal("101.2"),
        low=Decimal("99.8"),
        close=Decimal("101"),
    )

    result = run_cibo_position_lifecycle(
        _lifecycle_input(),
        (bar,),
        features=frozenset(
            {CiboLifecycleFeature.BREAKEVEN}
        ),
    )

    assert "STOP_OR_PROTECTED_STOP" not in result.actions
    assert result.actions[0] == "MOVE_TO_BREAKEVEN"
    assert result.actions[-1] == "HORIZON_ORIGINAL_SETTLEMENT"


def test_partial_then_horizon_uses_original_settlement_not_last_close() -> None:
    opportunity = _opportunity()
    bar = Bar(
        opened_at=opportunity.entry_at,
        closed_at=opportunity.entry_at + timedelta(minutes=5),
        open=Decimal("100"),
        high=Decimal("101.2"),
        low=Decimal("99.8"),
        close=Decimal("101.1"),
    )

    result = run_cibo_position_lifecycle(
        _lifecycle_input(),
        (bar,),
        features=frozenset(
            {CiboLifecycleFeature.PARTIAL_REALIZATION}
        ),
    )

    assert result.actions == (
        "PARTIAL_REALIZATION_AT_CLOSE",
        "HORIZON_ORIGINAL_SETTLEMENT",
    )
    assert result.gross_r == Decimal("-0.475")



def test_partial_realization_requires_causal_close_price() -> None:
    opportunity = _opportunity()
    wick_only = Bar(
        opened_at=opportunity.entry_at,
        closed_at=opportunity.entry_at + timedelta(minutes=5),
        open=Decimal("100"),
        high=Decimal("101.4"),
        low=Decimal("99.8"),
        close=Decimal("100.6"),
    )
    close_above = Bar(
        opened_at=opportunity.entry_at + timedelta(minutes=5),
        closed_at=opportunity.entry_at + timedelta(minutes=10),
        open=Decimal("100.6"),
        high=Decimal("101.6"),
        low=Decimal("100.5"),
        close=Decimal("101.2"),
    )

    result = run_cibo_position_lifecycle(
        _lifecycle_input(),
        (wick_only, close_above),
        features=frozenset(
            {CiboLifecycleFeature.PARTIAL_REALIZATION}
        ),
    )

    assert result.actions.count("PARTIAL_REALIZATION_AT_CLOSE") == 1
    partial = next(
        item
        for item in result.events
        if item.action == "PARTIAL_REALIZATION_AT_CLOSE"
    )
    assert partial.occurred_at == close_above.closed_at
    assert partial.realized_r_delta == Decimal("0.30")


def test_wick_touch_without_close_cannot_realize_partial() -> None:
    opportunity = _opportunity()
    bar = Bar(
        opened_at=opportunity.entry_at,
        closed_at=opportunity.entry_at + timedelta(minutes=5),
        open=Decimal("100"),
        high=Decimal("101.5"),
        low=Decimal("99.8"),
        close=Decimal("100.7"),
    )

    result = run_cibo_position_lifecycle(
        _lifecycle_input(),
        (bar,),
        features=frozenset(
            {CiboLifecycleFeature.PARTIAL_REALIZATION}
        ),
    )

    assert "PARTIAL_REALIZATION_AT_CLOSE" not in result.actions


def test_frontier_is_diagnostic_and_cannot_close_ceiling_discovery() -> None:
    assert FRONTIER_ROLE == "DIAGNOSTIC_FRONTIER_ONLY"
    assert CEILING_DISCOVERY_CLOSURE_ELIGIBLE is False
