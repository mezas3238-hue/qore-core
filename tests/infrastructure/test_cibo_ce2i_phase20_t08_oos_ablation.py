from dataclasses import replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)
from qore.infrastructure.cibo_ce2i_phase20_t08_oos_ablation import (
    T08NettingShadowEpoch,
    assess_t08_fresh_oos_netting_ablation,
)

BASE = datetime(2026, 9, 29, 1, tzinfo=UTC)


def _epoch(
    index: int,
    *,
    baseline_pnl: Decimal = Decimal("1"),
    treatment_pnl: Decimal = Decimal("1.2"),
    baseline_selected: int = 1,
    treatment_selected: int = 2,
    treatment_peak_loss: Decimal = Decimal("4"),
    treatment_netted_risk: Decimal = Decimal("8"),
) -> T08NettingShadowEpoch:
    decision_at = BASE + timedelta(minutes=5 * index)
    return T08NettingShadowEpoch(
        epoch_id=f"epoch-{index:03d}",
        decision_at=decision_at,
        shadow_sealed_at=decision_at + timedelta(milliseconds=100),
        outcome_observed_at=decision_at + timedelta(hours=2),
        baseline_selected_count=baseline_selected,
        treatment_selected_count=treatment_selected,
        baseline_realized_net_pnl_usd=baseline_pnl,
        treatment_realized_net_pnl_usd=treatment_pnl,
        baseline_peak_loss_usd=Decimal("5"),
        treatment_peak_loss_usd=treatment_peak_loss,
        treatment_gross_stop_risk_usd=Decimal("10"),
        treatment_netted_risk_usd=treatment_netted_risk,
        netting_credit_usd=Decimal("10") - treatment_netted_risk,
        risk_mapping_evidence_id=f"risk-map:{index}",
        correlation_evidence_id=f"corr:{index}",
        outcome_evidence_ids=(f"outcome:{index}:a", f"outcome:{index}:b"),
    )


def test_fresh_oos_ablation_can_demonstrate_utility_without_authorizing_runtime() -> None:
    report = assess_t08_fresh_oos_netting_ablation(
        tuple(_epoch(index) for index in range(32))
    )

    assert report.sample_size == 32
    assert len(report.folds) == 4
    assert all(fold.epoch_count == 8 for fold in report.folds)
    assert report.incremental_selected_count == 32
    assert report.treatment_total_pnl_usd > report.baseline_total_pnl_usd
    assert report.treatment_max_drawdown_usd <= report.baseline_max_drawdown_usd
    assert report.pathwise_authorization_respected is True
    assert report.fresh_oos_utility_demonstrated is True
    assert report.risk_mapping_verified is False
    assert report.correlation_state_verified is False
    assert report.netting_credit_authorized is False
    assert (
        "SIGNED_FACTOR_RISK_MAP_REQUIRES_INDEPENDENT_CERTIFICATION"
        in report.blockers
    )


def test_oos_ablation_fails_when_treatment_breaches_netted_risk() -> None:
    epochs = tuple(
        _epoch(
            index,
            treatment_peak_loss=Decimal("9") if index == 31 else Decimal("4"),
        )
        for index in range(32)
    )

    report = assess_t08_fresh_oos_netting_ablation(epochs)

    assert report.pathwise_authorization_respected is False
    assert report.fresh_oos_utility_demonstrated is False
    assert "T08_OOS_NETTED_RISK_AUTHORIZATION_BREACHED" in report.blockers


def test_oos_ablation_requires_incremental_capital_utility() -> None:
    report = assess_t08_fresh_oos_netting_ablation(
        tuple(
            _epoch(
                index,
                treatment_selected=1,
                treatment_pnl=Decimal("1"),
            )
            for index in range(32)
        )
    )

    assert report.incremental_selected_count == 0
    assert report.fresh_oos_utility_demonstrated is False
    assert "T08_OOS_NO_INCREMENTAL_CAPITAL_UTILITY" in report.blockers


def test_oos_ablation_rejects_treatment_drawdown_degradation() -> None:
    epochs = tuple(
        _epoch(
            index,
            baseline_pnl=Decimal("1"),
            treatment_pnl=(
                Decimal("-3") if index in {7, 15, 23, 31} else Decimal("1.2")
            ),
        )
        for index in range(32)
    )

    report = assess_t08_fresh_oos_netting_ablation(epochs)

    assert report.treatment_max_drawdown_usd > report.baseline_max_drawdown_usd
    assert report.fresh_oos_utility_demonstrated is False
    assert "T08_OOS_TREATMENT_DRAWDOWN_WORSE_THAN_BASELINE" in report.blockers


def test_shadow_epoch_rejects_credit_above_frozen_half_ceiling() -> None:
    decision_at = BASE
    with pytest.raises(
        CiboCapitalManagementError,
        match="exceeds frozen 50% ceiling",
    ):
        T08NettingShadowEpoch(
            epoch_id="too-much-credit",
            decision_at=decision_at,
            shadow_sealed_at=decision_at + timedelta(milliseconds=10),
            outcome_observed_at=decision_at + timedelta(hours=1),
            baseline_selected_count=1,
            treatment_selected_count=2,
            baseline_realized_net_pnl_usd=Decimal(0),
            treatment_realized_net_pnl_usd=Decimal(0),
            baseline_peak_loss_usd=Decimal(1),
            treatment_peak_loss_usd=Decimal(1),
            treatment_gross_stop_risk_usd=Decimal("10"),
            treatment_netted_risk_usd=Decimal("4"),
            netting_credit_usd=Decimal("6"),
            risk_mapping_evidence_id="risk-map",
            correlation_evidence_id="corr",
            outcome_evidence_ids=("outcome",),
        )


def test_oos_ablation_rejects_duplicate_epoch_identity() -> None:
    epoch = _epoch(0)

    with pytest.raises(
        CiboCapitalManagementError,
        match="epoch ids must be unique",
    ):
        assess_t08_fresh_oos_netting_ablation((epoch, epoch))


def test_oos_ablation_rejects_noncanonical_fold_count() -> None:
    with pytest.raises(
        CiboCapitalManagementError,
        match="required_folds must be exactly four",
    ):
        assess_t08_fresh_oos_netting_ablation(
            tuple(_epoch(index) for index in range(16)),
            required_folds=2,
        )


def test_oos_report_rejects_noncanonical_direct_fold_count() -> None:
    report = assess_t08_fresh_oos_netting_ablation(
        tuple(_epoch(index) for index in range(32))
    )

    with pytest.raises(
        CiboCapitalManagementError,
        match="report requires exactly four temporal folds",
    ):
        replace(report, required_folds=2)
