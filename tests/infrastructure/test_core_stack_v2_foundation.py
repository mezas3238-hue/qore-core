from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID

import pytest

from qore.governance.executive_control import ExecutiveReadScope
from qore.governance.executive_operational_read_models import (
    ExecutiveAssetClass,
    ExecutiveMarketAuthorizationState,
    ExecutiveMarketAvailability,
    ExecutiveMarketInstrument,
    ExecutiveMarketsReadModel,
    ExecutiveMarketSummary,
)
from qore.governance.executive_ports import ExecutiveEvidenceRef
from qore.governance.executive_read_models import (
    ExecutiveAttentionLevel,
    ExecutiveProjectionId,
    ExecutiveProjectionMetadata,
    ExecutiveProjectionVersion,
    ExecutiveSourceFreshness,
)
from qore.infrastructure.core_stack_v2 import (
    GLOBAL_MARKET_UNIVERSE_REQUIRED,
    AnalogQuery,
    CausalAnalogMemory,
    ClosedEpisode,
    ActualTrade,
    CoreHypothesis,
    CoreStackConfig,
    DecisionObservation,
    HypothesisStatus,
    MarketEvent,
    PortfolioIntent,
    ShadowAction,
    SharedShadowDecision,
    build_global_market_universe,
    build_snapshot,
    compatibility_manifest,
    evaluate_real_operation_falsification,
    freeze_facts,
    summarize_decision_ab,
    superintelligence_freeze_contract,
    superintelligence_freeze_fingerprint,
)
from qore.infrastructure.traders.vt31_core_stack_v2_adapter import VT31CoreAdapter

NOW = datetime(2026, 9, 23, 20, 0, 1, tzinfo=UTC)


def _event(
    event_id: str,
    *,
    sequence: int,
    seconds_ago: int,
    complete: bool = True,
    event_type: str = "STRUCTURE_CHANGE",
    timeframe_seconds: int | None = None,
    facts: dict[str, str] | None = None,
) -> MarketEvent:
    source = NOW - timedelta(seconds=seconds_ago)
    return MarketEvent(
        event_id=event_id,
        market="NAS100",
        event_type=event_type,
        source_at=source,
        observed_at=source,
        sequence=sequence,
        complete=complete,
        timeframe_seconds=timeframe_seconds,
        facts=freeze_facts(facts or {}),
    )


def _valid_events() -> tuple[MarketEvent, ...]:
    return (
        _event(
            "e1",
            sequence=1,
            seconds_ago=1,
            facts={
                "market_state": "ACTIVE",
                "session_state": "NY",
                "liquidity_state": "POST_RAID",
                "structure_state": "CONFIRMED",
                "volatility_state": "NORMAL",
            },
        ),
        _event(
            "e2",
            sequence=2,
            seconds_ago=0,
            facts={
                "expansion_state": "EXPANDING",
                "compression_state": "NOT_COMPRESSED",
                "directional_state": "REVERSAL",
                "reversal_state": "SUPPORTED",
                "continuation_state": "AMBIGUOUS",
            },
        ),
    )


def test_same_inputs_produce_same_snapshot() -> None:
    first = build_snapshot(events=_valid_events(), generated_at=NOW)
    second = build_snapshot(events=_valid_events(), generated_at=NOW)
    assert first == second
    assert first.snapshot_id == second.snapshot_id
    assert first.fingerprint() == second.fingerprint()


def test_future_timestamp_fails_closed() -> None:
    future = MarketEvent(
        event_id="future",
        market="NAS100",
        event_type="NEW_BAR",
        source_at=NOW + timedelta(seconds=1),
        observed_at=NOW + timedelta(seconds=1),
        sequence=1,
        complete=True,
        timeframe_seconds=60,
        facts=freeze_facts({"market_state": "ACTIVE"}),
    )
    snapshot = build_snapshot(events=(future,), generated_at=NOW)
    context = VT31CoreAdapter().adapt(snapshot)
    assert snapshot.perception_integrity.valid is False
    assert "FUTURE_SOURCE_TIMESTAMP" in snapshot.perception_integrity.codes
    assert context.core_context_valid is False


