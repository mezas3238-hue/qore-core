"""Source-authorized M5_FRACTAL density-recovery experiment for VT08 5M.

M15 and M5 are independent profiles. This module does not combine their
confirmations. It preserves the same H4/daily-bias/completed-C2 admission and
substitutes M5 only for the lower-timeframe CISD/Protected-Swing construction.
"""
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
from qore.infrastructure.traders.contracts import (
    DemoTradingError,
    DemoTradingSetupSide,
    DemoTradingSetupSpec,
)
from qore.infrastructure.traders.vt08_b01_r3_8 import (
    Vt08B01Bar,
    methodology_fingerprint,
    protected_swings_in_candle2,
    resolve_bias,
    source_h4_from_m15,
)

SCHEMA: Final = "qore.trader_lab.vt08_cognitive_m5_fractal_density_recovery.v1"
PROFILE: Final = "M5_FRACTAL"
_NY = ZoneInfo("America/New_York")


def _load_m5(path: Path) -> tuple[Vt08B01Bar, ...]:
    try:
        decoded: object = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ValueError("cannot read M5 evidence") from error
    payload = _object(decoded, name="market evidence")
    periods = _object(payload.get("periods"), name="periods")
    bars = tuple(_parse_bar(item) for item in _array(periods.get("M5"), name="M5"))
    if not bars:
        raise ValueError("M5 evidence is empty")
    if bars != tuple(sorted(bars, key=lambda item: item.opened_at)):
        raise ValueError("M5 evidence must be chronological")
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
        if bar is None or bar.closed_at != cursor + timedelta(minutes=5):
            return None
        retained.append(bar)
        cursor += timedelta(minutes=5)
    return tuple(retained) if cursor == end else None


def _candidate(
    *,
    symbol: str,
    decision_at: datetime,
    anchor: int,
    reference: Vt08B01Bar,
    candle2: Vt08B01Bar,
    side: DemoTradingSetupSide,
    protected,
    entry_bar: Vt08B01Bar,
) -> Vt08ExpansionCandidate | None:
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
            entry_reason=(
                "vt08-cognitive-m5-fractal-v1;"
                "independent-source-authorized-ltf-profile;"
                "completed-c2-h4;"
                "m5-cisd-protected-swing"
            ),
        )
    except DemoTradingError:
        return None
    return Vt08ExpansionCandidate(
        symbol=symbol,
        side=side,
        decision_at=decision_at,
        entry_anchor_hour=anchor,
        reference_h4=reference,
        candle2=candle2,
        protected_swing=protected,
        setup=setup,
        vt08_methodology_fingerprint=methodology_fingerprint(),
        expansion_program_fingerprint=program_fingerprint(),
    )


def _model_trade_m15_outer(
    candidate: Vt08ExpansionCandidate,
    *,
    m15_by_open: dict[datetime, Vt08B01Bar],
) -> ExpansionTrade | None:
    start = candidate.decision_at.astimezone(UTC)
    end = (start.astimezone(_NY) + timedelta(hours=4)).astimezone(UTC)
    rows: list[Vt08B01Bar] = []
    cursor = start
    while cursor < end:
        bar = m15_by_open.get(cursor)
        if bar is None or bar.closed_at != cursor + timedelta(minutes=15):
            return None
        rows.append(bar)
        cursor += timedelta(minutes=15)
    if cursor != end or not rows:
        return None

    setup = candidate.setup
    exit_price = rows[-1].close
    exited_at = rows[-1].closed_at
    reason = "h4_containment_exit"
    for bar in rows:
        if bar.low <= setup.invalidation_price <= bar.high:
            exit_price = setup.invalidation_price
            exited_at = bar.closed_at
            reason = "stop"
            break
        if bar.low <= setup.take_profit_price <= bar.high:
            exit_price = setup.take_profit_price
            exited_at = bar.closed_at
            reason = "target"
            break

    risk = (
        setup.entry_price - setup.invalidation_price
        if candidate.side is DemoTradingSetupSide.LONG
        else setup.invalidation_price - setup.entry_price
    )
    if candidate.side is DemoTradingSetupSide.LONG:
        result_r = (exit_price - setup.entry_price) / risk
    else:
        result_r = (setup.entry_price - exit_price) / risk
    return ExpansionTrade(
        symbol=candidate.symbol,
        signal_at=start,
        exited_at=exited_at,
        anchor_hour_ny=candidate.entry_anchor_hour,
        side=candidate.side,
        entry=setup.entry_price,
        stop=setup.invalidation_price,
        target=setup.take_profit_price,
        exit_price=exit_price,
        exit_reason=reason,
        r_multiple=result_r,
    )


