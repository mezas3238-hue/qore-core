from dataclasses import replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path

import pytest

from qore.infrastructure.account_wide_risk import TraderLineage
from qore.infrastructure.cibo_account_capital_mission import (
    CiboAccountCapitalIdentity,
    derive_cibo_capital_mission,
)
from qore.infrastructure.cibo_capital_management_authority import (
    TraderOpportunityEnvelope,
)
from qore.infrastructure.cibo_ce2i_causal_expectation import (
    CausalExpectationBasis,
    CausalOpportunityExpectation,
)
from qore.infrastructure.cibo_ce2i_opportunity_competition import (
    CapitalOpportunityCandidate,
)
from qore.infrastructure.cibo_ce2i_phase20_forward_evidence import (
    Phase20ForwardCandidateEvidence,
    Phase20ForwardDecisionEvidence,
    Phase20ForwardEvidenceKind,
    Phase20ForwardOutcomeEvidence,
    Phase20ForwardPopulationDisposition,
    Phase20ForwardPopulationSlotEvidence,
    Phase20PolicyCandidateLineage,
    phase20_forward_evidence_sha256,
)
from qore.infrastructure.cibo_ce2i_phase20_forward_store import (
    DurablePhase20ForwardEvidenceError,
    DurablePhase20ForwardEvidenceStore,
)
from qore.infrastructure.cibo_ce2i_phase20_policy_candidate import (
    FROZEN_PHASE20_POLICY_CANDIDATE,
)
from qore.infrastructure.cibo_ce2i_regime_selector import (
    CiboCapitalRegimeState,
    CorrelationState,
    LiquidityState,
    ProviderCondition,
    VolatilityState,
)
from qore.infrastructure.cibo_provider_economic_normalization import (
    ProviderEconomicObservation,
)
from qore.infrastructure.market_test_environment import MarketRuntimeEnvironment

NOW = datetime(2026, 9, 27, 14, 5, tzinfo=UTC)


def _decision(
    *,
    kind: Phase20ForwardEvidenceKind = Phase20ForwardEvidenceKind.FORWARD_OBSERVED,
) -> Phase20ForwardDecisionEvidence:
    account = CiboAccountCapitalIdentity(
        provider_key="ctrader-demo",
        account_ref="phase20d-store-contract",
        environment=MarketRuntimeEnvironment.DEMO,
    )
    opportunity = TraderOpportunityEnvelope(
        trader_id=TraderLineage.R43_GBPUSD,
        signal_fingerprint="store-signal-1",
        qore_symbol="GBPUSD",
        provider_symbol="GBPUSD",
        side="long",
        entry_type="market",
        intended_entry=Decimal("100"),
        stop_loss=Decimal("99"),
        take_profit=Decimal("102"),
        stop_loss_per_volume=Decimal("11"),
        margin_per_volume=Decimal("10"),
        volume_step=Decimal("1"),
        minimum_volume=Decimal("1"),
        maximum_volume=Decimal("10"),
    )
    provider = ProviderEconomicObservation(
        provider_key="ctrader-demo",
        qore_symbol="GBPUSD",
        provider_symbol="GBPUSD",
        bid=Decimal("100"),
        ask=Decimal("100.1"),
        contract_size=Decimal("100000"),
        tick_size=Decimal("0.1"),
        tick_value=Decimal("1"),
        minimum_volume=Decimal("1"),
        maximum_volume=Decimal("10"),
        volume_step=Decimal("1"),
        margin_per_volume=Decimal("10"),
        commission_per_volume_usd=Decimal("0"),
        slippage_reserve_per_volume_usd=Decimal("0"),
        observed_at=NOW - timedelta(seconds=1),
    )
    expectation = CausalOpportunityExpectation(
        evidence_id="store-expectation-1",
        as_of=NOW - timedelta(seconds=1),
        basis=CausalExpectationBasis.CURRENT_STATE_FORECAST,
        expected_net_value_usd=Decimal("5"),
        expected_capital_minutes=Decimal("10"),
    )
    candidate = CapitalOpportunityCandidate(
        signal_fingerprint=opportunity.signal_fingerprint,
        trader_id=opportunity.trader_id,
        qore_symbol=opportunity.qore_symbol,
        provider_symbol=opportunity.provider_symbol,
        decision_as_of=NOW,
        expectation=expectation,
        stop_risk_usd=Decimal("11"),
        margin_usd=Decimal("10"),
        concentration_group="GBPUSD",
        concentration_risk_usd=Decimal("11"),
    )
    frozen = FROZEN_PHASE20_POLICY_CANDIDATE
    return Phase20ForwardDecisionEvidence(
        evidence_id="store-decision-1",
        decision_epoch_id="store-epoch-1",
        evidence_kind=kind,
        decision_at=NOW,
        lineage=Phase20PolicyCandidateLineage(
            candidate_id=frozen.candidate_id,
            code_sha=frozen.code_sha,
            parameter_sha256=frozen.parameter_sha256(),
            frozen_at=frozen.frozen_at,
        ),
        account_identity=account,
        mission=derive_cibo_capital_mission(account),
        capital_snapshot_id="capital-1",
        capital_snapshot_observed_at=NOW - timedelta(seconds=1),
        risk_snapshot_id="risk-1",
        risk_snapshot_observed_at=NOW - timedelta(seconds=1),
        hard_risk_headroom_usd=Decimal("20"),
        margin_headroom_usd=Decimal("100"),
        concentration_limit_by_group=(("GBPUSD", Decimal("20")),),
        regime_state=CiboCapitalRegimeState(
            liquidity=LiquidityState.NORMAL,
            volatility=VolatilityState.NORMAL,
            correlation=CorrelationState.NORMAL,
            provider_condition=ProviderCondition.HEALTHY,
            risk_utilization=Decimal("0.20"),
            margin_utilization=Decimal("0.20"),
            drawdown_utilization=Decimal("0.10"),
            opportunity_count=1,
        ),
        current_step=0,
        horizon_steps=frozen.mpc_horizon_steps,
        population_slots=(
            Phase20ForwardPopulationSlotEvidence(
                slot_id="R43_GBPUSD|GBPUSD|store-epoch-1",
                trader_id=TraderLineage.R43_GBPUSD,
                qore_symbol="GBPUSD",
                observed_at=NOW - timedelta(milliseconds=1),
                disposition=Phase20ForwardPopulationDisposition.CANDIDATE,
                reason="synthetic candidate fixture",
                signal_fingerprint="store-signal-1",
            ),
        ),
        candidates=(
            Phase20ForwardCandidateEvidence(
                provider_evidence_id="provider-1",
                opportunity=opportunity,
                provider_observation=provider,
                candidate=candidate,
            ),
        ),
    )


