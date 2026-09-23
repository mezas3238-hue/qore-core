"""Diagnostics-only mechanism forensics for CADJPY/NZDUSD Core Stack failures."""
from __future__ import annotations

import json
from collections import defaultdict
from decimal import Decimal
from pathlib import Path
from typing import Final

from qore.infrastructure.trader_lab.vt08_cognitive_core_allocation_frontier_v1 import (
    CausalTradeRow,
    causal_rows,
)
from qore.infrastructure.trader_lab.vt08_cognitive_core_stack_dev_v1 import (
    CoreStackTrade,
    stack_rows,
)
from qore.infrastructure.trader_lab.vt08_cognitive_expansion_5m_backtest_v1 import (
    metrics,
)

SCHEMA: Final = "qore.trader_lab.vt08_cognitive_core_stack_failure_forensics.v1"
FORENSIC_MARKETS: Final = ("CADJPY", "NZDUSD")
AXES: Final = (
    "anchor",
    "side",
    "risk_ref_band",
    "c2_body_band",
    "protected_swing_age_band",
    "reference_body_alignment",
)


def _metrics(rows: tuple[CoreStackTrade, ...]) -> dict[str, object]:
    return metrics(tuple(row.as_trade() for row in rows))


def _baseline_metrics(rows: tuple[CoreStackTrade, ...]) -> dict[str, object]:
    return metrics(tuple(row.baseline for row in rows))


def _delta(
    baseline: dict[str, object],
    managed: dict[str, object],
) -> dict[str, object]:
    def d(payload: dict[str, object], key: str) -> Decimal:
        raw = payload[key]
        return Decimal(0) if raw is None else Decimal(str(raw))

    baseline_pf = baseline["profit_factor"]
    managed_pf = managed["profit_factor"]
    return {
        "total_r_delta": format(
            d(managed, "total_r") - d(baseline, "total_r"),
            "f",
        ),
        "dd_delta": format(
            d(managed, "max_drawdown_r") - d(baseline, "max_drawdown_r"),
            "f",
        ),
        "pf_delta": (
            None
            if baseline_pf is None or managed_pf is None
            else format(
                Decimal(str(managed_pf)) - Decimal(str(baseline_pf)),
                "f",
            )
        ),
    }


def _bucket(
    pairs: tuple[tuple[CoreStackTrade, CausalTradeRow], ...],
) -> dict[str, object]:
    stack = tuple(left for left, _right in pairs)
    baseline = _baseline_metrics(stack)
    managed = _metrics(stack)
    return {
        "sample_size": len(stack),
        "baseline": baseline,
        "core_stack": managed,
        "delta": _delta(baseline, managed),
        "mechanism_counts": {
            "eq_banked": sum(item.eq_banked for item in stack),
            "destination_banked": sum(item.destination_banked for item in stack),
            "protected_stop_used": sum(item.protected_stop_used for item in stack),
        },
    }


def evaluate(path: Path) -> dict[str, object]:
    stack = stack_rows(path)
    causal = causal_rows(path)
    if not stack:
        raise ValueError("failure forensics requires Core Stack rows")
    market = stack[0].baseline.symbol
    if market not in FORENSIC_MARKETS:
        raise ValueError("forensics market is not a robustness failure target")

    causal_by_signal = {
        item.trade.signal_at: item
        for item in causal
    }
    pairs: list[tuple[CoreStackTrade, CausalTradeRow]] = []
    for item in stack:
        matched = causal_by_signal.get(item.baseline.signal_at)
        if matched is None:
            raise AssertionError("Core Stack row lacks causal state row")
        pairs.append((item, matched))
    joined = tuple(pairs)
    if len(joined) != len(causal):
        raise AssertionError("causal/Core Stack cardinality drift")

    thirds: list[dict[str, object]] = []
    n = len(joined)
    bounds = (0, n // 3, (2 * n) // 3, n)
    for index in range(3):
        selected = joined[bounds[index] : bounds[index + 1]]
        item = _bucket(selected)
        item["block"] = index + 1
        item["start_signal_at"] = selected[0][0].baseline.signal_at.isoformat()
        item["end_signal_at"] = selected[-1][0].baseline.signal_at.isoformat()
        thirds.append(item)

    by_axis: dict[str, object] = {}
    for axis in AXES:
        buckets: dict[str, list[tuple[CoreStackTrade, CausalTradeRow]]] = defaultdict(list)
        for pair in joined:
            buckets[pair[1].state(axis)].append(pair)
        by_axis[axis] = {
            state: _bucket(tuple(rows))
            for state, rows in sorted(buckets.items())
        }

    return {
        "schema": SCHEMA,
        "market": market,
        "evidence_status": "CONSUMED_FORENSICS",
        "diagnostics_only": True,
        "overall": _bucket(joined),
        "chronological_thirds": thirds,
        "by_causal_axis": by_axis,
        "governance": {
            "runtime_filter_created": False,
            "market_filter_created": False,
            "anchor_filter_created": False,
            "side_filter_created": False,
            "threshold_search": False,
            "forensics_may_promote_rule": False,
            "next_hypothesis_requires_pre_economic_freeze": True,
            "live_authorized": False,
        },
    }


def to_json(path: Path) -> str:
    return json.dumps(evaluate(path), sort_keys=True, separators=(",", ":"))
