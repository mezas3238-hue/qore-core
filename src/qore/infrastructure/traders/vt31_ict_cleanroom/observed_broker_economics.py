"""Research-only observed MT5 closed-position economics for NAS100/NDX100.

These are human-readable values transcribed from the owner's 2026-10-10
MT5 history screenshot. They are NOT a broker contract specification,
tick/quote history, verified opening-side commission timing, or authority
to size, route, execute or simulate exact fills. The symbol in MT5 was
NDX100; equivalence to strategy NAS100 must be verified separately.

This module is never imported into the live QDLE/CIBO sizing path.
"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal
from typing import Literal

RESEARCH_ONLY = True
BROKER_SYMBOL_OBSERVED = "NDX100"
STRATEGY_SYMBOL = "NAS100"
DISPLAY_CURRENCY_UNVERIFIED = True
BROKER_CONTRACT_UNVERIFIED = True
HISTORICAL_BID_ASK_UNAVAILABLE = True
LIVE_SIZING_AUTHORIZED = False


@dataclass(frozen=True, slots=True)
class MT5ClosedPositionObservation:
    """Closed-position facts, not proof of individual bid/ask quotes.

    The observed account currency is unspecified in the screenshot; numeric
    monetary values are kept in *account-currency units*, not hardcoded USD.
    """

    symbol: str
    side: Literal["BUY", "SELL"]
    lots: Decimal
    opening_execution: Decimal
    closing_execution: Decimal
    gross_result_displayed: Decimal
    commission_displayed: Decimal
    provenance: str = "USER_SUPPLIED_MT5_HISTORY_SCREENSHOT_2026-10-10"

    def __post_init__(self) -> None:
        if self.lots <= 0:
            raise ValueError("lot quantity must be positive")
        if self.opening_execution <= 0 or self.closing_execution <= 0:
            raise ValueError("execution prices must be positive")
        if self.symbol != BROKER_SYMBOL_OBSERVED:
            raise ValueError("do not transpose NDX100 contract evidence across symbols")
        if not self.provenance:
            raise ValueError("source must be identified")

    @property
    def signed_price_move(self) -> Decimal:
        move = self.closing_execution - self.opening_execution
        return move if self.side == "BUY" else -move

    @property
    def implied_account_currency_per_point_at_observed_lots(self) -> Decimal:
        if self.signed_price_move == 0:
            raise ValueError("cannot infer point value without observed price movement")
        return self.gross_result_displayed / self.signed_price_move

    @property
    def implied_account_currency_per_point_per_lot(self) -> Decimal:
        return self.implied_account_currency_per_point_at_observed_lots / self.lots

    def theoretical_gross_at_hypothetical_point_value(
        self, account_currency_per_point_per_lot: Decimal
    ) -> Decimal:
        """Compute a *hypothesis*, never official FundedNext/MT5 specs."""
        if account_currency_per_point_per_lot <= 0:
            raise ValueError("point value must be positive")
        exact = (
            self.signed_price_move * self.lots
            * account_currency_per_point_per_lot
        )
        return exact.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


NDX100_CLOSED_SAMPLE = MT5ClosedPositionObservation(
    symbol="NDX100",
    side="BUY",
    lots=Decimal("0.01"),
    opening_execution=Decimal("30852.60"),
    closing_execution=Decimal("30848.08"),
    gross_result_displayed=Decimal("-0.45"),
    commission_displayed=Decimal("0.00"),
)


def screenshot_economic_observation() -> dict[str, object]:
    """Machine-readable evidence for architectural review, not trading."""
    s = NDX100_CLOSED_SAMPLE
    return {
        "trader_id": "VT31",
        "strategy_symbol": STRATEGY_SYMBOL,
        "observed_mt5_symbol": s.symbol,
        "observed_lots": str(s.lots),
        "observed_opening_execution": str(s.opening_execution),
        "observed_closing_execution": str(s.closing_execution),
        "observed_signed_price_move_index_points": str(s.signed_price_move),
        "observed_gross_result_account_currency": str(s.gross_result_displayed),
        "observed_commission_account_currency": str(s.commission_displayed),
        "implied_per_point_at_001_lot": str(
            s.implied_account_currency_per_point_at_observed_lots
        ),
        "implied_per_point_per_full_lot_not_verified": str(
            s.implied_account_currency_per_point_per_lot
        ),
        "hypothesized_ten_account_currency_units_per_point_per_lot": (
            s.theoretical_gross_at_hypothetical_point_value(Decimal("10"))
            == s.gross_result_displayed
        ),
        "account_currency_confirmed": False,
        "NDX100_NAS100_contract_identity_verified": False,
        "broker_contract_spec_confirmed": False,
        "commission_waiver_for_all_NDX100_trades_confirmed": False,
        "commission_charged_at_open_vs_close_confirmed": False,
        "historical_bid_ask_tick_source_available": False,
        "research_only": RESEARCH_ONLY,
        "safe_to_use_for_live_sizing": LIVE_SIZING_AUTHORIZED,
        "source": s.provenance,
    }