def test_duplicate_and_out_of_order_events_fail_closed() -> None:
    first = _event("dup", sequence=2, seconds_ago=1)
    second = _event("dup", sequence=1, seconds_ago=0)
    snapshot = build_snapshot(events=(first, second), generated_at=NOW)
    assert snapshot.perception_integrity.valid is False
    assert "DUPLICATE_EVENT_ID" in snapshot.perception_integrity.codes
    assert "OUT_OF_ORDER_EVENT" in snapshot.perception_integrity.codes


def test_missing_bar_is_detected_without_guessing_context() -> None:
    first = _event(
        "m1-1",
        sequence=1,
        seconds_ago=121,
        event_type="NEW_BAR",
        timeframe_seconds=60,
    )
    second = _event(
        "m1-2",
        sequence=2,
        seconds_ago=0,
        event_type="NEW_BAR",
        timeframe_seconds=60,
    )
    snapshot = build_snapshot(
        events=(first, second),
        generated_at=NOW,
        config=CoreStackConfig(stale_after_ms=200_000),
    )
    assert snapshot.perception_integrity.valid is False
    assert "MISSING_CANDLE:60" in snapshot.perception_integrity.codes


def test_core_and_adapter_have_no_risk_or_order_authority() -> None:
    snapshot = build_snapshot(events=_valid_events(), generated_at=NOW)
    context = VT31CoreAdapter().adapt(snapshot)
    assert snapshot.order_authority is False
    assert snapshot.risk_authority is False
    assert snapshot.strategy_mutation_authority is False
    assert context.order_authority is False
    assert context.risk_authority is False
    assert context.methodology_mutation_allowed is False


def test_vt31_adapter_contextualizes_without_strategy_rules() -> None:
    hypothesis = CoreHypothesis(
        hypothesis_id="h1",
        market="NAS100",
        thesis="current causal market hypothesis",
        status=HypothesisStatus.WAIT,
        supporting_event_ids=("e1",),
        contradictory_event_ids=(),
        confidence_bps=6_000,
        updated_at=NOW,
    )
    snapshot = build_snapshot(
        events=_valid_events(),
        generated_at=NOW,
        hypotheses=(hypothesis,),
        cross_market_facts={
            "SP500": "SAME_SIDE_OBSERVED",
            "US30": "DIVERGENT",
        },
    )
    context = VT31CoreAdapter().adapt(snapshot)
    assert context.core_context_valid is True
    assert context.active_hypothesis_ids == ("h1",)
    assert ("SP500", "SAME_SIDE_OBSERVED") in context.cross_market_facts
    assert not hasattr(context, "entry_price")
    assert not hasattr(context, "stop_price")
    assert not hasattr(context, "target_price")


def test_portfolio_model_detects_duplicate_and_factor_exposure() -> None:
    intents = (
        PortfolioIntent(
            trader_id="VT31",
            market="NAS100",
            side="LONG",
            hypothesis_id="h-vt31",
            factor_tags=("USD_RISK_ON",),
            generated_at=NOW,
        ),
        PortfolioIntent(
            trader_id="CAPITALIZER",
            market="NAS100",
            side="LONG",
            hypothesis_id="h-cap",
            factor_tags=("USD_RISK_ON",),
            generated_at=NOW,
        ),
    )
    snapshot = build_snapshot(
        events=_valid_events(),
        generated_at=NOW,
        portfolio_intents=intents,
    )
    assert snapshot.portfolio_state.duplicated_exposures == (
        "NAS100:LONG:CAPITALIZER,VT31",
    )
    assert snapshot.portfolio_state.factor_clusters == (
        "USD_RISK_ON:LONG:CAPITALIZER,VT31",
    )


