"""Informational V3 2Y experiment with one additional frozen M5 ALIGNED gate.

Only experimental change:
    after frozen V3 selects its M5 closeback, require the frozen causal M5 directional
    state to be ALIGNED.

Everything downstream remains frozen V3: M3 swing/CISD/body/ATR, causal M1 OB+FVG,
entry, stop, target/lifecycle, and portfolio MAX3.
"""

from __future__ import annotations

import argparse
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

IDENTITY = "QORE_CAPITALIZER_V3_M5_ALIGNED_GATE_2Y_V1"
MATRIX_IDENTITY = "QORE_CAPITALIZER_NINE_MARKET_V3_M5_ALIGNED_GATE_2Y_V1"
BASELINE_IDENTITY = "QORE_CAPITALIZER_NINE_MARKET_V3_FROZEN_REPLAY_2Y_V1"
BASELINE_MAX3_TRADES = 474
BASELINE_PF = Decimal("1.283270342004661566350801358")
BASELINE_TOTAL_R = Decimal("50.34686423146549474995387094")
BASELINE_MEAN_R = Decimal("0.1062170131465516766876663944")
BASELINE_DD_R = Decimal("13.43559872546085473546771142")
BASELINE_LOSING_STREAK = 8


def _load_state_lookup(root: Path) -> dict[tuple[str, str], CapitalizerM5DirectionalState]:
    paths = sorted(
        root.rglob("capitalizer-*-v3-m3-microstructure-context-2y-v1-rows.jsonl")
    )
    if len(paths) != 1:
        raise ValueError("M5-aligned experiment requires one microstructure row ledger")
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
                side=v3.CapitalizerSide(str(raw["side"])),
                microstructure_signature=str(raw["microstructure_signature"]),
            )
            if key in result:
                raise ValueError(f"duplicate closeback/side state key: {key}")
            result[key] = state
    if not result:
        raise ValueError("M5-aligned experiment requires non-empty state lookup")
    return result


@contextmanager
def _aligned_closeback_gate(
    lookup: dict[tuple[str, str], CapitalizerM5DirectionalState],
    counters: Counter[str],
) -> Iterator[None]:
    original = getattr(v3, "_find_sweep_closeback")

    def gated(*args: Any, **kwargs: Any) -> tuple[bool, v3.SweepCloseback | None]:
        sweep_seen, closeback = original(*args, **kwargs)
        if closeback is None:
            return sweep_seen, None
        counters["M5_CLOSEBACK_SELECTED_BY_V3"] += 1
        key = (closeback.closeback_at.isoformat(), closeback.side.value)
        state = lookup.get(key)
        if state is None:
            counters["M5_STATE_LOOKUP_MISSING"] += 1
            return sweep_seen, None
        counters[f"M5_STATE_{state.value}"] += 1
        if state is not CapitalizerM5DirectionalState.ALIGNED:
            counters["M5_ALIGNED_GATE_REJECTED"] += 1
            return sweep_seen, None
        counters["M5_ALIGNED_GATE_PASSED"] += 1
        return sweep_seen, closeback

    try:
        setattr(v3, "_find_sweep_closeback", gated)
        yield
    finally:
        setattr(v3, "_find_sweep_closeback", original)


