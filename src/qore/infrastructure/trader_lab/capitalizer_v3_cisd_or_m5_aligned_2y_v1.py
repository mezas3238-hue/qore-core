"""V3 2Y density experiment: same-bar CISD OR frozen M5=ALIGNED.

Frozen experimental change:
- V3 still requires one directional M3 bar with body >=60%, range >1.2*ATR,
  a valid broken swing, and a calculable CISD boundary.
- The M3 bar passes the final confirmation iff:
      CISD break is true OR the already-completed V3-selected M5 closeback state is ALIGNED.
- A missing CISD boundary remains fail-closed because it is part of the frozen M3MssEvent
  contract and is recorded in every V3 trade.

Everything downstream remains exact V3: M1 causal OB+FVG, fill, structural stop,
fixed 2R / next-H1 lifecycle, one-market ceiling, and global portfolio MAX3.
"""

from __future__ import annotations

import argparse
import bisect
import json
from collections import Counter
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
from qore.infrastructure.trader_lab.capitalizer_contract import CapitalizerSession
from qore.infrastructure.trader_lab.capitalizer_exposure_graph import CapitalizerSide
from qore.infrastructure.trader_lab.capitalizer_v3_frozen_replay_2y_v1 import (
    LOOKBACK_START,
    WINDOW_END,
    WINDOW_START,
    _v3_window,
)
from qore.infrastructure.trader_lab.capitalizer_v3_m5_directional_state_v1 import (
    IDENTITY as STATE_IDENTITY,
)
from qore.infrastructure.trader_lab.capitalizer_v3_m5_directional_state_v1 import (
    CapitalizerM5DirectionalState,
    classify_m5_directional_state,
)

IDENTITY = "QORE_CAPITALIZER_V3_CISD_OR_M5_ALIGNED_2Y_V1"
MATRIX_IDENTITY = "QORE_CAPITALIZER_NINE_MARKET_V3_CISD_OR_M5_ALIGNED_2Y_V1"

BASELINE_MAX3_TRADES = 474
BASELINE_PF = Decimal("1.283270342004661566350801358")
BASELINE_TOTAL_R = Decimal("50.34686423146549474995387094")
BASELINE_MEAN_R = Decimal("0.1062170131465516766876663944")
BASELINE_DD_R = Decimal("13.43559872546085473546771142")
BASELINE_LOSING_STREAK = 8
CLEAN_SAME_BAR_CISD_ONLY = 1298
CLEAN_SAME_BAR_CISD_ONLY_ALIGNED = 925


