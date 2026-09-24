"""Source-adjudicated latest-confirmed Protected Swing density experiment.

The selector never uses PnL. M15, M5 and M3 are evaluated as independent
profiles with the same H4 admission and replay lifecycle.
"""
from __future__ import annotations

import json
from collections import Counter, defaultdict
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Final, cast
from zoneinfo import ZoneInfo

from qore.infrastructure.trader_lab.vt08_cognitive_expansion_5m_backtest_v1 import (
    ExpansionTrade,
    load_market_evidence,
    metrics,
    run_market_backtest,
)
from qore.infrastructure.trader_lab.vt08_cognitive_expansion_5m_evaluator_v1 import (
    Vt08ExpansionCandidate,
    _candle2_reversal_side,
    _latest_complete_source_days,
    _window_bars,
)
from qore.infrastructure.trader_lab.vt08_cognitive_expansion_5m_v1 import (
    ANCHORS_NY,
    EXPANSION_MARKETS,
)
from qore.infrastructure.trader_lab.vt08_cognitive_m3_fractal_density_recovery_v1 import (
    _load_m3,
    _window as _window_m3,
)
from qore.infrastructure.trader_lab.vt08_cognitive_m5_fractal_density_recovery_v1 import (
    _candidate,
    _load_m5,
    _model_trade_m15_outer,
    _window as _window_m5,
)
from qore.infrastructure.traders.contracts import DemoTradingSetupSide
from qore.infrastructure.traders.vt08_b01_r3_8 import (
    Vt08B01Bar,
    Vt08B01ProtectedSwing,
    protected_swings_in_candle2,
    resolve_bias,
    source_h4_from_m15,
)

SCHEMA: Final = "qore.trader_lab.vt08_cognitive_latest_ps_density_recovery.v1"
SELECTOR_ID: Final = "LATEST_CONFIRMED_PROTECTED_SWING_V1"
PROFILES: Final = ("M15_STANDARD", "M5_FRACTAL", "M3_FRACTAL")
_NY = ZoneInfo("America/New_York")


def latest_confirmed_swing(
    swings: tuple[Vt08B01ProtectedSwing, ...],
) -> Vt08B01ProtectedSwing:
    if not swings:
        raise ValueError("latest PS selector requires at least one swing")
    ordered = tuple(
        sorted(
            swings,
            key=lambda item: (
                item.confirmed_at,
                item.opposing_series_opened_at,
                item.price,
            ),
        )
    )
    selected = ordered[-1]
    selected_identity = (
        selected.confirmed_at,
        selected.opposing_series_opened_at,
        selected.price,
    )
    if sum(
        (
            item.confirmed_at,
            item.opposing_series_opened_at,
            item.price,
        )
        == selected_identity
        for item in swings
    ) != 1:
        raise ValueError("latest PS identity remains ambiguous")
    return selected


def _profile_bars(
    *,
    profile: str,
    base_path: Path,
    m3_path: Path | None,
    symbol: str,
    m15: tuple[Vt08B01Bar, ...],
) -> tuple[tuple[Vt08B01Bar, ...], int]:
    if profile == "M15_STANDARD":
        return m15, 15
    if profile == "M5_FRACTAL":
        return _load_m5(base_path), 5
    if profile == "M3_FRACTAL":
        if m3_path is None:
            raise ValueError("M3 profile requires M3 evidence")
        return _load_m3(m3_path, expected_symbol=symbol), 3
    raise ValueError("unsupported independent LTF profile")


def _ltf_window(
    *,
    profile: str,
    bars_by_open: dict,
    opened_at,
    closed_at,
):
    if profile == "M15_STANDARD":
        return _window_bars(
            bars_by_open,
            opened_at=opened_at,
            closed_at=closed_at,
        )
    if profile == "M5_FRACTAL":
        return _window_m5(
            bars_by_open,
            opened_at=opened_at,
            closed_at=closed_at,
        )
    if profile == "M3_FRACTAL":
        return _window_m3(
            bars_by_open,
            opened_at=opened_at,
            closed_at=closed_at,
        )
    raise ValueError(profile)