def build_market_report(
    m1_root: Path,
    micro_root: Path,
    *,
    session: CapitalizerSession,
) -> tuple[dict[str, Any], tuple[v3.V3Trade, ...]]:
    lookup = _load_state_lookup(micro_root)
    counters: Counter[str] = Counter()
    with _aligned_closeback_gate(lookup, counters), _v3_window():
        source_report, trades = v3.build_market_report(m1_root, session=session)

    report = asdict(source_report)
    report.update(
        {
            "identity": IDENTITY,
            "source_strategy_identity": v3.IDENTITY,
            "state_identity": STATE_IDENTITY,
            "window_start": WINDOW_START.isoformat(),
            "window_end_exclusive": WINDOW_END.isoformat(),
            "lookback_start": LOOKBACK_START.isoformat(),
            "gate_counters": dict(sorted(counters.items())),
            "state_lookup_rows": len(lookup),
            "variant_only_change": "REQUIRE_M5_ALIGNED_AT_V3_SELECTED_CLOSEBACK",
            "baseline_v3_source_unchanged": True,
            "swing_break_changed": False,
            "cisd_changed": False,
            "body_threshold_changed": False,
            "atr_threshold_changed": False,
            "fvg_changed": False,
            "stop_changed": False,
            "target_changed": False,
            "max3_changed": False,
            "outcome_used_for_admission": False,
            "neutral_fail_closed": True,
            "diagnostic_window_role": "CONSUMED_DIAGNOSTIC_RESEARCH",
            "experiment_role": "INFORMATIONAL_INCREMENTAL_VALUE_TEST",
            "economic_candidate": False,
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
    stem = f"capitalizer-{symbol}-v3-m5-aligned-gate-2y-v1"
    (output / f"{stem}.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    with (output / f"{stem}-trades.jsonl").open("w", encoding="utf-8") as handle:
        for trade in trades:
            handle.write(json.dumps(asdict(trade), sort_keys=True) + "\n")


def _load_reports(root: Path) -> list[dict[str, Any]]:
    paths = sorted(root.rglob("capitalizer-*-v3-m5-aligned-gate-2y-v1.json"))
    if len(paths) != 9:
        raise ValueError(f"M5-aligned matrix requires 9 reports, got {len(paths)}")
    reports = [dict(json.loads(path.read_text(encoding="utf-8"))) for path in paths]
    if {str(item["symbol"]) for item in reports} != v3.EXPECTED_SYMBOLS:
        raise ValueError("M5-aligned universe mismatch")
    return reports


def _load_trades(root: Path) -> tuple[v3.V3Trade, ...]:
    result: list[v3.V3Trade] = []
    for path in sorted(root.rglob("capitalizer-*-v3-m5-aligned-gate-2y-v1-trades.jsonl")):
        with path.open(encoding="utf-8") as handle:
            for line in handle:
                if line.strip():
                    result.append(v3.V3Trade(**json.loads(line)))
    return tuple(
        sorted(
            result,
            key=lambda item: (datetime.fromisoformat(item.entry_at), item.symbol),
        )
    )


def _metrics_dict(trades: tuple[v3.V3Trade, ...]) -> dict[str, Any] | None:
    value = v3._metrics(trades)
    return None if value is None else asdict(value)


def build_matrix(root: Path) -> dict[str, Any]:
    reports = _load_reports(root)
    raw = _load_trades(root)
    max3 = v3._portfolio_max3(raw)
    metrics = v3._metrics(max3)
    if metrics is None:
        raise ValueError("M5-aligned experiment produced no MAX3 trades")

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

    gate_totals: Counter[str] = Counter()
    for report in reports:
        raw_gate = report["gate_counters"]
        if not isinstance(raw_gate, dict):
            raise ValueError("gate_counters must be mapping")
        for key, value in raw_gate.items():
            gate_totals[str(key)] += int(value)

    return {
        "identity": MATRIX_IDENTITY,
        "baseline_identity": BASELINE_IDENTITY,
        "source_strategy_identity": v3.IDENTITY,
        "state_identity": STATE_IDENTITY,
        "market_count": 9,
        "window_start": WINDOW_START.isoformat(),
        "window_end_exclusive": WINDOW_END.isoformat(),
        "gate_counters": dict(sorted(gate_totals.items())),
        "raw_trades": len(raw),
        "max3_selected_trades": len(max3),
        "max3_metrics": asdict(metrics),
        "per_session": per_session,
        "per_market": per_market,
        "baseline_max3_trades": BASELINE_MAX3_TRADES,
        "baseline_pf": str(BASELINE_PF),
        "baseline_total_r": str(BASELINE_TOTAL_R),
        "baseline_mean_r": str(BASELINE_MEAN_R),
        "baseline_dd_r": str(BASELINE_DD_R),
        "baseline_losing_streak": BASELINE_LOSING_STREAK,
        "trade_retention_vs_baseline": str(
            Decimal(len(max3)) / Decimal(BASELINE_MAX3_TRADES)
        ),
        "pf_ratio_vs_baseline": str(
            Decimal(metrics.profit_factor) / BASELINE_PF
        ),
        "total_r_delta_vs_baseline": str(
            Decimal(metrics.total_r) - BASELINE_TOTAL_R
        ),
        "mean_r_delta_vs_baseline": str(
            Decimal(metrics.mean_r) - BASELINE_MEAN_R
        ),
        "dd_delta_vs_baseline": str(
            Decimal(metrics.max_drawdown_r) - BASELINE_DD_R
        ),
        "variant_only_change": "REQUIRE_M5_ALIGNED_AT_V3_SELECTED_CLOSEBACK",
        "baseline_v3_source_unchanged": True,
        "swing_break_changed": False,
        "cisd_changed": False,
        "body_threshold_changed": False,
        "atr_threshold_changed": False,
        "fvg_changed": False,
        "stop_changed": False,
        "target_changed": False,
        "max3_changed": False,
        "outcome_used_for_admission": False,
        "neutral_fail_closed": True,
        "diagnostic_window_role": "CONSUMED_DIAGNOSTIC_RESEARCH",
        "experiment_role": "INFORMATIONAL_INCREMENTAL_VALUE_TEST",
        "economic_candidate": False,
        "rule_promotion_allowed": False,
        "trader_certified": False,
        "live_authorized": False,
        "real_capital_authorized": False,
    }


def write_matrix(
    report: dict[str, Any],
    output: Path,
    *,
    source_root: Path,
) -> None:
    output.mkdir(parents=True, exist_ok=True)
    path = output / "capitalizer-nine-market-v3-m5-aligned-gate-2y-v1.json"
    path.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    max3 = v3._portfolio_max3(_load_trades(source_root))
    ledger = output / "capitalizer-nine-market-v3-m5-aligned-gate-2y-v1-max3-trades.jsonl"
    with ledger.open("w", encoding="utf-8") as handle:
        for trade in max3:
            handle.write(json.dumps(asdict(trade), sort_keys=True) + "\n")


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
        report, trades = build_market_report(
            args.m1_root,
            args.micro_root,
            session=CapitalizerSession(args.session),
        )
        write_market(report, trades, args.output)
        print(json.dumps(report, sort_keys=True))
        return

    report = build_matrix(args.input_root)
    write_matrix(report, args.output, source_root=args.input_root)
    print(json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    main()
