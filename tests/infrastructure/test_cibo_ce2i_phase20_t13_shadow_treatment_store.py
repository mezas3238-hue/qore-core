from __future__ import annotations

import json
from datetime import timedelta
from decimal import Decimal

import pytest

from qore.infrastructure.cibo_ce2i_phase20_forward_policy_store import (
    Phase20ForwardPolicyDecisionSeal,
    VersionedPhase20ForwardPolicyBook,
)
from qore.infrastructure.cibo_ce2i_phase20_forward_store import (
    Phase20ForwardDecisionSeal,
    Phase20ForwardOutcomeSeal,
    VersionedPhase20ForwardEvidenceBook,
)
from qore.infrastructure.cibo_ce2i_phase20_robust_allocator import (
    Phase20AllocatorDisposition,
    Phase20RobustAllocatorDecision,
)
from qore.infrastructure.cibo_ce2i_phase20_t13_shadow_policy import (
    T13_SHADOW_POLICY_FROZEN_AT,
    Phase20T13ShadowRecommendation,
    t13_shadow_policy_sha256,
)
from qore.infrastructure.cibo_ce2i_phase20_t13_shadow_store import (
    DurableT13ShadowDecisionStore,
)
from qore.infrastructure.cibo_ce2i_phase20_t13_shadow_treatment import (
    Phase20T13ShadowTreatmentDecision,
)
from qore.infrastructure.cibo_ce2i_phase20_t13_shadow_treatment_store import (
    DurableT13ShadowTreatmentError,
    DurableT13ShadowTreatmentStore,
)
from qore.infrastructure.cibo_ce2i_regime_selector import CiboRegimePosture

DECISION_AT = T13_SHADOW_POLICY_FROZEN_AT + timedelta(minutes=5)
EVIDENCE_SHA = "sha256:" + ("1" * 64)
BASELINE_SHA = "sha256:" + ("2" * 64)


def _evidence_book(
    *,
    with_outcome: bool = False,
) -> VersionedPhase20ForwardEvidenceBook:
    payload = {
        "evidence_kind": "FORWARD_OBSERVED",
        "hard_risk_headroom_usd": "20",
        "candidates": [],
    }
    decision = Phase20ForwardDecisionSeal(
        evidence_id="decision-1",
        decision_epoch_id="epoch-1",
        evidence_sha256=EVIDENCE_SHA,
        decision_at=DECISION_AT,
        candidate_id="phase20-candidate",
        code_sha="a" * 40,
        parameter_sha256="sha256:" + ("b" * 64),
        signal_fingerprints=("signal-1",),
        canonical_payload_json=json.dumps(payload, sort_keys=True),
        collector_git_sha="c" * 40,
        sealed_at=DECISION_AT + timedelta(milliseconds=100),
        seal_deadline_at=DECISION_AT + timedelta(seconds=2),
    )
    outcomes = ()
    if with_outcome:
        outcomes = (
            Phase20ForwardOutcomeSeal(
                evidence_id="outcome-1",
                decision_evidence_sha256=EVIDENCE_SHA,
                signal_fingerprint="signal-1",
                position_id=1,
                execution_risk_evidence_id="risk-1",
                settlement_deal_ids=(7001,),
                fill_evidence_refs=("fill-1",),
                observed_at=DECISION_AT + timedelta(minutes=10),
                realized_net_pnl_usd=Decimal("-2"),
                executed_initial_stop_risk_usd=Decimal("5"),
                realized_structural_outcome_r=Decimal("-0.4"),
            ),
        )
    return VersionedPhase20ForwardEvidenceBook(
        generation=1 + len(outcomes),
        decisions=(decision,),
        outcomes=outcomes,
    )


def _policy_book() -> VersionedPhase20ForwardPolicyBook:
    seal = Phase20ForwardPolicyDecisionSeal(
        evidence_sha256=EVIDENCE_SHA,
        policy_record_sha256=BASELINE_SHA,
        allocator_disposition="ALLOCATE",
        selected_signal_fingerprints=("signal-1",),
        canonical_record_json="{}",
    )
    return VersionedPhase20ForwardPolicyBook(
        generation=1,
        decisions=(seal,),
    )


def _recommendation() -> Phase20T13ShadowRecommendation:
    return Phase20T13ShadowRecommendation(
        policy_id="CIBO_T13_ONE_MINIMUM_SEED_RESERVE_SHADOW_V1",
        policy_sha256=t13_shadow_policy_sha256(),
        decision_epoch_id="epoch-1",
        decision_evidence_sha256=EVIDENCE_SHA,
        decision_at=DECISION_AT,
        causal_pressure_active=True,
        arrival_evidence_available=True,
        reserve_triggered=True,
        reserved_risk_usd=Decimal("10"),
        minimum_seed_risk_usd=Decimal("10"),
        hard_risk_headroom_usd=Decimal("20"),
        full_seed_preserved=True,
        source_decision_sha256s=("sha256:" + ("3" * 64),),
        source_outcome_evidence_ids=("prior-outcome",),
    )


def _recommendation_book(tmp_path):
    book = _evidence_book()
    store = DurableT13ShadowDecisionStore(
        tmp_path / "recommendation.json",
        clock=lambda: DECISION_AT + timedelta(milliseconds=500),
    )
    return store.seal_recommendation(
        _recommendation(),
        evidence_book=book,
        expected_generation=0,
    )