def evaluate(
    base_path: Path,
    *,
    profile: str,
    m3_path: Path | None = None,
) -> dict[str, object]:
    if profile not in PROFILES:
        raise ValueError("profile outside frozen latest-PS experiment")
    _fingerprint, symbol, checked_at, software_sha, m15 = load_market_evidence(
        base_path
    )
    if symbol not in EXPANSION_MARKETS:
        raise ValueError("market outside frozen 5M universe")

    ltf, ltf_minutes = _profile_bars(
        profile=profile,
        base_path=base_path,
        m3_path=m3_path,
        symbol=symbol,
        m15=m15,
    )
    m15_by_open = {bar.opened_at: bar for bar in m15}
    ltf_by_open = {bar.opened_at: bar for bar in ltf}

    candidates_by_day: dict[date, list[Vt08ExpansionCandidate]] = defaultdict(list)
    failures: Counter[str] = Counter()
    swing_cardinality: Counter[int] = Counter()
    multi_ps_recovered = 0

    for entry_bar in m15:
        local = entry_bar.opened_at.astimezone(_NY)
        if local.minute != 0 or local.hour not in ANCHORS_NY:
            continue

        reference = source_h4_from_m15(
            m15_by_open,
            opened_at_local=local - __import__("datetime").timedelta(hours=8),
        )
        candle2 = source_h4_from_m15(
            m15_by_open,
            opened_at_local=local - __import__("datetime").timedelta(hours=4),
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

        rows = _ltf_window(
            profile=profile,
            bars_by_open=ltf_by_open,
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
        swing_cardinality[len(swings)] += 1
        if not swings:
            failures["NO_PROTECTED_SWING"] += 1
            continue

        try:
            selected = latest_confirmed_swing(swings)
        except ValueError:
            failures["LATEST_PS_IDENTITY_AMBIGUOUS"] += 1
            continue
        if len(swings) > 1:
            multi_ps_recovered += 1

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
        candidates_by_day[local.date()].append(candidate)

    terminal: list[ExpansionTrade] = []
    multi_days = 0
    candidates_lost = 0
    incomplete_exit = 0
    for day in sorted(candidates_by_day):
        candidates = candidates_by_day[day]
        if len(candidates) != 1:
            multi_days += 1
            candidates_lost += len(candidates)
            continue
        trade = _model_trade_m15_outer(
            candidates[0],
            m15_by_open=m15_by_open,
        )
        if trade is None:
            incomplete_exit += 1
            continue
        terminal.append(trade)

    ordered = tuple(sorted(terminal, key=lambda item: item.signal_at))
    baseline_report = run_market_backtest(base_path)
    baseline = cast(dict[str, object], baseline_report["economics"])
    baseline_count = baseline["sample_size"]
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
    mechanical = sum(len(items) for items in candidates_by_day.values())

    return {
        "schema": SCHEMA,
        "selector_id": SELECTOR_ID,
        "profile": profile,
        "ltf_minutes": ltf_minutes,
        "market": symbol,
        "evidence_status": "CONSUMED_DEVELOPMENT",
        "checked_at": checked_at.isoformat(),
        "software_sha": software_sha,
        "m15_exactly_one_baseline": baseline,
        "latest_ps_profile": metrics(ordered),
        "density": {
            "m15_exactly_one_terminal_trades": baseline_count,
            "latest_ps_mechanical_candidates": mechanical,
            "latest_ps_terminal_trades": len(ordered),
            "annualized_trades": format(annualized, "f"),
            "two_year_equivalent_trades": format(annualized * Decimal("2"), "f"),
            "terminal_delta_vs_m15_exactly_one": len(ordered) - baseline_count,
            "multi_ps_opportunities_recovered_pre_cardinality": multi_ps_recovered,
            "multi_candidate_days": multi_days,
            "candidates_lost_to_daily_cardinality": candidates_lost,
            "incomplete_exit_windows": incomplete_exit,
        },
        "swing_cardinality_counts": {
            str(key): value for key, value in sorted(swing_cardinality.items())
        },
        "first_failure_counts": dict(failures.most_common()),
        "by_anchor_ny": {
            str(anchor): metrics(
                tuple(item for item in ordered if item.anchor_hour_ny == anchor)
            )
            for anchor in ANCHORS_NY
        },
        "governance": {
            "selector_uses_terminal_pnl": False,
            "selector_uses_future_bar": False,
            "selector_uses_market_rank": False,
            "selector_uses_anchor_rank": False,
            "profiles_combined": False,
            "daily_bias_changed": False,
            "completed_c2_changed": False,
            "entry_changed": False,
            "target_changed": False,
            "daily_cardinality_changed": False,
            "freshness_claimed": False,
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
