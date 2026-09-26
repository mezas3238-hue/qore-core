"""Corrected universal target sensitivity for the frozen MAX_RECOVERY_FINAL universe.

V1 reused the original V3 lifecycle, whose TARGET branch is intentionally hard-coded
to +2R because V3 itself is a fixed-2R strategy. That made every V1 target variant
place the target at the requested R multiple while still booking +2R on a hit.

V2 preserves the frozen selection, entries, stops, H1 deadlines and MAX3, but fixes
only the target-hit accounting:
    realized TARGET R == requested target_r

The 2R baseline must remain identical to V1. No target is selected or promoted.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from datetime import datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any

from qore.infrastructure.trader_lab import (
    capitalizer_max_recovery_target_ready_freeze_v1 as freeze,
)
from qore.infrastructure.trader_lab import (
    capitalizer_max_recovery_target_sensitivity_2y_v1 as v1,
)
from qore.infrastructure.trader_lab import (
    capitalizer_owner_h1_m3_m1_causal_reversal_1y_v3 as v3,
)
from qore.infrastructure.trader_lab.capitalizer_cibo_m1_reader_v1 import (
    CapitalizerM1Bar,
    iter_cibo_m1,
)
from qore.infrastructure.trader_lab.capitalizer_contract import CapitalizerSession
from qore.infrastructure.trader_lab.capitalizer_exposure_graph import CapitalizerSide
from qore.infrastructure.trader_lab.capitalizer_m3_mss_bottleneck_forensics_2y_v1 import (
    LOOKBACK_START,
    WINDOW_END,
)
from qore.infrastructure.trader_lab.capitalizer_strict_htf_gate_1y_v1 import (
    _index_day_inputs,
)

IDENTITY = "QORE_CAPITALIZER_MAX_RECOVERY_TARGET_SENSITIVITY_2Y_V2"
MATRIX_IDENTITY = (
    "QORE_CAPITALIZER_NINE_MARKET_MAX_RECOVERY_TARGET_SENSITIVITY_2Y_V2"
)

V1_DEFECT = "TARGET_HIT_REALIZED_R_HARDCODED_TO_2"
TARGET_RS = v1.TARGET_RS
BASELINE_TARGET_R = v1.BASELINE_TARGET_R
EXPECTED_FINAL_RAW = v1.EXPECTED_FINAL_RAW
EXPECTED_FINAL_MAX3 = v1.EXPECTED_FINAL_MAX3
EXPECTED_BASELINE_PF = v1.EXPECTED_BASELINE_PF
EXPECTED_BASELINE_TOTAL_R = v1.EXPECTED_BASELINE_TOTAL_R
EXPECTED_BASELINE_DD_R = v1.EXPECTED_BASELINE_DD_R
EXPECTED_BASELINE_LS = v1.EXPECTED_BASELINE_LS


def _correct_realized_target_r(
    *,
    lifecycle_realized: Decimal,
    reason: str,
    target_r: Decimal,
) -> Decimal:
    if reason == "TARGET":
        return target_r
    return lifecycle_realized


def _simulate(
    trade: freeze.TargetReadyTrade,
    *,
    target_r: Decimal,
    execution: tuple[CapitalizerM1Bar, ...],
) -> v1.TargetOutcome:
    entry_at = datetime.fromisoformat(trade.entry_at)
    deadline = datetime.fromisoformat(trade.h1_deadline)
    entry = Decimal(trade.entry_price)
    stop = Decimal(trade.stop_price)
    risk = Decimal(trade.risk_price)
    side = CapitalizerSide(trade.side)
    if risk <= 0:
        raise ValueError("target sensitivity V2 requires positive frozen risk")

    entry_index = next(
        (
            index
            for index, bar in enumerate(execution)
            if bar.opened_at == entry_at
        ),
        None,
    )
    if entry_index is None:
        raise ValueError("target sensitivity V2 entry timestamp missing from M1")

    target = (
        entry + target_r * risk
        if side is CapitalizerSide.LONG
        else entry - target_r * risk
    )
    lifecycle_realized, reason, _, ambiguous, exit_at = v3._lifecycle(
        execution,
        entry_index=entry_index,
        side=side,
        entry_price=entry,
        stop_price=stop,
        target_price=target,
        deadline=deadline,
    )
    realized = _correct_realized_target_r(
        lifecycle_realized=lifecycle_realized,
        reason=reason,
        target_r=target_r,
    )
    return v1.TargetOutcome(
        symbol=trade.symbol,
        session=trade.session,
        operating_date=trade.operating_date,
        side=trade.side,
        h1_open=trade.h1_open,
        h1_deadline=trade.h1_deadline,
        entry_at=trade.entry_at,
        entry_price=trade.entry_price,
        stop_price=trade.stop_price,
        target_r=str(target_r),
        target_price=str(target),
        exit_at=exit_at.isoformat(),
        realized_gross_r=str(realized),
        exit_reason=reason,
        same_minute_stop_target_ambiguity=ambiguous,
        provenance=trade.provenance,
    )


def build_market_report(
    final_root: Path,
    arbitration_root: Path,
    stop_root: Path,
    funnel_root: Path,
    rearm_root: Path,
    m1_root: Path,
    *,
    session: CapitalizerSession,
) -> tuple[dict[str, Any], tuple[v1.TargetOutcome, ...]]:
    freeze_report, frozen = freeze.build_market_report(
        final_root,
        arbitration_root,
        stop_root,
        funnel_root,
        rearm_root,
        m1_root,
        session=session,
    )
    bars = tuple(
        bar
        for bar in iter_cibo_m1(m1_root)
        if LOOKBACK_START <= bar.opened_at < WINDOW_END + timedelta(days=1)
    )
    if not bars:
        raise ValueError("target sensitivity V2 requires native M1")
    symbol = bars[0].symbol
    execution_by_day, _ = _index_day_inputs(bars, session=session)

    outcomes: list[v1.TargetOutcome] = []
    per_target: dict[str, dict[str, Any]] = {}
    for target_r in TARGET_RS:
        target_outcomes: list[v1.TargetOutcome] = []
        for trade in frozen:
            execution = execution_by_day.get(trade.operating_date, ())
            if not execution:
                raise ValueError("target sensitivity V2 missing execution day")
            target_outcomes.append(
                _simulate(
                    trade,
                    target_r=target_r,
                    execution=execution,
                )
            )
        ordered = tuple(
            sorted(
                target_outcomes,
                key=lambda item: (
                    datetime.fromisoformat(item.entry_at),
                    item.symbol,
                ),
            )
        )
        outcomes.extend(ordered)
        per_target[str(target_r)] = {
            "raw_trades": len(ordered),
            "raw_metrics": v1._metrics(ordered),
        }

    return {
        "identity": IDENTITY,
        "symbol": symbol,
        "session": session.value,
        "target_grid_r": [str(item) for item in TARGET_RS],
        "final_recovery_trades": int(freeze_report["final_recovery_trades"]),
        "target_ready_trades": len(frozen),
        "per_target": per_target,
        "selection_changed": False,
        "entry_changed": False,
        "stop_changed": False,
        "h1_deadline_changed": False,
        "max3_changed": False,
        "only_target_r_varied": True,
        "target_hit_realized_r_equals_target_r": True,
        "supersedes_target_sensitivity_v1": True,
        "v1_defect": V1_DEFECT,
        "outcome_used_for_admission": False,
        "development_window_role": "CONSUMED_TARGET_RESEARCH",
        "target_selected": False,
        "fresh_holdout_required_after_selection": True,
        "automatic_promotion_allowed": False,
        "trader_certified": False,
        "live_authorized": False,
        "real_capital_authorized": False,
    }, tuple(outcomes)


def write_market(
    report: dict[str, Any],
    outcomes: tuple[v1.TargetOutcome, ...],
    output: Path,
) -> None:
    output.mkdir(parents=True, exist_ok=True)
    symbol = str(report["symbol"]).lower()
    stem = f"capitalizer-{symbol}-max-recovery-target-sensitivity-2y-v2"
    (output / f"{stem}.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    with (output / f"{stem}-outcomes.jsonl").open("w", encoding="utf-8") as handle:
        for outcome in outcomes:
            handle.write(json.dumps(asdict(outcome), sort_keys=True) + "\n")


def _load_reports(root: Path) -> list[dict[str, Any]]:
    paths = sorted(
        root.rglob("capitalizer-*-max-recovery-target-sensitivity-2y-v2.json")
    )
    if len(paths) != 9:
        raise ValueError(f"target sensitivity V2 requires 9 reports, got {len(paths)}")
    return [dict(json.loads(path.read_text(encoding="utf-8"))) for path in paths]


def _load_outcomes(root: Path) -> tuple[v1.TargetOutcome, ...]:
    paths = sorted(
        root.rglob(
            "capitalizer-*-max-recovery-target-sensitivity-2y-v2-outcomes.jsonl"
        )
    )
    if len(paths) != 9:
        raise ValueError(
            f"target sensitivity V2 requires 9 outcome ledgers, got {len(paths)}"
        )
    result: list[v1.TargetOutcome] = []
    for path in paths:
        with path.open(encoding="utf-8") as handle:
            for line in handle:
                if line.strip():
                    result.append(v1.TargetOutcome(**json.loads(line)))
    return tuple(result)


def build_matrix(root: Path) -> dict[str, Any]:
    _load_reports(root)
    outcomes = _load_outcomes(root)

    variants: list[dict[str, Any]] = []
    baseline_metrics: dict[str, Any] | None = None
    for target_r in TARGET_RS:
        selected_raw = tuple(
            item for item in outcomes if Decimal(item.target_r) == target_r
        )
        selected = v1._max3(selected_raw)
        metrics = v1._metrics(selected)
        variants.append(
            {
                "target_r": str(target_r),
                "raw_trades": len(selected_raw),
                "max3_trades": len(selected),
                "metrics": metrics,
            }
        )
        if target_r == BASELINE_TARGET_R:
            baseline_metrics = metrics
            if len(selected_raw) != EXPECTED_FINAL_RAW:
                raise ValueError("V2 2R raw control mismatch")
            if len(selected) != EXPECTED_FINAL_MAX3:
                raise ValueError("V2 2R MAX3 control mismatch")
            if Decimal(str(metrics["profit_factor"])) != EXPECTED_BASELINE_PF:
                raise ValueError("V2 2R PF control mismatch")
            if Decimal(str(metrics["total_r"])) != EXPECTED_BASELINE_TOTAL_R:
                raise ValueError("V2 2R total-R control mismatch")
            if Decimal(str(metrics["max_drawdown_r"])) != EXPECTED_BASELINE_DD_R:
                raise ValueError("V2 2R DD control mismatch")
            if int(metrics["max_losing_streak"]) != EXPECTED_BASELINE_LS:
                raise ValueError("V2 2R losing-streak control mismatch")

    if baseline_metrics is None:
        raise ValueError("target sensitivity V2 missing 2R baseline")

    return {
        "identity": MATRIX_IDENTITY,
        "market_count": 9,
        "target_grid_r": [str(item) for item in TARGET_RS],
        "variants": variants,
        "baseline_target_r": str(BASELINE_TARGET_R),
        "baseline_control_reproduced": True,
        "baseline_metrics": baseline_metrics,
        "final_raw_trades": EXPECTED_FINAL_RAW,
        "final_max3_trades": EXPECTED_FINAL_MAX3,
        "selection_changed": False,
        "entry_changed": False,
        "stop_changed": False,
        "h1_deadline_changed": False,
        "max3_changed": False,
        "only_target_r_varied": True,
        "target_hit_realized_r_equals_target_r": True,
        "supersedes_target_sensitivity_v1": True,
        "v1_defect": V1_DEFECT,
        "outcome_used_for_admission": False,
        "development_window_role": "CONSUMED_TARGET_RESEARCH",
        "target_selected": False,
        "fresh_holdout_required_after_selection": True,
        "automatic_promotion_allowed": False,
        "trader_certified": False,
        "live_authorized": False,
        "real_capital_authorized": False,
    }


def write_matrix(report: dict[str, Any], output: Path) -> None:
    output.mkdir(parents=True, exist_ok=True)
    path = output / (
        "capitalizer-nine-market-max-recovery-target-sensitivity-2y-v2.json"
    )
    path.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)

    market = sub.add_parser("market")
    market.add_argument("final_root", type=Path)
    market.add_argument("arbitration_root", type=Path)
    market.add_argument("stop_root", type=Path)
    market.add_argument("funnel_root", type=Path)
    market.add_argument("rearm_root", type=Path)
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
        report, outcomes = build_market_report(
            args.final_root,
            args.arbitration_root,
            args.stop_root,
            args.funnel_root,
            args.rearm_root,
            args.m1_root,
            session=CapitalizerSession(args.session),
        )
        write_market(report, outcomes, args.output)
        print(
            json.dumps(
                {
                    "identity": report["identity"],
                    "symbol": report["symbol"],
                    "session": report["session"],
                    "target_ready_trades": report["target_ready_trades"],
                    "target_grid_r": report["target_grid_r"],
                    "target_hit_realized_r_equals_target_r": True,
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
