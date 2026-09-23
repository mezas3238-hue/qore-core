"""Consumed-window A/B: WAIT5 plus post-H1 CE50-only carry.

Predeclared change relative to frozen WAIT5:
- only frozen NORMAL_FILL_MISSING setups may remain observable after the old H1;
- the observation window is at most +60 minutes;
- post-H1 fill is the SAME frozen FVG CE50 only;
- post-H1 OB/FVG-overlap retest is never an entry;
- the SAME structural stop invalidates before CE;
- CE+STOP same M1 keeps frozen STOP-first lifecycle precedence;
- no new MSS, FVG, liquidity event, stop rule, target rule or MAX3 rule.

The baseline WAIT5 trades are loaded unchanged from frozen artifacts.
This consumed 2Y experiment cannot promote a live rule by itself.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
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
from qore.infrastructure.trader_lab.capitalizer_contract import CapitalizerSession
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
from qore.infrastructure.trader_lab.capitalizer_v3_source_first_wait5_late60_2y_v1 import (
    _load_funnel_rows,
    _load_wait5,
    _market_max3,
    _reconstruct_closeback,
)

IDENTITY = "QORE_CAPITALIZER_V3_SOURCE_FIRST_WAIT5_LATE60_CE50_2Y_V1"
MATRIX_IDENTITY = (
    "QORE_CAPITALIZER_NINE_MARKET_V3_SOURCE_FIRST_WAIT5_LATE60_CE50_2Y_V1"
)
EXTENSION_MINUTES = 60
EXPECTED_WAIT5_RAW = 1003
EXPECTED_WAIT5_MAX3 = 983
EXPECTED_CLEAN_LATE = 376

WAIT5_PF = Decimal("1.384597543145107741177480996")
WAIT5_TOTAL_R = Decimal("135.7651037644532073259312101")
WAIT5_MEAN_R = Decimal("0.1381130251927296107079666430")
WAIT5_DD_R = Decimal("11.9420088471277198029814040")
WAIT5_LS = 9


def _aware(value: str) -> datetime:
    return datetime.fromisoformat(value)


def _load_clean_late_rows(root: Path) -> tuple[dict[str, Any], ...]:
    paths = sorted(
        root.rglob(
            "capitalizer-*-v3-source-first-fill-miss-anatomy-2y-v1-rows.jsonl"
        )
    )
    if len(paths) != 1:
        raise ValueError("LATE60_CE50 requires one anatomy ledger")
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


def _find_ce50_fill(
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
    for index, bar in enumerate(execution):
        if bar.opened_at < original_deadline:
            continue
        if bar.opened_at >= extended_deadline:
            break

        ce_touch = bar.low <= ce <= bar.high
        stop_hit = _stop_hit(bar, side=event.side, stop_price=stop_price)
        if ce_touch:
            return (
                (index, ce, "LATE60_CE50"),
                "CE_STOP_SAME_BAR" if stop_hit else "CE_AVAILABLE",
            )
        if stop_hit:
            return None, "STOP_INVALIDATED_BEFORE_CE"

    return None, "NO_CE_WITHIN_60M"


def build_market_report(
    wait5_root: Path,
    funnel_root: Path,
    anatomy_root: Path,
    m1_root: Path,
) -> tuple[dict[str, Any], tuple[v3.V3Trade, ...]]:
    wait5_report, baseline = _load_wait5(wait5_root)
    symbol = str(wait5_report["symbol"])
    session = CapitalizerSession(str(wait5_report["session"]))
    frozen = _load_funnel_rows(funnel_root)
    clean_late = _load_clean_late_rows(anatomy_root)

    all_bars = tuple(iter_cibo_m1(m1_root))
    if not all_bars or all_bars[0].symbol != symbol:
        raise ValueError("LATE60_CE50 native M1 symbol mismatch")

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

    for raw in clean_late:
        operating_date = str(raw["operating_date"])
        expected_mss = str(raw["source_first_mss_at"])
        key = (operating_date, expected_mss)
        funnel = frozen.get(key)
        if funnel is None:
            raise ValueError("LATE60_CE50 missing frozen funnel row")

        execution = execution_by_day.get(operating_date, ())
        if not execution:
            raise ValueError("LATE60_CE50 missing execution bars")

        operating_day = date.fromisoformat(operating_date)
        closeback = _reconstruct_closeback(
            raw=funnel,
            operating_day=operating_day,
            execution=execution,
            all_bars=all_bars,
            h1_swings=h1_swings,
            m5=m5,
            m5_closes=m5_closes,
            prior_session=reference_by_day.get(operating_date),
        )
        original_deadline = _aware(str(funnel["h1_deadline"]))
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
        if event is None or event.confirmed_at.isoformat() != expected_mss:
            raise ValueError("LATE60_CE50 SOURCE_FIRST MSS mismatch")

        zone = v3._m1_causal_zone(execution, event=event)
        if zone is None:
            raise ValueError("LATE60_CE50 candidate lacks frozen FVG")
        if v3._find_m1_fill(
            execution,
            event=event,
            zone=zone,
            deadline=original_deadline,
        ) is not None:
            raise ValueError("LATE60_CE50 candidate unexpectedly has normal fill")

        stop_price = (
            event.broken_swing_price - buffer_price
            if event.side is CapitalizerSide.LONG
            else event.broken_swing_price + buffer_price
        )
        ce_fill, status = _find_ce50_fill(
            execution,
            event=event,
            zone=zone,
            stop_price=stop_price,
            original_deadline=original_deadline,
            extended_deadline=extended_deadline,
        )
        stages[status] += 1
        if ce_fill is None:
            continue

        entry_index, entry_price, entry_mode = ce_fill
        valid_stop = (
            stop_price < entry_price
            if event.side is CapitalizerSide.LONG
            else stop_price > entry_price
        )
        if not valid_stop:
            stages["STOP_INVALID_GEOMETRY"] += 1
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

    selected, selection = _market_max3(baseline, tuple(late_trades))
    metrics = v3._metrics(selected)
    return {
        "identity": IDENTITY,
        "symbol": symbol,
        "session": session.value,
        "baseline_wait5_raw": len(baseline),
        "clean_late_rows": len(clean_late),
        "ce50_candidates": len(late_trades),
        "market_raw_after_ce50": len(selected),
        "late_ce50_selected_after_market_max3": sum(
            trade.entry_mode == "LATE60_CE50" for trade in selected
        ),
        "selection_counts": selection,
        "ce50_status_counts": dict(sorted(stages.items())),
        "raw_metrics": None if metrics is None else asdict(metrics),
        "variant_only_change": "WAIT5_NORMAL_FILL_MISSING_LATE60_CE50_ONLY",
        "same_source_first_mss_preserved": True,
        "same_fvg_zone_preserved": True,
        "same_ce50_definition_preserved": True,
        "post_h1_overlap_entry_allowed": False,
        "same_stop_preserved": True,
        "same_target_rule_preserved": True,
        "entry_window_extended_minutes": EXTENSION_MINUTES,
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
    }, selected


def write_market(
    report: dict[str, Any],
    trades: tuple[v3.V3Trade, ...],
    output: Path,
) -> None:
    output.mkdir(parents=True, exist_ok=True)
    symbol = str(report["symbol"]).lower()
    stem = f"capitalizer-{symbol}-v3-source-first-wait5-late60-ce50-2y-v1"
    (output / f"{stem}.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    with (output / f"{stem}-trades.jsonl").open("w", encoding="utf-8") as handle:
        for trade in trades:
            handle.write(json.dumps(asdict(trade), sort_keys=True) + "\n")


def _load_reports(root: Path) -> list[dict[str, Any]]:
    paths = sorted(
        root.rglob("capitalizer-*-v3-source-first-wait5-late60-ce50-2y-v1.json")
    )
    if len(paths) != 9:
        raise ValueError(f"LATE60_CE50 matrix requires 9 reports, got {len(paths)}")
    return [dict(json.loads(path.read_text(encoding="utf-8"))) for path in paths]


def _load_trades(root: Path) -> tuple[v3.V3Trade, ...]:
    rows: list[v3.V3Trade] = []
    for path in sorted(
        root.rglob(
            "capitalizer-*-v3-source-first-wait5-late60-ce50-2y-v1-trades.jsonl"
        )
    ):
        with path.open(encoding="utf-8") as handle:
            for line in handle:
                if line.strip():
                    rows.append(v3.V3Trade(**json.loads(line)))
    return tuple(
        sorted(rows, key=lambda item: (_aware(item.entry_at), item.symbol))
    )


def _metrics_dict(trades: tuple[v3.V3Trade, ...]) -> dict[str, Any] | None:
    value = v3._metrics(trades)
    return None if value is None else asdict(value)


def build_matrix(root: Path) -> dict[str, Any]:
    reports = _load_reports(root)
    raw = _load_trades(root)
    max3 = v3._portfolio_max3(raw)
    metrics = v3._metrics(max3)
    if metrics is None or metrics.profit_factor is None or metrics.mean_r is None:
        raise ValueError("LATE60_CE50 matrix requires complete metrics")

    per_session: dict[str, dict[str, Any]] = {}
    for session in CapitalizerSession:
        selected = tuple(item for item in max3 if item.session == session.value)
        per_session[session.value] = {
            "trades": len(selected),
            "late_ce50_trades": sum(
                item.entry_mode == "LATE60_CE50" for item in selected
            ),
            "metrics": _metrics_dict(selected),
        }

    per_market: dict[str, dict[str, Any]] = {}
    for symbol in sorted(v3.EXPECTED_SYMBOLS):
        selected = tuple(item for item in max3 if item.symbol == symbol)
        per_market[symbol] = {
            "trades": len(selected),
            "late_ce50_trades": sum(
                item.entry_mode == "LATE60_CE50" for item in selected
            ),
            "metrics": _metrics_dict(selected),
        }

    late_selected = sum(item.entry_mode == "LATE60_CE50" for item in max3)
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
        "ce50_candidates": sum(int(item["ce50_candidates"]) for item in reports),
        "raw_trades": len(raw),
        "max3_selected_trades": len(max3),
        "late_ce50_selected_trades": late_selected,
        "wait5_baseline_trades_surviving": len(max3) - late_selected,
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
        "variant_only_change": "WAIT5_NORMAL_FILL_MISSING_LATE60_CE50_ONLY",
        "same_source_first_mss_preserved": True,
        "same_fvg_zone_preserved": True,
        "same_ce50_definition_preserved": True,
        "post_h1_overlap_entry_allowed": False,
        "same_stop_preserved": True,
        "same_target_rule_preserved": True,
        "entry_window_extended_minutes": EXTENSION_MINUTES,
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
        / "capitalizer-nine-market-v3-source-first-wait5-late60-ce50-2y-v1.json"
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
