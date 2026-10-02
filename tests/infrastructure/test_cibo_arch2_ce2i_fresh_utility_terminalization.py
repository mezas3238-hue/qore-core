from decimal import Decimal

from qore.infrastructure.cibo_arch2_ce2i_fresh_utility_terminalization import (
    COMPLETED,
    FALSIFIED,
    terminalize_t08,
    terminalize_t12,
    terminalize_t13,
)
from qore.infrastructure.cibo_ce2i_phase20_qualification_plan import (
    FROZEN_PHASE20D_QUALIFICATION_PLAN,
)
from qore.infrastructure.cibo_ce2i_phase20_t08_oos_ablation import (
    T08NettingOosAblationReport,
)
from qore.infrastructure.cibo_ce2i_phase20_t12_oos_utility import (
    Phase20T12UtilityReport,
)
from qore.infrastructure.cibo_ce2i_phase20_t13_oos_utility import (
    Phase20T13UtilityReport,
)


def _fake(cls: type[object], **values: object) -> object:
    result = object.__new__(cls)
    for name, value in values.items():
        object.__setattr__(result, name, value)
    return result


def test_t08_sufficient_failed_evidence_is_falsification() -> None:
    report = _fake(
        T08NettingOosAblationReport,
        sample_size=30,
        minimum_epochs=30,
        required_folds=4,
        folds=(object(), object(), object(), object()),
        mapping_evidence_bound=True,
        correlation_evidence_bound=True,
        fresh_oos_utility_demonstrated=False,
        blockers=("T08_OOS_NO_INCREMENTAL_CAPITAL_UTILITY",),
    )

    result = terminalize_t08(report)  # type: ignore[arg-type]

    assert result.terminal_ready is True
    assert result.terminal_recommendation == FALSIFIED


def test_t08_missing_population_stays_external_dependency() -> None:
    report = _fake(
        T08NettingOosAblationReport,
        sample_size=0,
        minimum_epochs=30,
        required_folds=4,
        folds=(),
        mapping_evidence_bound=False,
        correlation_evidence_bound=False,
        fresh_oos_utility_demonstrated=False,
        blockers=(
            "T08_OOS_MINIMUM_EPOCHS_NOT_MET:0/30",
            "T08_OOS_FOLD_COVERAGE_NOT_MET:0/4",
            "T08_OOS_RISK_MAPPING_EVIDENCE_NOT_BOUND",
            "T08_OOS_CORRELATION_EVIDENCE_NOT_BOUND",
        ),
    )

    result = terminalize_t08(report)  # type: ignore[arg-type]

    assert result.terminal_ready is False
    assert result.terminal_recommendation is None
    assert result.remaining_blockers


def _t12(*, utility: bool, blockers: tuple[str, ...] = ()) -> Phase20T12UtilityReport:
    return _fake(
        Phase20T12UtilityReport,
        population_ready=True,
        candidate_instances=100,
        treatment_selected_instances=40,
        control_selected_instances=40,
        candidate_outcome_coverage=Decimal("1"),
        treatment_selected_outcome_coverage=Decimal("1"),
        control_selected_outcome_coverage=Decimal("1"),
        fold_treatment_net_delta_usd=(Decimal("1"),) * 4,
        fold_control_net_delta_usd=(Decimal("1"),) * 4,
        fresh_oos_utility_demonstrated=utility,
        outcome_refit_performed=False,
        blockers=blockers,
    )  # type: ignore[return-value]


def test_t12_complete_economic_failure_falsifies() -> None:
    report = _t12(
        utility=False,
        blockers=("T12_TREATMENT_CAPITAL_PRODUCTIVITY_STRICTLY_ABOVE_CONTROL",),
    )
    result = terminalize_t12(report)

    assert result.evidence_surface_complete is True
    assert result.terminal_recommendation == FALSIFIED


def test_t12_complete_pass_finishes() -> None:
    result = terminalize_t12(_t12(utility=True))

    assert result.terminal_recommendation == COMPLETED


def _t13(*, utility: bool, blockers: tuple[str, ...] = ()) -> Phase20T13UtilityReport:
    return _fake(
        Phase20T13UtilityReport,
        population_ready=True,
        candidate_instances=100,
        baseline_selected_instances=40,
        treatment_selected_instances=40,
        candidate_outcome_coverage=Decimal("1"),
        baseline_selected_outcome_coverage=Decimal("1"),
        treatment_selected_outcome_coverage=Decimal("1"),
        fold_baseline_net_delta_usd=(Decimal("1"),) * 4,
        fold_treatment_net_delta_usd=(Decimal("1"),) * 4,
        fresh_oos_utility_demonstrated=utility,
        outcome_refit_performed=False,
        blockers=blockers,
    )  # type: ignore[return-value]


def test_t13_complete_pass_finishes() -> None:
    result = terminalize_t13(_t13(utility=True))

    assert result.terminal_recommendation == COMPLETED
    assert result.remaining_blockers == ()


def test_t13_incomplete_execution_stays_open() -> None:
    result = terminalize_t13(
        _t13(
            utility=False,
            blockers=("T13_REALIZED_EXECUTION_ECONOMICS_COMPLETE",),
        )
    )

    assert result.terminal_ready is False
    assert result.terminal_recommendation is None
    assert (
        result.remaining_blockers
        == ("T13_REALIZED_EXECUTION_ECONOMICS_COMPLETE",)
    )


def test_phase20_threshold_assumptions_remain_frozen() -> None:
    assert (
        FROZEN_PHASE20D_QUALIFICATION_PLAN.minimum_candidate_outcome_coverage
        == Decimal("0.95")
    )
    assert FROZEN_PHASE20D_QUALIFICATION_PLAN.fold_count == 4
