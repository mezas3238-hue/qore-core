"""Fresh older-window evaluator for frozen Adaptive Protection V2 hypotheses."""
from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path
from typing import Final

from qore.infrastructure.trader_lab.vt08_cognitive_adaptive_protection_v2 import (
    FRESH_BOUNDARY,
    MARKETS,
    AdaptiveProtectionTrade,
    adaptive_rows,
)
from qore.infrastructure.trader_lab.vt08_cognitive_core_stack_dev_v1 import (
    CoreStackTrade,
    stack_rows,
)
from qore.infrastructure.trader_lab.vt08_cognitive_expansion_5m_backtest_v1 import (
    metrics,
)

SCHEMA: Final = "qore.trader_lab.vt08_cognitive_adaptive_protection_v2_fresh.v1"
MIN_FRESH_TRADES: Final = 30
MIN_ADAPTIVE_PF: Final = Decimal("1.20")


def _metric_decimal(payload: dict[str, object], key: str) -> Decimal | None:
    raw = payload[key]
    if raw is None:
        return None
    return Decimal(str(raw))


def _fresh_adaptive(
    rows: tuple[AdaptiveProtectionTrade, ...],
) -> tuple[AdaptiveProtectionTrade, ...]:
    return tuple(
        row
        for row in rows
        if row.baseline.signal_at < FRESH_BOUNDARY
        and row.baseline.exited_at < FRESH_BOUNDARY
    )


def _fresh_core(
    rows: tuple[CoreStackTrade, ...],
) -> tuple[CoreStackTrade, ...]:
    return tuple(
        row
        for row in rows
        if row.baseline.signal_at < FRESH_BOUNDARY
        and row.baseline.exited_at < FRESH_BOUNDARY
    )


def evaluate(path: Path) -> dict[str, object]:
    adaptive = _fresh_adaptive(adaptive_rows(path))
    core = _fresh_core(stack_rows(path))
    if not adaptive:
        raise ValueError("adaptive V2 fresh window emitted no terminal trades")
    market = adaptive[0].baseline.symbol
    if market not in MARKETS:
        raise ValueError("adaptive V2 fresh market outside frozen scope")

    adaptive_map = {row.baseline.signal_at: row for row in adaptive}
    core_map = {row.baseline.signal_at: row for row in core}
    if set(adaptive_map) != set(core_map):
        raise AssertionError("adaptive V2 changed fresh trade identity")

    ordered_signals = tuple(sorted(adaptive_map))
    adaptive_ordered = tuple(adaptive_map[item] for item in ordered_signals)
    core_ordered = tuple(core_map[item] for item in ordered_signals)

    adaptive_metrics = metrics(tuple(row.as_trade() for row in adaptive_ordered))
    core_metrics = metrics(tuple(row.as_trade() for row in core_ordered))
    adaptive_pf = _metric_decimal(adaptive_metrics, "profit_factor")
    core_pf = _metric_decimal(core_metrics, "profit_factor")
    adaptive_total = _metric_decimal(adaptive_metrics, "total_r")
    adaptive_dd = _metric_decimal(adaptive_metrics, "max_drawdown_r")
    core_dd = _metric_decimal(core_metrics, "max_drawdown_r")

    gates = {
        "sample_at_least_30": len(adaptive_ordered) >= MIN_FRESH_TRADES,
        "adaptive_pf_gt_1_20": (
            adaptive_pf is not None and adaptive_pf > MIN_ADAPTIVE_PF
        ),
        "adaptive_total_positive": (
            adaptive_total is not None and adaptive_total > 0
        ),
        "adaptive_pf_gt_core_stack": (
            adaptive_pf is not None
            and core_pf is not None
            and adaptive_pf > core_pf
        ),
        "adaptive_dd_not_worse_than_core_stack": (
            adaptive_dd is not None
            and core_dd is not None
            and adaptive_dd <= core_dd
        ),
        "trade_count_identical": len(adaptive_ordered) == len(core_ordered),
    }
    if len(adaptive_ordered) < MIN_FRESH_TRADES:
        decision = "INCONCLUSIVE_FRESH_SAMPLE"
    elif all(gates.values()):
        decision = "FRESH_MECHANISM_SCREEN_PASS"
    else:
        decision = "ADAPTIVE_PROTECTION_V2_FALSIFIED"

    return {
        "schema": SCHEMA,
        "market": market,
        "candidate": (
            "VT08_CADJPY_ADAPTIVE_PROTECTION_V2_A9_BANK_ONLY"
            if market == "CADJPY"
            else "VT08_NZDUSD_ADAPTIVE_PROTECTION_V2_LOW_RISKREF_BANK_ONLY"
        ),
        "fresh_boundary": FRESH_BOUNDARY.isoformat(),
        "fresh_evidence_only": True,
        "trade_count": len(adaptive_ordered),
        "core_stack_control": core_metrics,
        "adaptive_v2": adaptive_metrics,
        "policy_counts": {
            "off": sum(row.policy_name == "off" for row in adaptive_ordered),
            "aggressive": sum(
                row.policy_name == "aggressive"
                for row in adaptive_ordered
            ),
        },
        "gates": gates,
        "decision": decision,
        "governance": {
            "candidate_retuned_from_fresh_result": False,
            "trade_filtering": False,
            "trade_identity_changed": False,
            "live_authorized": False,
            "production_authorized": False,
            "real_capital_authorized": False,
        },
    }


def to_json(path: Path) -> str:
    return json.dumps(evaluate(path), sort_keys=True, separators=(",", ":"))
