"""Attribution frontier for high-density M3 VT08 management.

Compares raw, structural-bank-only, and frozen aggressive Core Stack mechanics
on exactly the same latest-PS M3 trade population.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Final

from qore.infrastructure.trader_lab.vt08_cognitive_core_stack_dev_v1 import (
    simulate_core_stack,
)
from qore.infrastructure.trader_lab.vt08_cognitive_expansion_5m_backtest_v1 import (
    ExpansionTrade,
    metrics,
)
from qore.infrastructure.trader_lab.vt08_cognitive_latest_ps_core_stack_frontier_v1 import (
    _candidate_rows,
)
from qore.infrastructure.trader_lab.vt08_cognitive_structural_bank_frontier_v1 import (
    simulate_structural_bank,
)

SCHEMA: Final = "qore.trader_lab.vt08_cognitive_m3_management_attribution_frontier.v1"
PROFILE: Final = "M3_FRACTAL"


def evaluate(base_path: Path, *, m3_path: Path) -> dict[str, object]:
    candidates, bars_by_open, symbol, checked_at, software_sha, _span_days = (
        _candidate_rows(base_path, profile=PROFILE, m3_path=m3_path)
    )

    raw: list[ExpansionTrade] = []
    bank: list[ExpansionTrade] = []
    aggressive: list[ExpansionTrade] = []

    for candidate in candidates:
        bank_item = simulate_structural_bank(candidate, bars_by_open=bars_by_open)
        aggressive_item = simulate_core_stack(candidate, bars_by_open=bars_by_open)
        if bank_item is None or aggressive_item is None:
            continue
        raw.append(bank_item.baseline)
        bank.append(bank_item.as_trade())
        aggressive.append(aggressive_item.as_trade())

    if not (len(raw) == len(bank) == len(aggressive)):
        raise AssertionError("management attribution changed trade cardinality")

    def identity(row: ExpansionTrade) -> tuple[object, ...]:
        return (
            row.symbol,
            row.signal_at,
            row.anchor_hour_ny,
            row.side,
            row.entry,
            row.stop,
            row.target,
        )

    if any(
        identity(a) != identity(b) or identity(a) != identity(c)
        for a, b, c in zip(raw, bank, aggressive, strict=True)
    ):
        raise AssertionError("management attribution changed frozen geometry")

    return {
        "schema": SCHEMA,
        "market": symbol,
        "profile": PROFILE,
        "checked_at": checked_at.isoformat(),
        "software_sha": software_sha,
        "evidence_status": "CONSUMED_DEVELOPMENT",
        "trade_count": len(raw),
        "raw_equal_risk": metrics(tuple(raw)),
        "bank_only": metrics(tuple(bank)),
        "core_aggressive": metrics(tuple(aggressive)),
        "governance": {
            "same_trade_population": True,
            "new_threshold_search": False,
            "trade_filtering": False,
            "capital_weighting": False,
            "market_filtering": False,
            "freshness_claimed": False,
            "live_authorized": False,
        },
    }


def to_json(base_path: Path, *, m3_path: Path) -> str:
    return json.dumps(
        evaluate(base_path, m3_path=m3_path),
        sort_keys=True,
        separators=(",", ":"),
    )
