from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)
from qore.infrastructure.cibo_ce2i_phase20_qualification import (
    Phase20QualificationRow,
)
from qore.infrastructure.cibo_ce2i_phase20_t09_t18_scarcity_readiness import (
    Phase20T09T18ScarcityReadiness,
)
from qore.infrastructure.cibo_ce2i_phase20_t09_t18_scarcity_utility import (
    assess_phase20_t09_t18_scarcity_utility,
)

BASE = datetime(2026, 9, 29, 5, 0, tzinfo=UTC)


def _readiness(*, ready: bool = True) -> Phase20T09T18ScarcityReadiness:
    shas = tuple("sha256:" + f"{index + 1:064x}" for index in range(32))
    blockers = (
        ()
        if ready
        else ("T09_SCARCITY_CANDIDATE_OUTCOME_COVERAGE_NOT_MET",)
    )
    return Phase20T09T18ScarcityReadiness(
        usable_forward_epochs=80,
        exact_competition_epochs=32,
        scarce_competition_epochs=32,
        cross_trader_scarce_epochs=32,
        scarcity_candidate_instances=64,
        scarcity_candidate_outcomes=64 if ready else 60,
        scarcity_selected_instances=32,
        scarcity_selected_outcomes=32,
        scarcity_candidate_outcome_coverage=(
            Decimal("1") if ready else Decimal("0.9375")
        ),
        scarcity_selected_outcome_coverage=Decimal("1"),
        represented_lineages=("R38_EURUSD", "R43_GBPUSD"),
        missing_policy_scarcity_epochs=0,
        t09_folds=(),
        t18_folds=(),
        t09_ready_for_utility_analysis=ready,
        t18_ready_for_utility_analysis=ready,
        fresh_oos_utility_demonstrated=False,
        t09_blockers=blockers,
        t18_blockers=blockers,
        t09_scarce_decision_sha256s=shas,
        t18_cross_trader_scarce_decision_sha256s=shas,
    )


def _rows(
    *,
    policy_pnl: Decimal = Decimal("2"),
    baseline_pnl: Decimal = Decimal("1"),
) -> tuple[Phase20QualificationRow, ...]:
    result: list[Phase20QualificationRow] = []
    for index in range(32):
        decision_at = BASE + timedelta(hours=index)
        sha = "sha256:" + f"{index + 1:064x}"
        result.extend(
            (
                Phase20QualificationRow(
                    decision_epoch_id=f"epoch-{index}",
                    decision_evidence_sha256=sha,
                    decision_at=decision_at,
                    signal_fingerprint=f"policy-{index}",
                    trader_id="R38_EURUSD",
                    stop_risk_usd=Decimal("5"),
                    margin_usd=Decimal("10"),
                    concentration_group="USD",
                    concentration_risk_usd=Decimal("5"),
                    expected_capital_minutes=Decimal("10"),
                    provider_cost_proxy_usd=Decimal("0"),
                    policy_selected=True,
                    baseline_selected=False,
                    realized_net_pnl_usd=policy_pnl,
                    executed_initial_stop_risk_usd=Decimal("5"),
                    realized_structural_outcome_r=policy_pnl / Decimal("5"),
                    capital_minutes=Decimal("10"),
                    outcome_observed_at=decision_at + timedelta(minutes=20),
                ),
                Phase20QualificationRow(
                    decision_epoch_id=f"epoch-{index}",
                    decision_evidence_sha256=sha,
                    decision_at=decision_at,
                    signal_fingerprint=f"baseline-{index}",
                    trader_id="R43_GBPUSD",
                    stop_risk_usd=Decimal("5"),
                    margin_usd=Decimal("10"),
                    concentration_group="USD",
                    concentration_risk_usd=Decimal("5"),
                    expected_capital_minutes=Decimal("20"),
                    provider_cost_proxy_usd=Decimal("0"),
                    policy_selected=False,
                    baseline_selected=True,
                    realized_net_pnl_usd=baseline_pnl,
                    executed_initial_stop_risk_usd=Decimal("5"),
                    realized_structural_outcome_r=baseline_pnl / Decimal("5"),
                    capital_minutes=Decimal("20"),
                    outcome_observed_at=decision_at + timedelta(minutes=25),
                ),
            )
        )
    return tuple(result)


def test_scarcity_utility_reuses_frozen_phase20d_gates() -> None:
    report = assess_phase20_t09_t18_scarcity_utility(
        qualification_rows=_rows(),
        scarcity_readiness=_readiness(),
    )

    assert report.outcome_refit_performed is False
    assert report.t09.fresh_oos_utility_demonstrated is True
    assert report.t18.fresh_oos_utility_demonstrated is True
    assert report.t09.policy_net_delta_usd == Decimal("64")
    assert report.t09.baseline_net_delta_usd == Decimal("32")
    assert report.t09.policy_capital_productivity > (
        report.t09.baseline_capital_productivity
    )
    assert report.t09.fold_policy_net_delta_usd == (
        Decimal("16"),
        Decimal("16"),
        Decimal("16"),
        Decimal("16"),
    )
    assert report.t09.blockers == ()


def test_scarcity_utility_fails_fixed_baseline_gate() -> None:
    report = assess_phase20_t09_t18_scarcity_utility(
        qualification_rows=_rows(
            policy_pnl=Decimal("0.5"),
            baseline_pnl=Decimal("1"),
        ),
        scarcity_readiness=_readiness(),
    )

    assert report.t09.fresh_oos_utility_demonstrated is False
    assert "T09_POLICY_DELTA_NOT_BELOW_FIXED_BASELINE" in report.t09.blockers
    assert report.t18.fresh_oos_utility_demonstrated is False


def test_scarcity_utility_does_not_score_unready_population() -> None:
    report = assess_phase20_t09_t18_scarcity_utility(
        qualification_rows=_rows(),
        scarcity_readiness=_readiness(ready=False),
    )

    assert report.t09.population_ready is False
    assert report.t09.fresh_oos_utility_demonstrated is False
    assert (
        "T09_SCARCITY_CANDIDATE_OUTCOME_COVERAGE_NOT_MET"
        in report.t09.blockers
    )


def test_scarcity_scope_rejects_noncanonical_fold_count() -> None:
    report = assess_phase20_t09_t18_scarcity_utility(
        qualification_rows=_rows(),
        scarcity_readiness=_readiness(),
    )

    with pytest.raises(
        CiboCapitalManagementError,
        match="report requires frozen fold count",
    ):
        replace(
            report.t09,
            fold_policy_net_delta_usd=(Decimal("1"), Decimal("1")),
        )
