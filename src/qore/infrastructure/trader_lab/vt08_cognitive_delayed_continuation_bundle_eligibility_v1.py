"""Eligibility census for delayed protected-swing continuation source bundles."""
from __future__ import annotations

import json
from collections import Counter
from datetime import datetime, timedelta
from decimal import Decimal
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
    Vt08B01ProtectedSwing,
    protected_swings_in_candle2,
    resolve_bias,
    source_h4_from_m15,
)

SCHEMA: Final = "qore.trader_lab.vt08_cognitive_delayed_continuation_bundle_eligibility.v1"
_NY = ZoneInfo("America/New_York")


def _unique_causal_fvg_at_confirmation(
    bars: tuple[Vt08B01Bar, ...],
    *,
    confirmation_index: int,
    side: DemoTradingSetupSide,
) -> tuple[Decimal, Decimal, datetime] | None:
    matches: list[tuple[Decimal, Decimal, datetime]] = []
    for index in range(2, confirmation_index):
        left = bars[index - 2]
        right = bars[index]
        if side is DemoTradingSetupSide.LONG:
            lower, upper = left.high, right.low
            exists = lower < upper
        else:
            lower, upper = right.high, left.low
            exists = lower < upper
        if not exists:
            continue

        invalidated = any(
            later.low < lower
            if side is DemoTradingSetupSide.LONG
            else later.high > upper
            for later in bars[index + 1 : confirmation_index]
        )
        if invalidated:
            continue

        confirmation = bars[confirmation_index]
        reached = confirmation.low <= upper and confirmation.high >= lower
        close_inside = lower <= confirmation.close <= upper
        if reached and close_inside:
            matches.append((lower, upper, bars[index].closed_at))

    unique = tuple(dict.fromkeys(matches))
    return unique[0] if len(unique) == 1 else None


def _fvg_match_count(
    bars: tuple[Vt08B01Bar, ...],
    *,
    confirmation_index: int,
    side: DemoTradingSetupSide,
) -> int:
    matches: set[tuple[Decimal, Decimal, datetime]] = set()
    for index in range(2, confirmation_index):
        left = bars[index - 2]
        right = bars[index]
        if side is DemoTradingSetupSide.LONG:
            lower, upper = left.high, right.low
            exists = lower < upper
        else:
            lower, upper = right.high, left.low
            exists = lower < upper
        if not exists:
            continue
        invalidated = any(
            later.low < lower
            if side is DemoTradingSetupSide.LONG
            else later.high > upper
            for later in bars[index + 1 : confirmation_index]
        )
        confirmation = bars[confirmation_index]
        if (
            not invalidated
            and confirmation.low <= upper
            and confirmation.high >= lower
            and lower <= confirmation.close <= upper
        ):
            matches.add((lower, upper, bars[index].closed_at))
    return len(matches)


def _confirmation_index(
    bars: tuple[Vt08B01Bar, ...],
    swing: Vt08B01ProtectedSwing,
) -> int:
    matches = tuple(
        index
        for index, bar in enumerate(bars)
        if bar.closed_at == swing.confirmed_at
    )
    if len(matches) != 1:
        raise ValueError("Protected Swing confirmation must map to one LTF bar")
    return matches[0]


def _profile_mask(profiles: set[str]) -> str:
    labels = tuple(profile for profile in PROFILES if profile in profiles)
    return "_".join(labels) if labels else "NONE"


