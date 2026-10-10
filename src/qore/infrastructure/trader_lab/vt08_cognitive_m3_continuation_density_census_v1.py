"""Source-bound M3 continuation-entry density census for VT08 expansion.

Counts causal PROTECTED_SWING_CONTINUATION opportunities only. It does not
replay outcomes or use terminal PnL.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Final

from qore.infrastructure.trader_lab.vt08_cognitive_expansion_5m_evaluator_v1 import (
    Vt08ExpansionCandidate,
)
from qore.infrastructure.trader_lab.vt08_cognitive_latest_ps_density_recovery_v1 import (
    _ltf_window,
    _profile_bars,
)
from qore.infrastructure.trader_lab.vt08_cognitive_m3_all_valid_anchors_frontier_v1 import (
    PROFILE,
    _all_anchor_candidates,
)
from qore.infrastructure.traders.contracts import DemoTradingSetupSide
from qore.infrastructure.traders.vt08_b01_r3_8 import Vt08B01Bar

SCHEMA: Final = "qore.trader_lab.vt08_cognitive_m3_continuation_density_census.v1"


@dataclass(frozen=True, slots=True)
class ContinuationOpportunity:
    signal_at: datetime
    side: DemoTradingSetupSide
    entry: Decimal
    stop: Decimal
    destination: Decimal
    room_r: Decimal


def _unique_active_fvg(
    bars: tuple[Vt08B01Bar, ...],
    *,
    confirmation_index: int,
    side: DemoTradingSetupSide,
) -> tuple[Decimal, Decimal] | None:
    matches: list[tuple[Decimal, Decimal]] = []
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
        reached = confirmation.low <= upper and confirmation.high >= lower
        if (
            not invalidated
            and reached
            and lower <= confirmation.close <= upper
        ):
            matches.append((lower, upper))
    unique = tuple(dict.fromkeys(matches))
    return unique[0] if len(unique) == 1 else None


def _continuation_swings(
    bars: tuple[Vt08B01Bar, ...],
    *,
    side: DemoTradingSetupSide,
) -> tuple[tuple[int, Decimal, Decimal], ...]:
    rows: list[tuple[int, Decimal, Decimal]] = []
    series_open: Decimal | None = None
    extreme: Decimal | None = None
    in_opposing = False

    for index, bar in enumerate(bars):
        opposing = (
            bar.close < bar.open
            if side is DemoTradingSetupSide.LONG
            else bar.close > bar.open
        )
        if opposing:
            if not in_opposing:
                series_open = bar.open
                extreme = bar.low if side is DemoTradingSetupSide.LONG else bar.high
            else:
                assert extreme is not None
                extreme = (
                    min(extreme, bar.low)
                    if side is DemoTradingSetupSide.LONG
                    else max(extreme, bar.high)
                )
            in_opposing = True
            continue

        if series_open is not None and extreme is not None:
            confirmed = (
                bar.close > series_open
                if side is DemoTradingSetupSide.LONG
                else bar.close < series_open
            )
            if confirmed:
                rows.append((index, series_open, extreme))
        series_open = None
        extreme = None
        in_opposing = False

    return tuple(rows)


def _opportunities(
    candidate: Vt08ExpansionCandidate,
    *,
    m3_by_open: dict[datetime, Vt08B01Bar],
) -> tuple[ContinuationOpportunity, ...]:
    end = candidate.decision_at + timedelta(hours=4)
    bars = _ltf_window(
        profile=PROFILE,
        bars_by_open=m3_by_open,
        opened_at=candidate.decision_at,
        closed_at=end,
    )
    if bars is None:
        return ()

    destination = (
        candidate.reference_h4.high
        if candidate.side is DemoTradingSetupSide.LONG
        else candidate.reference_h4.low
    )
    rows: list[ContinuationOpportunity] = []
    for index, _cisd_level, extreme in _continuation_swings(
        bars,
        side=candidate.side,
    ):
        if _unique_active_fvg(
            bars,
            confirmation_index=index,
            side=candidate.side,
        ) is None:
            continue
        confirmation = bars[index]
        entry = confirmation.close
        risk = (
            entry - extreme
            if candidate.side is DemoTradingSetupSide.LONG
            else extreme - entry
        )
        if risk <= 0:
            continue
        room = (
            destination - entry
            if candidate.side is DemoTradingSetupSide.LONG
            else entry - destination
        )
        if room < Decimal("2") * risk:
            continue
        rows.append(
            ContinuationOpportunity(
                signal_at=confirmation.closed_at,
                side=candidate.side,
                entry=entry,
                stop=extreme,
                destination=destination,
                room_r=room / risk,
            )
        )
    return tuple(rows)


def evaluate(base_path: Path, *, m3_path: Path) -> dict[str, object]:
    (
        candidates,
        bars_by_open,
        symbol,
        checked_at,
        software_sha,
        span_days,
        failures,
    ) = _all_anchor_candidates(base_path, m3_path=m3_path)
    m15 = tuple(bars_by_open[key] for key in sorted(bars_by_open))
    m3, _minutes = _profile_bars(
        profile=PROFILE,
        base_path=base_path,
        m3_path=m3_path,
        symbol=symbol,
        m15=m15,
    )
    m3_by_open = {bar.opened_at: bar for bar in m3}

    total = 0
    anchors_with_continuation = 0
    counts_by_anchor = {1: 0, 5: 0, 9: 0}
    for candidate in candidates:
        rows = _opportunities(candidate, m3_by_open=m3_by_open)
        if rows:
            anchors_with_continuation += 1
        total += len(rows)
        counts_by_anchor[candidate.entry_anchor_hour] += len(rows)

    annualized = (
        Decimal(total) * Decimal("365") / span_days
        if span_days > 0
        else Decimal("0")
    )
    base_annualized = (
        Decimal(len(candidates)) * Decimal("365") / span_days
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
        "base_valid_anchor_candidates": len(candidates),
        "continuation_opportunities": total,
        "anchors_with_one_or_more_continuations": anchors_with_continuation,
        "combined_structural_opportunity_count": len(candidates) + total,
        "base_two_year_equivalent": format(base_annualized * Decimal("2"), "f"),
        "continuation_two_year_equivalent": format(annualized * Decimal("2"), "f"),
        "combined_two_year_equivalent": format(
            (base_annualized + annualized) * Decimal("2"),
            "f",
        ),
        "continuations_by_anchor_ny": {
            str(key): value for key, value in sorted(counts_by_anchor.items())
        },
        "base_first_failure_counts": dict(failures.most_common()),
        "governance": {
            "diagnostics_only": True,
            "terminal_pnl_used": False,
            "future_after_signal_used_for_admission": False,
            "entry_family": "PROTECTED_SWING_CONTINUATION",
            "unique_active_fvg_required": True,
            "protected_swing_stop_required": True,
            "structural_destination_room_at_least_2r": True,
            "owner_anchors_only": True,
            "market_filtering": False,
            "live_authorized": False,
        },
    }


def to_json(base_path: Path, *, m3_path: Path) -> str:
    return json.dumps(
        evaluate(base_path, m3_path=m3_path),
        sort_keys=True,
        separators=(",", ":"),
    )