def _outcome(
    decision: Phase20ForwardDecisionEvidence,
    *,
    value: str = "1.5",
) -> Phase20ForwardOutcomeEvidence:
    return Phase20ForwardOutcomeEvidence(
        evidence_id="store-outcome-1",
        decision_evidence_sha256=phase20_forward_evidence_sha256(decision),
        signal_fingerprint="store-signal-1",
        position_id=77,
        execution_risk_evidence_id="store-risk-77",
        settlement_deal_ids=(7001,),
        fill_evidence_refs=("store-fill-1",),
        observed_at=NOW + timedelta(hours=1),
        realized_net_pnl_usd=Decimal(value) * Decimal("10"),
        executed_initial_stop_risk_usd=Decimal("10"),
        realized_structural_outcome_r=Decimal(value),
        outcome_reconciled=True,
    )


def test_forward_store_survives_restart_with_decision_and_outcome(
    tmp_path: Path,
) -> None:
    path = tmp_path / "phase20-forward.json"
    store = DurablePhase20ForwardEvidenceStore(path)
    decision = _decision()
    first = store.seal_decision(decision, expected_generation=0)
    second = store.append_outcome(
        _outcome(decision),
        expected_generation=first.generation,
    )

    restarted = DurablePhase20ForwardEvidenceStore(path).load()

    assert second.generation == 2
    assert restarted == second
    assert len(restarted.decisions) == 1
    assert len(restarted.outcomes) == 1


def test_forward_store_persists_physical_seal_timing(tmp_path: Path) -> None:
    sealed_at = NOW + timedelta(seconds=1)
    deadline_at = NOW + timedelta(seconds=2)
    path = tmp_path / "phase20-forward-timing.json"
    store = DurablePhase20ForwardEvidenceStore(
        path,
        clock=lambda: sealed_at,
    )

    book = store.seal_decision(
        _decision(),
        expected_generation=0,
        seal_deadline_at=deadline_at,
    )
    seal = book.decisions[0]

    assert seal.sealed_at == sealed_at
    assert seal.seal_deadline_at == deadline_at
    assert seal.sealed_within_deadline is True
    assert DurablePhase20ForwardEvidenceStore(path).load() == book