def evaluate(path: Path) -> dict[str, object]:
    _fingerprint, symbol, checked_at, software_sha, m15 = load_market_evidence(path)
    if symbol not in EXPANSION_MARKETS:
        raise ValueError("M5 profile market outside frozen 5M universe")
    m5 = _load_m5(path)

    m15_by_open = {bar.opened_at: bar for bar in m15}
    m5_by_open = {bar.opened_at: bar for bar in m5}

    candidates_by_day: dict[date, list[Vt08ExpansionCandidate]] = defaultdict(list)
    failures: Counter[str] = Counter()
    by_anchor_candidates: Counter[int] = Counter()

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

        c2_m5 = _window(
            m5_by_open,
            opened_at=candle2.opened_at,
            closed_at=candle2.closed_at,
        )
        if c2_m5 is None:
            failures["M5_C2_WINDOW_INCOMPLETE"] += 1
            continue

        important_level = (
            reference.low if side is DemoTradingSetupSide.LONG else reference.high
        )
        swings = protected_swings_in_candle2(
            c2_m5,
            side=side,
            important_level=important_level,
        )
        if not swings:
            failures["M5_NO_PROTECTED_SWING"] += 1
            continue
        if len(swings) != 1:
            failures["M5_MULTIPLE_PROTECTED_SWINGS"] += 1
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
        by_anchor_candidates[local.hour] += 1

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
    baseline_report = cast(
        dict[str, object],
        __import__(
            "qore.infrastructure.trader_lab.vt08_cognitive_expansion_5m_backtest_v1",
            fromlist=["run_market_backtest"],
        ).run_market_backtest(path),
    )
    baseline_economics = cast(dict[str, object], baseline_report["economics"])

    coverage_days = Decimal(
        str((max(bar.closed_at for bar in m15) - min(bar.opened_at for bar in m15)).total_seconds())
    ) / Decimal("86400")
    annualized = Decimal(len(ordered)) * Decimal("365") / coverage_days
    by_anchor = {
        str(anchor): metrics(
            tuple(item for item in ordered if item.anchor_hour_ny == anchor)
        )
        for anchor in ANCHORS_NY
    }

    mechanical = sum(len(rows) for rows in candidates_by_day.values())
    baseline_count_raw = baseline_economics["sample_size"]
    if not isinstance(baseline_count_raw, int):
        raise ValueError("baseline sample_size must be int")

    return {
        "schema": SCHEMA,
        "profile": PROFILE,
        "market": symbol,
        "evidence_status": "CONSUMED_DEVELOPMENT",
        "checked_at": checked_at.isoformat(),
        "software_sha": software_sha,
        "m15_baseline": baseline_economics,
        "m5_profile": metrics(ordered),
        "density": {
            "m15_terminal_trades": baseline_count_raw,
            "m5_mechanical_candidates": mechanical,
            "m5_terminal_trades": len(ordered),
            "m5_annualized_trades": format(annualized, "f"),
            "m5_two_year_equivalent_trades": format(annualized * Decimal("2"), "f"),
            "candidate_delta_vs_m15_terminal": mechanical - baseline_count_raw,
            "terminal_delta_vs_m15": len(ordered) - baseline_count_raw,
            "multi_candidate_days": multi_days,
            "candidates_lost_to_daily_cardinality": candidates_lost,
            "incomplete_exit_windows": incomplete_exit,
        },
        "first_failure_counts": dict(failures.most_common()),
        "by_anchor_ny": by_anchor,
        "governance": {
            "source_authorized_independent_ltf_profile": True,
            "m15_m5_cross_confirmation": False,
            "completed_c2_h4_changed": False,
            "daily_bias_changed": False,
            "entry_changed": False,
            "target_changed": False,
            "daily_cardinality_changed": False,
            "freshness_claimed": False,
            "live_authorized": False,
        },
    }


def to_json(path: Path) -> str:
    return json.dumps(evaluate(path), sort_keys=True, separators=(",", ":"))
