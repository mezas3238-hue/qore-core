from datetime import UTC, datetime, timedelta
from decimal import Decimal
from hashlib import sha256
from pathlib import Path

import pytest

from qore.infrastructure.account_wide_risk import RiskDecision, TraderLineage
from qore.infrastructure.cibo_account_capital_mission import (
    CiboAccountCapitalIdentity,
)
from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
    TraderOpportunityEnvelope,
)
from qore.infrastructure.cibo_ce2i_phase20_forward_policy_store import (
    VersionedPhase20ForwardPolicyBook,
)
from qore.infrastructure.cibo_ce2i_regime_selector import (
    CiboCapitalRegimeState,
    CorrelationState,
    LiquidityState,
    ProviderCondition,
    VolatilityState,
)
from qore.infrastructure.cibo_phase22_historical_policy_replay import (
    Phase22HistoricalCapitalInput,
)
from qore.infrastructure.cibo_phase22_historical_replay_economics_amendment import (
    Phase22ProviderCalibrationReceipt,
    freeze_phase22_historical_replay_economics_amendment,
)
from qore.infrastructure.cibo_phase22_historical_replay_sealing import (
    Phase22HistoricalReplayCandidateEvidence,
    seal_phase22_historical_replay_epoch,
)
from qore.infrastructure.cibo_phase22_historical_replay_settlement import (
    VersionedPhase22HistoricalReplayEvidenceBook,
    build_phase22_historical_replay_outcome,
)
from qore.infrastructure.cibo_phase22_historical_replay_stores import (
    Phase22HistoricalReplayStoreSet,
    VersionedPhase22HistoricalExecutedRiskBook,
    VersionedPhase22HistoricalReleaseBook,
    VersionedPhase22HistoricalSettlementBook,
    build_phase22_historical_release_seal,
    build_phase22_historical_risk_seal,
    persist_phase22_historical_store_set,
)
from qore.infrastructure.cibo_phase22_holdout_v2_source_receipt import (
    V2_SOURCE_BINDINGS,
    phase22_v2_holdout_source_receipt_sha256,
)
from qore.infrastructure.cibo_phase22_provider_execution_calibration_receipt import (
    PHASE22_PROVIDER_EXECUTION_CALIBRATION_RECEIPT,
)
from qore.infrastructure.cibo_phase22_store_bundle import build_phase22_store_bundle
from qore.infrastructure.cibo_provider_economic_normalization import (
    ProviderEconomicObservation,
)
from qore.infrastructure.market_test_environment import MarketRuntimeEnvironment

MARKET_AT = datetime(2015, 10, 20, 12, 0, tzinfo=UTC)
SEALED_AT = datetime(2026, 10, 27, 12, 0, tzinfo=UTC)


def _sha(label: str) -> str:
    return "sha256:" + sha256(label.encode()).hexdigest()


def _candidate() -> Phase22HistoricalReplayCandidateEvidence:
    opportunity = TraderOpportunityEnvelope(
        trader_id=TraderLineage.R43_GBPUSD,
        signal_fingerprint="phase22-store-signal-1",
        qore_symbol="GBPUSD",
        provider_symbol="GBPUSD",
        side="long",
        entry_type="market",
        intended_entry=Decimal("100"),
        stop_loss=Decimal("99"),
        take_profit=Decimal("102"),
        stop_loss_per_volume=Decimal("10"),
        margin_per_volume=Decimal("20"),
        volume_step=Decimal("0.01"),
        minimum_volume=Decimal("0.01"),
        maximum_volume=Decimal("100"),
    )
    provider = ProviderEconomicObservation(
        provider_key="ctrader-demo",
        qore_symbol="GBPUSD",
        provider_symbol="GBPUSD",
        bid=Decimal("100"),
        ask=Decimal("101"),
        contract_size=Decimal("100000"),
        tick_size=Decimal("1"),
        tick_value=Decimal("10"),
        minimum_volume=Decimal("0.01"),
        maximum_volume=Decimal("100"),
        volume_step=Decimal("0.01"),
        margin_per_volume=Decimal("20"),
        commission_per_volume_usd=Decimal("3"),
        slippage_reserve_per_volume_usd=Decimal("1"),
        observed_at=datetime(2026, 10, 1, 20, tzinfo=UTC),
    )
    return Phase22HistoricalReplayCandidateEvidence(
        capital_input=Phase22HistoricalCapitalInput(
            opportunity=opportunity,
            minimum_stop_risk_usd=Decimal("0.10"),
            minimum_margin_usd=Decimal("0.20"),
            concentration_group="GBPUSD",
            concentration_risk_usd=Decimal("0.10"),
            provider_model_sha256=(
                PHASE22_PROVIDER_EXECUTION_CALIBRATION_RECEIPT.fingerprint()
            ),
        ),
        provider_observation=provider,
        provider_evidence_id="provider-current:GBPUSD:store-test",
    )


def _pair():
    return seal_phase22_historical_replay_epoch(
        decision_epoch_id="phase22-store-epoch-1",
        market_decision_at=MARKET_AT,
        replay_sealed_at=SEALED_AT,
        seal_deadline_at=SEALED_AT + timedelta(seconds=2),
        account_identity=CiboAccountCapitalIdentity(
            provider_key="ctrader-demo",
            account_ref="phase22-v2-counterfactual",
            environment=MarketRuntimeEnvironment.DEMO,
        ),
        candidates=(_candidate(),),
        regime_state=CiboCapitalRegimeState(
            liquidity=LiquidityState.NORMAL,
            volatility=VolatilityState.NORMAL,
            correlation=CorrelationState.NORMAL,
            provider_condition=ProviderCondition.HEALTHY,
            risk_utilization=Decimal("0"),
            margin_utilization=Decimal("0"),
            drawdown_utilization=Decimal("0"),
            opportunity_count=1,
        ),
        hard_risk_headroom_usd=Decimal("3.60"),
        margin_headroom_usd=Decimal("60"),
        concentration_limit_by_group=(("GBPUSD", Decimal("1.80")),),
        current_step=0,
    )


