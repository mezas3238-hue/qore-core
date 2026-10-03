from datetime import UTC, datetime
from decimal import Decimal

from qore.infrastructure import cibo_capital_science_runtime_bridge as runtime
from qore.infrastructure.cibo_profit_preservation_shadow import (
    Genc7Action,
    Genc7PreservationProposalEvidence,
    Genc7SourceBucket,
)

NOW = datetime(2026, 10, 3, 12, 0, tzinfo=UTC)


def _state(**overrides: object) -> runtime.CapitalSciencePredecisionInput:
    values: dict[str, object] = {
        "decision_epoch_id": "epoch-1",
        "signal_fingerprint": "signal-1",
        "trader_id": "VT31_NAS100",
        "qore_symbol": "NAS100",
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
        "account_identity": runtime.CiboAccountCapitalIdentity(
            provider_key="trader-lab",
            account_ref="cibo-capital-science-replay",
            environment=runtime.MarketRuntimeEnvironment.TEST,
        ),
    }
    values.update(overrides)
    if "regime_state" not in overrides:
        used_risk = values["open_stop_risk_usd"]
        risk_headroom = values["hard_risk_headroom_usd"]
        used_margin = values["open_margin_usd"]
        margin_headroom = values["margin_headroom_usd"]
        peak = values["peak_realized_capital_usd"]
        current = values["realized_capital_usd"]
        assert isinstance(used_risk, Decimal)
        assert isinstance(risk_headroom, Decimal)
        assert isinstance(used_margin, Decimal)
        assert isinstance(margin_headroom, Decimal)
        assert isinstance(peak, Decimal)
        assert isinstance(current, Decimal)
        values["regime_state"] = runtime.CiboCapitalRegimeState(
            liquidity=runtime.LiquidityState.NORMAL,
            volatility=runtime.VolatilityState.NORMAL,
            correlation=runtime.CorrelationState.NORMAL,
            provider_condition=runtime.ProviderCondition.HEALTHY,
            risk_utilization=(
                Decimal(0)
                if used_risk + risk_headroom <= 0
                else used_risk / (used_risk + risk_headroom)
            ),
            margin_utilization=(
                Decimal(0)
                if used_margin + margin_headroom <= 0
                else used_margin / (used_margin + margin_headroom)
            ),
            drawdown_utilization=(Decimal(0) if peak <= 0 else (peak - current) / peak),
            opportunity_count=max(1, int(values["competing_candidates"])),
        )
    if "genc7_proposal" not in overrides:
        account_identity = values["account_identity"]
        assert isinstance(account_identity, runtime.CiboAccountCapitalIdentity)
        values["genc7_proposal"] = Genc7PreservationProposalEvidence(
            proposal_id="proposal-1",
            decision_at=NOW,
            account_identity=account_identity,
            action=Genc7Action.COMPOUND,
            source_bucket=Genc7SourceBucket.COMPOUNDABLE_OR_RELEASED_CAPACITY,
            amount_usd=(
                values["requested_stop_risk_usd"] + values["provider_cost_usd"]
            ),
            evidence_sha256="sha256:" + "a" * 64,
            rationale_code="CAUSAL_TEST_PROPOSAL",
            evaluation_horizon_minutes=46,
            calibrated=True,
            capital_eligible=True,
        )
    return runtime.CapitalSciencePredecisionInput(**values)  # type: ignore[arg-type]


