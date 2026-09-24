"""Forensics for C2-valid anchors with no Protected Swing in any LTF profile."""
from __future__ import annotations

import json
from collections import Counter
from dataclasses import dataclass
from datetime import timedelta
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
    resolve_bias,
    source_h4_from_m15,
)

SCHEMA: Final = "qore.trader_lab.vt08_cognitive_no_ps_forensics.v1"
_NY = ZoneInfo("America/New_York")


@dataclass(frozen=True, slots=True)
class SeriesDiagnostic:
    swept_important_level: bool
    terminated_inside_c2: bool
    cisd_confirmed: bool


def _series_diagnostics(
    bars: tuple[Vt08B01Bar, ...],
    *,
    side: DemoTradingSetupSide,
    important_level: Decimal,
) -> tuple[SeriesDiagnostic, ...]:
    diagnostics: list[SeriesDiagnostic] = []
    series_open = None
    series_extreme = None

    def opposing(bar: Vt08B01Bar) -> bool:
        if side is DemoTradingSetupSide.LONG:
            return bar.close < bar.open
        return bar.close > bar.open

    for bar in bars:
        if opposing(bar):
            if series_open is None:
                series_open = bar.open
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

        if series_open is not None and series_extreme is not None:
            swept = (
                series_extreme < important_level
                if side is DemoTradingSetupSide.LONG
                else series_extreme > important_level
            )
            confirmed = (
                bar.close > series_open
                if side is DemoTradingSetupSide.LONG
                else bar.close < series_open
            )
            diagnostics.append(
                SeriesDiagnostic(
                    swept_important_level=swept,
                    terminated_inside_c2=True,
                    cisd_confirmed=confirmed,
                )
            )
        series_open = None
        series_extreme = None

    if series_open is not None and series_extreme is not None:
        swept = (
            series_extreme < important_level
            if side is DemoTradingSetupSide.LONG
            else series_extreme > important_level
        )
        diagnostics.append(
            SeriesDiagnostic(
                swept_important_level=swept,
                terminated_inside_c2=False,
                cisd_confirmed=False,
            )
        )

    return tuple(diagnostics)


def _profile_failure_class(
    bars: tuple[Vt08B01Bar, ...],
    *,
    side: DemoTradingSetupSide,
    important_level: Decimal,
) -> str:
    diagnostics = _series_diagnostics(
        bars,
        side=side,
        important_level=important_level,
    )
    if not diagnostics:
        return "NO_OPPOSING_SERIES"

    if any(
        item.swept_important_level
        and item.terminated_inside_c2
        and item.cisd_confirmed
        for item in diagnostics
    ):
        return "WOULD_HAVE_PROTECTED_SWING"

    if any(
        item.swept_important_level
        and item.terminated_inside_c2
        and not item.cisd_confirmed
        for item in diagnostics
    ):
        return "IMPORTANT_LEVEL_SWEPT_CISD_NOT_CONFIRMED"

    if any(
        item.swept_important_level
        and not item.terminated_inside_c2
        for item in diagnostics
    ):
        return "IMPORTANT_LEVEL_SWEPT_SERIES_OPEN_AT_C2_END"

    return "NO_OPPOSING_SERIES_SWEEP_OF_IMPORTANT_LEVEL"


def evaluate(base_path: Path, *, m3_path: Path) -> dict[str, object]:
    _fingerprint, symbol, checked_at, software_sha, m15 = load_market_evidence(
        base_path
    )
    if symbol not in EXPANSION_MARKETS:
        raise ValueError("no-PS forensics market outside frozen universe")

    m15_by_open = {bar.opened_at: bar for bar in m15}
    executable_signals = {
        row.signal_at
        for profile in PROFILES
        for row in _profile_variants(
            base_path,
            profile=profile,
            m3_path=m3_path,
        )
    }

    profile_bars = {}
    profile_indexes = {}
    for profile in PROFILES:
        bars, _minutes = _profile_bars(
            profile=profile,
            base_path=base_path,
            m3_path=m3_path,
            symbol=symbol,
            m15=m15,
        )
        profile_bars[profile] = bars
        profile_indexes[profile] = {bar.opened_at: bar for bar in bars}

    cases = 0
    profile_failure_counts: dict[str, Counter[str]] = {
        profile: Counter() for profile in PROFILES
    }
    cross_profile_patterns: Counter[str] = Counter()
    by_anchor: dict[int, Counter[str]] = {
        anchor: Counter() for anchor in ANCHORS_NY
    }

    for entry_bar in m15:
        local = entry_bar.opened_at.astimezone(_NY)
        if local.minute != 0 or local.hour not in ANCHORS_NY:
            continue
        if entry_bar.opened_at in executable_signals:
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

        cases += 1
        important_level = (
            reference.low
            if side is DemoTradingSetupSide.LONG
            else reference.high
        )
        pattern_parts: list[str] = []

        for profile in PROFILES:
            rows = _ltf_window(
                profile=profile,
                bars_by_open=profile_indexes[profile],
                opened_at=candle2.opened_at,
                closed_at=candle2.closed_at,
            )
            if rows is None:
                failure = "LTF_C2_WINDOW_INCOMPLETE"
            else:
                failure = _profile_failure_class(
                    rows,
                    side=side,
                    important_level=important_level,
                )
            if failure == "WOULD_HAVE_PROTECTED_SWING":
                raise AssertionError(
                    "no-PS case unexpectedly contains a valid Protected Swing"
                )
            profile_failure_counts[profile][failure] += 1
            pattern_parts.append(f"{profile}:{failure}")

        pattern = "|".join(pattern_parts)
        cross_profile_patterns[pattern] += 1
        by_anchor[local.hour][pattern] += 1

    return {
        "schema": SCHEMA,
        "market": symbol,
        "checked_at": checked_at.isoformat(),
        "software_sha": software_sha,
        "c2_valid_no_ps_any_profile_cases": cases,
        "profile_failure_counts": {
            profile: dict(counter.most_common())
            for profile, counter in profile_failure_counts.items()
        },
        "cross_profile_patterns": dict(cross_profile_patterns.most_common()),
        "by_anchor_ny": {
            str(anchor): dict(counter.most_common())
            for anchor, counter in by_anchor.items()
        },
        "governance": {
            "diagnostics_only": True,
            "pnl_used": False,
            "protected_swing_rule_changed": False,
            "cisd_rule_changed": False,
            "entry_created": False,
            "live_authorized": False,
        },
    }


def to_json(base_path: Path, *, m3_path: Path) -> str:
    return json.dumps(
        evaluate(base_path, m3_path=m3_path),
        sort_keys=True,
        separators=(",", ":"),
    )
