from __future__ import annotations

import json
from datetime import timedelta
from decimal import Decimal

from qore.infrastructure.account_wide_risk import TraderLineage
from qore.infrastructure.cibo_ce2i_phase20_forward_policy_store import (
    Phase20ForwardPolicyDecisionSeal,
    VersionedPhase20ForwardPolicyBook,
)
from qore.infrastructure.cibo_ce2i_phase20_forward_store import (
    Phase20ForwardDecisionSeal,
    Phase20ForwardOutcomeSeal,
    VersionedPhase20ForwardEvidenceBook,
)
from qore.infrastructure.cibo_ce2i_phase20_t13_oos_readiness import (
    assess_phase20_t13_oos_readiness,
)
from qore.infrastructure.cibo_ce2i_phase20_t13_shadow_policy import (
    T13_SHADOW_POLICY_FROZEN_AT,
    t13_shadow_policy_sha256,
)
from qore.infrastructure.cibo_ce2i_phase20_t13_shadow_treatment_store import (
    T13ShadowTreatmentSeal,
)

LINEAGES = tuple(TraderLineage)
BASE = T13_SHADOW_POLICY_FROZEN_AT + timedelta(minutes=5)


def _population(*, omit_treatment_outcome: bool = False):
    decisions = []
    outcomes = []
    policies = []
    treatments = []
    for index in range(80):
        decision_at = BASE + timedelta(hours=9 * index)
        signals = tuple(f"signal-{index}-{slot}" for slot in range(3))
        candidates = []
        for slot, signal in enumerate(signals):
            lineage = LINEAGES[(index * 3 + slot) % len(LINEAGES)]
            candidates.append(
                {
                    "candidate": {
                        "signal_fingerprint": signal,
                        "trader_id": lineage.value,
                    }
                }
            )
        payload = {
            "evidence_kind": "FORWARD_OBSERVED",
            "candidates": candidates,
        }
        evidence_sha = "sha256:" + f"{index + 1:064x}"
        decisions.append(
            Phase20ForwardDecisionSeal(
                evidence_id=f"decision-{index}",
                decision_epoch_id=f"epoch-{index}",
                evidence_sha256=evidence_sha,
                decision_at=decision_at,
                candidate_id="phase20-candidate",
                code_sha="a" * 40,
                parameter_sha256="sha256:" + ("b" * 64),
                signal_fingerprints=signals,
                canonical_payload_json=json.dumps(payload, sort_keys=True),
                collector_git_sha="c" * 40,
                sealed_at=decision_at + timedelta(milliseconds=100),
                seal_deadline_at=decision_at + timedelta(seconds=2),
            )
        )
        baseline_sha = "sha256:" + f"{1000 + index:064x}"
        policies.append(
            Phase20ForwardPolicyDecisionSeal(
                evidence_sha256=evidence_sha,
                policy_record_sha256=baseline_sha,
                allocator_disposition="ALLOCATE",
                selected_signal_fingerprints=(signals[0],),
                canonical_record_json="{}",
            )
        )
        changed = index < 20
        treatment_selected = (signals[1],) if changed else (signals[0],)
        treatments.append(
            T13ShadowTreatmentSeal(
                treatment_sha256="sha256:" + f"{2000 + index:064x}",
                recommendation_sha256=(
                    "sha256:" + f"{3000 + index:064x}"
                ),
                decision_epoch_id=f"epoch-{index}",
                decision_evidence_sha256=evidence_sha,
                baseline_policy_record_sha256=baseline_sha,
                t13_policy_sha256=t13_shadow_policy_sha256(),
                decision_at=decision_at,
                treatment_sealed_at=(
                    decision_at + timedelta(milliseconds=500)
                ),
                reserve_triggered=changed,
                shadow_reserved_risk_usd=(
                    Decimal("10") if changed else Decimal("0")
                ),
                baseline_allocator_input_stop_risk_usd=Decimal("20"),
                treatment_allocator_input_stop_risk_usd=(
                    Decimal("10") if changed else Decimal("20")
                ),
                allocator_input_margin_usd=Decimal("100"),
                baseline_selected_signal_fingerprints=(signals[0],),
                treatment_selected_signal_fingerprints=treatment_selected,
                baseline_only_signal_fingerprints=(
                    (signals[0],) if changed else ()
                ),
                treatment_only_signal_fingerprints=(
                    (signals[1],) if changed else ()
                ),
                selection_changed=changed,
            )
        )
        for slot, signal in enumerate(signals):
            if (
                omit_treatment_outcome
                and index == 0
                and slot == 1
            ):
                continue
            risk = Decimal("5")
            pnl = Decimal(str(slot - 1))
            outcomes.append(
                Phase20ForwardOutcomeSeal(
                    evidence_id=f"outcome-{index}-{slot}",
                    decision_evidence_sha256=evidence_sha,
                    signal_fingerprint=signal,
                    position_id=index * 10 + slot + 1,
                    execution_risk_evidence_id=f"risk-{index}-{slot}",
                    settlement_deal_ids=(10000 + index * 10 + slot,),
                    fill_evidence_refs=(f"fill-{index}-{slot}",),
                    observed_at=decision_at + timedelta(hours=1),
                    realized_net_pnl_usd=pnl,
                    executed_initial_stop_risk_usd=risk,
                    realized_structural_outcome_r=pnl / risk,
                )
            )
    return (
        VersionedPhase20ForwardEvidenceBook(
            generation=len(decisions) + len(outcomes),
            decisions=tuple(decisions),
            outcomes=tuple(outcomes),
        ),
        VersionedPhase20ForwardPolicyBook(
            generation=len(policies),
            decisions=tuple(policies),
        ),
        tuple(treatments),
    )


