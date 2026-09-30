from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from qore.infrastructure.cibo_ce2i_phase20_causal_history_state import (
    build_phase20_causal_history_state,
)
from qore.infrastructure.cibo_ce2i_phase20_forward_store import (
    Phase20ForwardDecisionSeal,
    Phase20ForwardOutcomeSeal,
    VersionedPhase20ForwardEvidenceBook,
)

BASE = datetime(2026, 9, 28, 5, 0, tzinfo=UTC)


def _decision(index: int) -> Phase20ForwardDecisionSeal:
    decision_at = BASE + timedelta(minutes=index)
    payload = {
        "evidence_kind": "FORWARD_OBSERVED",
        "candidates": [
            {"candidate": {"signal_fingerprint": f"a-{index}"}},
            {"candidate": {"signal_fingerprint": f"b-{index}"}},
        ],
    }
    return Phase20ForwardDecisionSeal(
        evidence_id=f"e-{index}",
        decision_epoch_id=f"epoch-{index}",
        evidence_sha256=f"sha256:{index + 1:064x}",
        decision_at=decision_at,
        candidate_id="candidate",
        code_sha="code",
        parameter_sha256="params",
        signal_fingerprints=(f"a-{index}", f"b-{index}"),
        canonical_payload_json=json.dumps(payload, sort_keys=True),
        sealed_at=decision_at + timedelta(milliseconds=100),
        seal_deadline_at=decision_at + timedelta(seconds=2),
    )


def _loss(decision: Phase20ForwardDecisionSeal) -> Phase20ForwardOutcomeSeal:
    return Phase20ForwardOutcomeSeal(
        evidence_id=f"outcome:{decision.evidence_id}",
        decision_evidence_sha256=decision.evidence_sha256,
        signal_fingerprint=decision.signal_fingerprints[0],
        position_id=1,
        execution_risk_evidence_id="risk:1",
        settlement_deal_ids=(1,),
        fill_evidence_refs=("fill:1",),
        observed_at=decision.decision_at + timedelta(seconds=30),
        realized_net_pnl_usd=Decimal("-5"),
        executed_initial_stop_risk_usd=Decimal("5"),
        realized_structural_outcome_r=Decimal("-1"),
    )


def test_causal_history_uses_only_prior_sealed_decisions_and_outcomes() -> None:
    first = _decision(0)
    second = _decision(1)
    future = _decision(2)
    book = VersionedPhase20ForwardEvidenceBook(
        generation=4,
        decisions=(first, second, future),
        outcomes=(_loss(first),),
    )

    state = build_phase20_causal_history_state(
        evidence_book=book,
        decision=second,
    )

    assert state.prior_decision_epochs == 1
    assert state.prior_candidate_instances == 2
    assert state.prior_settled_outcomes == 1
    assert state.consecutive_settled_losses == 1
    assert state.cumulative_net_pnl_usd == Decimal("-5")
    assert state.settlement_cash_drawdown_usd == Decimal("5")
    assert state.max_settlement_cash_drawdown_usd == Decimal("5")
    assert state.observed_candidate_arrivals_per_day == Decimal("2880")
    assert state.source_decision_sha256s == (first.evidence_sha256,)
    assert state.source_outcome_evidence_ids == ("outcome:e-0",)


def test_causal_history_excludes_outcome_not_observed_before_decision() -> None:
    first = _decision(0)
    second = _decision(1)
    late = Phase20ForwardOutcomeSeal(
        evidence_id="late",
        decision_evidence_sha256=first.evidence_sha256,
        signal_fingerprint=first.signal_fingerprints[0],
        position_id=2,
        execution_risk_evidence_id="risk:late",
        settlement_deal_ids=(2,),
        fill_evidence_refs=("fill:late",),
        observed_at=second.decision_at + timedelta(seconds=1),
        realized_net_pnl_usd=Decimal("5"),
        executed_initial_stop_risk_usd=Decimal("5"),
        realized_structural_outcome_r=Decimal("1"),
    )
    state = build_phase20_causal_history_state(
        evidence_book=VersionedPhase20ForwardEvidenceBook(
            generation=3,
            decisions=(first, second),
            outcomes=(late,),
        ),
        decision=second,
    )

    assert state.prior_settled_outcomes == 0
    assert state.cumulative_net_pnl_usd == 0
    assert state.source_outcome_evidence_ids == ()
