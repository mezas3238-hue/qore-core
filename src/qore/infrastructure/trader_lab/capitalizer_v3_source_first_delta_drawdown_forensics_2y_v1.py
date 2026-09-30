"""Ledger-level delta and drawdown forensics for V3 SOURCE_FIRST CISD 2Y.

Consumes only frozen V3 and SOURCE_FIRST raw trade ledgers, reapplies the unchanged
portfolio MAX3 independently, then explains:
- which causal closeback opportunities are added/lost/preserved/reconfirmed;
- which V3 MAX3 opportunities are displaced only by portfolio competition;
- which provenance categories create the SOURCE_FIRST maximum drawdown episode;
- exact category/session/market contribution inside that peak-to-trough interval.

Post-outcome diagnostic evidence only. It derives no admission rule.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from dataclasses import asdict
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

from qore.infrastructure.trader_lab import (
    capitalizer_owner_h1_m3_m1_causal_reversal_1y_v3 as v3,
)

IDENTITY = "QORE_CAPITALIZER_V3_SOURCE_FIRST_DELTA_DRAWDOWN_FORENSICS_2Y_V1"
EXPECTED_V3_RAW = 475
EXPECTED_SOURCE_FIRST_RAW = 1142
EXPECTED_V3_MAX3 = 474
EXPECTED_SOURCE_FIRST_MAX3 = 1118

ADDED = "SOURCE_FIRST_ADDED"
LOST = "SOURCE_FIRST_LOST"
PRESERVED = "PRESERVED_SAME_MSS"
REPLACED = "REPLACED_MSS"


def _load_v3(root: Path) -> tuple[v3.V3Trade, ...]:
    paths = sorted(root.rglob("capitalizer-*-v3-frozen-replay-2y-v1-trades.jsonl"))
    if len(paths) != 9:
        raise ValueError(f"delta forensics requires 9 V3 ledgers, got {len(paths)}")
    rows: list[v3.V3Trade] = []
    for path in paths:
        with path.open(encoding="utf-8") as handle:
            for line in handle:
                if line.strip():
                    rows.append(v3.V3Trade(**json.loads(line)))
    return tuple(rows)


def _load_source_first(root: Path) -> tuple[v3.V3Trade, ...]:
    paths = sorted(
        root.rglob("capitalizer-*-v3-source-first-cisd-2y-v1-trades.jsonl")
    )
    if len(paths) != 9:
        raise ValueError(
            f"delta forensics requires 9 SOURCE_FIRST ledgers, got {len(paths)}"
        )
    rows: list[v3.V3Trade] = []
    for path in paths:
        with path.open(encoding="utf-8") as handle:
            for line in handle:
                if line.strip():
                    rows.append(v3.V3Trade(**json.loads(line)))
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


def _sum_r(trades: tuple[v3.V3Trade, ...]) -> Decimal:
    return sum(
        (Decimal(item.realized_gross_r) for item in trades),
        Decimal("0"),
    )


def _drawdown_episode(
    trades: tuple[v3.V3Trade, ...],
) -> dict[str, Any]:
    ordered = tuple(
        sorted(
            trades,
            key=lambda item: (
                datetime.fromisoformat(item.exit_at),
                datetime.fromisoformat(item.entry_at),
                item.symbol,
            ),
        )
    )
    if not ordered:
        raise ValueError("drawdown episode requires trades")

    equity = Decimal("0")
    peak = Decimal("0")
    peak_index = -1
    peak_trade: v3.V3Trade | None = None
    max_dd = Decimal("0")
    max_peak = Decimal("0")
    max_peak_index = -1
    max_peak_trade: v3.V3Trade | None = None
    trough_index = 0
    trough_equity = Decimal("0")

    for index, trade in enumerate(ordered):
        equity += Decimal(trade.realized_gross_r)
        if equity > peak:
            peak = equity
            peak_index = index
            peak_trade = trade
        drawdown = peak - equity
        if drawdown > max_dd:
            max_dd = drawdown
            max_peak = peak
            max_peak_index = peak_index
            max_peak_trade = peak_trade
            trough_index = index
            trough_equity = equity

    episode = ordered[max_peak_index + 1 : trough_index + 1]
    if not episode:
        raise ValueError("maximum drawdown episode cannot be empty")
    return {
        "peak_equity_r": str(max_peak),
        "trough_equity_r": str(trough_equity),
        "drawdown_r": str(max_dd),
        "peak_exit_at": (
            None if max_peak_trade is None else max_peak_trade.exit_at
        ),
        "trough_exit_at": ordered[trough_index].exit_at,
        "first_episode_exit_at": episode[0].exit_at,
        "trades_in_episode": len(episode),
        "episode_total_r": str(_sum_r(episode)),
        "episode_trades": episode,
    }


def _cohort(
    trades: tuple[v3.V3Trade, ...],
) -> dict[str, Any]:
    return {
        "trades": len(trades),
        "metrics": _metrics(trades),
        "total_r": str(_sum_r(trades)),
    }


def build_report(
    v3_root: Path,
    source_first_root: Path,
) -> dict[str, Any]:
    baseline_raw = _load_v3(v3_root)
    source_raw = _load_source_first(source_first_root)
    if len(baseline_raw) != EXPECTED_V3_RAW:
        raise ValueError("V3 raw control mismatch")
    if len(source_raw) != EXPECTED_SOURCE_FIRST_RAW:
        raise ValueError("SOURCE_FIRST raw control mismatch")

    base_by_key = {_key(item): item for item in baseline_raw}
    source_by_key = {_key(item): item for item in source_raw}
    if len(base_by_key) != len(baseline_raw):
        raise ValueError("duplicate V3 closeback opportunity")
    if len(source_by_key) != len(source_raw):
        raise ValueError("duplicate SOURCE_FIRST closeback opportunity")

    base_keys = set(base_by_key)
    source_keys = set(source_by_key)
    added_keys = source_keys - base_keys
    lost_keys = base_keys - source_keys
    common_keys = base_keys & source_keys
    preserved_keys = {
        key
        for key in common_keys
        if base_by_key[key].m3_mss_at == source_by_key[key].m3_mss_at
    }
    replaced_keys = common_keys - preserved_keys

    provenance_by_key: dict[tuple[str, str, str, str, str], str] = {}
    for key in added_keys:
        provenance_by_key[key] = ADDED
    for key in lost_keys:
        provenance_by_key[key] = LOST
    for key in preserved_keys:
        provenance_by_key[key] = PRESERVED
    for key in replaced_keys:
        provenance_by_key[key] = REPLACED

    baseline_max3 = v3._portfolio_max3(baseline_raw)
    source_max3 = v3._portfolio_max3(source_raw)
    if len(baseline_max3) != EXPECTED_V3_MAX3:
        raise ValueError("V3 MAX3 control mismatch")
    if len(source_max3) != EXPECTED_SOURCE_FIRST_MAX3:
        raise ValueError("SOURCE_FIRST MAX3 control mismatch")

    base_max3_keys = {_key(item) for item in baseline_max3}
    source_max3_keys = {_key(item) for item in source_max3}
    selected_added_keys = source_max3_keys & added_keys
    selected_preserved_keys = source_max3_keys & preserved_keys
    selected_replaced_keys = source_max3_keys & replaced_keys

    baseline_displaced_keys = {
        key
        for key in base_max3_keys
        if key in source_keys and key not in source_max3_keys
    }
    baseline_semantic_lost_keys = base_max3_keys & lost_keys
    source_newly_selected_existing_keys = {
        key
        for key in source_max3_keys
        if key in base_keys and key not in base_max3_keys
    }

    source_provenance_counts = Counter(
        provenance_by_key[_key(item)] for item in source_max3
    )

    episode = _drawdown_episode(source_max3)
    episode_trades = tuple(episode.pop("episode_trades"))
    episode_provenance = Counter(
        provenance_by_key[_key(item)] for item in episode_trades
    )
    episode_by_market: dict[str, list[v3.V3Trade]] = defaultdict(list)
    episode_by_session: dict[str, list[v3.V3Trade]] = defaultdict(list)
    episode_by_provenance: dict[str, list[v3.V3Trade]] = defaultdict(list)
    for trade in episode_trades:
        episode_by_market[trade.symbol].append(trade)
        episode_by_session[trade.session].append(trade)
        episode_by_provenance[provenance_by_key[_key(trade)]].append(trade)

    per_market: dict[str, dict[str, Any]] = {}
    for symbol in sorted(v3.EXPECTED_SYMBOLS):
        selected = tuple(item for item in source_max3 if item.symbol == symbol)
        categories = Counter(
            provenance_by_key[_key(item)] for item in selected
        )
        per_market[symbol] = {
            "trades": len(selected),
            "total_r": str(_sum_r(selected)),
            "provenance": dict(sorted(categories.items())),
            "added": _cohort(
                tuple(
                    item
                    for item in selected
                    if provenance_by_key[_key(item)] == ADDED
                )
            ),
            "replaced": _cohort(
                tuple(
                    item
                    for item in selected
                    if provenance_by_key[_key(item)] == REPLACED
                )
            ),
        }

    per_session: dict[str, dict[str, Any]] = {}
    for session in ("ASIA", "LONDON", "NEW_YORK"):
        selected = tuple(item for item in source_max3 if item.session == session)
        categories = Counter(
            provenance_by_key[_key(item)] for item in selected
        )
        per_session[session] = {
            "trades": len(selected),
            "total_r": str(_sum_r(selected)),
            "provenance": dict(sorted(categories.items())),
            "added": _cohort(
                tuple(
                    item
                    for item in selected
                    if provenance_by_key[_key(item)] == ADDED
                )
            ),
            "replaced": _cohort(
                tuple(
                    item
                    for item in selected
                    if provenance_by_key[_key(item)] == REPLACED
                )
            ),
        }

    return {
        "identity": IDENTITY,
        "raw": {
            "v3_trades": len(baseline_raw),
            "source_first_trades": len(source_raw),
            "added_opportunities": len(added_keys),
            "lost_opportunities": len(lost_keys),
            "preserved_same_mss": len(preserved_keys),
            "replaced_mss": len(replaced_keys),
            "delta_reconciled": (
                len(source_raw) - len(baseline_raw)
                == len(added_keys) - len(lost_keys)
            ),
        },
        "max3": {
            "v3_trades": len(baseline_max3),
            "source_first_trades": len(source_max3),
            "delta": len(source_max3) - len(baseline_max3),
            "source_first_provenance": dict(
                sorted(source_provenance_counts.items())
            ),
            "selected_added": len(selected_added_keys),
            "selected_preserved": len(selected_preserved_keys),
            "selected_replaced": len(selected_replaced_keys),
            "baseline_displaced_by_competition": len(baseline_displaced_keys),
            "baseline_lost_by_semantics": len(baseline_semantic_lost_keys),
            "source_newly_selected_existing_opportunities": len(
                source_newly_selected_existing_keys
            ),
        },
        "cohorts": {
            "source_first_added_selected": _cohort(
                tuple(
                    source_by_key[key]
                    for key in sorted(selected_added_keys)
                )
            ),
            "source_first_replaced_selected": _cohort(
                tuple(
                    source_by_key[key]
                    for key in sorted(selected_replaced_keys)
                )
            ),
            "v3_displaced_by_source_first_max3": _cohort(
                tuple(
                    base_by_key[key]
                    for key in sorted(baseline_displaced_keys)
                )
            ),
            "v3_lost_by_source_first_semantics": _cohort(
                tuple(
                    base_by_key[key]
                    for key in sorted(baseline_semantic_lost_keys)
                )
            ),
        },
        "source_first_max_drawdown_episode": {
            **episode,
            "provenance_counts": dict(sorted(episode_provenance.items())),
            "by_provenance": {
                key: _cohort(tuple(value))
                for key, value in sorted(episode_by_provenance.items())
            },
            "by_market": {
                key: _cohort(tuple(value))
                for key, value in sorted(episode_by_market.items())
            },
            "by_session": {
                key: _cohort(tuple(value))
                for key, value in sorted(episode_by_session.items())
            },
        },
        "per_market": per_market,
        "per_session": per_session,
        "controls": {
            "v3_raw_reproduced": len(baseline_raw) == EXPECTED_V3_RAW,
            "source_first_raw_reproduced": (
                len(source_raw) == EXPECTED_SOURCE_FIRST_RAW
            ),
            "v3_max3_reproduced": len(baseline_max3) == EXPECTED_V3_MAX3,
            "source_first_max3_reproduced": (
                len(source_max3) == EXPECTED_SOURCE_FIRST_MAX3
            ),
        },
        "max3_contract_preserved": True,
        "realized_exit_order_used_for_drawdown": True,
        "outcome_aware_forensics": True,
        "decision_time_rule_derived": False,
        "strategy_mutated": False,
        "rule_promotion_allowed": False,
        "economic_candidate": False,
        "fresh_holdout_claimed": False,
    }


def write_report(report: dict[str, Any], output: Path) -> None:
    output.mkdir(parents=True, exist_ok=True)
    path = (
        output
        / "capitalizer-v3-source-first-delta-drawdown-forensics-2y-v1.json"
    )
    path.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("v3_root", type=Path)
    parser.add_argument("source_first_root", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    report = build_report(args.v3_root, args.source_first_root)
    write_report(report, args.output)
    print(json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    main()
