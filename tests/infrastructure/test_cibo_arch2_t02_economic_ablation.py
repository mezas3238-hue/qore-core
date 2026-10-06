from datetime import timedelta
from decimal import Decimal

from qore.infrastructure.account_wide_risk import TraderLineage
from qore.infrastructure.cibo_arch2_t02_economic_ablation import (
    FROZEN_AT,
    MINIMUM_PAIRS_PER_FOLD,
    T02EconomicAblationPair,
    evaluate_t02_provider_bound_economic_ablation,
)


def _pair(
    *,
    fold: int,
    index: int,
    treatment_pnl: str = "1.50",
    treatment_adverse: str = "0.80",
) -> T02EconomicAblationPair:
    return T02EconomicAblationPair(
        fold_index=fold,
        signal_fingerprint=f"sig-{fold}-{index}",
        trader_id=TraderLineage.R43_GBPUSD,
        observed_at=FROZEN_AT + timedelta(minutes=fold * 100 + index + 1),
        provider_evidence_id=f"provider-{fold}-{index}",
        structural_evidence_id=f"structural-{fold}-{index}",
        baseline_volume=Decimal("0.01"),
        treatment_volume=Decimal("0.02"),
        stop_loss_per_volume_usd=Decimal("10"),
        baseline_margin_usd=Decimal("1"),
        treatment_margin_usd=Decimal("2"),
        baseline_net_pnl_usd=Decimal("1.00"),
        treatment_net_pnl_usd=Decimal(treatment_pnl),
        baseline_max_adverse_r=Decimal("0.80"),
        treatment_max_adverse_r=Decimal(treatment_adverse),
        stop_geometry_unchanged=True,
        provider_bound=True,
        risk_authorized=True,
        outcome_pair_predeclared=True,
    )


def test_t02_ablation_requires_four_independently_positive_folds() -> None:
    pairs = tuple(
        _pair(fold=fold, index=index)
        for fold in range(1, 5)
        for index in range(MINIMUM_PAIRS_PER_FOLD)
    )

    result = evaluate_t02_provider_bound_economic_ablation(pairs)

    assert result.four_of_four_pass is True
    assert result.provider_bound_economic_value_proven is True
    assert all(item.pass_gate for item in result.fold_results)
    assert result.productive_authority is False


def test_t02_ablation_rejects_pooled_rescue() -> None:
    pairs = tuple(
        _pair(
            fold=fold,
            index=index,
            treatment_pnl="0.50" if fold == 4 else "2.00",
        )
        for fold in range(1, 5)
        for index in range(MINIMUM_PAIRS_PER_FOLD)
    )

    result = evaluate_t02_provider_bound_economic_ablation(pairs)

    assert result.fold_results[-1].economic_value_positive is False
    assert result.fold_results[-1].pass_gate is False
    assert result.four_of_four_pass is False
    assert result.provider_bound_economic_value_proven is False


def test_t02_ablation_rejects_worse_normalized_tail() -> None:
    pairs = tuple(
        _pair(
            fold=fold,
            index=index,
            treatment_adverse="0.90" if fold == 2 else "0.80",
        )
        for fold in range(1, 5)
        for index in range(MINIMUM_PAIRS_PER_FOLD)
    )

    result = evaluate_t02_provider_bound_economic_ablation(pairs)

    assert result.fold_results[1].normalized_tail_nonworse is False
    assert result.four_of_four_pass is False
