"""Consumed-window economic A/B for SOURCE_FIRST series rearm + WAIT5.

The series-rearm boundary semantic was frozen from outcome-free evidence before
reading this candidate's economics:

- observe strictly after the actual sweep;
- first opposing M3 series establishes boundary at the opening of its first bar;
- a later distinct opposing series rearms boundary to its own first-bar open;
- pre-sweep boundaries are forbidden;
- frozen V3 direction/swing/body60/ATR1.2 requirements remain unchanged.

This module changes only the M3 CISD boundary semantic inside the already-frozen
SOURCE_FIRST + WAIT5 replay. FVG, fill, WAIT5, stop, target, H1 deadline, STOP-
first precedence and MAX3 remain unchanged.

Window [2024-09-17, 2026-09-17) is consumed development evidence. No promotion
or fresh-holdout claim is allowed from this result.
"""

from __future__ import annotations

import argparse
import json
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import asdict
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

from qore.infrastructure.trader_lab import (
    capitalizer_owner_h1_m3_m1_causal_reversal_1y_v3 as v3,
)
from qore.infrastructure.trader_lab import (
    capitalizer_v3_source_first_wait5_2y_v1 as wait5,
)
from qore.infrastructure.trader_lab.capitalizer_contract import CapitalizerSession
from qore.infrastructure.trader_lab.capitalizer_v3_source_first_series_rearm_v1 import (
    BOUNDARY_SEMANTICS,
    find_series_rearm_m3_mss,
)
from qore.infrastructure.trader_lab.capitalizer_v3_source_first_series_rearm_v1 import (
    IDENTITY as SERIES_REARM_HELPER_IDENTITY,
)

IDENTITY = "QORE_CAPITALIZER_V3_SOURCE_FIRST_SERIES_REARM_WAIT5_2Y_V1"
MATRIX_IDENTITY = (
    "QORE_CAPITALIZER_NINE_MARKET_V3_SOURCE_FIRST_SERIES_REARM_WAIT5_2Y_V1"
)

WAIT5_BASELINE_RAW = 1003
WAIT5_BASELINE_MAX3 = 983
WAIT5_BASELINE_PF = Decimal("1.384597543145107741177480996")
WAIT5_BASELINE_TOTAL_R = Decimal("135.7651037644532073259312101")
WAIT5_BASELINE_MEAN_R = Decimal("0.1381130251927296107079666430")
WAIT5_BASELINE_DD_R = Decimal("11.9420088471277198029814040")
WAIT5_BASELINE_LS = 9


@contextmanager
def _series_rearm_patch() -> Iterator[None]:
    mutable_wait5: Any = wait5
    original = mutable_wait5.find_source_first_m3_mss
    try:
        mutable_wait5.find_source_first_m3_mss = find_series_rearm_m3_mss
        yield
    finally:
        mutable_wait5.find_source_first_m3_mss = original


def build_market_report(
    m1_root: Path,
    *,
    session: CapitalizerSession,
) -> tuple[dict[str, Any], tuple[v3.V3Trade, ...]]:
    with _series_rearm_patch():
        report, trades = wait5.build_market_report(
            m1_root,
            session=session,
        )

    report.update(
        {
            "identity": IDENTITY,
            "series_rearm_helper_identity": SERIES_REARM_HELPER_IDENTITY,
            "boundary_semantics": BOUNDARY_SEMANTICS,
            "variant_only_change": "M3_CISD_SOURCE_FIRST_SERIES_REARM",
            "source_first_rearm_enabled": True,
            "pre_sweep_boundary_forbidden": True,
            "same_source_first_post_sweep_origin": True,
            "same_m3_non_cisd_filters": True,
            "same_fvg_preserved": True,
            "same_fill_preserved": True,
            "same_wait5_preserved": True,
            "same_stop_preserved": True,
            "same_target_preserved": True,
            "same_h1_deadline_preserved": True,
            "same_stop_first_precedence": True,
            "same_max3_preserved": True,
            "outcome_used_for_admission": False,
            "component_rule_frozen_outcome_free": True,
            "development_window_role": "CONSUMED_DEVELOPMENT_ONLY",
            "fresh_holdout_required": True,
            "fresh_holdout_claimed": False,
            "economic_candidate": True,
            "rule_promotion_allowed": False,
            "trader_certified": False,
            "live_authorized": False,
            "real_capital_authorized": False,
        }
    )
    return report, trades


