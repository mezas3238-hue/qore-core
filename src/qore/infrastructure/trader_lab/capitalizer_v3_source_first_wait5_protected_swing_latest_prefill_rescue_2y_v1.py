"""Isolated A/B: rescue WAIT5 invalid-stop setups with latest protected swing before fill.

This is the second structural stop semantic predeclared in the outcome-free
STOP_INVALID_GEOMETRY atlas. It is not derived from the economic result of the
protected-at-MSS rescue.

Only frozen STOP_INVALID_GEOMETRY setups are eligible. Existing WAIT5 trades are
untouched. The rescue uses the latest opposite-kind M3 pivot causally confirmed
before the frozen fill, applies the same V3 5-pip buffer, requires the stop to
be valid at entry and intact after that pivot is confirmed, and preserves the
same fill, H1 deadline, fixed 2R, STOP-first precedence and portfolio MAX3.
"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from dataclasses import asdict
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

from qore.infrastructure.trader_lab import (
    capitalizer_owner_h1_m3_m1_causal_reversal_1y_v3 as v3,
)
from qore.infrastructure.trader_lab import (
    capitalizer_v3_source_first_wait5_protected_swing_rescue_2y_v1 as prior,
)
from qore.infrastructure.trader_lab.capitalizer_cibo_m1_reader_v1 import (
    CapitalizerM1Bar,
    iter_cibo_m1,
)
from qore.infrastructure.trader_lab.capitalizer_contract import (
    MAX_EXECUTIONS_PER_SESSION,
    CapitalizerSession,
)
from qore.infrastructure.trader_lab.capitalizer_exposure_graph import CapitalizerSide
from qore.infrastructure.trader_lab.capitalizer_strict_htf_gate_1y_v1 import (
    _index_day_inputs,
)

IDENTITY = (
    "QORE_CAPITALIZER_V3_SOURCE_FIRST_WAIT5_"
    "PROTECTED_SWING_LATEST_PREFILL_RESCUE_2Y_V1"
)
MATRIX_IDENTITY = (
    "QORE_CAPITALIZER_NINE_MARKET_V3_SOURCE_FIRST_WAIT5_"
    "PROTECTED_SWING_LATEST_PREFILL_RESCUE_2Y_V1"
)
EXPECTED_STOP_INVALID = 111
WAIT5_BASELINE_MAX3 = 983
WAIT5_BASELINE_PF = Decimal("1.384597543145107741177480996")
WAIT5_BASELINE_TOTAL_R = Decimal("135.7651037644532073259312101")
WAIT5_BASELINE_DD_R = Decimal("11.9420088471277198029814040")


def _stop_hit(
    bar: CapitalizerM1Bar,
    *,
    side: str,
    stop_price: Decimal,
) -> bool:
    return bool(
        bar.low <= stop_price if side == "LONG" else bar.high >= stop_price
    )


def _candidate_additions(
    *,
    stop_rows: tuple[dict[str, Any], ...],
    funnel_rows: tuple[dict[str, Any], ...],
    execution_by_day: dict[str, tuple[CapitalizerM1Bar, ...]],
) -> tuple[prior.PortfolioTrade, ...]:
    funnel_by_key = {prior._funnel_key(row): row for row in funnel_rows}
    if len(funnel_by_key) != len(funnel_rows):
        raise ValueError("duplicate STOP_INVALID_GEOMETRY funnel key")

    additions: list[prior.PortfolioTrade] = []
    for row in stop_rows:
        if row.get("protected_before_fill_stop_valid") is not True:
            continue

        stop_raw = row.get("protected_before_fill_stop_price")
        confirmed_raw = row.get("protected_before_fill_confirmed_at")
        if stop_raw is None or confirmed_raw is None:
            continue

        key = prior._stop_key(row)
        funnel = funnel_by_key.get(key)
        if funnel is None:
            raise ValueError("latest-prefill row missing frozen funnel counterpart")

        day = str(row["operating_date"])
        execution = execution_by_day.get(day, ())
        if not execution:
            raise ValueError("latest-prefill rescue missing execution day")

        entry_at = datetime.fromisoformat(str(row["final_fill_at"]))
        mss_at = datetime.fromisoformat(str(row["source_first_mss_at"]))
        protected_confirmed_at = datetime.fromisoformat(str(confirmed_raw))
        deadline = datetime.fromisoformat(str(funnel["h1_deadline"]))
        entry_price = Decimal(str(row["entry_price"]))
        stop_price = Decimal(str(stop_raw))
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
            raise ValueError("latest-prefill rescue fill missing in native M1")
        if protected_confirmed_at > entry_at:
            raise ValueError("protected swing cannot confirm after frozen fill")

        active_from = max(mss_at, protected_confirmed_at)
        prefill = tuple(
            bar
            for bar in execution
            if active_from <= bar.opened_at < entry_at
        )
        if any(
            _stop_hit(bar, side=side, stop_price=stop_price)
            for bar in prefill
        ):
            continue

        risk = abs(entry_price - stop_price)
        if risk <= 0:
            raise ValueError("latest-prefill rescue requires positive risk")
        target_price = (
            entry_price + Decimal("2") * risk
            if side == "LONG"
            else entry_price - Decimal("2") * risk
        )

        realized, reason, _, ambiguous, exit_at = v3._lifecycle(
            execution,
            entry_index=entry_index,
            side=CapitalizerSide(side),
            entry_price=entry_price,
            stop_price=stop_price,
            target_price=target_price,
            deadline=deadline,
        )
        additions.append(
            prior.PortfolioTrade(
                symbol=str(row["symbol"]),
                session=str(row["session"]),
                operating_date=day,
                entry_at=entry_at.isoformat(),
                exit_at=exit_at.isoformat(),
                realized_gross_r=str(realized),
                exit_reason=reason,
                same_minute_stop_target_ambiguity=ambiguous,
                provenance="PROTECTED_SWING_LATEST_PREFILL_RESCUE",
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
    tuple[prior.PortfolioTrade, ...],
    tuple[prior.PortfolioTrade, ...],
]:
    baseline = prior._baseline_trades(baseline_root)
    stop_rows = prior._stop_rows(stop_root)
    funnel_rows = prior._funnel_rows(funnel_root)
    if len(stop_rows) != len(funnel_rows):
        raise ValueError("latest-prefill stop/funnel invalid population mismatch")

    bars = tuple(iter_cibo_m1(m1_root))
    if not bars:
        raise ValueError("latest-prefill rescue requires native M1")
    symbol = bars[0].symbol
    if any(bar.symbol != symbol for bar in bars):
        raise ValueError("latest-prefill rescue requires one market")
    if any(str(row["symbol"]) != symbol for row in stop_rows):
        raise ValueError("latest-prefill stop/M1 symbol mismatch")
    if any(str(row["session"]) != session.value for row in stop_rows):
        raise ValueError("latest-prefill session mismatch")

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
        "protected_before_fill_stop_valid": sum(
            row.get("protected_before_fill_stop_valid") is True
            for row in stop_rows
        ),
        "protected_updated_after_mss": sum(
            bool(row.get("protected_updated_after_mss")) for row in stop_rows
        ),
        "rescued_after_active_stop_check": len(additions),
        "baseline_raw_trades": len(baseline),
        "candidate_raw_trades": len(candidate),
        "rescue_raw_metrics": prior._metrics(additions),
        "original_wait5_trades_modified": 0,
        "protected_swing_semantics": (
            "LATEST_OPPOSITE_M3_PIVOT_CONFIRMED_BEFORE_FILL"
        ),
        "semantic_predeclared_in_outcome_free_atlas": True,
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
    baseline: tuple[prior.PortfolioTrade, ...],
    candidate: tuple[prior.PortfolioTrade, ...],
    output: Path,
) -> None:
    output.mkdir(parents=True, exist_ok=True)
    symbol = str(report["symbol"]).lower()
    stem = (
        f"capitalizer-{symbol}-v3-source-first-wait5-"
        "protected-swing-latest-prefill-rescue-2y-v1"
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


def _load_reports(root: Path) -> list[dict[str, Any]]:
    paths = sorted(
        root.rglob(
            "capitalizer-*-v3-source-first-wait5-"
            "protected-swing-latest-prefill-rescue-2y-v1.json"
        )
    )
    if len(paths) != 9:
        raise ValueError(
            f"latest-prefill rescue matrix requires 9 reports, got {len(paths)}"
        )
    return [dict(json.loads(path.read_text(encoding="utf-8"))) for path in paths]


def _load_portfolio(
    root: Path,
    *,
    variant: str,
) -> tuple[prior.PortfolioTrade, ...]:
    paths = sorted(
        root.rglob(
            "capitalizer-*-v3-source-first-wait5-"
            f"protected-swing-latest-prefill-rescue-2y-v1-{variant}-trades.jsonl"
        )
    )
    if len(paths) != 9:
        raise ValueError(f"latest-prefill rescue requires 9 {variant} ledgers")
    rows: list[prior.PortfolioTrade] = []
    for path in paths:
        with path.open(encoding="utf-8") as handle:
            for line in handle:
                if line.strip():
                    rows.append(prior.PortfolioTrade(**json.loads(line)))
    return tuple(rows)


def _max3(
    trades: tuple[prior.PortfolioTrade, ...],
) -> tuple[prior.PortfolioTrade, ...]:
    grouped: dict[str, list[prior.PortfolioTrade]] = defaultdict(list)
    for trade in trades:
        grouped[f"{trade.session}:{trade.operating_date}"].append(trade)
    selected: list[prior.PortfolioTrade] = []
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


def build_matrix(root: Path) -> dict[str, Any]:
    reports = _load_reports(root)
    baseline_raw = _load_portfolio(root, variant="baseline")
    candidate_raw = _load_portfolio(root, variant="candidate")
    baseline_max3 = _max3(baseline_raw)
    candidate_max3 = _max3(candidate_raw)

    baseline_metrics = prior._metrics(baseline_max3)
    candidate_metrics = prior._metrics(candidate_max3)
    if baseline_metrics is None or candidate_metrics is None:
        raise ValueError("latest-prefill rescue needs complete portfolio metrics")

    selected_rescue = tuple(
        item
        for item in candidate_max3
        if item.provenance == "PROTECTED_SWING_LATEST_PREFILL_RESCUE"
    )
    total_invalid = sum(int(r["stop_invalid_population"]) for r in reports)
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
        "protected_before_fill_stop_valid": sum(
            int(r["protected_before_fill_stop_valid"]) for r in reports
        ),
        "protected_updated_after_mss": sum(
            int(r["protected_updated_after_mss"]) for r in reports
        ),
        "rescued_after_active_stop_check": sum(
            int(r["rescued_after_active_stop_check"]) for r in reports
        ),
        "baseline_raw_trades": len(baseline_raw),
        "candidate_raw_trades": len(candidate_raw),
        "baseline_max3_trades": len(baseline_max3),
        "candidate_max3_trades": len(candidate_max3),
        "selected_rescue_max3_trades": len(selected_rescue),
        "baseline_max3_metrics": baseline_metrics,
        "candidate_max3_metrics": candidate_metrics,
        "selected_rescue_metrics": prior._metrics(selected_rescue),
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
            "LATEST_OPPOSITE_M3_PIVOT_CONFIRMED_BEFORE_FILL"
        ),
        "semantic_predeclared_in_outcome_free_atlas": True,
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
        "protected-swing-latest-prefill-rescue-2y-v1.json"
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
