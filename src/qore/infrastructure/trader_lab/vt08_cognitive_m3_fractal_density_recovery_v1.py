"""Independent M3_FRACTAL density-recovery replay for VT08 5M."""
from __future__ import annotations

import json
from collections import Counter, defaultdict
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Final, cast
from zoneinfo import ZoneInfo

from qore.infrastructure.trader_lab.vt08_cognitive_expansion_5m_backtest_v1 import (
    ExpansionTrade,
    _array,
    _object,
    _parse_bar,
    load_market_evidence,
    metrics,
    run_market_backtest,
)
from qore.infrastructure.trader_lab.vt08_cognitive_expansion_5m_evaluator_v1 import (
    Vt08ExpansionCandidate,
    _candle2_reversal_side,
    _latest_complete_source_days,
)
from qore.infrastructure.trader_lab.vt08_cognitive_expansion_5m_v1 import (
    ANCHORS_NY,
    EXPANSION_MARKETS,
    program_fingerprint,
)
from qore.infrastructure.trader_lab.vt08_cognitive_m5_fractal_density_recovery_v1 import (
    _candidate,
    _model_trade_m15_outer,
)
from qore.infrastructure.traders.contracts import DemoTradingSetupSide
from qore.infrastructure.traders.vt08_b01_r3_8 import (
    Vt08B01Bar,
    protected_swings_in_candle2,
    resolve_bias,
    source_h4_from_m15,
)

SCHEMA: Final = "qore.trader_lab.vt08_cognitive_m3_fractal_density_recovery.v1"
PROFILE: Final = "M3_FRACTAL"
_NY = ZoneInfo("America/New_York")


def _load_m3(path: Path, *, expected_symbol: str) -> tuple[Vt08B01Bar, ...]:
    try:
        decoded: object = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ValueError("cannot read M3 evidence") from error
    payload = _object(decoded, name="M3 evidence")
    if payload.get("environment") != "demo":
        raise ValueError("M3 evidence must be DEMO")
    if payload.get("read_only") is not True or payload.get("account_is_live") is not False:
        raise ValueError("M3 evidence must be read-only and non-LIVE")
    symbol_payload = _object(payload.get("symbol"), name="M3 symbol")
    if symbol_payload.get("symbol_name") != expected_symbol:
        raise ValueError("M3 symbol does not match immutable base evidence")
    if payload.get("period") != "M3":
        raise ValueError("M3 evidence period drifted")

    bars = tuple(_parse_bar(item) for item in _array(payload.get("bars"), name="M3 bars"))
    if not bars:
        raise ValueError("M3 evidence is empty")
    if bars != tuple(sorted(bars, key=lambda item: item.opened_at)):
        raise ValueError("M3 evidence must be chronological")
    return bars


def _window(
    bars_by_open: dict[datetime, Vt08B01Bar],
    *,
    opened_at: datetime,
    closed_at: datetime,
) -> tuple[Vt08B01Bar, ...] | None:
    start = opened_at.astimezone(UTC)
    end = closed_at.astimezone(UTC)
    cursor = start
    retained: list[Vt08B01Bar] = []
    while cursor < end:
        bar = bars_by_open.get(cursor)
        if bar is None or bar.closed_at != cursor + timedelta(minutes=3):
            return None
        retained.append(bar)
        cursor += timedelta(minutes=3)
    return tuple(retained) if cursor == end else None


