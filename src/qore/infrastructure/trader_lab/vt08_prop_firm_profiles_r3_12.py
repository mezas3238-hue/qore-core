"""Versioned prop-firm rule profiles for VT-08 R3.12 research.

Values are frozen from provider-published rules observed on 2026-09-12.  Profiles
are data contracts, not trading authority.  They are deliberately separated from
Trader methodology so provider rule changes cannot mutate VT-08 semantics.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal


class PropFirmProfileError(ValueError):
    """Raised when a provider profile is internally inconsistent."""


@dataclass(frozen=True, slots=True)
class PropFirmProfile:
    profile_id: str
    provider: str
    program: str
    version_date: str
    starting_balance_usd: Decimal
    daily_loss_limit_fraction: Decimal
    maximum_loss_limit_fraction: Decimal
    daily_reset_timezone: str
    daily_reset_description: str
    phase1_profit_target_fraction: Decimal
    phase2_profit_target_fraction: Decimal
    minimum_trading_days_per_phase: int
    unlimited_trading_period: bool
    equity_includes_floating_pnl: bool
    equity_includes_commissions: bool
    equity_includes_swaps: bool
    maximum_loss_is_static_floor: bool
    source_urls: tuple[str, ...]

    def __post_init__(self) -> None:
        if not self.profile_id or not self.provider or not self.program:
            raise PropFirmProfileError("profile identity fields must be non-empty")
        if self.starting_balance_usd <= 0:
            raise PropFirmProfileError("starting balance must be positive")
        for name, value in (
            ("daily loss", self.daily_loss_limit_fraction),
            ("maximum loss", self.maximum_loss_limit_fraction),
            ("phase1 target", self.phase1_profit_target_fraction),
            ("phase2 target", self.phase2_profit_target_fraction),
        ):
            if not Decimal(0) < value < Decimal(1):
                raise PropFirmProfileError(f"{name} fraction must be in (0,1)")
        if self.daily_loss_limit_fraction >= self.maximum_loss_limit_fraction:
            raise PropFirmProfileError("daily loss limit must be below maximum loss limit")
        if self.minimum_trading_days_per_phase < 0:
            raise PropFirmProfileError("minimum trading days cannot be negative")
        if not self.source_urls:
            raise PropFirmProfileError("profile must retain provider source URLs")

    @property
    def daily_loss_amount_usd(self) -> Decimal:
        return self.starting_balance_usd * self.daily_loss_limit_fraction

    @property
    def maximum_loss_floor_usd(self) -> Decimal:
        return self.starting_balance_usd * (Decimal(1) - self.maximum_loss_limit_fraction)

    def daily_loss_floor_usd(self, reset_balance_usd: Decimal) -> Decimal:
        """Return the provider loss boundary in force for the current reset day.

        Both frozen 2-step profiles define the daily budget as a fixed percentage
        of initial capital while the in-force floor is anchored to the balance at
        the daily reset. Intraday profits therefore increase remaining headroom,
        while the next reset rebases the floor from that reset balance.
        """
        if reset_balance_usd <= 0:
            raise PropFirmProfileError("reset balance must be positive")
        return reset_balance_usd - self.daily_loss_amount_usd


FTMO_2STEP_2026_09_12 = PropFirmProfile(
    profile_id="FTMO_2STEP_2026_09_12",
    provider="FTMO",
    program="2-Step",
    version_date="2026-09-12",
    starting_balance_usd=Decimal("100000"),
    daily_loss_limit_fraction=Decimal("0.05"),
    maximum_loss_limit_fraction=Decimal("0.10"),
    daily_reset_timezone="Europe/Prague",
    daily_reset_description="00:00 CE(S)T; balance-at-reset minus 5% initial capital",
    phase1_profit_target_fraction=Decimal("0.10"),
    phase2_profit_target_fraction=Decimal("0.05"),
    minimum_trading_days_per_phase=4,
    unlimited_trading_period=True,
    equity_includes_floating_pnl=True,
    equity_includes_commissions=True,
    equity_includes_swaps=True,
    maximum_loss_is_static_floor=True,
    source_urls=(
        "https://ftmo.com/en/trading-objectives/",
        "https://academy.ftmo.com/lesson/maximum-daily-loss/",
    ),
)


FUNDEDNEXT_STELLAR_2STEP_2026_09_12 = PropFirmProfile(
    profile_id="FUNDEDNEXT_STELLAR_2STEP_2026_09_12",
    provider="FundedNext",
    program="Stellar 2-Step",
    version_date="2026-09-12",
    starting_balance_usd=Decimal("100000"),
    daily_loss_limit_fraction=Decimal("0.05"),
    maximum_loss_limit_fraction=Decimal("0.10"),
    daily_reset_timezone="FundedNextServerTime",
    daily_reset_description="00:00 server time; GMT+3 in DST, GMT+2 otherwise",
    phase1_profit_target_fraction=Decimal("0.08"),
    phase2_profit_target_fraction=Decimal("0.05"),
    minimum_trading_days_per_phase=5,
    unlimited_trading_period=True,
    equity_includes_floating_pnl=True,
    equity_includes_commissions=True,
    equity_includes_swaps=True,
    maximum_loss_is_static_floor=True,
    source_urls=(
        "https://help.fundednext.com/en/articles/8021076-what-rules-do-i-need-to-follow-in-the-stellar-2-step-challenge",
        "https://help.fundednext.com/en/articles/8021071-what-is-the-profit-target-of-the-stellar-2-step-challenge",
        "https://help.fundednext.com/en/articles/8394309-when-does-the-daily-loss-limit-reset-with-fundednext-cfd",
    ),
)


PROFILES = {
    profile.profile_id: profile
    for profile in (FTMO_2STEP_2026_09_12, FUNDEDNEXT_STELLAR_2STEP_2026_09_12)
}
