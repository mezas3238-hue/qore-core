"""Ledger-level forensics for WAIT5 vs WAIT5_LATE60 on consumed 2Y data.

Post-outcome diagnostic only. No admission rule is derived.

Reapplies frozen portfolio MAX3 independently and explains:
- preserved WAIT5 trades;
- LATE60-added trades;
- WAIT5 trades displaced by portfolio competition;
- economics of the late cohort in predeclared delay bands;
- provenance inside the LATE60 maximum-drawdown episode.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from dataclasses import asdict
from datetime import datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any

from qore.infrastructure.trader_lab import (
    capitalizer_owner_h1_m3_m1_causal_reversal_1y_v3 as v3,
)

IDENTITY = "QORE_CAPITALIZER_V3_WAIT5_LATE60_DELTA_FORENSICS_2Y_V1"
EXPECTED_WAIT5_RAW = 1003
EXPECTED_LATE60_RAW = 1368
EXPECTED_WAIT5_MAX3 = 983
EXPECTED_LATE60_MAX3 = 1327
EXPECTED_LATE60_SELECTED = 354
EXPECTED_WAIT5_DISPLACED = 10

PRESERVED = "WAIT5_PRESERVED"
LATE_ADDED = "LATE60_ADDED"


def _aware(value: str) -> datetime:
    return datetime.fromisoformat(value)


def _load(
    root: Path,
    pattern: str,
    *,
    expected_paths: int = 9,
) -> tuple[v3.V3Trade, ...]:
    paths = sorted(root.rglob(pattern))
    if len(paths) != expected_paths:
        raise ValueError(f"expected {expected_paths} ledgers, got {len(paths)}")
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
        trade.entry_at,
    )


def _metrics(trades: tuple[v3.V3Trade, ...]) -> dict[str, Any] | None:
    value = v3._metrics(trades)
    return None if value is None else asdict(value)


def _sum_r(trades: tuple[v3.V3Trade, ...]) -> Decimal:
    return sum(
        (Decimal(item.realized_gross_r) for item in trades),
        Decimal("0"),
    )


def _cohort(trades: tuple[v3.V3Trade, ...]) -> dict[str, Any]:
    ordered = tuple(
        sorted(trades, key=lambda item: (_aware(item.entry_at), item.symbol))
    )
    return {
        "trades": len(ordered),
        "total_r": str(_sum_r(ordered)),
        "metrics": _metrics(ordered),
    }


def _late_delay_minutes(trade: v3.V3Trade) -> int:
    if not trade.entry_mode.startswith("LATE60_"):
        raise ValueError("delay requested for non-LATE60 trade")
    extended = _aware(trade.h1_deadline)
    original = extended - timedelta(minutes=60)
    return int((_aware(trade.entry_at) - original).total_seconds() // 60)


def _delay_band(trade: v3.V3Trade) -> str:
    value = _late_delay_minutes(trade)
    if value <= 5:
        return "00_05M"
    if value <= 15:
        return "06_15M"
    if value <= 30:
        return "16_30M"
    return "31_60M"


def _drawdown_episode(
    trades: tuple[v3.V3Trade, ...],
    provenance: dict[tuple[str, str, str, str, str], str],
) -> dict[str, Any]:
    ordered = tuple(
        sorted(
            trades,
            key=lambda item: (
                _aware(item.exit_at),
                _aware(item.entry_at),
                item.symbol,
            ),
        )
    )
    equity = Decimal("0")
    peak = Decimal("0")
    peak_index = -1
    peak_trade: v3.V3Trade | None = None
    max_dd = Decimal("0")
    max_peak_index = -1
    max_peak_trade: v3.V3Trade | None = None
    trough_index = -1
    trough_equity = Decimal("0")

    for index, trade in enumerate(ordered):
        equity += Decimal(trade.realized_gross_r)
        if equity > peak:
            peak = equity
            peak_index = index
            peak_trade = trade
        dd = peak - equity
        if dd > max_dd:
            max_dd = dd
            max_peak_index = peak_index
            max_peak_trade = peak_trade
            trough_index = index
            trough_equity = equity

    if trough_index < 0:
        raise ValueError("drawdown episode not found")
    episode = ordered[max_peak_index + 1 : trough_index + 1]
    by_provenance: dict[str, list[v3.V3Trade]] = defaultdict(list)
    by_session: dict[str, list[v3.V3Trade]] = defaultdict(list)
    by_market: dict[str, list[v3.V3Trade]] = defaultdict(list)
    for trade in episode:
        kind = provenance[_key(trade)]
        by_provenance[kind].append(trade)
        by_session[trade.session].append(trade)
        by_market[trade.symbol].append(trade)

    return {
        "drawdown_r": str(max_dd),
        "peak_exit_at": None if max_peak_trade is None else max_peak_trade.exit_at,
        "trough_exit_at": ordered[trough_index].exit_at,
        "trough_equity_r": str(trough_equity),
        "trades_in_episode": len(episode),
        "episode_total_r": str(_sum_r(episode)),
        "by_provenance": {
            key: _cohort(tuple(value))
            for key, value in sorted(by_provenance.items())
        },
        "by_session": {
            key: _cohort(tuple(value))
            for key, value in sorted(by_session.items())
        },
        "by_market": {
            key: _cohort(tuple(value))
            for key, value in sorted(by_market.items())
        },
    }


def build_report(wait5_root: Path, late60_root: Path) -> dict[str, Any]:
    wait5_raw = _load(
        wait5_root,
        "capitalizer-*-v3-source-first-wait5-2y-v1-trades.jsonl",
    )
    late60_raw = _load(
        late60_root,
        "capitalizer-*-v3-source-first-wait5-late60-2y-v1-trades.jsonl",
    )
    if len(wait5_raw) != EXPECTED_WAIT5_RAW:
        raise ValueError("WAIT5 raw control mismatch")
    if len(late60_raw) != EXPECTED_LATE60_RAW:
        raise ValueError("LATE60 raw control mismatch")

    wait5 = v3._portfolio_max3(wait5_raw)
    late60 = v3._portfolio_max3(late60_raw)
    if len(wait5) != EXPECTED_WAIT5_MAX3:
        raise ValueError("WAIT5 MAX3 control mismatch")
    if len(late60) != EXPECTED_LATE60_MAX3:
        raise ValueError("LATE60 MAX3 control mismatch")

    wait5_by_key = {_key(item): item for item in wait5}
    late60_by_key = {_key(item): item for item in late60}
    if len(wait5_by_key) != len(wait5) or len(late60_by_key) != len(late60):
        raise ValueError("duplicate selected trade key")

    wait5_keys = set(wait5_by_key)
    late60_keys = set(late60_by_key)
    common_keys = wait5_keys & late60_keys
    displaced_keys = wait5_keys - late60_keys
    added_keys = late60_keys - wait5_keys

    added = tuple(late60_by_key[key] for key in added_keys)
    preserved = tuple(late60_by_key[key] for key in common_keys)
    displaced = tuple(wait5_by_key[key] for key in displaced_keys)

    if len(added) != EXPECTED_LATE60_SELECTED:
        raise ValueError("LATE60 added selected control mismatch")
    if len(displaced) != EXPECTED_WAIT5_DISPLACED:
        raise ValueError("WAIT5 displaced control mismatch")
    if any(not item.entry_mode.startswith("LATE60_") for item in added):
        raise ValueError("non-LATE60 trade found in added cohort")

    provenance = {
        _key(item): (
            LATE_ADDED if item.entry_mode.startswith("LATE60_") else PRESERVED
        )
        for item in late60
    }

    by_delay: dict[str, tuple[v3.V3Trade, ...]] = {}
    for band in ("00_05M", "06_15M", "16_30M", "31_60M"):
        by_delay[band] = tuple(item for item in added if _delay_band(item) == band)

    by_mode: dict[str, tuple[v3.V3Trade, ...]] = {}
    for mode in sorted({item.entry_mode for item in added}):
        by_mode[mode] = tuple(item for item in added if item.entry_mode == mode)

    by_session: dict[str, tuple[v3.V3Trade, ...]] = {}
    for session in ("ASIA", "LONDON", "NEW_YORK"):
        by_session[session] = tuple(item for item in added if item.session == session)

    by_market: dict[str, tuple[v3.V3Trade, ...]] = {}
    for symbol in sorted(v3.EXPECTED_SYMBOLS):
        by_market[symbol] = tuple(item for item in added if item.symbol == symbol)

    return {
        "identity": IDENTITY,
        "wait5_raw": len(wait5_raw),
        "late60_raw": len(late60_raw),
        "wait5_max3": len(wait5),
        "late60_max3": len(late60),
        "preserved_wait5": len(preserved),
        "late60_added": len(added),
        "wait5_displaced": len(displaced),
        "reconciliation": {
            "late60_selected": f"{len(preserved)} + {len(added)} = {len(late60)}",
            "net_trade_delta": len(late60) - len(wait5),
            "added_minus_displaced": len(added) - len(displaced),
        },
        "cohorts": {
            "late60_added": _cohort(added),
            "wait5_preserved": _cohort(preserved),
            "wait5_displaced": _cohort(displaced),
        },
        "late_by_delay_band": {
            key: _cohort(value) for key, value in by_delay.items()
        },
        "late_by_entry_mode": {
            key: _cohort(value) for key, value in by_mode.items()
        },
        "late_by_session": {
            key: _cohort(value) for key, value in by_session.items()
        },
        "late_by_market": {
            key: _cohort(value) for key, value in by_market.items()
        },
        "late_delay_counts": dict(
            Counter(_delay_band(item) for item in added)
        ),
        "late_entry_mode_counts": dict(
            Counter(item.entry_mode for item in added)
        ),
        "late60_max_drawdown_episode": _drawdown_episode(
            late60,
            provenance,
        ),
        "outcome_aware": True,
        "post_result_diagnostic_only": True,
        "outcome_used_for_admission": False,
        "rule_promotion_allowed": False,
        "fresh_holdout_claimed": False,
        "strategy_mutated": False,
        "live_authorized": False,
        "real_capital_authorized": False,
    }


def write_report(report: dict[str, Any], output: Path) -> None:
    output.mkdir(parents=True, exist_ok=True)
    path = output / "capitalizer-v3-wait5-late60-delta-forensics-2y-v1.json"
    path.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("wait5_root", type=Path)
    parser.add_argument("late60_root", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    report = build_report(args.wait5_root, args.late60_root)
    write_report(report, args.output)
    print(json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    main()
