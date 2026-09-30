from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

from qore.infrastructure.cibo_arch_b_forward_economic_manifest import (
    ARCH_B_FORWARD_ECONOMIC_MANIFEST_ID,
    ArchBForwardEconomicManifest,
    ArchBForwardEconomicManifestRow,
    build_arch_b_forward_economic_manifest,
)
from qore.infrastructure.cibo_ce2i_phase20_execution_risk_store import (
    VersionedPhase20ExecutedRiskBook,
)
from qore.infrastructure.cibo_ce2i_phase20_forward_policy_store import (
    VersionedPhase20ForwardPolicyBook,
)
from qore.infrastructure.cibo_ce2i_phase20_forward_store import (
    VersionedPhase20ForwardEvidenceBook,
)
from qore.infrastructure.cibo_ce2i_phase20_policy_candidate import (
    FROZEN_PHASE20_POLICY_CANDIDATE,
)
from qore.infrastructure.cibo_ce2i_phase20_qualification_plan import (
    FROZEN_PHASE20D_QUALIFICATION_PLAN,
    phase20d_qualification_plan_sha256,
)
from qore.infrastructure.cibo_cma_settlement_store import (
    VersionedCmaSettlementBook,
)
from qore.infrastructure.cibo_t20_capital_release_evidence import (
    VersionedT20CapitalReleaseBook,
)
from qore.infrastructure.cibo_usd60_exam_readiness import (
    CiboUsd60PrerequisiteEvidence,
    assess_cibo_usd60_pre_exam_readiness,
    required_usd60_pre_exam_prerequisites,
)

T0 = datetime(2026, 9, 30, 19, 30, tzinfo=UTC)


def _empty_manifest():
    return build_arch_b_forward_economic_manifest(
        evidence_book=VersionedPhase20ForwardEvidenceBook(generation=0),
        policy_book=VersionedPhase20ForwardPolicyBook(generation=0),
        executed_risk_book=VersionedPhase20ExecutedRiskBook(generation=0),
        settlement_book=VersionedCmaSettlementBook(generation=0),
        release_book=VersionedT20CapitalReleaseBook(generation=0),
    )


def _ready_manifest() -> ArchBForwardEconomicManifest:
    frozen = FROZEN_PHASE20_POLICY_CANDIDATE
    plan = FROZEN_PHASE20D_QUALIFICATION_PLAN
    lineages = (
        "R34_XAUUSD",
        "R38_EURUSD",
        "R43_GBPUSD",
        "R38_GBPJPY",
        "R42_AUDJPY",
        "VT08_FOREX",
        "VT31_NAS100",
    )
    symbols = (
        ("XAUUSD", "XAUUSD"),
        ("EURUSD", "EURUSD"),
        ("GBPUSD", "GBPUSD"),
        ("GBPJPY", "GBPJPY"),
        ("AUDJPY", "AUDJPY"),
        ("EURUSD", "EURUSD"),
        ("NAS100", "US100"),
    )
    rows = []
    for index in range(plan.minimum_candidate_outcomes):
        lineage = lineages[index % len(lineages)]
        qore_symbol, provider_symbol = symbols[index % len(symbols)]
        decision_at = T0 + timedelta(minutes=index)
        rows.append(
            ArchBForwardEconomicManifestRow(
                decision_epoch_id=f"epoch-{index}",
                decision_evidence_sha256=(
                    "sha256:" + f"{index + 1:064x}"
                ),
                decision_at=decision_at,
                fold_id=f"WF{(index % plan.fold_count) + 1}",
                signal_fingerprint=f"signal-{index}",
                trader_id=lineage,
                candidate_id=frozen.candidate_id,
                code_sha=frozen.code_sha,
                parameter_sha256=frozen.parameter_sha256(),
                collector_git_sha="a" * 40,
                provider_key="ctrader-demo",
                account_ref="12345",
                environment="DEMO",
                provider_evidence_id=f"provider-{index}",
                qore_symbol=qore_symbol,
                provider_symbol=provider_symbol,
                provider_economics_sha256="sha256:" + "2" * 64,
                provider_observed_at=(
                    decision_at - timedelta(seconds=1)
                ).isoformat(),
                provider_minimum_volume=Decimal("0.01"),
                provider_volume_step=Decimal("0.01"),
                provider_margin_per_volume_usd=Decimal("1"),
                provider_commission_per_volume_usd=Decimal("0"),
                provider_slippage_reserve_per_volume_usd=Decimal("0"),
                provider_bid=Decimal("20000"),
                provider_ask=Decimal("20001"),
                policy_record_sha256="sha256:" + "3" * 64,
                policy_selected=index < plan.minimum_selected_outcomes,
                baseline_policy_id=plan.baseline_policy_id,
                baseline_selected=True,
                execution_risk_evidence_id=f"risk-{index}",
                executed_risk_sha256="sha256:" + "4" * 64,
                executed_source_volume=Decimal("0.01"),
                executed_initial_stop_risk_usd=Decimal("1"),
                settlement_sha256="sha256:" + "5" * 64,
                settlement_deal_ids=(index + 1,),
                realized_net_pnl_usd=Decimal("2"),
                outcome_observed_at=decision_at + timedelta(minutes=10),
                release_evidence_sha256="sha256:" + "6" * 64,
                release_chain_sha256="sha256:" + "7" * 64,
                released_stop_risk_capacity_usd=Decimal("1"),
                released_margin_capacity_usd=Decimal("1"),
                terminal_release_at=decision_at + timedelta(minutes=9),
                capital_minutes=Decimal("9"),
            )
        )
    return ArchBForwardEconomicManifest(
        manifest_id=ARCH_B_FORWARD_ECONOMIC_MANIFEST_ID,
        frozen_candidate_id=frozen.candidate_id,
        frozen_code_sha=frozen.code_sha,
        frozen_parameter_sha256=frozen.parameter_sha256(),
        qualification_plan_id=plan.plan_id,
        qualification_plan_sha256=phase20d_qualification_plan_sha256(),
        baseline_policy_id=plan.baseline_policy_id,
        qualification_status="PASS",
        decision_epochs=plan.minimum_decision_epochs,
        candidate_rows=len(rows),
        complete_lineage_rows=len(rows),
        rows=tuple(rows),
        gaps=(),
        ready_for_scientific_consumption=True,
    )

