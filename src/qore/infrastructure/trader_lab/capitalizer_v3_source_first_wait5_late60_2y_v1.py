"""Consumed-window A/B: SOURCE_FIRST + WAIT5 with structural LATE60 carry.

Baseline trades are loaded unchanged from the frozen WAIT5 artifact.

Only NORMAL_FILL_MISSING setups from the frozen funnel may contribute a new trade.
A late trade is admissible only when:
- the frozen SOURCE_FIRST MSS reconstructs exactly;
- the exact same frozen M1 OB/FVG zone reconstructs;
- there was no normal V3 fill before the original H1 deadline;
- the original buffered protected-swing stop remained intact;
- the first exact OB/FVG or CE fill occurs after the old deadline and before
  old deadline + 60 minutes, bounded by available assigned-session M1.

No new MSS, FVG, liquidity event, stop rule or target rule is introduced.
Late entries use the same fixed 2R construction and expire at the extended
boundary. Same-bar STOP-first precedence remains frozen V3 behavior.

This 2Y window is consumed diagnostic evidence and cannot promote a live rule.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
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
    iter_cibo_m1,
)
from qore.infrastructure.trader_lab.capitalizer_contract import (
    MAX_EXECUTIONS_PER_SESSION,
    CapitalizerSession,
)
from qore.infrastructure.trader_lab.capitalizer_exposure_graph import CapitalizerSide
from qore.infrastructure.trader_lab.capitalizer_full_ict_density_scanner_1y_v1 import (
    _aggregate_h1,
)
from qore.infrastructure.trader_lab.capitalizer_strict_htf_gate_1y_v1 import (
    TFBar,
    _aggregate_tf,
    _index_day_inputs,
    _pivots,
)
from qore.infrastructure.trader_lab.capitalizer_v3_source_first_cisd_v1 import (
    find_source_first_m3_mss,
)

IDENTITY = "QORE_CAPITALIZER_V3_SOURCE_FIRST_WAIT5_LATE60_2Y_V1"
MATRIX_IDENTITY = (
    "QORE_CAPITALIZER_NINE_MARKET_V3_SOURCE_FIRST_WAIT5_LATE60_2Y_V1"
)
EXTENSION_MINUTES = 60
EXPECTED_WAIT5_RAW = 1003
EXPECTED_WAIT5_MAX3 = 983
EXPECTED_FILL_MISS = 1091
EXPECTED_CLEAN_LATE = 376

WAIT5_PF = Decimal("1.384597543145107741177480996")
WAIT5_TOTAL_R = Decimal("135.7651037644532073259312101")
WAIT5_MEAN_R = Decimal("0.1381130251927296107079666430")
WAIT5_DD_R = Decimal("11.9420088471277198029814040")
WAIT5_LS = 9


def _aware(value: str) -> datetime:
    return datetime.fromisoformat(value)


def _load_wait5(
    root: Path,
) -> tuple[dict[str, Any], tuple[v3.V3Trade, ...]]:
    reports = sorted(root.rglob("capitalizer-*-v3-source-first-wait5-2y-v1.json"))
    trades = sorted(
        root.rglob("capitalizer-*-v3-source-first-wait5-2y-v1-trades.jsonl")
    )
    if len(reports) != 1 or len(trades) != 1:
        raise ValueError("LATE60 requires one WAIT5 market artifact")
    report = dict(json.loads(reports[0].read_text(encoding="utf-8")))
    rows: list[v3.V3Trade] = []
    with trades[0].open(encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                rows.append(v3.V3Trade(**json.loads(line)))
    return report, tuple(rows)


def _load_funnel_rows(root: Path) -> dict[tuple[str, str], dict[str, Any]]:
    paths = sorted(
        root.rglob(
            "capitalizer-*-v3-source-first-wait5-funnel-atlas-2y-v1-rows.jsonl"
        )
    )
    if len(paths) != 1:
        raise ValueError("LATE60 requires one funnel ledger")
    result: dict[tuple[str, str], dict[str, Any]] = {}
    with paths[0].open(encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            raw = json.loads(line)
            if not isinstance(raw, dict):
                raise ValueError("funnel row must be object")
            key = (str(raw["operating_date"]), str(raw["source_first_mss_at"]))
            result[key] = raw
    return result


def _load_clean_late_rows(root: Path) -> tuple[dict[str, Any], ...]:
    paths = sorted(
        root.rglob(
            "capitalizer-*-v3-source-first-fill-miss-anatomy-2y-v1-rows.jsonl"
        )
    )
    if len(paths) != 1:
        raise ValueError("LATE60 requires one fill-miss anatomy ledger")
    rows: list[dict[str, Any]] = []
    with paths[0].open(encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            raw = json.loads(line)
            if not isinstance(raw, dict):
                raise ValueError("anatomy row must be object")
            if raw.get("late_status") == "LATE_FILL_WITHIN_60M_CLEAN":
                rows.append(raw)
    return tuple(rows)


def _stop_hit(
    bar: CapitalizerM1Bar,
    *,
    side: CapitalizerSide,
    stop_price: Decimal,
) -> bool:
    return bool(
        bar.low <= stop_price
        if side is CapitalizerSide.LONG
        else bar.high >= stop_price
    )


def _find_late_fill(
    execution: tuple[CapitalizerM1Bar, ...],
    *,
    event: v3.M3MssEvent,
    zone: v3.M1EntryZone,
    stop_price: Decimal,
    original_deadline: datetime,
    extended_deadline: datetime,
) -> tuple[tuple[int, Decimal, str] | None, str]:
    for bar in execution:
        if bar.opened_at < event.confirmed_at:
            continue
        if bar.opened_at >= original_deadline:
            break
        if _stop_hit(bar, side=event.side, stop_price=stop_price):
            return None, "STOP_INVALIDATED_PRE_DEADLINE"

    ce = (zone.fvg_low + zone.fvg_high) / Decimal("2")
    ob_retest: Decimal | None = None
    if zone.overlap_low is not None and zone.overlap_high is not None:
        ob_retest = (
            zone.overlap_high
            if event.side is CapitalizerSide.LONG
            else zone.overlap_low
        )

    for index, bar in enumerate(execution):
        if bar.opened_at < original_deadline:
            continue
        if bar.opened_at >= extended_deadline:
            break

        fill_price: Decimal | None = None
        fill_mode: str | None = None
        if ob_retest is not None and bar.low <= ob_retest <= bar.high:
            fill_price = ob_retest
            fill_mode = "LATE60_OB_FVG_RETEST"
        elif bar.low <= ce <= bar.high:
            fill_price = ce
            fill_mode = "LATE60_FVG_CE_50"

        stop_hit = _stop_hit(bar, side=event.side, stop_price=stop_price)
        if fill_price is not None and fill_mode is not None:
            return (
                (index, fill_price, fill_mode),
                "LATE_FILL_STOP_SAME_BAR" if stop_hit else "LATE_FILL_CLEAN",
            )
        if stop_hit:
            return None, "STOP_INVALIDATED_BEFORE_LATE_FILL"

    return None, "NO_LATE_FILL_WITHIN_60M"


def _reconstruct_closeback(
    *,
    raw: dict[str, Any],
    operating_day: date,
    execution: tuple[CapitalizerM1Bar, ...],
    all_bars: tuple[CapitalizerM1Bar, ...],
    h1_swings: Any,
    m5: tuple[TFBar, ...],
    m5_closes: tuple[datetime, ...],
    prior_session: Any,
) -> v3.SweepCloseback:
    deadline = _aware(str(raw["h1_deadline"]))
    expected_closeback = _aware(str(raw["closeback_at"]))
    expected_sweep = _aware(str(raw["sweep_at"]))
    expected_side = CapitalizerSide(str(raw["side"]))
    previous_day = v3._previous_day_range(
        all_bars,
        operating_day=operating_day,
    )

    for h1_open, h1_deadline, hour_bars in v3._h1_windows(execution):
        if h1_deadline != deadline:
            continue
        levels = v3._liquidity_levels(
            prior_session=prior_session,
            previous_day=previous_day,
            h1_swings=h1_swings,
            hour_open=h1_open,
        )
        _, closeback = v3._find_sweep_closeback(
            hour_bars,
            levels=levels,
            m5=m5,
            m5_closes=m5_closes,
            h1_open=h1_open,
            h1_deadline=h1_deadline,
        )
        if closeback is None:
            break
        if (
            closeback.closeback_at != expected_closeback
            or closeback.sweep_at != expected_sweep
            or closeback.side is not expected_side
        ):
            raise ValueError("LATE60 closeback reconstruction mismatch")
        return closeback

    raise ValueError("LATE60 could not reconstruct frozen closeback")


def _market_max3(
    baseline: tuple[v3.V3Trade, ...],
    late: tuple[v3.V3Trade, ...],
) -> tuple[tuple[v3.V3Trade, ...], dict[str, int]]:
    combined = sorted(
        [*baseline, *late],
        key=lambda item: (
            _aware(item.entry_at),
            1 if item.entry_mode.startswith("LATE60_") else 0,
            item.side,
        ),
    )
    seen: set[tuple[str, str]] = set()
    deduped: list[v3.V3Trade] = []
    duplicate_late = 0
    for trade in combined:
        key = (trade.operating_date, trade.entry_at)
        if key in seen:
            if trade.entry_mode.startswith("LATE60_"):
                duplicate_late += 1
            continue
        seen.add(key)
        deduped.append(trade)

    grouped: dict[str, list[v3.V3Trade]] = defaultdict(list)
    for trade in deduped:
        grouped[trade.operating_date].append(trade)

    selected: list[v3.V3Trade] = []
    blocked_late = 0
    blocked_baseline = 0
    for operating_date in sorted(grouped):
        ordered = sorted(
            grouped[operating_date],
            key=lambda item: (
                _aware(item.entry_at),
                1 if item.entry_mode.startswith("LATE60_") else 0,
            ),
        )
        chosen = ordered[:MAX_EXECUTIONS_PER_SESSION]
        selected.extend(chosen)
        for trade in ordered[MAX_EXECUTIONS_PER_SESSION:]:
            if trade.entry_mode.startswith("LATE60_"):
                blocked_late += 1
            else:
                blocked_baseline += 1

    return (
        tuple(sorted(selected, key=lambda item: (_aware(item.entry_at), item.symbol))),
        {
            "duplicate_late_collision": duplicate_late,
            "late_blocked_by_market_max3": blocked_late,
            "baseline_displaced_by_market_max3": blocked_baseline,
        },
    )


def build_market_report(
    wait5_root: Path,
    funnel_root: Path,
    anatomy_root: Path,
    m1_root: Path,
) -> tuple[dict[str, Any], tuple[v3.V3Trade, ...]]:
    wait5_report, baseline = _load_wait5(wait5_root)
    symbol = str(wait5_report["symbol"])
    session = CapitalizerSession(str(wait5_report["session"]))
    funnel = _load_funnel_rows(funnel_root)
    anatomy = _load_clean_late_rows(anatomy_root)

    all_bars = tuple(iter_cibo_m1(m1_root))
    if not all_bars or all_bars[0].symbol != symbol:
        raise ValueError("LATE60 native M1 symbol mismatch")
    h1 = _aggregate_h1(all_bars)
    h1_swings = v3._build_h1_swings(h1)
    m5 = _aggregate_tf(all_bars, minutes=5)
    m5_closes = tuple(item.closed_at for item in m5)
    m3 = _aggregate_tf(all_bars, minutes=3)
    m3_closes = tuple(item.closed_at for item in m3)
    m3_pivots = _pivots(m3)
    buffer_price = v3._stop_buffer(all_bars)
    execution_by_day, reference_by_day = _index_day_inputs(
        all_bars,
        session=session,
    )

    stages: Counter[str] = Counter()
    late_trades: list[v3.V3Trade] = []

    for row in anatomy:
        operating_date = str(row["operating_date"])
        mss_at = str(row["source_first_mss_at"])
        frozen = funnel.get((operating_date, mss_at))
        if frozen is None:
            raise ValueError("LATE60 missing matching frozen funnel row")
        execution = execution_by_day.get(operating_date, ())
        if not execution:
            raise ValueError("LATE60 missing execution bars")

        operating_day = date.fromisoformat(operating_date)
        closeback = _reconstruct_closeback(
            raw=frozen,
            operating_day=operating_day,
            execution=execution,
            all_bars=all_bars,
            h1_swings=h1_swings,
            m5=m5,
            m5_closes=m5_closes,
            prior_session=reference_by_day.get(operating_date),
        )
        original_deadline = _aware(str(frozen["h1_deadline"]))
        extended_deadline = original_deadline + timedelta(
            minutes=EXTENSION_MINUTES
        )
        event = find_source_first_m3_mss(
            m3,
            m3_closes,
            m3_pivots,
            sweep_at=closeback.sweep_at,
            after=closeback.closeback_at,
            before=original_deadline,
            side=closeback.side,
        )
        if event is None or event.confirmed_at.isoformat() != mss_at:
            raise ValueError("LATE60 SOURCE_FIRST MSS mismatch")
        zone = v3._m1_causal_zone(execution, event=event)
        if zone is None:
            raise ValueError("LATE60 clean-late row lacks reconstructed FVG")
        if v3._find_m1_fill(
            execution,
            event=event,
            zone=zone,
            deadline=original_deadline,
        ) is not None:
            raise ValueError("LATE60 candidate unexpectedly has normal fill")

        stop_price = (
            event.broken_swing_price - buffer_price
            if event.side is CapitalizerSide.LONG
            else event.broken_swing_price + buffer_price
        )
        late_fill, status = _find_late_fill(
            execution,
            event=event,
            zone=zone,
            stop_price=stop_price,
            original_deadline=original_deadline,
            extended_deadline=extended_deadline,
        )
        stages[status] += 1
        if late_fill is None:
            raise ValueError("anatomy clean late fill did not reproduce")

        entry_index, entry_price, entry_mode = late_fill
        entry_at = execution[entry_index].opened_at
        if entry_at.isoformat() != str(row["late_fill_at"]):
            raise ValueError("LATE60 late-fill timestamp mismatch")
        valid_stop = (
            stop_price < entry_price
            if event.side is CapitalizerSide.LONG
            else stop_price > entry_price
        )
        if not valid_stop:
            stages["LATE60_STOP_INVALID_GEOMETRY"] += 1
            continue

        risk = abs(entry_price - stop_price)
        target_price = (
            entry_price + Decimal("2") * risk
            if event.side is CapitalizerSide.LONG
            else entry_price - Decimal("2") * risk
        )
        realized, reason, held, ambiguous, exit_at = v3._lifecycle(
            execution,
            entry_index=entry_index,
            side=event.side,
            entry_price=entry_price,
            stop_price=stop_price,
            target_price=target_price,
            deadline=extended_deadline,
        )
        late_trades.append(
            v3.V3Trade(
                symbol=symbol,
                session=session.value,
                operating_date=operating_date,
                side=event.side.value,
                h1_open=closeback.h1_open.isoformat(),
                h1_deadline=extended_deadline.isoformat(),
                liquidity_source=closeback.reference.source,
                liquidity_kind=closeback.reference.kind,
                liquidity_price=str(closeback.reference.price),
                h1_sweep_at=closeback.sweep_at.isoformat(),
                h1_sweep_extreme=str(closeback.sweep_extreme),
                m5_closeback_at=closeback.closeback_at.isoformat(),
                m3_mss_at=event.confirmed_at.isoformat(),
                m3_broken_swing_price=str(event.broken_swing_price),
                m3_cisd_boundary=str(event.cisd_boundary),
                m3_body_ratio=str(event.body_ratio),
                m3_atr14=str(event.atr14),
                m3_displacement_range=str(event.displacement_range),
                m1_ob_opened_at=zone.ob_opened_at.isoformat(),
                m1_ob_low=str(zone.ob_low),
                m1_ob_high=str(zone.ob_high),
                m1_fvg_confirmed_at=zone.fvg_confirmed_at.isoformat(),
                m1_fvg_low=str(zone.fvg_low),
                m1_fvg_high=str(zone.fvg_high),
                m1_ob_fvg_overlap=(
                    zone.overlap_low is not None
                    and zone.overlap_high is not None
                ),
                entry_mode=entry_mode,
                entry_at=entry_at.isoformat(),
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

    selected, selection = _market_max3(baseline, tuple(late_trades))
    metrics = v3._metrics(selected)
    report = {
        "identity": IDENTITY,
        "symbol": symbol,
        "session": session.value,
        "baseline_wait5_raw": len(baseline),
        "clean_late_rows": len(anatomy),
        "late_candidates_valid_geometry": len(late_trades),
        "market_raw_after_late60": len(selected),
        "late_selected_after_market_max3": sum(
            trade.entry_mode.startswith("LATE60_") for trade in selected
        ),
        "selection_counts": selection,
        "late_status_counts": dict(sorted(stages.items())),
        "raw_metrics": None if metrics is None else asdict(metrics),
        "variant_only_change": "WAIT5_NORMAL_FILL_MISSING_LATE60_CARRY",
        "same_source_first_mss_preserved": True,
        "same_fvg_zone_preserved": True,
        "same_fill_level_preserved": True,
        "same_stop_preserved": True,
        "same_target_rule_preserved": True,
        "entry_window_extended_minutes": EXTENSION_MINUTES,
        "late_lifecycle_extended_to_same_boundary": True,
        "new_mss_allowed": False,
        "new_fvg_allowed": False,
        "outcome_used_for_admission": False,
        "diagnostic_window_role": "CONSUMED_DIAGNOSTIC_RESEARCH",
        "fresh_holdout_claimed": False,
        "economic_candidate": False,
        "rule_promotion_allowed": False,
        "trader_certified": False,
        "live_authorized": False,
        "real_capital_authorized": False,
    }
    return report, selected


def write_market(
    report: dict[str, Any],
    trades: tuple[v3.V3Trade, ...],
    output: Path,
) -> None:
    output.mkdir(parents=True, exist_ok=True)
    symbol = str(report["symbol"]).lower()
    stem = f"capitalizer-{symbol}-v3-source-first-wait5-late60-2y-v1"
    (output / f"{stem}.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    with (output / f"{stem}-trades.jsonl").open("w", encoding="utf-8") as handle:
        for trade in trades:
            handle.write(json.dumps(asdict(trade), sort_keys=True) + "\n")


def _load_reports(root: Path) -> list[dict[str, Any]]:
    paths = sorted(
        root.rglob("capitalizer-*-v3-source-first-wait5-late60-2y-v1.json")
    )
    if len(paths) != 9:
        raise ValueError(f"LATE60 matrix requires 9 reports, got {len(paths)}")
    return [dict(json.loads(path.read_text(encoding="utf-8"))) for path in paths]


def _load_trades(root: Path) -> tuple[v3.V3Trade, ...]:
    rows: list[v3.V3Trade] = []
    for path in sorted(
        root.rglob(
            "capitalizer-*-v3-source-first-wait5-late60-2y-v1-trades.jsonl"
        )
    ):
        with path.open(encoding="utf-8") as handle:
            for line in handle:
                if line.strip():
                    rows.append(v3.V3Trade(**json.loads(line)))
    return tuple(sorted(rows, key=lambda item: (_aware(item.entry_at), item.symbol)))


def _metrics_dict(trades: tuple[v3.V3Trade, ...]) -> dict[str, Any] | None:
    value = v3._metrics(trades)
    return None if value is None else asdict(value)


def build_matrix(root: Path) -> dict[str, Any]:
    reports = _load_reports(root)
    raw = _load_trades(root)
    max3 = v3._portfolio_max3(raw)
    metrics = v3._metrics(max3)
    if metrics is None or metrics.profit_factor is None or metrics.mean_r is None:
        raise ValueError("LATE60 matrix requires complete metrics")

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
            "late60_trades": sum(
                item.entry_mode.startswith("LATE60_") for item in selected
            ),
            "metrics": _metrics_dict(selected),
        }

    late_selected = sum(
        item.entry_mode.startswith("LATE60_") for item in max3
    )
    baseline_surviving = len(max3) - late_selected
    pf = Decimal(metrics.profit_factor)
    total = Decimal(metrics.total_r)
    mean = Decimal(metrics.mean_r)
    dd = Decimal(metrics.max_drawdown_r)

    return {
        "identity": MATRIX_IDENTITY,
        "market_count": 9,
        "baseline_wait5_raw_control": sum(
            int(item["baseline_wait5_raw"]) for item in reports
        ),
        "baseline_wait5_raw_control_reproduced": (
            sum(int(item["baseline_wait5_raw"]) for item in reports)
            == EXPECTED_WAIT5_RAW
        ),
        "clean_late_rows": sum(int(item["clean_late_rows"]) for item in reports),
        "clean_late_control_reproduced": (
            sum(int(item["clean_late_rows"]) for item in reports)
            == EXPECTED_CLEAN_LATE
        ),
        "raw_trades": len(raw),
        "max3_selected_trades": len(max3),
        "late60_selected_trades": late_selected,
        "wait5_baseline_trades_surviving": baseline_surviving,
        "max3_metrics": asdict(metrics),
        "per_session": per_session,
        "per_market": per_market,
        "wait5_baseline": {
            "trades": EXPECTED_WAIT5_MAX3,
            "profit_factor": str(WAIT5_PF),
            "total_r": str(WAIT5_TOTAL_R),
            "mean_r": str(WAIT5_MEAN_R),
            "max_drawdown_r": str(WAIT5_DD_R),
            "losing_streak": WAIT5_LS,
        },
        "delta_vs_wait5": {
            "trades": len(max3) - EXPECTED_WAIT5_MAX3,
            "profit_factor": str(pf - WAIT5_PF),
            "total_r": str(total - WAIT5_TOTAL_R),
            "mean_r": str(mean - WAIT5_MEAN_R),
            "max_drawdown_r": str(dd - WAIT5_DD_R),
            "losing_streak": metrics.max_losing_streak - WAIT5_LS,
        },
        "variant_only_change": "WAIT5_NORMAL_FILL_MISSING_LATE60_CARRY",
        "same_source_first_mss_preserved": True,
        "same_fvg_zone_preserved": True,
        "same_fill_level_preserved": True,
        "same_stop_preserved": True,
        "same_target_rule_preserved": True,
        "entry_window_extended_minutes": EXTENSION_MINUTES,
        "late_lifecycle_extended_to_same_boundary": True,
        "new_mss_allowed": False,
        "new_fvg_allowed": False,
        "outcome_used_for_admission": False,
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
        / "capitalizer-nine-market-v3-source-first-wait5-late60-2y-v1.json"
    )
    path.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)

    market = sub.add_parser("market")
    market.add_argument("wait5_root", type=Path)
    market.add_argument("funnel_root", type=Path)
    market.add_argument("anatomy_root", type=Path)
    market.add_argument("m1_root", type=Path)
    market.add_argument("output", type=Path)

    matrix = sub.add_parser("matrix")
    matrix.add_argument("input_root", type=Path)
    matrix.add_argument("output", type=Path)

    args = parser.parse_args()
    if args.command == "market":
        report, trades = build_market_report(
            args.wait5_root,
            args.funnel_root,
            args.anatomy_root,
            args.m1_root,
        )
        write_market(report, trades, args.output)
        print(json.dumps(report, sort_keys=True))
        return

    report = build_matrix(args.input_root)
    write_matrix(report, args.output)
    print(json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    main()
