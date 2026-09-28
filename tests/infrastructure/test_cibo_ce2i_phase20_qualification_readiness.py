import json
from dataclasses import replace
from datetime import UTC, datetime, timedelta
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
from qore.infrastructure.cibo_ce2i_phase20_qualification_plan import (
    FROZEN_PHASE20D_QUALIFICATION_PLAN,
)
from qore.infrastructure.cibo_ce2i_phase20_qualification_readiness import (
    assess_phase20d_qualification_readiness,
)

START = datetime(2026, 9, 28, 12, 0, tzinfo=UTC)
LINEAGES = (
    TraderLineage.VT31_NAS100.value,
    TraderLineage.R43_GBPUSD.value,
    TraderLineage.R34_XAUUSD.value,
    TraderLineage.R38_EURUSD.value,
    TraderLineage.R38_GBPJPY.value,
    TraderLineage.R42_AUDJPY.value,
    TraderLineage.VT08_FOREX.value,
)


def _sha(index: int) -> str:
    return f"sha256:{index + 1:064x}"


def test_phase20d_readiness_rejects_empty_population_without_economics() -> None:
    readiness = assess_phase20d_qualification_readiness(
        evidence_book=VersionedPhase20ForwardEvidenceBook(generation=0),
        policy_book=VersionedPhase20ForwardPolicyBook(generation=0),
    )

    assert readiness.ready is False
    assert readiness.decision_epochs == 0
    assert readiness.candidate_outcomes == 0
    assert readiness.candidate_outcome_coverage == 0
    assert "MINIMUM_DECISION_EPOCHS_NOT_MET" in readiness.reasons
    assert "MINIMUM_CANDIDATE_OUTCOMES_NOT_MET" in readiness.reasons
    assert "SELECTED_OUTCOME_COVERAGE_NOT_MET" in readiness.reasons


def test_phase20d_readiness_passes_only_mature_complete_population() -> None:
    decisions: list[Phase20ForwardDecisionSeal] = []
    policies: list[Phase20ForwardPolicyDecisionSeal] = []
    outcomes: list[Phase20ForwardOutcomeSeal] = []
    for decision_index in range(80):
        day_offset = decision_index % 28
        decision_at = START + timedelta(
            days=day_offset,
            minutes=decision_index,
        )
        evidence_sha = _sha(decision_index)
        fingerprints = tuple(
            f"signal-{decision_index}-{candidate_index}"
            for candidate_index in range(3)
        )
        candidate_rows = [
            {
                "candidate": {
                    "signal_fingerprint": fingerprint,
                    "trader_id": LINEAGES[
                        (decision_index * 3 + candidate_index) % len(LINEAGES)
                    ],
                }
            }
            for candidate_index, fingerprint in enumerate(fingerprints)
        ]
        decisions.append(
            Phase20ForwardDecisionSeal(
                evidence_id=f"evidence-{decision_index}",
                decision_epoch_id=f"epoch-{decision_index}",
                evidence_sha256=evidence_sha,
                decision_at=decision_at,
                sealed_at=decision_at + timedelta(milliseconds=500),
                seal_deadline_at=decision_at + timedelta(seconds=2),
                candidate_id="CIBO_PHASE20H20I_FORWARD_CANDIDATE_V2",
                code_sha="7acce68c6ece61fae1adacf3f8e60815839b6f6a",
                parameter_sha256=_sha(1000),
                signal_fingerprints=fingerprints,
                canonical_payload_json=json.dumps(
                    {"candidates": candidate_rows},
                    sort_keys=True,
                ),
            )
        )
        policies.append(
            Phase20ForwardPolicyDecisionSeal(
                evidence_sha256=evidence_sha,
                policy_record_sha256=_sha(2000 + decision_index),
                allocator_disposition="ALLOCATE",
                selected_signal_fingerprints=(fingerprints[0],),
                canonical_record_json="{}",
            )
        )
        for candidate_index, fingerprint in enumerate(fingerprints):
            outcomes.append(
                Phase20ForwardOutcomeSeal(
                    evidence_id=(
                        f"outcome-{decision_index}-{candidate_index}"
                    ),
                    decision_evidence_sha256=evidence_sha,
                    signal_fingerprint=fingerprint,
                    position_id=decision_index * 10 + candidate_index + 1,
                    execution_risk_evidence_id=(
                        f"risk-{decision_index}-{candidate_index}"
                    ),
                    settlement_deal_ids=(
                        decision_index * 10 + candidate_index + 20001,
                    ),
                    fill_evidence_refs=(
                        f"fill-{decision_index}-{candidate_index}",
                    ),
                    observed_at=decision_at + timedelta(hours=1),
                    realized_net_pnl_usd=Decimal("0"),
                    executed_initial_stop_risk_usd=Decimal("10"),
                    realized_structural_outcome_r=Decimal("0"),
                )
            )

    readiness = assess_phase20d_qualification_readiness(
        evidence_book=VersionedPhase20ForwardEvidenceBook(
            generation=1,
            decisions=tuple(decisions),
            outcomes=tuple(outcomes),
        ),
        policy_book=VersionedPhase20ForwardPolicyBook(
            generation=1,
            decisions=tuple(policies),
        ),
    )

    assert readiness.ready is True
    assert readiness.reasons == ()
    assert readiness.decision_epochs == 80
    assert readiness.candidate_instances == 240
    assert readiness.candidate_outcomes == 240
    assert readiness.selected_instances == 80
    assert readiness.selected_outcomes == 80
    assert readiness.candidate_outcome_coverage == Decimal("1")
    assert readiness.selected_outcome_coverage == Decimal("1")
    assert readiness.calendar_span_days >= 28
    assert readiness.distinct_trading_days == 28
    assert readiness.represented_lineages == 7
    assert readiness.minimum_fold_candidate_outcomes >= 40
    assert readiness.minimum_fold_lineages >= 4
    assert readiness.pre_freeze_decisions == 0

    pre_freeze = replace(
        decisions[0],
        decision_at=(
            FROZEN_PHASE20D_QUALIFICATION_PLAN.frozen_at
            - timedelta(microseconds=1)
        ),
    )
    contaminated = assess_phase20d_qualification_readiness(
        evidence_book=VersionedPhase20ForwardEvidenceBook(
            generation=2,
            decisions=(pre_freeze, *decisions[1:]),
            outcomes=tuple(outcomes),
        ),
        policy_book=VersionedPhase20ForwardPolicyBook(
            generation=1,
            decisions=tuple(policies),
        ),
    )

    assert contaminated.ready is False
    assert contaminated.pre_freeze_decisions == 1
    assert (
        "DECISION_PREDATES_QUALIFICATION_FREEZE"
        in contaminated.reasons
    )


