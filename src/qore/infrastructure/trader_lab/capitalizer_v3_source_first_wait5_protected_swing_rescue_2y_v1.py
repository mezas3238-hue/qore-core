"""Isolated A/B: rescue only WAIT5 STOP_INVALID_GEOMETRY with causal protected swing.

Frozen outcome-free evidence showed 111 SOURCE_FIRST + WAIT5 setups reach a valid
fill but fail only because the V3 broken-swing stop is geometrically on the wrong
side of entry. This candidate does NOT change any already-executable WAIT5 trade.

For those 111 only:
- use the latest opposite-kind M3 pivot confirmed before the original displacement;
- apply the same frozen V3 5-pip buffer;
- require the protected stop to be valid relative to the frozen fill;
- require the protected stop to remain intact from MSS confirmation until fill;
- preserve the frozen fill time/price/mode;
- preserve the original H1 deadline;
- preserve fixed 2R and STOP-first lifecycle precedence;
- preserve portfolio MAX3.

No market/session/outcome result is used for admission. Development window is consumed.
"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from dataclasses import asdict, dataclass
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

from qore.infrastructure.trader_lab import (
    capitalizer_owner_h1_m3_m1_causal_reversal_1y_v3 as v3,
)
from qore.infrastructure.trader_lab.capitalizer_cibo_m1_reader_v1 import (
    CapitalizerM1Bar,
    iter_cibo_m1,
)
from qore.infrastructure.trader_lab.capitalizer_contract import (
    MAX_EXECUTIONS_PER_SESSION,
    CapitalizerSession,
)
from qore.infrastructure.trader_lab.capitalizer_strict_htf_gate_1y_v1 import (
    _index_day_inputs,
)

IDENTITY = (
    "QORE_CAPITALIZER_V3_SOURCE_FIRST_WAIT5_"
    "PROTECTED_SWING_RESCUE_2Y_V1"
)
MATRIX_IDENTITY = (
    "QORE_CAPITALIZER_NINE_MARKET_V3_SOURCE_FIRST_WAIT5_"
    "PROTECTED_SWING_RESCUE_2Y_V1"
)
EXPECTED_STOP_INVALID = 111
WAIT5_BASELINE_MAX3 = 983
WAIT5_BASELINE_PF = Decimal("1.384597543145107741177480996")
WAIT5_BASELINE_TOTAL_R = Decimal("135.7651037644532073259312101")
WAIT5_BASELINE_DD_R = Decimal("11.9420088471277198029814040")


@dataclass(frozen=True, slots=True)
class PortfolioTrade:
    symbol: str
    session: str
    operating_date: str
    entry_at: str
    exit_at: str
    realized_gross_r: str
    exit_reason: str
    same_minute_stop_target_ambiguity: bool
    provenance: str


def _load_jsonl(root: Path, pattern: str) -> tuple[dict[str, Any], ...]:
    paths = sorted(root.rglob(pattern))
    if len(paths) != 1:
        raise ValueError(f"expected one ledger for {pattern}, got {len(paths)}")
    rows: list[dict[str, Any]] = []
    with paths[0].open(encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            raw = json.loads(line)
            if not isinstance(raw, dict):
                raise ValueError("ledger row must be object")
            rows.append(raw)
    return tuple(rows)


def _baseline_trades(root: Path) -> tuple[PortfolioTrade, ...]:
    rows = _load_jsonl(
        root,
        "capitalizer-*-v3-source-first-wait5-2y-v1-trades.jsonl",
    )
    return tuple(
        PortfolioTrade(
            symbol=str(row["symbol"]),
            session=str(row["session"]),
            operating_date=str(row["operating_date"]),
            entry_at=str(row["entry_at"]),
            exit_at=str(row["exit_at"]),
            realized_gross_r=str(row["realized_gross_r"]),
            exit_reason=str(row["exit_reason"]),
            same_minute_stop_target_ambiguity=bool(
                row["same_minute_stop_target_ambiguity"]
            ),
            provenance="WAIT5_BASELINE",
        )
        for row in rows
    )


def _stop_rows(root: Path) -> tuple[dict[str, Any], ...]:
    return _load_jsonl(
        root,
        "capitalizer-*-v3-source-first-wait5-"
        "stop-invalid-geometry-atlas-2y-v1-rows.jsonl",
    )


def _funnel_rows(root: Path) -> tuple[dict[str, Any], ...]:
    rows = _load_jsonl(
        root,
        "capitalizer-*-v3-source-first-wait5-funnel-atlas-2y-v1-rows.jsonl",
    )
    return tuple(
        row
        for row in rows
        if row.get("terminal_reason") == "STOP_INVALID_GEOMETRY"
    )


def _funnel_key(row: dict[str, Any]) -> tuple[str, str, str, str]:
    return (
        str(row["operating_date"]),
        str(row["side"]),
        str(row["source_first_mss_at"]),
        str(row["final_fill_at"]),
    )


def _stop_key(row: dict[str, Any]) -> tuple[str, str, str, str]:
    return (
        str(row["operating_date"]),
        str(row["side"]),
        str(row["source_first_mss_at"]),
        str(row["final_fill_at"]),
    )


def _stop_hit(
    bar: CapitalizerM1Bar,
    *,
    side: str,
    stop_price: Decimal,
) -> bool:
    return bool(
        bar.low <= stop_price if side == "LONG" else bar.high >= stop_price
    )


def _max3(trades: tuple[PortfolioTrade, ...]) -> tuple[PortfolioTrade, ...]:
    grouped: dict[str, list[PortfolioTrade]] = defaultdict(list)
    for trade in trades:
        grouped[f"{trade.session}:{trade.operating_date}"].append(trade)
    selected: list[PortfolioTrade] = []
    for key in sorted(grouped):
        ordered = sorted(
            grouped[key],
            key=lambda item: (datetime.fromisoformat(item.entry_at), item.symbol),
        )
        selected.extend(ordered[:MAX_EXECUTIONS_PER_SESSION])
    return tuple(
        sorted(
            selected,
            key=lambda item: (datetime.fromisoformat(item.entry_at), item.symbol),
        )
    )


def _metrics(trades: tuple[PortfolioTrade, ...]) -> dict[str, Any] | None:
    if not trades:
        return None
    ordered = tuple(
        sorted(trades, key=lambda item: datetime.fromisoformat(item.entry_at))
    )
    values = tuple(Decimal(item.realized_gross_r) for item in ordered)
    gp = sum((value for value in values if value > 0), Decimal("0"))
    gl = -sum((value for value in values if value < 0), Decimal("0"))
    total = sum(values, Decimal("0"))
    equity = Decimal("0")
    peak = Decimal("0")
    dd = Decimal("0")
    streak = 0
    max_streak = 0
    for value in values:
        equity += value
        peak = max(peak, equity)
        dd = max(dd, peak - equity)
        if value < 0:
            streak += 1
            max_streak = max(max_streak, streak)
        else:
            streak = 0
    return {
        "trades": len(values),
        "wins": sum(value > 0 for value in values),
        "losses": sum(value < 0 for value in values),
        "flats": sum(value == 0 for value in values),
        "total_r": str(total),
        "mean_r": str(total / Decimal(len(values))),
        "gross_profit_r": str(gp),
        "gross_loss_r": str(gl),
        "profit_factor": None if gl == 0 else str(gp / gl),
        "max_drawdown_r": str(dd),
        "max_losing_streak": max_streak,
        "stop_exits": sum(item.exit_reason == "STOP" for item in ordered),
        "target_exits": sum(item.exit_reason == "TARGET" for item in ordered),
        "session_exits": sum(
            item.exit_reason == "SESSION_EXIT" for item in ordered
        ),
        "ambiguous_stop_first_exits": sum(
            item.same_minute_stop_target_ambiguity for item in ordered
        ),
    }


def _candidate_additions(
    *,
    stop_rows: tuple[dict[str, Any], ...],
    funnel_rows: tuple[dict[str, Any], ...],
    execution_by_day: dict[str, tuple[CapitalizerM1Bar, ...]],
) -> tuple[PortfolioTrade, ...]:
    funnel_by_key = {_funnel_key(row): row for row in funnel_rows}
    if len(funnel_by_key) != len(funnel_rows):
        raise ValueError("duplicate STOP_INVALID_GEOMETRY funnel key")

    additions: list[PortfolioTrade] = []
    for row in stop_rows:
        if row.get("protected_at_mss_stop_valid") is not True:
            continue
        protected_raw = row.get("protected_at_mss_stop_price")
        if protected_raw is None:
            continue

        key = _stop_key(row)
        funnel = funnel_by_key.get(key)
        if funnel is None:
            raise ValueError("stop atlas row missing frozen funnel counterpart")

        day = str(row["operating_date"])
        execution = execution_by_day.get(day, ())
        if not execution:
            raise ValueError("protected rescue missing execution day")

        entry_at = datetime.fromisoformat(str(row["final_fill_at"]))
        mss_at = datetime.fromisoformat(str(row["source_first_mss_at"]))
        deadline = datetime.fromisoformat(str(funnel["h1_deadline"]))
        entry_price = Decimal(str(row["entry_price"]))
        stop_price = Decimal(str(protected_raw))
        side = str(row["side"])

        entry_index = next(
            (
                index
                for index, bar in enumerate(execution)
                if bar.opened_at == entry_at
            ),
            None,
        )
        if entry_index is None:
            raise ValueError("protected rescue fill not found in native M1")

        prefill = tuple(
            bar
            for bar in execution
            if mss_at <= bar.opened_at < entry_at
        )
        if any(
            _stop_hit(bar, side=side, stop_price=stop_price)
            for bar in prefill
        ):
            continue

        risk = abs(entry_price - stop_price)
        if risk <= 0:
            raise ValueError("protected rescue requires positive risk")
        target_price = (
            entry_price + Decimal("2") * risk
            if side == "LONG"
            else entry_price - Decimal("2") * risk
        )

        realized, reason, _, ambiguous, exit_at = v3._lifecycle(
            execution,
            entry_index=entry_index,
            side=v3.CapitalizerSide(side),
            entry_price=entry_price,
            stop_price=stop_price,
            target_price=target_price,
            deadline=deadline,
        )
        additions.append(
            PortfolioTrade(
                symbol=str(row["symbol"]),
                session=str(row["session"]),
                operating_date=day,
                entry_at=entry_at.isoformat(),
                exit_at=exit_at.isoformat(),
                realized_gross_r=str(realized),
                exit_reason=reason,
                same_minute_stop_target_ambiguity=ambiguous,
                provenance="PROTECTED_SWING_RESCUE",
            )
        )

    return tuple(
        sorted(
            additions,
            key=lambda item: (datetime.fromisoformat(item.entry_at), item.symbol),
        )
    )


def build_market_report(
    baseline_root: Path,
    stop_root: Path,
    funnel_root: Path,
    m1_root: Path,
    *,
    session: CapitalizerSession,
) -> tuple[
    dict[str, Any],
    tuple[PortfolioTrade, ...],
    tuple[PortfolioTrade, ...],
]:
    baseline = _baseline_trades(baseline_root)
    stop_rows = _stop_rows(stop_root)
    funnel_rows = _funnel_rows(funnel_root)
    if len(stop_rows) != len(funnel_rows):
        raise ValueError("stop/funnel invalid population mismatch")

    bars = tuple(iter_cibo_m1(m1_root))
    if not bars:
        raise ValueError("protected rescue requires native M1")
    symbol = bars[0].symbol
    if any(bar.symbol != symbol for bar in bars):
        raise ValueError("protected rescue requires one market per M1 root")
    if any(str(row["symbol"]) != symbol for row in stop_rows):
        raise ValueError("protected rescue stop/M1 symbol mismatch")
    if any(str(row["session"]) != session.value for row in stop_rows):
        raise ValueError("protected rescue session mismatch")

    execution_by_day, _ = _index_day_inputs(bars, session=session)
    additions = _candidate_additions(
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
    report = {
        "identity": IDENTITY,
        "symbol": symbol,
        "session": session.value,
        "stop_invalid_population": len(stop_rows),
        "protected_at_mss_stop_valid": sum(
            row.get("protected_at_mss_stop_valid") is True for row in stop_rows
        ),
        "rescued_after_prefill_stop_check": len(additions),
        "baseline_raw_trades": len(baseline),
        "candidate_raw_trades": len(candidate),
        "rescue_raw_metrics": _metrics(additions),
        "original_wait5_trades_modified": 0,
        "protected_swing_semantics": (
            "LATEST_OPPOSITE_M3_PIVOT_CONFIRMED_BEFORE_DISPLACEMENT"
        ),
        "same_v3_5pip_buffer": True,
        "same_frozen_fill": True,
        "same_h1_deadline": True,
        "fixed_2r_preserved": True,
        "stop_first_preserved": True,
        "max3_preserved": True,
        "outcome_used_for_admission": False,
        "development_window_role": "CONSUMED_DEVELOPMENT_ONLY",
        "fresh_holdout_claimed": False,
        "rule_promotion_allowed": False,
        "trader_certified": False,
        "live_authorized": False,
        "real_capital_authorized": False,
    }
    return report, baseline, candidate


def write_market(
    report: dict[str, Any],
    baseline: tuple[PortfolioTrade, ...],
    candidate: tuple[PortfolioTrade, ...],
    output: Path,
) -> None:
    output.mkdir(parents=True, exist_ok=True)
    symbol = str(report["symbol"]).lower()
    stem = (
        f"capitalizer-{symbol}-v3-source-first-wait5-"
        "protected-swing-rescue-2y-v1"
    )
    (output / f"{stem}.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    for variant, trades in (("baseline", baseline), ("candidate", candidate)):
        with (output / f"{stem}-{variant}-trades.jsonl").open(
            "w",
            encoding="utf-8",
        ) as handle:
            for trade in trades:
                handle.write(json.dumps(asdict(trade), sort_keys=True) + "\n")


def _load_market_reports(root: Path) -> list[dict[str, Any]]:
    paths = sorted(
        root.rglob(
            "capitalizer-*-v3-source-first-wait5-"
            "protected-swing-rescue-2y-v1.json"
        )
    )
    if len(paths) != 9:
        raise ValueError(f"protected rescue matrix requires 9 reports, got {len(paths)}")
    return [dict(json.loads(path.read_text(encoding="utf-8"))) for path in paths]


def _load_portfolio(
    root: Path,
    *,
    variant: str,
) -> tuple[PortfolioTrade, ...]:
    paths = sorted(
        root.rglob(
            "capitalizer-*-v3-source-first-wait5-"
            f"protected-swing-rescue-2y-v1-{variant}-trades.jsonl"
        )
    )
    if len(paths) != 9:
        raise ValueError(f"protected rescue requires 9 {variant} ledgers")
    rows: list[PortfolioTrade] = []
    for path in paths:
        with path.open(encoding="utf-8") as handle:
            for line in handle:
                if line.strip():
                    rows.append(PortfolioTrade(**json.loads(line)))
    return tuple(rows)


def build_matrix(root: Path) -> dict[str, Any]:
    reports = _load_market_reports(root)
    baseline_raw = _load_portfolio(root, variant="baseline")
    candidate_raw = _load_portfolio(root, variant="candidate")
    baseline_max3 = _max3(baseline_raw)
    candidate_max3 = _max3(candidate_raw)

    baseline_metrics = _metrics(baseline_max3)
    candidate_metrics = _metrics(candidate_max3)
    if baseline_metrics is None or candidate_metrics is None:
        raise ValueError("protected rescue requires complete portfolio metrics")

    selected_rescue = tuple(
        item
        for item in candidate_max3
        if item.provenance == "PROTECTED_SWING_RESCUE"
    )
    total_invalid = sum(int(report["stop_invalid_population"]) for report in reports)

    pf_base = Decimal(str(baseline_metrics["profit_factor"]))
    pf_candidate = Decimal(str(candidate_metrics["profit_factor"]))
    total_base = Decimal(str(baseline_metrics["total_r"]))
    total_candidate = Decimal(str(candidate_metrics["total_r"]))
    dd_base = Decimal(str(baseline_metrics["max_drawdown_r"]))
    dd_candidate = Decimal(str(candidate_metrics["max_drawdown_r"]))

    return {
        "identity": MATRIX_IDENTITY,
        "market_count": 9,
        "stop_invalid_population": total_invalid,
        "stop_invalid_control_reproduced": total_invalid == EXPECTED_STOP_INVALID,
        "protected_at_mss_stop_valid": sum(
            int(report["protected_at_mss_stop_valid"]) for report in reports
        ),
        "rescued_after_prefill_stop_check": sum(
            int(report["rescued_after_prefill_stop_check"]) for report in reports
        ),
        "baseline_raw_trades": len(baseline_raw),
        "candidate_raw_trades": len(candidate_raw),
        "baseline_max3_trades": len(baseline_max3),
        "candidate_max3_trades": len(candidate_max3),
        "selected_rescue_max3_trades": len(selected_rescue),
        "baseline_max3_metrics": baseline_metrics,
        "candidate_max3_metrics": candidate_metrics,
        "selected_rescue_metrics": _metrics(selected_rescue),
        "delta_vs_wait5": {
            "max3_trades": len(candidate_max3) - len(baseline_max3),
            "profit_factor": str(pf_candidate - pf_base),
            "total_r": str(total_candidate - total_base),
            "max_drawdown_r": str(dd_candidate - dd_base),
            "losing_streak": (
                int(candidate_metrics["max_losing_streak"])
                - int(baseline_metrics["max_losing_streak"])
            ),
        },
        "wait5_reference_check": {
            "expected_max3_trades": WAIT5_BASELINE_MAX3,
            "expected_profit_factor": str(WAIT5_BASELINE_PF),
            "expected_total_r": str(WAIT5_BASELINE_TOTAL_R),
            "expected_max_drawdown_r": str(WAIT5_BASELINE_DD_R),
        },
        "original_wait5_trades_modified": 0,
        "protected_swing_semantics": (
            "LATEST_OPPOSITE_M3_PIVOT_CONFIRMED_BEFORE_DISPLACEMENT"
        ),
        "same_v3_5pip_buffer": True,
        "same_frozen_fill": True,
        "same_h1_deadline": True,
        "fixed_2r_preserved": True,
        "stop_first_preserved": True,
        "max3_preserved": True,
        "outcome_used_for_admission": False,
        "development_window_role": "CONSUMED_DEVELOPMENT_ONLY",
        "fresh_holdout_claimed": False,
        "automatic_promotion_allowed": False,
        "rule_promotion_allowed": False,
        "trader_certified": False,
        "live_authorized": False,
        "real_capital_authorized": False,
    }


def write_matrix(report: dict[str, Any], output: Path) -> None:
    output.mkdir(parents=True, exist_ok=True)
    path = output / (
        "capitalizer-nine-market-v3-source-first-wait5-"
        "protected-swing-rescue-2y-v1.json"
    )
    path.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)

    market = sub.add_parser("market")
    market.add_argument("baseline_root", type=Path)
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
            args.baseline_root,
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
