"""Causal entry+stop eligibility census for C3 positional opportunities."""
from __future__ import annotations

import json
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Final
from zoneinfo import ZoneInfo

from qore.infrastructure.trader_lab.vt08_cognitive_c3_shape_opportunity_audit_v1 import (
    is_c3_closure_shape,
)
from qore.infrastructure.trader_lab.vt08_cognitive_delayed_continuation_bundle_eligibility_v1 import (
    _unique_causal_fvg_at_confirmation,
)
from qore.infrastructure.trader_lab.vt08_cognitive_expansion_5m_backtest_v1 import (
    load_market_evidence,
)
from qore.infrastructure.trader_lab.vt08_cognitive_expansion_5m_evaluator_v1 import (
    _latest_complete_source_days,
)
from qore.infrastructure.trader_lab.vt08_cognitive_expansion_5m_v1 import (
    ANCHORS_NY,
    EXPANSION_MARKETS,
)
from qore.infrastructure.trader_lab.vt08_cognitive_latest_ps_density_recovery_v1 import (
    PROFILES,
    _ltf_window,
    _profile_bars,
)
from qore.infrastructure.traders.contracts import DemoTradingSetupSide
from qore.infrastructure.traders.vt08_b01_r3_8 import (
    Vt08B01Bar,
    resolve_bias,
    source_h4_from_m15,
)

SCHEMA: Final = "qore.trader_lab.vt08_cognitive_c3_positional_eligibility.v1"
_NY = ZoneInfo("America/New_York")


@dataclass(frozen=True, slots=True)
class FvgBackedProtectedSwing:
    side: DemoTradingSetupSide
    price: Decimal
    cisd_level: Decimal
    confirmed_at: datetime
    opposing_series_opened_at: datetime
    poi_lower: Decimal
    poi_upper: Decimal
    poi_formed_at: datetime


def _fvg_backed_swings(
    bars: tuple[Vt08B01Bar, ...],
    *,
    side: DemoTradingSetupSide,
) -> tuple[FvgBackedProtectedSwing, ...]:
    result: list[FvgBackedProtectedSwing] = []
    series_open: Decimal | None = None
    series_extreme: Decimal | None = None
    series_opened_at: datetime | None = None

    def opposing(bar: Vt08B01Bar) -> bool:
        if side is DemoTradingSetupSide.LONG:
            return bar.close < bar.open
        return bar.close > bar.open

    for index, bar in enumerate(bars):
        if opposing(bar):
            if series_open is None:
                series_open = bar.open
                series_opened_at = bar.opened_at
                series_extreme = (
                    bar.low if side is DemoTradingSetupSide.LONG else bar.high
                )
            else:
                assert series_extreme is not None
                series_extreme = (
                    min(series_extreme, bar.low)
                    if side is DemoTradingSetupSide.LONG
                    else max(series_extreme, bar.high)
                )
            continue

        if (
            series_open is not None
            and series_extreme is not None
            and series_opened_at is not None
        ):
            confirmed = (
                bar.close > series_open
                if side is DemoTradingSetupSide.LONG
                else bar.close < series_open
            )
            if confirmed:
                poi = _unique_causal_fvg_at_confirmation(
                    bars,
                    confirmation_index=index,
                    side=side,
                )
                if poi is not None:
                    result.append(
                        FvgBackedProtectedSwing(
                            side=side,
                            price=series_extreme,
                            cisd_level=series_open,
                            confirmed_at=bar.closed_at,
                            opposing_series_opened_at=series_opened_at,
                            poi_lower=poi[0],
                            poi_upper=poi[1],
                            poi_formed_at=poi[2],
                        )
                    )
        series_open = None
        series_extreme = None
        series_opened_at = None

    return tuple(result)


def _latest(
    swings: tuple[FvgBackedProtectedSwing, ...],
) -> FvgBackedProtectedSwing:
    if not swings:
        raise ValueError("C3 positional selector requires eligible PS")
    ordered = tuple(
        sorted(
            swings,
            key=lambda item: (
                item.confirmed_at,
                item.opposing_series_opened_at,
                item.price,
            ),
        )
    )
    selected = ordered[-1]
    identity = (
        selected.confirmed_at,
        selected.opposing_series_opened_at,
        selected.price,
    )
    if sum(
        (
            item.confirmed_at,
            item.opposing_series_opened_at,
            item.price,
        )
        == identity
        for item in swings
    ) != 1:
        raise ValueError("latest C3 PS identity is ambiguous")
    return selected


def _geometry_valid(
    *,
    side: DemoTradingSetupSide,
    entry: Decimal,
    stop: Decimal,
) -> bool:
    if side is DemoTradingSetupSide.LONG:
        return stop < entry
    return entry < stop


def _profile_mask(profiles: set[str]) -> str:
    labels = tuple(profile for profile in PROFILES if profile in profiles)
    return "_".join(labels) if labels else "NONE"