def test_forward_store_incomplete_completion_witness_fails_closed(
    tmp_path: Path,
) -> None:
    path = tmp_path / "phase20-forward-incomplete-seal.json"
    store = DurablePhase20ForwardEvidenceStore(
        path,
        clock=lambda: datetime(2026, 9, 27, 14, 5),
    )

    with pytest.raises(
        DurablePhase20ForwardEvidenceError,
        match="physical seal timestamp must be timezone-aware",
    ):
        store.seal_decision(
            _decision(),
            expected_generation=0,
            seal_deadline_at=NOW + timedelta(seconds=2),
        )

    persisted = DurablePhase20ForwardEvidenceStore(path).load()
    assert persisted.generation == 1
    assert len(persisted.decisions) == 1
    assert persisted.decisions[0].sealed_at is None
    assert persisted.decisions[0].sealed_within_deadline is False


def test_forward_store_rejects_synthetic_decision(tmp_path: Path) -> None:
    store = DurablePhase20ForwardEvidenceStore(tmp_path / "forward.json")
    with pytest.raises(
        DurablePhase20ForwardEvidenceError,
        match="FORWARD_OBSERVED",
    ):
        store.seal_decision(
            _decision(kind=Phase20ForwardEvidenceKind.SYNTHETIC_CONTRACT),
            expected_generation=0,
        )


def test_forward_store_exact_decision_duplicate_is_idempotent(
    tmp_path: Path,
) -> None:
    store = DurablePhase20ForwardEvidenceStore(tmp_path / "forward.json")
    decision = _decision()
    first = store.seal_decision(decision, expected_generation=0)
    duplicate = store.seal_decision(
        decision,
        expected_generation=first.generation,
    )

    assert duplicate.generation == first.generation


def test_forward_store_rejects_decision_rewrite(tmp_path: Path) -> None:
    store = DurablePhase20ForwardEvidenceStore(tmp_path / "forward.json")
    decision = _decision()
    first = store.seal_decision(decision, expected_generation=0)
    changed = replace(decision, capital_snapshot_id="capital-rewritten")

    with pytest.raises(
        DurablePhase20ForwardEvidenceError,
        match="conflicting forward decision rewrite",
    ):
        store.seal_decision(
            changed,
            expected_generation=first.generation,
        )


def test_forward_store_rejects_outcome_without_sealed_decision(
    tmp_path: Path,
) -> None:
    store = DurablePhase20ForwardEvidenceStore(tmp_path / "forward.json")
    decision = _decision()

    with pytest.raises(
        DurablePhase20ForwardEvidenceError,
        match="no sealed decision",
    ):
        store.append_outcome(_outcome(decision), expected_generation=0)


def test_forward_store_rejects_conflicting_outcome_rewrite(
    tmp_path: Path,
) -> None:
    store = DurablePhase20ForwardEvidenceStore(tmp_path / "forward.json")
    decision = _decision()
    first = store.seal_decision(decision, expected_generation=0)
    second = store.append_outcome(
        _outcome(decision),
        expected_generation=first.generation,
    )

    with pytest.raises(
        DurablePhase20ForwardEvidenceError,
        match="already sealed for decision/signal",
    ):
        store.append_outcome(
            replace(
                _outcome(decision, value="-1"),
                evidence_id="store-outcome-2",
            ),
            expected_generation=second.generation,
        )


def test_forward_store_rejects_stale_generation(tmp_path: Path) -> None:
    store = DurablePhase20ForwardEvidenceStore(tmp_path / "forward.json")
    store.seal_decision(_decision(), expected_generation=0)

    with pytest.raises(
        DurablePhase20ForwardEvidenceError,
        match="stale forward evidence generation",
    ):
        store.seal_decision(
            replace(_decision(), evidence_id="store-decision-2"),
            expected_generation=0,
        )


def test_forward_store_corruption_fails_closed(tmp_path: Path) -> None:
    path = tmp_path / "forward.json"
    path.write_text("{not-json", encoding="utf-8")

    with pytest.raises(
        DurablePhase20ForwardEvidenceError,
        match="unreadable",
    ):
        DurablePhase20ForwardEvidenceStore(path).load()

def test_forward_store_rejects_same_epoch_under_different_evidence_id(
    tmp_path: Path,
) -> None:
    store = DurablePhase20ForwardEvidenceStore(tmp_path / "forward.json")
    decision = _decision()
    first = store.seal_decision(decision, expected_generation=0)
    relabelled = replace(decision, evidence_id="store-decision-relabelled")

    with pytest.raises(
        DurablePhase20ForwardEvidenceError,
        match="conflicting forward decision epoch rewrite",
    ):
        store.seal_decision(
            relabelled,
            expected_generation=first.generation,
        )

    assert store.load().generation == 1