def test_vt08_forex_is_explicitly_excluded() -> None:
    manifest = compatibility_manifest()
    raw_entries = manifest["entries"]
    assert isinstance(raw_entries, list)
    entries = {
        str(entry["trader_id"]): entry
        for entry in raw_entries
        if isinstance(entry, dict)
    }
    assert entries["VT08_FOREX"]["status"] == "EXCLUDED"
    assert entries["VT08_FOREX"]["integration_mode"] == "CURRENT_ARCHITECTURE_ONLY"
    governance = manifest["governance"]
    assert isinstance(governance, dict)
    assert governance["vt08_forex_excluded"] is True
    assert governance["live_deployment_authorized"] is False


def test_ab_summary_reports_decision_and_latency_deltas() -> None:
    summary = summarize_decision_ab(
        (
            DecisionObservation(
                trader_id="VT31",
                observation_id="1",
                baseline_action="WAIT",
                v2_action="WAIT",
                baseline_fingerprint="a",
                v2_fingerprint="a",
                core_context_valid=True,
                end_to_end_latency_us=100,
            ),
            DecisionObservation(
                trader_id="VT31",
                observation_id="2",
                baseline_action="EXECUTE",
                v2_action="ABSTAIN",
                baseline_fingerprint="b",
                v2_fingerprint="c",
                core_context_valid=True,
                end_to_end_latency_us=200,
            ),
        )
    )
    assert summary.observations == 2
    assert summary.decision_deltas == 1
    assert summary.abstain_deltas == 1
    assert summary.invalid_core_contexts == 0
    assert summary.latency_p99_us == 200



def _executive_market(
    symbol: str,
    *,
    asset_class: str,
    availability: ExecutiveMarketAvailability,
    authorization: ExecutiveMarketAuthorizationState,
) -> ExecutiveMarketSummary:
    evidence = ExecutiveEvidenceRef(f"market-evidence:{symbol.lower()}")
    return ExecutiveMarketSummary(
        instrument=ExecutiveMarketInstrument(symbol),
        asset_class=ExecutiveAssetClass(asset_class),
        availability=availability,
        authorization_state=authorization,
        regime_code="context-available",
        session_code="global",
        reason_codes=("canonical-market-state",),
        evidence_refs=(evidence,),
    )


def test_global_market_universe_retains_every_qore_market_without_allowlist() -> None:
    metadata = ExecutiveProjectionMetadata(
        projection_id=ExecutiveProjectionId(
            UUID("00000000-0000-0000-0000-000000000635")
        ),
        projection_version=ExecutiveProjectionVersion("core-v2-market-universe"),
        scope=ExecutiveReadScope.MARKETS,
        source_observed_at=NOW,
        projected_at=NOW,
        freshness=ExecutiveSourceFreshness.FRESH,
    )
    read_model = ExecutiveMarketsReadModel(
        metadata=metadata,
        attention=ExecutiveAttentionLevel.INFORMATION,
        markets=(
            _executive_market(
                "XAUUSD",
                asset_class="metals",
                availability=ExecutiveMarketAvailability.RESTRICTED,
                authorization=ExecutiveMarketAuthorizationState.BLOCKED,
            ),
            _executive_market(
                "NAS100",
                asset_class="indices",
                availability=ExecutiveMarketAvailability.AVAILABLE,
                authorization=ExecutiveMarketAuthorizationState.AUTHORIZED,
            ),
            _executive_market(
                "EURUSD",
                asset_class="forex",
                availability=ExecutiveMarketAvailability.AVAILABLE,
                authorization=ExecutiveMarketAuthorizationState.AUTHORIZED,
            ),
        ),
    )

    universe = build_global_market_universe(read_model)

    assert GLOBAL_MARKET_UNIVERSE_REQUIRED is True
    assert tuple(item.instrument for item in universe.markets) == (
        "EURUSD",
        "NAS100",
        "XAUUSD",
    )
    assert universe.market_count == 3
    xau = next(item for item in universe.markets if item.instrument == "XAUUSD")
    assert xau.availability == "restricted"
    assert xau.authorization_state == "blocked"
    assert universe.order_authority is False
    assert universe.risk_authority is False
    assert universe.strategy_mutation_authority is False
    assert universe.execution_authority is False


