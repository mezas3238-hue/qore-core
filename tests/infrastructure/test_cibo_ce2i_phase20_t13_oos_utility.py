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
from qore.infrastructure.cibo_ce2i_phase20_t13_oos_readiness import (
    Phase20T13OosReadiness,
)
from qore.infrastructure.cibo_ce2i_phase20_t13_oos_utility import (
    assess_phase20_t13_oos_utility,
)
from qore.infrastructure.cibo_ce2i_phase20_t13_shadow_policy import (
    T13_SHADOW_POLICY_FROZEN_AT,
    t13_shadow_policy_sha256,
)
from qore.infrastructure.cibo_ce2i_phase20_t13_shadow_treatment_store import (
    T13ShadowTreatmentSeal,
)

BASE = T13_SHADOW_POLICY_FROZEN_AT + timedelta(hours=1)
DECISION_COUNT = 80
CANDIDATES_PER_DECISION = 3


def _sha(index: int) -> str:
    return "sha256:" + f"{index:064x}"


def _readiness() -> Phase20T13OosReadiness:
    decisions = tuple(_sha(index + 1) for index in range(DECISION_COUNT))
    changed = decisions[:20]
    return Phase20T13OosReadiness(
        ready_for_utility_analysis=True,
        blockers=(),
        post_freeze_decision_epochs=DECISION_COUNT,
        pre_t13_freeze_decisions_excluded=0,
        treatment_sealed_epochs=DECISION_COUNT,
        missing_treatment_decisions=0,
        missing_baseline_policy_decisions=0,
        selection_changed_epochs=20,
        candidate_instances=DECISION_COUNT * CANDIDATES_PER_DECISION,
        candidate_outcomes=DECISION_COUNT * CANDIDATES_PER_DECISION,
        candidate_outcome_coverage=Decimal("1"),
        baseline_selected_instances=DECISION_COUNT,
        baseline_selected_outcomes=DECISION_COUNT,
        baseline_selected_outcome_coverage=Decimal("1"),
        treatment_selected_instances=DECISION_COUNT,
        treatment_selected_outcomes=DECISION_COUNT,
        treatment_selected_outcome_coverage=Decimal("1"),
        baseline_only_instances=20,
        baseline_only_outcomes=20,
        treatment_only_instances=20,
        treatment_only_outcomes=20,
        calendar_span_days=30,
        distinct_trading_days=20,
        represented_lineages=7,
        minimum_outcomes_any_lineage=8,
        minimum_fold_candidate_outcomes=60,
        minimum_fold_lineages=4,
        minimum_decision_epochs=80,
        minimum_candidate_outcomes=200,
        minimum_selected_outcomes=60,
        required_candidate_coverage=Decimal("0.95"),
        required_selected_coverage=Decimal("1"),
        fold_count=4,
        decision_sha256s=decisions,
        changed_decision_sha256s=changed,
        fresh_oos_utility_demonstrated=False,
    )


def _treatments() -> tuple[T13ShadowTreatmentSeal, ...]:
    result = []
    for index in range(DECISION_COUNT):
        decision_at = BASE + timedelta(hours=9 * index)
        evidence_sha = _sha(index + 1)
        baseline_signal = f"signal-{index}-0"
        changed = index < 20
        treatment_signal = (
            f"signal-{index}-1" if changed else baseline_signal
        )
        result.append(
            T13ShadowTreatmentSeal(
                treatment_sha256=_sha(1000 + index),
                recommendation_sha256=_sha(2000 + index),
                decision_epoch_id=f"epoch-{index}",
                decision_evidence_sha256=evidence_sha,
                baseline_policy_record_sha256=_sha(3000 + index),
                t13_policy_sha256=t13_shadow_policy_sha256(),
                decision_at=decision_at,
                treatment_sealed_at=decision_at + timedelta(milliseconds=500),
                reserve_triggered=changed,
                shadow_reserved_risk_usd=(
                    Decimal("10") if changed else Decimal("0")
                ),
                baseline_allocator_input_stop_risk_usd=Decimal("20"),
                treatment_allocator_input_stop_risk_usd=(
                    Decimal("10") if changed else Decimal("20")
                ),
                allocator_input_margin_usd=Decimal("100"),
                baseline_selected_signal_fingerprints=(baseline_signal,),
                treatment_selected_signal_fingerprints=(treatment_signal,),
                baseline_only_signal_fingerprints=(
                    (baseline_signal,) if changed else ()
                ),
                treatment_only_signal_fingerprints=(
                    (treatment_signal,) if changed else ()
                ),
                selection_changed=changed,
            )
        )
    return tuple(result)


