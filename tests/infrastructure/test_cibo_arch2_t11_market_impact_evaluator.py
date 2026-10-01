from datetime import timedelta
from decimal import Decimal

import pytest

from qore.infrastructure.cibo_arch2_t11_market_impact_evaluator import (
    T11MarketImpactEpisode,
    evaluate_t11_market_impact,
)
from qore.infrastructure.cibo_arch2_t11_nonlinear_input_freeze import (
    FROZEN_AT,
    REQUIRED_SYMBOLS,
)
from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)


def _episodes(*, nonlinear: bool = True) -> tuple[T11MarketImpactEpisode, ...]:
    rows: list[T11MarketImpactEpisode] = []
    minute = 1
    for symbol in REQUIRED_SYMBOLS:
        minimum = Decimal("0.01")
        for phase, pairs in (("CALIBRATION", 8), ("VALIDATION", 4)):
            for index in range(pairs):
                fold = 0 if phase == "CALIBRATION" else index + 1
                side = "long" if index % 2 == 0 else "short"
                pair_id = f"{symbol}-{phase}-{index}"
                for child_count in (1, 2):
                    volume = minimum * child_count
                    linear = Decimal("2") * volume
                    impact = (
                        Decimal("10") * volume * volume
                        if nonlinear
                        else Decimal(0)
                    )
                    rows.append(
                        T11MarketImpactEpisode(
                            evidence_id=(
                                f"{symbol}-{phase}-{index}-{child_count}"
                            ),
                            qore_symbol=symbol,
                            pair_id=pair_id,
                            phase=phase,
                            fold_index=fold,
                            side=side,
                            child_count=child_count,
                            minimum_volume=minimum,
                            aggregate_volume=volume,
                            adverse_slippage_cost_total_usd=linear + impact,
                            observed_at=FROZEN_AT + timedelta(minutes=minute),
                            provider_bound=True,
                            every_child_order_minimum_volume=True,
                        )
                    )
                    minute += 1
    return tuple(rows)


def test_market_impact_recovers_quadratic_coefficient_and_validates_4_of_4() -> None:
    result = evaluate_t11_market_impact(_episodes())

    assert result.market_impact_model_ready is True
    assert tuple(item.qore_symbol for item in result.symbols) == REQUIRED_SYMBOLS
    assert all(
        item.impact_cost_per_volume_squared_usd == Decimal("10")
        for item in result.symbols
    )
    assert all(item.four_of_four_validated for item in result.symbols)


def test_market_impact_allows_empirically_validated_zero_nonlinearity() -> None:
    result = evaluate_t11_market_impact(_episodes(nonlinear=False))

    assert result.market_impact_model_ready is True
    assert all(
        item.impact_cost_per_volume_squared_usd == Decimal(0)
        for item in result.symbols
    )


def test_market_impact_rejects_non_minimum_child_volume_identity() -> None:
    with pytest.raises(
        CiboCapitalManagementError,
        match="aggregate volume/child identity drift",
    ):
        T11MarketImpactEpisode(
            evidence_id="bad",
            qore_symbol="EURUSD",
            pair_id="bad-pair",
            phase="CALIBRATION",
            fold_index=0,
            side="long",
            child_count=2,
            minimum_volume=Decimal("0.01"),
            aggregate_volume=Decimal("0.03"),
            adverse_slippage_cost_total_usd=Decimal("0"),
            observed_at=FROZEN_AT + timedelta(minutes=1),
            provider_bound=True,
            every_child_order_minimum_volume=True,
        )
