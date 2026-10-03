from datetime import UTC, datetime
from decimal import Decimal

from qore.infrastructure import cibo_capital_science_runtime_bridge as runtime


NOW = datetime(2026, 10, 3, 12, 0, tzinfo=UTC)


def _state(**overrides: object) -> runtime.CapitalSciencePredecisionInput:
    values: dict[str, object] = {
        "decision_epoch_id": "epoch-1",
        "signal_fingerprint": "signal-1",
        "trader_id": "VT31_NAS100",
        "decision_at": NOW,
        "realized_capital_usd": Decimal("72"),
        "peak_realized_capital_usd": Decimal("75"),
        "realized_profit_pool_usd": Decimal("12"),
        "protected_capacity_usd": Decimal("2"),
        "open_stop_risk_usd": Decimal("4"),
        "open_margin_usd": Decimal("5"),
        "requested_stop_risk_usd": Decimal("1.50"),
        "requested_margin_usd": Decimal("1.00"),
        "provider_cost_usd": Decimal("0.10"),
        "expected_net_value_usd": Decimal("0.80"),
        "expected_capital_minutes": Decimal("45"),
        "hard_risk_headroom_usd": Decimal("68"),
        "margin_headroom_usd": Decimal("67"),
        "competing_candidates": 2,
    }
    values.update(overrides)
    return runtime.CapitalSciencePredecisionInput(**values)  # type: ignore[arg-type]


def test_predecision_bridge_invokes_exact_mandatory_causal_surface() -> None:
    directive = runtime.evaluate_capital_science_predecision(_state())

    assert directive.allow_incremental_compound is True
    assert directive.deployable_profit_usd == Decimal("10")
    assert {item.function_code for item in directive.receipts} == {
        "GEN-C2",
        "GEN-C4",
        "GEN-C7",
        "GEN-C8",
        "GEN-C10",
        "GEN-C11",
        "GEN-C12",
    }

    by_code = {item.function_code: item for item in directive.receipts}
    assert by_code["GEN-C2"].disposition is runtime.CapitalScienceDisposition.APPLIED
    assert (
        by_code["GEN-C10"].disposition
        is runtime.CapitalScienceDisposition.APPLIED
    )
    assert (
        by_code["GEN-C11"].disposition
        is runtime.CapitalScienceDisposition.ELIGIBLE_NO_CHANGE
    )
    assert all(item.outcome_used_for_same_decision is False for item in directive.receipts)
    assert all(item.qore_risk_bypassed is False for item in directive.receipts)
    assert all(item.productive_authority is False for item in directive.receipts)


def test_nonpositive_marginal_value_abstains_before_cma_and_risk() -> None:
    directive = runtime.evaluate_capital_science_predecision(
        _state(
            expected_net_value_usd=Decimal("0.05"),
            provider_cost_usd=Decimal("0.10"),
        )
    )

    c4 = next(
        item for item in directive.receipts if item.function_code == "GEN-C4"
    )
    assert directive.allow_incremental_compound is False
    assert c4.disposition is runtime.CapitalScienceDisposition.APPLIED
    assert c4.decision_changed is True
    assert c4.consumer_action == "ABSTAIN_FROM_INCREMENTAL_COMPOUND"
    assert c4.qore_risk_bypassed is False


def test_postrun_receipts_complete_c9_c13_c14_without_same_trade_mutation() -> None:
    pre = runtime.evaluate_capital_science_predecision(_state()).receipts
    post = runtime.build_capital_science_postrun_receipts(
        observed_at=NOW,
        ending_capital_usd=Decimal("66"),
        net_realized_pnl_usd=Decimal("6"),
        settlement_rows=(
            ("signal-1", "VT31_NAS100", Decimal("1.25")),
        ),
    )
    aggregate = runtime.aggregate_capital_science_receipts(pre + post)

    assert {row["function_code"].split("_", 1)[0] for row in aggregate} == set(
        runtime.MANDATORY_RUNTIME_GENC
    )
    assert all(row["status"] != "NOT_INTEGRATED" for row in aggregate)
    assert all(row["invoked_count"] > 0 for row in aggregate)
    assert all(row["causal_trace_count"] > 0 for row in aggregate)
    assert all(row["research_mode"] == runtime.RESEARCH_MODE for row in aggregate)

    by_code = {
        item.function_code: item
        for item in post
    }
    assert by_code["GEN-C9"].stage == "POST_SEGMENT"
    assert by_code["GEN-C13"].stage == "POST_OUTCOME"
    assert by_code["GEN-C14"].stage == "RESEARCH_GOVERNANCE"
    assert all(item.outcome_used_for_same_decision is False for item in post)
    assert all(item.qore_risk_bypassed is False for item in post)


def test_c11_is_explicitly_not_applicable_without_competing_known_options() -> None:
    directive = runtime.evaluate_capital_science_predecision(
        _state(competing_candidates=1)
    )
    c11 = next(
        item for item in directive.receipts if item.function_code == "GEN-C11"
    )
    assert (
        c11.disposition
        is runtime.CapitalScienceDisposition.JUSTIFIED_NOT_APPLICABLE
    )
    assert c11.consumer_action == "NO_MULTI_PERIOD_REALLOCATION_REQUIRED"


def test_exhausted_headroom_fail_closes_c8_and_c12() -> None:
    directive = runtime.evaluate_capital_science_predecision(
        _state(
            hard_risk_headroom_usd=Decimal("0"),
            margin_headroom_usd=Decimal("0"),
        )
    )
    by_code = {item.function_code: item for item in directive.receipts}

    assert directive.allow_incremental_compound is False
    assert by_code["GEN-C8"].disposition is runtime.CapitalScienceDisposition.FAIL_CLOSED
    assert by_code["GEN-C12"].disposition is runtime.CapitalScienceDisposition.FAIL_CLOSED
    assert by_code["GEN-C8"].decision_changed is True
    assert by_code["GEN-C12"].decision_changed is True
