"""Stop-only CIBO policy frontier on the high-density M3 VT08 population."""
from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path
from typing import Final

from qore.infrastructure.trader_lab.vt08_cognitive_cibo_stop_protection_v1 import (
    replay_policy_trade,
)
from qore.infrastructure.trader_lab.vt08_cognitive_expansion_5m_backtest_v1 import (
    ExpansionTrade,
    metrics,
)
from qore.infrastructure.trader_lab.vt08_cognitive_latest_ps_core_stack_frontier_v1 import (
    _candidate_rows,
)
from qore.infrastructure.trader_lab.vt08_index_c2_r1_cibo_stop_protection import (
    STOP_POLICIES,
)

SCHEMA: Final = "qore.trader_lab.vt08_cognitive_m3_cibo_stop_only_frontier.v1"
PROFILE: Final = "M3_FRACTAL"
TRAIN_FRACTION: Final = Decimal("0.70")


def _summary(rows: tuple[ExpansionTrade, ...]) -> dict[str, object]:
    return metrics(rows)


def evaluate(base_path: Path, *, m3_path: Path) -> dict[str, object]:
    candidates, bars_by_open, symbol, checked_at, software_sha, _span_days = (
        _candidate_rows(base_path, profile=PROFILE, m3_path=m3_path)
    )
    results: dict[str, tuple[ExpansionTrade, ...]] = {}

    for policy in STOP_POLICIES:
        rows: list[ExpansionTrade] = []
        for candidate in candidates:
            item = replay_policy_trade(
                candidate,
                bars_by_open=bars_by_open,
                policy=policy,
            )
            if item is not None:
                rows.append(item.as_trade())
        results[policy.name] = tuple(rows)

    counts = {len(rows) for rows in results.values()}
    if len(counts) != 1:
        raise AssertionError("CIBO policy changed M3 trade cardinality")

    count = next(iter(counts), 0)
    split = int(Decimal(count) * TRAIN_FRACTION)
    split = max(1, min(split, count - 1)) if count >= 2 else 0

    payload: dict[str, object] = {}
    for policy in STOP_POLICIES:
        rows = results[policy.name]
        payload[policy.name] = {
            "ratchets": [
                {"trigger_r": format(trigger, "f"), "lock_r": format(lock, "f")}
                for trigger, lock in policy.ratchets
            ],
            "full_consumed": _summary(rows),
            "train_consumed": _summary(rows[:split]),
            "temporal_consumed": _summary(rows[split:]),
        }

    return {
        "schema": SCHEMA,
        "market": symbol,
        "profile": PROFILE,
        "checked_at": checked_at.isoformat(),
        "software_sha": software_sha,
        "trade_count": count,
        "split": {
            "train_fraction": format(TRAIN_FRACTION, "f"),
            "train_count": split,
            "temporal_count": count - split,
        },
        "policies": payload,
        "governance": {
            "consumed_development": True,
            "pre_existing_policies_only": True,
            "new_threshold_search": False,
            "structural_banking": False,
            "trade_filtering": False,
            "market_specific_policy_selection": False,
            "capital_weighting": False,
            "live_authorized": False,
        },
    }


def to_json(base_path: Path, *, m3_path: Path) -> str:
    return json.dumps(
        evaluate(base_path, m3_path=m3_path),
        sort_keys=True,
        separators=(",", ":"),
    )