def test_superintelligence_architecture_freeze_preserves_owner_laws() -> None:
    contract = superintelligence_freeze_contract()
    universe = contract["global_market_universe"]
    sovereignty = contract["specialist_sovereignty"]
    dual_mission = contract["shared_dual_mission"]
    benchmark = contract["vt31_benchmark"]
    falsification = contract["operational_falsification"]
    governance = contract["governance"]

    assert isinstance(universe, dict)
    assert universe["required"] is True
    assert universe["dynamic_not_hardcoded"] is True
    assert universe["retain_restricted_markets_as_context"] is True
    assert universe["market_knowledge_implies_trade_authority"] is False

    assert isinstance(sovereignty, dict)
    assert sovereignty["shared_core_may_rewrite_setup"] is False
    assert sovereignty["shared_core_may_authorize_order"] is False
    assert sovereignty["shared_core_may_authorize_risk"] is False
    assert sovereignty["qore_risk_sovereign"] is True

    assert isinstance(dual_mission, dict)
    mission_1 = dual_mission["mission_1_decision_support"]
    mission_2 = dual_mission["mission_2_trade_potentiation"]
    assert isinstance(mission_1, dict)
    assert isinstance(mission_2, dict)
    assert mission_1["methodology_rules_unchanged"] is True
    assert mission_1["profit_factor_must_increase"] is True
    assert mission_1["observed_drawdown_must_decrease"] is True
    assert mission_2["trader_trade_identity_preserved"] is True
    assert mission_2["profit_factor_must_increase"] is True
    assert mission_2["observed_drawdown_may_increase"] is False
    assert dual_mission["success_requires_both_missions"] is True

    assert isinstance(benchmark, dict)
    assert benchmark["parity_is_only_safety_gate"] is True
    assert benchmark["economic_objective_is_material_uplift"] is True
    assert benchmark["no_future_features"] is True
    legacy = benchmark["legacy_core_stack_certified"]
    assert isinstance(legacy, dict)
    assert legacy["winner_count_5y"] == 241
    assert legacy["certification_loser_count_5y"] == 565
    assert legacy["weighted_pf_is_not_signal_quality_pf"] is True
    assert legacy["signal_quality_must_be_measured_unweighted"] is True

    assert isinstance(falsification, dict)
    assert falsification["required"] is True
    assert falsification["same_realized_market_path_required"] is True
    assert falsification["same_opportunity_universe_required"] is True
    assert falsification["shared_decision_must_precede_outcome"] is True
    assert falsification["shared_must_materially_outperform_on_poor_period"] is True
    assert falsification["shared_failure_to_improve_materially_is_falsification"] is True
    assert falsification["hindsight_reclassification_forbidden"] is True

    assert isinstance(governance, dict)
    assert governance["vt08_forex_excluded"] is True
    assert governance["live_deployment_authorized"] is False
    assert governance["merge_authorized"] is False
    assert len(superintelligence_freeze_fingerprint()) == 64