def evaluate(base_path: Path, *, m3_path: Path) -> dict[str, object]:
    _fingerprint, symbol, checked_at, software_sha, m15 = load_market_evidence(
        base_path
    )
    if symbol not in EXPANSION_MARKETS:
        raise ValueError("continuation eligibility market outside frozen universe")

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

    pre_anchor_no_ps_cases = 0
    post_anchor_ps_cases = 0
    eligible_union_cases = 0
    by_profile: dict[str, Counter[str]] = {
        profile: Counter() for profile in PROFILES
    }
    eligible_masks: Counter[str] = Counter()
    eligibility_delays: dict[str, list[int]] = {
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

        pre_anchor_no_ps_cases += 1
        important_level = (
            reference.low
            if side is DemoTradingSetupSide.LONG
            else reference.high
        )
        profiles_with_ps: set[str] = set()
        profiles_eligible: set[str] = set()

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

            profiles_with_ps.add(profile)
            by_profile[profile]["POST_ANCHOR_PS_CASE"] += 1

            eligible_events = 0
            ambiguous_events = 0
            no_match_events = 0
            for swing in swings:
                index = _confirmation_index(rows, swing)
                match_count = _fvg_match_count(
                    rows,
                    confirmation_index=index,
                    side=side,
                )
                if match_count == 1:
                    poi = _unique_causal_fvg_at_confirmation(
                        rows,
                        confirmation_index=index,
                        side=side,
                    )
                    if poi is None:
                        raise AssertionError("unique FVG count failed to resolve POI")
                    eligible_events += 1
                    delay = int(
                        (swing.confirmed_at - entry_bar.opened_at).total_seconds()
                        // 60
                    )
                    eligibility_delays[profile].append(delay)
                elif match_count > 1:
                    ambiguous_events += 1
                else:
                    no_match_events += 1

            by_profile[profile]["ELIGIBLE_CONFIRMATION_EVENTS"] += eligible_events
            by_profile[profile]["AMBIGUOUS_FVG_EVENTS"] += ambiguous_events
            by_profile[profile]["NO_MATCHING_FVG_EVENTS"] += no_match_events
            if eligible_events:
                profiles_eligible.add(profile)
                by_profile[profile]["ELIGIBLE_ANCHOR_CASE"] += 1

        if profiles_with_ps:
            post_anchor_ps_cases += 1
        mask = _profile_mask(profiles_eligible)
        eligible_masks[mask] += 1
        if profiles_eligible:
            eligible_union_cases += 1

    delay_summary = {}
    for profile, values in eligibility_delays.items():
        ordered = sorted(values)
        delay_summary[profile] = {
            "eligible_event_count": len(ordered),
            "min": None if not ordered else ordered[0],
            "median": None if not ordered else ordered[(len(ordered) - 1) // 2],
            "max": None if not ordered else ordered[-1],
        }

    return {
        "schema": SCHEMA,
        "market": symbol,
        "checked_at": checked_at.isoformat(),
        "software_sha": software_sha,
        "pre_anchor_c2_valid_no_ps_cases": pre_anchor_no_ps_cases,
        "post_anchor_ps_union_cases": post_anchor_ps_cases,
        "continuation_bundle_eligible_union_cases": eligible_union_cases,
        "eligible_rate_of_pre_anchor_no_ps": (
            "0"
            if pre_anchor_no_ps_cases == 0
            else format(
                eligible_union_cases / pre_anchor_no_ps_cases,
                ".12f",
            )
        ),
        "eligible_rate_of_post_anchor_ps": (
            "0"
            if post_anchor_ps_cases == 0
            else format(
                eligible_union_cases / post_anchor_ps_cases,
                ".12f",
            )
        ),
        "profile_counts": {
            profile: dict(counter)
            for profile, counter in by_profile.items()
        },
        "eligible_profile_masks": dict(sorted(eligible_masks.items())),
        "eligible_confirmation_delay_minutes": delay_summary,
        "governance": {
            "eligibility_only": True,
            "pnl_read": False,
            "historical_fill_assigned": False,
            "target_assigned": False,
            "profiles_combined_for_execution": False,
            "poi_rule_from_pr518_forensic_source_audit": True,
            "pr518_economics_reused": False,
            "freshness_claimed": False,
            "live_authorized": False,
        },
    }


def to_json(base_path: Path, *, m3_path: Path) -> str:
    return json.dumps(
        evaluate(base_path, m3_path=m3_path),
        sort_keys=True,
        separators=(",", ":"),
    )