def _prerequisites(*, passed: bool = True, inspected: bool = False):
    return tuple(
        CiboUsd60PrerequisiteEvidence(
            prerequisite_id=item,
            passed=passed,
            evidence_refs=(f"evidence:{item}",),
            observed_at=T0,
            holdout_outcomes_inspected=inspected,
        )
        for item in required_usd60_pre_exam_prerequisites()
    )


def test_pre_exam_gate_fails_closed_without_forward_population() -> None:
    report = assess_cibo_usd60_pre_exam_readiness(
        forward_manifest=_empty_manifest(),
        prerequisites=_prerequisites(),
    )

    assert report.forward_manifest_ready is False
    assert report.ready_for_governed_exam is False
    assert "USD60_PHASE20D_FORWARD_MANIFEST_NOT_READY" in report.blockers
    assert report.holdout_access_authority is False
    assert report.certification_ready is False
    assert report.productive_authority is False


def test_pre_exam_gate_can_be_ready_without_granting_holdout_access() -> None:
    report = assess_cibo_usd60_pre_exam_readiness(
        forward_manifest=_ready_manifest(),
        prerequisites=_prerequisites(),
    )

    assert report.ready_for_governed_exam is True
    assert report.blockers == ()
    assert report.holdout_access_authority is False
    assert report.certification_ready is False


def test_holdout_outcome_inspection_before_exam_is_hard_blocker() -> None:
    report = assess_cibo_usd60_pre_exam_readiness(
        forward_manifest=_ready_manifest(),
        prerequisites=_prerequisites(inspected=True),
    )

    assert report.ready_for_governed_exam is False
    assert (
        "USD60_PRE_EXAM_HOLDOUT_OUTCOMES_ALREADY_INSPECTED"
        in report.blockers
    )


def test_missing_or_failed_prerequisite_blocks_exam() -> None:
    prerequisites = list(_prerequisites())
    first = prerequisites[0]
    prerequisites[0] = CiboUsd60PrerequisiteEvidence(
        prerequisite_id=first.prerequisite_id,
        passed=False,
        evidence_refs=first.evidence_refs,
        observed_at=first.observed_at,
    )
    report = assess_cibo_usd60_pre_exam_readiness(
        forward_manifest=_ready_manifest(),
        prerequisites=tuple(prerequisites),
    )

    assert report.ready_for_governed_exam is False
    assert any(item.endswith("_NOT_PASSED") for item in report.blockers)
