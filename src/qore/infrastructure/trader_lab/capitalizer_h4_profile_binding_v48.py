"""V48 H4 profile/time binding ledger for TTrades Asia and London Forex routes.

Source adjudication is now closed for the H4 *profile clock* used by Capitalizer's Forex
markets:
- TTrades 4-Hour Power of 3 distinguishes futures anchors 02/06/10 from Forex 01/05/09.
- TTrades' timing material uses New York chart time.
- The four-hour Forex cycle therefore continues 01/05/09/13/17/21 New York time.

V48 does not assume the broker's native H4 boundary is equivalent. Instead, it is authorized
to construct source-bound H4 methodology candles from retained provider-native M1 using
capitalizer_ttrades_forex_h4_profile_v48.py.

This resolves H4 clock identity. The Forex Daily profile is source-bound independently at
17:00 New York by the same primary TTrades timing table.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

IDENTITY = "QORE_CAPITALIZER_V48_H4_PROFILE_BINDING"


class V48H4BindingState(StrEnum):
    RESOLVED_FOREX_SOURCE_PROFILE = "RESOLVED_FOREX_SOURCE_PROFILE"


@dataclass(frozen=True, slots=True)
class V48H4ProfileEvidence:
    source_id: str
    source_url: str
    evidence: str
    source_clock_fact: bool
    proves_native_broker_h4_equivalence: bool = False

    def __post_init__(self) -> None:
        if not self.source_id or self.source_id != self.source_id.upper():
            raise ValueError("H4 evidence id must be non-empty uppercase")
        if not self.source_url.startswith("https://"):
            raise ValueError("H4 evidence requires source URL")
        if not self.evidence:
            raise ValueError("H4 evidence requires description")


EVIDENCE: tuple[V48H4ProfileEvidence, ...] = (
    V48H4ProfileEvidence(
        "TTRADES_FOREX_H4_ANCHORS",
        "https://ttrades.com/trading-the-4-hour-power-of-3-open-high-low-close-strategy/",
        (
            "TTrades distinguishes futures 02/06/10 anchors from Forex 01/05/09 anchors "
            "and pairs the H4 structure with 15M confirmation."
        ),
        True,
    ),
    V48H4ProfileEvidence(
        "TTRADES_NEW_YORK_TIME_CONVENTION",
        "https://ttrades.com/kill-zones-explained-best-trading-sessions-for-entries/",
        "TTrades instructs chart/session timing to be read in New York time.",
        True,
    ),
    V48H4ProfileEvidence(
        "TTRADES_LONDON_FOREX_ONE_HOUR_SHIFT",
        "https://ttrades.com/how-to-trade-london-using-ttrades-fractal-model/",
        (
            "London Forex examples use the same fractal logic with the Forex higher-timeframe "
            "open shifted one hour from the futures examples."
        ),
        True,
    ),
)


@dataclass(frozen=True, slots=True)
class V48H4ProfileBinding:
    identity: str = IDENTITY
    state: V48H4BindingState = V48H4BindingState.RESOLVED_FOREX_SOURCE_PROFILE
    evidence: tuple[V48H4ProfileEvidence, ...] = EVIDENCE
    forex_anchor_hours_ny: tuple[int, ...] = (1, 5, 9, 13, 17, 21)
    provider_native_m1_required: bool = True
    native_broker_h4_equivalence_assumed: bool = False
    source_bound_m1_resampling_authorized: bool = True
    synthetic_price_authorized: bool = False
    h4_profile_construction_authorized: bool = True
    full_asia_london_route_authorized: bool = False
    daily_profile_binding_resolved_independently: bool = True
    generic_scalp_blocked: bool = False
    fresh_holdout_authorized: bool = False
    economics_authorized: bool = False

    def __post_init__(self) -> None:
        if self.identity != IDENTITY:
            raise ValueError("H4 binding identity is frozen")
        if self.forex_anchor_hours_ny != (1, 5, 9, 13, 17, 21):
            raise ValueError("Forex H4 source clock is frozen to 01/05/09/13/17/21 NY")
        if not self.provider_native_m1_required:
            raise ValueError("source-bound H4 construction requires provider-native M1")
        if self.native_broker_h4_equivalence_assumed:
            raise ValueError("V48 may not assume broker H4 clock equivalence")
        if not self.source_bound_m1_resampling_authorized:
            raise ValueError("resolved Forex H4 source clock must authorize M1 resampling")
        if self.synthetic_price_authorized:
            raise ValueError("V48 H4 construction cannot synthesize price")
        if not self.h4_profile_construction_authorized:
            raise ValueError("resolved Forex H4 clock must allow profile construction")
        if self.full_asia_london_route_authorized:
            raise ValueError("H4 clock closure alone cannot authorize full Asia/London route")
        if not self.daily_profile_binding_resolved_independently:
            raise ValueError("Forex Daily clock should be resolved by its independent ledger")
        if self.generic_scalp_blocked:
            raise ValueError("H4 work cannot block independent H1/M15/M1 Scalping")
        if self.fresh_holdout_authorized or self.economics_authorized:
            raise ValueError("H4 binding ledger grants no Fresh/economic authority")


V48_H4_PROFILE_BINDING = V48H4ProfileBinding()
