"""Ledger-level provenance for the V3 -> Step-4 trade delta.

Compares frozen V3 2Y raw ledgers with Step-4 CISD-OR-M5-ALIGNED raw ledgers.
The comparison is keyed by the causal closeback opportunity, not by outcome.

Categories:
- ADDED: Step 4 has a trade for a closeback with no V3 trade.
- LOST: V3 has a trade for a closeback with no Step-4 trade.
- PRESERVED_SAME_MSS: both trade the closeback from the same M3 confirmation.
- REPLACED_EARLIER_MSS: both trade the closeback but Step 4 uses a different,
  earlier M3 confirmation.

MAX3 is then reapplied independently to both frozen raw ledgers.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from dataclasses import asdict
from decimal import Decimal
from pathlib import Path
from typing import Any

from qore.infrastructure.trader_lab import (
    capitalizer_owner_h1_m3_m1_causal_reversal_1y_v3 as v3,
)

IDENTITY = "QORE_CAPITALIZER_V3_STEP4_TRADE_DELTA_PROVENANCE_2Y_V1"
EXPECTED_V3_RAW = 475
EXPECTED_STEP4_RAW = 495
EXPECTED_V3_MAX3 = 474
EXPECTED_STEP4_MAX3 = 494


def _load_v3(root: Path) -> tuple[v3.V3Trade, ...]:
    paths = sorted(root.rglob("capitalizer-*-v3-frozen-replay-2y-v1-trades.jsonl"))
    if len(paths) != 9:
        raise ValueError(f"expected 9 V3 ledgers, got {len(paths)}")
    rows: list[v3.V3Trade] = []
    for path in paths:
        with path.open(encoding="utf-8") as handle:
            for line in handle:
                if line.strip():
                    rows.append(v3.V3Trade(**json.loads(line)))
    return tuple(rows)


def _load_step4(root: Path) -> tuple[tuple[v3.V3Trade, str], ...]:
    paths = sorted(
        root.rglob("capitalizer-*-v3-cisd-or-m5-aligned-2y-v1-trades.jsonl")
    )
    if len(paths) != 9:
        raise ValueError(f"expected 9 Step-4 ledgers, got {len(paths)}")
    rows: list[tuple[v3.V3Trade, str]] = []
    for path in paths:
        with path.open(encoding="utf-8") as handle:
            for line in handle:
                if not line.strip():
                    continue
                raw = json.loads(line)
                if not isinstance(raw, dict):
                    raise ValueError("Step-4 trade row must be object")
                route = str(raw["m3_confirmation_route"])
                clean = {
                    key: value
                    for key, value in raw.items()
                    if key != "m3_confirmation_route"
                }
                rows.append((v3.V3Trade(**clean), route))
    return tuple(rows)


def _key(trade: v3.V3Trade) -> tuple[str, str, str, str, str]:
    return (
        trade.symbol,
        trade.session,
        trade.operating_date,
        trade.side,
        trade.m5_closeback_at,
    )


def _metrics(trades: tuple[v3.V3Trade, ...]) -> dict[str, Any] | None:
    value = v3._metrics(trades)
    return None if value is None else asdict(value)


def _r_sum(trades: tuple[v3.V3Trade, ...]) -> str:
    return str(
        sum(
            (Decimal(item.realized_gross_r) for item in trades),
            Decimal("0"),
        )
    )


def build_report(
    v3_root: Path,
    step4_root: Path,
) -> dict[str, Any]:
    baseline = _load_v3(v3_root)
    step4_rows = _load_step4(step4_root)
    step4 = tuple(item for item, _ in step4_rows)
    route_by_key = {_key(item): route for item, route in step4_rows}

    base_by_key = {_key(item): item for item in baseline}
    step4_by_key = {_key(item): item for item in step4}
    if len(base_by_key) != len(baseline):
        raise ValueError("V3 raw ledger has duplicate closeback opportunity keys")
    if len(step4_by_key) != len(step4):
        raise ValueError("Step-4 raw ledger has duplicate closeback opportunity keys")

    base_keys = set(base_by_key)
    step4_keys = set(step4_by_key)
    added_keys = step4_keys - base_keys
    lost_keys = base_keys - step4_keys
    common_keys = base_keys & step4_keys

    preserved: list[v3.V3Trade] = []
    replaced: list[v3.V3Trade] = []
    replaced_routes: Counter[str] = Counter()
    for key in sorted(common_keys):
        base = base_by_key[key]
        new = step4_by_key[key]
        if base.m3_mss_at == new.m3_mss_at:
            preserved.append(new)
        else:
            if not new.m3_mss_at < base.m3_mss_at:
                raise AssertionError("Step-4 replacement must be earlier than V3 MSS")
            replaced.append(new)
            replaced_routes[route_by_key[key]] += 1

    added = tuple(step4_by_key[key] for key in sorted(added_keys))
    lost = tuple(base_by_key[key] for key in sorted(lost_keys))
    preserved_tuple = tuple(preserved)
    replaced_tuple = tuple(replaced)

    added_routes = Counter(route_by_key[key] for key in added_keys)

    base_max3 = v3._portfolio_max3(baseline)
    step4_max3 = v3._portfolio_max3(step4)
    base_max3_keys = {_key(item) for item in base_max3}
    step4_max3_keys = {_key(item) for item in step4_max3}
    max3_added = step4_max3_keys - base_max3_keys
    max3_lost = base_max3_keys - step4_max3_keys
    max3_common = base_max3_keys & step4_max3_keys
    max3_replaced = {
        key
        for key in max3_common
        if base_by_key[key].m3_mss_at != step4_by_key[key].m3_mss_at
    }

    per_session: dict[str, Counter[str]] = {}
    for key in added_keys:
        session = key[1]
        per_session.setdefault(session, Counter())["ADDED"] += 1
    for key in lost_keys:
        session = key[1]
        per_session.setdefault(session, Counter())["LOST"] += 1
    for key in common_keys:
        session = key[1]
        name = (
            "PRESERVED_SAME_MSS"
            if base_by_key[key].m3_mss_at == step4_by_key[key].m3_mss_at
            else "REPLACED_EARLIER_MSS"
        )
        per_session.setdefault(session, Counter())[name] += 1

    per_market: dict[str, Counter[str]] = {}
    for key in added_keys:
        per_market.setdefault(key[0], Counter())["ADDED"] += 1
    for key in lost_keys:
        per_market.setdefault(key[0], Counter())["LOST"] += 1
    for key in common_keys:
        name = (
            "PRESERVED_SAME_MSS"
            if base_by_key[key].m3_mss_at == step4_by_key[key].m3_mss_at
            else "REPLACED_EARLIER_MSS"
        )
        per_market.setdefault(key[0], Counter())[name] += 1

    return {
        "identity": IDENTITY,
        "v3_raw_trades": len(baseline),
        "step4_raw_trades": len(step4),
        "v3_raw_control_reproduced": len(baseline) == EXPECTED_V3_RAW,
        "step4_raw_control_reproduced": len(step4) == EXPECTED_STEP4_RAW,
        "raw_added_opportunities": len(added_keys),
        "raw_lost_opportunities": len(lost_keys),
        "raw_preserved_same_mss": len(preserved_tuple),
        "raw_replaced_earlier_mss": len(replaced_tuple),
        "raw_delta_reconciled": (
            len(step4) - len(baseline)
            == len(added_keys) - len(lost_keys)
        ),
        "added_routes": dict(sorted(added_routes.items())),
        "replaced_routes": dict(sorted(replaced_routes.items())),
        "added_metrics": _metrics(added),
        "added_total_r": _r_sum(added),
        "lost_metrics": _metrics(lost),
        "lost_total_r": _r_sum(lost),
        "replaced_step4_metrics": _metrics(replaced_tuple),
        "replaced_step4_total_r": _r_sum(replaced_tuple),
        "v3_max3_trades": len(base_max3),
        "step4_max3_trades": len(step4_max3),
        "v3_max3_control_reproduced": len(base_max3) == EXPECTED_V3_MAX3,
        "step4_max3_control_reproduced": len(step4_max3) == EXPECTED_STEP4_MAX3,
        "max3_added_opportunities": len(max3_added),
        "max3_lost_opportunities": len(max3_lost),
        "max3_common_opportunities": len(max3_common),
        "max3_replaced_earlier_mss": len(max3_replaced),
        "max3_delta_reconciled": (
            len(step4_max3) - len(base_max3)
            == len(max3_added) - len(max3_lost)
        ),
        "per_session": {
            key: dict(value) for key, value in sorted(per_session.items())
        },
        "per_market": {
            key: dict(value) for key, value in sorted(per_market.items())
        },
        "outcome_used_for_admission": False,
        "strategy_mutated": False,
        "diagnostic_only": True,
        "economic_candidate": False,
    }


def write_report(report: dict[str, Any], output: Path) -> None:
    output.mkdir(parents=True, exist_ok=True)
    path = output / "capitalizer-v3-step4-trade-delta-provenance-2y-v1.json"
    path.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("v3_root", type=Path)
    parser.add_argument("step4_root", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    report = build_report(args.v3_root, args.step4_root)
    write_report(report, args.output)
    print(json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    main()