def test_phase20d_readiness_requires_policy_record_for_every_epoch() -> None:
    decision_at = START
    decision = Phase20ForwardDecisionSeal(
        evidence_id="evidence-one",
        decision_epoch_id="epoch-one",
        evidence_sha256=_sha(1),
        decision_at=decision_at,
        candidate_id="CIBO_PHASE20H20I_FORWARD_CANDIDATE_V2",
        code_sha="7acce68c6ece61fae1adacf3f8e60815839b6f6a",
        parameter_sha256=_sha(1000),
        signal_fingerprints=("signal-one",),
        canonical_payload_json=json.dumps(
            {
                "candidates": [
                    {
                        "candidate": {
                            "signal_fingerprint": "signal-one",
                            "trader_id": TraderLineage.VT31_NAS100.value,
                        }
                    }
                ]
            }
        ),
    )
    outcome = Phase20ForwardOutcomeSeal(
        evidence_id="outcome-one",
        decision_evidence_sha256=decision.evidence_sha256,
        signal_fingerprint="signal-one",
        position_id=1,
        execution_risk_evidence_id="risk-one",
        settlement_deal_ids=(30001,),
        fill_evidence_refs=("fill-one",),
        observed_at=decision_at + timedelta(hours=1),
        realized_net_pnl_usd=Decimal("10"),
        executed_initial_stop_risk_usd=Decimal("10"),
        realized_structural_outcome_r=Decimal("1"),
    )

    readiness = assess_phase20d_qualification_readiness(
        evidence_book=VersionedPhase20ForwardEvidenceBook(
            generation=2,
            decisions=(decision,),
            outcomes=(outcome,),
        ),
        policy_book=VersionedPhase20ForwardPolicyBook(generation=0),
    )

    assert readiness.missing_policy_decisions == 1
    assert "MISSING_POLICY_DECISIONS" in readiness.reasons
