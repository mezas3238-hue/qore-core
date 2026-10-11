"""DCVC causal features only: no trade outcomes, no historical winners or exits.

Native M1 CLOSED at source decision is the only price information used to
form regimes. Any gap within 241 minutes produces UNKNOWN instead of backfill.
M30/M3 features are strictly SHADOW: never mixed into H1/M15/M1 admission.
"""
from __future__ import annotations

import bisect
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any

from qore.infrastructure.trader_lab.capitalizer_cibo_m1_reader_v1 import (
    CapitalizerM1Bar,
)
from qore.infrastructure.trader_lab.capitalizer_high_frequency_capacity_census_v49 import (
    V49Opportunity,
)
from qore.infrastructure.trader_lab.capitalizer_scalper_v49_v50_g_waterfall_v1 import (
    source_id,
)

IDENTITY = "QORE_SCALPER_DCVC_CAUSAL_REGIME_FEATURE_V01"


@dataclass(frozen=True, slots=True)
class DCVCPredecision:
    source_opportunity_id: str
    symbol: str
    session: str
    operating_date: str
    decision_at: str
    source_h1_confirmed_at: str
    source_m15_confirmed_at: str
    native_last_m1_closed_at: str
    regime: str
    relative_volatility: str | None
    directional_efficiency: str | None
    displacement_intensity: str | None
    directional_persistence: str | None
    planned_reward_r: str | None
    m30_closed_m1_count: int
    m3_closed_m1_count: int
    features_known_at: str
    h1_m15_parent_author_certified: bool = False
    m30_m3_author_cisd_confirmed: bool = False
    native_bid_ask_present: bool = False
    risk_trade_authorized: bool = False

    def __post_init__(self) -> None:
        at = datetime.fromisoformat(self.decision_at)
        if (
            datetime.fromisoformat(self.source_h1_confirmed_at) > at
            or datetime.fromisoformat(self.source_m15_confirmed_at) >= at
            or datetime.fromisoformat(self.native_last_m1_closed_at) > at
            or datetime.fromisoformat(self.features_known_at) > at
        ):
            raise ValueError("DCVC feature contains future or unclosed candle")
        if self.regime not in (
            "HIGH_VOL_TREND", "HIGH_VOL_CHOP", "LOW_VOL_TREND",
            "LOW_VOL_CHOP", "UNKNOWN",
        ):
            raise ValueError("unrecognized preregistered regime")
        if any((self.h1_m15_parent_author_certified,
                self.m30_m3_author_cisd_confirmed,
                self.native_bid_ask_present,self.risk_trade_authorized)):
            raise ValueError("DCVC cannot claim native broker/method authority")


def _mean(items: tuple[Decimal, ...]) -> Decimal:
    return sum(items, Decimal(0)) / Decimal(len(items))


def observe(
    source: V49Opportunity,
    bars: tuple[CapitalizerM1Bar, ...],
    closed: tuple[datetime, ...],
) -> DCVCPredecision:
    at = datetime.fromisoformat(source.m1_trigger_confirmed_at)
    if at.utcoffset() is None:
        raise ValueError("source decision must be timezone-aware")
    if not bars or len(bars) != len(closed):
        raise ValueError("genuine native bar index is absent")
    idx = bisect.bisect_right(closed, at)
    if idx == 0 or closed[idx-1] != at:
        raise ValueError("provider M1 decision close not exact")
    witness = bars[idx-1]
    if witness.symbol != source.symbol:
        raise ValueError("native symbol mismatch")
    if witness.close != Decimal(source.decision_reference_price):
        raise ValueError("V49 reference entry differs from native M1 close")
    if any(
        bars[i].closed_at != closed[i] or bars[i].symbol != source.symbol
        for i in range(max(0,idx-242),idx)
    ):
        raise ValueError("invalid native timeline/source")
    past = bars[max(0,idx-241):idx]
    complete = (
        len(past) == 241 and
        all(
            past[i+1].opened_at == past[i].closed_at and
            past[i+1].closed_at-past[i].closed_at == timedelta(minutes=1)
            for i in range(len(past)-1)
        )
    )
    regime = "UNKNOWN"
    rel_vol = efficiency = displacement = persistence = None
    if complete:
        prices = tuple(item.close for item in past)
        changes = tuple(prices[i+1]-prices[i] for i in range(240))
        fast = changes[-30:]
        overall = tuple(abs(x) for x in changes)
        fast_abs = tuple(abs(x) for x in fast)
        slow_avg = _mean(overall)
        fast_avg = _mean(fast_abs)
        magnitude = sum(fast_abs, Decimal(0))
        if slow_avg > 0 and magnitude > 0:
            ratio = fast_avg/slow_avg
            eff = abs(sum(fast,Decimal(0)))/magnitude
            current = abs(fast[-1])/slow_avg
            nonzero = tuple(x for x in fast if x != 0)
            ref_direction = 1 if sum(fast,Decimal(0)) >= 0 else -1
            persisted = (
                Decimal(sum((x > 0) == (ref_direction > 0) for x in nonzero))
                / Decimal(len(nonzero))
                if nonzero else Decimal(0)
            )
            regime = (
                ("HIGH_VOL_" if ratio >= 1 else "LOW_VOL_")
                + ("TREND" if eff >= Decimal("0.35") else "CHOP")
            )
            rel_vol, efficiency = str(ratio), str(eff)
            displacement, persistence = str(current), str(persisted)
    entry = witness.close
    stop = Decimal(source.m15_protected_swing_price)
    target = Decimal(source.structural_target_witness_price)
    planned = (
        str(abs(target-entry)/abs(entry-stop))
        if entry != stop else None
    )
    # Shadow completeness counters only; not M30 structural confirmation or M3 CISD.
    m30_count = len(tuple(bar for bar in bars[max(0,idx-30):idx]
                          if bar.closed_at <= at))
    m3_count = len(tuple(bar for bar in bars[max(0,idx-3):idx]
                         if bar.closed_at <= at))
    return DCVCPredecision(
        source_opportunity_id=source_id(source),symbol=source.symbol,
        session=source.session,operating_date=source.operating_date,
        decision_at=source.m1_trigger_confirmed_at,
        source_h1_confirmed_at=source.h1_state_from,
        source_m15_confirmed_at=source.m15_setup_confirmed_at,
        native_last_m1_closed_at=witness.closed_at.isoformat(),
        regime=regime,relative_volatility=rel_vol,
        directional_efficiency=efficiency,
        displacement_intensity=displacement,
        directional_persistence=persistence,
        planned_reward_r=planned,
        m30_closed_m1_count=m30_count,m3_closed_m1_count=m3_count,
        features_known_at=witness.closed_at.isoformat(),
    )


def safe_record(item: DCVCPredecision) -> dict[str, Any]:
    """Serialization contains no future economic outcomes by construction."""
    return asdict(item)
