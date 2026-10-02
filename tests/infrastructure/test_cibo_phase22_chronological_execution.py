from datetime import UTC, datetime, timedelta
from decimal import Decimal
from hashlib import sha256

from qore.infrastructure.account_wide_risk import TraderLineage
from qore.infrastructure.cibo_ce2i_regime_selector import (
    CorrelationState,
    LiquidityState,
    ProviderCondition,
    VolatilityState,
)
from qore.infrastructure.cibo_phase22_chronological_execution import (
    Phase22HistoricalRegimeEvidence,
    execute_phase22_chronological_replay,
    phase22_historical_risk_model_sha256,
)
from qore.infrastructure.cibo_phase22_chronological_replay_plan import (
    build_phase22_chronological_replay_plan,
)
from qore.infrastructure.cibo_phase22_execution_inputs import (
    load_phase22_sealed_fresh_batch,
    load_phase22_sealed_provider_numeric,
    project_phase22_execution_inputs,
)
from qore.infrastructure.cibo_phase22_fresh_opportunity_batch import (
    Phase22FreshOpportunity,
    Phase22FreshTraderEvidence,
    build_phase22_fresh_opportunity_batch,
)
from qore.infrastructure.cibo_phase22_provider_numeric_execution import (
    Phase22ProviderAccountLineageReceipt,
    Phase22ProviderNumericExecutionSpec,
)
from qore.infrastructure.cibo_phase22_trader_parity_manifest import (
    CANONICAL_PHASE22_TRADER_IDS,
)


def _sha(label: str) -> str:
    return "sha256:" + sha256(label.encode()).hexdigest()


def _fresh(trader_id: str, symbol: str, index: int) -> Phase22FreshOpportunity:
    signal_at = datetime(2015, 11, 2, 10, tzinfo=UTC) + timedelta(
        days=index * 3
    )
    return Phase22FreshOpportunity(
        trader_id=TraderLineage(trader_id),
        qore_symbol=symbol,
        signal_fingerprint=_sha(f"exec-signal-{trader_id}"),
        signal_at=signal_at,
        entry_at=signal_at + timedelta(minutes=5),
        exit_at=signal_at + timedelta(hours=2),
        side="long",
        entry_price=Decimal("100"),
        structural_stop=Decimal("99"),
        technical_target=Decimal("102"),
        exit_reason="target",
        gross_structural_outcome_r=Decimal("2"),
        methodology_sha256=_sha(f"method-{trader_id}"),
        source_evidence_ids=(_sha(f"source-{trader_id}"),),
    )


def _fresh_payload() -> dict[str, object]:
    symbols = {
        "VT08_FOREX": "GBPUSD",
        "R34_XAUUSD": "XAUUSD",
        "R38_EURUSD": "EURUSD",
        "R43_GBPUSD": "GBPUSD",
        "R38_GBPJPY": "GBPJPY",
        "R42_AUDJPY": "AUDJPY",
        "VT31_NAS100": "NAS100",
    }
    traders = tuple(
        Phase22FreshTraderEvidence(
            trader_id=trader_id,
            source_artifact_sha256=_sha(f"lane-{trader_id}"),
            opportunities=(_fresh(trader_id, symbols[trader_id], index),),
            fresh_outcomes_executed=True,
            methodology_changed=False,
            legacy_trader_sizing_used_for_cibo=False,
        )
        for index, trader_id in enumerate(CANONICAL_PHASE22_TRADER_IDS)
    )
    batch = build_phase22_fresh_opportunity_batch(traders)
    return {
        "schema": "qore.cibo.phase22.fresh-batch-assembly.v1",
        "candidate_id": batch.candidate_id,
        "batch_sha256": batch.fingerprint(),
        "traders": [
            {
                "trader_id": item.trader_id,
                "lane_artifact_sha256": item.source_artifact_sha256,
                "opportunity_count": len(item.opportunities),
                "evidence_sha256": item.fingerprint(),
            }
            for item in batch.traders
        ],
        "opportunities": [item.payload() for item in batch.opportunities],
        "legacy_trader_sizing_used_for_cibo": False,
        "productive_authority": False,
    }


