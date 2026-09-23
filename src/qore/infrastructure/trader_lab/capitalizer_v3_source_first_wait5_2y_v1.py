"""Isolated 2Y A/B: SOURCE_FIRST CISD plus causal WAIT5 execution maturation.

Only execution timing changes relative to frozen SOURCE_FIRST:
- derive the exact same V3 M1 OB/FVG zone;
- obtain the exact normal V3 fill;
- if OB/FVG overlap exists, keep the normal fill;
- if the normal fill is already >=5 minutes after M3 MSS, keep it;
- otherwise, for a no-overlap early CE fill, arm WAIT until MSS+5m;
- preserve the same FVG CE, same structural stop, same H1 deadline;
- structural stop before an eligible CE retest invalidates the opportunity;
- the first eligible retest is filled at the same CE;
- same-bar eligible fill+stop retains frozen V3 STOP-first lifecycle precedence.

No future-V3 relation, market/session result, side, quarter, or outcome is used.
This consumed 2Y development A/B cannot promote a live rule by itself.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import asdict
from datetime import date, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any

from qore.infrastructure.trader_lab import (
    capitalizer_owner_h1_m3_m1_causal_reversal_1y_v3 as v3,
)
from qore.infrastructure.trader_lab.capitalizer_cibo_m1_reader_v1 import (
    CapitalizerM1Bar,
)
from qore.infrastructure.trader_lab.capitalizer_contract import (
    MAX_EXECUTIONS_PER_SESSION,
    CapitalizerSession,
)
from qore.infrastructure.trader_lab.capitalizer_strict_htf_gate_1y_v1 import (
    Pivot,
    TFBar,
)
from qore.infrastructure.trader_lab.capitalizer_v3_frozen_replay_2y_v1 import (
    LOOKBACK_START,
    WINDOW_END,
    WINDOW_START,
    _v3_window,
)
from qore.infrastructure.trader_lab.capitalizer_v3_source_first_cisd_v1 import (
    BOUNDARY_SEMANTICS,
    IDENTITY as SOURCE_FIRST_HELPER_IDENTITY,
    find_source_first_m3_mss,
)

IDENTITY = "QORE_CAPITALIZER_V3_SOURCE_FIRST_WAIT5_2Y_V1"
MATRIX_IDENTITY = "QORE_CAPITALIZER_NINE_MARKET_V3_SOURCE_FIRST_WAIT5_2Y_V1"
WAIT_MINUTES = 5

SOURCE_FIRST_BASELINE_TRADES = 1118
SOURCE_FIRST_BASELINE_PF = Decimal("1.245847667002435638004144440")
SOURCE_FIRST_BASELINE_TOTAL_R = Decimal("105.0188363132290669775787956")
SOURCE_FIRST_BASELINE_MEAN_R = Decimal("0.09393455841970399550767334132")
SOURCE_FIRST_BASELINE_DD_R = Decimal("18.13811917508204475002954529")
SOURCE_FIRST_BASELINE_LS = 10

V3_BASELINE_TRADES = 474
V3_BASELINE_PF = Decimal("1.283270342004661566350801358")
V3_BASELINE_DD_R = Decimal("13.43559872546085473546771142")


def _stop_hit(
    bar: CapitalizerM1Bar,
    *,
    side: str,
    stop_price: Decimal,
) -> bool:
    return bool(
        bar.low <= stop_price
        if side == "LONG"
        else bar.high >= stop_price
    )


def _find_wait5_fill(
    execution: tuple[CapitalizerM1Bar, ...],
    *,
    event: v3.M3MssEvent,
    zone: v3.M1EntryZone,
    stop_price: Decimal,
    deadline: datetime,
) -> tuple[tuple[int, Decimal, str] | None, str]:
    ce = (zone.fvg_low + zone.fvg_high) / Decimal("2")
    eligible_at = event.confirmed_at + timedelta(minutes=WAIT_MINUTES)

    for index, bar in enumerate(execution):
        if bar.opened_at < event.confirmed_at:
            continue
        if bar.opened_at >= deadline:
            break

        stop_hit = _stop_hit(
            bar,
            side=event.side.value,
            stop_price=stop_price,
        )
        eligible = bar.opened_at >= eligible_at
        ce_touch = eligible and bar.low <= ce <= bar.high

        if stop_hit and not ce_touch:
            return None, "STOP_INVALIDATED_BEFORE_REFILL"
        if ce_touch:
            return (
                (index, ce, "FVG_CE_50_WAIT5"),
                (
                    "REFILL_STOP_SAME_BAR"
                    if stop_hit
                    else "REFILL_AVAILABLE"
                ),
            )

    return None, "NO_REFILL_BEFORE_DEADLINE"


def _wait5_scan_day(
    *,
    symbol: str,
    session: CapitalizerSession,
    operating_day: date,
    prior_session: Any,
    execution: tuple[CapitalizerM1Bar, ...],
    all_bars: tuple[CapitalizerM1Bar, ...],
    h1_swings: Any,
    m5: tuple[TFBar, ...],
    m5_closes: tuple[datetime, ...],
    m3: tuple[TFBar, ...],
    m3_closes: tuple[datetime, ...],
    m3_pivots: tuple[Pivot, ...],
    buffer_price: Decimal,
    stages: Counter[str],
) -> tuple[v3.V3Trade, ...]:
    if len(execution) < 15:
        stages["EXECUTION_WINDOW_TOO_SPARSE"] += 1
        return ()

    previous_day = v3._previous_day_range(
        all_bars,
        operating_day=operating_day,
    )
    results: list[v3.V3Trade] = []

    for h1_open, h1_deadline, hour_bars in v3._h1_windows(execution):
        if len(results) >= MAX_EXECUTIONS_PER_SESSION:
            break

        stages["H1_HOUR_SCANNED"] += 1
        levels = v3._liquidity_levels(
            prior_session=prior_session,
            previous_day=previous_day,
            h1_swings=h1_swings,
            hour_open=h1_open,
        )
        if not levels:
            stages["H1_HOUR_NO_LIQUIDITY"] += 1
            continue

        stages["H1_HOUR_WITH_LIQUIDITY"] += 1
        sweep_seen, closeback = v3._find_sweep_closeback(
            hour_bars,
            levels=levels,
            m5=m5,
            m5_closes=m5_closes,
            h1_open=h1_open,
            h1_deadline=h1_deadline,
        )
        if sweep_seen:
            stages["H1_SWEEP_DETECTED"] += 1
        if closeback is None:
            if sweep_seen:
                stages["M5_CLOSEBACK_MISSING"] += 1
            continue

        stages["M5_CLOSEBACK_CONFIRMED"] += 1
        mss = find_source_first_m3_mss(
            m3,
            m3_closes,
            m3_pivots,
            sweep_at=closeback.sweep_at,
            after=closeback.closeback_at,
            before=h1_deadline,
            side=closeback.side,
        )
        if mss is None:
            stages["M3_MSS_MISSING"] += 1
            continue

        stages["M3_MSS_CONFIRMED"] += 1
        zone = v3._m1_causal_zone(execution, event=mss)
        if zone is None:
            stages["M1_CAUSAL_FVG_MISSING"] += 1
            continue

        stages["M1_CAUSAL_FVG_CONFIRMED"] += 1
        has_overlap = (
            zone.overlap_low is not None
            and zone.overlap_high is not None
        )
        if has_overlap:
            stages["M1_OB_FVG_CONFLUENCE"] += 1

        stop_price = (
            mss.broken_swing_price - buffer_price
            if closeback.side.value == "LONG"
            else mss.broken_swing_price + buffer_price
        )

        normal_fill = v3._find_m1_fill(
            execution,
            event=mss,
            zone=zone,
            deadline=h1_deadline,
        )
        if normal_fill is None:
            stages["M1_FILL_MISSING"] += 1
            continue

        entry_index, entry_price, entry_mode = normal_fill
        normal_entry_at = execution[entry_index].opened_at
        eligible_at = mss.confirmed_at + timedelta(minutes=WAIT_MINUTES)
        wait_required = (
            not has_overlap
            and normal_entry_at < eligible_at
        )

        if wait_required:
            stages["WAIT5_ARMED"] += 1
            wait_fill, wait_status = _find_wait5_fill(
                execution,
                event=mss,
                zone=zone,
                stop_price=stop_price,
                deadline=h1_deadline,
            )
            stages[f"WAIT5_{wait_status}"] += 1
            if wait_fill is None:
                continue
            entry_index, entry_price, entry_mode = wait_fill

        valid_stop = (
            stop_price < entry_price
            if closeback.side.value == "LONG"
            else stop_price > entry_price
        )
        if not valid_stop:
            stages["M3_STOP_INVALID_GEOMETRY"] += 1
            continue

        risk = abs(entry_price - stop_price)
        target_price = (
            entry_price + Decimal("2") * risk
            if closeback.side.value == "LONG"
            else entry_price - Decimal("2") * risk
        )
        realized, reason, held, ambiguous, exit_at = v3._lifecycle(
            execution,
            entry_index=entry_index,
            side=closeback.side,
            entry_price=entry_price,
            stop_price=stop_price,
            target_price=target_price,
            deadline=h1_deadline,
        )

        stages["ENTRY_EXECUTED"] += 1
        results.append(
            v3.V3Trade(
                symbol=symbol,
                session=session.value,
                operating_date=operating_day.isoformat(),
                side=closeback.side.value,
                h1_open=h1_open.isoformat(),
                h1_deadline=h1_deadline.isoformat(),
                liquidity_source=closeback.reference.source,
                liquidity_kind=closeback.reference.kind,
                liquidity_price=str(closeback.reference.price),
                h1_sweep_at=closeback.sweep_at.isoformat(),
                h1_sweep_extreme=str(closeback.sweep_extreme),
                m5_closeback_at=closeback.closeback_at.isoformat(),
                m3_mss_at=mss.confirmed_at.isoformat(),
                m3_broken_swing_price=str(mss.broken_swing_price),
                m3_cisd_boundary=str(mss.cisd_boundary),
                m3_body_ratio=str(mss.body_ratio),
                m3_atr14=str(mss.atr14),
                m3_displacement_range=str(mss.displacement_range),
                m1_ob_opened_at=zone.ob_opened_at.isoformat(),
                m1_ob_low=str(zone.ob_low),
                m1_ob_high=str(zone.ob_high),
                m1_fvg_confirmed_at=zone.fvg_confirmed_at.isoformat(),
                m1_fvg_low=str(zone.fvg_low),
                m1_fvg_high=str(zone.fvg_high),
                m1_ob_fvg_overlap=has_overlap,
                entry_mode=entry_mode,
                entry_at=execution[entry_index].opened_at.isoformat(),
                exit_at=exit_at.isoformat(),
                entry_price=str(entry_price),
                stop_price=str(stop_price),
                stop_buffer_price=str(buffer_price),
                target_price=str(target_price),
                realized_gross_r=str(realized),
                exit_reason=reason,
                m1_bars_held=held,
                same_minute_stop_target_ambiguity=ambiguous,
            )
        )

    return tuple(results)


@contextmanager
def _wait5_scan_patch() -> Iterator[None]:
    original = v3._scan_day
    try:
        v3._scan_day = _wait5_scan_day
        yield
    finally:
        v3._scan_day = original


def build_market_report(
    m1_root: Path,
    *,
    session: CapitalizerSession,
) -> tuple[dict[str, Any], tuple[v3.V3Trade, ...]]:
    with _wait5_scan_patch(), _v3_window():
        source_report, trades = v3.build_market_report(
            m1_root,
            session=session,
        )

    report = asdict(source_report)
    stage_counts = dict(source_report.stage_counts)
    report.update(
        {
            "identity": IDENTITY,
            "source_strategy_identity": v3.IDENTITY,
            "source_first_helper_identity": SOURCE_FIRST_HELPER_IDENTITY,
            "boundary_semantics": BOUNDARY_SEMANTICS,
            "wait_minutes": WAIT_MINUTES,
            "wait5_armed": stage_counts.get("WAIT5_ARMED", 0),
            "wait5_refill_available": stage_counts.get(
                "WAIT5_REFILL_AVAILABLE", 0
            ),
            "wait5_refill_stop_same_bar": stage_counts.get(
                "WAIT5_REFILL_STOP_SAME_BAR", 0
            ),
            "wait5_stop_invalidated": stage_counts.get(
                "WAIT5_STOP_INVALIDATED_BEFORE_REFILL", 0
            ),
            "wait5_no_refill": stage_counts.get(
                "WAIT5_NO_REFILL_BEFORE_DEADLINE", 0
            ),
            "window_start": WINDOW_START.isoformat(),
            "window_end_exclusive": WINDOW_END.isoformat(),
            "lookback_start": LOOKBACK_START.isoformat(),
            "variant_only_change": "SOURCE_FIRST_M1_EXECUTION_MATURATION_WAIT5",
            "same_fvg_zone_preserved": True,
            "same_stop_preserved": True,
            "same_h1_deadline_preserved": True,
            "source_first_boundary_changed": False,
            "sweep_changed": False,
            "m5_closeback_changed": False,
            "swing_break_changed": False,
            "body_threshold_changed": False,
            "atr_threshold_changed": False,
            "fvg_changed": False,
            "target_changed": False,
            "max3_changed": False,
            "outcome_used_for_admission": False,
            "future_v3_relation_used": False,
            "diagnostic_window_role": "CONSUMED_DIAGNOSTIC_RESEARCH",
            "fresh_holdout_claimed": False,
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
    stem = f"capitalizer-{symbol}-v3-source-first-wait5-2y-v1"
    (output / f"{stem}.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    with (output / f"{stem}-trades.jsonl").open("w", encoding="utf-8") as handle:
        for trade in trades:
            handle.write(json.dumps(asdict(trade), sort_keys=True) + "\n")


def _load_reports(root: Path) -> list[dict[str, Any]]:
    paths = sorted(
        root.rglob("capitalizer-*-v3-source-first-wait5-2y-v1.json")
    )
    if len(paths) != 9:
        raise ValueError(f"WAIT5 matrix requires 9 reports, got {len(paths)}")
    reports = [dict(json.loads(path.read_text(encoding="utf-8"))) for path in paths]
    if {str(item["symbol"]) for item in reports} != v3.EXPECTED_SYMBOLS:
        raise ValueError("WAIT5 universe mismatch")
    return reports


def _load_trades(root: Path) -> tuple[v3.V3Trade, ...]:
    rows: list[v3.V3Trade] = []
    for path in sorted(
        root.rglob("capitalizer-*-v3-source-first-wait5-2y-v1-trades.jsonl")
    ):
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
    reports = _load_reports(root)
    raw = _load_trades(root)
    max3 = v3._portfolio_max3(raw)
    metrics = v3._metrics(max3)
    if metrics is None or metrics.profit_factor is None or metrics.mean_r is None:
        raise ValueError("WAIT5 experiment requires complete MAX3 metrics")

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

    wait_totals = Counter[str]()
    for report in reports:
        wait_totals["armed"] += int(report["wait5_armed"])
        wait_totals["refill_available"] += int(
            report["wait5_refill_available"]
        )
        wait_totals["refill_stop_same_bar"] += int(
            report["wait5_refill_stop_same_bar"]
        )
        wait_totals["stop_invalidated"] += int(
            report["wait5_stop_invalidated"]
        )
        wait_totals["no_refill"] += int(report["wait5_no_refill"])

    pf = Decimal(metrics.profit_factor)
    total = Decimal(metrics.total_r)
    mean = Decimal(metrics.mean_r)
    dd = Decimal(metrics.max_drawdown_r)
    return {
        "identity": MATRIX_IDENTITY,
        "source_strategy_identity": v3.IDENTITY,
        "source_first_helper_identity": SOURCE_FIRST_HELPER_IDENTITY,
        "boundary_semantics": BOUNDARY_SEMANTICS,
        "wait_minutes": WAIT_MINUTES,
        "market_count": 9,
        "window_start": WINDOW_START.isoformat(),
        "window_end_exclusive": WINDOW_END.isoformat(),
        "raw_trades": len(raw),
        "max3_selected_trades": len(max3),
        "max3_metrics": asdict(metrics),
        "wait5_counts": dict(wait_totals),
        "per_session": per_session,
        "per_market": per_market,
        "source_first_baseline": {
            "trades": SOURCE_FIRST_BASELINE_TRADES,
            "profit_factor": str(SOURCE_FIRST_BASELINE_PF),
            "total_r": str(SOURCE_FIRST_BASELINE_TOTAL_R),
            "mean_r": str(SOURCE_FIRST_BASELINE_MEAN_R),
            "max_drawdown_r": str(SOURCE_FIRST_BASELINE_DD_R),
            "losing_streak": SOURCE_FIRST_BASELINE_LS,
        },
        "delta_vs_source_first": {
            "trades": len(max3) - SOURCE_FIRST_BASELINE_TRADES,
            "profit_factor": str(pf - SOURCE_FIRST_BASELINE_PF),
            "total_r": str(total - SOURCE_FIRST_BASELINE_TOTAL_R),
            "mean_r": str(mean - SOURCE_FIRST_BASELINE_MEAN_R),
            "max_drawdown_r": str(dd - SOURCE_FIRST_BASELINE_DD_R),
            "losing_streak": (
                metrics.max_losing_streak - SOURCE_FIRST_BASELINE_LS
            ),
        },
        "v3_baseline": {
            "trades": V3_BASELINE_TRADES,
            "profit_factor": str(V3_BASELINE_PF),
            "max_drawdown_r": str(V3_BASELINE_DD_R),
        },
        "variant_only_change": "SOURCE_FIRST_M1_EXECUTION_MATURATION_WAIT5",
        "same_fvg_zone_preserved": True,
        "same_stop_preserved": True,
        "same_h1_deadline_preserved": True,
        "source_first_boundary_changed": False,
        "sweep_changed": False,
        "m5_closeback_changed": False,
        "swing_break_changed": False,
        "body_threshold_changed": False,
        "atr_threshold_changed": False,
        "fvg_changed": False,
        "target_changed": False,
        "max3_changed": False,
        "outcome_used_for_admission": False,
        "future_v3_relation_used": False,
        "diagnostic_window_role": "CONSUMED_DIAGNOSTIC_RESEARCH",
        "fresh_holdout_claimed": False,
        "economic_candidate": False,
        "rule_promotion_allowed": False,
        "trader_certified": False,
        "live_authorized": False,
        "real_capital_authorized": False,
    }


def write_matrix(report: dict[str, Any], output: Path) -> None:
    output.mkdir(parents=True, exist_ok=True)
    path = (
        output
        / "capitalizer-nine-market-v3-source-first-wait5-2y-v1.json"
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
                    "wait5_armed": report["wait5_armed"],
                    "wait5_refill_available": report["wait5_refill_available"],
                    "wait5_stop_invalidated": report["wait5_stop_invalidated"],
                    "wait5_no_refill": report["wait5_no_refill"],
                    "trades": len(trades),
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
