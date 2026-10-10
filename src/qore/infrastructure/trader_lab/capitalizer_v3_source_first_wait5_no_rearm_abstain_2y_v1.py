"""Consumed-window A/B: WAIT5 armed state becomes abstention without rearm.

Causal architecture rule frozen before reading this candidate's economics:
- WAIT is a real state, not delayed automatic permission;
- rearm requires new causal evidence;
- the existing WAIT5 implementation can reuse the same original FVG CE after
  five minutes without a new raid or a new confirmation;
- this candidate forbids that stale same-setup reuse.

Only change relative to frozen SOURCE_FIRST + WAIT5:
- when WAIT5 is armed, the current setup ends in ABSTAIN;
- later independent H1 setups remain eligible under the original scanner;
- overlap entries and normal fills >=5m remain unchanged;
- FVG, stop, target, H1 deadline, STOP-first and MAX3 remain unchanged.

No market/session/side/outcome is used for admission. The 2Y window is consumed
development evidence and cannot promote by itself.
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

IDENTITY = "QORE_CAPITALIZER_V3_SOURCE_FIRST_WAIT5_NO_REARM_ABSTAIN_2Y_V1"
MATRIX_IDENTITY = (
    "QORE_CAPITALIZER_NINE_MARKET_V3_SOURCE_FIRST_WAIT5_NO_REARM_ABSTAIN_2Y_V1"
)
ARCHITECTURE_RULE = "WAIT_REARM_REQUIRES_NEW_CAUSAL_EVIDENCE"

WAIT5_BASELINE_RAW = 1003
WAIT5_BASELINE_MAX3 = 983
WAIT5_BASELINE_PF = Decimal("1.384597543145107741177480996")
WAIT5_BASELINE_TOTAL_R = Decimal("135.7651037644532073259312101")
WAIT5_BASELINE_MEAN_R = Decimal("0.1381130251927296107079666430")
WAIT5_BASELINE_DD_R = Decimal("11.9420088471277198029814040")
WAIT5_BASELINE_LS = 9


def _abstain_wait_fill(*args: Any, **kwargs: Any) -> tuple[None, str]:
    del args, kwargs
    return None, "ABSTAIN_NO_REARM"


@contextmanager
def _no_rearm_patch() -> Iterator[None]:
    mutable_wait5: Any = wait5
    original = mutable_wait5._find_wait5_fill
    try:
        mutable_wait5._find_wait5_fill = _abstain_wait_fill
        yield
    finally:
        mutable_wait5._find_wait5_fill = original


def build_market_report(
    m1_root: Path,
    *,
    session: CapitalizerSession,
) -> tuple[dict[str, Any], tuple[v3.V3Trade, ...]]:
    with _no_rearm_patch():
        report, trades = wait5.build_market_report(
            m1_root,
            session=session,
        )

    report.update(
        {
            "identity": IDENTITY,
            "architecture_rule": ARCHITECTURE_RULE,
            "variant_only_change": "WAIT5_ARMED_CURRENT_SETUP_ABSTAINS",
            "same_original_setup_reuse_forbidden": True,
            "new_independent_h1_setup_remains_eligible": True,
            "same_source_first_mss_preserved": True,
            "same_fvg_preserved": True,
            "same_normal_fill_preserved": True,
            "same_stop_preserved": True,
            "same_target_preserved": True,
            "same_h1_deadline_preserved": True,
            "same_stop_first_precedence": True,
            "same_max3_preserved": True,
            "outcome_used_for_admission": False,
            "component_rule_frozen_from_architecture": True,
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
        "wait5-no-rearm-abstain-2y-v1"
    )
    (output / f"{stem}.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    with (output / f"{stem}-trades.jsonl").open("w", encoding="utf-8") as handle:
        for trade in trades:
            handle.write(json.dumps(asdict(trade), sort_keys=True) + "\n")


def _load_reports(root: Path) -> list[dict[str, Any]]:
    paths = sorted(
        root.rglob(
            "capitalizer-*-v3-source-first-wait5-no-rearm-abstain-2y-v1.json"
        )
    )
    if len(paths) != 9:
        raise ValueError(f"WAIT5 no-rearm matrix requires 9 reports, got {len(paths)}")
    reports = [
        dict(json.loads(path.read_text(encoding="utf-8")))
        for path in paths
    ]
    if {str(item["symbol"]) for item in reports} != v3.EXPECTED_SYMBOLS:
        raise ValueError("WAIT5 no-rearm universe mismatch")
    return reports


def _load_trades(root: Path) -> tuple[v3.V3Trade, ...]:
    rows: list[v3.V3Trade] = []
    paths = sorted(
        root.rglob(
            "capitalizer-*-v3-source-first-"
            "wait5-no-rearm-abstain-2y-v1-trades.jsonl"
        )
    )
    if len(paths) != 9:
        raise ValueError(f"WAIT5 no-rearm requires 9 trade ledgers, got {len(paths)}")
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


def build_matrix(root: Path) -> dict[str, Any]:
    _load_reports(root)
    raw = _load_trades(root)
    max3 = v3._portfolio_max3(raw)
    metrics = v3._metrics(max3)
    if metrics is None or metrics.profit_factor is None or metrics.mean_r is None:
        raise ValueError("WAIT5 no-rearm requires complete MAX3 metrics")

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

    pf = Decimal(metrics.profit_factor)
    total = Decimal(metrics.total_r)
    mean = Decimal(metrics.mean_r)
    dd_value = Decimal(metrics.max_drawdown_r)

    return {
        "identity": MATRIX_IDENTITY,
        "architecture_rule": ARCHITECTURE_RULE,
        "market_count": 9,
        "raw_trades": len(raw),
        "max3_selected_trades": len(max3),
        "max3_metrics": asdict(metrics),
        "per_session": per_session,
        "per_market": per_market,
        "wait5_baseline": {
            "raw_trades": WAIT5_BASELINE_RAW,
            "max3_trades": WAIT5_BASELINE_MAX3,
            "profit_factor": str(WAIT5_BASELINE_PF),
            "total_r": str(WAIT5_BASELINE_TOTAL_R),
            "mean_r": str(WAIT5_BASELINE_MEAN_R),
            "max_drawdown_r": str(WAIT5_BASELINE_DD_R),
            "losing_streak": WAIT5_BASELINE_LS,
        },
        "delta_vs_wait5": {
            "raw_trades": len(raw) - WAIT5_BASELINE_RAW,
            "max3_trades": len(max3) - WAIT5_BASELINE_MAX3,
            "profit_factor": str(pf - WAIT5_BASELINE_PF),
            "total_r": str(total - WAIT5_BASELINE_TOTAL_R),
            "mean_r": str(mean - WAIT5_BASELINE_MEAN_R),
            "max_drawdown_r": str(dd_value - WAIT5_BASELINE_DD_R),
            "losing_streak": metrics.max_losing_streak - WAIT5_BASELINE_LS,
        },
        "same_original_setup_reuse_forbidden": True,
        "new_independent_h1_setup_remains_eligible": True,
        "same_source_first_mss_preserved": True,
        "same_fvg_preserved": True,
        "same_normal_fill_preserved": True,
        "same_stop_preserved": True,
        "same_target_preserved": True,
        "same_h1_deadline_preserved": True,
        "same_stop_first_precedence": True,
        "same_max3_preserved": True,
        "outcome_used_for_admission": False,
        "component_rule_frozen_from_architecture": True,
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
        "capitalizer-nine-market-v3-source-first-"
        "wait5-no-rearm-abstain-2y-v1.json"
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
                    "entries": len(trades),
                    "raw_metrics": report["raw_metrics"],
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