def test_t13_oos_readiness_uses_frozen_phase20_thresholds() -> None:
    evidence, policies, treatments = _population()

    audit = assess_phase20_t13_oos_readiness(
        evidence_book=evidence,
        baseline_policy_book=policies,
        treatment_decisions=treatments,
    )

    assert audit.ready_for_utility_analysis is True
    assert audit.blockers == ()
    assert audit.post_freeze_decision_epochs == 80
    assert audit.candidate_instances == 240
    assert audit.candidate_outcomes == 240
    assert audit.baseline_selected_outcomes == 80
    assert audit.treatment_selected_outcomes == 80
    assert audit.selection_changed_epochs == 20
    assert audit.baseline_only_instances == 20
    assert audit.treatment_only_instances == 20
    assert audit.candidate_outcome_coverage == Decimal("1")
    assert audit.baseline_selected_outcome_coverage == Decimal("1")
    assert audit.treatment_selected_outcome_coverage == Decimal("1")
    assert audit.represented_lineages == 7
    assert audit.minimum_fold_candidate_outcomes >= 40
    assert audit.minimum_fold_lineages >= 4
    assert audit.fresh_oos_utility_demonstrated is False


def test_t13_oos_readiness_fails_if_treatment_only_outcome_missing() -> None:
    evidence, policies, treatments = _population(
        omit_treatment_outcome=True
    )

    audit = assess_phase20_t13_oos_readiness(
        evidence_book=evidence,
        baseline_policy_book=policies,
        treatment_decisions=treatments,
    )

    assert audit.ready_for_utility_analysis is False
    assert audit.treatment_only_instances == 20
    assert audit.treatment_only_outcomes == 19
    assert (
        "T13_TREATMENT_SELECTED_OUTCOME_COVERAGE_NOT_MET"
        in audit.blockers
    )


def test_t13_oos_readiness_rejects_selective_treatment_sampling() -> None:
    evidence, policies, treatments = _population()

    audit = assess_phase20_t13_oos_readiness(
        evidence_book=evidence,
        baseline_policy_book=policies,
        treatment_decisions=treatments[:-1],
    )

    assert audit.ready_for_utility_analysis is False
    assert audit.missing_treatment_decisions == 1
    assert "T13_MISSING_SHADOW_TREATMENT_DECISIONS" in audit.blockers


def test_t13_oos_readiness_excludes_pre_policy_freeze_decision() -> None:
    evidence, policies, treatments = _population()
    decision_at = T13_SHADOW_POLICY_FROZEN_AT - timedelta(minutes=1)
    payload = {
        "evidence_kind": "FORWARD_OBSERVED",
        "candidates": [
            {
                "candidate": {
                    "signal_fingerprint": "pre-signal",
                    "trader_id": LINEAGES[0].value,
                }
            }
        ],
    }
    pre = Phase20ForwardDecisionSeal(
        evidence_id="pre-decision",
        decision_epoch_id="pre-epoch",
        evidence_sha256="sha256:" + ("f" * 64),
        decision_at=decision_at,
        candidate_id="phase20-candidate",
        code_sha="a" * 40,
        parameter_sha256="sha256:" + ("b" * 64),
        signal_fingerprints=("pre-signal",),
        canonical_payload_json=json.dumps(payload, sort_keys=True),
        collector_git_sha="c" * 40,
        sealed_at=decision_at + timedelta(milliseconds=100),
        seal_deadline_at=decision_at + timedelta(seconds=2),
    )
    expanded = VersionedPhase20ForwardEvidenceBook(
        generation=evidence.generation + 1,
        decisions=(pre,) + evidence.decisions,
        outcomes=evidence.outcomes,
    )

    audit = assess_phase20_t13_oos_readiness(
        evidence_book=expanded,
        baseline_policy_book=policies,
        treatment_decisions=treatments,
    )

    assert audit.ready_for_utility_analysis is True
    assert audit.pre_t13_freeze_decisions_excluded == 1
