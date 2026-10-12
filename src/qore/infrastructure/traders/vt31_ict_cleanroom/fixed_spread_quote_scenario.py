"""VT31 fixed-spread quote-side *simulation*, not historical bid/ask evidence.

Input M1 OHLC has NO independently certified BID/MID/ASK basis.
For this stress scenario only, treat historical M1 OHLC as a synthetic MID:
    bid = mid - 0.80 NAS100 index points
    ask = mid + 0.80 NAS100 index points
This reconstructs a constant 1.60 spread observed once in the user's MT5
NDX100 screenshot, NOT broker quotes in 2023–2026 and NOT NAS100↔NDX100
identity equivalence. No fills or PnL can follow without broker ACK.
"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from .contracts import M1Bar, Side

SCREENSHOT_BID = Decimal("30853.00")
SCREENSHOT_ASK = Decimal("30854.60")
FIXED_SPREAD = SCREENSHOT_ASK - SCREENSHOT_BID
HALF_SPREAD = FIXED_SPREAD / Decimal("2")


@dataclass(frozen=True, slots=True)
class SyntheticM1QuoteBounds:
    bid_low: Decimal
    bid_high: Decimal
    ask_low: Decimal
    ask_high: Decimal
    spread: Decimal = FIXED_SPREAD

    @classmethod
    def from_mid_m1(cls, bar: M1Bar) -> SyntheticM1QuoteBounds:
        return cls(
            bid_low=bar.low - HALF_SPREAD,
            bid_high=bar.high - HALF_SPREAD,
            ask_low=bar.low + HALF_SPREAD,
            ask_high=bar.high + HALF_SPREAD,
        )

    def eligible_quote_side_reachable(
        self, side: Side, ce_limit: Decimal,
    ) -> bool:
        """Potential crossing; not enough for fill or intrabar chronology."""
        return (
            self.ask_low <= ce_limit
            if side is Side.LONG
            else self.bid_high >= ce_limit
        )


def screenshot_quote_crosses(
    *, side: Side, ce_limit: Decimal,
) -> bool:
    """Demonstrate exact user-observed snapshot rules only at that instant."""
    if ce_limit.is_nan() or not ce_limit.is_finite():
        raise ValueError("CE must be finite")
    return (
        SCREENSHOT_ASK <= ce_limit
        if side is Side.LONG
        else SCREENSHOT_BID >= ce_limit
    )
