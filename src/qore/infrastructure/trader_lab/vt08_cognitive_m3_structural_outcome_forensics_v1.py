"""Outcome forensics for source-known M3 structural states."""
from __future__ import annotations

import json
from collections import defaultdict
from decimal import Decimal
from pathlib import Path
from typing import Final

from qore.infrastructure.trader_lab.vt08_cognitive_core_allocation_frontier_v1 import (
    _alignment,
    _band,
)
from qore.infrastructure.trader_lab.vt08_cognitive_expansion_5m_backtest_v1 import (
    ExpansionTrade,
    metrics,
    model_trade,
)
from qore.infrastructure.trader_lab.vt08_cognitive_latest_ps_core_stack_frontier_v1 import (
    _candidate_rows,
)
from qore.infrastructure.trader_lab.vt08_cognitive_latest_ps_density_recovery_v1 import (
    _ltf_window,
    _profile_bars,
)
from qore.infrastructure.traders.contracts import DemoTradingSetupSide
from qore.infrastructure.traders.vt08_b01_r3_8 import (
    protected_swings_in_candle2,
)

SCHEMA: Final = "qore.trader_lab.vt08_cognitive_m3_structural_outcome_forensics.v1"
PROFILE: Final = "M3_FRACTAL"
AXES: Final = (
    "anchor",
    "side",
    "c2_body_alignment",
    "c2_range_regime",
    "entry_reference_half",
    "c2_close_recovery",
    "c2_body_strength",
    "ps_cardinality",
    "ps_age",
    "risk_ref_band",
    "reference_body_alignment",
)


def _with_side(side: DemoTradingSetupSide, open_: Decimal, close: Decimal) -> str:
    if close == open_:
        return "DOJI"
    bullish = close > open_
    aligned = bullish if side is DemoTradingSetupSide.LONG else not bullish
    return "WITH_SIDE" if aligned else "AGAINST_SIDE"


def _features(candidate: object, *, ps_count: int) -> dict[str, str]:
    side = candidate.side
    reference = candidate.reference_h4
    c2 = candidate.candle2
    entry = candidate.setup.entry_price
    risk = abs(entry - candidate.setup.invalidation_price)
    reference_range = reference.high - reference.low
    c2_range = c2.high - c2.low
    if reference_range <= 0 or c2_range <= 0 or risk <= 0:
        raise ValueError("structural forensics requires positive geometry")

    eq = (reference.high + reference.low) / Decimal("2")
    favorable_half = (
        entry <= eq
        if side is DemoTradingSetupSide.LONG
        else entry >= eq
    )
    recovery = (
        (c2.close - c2.low) / c2_range
        if side is DemoTradingSetupSide.LONG
        else (c2.high - c2.close) / c2_range
    )
    body_fraction = abs(c2.close - c2.open) / c2_range
    age_minutes = Decimal(
        str((candidate.decision_at - candidate.protected_swing.confirmed_at).total_seconds())
    ) / Decimal("60")

    return {
        "anchor": str(candidate.entry_anchor_hour),
        "side": side.value,
        "c2_body_alignment": _with_side(side, c2.open, c2.close),
        "c2_range_regime": (
            "EXPANDED_OR_EQUAL" if c2_range >= reference_range else "CONTRACTED"
        ),
        "entry_reference_half": (
            "FAVORABLE_HALF" if favorable_half else "UNFAVORABLE_HALF"
        ),
        "c2_close_recovery": (
            "ABOVE_HALF_RECOVERY" if recovery >= Decimal("0.50") else "BELOW_HALF_RECOVERY"
        ),
        "c2_body_strength": (
            "BODY_MAJORITY" if body_fraction >= Decimal("0.50") else "BODY_MINORITY"
        ),
        "ps_cardinality": "MULTIPLE" if ps_count > 1 else "SINGLE",
        "ps_age": "FRESH" if age_minutes <= Decimal("60") else "MATURE",
        "risk_ref_band": _band(
            risk / reference_range,
            low=Decimal("0.25"),
            high=Decimal("0.75"),
        ),
        "reference_body_alignment": _alignment(candidate),
    }


def _state_summary(rows: tuple[ExpansionTrade, ...]) -> dict[str, object]:
    if not rows:
        return {"sample_size": 0}
    return metrics(rows)


def evaluate(base_path: Path, *, m3_path: Path) -> dict[str, object]:
    candidates, bars_by_open, symbol, checked_at, software_sha, _span_days = (
        _candidate_rows(base_path, profile=PROFILE, m3_path=m3_path)
    )
    m15 = tuple(bars_by_open[key] for key in sorted(bars_by_open))
    m3, _minutes = _profile_bars(
        profile=PROFILE,
        base_path=base_path,
        m3_path=m3_path,
        symbol=symbol,
        m15=m15,
    )
    m3_by_open = {bar.opened_at: bar for bar in m3}

    rows: list[tuple[ExpansionTrade, dict[str, str]]] = []
    for candidate in candidates:
        trade = model_trade(candidate, bars_by_open=bars_by_open)
        if trade is None:
            continue
        ltf = _ltf_window(
            profile=PROFILE,
            bars_by_open=m3_by_open,
            opened_at=candidate.candle2.opened_at,
            closed_at=candidate.candle2.closed_at,
        )
        if ltf is None:
            raise ValueError("M3 forensic window missing")
        important_level = (
            candidate.reference_h4.low
            if candidate.side is DemoTradingSetupSide.LONG
            else candidate.reference_h4.high
        )
        swings = protected_swings_in_candle2(
            ltf,
            side=candidate.side,
            important_level=important_level,
        )
        if not swings:
            raise AssertionError("retained M3 candidate lost Protected Swing identity")
        rows.append((trade, _features(candidate, ps_count=len(swings))))

    ordered = tuple(rows)
    n = len(ordered)
    bounds = (0, n // 3, (2 * n) // 3, n)

    axes: dict[str, object] = {}
    for axis in AXES:
        states: dict[str, list[tuple[int, ExpansionTrade]]] = defaultdict(list)
        for index, (trade, features) in enumerate(ordered):
            states[features[axis]].append((index, trade))

        axis_payload: dict[str, object] = {}
        for state, indexed in sorted(states.items()):
            all_trades = tuple(trade for _, trade in indexed)
            blocks = []
            for block in range(3):
                lo, hi = bounds[block], bounds[block + 1]
                selected = tuple(
                    trade for index, trade in indexed if lo <= index < hi
                )
                block_payload = _state_summary(selected)
                block_payload["block"] = block + 1
                blocks.append(block_payload)
            axis_payload[state] = {
                "overall": _state_summary(all_trades),
                "chronological_blocks": blocks,
            }
        axes[axis] = axis_payload

    return {
        "schema": SCHEMA,
        "market": symbol,
        "profile": PROFILE,
        "checked_at": checked_at.isoformat(),
        "software_sha": software_sha,
        "trade_count": n,
        "overall": metrics(tuple(trade for trade, _features_row in ordered)),
        "axes": axes,
        "governance": {
            "diagnostics_only": True,
            "runtime_rule_created": False,
            "features_known_before_decision": True,
            "market_deleted": False,
            "anchor_deleted": False,
            "side_deleted": False,
            "fresh_validation_required_for_any_rule": True,
            "live_authorized": False,
        },
    }


def to_json(base_path: Path, *, m3_path: Path) -> str:
    return json.dumps(
        evaluate(base_path, m3_path=m3_path),
        sort_keys=True,
        separators=(",", ":"),
    )
