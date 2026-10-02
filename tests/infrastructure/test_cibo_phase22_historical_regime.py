from datetime import UTC, datetime, timedelta
from decimal import Decimal
from hashlib import sha256

from qore.infrastructure.account_wide_risk import TraderLineage
from qore.infrastructure.cibo_ce2i_phase20_demo_regime import (
    phase20_demo_regime_policy_sha256,
)
from qore.infrastructure.cibo_ce2i_regime_selector import (
    CorrelationState,
    LiquidityState,
    ProviderCondition,
    VolatilityState,
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
from qore.infrastructure.cibo_phase22_historical_regime import (
    PHASE22_REGIME_SYMBOLS,
    build_phase22_historical_regime_evidence,
)
from qore.infrastructure.cibo_phase22_provider_numeric_execution import (
    Phase22ProviderAccountLineageReceipt,
    Phase22ProviderNumericExecutionSpec,
)
from qore.infrastructure.cibo_phase22_trader_parity_manifest import (
    CANONICAL_PHASE22_TRADER_IDS,
)
from qore.infrastructure.trader_lab.ict_turtle_soup_r4_source_exact import (
    Bar,
    Evidence,
)


def _sha(label: str) -> str:
    return "sha256:" + sha256(label.encode()).hexdigest()


def _fresh(trader_id: str, symbol: str, index: int) -> Phase22FreshOpportunity:
    signal_at = datetime(2015, 10, 21, 12, tzinfo=UTC) + timedelta(
        days=index
    )
    return Phase22FreshOpportunity(
        trader_id=TraderLineage(trader_id),
        qore_symbol=symbol,
        signal_fingerprint=_sha(f"regime-signal-{trader_id}"),
        signal_at=signal_at,
        entry_at=signal_at + timedelta(minutes=5),
        exit_at=signal_at + timedelta(hours=1),
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
        specs.append(
            Phase22ProviderNumericExecutionSpec(
                qore_symbol=symbol,
                provider_symbol=symbol,
                observed_at=datetime(2026, 10, 1, 20, tzinfo=UTC),
                bid=Decimal("100"),
                ask=Decimal("100.01"),
                display_digits=2,
                contract_size_per_volume=Decimal("1"),
                minimum_volume=Decimal("0.01"),
                maximum_volume=Decimal("100"),
                volume_step=Decimal("0.01"),
                margin_per_volume_usd=Decimal("10"),
                commission_per_volume_usd=Decimal("0"),
                worst_adverse_slippage_bps=Decimal("0"),
                quote_to_usd=Decimal("1"),
                usd_value_per_price_unit_per_volume=Decimal("1"),
                derived_price_quantum=Decimal("0.01"),
                derived_value_per_quantum_usd=Decimal("0.01"),
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


def _corpora(*, bar_count: int = 900) -> tuple[Evidence, ...]:
    start = datetime(2015, 10, 18, tzinfo=UTC)
    result = []
    for symbol_index, symbol in enumerate(PHASE22_REGIME_SYMBOLS):
        bars = []
        base = Decimal("100") + Decimal(symbol_index)
        for index in range(bar_count):
            opened = start + timedelta(minutes=5 * index)
            center = base + Decimal(index) / Decimal("10000")
            width = Decimal("0.20")
            bars.append(
                Bar(
                    opened_at=opened,
                    closed_at=opened + timedelta(minutes=5),
                    open=center,
                    high=center + width / Decimal(2),
                    low=center - width / Decimal(2),
                    close=center + Decimal("0.01"),
                )
            )
        result.append(Evidence(symbol=symbol, digits=2, bars=tuple(bars)))
    return tuple(result)


def _plan_and_provider():
    fresh = load_phase22_sealed_fresh_batch(_fresh_payload())
    provider = load_phase22_sealed_provider_numeric(_provider_payload())
    projections = project_phase22_execution_inputs(
        fresh=fresh,
        provider=provider,
        provider_numeric_freeze_sha256=_sha("provider-freeze"),
    )
    plan = build_phase22_chronological_replay_plan(
        fresh=fresh,
        projections=projections,
    )
    return plan, provider


def test_historical_regime_reuses_frozen_phase20_policy_without_history_claims() -> None:
    plan, provider = _plan_and_provider()
    evidence = build_phase22_historical_regime_evidence(
        plan=plan,
        provider=provider,
        provider_numeric_freeze_sha256=_sha("provider-freeze"),
        corpora=_corpora(),
    )

    assert len(evidence) == len(plan.epochs)
    assert all(
        item.regime_policy_sha256 == phase20_demo_regime_policy_sha256()
        for item in evidence
    )
    assert all(item.counterfactual_provider_model for item in evidence)
    assert not any(item.historical_provider_state_claimed for item in evidence)
    assert not any(item.outcome_fields_used for item in evidence)
    assert all(item.concentration_limit_by_group == () for item in evidence)
    assert all(item.market_history_sufficient for item in evidence)
    assert not any(item.evidence_stale for item in evidence)
    assert all(item.provider_condition is ProviderCondition.HEALTHY for item in evidence)


def test_missing_72_bar_history_fails_closed() -> None:
    plan, provider = _plan_and_provider()
    evidence = build_phase22_historical_regime_evidence(
        plan=plan,
        provider=provider,
        provider_numeric_freeze_sha256=_sha("provider-freeze"),
        corpora=_corpora(bar_count=20),
    )

    assert all(not item.market_history_sufficient for item in evidence)
    assert all(item.evidence_stale for item in evidence)
    assert all(item.liquidity is LiquidityState.STRESSED for item in evidence)
    assert all(item.volatility is VolatilityState.DISLOCATED for item in evidence)
    assert all(item.correlation is CorrelationState.BREAK for item in evidence)
    assert all(item.provider_condition is ProviderCondition.DEGRADED for item in evidence)


def test_historical_regime_evidence_is_deterministic() -> None:
    plan, provider = _plan_and_provider()
    first = build_phase22_historical_regime_evidence(
        plan=plan,
        provider=provider,
        provider_numeric_freeze_sha256=_sha("provider-freeze"),
        corpora=_corpora(),
    )
    second = build_phase22_historical_regime_evidence(
        plan=plan,
        provider=provider,
        provider_numeric_freeze_sha256=_sha("provider-freeze"),
        corpora=_corpora(),
    )

    assert first == second
    assert tuple(item.evidence_sha256 for item in first) == tuple(
        item.evidence_sha256 for item in second
    )
