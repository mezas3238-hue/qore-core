from datetime import timedelta
from decimal import Decimal
from pathlib import Path

from qore.infrastructure.account_wide_risk import TraderLineage
from qore.infrastructure.cibo_account_capital_mission import (
    CiboAccountCapitalIdentity,
    derive_cibo_capital_mission,
)
from qore.infrastructure.cibo_ce2i_advanced_evidence import (
    build_missing_advanced_evidence_snapshot,
)
from qore.infrastructure.cibo_ce2i_phase20_forward_evidence import (
    Phase20ForwardDecisionEvidence,
    Phase20ForwardEvidenceKind,
    Phase20ForwardPopulationDisposition,
    Phase20ForwardPopulationSlotEvidence,
    Phase20PolicyCandidateLineage,
    build_phase20_forward_decision_record,
    phase20_forward_decision_record_json,
    phase20_forward_decision_record_sha256,
    phase20_forward_evidence_json,
    phase20_forward_evidence_sha256,
)
from qore.infrastructure.cibo_ce2i_phase20_forward_policy_store import (
    Phase20ForwardPolicyDecisionSeal,
    VersionedPhase20ForwardPolicyBook,
)
from qore.infrastructure.cibo_ce2i_phase20_forward_store import (
    Phase20ForwardDecisionSeal,
    VersionedPhase20ForwardEvidenceBook,
)
from qore.infrastructure.cibo_ce2i_phase20_policy_candidate import (
    FROZEN_PHASE20_POLICY_CANDIDATE,
)
from qore.infrastructure.cibo_ce2i_phase20_t13_runtime_shadow import (
    seal_phase20_t13_runtime_shadow,
)
from qore.infrastructure.cibo_ce2i_phase20_t13_shadow_policy import (
    T13_SHADOW_POLICY_FROZEN_AT,
)
from qore.infrastructure.cibo_ce2i_phase20_t13_shadow_store import (
    DurableT13ShadowDecisionStore,
)
from qore.infrastructure.cibo_ce2i_phase20_t13_shadow_treatment_store import (
    DurableT13ShadowTreatmentStore,
)
from qore.infrastructure.cibo_ce2i_regime_selector import (
    CiboCapitalRegimeState,
    CorrelationState,
    LiquidityState,
    ProviderCondition,
    VolatilityState,
)
from qore.infrastructure.market_test_environment import MarketRuntimeEnvironment

DECISION_AT = T13_SHADOW_POLICY_FROZEN_AT + timedelta(minutes=5)


def _evidence() -> Phase20ForwardDecisionEvidence:
    account = CiboAccountCapitalIdentity(
        provider_key="ctrader-demo",
        account_ref="t13-runtime-shadow",
        environment=MarketRuntimeEnvironment.DEMO,
    )
    frozen = FROZEN_PHASE20_POLICY_CANDIDATE
    lineage = Phase20PolicyCandidateLineage(
        candidate_id=frozen.candidate_id,
        code_sha=frozen.code_sha,
        parameter_sha256=frozen.parameter_sha256(),
        frozen_at=frozen.frozen_at,
    )
    return Phase20ForwardDecisionEvidence(
        evidence_id="t13-runtime-evidence",
        decision_epoch_id="t13-runtime-epoch",
        evidence_kind=Phase20ForwardEvidenceKind.FORWARD_OBSERVED,
        decision_at=DECISION_AT,
        lineage=lineage,
        account_identity=account,
        mission=derive_cibo_capital_mission(account),
        capital_snapshot_id="capital-1",
        capital_snapshot_observed_at=DECISION_AT - timedelta(seconds=1),
        risk_snapshot_id="risk-1",
        risk_snapshot_observed_at=DECISION_AT - timedelta(seconds=1),
        hard_risk_headroom_usd=Decimal("20"),
        margin_headroom_usd=Decimal("100"),
        concentration_limit_by_group=(),
        regime_state=CiboCapitalRegimeState(
            liquidity=LiquidityState.NORMAL,
            volatility=VolatilityState.NORMAL,
            correlation=CorrelationState.NORMAL,
            provider_condition=ProviderCondition.HEALTHY,
            risk_utilization=Decimal("0.10"),
            margin_utilization=Decimal("0.10"),
            drawdown_utilization=Decimal("0"),
            opportunity_count=0,
        ),
        current_step=0,
        horizon_steps=frozen.mpc_horizon_steps,
        population_slots=(
            Phase20ForwardPopulationSlotEvidence(
                slot_id="VT31_NAS100|NAS100|t13-runtime-epoch",
                trader_id=TraderLineage.VT31_NAS100,
                qore_symbol="NAS100",
                observed_at=DECISION_AT - timedelta(milliseconds=1),
                disposition=Phase20ForwardPopulationDisposition.ABSTAIN,
                reason="CAUSAL_ABSTAIN",
            ),
        ),
        candidates=(),
        known_options=(),
        advanced_evidence_snapshot=(
            build_missing_advanced_evidence_snapshot(
                decision_at=DECISION_AT,
            )
        ),
    )


