"""Universal target sensitivity on the frozen MAX_RECOVERY_FINAL universe.

Selection, entries, stops, H1 deadlines and portfolio MAX3 are frozen.
Only the fixed target multiple changes.

This is consumed-window target research. It maps the economic response curve and
does NOT select or promote a target. Fresh validation is required after a target
rule is frozen.
"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any

from qore.infrastructure.trader_lab import (
    capitalizer_max_recovery_target_ready_freeze_v1 as freeze,
)
from qore.infrastructure.trader_lab import (
    capitalizer_owner_h1_m3_m1_causal_reversal_1y_v3 as v3,
)
from qore.infrastructure.trader_lab import (
    capitalizer_v3_source_first_wait5_protected_swing_rescue_2y_v1 as rescue,
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

IDENTITY = "QORE_CAPITALIZER_MAX_RECOVERY_TARGET_SENSITIVITY_2Y_V1"
MATRIX_IDENTITY = (
    "QORE_CAPITALIZER_NINE_MARKET_MAX_RECOVERY_TARGET_SENSITIVITY_2Y_V1"
)
TARGET_RS = (
    Decimal("1.00"),
    Decimal("1.25"),
    Decimal("1.50"),
    Decimal("1.75"),
    Decimal("2.00"),
    Decimal("2.25"),
    Decimal("2.50"),
    Decimal("2.75"),
    Decimal("3.00"),
)
BASELINE_TARGET_R = Decimal("2.00")
EXPECTED_FINAL_RAW = 963
EXPECTED_FINAL_MAX3 = 948
EXPECTED_BASELINE_PF = Decimal("1.466020472120789368123727041")
EXPECTED_BASELINE_TOTAL_R = Decimal("153.9927998412621697329314877")
EXPECTED_BASELINE_DD_R = Decimal("12.93584837435268644582248142")
EXPECTED_BASELINE_LS = 7


@dataclass(frozen=True, slots=True)
class TargetOutcome:
    symbol: str
    session: str
    operating_date: str
    side: str
    h1_open: str
    h1_deadline: str
    entry_at: str
    entry_price: str
    stop_price: str
    target_r: str
    target_price: str
    exit_at: str
    realized_gross_r: str
    exit_reason: str
    same_minute_stop_target_ambiguity: bool
    provenance: str


def _simulate(
    trade: freeze.TargetReadyTrade,
    *,
    target_r: Decimal,
    execution: tuple[CapitalizerM1Bar, ...],
) -> TargetOutcome:
    entry_at = datetime.fromisoformat(trade.entry_at)
    deadline = datetime.fromisoformat(trade.h1_deadline)
    entry = Decimal(trade.entry_price)
    stop = Decimal(trade.stop_price)
    risk = Decimal(trade.risk_price)
    side = CapitalizerSide(trade.side)
    if risk <= 0:
        raise ValueError("target sensitivity requires positive frozen risk")

    entry_index = next(
        (
            index
            for index, bar in enumerate(execution)
            if bar.opened_at == entry_at
        ),
        None,
    )
    if entry_index is None:
        raise ValueError("target sensitivity entry timestamp missing from M1")

    target = (
        entry + target_r * risk
        if side is CapitalizerSide.LONG
        else entry - target_r * risk
    )
    realized, reason, _, ambiguous, exit_at = v3._lifecycle(
        execution,
        entry_index=entry_index,
        side=side,
        entry_price=entry,
        stop_price=stop,
        target_price=target,
        deadline=deadline,
    )
    return TargetOutcome(
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


def _proxy(outcome: TargetOutcome) -> rescue.PortfolioTrade:
    return rescue.PortfolioTrade(
        symbol=outcome.symbol,
        session=outcome.session,
        operating_date=outcome.operating_date,
        entry_at=outcome.entry_at,
        exit_at=outcome.exit_at,
        realized_gross_r=outcome.realized_gross_r,
        exit_reason=outcome.exit_reason,
        same_minute_stop_target_ambiguity=(
            outcome.same_minute_stop_target_ambiguity
        ),
        provenance=outcome.provenance,
    )


def _metrics(outcomes: tuple[TargetOutcome, ...]) -> dict[str, Any]:
    value = rescue._metrics(tuple(_proxy(item) for item in outcomes))
    if value is None:
        raise ValueError("target sensitivity requires complete metrics")
    return value


def _max3(outcomes: tuple[TargetOutcome, ...]) -> tuple[TargetOutcome, ...]:
    by_key = {(
        item.symbol,
        item.session,
        item.operating_date,
        item.entry_at,
        item.target_r,
    ): item for item in outcomes}
    selected_proxy = rescue._max3(tuple(_proxy(item) for item in outcomes))
    selected: list[TargetOutcome] = []
    for item in selected_proxy:
        matches = [
            value
            for key, value in by_key.items()
            if key[0] == item.symbol
            and key[1] == item.session
            and key[2] == item.operating_date
            and key[3] == item.entry_at
        ]
        if len(matches) != 1:
            raise ValueError("target sensitivity MAX3 mapping must be unique")
        selected.append(matches[0])
    return tuple(
        sorted(
            selected,
            key=lambda item: (
                datetime.fromisoformat(item.entry_at),
                item.symbol,
            ),
        )
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
) -> tuple[dict[str, Any], tuple[TargetOutcome, ...]]:
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
        raise ValueError("target sensitivity requires native M1")
    symbol = bars[0].symbol
    execution_by_day, _ = _index_day_inputs(bars, session=session)

    outcomes: list[TargetOutcome] = []
    per_target: dict[str, dict[str, Any]] = {}
    for target_r in TARGET_RS:
        target_outcomes: list[TargetOutcome] = []
        for trade in frozen:
            execution = execution_by_day.get(trade.operating_date, ())
            if not execution:
                raise ValueError("target sensitivity missing execution day")
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
            "raw_metrics": _metrics(ordered),
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
    outcomes: tuple[TargetOutcome, ...],
    output: Path,
) -> None:
    output.mkdir(parents=True, exist_ok=True)
    symbol = str(report["symbol"]).lower()
    stem = f"capitalizer-{symbol}-max-recovery-target-sensitivity-2y-v1"
    (output / f"{stem}.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    with (output / f"{stem}-outcomes.jsonl").open("w", encoding="utf-8") as handle:
        for outcome in outcomes:
            handle.write(json.dumps(asdict(outcome), sort_keys=True) + "\n")


def _load_reports(root: Path) -> list[dict[str, Any]]:
    paths = sorted(
        root.rglob(
            "capitalizer-*-max-recovery-target-sensitivity-2y-v1.json"
        )
    )
    if len(paths) != 9:
        raise ValueError(f"target sensitivity requires 9 reports, got {len(paths)}")
    return [dict(json.loads(path.read_text(encoding="utf-8"))) for path in paths]


def _load_outcomes(root: Path) -> tuple[TargetOutcome, ...]:
    paths = sorted(
        root.rglob(
            "capitalizer-*-max-recovery-target-sensitivity-2y-v1-outcomes.jsonl"
        )
    )
    if len(paths) != 9:
        raise ValueError(
            f"target sensitivity requires 9 outcome ledgers, got {len(paths)}"
        )
    result: list[TargetOutcome] = []
    for path in paths:
        with path.open(encoding="utf-8") as handle:
            for line in handle:
                if line.strip():
                    result.append(TargetOutcome(**json.loads(line)))
    return tuple(result)


def build_matrix(root: Path) -> dict[str, Any]:
    reports = _load_reports(root)
    outcomes = _load_outcomes(root)

    variants: list[dict[str, Any]] = []
    baseline_metrics: dict[str, Any] | None = None
    for target_r in TARGET_RS:
        selected_raw = tuple(
            item for item in outcomes if Decimal(item.target_r) == target_r
        )
        selected = _max3(selected_raw)
        metrics = _metrics(selected)
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
                raise ValueError("2R target raw control mismatch")
            if len(selected) != EXPECTED_FINAL_MAX3:
                raise ValueError("2R target MAX3 control mismatch")
            if Decimal(str(metrics["profit_factor"])) != EXPECTED_BASELINE_PF:
                raise ValueError("2R target PF control mismatch")
            if Decimal(str(metrics["total_r"])) != EXPECTED_BASELINE_TOTAL_R:
                raise ValueError("2R target total-R control mismatch")
            if Decimal(str(metrics["max_drawdown_r"])) != EXPECTED_BASELINE_DD_R:
                raise ValueError("2R target DD control mismatch")
            if int(metrics["max_losing_streak"]) != EXPECTED_BASELINE_LS:
                raise ValueError("2R target losing-streak control mismatch")

    if baseline_metrics is None:
        raise ValueError("target sensitivity missing 2R baseline")

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
        "capitalizer-nine-market-max-recovery-target-sensitivity-2y-v1.json"
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
