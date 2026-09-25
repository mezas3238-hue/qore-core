"""M3 latest-PS frontier retaining every source-valid owner anchor.

Consumed-development research only. This removes the research-only daily
cardinality suppression while leaving VT08 admission, entry, stop, target and
H4 lifecycle unchanged.
"""
from __future__ import annotations

import json
from collections import Counter, defaultdict
from datetime import date, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Final
from zoneinfo import ZoneInfo

from qore.infrastructure.trader_lab.vt08_cognitive_expansion_5m_backtest_v1 import (
    ExpansionTrade,
    load_market_evidence,
    metrics,
    model_trade,
)
from qore.infrastructure.trader_lab.vt08_cognitive_expansion_5m_evaluator_v1 import (
    Vt08ExpansionCandidate,
    _candle2_reversal_side,
    _latest_complete_source_days,
)
from qore.infrastructure.trader_lab.vt08_cognitive_expansion_5m_v1 import (
    ANCHORS_NY,
    EXPANSION_MARKETS,
)
from qore.infrastructure.trader_lab.vt08_cognitive_latest_ps_core_stack_frontier_v1 import (
    _candidate_rows,
)
from qore.infrastructure.trader_lab.vt08_cognitive_latest_ps_density_recovery_v1 import (
    _ltf_window,
    _profile_bars,
    latest_confirmed_swing,
)
from qore.infrastructure.trader_lab.vt08_cognitive_m5_fractal_density_recovery_v1 import (
    _candidate,
)
from qore.infrastructure.traders.contracts import DemoTradingSetupSide
from qore.infrastructure.traders.vt08_b01_r3_8 import (
    Vt08B01Bar,
    protected_swings_in_candle2,
    resolve_bias,
    source_h4_from_m15,
)

SCHEMA: Final = "qore.trader_lab.vt08_cognitive_m3_all_valid_anchors_frontier.v1"
PROFILE: Final = "M3_FRACTAL"
_NY = ZoneInfo("America/New_York")


def _all_anchor_candidates(
    base_path: Path,
    *,
    m3_path: Path,
) -> tuple[
    tuple[Vt08ExpansionCandidate, ...],
    dict[datetime, Vt08B01Bar],
    str,
    datetime,
    str,
    Decimal,
    Counter[str],
]:
    _fingerprint, symbol, checked_at, software_sha, m15 = load_market_evidence(base_path)
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
    candidates: list[Vt08ExpansionCandidate] = []

    for entry_bar in m15:
        local = entry_bar.opened_at.astimezone(_NY)
        if local.minute != 0 or local.hour not in ANCHORS_NY:
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
            failures["INCOMPLETE_SOURCE_H4"] += 1
            continue

        source_days = _latest_complete_source_days(m15_by_open, before_local=local)
        if len(source_days) != 2:
            failures["INCOMPLETE_SOURCE_DAY"] += 1
            continue
        current_day, previous_day = source_days
        side = resolve_bias(previous_day=previous_day, current_day=current_day)
        if side is None:
            failures["BIAS_UNRESOLVED"] += 1
            continue
        if _candle2_reversal_side(reference, candle2) is not side:
            failures["C2_REVERSAL_MISMATCH"] += 1
            continue

        rows = _ltf_window(
            profile=PROFILE,
            bars_by_open=m3_by_open,
            opened_at=candle2.opened_at,
            closed_at=candle2.closed_at,
        )
        if rows is None:
            failures["LTF_C2_WINDOW_INCOMPLETE"] += 1
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
            failures["NO_PROTECTED_SWING"] += 1
            continue

        try:
            selected = latest_confirmed_swing(swings)
        except ValueError:
            failures["LATEST_PS_IDENTITY_AMBIGUOUS"] += 1
            continue

        candidate = _candidate(
            symbol=symbol,
            decision_at=entry_bar.opened_at,
            anchor=local.hour,
            reference=reference,
            candle2=candle2,
            side=side,
            protected=selected,
            entry_bar=entry_bar,
        )
        if candidate is None:
            failures["INVALID_RISK_GEOMETRY"] += 1
            continue
        candidates.append(candidate)

    ordered = tuple(sorted(candidates, key=lambda item: item.decision_at))
    span_days = Decimal(
        str(
            (
                max(bar.closed_at for bar in m15)
                - min(bar.opened_at for bar in m15)
            ).total_seconds()
        )
    ) / Decimal("86400")
    return (
        ordered,
        m15_by_open,
        symbol,
        checked_at,
        software_sha,
        span_days,
        failures,
    )