def _load_state_lookup(root: Path) -> dict[tuple[str, str], CapitalizerM5DirectionalState]:
    paths = sorted(
        root.rglob("capitalizer-*-v3-m3-microstructure-context-2y-v1-rows.jsonl")
    )
    if len(paths) != 1:
        raise ValueError("CISD-or-M5 experiment requires one microstructure row ledger")
    result: dict[tuple[str, str], CapitalizerM5DirectionalState] = {}
    with paths[0].open(encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            raw = json.loads(line)
            if not isinstance(raw, dict):
                raise ValueError("microstructure row must be object")
            key = (str(raw["closeback_at"]), str(raw["side"]))
            state = classify_m5_directional_state(
                side=CapitalizerSide(str(raw["side"])),
                microstructure_signature=str(raw["microstructure_signature"]),
            )
            if key in result:
                raise ValueError(f"duplicate M5 state key: {key}")
            result[key] = state
    if not result:
        raise ValueError("CISD-or-M5 experiment requires non-empty M5 state lookup")
    return result


def _confirmation_route_key(
    *,
    closeback_at: datetime,
    side: CapitalizerSide,
    confirmed_at: datetime,
) -> str:
    return "|".join((closeback_at.isoformat(), side.value, confirmed_at.isoformat()))


@contextmanager
def _cisd_or_m5_confirmation(
    lookup: dict[tuple[str, str], CapitalizerM5DirectionalState],
    counters: Counter[str],
    routes: dict[str, str],
) -> Iterator[None]:
    original = v3._find_m3_mss

    def variant(
        bars: Any,
        closes: Any,
        pivots: Any,
        *,
        after: datetime,
        before: datetime,
        side: CapitalizerSide,
    ) -> v3.M3MssEvent | None:
        start = bisect.bisect_right(closes, after)
        end = bisect.bisect_right(closes, before)
        break_kind = "HIGH" if side is CapitalizerSide.LONG else "LOW"
        state = lookup.get((after.isoformat(), side.value))
        if state is None:
            counters["M5_STATE_LOOKUP_MISSING"] += 1
            return None
        counters[f"M5_STATE_{state.value}_MSS_SEARCH"] += 1

        for index in range(start, end):
            bar = bars[index]
            source = bar.source
            full_range = source.high - source.low
            if full_range <= 0:
                continue
            directional = (
                source.close > source.open
                if side is CapitalizerSide.LONG
                else source.close < source.open
            )
            if not directional:
                continue
            body_ratio = abs(source.close - source.open) / full_range
            if body_ratio < v3.BODY_RATIO_MIN:
                continue
            atr = v3._atr14(bars, index)
            if atr is None or full_range <= v3.ATR_MULTIPLIER * atr:
                continue
            broken = v3._latest_pivot(
                pivots,
                before=bar.opened_at,
                kind=break_kind,
            )
            if broken is None:
                continue
            structure_break = (
                source.close > broken.price
                if side is CapitalizerSide.LONG
                else source.close < broken.price
            )
            if not structure_break:
                continue

            boundary = v3._opposing_series_boundary(
                bars,
                index=index,
                side=side,
            )
            if boundary is None:
                if state is CapitalizerM5DirectionalState.ALIGNED:
                    counters["M5_SUBSTITUTE_BOUNDARY_MISSING_REJECTED"] += 1
                continue

            cisd_break = (
                source.close > boundary
                if side is CapitalizerSide.LONG
                else source.close < boundary
            )
            m5_substitute = (
                not cisd_break
                and state is CapitalizerM5DirectionalState.ALIGNED
            )
            if not cisd_break and not m5_substitute:
                continue

            route = "CISD" if cisd_break else "M5_ALIGNED_SUBSTITUTE"
            counters[f"M3_CONFIRMATION_ROUTE_{route}"] += 1
            event = v3.M3MssEvent(
                side=side,
                confirmed_at=bar.closed_at,
                displacement_opened_at=bar.opened_at,
                displacement_closed_at=bar.closed_at,
                broken_swing_price=broken.price,
                cisd_boundary=boundary,
                body_ratio=body_ratio,
                atr14=atr,
                displacement_range=full_range,
            )
            routes[
                _confirmation_route_key(
                    closeback_at=after,
                    side=side,
                    confirmed_at=event.confirmed_at,
                )
            ] = route
            return event
        return None

    try:
        v3._find_m3_mss = variant
        yield
    finally:
        v3._find_m3_mss = original


def _trade_route(trade: v3.V3Trade, routes: dict[str, str]) -> str:
    key = "|".join((trade.m5_closeback_at, trade.side, trade.m3_mss_at))
    return routes.get(key, "UNKNOWN")


def build_market_report(
    m1_root: Path,
    micro_root: Path,
    *,
    session: CapitalizerSession,
) -> tuple[dict[str, Any], tuple[v3.V3Trade, ...], dict[str, str]]:
    lookup = _load_state_lookup(micro_root)
    counters: Counter[str] = Counter()
    routes: dict[str, str] = {}
    with _cisd_or_m5_confirmation(lookup, counters, routes), _v3_window():
        source_report, trades = v3.build_market_report(m1_root, session=session)

    trade_routes = Counter(_trade_route(trade, routes) for trade in trades)
    if trade_routes.get("UNKNOWN", 0):
        raise ValueError("every executed trade must retain an M3 confirmation route")

    report = asdict(source_report)
    report.update(
        {
            "identity": IDENTITY,
            "source_strategy_identity": v3.IDENTITY,
            "state_identity": STATE_IDENTITY,
            "window_start": WINDOW_START.isoformat(),
            "window_end_exclusive": WINDOW_END.isoformat(),
            "lookback_start": LOOKBACK_START.isoformat(),
            "confirmation_counters": dict(sorted(counters.items())),
            "raw_trade_routes": dict(sorted(trade_routes.items())),
            "state_lookup_rows": len(lookup),
            "variant_only_change": "SAME_BAR_CISD_BREAK_OR_M5_ALIGNED",
            "cisd_boundary_still_required": True,
            "swing_break_changed": False,
            "body_threshold_changed": False,
            "atr_threshold_changed": False,
            "fvg_changed": False,
            "stop_changed": False,
            "target_changed": False,
            "max3_changed": False,
            "outcome_used_for_admission": False,
            "diagnostic_window_role": "CONSUMED_DIAGNOSTIC_RESEARCH",
            "experiment_role": "DENSITY_REDUNDANCY_TEST",
            "economic_candidate": False,
            "rule_promotion_allowed": False,
            "trader_certified": False,
            "live_authorized": False,
            "real_capital_authorized": False,
        }
    )
    return report, trades, routes


def write_market(
    report: dict[str, Any],
    trades: tuple[v3.V3Trade, ...],
    routes: dict[str, str],
    output: Path,
) -> None:
    output.mkdir(parents=True, exist_ok=True)
    symbol = str(report["symbol"]).lower()
    stem = f"capitalizer-{symbol}-v3-cisd-or-m5-aligned-2y-v1"
    (output / f"{stem}.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    with (output / f"{stem}-trades.jsonl").open("w", encoding="utf-8") as handle:
        for trade in trades:
            row = asdict(trade)
            row["m3_confirmation_route"] = _trade_route(trade, routes)
            handle.write(json.dumps(row, sort_keys=True) + "\n")


def _load_reports(root: Path) -> list[dict[str, Any]]:
    paths = sorted(root.rglob("capitalizer-*-v3-cisd-or-m5-aligned-2y-v1.json"))
    if len(paths) != 9:
        raise ValueError(f"CISD-or-M5 matrix requires 9 reports, got {len(paths)}")
    reports = [dict(json.loads(path.read_text(encoding="utf-8"))) for path in paths]
    if {str(item["symbol"]) for item in reports} != v3.EXPECTED_SYMBOLS:
        raise ValueError("CISD-or-M5 universe mismatch")
    return reports


def _load_trade_rows(root: Path) -> tuple[dict[str, Any], ...]:
    rows: list[dict[str, Any]] = []
    for path in sorted(root.rglob("capitalizer-*-v3-cisd-or-m5-aligned-2y-v1-trades.jsonl")):
        with path.open(encoding="utf-8") as handle:
            for line in handle:
                if line.strip():
                    raw = json.loads(line)
                    if not isinstance(raw, dict):
                        raise ValueError("variant trade row must be object")
                    rows.append(raw)
    return tuple(
        sorted(
            rows,
            key=lambda item: (
                datetime.fromisoformat(str(item["entry_at"])),
                str(item["symbol"]),
            ),
        )
    )


def _to_trade(row: dict[str, Any]) -> v3.V3Trade:
    clean = {key: value for key, value in row.items() if key != "m3_confirmation_route"}
    return v3.V3Trade(**clean)


def _metrics_dict(trades: tuple[v3.V3Trade, ...]) -> dict[str, Any] | None:
    value = v3._metrics(trades)
    return None if value is None else asdict(value)


def build_matrix(root: Path) -> dict[str, Any]:
    reports = _load_reports(root)
    rows = _load_trade_rows(root)
    raw = tuple(_to_trade(row) for row in rows)
    max3 = v3._portfolio_max3(raw)
    metrics = v3._metrics(max3)
    if metrics is None or metrics.profit_factor is None or metrics.mean_r is None:
        raise ValueError("CISD-or-M5 experiment requires complete MAX3 metrics")

    route_lookup = {
        (
            str(row["symbol"]),
            str(row["entry_at"]),
            str(row["m5_closeback_at"]),
            str(row["m3_mss_at"]),
        ): str(row["m3_confirmation_route"])
        for row in rows
    }
    max3_routes: Counter[str] = Counter()
    for trade in max3:
        key = (
            trade.symbol,
            trade.entry_at,
            trade.m5_closeback_at,
            trade.m3_mss_at,
        )
        route = route_lookup.get(key)
        if route is None:
            raise ValueError("MAX3 trade lost confirmation provenance")
        max3_routes[route] += 1

    per_session: dict[str, dict[str, Any]] = {}
    for session in CapitalizerSession:
        selected = tuple(item for item in max3 if item.session == session.value)
        per_session[session.value] = {
            "trades": len(selected),
            "metrics": _metrics_dict(selected),
        }

    per_market: dict[str, dict[str, Any]] = {}
    for symbol in sorted(v3.EXPECTED_SYMBOLS):
        selected = tuple(item for item in max3 if item.symbol == symbol)
        per_market[symbol] = {
            "trades": len(selected),
            "metrics": _metrics_dict(selected),
        }

    counters: Counter[str] = Counter()
    for report in reports:
        raw_counts = report["confirmation_counters"]
        if not isinstance(raw_counts, dict):
            raise ValueError("confirmation_counters must be mapping")
        for key, value in raw_counts.items():
            counters[str(key)] += int(value)

    return {
        "identity": MATRIX_IDENTITY,
        "source_strategy_identity": v3.IDENTITY,
        "state_identity": STATE_IDENTITY,
        "market_count": 9,
        "window_start": WINDOW_START.isoformat(),
        "window_end_exclusive": WINDOW_END.isoformat(),
        "confirmation_counters": dict(sorted(counters.items())),
        "raw_trades": len(raw),
        "max3_selected_trades": len(max3),
        "max3_metrics": asdict(metrics),
        "max3_confirmation_routes": dict(sorted(max3_routes.items())),
        "per_session": per_session,
        "per_market": per_market,
        "baseline_max3_trades": BASELINE_MAX3_TRADES,
        "baseline_pf": str(BASELINE_PF),
        "baseline_total_r": str(BASELINE_TOTAL_R),
        "baseline_mean_r": str(BASELINE_MEAN_R),
        "baseline_dd_r": str(BASELINE_DD_R),
        "baseline_losing_streak": BASELINE_LOSING_STREAK,
        "clean_same_bar_cisd_only": CLEAN_SAME_BAR_CISD_ONLY,
        "clean_same_bar_cisd_only_aligned": CLEAN_SAME_BAR_CISD_ONLY_ALIGNED,
        "trade_delta_vs_baseline": len(max3) - BASELINE_MAX3_TRADES,
        "pf_ratio_vs_baseline": str(Decimal(metrics.profit_factor) / BASELINE_PF),
        "total_r_delta_vs_baseline": str(Decimal(metrics.total_r) - BASELINE_TOTAL_R),
        "mean_r_delta_vs_baseline": str(Decimal(metrics.mean_r) - BASELINE_MEAN_R),
        "dd_delta_vs_baseline": str(
            Decimal(metrics.max_drawdown_r) - BASELINE_DD_R
        ),
        "variant_only_change": "SAME_BAR_CISD_BREAK_OR_M5_ALIGNED",
        "cisd_boundary_still_required": True,
        "swing_break_changed": False,
        "body_threshold_changed": False,
        "atr_threshold_changed": False,
        "fvg_changed": False,
        "stop_changed": False,
        "target_changed": False,
        "max3_changed": False,
        "outcome_used_for_admission": False,
        "diagnostic_window_role": "CONSUMED_DIAGNOSTIC_RESEARCH",
        "experiment_role": "DENSITY_REDUNDANCY_TEST",
        "economic_candidate": False,
        "rule_promotion_allowed": False,
        "trader_certified": False,
        "live_authorized": False,
        "real_capital_authorized": False,
    }


def write_matrix(
    report: dict[str, Any],
    output: Path,
) -> None:
    output.mkdir(parents=True, exist_ok=True)
    path = output / "capitalizer-nine-market-v3-cisd-or-m5-aligned-2y-v1.json"
    path.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    market = sub.add_parser("market")
    market.add_argument("m1_root", type=Path)
    market.add_argument("micro_root", type=Path)
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
        market_report, trades, routes = build_market_report(
            args.m1_root,
            args.micro_root,
            session=CapitalizerSession(args.session),
        )
        write_market(market_report, trades, routes, args.output)
        print(json.dumps(market_report, sort_keys=True))
        return

    matrix_report = build_matrix(args.input_root)
    write_matrix(matrix_report, args.output)
    print(json.dumps(matrix_report, sort_keys=True))


if __name__ == "__main__":
    main()
