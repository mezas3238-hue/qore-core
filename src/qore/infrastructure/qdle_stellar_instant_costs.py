"""Account-program-specific PAPER fee schedule for QDLE cost-aware sizing.

The Stellar Instant HELP policy at October 2026 says Forex $7/lot on OPEN,
metals 0.0016% of opening notional on OPEN, indices $0, no CLOSE commission.
See https://help.fundednext.com/en/articles/11641300-what-are-the-commission-charges-for-the-stellar-instant-account

FundedNext general rules describe some charges "per side". Both are kept as
separately labeled research scenarios until actual MT5 account deals verify.
Neither is proof of account-specific fees, historical conditions or LIVE.
"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

FOREX = frozenset(("AUDJPY", "EURUSD", "GBPJPY", "GBPUSD"))
STELLAR_HELP_OPEN_ONLY = "stellar_instant_open_only"
GENERAL_RULES_PER_SIDE = "stellar_general_per_side"
LEGACY_REPLAY_PROXY = "legacy_proxy"
MODELS = (LEGACY_REPLAY_PROXY, STELLAR_HELP_OPEN_ONLY, GENERAL_RULES_PER_SIDE)
SOURCE_STELLAR = (
    "https://help.fundednext.com/en/articles/"
    "11641300-what-are-the-commission-charges-for-the-stellar-instant-account"
)


@dataclass(frozen=True, slots=True)
class PerLotFeeEstimate:
    symbol: str
    fee_model: str
    opening_usd: Decimal
    closing_usd: Decimal
    fee_evidence: str
    actual_mt5_account_verified: bool = False

    @property
    def total_usd(self) -> Decimal:
        return self.opening_usd + self.closing_usd


def estimate_per_lot_fees(
    symbol: str, *, entry_price: Decimal, contract_size: Decimal,
    model: str, legacy_ndx_fee_usd: Decimal | None = None,
) -> PerLotFeeEstimate:
    """Price each leg per lot, excluding bid/ask spread already in execution.

    Do NOT treat these published tariffs as historical provider-confirmed
    settlement costs. The NDX $20 old run was an unverified sensitivity.
    """
    if model not in MODELS:
        raise ValueError("unknown Stellar Instant tariff scenario")
    if symbol not in FOREX | {"XAUUSD", "NDX100"}:
        raise ValueError("unrecognized QORE symbol")
    if (not isinstance(entry_price, Decimal) or not entry_price.is_finite()
        or entry_price <= 0 or not isinstance(contract_size, Decimal)
        or not contract_size.is_finite() or contract_size <= 0):
        raise ValueError("finite positive entry/contract needed")
    if model == LEGACY_REPLAY_PROXY:
        if symbol == "NDX100":
            if (not isinstance(legacy_ndx_fee_usd, Decimal)
                or not legacy_ndx_fee_usd.is_finite()
                or legacy_ndx_fee_usd < 0):
                raise ValueError("legacy NDX quote needs explicit research fee")
            return PerLotFeeEstimate(symbol, model, legacy_ndx_fee_usd / 2,
                                     legacy_ndx_fee_usd / 2,
                                     "LEGACY_REPLAY_NDX_EXPLICIT_SENSITIVITY")
        if symbol in FOREX:
            return PerLotFeeEstimate(symbol, model, Decimal("7"), Decimal("7"),
                                     "LEGACY_REPLAY_FOREX_SYMMETRIC")
        xau_open = Decimal("0.000016") * contract_size * entry_price
        return PerLotFeeEstimate(symbol, model, xau_open, xau_open,
                                 "LEGACY_REPLAY_XAU_TWO_LEGS_AT_ENTRY_PROXY")

    # Published Stellar Instant help says all commission is charged on OPEN.
    # General CFD rules say 'per side': retain as a stress sensitivity.
    per_side = model == GENERAL_RULES_PER_SIDE
    evidence = ("FUNDEDNEXT_GENERAL_RULES_PER_SIDE_SENSITIVITY"
                if per_side else "FUNDEDNEXT_STELLAR_INSTANT_HELP_OPEN_ONLY")
    if symbol == "NDX100":
        return PerLotFeeEstimate(symbol, model, Decimal(0), Decimal(0), evidence)
    if symbol in FOREX:
        return PerLotFeeEstimate(symbol, model, Decimal("7"),
                                 Decimal("7") if per_side else Decimal(0),
                                 evidence)
    opening = Decimal("0.000016") * contract_size * entry_price
    return PerLotFeeEstimate(symbol, model, opening,
                             opening if per_side else Decimal(0),
                             evidence + "_XAU_CLOSE_PRICE_NOT_HISTORICALLY_KNOWN")


def jpy_quote_pip_value_usd_per_lot(
    *, contract_size: Decimal, usd_jpy: Decimal,
    pip_size_jpy: Decimal = Decimal("0.01"),
) -> Decimal:
    """Convert 1000 JPY/pip on 100K base-unit standard JPY crosses.

    Caller must supply an epoch-appropriate USDJPY. Do not silently reuse
    today's USDJPY on burned 2019-2022 historical opportunities.
    """
    for val in (contract_size, usd_jpy, pip_size_jpy):
        if not isinstance(val, Decimal) or not val.is_finite() or val <= 0:
            raise ValueError("JPY valuation requires positive finite inputs")
    return contract_size * pip_size_jpy / usd_jpy
