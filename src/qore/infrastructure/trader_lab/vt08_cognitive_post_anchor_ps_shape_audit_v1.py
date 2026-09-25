"""Shape-only audit of post-anchor Protected Swings for pre-anchor no-PS cases."""
from __future__ import annotations

import json
from collections import Counter
from datetime import datetime, timedelta
from pathlib import Path
from typing import Final
from zoneinfo import ZoneInfo

from qore.infrastructure.trader_lab.vt08_cognitive_5m_density_funnel_audit_v1 import (
    _c2_state,
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
from qore.infrastructure.trader_lab.vt08_cognitive_three_year_opportunity_census_v1 import (
    _profile_variants,
)
from qore.infrastructure.traders.contracts import DemoTradingSetupSide
from qore.infrastructure.traders.vt08_b01_r3_8 import (
    Vt08B01Bar,
    protected_swings_in_candle2,
    resolve_bias,
    source_h4_from_m15,
)

SCHEMA: Final = "qore.trader_lab.vt08_cognitive_post_anchor_ps_shape_audit.v1"
_NY = ZoneInfo("America/New_York")


def _profile_mask(profiles: set[str]) -> str:
    return "_".join(profile for profile in PROFILES if profile in profiles) or "NONE"


def evaluate(base_path: Path, *, m3_path: Path) -> dict[str, object]:
    _fingerprint, symbol, checked_at, software_sha, m15 = load_market_evidence(
        base_path
    )
    if symbol not in EXPANSION_MARKETS:
        raise ValueError("post-anchor PS audit market outside frozen universe")

    m15_by_open = {bar.opened_at: bar for bar in m15}
    pre_anchor_executable = {
        row.signal_at
        for profile in PROFILES
        for row in _profile_variants(
            base_path,
            profile=profile,
            m3_path=m3_path,
        )
    }

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

    total_cases = 0
    recovered_union = 0
    by_profile: dict[str, Counter[str]] = {
        profile: Counter() for profile in PROFILES
    }
    masks: Counter[str] = Counter()
    first_delay_minutes: dict[str, list[int]] = {
        profile: [] for profile in PROFILES
    }

    for entry_bar in m15:
        local = entry_bar.opened_at.astimezone(_NY)
        if local.minute != 0 or local.hour not in ANCHORS_NY:
            continue
        if entry_bar.opened_at in pre_anchor_executable:
            continue

        reference = source_h4_from_m15(
            m15_by_open,
            opened_at_local=local - timedelta(hours=8),
        )
        candle2 = source_h4_from_m15(
            m15_by_open,
            opened_at_local=local - timedelta(hours=4),
        )
        if reference is None or candle2 is None or candle2.closed_at != entry_bar.opened_at:
            continue

        source_days = _latest_complete_source_days(
            m15_by_open,
            before_local=local,
        )
        if len(source_days) != 2:
            continue
        current_day, previous_day = source_days
        side = resolve_bias(previous_day=previous_day, current_day=current_day)
        if side is None:
            continue
        state, c2_side = _c2_state(reference, candle2)
        if state != "C2_ONE_SIDE_SWEEP_CLOSE_INSIDE" or c2_side is not side:
            continue

        total_cases += 1
        important_level = (
            reference.low
            if side is DemoTradingSetupSide.LONG
            else reference.high
        )
        positive_profiles: set[str] = set()

        for profile in PROFILES:
            rows = _ltf_window(
                profile=profile,
                bars_by_open=profile_indexes[profile],
                opened_at=entry_bar.opened_at,
                closed_at=entry_bar.opened_at + timedelta(hours=4),
            )
            if rows is None:
                by_profile[profile]["CURRENT_H4_WINDOW_INCOMPLETE"] += 1
                continue

            swings = protected_swings_in_candle2(
                rows,
                side=side,
                important_level=important_level,
            )
            if not swings:
                by_profile[profile]["NO_POST_ANCHOR_PS"] += 1
                continue

            positive_profiles.add(profile)
            by_profile[profile]["POST_ANCHOR_PS_CASE"] += 1
            by_profile[profile]["POST_ANCHOR_PS_TOTAL"] += len(swings)
            first = min(item.confirmed_at for item in swings)
            delay = int(
                (first - entry_bar.opened_at).total_seconds() // 60
            )
            if delay < 0 or delay > 240:
                raise AssertionError("post-anchor PS confirmation delay is invalid")
            first_delay_minutes[profile].append(delay)

        mask = _profile_mask(positive_profiles)
        masks[mask] += 1
        if positive_profiles:
            recovered_union += 1

    delay_summary = {}
    for profile, values in first_delay_minutes.items():
        ordered = sorted(values)
        delay_summary[profile] = {
            "count": len(ordered),
            "min": None if not ordered else ordered[0],
            "median": (
                None
                if not ordered
                else ordered[(len(ordered) - 1) // 2]
            ),
            "max": None if not ordered else ordered[-1],
        }

    return {
        "schema": SCHEMA,
        "market": symbol,
        "checked_at": checked_at.isoformat(),
        "software_sha": software_sha,
        "pre_anchor_c2_valid_no_ps_cases": total_cases,
        "post_anchor_ps_union_cases": recovered_union,
        "post_anchor_ps_union_rate": (
            "0"
            if total_cases == 0
            else format(recovered_union / total_cases, ".12f")
        ),
        "profile_counts": {
            profile: dict(counter)
            for profile, counter in by_profile.items()
        },
        "profile_presence_masks": dict(sorted(masks.items())),
        "first_confirmation_delay_minutes": delay_summary,
        "governance": {
            "shape_only": True,
            "position_entry_backfilled": False,
            "entry_family_selected": False,
            "pnl_read": False,
            "current_h4_only": True,
            "live_authorized": False,
        },
    }


def to_json(base_path: Path, *, m3_path: Path) -> str:
    return json.dumps(
        evaluate(base_path, m3_path=m3_path),
        sort_keys=True,
        separators=(",", ":"),
    )
