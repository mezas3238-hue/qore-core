"""Paired fresh holdout for frozen SOURCE_FIRST + WAIT5 + FVG_LAG2.

Holdout window is frozen before reading any results:
2022-09-17T00:00:00Z <= signal < 2024-09-17T00:00:00Z.

The candidate rule is imported unchanged from the consumed 2024-09-17 ->
2026-09-17 development experiment. This module runs two variants on identical
native-M1 holdout data:
1) SOURCE_FIRST + WAIT5 baseline;
2) SOURCE_FIRST + WAIT5 + frozen FVG_LAG2.

No holdout outcome is used to alter admission, stop, target, WAIT5, MAX3, or the
+2 minute confirmation-lag contract.
"""

from __future__ import annotations

import argparse
import json
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import asdict
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any

from qore.infrastructure.trader_lab import (
    capitalizer_owner_h1_m3_m1_causal_reversal_1y_v3 as v3,
)
from qore.infrastructure.trader_lab import (
    capitalizer_v3_source_first_wait5_2y_v1 as wait5,
)
from qore.infrastructure.trader_lab import (
    capitalizer_v3_source_first_wait5_fvg_lag2_2y_v1 as lag2,
)
from qore.infrastructure.trader_lab.capitalizer_contract import CapitalizerSession

IDENTITY = (
    "QORE_CAPITALIZER_V3_SOURCE_FIRST_WAIT5_FVG_LAG2_"
    "FRESH_HOLDOUT_2Y_V1"
)
MATRIX_IDENTITY = (
    "QORE_CAPITALIZER_NINE_MARKET_V3_SOURCE_FIRST_WAIT5_FVG_LAG2_"
    "FRESH_HOLDOUT_2Y_V1"
)
HOLDOUT_START = datetime(2022, 9, 17, 0, 0, tzinfo=UTC)
HOLDOUT_END = datetime(2024, 9, 17, 0, 0, tzinfo=UTC)
LOOKBACK_START = HOLDOUT_START - timedelta(days=21)
DEVELOPMENT_START = datetime(2024, 9, 17, 0, 0, tzinfo=UTC)
DEVELOPMENT_END = datetime(2026, 9, 17, 0, 0, tzinfo=UTC)


@contextmanager
def _holdout_window() -> Iterator[None]:
    mutable_v3: Any = v3
    old_start = mutable_v3.WINDOW_START
    old_end = mutable_v3.WINDOW_END
    old_lookback = mutable_v3.LOOKBACK_START
    try:
        mutable_v3.WINDOW_START = HOLDOUT_START
        mutable_v3.WINDOW_END = HOLDOUT_END
        mutable_v3.LOOKBACK_START = LOOKBACK_START
        yield
    finally:
        mutable_v3.WINDOW_START = old_start
        mutable_v3.WINDOW_END = old_end
        mutable_v3.LOOKBACK_START = old_lookback


def _run_wait5(
    m1_root: Path,
    *,
    session: CapitalizerSession,
    with_lag2: bool,
) -> tuple[v3.V3MarketReport, tuple[v3.V3Trade, ...]]:
    with _holdout_window(), wait5._wait5_scan_patch():
        if with_lag2:
            with lag2._lag2_patch():
                return v3.build_market_report(m1_root, session=session)
        return v3.build_market_report(m1_root, session=session)


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


