from datetime import UTC, datetime
from decimal import Decimal

from qore.infrastructure.account_wide_risk import TraderLineage
from qore.infrastructure.cibo_arch2_t02_economic_ablation import (
    PROTOCOL_ID,
    T02EconomicAblationResult,
    T02EconomicFoldResult,
)
from qore.infrastructure.cibo_arch2_t02_terminal_disposition import (
    COMPLETED,
    FALSIFIED,
    WAITING_ABLATION,
    WAITING_STRUCTURAL,
    assess_t02_terminal_disposition,
)
from qore.infrastructure.cibo_ce2i_phase20_t02_structural_oos import (
    T02_FORWARD_STRUCTURAL_AUDIT_ID,
    T02_FORWARD_STRUCTURAL_FROZEN_AT,
    T02ForwardLineageAudit,
    T02ForwardStructuralAudit,
)


def _lineage(*, sample: bool = True, passed: bool = True) -> T02ForwardLineageAudit:
    return T02ForwardLineageAudit(
        lineage=TraderLineage.R38_EURUSD,
        selected_field="side",
        selected_value="long",
        baseline_outcomes=60 if sample else 5,
        candidate_outcomes=30 if sample else 5,
        baseline_stop_rate=Decimal("0.5"),
        candidate_stop_rate=Decimal("0.4") if passed else Decimal("0.6"),
        baseline_p95_loss_r=Decimal("1"),
        candidate_p95_loss_r=Decimal("1"),
        provider_binding_complete=True,
        minimum_sample_met=sample,
        strict_stop_rate_improvement=passed,
        tail_loss_not_worse=True,
        fresh_structural_precision_demonstrated=sample and passed,
    )


def _structural(*, sample: bool = True, passed: bool = True) -> T02ForwardStructuralAudit:
    line = _lineage(sample=sample, passed=passed)
    demonstrated = line.fresh_structural_precision_demonstrated
    return T02ForwardStructuralAudit(
        audit_id=T02_FORWARD_STRUCTURAL_AUDIT_ID,
        frozen_at=T02_FORWARD_STRUCTURAL_FROZEN_AT,
        lineages=(line,),
        fresh_structural_precision_demonstrated=demonstrated,
        ready_for_provider_bound_leverage_ablation=demonstrated,
        runtime_authority=False,
        blockers=(),
    )


def _economic(*, passed: bool) -> T02EconomicAblationResult:
    folds = tuple(
        T02EconomicFoldResult(
            fold_index=index,
            pair_count=8,
            incremental_net_pnl_usd=Decimal("1") if passed else Decimal("-1"),
            incremental_stop_risk_usd=Decimal("2"),
            incremental_return_on_risk=(
                Decimal("0.5") if passed else Decimal("-0.5")
            ),
            baseline_p95_adverse_r=Decimal("1"),
            treatment_p95_adverse_r=Decimal("1"),
            economic_value_positive=passed,
            normalized_tail_nonworse=True,
            pass_gate=passed,
        )
        for index in range(1, 5)
    )
    return T02EconomicAblationResult(
        protocol_id=PROTOCOL_ID,
        fold_results=folds,
        four_of_four_pass=passed,
        provider_bound_economic_value_proven=passed,
        productive_authority=False,
    )


def test_t02_waits_only_when_structural_population_is_insufficient() -> None:
    result = assess_t02_terminal_disposition(
        structural=_structural(sample=False),
        economic=None,
    )

    assert result.terminal_ready is False
    assert result.waiting_reason == WAITING_STRUCTURAL


def test_t02_sufficient_structural_failure_is_terminal_falsification() -> None:
    result = assess_t02_terminal_disposition(
        structural=_structural(passed=False),
        economic=None,
    )

    assert result.terminal_ready is True
    assert result.recommendation == FALSIFIED


def test_t02_structural_pass_waits_for_economic_ablation() -> None:
    result = assess_t02_terminal_disposition(
        structural=_structural(),
        economic=None,
    )

    assert result.terminal_ready is False
    assert result.waiting_reason == WAITING_ABLATION


def test_t02_economic_4_of_4_pass_completes() -> None:
    result = assess_t02_terminal_disposition(
        structural=_structural(),
        economic=_economic(passed=True),
    )

    assert result.terminal_ready is True
    assert result.recommendation == COMPLETED


def test_t02_economic_failure_is_terminal_falsification() -> None:
    result = assess_t02_terminal_disposition(
        structural=_structural(),
        economic=_economic(passed=False),
    )

    assert result.terminal_ready is True
    assert result.recommendation == FALSIFIED
