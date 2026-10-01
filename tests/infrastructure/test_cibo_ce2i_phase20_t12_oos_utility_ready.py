from __future__ import annotations

from dataclasses import replace
from datetime import timedelta
from decimal import Decimal

import pytest

from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)
from qore.infrastructure.cibo_ce2i_phase20_qualification import (
    Phase20QualificationRow,
)
from qore.infrastructure.cibo_ce2i_phase20_t12_oos_readiness import (
    Phase20T12OosReadiness,
)
from qore.infrastructure.cibo_ce2i_phase20_t12_oos_utility import (
    assess_phase20_t12_oos_utility,
)
from qore.infrastructure.cibo_ce2i_phase20_t12_shadow_policy import (
    T12_SHADOW_POLICY_FROZEN_AT,
    t12_shadow_policy_sha256,
)
from qore.infrastructure.cibo_ce2i_phase20_t12_shadow_store import (
    T12ShadowDecisionSeal,
)

BASE = T12_SHADOW_POLICY_FROZEN_AT + timedelta(hours=1)
DECISION_COUNT = 80
CANDIDATES_PER_DECISION = 3


def _sha(index: int) -> str:
    return "sha256:" + f"{index:064x}"


def _readiness() -> Phase20T12OosReadiness:
    decisions = tuple(_sha(index + 1) for index in range(DECISION_COUNT))
    return Phase20T12OosReadiness(
        ready_for_utility_analysis=True,
        blockers=(),
        post_freeze_decision_epochs=DECISION_COUNT,
        pre_t12_freeze_decisions_excluded=0,
        shadow_sealed_epochs=DECISION_COUNT,
        missing_shadow_decisions=0,
        missing_treatment_policy_decisions=0,
        selection_changed_epochs=DECISION_COUNT,
        allocator_changed_epochs=DECISION_COUNT,
        candidate_instances=DECISION_COUNT * CANDIDATES_PER_DECISION,
        candidate_outcomes=DECISION_COUNT * CANDIDATES_PER_DECISION,
        candidate_outcome_coverage=Decimal("1"),
        treatment_selected_instances=DECISION_COUNT,
        treatment_selected_outcomes=DECISION_COUNT,
        treatment_selected_outcome_coverage=Decimal("1"),
        control_selected_instances=DECISION_COUNT,
        control_selected_outcomes=DECISION_COUNT,
        control_selected_outcome_coverage=Decimal("1"),
        treatment_only_instances=DECISION_COUNT,
        treatment_only_outcomes=DECISION_COUNT,
        control_only_instances=DECISION_COUNT,
        control_only_outcomes=DECISION_COUNT,
        calendar_span_days=30,
        distinct_trading_days=20,
        represented_lineages=7,
        minimum_outcomes_any_lineage=8,
        minimum_fold_candidate_outcomes=60,
        minimum_fold_lineages=4,
        minimum_fold_selection_changed_epochs=20,
        minimum_decision_epochs=80,
        minimum_candidate_outcomes=200,
        minimum_selected_outcomes=60,
        required_candidate_coverage=Decimal("0.95"),
        required_selected_coverage=Decimal("1"),
        fold_count=4,
        decision_sha256s=decisions,
        changed_decision_sha256s=decisions,
        fresh_oos_utility_demonstrated=False,
    )


def _shadows() -> tuple[T12ShadowDecisionSeal, ...]:
    result = []
    for index in range(DECISION_COUNT):
        decision_at = BASE + timedelta(hours=9 * index)
        treatment_signal = f"signal-{index}-0"
        control_signal = f"signal-{index}-1"
        result.append(
            T12ShadowDecisionSeal(
                shadow_decision_sha256=_sha(1000 + index),
                policy_sha256=t12_shadow_policy_sha256(),
                decision_epoch_id=f"epoch-{index}",
                decision_evidence_sha256=_sha(index + 1),
                baseline_policy_record_sha256=_sha(2000 + index),
                decision_at=decision_at,
                shadow_sealed_at=decision_at + timedelta(milliseconds=500),
                treatment_enabled_tools=("T01",),
                treatment_blocked_tools=("T08",),
                control_enabled_tools=("T01", "T08"),
                control_blocked_tools=(),
                treatment_allocator_disposition="ALLOCATE",
                control_allocator_disposition="ALLOCATE",
                treatment_allocator_applied_tools=("T01",),
                control_allocator_applied_tools=("T01", "T08"),
                treatment_selected_signal_fingerprints=(treatment_signal,),
                control_selected_signal_fingerprints=(control_signal,),
                selection_changed=True,
                allocator_changed=True,
            )
        )
    return tuple(result)


