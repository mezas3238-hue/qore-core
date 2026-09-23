"""Informational V3 2Y experiment: require frozen M5 ALIGNED state.

The frozen V3 raw trade ledger is joined to the already-causal M5 microstructure state at
m5_closeback_at. Only ALIGNED rows are retained, then the original portfolio MAX3 ceiling
is reapplied globally. No V3 signal, lifecycle, stop, target, or sizing rule is recomputed.

Purpose: measure whether frozen M5 directional state adds information to already-valid V3
trades. This is consumed diagnostic research, not a promotion candidate.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from decimal import Decimal
from pathlib import Path
from typing import Any

from qore.infrastructure.trader_lab import (
    capitalizer_owner_h1_m3_m1_causal_reversal_1y_v3 as v3,
)
from qore.infrastructure.trader_lab.capitalizer_contract import CapitalizerSession
from qore.infrastructure.trader_lab.capitalizer_exposure_graph import CapitalizerSide
from qore.infrastructure.trader_lab.capitalizer_v3_m5_directional_state_v1 import (
    IDENTITY as STATE_IDENTITY,
)
from qore.infrastructure.trader_lab.capitalizer_v3_m5_directional_state_v1 import (
    CapitalizerM5DirectionalState,
    classify_m5_directional_state,
)

IDENTITY = "QORE_CAPITALIZER_V3_M5_ALIGNED_GATE_EXPERIMENT_2Y_V1"
MATRIX_IDENTITY = (
    "QORE_CAPITALIZER_NINE_MARKET_V3_M5_ALIGNED_GATE_EXPERIMENT_2Y_V1"
)

BASELINE_RAW_TRADES = 475
BASELINE_MAX3_TRADES = 474
BASELINE_PF = Decimal("1.283270342004661566350801358")
BASELINE_TOTAL_R = Decimal("50.34686423146549474995387094")
BASELINE_MEAN_R = Decimal("0.1062170131465516766876663944")
BASELINE_DD_R = Decimal("13.43559872546085473546771142")
BASELINE_LOSING_STREAK = 8


def _load_trades(root: Path) -> tuple[v3.V3Trade, ...]:
    paths = sorted(root.rglob("capitalizer-*-v3-frozen-replay-2y-v1-trades.jsonl"))
    if len(paths) != 1:
        raise ValueError("M5-aligned experiment requires one V3 market trade ledger")
    rows: list[v3.V3Trade] = []
    with paths[0].open(encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                rows.append(v3.V3Trade(**json.loads(line)))
    return tuple(rows)


def _load_micro_rows(root: Path) -> dict[str, dict[str, Any]]:
    paths = sorted(
        root.rglob("capitalizer-*-v3-m3-microstructure-context-2y-v1-rows.jsonl")
    )
    if len(paths) != 1:
        raise ValueError("M5-aligned experiment requires one microstructure row ledger")
    result: dict[str, dict[str, Any]] = {}
    with paths[0].open(encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            raw = json.loads(line)
            if not isinstance(raw, dict):
                raise ValueError("microstructure row must be object")
            key = str(raw["closeback_at"])
            if key in result:
                raise ValueError("duplicate microstructure closeback timestamp")
            result[key] = raw
    return result


def _gate_state(trade: v3.V3Trade, micro: dict[str, dict[str, Any]]) -> str:
    raw = micro.get(trade.m5_closeback_at)
    if raw is None:
        raise ValueError(
            f"missing M5 state for {trade.symbol} closeback {trade.m5_closeback_at}"
        )
    if str(raw["side"]) != trade.side:
        raise ValueError("microstructure/trade side mismatch")
    return classify_m5_directional_state(
        side=CapitalizerSide(trade.side),
        microstructure_signature=str(raw["microstructure_signature"]),
    ).value


def build_market_report(
    replay_root: Path,
    micro_root: Path,
) -> tuple[dict[str, Any], tuple[v3.V3Trade, ...]]:
    trades = _load_trades(replay_root)
    micro = _load_micro_rows(micro_root)
    if not trades:
        raise ValueError("M5-aligned experiment requires raw V3 trades")

    symbols = {trade.symbol for trade in trades}
    sessions = {trade.session for trade in trades}
    if len(symbols) != 1 or len(sessions) != 1:
        raise ValueError("market experiment requires one symbol/session")
    symbol = next(iter(symbols))
    session = next(iter(sessions))

    state_counts = {
        CapitalizerM5DirectionalState.ALIGNED.value: 0,
        CapitalizerM5DirectionalState.OPPOSED.value: 0,
        CapitalizerM5DirectionalState.NEUTRAL.value: 0,
    }
    selected: list[v3.V3Trade] = []
    for trade in trades:
        state = _gate_state(trade, micro)
        state_counts[state] += 1
        if state == CapitalizerM5DirectionalState.ALIGNED.value:
            selected.append(trade)

    selected_tuple = tuple(selected)
    baseline_metrics = v3._metrics(trades)
    gated_metrics = v3._metrics(selected_tuple)
    if baseline_metrics is None or gated_metrics is None:
        raise ValueError("market metrics unavailable")

    return {
        "identity": IDENTITY,
        "state_identity": STATE_IDENTITY,
        "symbol": symbol,
        "session": session,
        "baseline_raw_trades": len(trades),
        "state_counts": state_counts,
        "aligned_raw_trades": len(selected_tuple),
        "raw_retention_rate": str(
            Decimal(len(selected_tuple)) / Decimal(len(trades))
        ),
        "baseline_raw_metrics": asdict(baseline_metrics),
        "aligned_raw_metrics": asdict(gated_metrics),
        "gate_uses_closeback_time_information_only": True,
        "neutral_is_fail_closed": True,
        "max3_reapplied_after_gate": False,
        "v3_signal_recomputed": False,
        "strategy_mutated": False,
        "stop_mutated": False,
        "target_mutated": False,
        "outcome_used_for_admission": False,
        "diagnostic_only": True,
        "economic_candidate": False,
        "fresh_holdout_claimed": False,
    }, selected_tuple


def write_market(
    report: dict[str, Any],
    trades: tuple[v3.V3Trade, ...],
    output: Path,
) -> None:
    output.mkdir(parents=True, exist_ok=True)
    symbol = str(report["symbol"]).lower()
    stem = f"capitalizer-{symbol}-v3-m5-aligned-gate-experiment-2y-v1"
    (output / f"{stem}.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    with (output / f"{stem}-trades.jsonl").open("w", encoding="utf-8") as handle:
        for trade in trades:
            handle.write(json.dumps(asdict(trade), sort_keys=True) + "\n")


def _load_reports(root: Path) -> list[dict[str, Any]]:
    paths = sorted(
        root.rglob("capitalizer-*-v3-m5-aligned-gate-experiment-2y-v1.json")
    )
    if len(paths) != 9:
        raise ValueError(f"M5-aligned matrix requires 9 reports, got {len(paths)}")
    return [dict(json.loads(path.read_text(encoding="utf-8"))) for path in paths]


def _load_selected_trades(root: Path) -> tuple[v3.V3Trade, ...]:
    rows: list[v3.V3Trade] = []
    for path in sorted(
        root.rglob("capitalizer-*-v3-m5-aligned-gate-experiment-2y-v1-trades.jsonl")
    ):
        with path.open(encoding="utf-8") as handle:
            for line in handle:
                if line.strip():
                    rows.append(v3.V3Trade(**json.loads(line)))
    return tuple(rows)


def _metric_delta(
    *,
    gated: v3.V3Metrics,
) -> dict[str, str | int]:
    return {
        "trades_delta": gated.trades - BASELINE_MAX3_TRADES,
        "trades_retention_rate": str(
            Decimal(gated.trades) / Decimal(BASELINE_MAX3_TRADES)
        ),
        "profit_factor_delta": str(gated.profit_factor - BASELINE_PF),
        "profit_factor_relative_change": str(
            gated.profit_factor / BASELINE_PF - Decimal("1")
        ),
        "total_r_delta": str(gated.total_r - BASELINE_TOTAL_R),
        "mean_r_delta": str(gated.mean_r - BASELINE_MEAN_R),
        "max_drawdown_r_delta": str(gated.max_drawdown_r - BASELINE_DD_R),
        "losing_streak_delta": gated.max_losing_streak - BASELINE_LOSING_STREAK,
    }


def build_matrix(root: Path) -> dict[str, Any]:
    reports = _load_reports(root)
    raw_selected = _load_selected_trades(root)
    gated_max3 = v3._portfolio_max3(raw_selected)
    raw_metrics = v3._metrics(raw_selected)
    max3_metrics = v3._metrics(gated_max3)
    if raw_metrics is None or max3_metrics is None:
        raise ValueError("aggregate M5-aligned metrics unavailable")

    per_session: dict[str, dict[str, Any]] = {}
    for session in CapitalizerSession:
        session_raw = tuple(
            item for item in raw_selected if item.session == session.value
        )
        session_max3 = tuple(
            item for item in gated_max3 if item.session == session.value
        )
        raw_value = v3._metrics(session_raw)
        max3_value = v3._metrics(session_max3)
        per_session[session.value] = {
            "raw_trades": len(session_raw),
            "raw_metrics": None if raw_value is None else asdict(raw_value),
            "max3_trades": len(session_max3),
            "max3_metrics": None if max3_value is None else asdict(max3_value),
        }

    state_totals = {
        CapitalizerM5DirectionalState.ALIGNED.value: 0,
        CapitalizerM5DirectionalState.OPPOSED.value: 0,
        CapitalizerM5DirectionalState.NEUTRAL.value: 0,
    }
    for report in reports:
        raw_states = report["state_counts"]
        if not isinstance(raw_states, dict):
            raise ValueError("state_counts must be mapping")
        for state, count in raw_states.items():
            state_totals[str(state)] += int(count)

    baseline_raw = sum(int(item["baseline_raw_trades"]) for item in reports)
    aligned_raw = len(raw_selected)
    return {
        "identity": MATRIX_IDENTITY,
        "state_identity": STATE_IDENTITY,
        "market_count": 9,
        "baseline_raw_trades": baseline_raw,
        "baseline_raw_control_reproduced": baseline_raw == BASELINE_RAW_TRADES,
        "baseline_max3_trades": BASELINE_MAX3_TRADES,
        "state_counts_on_baseline_raw_trades": state_totals,
        "aligned_raw_trades": aligned_raw,
        "aligned_raw_metrics": asdict(raw_metrics),
        "aligned_max3_trades": len(gated_max3),
        "aligned_max3_metrics": asdict(max3_metrics),
        "max3_reapplied_after_gate": True,
        "comparison_to_v3_2y_max3": _metric_delta(gated=max3_metrics),
        "per_session": per_session,
        "markets": sorted(reports, key=lambda item: str(item["symbol"])),
        "gate_uses_closeback_time_information_only": True,
        "neutral_is_fail_closed": True,
        "v3_signal_recomputed": False,
        "strategy_mutated": False,
        "stop_mutated": False,
        "target_mutated": False,
        "outcome_used_for_admission": False,
        "diagnostic_only": True,
        "economic_candidate": False,
        "fresh_holdout_claimed": False,
    }


def write_matrix(report: dict[str, Any], output: Path) -> None:
    output.mkdir(parents=True, exist_ok=True)
    path = (
        output
        / "capitalizer-nine-market-v3-m5-aligned-gate-experiment-2y-v1.json"
    )
    path.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    market = sub.add_parser("market")
    market.add_argument("replay_root", type=Path)
    market.add_argument("micro_root", type=Path)
    market.add_argument("output", type=Path)
    matrix = sub.add_parser("matrix")
    matrix.add_argument("input_root", type=Path)
    matrix.add_argument("output", type=Path)
    args = parser.parse_args()

    if args.command == "market":
        report, trades = build_market_report(args.replay_root, args.micro_root)
        write_market(report, trades, args.output)
        print(json.dumps(report, sort_keys=True))
        return

    report = build_matrix(args.input_root)
    write_matrix(report, args.output)
    print(json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    main()
