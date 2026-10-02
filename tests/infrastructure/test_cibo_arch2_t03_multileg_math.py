from __future__ import annotations

from decimal import Decimal

from qore.infrastructure.cibo_arch2_t03_multileg_math import PairTerms, candidate


def _pairs(
    *,
    target_margin: Decimal = Decimal("0.00001"),
    leg_margin: Decimal = Decimal("0.000005"),
) -> dict[str, PairTerms]:
    return {
        "EURUSD": PairTerms(
            symbol="EURUSD",
            base="EUR",
            quote="USD",
            midpoint=Decimal("1.10"),
            lot_size_cents=10_000_000,
            buy_margin_per_native_cent=target_margin,
            sell_margin_per_native_cent=target_margin,
        ),
        "EURJPY": PairTerms(
            symbol="EURJPY",
            base="EUR",
            quote="JPY",
            midpoint=Decimal("165"),
            lot_size_cents=10_000_000,
            buy_margin_per_native_cent=leg_margin,
            sell_margin_per_native_cent=leg_margin,
        ),
        "USDJPY": PairTerms(
            symbol="USDJPY",
            base="USD",
            quote="JPY",
            midpoint=Decimal("150"),
            lot_size_cents=10_000_000,
            buy_margin_per_native_cent=leg_margin,
            sell_margin_per_native_cent=leg_margin,
        ),
    }


def test_triangulation_cancels_pivot_currency() -> None:
    row = candidate(
        target=_pairs()["EURUSD"],
        pivot="JPY",
        pairs=_pairs(),
        target_side="BUY",
    )
    assert row is not None
    assert Decimal(str(row["pivot_residual_continuous"])) == 0
    assert row["leg1_symbol"] == "EURJPY"
    assert row["leg1_side"] == "BUY"
    assert row["leg2_symbol"] == "USDJPY"
    assert row["leg2_side"] == "SELL"


def test_continuous_margin_lower_bound_can_reject_candidate() -> None:
    pairs = _pairs(
        target_margin=Decimal("0.00001"),
        leg_margin=Decimal("0.00002"),
    )
    row = candidate(
        target=pairs["EURUSD"],
        pivot="JPY",
        pairs=pairs,
        target_side="BUY",
    )
    assert row is not None
    assert row["continuous_lower_margin"] is False
    assert Decimal(str(row["continuous_margin_ratio"])) > 1
