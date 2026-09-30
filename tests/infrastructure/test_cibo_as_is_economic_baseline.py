from __future__ import annotations

from dataclasses import replace
from datetime import timedelta
from decimal import Decimal

import pytest

from qore.infrastructure.account_wide_risk import TraderLineage
from qore.infrastructure.cibo_as_is_economic_baseline import (
    AS_IS_CONTROL_GIT_SHA,
    AS_IS_CONTROL_ID,
    as_is_economic_baseline_sha256,
    materialize_as_is_economic_baseline,
)
from qore.infrastructure.cibo_ce2i_phase20_policy_candidate import (
    FROZEN_PHASE20_POLICY_CANDIDATE,
)
from qore.infrastructure.cibo_ce2i_phase20_qualification import (
    Phase20QualificationFold,
    Phase20QualificationReport,
    Phase20QualificationRow,
    Phase20QualificationStatus,
)
from qore.infrastructure.cibo_ce2i_phase20_qualification_plan import (
    FROZEN_PHASE20D_QUALIFICATION_PLAN,
    phase20d_qualification_plan_sha256,
)
from qore.infrastructure.cibo_ce2i_phase20_qualification_readiness import (
    Phase20QualificationReadiness,
)
from qore.infrastructure.cibo_compound_capital import CiboCompoundCapitalError
from qore.infrastructure.cibo_compound_real_population_binding import (
    CompoundPopulationEvidenceKind,
    ForwardCompoundEconomicRecord,
)

T0 = FROZEN_PHASE20_POLICY_CANDIDATE.frozen_at + timedelta(days=40)
LINEAGES = tuple(TraderLineage)[:7]


def _sha(char: str) -> str:
    return "sha256:" + char * 64


