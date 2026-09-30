"""Consumed-window A/B: No-Rearm plus minimal ATR relaxation to >1.10.

Frozen before economics from the outcome-free ATR readiness atlas:
- original universal ATR requirement is displacement range > 1.20 * ATR14;
- 829 residual SOURCE_FIRST blockers satisfy every other same-bar requirement;
- the nearest predeclared readiness band is 1.10 <= ratio <= 1.20;
- this candidate tests only the minimal adjacent relaxation: >1.10 * ATR14.

The No-Rearm architecture remains mandatory: an armed WAIT setup abstains unless
new causal evidence creates a new independent setup.

No market/session/side/PnL result is used for admission. This is consumed 2Y
development evidence only.
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
    capitalizer_v3_source_first_wait5_no_rearm_abstain_2y_v1 as no_rearm,
)
from qore.infrastructure.trader_lab.capitalizer_contract import CapitalizerSession

IDENTITY = "QORE_CAPITALIZER_V3_SOURCE_FIRST_NO_REARM_ATR110_2Y_V1"
MATRIX_IDENTITY = "QORE_CAPITALIZER_NINE_MARKET_V3_SOURCE_FIRST_NO_REARM_ATR110_2Y_V1"
FROZEN_ATR_MULTIPLIER = Decimal("1.10")
ORIGINAL_ATR_MULTIPLIER = Decimal("1.20")

BASELINE_MAX3 = 793
BASELINE_PF = Decimal("1.591302271555862985264867662")
BASELINE_TOTAL_R = Decimal("160.4161625060456517859037840")
BASELINE_MEAN_R = Decimal("0.2022902427566779972079492863")
BASELINE_DD_R = Decimal("11.34554432703924017558271105")
BASELINE_LS = 8


@contextmanager
def _atr110_patch() -> Iterator[None]:
    mutable_v3: Any = v3
    original = mutable_v3.ATR_MULTIPLIER
    try:
        mutable_v3.ATR_MULTIPLIER = FROZEN_ATR_MULTIPLIER
        yield
    finally:
        mutable_v3.ATR_MULTIPLIER = original


def build_market_report(
    m1_root: Path,
    *,
    session: CapitalizerSession,
) -> tuple[dict[str, Any], tuple[v3.V3Trade, ...]]:
    with _atr110_patch():
        report, trades = no_rearm.build_market_report(
            m1_root,
            session=session,
        )
    report.update(
        {
            "identity": IDENTITY,
            "variant_only_change": "SOURCE_FIRST_ATR_MULTIPLIER_1_20_TO_1_10",
            "atr_multiplier_original": str(ORIGINAL_ATR_MULTIPLIER),
            "atr_multiplier_candidate": str(FROZEN_ATR_MULTIPLIER),
            "minimal_adjacent_relaxation": True,
            "same_no_rearm_architecture": True,
            "same_source_first_boundary": True,
            "same_body_threshold": True,
            "same_swing_break": True,
            "same_cisd_requirement": True,
            "same_fvg": True,
            "same_stop": True,
            "same_target": True,
            "same_h1_deadline": True,
            "same_max3": True,
            "outcome_used_for_admission": False,
            "readiness_atlas_used_outcomes": False,
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
    )
    return report, trades


def write_market(
    report: dict[str, Any],
    trades: tuple[v3.V3Trade, ...],
    output: Path,
) -> None:
    output.mkdir(parents=True, exist_ok=True)
    symbol = str(report["symbol"]).lower()
    stem = f"capitalizer-{symbol}-v3-source-first-no-rearm-atr110-2y-v1"
    (output / f"{stem}.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    with (output / f"{stem}-trades.jsonl").open("w", encoding="utf-8") as handle:
        for trade in trades:
            handle.write(json.dumps(asdict(trade), sort_keys=True) + "\n")


def _load_reports(root: Path) -> list[dict[str, Any]]:
    paths = sorted(
        root.rglob("capitalizer-*-v3-source-first-no-rearm-atr110-2y-v1.json")
    )
    if len(paths) != 9:
        raise ValueError(f"ATR110 matrix requires 9 reports, got {len(paths)}")
    reports = [dict(json.loads(path.read_text(encoding="utf-8"))) for path in paths]
    if {str(item["symbol"]) for item in reports} != v3.EXPECTED_SYMBOLS:
        raise ValueError("ATR110 universe mismatch")
    return reports


def _load_trades(root: Path) -> tuple[v3.V3Trade, ...]:
    rows: list[v3.V3Trade] = []
    paths = sorted(
        root.rglob("capitalizer-*-v3-source-first-no-rearm-atr110-2y-v1-trades.jsonl")
    )
    if len(paths) != 9:
        raise ValueError(f"ATR110 requires 9 trade ledgers, got {len(paths)}")
    for path in paths:
        with path.open(encoding="utf-8") as handle:
            for line in handle:
                if line.strip():
                    rows.append(v3.V3Trade(**json.loads(line)))
    return tuple(
        sorted(
            rows,
            key=lambda item: (datetime.fromisoformat(item.entry_at), item.symbol),
        )
    )


def _metrics_dict(trades: tuple[v3.V3Trade, ...]) -> dict[str, Any] | None:
    result = v3._metrics(trades)
    return None if result is None else asdict(result)


def build_matrix(root: Path) -> dict[str, Any]:
    _load_reports(root)
    raw = _load_trades(root)
    max3 = v3._portfolio_max3(raw)
    metrics = v3._metrics(max3)
    if metrics is None or metrics.profit_factor is None or metrics.mean_r is None:
        raise ValueError("ATR110 candidate requires complete metrics")

    pf = Decimal(metrics.profit_factor)
    total = Decimal(metrics.total_r)
    mean = Decimal(metrics.mean_r)
    dd = Decimal(metrics.max_drawdown_r)

    per_session: dict[str, dict[str, Any]] = {}
    for session in CapitalizerSession:
        selected = tuple(item for item in max3 if item.session == session.value)
        per_session[session.value] = {
            "trades": len(selected),
            "metrics": _metrics_dict(selected),
        }

    return {
        "identity": MATRIX_IDENTITY,
        "market_count": 9,
        "raw_trades": len(raw),
        "max3_selected_trades": len(max3),
        "max3_metrics": asdict(metrics),
        "per_session": per_session,
        "no_rearm_baseline": {
            "max3_trades": BASELINE_MAX3,
            "profit_factor": str(BASELINE_PF),
            "total_r": str(BASELINE_TOTAL_R),
            "mean_r": str(BASELINE_MEAN_R),
            "max_drawdown_r": str(BASELINE_DD_R),
            "losing_streak": BASELINE_LS,
        },
        "delta_vs_no_rearm": {
            "max3_trades": len(max3) - BASELINE_MAX3,
            "profit_factor": str(pf - BASELINE_PF),
            "total_r": str(total - BASELINE_TOTAL_R),
            "mean_r": str(mean - BASELINE_MEAN_R),
            "max_drawdown_r": str(dd - BASELINE_DD_R),
            "losing_streak": metrics.max_losing_streak - BASELINE_LS,
        },
        "variant_only_change": "SOURCE_FIRST_ATR_MULTIPLIER_1_20_TO_1_10",
        "atr_multiplier_original": str(ORIGINAL_ATR_MULTIPLIER),
        "atr_multiplier_candidate": str(FROZEN_ATR_MULTIPLIER),
        "minimal_adjacent_relaxation": True,
        "same_no_rearm_architecture": True,
        "same_source_first_boundary": True,
        "same_body_threshold": True,
        "same_swing_break": True,
        "same_cisd_requirement": True,
        "same_fvg": True,
        "same_stop": True,
        "same_target": True,
        "same_h1_deadline": True,
        "same_max3": True,
        "outcome_used_for_admission": False,
        "readiness_atlas_used_outcomes": False,
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
    path = output / "capitalizer-nine-market-v3-source-first-no-rearm-atr110-2y-v1.json"
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
        report, trades = build_market_report(
            args.m1_root,
            session=CapitalizerSession(args.session),
        )
        write_market(report, trades, args.output)
        print(json.dumps({
            "identity": report["identity"],
            "symbol": report["symbol"],
            "session": report["session"],
            "trades": len(trades),
            "raw_metrics": report["raw_metrics"],
        }, sort_keys=True))
        return

    report = build_matrix(args.input_root)
    write_matrix(report, args.output)
    print(json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    main()
