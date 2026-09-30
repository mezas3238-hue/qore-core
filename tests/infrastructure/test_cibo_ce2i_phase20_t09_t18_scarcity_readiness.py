from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from qore.infrastructure.cibo_ce2i_phase20_forward_policy_store import (
    Phase20ForwardPolicyDecisionSeal,
    VersionedPhase20ForwardPolicyBook,
)
from qore.infrastructure.cibo_ce2i_phase20_forward_store import (
    Phase20ForwardDecisionSeal,
    Phase20ForwardOutcomeSeal,
    VersionedPhase20ForwardEvidenceBook,
)
from qore.infrastructure.cibo_ce2i_phase20_t09_t18_scarcity_readiness import (
    assess_phase20_t09_t18_scarcity_readiness,
)

BASE = datetime(2026, 9, 28, 5, 0, tzinfo=UTC)


def _population(
    *,
    same_trader: bool = False,
    omit_candidate_outcomes: int = 0,
):
    decisions = []
    outcomes = []
    policies = []
    for index in range(32):
        decision_at = BASE + timedelta(hours=index)
        signals = (f"a-{index}", f"b-{index}")
        traders = (
            "R38_EURUSD",
            "R38_EURUSD" if same_trader else "R43_GBPUSD",
        )
        candidates = [
            {
                "candidate": {
                    "signal_fingerprint": signal,
                    "trader_id": trader,
                    "stop_risk_usd": "5",
                    "margin_usd": "10",
                    "concentration_group": "USD",
                    "concentration_risk_usd": "5",
                }
            }
            for signal, trader in zip(signals, traders, strict=True)
        ]
        payload = {
            "evidence_kind": "FORWARD_OBSERVED",
            "hard_risk_headroom_usd": "5",
            "margin_headroom_usd": "100",
            "concentration_limit_by_group": [["USD", "100"]],
            "candidates": candidates,
        }
        evidence_sha = "sha256:" + f"{index + 1:064x}"
        decisions.append(
            Phase20ForwardDecisionSeal(
                evidence_id=f"decision-{index}",
                decision_epoch_id=f"epoch-{index}",
                evidence_sha256=evidence_sha,
                decision_at=decision_at,
                candidate_id="candidate",
                code_sha="a" * 40,
                parameter_sha256="params",
                signal_fingerprints=signals,
                canonical_payload_json=json.dumps(payload, sort_keys=True),
                collector_git_sha="b" * 40,
                sealed_at=decision_at + timedelta(milliseconds=100),
                seal_deadline_at=decision_at + timedelta(seconds=2),
            )
        )
        canonical = json.dumps(
            {"evidence_sha256": evidence_sha},
            sort_keys=True,
            separators=(",", ":"),
        )
        policies.append(
            Phase20ForwardPolicyDecisionSeal(
                evidence_sha256=evidence_sha,
                policy_record_sha256=(
                    "sha256:"
                    + hashlib.sha256(canonical.encode()).hexdigest()
                ),
                allocator_disposition="ALLOCATE",
                selected_signal_fingerprints=(signals[0],),
                canonical_record_json=canonical,
            )
        )
        for slot, signal in enumerate(signals):
            if (
                slot == 1
                and index < omit_candidate_outcomes
            ):
                continue
            outcomes.append(
                Phase20ForwardOutcomeSeal(
                    evidence_id=f"outcome-{index}-{slot}",
                    decision_evidence_sha256=evidence_sha,
                    signal_fingerprint=signal,
                    position_id=index * 10 + slot + 1,
                    execution_risk_evidence_id=f"risk-{index}-{slot}",
                    settlement_deal_ids=(1000 + index * 10 + slot,),
                    fill_evidence_refs=(f"fill-{index}-{slot}",),
                    observed_at=decision_at + timedelta(minutes=30),
                    realized_net_pnl_usd=Decimal("1"),
                    executed_initial_stop_risk_usd=Decimal("5"),
                    realized_structural_outcome_r=Decimal("0.2"),
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
    )


def test_scarcity_readiness_prepares_t09_and_cross_trader_t18() -> None:
    evidence, policies = _population()

    audit = assess_phase20_t09_t18_scarcity_readiness(
        evidence_book=evidence,
        policy_book=policies,
    )

    assert audit.exact_competition_epochs == 32
    assert audit.scarce_competition_epochs == 32
    assert audit.cross_trader_scarce_epochs == 32
    assert audit.scarcity_candidate_instances == 64
    assert audit.scarcity_candidate_outcomes == 64
    assert audit.scarcity_selected_instances == 32
    assert audit.scarcity_selected_outcomes == 32
    assert audit.scarcity_candidate_outcome_coverage == Decimal("1")
    assert audit.scarcity_selected_outcome_coverage == Decimal("1")
    assert len(audit.t09_folds) == 4
    assert len(audit.t18_folds) == 4
    assert len(audit.t09_scarce_decision_sha256s) == 32
    assert len(audit.t18_cross_trader_scarce_decision_sha256s) == 32
    assert audit.t09_ready_for_utility_analysis is True
    assert audit.t18_ready_for_utility_analysis is True
    assert audit.fresh_oos_utility_demonstrated is False


def test_t18_requires_cross_trader_scarcity() -> None:
    evidence, policies = _population(same_trader=True)

    audit = assess_phase20_t09_t18_scarcity_readiness(
        evidence_book=evidence,
        policy_book=policies,
    )

    assert audit.t09_ready_for_utility_analysis is True
    assert audit.t18_ready_for_utility_analysis is False
    assert audit.cross_trader_scarce_epochs == 0
    assert any(
        item.startswith("T18_FRESH_CROSS_TRADER_SCARCE_EPOCHS_0_OF_30")
        for item in audit.t18_blockers
    )


def test_scarcity_readiness_requires_candidate_coverage_in_folds() -> None:
    evidence, policies = _population(omit_candidate_outcomes=4)

    audit = assess_phase20_t09_t18_scarcity_readiness(
        evidence_book=evidence,
        policy_book=policies,
    )

    assert audit.scarcity_candidate_outcome_coverage == Decimal("0.9375")
    assert audit.t09_ready_for_utility_analysis is False
    assert audit.t18_ready_for_utility_analysis is False
    assert "T09_SCARCITY_CANDIDATE_OUTCOME_COVERAGE_NOT_MET" in (
        audit.t09_blockers
    )
    assert "T18_CROSS_TRADER_CANDIDATE_OUTCOME_COVERAGE_NOT_MET" in (
        audit.t18_blockers
    )
