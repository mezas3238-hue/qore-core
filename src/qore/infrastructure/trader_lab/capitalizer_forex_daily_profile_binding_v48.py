"""V48 source binding for the TTrades Forex Daily profile/open.

The official TTrades H4 Power-of-3 PDF contains an explicit Futures/Forex timing table:
Futures 18:00 corresponds to Forex 17:00, followed by the one-hour-shifted H4 cycle.

The Forex Daily methodology boundary is therefore source-resolved at 17:00 New York time.
V48 constructs it from retained provider-native M1 rather than assuming broker-native Daily
candle equivalence.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

IDENTITY = "QORE_CAPITALIZER_V48_FOREX_DAILY_PROFILE_BINDING"


class V48ForexDailyBindingState(StrEnum):
    RESOLVED_FOREX_SOURCE_PROFILE = "RESOLVED_FOREX_SOURCE_PROFILE"


@dataclass(frozen=True, slots=True)
class V48ForexDailyProfileBinding:
    identity: str = IDENTITY
    state: V48ForexDailyBindingState = (
        V48ForexDailyBindingState.RESOLVED_FOREX_SOURCE_PROFILE
    )
    exact_forex_daily_open_hour_ny: int = 17
    primary_source_url: str = (
        "https://ttrades.com/wp-content/uploads/2025/09/H4-PO3-TTrades-PDF.pdf"
    )
    provider_native_m1_required: bool = True
    native_broker_daily_equivalence_assumed: bool = False
    source_bound_m1_resampling_authorized: bool = True
    synthetic_price_authorized: bool = False
    daily_profile_construction_authorized: bool = True
    generic_scalp_blocked: bool = False
    fresh_holdout_authorized: bool = False
    economics_authorized: bool = False

    def __post_init__(self) -> None:
        if self.identity != IDENTITY:
            raise ValueError("Forex Daily binding identity is frozen")
        if self.exact_forex_daily_open_hour_ny != 17:
            raise ValueError("TTrades Forex Daily source clock is frozen at 17:00 NY")
        if not self.primary_source_url.startswith("https://"):
            raise ValueError("Daily binding requires primary source provenance")
        if not self.provider_native_m1_required:
            raise ValueError("Daily construction requires provider-native M1")
        if self.native_broker_daily_equivalence_assumed:
            raise ValueError("broker Daily boundary equivalence may not be assumed")
        if not self.source_bound_m1_resampling_authorized:
            raise ValueError("resolved Daily clock must authorize M1 resampling")
        if self.synthetic_price_authorized:
            raise ValueError("Daily profile cannot synthesize price")
        if not self.daily_profile_construction_authorized:
            raise ValueError("resolved Daily clock must authorize profile construction")
        if self.generic_scalp_blocked:
            raise ValueError("Daily route work cannot block H1 decision route")
        if self.fresh_holdout_authorized or self.economics_authorized:
            raise ValueError("Daily binding grants no Fresh/economic authority")


V48_FOREX_DAILY_PROFILE_BINDING = V48ForexDailyProfileBinding()