def _rows(
    *,
    treatment_pnl: Decimal = Decimal("2"),
    control_pnl: Decimal = Decimal("1"),
) -> tuple[Phase20QualificationRow, ...]:
    rows = []
    for index in range(DECISION_COUNT):
        decision_at = BASE + timedelta(hours=9 * index)
        for slot in range(CANDIDATES_PER_DECISION):
            signal = f"signal-{index}-{slot}"
            if slot == 0:
                pnl = treatment_pnl
            elif slot == 1:
                pnl = control_pnl
            else:
                pnl = Decimal("0")
            rows.append(
                Phase20QualificationRow(
                    decision_epoch_id=f"epoch-{index}",
                    decision_evidence_sha256=_sha(index + 1),
                    decision_at=decision_at,
                    signal_fingerprint=signal,
                    trader_id=f"TRADER-{slot}",
                    stop_risk_usd=Decimal("5"),
                    margin_usd=Decimal("100"),
                    concentration_group=f"group-{slot}",
                    concentration_risk_usd=Decimal("5"),
                    expected_capital_minutes=Decimal("10"),
                    provider_cost_proxy_usd=Decimal("0.10"),
                    policy_selected=slot == 0,
                    baseline_selected=slot == 1,
                    realized_net_pnl_usd=pnl,
                    executed_initial_stop_risk_usd=Decimal("5"),
                    realized_structural_outcome_r=pnl / Decimal("5"),
                    capital_minutes=Decimal("10"),
                    outcome_observed_at=decision_at + timedelta(hours=1),
                )
            )
    return tuple(rows)


def test_t12_utility_passes_fixed_four_fold_treatment() -> None:
    report = assess_phase20_t12_oos_utility(
        qualification_rows=_rows(),
        readiness=_readiness(),
        shadow_decisions=_shadows(),
    )

    assert report.fresh_oos_utility_demonstrated is True
    assert report.blockers == ()
    assert report.treatment_net_delta_usd == Decimal("160")
    assert report.control_net_delta_usd == Decimal("80")
    assert report.fold_incremental_net_delta_usd == (
        Decimal("20"),
        Decimal("20"),
        Decimal("20"),
        Decimal("20"),
    )
    assert (
        report.treatment_capital_productivity
        > report.control_capital_productivity
    )
    assert report.outcome_refit_performed is False
    assert report.runtime_authority is False


def test_t12_utility_rejects_no_strict_productivity_improvement() -> None:
    report = assess_phase20_t12_oos_utility(
        qualification_rows=_rows(treatment_pnl=Decimal("1")),
        readiness=_readiness(),
        shadow_decisions=_shadows(),
    )

    assert report.fresh_oos_utility_demonstrated is False
    assert (
        "T12_TREATMENT_CAPITAL_PRODUCTIVITY_STRICTLY_ABOVE_CONTROL"
        in report.blockers
    )


def test_t12_utility_rejects_incomplete_control_outcome_coverage() -> None:
    rows = list(_rows())
    target = next(
        index
        for index, row in enumerate(rows)
        if row.signal_fingerprint == "signal-0-1"
    )
    rows[target] = replace(
        rows[target],
        realized_net_pnl_usd=None,
        executed_initial_stop_risk_usd=None,
        realized_structural_outcome_r=None,
        capital_minutes=None,
        outcome_observed_at=None,
    )

    report = assess_phase20_t12_oos_utility(
        qualification_rows=tuple(rows),
        readiness=_readiness(),
        shadow_decisions=_shadows(),
    )

    assert report.fresh_oos_utility_demonstrated is False
    assert "T12_CONTROL_SELECTED_OUTCOME_COVERAGE_COMPLETE" in report.blockers


def test_t12_utility_rejects_treatment_selection_binding_drift() -> None:
    rows = list(_rows())
    rows[0] = replace(rows[0], policy_selected=False)

    with pytest.raises(
        CiboCapitalManagementError,
        match="treatment selection binding drift",
    ):
        assess_phase20_t12_oos_utility(
            qualification_rows=tuple(rows),
            readiness=_readiness(),
            shadow_decisions=_shadows(),
        )