def _books():
    evidence = _evidence()
    record = build_phase20_forward_decision_record(evidence)
    evidence_sha = phase20_forward_evidence_sha256(evidence)
    decision = Phase20ForwardDecisionSeal(
        evidence_id=evidence.evidence_id,
        decision_epoch_id=evidence.decision_epoch_id,
        evidence_sha256=evidence_sha,
        decision_at=evidence.decision_at,
        candidate_id=evidence.lineage.candidate_id,
        code_sha=evidence.lineage.code_sha,
        parameter_sha256=evidence.lineage.parameter_sha256,
        signal_fingerprints=(),
        canonical_payload_json=phase20_forward_evidence_json(evidence),
        collector_git_sha="d" * 40,
        sealed_at=DECISION_AT + timedelta(milliseconds=100),
        seal_deadline_at=DECISION_AT + timedelta(seconds=2),
    )
    evidence_book = VersionedPhase20ForwardEvidenceBook(
        generation=1,
        decisions=(decision,),
    )
    allocation = record.allocator_decision.allocation
    selected = (
        ()
        if allocation is None
        else allocation.selected_signal_fingerprints
    )
    policy = Phase20ForwardPolicyDecisionSeal(
        evidence_sha256=evidence_sha,
        policy_record_sha256=phase20_forward_decision_record_sha256(record),
        allocator_disposition=record.allocator_decision.disposition.value,
        selected_signal_fingerprints=selected,
        canonical_record_json=phase20_forward_decision_record_json(record),
    )
    policy_book = VersionedPhase20ForwardPolicyBook(
        generation=1,
        decisions=(policy,),
    )
    return evidence, record, evidence_book, policy_book


def test_runtime_shadow_seals_both_t13_ledgers_pre_outcome(
    tmp_path: Path,
) -> None:
    evidence, record, evidence_book, policy_book = _books()
    recommendation_store = DurableT13ShadowDecisionStore(
        tmp_path / "recommendation.json",
        clock=lambda: DECISION_AT + timedelta(milliseconds=500),
    )
    treatment_store = DurableT13ShadowTreatmentStore(
        tmp_path / "treatment.json",
        clock=lambda: DECISION_AT + timedelta(seconds=1),
    )

    sealed = seal_phase20_t13_runtime_shadow(
        evidence=evidence,
        decision_record=record,
        evidence_book=evidence_book,
        policy_book=policy_book,
        recommendation_store=recommendation_store,
        treatment_store=treatment_store,
    )

    assert sealed is not None
    assert sealed.recommendation_generation == 1
    assert sealed.treatment_generation == 1
    assert sealed.reserve_triggered is False
    assert sealed.reserved_risk_usd == Decimal("0")
    assert sealed.selection_changed is False
    assert sealed.broker_mutation_performed is False
    assert sealed.runtime_authority is False
    assert recommendation_store.load().generation == 1
    assert treatment_store.load().generation == 1


def test_runtime_shadow_is_idempotent_after_complete_chain(
    tmp_path: Path,
) -> None:
    evidence, record, evidence_book, policy_book = _books()
    recommendation_store = DurableT13ShadowDecisionStore(
        tmp_path / "recommendation.json",
        clock=lambda: DECISION_AT + timedelta(milliseconds=500),
    )
    treatment_store = DurableT13ShadowTreatmentStore(
        tmp_path / "treatment.json",
        clock=lambda: DECISION_AT + timedelta(seconds=1),
    )
    first = seal_phase20_t13_runtime_shadow(
        evidence=evidence,
        decision_record=record,
        evidence_book=evidence_book,
        policy_book=policy_book,
        recommendation_store=recommendation_store,
        treatment_store=treatment_store,
    )
    second = seal_phase20_t13_runtime_shadow(
        evidence=evidence,
        decision_record=record,
        evidence_book=evidence_book,
        policy_book=policy_book,
        recommendation_store=recommendation_store,
        treatment_store=treatment_store,
    )

    assert first == second
    assert recommendation_store.load().generation == 1
    assert treatment_store.load().generation == 1