def build_market_report(
    m1_root: Path,
    *,
    session: CapitalizerSession,
) -> tuple[
    dict[str, Any],
    tuple[v3.V3Trade, ...],
    tuple[v3.V3Trade, ...],
]:
    baseline_report, baseline_trades = _run_wait5(
        m1_root,
        session=session,
        with_lag2=False,
    )
    candidate_report, candidate_trades = _run_wait5(
        m1_root,
        session=session,
        with_lag2=True,
    )

    if baseline_report.symbol != candidate_report.symbol:
        raise ValueError("holdout paired replay symbol mismatch")
    if baseline_report.session != candidate_report.session:
        raise ValueError("holdout paired replay session mismatch")

    candidate_lag2 = tuple(
        trade for trade in candidate_trades if lag2._is_lag2_trade(trade)
    )
    baseline_keys = {_trade_key(trade) for trade in baseline_trades}
    candidate_keys = {_trade_key(trade) for trade in candidate_trades}
    added = tuple(
        trade
        for trade in candidate_trades
        if _trade_key(trade) not in baseline_keys
    )
    displaced = tuple(
        trade
        for trade in baseline_trades
        if _trade_key(trade) not in candidate_keys
    )

    report = {
        "identity": IDENTITY,
        "symbol": baseline_report.symbol,
        "session": baseline_report.session,
        "holdout_start": HOLDOUT_START.isoformat(),
        "holdout_end_exclusive": HOLDOUT_END.isoformat(),
        "development_start": DEVELOPMENT_START.isoformat(),
        "development_end_exclusive": DEVELOPMENT_END.isoformat(),
        "non_overlapping_with_development": HOLDOUT_END <= DEVELOPMENT_START,
        "baseline_raw_trades": len(baseline_trades),
        "candidate_raw_trades": len(candidate_trades),
        "candidate_lag2_raw_trades": len(candidate_lag2),
        "added_candidate_trades": len(added),
        "displaced_baseline_trades": len(displaced),
        "baseline_raw_metrics": (
            None
            if baseline_report.raw_metrics is None
            else asdict(baseline_report.raw_metrics)
        ),
        "candidate_raw_metrics": (
            None
            if candidate_report.raw_metrics is None
            else asdict(candidate_report.raw_metrics)
        ),
        "candidate_lag2_raw_metrics": _metrics_dict(candidate_lag2),
        "frozen_candidate_identity": lag2.IDENTITY,
        "frozen_admission_source": lag2.ADMISSION_SOURCE,
        "max_confirmation_lag_minutes": lag2.MAX_CONFIRMATION_LAG_MINUTES,
        "same_source_first_mss_preserved": True,
        "same_original_m3_displacement_required": True,
        "same_original_causal_ob_required": True,
        "opposed_fvg_before_completion_rejected": True,
        "fill_before_fvg_confirmation_forbidden": True,
        "same_wait5_preserved": True,
        "same_stop_preserved": True,
        "same_target_preserved": True,
        "same_h1_deadline_preserved": True,
        "max3_contract_preserved": True,
        "outcome_used_for_admission": False,
        "holdout_outcome_used_for_rule_change": False,
        "fresh_holdout_for_lag2_rule": True,
        "fresh_holdout_role": (
            "NON_OVERLAPPING_PREDEVELOPMENT_FOR_FVG_LAG2_RULE"
        ),
        "rule_promotion_allowed": False,
        "trader_certified": False,
        "live_authorized": False,
        "real_capital_authorized": False,
    }
    return report, baseline_trades, candidate_trades


def write_market(
    report: dict[str, Any],
    baseline_trades: tuple[v3.V3Trade, ...],
    candidate_trades: tuple[v3.V3Trade, ...],
    output: Path,
) -> None:
    output.mkdir(parents=True, exist_ok=True)
    symbol = str(report["symbol"]).lower()
    stem = (
        f"capitalizer-{symbol}-v3-source-first-wait5-fvg-lag2-"
        "fresh-holdout-2y-v1"
    )
    (output / f"{stem}.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    with (output / f"{stem}-baseline-trades.jsonl").open(
        "w",
        encoding="utf-8",
    ) as handle:
        for trade in baseline_trades:
            handle.write(json.dumps(asdict(trade), sort_keys=True) + "\n")
    with (output / f"{stem}-candidate-trades.jsonl").open(
        "w",
        encoding="utf-8",
    ) as handle:
        for trade in candidate_trades:
            handle.write(json.dumps(asdict(trade), sort_keys=True) + "\n")


def _load_reports(root: Path) -> list[dict[str, Any]]:
    paths = sorted(
        root.rglob(
            "capitalizer-*-v3-source-first-wait5-fvg-lag2-"
            "fresh-holdout-2y-v1.json"
        )
    )
    if len(paths) != 9:
        raise ValueError(
            f"FVG_LAG2 holdout matrix requires 9 reports, got {len(paths)}"
        )
    reports = [
        dict(json.loads(path.read_text(encoding="utf-8")))
        for path in paths
    ]
    if {str(item["symbol"]) for item in reports} != v3.EXPECTED_SYMBOLS:
        raise ValueError("FVG_LAG2 holdout universe mismatch")
    return reports


def _load_trades(
    root: Path,
    *,
    variant: str,
) -> tuple[v3.V3Trade, ...]:
    if variant not in {"baseline", "candidate"}:
        raise ValueError("unknown holdout variant")
    pattern = (
        "capitalizer-*-v3-source-first-wait5-fvg-lag2-"
        f"fresh-holdout-2y-v1-{variant}-trades.jsonl"
    )
    rows: list[v3.V3Trade] = []
    for path in sorted(root.rglob(pattern)):
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


def _decimal_metric(
    metrics: Any,
    field: str,
) -> Decimal:
    value = getattr(metrics, field)
    if value is None:
        raise ValueError(f"holdout metric {field} unexpectedly null")
    return Decimal(str(value))


