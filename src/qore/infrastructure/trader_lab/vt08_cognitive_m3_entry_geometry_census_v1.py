"""Outcome-blind M3 entry-geometry census for VT08 Cognitive Expansion.

The census starts from source-observable intracycle boundary-run + CISD +
Protected-Swing events and measures causal entry geometry availability. It does
not label any geometry as an authorized entry family and does not replay PnL.
"""
from __future__ import annotations

import json
from collections import Counter, defaultdict
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Final
from zoneinfo import ZoneInfo

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
    _ltf_window,
    _profile_bars,
)
from qore.infrastructure.traders.contracts import DemoTradingSetupSide
from qore.infrastructure.traders.vt08_b01_r3_8 import (
    Vt08B01Bar,
    protected_swings_in_candle2,
    resolve_bias,
    source_h4_from_m15,
)

SCHEMA: Final = "qore.trader_lab.vt08_cognitive_m3_entry_geometry_census.v1"
PROFILE: Final = "M3_FRACTAL"
_NY = ZoneInfo("America/New_York")


def _active_fvgs(
    bars: tuple[Vt08B01Bar, ...],
    *,
    confirmation_index: int,
    side: DemoTradingSetupSide,
) -> tuple[tuple[Decimal, Decimal], ...]:
    zones: list[tuple[Decimal, Decimal]] = []
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

        invalidated_before_confirmation = any(
            later.low < lower
            if side is DemoTradingSetupSide.LONG
            else later.high > upper
            for later in bars[index + 1 : confirmation_index]
        )
        if not invalidated_before_confirmation:
            zones.append((lower, upper))
    return tuple(dict.fromkeys(zones))


def _touches(bar: Vt08B01Bar, zone: tuple[Decimal, Decimal]) -> bool:
    lower, upper = zone
    return bar.low <= upper and bar.high >= lower


def _close_inside(bar: Vt08B01Bar, zone: tuple[Decimal, Decimal]) -> bool:
    lower, upper = zone
    return lower <= bar.close <= upper


def _open_inside(bar: Vt08B01Bar, zone: tuple[Decimal, Decimal]) -> bool:
    lower, upper = zone
    return lower <= bar.open <= upper


def _two_year_equivalent(count: int, *, span_days: Decimal) -> str:
    if span_days <= 0:
        return "0"
    return format(
        Decimal(count) * Decimal("730") / span_days,
        "f",
    )


