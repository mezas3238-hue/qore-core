"""M3 intracycle Candle-2 source-opportunity census for VT08 expansion.

This module counts causal source states only. It does not replay outcomes or
select markets/anchors from economics.
"""
from __future__ import annotations

import json
from collections import Counter
from datetime import datetime, timedelta
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
from qore.infrastructure.trader_lab.vt08_cognitive_m3_continuation_density_census_v1 import (
    _unique_active_fvg,
)
from qore.infrastructure.traders.contracts import DemoTradingSetupSide
from qore.infrastructure.traders.vt08_b01_r3_8 import (
    protected_swings_in_candle2,
    resolve_bias,
    source_h4_from_m15,
)

SCHEMA: Final = "qore.trader_lab.vt08_cognitive_m3_intracycle_c2_density_census.v1"
PROFILE: Final = "M3_FRACTAL"
_NY = ZoneInfo("America/New_York")


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
    owner_cycles = 0
    bias_resolved_cycles = 0
    boundary_cisd_ps = 0
    strict_fvg_confirmation_close = 0
    positive_risk_geometry = 0
    cycles_with_source_confirmation = 0
    cycles_with_strict_close_entry = 0
    by_anchor = {
        anchor: {
            "cycles": 0,
            "bias_resolved": 0,
            "boundary_cisd_ps": 0,
            "strict_fvg_confirmation_close": 0,
        }
        for anchor in ANCHORS_NY
    }

    for entry_bar in m15:
        local = entry_bar.opened_at.astimezone(_NY)
        if local.minute != 0 or local.hour not in ANCHORS_NY:
            continue
        owner_cycles += 1
        by_anchor[local.hour]["cycles"] += 1

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
        bias_resolved_cycles += 1
        by_anchor[local.hour]["bias_resolved"] += 1

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

        cycles_with_source_confirmation += 1
        boundary_cisd_ps += len(swings)
        by_anchor[local.hour]["boundary_cisd_ps"] += len(swings)

        strict_this_cycle = 0
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
                raise AssertionError("Protected Swing confirmation missing from M3 window")
            if (
                _unique_active_fvg(
                    rows,
                    confirmation_index=confirmation_index,
                    side=side,
                )
                is None
            ):
                continue

            strict_fvg_confirmation_close += 1
            strict_this_cycle += 1
            by_anchor[local.hour]["strict_fvg_confirmation_close"] += 1

            entry = rows[confirmation_index].close
            risk = (
                entry - swing.price
                if side is DemoTradingSetupSide.LONG
                else swing.price - entry
            )
            if risk > Decimal("0"):
                positive_risk_geometry += 1

        if strict_this_cycle:
            cycles_with_strict_close_entry += 1

    span_days = Decimal(
        str(
            (
                max(bar.closed_at for bar in m15)
                - min(bar.opened_at for bar in m15)
            ).total_seconds()
        )
    ) / Decimal("86400")
    strict_annualized = (
        Decimal(strict_fvg_confirmation_close) * Decimal("365") / span_days
        if span_days > 0
        else Decimal("0")
    )
    raw_annualized = (
        Decimal(boundary_cisd_ps) * Decimal("365") / span_days
        if span_days > 0
        else Decimal("0")
    )

    return {
        "schema": SCHEMA,
        "market": symbol,
        "profile": PROFILE,
        "checked_at": checked_at.isoformat(),
        "software_sha": software_sha,
        "evidence_status": "CONSUMED_DEVELOPMENT_NO_OUTCOMES",
        "owner_h4_cycles": owner_cycles,
        "bias_resolved_cycles": bias_resolved_cycles,
        "source_confirmed_boundary_cisd_ps": boundary_cisd_ps,
        "cycles_with_source_confirmation": cycles_with_source_confirmation,
        "strict_cisd_confirmation_close_fvg": strict_fvg_confirmation_close,
        "cycles_with_strict_close_entry": cycles_with_strict_close_entry,
        "strict_positive_risk_geometry": positive_risk_geometry,
        "source_confirmed_two_year_equivalent": format(
            raw_annualized * Decimal("2"),
            "f",
        ),
        "strict_close_entry_two_year_equivalent": format(
            strict_annualized * Decimal("2"),
            "f",
        ),
        "by_anchor_ny": {
            str(key): value for key, value in sorted(by_anchor.items())
        },
        "first_failure_counts": dict(failures.most_common()),
        "methodology_note": (
            "C2 intracycle reversal requires source qualitative wick-profile "
            "adjudication before executable authority; this census deliberately "
            "does not infer shallow/large from outcomes."
        ),
        "governance": {
            "diagnostics_only": True,
            "terminal_pnl_used": False,
            "future_after_signal_used_for_admission": False,
            "owner_anchors_only": True,
            "daily_cardinality_cap": False,
            "c2_final_h4_close_required": False,
            "source_wick_profile_inferred": False,
            "strict_close_entry_requires_unique_active_fvg": True,
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
