from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)
from qore.infrastructure.cibo_ce2i_phase20_causal_tool_readiness import (
    Phase20ToolEvidenceState,
    assess_phase20_causal_tool_readiness,
)
from qore.infrastructure.cibo_ce2i_phase20_forward_store import (
    Phase20ForwardDecisionSeal,
    Phase20ForwardOutcomeSeal,
    VersionedPhase20ForwardEvidenceBook,
)
from qore.infrastructure.cibo_ce2i_phase20_qualification_readiness import (
    Phase20QualificationReadiness,
)

BASE = datetime(2026, 9, 28, 5, 0, tzinfo=UTC)


def _qualification(*, ready: bool) -> Phase20QualificationReadiness:
    return Phase20QualificationReadiness(
        ready=ready,
        reasons=() if ready else ("MINIMUM_DECISION_EPOCHS_NOT_MET",),
        decision_epochs=80 if ready else 1,
        candidate_instances=200 if ready else 2,
        candidate_outcomes=200 if ready else 0,
        selected_instances=60 if ready else 1,
        selected_outcomes=60 if ready else 0,
        candidate_outcome_coverage=Decimal("1") if ready else Decimal("0"),
        selected_outcome_coverage=Decimal("1") if ready else Decimal("0"),
        calendar_span_days=28 if ready else 1,
        distinct_trading_days=20 if ready else 1,
        represented_lineages=7 if ready else 2,
        minimum_outcomes_any_lineage=8 if ready else 0,
        minimum_fold_candidate_outcomes=40 if ready else 0,
        minimum_fold_lineages=7 if ready else 0,
        missing_policy_decisions=0,
        pre_freeze_decisions=0,
    )


def _payload(index: int, *, malformed: bool = False) -> dict[str, object]:
    candidates: list[object] = [
        {
            "candidate": {
                "signal_fingerprint": f"a-{index}",
                "trader_id": "R38_EURUSD",
                "stop_risk_usd": "5",
                "margin_usd": "10",
                "concentration_group": "USD",
                "concentration_risk_usd": "5",
            }
        },
        {
            "candidate": {
                "signal_fingerprint": f"b-{index}",
                "trader_id": "R43_GBPUSD",
                "stop_risk_usd": "5",
                "margin_usd": "10",
                "concentration_group": "USD",
                "concentration_risk_usd": "5",
            }
        },
    ]
    if malformed:
        candidates[0] = {"candidate": {"signal_fingerprint": "broken"}}
    return {
        "evidence_kind": "FORWARD_OBSERVED",
        "hard_risk_headroom_usd": "5",
        "margin_headroom_usd": "100",
        "concentration_limit_by_group": [["USD", "100"]],
        "regime_state": {
            "provider_condition": "HEALTHY",
            "evidence_stale": False,
            "drawdown_utilization": "0.10",
        },
        "candidates": candidates,
        "known_options": [],
        "advanced_evidence": {"portfolio_netting": None},
    }


def _seal(index: int, *, malformed: bool = False) -> Phase20ForwardDecisionSeal:
    decision_at = BASE + timedelta(minutes=index)
    return Phase20ForwardDecisionSeal(
        evidence_id=f"evidence-{index}",
        decision_epoch_id=f"epoch-{index}",
        evidence_sha256=f"sha256:{index:064x}",
        decision_at=decision_at,
        candidate_id="candidate",
        code_sha="code",
        parameter_sha256="params",
        signal_fingerprints=(f"a-{index}", f"b-{index}"),
        canonical_payload_json=json.dumps(
            _payload(index, malformed=malformed),
            sort_keys=True,
        ),
        sealed_at=decision_at + timedelta(milliseconds=100),
        seal_deadline_at=decision_at + timedelta(seconds=2),
    )