def _genc7_proposal(
    action: Genc7Action,
    *,
    calibrated: bool = True,
) -> Genc7PreservationProposalEvidence:
    source = (
        Genc7SourceBucket.REALIZED_UNPROTECTED_PROFIT
        if action in {Genc7Action.PROTECT, Genc7Action.HARVEST_TO_STRATEGIC_RESERVE}
        else Genc7SourceBucket.COMPOUNDABLE_OR_RELEASED_CAPACITY
    )
    return Genc7PreservationProposalEvidence(
        proposal_id=f"proposal-{action.value.lower()}",
        decision_at=NOW,
        account_identity=runtime.CiboAccountCapitalIdentity(
            provider_key="trader-lab",
            account_ref="cibo-capital-science-replay",
            environment=runtime.MarketRuntimeEnvironment.TEST,
        ),
        action=action,
        source_bucket=source,
        amount_usd=(Decimal("1.60") if action is Genc7Action.COMPOUND else Decimal("1")),
        evidence_sha256="sha256:" + "b" * 64,
        rationale_code="CAUSAL_BRANCH_EVIDENCE",
        evaluation_horizon_minutes=46,
        calibrated=calibrated,
        capital_eligible=True,
    )


def test_predecision_bridge_invokes_exact_mandatory_causal_surface() -> None:
    directive = runtime.evaluate_capital_science_predecision(_state())

    assert directive.allow_incremental_compound is True
    assert directive.deployable_profit_usd == Decimal("10")
    assert {item.function_code for item in directive.receipts} == {
        "GEN-C2",
        "GEN-C4",
        "GEN-C5",
        "GEN-C7",
        "GEN-C8",
        "GEN-C10",
        "GEN-C11",
        "GEN-C12",
    }

    by_code = {item.function_code: item for item in directive.receipts}
    assert by_code["GEN-C2"].disposition is runtime.CapitalScienceDisposition.APPLIED
    assert by_code["GEN-C10"].disposition is runtime.CapitalScienceDisposition.APPLIED
    assert by_code["GEN-C11"].disposition is runtime.CapitalScienceDisposition.APPLIED
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
    assert by_code["GEN-C5"].native_engine_called is True
    assert by_code["GEN-C7"].native_engine_called is True
    assert by_code["GEN-C8"].native_engine_called is True
    assert by_code["GEN-C10"].native_engine_called is True
    assert by_code["GEN-C11"].native_engine_called is True
    assert by_code["GEN-C12"].native_engine_called is True
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

    c4 = next(item for item in directive.receipts if item.function_code == "GEN-C4")
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
        settlement_rows=(("signal-1", "VT31_NAS100", Decimal("1.25")),),
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

    by_code = {item.function_code: item for item in post}
    assert by_code["GEN-C9"].stage == "POST_SEGMENT"
    assert by_code["GEN-C13"].stage == "POST_OUTCOME"
    assert by_code["GEN-C14"].stage == "RESEARCH_GOVERNANCE"
    assert all(item.outcome_used_for_same_decision is False for item in post)
    assert all(item.qore_risk_bypassed is False for item in post)


def test_c11_runs_on_current_known_option_even_without_peer_competition() -> None:
    directive = runtime.evaluate_capital_science_predecision(_state(competing_candidates=1))
    c11 = next(item for item in directive.receipts if item.function_code == "GEN-C11")
    assert c11.disposition is runtime.CapitalScienceDisposition.APPLIED
    assert c11.consumer_action == "CONSUME_ROBUST_CAPACITY_ENVELOPE"
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
    assert normal_by["GEN-C11"].consumer_action == "CONSUME_ROBUST_CAPACITY_ENVELOPE"
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
    assert stressed_by["GEN-C8"].consumer_action == "PAUSE"
    assert stressed_by["GEN-C8"].decision_changed is True
    assert stressed_by["GEN-C12"].consumer_action == "PAUSE_NEW_CAPITAL"
    assert stressed_by["GEN-C12"].decision_changed is True

    single = runtime.evaluate_capital_science_predecision(_state(competing_candidates=1))
    single_c11 = next(item for item in single.receipts if item.function_code == "GEN-C11")
    assert single_c11.consumer_action == "CONSUME_ROBUST_CAPACITY_ENVELOPE"
    assert single_c11.output_payload["disposition"] == "APPLIED"