def evaluate(base_path: Path, m3_path: Path) -> dict[str, object]:
    _fingerprint, symbol, checked_at, software_sha, m15 = load_market_evidence(base_path)
    if symbol not in EXPANSION_MARKETS:
        raise ValueError("M3 profile market outside frozen 5M universe")
    m3 = _load_m3(m3_path, expected_symbol=symbol)

    m15_by_open = {bar.opened_at: bar for bar in m15}
    m3_by_open = {bar.opened_at: bar for bar in m3}

    candidates_by_day: dict[date, list[Vt08ExpansionCandidate]] = defaultdict(list)
    failures: Counter[str] = Counter()

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
        if _candle2_reversal_side(reference, candle2) is not side:
            failures["C2_REVERSAL_MISMATCH"] += 1
            continue

        c2_m3 = _window(
            m3_by_open,
            opened_at=candle2.opened_at,
            closed_at=candle2.closed_at,
        )
        if c2_m3 is None:
            failures["M3_C2_WINDOW_INCOMPLETE"] += 1
            continue

        important_level = (
            reference.low if side is DemoTradingSetupSide.LONG else reference.high
        )
        swings = protected_swings_in_candle2(
            c2_m3,
            side=side,
            important_level=important_level,
        )
        if not swings:
            failures["M3_NO_PROTECTED_SWING"] += 1
            continue
        if len(swings) != 1:
            failures["M3_MULTIPLE_PROTECTED_SWINGS"] += 1
            continue

        candidate = _candidate(
            symbol=symbol,
            decision_at=entry_bar.opened_at,
            anchor=local.hour,
            reference=reference,
            candle2=candle2,
            side=side,
            protected=swings[0],
            entry_bar=entry_bar,
        )
        if candidate is None:
            failures["INVALID_RISK_GEOMETRY"] += 1
            continue
        candidates_by_day[local.date()].append(candidate)

    terminal: list[ExpansionTrade] = []
    multi_days = 0
    candidates_lost = 0
    incomplete_exit = 0
    for day in sorted(candidates_by_day):
        rows = candidates_by_day[day]
        if len(rows) != 1:
            multi_days += 1
            candidates_lost += len(rows)
            continue
        trade = _model_trade_m15_outer(rows[0], m15_by_open=m15_by_open)
        if trade is None:
            incomplete_exit += 1
            continue
        terminal.append(trade)

    ordered = tuple(sorted(terminal, key=lambda item: item.signal_at))
    baseline_report = run_market_backtest(base_path)
    baseline_economics = cast(dict[str, object], baseline_report["economics"])
    baseline_count = baseline_economics["sample_size"]
    if not isinstance(baseline_count, int):
        raise ValueError("baseline sample_size must be int")

    coverage_days = Decimal(
        str(
            (
                max(bar.closed_at for bar in m15)
                - min(bar.opened_at for bar in m15)
            ).total_seconds()
        )
    ) / Decimal("86400")
    annualized = Decimal(len(ordered)) * Decimal("365") / coverage_days
    mechanical = sum(len(rows) for rows in candidates_by_day.values())
    by_anchor = {
        str(anchor): metrics(
            tuple(item for item in ordered if item.anchor_hour_ny == anchor)
        )
        for anchor in ANCHORS_NY
    }

    return {
        "schema": SCHEMA,
        "profile": PROFILE,
        "market": symbol,
        "evidence_status": "CONSUMED_DEVELOPMENT",
        "checked_at": checked_at.isoformat(),
        "software_sha": software_sha,
        "m15_baseline": baseline_economics,
        "m3_profile": metrics(ordered),
        "density": {
            "m15_terminal_trades": baseline_count,
            "m3_mechanical_candidates": mechanical,
            "m3_terminal_trades": len(ordered),
            "m3_annualized_trades": format(annualized, "f"),
            "m3_two_year_equivalent_trades": format(annualized * Decimal("2"), "f"),
            "candidate_delta_vs_m15_terminal": mechanical - baseline_count,
            "terminal_delta_vs_m15": len(ordered) - baseline_count,
            "multi_candidate_days": multi_days,
            "candidates_lost_to_daily_cardinality": candidates_lost,
            "incomplete_exit_windows": incomplete_exit,
        },
        "first_failure_counts": dict(failures.most_common()),
        "by_anchor_ny": by_anchor,
        "governance": {
            "source_authorized_independent_ltf_profile": True,
            "m15_m3_cross_confirmation": False,
            "m5_m3_cross_confirmation": False,
            "completed_c2_h4_changed": False,
            "daily_bias_changed": False,
            "entry_changed": False,
            "target_changed": False,
            "daily_cardinality_changed": False,
            "freshness_claimed": False,
            "live_authorized": False,
        },
    }


def to_json(base_path: Path, m3_path: Path) -> str:
    return json.dumps(
        evaluate(base_path, m3_path),
        sort_keys=True,
        separators=(",", ":"),
    )
