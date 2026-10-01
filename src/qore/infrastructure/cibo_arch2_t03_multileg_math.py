"""Pure two-leg FX exposure and margin algebra for Architect-2 T03."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True, slots=True)
class PairTerms:
    symbol: str
    base: str
    quote: str
    midpoint: Decimal
    lot_size_cents: int
    buy_margin_per_native_cent: Decimal
    sell_margin_per_native_cent: Decimal


def leg_for_exposure(
    *,
    wanted_currency: str,
    pivot: str,
    wanted_positive: bool,
    pairs: dict[str, PairTerms],
    wanted_units: Decimal,
) -> tuple[PairTerms, str, Decimal, Decimal]:
    direct = pairs.get(wanted_currency + pivot)
    inverse = pairs.get(pivot + wanted_currency)
    if direct is not None:
        side = "BUY" if wanted_positive else "SELL"
        volume = wanted_units
        pivot_exposure = (
            -volume * direct.midpoint
            if wanted_positive
            else volume * direct.midpoint
        )
        return direct, side, volume, pivot_exposure
    if inverse is not None:
        side = "SELL" if wanted_positive else "BUY"
        volume = wanted_units / inverse.midpoint
        pivot_exposure = -volume if wanted_positive else volume
        return inverse, side, volume, pivot_exposure
    raise KeyError((wanted_currency, pivot))


def margin(terms: PairTerms, side: str, native_volume: Decimal) -> Decimal:
    rate = (
        terms.buy_margin_per_native_cent
        if side == "BUY"
        else terms.sell_margin_per_native_cent
    )
    return rate * native_volume


def candidate(
    *,
    target: PairTerms,
    pivot: str,
    pairs: dict[str, PairTerms],
    target_side: str,
) -> dict[str, object] | None:
    target_positive = target_side == "BUY"
    target_units = Decimal(target.lot_size_cents)
    try:
        leg1, side1, volume1, pivot1 = leg_for_exposure(
            wanted_currency=target.base,
            pivot=pivot,
            wanted_positive=target_positive,
            pairs=pairs,
            wanted_units=target_units,
        )
    except KeyError:
        return None

    quote_units = target_units * target.midpoint
    try:
        leg2, side2, volume2, pivot2 = leg_for_exposure(
            wanted_currency=target.quote,
            pivot=pivot,
            wanted_positive=not target_positive,
            pairs=pairs,
            wanted_units=quote_units,
        )
    except KeyError:
        return None

    if leg1.symbol == leg2.symbol:
        return None

    direct_margin = margin(target, target_side, target_units)
    candidate_margin = margin(leg1, side1, volume1) + margin(
        leg2,
        side2,
        volume2,
    )
    ratio = candidate_margin / direct_margin
    return {
        "pivot": pivot,
        "target_side": target_side,
        "leg1_symbol": leg1.symbol,
        "leg1_side": side1,
        "leg1_continuous_native_volume": format(volume1, "f"),
        "leg2_symbol": leg2.symbol,
        "leg2_side": side2,
        "leg2_continuous_native_volume": format(volume2, "f"),
        "pivot_residual_continuous": format(pivot1 + pivot2, "f"),
        "direct_margin_usd": format(direct_margin, "f"),
        "continuous_candidate_margin_usd": format(candidate_margin, "f"),
        "continuous_margin_ratio": format(ratio, "f"),
        "continuous_lower_margin": ratio < 1,
    }
