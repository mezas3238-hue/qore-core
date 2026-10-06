from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime, timedelta

from qore.infrastructure.cibo_ce2i_phase20_forward_policy_store import (
    Phase20ForwardPolicyDecisionSeal,
    VersionedPhase20ForwardPolicyBook,
)
from qore.infrastructure.cibo_ce2i_phase20_forward_store import (
    Phase20ForwardDecisionSeal,
    VersionedPhase20ForwardEvidenceBook,
)
from qore.infrastructure.cibo_ce2i_phase20_t15_reservation_binding import (
    assess_phase20_t15_reservation_binding,
)

BASE = datetime(2026, 9, 28, 5, 0, tzinfo=UTC)
EVIDENCE_SHA = "sha256:" + ("1" * 64)
OPTION_ID = "known-option:VT31_NAS100:future-signal"


def _decision() -> Phase20ForwardDecisionSeal:
    payload = {
        "evidence_kind": "FORWARD_OBSERVED",
        "current_step": 10,
        "horizon_steps": 2,
        "hard_risk_headroom_usd": "20",
        "margin_headroom_usd": "100",
        "known_options": [
            {
                "evidence_id": "option-1",
                "option": {
                    "opportunity_id": OPTION_ID,
                    "decision_step": 11,
                    "minimum_stop_risk_usd": "5",
                    "minimum_margin_usd": "10",
                },
                "known_as_of": BASE.isoformat(),
                "active_at_decision": True,
                "expires_at": (BASE + timedelta(hours=2)).isoformat(),
                "cancelled_at": None,
            }
        ],
    }
    return Phase20ForwardDecisionSeal(
        evidence_id="decision",
        decision_epoch_id="epoch",
        evidence_sha256=EVIDENCE_SHA,
        decision_at=BASE,
        candidate_id="candidate",
        code_sha="code",
        parameter_sha256="params",
        signal_fingerprints=(),
        canonical_payload_json=json.dumps(payload, sort_keys=True),
        sealed_at=BASE + timedelta(milliseconds=100),
        seal_deadline_at=BASE + timedelta(seconds=2),
    )


def _policy(
    *,
    considered: tuple[str, ...] = (OPTION_ID,),
    reserve_risk: str = "5",
    reserve_margin: str = "10",
) -> Phase20ForwardPolicyDecisionSeal:
    record = {
        "evidence_sha256": EVIDENCE_SHA,
        "mpc_plan": {
            "posture": "STABLE",
            "considered_option_ids": list(considered),
            "representative_option_ids": list(considered),
            "reserve_stop_risk_usd": reserve_risk,
            "reserve_margin_usd": reserve_margin,
        },
    }
    canonical = json.dumps(
        record,
        sort_keys=True,
        separators=(",", ":"),
    )
    digest = "sha256:" + hashlib.sha256(canonical.encode()).hexdigest()
    return Phase20ForwardPolicyDecisionSeal(
        evidence_sha256=EVIDENCE_SHA,
        policy_record_sha256=digest,
        allocator_disposition="PRESERVE_CAPACITY",
        selected_signal_fingerprints=(),
        canonical_record_json=canonical,
    )


def _book() -> VersionedPhase20ForwardEvidenceBook:
    return VersionedPhase20ForwardEvidenceBook(
        generation=1,
        decisions=(_decision(),),
    )


def test_t15_reservation_binding_links_option_to_mpc_geometry() -> None:
    audit = assess_phase20_t15_reservation_binding(
        evidence_book=_book(),
        policy_book=VersionedPhase20ForwardPolicyBook(
            generation=1,
            decisions=(_policy(),),
        ),
    )

    assert audit.origin_epochs_with_known_options == 1
    assert audit.known_option_instances == 1
    assert audit.in_horizon_option_instances == 1
    assert audit.considered_option_instances == 1
    assert audit.representative_option_instances == 1
    assert audit.policy_bound_origin_epochs == 1
    assert audit.geometry_verified_origin_epochs == 1
    assert audit.nonzero_reserve_origin_epochs == 1
    assert audit.completely_bound_origin_epochs == 1
    assert audit.reservation_binding_complete is True
    assert audit.future_materialization_used is False
    assert audit.outcome_magnitudes_read is False
    assert audit.counterfactual_reservation_effect_identified is False
    assert audit.blockers == (
        "COUNTERFACTUAL_RESERVATION_CAUSAL_EFFECT_NOT_IDENTIFIED",
        "FRESH_OOS_OPTIONALITY_UTILITY_ANALYSIS_REQUIRED",
    )


def test_t15_reservation_binding_detects_missing_considered_option() -> None:
    audit = assess_phase20_t15_reservation_binding(
        evidence_book=_book(),
        policy_book=VersionedPhase20ForwardPolicyBook(
            generation=1,
            decisions=(_policy(considered=()),),
        ),
    )

    assert audit.reservation_binding_complete is False
    assert audit.considered_set_mismatch_epochs == 1
    assert "T15_MPC_CONSIDERED_OPTION_SET_MISMATCH" in audit.blockers


def test_t15_reservation_binding_detects_wrong_reserve_geometry() -> None:
    audit = assess_phase20_t15_reservation_binding(
        evidence_book=_book(),
        policy_book=VersionedPhase20ForwardPolicyBook(
            generation=1,
            decisions=(
                _policy(
                    reserve_risk="4",
                    reserve_margin="10",
                ),
            ),
        ),
    )

    assert audit.reservation_binding_complete is False
    assert audit.reserve_geometry_mismatch_epochs == 1
    assert "T15_MPC_RESERVATION_GEOMETRY_MISMATCH" in audit.blockers


def test_t15_reservation_binding_reports_missing_policy() -> None:
    audit = assess_phase20_t15_reservation_binding(
        evidence_book=_book(),
        policy_book=VersionedPhase20ForwardPolicyBook(generation=0),
    )

    assert audit.reservation_binding_complete is False
    assert audit.missing_policy_origin_epochs == 1
    assert "T15_KNOWN_OPTION_ORIGIN_MISSING_POLICY_RECORD" in audit.blockers
