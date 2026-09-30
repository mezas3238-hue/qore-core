from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from qore.infrastructure.cibo_ce2i_phase20_forward_store import (
    Phase20ForwardDecisionSeal,
    Phase20ForwardOutcomeSeal,
    VersionedPhase20ForwardEvidenceBook,
)
from qore.infrastructure.cibo_ce2i_phase20_t15_option_realization import (
    assess_phase20_t15_option_realization,
)

BASE = datetime(2026, 9, 28, 5, 0, tzinfo=UTC)


def _decision(
    *,
    index: int,
    step: int,
    signal: str,
    known_options: list[dict[str, object]],
) -> Phase20ForwardDecisionSeal:
    at = BASE + timedelta(hours=index)
    payload = {
        "evidence_kind": "FORWARD_OBSERVED",
        "current_step": step,
        "candidates": (
            []
            if not signal
            else [{"candidate": {"signal_fingerprint": signal}}]
        ),
        "known_options": known_options,
    }
    return Phase20ForwardDecisionSeal(
        evidence_id=f"decision-{index}",
        decision_epoch_id=f"epoch-{index}",
        evidence_sha256=f"sha256:{index + 1:064x}",
        decision_at=at,
        candidate_id="candidate",
        code_sha="code",
        parameter_sha256="params",
        signal_fingerprints=(() if not signal else (signal,)),
        canonical_payload_json=json.dumps(payload, sort_keys=True),
        sealed_at=at + timedelta(milliseconds=100),
        seal_deadline_at=at + timedelta(seconds=2),
    )


def _option(*, signal: str, step: int, expires_hours: int = 4) -> dict[str, object]:
    return {
        "evidence_id": f"option:{signal}",
        "option": {
            "opportunity_id": f"known-option:VT31_NAS100:{signal}",
            "decision_step": step,
            "minimum_stop_risk_usd": "5",
            "minimum_margin_usd": "10",
        },
        "known_as_of": BASE.isoformat(),
        "active_at_decision": True,
        "expires_at": (BASE + timedelta(hours=expires_hours)).isoformat(),
        "cancelled_at": None,
    }


def test_t15_tracks_known_option_into_later_candidate_and_outcome() -> None:
    origin = _decision(
        index=0,
        step=1,
        signal="",
        known_options=[_option(signal="vt31-long", step=2)],
    )
    realized = _decision(
        index=1,
        step=2,
        signal="vt31-long",
        known_options=[],
    )
    outcome = Phase20ForwardOutcomeSeal(
        evidence_id="outcome",
        decision_evidence_sha256=realized.evidence_sha256,
        signal_fingerprint="vt31-long",
        position_id=1,
        execution_risk_evidence_id="risk",
        settlement_deal_ids=(1,),
        fill_evidence_refs=("fill",),
        observed_at=realized.decision_at + timedelta(minutes=30),
        realized_net_pnl_usd=Decimal("5"),
        executed_initial_stop_risk_usd=Decimal("5"),
        realized_structural_outcome_r=Decimal("1"),
    )

    report = assess_phase20_t15_option_realization(
        VersionedPhase20ForwardEvidenceBook(
            generation=3,
            decisions=(origin, realized),
            outcomes=(outcome,),
        )
    )

    assert report.stream_bound is True
    assert report.known_option_instances == 1
    assert report.signal_bound_option_instances == 1
    assert report.matured_option_instances == 1
    assert report.materialized_candidate_instances == 1
    assert report.reconciled_materialized_outcomes == 1
    assert report.expired_before_materialization == 0
    assert report.unresolved_matured_options == 0


def test_t15_expired_option_is_not_relabeled_as_materialized() -> None:
    origin = _decision(
        index=0,
        step=1,
        signal="",
        known_options=[
            _option(signal="never-triggered", step=2, expires_hours=1)
        ],
    )
    later = _decision(
        index=2,
        step=3,
        signal="other",
        known_options=[],
    )

    report = assess_phase20_t15_option_realization(
        VersionedPhase20ForwardEvidenceBook(
            generation=2,
            decisions=(origin, later),
        )
    )

    assert report.matured_option_instances == 1
    assert report.materialized_candidate_instances == 0
    assert report.expired_before_materialization == 1
    assert (
        "NO_KNOWN_OPTION_MATERIALIZED_AS_FUTURE_CANDIDATE"
        in report.blockers
    )