def write_market(
    report: dict[str, Any],
    trades: tuple[v3.V3Trade, ...],
    output: Path,
) -> None:
    output.mkdir(parents=True, exist_ok=True)
    symbol = str(report["symbol"]).lower()
    stem = (
        f"capitalizer-{symbol}-v3-source-first-"
        "series-rearm-wait5-2y-v1"
    )
    (output / f"{stem}.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    with (output / f"{stem}-trades.jsonl").open("w", encoding="utf-8") as handle:
        for trade in trades:
            handle.write(json.dumps(asdict(trade), sort_keys=True) + "\n")


def _load_candidate_reports(root: Path) -> list[dict[str, Any]]:
    paths = sorted(
        root.rglob(
            "capitalizer-*-v3-source-first-series-rearm-wait5-2y-v1.json"
        )
    )
    if len(paths) != 9:
        raise ValueError(f"series-rearm WAIT5 matrix requires 9 reports, got {len(paths)}")
    reports = [
        dict(json.loads(path.read_text(encoding="utf-8")))
        for path in paths
    ]
    if {str(item["symbol"]) for item in reports} != v3.EXPECTED_SYMBOLS:
        raise ValueError("series-rearm WAIT5 universe mismatch")
    return reports


def _load_candidate_trades(root: Path) -> tuple[v3.V3Trade, ...]:
    rows: list[v3.V3Trade] = []
    paths = sorted(
        root.rglob(
            "capitalizer-*-v3-source-first-series-rearm-wait5-2y-v1-trades.jsonl"
        )
    )
    if len(paths) != 9:
        raise ValueError(f"series-rearm WAIT5 requires 9 trade ledgers, got {len(paths)}")
    for path in paths:
        with path.open(encoding="utf-8") as handle:
            for line in handle:
                if line.strip():
                    rows.append(v3.V3Trade(**json.loads(line)))
    return tuple(
        sorted(
            rows,
            key=lambda item: (
                datetime.fromisoformat(item.entry_at),
                item.symbol,
            ),
        )
    )


def _load_baseline_trades(root: Path) -> tuple[v3.V3Trade, ...]:
    rows: list[v3.V3Trade] = []
    paths = sorted(
        root.rglob("capitalizer-*-v3-source-first-wait5-2y-v1-trades.jsonl")
    )
    if len(paths) != 9:
        raise ValueError(f"frozen WAIT5 baseline requires 9 trade ledgers, got {len(paths)}")
    for path in paths:
        with path.open(encoding="utf-8") as handle:
            for line in handle:
                if line.strip():
                    rows.append(v3.V3Trade(**json.loads(line)))
    return tuple(
        sorted(
            rows,
            key=lambda item: (
                datetime.fromisoformat(item.entry_at),
                item.symbol,
            ),
        )
    )


def _metrics_dict(
    trades: tuple[v3.V3Trade, ...],
) -> dict[str, Any] | None:
    value = v3._metrics(trades)
    return None if value is None else asdict(value)


def _trade_key(trade: v3.V3Trade) -> tuple[str, str, str, str, str]:
    return (
        trade.symbol,
        trade.session,
        trade.operating_date,
        trade.side,
        trade.entry_at,
    )


def build_matrix(
    candidate_root: Path,
    baseline_root: Path,
) -> dict[str, Any]:
    reports = _load_candidate_reports(candidate_root)
    candidate_raw = _load_candidate_trades(candidate_root)
    baseline_raw = _load_baseline_trades(baseline_root)

    candidate_max3 = v3._portfolio_max3(candidate_raw)
    baseline_max3 = v3._portfolio_max3(baseline_raw)
    candidate_metrics = v3._metrics(candidate_max3)
    baseline_metrics = v3._metrics(baseline_max3)
    if (
        candidate_metrics is None
        or candidate_metrics.profit_factor is None
        or candidate_metrics.mean_r is None
        or baseline_metrics is None
        or baseline_metrics.profit_factor is None
        or baseline_metrics.mean_r is None
    ):
        raise ValueError("series-rearm WAIT5 A/B requires complete MAX3 metrics")

    baseline_keys = {_trade_key(item) for item in baseline_max3}
    candidate_keys = {_trade_key(item) for item in candidate_max3}
    added = tuple(
        item
        for item in candidate_max3
        if _trade_key(item) not in baseline_keys
    )
    lost = tuple(
        item
        for item in baseline_max3
        if _trade_key(item) not in candidate_keys
    )
    preserved = tuple(
        item
        for item in candidate_max3
        if _trade_key(item) in baseline_keys
    )

    per_session: dict[str, dict[str, Any]] = {}
    for session in CapitalizerSession:
        baseline = tuple(
            item for item in baseline_max3 if item.session == session.value
        )
        candidate = tuple(
            item for item in candidate_max3 if item.session == session.value
        )
        per_session[session.value] = {
            "baseline_trades": len(baseline),
            "candidate_trades": len(candidate),
            "baseline_metrics": _metrics_dict(baseline),
            "candidate_metrics": _metrics_dict(candidate),
        }

    per_market: dict[str, dict[str, Any]] = {}
    for symbol in sorted(v3.EXPECTED_SYMBOLS):
        baseline = tuple(
            item for item in baseline_max3 if item.symbol == symbol
        )
        candidate = tuple(
            item for item in candidate_max3 if item.symbol == symbol
        )
        per_market[symbol] = {
            "baseline_trades": len(baseline),
            "candidate_trades": len(candidate),
            "baseline_metrics": _metrics_dict(baseline),
            "candidate_metrics": _metrics_dict(candidate),
        }

    candidate_pf = Decimal(candidate_metrics.profit_factor)
    baseline_pf = Decimal(baseline_metrics.profit_factor)
    candidate_total = Decimal(candidate_metrics.total_r)
    baseline_total = Decimal(baseline_metrics.total_r)
    candidate_mean = Decimal(candidate_metrics.mean_r)
    baseline_mean = Decimal(baseline_metrics.mean_r)
    candidate_dd = Decimal(candidate_metrics.max_drawdown_r)
    baseline_dd = Decimal(baseline_metrics.max_drawdown_r)

    return {
        "identity": MATRIX_IDENTITY,
        "market_count": 9,
        "window_start": reports[0]["window_start"],
        "window_end_exclusive": reports[0]["window_end_exclusive"],
        "baseline_raw_trades": len(baseline_raw),
        "candidate_raw_trades": len(candidate_raw),
        "baseline_max3_trades": len(baseline_max3),
        "candidate_max3_trades": len(candidate_max3),
        "baseline_max3_metrics": asdict(baseline_metrics),
        "candidate_max3_metrics": asdict(candidate_metrics),
        "candidate_added_max3_trades": len(added),
        "baseline_lost_max3_trades": len(lost),
        "preserved_max3_trades": len(preserved),
        "candidate_added_metrics": _metrics_dict(added),
        "baseline_lost_metrics": _metrics_dict(lost),
        "preserved_metrics": _metrics_dict(preserved),
        "delta_candidate_vs_wait5": {
            "raw_trades": len(candidate_raw) - len(baseline_raw),
            "max3_trades": len(candidate_max3) - len(baseline_max3),
            "profit_factor": str(candidate_pf - baseline_pf),
            "total_r": str(candidate_total - baseline_total),
            "mean_r": str(candidate_mean - baseline_mean),
            "max_drawdown_r": str(candidate_dd - baseline_dd),
            "losing_streak": (
                candidate_metrics.max_losing_streak
                - baseline_metrics.max_losing_streak
            ),
        },
        "frozen_wait5_reference": {
            "expected_raw_trades": WAIT5_BASELINE_RAW,
            "expected_max3_trades": WAIT5_BASELINE_MAX3,
            "expected_profit_factor": str(WAIT5_BASELINE_PF),
            "expected_total_r": str(WAIT5_BASELINE_TOTAL_R),
            "expected_mean_r": str(WAIT5_BASELINE_MEAN_R),
            "expected_max_drawdown_r": str(WAIT5_BASELINE_DD_R),
            "expected_losing_streak": WAIT5_BASELINE_LS,
        },
        "per_session": per_session,
        "per_market": per_market,
        "series_rearm_helper_identity": SERIES_REARM_HELPER_IDENTITY,
        "boundary_semantics": BOUNDARY_SEMANTICS,
        "variant_only_change": "M3_CISD_SOURCE_FIRST_SERIES_REARM",
        "source_first_rearm_enabled": True,
        "pre_sweep_boundary_forbidden": True,
        "same_source_first_post_sweep_origin": True,
        "same_m3_non_cisd_filters": True,
        "same_fvg_preserved": True,
        "same_fill_preserved": True,
        "same_wait5_preserved": True,
        "same_stop_preserved": True,
        "same_target_preserved": True,
        "same_h1_deadline_preserved": True,
        "same_stop_first_precedence": True,
        "same_max3_preserved": True,
        "outcome_used_for_admission": False,
        "component_rule_frozen_outcome_free": True,
        "development_window_role": "CONSUMED_DEVELOPMENT_ONLY",
        "fresh_holdout_required": True,
        "fresh_holdout_claimed": False,
        "economic_candidate": True,
        "automatic_promotion_allowed": False,
        "rule_promotion_allowed": False,
        "trader_certified": False,
        "live_authorized": False,
        "real_capital_authorized": False,
    }


def write_matrix(report: dict[str, Any], output: Path) -> None:
    output.mkdir(parents=True, exist_ok=True)
    path = output / (
        "capitalizer-nine-market-v3-source-first-series-rearm-wait5-2y-v1.json"
    )
    path.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)

    market = sub.add_parser("market")
    market.add_argument("m1_root", type=Path)
    market.add_argument("output", type=Path)
    market.add_argument(
        "--session",
        required=True,
        choices=[item.value for item in CapitalizerSession],
    )

    matrix = sub.add_parser("matrix")
    matrix.add_argument("candidate_root", type=Path)
    matrix.add_argument("baseline_root", type=Path)
    matrix.add_argument("output", type=Path)

    args = parser.parse_args()
    if args.command == "market":
        report, trades = build_market_report(
            args.m1_root,
            session=CapitalizerSession(args.session),
        )
        write_market(report, trades, args.output)
        print(
            json.dumps(
                {
                    "identity": report["identity"],
                    "symbol": report["symbol"],
                    "session": report["session"],
                    "m3_mss_confirmed": report["m3_mss_confirmed"],
                    "trades": len(trades),
                    "raw_metrics": report["raw_metrics"],
                },
                sort_keys=True,
            )
        )
        return

    report = build_matrix(args.candidate_root, args.baseline_root)
    write_matrix(report, args.output)
    print(json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    main()
