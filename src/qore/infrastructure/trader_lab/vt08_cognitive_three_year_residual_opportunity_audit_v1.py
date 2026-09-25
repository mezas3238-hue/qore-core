"""Residual opportunity audit reconciling every observed VT08 anchor over ~3Y."""
from __future__ import annotations

import json
from collections import Counter, defaultdict
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
)
from qore.infrastructure.trader_lab.vt08_cognitive_three_year_opportunity_census_v1 import (
    _c3_shapes,
    _profile_variants,
)
from qore.infrastructure.traders.vt08_b01_r3_8 import (
    Vt08B01Bar,
    resolve_bias,
    source_h4_from_m15,
)

SCHEMA: Final = "qore.trader_lab.vt08_cognitive_three_year_residual_opportunity_audit.v1"
_NY = ZoneInfo("America/New_York")


def _source_state(
    *,
    bars_by_open: dict[datetime, Vt08B01Bar],
    entry_bar: Vt08B01Bar,
) -> str:
    local = entry_bar.opened_at.astimezone(_NY)
    reference = source_h4_from_m15(
        bars_by_open,
        opened_at_local=local - timedelta(hours=8),
    )
    candle2 = source_h4_from_m15(
        bars_by_open,
        opened_at_local=local - timedelta(hours=4),
    )
    if reference is None or candle2 is None or candle2.closed_at != entry_bar.opened_at:
        return "INCOMPLETE_SOURCE_H4"

    source_days = _latest_complete_source_days(
        bars_by_open,
        before_local=local,
    )
    if len(source_days) != 2:
        return "INCOMPLETE_SOURCE_DAY"
    current_day, previous_day = source_days
    side = resolve_bias(previous_day=previous_day, current_day=current_day)
    if side is None:
        return "BIAS_UNRESOLVED"

    state, c2_side = _c2_state(reference, candle2)
    if state != "C2_ONE_SIDE_SWEEP_CLOSE_INSIDE":
        return state
    if c2_side is not side:
        return "C2_SIDE_BIAS_MISMATCH"
    return "C2_SOURCE_VALID"


def evaluate(base_path: Path, *, m3_path: Path) -> dict[str, object]:
    _fingerprint, symbol, checked_at, software_sha, m15 = load_market_evidence(
        base_path
    )
    if symbol not in EXPANSION_MARKETS:
        raise ValueError("residual audit market outside frozen 5M universe")

    bars_by_open = {bar.opened_at: bar for bar in m15}
    mechanical_by_profile = {
        profile: _profile_variants(
            base_path,
            profile=profile,
            m3_path=m3_path,
        )
        for profile in PROFILES
    }
    profiles_by_signal: dict[datetime, set[str]] = defaultdict(set)
    for profile, rows in mechanical_by_profile.items():
        for row in rows:
            profiles_by_signal[row.signal_at].add(profile)

    c3 = _c3_shapes(base_path)
    c3_by_signal = {row.signal_at: row for row in c3}

    state_counts: Counter[str] = Counter()
    resolution_counts: Counter[str] = Counter()
    cross_counts: Counter[str] = Counter()
    by_anchor: dict[int, Counter[str]] = {
        anchor: Counter() for anchor in ANCHORS_NY
    }

    observed = 0
    c2_valid = 0
    for entry_bar in m15:
        local = entry_bar.opened_at.astimezone(_NY)
        if local.minute != 0 or local.hour not in ANCHORS_NY:
            continue
        observed += 1
        source_state = _source_state(
            bars_by_open=bars_by_open,
            entry_bar=entry_bar,
        )
        state_counts[source_state] += 1

        profiles = profiles_by_signal.get(entry_bar.opened_at, set())
        has_c3 = entry_bar.opened_at in c3_by_signal

        if source_state == "C2_SOURCE_VALID":
            c2_valid += 1
            if profiles:
                resolution = "C2_EXECUTABLE_PROFILE_UNION"
            else:
                resolution = "C2_VALID_NO_PS_ANY_PROFILE"
        elif has_c3:
            resolution = "C3_SHAPE_FROM_NONEXECUTABLE_C2"
        else:
            resolution = "NO_EXECUTABLE_C2_OR_C3_SHAPE"

        resolution_counts[resolution] += 1
        by_anchor[local.hour][resolution] += 1

        if profiles:
            profile_mask = "_".join(
                profile
                for profile in PROFILES
                if profile in profiles
            )
        else:
            profile_mask = "NONE"
        cross_counts[
            f"{source_state}|profiles={profile_mask}|c3={str(has_c3).lower()}"
        ] += 1

    if observed != sum(state_counts.values()):
        raise AssertionError("source-state census does not reconcile anchors")
    if observed != sum(resolution_counts.values()):
        raise AssertionError("residual resolution does not reconcile anchors")

    executable_signals = set(profiles_by_signal)
    c3_signals = set(c3_by_signal)
    c3_overlap_executable = executable_signals & c3_signals
    if c3_overlap_executable:
        raise AssertionError(
            "C3 shapes unexpectedly overlap executable C2 signal timestamps"
        )

    return {
        "schema": SCHEMA,
        "market": symbol,
        "checked_at": checked_at.isoformat(),
        "software_sha": software_sha,
        "observed_anchor_bars": observed,
        "source_state_counts": dict(state_counts.most_common()),
        "residual_resolution_counts": dict(resolution_counts.most_common()),
        "profile_union": {
            "distinct_mechanical_signal_timestamps": len(executable_signals),
            "by_profile": {
                profile: len(rows)
                for profile, rows in mechanical_by_profile.items()
            },
        },
        "c3": {
            "shape_signal_timestamps": len(c3_signals),
            "overlap_with_executable_c2": len(c3_overlap_executable),
        },
        "c2_source_valid": {
            "total": c2_valid,
            "executable_in_any_profile": resolution_counts[
                "C2_EXECUTABLE_PROFILE_UNION"
            ],
            "no_ps_in_any_profile": resolution_counts[
                "C2_VALID_NO_PS_ANY_PROFILE"
            ],
        },
        "by_anchor_ny": {
            str(anchor): dict(counter.most_common())
            for anchor, counter in by_anchor.items()
        },
        "cross_classification": dict(cross_counts.most_common()),
        "governance": {
            "diagnostics_only": True,
            "profiles_combined_for_execution": False,
            "c3_executable": False,
            "pnl_used": False,
            "methodology_changed": False,
            "live_authorized": False,
        },
    }


def to_json(base_path: Path, *, m3_path: Path) -> str:
    return json.dumps(
        evaluate(base_path, m3_path=m3_path),
        sort_keys=True,
        separators=(",", ":"),
    )
