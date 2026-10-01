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
                            level_order_position=(
                                1
                                if (
                                    (index % 2 == 0 and child_count == 1)
                                    or (index % 2 == 1 and child_count == 2)
                                )
                                else 2
                            ),
                            minimum_volume=minimum,
                            aggregate_volume=volume,
                            realized_settlement_cost_total_usd=linear + impact,
                            deposit_asset="USD",
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
            level_order_position=1,
            minimum_volume=Decimal("0.01"),
            aggregate_volume=Decimal("0.03"),
            realized_settlement_cost_total_usd=Decimal("0"),
            deposit_asset="USD",
            observed_at=FROZEN_AT + timedelta(minutes=1),
            provider_bound=True,
            every_child_order_minimum_volume=True,
        )


def test_market_impact_rejects_non_usd_settlement_asset() -> None:
    with pytest.raises(
        CiboCapitalManagementError,
        match="deposit asset must be USD",
    ):
        T11MarketImpactEpisode(
            evidence_id="bad-asset",
            qore_symbol="EURUSD",
            pair_id="bad-asset-pair",
            phase="CALIBRATION",
            fold_index=0,
            side="long",
            child_count=1,
            level_order_position=1,
            minimum_volume=Decimal("0.01"),
            aggregate_volume=Decimal("0.01"),
            realized_settlement_cost_total_usd=Decimal("0"),
            deposit_asset="EUR",
            observed_at=FROZEN_AT + timedelta(minutes=1),
            provider_bound=True,
            every_child_order_minimum_volume=True,
        )


def test_market_impact_rejects_non_alternating_level_order() -> None:
    rows = list(_episodes())
    first = rows[0]
    second = rows[1]
    rows[0] = T11MarketImpactEpisode(
        evidence_id=first.evidence_id,
        qore_symbol=first.qore_symbol,
        pair_id=first.pair_id,
        phase=first.phase,
        fold_index=first.fold_index,
        side=first.side,
        child_count=first.child_count,
        level_order_position=2,
        minimum_volume=first.minimum_volume,
        aggregate_volume=first.aggregate_volume,
        realized_settlement_cost_total_usd=(
            first.realized_settlement_cost_total_usd
        ),
        deposit_asset=first.deposit_asset,
        observed_at=first.observed_at,
        provider_bound=True,
        every_child_order_minimum_volume=True,
    )
    rows[1] = T11MarketImpactEpisode(
        evidence_id=second.evidence_id,
        qore_symbol=second.qore_symbol,
        pair_id=second.pair_id,
        phase=second.phase,
        fold_index=second.fold_index,
        side=second.side,
        child_count=second.child_count,
        level_order_position=1,
        minimum_volume=second.minimum_volume,
        aggregate_volume=second.aggregate_volume,
        realized_settlement_cost_total_usd=(
            second.realized_settlement_cost_total_usd
        ),
        deposit_asset=second.deposit_asset,
        observed_at=second.observed_at,
        provider_bound=True,
        every_child_order_minimum_volume=True,
    )

    with pytest.raises(
        CiboCapitalManagementError,
        match="level order must alternate",
    ):
        evaluate_t11_market_impact(tuple(rows))
