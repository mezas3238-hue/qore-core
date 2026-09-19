"""Permanent VT08 Index concurrent-market operating contract.

This contract is architecture, not an economic candidate.

NAS100, SP500 and US30 are independent VT08 Index signal engines. A valid
position on one symbol MUST NOT block a valid position on another symbol.
Risk may resize concurrent signals but may not suppress them merely because
another index is already open.

The portfolio-level drawdown ceiling is six R across all three markets.

Owner density contract (18-Sep-2026):
- 5Y must naturally produce roughly 2,300-2,500 trades across the three markets.
- 2Y must produce at least 1,000 trades.
Density may not be manufactured by suppressing valid signals or by trivial
risk scaling.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Final

CONTRACT_ID: Final = "VT08_INDEX_CONCURRENT_MARKET_CONTRACT_V2"
MARKETS: Final = ("NAS100", "SP500", "US30")

MAX_ACTIVE_POSITIONS_PER_SYMBOL: Final = 1
MAX_CROSS_MARKET_CONCURRENT_POSITIONS: Final = 3

GLOBAL_SINGLE_POSITION_RULE: Final = False
CROSS_MARKET_CONCURRENCY_REQUIRED: Final = True
VALID_SIGNAL_SUPPRESSION_DUE_TO_OTHER_MARKET_OPEN: Final = False
SAME_TIMESTAMP_SIGNALS_MUST_SHARE_PRE_BATCH_STATE: Final = True
RISK_MAY_RESIZE_VALID_SIGNALS: Final = True
ZERO_RISK_AS_SIGNAL_SUPPRESSION: Final = False

PORTFOLIO_MAX_DRAWDOWN_R: Final = Decimal("6")
PREFERRED_PORTFOLIO_DRAWDOWN_BAND_R: Final = (
    Decimal("5"),
    Decimal("6"),
)

FIVE_YEAR_TRADE_RANGE: Final = (2300, 2500)
TWO_YEAR_MIN_TRADES: Final = 1000

PRIMARY_STRESS_R_PER_TRADE: Final = Decimal("0.05")
SECONDARY_STRESS_R_PER_TRADE: Final = Decimal("0.10")

LIVE_AUTHORIZED: Final = False
REAL_CAPITAL_AUTHORIZED: Final = False
PRODUCTION_AUTHORIZED: Final = False


def validates_trade_count(*, years: int, sample: int) -> bool:
    if years == 5:
        low, high = FIVE_YEAR_TRADE_RANGE
    elif years == 2:
        return sample >= TWO_YEAR_MIN_TRADES
    else:
        raise ValueError("VT08 concurrent contract defines only 5Y and 2Y density")
    return low <= sample <= high
