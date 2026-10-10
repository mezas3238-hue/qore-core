"""Research-only, outcome-blind per-anchor VT08 density attribution ledger.

Exactly replays the *admission* order of the frozen 5M density funnel;
it does not relax rules, inspect winning trades or construct new family fills.
Its first-failure classification describes the NARROW B01 implementation,
not whether TTrades itself would forbid a different source entry family.
"""

from __future__ import annotations

import hashlib
import json
from collections import Counter, defaultdict
from datetime import date, timedelta
from pathlib import Path
from typing import Final
from zoneinfo import ZoneInfo

from qore.infrastructure.trader_lab.vt08_cognitive_5m_density_funnel_audit_v1 import (
    SOURCE_HEAD,
    SOURCE_RUN_ID,
    _c2_state,
    _candidate_from_components,
)
from qore.infrastructure.trader_lab.vt08_cognitive_expansion_5m_backtest_v1 import (
    load_market_evidence,
)
from qore.infrastructure.trader_lab.vt08_cognitive_expansion_5m_evaluator_v1 import (
    _latest_complete_source_days,
    _window_bars,
)
from qore.infrastructure.trader_lab.vt08_cognitive_expansion_5m_v1 import (
    ANCHORS_NY,
    EXPANSION_MARKETS,
)
from qore.infrastructure.traders.contracts import DemoTradingSetupSide
from qore.infrastructure.traders.vt08_b01_r3_8 import (
    protected_swings_in_candle2,
    resolve_bias,
    source_h4_from_m15,
)

SCHEMA: Final = "qore.trader_lab.vt08_5m_methodology_anchor_ledger.v1"
_NY = ZoneInfo("America/New_York")
# Descriptive attribution only; does NOT approve removing any source exclusion.
REASON_AUTHORITY: Final = {
    "INCOMPLETE_SOURCE_H4": "DATA_GAP",
    "INCOMPLETE_SOURCE_DAY": "DATA_GAP_OR_SOURCE_DAY_CONTAINMENT",
    "BIAS_UNRESOLVED": "UNRESOLVED_SOURCE_BIAS_OR_QORE_DAY",
    "C2_NO_REFERENCE_SWEEP": "NARROW_B01_SOURCE_FAMILY_SCOPE",
    "C2_BOTH_SIDES_SWEPT": "UNRESOLVED_QORE_DIRECTION_CONTAINMENT",
    "C2_CLOSE_NOT_INSIDE_REFERENCE": "PENDING_PRIMARY_SOURCE_ADJUDICATION",
    "C2_SIDE_BIAS_MISMATCH": "NARROW_B01_BIAS_CONFLUENCE",
    "C2_M15_WINDOW_INCOMPLETE": "DATA_GAP",
    "NO_PROTECTED_SWING": "NARROW_B01_PS_REQUIREMENT",
    "MULTIPLE_PROTECTED_SWINGS": "QORE_SELECTION_CONTAINMENT",
    "INVALID_RISK_GEOMETRY": "INVALID_EXECUTION_GEOMETRY",
    "MECHANICAL_CANDIDATE": "NARROW_B01_MACHINE_COMPLETE",
}


def _event_id(market: str, decision_at: str) -> str:
    digest = hashlib.sha256(
        f"{SCHEMA}|{market}|M15_STANDARD|{decision_at}".encode()
    ).hexdigest()
    return f"vt08-anchor:{digest}"


def summarize_rows(rows: list[dict[str, object]]) -> dict[str, object]:
    """Summarize a full outcome-blind ledger, rejecting duplicates."""
    seen: set[str] = set()
    years: dict[str, Counter[str]] = defaultdict(Counter)
    first_fail: Counter[str] = Counter()
    by_anchor: dict[str, Counter[str]] = defaultdict(Counter)
    days: dict[str, int] = defaultdict(int)
    candidate_count = 0
    for row in rows:
        event_id = row.get("event_id")
        if not isinstance(event_id, str) or not event_id:
            raise ValueError("anchor row requires event_id")
        if event_id in seen:
            raise ValueError("duplicate anchor event fingerprint")
        seen.add(event_id)
        ny_date = row.get("ny_date")
        reason = row.get("first_failure")
        anchor = row.get("anchor_ny_hour")
        if (
            not isinstance(ny_date, str)
            or not isinstance(reason, str)
            or reason not in REASON_AUTHORITY
            or type(anchor) is not int
            or anchor not in ANCHORS_NY
        ):
            raise ValueError("anchor row is not an approved ledger state")
        year = str(date.fromisoformat(ny_date).year)
        first_fail[reason] += 1
        years[year][reason] += 1
        by_anchor[str(anchor)][reason] += 1
        if reason == "MECHANICAL_CANDIDATE":
            candidate_count += 1
            days[ny_date] += 1

    ambiguous_candidates = sum(n for n in days.values() if n != 1)
    selected_candidates = sum(n for n in days.values() if n == 1)
    if len(rows) != sum(first_fail.values()):
        raise AssertionError("first-failure classes do not reconcile")
    if candidate_count != selected_candidates + ambiguous_candidates:
        raise AssertionError("candidate/daily-cardinality mismatch")
    return {
        "schema": SCHEMA,
        "observed_anchor_bars": len(rows),
        "mechanical_candidates": candidate_count,
        "candidate_unique_ny_dates": len(days),
        "daily_cardinality_ambiguous_candidates": ambiguous_candidates,
        "one_per_day_selected_candidates": selected_candidates,
        "first_failure_counts": dict(sorted(first_fail.items())),
        "by_year_first_failure": {
            year: dict(sorted(c.items())) for year, c in sorted(years.items())
        },
        "by_anchor_first_failure": {
            anchor: dict(sorted(c.items())) for anchor, c in sorted(by_anchor.items())
        },
        "trade_pnl_used": False,
        "outcome_used_for_source_adjudication": False,
        "replay_fills_measured": False,
        "methodology_changed": False,
    }