def _outcome(
    decision: Phase20ForwardDecisionSeal,
) -> Phase20ForwardOutcomeSeal:
    return Phase20ForwardOutcomeSeal(
        evidence_id=f"outcome:{decision.evidence_id}",
        decision_evidence_sha256=decision.evidence_sha256,
        signal_fingerprint=decision.signal_fingerprints[0],
        position_id=1,
        execution_risk_evidence_id=f"risk:{decision.evidence_id}",
        settlement_deal_ids=(1,),
        fill_evidence_refs=(f"fill:{decision.evidence_id}",),
        observed_at=decision.decision_at + timedelta(seconds=30),
        realized_net_pnl_usd=Decimal("-5"),
        executed_initial_stop_risk_usd=Decimal("5"),
        realized_structural_outcome_r=Decimal("-1"),
    )


def _row(report: object, code: str) -> object:
    return next(item for item in report.tools if item.tool_code == code)


def test_forward_readiness_uses_frozen_exact_competition_threshold() -> None:
    book = VersionedPhase20ForwardEvidenceBook(
        generation=30,
        decisions=tuple(_seal(index) for index in range(30)),
    )
    report = assess_phase20_causal_tool_readiness(
        evidence_book=book,
        qualification_readiness=_qualification(ready=True),
    )

    assert report.exact_competition_epochs == 30
    assert report.scarce_competition_epochs == 30
    assert report.valid_regime_epochs == 30

    t09 = _row(report, "T09")
    t12 = _row(report, "T12")
    t18 = _row(report, "T18")
    assert t09.state is Phase20ToolEvidenceState.FORWARD_POPULATION_READY
    assert t12.state is Phase20ToolEvidenceState.FORWARD_POPULATION_READY
    assert t18.state is Phase20ToolEvidenceState.FORWARD_POPULATION_READY

    t08 = _row(report, "T08")
    assert t08.state is Phase20ToolEvidenceState.STREAM_BLOCKED
    assert "PORTFOLIO_NETTING_EVIDENCE_COVERAGE_INCOMPLETE" in t08.blockers


def test_forward_readiness_does_not_confuse_contract_stream_with_calibration() -> None:
    report = assess_phase20_causal_tool_readiness(
        evidence_book=VersionedPhase20ForwardEvidenceBook(
            generation=1,
            decisions=(_seal(0),),
        ),
        qualification_readiness=_qualification(ready=False),
    )

    assert _row(report, "T09").state is Phase20ToolEvidenceState.COLLECTING_FORWARD
    assert _row(report, "T12").state is Phase20ToolEvidenceState.COLLECTING_FORWARD
    assert _row(report, "T13").state is Phase20ToolEvidenceState.STREAM_BLOCKED
    assert (
        _row(report, "T14").state
        is Phase20ToolEvidenceState.REQUIRES_DIFFERENT_EVIDENCE
    )
    assert _row(report, "T15").state is Phase20ToolEvidenceState.COLLECTING_FORWARD
    assert report.global_forward_ready is False


def test_forward_readiness_fails_closed_on_malformed_scarcity_payload() -> None:
    with pytest.raises(CiboCapitalManagementError, match="monetary field"):
        assess_phase20_causal_tool_readiness(
            evidence_book=VersionedPhase20ForwardEvidenceBook(
                generation=1,
                decisions=(_seal(0, malformed=True),),
            ),
            qualification_readiness=_qualification(ready=False),
        )

def test_t13_becomes_collecting_when_prior_causal_history_is_reconstructible() -> None:
    first = _seal(0)
    second = _seal(1)
    report = assess_phase20_causal_tool_readiness(
        evidence_book=VersionedPhase20ForwardEvidenceBook(
            generation=3,
            decisions=(first, second),
            outcomes=(_outcome(first),),
        ),
        qualification_readiness=_qualification(ready=False),
    )

    t13 = _row(report, "T13")
    assert report.causal_history_epochs == 1
    assert t13.state is Phase20ToolEvidenceState.COLLECTING_FORWARD
    assert t13.stream_bound is True
    assert t13.qualifying_epochs == 1
    assert (
        "FRESH_OOS_DRAWDOWN_RESERVE_UTILITY_ANALYSIS_REQUIRED"
        in t13.blockers
    )
