"""FundedNext Stellar Instant provider contract for the QORE $2K pilot.

Provider rules constrain account-wide QORE Risk. This module does not issue a
RiskAuthorization and never changes Trader or CIBO methodology.

The exact purchased account is governed here by the verified Stellar Instant
6% trailing Maximum Loss Limit and the applicable cumulative open-risk limit.
QORE-internal operating buffers/heat limits are intentionally defined in a
separate module and remain stricter than the provider open-risk ceiling.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from enum import StrEnum

from qore.kernel.errors import InfrastructureError


class StellarInstantContractError(InfrastructureError):
    """The Stellar Instant provider state is incomplete or internally inconsistent."""

    __slots__ = ()


class RuleVerificationState(StrEnum):
    CURRENT = "current"
    STALE = "stale"
    CONFLICTED = "conflicted"


class AutomationVerificationState(StrEnum):
    VERIFIED = "verified"
    UNVERIFIED = "unverified"
    DISALLOWED = "disallowed"


PROVIDER = "FUNDEDNEXT"
PROGRAM = "STELLAR_INSTANT"
PLATFORM = "MT5"
PILOT_INITIAL_BALANCE = Decimal("2000")
MAXIMUM_LOSS_FRACTION = Decimal("0.06")
SEPARATE_MAX_RISK_AT_ANY_TIME_FRACTION = Decimal("0.03")
FOREX_OPEN_COMMISSION_PER_LOT_USD = Decimal("7")
INDEX_OPEN_COMMISSION_PER_LOT_USD = Decimal("0")
PILOT_SYMBOL_MAP: dict[str, str] = {
    "AUDJPY": "AUDJPY",
    "GBPUSD": "GBPUSD",
    "GBPJPY": "GBPJPY",
    "NAS100": "NDX100",
    "SP500": "SPX500",
    "US30": "US30",
}

# Two retained documentation surfaces disagree on index/commodity leverage.
# QORE therefore refuses to use documentation leverage for order sizing. Live
# MT5 SymbolInfo/Specification and order_calc_margin are execution authority.
DOCUMENTED_FOREX_LEVERAGE = (Decimal("30"),)
DOCUMENTED_INDEX_LEVERAGE = (Decimal("5"), Decimal("10"))
DOCUMENTED_COMMODITY_LEVERAGE = (Decimal("7.5"), Decimal("15"))


@dataclass(frozen=True, slots=True)
class StellarInstantRuleVerification:
    verification_state: RuleVerificationState
    automation_state: AutomationVerificationState
    ea_addon_verified: bool
    platform_verified: bool
    exact_product_verified: bool
    leverage_execution_source: str = "MT5_SYMBOL_INFO"

    def __post_init__(self) -> None:
        if type(self.verification_state) is not RuleVerificationState:
            raise StellarInstantContractError("verification_state must be canonical")
        if type(self.automation_state) is not AutomationVerificationState:
            raise StellarInstantContractError("automation_state must be canonical")
        if self.leverage_execution_source != "MT5_SYMBOL_INFO":
            raise StellarInstantContractError("Stellar Instant sizing must use live MT5 SymbolInfo")

    def is_current(self, now: datetime) -> bool:
        _aware(now, "now")
        return self.verification_state is RuleVerificationState.CURRENT

    def automated_mt5_allowed(self, now: datetime) -> bool:
        return (
            self.is_current(now)
            and self.automation_state is AutomationVerificationState.VERIFIED
            and self.ea_addon_verified
            and self.platform_verified
            and self.exact_product_verified
        )


@dataclass(frozen=True, slots=True)
class StellarInstantAccountSnapshot:
    """Provider state required to reconstruct and verify the 6% trailing MLL."""

    initial_balance: Decimal
    balance: Decimal
    equity: Decimal
    highest_closed_balance: Decimal
    previous_active_mll: Decimal
    provider_reported_mll: Decimal | None = None

    def __post_init__(self) -> None:
        for name, value in (
            ("initial_balance", self.initial_balance),
            ("balance", self.balance),
            ("equity", self.equity),
            ("highest_closed_balance", self.highest_closed_balance),
            ("previous_active_mll", self.previous_active_mll),
        ):
            _positive(value, name)
        if self.provider_reported_mll is not None:
            _positive(self.provider_reported_mll, "provider_reported_mll")
        if self.highest_closed_balance < self.initial_balance:
            raise StellarInstantContractError(
                "highest_closed_balance cannot be below initial balance"
            )
        allowance = self.initial_balance * MAXIMUM_LOSS_FRACTION
        initial_floor = self.initial_balance - allowance
        if not initial_floor <= self.previous_active_mll <= self.initial_balance:
            raise StellarInstantContractError("previous_active_mll violates trailing MLL bounds")


@dataclass(frozen=True, slots=True)
class StellarInstantRiskBudget:
    initial_balance: Decimal
    loss_allowance: Decimal
    reconstructed_mll: Decimal
    provider_reported_mll: Decimal | None
    active_mll: Decimal
    provider_headroom: Decimal
    # Provider cumulative open-risk ceiling consumed by account-wide Risk.
    # It is the tighter of remaining trailing-MLL headroom and 3% of initial balance.
    max_risk_at_any_time: Decimal
    hard_breach: bool
    daily_loss_limit_present: bool
    separate_max_risk_at_any_time_fraction: Decimal | None
    payout_can_lower_mll: bool
    leverage_execution_source: str

    def __post_init__(self) -> None:
        for name, value in (
            ("initial_balance", self.initial_balance),
            ("loss_allowance", self.loss_allowance),
            ("reconstructed_mll", self.reconstructed_mll),
            ("active_mll", self.active_mll),
            ("provider_headroom", self.provider_headroom),
            ("max_risk_at_any_time", self.max_risk_at_any_time),
        ):
            if not isinstance(value, Decimal) or not value.is_finite():
                raise StellarInstantContractError(f"{name} must be finite Decimal")
        if self.provider_headroom < 0:
            raise StellarInstantContractError("provider_headroom cannot be negative")
        expected_risk_cap = min(
            self.provider_headroom,
            self.initial_balance * SEPARATE_MAX_RISK_AT_ANY_TIME_FRACTION,
        )
        if self.max_risk_at_any_time != expected_risk_cap:
            raise StellarInstantContractError(
                "provider risk ceiling must enforce 3% cumulative open risk"
            )
        if self.active_mll > self.initial_balance:
            raise StellarInstantContractError("active MLL cannot trail above initial balance")
        if self.daily_loss_limit_present:
            raise StellarInstantContractError("Stellar Instant must not invent a daily loss limit")
        if self.separate_max_risk_at_any_time_fraction != SEPARATE_MAX_RISK_AT_ANY_TIME_FRACTION:
            raise StellarInstantContractError(
                "provider cumulative open-risk fraction must remain exact 3%"
            )
        if self.payout_can_lower_mll:
            raise StellarInstantContractError("payout cannot lower Stellar Instant MLL")
        if self.leverage_execution_source != "MT5_SYMBOL_INFO":
            raise StellarInstantContractError("provider budget must require MT5 leverage evidence")


def evaluate_stellar_instant_budget(
    snapshot: StellarInstantAccountSnapshot,
) -> StellarInstantRiskBudget:
    """Reconstruct the 6% capped trailing MLL and fail closed on provider mismatch."""

    if not isinstance(snapshot, StellarInstantAccountSnapshot):
        raise StellarInstantContractError("snapshot must be StellarInstantAccountSnapshot")
    allowance = snapshot.initial_balance * MAXIMUM_LOSS_FRACTION
    candidate_floor = snapshot.highest_closed_balance - allowance
    reconstructed = min(
        snapshot.initial_balance,
        max(snapshot.previous_active_mll, candidate_floor),
    )
    reported = snapshot.provider_reported_mll
    if reported is not None:
        if reported < snapshot.previous_active_mll:
            raise StellarInstantContractError("provider-reported MLL moved downward")
        if reported > snapshot.initial_balance:
            raise StellarInstantContractError("provider-reported MLL exceeds starting balance")
        if reported < reconstructed:
            raise StellarInstantContractError(
                "provider-reported MLL is looser than the invariant reconstruction"
            )
        active_mll = reported
    else:
        active_mll = reconstructed
    hard_breach = snapshot.equity < active_mll
    headroom = max(Decimal(0), snapshot.equity - active_mll)
    return StellarInstantRiskBudget(
        initial_balance=snapshot.initial_balance,
        loss_allowance=allowance,
        reconstructed_mll=reconstructed,
        provider_reported_mll=reported,
        active_mll=active_mll,
        provider_headroom=headroom,
        max_risk_at_any_time=min(
            headroom,
            snapshot.initial_balance * SEPARATE_MAX_RISK_AT_ANY_TIME_FRACTION,
        ),
        hard_breach=hard_breach,
        daily_loss_limit_present=False,
        separate_max_risk_at_any_time_fraction=SEPARATE_MAX_RISK_AT_ANY_TIME_FRACTION,
        payout_can_lower_mll=False,
        leverage_execution_source="MT5_SYMBOL_INFO",
    )


def resolve_pilot_symbol(qore_symbol: str) -> str:
    try:
        return PILOT_SYMBOL_MAP[qore_symbol]
    except KeyError as error:
        raise StellarInstantContractError(
            "symbol is outside the frozen six-market pilot"
        ) from error


def opening_commission_per_lot(qore_symbol: str) -> Decimal:
    if qore_symbol in {"AUDJPY", "GBPUSD", "GBPJPY"}:
        return FOREX_OPEN_COMMISSION_PER_LOT_USD
    if qore_symbol in {"NAS100", "SP500", "US30"}:
        return INDEX_OPEN_COMMISSION_PER_LOT_USD
    raise StellarInstantContractError("symbol is outside the frozen six-market pilot")


def _aware(value: datetime, name: str) -> None:
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise StellarInstantContractError(f"{name} must be timezone-aware")
    value.astimezone(UTC)


def _positive(value: Decimal, name: str) -> None:
    if not isinstance(value, Decimal) or not value.is_finite() or value <= 0:
        raise StellarInstantContractError(f"{name} must be positive finite Decimal")