def build_matrix(root: Path) -> dict[str, Any]:
    reports = _load_reports(root)
    baseline_raw = _load_trades(root, variant="baseline")
    candidate_raw = _load_trades(root, variant="candidate")

    baseline_max3 = v3._portfolio_max3(baseline_raw)
    candidate_max3 = v3._portfolio_max3(candidate_raw)
    baseline_metrics = v3._metrics(baseline_max3)
    candidate_metrics = v3._metrics(candidate_max3)
    if baseline_metrics is None or candidate_metrics is None:
        raise ValueError("holdout requires non-empty paired portfolio metrics")

    candidate_lag2 = tuple(
        trade for trade in candidate_max3 if lag2._is_lag2_trade(trade)
    )
    lag2_metrics = v3._metrics(candidate_lag2)

    candidate_keys = {_trade_key(trade) for trade in candidate_max3}
    baseline_keys = {_trade_key(trade) for trade in baseline_max3}
    added = tuple(
        trade
        for trade in candidate_max3
        if _trade_key(trade) not in baseline_keys
    )
    displaced = tuple(
        trade
        for trade in baseline_max3
        if _trade_key(trade) not in candidate_keys
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
            "lag2_trades": sum(lag2._is_lag2_trade(item) for item in candidate),
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
            "lag2_trades": sum(lag2._is_lag2_trade(item) for item in candidate),
            "baseline_metrics": _metrics_dict(baseline),
            "candidate_metrics": _metrics_dict(candidate),
        }

    return {
        "identity": MATRIX_IDENTITY,
        "market_count": 9,
        "holdout_start": HOLDOUT_START.isoformat(),
        "holdout_end_exclusive": HOLDOUT_END.isoformat(),
        "development_start": DEVELOPMENT_START.isoformat(),
        "development_end_exclusive": DEVELOPMENT_END.isoformat(),
        "non_overlapping_with_development": HOLDOUT_END <= DEVELOPMENT_START,
        "baseline_raw_trades": len(baseline_raw),
        "candidate_raw_trades": len(candidate_raw),
        "baseline_max3_trades": len(baseline_max3),
        "candidate_max3_trades": len(candidate_max3),
        "candidate_max3_lag2_trades": len(candidate_lag2),
        "added_candidate_max3_trades": len(added),
        "displaced_baseline_max3_trades": len(displaced),
        "baseline_max3_metrics": asdict(baseline_metrics),
        "candidate_max3_metrics": asdict(candidate_metrics),
        "candidate_lag2_metrics": (
            None if lag2_metrics is None else asdict(lag2_metrics)
        ),
        "delta_candidate_vs_baseline": {
            "raw_trades": len(candidate_raw) - len(baseline_raw),
            "max3_trades": len(candidate_max3) - len(baseline_max3),
            "profit_factor": str(
                _decimal_metric(candidate_metrics, "profit_factor")
                - _decimal_metric(baseline_metrics, "profit_factor")
            ),
            "total_r": str(
                _decimal_metric(candidate_metrics, "total_r")
                - _decimal_metric(baseline_metrics, "total_r")
            ),
            "mean_r": str(
                _decimal_metric(candidate_metrics, "mean_r")
                - _decimal_metric(baseline_metrics, "mean_r")
            ),
            "max_drawdown_r": str(
                _decimal_metric(candidate_metrics, "max_drawdown_r")
                - _decimal_metric(baseline_metrics, "max_drawdown_r")
            ),
            "losing_streak": (
                candidate_metrics.max_losing_streak
                - baseline_metrics.max_losing_streak
            ),
        },
        "per_session": per_session,
        "per_market": per_market,
        "frozen_candidate_identity": lag2.IDENTITY,
        "frozen_admission_source": lag2.ADMISSION_SOURCE,
        "max_confirmation_lag_minutes": lag2.MAX_CONFIRMATION_LAG_MINUTES,
        "same_source_first_mss_preserved": True,
        "same_original_m3_displacement_required": True,
        "same_original_causal_ob_required": True,
        "opposed_fvg_before_completion_rejected": True,
        "fill_before_fvg_confirmation_forbidden": True,
        "same_wait5_preserved": True,
        "same_stop_preserved": True,
        "same_target_preserved": True,
        "same_h1_deadline_preserved": True,
        "max3_contract_preserved": True,
        "outcome_used_for_admission": False,
        "holdout_outcome_used_for_rule_change": False,
        "fresh_holdout_for_lag2_rule": True,
        "fresh_holdout_role": (
            "NON_OVERLAPPING_PREDEVELOPMENT_FOR_FVG_LAG2_RULE"
        ),
        "automatic_promotion_allowed": False,
        "rule_promotion_allowed": False,
        "trader_certified": False,
        "live_authorized": False,
        "real_capital_authorized": False,
    }


def write_matrix(report: dict[str, Any], output: Path) -> None:
    output.mkdir(parents=True, exist_ok=True)
    path = output / (
        "capitalizer-nine-market-v3-source-first-wait5-fvg-lag2-"
        "fresh-holdout-2y-v1.json"
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
    matrix.add_argument("input_root", type=Path)
    matrix.add_argument("output", type=Path)

    args = parser.parse_args()
    if args.command == "market":
        report, baseline, candidate = build_market_report(
            args.m1_root,
            session=CapitalizerSession(args.session),
        )
        write_market(report, baseline, candidate, args.output)
        print(
            json.dumps(
                {
                    "identity": report["identity"],
                    "symbol": report["symbol"],
                    "session": report["session"],
                    "baseline_raw_trades": report["baseline_raw_trades"],
                    "candidate_raw_trades": report["candidate_raw_trades"],
                    "candidate_lag2_raw_trades": report[
                        "candidate_lag2_raw_trades"
                    ],
                },
                sort_keys=True,
            )
        )
        return

    report = build_matrix(args.input_root)
    write_matrix(report, args.output)
    print(json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    main()
