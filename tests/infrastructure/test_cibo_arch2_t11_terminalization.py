from dataclasses import replace
from datetime import timedelta
from decimal import Decimal

from qore.infrastructure.account_wide_risk import TraderLineage
from qore.infrastructure.cibo_arch2_t11_gross_edge_oos import (
    T11GrossEdgeFreshObservation,
    evaluate_t11_gross_edge_fresh_oos,
)
from qore.infrastructure.cibo_arch2_t11_market_impact_evaluator import (
    T11MarketImpactEpisode,
    evaluate_t11_market_impact,
)
from qore.infrastructure.cibo_arch2_t11_nonlinear_input_freeze import (
    FROZEN_AT,
    MARKET_IMPACT_CALIBRATION_EPISODES_PER_LEVEL_PER_SYMBOL,
    MARKET_IMPACT_VALIDATION_EPISODES_PER_LEVEL_PER_SYMBOL,
    REQUIRED_SYMBOLS,
)
from qore.infrastructure.cibo_arch2_t11_terminalization import (
    COMPLETED,
    FALSIFIED,
    WAITING,
    terminalize_t11,
)
from qore.infrastructure.cibo_ce2i_phase20_train_prior import (
    frozen_train_prior_for,
)

_LINEAGES = (
    TraderLineage.R38_GBPJPY,
    TraderLineage.R43_GBPUSD,
    TraderLineage.R42_AUDJPY,
    TraderLineage.R38_EURUSD,
    TraderLineage.R34_XAUUSD,
    TraderLineage.VT08_FOREX,
    TraderLineage.VT31_NAS100,
)
_SYMBOLS = (
    "GBPJPY",
    "GBPUSD",
    "AUDJPY",
    "EURUSD",
    "XAUUSD",
    "EURUSD",
    "NAS100",
)


def _gross_edge_valid():
    rows = []
    minute = 1
    for repeat in range(10):
        for trader, symbol in zip(_LINEAGES, _SYMBOLS, strict=True):
            rows.append(
                T11GrossEdgeFreshObservation(
                    evidence_id=f"e-{trader.value}-{repeat}",
                    signal_fingerprint=f"s-{trader.value}-{repeat}",
                    trader_id=trader,
                    qore_symbol=symbol,
                    observed_at=FROZEN_AT + timedelta(minutes=minute),
                    structural_outcome_r=(
                        frozen_train_prior_for(trader).expected_structural_r
                    ),
                    stop_risk_per_volume_usd=Decimal("10"),
                    outcome_reconciled=True,
                    provider_bound=True,
                    holdout_receipt_authorized=True,
                )
            )
            minute += 1
    return evaluate_t11_gross_edge_fresh_oos(tuple(rows))


def _impact_valid():
    episodes = []
    minute = 1
    for symbol in REQUIRED_SYMBOLS:
        for phase, pairs in (
            ("CALIBRATION", MARKET_IMPACT_CALIBRATION_EPISODES_PER_LEVEL_PER_SYMBOL),
            ("VALIDATION", MARKET_IMPACT_VALIDATION_EPISODES_PER_LEVEL_PER_SYMBOL),
        ):
            for pair_index in range(1, pairs + 1):
                side = "long" if pair_index % 2 else "short"
                order = (1, 2) if pair_index % 2 else (2, 1)
                fold = 0 if phase == "CALIBRATION" else pair_index
                for order_position, child_count in enumerate(order, start=1):
                    # Perfectly linear cost => quadratic b=0 and 4/4 nonworse.
                    cost = Decimal(child_count) * Decimal("0.01")
                    episodes.append(
                        T11MarketImpactEpisode(
                            evidence_id=f"{symbol}-{phase}-{pair_index}-{child_count}",
                            qore_symbol=symbol,
                            pair_id=f"{symbol}-{phase}-{pair_index}",
                            phase=phase,
                            fold_index=fold,
                            side=side,
                            child_count=child_count,
                            level_order_position=order_position,
                            minimum_volume=Decimal("0.01"),
                            aggregate_volume=Decimal("0.01") * child_count,
                            realized_settlement_cost_total_usd=cost,
                            deposit_asset="USD",
                            observed_at=FROZEN_AT + timedelta(minutes=minute),
                            provider_bound=True,
                            every_child_order_minimum_volume=True,
                        )
                    )
                    minute += 1
    return evaluate_t11_market_impact(tuple(episodes))


def test_t11_waits_when_required_evidence_is_missing() -> None:
    result = terminalize_t11(market_impact=None, gross_edge=None)

    assert result.recommendation == WAITING
    assert result.unresolved_requirements == (
        "REAL_PROVIDER_BOUND_MARKET_IMPACT_MODEL_REQUIRED",
        "REAL_CALIBRATED_FRESH_OOS_GROSS_EDGE_MODEL_REQUIRED",
    )


def test_t11_completes_only_when_both_components_are_proven() -> None:
    result = terminalize_t11(
        market_impact=_impact_valid(),
        gross_edge=_gross_edge_valid(),
    )

    assert result.recommendation == COMPLETED
    assert result.unresolved_requirements == ()
    assert result.falsification_reasons == ()


def test_t11_falsifies_when_frozen_market_impact_component_fails() -> None:
    impact = _impact_valid()
    first = impact.symbols[0]
    failed_fold = replace(first.fold_results[0], quadratic_nonworse=False)
    failed_symbol = replace(
        first,
        fold_results=(failed_fold,) + first.fold_results[1:],
        four_of_four_validated=False,
        fresh_oos_validated=False,
    )
    failed_impact = replace(
        impact,
        symbols=(failed_symbol,) + impact.symbols[1:],
        market_impact_model_ready=False,
    )

    result = terminalize_t11(market_impact=failed_impact, gross_edge=None)

    assert result.recommendation == FALSIFIED
    assert result.unresolved_requirements == ()
    assert result.falsification_reasons == (
        "FROZEN_PROVIDER_BOUND_MARKET_IMPACT_MODEL_FAILED_4_OF_4_VALIDATION",
    )