def _decision_at(epoch: int):
    return T0 + timedelta(days=(epoch * 27) // 79, minutes=epoch)


def _rows() -> tuple[Phase20QualificationRow, ...]:
    rows: list[Phase20QualificationRow] = []
    for index in range(200):
        epoch = index % 80
        selected = index < 100
        baseline = index >= 100
        pnl = Decimal("2") if selected else Decimal("1")
        decision_at = _decision_at(epoch)
        rows.append(
            Phase20QualificationRow(
                decision_epoch_id=f"epoch-{epoch:03d}",
                decision_evidence_sha256=_sha(f"{index % 10:x}"),
                decision_at=decision_at,
                signal_fingerprint=f"sig-{index:03d}",
                trader_id=LINEAGES[index % len(LINEAGES)].value,
                stop_risk_usd=Decimal("1"),
                margin_usd=Decimal("4"),
                concentration_group="index-risk",
                concentration_risk_usd=Decimal("1"),
                expected_capital_minutes=Decimal("60"),
                provider_cost_proxy_usd=Decimal("0.10"),
                policy_selected=selected,
                baseline_selected=baseline,
                realized_net_pnl_usd=pnl,
                executed_initial_stop_risk_usd=Decimal("1"),
                realized_structural_outcome_r=pnl,
                capital_minutes=Decimal("60"),
                outcome_observed_at=decision_at + timedelta(minutes=61),
            )
        )
    return tuple(rows)


def _readiness() -> Phase20QualificationReadiness:
    return Phase20QualificationReadiness(
        ready=True,
        reasons=(),
        decision_epochs=80,
        candidate_instances=200,
        candidate_outcomes=200,
        selected_instances=100,
        selected_outcomes=100,
        candidate_outcome_coverage=Decimal("1"),
        selected_outcome_coverage=Decimal("1"),
        calendar_span_days=28,
        distinct_trading_days=28,
        represented_lineages=7,
        minimum_outcomes_any_lineage=28,
        minimum_fold_candidate_outcomes=50,
        minimum_fold_lineages=7,
        missing_policy_decisions=0,
        pre_freeze_decisions=0,
    )


def _folds() -> tuple[Phase20QualificationFold, ...]:
    return tuple(
        Phase20QualificationFold(
            fold_id=f"WF{index}",
            decision_epoch_count=20,
            candidate_count=50,
            policy_selected_count=25,
            baseline_selected_count=25,
            policy_net_delta_usd=Decimal("50"),
            baseline_net_delta_usd=Decimal("25"),
        )
        for index in range(1, 5)
    )


def _report(
    *,
    status: Phase20QualificationStatus = Phase20QualificationStatus.PASS,
    failures: tuple[str, ...] = (),
) -> Phase20QualificationReport:
    rows = _rows()
    return Phase20QualificationReport(
        status=status,
        plan_id=FROZEN_PHASE20D_QUALIFICATION_PLAN.plan_id,
        plan_sha256=phase20d_qualification_plan_sha256(),
        candidate_id=FROZEN_PHASE20D_QUALIFICATION_PLAN.candidate_id,
        readiness=_readiness(),
        failures=failures,
        rows=rows,
        folds=_folds(),
        policy_net_delta_usd=Decimal("200"),
        baseline_net_delta_usd=Decimal("100"),
        policy_settlement_cash_drawdown_usd=Decimal("0"),
        baseline_settlement_cash_drawdown_usd=Decimal("0"),
        policy_capital_productivity=Decimal("200") / Decimal("6000"),
        baseline_capital_productivity=Decimal("100") / Decimal("6000"),
        policy_acceptance_rate=Decimal("0.5"),
        baseline_acceptance_rate=Decimal("0.5"),
        policy_selected_outcome_coverage=Decimal("1"),
        baseline_selected_outcome_coverage=Decimal("1"),
        candidate_outcome_coverage=Decimal("1"),
        capital_utilization=Decimal("0.50"),
        capital_starvation_rate=Decimal("0.10"),
        mpc_reserve_efficiency=Decimal("0.80"),
        optionality_preserved_rate=Decimal("0.90"),
        concentration_utilization=Decimal("0.40"),
        provider_failure_incidence=Decimal("0"),
        evidence_missingness=Decimal("0"),
        advanced_ce2i_applied_rate=Decimal("0.50"),
        advanced_ce2i_abstention_rate=Decimal("0.50"),
        advanced_ce2i_fail_closed_rate=Decimal("0"),
    )


def _record(
    row: Phase20QualificationRow,
    *,
    fold_id: str,
    suffix: str,
) -> ForwardCompoundEconomicRecord:
    return ForwardCompoundEconomicRecord(
        episode_id=f"episode-{suffix}",
        deployment_id=f"deployment-{suffix}",
        market_event_id=f"market-{suffix}",
        decision_id=row.decision_epoch_id,
        candidate_id=FROZEN_PHASE20_POLICY_CANDIDATE.candidate_id,
        trader_id=TraderLineage(row.trader_id),
        signal_fingerprint=row.signal_fingerprint,
        account_identity_fingerprint="account-fingerprint",
        qualification_fold_id=fold_id,
        decision_at=row.decision_at,
        deployed_at=row.decision_at + timedelta(minutes=1),
        settled_at=row.decision_at + timedelta(minutes=61),
        source_generation=1,
        deployed_capital_usd=Decimal("10"),
        stop_risk_usd=row.stop_risk_usd,
        margin_usd=row.margin_usd,
        realized_pnl_usd=row.realized_net_pnl_usd or Decimal("0"),
        protected_floor_graduation_usd=Decimal("0"),
        decision_evidence_sha256=_sha("a"),
        provider_economics_sha256=_sha("b"),
        risk_lineage_sha256=_sha("c"),
        cma_lineage_sha256=_sha("d"),
        terminal_settlement_sha256=_sha("e"),
        release_evidence_sha256=_sha("f"),
        source_manifest_sha256=_sha("9"),
        frozen_candidate_id=FROZEN_PHASE20_POLICY_CANDIDATE.candidate_id,
        frozen_candidate_code_sha=FROZEN_PHASE20_POLICY_CANDIDATE.code_sha,
        evidence_kind=CompoundPopulationEvidenceKind.FORWARD_OBSERVED,
    )


def _compound_records(
    report: Phase20QualificationReport,
) -> tuple[ForwardCompoundEconomicRecord, ...]:
    by_signal = {row.signal_fingerprint: row for row in report.rows}
    selected = (
        by_signal["sig-000"],
        by_signal["sig-025"],
        by_signal["sig-050"],
        by_signal["sig-079"],
    )
    return tuple(
        _record(row, fold_id=f"WF{index}", suffix=str(index))
        for index, row in enumerate(selected, start=1)
    )


def test_as_is_materializes_ready_provider_valid_population() -> None:
    report = _report()
    result = materialize_as_is_economic_baseline(
        report=report,
        compound_records=_compound_records(report),
    )

    assert result.control_id == AS_IS_CONTROL_ID
    assert result.control_git_sha == AS_IS_CONTROL_GIT_SHA
    assert result.qualification_status is Phase20QualificationStatus.PASS
    assert result.decision_epoch_count == 80
    assert result.candidate_row_count == 200
    assert result.fold_ids == ("WF1", "WF2", "WF3", "WF4")
    assert result.policy_net_delta_usd == Decimal("200")
    assert result.baseline_net_delta_usd == Decimal("100")
    assert result.compound_episode_count == 4
    assert result.gross_compound_deployment_usd == Decimal("40")
    assert result.compound_realized_net_pnl_usd == Decimal("8")
    assert result.compound_capital_minutes_usd == Decimal("2400")
    assert result.compound_stop_risk_minutes_usd == Decimal("240")
    assert result.compound_margin_minutes_usd == Decimal("960")
    assert result.synthetic_values_used is False
    assert result.treatment_effect_claimed is False
    assert result.certification_ready is False
    assert as_is_economic_baseline_sha256(result).startswith("sha256:")


def test_as_is_preserves_economic_fail_as_measurement_not_data_invalidity() -> None:
    report = _report(
        status=Phase20QualificationStatus.FAIL,
        failures=("POLICY_CAPITAL_PRODUCTIVITY_STRICTLY_ABOVE_FIXED_BASELINE",),
    )

    result = materialize_as_is_economic_baseline(
        report=report,
        compound_records=_compound_records(report),
    )

    assert result.qualification_status is Phase20QualificationStatus.FAIL
    assert result.qualification_failures == (
        "POLICY_CAPITAL_PRODUCTIVITY_STRICTLY_ABOVE_FIXED_BASELINE",
    )
    assert result.certification_ready is False


@pytest.mark.parametrize(
    "status",
    (
        Phase20QualificationStatus.NOT_READY,
        Phase20QualificationStatus.INVALID,
    ),
)
def test_as_is_rejects_nonqualifying_population_state(status) -> None:
    report = _report(status=status, failures=("not-ready",))

    with pytest.raises(
        CiboCompoundCapitalError,
        match="causally ready non-invalid population",
    ):
        materialize_as_is_economic_baseline(
            report=report,
            compound_records=_compound_records(report),
        )


def test_as_is_rejects_readiness_summary_drift() -> None:
    report = _report()
    report = replace(
        report,
        readiness=replace(report.readiness, candidate_outcomes=199),
    )

    with pytest.raises(
        CiboCompoundCapitalError,
        match="readiness/report consistency drift",
    ):
        materialize_as_is_economic_baseline(
            report=report,
            compound_records=_compound_records(report),
        )


def test_as_is_rejects_aggregate_metric_drift() -> None:
    report = replace(_report(), policy_net_delta_usd=Decimal("201"))

    with pytest.raises(
        CiboCompoundCapitalError,
        match="aggregate/report reconciliation drift",
    ):
        materialize_as_is_economic_baseline(
            report=report,
            compound_records=_compound_records(report),
        )


def test_as_is_rejects_compound_pnl_lineage_drift() -> None:
    report = _report()
    records = _compound_records(report)
    records = (
        replace(records[0], realized_pnl_usd=Decimal("3")),
        *records[1:],
    )

    with pytest.raises(
        CiboCompoundCapitalError,
        match="realized PnL lineage drift",
    ):
        materialize_as_is_economic_baseline(
            report=report,
            compound_records=records,
        )


def test_as_is_rejects_compound_risk_lineage_drift() -> None:
    report = _report()
    records = _compound_records(report)
    records = (
        replace(records[0], stop_risk_usd=Decimal("2")),
        *records[1:],
    )

    with pytest.raises(
        CiboCompoundCapitalError,
        match="Trader/risk/margin lineage drift",
    ):
        materialize_as_is_economic_baseline(
            report=report,
            compound_records=records,
        )


def test_as_is_rejects_missing_four_fold_compound_binding() -> None:
    report = _report()
    records = _compound_records(report)[:3]

    with pytest.raises(
        CiboCompoundCapitalError,
        match="all four frozen temporal folds",
    ):
        materialize_as_is_economic_baseline(
            report=report,
            compound_records=records,
        )