def _provider_payload() -> dict[str, object]:
    lineage = Phase22ProviderAccountLineageReceipt(
        provider_key="ctrader-demo",
        legacy_account_fingerprint_sha256=(
            "70d38b13a2afb1ada12883a486ddb39aa0626e4c262b69ee44410bb6531d6086"
        ),
        phase22_account_fingerprint_sha256=(
            "17585ecd6f116a92d19919e46948f06c027d0cbf9f1cb8d97802f20055bad17b"
        ),
        same_account_proven=True,
    )
    specs = []
    for symbol in ("AUDJPY", "EURUSD", "GBPJPY", "GBPUSD", "NAS100", "XAUUSD"):
        is_nas = symbol == "NAS100"
        specs.append(
            Phase22ProviderNumericExecutionSpec(
                qore_symbol=symbol,
                provider_symbol="USTEC" if is_nas else symbol,
                observed_at=datetime(2026, 10, 1, 20, tzinfo=UTC),
                bid=Decimal("100"),
                ask=Decimal("100"),
                display_digits=2,
                contract_size_per_volume=(
                    Decimal("1") if is_nas else Decimal("100000")
                ),
                minimum_volume=(
                    Decimal("0.1") if is_nas else Decimal("0.01")
                ),
                maximum_volume=Decimal("100"),
                volume_step=(
                    Decimal("0.1") if is_nas else Decimal("0.01")
                ),
                margin_per_volume_usd=Decimal("10"),
                commission_per_volume_usd=Decimal("0"),
                worst_adverse_slippage_bps=Decimal("0"),
                quote_to_usd=Decimal("1"),
                usd_value_per_price_unit_per_volume=(
                    Decimal("1") if is_nas else Decimal("100000")
                ),
                derived_price_quantum=Decimal("0.01"),
                derived_value_per_quantum_usd=(
                    Decimal("0.01") if is_nas else Decimal("1000")
                ),
                source_provider_terms_artifact_sha256=_sha("terms"),
                source_empirical_execution_artifact_sha256=_sha("empirical"),
            )
        )
    return {
        "schema": "qore.cibo.phase22.provider-numeric-execution-freeze.v1",
        "status": "READY",
        "account_lineage": lineage.payload(),
        "account_lineage_sha256": lineage.fingerprint(),
        "specs": [item.payload() for item in specs],
        "holdout_market_data_read": False,
        "holdout_outcomes_used": False,
        "broker_mutation_performed": False,
        "historical_provider_economics_claimed": False,
        "productive_authority": False,
    }


def _execution_inputs():
    fresh = load_phase22_sealed_fresh_batch(_fresh_payload())
    provider = load_phase22_sealed_provider_numeric(_provider_payload())
    projections = project_phase22_execution_inputs(
        fresh=fresh,
        provider=provider,
        provider_numeric_freeze_sha256=_sha("provider-freeze"),
    )
    replay = build_phase22_chronological_replay_plan(
        fresh=fresh,
        projections=projections,
    )
    regimes = tuple(
        Phase22HistoricalRegimeEvidence(
            decision_epoch_id=epoch.decision_epoch_id,
            observed_at=epoch.market_decision_at,
            liquidity=LiquidityState.NORMAL,
            volatility=VolatilityState.NORMAL,
            correlation=CorrelationState.NORMAL,
            provider_condition=ProviderCondition.HEALTHY,
            concentration_limit_by_group=tuple(
                (
                    candidate.projection.candidate.capital_input.concentration_group,
                    Decimal("60"),
                )
                for candidate in epoch.candidates
            ),
            evidence_sha256=_sha(epoch.decision_epoch_id),
            source_evidence_ids=(_sha("regime-source-" + epoch.decision_epoch_id),),
        )
        for epoch in replay.epochs
    )
    return replay, regimes


def test_chronological_execution_preserves_risk_settlement_release_identity() -> None:
    replay, regimes = _execution_inputs()
    report = execute_phase22_chronological_replay(
        plan=replay,
        regime_evidence=regimes,
        replay_started_at=datetime(2026, 10, 2, 7, tzinfo=UTC),
    )

    assert report.initial_realized_capital_usd == Decimal("60")
    assert report.accounting_residual_usd == 0
    assert report.selected_count == (
        report.allowed_count + report.reduced_count + report.rejected_count
    )
    assert report.settled_count == report.allowed_count + report.reduced_count
    assert len(report.books.executed_risk.executed_risk) == report.selected_count
    assert len(report.books.cma_settlement.settlements) == report.settled_count
    assert len(report.books.t20_release.release_chain) == report.settled_count
    assert report.floating_pnl_used_as_funding is False
    assert report.broker_mutation_performed is False
    assert report.historical_broker_fills_claimed is False


def test_replay_risk_model_is_stable_and_counterfactual() -> None:
    first = phase22_historical_risk_model_sha256()
    second = phase22_historical_risk_model_sha256()

    assert first == second
    assert first.startswith("sha256:")


def test_regime_evidence_must_cover_exact_epoch_surface() -> None:
    replay, regimes = _execution_inputs()

    try:
        execute_phase22_chronological_replay(
            plan=replay,
            regime_evidence=regimes[:-1],
            replay_started_at=datetime(2026, 10, 2, 7, tzinfo=UTC),
        )
    except Exception as error:
        assert "exact epoch set" in str(error)
    else:
        raise AssertionError("missing regime evidence must fail closed")