def test_real_operation_falsification_uses_exact_pre_entry_shadow_decisions() -> None:
    entries = tuple(
        NOW + timedelta(minutes=index)
        for index in range(5)
    )
    realized = (
        Decimal("1"),
        Decimal("-1"),
        Decimal("2"),
        Decimal("-1"),
        Decimal("1"),
    )
    trades = tuple(
        ActualTrade(
            trade_id=f"real-{index}",
            entry_at=entry,
            exit_at=entry + timedelta(minutes=10),
            realized_r=value,
        )
        for index, (entry, value) in enumerate(zip(entries, realized, strict=True))
    )
    decisions = tuple(
        SharedShadowDecision(
            trade_id=trade.trade_id,
            decided_at=trade.entry_at - timedelta(seconds=1),
            action=(
                ShadowAction.ABSTAIN
                if trade.trade_id == "real-1"
                else ShadowAction.PASS
            ),
            context_fingerprint=f"ctx-{index}",
        )
        for index, trade in enumerate(trades)
    )

    result = evaluate_real_operation_falsification(trades, decisions)

    assert result.baseline.profit_factor == Decimal("2")
    assert result.shared_shadow.profit_factor == Decimal("4")
    assert result.baseline.total_r == Decimal("2")
    assert result.shared_shadow.total_r == Decimal("3")
    assert result.density_retained == Decimal("0.8")
    assert result.losses_avoided == 1
    assert result.winners_sacrificed == 0
    assert result.pf_delta_pct == Decimal("100")
    assert result.exact_opportunity_binding is True
    assert result.all_shadow_decisions_pre_entry is True
    assert result.current_outcome_used_by_shadow is False
    assert result.shared_order_authority is False
    assert result.shared_risk_authority is False


def test_real_operation_falsification_rejects_post_entry_shadow_decision() -> None:
    trade = ActualTrade(
        trade_id="late-shadow",
        entry_at=NOW,
        exit_at=NOW + timedelta(minutes=5),
        realized_r=Decimal("-1"),
    )
    decision = SharedShadowDecision(
        trade_id=trade.trade_id,
        decided_at=NOW + timedelta(microseconds=1),
        action=ShadowAction.ABSTAIN,
        context_fingerprint="ctx-late",
    )

    with pytest.raises(ValueError, match="produced after entry"):
        evaluate_real_operation_falsification((trade,), (decision,))



def test_causal_analog_memory_excludes_current_and_future_episodes() -> None:
    memory = CausalAnalogMemory(
        (
            ClosedEpisode(
                episode_id="past-loss",
                market="NAS100",
                closed_at=NOW - timedelta(days=3),
                signature=(("entry_family", "fvg"), ("risk_ref", "0.5")),
                terminal_r=Decimal("-1"),
            ),
            ClosedEpisode(
                episode_id="past-win",
                market="NAS100",
                closed_at=NOW - timedelta(days=2),
                signature=(("entry_family", "fvg"), ("risk_ref", "0.6")),
                terminal_r=Decimal("2"),
            ),
            ClosedEpisode(
                episode_id="future-forbidden",
                market="NAS100",
                closed_at=NOW + timedelta(minutes=1),
                signature=(("entry_family", "fvg"), ("risk_ref", "0.5")),
                terminal_r=Decimal("-10"),
            ),
        )
    )
    summary = memory.query(
        AnalogQuery(
            market="NAS100",
            as_of=NOW,
            signature=(("entry_family", "fvg"), ("risk_ref", "0.5")),
            maximum_analogs=10,
            minimum_similarity_bps=0,
        )
    )
    assert {item.episode_id for item in summary.analogs} == {
        "past-loss",
        "past-win",
    }
    assert all(item.closed_at < NOW for item in summary.analogs)
    assert summary.weighted_mean_r is not None
    assert summary.weighted_loss_rate is not None


def test_causal_analog_memory_is_deterministic() -> None:
    episodes = (
        ClosedEpisode(
            episode_id="a",
            market="NAS100",
            closed_at=NOW - timedelta(days=3),
            signature=(("side", "long"), ("risk_ref", "0.5")),
            terminal_r=Decimal("-1"),
        ),
        ClosedEpisode(
            episode_id="b",
            market="NAS100",
            closed_at=NOW - timedelta(days=2),
            signature=(("side", "long"), ("risk_ref", "0.55")),
            terminal_r=Decimal("2"),
        ),
    )
    request = AnalogQuery(
        market="NAS100",
        as_of=NOW,
        signature=(("side", "long"), ("risk_ref", "0.52")),
        maximum_analogs=2,
        minimum_similarity_bps=0,
    )
    first = CausalAnalogMemory(episodes).query(request)
    second = CausalAnalogMemory(episodes).query(request)
    assert first == second
