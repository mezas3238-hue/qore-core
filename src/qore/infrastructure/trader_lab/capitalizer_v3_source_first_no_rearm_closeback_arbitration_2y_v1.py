"""Consumed-window A/B: No-Rearm plus causal closeback arbitration.

Frozen policy before reading this candidate's economics:
- enumerate all causal liquidity closebacks inside each H1;
- preserve fail-closed handling for opposite-side candidates tied at the
  earliest closeback timestamp;
- strictly later independent closebacks remain eligible;
- apply the exact SOURCE_FIRST + No-Rearm structural contract to every eligible
  hypothesis;
- the first hypothesis to become executable by entry timestamp wins the H1;
- one execution maximum per H1 and portfolio MAX3/session remain unchanged.

No lifecycle outcome, PnL, stop/target result, market/session profitability, or
future failure state participates in arbitration.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import asdict, dataclass
from datetime import date, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any

from qore.infrastructure.trader_lab import (
    capitalizer_owner_h1_m3_m1_causal_reversal_1y_v3 as v3,
)
from qore.infrastructure.trader_lab import (
    capitalizer_v3_source_first_closeback_causal_arbitration_atlas_2y_v1 as arb,
)
from qore.infrastructure.trader_lab import (
    capitalizer_v3_source_first_closeback_competition_atlas_2y_v1 as comp,
)
from qore.infrastructure.trader_lab import (
    capitalizer_v3_source_first_wait5_2y_v1 as wait5,
)
from qore.infrastructure.trader_lab.capitalizer_cibo_m1_reader_v1 import CapitalizerM1Bar
from qore.infrastructure.trader_lab.capitalizer_contract import (
    MAX_EXECUTIONS_PER_SESSION,
    CapitalizerSession,
)
from qore.infrastructure.trader_lab.capitalizer_strict_htf_gate_1y_v1 import (
    Pivot,
    TFBar,
)
from qore.infrastructure.trader_lab.capitalizer_v3_source_first_cisd_v1 import (
    find_source_first_m3_mss,
)

IDENTITY = "QORE_CAPITALIZER_V3_SOURCE_FIRST_NO_REARM_CLOSEBACK_ARBITRATION_2Y_V1"
MATRIX_IDENTITY = (
    "QORE_CAPITALIZER_NINE_MARKET_V3_SOURCE_FIRST_"
    "NO_REARM_CLOSEBACK_ARBITRATION_2Y_V1"
)
POLICY = "EARLIEST_CAUSAL_EXECUTABLE_CLOSEBACK_WINS"

BASELINE_RAW = 804
BASELINE_MAX3 = 793
BASELINE_PF = Decimal("1.591302271555862985264867662")
BASELINE_TOTAL_R = Decimal("160.4161625060456517859037840")
BASELINE_MEAN_R = Decimal("0.2022902427566779972079492863")
BASELINE_DD_R = Decimal("11.34554432703924017558271105")
BASELINE_LS = 8


@dataclass(frozen=True, slots=True)
class _ExecutableCandidate:
    closeback: v3.SweepCloseback
    mss: v3.M3MssEvent
    zone: v3.M1EntryZone
    entry_index: int
    entry_price: Decimal
    entry_mode: str
    stop_price: Decimal


def _candidate(
    closeback: v3.SweepCloseback,
    *,
    execution: tuple[CapitalizerM1Bar, ...],
    m3: tuple[TFBar, ...],
    m3_closes: tuple[datetime, ...],
    m3_pivots: tuple[Pivot, ...],
    buffer_price: Decimal,
) -> _ExecutableCandidate | None:
    mss = find_source_first_m3_mss(
        m3,
        m3_closes,
        m3_pivots,
        sweep_at=closeback.sweep_at,
        after=closeback.closeback_at,
        before=closeback.h1_deadline,
        side=closeback.side,
    )
    if mss is None:
        return None

    zone = v3._m1_causal_zone(execution, event=mss)
    if zone is None:
        return None

    fill = v3._find_m1_fill(
        execution,
        event=mss,
        zone=zone,
        deadline=closeback.h1_deadline,
    )
    if fill is None:
        return None
    entry_index, entry_price, entry_mode = fill
    entry_at = execution[entry_index].opened_at

    has_overlap = zone.overlap_low is not None and zone.overlap_high is not None
    if not has_overlap and entry_at < mss.confirmed_at + timedelta(minutes=5):
        return None

    stop_price = (
        mss.broken_swing_price - buffer_price
        if closeback.side.value == "LONG"
        else mss.broken_swing_price + buffer_price
    )
    valid_stop = (
        stop_price < entry_price
        if closeback.side.value == "LONG"
        else stop_price > entry_price
    )
    if not valid_stop:
        return None

    return _ExecutableCandidate(
        closeback=closeback,
        mss=mss,
        zone=zone,
        entry_index=entry_index,
        entry_price=entry_price,
        entry_mode=entry_mode,
        stop_price=stop_price,
    )


def _same_closeback(
    left: v3.SweepCloseback,
    right: v3.SweepCloseback,
) -> bool:
    return bool(
        left.closeback_at == right.closeback_at
        and left.side is right.side
        and left.reference.source == right.reference.source
        and left.reference.price == right.reference.price
    )


def _arbitration_scan_day(
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

        sweep_seen, candidates = comp._enumerate_closebacks(
            hour_bars,
            levels=levels,
            m5=m5,
            m5_closes=m5_closes,
            h1_open=h1_open,
            h1_deadline=h1_deadline,
        )
        if sweep_seen:
            stages["H1_SWEEP_DETECTED"] += 1
        if not candidates:
            if sweep_seen:
                stages["M5_CLOSEBACK_MISSING"] += 1
            continue

        stages["M5_CLOSEBACK_CONFIRMED"] += 1
        eligible, ambiguous = arb._eligible_after_ambiguity(candidates)
        if ambiguous:
            stages["ARBITRATION_EARLIEST_AMBIGUOUS"] += 1
        if len(candidates) > 1:
            stages["ARBITRATION_MULTIPLE_CLOSEBACKS"] += 1

        current_first, _ = comp._current_first(candidates)
        current_exec = (
            None
            if current_first is None
            else _candidate(
                current_first,
                execution=execution,
                m3=m3,
                m3_closes=m3_closes,
                m3_pivots=m3_pivots,
                buffer_price=buffer_price,
            )
        )

        executable: list[_ExecutableCandidate] = []
        for closeback in eligible:
            item = _candidate(
                closeback,
                execution=execution,
                m3=m3,
                m3_closes=m3_closes,
                m3_pivots=m3_pivots,
                buffer_price=buffer_price,
            )
            if item is not None:
                executable.append(item)

        if not executable:
            stages["ARBITRATION_NO_EXECUTABLE"] += 1
            continue

        winner = min(
            executable,
            key=lambda item: (
                execution[item.entry_index].opened_at,
                item.closeback.closeback_at,
                item.closeback.sweep_at,
                item.closeback.reference.source,
                item.closeback.reference.price,
            ),
        )
        if current_exec is None:
            stages["ARBITRATION_RECOVERED_ALTERNATIVE"] += 1
        elif _same_closeback(winner.closeback, current_exec.closeback):
            stages["ARBITRATION_CURRENT_FIRST_WINS"] += 1
        else:
            stages["ARBITRATION_ALTERNATIVE_PREEMPTS"] += 1

        closeback = winner.closeback
        mss = winner.mss
        zone = winner.zone
        entry_index = winner.entry_index
        entry_price = winner.entry_price
        stop_price = winner.stop_price

        risk = abs(entry_price - stop_price)
        target_price = (
            entry_price + Decimal("2") * risk
            if closeback.side.value == "LONG"
            else entry_price - Decimal("2") * risk
        )
        realized, reason, held, ambiguous_lifecycle, exit_at = v3._lifecycle(
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
                m1_ob_fvg_overlap=(
                    zone.overlap_low is not None and zone.overlap_high is not None
                ),
                entry_mode=winner.entry_mode,
                entry_at=execution[entry_index].opened_at.isoformat(),
                exit_at=exit_at.isoformat(),
                entry_price=str(entry_price),
                stop_price=str(stop_price),
                stop_buffer_price=str(buffer_price),
                target_price=str(target_price),
                realized_gross_r=str(realized),
                exit_reason=reason,
                m1_bars_held=held,
                same_minute_stop_target_ambiguity=ambiguous_lifecycle,
            )
        )

    return tuple(results)


@contextmanager
def _scan_patch() -> Iterator[None]:
    mutable_wait5: Any = wait5
    original = mutable_wait5._wait5_scan_day
    try:
        mutable_wait5._wait5_scan_day = _arbitration_scan_day
        yield
    finally:
        mutable_wait5._wait5_scan_day = original


def build_market_report(
    m1_root: Path,
    *,
    session: CapitalizerSession,
) -> tuple[dict[str, Any], tuple[v3.V3Trade, ...]]:
    with _scan_patch():
        report, trades = wait5.build_market_report(
            m1_root,
            session=session,
        )

    stage_counts = dict(report["stage_counts"])
    report.update(
        {
            "identity": IDENTITY,
            "policy": POLICY,
            "variant_only_change": "CAUSAL_CLOSEBACK_ARBITRATION",
            "arbitration_multiple_closebacks": stage_counts.get(
                "ARBITRATION_MULTIPLE_CLOSEBACKS", 0
            ),
            "arbitration_recovered_alternative": stage_counts.get(
                "ARBITRATION_RECOVERED_ALTERNATIVE", 0
            ),
            "arbitration_alternative_preempts": stage_counts.get(
                "ARBITRATION_ALTERNATIVE_PREEMPTS", 0
            ),
            "arbitration_current_first_wins": stage_counts.get(
                "ARBITRATION_CURRENT_FIRST_WINS", 0
            ),
            "earliest_executable_wins": True,
            "ambiguous_earliest_tie_fail_closed": True,
            "strictly_later_closebacks_remain_eligible_after_ambiguity": True,
            "same_liquidity_universe": True,
            "same_no_rearm_architecture": True,
            "same_source_first_mss": True,
            "same_fvg": True,
            "same_stop": True,
            "same_target": True,
            "same_h1_deadline": True,
            "same_max3": True,
            "outcome_used_for_admission": False,
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
    stem = (
        f"capitalizer-{symbol}-v3-source-first-"
        "no-rearm-closeback-arbitration-2y-v1"
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
            "capitalizer-*-v3-source-first-"
            "no-rearm-closeback-arbitration-2y-v1.json"
        )
    )
    if len(paths) != 9:
        raise ValueError(f"arbitration matrix requires 9 reports, got {len(paths)}")
    return [dict(json.loads(path.read_text(encoding="utf-8"))) for path in paths]


def _load_trades(root: Path) -> tuple[v3.V3Trade, ...]:
    rows: list[v3.V3Trade] = []
    paths = sorted(
        root.rglob(
            "capitalizer-*-v3-source-first-"
            "no-rearm-closeback-arbitration-2y-v1-trades.jsonl"
        )
    )
    if len(paths) != 9:
        raise ValueError(f"arbitration requires 9 trade ledgers, got {len(paths)}")
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
        raise ValueError("arbitration candidate requires complete MAX3 metrics")

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
        "policy": POLICY,
        "market_count": 9,
        "raw_trades": len(raw),
        "max3_selected_trades": len(max3),
        "max3_metrics": asdict(metrics),
        "per_session": per_session,
        "arbitration_counts": {
            "multiple_closebacks": sum(
                int(item["arbitration_multiple_closebacks"]) for item in reports
            ),
            "recovered_alternative": sum(
                int(item["arbitration_recovered_alternative"]) for item in reports
            ),
            "alternative_preempts": sum(
                int(item["arbitration_alternative_preempts"]) for item in reports
            ),
            "current_first_wins": sum(
                int(item["arbitration_current_first_wins"]) for item in reports
            ),
        },
        "no_rearm_baseline": {
            "raw_trades": BASELINE_RAW,
            "max3_trades": BASELINE_MAX3,
            "profit_factor": str(BASELINE_PF),
            "total_r": str(BASELINE_TOTAL_R),
            "mean_r": str(BASELINE_MEAN_R),
            "max_drawdown_r": str(BASELINE_DD_R),
            "losing_streak": BASELINE_LS,
        },
        "delta_vs_no_rearm": {
            "raw_trades": len(raw) - BASELINE_RAW,
            "max3_trades": len(max3) - BASELINE_MAX3,
            "profit_factor": str(pf - BASELINE_PF),
            "total_r": str(total - BASELINE_TOTAL_R),
            "mean_r": str(mean - BASELINE_MEAN_R),
            "max_drawdown_r": str(dd - BASELINE_DD_R),
            "losing_streak": metrics.max_losing_streak - BASELINE_LS,
        },
        "earliest_executable_wins": True,
        "ambiguous_earliest_tie_fail_closed": True,
        "strictly_later_closebacks_remain_eligible_after_ambiguity": True,
        "same_liquidity_universe": True,
        "same_no_rearm_architecture": True,
        "same_source_first_mss": True,
        "same_fvg": True,
        "same_stop": True,
        "same_target": True,
        "same_h1_deadline": True,
        "same_max3": True,
        "outcome_used_for_admission": False,
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
        "no-rearm-closeback-arbitration-2y-v1.json"
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
                    "arbitration_recovered_alternative": report[
                        "arbitration_recovered_alternative"
                    ],
                    "arbitration_alternative_preempts": report[
                        "arbitration_alternative_preempts"
                    ],
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
