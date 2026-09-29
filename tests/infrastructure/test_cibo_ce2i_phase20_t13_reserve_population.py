import json
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from qore.infrastructure.cibo_ce2i_phase20_forward_store import (
    Phase20ForwardDecisionSeal,
    Phase20ForwardOutcomeSeal,
    VersionedPhase20ForwardEvidenceBook,
)
from qore.infrastructure.cibo_ce2i_phase20_qualification_plan import (
    FROZEN_PHASE20D_QUALIFICATION_PLAN,
)
from qore.infrastructure.cibo_ce2i_phase20_t13_reserve_population import (
    assess_phase20_t13_reserve_population,
)

BASE = FROZEN_PHASE20D_QUALIFICATION_PLAN.frozen_at + timedelta(hours=1)


def _decision(
    index: int,
    *,
    hard_headroom: Decimal,
    candidate_risk: Decimal | None,
) -> Phase20ForwardDecisionSeal:
    decision_at = BASE + timedelta(hours=index)
    candidates = (
        []
        if candidate_risk is None
        else [{"candidate": {"stop_risk_usd": str(candidate_risk)}}]
    )
    payload = {
        "evidence_kind": "FORWARD_OBSERVED",
        "hard_risk_headroom_usd": str(hard_headroom),
        "candidates": candidates,
    }
    return Phase20ForwardDecisionSeal(
        evidence_id=f"decision-{index}",
        decision_epoch_id=f"epoch-{index}",
        evidence_sha256="sha256:" + f"{index + 1:064x}",
        decision_at=decision_at,
        candidate_id="phase20-candidate",
        code_sha="a" * 40,
        parameter_sha256="sha256:" + ("b" * 64),
        signal_fingerprints=(
            () if candidate_risk is None else (f"signal-{index}",)
        ),
        canonical_payload_json=json.dumps(payload, sort_keys=True),
        collector_git_sha="c" * 40,
        sealed_at=decision_at + timedelta(milliseconds=100),
        seal_deadline_at=decision_at + timedelta(seconds=2),
    )


def _outcome(
    decision: Phase20ForwardDecisionSeal,
    index: int,
    pnl: Decimal,
) -> Phase20ForwardOutcomeSeal:
    observed_at = decision.decision_at + timedelta(minutes=30)
    risk = Decimal("5")
    return Phase20ForwardOutcomeSeal(
        evidence_id=f"outcome-{index}",
        decision_evidence_sha256=decision.evidence_sha256,
        signal_fingerprint=f"signal-{index}",
        position_id=index + 1,
        execution_risk_evidence_id=f"risk-{index}",
        settlement_deal_ids=(1000 + index,),
        fill_evidence_refs=(f"fill-{index}",),
        observed_at=observed_at,
        realized_net_pnl_usd=pnl,
        executed_initial_stop_risk_usd=risk,
        realized_structural_outcome_r=pnl / risk,
    )


def test_t13_population_detects_drawdown_pressure_and_scarcity() -> None:
    decisions = tuple(
        _decision(
            index,
            hard_headroom=Decimal("4") if index >= 2 else Decimal("10"),
            candidate_risk=Decimal("6"),
        )
        for index in range(5)
    )
    outcomes = (
        _outcome(decisions[0], 0, Decimal("-3")),
        _outcome(decisions[1], 1, Decimal("-2")),
    )
    book = VersionedPhase20ForwardEvidenceBook(
        generation=len(decisions) + len(outcomes),
        decisions=decisions,
        outcomes=outcomes,
    )

    audit = assess_phase20_t13_reserve_population(book)

    assert audit.usable_decision_epochs == 5
    assert audit.candidate_epochs == 5
    assert audit.candidate_instances == 5
    assert audit.settled_history_epochs >= 3
    assert audit.loss_cluster_epochs >= 3
    assert audit.settlement_drawdown_epochs >= 3
    assert audit.reserve_pressure_epochs >= 3
    assert audit.scarce_risk_headroom_epochs == 3
    assert audit.pressure_and_scarcity_epochs >= 3
    assert audit.maximum_loss_cluster == 2
    assert audit.maximum_settlement_drawdown_usd == Decimal("5")
    assert audit.reserve_policy_identified is False
    assert audit.oos_utility_demonstrated is False
    assert "T13_RESERVE_POLICY_NOT_IDENTIFIED" in audit.blockers


def test_t13_population_refuses_to_infer_policy_without_pressure() -> None:
    decisions = tuple(
        _decision(
            index,
            hard_headroom=Decimal("20"),
            candidate_risk=Decimal("2"),
        )
        for index in range(4)
    )
    book = VersionedPhase20ForwardEvidenceBook(
        generation=len(decisions),
        decisions=decisions,
        outcomes=(),
    )

    audit = assess_phase20_t13_reserve_population(book)

    assert audit.reserve_pressure_epochs == 0
    assert audit.pressure_and_scarcity_epochs == 0
    assert "NO_FORWARD_SETTLED_HISTORY_FOR_T13" in audit.blockers
    assert "NO_FORWARD_DRAWDOWN_RESERVE_PRESSURE_EPOCHS" in audit.blockers
    assert (
        "NO_T13_PRESSURE_AND_SCARCE_CAPACITY_INTERSECTION"
        in audit.blockers
    )


def test_t13_population_uses_frozen_phase20_decision_threshold() -> None:
    decisions = tuple(
        _decision(
            index,
            hard_headroom=Decimal("10"),
            candidate_risk=None,
        )
        for index in range(3)
    )
    book = VersionedPhase20ForwardEvidenceBook(
        generation=len(decisions),
        decisions=decisions,
        outcomes=(),
    )

    audit = assess_phase20_t13_reserve_population(book)

    assert audit.minimum_decision_epochs == (
        FROZEN_PHASE20D_QUALIFICATION_PLAN.minimum_decision_epochs
    )
    assert audit.decision_threshold_met is False
    assert any(
        blocker.startswith("PHASE20_MINIMUM_DECISION_EPOCHS_NOT_MET:")
        for blocker in audit.blockers
    )