def _trade_rows(
    candidates: tuple[Vt08ExpansionCandidate, ...],
    *,
    bars_by_open: dict[datetime, Vt08B01Bar],
) -> tuple[tuple[ExpansionTrade, ...], int]:
    rows: list[ExpansionTrade] = []
    incomplete = 0
    for candidate in candidates:
        trade = model_trade(candidate, bars_by_open=bars_by_open)
        if trade is None:
            incomplete += 1
            continue
        rows.append(trade)
    return tuple(rows), incomplete


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

    all_rows, incomplete = _trade_rows(candidates, bars_by_open=bars_by_open)

    current_candidates, _bars, _symbol, _checked, _sha, _span = _candidate_rows(
        base_path,
        profile=PROFILE,
        m3_path=m3_path,
    )
    current_rows, current_incomplete = _trade_rows(
        current_candidates,
        bars_by_open=bars_by_open,
    )

    by_day: dict[date, int] = defaultdict(int)
    for candidate in candidates:
        by_day[candidate.decision_at.astimezone(_NY).date()] += 1
    multi_days = {day: count for day, count in by_day.items() if count > 1}

    annualized = (
        Decimal(len(all_rows)) * Decimal("365") / span_days
        if span_days > 0
        else Decimal("0")
    )

    return {
        "schema": SCHEMA,
        "market": symbol,
        "profile": PROFILE,
        "checked_at": checked_at.isoformat(),
        "software_sha": software_sha,
        "evidence_status": "CONSUMED_DEVELOPMENT",
        "current_daily_uniqueness": {
            "candidate_count": len(current_candidates),
            "terminal_trade_count": len(current_rows),
            "incomplete_exit_windows": current_incomplete,
            "economics": metrics(current_rows),
        },
        "all_valid_owner_anchors": {
            "candidate_count": len(candidates),
            "terminal_trade_count": len(all_rows),
            "incomplete_exit_windows": incomplete,
            "economics": metrics(all_rows),
            "annualized_trades": format(annualized, "f"),
            "two_year_equivalent_trades": format(annualized * Decimal("2"), "f"),
            "by_anchor_ny": {
                str(anchor): metrics(
                    tuple(row for row in all_rows if row.anchor_hour_ny == anchor)
                )
                for anchor in ANCHORS_NY
            },
        },
        "density_delta": {
            "candidate_delta": len(candidates) - len(current_candidates),
            "terminal_trade_delta": len(all_rows) - len(current_rows),
            "multi_candidate_days": len(multi_days),
            "extra_candidates_on_multi_days": sum(multi_days.values()),
        },
        "first_failure_counts": dict(failures.most_common()),
        "governance": {
            "consumed_development": True,
            "source_valid_owner_anchors_only": True,
            "daily_cardinality_suppression_removed": True,
            "entry_changed": False,
            "initial_stop_changed": False,
            "target_changed": False,
            "h4_lifecycle_changed": False,
            "pnl_used_for_admission": False,
            "market_filtering": False,
            "anchor_filtering": False,
            "side_filtering": False,
            "profiles_combined": False,
            "live_authorized": False,
        },
    }


def to_json(base_path: Path, *, m3_path: Path) -> str:
    return json.dumps(
        evaluate(base_path, m3_path=m3_path),
        sort_keys=True,
        separators=(",", ":"),
    )
