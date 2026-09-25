"""Causal CAUTIOUS-state admission shield for high-density M3 VT08."""
from __future__ import annotations

import json
from collections import Counter
from decimal import Decimal
from pathlib import Path
from typing import Final

from qore.infrastructure.trader_lab.vt08_cognitive_core_allocation_frontier_v1 import (
    _causal_row,
    classify_context,
    fit_state_table,
)
from qore.infrastructure.trader_lab.vt08_cognitive_expansion_5m_backtest_v1 import (
    ExpansionTrade,
    metrics,
    model_trade,
)
from qore.infrastructure.trader_lab.vt08_cognitive_latest_ps_core_stack_frontier_v1 import (
    _candidate_rows,
)

SCHEMA: Final = "qore.trader_lab.vt08_cognitive_m3_cautious_state_shield.v1"
PROFILE: Final = "M3_FRACTAL"
TRAIN_FRACTION: Final = Decimal("0.70")
MIN_TEMPORAL_TRADES: Final = 30
MIN_RETENTION: Final = Decimal("0.70")
MIN_SHIELD_PF: Final = Decimal("1.20")


def _metric_decimal(payload: dict[str, object], key: str) -> Decimal | None:
    raw = payload[key]
    return None if raw is None else Decimal(str(raw))


def evaluate(base_path: Path, *, m3_path: Path) -> dict[str, object]:
    candidates, bars_by_open, symbol, checked_at, software_sha, _span_days = (
        _candidate_rows(base_path, profile=PROFILE, m3_path=m3_path)
    )

    paired = []
    for candidate in candidates:
        trade = model_trade(candidate, bars_by_open=bars_by_open)
        if trade is None:
            continue
        paired.append((candidate, trade, _causal_row(candidate, trade)))

    if len(paired) < 2:
        raise ValueError("M3 cognitive shield requires terminal trades")

    split = int(Decimal(len(paired)) * TRAIN_FRACTION)
    split = max(1, min(split, len(paired) - 1))
    train_rows = tuple(item[2] for item in paired[:split])
    temporal = tuple(paired[split:])
    table = fit_state_table(train_rows)

    baseline_trades = tuple(item[1] for item in temporal)
    retained: list[ExpansionTrade] = []
    context_counts: Counter[str] = Counter()
    vetoed = 0
    audit = []

    for candidate, trade, causal in temporal:
        context, score = classify_context(causal, table)
        context_counts[context] += 1
        admit = context != "CAUTIOUS"
        if admit:
            retained.append(trade)
        else:
            vetoed += 1
        audit.append(
            {
                "signal_at": trade.signal_at.isoformat(),
                "context": context,
                "score": score,
                "admitted": admit,
                "anchor": causal.anchor,
                "side": causal.side,
                "risk_ref_band": causal.risk_ref_band,
                "c2_body_band": causal.c2_body_band,
                "protected_swing_age_band": causal.protected_swing_age_band,
                "reference_body_alignment": causal.reference_body_alignment,
            }
        )

    baseline = metrics(baseline_trades)
    shield = metrics(tuple(retained))
    retention = Decimal(len(retained)) / Decimal(len(baseline_trades))
    baseline_pf = _metric_decimal(baseline, "profit_factor")
    shield_pf = _metric_decimal(shield, "profit_factor")
    shield_total = _metric_decimal(shield, "total_r")
    baseline_dd = _metric_decimal(baseline, "max_drawdown_r")
    shield_dd = _metric_decimal(shield, "max_drawdown_r")

    gates = {
        "temporal_baseline_sample_at_least_30": len(baseline_trades) >= MIN_TEMPORAL_TRADES,
        "retained_sample_at_least_30": len(retained) >= MIN_TEMPORAL_TRADES,
        "retention_at_least_70pct": retention >= MIN_RETENTION,
        "shield_pf_gt_1_20": shield_pf is not None and shield_pf > MIN_SHIELD_PF,
        "shield_pf_gt_baseline": (
            shield_pf is not None
            and baseline_pf is not None
            and shield_pf > baseline_pf
        ),
        "shield_total_positive": shield_total is not None and shield_total > 0,
        "shield_dd_not_worse": (
            shield_dd is not None
            and baseline_dd is not None
            and shield_dd <= baseline_dd
        ),
    }
    decision = (
        "TEMPORAL_CAUSAL_SHIELD_SCREEN_PASS"
        if all(gates.values())
        else "TEMPORAL_CAUSAL_SHIELD_SCREEN_FAIL"
    )

    return {
        "schema": SCHEMA,
        "market": symbol,
        "profile": PROFILE,
        "checked_at": checked_at.isoformat(),
        "software_sha": software_sha,
        "evidence_status": "CONSUMED_DEVELOPMENT",
        "split": {
            "train_fraction": format(TRAIN_FRACTION, "f"),
            "train_count": split,
            "temporal_count": len(temporal),
        },
        "state_table": [item.payload() for item in table],
        "temporal": {
            "baseline": baseline,
            "shield": shield,
            "retained_count": len(retained),
            "vetoed_cautious_count": vetoed,
            "retention_rate": format(retention, "f"),
            "context_counts": dict(sorted(context_counts.items())),
        },
        "gates": gates,
        "decision": decision,
        "audit": audit,
        "governance": {
            "fit_uses_train_terminal_pnl": True,
            "temporal_runtime_uses_terminal_pnl": False,
            "temporal_runtime_uses_future_bar": False,
            "market_deleted": False,
            "anchor_deleted": False,
            "side_deleted": False,
            "capital_weighting": False,
            "cibo_management_applied": False,
            "structural_banking_applied": False,
            "fresh_validation_required": True,
            "live_authorized": False,
        },
    }


def to_json(base_path: Path, *, m3_path: Path) -> str:
    return json.dumps(
        evaluate(base_path, m3_path=m3_path),
        sort_keys=True,
        separators=(",", ":"),
    )
