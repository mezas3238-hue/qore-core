from datetime import UTC, datetime, timedelta
from decimal import Decimal

from qore.infrastructure.account_wide_risk import TraderLineage
from qore.infrastructure.cibo_account_capital_mission import (
    CiboAccountCapitalIdentity,
)
from qore.infrastructure.cibo_capital_management_authority import (
    TraderOpportunityEnvelope,
)
from qore.infrastructure.cibo_ce2i_phase20_forward_policy_store import (
    VersionedPhase20ForwardPolicyBook,
)
from qore.infrastructure.cibo_ce2i_phase20_policy_candidate import (
    FROZEN_PHASE20_POLICY_CANDIDATE,
)
from qore.infrastructure.cibo_ce2i_phase20_qualification_readiness import (
    assess_phase20d_qualification_readiness,
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
from qore.infrastructure.cibo_phase22_historical_replay_sealing import (
    Phase22HistoricalReplayCandidateEvidence,
    seal_phase22_historical_replay_epoch,
)
from qore.infrastructure.cibo_phase22_historical_replay_settlement import (
    VersionedPhase22HistoricalReplayEvidenceBook,
)
from qore.infrastructure.cibo_phase22_holdout_v2_source_receipt import (
    V2_SOURCE_BINDINGS,
    phase22_v2_holdout_source_receipt_sha256,
)
from qore.infrastructure.cibo_phase22_provider_execution_calibration_receipt import (
    PHASE22_PROVIDER_EXECUTION_CALIBRATION_RECEIPT,
)
from qore.infrastructure.cibo_phase22_v4_historical_policy_replay import (
    Phase22HistoricalCapitalInput as Phase22V4HistoricalCapitalInput,
)
from qore.infrastructure.cibo_phase22_v4_historical_replay_sealing import (
    Phase22HistoricalReplayCandidateEvidence as Phase22V4ReplayCandidateEvidence,
)
from qore.infrastructure.cibo_phase22_v4_historical_replay_sealing import (
    seal_phase22_historical_replay_epoch as seal_phase22_v4_historical_replay_epoch,
)
from qore.infrastructure.cibo_provider_economic_normalization import (
    ProviderEconomicObservation,
)
from qore.infrastructure.market_test_environment import MarketRuntimeEnvironment

MARKET_AT = datetime(2015, 10, 20, 12, 0, tzinfo=UTC)
SEALED_AT = datetime(2026, 10, 27, 12, 0, tzinfo=UTC)


def _account() -> CiboAccountCapitalIdentity:
    return CiboAccountCapitalIdentity(
        provider_key="ctrader-demo",
        account_ref="phase22-v2-counterfactual",
        environment=MarketRuntimeEnvironment.DEMO,
    )


def _candidate() -> Phase22HistoricalReplayCandidateEvidence:
    opportunity = TraderOpportunityEnvelope(
        trader_id=TraderLineage.R43_GBPUSD,
        signal_fingerprint="phase22-r43-signal-1",
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
        observed_at=datetime(2026, 10, 1, 20, 0, tzinfo=UTC),
    )
    capital = Phase22HistoricalCapitalInput(
        opportunity=opportunity,
        minimum_stop_risk_usd=Decimal("0.10"),
        minimum_margin_usd=Decimal("0.20"),
        concentration_group="GBPUSD",
        concentration_risk_usd=Decimal("0.10"),
        provider_model_sha256=(
            PHASE22_PROVIDER_EXECUTION_CALIBRATION_RECEIPT.fingerprint()
        ),
    )
    return Phase22HistoricalReplayCandidateEvidence(
        capital_input=capital,
        provider_observation=provider,
        provider_evidence_id="provider-current:GBPUSD:test",
    )


def _v4_candidate() -> Phase22V4ReplayCandidateEvidence:
    base = _candidate()
    capital = base.capital_input
    return Phase22V4ReplayCandidateEvidence(
        capital_input=Phase22V4HistoricalCapitalInput(
            opportunity=capital.opportunity,
            minimum_stop_risk_usd=capital.minimum_stop_risk_usd,
            minimum_margin_usd=capital.minimum_margin_usd,
            concentration_group=capital.concentration_group,
            concentration_risk_usd=capital.concentration_risk_usd,
            provider_model_sha256=capital.provider_model_sha256,
        ),
        provider_observation=base.provider_observation,
        provider_evidence_id=base.provider_evidence_id,
    )


def _regime() -> CiboCapitalRegimeState:
    return CiboCapitalRegimeState(
        liquidity=LiquidityState.NORMAL,
        volatility=VolatilityState.NORMAL,
        correlation=CorrelationState.NORMAL,
        provider_condition=ProviderCondition.HEALTHY,
        risk_utilization=Decimal("0"),
        margin_utilization=Decimal("0"),
        drawdown_utilization=Decimal("0"),
        opportunity_count=1,
    )


def _sealed_pair():
    return seal_phase22_historical_replay_epoch(
        decision_epoch_id="phase22-epoch-1",
        market_decision_at=MARKET_AT,
        replay_sealed_at=SEALED_AT,
        seal_deadline_at=SEALED_AT + timedelta(seconds=2),
        account_identity=_account(),
        candidates=(_candidate(),),
        regime_state=_regime(),
        hard_risk_headroom_usd=Decimal("3.60"),
        margin_headroom_usd=Decimal("60"),
        concentration_limit_by_group=(("GBPUSD", Decimal("1.80")),),
        current_step=0,
    )


def test_sealer_preserves_historical_market_clock_and_postfreeze_seal() -> None:
    pair = _sealed_pair()

    assert pair.decision.decision_at == MARKET_AT
    assert pair.decision.sealed_at == SEALED_AT
    assert pair.decision.sealed_within_deadline is True
    assert pair.decision.collector_git_sha is None
    assert pair.policy.evidence_sha256 == pair.decision.evidence_sha256
    assert (
        pair.policy.selected_signal_fingerprints
        == (
            ()
            if pair.policy_record.allocator_decision.allocation is None
            else pair.policy_record.allocator_decision.allocation.selected_signal_fingerprints
        )
    )


def test_v4_sealer_keeps_market_time_separate_from_prior_availability() -> None:
    import json

    pair = seal_phase22_v4_historical_replay_epoch(
        decision_epoch_id="phase22-v4-clock-separation",
        market_decision_at=MARKET_AT,
        replay_sealed_at=SEALED_AT,
        seal_deadline_at=SEALED_AT + timedelta(seconds=2),
        account_identity=_account(),
        candidates=(_v4_candidate(),),
        regime_state=_regime(),
        hard_risk_headroom_usd=Decimal("3.60"),
        margin_headroom_usd=Decimal("60"),
        concentration_limit_by_group=(("GBPUSD", Decimal("1.80")),),
        current_step=0,
        lab_allow_nonpositive_expectation=True,
    )
    payload = json.loads(pair.decision.canonical_payload_json)
    candidate = payload["candidates"][0]["candidate"]

    assert payload["market_decision_at"] == MARKET_AT.isoformat()
    assert payload["policy_decision_at"] == SEALED_AT.isoformat()
    assert payload["train_prior_available_at"] == (
        FROZEN_PHASE20_POLICY_CANDIDATE.frozen_at.isoformat()
    )
    assert payload["time_semantics"]["train_prior_backdated_to_market_time"] is False
    assert candidate["decision_as_of"] == SEALED_AT.isoformat()
    assert candidate["expectation"]["as_of"] == (
        FROZEN_PHASE20_POLICY_CANDIDATE.frozen_at.isoformat()
    )


def test_sealer_binds_exact_v2_multi_source_and_counterfactual_provider_model() -> None:
    import json

    pair = _sealed_pair()
    payload = json.loads(pair.decision.canonical_payload_json)

    assert payload["evidence_kind"] == "HISTORICAL_REPLAY_OBSERVED"
    assert payload["source_lineage"]["source_receipt_sha256"] == (
        phase22_v2_holdout_source_receipt_sha256()
    )
    assert payload["source_lineage"]["collector_git_shas"] == list(
        sorted({item.collector_git_sha for item in V2_SOURCE_BINDINGS})
    )
    assert payload["historical_provider_terms_claimed"] is False
    assert payload["historical_broker_fills_claimed"] is False
    assert payload["outcome_present"] is False
    assert payload["provider_model_sha256"] == (
        PHASE22_PROVIDER_EXECUTION_CALIBRATION_RECEIPT.fingerprint()
    )
    candidate = payload["candidates"][0]
    assert candidate["provider_time_semantics"] == (
        "CURRENT_EMPIRICAL_COUNTERFACTUAL_MODEL_NOT_HISTORICAL_TERMS"
    )


def test_sealed_pair_is_structurally_consumable_by_qualification_readiness() -> None:
    pair = _sealed_pair()
    book = VersionedPhase22HistoricalReplayEvidenceBook(
        generation=1,
        amendment_sha256="sha256:" + "a" * 64,
        decisions=(pair.decision,),
        outcomes=(),
        source_receipt_sha256=phase22_v2_holdout_source_receipt_sha256(),
        source_collector_git_shas=tuple(
            sorted({item.collector_git_sha for item in V2_SOURCE_BINDINGS})
        ),
    )
    policy_book = VersionedPhase20ForwardPolicyBook(
        generation=1,
        decisions=(pair.policy,),
    )

    readiness = assess_phase20d_qualification_readiness(
        evidence_book=book,
        policy_book=policy_book,
    )

    assert readiness.ready is False
    assert readiness.decision_epochs == 1
    assert readiness.candidate_instances == 1
    assert readiness.pre_freeze_decisions == 0
    assert readiness.missing_policy_decisions == 0