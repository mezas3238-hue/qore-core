"""Provider-rule contracts for prop-firm Challenge accounts.

The provider layer owns external hard constraints only. QORE Risk may be more
conservative, but neither CIBO nor an internal safety overlay may enlarge the
budget returned by this module.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum

from qore.kernel.errors import InfrastructureError


class ProviderContractError(InfrastructureError):
    """A provider contract or account snapshot violates a fail-closed invariant."""

    __slots__ = ()


class Provider(StrEnum):
    FTMO = "ftmo"
    FUNDEDNEXT = "fundednext"


class ChallengeProgram(StrEnum):
    FTMO_1_STEP = "ftmo-1-step"
    FTMO_2_STEP = "ftmo-2-step"
    FUNDEDNEXT_STELLAR_1_STEP = "fundednext-stellar-1-step"
    FUNDEDNEXT_STELLAR_2_STEP = "fundednext-stellar-2-step"


class ChallengeStage(StrEnum):
    SINGLE_STEP = "single-step"
    PHASE_1 = "phase-1"
    PHASE_2 = "phase-2"


class OverallLossModel(StrEnum):
    STATIC_INITIAL = "static-initial"
    TRAILING_EOD_BALANCE = "trailing-eod-balance"


class TradingPlatform(StrEnum):
    CTRADER = "ctrader"
    MT4 = "mt4"
    MT5 = "mt5"
    MATCH_TRADER = "match-trader"
    UNKNOWN = "unknown"


class AutomationMode(StrEnum):
    AUTOMATED_ALLOWED = "automated-allowed"
    CONDITIONAL = "conditional"
    MANUAL_ONLY = "manual-only"
    FAIL_CLOSED = "fail-closed"


class RuleAuthority(StrEnum):
    PROVIDER_RULE = "provider-rule"
    QORE_POLICY = "qore-policy"


@dataclass(frozen=True, slots=True)
class ProviderSource:
    url: str
    verified_on: str

    def __post_init__(self) -> None:
        if not self.url.startswith("https://"):
            raise ProviderContractError("provider source must use https")
        if not self.verified_on:
            raise ProviderContractError("provider source requires verification date")


@dataclass(frozen=True, slots=True)
class ProviderContract:
    contract_id: str
    provider: Provider
    program: ChallengeProgram
    stage: ChallengeStage
    daily_loss_fraction: Decimal
    maximum_loss_fraction: Decimal
    overall_loss_model: OverallLossModel
    profit_target_fraction: Decimal
    minimum_trading_days: int
    daily_reset_clock: str
    daily_reset_timezone: str
    floating_pnl_counts: bool
    commissions_count: bool
    swaps_count: bool
    fees_count: bool
    best_day_max_positive_profit_fraction: Decimal | None
    unlimited_trading_period: bool
    sources: tuple[ProviderSource, ...]

    def __post_init__(self) -> None:
        if not self.contract_id:
            raise ProviderContractError("contract_id must be non-empty")
        if not isinstance(self.provider, Provider):
            raise ProviderContractError("provider must be Provider")
        if not isinstance(self.program, ChallengeProgram):
            raise ProviderContractError("program must be ChallengeProgram")
        if not isinstance(self.stage, ChallengeStage):
            raise ProviderContractError("stage must be ChallengeStage")
        for name, value in (
            ("daily_loss_fraction", self.daily_loss_fraction),
            ("maximum_loss_fraction", self.maximum_loss_fraction),
            ("profit_target_fraction", self.profit_target_fraction),
        ):
            if not isinstance(value, Decimal) or not value.is_finite():
                raise ProviderContractError(f"{name} must be a finite Decimal")
            if not Decimal(0) < value < Decimal(1):
                raise ProviderContractError(f"{name} must be in (0, 1)")
        if self.daily_loss_fraction >= self.maximum_loss_fraction:
            raise ProviderContractError("daily loss must be below maximum loss")
        if self.minimum_trading_days < 0:
            raise ProviderContractError("minimum trading days cannot be negative")
        if not self.daily_reset_clock or not self.daily_reset_timezone:
            raise ProviderContractError("daily reset semantics must be explicit")
        if self.best_day_max_positive_profit_fraction is not None:
            value = self.best_day_max_positive_profit_fraction
            if not Decimal(0) < value <= Decimal(1):
                raise ProviderContractError("best-day fraction must be in (0, 1]")
        if not self.sources:
            raise ProviderContractError("provider contract requires source evidence")
        if any(not isinstance(source, ProviderSource) for source in self.sources):
            raise ProviderContractError("sources must contain ProviderSource values")


@dataclass(frozen=True, slots=True)
class ProviderAccountSnapshot:
    """Provider-account state required to evaluate hard Challenge boundaries."""

    initial_balance: Decimal
    balance: Decimal
    equity: Decimal
    daily_reset_balance: Decimal
    highest_eod_balance: Decimal
    trading_days_completed: int
    open_positions: int = 0
    best_day_profit: Decimal = Decimal(0)
    positive_days_profit: Decimal = Decimal(0)

    def __post_init__(self) -> None:
        for name, value in (
            ("initial_balance", self.initial_balance),
            ("balance", self.balance),
            ("equity", self.equity),
            ("daily_reset_balance", self.daily_reset_balance),
            ("highest_eod_balance", self.highest_eod_balance),
            ("best_day_profit", self.best_day_profit),
            ("positive_days_profit", self.positive_days_profit),
        ):
            if not isinstance(value, Decimal) or not value.is_finite():
                raise ProviderContractError(f"{name} must be a finite Decimal")
        if min(
            self.initial_balance,
            self.balance,
            self.equity,
            self.daily_reset_balance,
            self.highest_eod_balance,
        ) <= 0:
            raise ProviderContractError("account balance/equity values must be positive")
        if self.highest_eod_balance < self.initial_balance:
            raise ProviderContractError(
                "highest_eod_balance cannot be below initial balance"
            )
        if self.trading_days_completed < 0 or self.open_positions < 0:
            raise ProviderContractError("account counters cannot be negative")
        if self.best_day_profit < 0 or self.positive_days_profit < 0:
            raise ProviderContractError("best-day inputs cannot be negative")
        if self.best_day_profit > self.positive_days_profit:
            raise ProviderContractError(
                "best-day profit cannot exceed positive-days profit"
            )


@dataclass(frozen=True, slots=True)
class ProviderRiskBudget:
    contract_id: str
    authority: RuleAuthority
    daily_floor: Decimal
    overall_floor: Decimal
    effective_floor: Decimal
    daily_headroom: Decimal
    overall_headroom: Decimal
    provider_headroom: Decimal
    hard_breach: bool
    profit_target_balance: Decimal
    profit_target_met: bool
    minimum_trading_days_met: bool
    best_day_rule_met: bool
    challenge_completion_eligible: bool

    def __post_init__(self) -> None:
        if self.authority is not RuleAuthority.PROVIDER_RULE:
            raise ProviderContractError(
                "ProviderRiskBudget authority must be PROVIDER_RULE"
            )
        for name, value in (
            ("daily_floor", self.daily_floor),
            ("overall_floor", self.overall_floor),
            ("effective_floor", self.effective_floor),
            ("daily_headroom", self.daily_headroom),
            ("overall_headroom", self.overall_headroom),
            ("provider_headroom", self.provider_headroom),
            ("profit_target_balance", self.profit_target_balance),
        ):
            if not isinstance(value, Decimal) or not value.is_finite():
                raise ProviderContractError(f"{name} must be a finite Decimal")
        if min(self.daily_headroom, self.overall_headroom, self.provider_headroom) < 0:
            raise ProviderContractError("provider headroom cannot be negative")


@dataclass(frozen=True, slots=True)
class ProviderExecutionCapability:
    provider: Provider
    platform: TradingPlatform
    mode: AutomationMode
    automated_order_submission_allowed: bool
    reason: str

    def __post_init__(self) -> None:
        if not self.reason:
            raise ProviderContractError("execution capability requires a reason")
        if self.automated_order_submission_allowed and self.mode in (
            AutomationMode.MANUAL_ONLY,
            AutomationMode.FAIL_CLOSED,
        ):
            raise ProviderContractError(
                "manual/fail-closed capability cannot allow automated submission"
            )


def evaluate_provider_budget(
    contract: ProviderContract,
    snapshot: ProviderAccountSnapshot,
) -> ProviderRiskBudget:
    """Evaluate provider hard floors without applying QORE safety overlays."""

    if not isinstance(contract, ProviderContract):
        raise ProviderContractError("contract must be ProviderContract")
    if not isinstance(snapshot, ProviderAccountSnapshot):
        raise ProviderContractError("snapshot must be ProviderAccountSnapshot")

    daily_amount = snapshot.initial_balance * contract.daily_loss_fraction
    daily_floor = snapshot.daily_reset_balance - daily_amount
    maximum_amount = snapshot.initial_balance * contract.maximum_loss_fraction

    if contract.overall_loss_model is OverallLossModel.STATIC_INITIAL:
        overall_floor = snapshot.initial_balance - maximum_amount
    elif contract.overall_loss_model is OverallLossModel.TRAILING_EOD_BALANCE:
        trailing_reference = max(
            snapshot.initial_balance,
            snapshot.highest_eod_balance,
        )
        overall_floor = trailing_reference - maximum_amount
    else:  # pragma: no cover - exhaustive enum guard
        raise ProviderContractError("unsupported overall loss model")

    daily_breach = snapshot.equity < daily_floor
    overall_breach = snapshot.equity < overall_floor
    daily_headroom = max(Decimal(0), snapshot.equity - daily_floor)
    overall_headroom = max(Decimal(0), snapshot.equity - overall_floor)
    provider_headroom = min(daily_headroom, overall_headroom)
    target_balance = snapshot.initial_balance * (
        Decimal(1) + contract.profit_target_fraction
    )
    profit_target_met = (
        snapshot.balance >= target_balance and snapshot.open_positions == 0
    )
    minimum_days_met = (
        snapshot.trading_days_completed >= contract.minimum_trading_days
    )
    best_day_rule_met = _best_day_rule_met(contract, snapshot)
    hard_breach = daily_breach or overall_breach

    return ProviderRiskBudget(
        contract_id=contract.contract_id,
        authority=RuleAuthority.PROVIDER_RULE,
        daily_floor=daily_floor,
        overall_floor=overall_floor,
        effective_floor=max(daily_floor, overall_floor),
        daily_headroom=daily_headroom,
        overall_headroom=overall_headroom,
        provider_headroom=provider_headroom,
        hard_breach=hard_breach,
        profit_target_balance=target_balance,
        profit_target_met=profit_target_met,
        minimum_trading_days_met=minimum_days_met,
        best_day_rule_met=best_day_rule_met,
        challenge_completion_eligible=(
            not hard_breach
            and profit_target_met
            and minimum_days_met
            and best_day_rule_met
        ),
    )


def _best_day_rule_met(
    contract: ProviderContract,
    snapshot: ProviderAccountSnapshot,
) -> bool:
    threshold = contract.best_day_max_positive_profit_fraction
    if threshold is None:
        return True
    if snapshot.positive_days_profit <= 0:
        return False
    return snapshot.best_day_profit <= snapshot.positive_days_profit * threshold


def execution_capability(
    contract: ProviderContract,
    *,
    platform: TradingPlatform,
    initial_balance: Decimal,
    fundednext_ea_addon_enabled: bool = False,
) -> ProviderExecutionCapability:
    """Return provider/platform automation capability and fail closed on unknowns."""

    if not isinstance(initial_balance, Decimal) or not initial_balance.is_finite():
        raise ProviderContractError("initial_balance must be a finite Decimal")
    if initial_balance <= 0:
        raise ProviderContractError("initial_balance must be positive")
    if not isinstance(platform, TradingPlatform):
        raise ProviderContractError("platform must be TradingPlatform")

    if platform is TradingPlatform.UNKNOWN:
        return ProviderExecutionCapability(
            provider=contract.provider,
            platform=platform,
            mode=AutomationMode.FAIL_CLOSED,
            automated_order_submission_allowed=False,
            reason="unknown-platform",
        )

    if contract.provider is Provider.FTMO:
        if platform in (
            TradingPlatform.CTRADER,
            TradingPlatform.MT4,
            TradingPlatform.MT5,
        ):
            return ProviderExecutionCapability(
                provider=contract.provider,
                platform=platform,
                mode=AutomationMode.AUTOMATED_ALLOWED,
                automated_order_submission_allowed=True,
                reason="ftmo-algorithmic-trading-provider-supported",
            )
        return ProviderExecutionCapability(
            provider=contract.provider,
            platform=platform,
            mode=AutomationMode.FAIL_CLOSED,
            automated_order_submission_allowed=False,
            reason="ftmo-platform-not-frozen-for-qore-automation",
        )

    if platform in (TradingPlatform.CTRADER, TradingPlatform.MATCH_TRADER):
        return ProviderExecutionCapability(
            provider=contract.provider,
            platform=platform,
            mode=AutomationMode.MANUAL_ONLY,
            automated_order_submission_allowed=False,
            reason="fundednext-platform-automation-prohibited",
        )

    if platform in (TradingPlatform.MT4, TradingPlatform.MT5):
        if initial_balance >= Decimal("50000"):
            return ProviderExecutionCapability(
                provider=contract.provider,
                platform=platform,
                mode=AutomationMode.MANUAL_ONLY,
                automated_order_submission_allowed=False,
                reason="fundednext-account-size-requires-manual-trading",
            )
        if not fundednext_ea_addon_enabled:
            return ProviderExecutionCapability(
                provider=contract.provider,
                platform=platform,
                mode=AutomationMode.CONDITIONAL,
                automated_order_submission_allowed=False,
                reason="fundednext-ea-option-not-confirmed",
            )
        return ProviderExecutionCapability(
            provider=contract.provider,
            platform=platform,
            mode=AutomationMode.CONDITIONAL,
            automated_order_submission_allowed=True,
            reason="fundednext-sub-50k-mt-ea-option-confirmed",
        )

    return ProviderExecutionCapability(
        provider=contract.provider,
        platform=platform,
        mode=AutomationMode.FAIL_CLOSED,
        automated_order_submission_allowed=False,
        reason="unsupported-provider-platform-combination",
    )


_VERIFIED_ON = "2026-09-13"
_FTMO_OBJECTIVES = ProviderSource(
    "https://ftmo.com/en/trading-objectives/",
    _VERIFIED_ON,
)
_FTMO_STRATEGIES = ProviderSource(
    "https://ftmo.com/faq/which-instruments-can-i-trade-and-what-strategies-am-i-allowed-to-use/",
    _VERIFIED_ON,
)
_FUNDEDNEXT_1_STEP = ProviderSource(
    "https://help.fundednext.com/en/articles/8021061-what-are-the-rules-for-the-stellar-1-step-challenge-at-fundednext",
    _VERIFIED_ON,
)
_FUNDEDNEXT_2_STEP = ProviderSource(
    "https://help.fundednext.com/en/articles/8021076-what-rules-do-i-need-to-follow-in-the-stellar-2-step-challenge",
    _VERIFIED_ON,
)
_FUNDEDNEXT_DAILY = ProviderSource(
    "https://help.fundednext.com/en/articles/8019811-how-can-i-calculate-the-daily-loss-limit",
    _VERIFIED_ON,
)
_FUNDEDNEXT_EA = ProviderSource(
    "https://help.fundednext.com/en/articles/8020763-is-ea-allowed-in-fundednext",
    _VERIFIED_ON,
)


FTMO_1_STEP_CHALLENGE = ProviderContract(
    contract_id="FTMO_1_STEP_CHALLENGE_2026_09_13",
    provider=Provider.FTMO,
    program=ChallengeProgram.FTMO_1_STEP,
    stage=ChallengeStage.SINGLE_STEP,
    daily_loss_fraction=Decimal("0.03"),
    maximum_loss_fraction=Decimal("0.10"),
    overall_loss_model=OverallLossModel.TRAILING_EOD_BALANCE,
    profit_target_fraction=Decimal("0.10"),
    minimum_trading_days=0,
    daily_reset_clock="00:00",
    daily_reset_timezone="Europe/Prague",
    floating_pnl_counts=True,
    commissions_count=True,
    swaps_count=True,
    fees_count=False,
    best_day_max_positive_profit_fraction=Decimal("0.50"),
    unlimited_trading_period=True,
    sources=(_FTMO_OBJECTIVES, _FTMO_STRATEGIES),
)

FTMO_2_STEP_PHASE_1 = ProviderContract(
    contract_id="FTMO_2_STEP_PHASE_1_2026_09_13",
    provider=Provider.FTMO,
    program=ChallengeProgram.FTMO_2_STEP,
    stage=ChallengeStage.PHASE_1,
    daily_loss_fraction=Decimal("0.05"),
    maximum_loss_fraction=Decimal("0.10"),
    overall_loss_model=OverallLossModel.STATIC_INITIAL,
    profit_target_fraction=Decimal("0.10"),
    minimum_trading_days=4,
    daily_reset_clock="00:00",
    daily_reset_timezone="Europe/Prague",
    floating_pnl_counts=True,
    commissions_count=True,
    swaps_count=True,
    fees_count=False,
    best_day_max_positive_profit_fraction=None,
    unlimited_trading_period=True,
    sources=(_FTMO_OBJECTIVES, _FTMO_STRATEGIES),
)

FTMO_2_STEP_PHASE_2 = ProviderContract(
    contract_id="FTMO_2_STEP_PHASE_2_2026_09_13",
    provider=Provider.FTMO,
    program=ChallengeProgram.FTMO_2_STEP,
    stage=ChallengeStage.PHASE_2,
    daily_loss_fraction=Decimal("0.05"),
    maximum_loss_fraction=Decimal("0.10"),
    overall_loss_model=OverallLossModel.STATIC_INITIAL,
    profit_target_fraction=Decimal("0.05"),
    minimum_trading_days=4,
    daily_reset_clock="00:00",
    daily_reset_timezone="Europe/Prague",
    floating_pnl_counts=True,
    commissions_count=True,
    swaps_count=True,
    fees_count=False,
    best_day_max_positive_profit_fraction=None,
    unlimited_trading_period=True,
    sources=(_FTMO_OBJECTIVES, _FTMO_STRATEGIES),
)

FUNDEDNEXT_STELLAR_1_STEP = ProviderContract(
    contract_id="FUNDEDNEXT_STELLAR_1_STEP_2026_09_13",
    provider=Provider.FUNDEDNEXT,
    program=ChallengeProgram.FUNDEDNEXT_STELLAR_1_STEP,
    stage=ChallengeStage.SINGLE_STEP,
    daily_loss_fraction=Decimal("0.03"),
    maximum_loss_fraction=Decimal("0.06"),
    overall_loss_model=OverallLossModel.STATIC_INITIAL,
    profit_target_fraction=Decimal("0.10"),
    minimum_trading_days=2,
    daily_reset_clock="00:00",
    daily_reset_timezone="FundedNext server GMT+2/GMT+3 seasonal",
    floating_pnl_counts=True,
    commissions_count=True,
    swaps_count=True,
    fees_count=True,
    best_day_max_positive_profit_fraction=None,
    unlimited_trading_period=True,
    sources=(_FUNDEDNEXT_1_STEP, _FUNDEDNEXT_DAILY, _FUNDEDNEXT_EA),
)

FUNDEDNEXT_STELLAR_2_STEP_PHASE_1 = ProviderContract(
    contract_id="FUNDEDNEXT_STELLAR_2_STEP_PHASE_1_2026_09_13",
    provider=Provider.FUNDEDNEXT,
    program=ChallengeProgram.FUNDEDNEXT_STELLAR_2_STEP,
    stage=ChallengeStage.PHASE_1,
    daily_loss_fraction=Decimal("0.05"),
    maximum_loss_fraction=Decimal("0.10"),
    overall_loss_model=OverallLossModel.STATIC_INITIAL,
    profit_target_fraction=Decimal("0.08"),
    minimum_trading_days=5,
    daily_reset_clock="00:00",
    daily_reset_timezone="FundedNext server GMT+2/GMT+3 seasonal",
    floating_pnl_counts=True,
    commissions_count=True,
    swaps_count=True,
    fees_count=True,
    best_day_max_positive_profit_fraction=None,
    unlimited_trading_period=True,
    sources=(_FUNDEDNEXT_2_STEP, _FUNDEDNEXT_DAILY, _FUNDEDNEXT_EA),
)

FUNDEDNEXT_STELLAR_2_STEP_PHASE_2 = ProviderContract(
    contract_id="FUNDEDNEXT_STELLAR_2_STEP_PHASE_2_2026_09_13",
    provider=Provider.FUNDEDNEXT,
    program=ChallengeProgram.FUNDEDNEXT_STELLAR_2_STEP,
    stage=ChallengeStage.PHASE_2,
    daily_loss_fraction=Decimal("0.05"),
    maximum_loss_fraction=Decimal("0.10"),
    overall_loss_model=OverallLossModel.STATIC_INITIAL,
    profit_target_fraction=Decimal("0.05"),
    minimum_trading_days=5,
    daily_reset_clock="00:00",
    daily_reset_timezone="FundedNext server GMT+2/GMT+3 seasonal",
    floating_pnl_counts=True,
    commissions_count=True,
    swaps_count=True,
    fees_count=True,
    best_day_max_positive_profit_fraction=None,
    unlimited_trading_period=True,
    sources=(_FUNDEDNEXT_2_STEP, _FUNDEDNEXT_DAILY, _FUNDEDNEXT_EA),
)


CHALLENGE_CONTRACTS: dict[str, ProviderContract] = {
    contract.contract_id: contract
    for contract in (
        FTMO_1_STEP_CHALLENGE,
        FTMO_2_STEP_PHASE_1,
        FTMO_2_STEP_PHASE_2,
        FUNDEDNEXT_STELLAR_1_STEP,
        FUNDEDNEXT_STELLAR_2_STEP_PHASE_1,
        FUNDEDNEXT_STELLAR_2_STEP_PHASE_2,
    )
}
