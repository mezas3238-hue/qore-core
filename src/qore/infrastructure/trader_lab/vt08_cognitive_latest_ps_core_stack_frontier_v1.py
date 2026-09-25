"""High-density latest-PS admission with the frozen VT08 Core Stack.

Consumed-development frontier only. Profiles are evaluated independently and
no market, anchor, side, or trade is filtered by economics.
"""
from __future__ import annotations

import json
from collections import defaultdict
from datetime import date, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Final
from zoneinfo import ZoneInfo

from qore.infrastructure.trader_lab.vt08_cognitive_core_stack_dev_v1 import (
    simulate_core_stack,
)
from qore.infrastructure.trader_lab.vt08_cognitive_expansion_5m_backtest_v1 import (
    ExpansionTrade,
    load_market_evidence,
    metrics,
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
from qore.infrastructure.trader_lab.vt08_cognitive_latest_ps_density_recovery_v1 import (
    PROFILES,
    SELECTOR_ID,
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

SCHEMA: Final = "qore.trader_lab.vt08_cognitive_latest_ps_core_stack_frontier.v1"
CORE_STACK_ID: Final = "VT08_COGNITIVE_CORE_STACK_DEV_V1"
_NY = ZoneInfo("America/New_York")


def _candidate_rows(
    base_path: Path,
    *,
    profile: str,
    m3_path: Path | None = None,
) -> tuple[
    tuple[Vt08ExpansionCandidate, ...],
    dict[datetime, Vt08B01Bar],
    str,
    datetime,
    str,
    Decimal,
]:
    if profile not in PROFILES:
        raise ValueError("profile outside frozen latest-PS Core Stack frontier")

    _fingerprint, symbol, checked_at, software_sha, m15 = load_market_evidence(
        base_path
    )
    if symbol not in EXPANSION_MARKETS:
        raise ValueError("market outside frozen 5M universe")

    ltf, _ltf_minutes = _profile_bars(
        profile=profile,
        base_path=base_path,
        m3_path=m3_path,
        symbol=symbol,
        m15=m15,
    )
    m15_by_open = {bar.opened_at: bar for bar in m15}
    ltf_by_open = {bar.opened_at: bar for bar in ltf}
    candidates_by_day: dict[date, list[Vt08ExpansionCandidate]] = defaultdict(list)

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
        if _candle2_reversal_side(reference, candle2) is not side:
            continue

        rows = _ltf_window(
            profile=profile,
            bars_by_open=ltf_by_open,
            opened_at=candle2.opened_at,
            closed_at=candle2.closed_at,
        )
        if rows is None:
            continue

        important_level = (
            reference.low
            if side is DemoTradingSetupSide.LONG
            else reference.high
        )
        swings = protected_swings_in_candle2(
            rows,
            side=side,
            important_level=important_level,
        )
        if not swings:
            continue

        try:
            selected = latest_confirmed_swing(swings)
        except ValueError:
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
        if candidate is not None:
            candidates_by_day[local.date()].append(candidate)

    retained = tuple(
        items[0]
        for local_day in sorted(candidates_by_day)
        if len(items := candidates_by_day[local_day]) == 1
    )
    ordered = tuple(sorted(retained, key=lambda item: item.decision_at))
    span_days = (
        Decimal(
            str(
                (
                    max(bar.closed_at for bar in m15)
                    - min(bar.opened_at for bar in m15)
                ).total_seconds()
            )
        )
        / Decimal("86400")
    )
    return ordered, m15_by_open, symbol, checked_at, software_sha, span_days


def evaluate(
    base_path: Path,
    *,
    profile: str,
    m3_path: Path | None = None,
) -> dict[str, object]:
    (
        candidates,
        m15_by_open,
        symbol,
        checked_at,
        software_sha,
        span_days,
    ) = _candidate_rows(base_path, profile=profile, m3_path=m3_path)

    raw: list[ExpansionTrade] = []
    managed: list[ExpansionTrade] = []
    for candidate in candidates:
        item = simulate_core_stack(candidate, bars_by_open=m15_by_open)
        if item is None:
            continue
        raw.append(item.baseline)
        managed.append(item.as_trade())

    if len(raw) != len(managed):
        raise AssertionError("Core Stack changed terminal trade cardinality")
    if any(
        (
            left.symbol,
            left.signal_at,
            left.anchor_hour_ny,
            left.side,
            left.entry,
            left.stop,
            left.target,
        )
        != (
            right.symbol,
            right.signal_at,
            right.anchor_hour_ny,
            right.side,
            right.entry,
            right.stop,
            right.target,
        )
        for left, right in zip(raw, managed, strict=True)
    ):
        raise AssertionError("Core Stack changed frozen trade identity or geometry")

    raw_metrics = metrics(tuple(raw))
    managed_metrics = metrics(tuple(managed))
    annualized = (
        Decimal(len(raw)) * Decimal("365") / span_days
        if span_days > 0
        else Decimal("0")
    )
    raw_pf = Decimal(str(raw_metrics["profit_factor"]))
    managed_pf = Decimal(str(managed_metrics["profit_factor"]))
    raw_total = Decimal(str(raw_metrics["total_r"]))
    managed_total = Decimal(str(managed_metrics["total_r"]))
    raw_dd = Decimal(str(raw_metrics["max_drawdown_r"]))
    managed_dd = Decimal(str(managed_metrics["max_drawdown_r"]))

    return {
        "schema": SCHEMA,
        "market": symbol,
        "profile": profile,
        "selector_id": SELECTOR_ID,
        "core_stack_id": CORE_STACK_ID,
        "checked_at": checked_at.isoformat(),
        "software_sha": software_sha,
        "evidence_status": "CONSUMED_DEVELOPMENT",
        "terminal_trade_count": len(raw),
        "annualized_trades": format(annualized, "f"),
        "two_year_equivalent_trades": format(annualized * Decimal("2"), "f"),
        "raw_equal_risk": raw_metrics,
        "core_stack_managed_r": managed_metrics,
        "delta": {
            "profit_factor": format(managed_pf - raw_pf, "f"),
            "total_r": format(managed_total - raw_total, "f"),
            "max_drawdown_r": format(managed_dd - raw_dd, "f"),
        },
        "governance": {
            "consumed_development": True,
            "profiles_combined": False,
            "market_filtering": False,
            "anchor_filtering": False,
            "side_filtering": False,
            "capital_weighting": False,
            "parameter_scan": False,
            "trade_cardinality_changed": False,
            "entry_changed": False,
            "initial_stop_changed": False,
            "target_changed": False,
            "live_authorized": False,
        },
    }


def to_json(
    base_path: Path,
    *,
    profile: str,
    m3_path: Path | None = None,
) -> str:
    return json.dumps(
        evaluate(base_path, profile=profile, m3_path=m3_path),
        sort_keys=True,
        separators=(",", ":"),
    )