def evaluate(path: Path) -> dict[str, object]:
    fingerprint, symbol, checked_at, software_sha, bars = load_market_evidence(path)
    if symbol not in EXPANSION_MARKETS:
        raise ValueError("market outside fixed 5M research universe")
    if software_sha != SOURCE_HEAD:
        raise ValueError("1095D evidence software SHA drifted")
    bars_by_open = {bar.opened_at: bar for bar in bars}
    if len(bars_by_open) != len(bars):
        raise ValueError("duplicate M15 evidence timestamps")

    rows: list[dict[str, object]] = []
    for bar in bars:
        local = bar.opened_at.astimezone(_NY)
        if local.minute != 0 or local.hour not in ANCHORS_NY:
            continue
        reason = "INCOMPLETE_SOURCE_H4"
        reference = source_h4_from_m15(
            bars_by_open, opened_at_local=local - timedelta(hours=8)
        )
        candle2 = source_h4_from_m15(
            bars_by_open, opened_at_local=local - timedelta(hours=4)
        )
        if (
            reference is not None
            and candle2 is not None
            and candle2.closed_at == bar.opened_at
        ):
            reason = "INCOMPLETE_SOURCE_DAY"
            source_days = _latest_complete_source_days(
                bars_by_open, before_local=local
            )
            if len(source_days) == 2:
                current_day, previous_day = source_days
                side = resolve_bias(
                    previous_day=previous_day, current_day=current_day
                )
                reason = "BIAS_UNRESOLVED"
                if side is not None:
                    state, c2_side = _c2_state(reference, candle2)
                    reason = state
                    if state == "C2_ONE_SIDE_SWEEP_CLOSE_INSIDE":
                        reason = "C2_SIDE_BIAS_MISMATCH"
                        if c2_side is side:
                            source_window = _window_bars(
                                bars_by_open,
                                opened_at=candle2.opened_at,
                                closed_at=candle2.closed_at,
                            )
                            reason = "C2_M15_WINDOW_INCOMPLETE"
                            if source_window is not None:
                                important = (
                                    reference.low
                                    if side is DemoTradingSetupSide.LONG
                                    else reference.high
                                )
                                ps = protected_swings_in_candle2(
                                    source_window,
                                    side=side,
                                    important_level=important,
                                )
                                reason = "NO_PROTECTED_SWING"
                                if ps:
                                    reason = "MULTIPLE_PROTECTED_SWINGS"
                                    if len(ps) == 1:
                                        candidate = _candidate_from_components(
                                            symbol=symbol,
                                            decision_at=bar.opened_at,
                                            entry_anchor_hour=local.hour,
                                            reference=reference,
                                            candle2=candle2,
                                            side=side,
                                            protected=ps[0],
                                            entry_bar=bar,
                                        )
                                        reason = (
                                            "MECHANICAL_CANDIDATE"
                                            if candidate is not None
                                            else "INVALID_RISK_GEOMETRY"
                                        )

        if reason not in REASON_AUTHORITY:
            raise AssertionError(f"noncanonical first failure: {reason}")
        decision_iso = bar.opened_at.isoformat()
        rows.append({
            "event_id": _event_id(symbol, decision_iso),
            "market": symbol,
            "ny_date": local.date().isoformat(),
            "anchor_ny_hour": local.hour,
            "as_of": decision_iso,
            "ltf_profile": "M15_STANDARD",
            "source_family": "positional-entry-narrow-B01",
            "first_failure": reason,
            "first_failure_authority": REASON_AUTHORITY[reason],
            "candidate_created": reason == "MECHANICAL_CANDIDATE",
            "causal_evidence_ref": fingerprint,
            "future_trade_outcome_present": False,
        })

    summary = summarize_rows(rows)
    return {
        "schema": SCHEMA,
        "market": symbol,
        "evidence_fingerprint": fingerprint,
        "checked_at": checked_at.isoformat(),
        "software_sha": software_sha,
        "source_run_id": SOURCE_RUN_ID,
        "source_head": SOURCE_HEAD,
        "ltf_profile": "M15_STANDARD",
        "summary": summary,
        "events": rows,
    }


def to_json(path: Path) -> str:
    return json.dumps(evaluate(path), sort_keys=True, separators=(",", ":"))