def _amendment():
    calibration = Phase22ProviderCalibrationReceipt(
        artifact_sha256=_sha("calibration"),
        git_sha="a" * 40,
        account_fingerprint_sha256=sha256(b"account").hexdigest(),
        observed_at=datetime(2026, 10, 1, 20, 40, tzinfo=UTC),
        status="READY",
        required_symbols=(
            "AUDJPY",
            "EURUSD",
            "GBPJPY",
            "GBPUSD",
            "NAS100",
            "XAUUSD",
        ),
        distinct_entry_orders_by_symbol=(
            ("AUDJPY", 8),
            ("EURUSD", 8),
            ("GBPJPY", 8),
            ("GBPUSD", 8),
            ("NAS100", 8),
            ("XAUUSD", 8),
        ),
        empirical_slippage_calibrated=True,
        execution_model_ready=True,
        execution_population_ready=True,
        created_positions_closed=True,
        minimum_volume_only=True,
        historical_provider_economics_claimed=False,
        historical_holdout_execution_claimed=False,
        holdout_outcomes_used=False,
        fundednext_touched=False,
        vps_touched=False,
        live_authorized=False,
        real_capital_authorized=False,
        productive_authority=False,
        blockers=(),
    )
    return freeze_phase22_historical_replay_economics_amendment(
        provider_calibration=calibration,
        fresh_outcomes_emitted=False,
        holdout_outcomes_inspected=False,
    )


def _books() -> Phase22HistoricalReplayStoreSet:
    pair = _pair()
    assert pair.policy.selected_signal_fingerprints == ("phase22-store-signal-1",)

    risk = build_phase22_historical_risk_seal(
        decision=pair.decision,
        signal_fingerprint="phase22-store-signal-1",
        trader_id="R43_GBPUSD",
        qore_symbol="GBPUSD",
        decided_at=MARKET_AT,
        risk_decision=RiskDecision.ALLOW,
        requested_stop_risk_usd=Decimal("0.10"),
        authorized_stop_risk_usd=Decimal("0.10"),
        authorized_margin_usd=Decimal("0.20"),
        risk_model_sha256=_sha("risk-model"),
    )
    amendment = _amendment()
    deployed = MARKET_AT + timedelta(minutes=1)
    released = deployed + timedelta(minutes=30)
    outcome = build_phase22_historical_replay_outcome(
        amendment=amendment,
        decision=pair.decision,
        signal_fingerprint="phase22-store-signal-1",
        trader_id="R43_GBPUSD",
        qore_symbol="GBPUSD",
        observed_at=released,
        gross_structural_outcome_r=Decimal("2"),
        executed_initial_stop_risk_usd=risk.authorized_stop_risk_usd,
        provider_execution_adjustment_usd=Decimal("0.01"),
        decision_provider_cost_proxy_usd=Decimal("0.01"),
        capital_deployed_at=deployed,
        capital_released_at=released,
    )
    release = build_phase22_historical_release_seal(
        risk=risk,
        settlement=outcome,
    )
    evidence = VersionedPhase22HistoricalReplayEvidenceBook(
        generation=1,
        amendment_sha256=amendment.fingerprint(),
        decisions=(pair.decision,),
        outcomes=(outcome,),
        source_receipt_sha256=phase22_v2_holdout_source_receipt_sha256(),
        source_collector_git_shas=tuple(
            sorted({item.collector_git_sha for item in V2_SOURCE_BINDINGS})
        ),
    )
    return Phase22HistoricalReplayStoreSet(
        holdout_evidence=evidence,
        holdout_policy=VersionedPhase20ForwardPolicyBook(
            generation=1,
            decisions=(pair.policy,),
        ),
        executed_risk=VersionedPhase22HistoricalExecutedRiskBook(
            generation=1,
            executed_risk=(risk,),
        ),
        cma_settlement=VersionedPhase22HistoricalSettlementBook(
            generation=1,
            settlements=(outcome,),
        ),
        t20_release=VersionedPhase22HistoricalReleaseBook(
            generation=1,
            release_chain=(release,),
        ),
    )


def test_phase22_native_stores_roundtrip_without_historical_broker_ids(
    tmp_path: Path,
) -> None:
    root = tmp_path / "phase22-v2-stores"
    bundle = build_phase22_store_bundle(root)
    bundle.assert_pristine()

    digests = persist_phase22_historical_store_set(
        root=root,
        books=_books(),
    )

    assert len(digests) == 5
    assert len(set(digests)) == 5
    assert bundle.holdout_evidence.load().generation == 1
    assert bundle.holdout_policy.load().generation == 1
    assert bundle.executed_risk.load().generation == 1
    assert bundle.cma_settlement.load().generation == 1
    assert bundle.t20_release.load().generation == 1

    for path in bundle.paths:
        text = path.read_text(encoding="utf-8")
        assert '"productive_authority": false' in text
        assert '"historical_broker_execution_claimed": false' in text
        assert "position_id" not in text
        assert "deal_id" not in text
        assert "fill_id" not in text


def test_phase22_native_store_set_is_create_once(tmp_path: Path) -> None:
    root = tmp_path / "phase22-v2-stores"
    books = _books()
    persist_phase22_historical_store_set(root=root, books=books)

    with pytest.raises(
        CiboCapitalManagementError,
        match="create-once and pristine",
    ):
        persist_phase22_historical_store_set(root=root, books=books)
