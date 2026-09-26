"""MAX_RECOVERY V1: causal arbitration baseline plus protected-swing geometry rescue.

This recovery union intentionally excludes methodology relaxations (ATR/body/CISD/
swing/FVG threshold changes). It combines only:
1. SOURCE_FIRST No-Rearm causal closeback arbitration; and
2. frozen protected-swing rescue for STOP_INVALID_GEOMETRY cases.

All admissions are causal and outcome-free. This is a recovery-density candidate,
not a certified economic candidate and not a target-optimization experiment.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

from qore.infrastructure.trader_lab import (
    capitalizer_v3_source_first_wait5_protected_swing_rescue_2y_v1 as rescue,
)
from qore.infrastructure.trader_lab.capitalizer_cibo_m1_reader_v1 import iter_cibo_m1
from qore.infrastructure.trader_lab.capitalizer_contract import CapitalizerSession
from qore.infrastructure.trader_lab.capitalizer_strict_htf_gate_1y_v1 import (
    _index_day_inputs,
)

IDENTITY = "QORE_CAPITALIZER_MAX_RECOVERY_V1"
MATRIX_IDENTITY = "QORE_CAPITALIZER_NINE_MARKET_MAX_RECOVERY_V1"
BASELINE_RAW = 854
BASELINE_MAX3 = 841


def _baseline(root: Path) -> tuple[rescue.PortfolioTrade, ...]:
    paths = sorted(
        root.rglob(
            "capitalizer-*-v3-source-first-no-rearm-"
            "closeback-arbitration-2y-v1-trades.jsonl"
        )
    )
    if len(paths) != 1:
        raise ValueError("MAX_RECOVERY requires one arbitration trade ledger")
    rows: list[rescue.PortfolioTrade] = []
    with paths[0].open(encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            raw = json.loads(line)
            rows.append(
                rescue.PortfolioTrade(
                    symbol=str(raw["symbol"]),
                    session=str(raw["session"]),
                    operating_date=str(raw["operating_date"]),
                    entry_at=str(raw["entry_at"]),
                    exit_at=str(raw["exit_at"]),
                    realized_gross_r=str(raw["realized_gross_r"]),
                    exit_reason=str(raw["exit_reason"]),
                    same_minute_stop_target_ambiguity=bool(
                        raw["same_minute_stop_target_ambiguity"]
                    ),
                    provenance="CAUSAL_ARBITRATION_BASE",
                )
            )
    return tuple(rows)


def build_market_report(
    arbitration_root: Path,
    stop_root: Path,
    funnel_root: Path,
    m1_root: Path,
    *,
    session: CapitalizerSession,
) -> tuple[
    dict[str, Any],
    tuple[rescue.PortfolioTrade, ...],
    tuple[rescue.PortfolioTrade, ...],
]:
    baseline = _baseline(arbitration_root)
    stop_rows = rescue._stop_rows(stop_root)
    funnel_rows = rescue._funnel_rows(funnel_root)

    bars = tuple(iter_cibo_m1(m1_root))
    if not bars:
        raise ValueError("MAX_RECOVERY requires native M1")
    symbol = bars[0].symbol
    if any(item.symbol != symbol for item in baseline):
        raise ValueError("MAX_RECOVERY arbitration/M1 symbol mismatch")
    if any(str(row["symbol"]) != symbol for row in stop_rows):
        raise ValueError("MAX_RECOVERY stop/M1 symbol mismatch")

    execution_by_day, _ = _index_day_inputs(bars, session=session)
    additions = rescue._candidate_additions(
        stop_rows=stop_rows,
        funnel_rows=funnel_rows,
        execution_by_day=execution_by_day,
    )

    candidate = tuple(
        sorted(
            (*baseline, *additions),
            key=lambda item: (datetime.fromisoformat(item.entry_at), item.symbol),
        )
    )
    return {
        "identity": IDENTITY,
        "symbol": symbol,
        "session": session.value,
        "arbitration_baseline_raw": len(baseline),
        "protected_swing_rescues_raw": len(additions),
        "max_recovery_raw": len(candidate),
        "recovery_families": [
            "CAUSAL_CLOSEBACK_ARBITRATION",
            "PROTECTED_SWING_GEOMETRY_RESCUE",
        ],
        "threshold_relaxations_included": False,
        "target_changes_included": False,
        "outcome_used_for_admission": False,
        "recovery_phase_open": True,
        "target_phase_open": False,
        "trader_certified": False,
        "live_authorized": False,
        "real_capital_authorized": False,
    }, baseline, candidate


def write_market(
    report: dict[str, Any],
    baseline: tuple[rescue.PortfolioTrade, ...],
    candidate: tuple[rescue.PortfolioTrade, ...],
    output: Path,
) -> None:
    output.mkdir(parents=True, exist_ok=True)
    symbol = str(report["symbol"]).lower()
    stem = f"capitalizer-{symbol}-max-recovery-v1"
    (output / f"{stem}.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    for variant, trades in (("baseline", baseline), ("candidate", candidate)):
        with (output / f"{stem}-{variant}-trades.jsonl").open(
            "w", encoding="utf-8"
        ) as handle:
            for trade in trades:
                handle.write(json.dumps(asdict(trade), sort_keys=True) + "\n")


def _load_reports(root: Path) -> list[dict[str, Any]]:
    paths = sorted(root.rglob("capitalizer-*-max-recovery-v1.json"))
    if len(paths) != 9:
        raise ValueError(f"MAX_RECOVERY matrix requires 9 reports, got {len(paths)}")
    return [dict(json.loads(path.read_text(encoding="utf-8"))) for path in paths]


def _load_portfolio(
    root: Path,
    *,
    variant: str,
) -> tuple[rescue.PortfolioTrade, ...]:
    paths = sorted(root.rglob(f"capitalizer-*-max-recovery-v1-{variant}-trades.jsonl"))
    if len(paths) != 9:
        raise ValueError(f"MAX_RECOVERY requires 9 {variant} ledgers")
    rows: list[rescue.PortfolioTrade] = []
    for path in paths:
        with path.open(encoding="utf-8") as handle:
            for line in handle:
                if line.strip():
                    rows.append(rescue.PortfolioTrade(**json.loads(line)))
    return tuple(rows)


def build_matrix(root: Path) -> dict[str, Any]:
    reports = _load_reports(root)
    baseline_raw = _load_portfolio(root, variant="baseline")
    candidate_raw = _load_portfolio(root, variant="candidate")
    baseline_max3 = rescue._max3(baseline_raw)
    candidate_max3 = rescue._max3(candidate_raw)
    baseline_metrics = rescue._metrics(baseline_max3)
    candidate_metrics = rescue._metrics(candidate_max3)
    if baseline_metrics is None or candidate_metrics is None:
        raise ValueError("MAX_RECOVERY requires complete metrics")

    pf_base = Decimal(str(baseline_metrics["profit_factor"]))
    pf_candidate = Decimal(str(candidate_metrics["profit_factor"]))
    total_base = Decimal(str(baseline_metrics["total_r"]))
    total_candidate = Decimal(str(candidate_metrics["total_r"]))
    dd_base = Decimal(str(baseline_metrics["max_drawdown_r"]))
    dd_candidate = Decimal(str(candidate_metrics["max_drawdown_r"]))

    return {
        "identity": MATRIX_IDENTITY,
        "market_count": 9,
        "baseline_raw_trades": len(baseline_raw),
        "candidate_raw_trades": len(candidate_raw),
        "baseline_max3_trades": len(baseline_max3),
        "candidate_max3_trades": len(candidate_max3),
        "protected_swing_rescues_raw": sum(
            int(item["protected_swing_rescues_raw"]) for item in reports
        ),
        "baseline_metrics": baseline_metrics,
        "candidate_metrics": candidate_metrics,
        "delta_vs_arbitration": {
            "raw_trades": len(candidate_raw) - len(baseline_raw),
            "max3_trades": len(candidate_max3) - len(baseline_max3),
            "profit_factor": str(pf_candidate - pf_base),
            "total_r": str(total_candidate - total_base),
            "max_drawdown_r": str(dd_candidate - dd_base),
            "losing_streak": (
                int(candidate_metrics["max_losing_streak"])
                - int(baseline_metrics["max_losing_streak"])
            ),
        },
        "arbitration_controls": {
            "expected_raw": BASELINE_RAW,
            "expected_max3": BASELINE_MAX3,
            "raw_reproduced": len(baseline_raw) == BASELINE_RAW,
            "max3_reproduced": len(baseline_max3) == BASELINE_MAX3,
        },
        "recovery_families": [
            "CAUSAL_CLOSEBACK_ARBITRATION",
            "PROTECTED_SWING_GEOMETRY_RESCUE",
        ],
        "threshold_relaxations_included": False,
        "target_changes_included": False,
        "outcome_used_for_admission": False,
        "recovery_phase_open": True,
        "target_phase_open": False,
        "automatic_promotion_allowed": False,
        "trader_certified": False,
        "live_authorized": False,
        "real_capital_authorized": False,
    }


def write_matrix(report: dict[str, Any], output: Path) -> None:
    output.mkdir(parents=True, exist_ok=True)
    path = output / "capitalizer-nine-market-max-recovery-v1.json"
    path.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)

    market = sub.add_parser("market")
    market.add_argument("arbitration_root", type=Path)
    market.add_argument("stop_root", type=Path)
    market.add_argument("funnel_root", type=Path)
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
            args.arbitration_root,
            args.stop_root,
            args.funnel_root,
            args.m1_root,
            session=CapitalizerSession(args.session),
        )
        write_market(report, baseline, candidate, args.output)
        print(json.dumps(report, sort_keys=True))
        return

    report = build_matrix(args.input_root)
    write_matrix(report, args.output)
    print(json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    main()
