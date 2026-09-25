"""Attribution-only forensics isolating CIBO aggressive protection delta.

Compares the exact VT08 Core Stack against the exact VT08 structural-bank arm
on identical admitted signals. The difference isolates the incremental economic
effect of the aggressive stop ratchets without changing signal identity.

This is diagnostics-only consumed evidence. It cannot create a runtime filter.
"""
from __future__ import annotations

import json
from collections import defaultdict
from dataclasses import dataclass
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
from qore.infrastructure.trader_lab.vt08_cognitive_structural_bank_frontier_v1 import (
    StructuralBankTrade,
    structural_rows,
)

SCHEMA: Final = "qore.trader_lab.vt08_cognitive_protection_attribution_forensics.v1"
FORENSIC_MARKETS: Final = ("CADJPY", "NZDUSD")
AXES: Final = (
    "anchor",
    "side",
    "risk_ref_band",
    "c2_body_band",
    "protected_swing_age_band",
    "reference_body_alignment",
)


@dataclass(frozen=True, slots=True)
class ProtectionAttributionRow:
    stack: CoreStackTrade
    bank_only: StructuralBankTrade
    causal: CausalTradeRow

    @property
    def delta_r(self) -> Decimal:
        return self.stack.managed_r - self.bank_only.structural_r

    @property
    def classification(self) -> str:
        if self.delta_r > 0:
            return "PROTECTION_BENEFICIAL"
        if self.delta_r < 0:
            return "PROTECTION_HARMFUL"
        return "PROTECTION_NEUTRAL"


def attribution_rows(path: Path) -> tuple[ProtectionAttributionRow, ...]:
    stack = stack_rows(path)
    bank = structural_rows(path)
    causal = causal_rows(path)
    if not stack:
        raise ValueError("protection attribution requires Core Stack rows")
    market = stack[0].baseline.symbol
    if market not in FORENSIC_MARKETS:
        raise ValueError("protection attribution market outside frozen forensics")

    bank_map = {row.baseline.signal_at: row for row in bank}
    causal_map = {row.trade.signal_at: row for row in causal}
    result: list[ProtectionAttributionRow] = []
    for row in stack:
        signal = row.baseline.signal_at
        bank_row = bank_map.get(signal)
        causal_row = causal_map.get(signal)
        if bank_row is None or causal_row is None:
            raise AssertionError("protection attribution identity mismatch")
        result.append(
            ProtectionAttributionRow(
                stack=row,
                bank_only=bank_row,
                causal=causal_row,
            )
        )
    if len(result) != len(bank) or len(result) != len(causal):
        raise AssertionError("protection attribution cardinality drift")
    return tuple(result)


def _summary(rows: tuple[ProtectionAttributionRow, ...]) -> dict[str, object]:
    values = tuple(row.delta_r for row in rows)
    beneficial = tuple(row for row in rows if row.delta_r > 0)
    harmful = tuple(row for row in rows if row.delta_r < 0)
    neutral = tuple(row for row in rows if row.delta_r == 0)
    activated = tuple(row for row in rows if row.stack.protected_stop_used)
    positive = sum((value for value in values if value > 0), Decimal(0))
    negative = sum((value for value in values if value < 0), Decimal(0))
    total = sum(values, Decimal(0))
    return {
        "sample_size": len(rows),
        "protection_activated_count": len(activated),
        "beneficial_count": len(beneficial),
        "harmful_count": len(harmful),
        "neutral_count": len(neutral),
        "gross_saved_r": format(positive, "f"),
        "gross_clipped_r": format(negative, "f"),
        "net_protection_delta_r": format(total, "f"),
        "mean_protection_delta_r": (
            "0" if not rows else format(total / Decimal(len(rows)), "f")
        ),
    }


def evaluate(path: Path) -> dict[str, object]:
    rows = attribution_rows(path)
    market = rows[0].stack.baseline.symbol

    n = len(rows)
    bounds = (0, n // 3, (2 * n) // 3, n)
    thirds = []
    for index in range(3):
        selected = rows[bounds[index] : bounds[index + 1]]
        payload = _summary(selected)
        payload["block"] = index + 1
        payload["start_signal_at"] = selected[0].stack.baseline.signal_at.isoformat()
        payload["end_signal_at"] = selected[-1].stack.baseline.signal_at.isoformat()
        thirds.append(payload)

    by_axis: dict[str, object] = {}
    for axis in AXES:
        buckets: dict[str, list[ProtectionAttributionRow]] = defaultdict(list)
        for row in rows:
            buckets[row.causal.state(axis)].append(row)
        by_axis[axis] = {
            state: _summary(tuple(bucket))
            for state, bucket in sorted(buckets.items())
        }

    by_classification: dict[str, list[ProtectionAttributionRow]] = defaultdict(list)
    for row in rows:
        by_classification[row.classification].append(row)

    return {
        "schema": SCHEMA,
        "market": market,
        "evidence_status": "CONSUMED_ATTRIBUTION_FORENSICS",
        "diagnostics_only": True,
        "comparison": "CORE_STACK_MINUS_STRUCTURAL_BANK_ONLY",
        "overall": _summary(rows),
        "chronological_thirds": thirds,
        "by_causal_axis": by_axis,
        "by_classification": {
            label: _summary(tuple(bucket))
            for label, bucket in sorted(by_classification.items())
        },
        "governance": {
            "signal_identity_changed": False,
            "entry_changed": False,
            "banking_arm_changed": False,
            "runtime_filter_created": False,
            "adaptive_policy_created": False,
            "post_hoc_state_may_authorize_rule": False,
            "next_policy_requires_pre_economic_freeze": True,
            "fresh_validation_required": True,
            "live_authorized": False,
        },
    }


def to_json(path: Path) -> str:
    return json.dumps(evaluate(path), sort_keys=True, separators=(",", ":"))
