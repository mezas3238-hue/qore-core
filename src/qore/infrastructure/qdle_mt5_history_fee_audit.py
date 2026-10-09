"""Reconcile FundedNext MT5 closed-position history against QDLE costs.

Only externally observed CLOSED MT5 history, not CIBO Native MAX 3368 fills.
A history screenshot shows aggregate commission *per position*, not whether
a broker charged it at entry, exit, or both. Do not claim LIVE tariff authority.
No order_send or account access, deterministic Decimal-only math.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP

from qore.infrastructure.qdle_stellar_instant_costs import (
    STELLAR_HELP_OPEN_ONLY,
    estimate_per_lot_fees,
    jpy_quote_pip_value_usd_per_lot,
)

CENT = Decimal("0.01")
CONTRACT = {
    "EURUSD": Decimal("100000"),
    "GBPUSD": Decimal("100000"),
    "GBPJPY": Decimal("100000"),
    "AUDJPY": Decimal("100000"),
    "XAUUSD": Decimal("100"),
    "NDX100": Decimal("10"),
}
USD_QUOTED = frozenset(("EURUSD", "GBPUSD", "XAUUSD", "NDX100"))


class MT5HistoryFeeAuditError(ValueError):
    """Missing/invalid screenshot history, tariff drift or ledger mismatch."""


def _positive(name: str, x: Decimal, *, allow_zero: bool = False) -> None:
    if not isinstance(x, Decimal) or not x.is_finite() or (
        x < 0 if allow_zero else x <= 0
    ):
        raise MT5HistoryFeeAuditError(f"{name}: finite positive Decimal required")


def _timestamp(name: str, t: datetime) -> None:
    if not isinstance(t, datetime) or t.tzinfo is None or t.utcoffset() is None:
        raise MT5HistoryFeeAuditError(f"{name}: timezone-aware datetime needed")


@dataclass(frozen=True, slots=True)
class ClosedMT5PositionEvidence:
    symbol: str
    side: str
    lots: Decimal
    entry_price: Decimal
    exit_price: Decimal
    opened_at: datetime
    closed_at: datetime
    price_pnl_usd: Decimal
    commission_debit_usd: Decimal
    swap_usd: Decimal = Decimal("0")

    def __post_init__(self) -> None:
        if self.symbol not in CONTRACT or self.side not in ("BUY", "SELL"):
            raise MT5HistoryFeeAuditError("unknown symbol or side")
        for name in ("lots", "entry_price", "exit_price"):
            _positive(name, getattr(self, name))
        _positive("commission_debit_usd", self.commission_debit_usd, allow_zero=True)
        if any(not isinstance(v, Decimal) or not v.is_finite() for v in (
            self.price_pnl_usd, self.swap_usd,
        )):
            raise MT5HistoryFeeAuditError("invalid price PnL/swap")
        _timestamp("opened_at", self.opened_at)
        _timestamp("closed_at", self.closed_at)
        if self.closed_at <= self.opened_at:
            raise MT5HistoryFeeAuditError("opening must precede close")

    @property
    def net_usd(self) -> Decimal:
        return self.price_pnl_usd - self.commission_debit_usd + self.swap_usd


def reconcile_mt5_closed_history(
    positions: tuple[ClosedMT5PositionEvidence, ...],
    *, initial_balance_usd: Decimal, observed_final_balance_usd: Decimal,
    observed_commission_debit_usd: Decimal,
    reference_usdjpy_spot: Decimal | None = None,
) -> dict:
    """Reconcile observed MT5 closed history and tariff-to-cent.

    Published Stellar help matches these screenshots as TOTAL position cost.
    Does NOT prove which deal leg charged commission, future tariff, other
    symbols, inferred history outside the screenshot, or CIBO-managed exits.
    """
    if not isinstance(positions, tuple) or not positions:
        raise MT5HistoryFeeAuditError("nonempty tuple of observed positions required")
    for name, val in (
        ("initial_balance", initial_balance_usd),
        ("final_balance", observed_final_balance_usd),
        ("commission_total", observed_commission_debit_usd),
    ):
        _positive(name, val, allow_zero=name != "initial_balance")
    if reference_usdjpy_spot is not None:
        _positive("reference_usdjpy_spot", reference_usdjpy_spot)

    fee_total = Decimal(0)
    profit_total = Decimal(0)
    swap_total = Decimal(0)
    records = []
    seen = set()
    events = []
    for p in positions:
        if not isinstance(p, ClosedMT5PositionEvidence):
            raise MT5HistoryFeeAuditError("typed MT5 evidence required")
        identity = (p.symbol, p.opened_at, p.closed_at)
        if identity in seen:
            raise MT5HistoryFeeAuditError("duplicate MT5 history row")
        seen.add(identity)
        fee = estimate_per_lot_fees(
            p.symbol, entry_price=p.entry_price,
            contract_size=CONTRACT[p.symbol],
            model=STELLAR_HELP_OPEN_ONLY,
        )
        predicted = (p.lots * fee.total_usd).quantize(CENT, rounding=ROUND_HALF_UP)
        if predicted != p.commission_debit_usd:
            raise MT5HistoryFeeAuditError("actual MT5 aggregate position commission differs from FAQ model")
        # USD-quoted exact arithmetic; JPY needs entry-time conversion and
        # the user's separate quote screenshot is an approximation only.
        pnl_formula = None
        if p.symbol in USD_QUOTED:
            pnl_formula = (
                (p.exit_price - p.entry_price)
                * CONTRACT[p.symbol] * p.lots
                * (1 if p.side == "BUY" else -1)
            ).quantize(CENT, rounding=ROUND_HALF_UP)
            if pnl_formula != p.price_pnl_usd:
                raise MT5HistoryFeeAuditError("USD-denominated MT5 price PnL/contract mismatch")
        elif reference_usdjpy_spot is not None:
            jpy_change = (
                (p.exit_price - p.entry_price)
                * CONTRACT[p.symbol] * p.lots
                * (1 if p.side == "BUY" else -1)
            )
            pnl_formula = (jpy_change / reference_usdjpy_spot).quantize(
                CENT, rounding=ROUND_HALF_UP
            )
            if abs(pnl_formula - p.price_pnl_usd) > CENT:
                raise MT5HistoryFeeAuditError("JPY price PnL deviates by >1 cent from reference spot")
        fee_total += p.commission_debit_usd
        profit_total += p.price_pnl_usd
        swap_total += p.swap_usd
        records.append({
            "symbol": p.symbol, "side": p.side, "lots": str(p.lots),
            "observed_commission_debit_usd": str(p.commission_debit_usd),
            "stellar_faq_predicted_commission_usd": str(predicted),
            "gross_price_pnl_usd": str(p.price_pnl_usd),
            "net_result_usd": str(p.net_usd),
            "conversion_reference_spot_only": p.symbol in ("GBPJPY", "AUDJPY"),
        })
        # Use OPEN commission timing only for a balance-event illustrative
        # closed-account path. The screenshot does not independently prove
        # leg timing; do not report full broker equity MTM drawdown.
        events.extend((
            (p.opened_at, 0, p.symbol, -p.commission_debit_usd),
            (p.closed_at, 1, p.symbol, p.price_pnl_usd + p.swap_usd),
        ))
    if fee_total != observed_commission_debit_usd:
        raise MT5HistoryFeeAuditError("position fees differ from MT5 summary")
    expected_balance = initial_balance_usd + profit_total + swap_total - fee_total
    if expected_balance != observed_final_balance_usd:
        raise MT5HistoryFeeAuditError("MT5 screenshot total/balance does not reconcile")

    balance = initial_balance_usd
    peak = balance
    max_dd = Decimal(0)
    for _at, _priority, _symbol, delta in sorted(events):
        balance += delta
        peak = max(peak, balance)
        max_dd = max(max_dd, (peak-balance)/peak)
    if balance != observed_final_balance_usd:
        raise MT5HistoryFeeAuditError("MT5 account event chronology does not reconcile")
    return {
        "schema": "qore.qdle.observed-mt5-history-fee-reconciliation.v1",
        "source": "USER_SUPPLIED_MT5_CLOSED_POSITIONS_SCREENSHOT",
        "position_count": len(positions),
        "all_observed_fees_match_stellar_faq": True,
        "actual_position_commissions_observed": True,
        "fee_leg_timing_independently_proven": False,
        "usd_jpy_quote_is_exact_at_all_entry_epochs": False,
        "tariff_account_wide_future_verified": False,
        "trader_history_is_cibo_managed": False,
        "all_instrument_tariffs_fully_certified": False,
        "observed_price_pnl_usd": str(profit_total),
        "observed_total_commission_debit_usd": str(fee_total),
        "observed_total_swap_usd": str(swap_total),
        "observed_net_change_usd": str(profit_total+swap_total-fee_total),
        "observed_initial_balance_usd": str(initial_balance_usd),
        "observed_final_balance_usd": str(observed_final_balance_usd),
        "illustrative_balance_event_max_dd_pct": str(max_dd*100),
        "cibo_3368_managed_dd_pct": None,
        "cibo_3368_managed_final_nav_usd": None,
        "rows": records,
    }
