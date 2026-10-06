from decimal import Decimal

from qore.infrastructure.account_wide_risk import TraderLineage
from qore.infrastructure.cibo_arch2_t11_gross_edge_oos import (
    T11GrossEdgeFoldResult,
    T11GrossEdgeFreshOOSResult,
    T11GrossEdgeSymbolResult,
)
from qore.infrastructure.cibo_arch2_t11_market_impact_evaluator import (
    T11MarketImpactEvaluation,
    T11MarketImpactFoldResult,
    T11MarketImpactSymbolResult,
)
from qore.infrastructure.cibo_arch2_t11_nonlinear_input_freeze import (
    REQUIRED_SYMBOLS,
)
from qore.infrastructure.cibo_arch2_t11_terminal_disposition import (
    T11TerminalRecommendation,
    assess_t11_terminal_disposition,
)
from qore.infrastructure.cibo_ce2i_phase20_train_prior import prior_digest_sha256


def _impact(*, ready: bool) -> T11MarketImpactEvaluation:
    fold_results = tuple(
        T11MarketImpactFoldResult(
            fold_index=index,
            quadratic_mae_usd=Decimal("0.01"),
            linear_only_mae_usd=(
                Decimal("0.02") if ready else Decimal("0.005")
            ),
            quadratic_nonworse=ready,
        )
        for index in range(1, 5)
    )
    symbols = tuple(
        T11MarketImpactSymbolResult(
            qore_symbol=symbol,
            minimum_volume=Decimal("0.01"),
            linear_cost_per_volume_usd=Decimal("1"),
            impact_cost_per_volume_squared_usd=Decimal("0"),
            calibration_pairs=8,
            validation_pairs=4,
            fold_results=fold_results,
            four_of_four_validated=ready,
            calibrated=True,
            fresh_oos_validated=ready,
        )
        for symbol in REQUIRED_SYMBOLS
    )
    return T11MarketImpactEvaluation(
        symbols=symbols,
        required_symbol_coverage_complete=True,
        market_impact_model_ready=ready,
    )


def _gross_edge(*, ready: bool) -> T11GrossEdgeFreshOOSResult:
    lineages = tuple(sorted(item.value for item in TraderLineage))
    symbols = tuple(
        T11GrossEdgeSymbolResult(
            qore_symbol=symbol,
            observations=8,
            frozen_gross_edge_per_volume_usd=Decimal("0.10"),
        )
        for symbol in REQUIRED_SYMBOLS
    )
    folds = tuple(
        T11GrossEdgeFoldResult(
            fold_index=index,
            observations=14,
            represented_lineages=lineages,
            frozen_model_mse_r2=Decimal("0.5"),
            zero_edge_mse_r2=(
                Decimal("0.6") if ready else Decimal("0.4")
            ),
            frozen_model_nonworse=ready,
        )
        for index in range(1, 5)
    )
    return T11GrossEdgeFreshOOSResult(
        train_prior_sha256=prior_digest_sha256(),
        observation_count=56,
        represented_lineages=lineages,
        minimum_outcomes_per_lineage=8,
        symbols=symbols,
        folds=folds,
        four_of_four_nonworse=ready,
        fresh_oos_validated=ready,
        temporal_stability_validated=ready,
        model_refit_performed=False,
    )


def test_market_impact_falsification_is_immediately_terminal() -> None:
    result = assess_t11_terminal_disposition(
        market_impact=_impact(ready=False),
        gross_edge=None,
    )

    assert result.recommendation is T11TerminalRecommendation.FALSIFIED_AND_CLOSED
    assert result.blocking_requirement is None


def test_market_impact_pass_waits_for_gross_edge() -> None:
    result = assess_t11_terminal_disposition(
        market_impact=_impact(ready=True),
        gross_edge=None,
    )

    assert (
        result.recommendation
        is T11TerminalRecommendation.WAITING_ON_GROSS_EDGE_FRESH_OOS
    )
    assert result.blocking_requirement == "FRESH_OOS_GROSS_EDGE_VALIDATION_REQUIRED"


def test_gross_edge_falsification_is_terminal_after_market_impact_pass() -> None:
    result = assess_t11_terminal_disposition(
        market_impact=_impact(ready=True),
        gross_edge=_gross_edge(ready=False),
    )

    assert result.recommendation is T11TerminalRecommendation.FALSIFIED_AND_CLOSED
    assert result.blocking_requirement is None


def test_both_mandatory_inputs_pass_complete_t11() -> None:
    result = assess_t11_terminal_disposition(
        market_impact=_impact(ready=True),
        gross_edge=_gross_edge(ready=True),
    )

    assert result.recommendation is T11TerminalRecommendation.COMPLETED_AND_PROVEN
    assert result.blocking_requirement is None
