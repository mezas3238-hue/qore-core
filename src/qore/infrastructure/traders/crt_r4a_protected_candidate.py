"""QORE CRT seven-family DEMO trade *proposal*, never execution authority.

Consumes a distinct, causal same-provider family event and authenticated
broker quote/contract/equity evidence. The output is NOT an OrderIntent,
AuthorizedOrderIntent or ExecutionSubmission: cTrader's current QORE order
codec does NOT carry broker-native protective SL/TP. No broker IO or LIVE.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import ROUND_FLOOR, Decimal
from enum import StrEnum
from uuid import NAMESPACE_URL, UUID, uuid5

from qore.infrastructure.market_test_environment import MarketRuntimeEnvironment

PINE_SOURCE_BLOB = "693e3f49719e86e2ea0702f7b355af33bd0c4c7c"
QORE_CRT_34 = (
    "AUDJPY", "GBPUSD", "GBPJPY", "XAUUSD", "USTEC", "US500", "US30",
    "BTCUSD", "AUDUSD", "USDCAD", "USDJPY", "EURUSD", "USDCHF",
    "NZDUSD", "NZDJPY", "NZDCHF", "XAGUSD", "AUDCAD", "AUDCHF",
    "AUDNZD", "CADCHF", "CADJPY", "CHFJPY", "EURAUD", "EURCAD",
    "EURCHF", "EURGBP", "EURJPY", "EURNZD", "GBPAUD", "GBPCAD",
    "GBPCHF", "GBPNZD", "NZDCAD",
)
D0 = Decimal("0")
D1 = Decimal("1")


class CRTCandidateError(ValueError):
    """No trading authority or trustworthy price/risk state exists."""


class CRTFamily(StrEnum):
    TWO_C_MSS_C2 = "CRT_2C_RETURN_MSS15_IN_C2"
    TWO_C_MSS_C3 = "CRT_2C_RETURN_MSS15_IN_C3"
    TRUE_THREE_C = "CRT_TRUE3C_MSS5"
    INSIDE = "CRT_INSIDE_RETURN"
    MULTI4 = "CRT_MULTI4"
    MULTIN = "CRT_MULTI_N"
    M15_RETEST = "CRT_M15_RETEST"


def _aware(value: datetime, name: str) -> None:
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise CRTCandidateError(f"{name} must be timezone-aware")


def _positive(value: Decimal, name: str) -> None:
    if not isinstance(value, Decimal) or not value.is_finite() or value <= D0:
        raise CRTCandidateError(f"{name} must be finite positive Decimal")


def _tick_aligned(value: Decimal, tick: Decimal) -> bool:
    return (value / tick) == (value / tick).to_integral_value()


@dataclass(frozen=True, slots=True)
class CRTClosedSignal:
    """An external hypothesis; no assertion of Pine parity is inferred."""

    event_id: str
    symbol: str
    family: CRTFamily
    direction: int
    c1_at: datetime
    sweep_at: datetime
    mss_at: datetime
    ratified_at: datetime
    available_at: datetime
    c1_high: Decimal
    c1_low: Decimal
    sweep_high: Decimal
    sweep_low: Decimal
    source_pine_blob: str = PINE_SOURCE_BLOB
    source_feed: str = "IC"

    def __post_init__(self) -> None:
        if (
            not isinstance(self.event_id, str)
            or not self.event_id.strip()
            or self.symbol not in QORE_CRT_34
            or not isinstance(self.family, CRTFamily)
            or self.direction not in (1, -1)
            or self.source_pine_blob != PINE_SOURCE_BLOB
            or self.source_feed != "IC"
        ):
            raise CRTCandidateError("invalid CRT event origin or family")
        for name in ("c1_at", "sweep_at", "mss_at", "ratified_at", "available_at"):
            _aware(getattr(self, name), name)
        if not (
            self.c1_at < self.sweep_at < self.mss_at <= self.available_at
            and self.ratified_at <= self.available_at
            and self.available_at == max(self.ratified_at, self.mss_at)
        ):
            raise CRTCandidateError("noncausal CRT/MSS availability")
        if self.family is CRTFamily.TWO_C_MSS_C2 and self.mss_at > self.ratified_at:
            raise CRTCandidateError("C2 MSS occurs after C2 ratification")
        if self.family is CRTFamily.TWO_C_MSS_C3 and self.mss_at <= self.ratified_at:
            raise CRTCandidateError("C3 MSS must follow C2 ratification")
        for name in ("c1_high", "c1_low", "sweep_high", "sweep_low"):
            _positive(getattr(self, name), name)
        if self.c1_high <= self.c1_low or self.sweep_high < self.sweep_low:
            raise CRTCandidateError("invalid frozen H4 source geometry")


@dataclass(frozen=True, slots=True)
class CRTBrokerQuote:
    symbol: str
    broker: str
    symbol_id: int
    bid: Decimal
    ask: Decimal
    observed_at: datetime

    def __post_init__(self) -> None:
        if self.symbol not in QORE_CRT_34 or self.broker != "ICMARKETS_DEMO":
            raise CRTCandidateError("quote must be the exact IC Markets DEMO symbol")
        if type(self.symbol_id) is not int or self.symbol_id <= 0:
            raise CRTCandidateError("invalid broker symbol id")
        _positive(self.bid, "bid")
        _positive(self.ask, "ask")
        _aware(self.observed_at, "quote timestamp")
        if self.ask <= self.bid:
            raise CRTCandidateError("bid/ask must be uncrossed and nonzero spread")


@dataclass(frozen=True, slots=True)
class CRTBrokerContract:
    symbol: str
    symbol_id: int
    price_tick: Decimal
    value_per_tick_per_unit: Decimal
    volume_step: Decimal
    volume_min: Decimal
    volume_max: Decimal
    account_currency: str
    verified_at: datetime
    provider_evidence_sha256: str

    def __post_init__(self) -> None:
        if self.symbol not in QORE_CRT_34 or type(self.symbol_id) is not int or self.symbol_id <= 0:
            raise CRTCandidateError("unknown broker symbol metadata")
        for name in (
            "price_tick", "value_per_tick_per_unit", "volume_step",
            "volume_min", "volume_max",
        ):
            _positive(getattr(self, name), name)
        if self.volume_max < self.volume_min or not _tick_aligned(
            self.volume_min, self.volume_step
        ):
            raise CRTCandidateError("broker volume bounds misaligned")
        if (
            not isinstance(self.account_currency, str)
            or not self.account_currency.isalpha()
            or len(self.account_currency) != 3
            or len(self.provider_evidence_sha256) != 64
            or any(c not in "0123456789abcdef" for c in self.provider_evidence_sha256)
        ):
            raise CRTCandidateError("missing exact broker contract/account currency evidence")
        _aware(self.verified_at, "contract verified_at")


@dataclass(frozen=True, slots=True)
class CRTDemoAccountRisk:
    """Explicit risk ceilings; NOT an upstream QORE Risk approval."""

    account_ref: str
    environment: MarketRuntimeEnvironment
    currency: str
    equity: Decimal
    risk_fraction: Decimal
    max_spread_ticks: int
    slippage_reserve_ticks: int
    max_open_and_pending: int
    daily_loss_fraction: Decimal

    def __post_init__(self) -> None:
        if not self.account_ref or self.environment is not MarketRuntimeEnvironment.DEMO:
            raise CRTCandidateError("LIVE/ambiguous accounts forbidden")
        _positive(self.equity, "equity")
        _positive(self.risk_fraction, "risk fraction")
        if (
            self.risk_fraction > Decimal("0.01")
            or self.currency != self.currency.upper()
            or len(self.currency) != 3
            or type(self.max_spread_ticks) is not int
            or self.max_spread_ticks < 1
            or type(self.slippage_reserve_ticks) is not int
            or self.slippage_reserve_ticks < 1
            or type(self.max_open_and_pending) is not int
            or self.max_open_and_pending < 0
            or not isinstance(self.daily_loss_fraction, Decimal)
            or not self.daily_loss_fraction.is_finite()
            or self.daily_loss_fraction < 0
        ):
            raise CRTCandidateError("invalid or excessive demo risk envelope")


@dataclass(frozen=True, slots=True)
class CRTProtectedProposal:
    """A non-executable, broker-denominated proposal pending ALL external gates."""

    signal_id: str
    family: CRTFamily
    symbol: str
    symbol_id: int
    direction: int
    entry_reference: Decimal
    stop_loss: Decimal
    take_profit: Decimal
    quantity: Decimal
    money_risk_including_slippage: Decimal
    gross_reward_risk_ratio: Decimal
    idempotency_key: UUID
    native_bracket_required: bool = True
    can_submit: bool = False

    def __post_init__(self) -> None:
        if not self.native_bracket_required or self.can_submit:
            raise CRTCandidateError("CRT plan must remain NON-EXECUTABLE before native SLTP")
        for name in ("entry_reference", "stop_loss", "take_profit", "quantity"):
            _positive(getattr(self, name), name)


def plan_crt_protected_candidate(
    signal: CRTClosedSignal,
    quote: CRTBrokerQuote,
    contract: CRTBrokerContract,
    risk: CRTDemoAccountRisk,
    *,
    evaluated_at: datetime,
    min_gross_rr: Decimal = Decimal("1.5"),
    stop_buffer_fraction: Decimal = Decimal("0.15"),
    max_signal_age: timedelta = timedelta(minutes=5),
    max_quote_age: timedelta = timedelta(seconds=30),
) -> CRTProtectedProposal:
    """Quantify a CRT entry with conservative account-currency risk, no submit.

    Requires an exact same-symbol contract, fresh bid/ask and closed-bar time.
    Source parity and execution protections are NOT independently certified.
    All outputs keep can_submit=False. Never auto-approve an OrderIntent.
    """
    if not all(
        isinstance(obj, typ)
        for obj, typ in (
            (signal, CRTClosedSignal),
            (quote, CRTBrokerQuote),
            (contract, CRTBrokerContract),
            (risk, CRTDemoAccountRisk),
        )
    ):
        raise CRTCandidateError("explicit typed signal/quote/contract/risk required")
    _aware(evaluated_at, "evaluated_at")
    _positive(min_gross_rr, "min_gross_rr")
    _positive(stop_buffer_fraction, "stop_buffer_fraction")
    if min_gross_rr < D1 or stop_buffer_fraction > D1:
        raise CRTCandidateError("risk policy cannot lower R:R or exaggerate stop buffer")
    if (
        signal.symbol != quote.symbol
        or quote.symbol != contract.symbol
        or quote.symbol_id != contract.symbol_id
        or risk.currency != contract.account_currency
    ):
        raise CRTCandidateError("broker quote/contract/account lineage mismatch")
    if (
        quote.observed_at < signal.available_at
        or evaluated_at < quote.observed_at
        or evaluated_at < signal.available_at
        or evaluated_at - signal.available_at > max_signal_age
        or evaluated_at - quote.observed_at > max_quote_age
        or evaluated_at - contract.verified_at > timedelta(days=1)
        or contract.verified_at > evaluated_at
        or risk.max_open_and_pending != 0
        or risk.daily_loss_fraction >= Decimal("0.02")
    ):
        raise CRTCandidateError("stale/missing source, unresolved exposure, or daily loss gate")
    spread_ticks = (quote.ask - quote.bid) / contract.price_tick
    if spread_ticks > risk.max_spread_ticks:
        raise CRTCandidateError("broker spread exceeds risk envelope")
    for name in ("c1_high", "c1_low", "sweep_high", "sweep_low"):
        if not _tick_aligned(getattr(signal, name), contract.price_tick):
            raise CRTCandidateError("source geometry not aligned with broker price tick")
    entry = quote.ask if signal.direction == 1 else quote.bid
    if not _tick_aligned(entry, contract.price_tick):
        raise CRTCandidateError("broker quote not aligned to own symbol tick")
    candle_range = signal.c1_high - signal.c1_low
    tick_buffer = (candle_range * stop_buffer_fraction / contract.price_tick).to_integral_value(
        rounding=ROUND_FLOOR
    )
    buffer = max(D1, tick_buffer) * contract.price_tick
    if signal.direction == 1:
        stop = min(signal.c1_low, signal.sweep_low) - buffer
        target = signal.c1_high
        loss_distance = entry - stop
        reward_distance = target - entry
    else:
        stop = max(signal.c1_high, signal.sweep_high) + buffer
        target = signal.c1_low
        loss_distance = stop - entry
        reward_distance = entry - target
    reserve = risk.slippage_reserve_ticks * contract.price_tick
    if stop <= D0 or target <= D0 or loss_distance <= D0 or reward_distance <= D0:
        raise CRTCandidateError("no valid sided stop and profit target at current bid/ask")
    effective_loss = loss_distance + reserve
    rr = reward_distance / effective_loss
    if rr < min_gross_rr:
        raise CRTCandidateError("trade does not satisfy stressed gross reward/risk")
    value_per_unit = (
        effective_loss / contract.price_tick * contract.value_per_tick_per_unit
    )
    budget = risk.equity * risk.risk_fraction
    steps = (budget / value_per_unit / contract.volume_step).to_integral_value(
        rounding=ROUND_FLOOR
    )
    quantity = min(steps * contract.volume_step, contract.volume_max)
    if quantity < contract.volume_min or not _tick_aligned(
        quantity, contract.volume_step
    ):
        raise CRTCandidateError("budget cannot afford broker minimum volume")
    risk_money = quantity * value_per_unit
    if risk_money > budget:
        raise CRTCandidateError("broker risk exceeds account budget")
    key = uuid5(
        NAMESPACE_URL,
        "|".join((
            "qore.crt.r4a.v1", risk.account_ref, signal.symbol,
            signal.family.value, signal.event_id, signal.source_pine_blob,
        )),
    )
    return CRTProtectedProposal(
        signal_id=signal.event_id,
        family=signal.family,
        symbol=signal.symbol,
        symbol_id=contract.symbol_id,
        direction=signal.direction,
        entry_reference=entry,
        stop_loss=stop,
        take_profit=target,
        quantity=quantity,
        money_risk_including_slippage=risk_money,
        gross_reward_risk_ratio=rr,
        idempotency_key=key,
    )