def evaluate(base_path: Path, *, m3_path: Path) -> dict[str, object]:
    _fingerprint, symbol, checked_at, software_sha, m15 = load_market_evidence(
        base_path
    )
    if symbol not in EXPANSION_MARKETS:
        raise ValueError("C3 eligibility market outside frozen universe")

    m15_by_open = {bar.opened_at: bar for bar in m15}
    profile_indexes: dict[str, dict[datetime, Vt08B01Bar]] = {}
    for profile in PROFILES:
        bars, _minutes = _profile_bars(
            profile=profile,
            base_path=base_path,
            m3_path=m3_path,
            symbol=symbol,
            m15=m15,
        )
        profile_indexes[profile] = {bar.opened_at: bar for bar in bars}

    c3_shapes = 0
    eligible_union = 0
    profile_counts: dict[str, Counter[str]] = {
        profile: Counter() for profile in PROFILES
    }
    masks: Counter[str] = Counter()
    delays_to_c3_close: dict[str, list[int]] = {
        profile: [] for profile in PROFILES
    }

    for entry_bar in m15:
        local = entry_bar.opened_at.astimezone(_NY)
        if local.minute != 0 or local.hour not in ANCHORS_NY:
            continue

        c1 = source_h4_from_m15(
            m15_by_open,
            opened_at_local=local - timedelta(hours=12),
        )
        c2 = source_h4_from_m15(
            m15_by_open,
            opened_at_local=local - timedelta(hours=8),
        )
        c3 = source_h4_from_m15(
            m15_by_open,
            opened_at_local=local - timedelta(hours=4),
        )
        if (
            c1 is None
            or c2 is None
            or c3 is None
            or c3.closed_at != entry_bar.opened_at
        ):
            continue

        source_days = _latest_complete_source_days(
            m15_by_open,
            before_local=local,
        )
        if len(source_days) != 2:
            continue
        current_day, previous_day = source_days
        bias = resolve_bias(previous_day=previous_day, current_day=current_day)
        if bias is None:
            continue
        if not is_c3_closure_shape(c2, c3, bias=bias):
            continue

        c3_shapes += 1
        eligible_profiles: set[str] = set()

        for profile in PROFILES:
            rows = _ltf_window(
                profile=profile,
                bars_by_open=profile_indexes[profile],
                opened_at=c3.opened_at,
                closed_at=c3.closed_at,
            )
            if rows is None:
                profile_counts[profile]["C3_LTF_WINDOW_INCOMPLETE"] += 1
                continue

            swings = _fvg_backed_swings(rows, side=bias)
            profile_counts[profile]["FVG_BACKED_PS_EVENTS"] += len(swings)
            if not swings:
                profile_counts[profile]["NO_FVG_BACKED_PS"] += 1
                continue

            try:
                selected = _latest(swings)
            except ValueError:
                profile_counts[profile]["LATEST_IDENTITY_AMBIGUOUS"] += 1
                continue

            if selected.confirmed_at > c3.closed_at:
                raise AssertionError("C3 PS confirmation leaked after C3 close")
            if not _geometry_valid(
                side=bias,
                entry=entry_bar.open,
                stop=selected.price,
            ):
                profile_counts[profile]["INVALID_POSITIONAL_GEOMETRY"] += 1
                continue

            eligible_profiles.add(profile)
            profile_counts[profile]["POSITIONAL_ENTRY_STOP_ELIGIBLE"] += 1
            delay = int(
                (c3.closed_at - selected.confirmed_at).total_seconds() // 60
            )
            if delay < 0 or delay > 240:
                raise AssertionError("C3 confirmation age at open is invalid")
            delays_to_c3_close[profile].append(delay)

        mask = _profile_mask(eligible_profiles)
        masks[mask] += 1
        if eligible_profiles:
            eligible_union += 1

    delay_summary = {}
    for profile, values in delays_to_c3_close.items():
        ordered = sorted(values)
        delay_summary[profile] = {
            "count": len(ordered),
            "min_minutes_before_h4_open": None if not ordered else ordered[0],
            "median_minutes_before_h4_open": (
                None if not ordered else ordered[(len(ordered) - 1) // 2]
            ),
            "max_minutes_before_h4_open": None if not ordered else ordered[-1],
        }

    return {
        "schema": SCHEMA,
        "market": symbol,
        "checked_at": checked_at.isoformat(),
        "software_sha": software_sha,
        "c3_shape_count": c3_shapes,
        "c3_positional_entry_stop_eligible_union": eligible_union,
        "eligibility_rate": (
            "0"
            if c3_shapes == 0
            else format(eligible_union / c3_shapes, ".12f")
        ),
        "profile_counts": {
            profile: dict(counter)
            for profile, counter in profile_counts.items()
        },
        "eligible_profile_masks": dict(sorted(masks.items())),
        "selected_ps_age_at_next_h4_open": delay_summary,
        "governance": {
            "eligibility_only": True,
            "c3_known_before_entry": True,
            "entry_reference": "next-h4-open",
            "stop_reference": "latest-causal-fvg-backed-protected-swing",
            "target_assigned": False,
            "pnl_read": False,
            "profiles_combined_for_execution": False,
            "pr518_economics_reused": False,
            "live_authorized": False,
        },
    }


def to_json(base_path: Path, *, m3_path: Path) -> str:
    return json.dumps(
        evaluate(base_path, m3_path=m3_path),
        sort_keys=True,
        separators=(",", ":"),
    )
