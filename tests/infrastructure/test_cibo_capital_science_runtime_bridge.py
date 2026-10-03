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
        is runtime.CapitalScienceDisposition.APPLIED
    )
    assert by_code["GEN-C7"].output_payload["engine_output"]["engine"] == (
        "evaluate_genc7_profit_preservation_shadow"
    )
    assert by_code["GEN-C8"].output_payload["engine_output"]["engine"] == (
        "evaluate_genc8_adaptive_compound_speed"
    )
    assert by_code["GEN-C11"].output_payload["engine_output"]["engine"] == (
        "plan_genc11_multi_period_capital"
    )
    assert by_code["GEN-C12"].output_payload["engine_output"]["engine"] == (
        "plan_genc12_crisis_capital"
    )
    assert all(item.outcome_used_for_same_decision is False for item in directive.receipts)
    assert all(item.qore_risk_bypassed is False for item in directive.receipts)
    assert all(item.productive_authority is False for item in directive.receipts)
    assert all(item.input_payload for item in directive.receipts)
    assert all(item.output_payload for item in directive.receipts)
    assert all(
        item.output_payload["consumer_action"] == item.consumer_action
        for item in directive.receipts
    )


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
    assert all(row["input_output_trace_count"] == row["invoked_count"] for row in aggregate)
    assert all(row["unique_input_count"] > 0 for row in aggregate)
    assert all(row["unique_output_count"] > 0 for row in aggregate)
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


def test_c11_runs_on_current_known_option_even_without_peer_competition() -> None:
    directive = runtime.evaluate_capital_science_predecision(
        _state(competing_candidates=1)
    )
    c11 = next(
        item for item in directive.receipts if item.function_code == "GEN-C11"
    )
    assert c11.disposition is runtime.CapitalScienceDisposition.APPLIED
    assert c11.consumer_action == "PUBLISH_ROBUST_CAPACITY_ENVELOPE"
    details = c11.output_payload["engine_output"]
    assert details["engine"] == "plan_genc11_multi_period_capital"
    assert details["known_option_ids"] == ["signal-1"]


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


def test_c7_c8_c11_c12_research_diagnostics_are_observable_per_call() -> None:
    normal = runtime.evaluate_capital_science_predecision(_state())
    normal_by = {item.function_code: item for item in normal.receipts}

    assert normal_by["GEN-C7"].consumer_action == "COMPOUND"
    assert normal_by["GEN-C7"].decision_changed is True
    assert normal_by["GEN-C7"].input_payload["realized_profit_pool_usd"] == "12"
    assert normal_by["GEN-C8"].consumer_action == "ACCELERATED"
    assert normal_by["GEN-C8"].decision_changed is True
    assert normal_by["GEN-C11"].consumer_action == "PUBLISH_ROBUST_CAPACITY_ENVELOPE"
    assert normal_by["GEN-C11"].decision_changed is True
    assert normal_by["GEN-C12"].consumer_action == "CRISIS_ENVELOPE_ALLOWS_CAPITAL"
    assert normal_by["GEN-C12"].output_payload["engine_output"]["posture"] in {
        "STABLE",
        "WATCH",
        "DEFENSIVE",
    }

    stressed = runtime.evaluate_capital_science_predecision(
        _state(
            hard_risk_headroom_usd=Decimal("0"),
            margin_headroom_usd=Decimal("0"),
        )
    )
    stressed_by = {item.function_code: item for item in stressed.receipts}
    assert stressed_by["GEN-C8"].consumer_action == "PAUSE_INCREMENTAL_COMPOUND"
    assert stressed_by["GEN-C8"].decision_changed is True
    assert stressed_by["GEN-C12"].consumer_action == "PAUSE_NEW_CAPITAL"
    assert stressed_by["GEN-C12"].decision_changed is True

    single = runtime.evaluate_capital_science_predecision(
        _state(competing_candidates=1)
    )
    single_c11 = next(
        item for item in single.receipts if item.function_code == "GEN-C11"
    )
    assert single_c11.consumer_action == "PUBLISH_ROBUST_CAPACITY_ENVELOPE"
    assert single_c11.output_payload["disposition"] == "APPLIED"
