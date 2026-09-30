import json
from datetime import timedelta
from decimal import Decimal

import pytest

from qore.infrastructure.account_wide_risk import TraderLineage
from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)
from qore.infrastructure.cibo_ce2i_phase20_execution_risk_store import (
    VersionedPhase20ExecutedRiskBook,
)
from qore.infrastructure.cibo_ce2i_phase20_forward_store import (
    Phase20ForwardDecisionSeal,
    VersionedPhase20ForwardEvidenceBook,
)
from qore.infrastructure.cibo_ce2i_phase20_outcome_reconciliation import (
    Phase20ExecutedRiskEvidence,
)
from qore.infrastructure.cibo_ce2i_phase20_qualification_plan import (
    FROZEN_PHASE20D_QUALIFICATION_PLAN,
)
from qore.infrastructure.cibo_ce2i_phase20_t11_execution_population import (
    assess_phase20_t11_execution_population,
)

BASE = FROZEN_PHASE20D_QUALIFICATION_PLAN.frozen_at + timedelta(hours=1)
LINEAGES = (
    TraderLineage.VT08_FOREX,
    TraderLineage.R34_XAUUSD,
    TraderLineage.R38_EURUSD,
    TraderLineage.R43_GBPUSD,
    TraderLineage.R38_GBPJPY,
    TraderLineage.R42_AUDJPY,
    TraderLineage.VT31_NAS100,
)


def _decision(index: int, lineage: TraderLineage) -> Phase20ForwardDecisionSeal:
    decision_at = BASE + timedelta(minutes=5 * index)
    signal = f"signal-{index}"
    payload = {
        "evidence_kind": "FORWARD_OBSERVED",
        "population_slots": [
            {
                "trader_id": lineage.value,
                "signal_fingerprint": signal,
            }
        ],
    }
    return Phase20ForwardDecisionSeal(
        evidence_id=f"decision-{index}",
        decision_epoch_id=f"epoch-{index}",
        evidence_sha256="sha256:" + f"{index + 1:064x}",
        decision_at=decision_at,
        candidate_id="phase20-candidate",
        code_sha="a" * 40,
        parameter_sha256="sha256:" + ("b" * 64),
        signal_fingerprints=(signal,),
        canonical_payload_json=json.dumps(payload, sort_keys=True),
        collector_git_sha="c" * 40,
        sealed_at=decision_at + timedelta(milliseconds=100),
        seal_deadline_at=decision_at + timedelta(seconds=2),
    )


def _risk(
    decision: Phase20ForwardDecisionSeal,
    index: int,
    *,
    with_latency: bool = True,
) -> Phase20ExecutedRiskEvidence:
    intended_risk = Decimal("1")
    executed_risk = (
        intended_risk + Decimal(index % 3 - 1) / Decimal("100")
    )
    return Phase20ExecutedRiskEvidence(
        evidence_id=f"executed-risk-{index}",
        decision_evidence_sha256=decision.evidence_sha256,
        signal_fingerprint=f"signal-{index}",
        qore_symbol="GBPUSD",
        provider_order_ref=f"order-{index}",
        side="long",
        position_id=index + 1,
        authorized_source_volume=Decimal("0.01"),
        filled_source_volume=Decimal("0.01"),
        weighted_fill_price=Decimal("100") + executed_risk - Decimal("1"),
        intended_entry_price=Decimal("100"),
        structural_stop_price=Decimal("99"),
        stop_risk_per_volume_at_intended_entry_usd=Decimal("100"),
        executed_initial_stop_risk_usd=executed_risk,
        observed_at=decision.decision_at + timedelta(seconds=1),
        fill_evidence_refs=(f"fill-{index}",),
        fill_reconciled=True,
        mutation_outcome_known=True,
        capital_deployed_at=(
            decision.decision_at + timedelta(milliseconds=500)
            if with_latency
            else None
        ),
    )


def _books(*, with_latency: bool = True):
    decisions = []
    risks = []
    counts = (9, 9, 9, 9, 8, 8, 8)
    index = 0
    for lineage, count in zip(LINEAGES, counts, strict=True):
        for _ in range(count):
            decision = _decision(index, lineage)
            decisions.append(decision)
            risks.append(_risk(decision, index, with_latency=with_latency))
            index += 1
    return (
        VersionedPhase20ForwardEvidenceBook(
            generation=len(decisions),
            decisions=tuple(decisions),
            outcomes=(),
        ),
        VersionedPhase20ExecutedRiskBook(
            generation=len(risks),
            evidences=tuple(risks),
        ),
    )


def test_t11_population_uses_frozen_execution_and_lineage_thresholds() -> None:
    evidence, risk = _books()

    audit = assess_phase20_t11_execution_population(
        evidence_book=evidence,
        executed_risk_book=risk,
    )

    assert audit.eligible_execution_instances == 60
    assert len(audit.represented_lineages) == 7
    assert audit.minimum_instances_per_lineage == 8
    assert audit.latency_bound_instances == 60
    assert audit.empirical_execution_population_ready is True
    assert audit.adverse_slippage_instances == 20
    assert audit.favorable_slippage_instances == 20
    assert audit.flat_slippage_instances == 20
    assert audit.mean_decision_to_deployment_ms == Decimal("500.0")
    assert audit.slippage_empirically_calibrated is False
    assert audit.execution_model_ready is False
    assert "REALIZED_COMMISSION_AND_SPREAD_ECONOMICS_NOT_BOUND" in audit.blockers


def test_t11_population_requires_complete_latency_coverage() -> None:
    evidence, risk = _books(with_latency=False)

    audit = assess_phase20_t11_execution_population(
        evidence_book=evidence,
        executed_risk_book=risk,
    )

    assert audit.eligible_execution_instances == 60
    assert audit.latency_bound_instances == 0
    assert audit.empirical_execution_population_ready is False
    assert (
        "T11_DECISION_TO_DEPLOYMENT_LATENCY_COVERAGE_INCOMPLETE"
        in audit.blockers
    )


def test_t11_rejects_decision_sealed_after_deployment() -> None:
    decision = _decision(0, LINEAGES[0])
    risk = _risk(decision, 0)
    bad_decision = Phase20ForwardDecisionSeal(
        evidence_id=decision.evidence_id,
        decision_epoch_id=decision.decision_epoch_id,
        evidence_sha256=decision.evidence_sha256,
        decision_at=decision.decision_at,
        candidate_id=decision.candidate_id,
        code_sha=decision.code_sha,
        parameter_sha256=decision.parameter_sha256,
        signal_fingerprints=decision.signal_fingerprints,
        canonical_payload_json=decision.canonical_payload_json,
        collector_git_sha=decision.collector_git_sha,
        sealed_at=decision.decision_at + timedelta(milliseconds=700),
        seal_deadline_at=decision.decision_at + timedelta(seconds=2),
    )
    evidence = VersionedPhase20ForwardEvidenceBook(
        generation=1,
        decisions=(bad_decision,),
        outcomes=(),
    )
    risk_book = VersionedPhase20ExecutedRiskBook(
        generation=1,
        evidences=(risk,),
    )

    with pytest.raises(
        CiboCapitalManagementError,
        match="sealed after capital deployment",
    ):
        assess_phase20_t11_execution_population(
            evidence_book=evidence,
            executed_risk_book=risk_book,
        )
