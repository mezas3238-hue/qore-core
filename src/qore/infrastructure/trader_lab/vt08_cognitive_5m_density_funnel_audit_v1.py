"""Root-cause density funnel audit for VT08 Cognitive Expansion 5M.

Every observed 01/05/09 New York anchor in the immutable 1095-day evidence is
walked through the frozen source-admission funnel. The audit changes no rule and
does not optimize density. It only counts exactly where opportunities disappear.
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
    load_market_evidence,
    model_trade,
)
from qore.infrastructure.trader_lab.vt08_cognitive_expansion_5m_evaluator_v1 import (
    Vt08ExpansionCandidate,
    _latest_complete_source_days,
    _window_bars,
)
from qore.infrastructure.trader_lab.vt08_cognitive_expansion_5m_v1 import (
    ANCHORS_NY,
    EXPANSION_MARKETS,
)
from qore.infrastructure.traders.contracts import DemoTradingSetupSide
from qore.infrastructure.traders.vt08_b01_r3_8 import (
    Vt08B01Bar,
    protected_swings_in_candle2,
    resolve_bias,
    source_h4_from_m15,
)

SCHEMA: Final = "qore.trader_lab.vt08_cognitive_5m_density_funnel_audit.v1"
SOURCE_RUN_ID: Final = 35934924907
SOURCE_HEAD: Final = "b2d33e1b4829d8b4afc76983decca8a99131403c"
_NY = ZoneInfo("America/New_York")


def _stage(counter: Counter[str], name: str) -> None:
    counter[name] += 1


def _c2_state(
    reference: Vt08B01Bar,
    candle2: Vt08B01Bar,
) -> tuple[str, DemoTradingSetupSide | None]:
    swept_high = candle2.high > reference.high
    swept_low = candle2.low < reference.low
    if not swept_high and not swept_low:
        return "C2_NO_REFERENCE_SWEEP", None
    if swept_high and swept_low:
        return "C2_BOTH_SIDES_SWEPT", None
    side = DemoTradingSetupSide.SHORT if swept_high else DemoTradingSetupSide.LONG
    if not reference.low < candle2.close < reference.high:
        return "C2_CLOSE_NOT_INSIDE_REFERENCE", side
    return "C2_ONE_SIDE_SWEEP_CLOSE_INSIDE", side


def _candidate_from_components(
    *,
    symbol: str,
    decision_at: datetime,
    entry_anchor_hour: int,
    reference: Vt08B01Bar,
    candle2: Vt08B01Bar,
    side: DemoTradingSetupSide,
    protected,
    entry_bar: Vt08B01Bar,
) -> Vt08ExpansionCandidate | None:
    from qore.infrastructure.trader_lab.vt08_cognitive_expansion_5m_evaluator_v1 import (
        Vt08ExpansionCandidate,
    )
    from qore.infrastructure.trader_lab.vt08_cognitive_expansion_5m_v1 import (
        program_fingerprint,
    )
    from qore.infrastructure.traders.contracts import (
        DemoTradingError,
        DemoTradingSetupSpec,
    )
    from qore.infrastructure.traders.vt08_b01_r3_8 import (
        methodology_fingerprint,
    )

    entry = entry_bar.open
    stop = protected.price
    risk = entry - stop if side is DemoTradingSetupSide.LONG else stop - entry
    if risk <= 0:
        return None
    target = (
        entry + Decimal(2) * risk
        if side is DemoTradingSetupSide.LONG
        else entry - Decimal(2) * risk
    )
    if target <= 0:
        return None
    try:
        setup = DemoTradingSetupSpec(
            side=side,
            entry_price=entry,
            invalidation_price=stop,
            take_profit_price=target,
            entry_reason="vt08-density-funnel-audit-reconstruction",
        )
    except DemoTradingError:
        return None
    return Vt08ExpansionCandidate(
        symbol=symbol,
        side=side,
        decision_at=decision_at,
        entry_anchor_hour=entry_anchor_hour,
        reference_h4=reference,
        candle2=candle2,
        protected_swing=protected,
        setup=setup,
        vt08_methodology_fingerprint=methodology_fingerprint(),
        expansion_program_fingerprint=program_fingerprint(),
    )


def evaluate(path: Path) -> dict[str, object]:
    _fingerprint, symbol, checked_at, software_sha, bars = load_market_evidence(path)
    if symbol not in EXPANSION_MARKETS:
        raise ValueError("market outside frozen 5M universe")

    bars_by_open = {bar.opened_at: bar for bar in bars}
    funnel: Counter[str] = Counter()
    losses: Counter[str] = Counter()
    candidates_by_day: dict[date, list[Vt08ExpansionCandidate]] = defaultdict(list)
    by_anchor_candidates: Counter[int] = Counter()
    by_anchor_losses: dict[int, Counter[str]] = {
        anchor: Counter() for anchor in ANCHORS_NY
    }

    anchor_bars = []
    dates_with_m15: set[date] = set()
    for bar in bars:
        local = bar.opened_at.astimezone(_NY)
        dates_with_m15.add(local.date())
        if local.minute == 0 and local.hour in ANCHORS_NY:
            anchor_bars.append(bar)

    for bar in anchor_bars:
        local = bar.opened_at.astimezone(_NY)
        anchor = local.hour
        _stage(funnel, "ANCHOR_BAR_OBSERVED")

        reference = source_h4_from_m15(
            bars_by_open,
            opened_at_local=local - timedelta(hours=8),
        )
        candle2 = source_h4_from_m15(
            bars_by_open,
            opened_at_local=local - timedelta(hours=4),
        )
        if reference is None or candle2 is None or candle2.closed_at != bar.opened_at:
            losses["INCOMPLETE_SOURCE_H4"] += 1
            by_anchor_losses[anchor]["INCOMPLETE_SOURCE_H4"] += 1
            continue
        _stage(funnel, "SOURCE_H4_COMPLETE")

        source_days = _latest_complete_source_days(
            bars_by_open,
            before_local=local,
        )
        if len(source_days) != 2:
            losses["INCOMPLETE_SOURCE_DAY"] += 1
            by_anchor_losses[anchor]["INCOMPLETE_SOURCE_DAY"] += 1
            continue
        _stage(funnel, "SOURCE_DAY_COMPLETE")

        current_day, previous_day = source_days
        side = resolve_bias(previous_day=previous_day, current_day=current_day)
        if side is None:
            losses["BIAS_UNRESOLVED"] += 1
            by_anchor_losses[anchor]["BIAS_UNRESOLVED"] += 1
            continue
        _stage(funnel, "BIAS_RESOLVED")

        c2_state, c2_side = _c2_state(reference, candle2)
        if c2_state != "C2_ONE_SIDE_SWEEP_CLOSE_INSIDE":
            losses[c2_state] += 1
            by_anchor_losses[anchor][c2_state] += 1
            continue
        _stage(funnel, "C2_ONE_SIDE_SWEEP")
        _stage(funnel, "C2_CLOSE_INSIDE")

        if c2_side is not side:
            losses["C2_SIDE_BIAS_MISMATCH"] += 1
            by_anchor_losses[anchor]["C2_SIDE_BIAS_MISMATCH"] += 1
            continue
        _stage(funnel, "C2_MATCHES_BIAS")

        candle2_m15 = _window_bars(
            bars_by_open,
            opened_at=candle2.opened_at,
            closed_at=candle2.closed_at,
        )
        if candle2_m15 is None:
            losses["C2_M15_WINDOW_INCOMPLETE"] += 1
            by_anchor_losses[anchor]["C2_M15_WINDOW_INCOMPLETE"] += 1
            continue
        _stage(funnel, "C2_M15_WINDOW_COMPLETE")

        important_level = (
            reference.low if side is DemoTradingSetupSide.LONG else reference.high
        )
        swings = protected_swings_in_candle2(
            candle2_m15,
            side=side,
            important_level=important_level,
        )
        if not swings:
            losses["NO_PROTECTED_SWING"] += 1
            by_anchor_losses[anchor]["NO_PROTECTED_SWING"] += 1
            continue
        _stage(funnel, "PROTECTED_SWING_AT_LEAST_ONE")
        if len(swings) != 1:
            losses["MULTIPLE_PROTECTED_SWINGS"] += 1
            by_anchor_losses[anchor]["MULTIPLE_PROTECTED_SWINGS"] += 1
            continue
        _stage(funnel, "PROTECTED_SWING_EXACTLY_ONE")

        candidate = _candidate_from_components(
            symbol=symbol,
            decision_at=bar.opened_at,
            entry_anchor_hour=anchor,
            reference=reference,
            candle2=candle2,
            side=side,
            protected=swings[0],
            entry_bar=bar,
        )
        if candidate is None:
            losses["INVALID_RISK_GEOMETRY"] += 1
            by_anchor_losses[anchor]["INVALID_RISK_GEOMETRY"] += 1
            continue
        _stage(funnel, "VALID_RISK_GEOMETRY")
        _stage(funnel, "MECHANICAL_CANDIDATE")
        candidates_by_day[local.date()].append(candidate)
        by_anchor_candidates[anchor] += 1

    terminal_count = 0
    incomplete_exit = 0
    multi_candidate_days = 0
    candidates_lost_to_daily_cardinality = 0
    for day in sorted(candidates_by_day):
        candidates = candidates_by_day[day]
        if len(candidates) != 1:
            multi_candidate_days += 1
            candidates_lost_to_daily_cardinality += len(candidates)
            continue
        trade = model_trade(candidates[0], bars_by_open=bars_by_open)
        if trade is None:
            incomplete_exit += 1
            continue
        terminal_count += 1

    mechanical_candidates = funnel["MECHANICAL_CANDIDATE"]
    reconciled = (
        terminal_count
        + incomplete_exit
        + candidates_lost_to_daily_cardinality
    )
    if reconciled != mechanical_candidates:
        raise AssertionError(
            "density funnel candidate-to-terminal reconciliation failed"
        )

    theoretical_anchor_slots = len(dates_with_m15) * len(ANCHORS_NY)
    observed_anchor_count = funnel["ANCHOR_BAR_OBSERVED"]
    missing_anchor_slots = theoretical_anchor_slots - observed_anchor_count

    if sum(losses.values()) + mechanical_candidates != observed_anchor_count:
        raise AssertionError("anchor funnel loss reconciliation failed")

    return {
        "schema": SCHEMA,
        "source_run_id": SOURCE_RUN_ID,
        "source_head": SOURCE_HEAD,
        "market": symbol,
        "checked_at": checked_at.isoformat(),
        "software_sha": software_sha,
        "observed_data_dates": len(dates_with_m15),
        "theoretical_anchor_slots_on_observed_dates": theoretical_anchor_slots,
        "observed_anchor_bars": observed_anchor_count,
        "missing_anchor_bars_on_observed_dates": missing_anchor_slots,
        "funnel_stage_pass_counts": dict(funnel),
        "first_failure_counts": dict(losses.most_common()),
        "by_anchor": {
            str(anchor): {
                "mechanical_candidates": by_anchor_candidates[anchor],
                "first_failure_counts": dict(
                    by_anchor_losses[anchor].most_common()
                ),
            }
            for anchor in ANCHORS_NY
        },
        "candidate_to_terminal": {
            "mechanical_candidates": mechanical_candidates,
            "multi_candidate_days": multi_candidate_days,
            "candidates_lost_to_daily_cardinality": (
                candidates_lost_to_daily_cardinality
            ),
            "incomplete_exit_windows": incomplete_exit,
            "terminal_trades": terminal_count,
        },
        "governance": {
            "methodology_changed": False,
            "threshold_search": False,
            "density_optimization": False,
            "post_hoc_filter_created": False,
            "research_only": True,
            "live_authorized": False,
        },
    }


def to_json(path: Path) -> str:
    return json.dumps(evaluate(path), sort_keys=True, separators=(",", ":"))
