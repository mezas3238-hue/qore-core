"""Diagnostics-only failure forensics for EURJPY 5Y Core Stack validation.

Compares baseline, structural-bank-only and frozen Core Stack on identical
signals, with emphasis on the first weak 365-day block. No runtime rule is
created here.
"""
from __future__ import annotations

import json
from collections import defaultdict
from datetime import timedelta
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
    load_market_evidence,
    metrics,
)
from qore.infrastructure.trader_lab.vt08_cognitive_structural_bank_frontier_v1 import (
    StructuralBankTrade,
    structural_rows,
)

SCHEMA: Final = "qore.trader_lab.vt08_eurjpy_5y_failure_forensics.v1"
MARKET: Final = "EURJPY"
AXES: Final = (
    "anchor",
    "side",
    "risk_ref_band",
    "c2_body_band",
    "protected_swing_age_band",
    "reference_body_alignment",
)


def _d(payload: dict[str, object], key: str) -> Decimal:
    raw = payload[key]
    return Decimal(0) if raw is None else Decimal(str(raw))


def _summary(
    stack: tuple[CoreStackTrade, ...],
    bank: tuple[StructuralBankTrade, ...],
) -> dict[str, object]:
    baseline_metrics = metrics(tuple(row.baseline for row in stack))
    bank_metrics = metrics(tuple(row.as_trade() for row in bank))
    stack_metrics = metrics(tuple(row.as_trade() for row in stack))
    protection_delta = sum(
        (
            stack_row.managed_r - bank_row.structural_r
            for stack_row, bank_row in zip(stack, bank, strict=True)
        ),
        Decimal(0),
    )
    return {
        "sample_size": len(stack),
        "baseline": baseline_metrics,
        "bank_only": bank_metrics,
        "core_stack": stack_metrics,
        "bank_delta_vs_baseline_r": format(
            _d(bank_metrics, "total_r") - _d(baseline_metrics, "total_r"),
            "f",
        ),
        "core_delta_vs_bank_r": format(protection_delta, "f"),
        "core_delta_vs_baseline_r": format(
            _d(stack_metrics, "total_r") - _d(baseline_metrics, "total_r"),
            "f",
        ),
        "mechanism_counts": {
            "eq_banked": sum(row.eq_banked for row in stack),
            "destination_banked": sum(row.destination_banked for row in stack),
            "protected_stop_used": sum(row.protected_stop_used for row in stack),
        },
    }


def evaluate(path: Path) -> dict[str, object]:
    _fingerprint, symbol, _checked_at, _software_sha, bars = load_market_evidence(path)
    if symbol != MARKET:
        raise ValueError("EURJPY 5Y forensics requires EURJPY")
    stack = stack_rows(path)
    bank = structural_rows(path)
    causal = causal_rows(path)
    if not stack or stack[0].baseline.symbol != MARKET:
        raise ValueError("EURJPY 5Y forensics emitted no EURJPY rows")
    bank_map = {row.baseline.signal_at: row for row in bank}
    causal_map = {row.trade.signal_at: row for row in causal}

    joined: list[tuple[CoreStackTrade, StructuralBankTrade, CausalTradeRow]] = []
    for row in stack:
        signal = row.baseline.signal_at
        bank_row = bank_map.get(signal)
        causal_row = causal_map.get(signal)
        if bank_row is None or causal_row is None:
            raise AssertionError("EURJPY 5Y forensic identity drift")
        joined.append((row, bank_row, causal_row))
    if len(joined) != len(bank) or len(joined) != len(causal):
        raise AssertionError("EURJPY 5Y forensic cardinality drift")

    coverage_start = min(bar.opened_at for bar in bars)
    blocks: list[dict[str, object]] = []
    block_axis: dict[str, object] = {}
    for index in range(5):
        start = coverage_start + timedelta(days=365 * index)
        end = start + timedelta(days=365)
        selected = tuple(
            item
            for item in joined
            if start <= item[0].baseline.signal_at < end
        )
        stack_rows_selected = tuple(item[0] for item in selected)
        bank_rows_selected = tuple(item[1] for item in selected)
        payload = _summary(stack_rows_selected, bank_rows_selected)
        payload["block"] = index + 1
        payload["start"] = start.isoformat()
        payload["end_exclusive"] = end.isoformat()
        blocks.append(payload)

        per_axis: dict[str, object] = {}
        for axis in AXES:
            axis_buckets: dict[
                str,
                list[tuple[CoreStackTrade, StructuralBankTrade, CausalTradeRow]],
            ] = defaultdict(list)
            for item in selected:
                axis_buckets[item[2].state(axis)].append(item)
            per_axis[axis] = {
                state: _summary(
                    tuple(item[0] for item in rows),
                    tuple(item[1] for item in rows),
                )
                for state, rows in sorted(axis_buckets.items())
            }
        block_axis[str(index + 1)] = per_axis

    weak_end = coverage_start + timedelta(days=365)
    weak = tuple(
        item
        for item in joined
        if coverage_start <= item[0].baseline.signal_at < weak_end
    )

    by_axis: dict[str, object] = {}
    for axis in AXES:
        buckets: dict[
            str,
            list[tuple[CoreStackTrade, StructuralBankTrade, CausalTradeRow]],
        ] = defaultdict(list)
        for item in weak:
            buckets[item[2].state(axis)].append(item)
        by_axis[axis] = {
            state: _summary(
                tuple(item[0] for item in rows),
                tuple(item[1] for item in rows),
            )
            for state, rows in sorted(buckets.items())
        }

    return {
        "schema": SCHEMA,
        "market": MARKET,
        "evidence_status": "CONSUMED_5Y_FORENSICS",
        "diagnostics_only": True,
        "overall": _summary(stack, bank),
        "five_365d_blocks": blocks,
        "five_blocks_by_causal_axis": block_axis,
        "weak_block_1_by_causal_axis": by_axis,
        "governance": {
            "runtime_filter_created": False,
            "adaptive_rule_created": False,
            "weak_period_excluded": False,
            "post_hoc_state_may_authorize_rule": False,
            "new_hypothesis_requires_pre_economic_freeze": True,
            "new_hypothesis_requires_older_unseen_validation": True,
            "live_authorized": False,
        },
    }


def to_json(path: Path) -> str:
    return json.dumps(evaluate(path), sort_keys=True, separators=(",", ":"))