def test_genc11_consumes_every_simultaneously_known_option() -> None:
    peer = runtime.CapitalScienceKnownOpportunity(
        option_id="peer-signal",
        trader_id="GENERIC_USDCAD_R1",
        qore_symbol="USDCAD",
        known_at=NOW,
        earliest_action_at=NOW,
        expires_at=NOW.replace(hour=13),
        requested_capital_usd=Decimal("1.10"),
        stop_risk_usd=Decimal("1.00"),
        margin_usd=Decimal("0.80"),
        evidence_sha256="sha256:" + "a" * 64,
    )
    directive = runtime.evaluate_capital_science_predecision(
        _state(
            competing_candidates=2,
            known_simultaneous_opportunities=(peer,),
        )
    )
    c10 = next(item for item in directive.receipts if item.function_code == "GEN-C10")
    c11 = next(item for item in directive.receipts if item.function_code == "GEN-C11")

    assert c10.output_payload["engine_output"]["known_option_count"] == 2
    assert set(c11.output_payload["engine_output"]["known_option_ids"]) == {
        "signal-1",
        "peer-signal",
    }
    schedules = c11.input_payload["typed_engine_input"]["option_schedules"]
    assert {item["option_id"] for item in schedules} == {
        "signal-1",
        "peer-signal",
    }


def test_unseen_trader_and_symbol_use_the_same_native_capability_path() -> None:
    identities = (
        ("SCALPER_BTCUSD_V1", "BTCUSD"),
        ("GENERIC_USDCAD_R1", "USDCAD"),
        ("PORTFOLIO.EURAUD/R2", "EURAUD"),
        ("FUTURE_SYNTHETIC_TRADER_2040", "SYNTH-2040"),
    )
    for trader_id, qore_symbol in identities:
        directive = runtime.evaluate_capital_science_predecision(
            _state(trader_id=trader_id, qore_symbol=qore_symbol)
        )
        native = {item.function_code for item in directive.receipts if item.native_engine_called}
        assert native == {"GEN-C5", "GEN-C7", "GEN-C8", "GEN-C10", "GEN-C11", "GEN-C12"}
        assert all(item.trader_id == trader_id for item in directive.receipts)
        assert all(item.qore_symbol == qore_symbol for item in directive.receipts)


def test_genc7_native_branch_diversity_is_driven_by_upstream_proposals() -> None:
    expected = (
        Genc7Action.PROTECT,
        Genc7Action.HARVEST_TO_STRATEGIC_RESERVE,
        Genc7Action.RESERVE_OPPORTUNITY_CAPACITY,
        Genc7Action.COMPOUND,
    )
    observed: list[str] = []
    for action in expected:
        directive = runtime.evaluate_capital_science_predecision(
            _state(genc7_proposal=_genc7_proposal(action))
        )
        receipt = next(item for item in directive.receipts if item.function_code == "GEN-C7")
        observed.append(receipt.consumer_action)
        assert receipt.native_engine_called is True
        assert receipt.output_payload["engine_output"]["treatment_action"] == action.value

    held = runtime.evaluate_capital_science_predecision(
        _state(genc7_proposal=_genc7_proposal(Genc7Action.PROTECT, calibrated=False))
    )
    held_receipt = next(item for item in held.receipts if item.function_code == "GEN-C7")
    assert held_receipt.consumer_action == Genc7Action.HOLD_CURRENT_CAPITAL_STATE.value
    assert tuple(observed) == tuple(action.value for action in expected)


def test_genc7_missing_proposal_fails_closed_without_false_native_receipt() -> None:
    directive = runtime.evaluate_capital_science_predecision(_state(genc7_proposal=None))
    receipt = next(item for item in directive.receipts if item.function_code == "GEN-C7")

    assert directive.allow_incremental_compound is False
    assert receipt.consumer_action == "UNAVAILABLE_MISSING_EVIDENCE"
    assert receipt.native_engine_called is False
    assert receipt.native_engine_name is None