def _treatment() -> Phase20T13ShadowTreatmentDecision:
    allocator = Phase20RobustAllocatorDecision(
        candidate_id="PHASE20H_ROBUST_CONSTRAINED_ALLOCATOR_V1",
        disposition=Phase20AllocatorDisposition.NO_ELIGIBLE_ALLOCATION,
        regime_posture=CiboRegimePosture.STABLE,
        applied_tools=("T15",),
        reserve_stop_risk_usd=Decimal("0"),
        reserve_margin_usd=Decimal("0"),
        deployable_stop_risk_usd=Decimal("10"),
        deployable_margin_usd=Decimal("100"),
        reserved_for_opportunity_ids=(),
        allocation=None,
        reason="shadow treatment fixture",
    )
    return Phase20T13ShadowTreatmentDecision(
        decision_epoch_id="epoch-1",
        decision_evidence_sha256=EVIDENCE_SHA,
        baseline_policy_record_sha256=BASELINE_SHA,
        t13_policy_sha256=t13_shadow_policy_sha256(),
        reserve_triggered=True,
        shadow_reserved_risk_usd=Decimal("10"),
        baseline_allocator_input_stop_risk_usd=Decimal("20"),
        treatment_allocator_input_stop_risk_usd=Decimal("10"),
        allocator_input_margin_usd=Decimal("100"),
        baseline_selected_signal_fingerprints=("signal-1",),
        treatment_selected_signal_fingerprints=(),
        baseline_only_signal_fingerprints=("signal-1",),
        treatment_only_signal_fingerprints=(),
        treatment_allocator=allocator,
        selection_changed=True,
        outcome_aware=False,
        runtime_authority=False,
    )


def test_t13_treatment_store_seals_after_prerequisites(tmp_path) -> None:
    recommendation_book = _recommendation_book(tmp_path)
    store = DurableT13ShadowTreatmentStore(
        tmp_path / "treatment.json",
        clock=lambda: DECISION_AT + timedelta(seconds=1),
    )

    sealed = store.seal_treatment(
        _treatment(),
        evidence_book=_evidence_book(),
        baseline_policy_book=_policy_book(),
        recommendation_book=recommendation_book,
        expected_generation=0,
    )

    assert sealed.generation == 1
    assert sealed.chain_sha256.startswith("sha256:")
    assert len(sealed.decisions) == 1
    assert sealed.decisions[0].treatment_selected_signal_fingerprints == ()
    assert sealed.decisions[0].baseline_only_signal_fingerprints == (
        "signal-1",
    )
    assert store.load() == sealed


def test_t13_treatment_store_rejects_after_outcome(tmp_path) -> None:
    recommendation_book = _recommendation_book(tmp_path)
    store = DurableT13ShadowTreatmentStore(
        tmp_path / "treatment.json",
        clock=lambda: DECISION_AT + timedelta(seconds=1),
    )

    with pytest.raises(
        DurableT13ShadowTreatmentError,
        match="cannot seal after outcome exists",
    ):
        store.seal_treatment(
            _treatment(),
            evidence_book=_evidence_book(with_outcome=True),
            baseline_policy_book=_policy_book(),
            recommendation_book=recommendation_book,
            expected_generation=0,
        )


def test_t13_treatment_store_requires_prior_recommendation(tmp_path) -> None:
    store = DurableT13ShadowTreatmentStore(
        tmp_path / "treatment.json",
        clock=lambda: DECISION_AT + timedelta(seconds=1),
    )
    empty_recommendations = _recommendation_book(tmp_path)
    empty_recommendations = type(empty_recommendations)(
        generation=0,
        records=(),
    )

    with pytest.raises(
        DurableT13ShadowTreatmentError,
        match="requires prior recommendation seal",
    ):
        store.seal_treatment(
            _treatment(),
            evidence_book=_evidence_book(),
            baseline_policy_book=_policy_book(),
            recommendation_book=empty_recommendations,
            expected_generation=0,
        )


def test_t13_treatment_store_rejects_late_seal(tmp_path) -> None:
    recommendation_book = _recommendation_book(tmp_path)
    store = DurableT13ShadowTreatmentStore(
        tmp_path / "treatment.json",
        clock=lambda: DECISION_AT + timedelta(seconds=3),
    )

    with pytest.raises(
        DurableT13ShadowTreatmentError,
        match="exceeds frozen two-second window",
    ):
        store.seal_treatment(
            _treatment(),
            evidence_book=_evidence_book(),
            baseline_policy_book=_policy_book(),
            recommendation_book=recommendation_book,
            expected_generation=0,
        )


def test_t13_treatment_store_detects_chain_tampering(tmp_path) -> None:
    recommendation_book = _recommendation_book(tmp_path)
    path = tmp_path / "treatment.json"
    store = DurableT13ShadowTreatmentStore(
        path,
        clock=lambda: DECISION_AT + timedelta(seconds=1),
    )
    store.seal_treatment(
        _treatment(),
        evidence_book=_evidence_book(),
        baseline_policy_book=_policy_book(),
        recommendation_book=recommendation_book,
        expected_generation=0,
    )
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["chain_sha256"] = "sha256:" + ("f" * 64)
    path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(
        DurableT13ShadowTreatmentError,
        match="terminal chain mismatch",
    ):
        store.load()