def evaluate(base_path: Path, *, m3_path: Path) -> dict[str, object]:
    _fingerprint, symbol, checked_at, software_sha, m15 = load_market_evidence(
        base_path
    )
    if symbol not in EXPANSION_MARKETS:
        raise ValueError("market outside frozen VT08 expansion scope")

    m3, _minutes = _profile_bars(
        profile=PROFILE,
        base_path=base_path,
        m3_path=m3_path,
        symbol=symbol,
        m15=m15,
    )
    m15_by_open = {bar.opened_at: bar for bar in m15}
    m3_by_open = {bar.opened_at: bar for bar in m3}
    failures: Counter[str] = Counter()
    event_counts: Counter[str] = Counter()
    day_sets: dict[str, set[date]] = defaultdict(set)
    anchor_counts: dict[int, Counter[str]] = {
        anchor: Counter() for anchor in ANCHORS_NY
    }

    for entry_bar in m15:
        local = entry_bar.opened_at.astimezone(_NY)
        if local.minute != 0 or local.hour not in ANCHORS_NY:
            continue

        reference = source_h4_from_m15(
            m15_by_open,
            opened_at_local=local - timedelta(hours=4),
        )
        if reference is None:
            failures["INCOMPLETE_REFERENCE_H4"] += 1
            continue

        source_days = _latest_complete_source_days(
            m15_by_open,
            before_local=local,
        )
        if len(source_days) != 2:
            failures["INCOMPLETE_SOURCE_DAY"] += 1
            continue
        current_day, previous_day = source_days
        side = resolve_bias(previous_day=previous_day, current_day=current_day)
        if side is None:
            failures["BIAS_UNRESOLVED"] += 1
            continue

        rows = _ltf_window(
            profile=PROFILE,
            bars_by_open=m3_by_open,
            opened_at=entry_bar.opened_at,
            closed_at=entry_bar.opened_at + timedelta(hours=4),
        )
        if rows is None:
            failures["M3_H4_WINDOW_INCOMPLETE"] += 1
            continue

        important_level = (
            reference.low if side is DemoTradingSetupSide.LONG else reference.high
        )
        swings = protected_swings_in_candle2(
            rows,
            side=side,
            important_level=important_level,
        )
        if not swings:
            failures["NO_BOUNDARY_CISD_PROTECTED_SWING"] += 1
            continue

        ny_day = local.date()
        for swing in swings:
            confirmation_index = next(
                (
                    index
                    for index, bar in enumerate(rows)
                    if bar.closed_at == swing.confirmed_at
                ),
                None,
            )
            if confirmation_index is None:
                raise AssertionError(
                    "Protected Swing confirmation missing from M3 window"
                )

            event_counts["SOURCE_CISD_PS"] += 1
            day_sets["SOURCE_CISD_PS"].add(ny_day)
            anchor_counts[local.hour]["SOURCE_CISD_PS"] += 1

            confirmation = rows[confirmation_index]
            risk = (
                confirmation.close - swing.price
                if side is DemoTradingSetupSide.LONG
                else swing.price - confirmation.close
            )
            if risk > 0:
                event_counts["POSITIVE_CONFIRMATION_RISK"] += 1
                day_sets["POSITIVE_CONFIRMATION_RISK"].add(ny_day)

            zones = _active_fvgs(
                rows,
                confirmation_index=confirmation_index,
                side=side,
            )
            if zones:
                event_counts["ACTIVE_PRECONFIRMATION_FVG_ANY"] += 1
                day_sets["ACTIVE_PRECONFIRMATION_FVG_ANY"].add(ny_day)
                anchor_counts[local.hour]["ACTIVE_PRECONFIRMATION_FVG_ANY"] += 1
            if len(zones) == 1:
                event_counts["ACTIVE_PRECONFIRMATION_FVG_UNIQUE"] += 1
                day_sets["ACTIVE_PRECONFIRMATION_FVG_UNIQUE"].add(ny_day)

            if any(_touches(confirmation, zone) for zone in zones):
                event_counts["CONFIRMATION_TOUCHES_ACTIVE_FVG"] += 1
                day_sets["CONFIRMATION_TOUCHES_ACTIVE_FVG"].add(ny_day)
            if any(_close_inside(confirmation, zone) for zone in zones):
                event_counts["CONFIRMATION_CLOSE_INSIDE_ACTIVE_FVG"] += 1
                day_sets["CONFIRMATION_CLOSE_INSIDE_ACTIVE_FVG"].add(ny_day)

            if confirmation_index + 1 < len(rows):
                next_bar = rows[confirmation_index + 1]
                if any(_open_inside(next_bar, zone) for zone in zones):
                    event_counts["NEXT_M3_OPEN_INSIDE_ACTIVE_FVG"] += 1
                    day_sets["NEXT_M3_OPEN_INSIDE_ACTIVE_FVG"].add(ny_day)

            future = rows[confirmation_index + 1 :]
            if zones and any(
                _touches(bar, zone)
                for bar in future
                for zone in zones
            ):
                event_counts["POST_CONFIRMATION_FVG_RETEST"] += 1
                day_sets["POST_CONFIRMATION_FVG_RETEST"].add(ny_day)
                anchor_counts[local.hour]["POST_CONFIRMATION_FVG_RETEST"] += 1
            if zones and any(
                _close_inside(bar, zone)
                for bar in future
                for zone in zones
            ):
                event_counts["POST_CONFIRMATION_CLOSE_IN_FVG"] += 1
                day_sets["POST_CONFIRMATION_CLOSE_IN_FVG"].add(ny_day)

            if any(
                bar.low <= swing.cisd_level <= bar.high
                for bar in future
            ):
                event_counts["POST_CONFIRMATION_CISD_LEVEL_RETEST"] += 1
                day_sets["POST_CONFIRMATION_CISD_LEVEL_RETEST"].add(ny_day)
                anchor_counts[local.hour]["POST_CONFIRMATION_CISD_LEVEL_RETEST"] += 1

    span_days = Decimal(
        str(
            (
                max(bar.closed_at for bar in m15)
                - min(bar.opened_at for bar in m15)
            ).total_seconds()
        )
    ) / Decimal("86400")

    keys = (
        "SOURCE_CISD_PS",
        "POSITIVE_CONFIRMATION_RISK",
        "ACTIVE_PRECONFIRMATION_FVG_ANY",
        "ACTIVE_PRECONFIRMATION_FVG_UNIQUE",
        "CONFIRMATION_TOUCHES_ACTIVE_FVG",
        "CONFIRMATION_CLOSE_INSIDE_ACTIVE_FVG",
        "NEXT_M3_OPEN_INSIDE_ACTIVE_FVG",
        "POST_CONFIRMATION_FVG_RETEST",
        "POST_CONFIRMATION_CLOSE_IN_FVG",
        "POST_CONFIRMATION_CISD_LEVEL_RETEST",
    )
    event_report = {
        key: {
            "event_count": event_counts[key],
            "unique_ny_days": len(day_sets[key]),
            "two_year_equivalent_events": _two_year_equivalent(
                event_counts[key],
                span_days=span_days,
            ),
            "two_year_equivalent_unique_days": _two_year_equivalent(
                len(day_sets[key]),
                span_days=span_days,
            ),
        }
        for key in keys
    }

    return {
        "schema": SCHEMA,
        "market": symbol,
        "profile": PROFILE,
        "checked_at": checked_at.isoformat(),
        "software_sha": software_sha,
        "evidence_status": "CONSUMED_DEVELOPMENT_ENTRY_GEOMETRY_ONLY",
        "events": event_report,
        "by_anchor_ny": {
            str(anchor): dict(anchor_counts[anchor])
            for anchor in ANCHORS_NY
        },
        "first_failure_counts": dict(failures.most_common()),
        "governance": {
            "diagnostics_only": True,
            "terminal_pnl_used": False,
            "trade_outcome_used": False,
            "entry_family_authorized_by_this_census": False,
            "future_after_candidate_used_only_to_observe_later_entry_retest_event": True,
            "owner_max_one_fill_per_market_day_preserved_in_unique_day_metric": True,
            "market_filtering": False,
            "anchor_filtering": False,
            "live_authorized": False,
        },
    }


def to_json(base_path: Path, *, m3_path: Path) -> str:
    return json.dumps(
        evaluate(base_path, m3_path=m3_path),
        sort_keys=True,
        separators=(",", ":"),
    )
