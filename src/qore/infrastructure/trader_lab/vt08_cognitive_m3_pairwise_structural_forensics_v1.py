"""Pairwise structural forensics for high-density M3 VT08."""
from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path
from typing import Final

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
from qore.infrastructure.trader_lab.vt08_cognitive_m3_structural_outcome_forensics_v1 import (
    PROFILE,
    _features,
)
from qore.infrastructure.traders.contracts import DemoTradingSetupSide
from qore.infrastructure.traders.vt08_b01_r3_8 import protected_swings_in_candle2

SCHEMA: Final = "qore.trader_lab.vt08_cognitive_m3_pairwise_structural_forensics.v1"
PAIRS: Final = (
    ("c2_body_alignment", "c2_range_regime"),
    ("c2_body_alignment", "entry_reference_half"),
    ("c2_close_recovery", "c2_body_strength"),
    ("ps_cardinality", "ps_age"),
    ("risk_ref_band", "c2_range_regime"),
    ("reference_body_alignment", "c2_body_alignment"),
    ("anchor", "side"),
    ("entry_reference_half", "ps_cardinality"),
    ("c2_close_recovery", "ps_cardinality"),
    ("risk_ref_band", "ps_cardinality"),
)


def _summary(rows: tuple[ExpansionTrade, ...]) -> dict[str, object]:
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
            raise ValueError("M3 pairwise forensic window missing")
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
            raise AssertionError("retained candidate lost M3 Protected Swing identity")
        rows.append((trade, _features(candidate, ps_count=len(swings))))

    ordered = tuple(rows)
    n = len(ordered)
    bounds = (0, n // 3, (2 * n) // 3, n)
    payload: dict[str, object] = {}

    for left, right in PAIRS:
        buckets: dict[str, list[tuple[int, ExpansionTrade]]] = defaultdict(list)
        for index, (trade, features) in enumerate(ordered):
            key = f"{features[left]}|{features[right]}"
            buckets[key].append((index, trade))

        states: dict[str, object] = {}
        for key, indexed in sorted(buckets.items()):
            all_trades = tuple(trade for _, trade in indexed)
            blocks = []
            for block in range(3):
                lo, hi = bounds[block], bounds[block + 1]
                selected = tuple(
                    trade for index, trade in indexed if lo <= index < hi
                )
                item = _summary(selected)
                item["block"] = block + 1
                blocks.append(item)
            states[key] = {
                "overall": _summary(all_trades),
                "chronological_blocks": blocks,
            }
        payload[f"{left}__X__{right}"] = states

    return {
        "schema": SCHEMA,
        "market": symbol,
        "profile": PROFILE,
        "checked_at": checked_at.isoformat(),
        "software_sha": software_sha,
        "trade_count": n,
        "pairs": payload,
        "governance": {
            "diagnostics_only": True,
            "runtime_rule_created": False,
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
