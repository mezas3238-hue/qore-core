"""Fresh backward temporal validation for VT08 Core Stack DEV V1."""
from __future__ import annotations

import json
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import Final

from qore.infrastructure.trader_lab.vt08_cognitive_core_stack_dev_v1 import (
    CoreStackTrade,
    stack_rows,
)
from qore.infrastructure.trader_lab.vt08_cognitive_expansion_5m_backtest_v1 import (
    load_market_evidence,
    metrics,
)
from qore.infrastructure.trader_lab.vt08_cognitive_expansion_5m_v1 import (
    EXPANSION_MARKETS,
    program_fingerprint,
)

SCHEMA: Final = "qore.trader_lab.vt08_cognitive_core_stack_fresh_holdout.v1"
CONSUMED_BOUNDARY: Final = datetime(2024, 8, 25, 21, 0, tzinfo=UTC)
MIN_FRESH_TRADES: Final = 20
MIN_CORE_STACK_PF: Final = Decimal("1.00")


def _fresh_rows(path: Path) -> tuple[CoreStackTrade, ...]:
    _, symbol, _, _, _ = load_market_evidence(path)
    if symbol not in EXPANSION_MARKETS:
        raise ValueError("fresh holdout market outside frozen 5M universe")
    rows = stack_rows(path)
    fresh = tuple(
        row
        for row in rows
        if row.baseline.signal_at < CONSUMED_BOUNDARY
        and row.baseline.exited_at < CONSUMED_BOUNDARY
    )
    if any(
        row.baseline.signal_at >= CONSUMED_BOUNDARY
        or row.baseline.exited_at >= CONSUMED_BOUNDARY
        for row in fresh
    ):
        raise AssertionError("fresh holdout overlaps consumed boundary")
    return fresh


def _decimal_metric(payload: dict[str, object], key: str) -> Decimal | None:
    raw = payload[key]
    if raw is None:
        return None
    return Decimal(str(raw))


def evaluate_fresh_market(path: Path) -> dict[str, object]:
    fingerprint, symbol, checked_at, software_sha, bars = load_market_evidence(path)
    rows = _fresh_rows(path)
    baseline = metrics(tuple(row.baseline for row in rows))
    stack = metrics(tuple(row.as_trade() for row in rows))

    sample = int(stack["sample_size"])
    baseline_pf = _decimal_metric(baseline, "profit_factor")
    stack_pf = _decimal_metric(stack, "profit_factor")
    stack_total = _decimal_metric(stack, "total_r")
    baseline_dd = _decimal_metric(baseline, "max_drawdown_r")
    stack_dd = _decimal_metric(stack, "max_drawdown_r")

    sufficient_sample = sample >= MIN_FRESH_TRADES
    positive_pf = stack_pf is not None and stack_pf > MIN_CORE_STACK_PF
    positive_total = stack_total is not None and stack_total > 0
    pf_improves = (
        stack_pf is not None
        and baseline_pf is not None
        and stack_pf > baseline_pf
    )
    dd_improves = (
        stack_dd is not None
        and baseline_dd is not None
        and stack_dd < baseline_dd
    )

    gates = {
        "sufficient_sample": sufficient_sample,
        "core_stack_pf_gt_1": positive_pf,
        "core_stack_total_r_gt_0": positive_total,
        "core_stack_pf_gt_baseline": pf_improves,
        "core_stack_dd_lt_baseline": dd_improves,
    }
    if not sufficient_sample:
        decision = "INCONCLUSIVE_SAMPLE"
    elif all(gates.values()):
        decision = "FRESH_SCREEN_PASS"
    else:
        decision = "FALSIFIED_FOR_THIS_STACK_V1"

    fresh_signals = tuple(row.baseline.signal_at for row in rows)
    first_m15 = min(bar.opened_at for bar in bars)
    last_m15 = max(bar.closed_at for bar in bars)
    return {
        "schema": SCHEMA,
        "program_fingerprint": program_fingerprint(),
        "market": symbol,
        "fresh_holdout": True,
        "consumed_boundary": CONSUMED_BOUNDARY.isoformat(),
        "evidence": {
            "account_fingerprint": fingerprint,
            "checked_at": checked_at.isoformat(),
            "software_sha": software_sha,
            "first_m15": first_m15.isoformat(),
            "last_m15": last_m15.isoformat(),
            "fresh_first_signal": (
                None if not fresh_signals else min(fresh_signals).isoformat()
            ),
            "fresh_last_signal": (
                None if not fresh_signals else max(fresh_signals).isoformat()
            ),
        },
        "baseline": baseline,
        "core_stack": stack,
        "gates": gates,
        "decision": decision,
        "governance": {
            "candidate_changed": False,
            "fresh_rows_before_consumed_boundary_only": True,
            "trade_count_changed": False,
            "market_filtering_authorized": False,
            "anchor_filtering_authorized": False,
            "side_filtering_authorized": False,
            "fresh_result_may_retune_candidate": False,
            "fresh_screen_is_final_certification": False,
            "demo_eligible": False,
            "live_authorized": False,
            "production_authorized": False,
            "real_capital_authorized": False,
        },
    }


def to_json(path: Path) -> str:
    return json.dumps(
        evaluate_fresh_market(path),
        sort_keys=True,
        separators=(",", ":"),
    )