def _rows(
    *,
    treatment_only_pnl: Decimal = Decimal("2"),
) -> tuple[Phase20QualificationRow, ...]:
    rows = []
    for index in range(DECISION_COUNT):
        decision_at = BASE + timedelta(hours=9 * index)
        evidence_sha = _sha(index + 1)
        for slot in range(CANDIDATES_PER_DECISION):
            signal = f"signal-{index}-{slot}"
            if slot == 0:
                pnl = Decimal("1")
            elif slot == 1:
                pnl = treatment_only_pnl
            else:
                pnl = Decimal("0")
            rows.append(
                Phase20QualificationRow(
                    decision_epoch_id=f"epoch-{index}",
                    decision_evidence_sha256=evidence_sha,
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
                    baseline_selected=slot == 0,
                    realized_net_pnl_usd=pnl,
                    executed_initial_stop_risk_usd=Decimal("5"),
                    realized_structural_outcome_r=pnl / Decimal("5"),
                    capital_minutes=Decimal("10"),
                    outcome_observed_at=decision_at + timedelta(hours=1),
                )
            )
    return tuple(rows)


def test_t13_utility_passes_fixed_positive_four_fold_treatment() -> None:
    report = assess_phase20_t13_oos_utility(
        qualification_rows=_rows(),
        readiness=_readiness(),
        treatment_decisions=_treatments(),
    )

    assert report.fresh_oos_utility_demonstrated is True
    assert report.blockers == ()
    assert report.baseline_net_delta_usd == Decimal("80")
    assert report.treatment_net_delta_usd == Decimal("100")
    assert report.treatment_settlement_cash_drawdown_usd == Decimal("0")
    assert (
        report.treatment_capital_productivity
        > report.baseline_capital_productivity
    )
    assert report.fold_treatment_net_delta_usd == (
        Decimal("40"),
        Decimal("20"),
        Decimal("20"),
        Decimal("20"),
    )
    assert report.outcome_refit_performed is False
    assert report.runtime_authority is False


def test_t13_utility_rejects_no_strict_productivity_improvement() -> None:
    report = assess_phase20_t13_oos_utility(
        qualification_rows=_rows(treatment_only_pnl=Decimal("1")),
        readiness=_readiness(),
        treatment_decisions=_treatments(),
    )

    assert report.fresh_oos_utility_demonstrated is False
    assert (
        "T13_TREATMENT_CAPITAL_PRODUCTIVITY_STRICTLY_ABOVE_BASELINE"
        in report.blockers
    )


def test_t13_utility_rejects_incomplete_treatment_outcome_coverage() -> None:
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

    report = assess_phase20_t13_oos_utility(
        qualification_rows=tuple(rows),
        readiness=_readiness(),
        treatment_decisions=_treatments(),
    )

    assert report.fresh_oos_utility_demonstrated is False
    assert (
        "T13_TREATMENT_SELECTED_OUTCOME_COVERAGE_COMPLETE"
        in report.blockers
    )


def test_t13_utility_rejects_baseline_selection_binding_drift() -> None:
    rows = list(_rows())
    rows[0] = replace(rows[0], policy_selected=False)

    with pytest.raises(
        CiboCapitalManagementError,
        match="baseline selection binding drift",
    ):
        assess_phase20_t13_oos_utility(
            qualification_rows=tuple(rows),
            readiness=_readiness(),
            treatment_decisions=_treatments(),
        )
