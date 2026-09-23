"""Consumed-window A/B for causal M1 FVG confirmation lag.

Frozen from outcome-free evidence before reading this candidate's economics:
- keep SOURCE_FIRST MSS unchanged;
- keep WAIT5 unchanged;
- preserve the original causal opposing M1 OB;
- preserve the exact original M3 displacement;
- only when baseline V3 has no causal zone, allow the same-side three-candle
  FVG to finish confirming up to +2 minutes after MSS;
- reject if an opposed FVG confirms before or at that completion;
- never allow a fill before the lagged FVG confirmation close;
- preserve broken-swing stop, 2R target, H1 deadline and MAX3 ceilings.

This 2Y window is consumed development evidence. Promotion requires fresh holdout.
"""

from __future__ import annotations

import argparse
import json
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import asdict
from datetime import datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any

from qore.infrastructure.trader_lab import (
    capitalizer_owner_h1_m3_m1_causal_reversal_1y_v3 as v3,
)
from qore.infrastructure.trader_lab import (
    capitalizer_v3_source_first_wait5_2y_v1 as wait5,
)
from qore.infrastructure.trader_lab.capitalizer_cibo_m1_reader_v1 import (
    CapitalizerM1Bar,
)
from qore.infrastructure.trader_lab.capitalizer_contract import CapitalizerSession

IDENTITY = "QORE_CAPITALIZER_V3_SOURCE_FIRST_WAIT5_FVG_LAG2_2Y_V1"
MATRIX_IDENTITY = (
    "QORE_CAPITALIZER_NINE_MARKET_V3_SOURCE_FIRST_WAIT5_FVG_LAG2_2Y_V1"
)
ADMISSION_SOURCE = (
    "QORE_CAPITALIZER_NINE_MARKET_V3_SOURCE_FIRST_"
    "FVG_CONFIRMATION_LAG_ATLAS_2Y_V1"
)
MAX_CONFIRMATION_LAG_MINUTES = 2

WAIT5_BASELINE_RAW = 1003
WAIT5_BASELINE_MAX3 = 983
WAIT5_BASELINE_PF = Decimal("1.384597543145107741177480996")
WAIT5_BASELINE_TOTAL_R = Decimal("135.7651037644532073259312101")
WAIT5_BASELINE_MEAN_R = Decimal("0.1381130251927296107079666430")
WAIT5_BASELINE_DD_R = Decimal("11.9420088471277198029814040")
WAIT5_BASELINE_LS = 9


def _opposed_fvg(
    first: CapitalizerM1Bar,
    third: CapitalizerM1Bar,
    *,
    side: str,
) -> bool:
    return bool(
        first.low > third.high
        if side == "LONG"
        else first.high < third.low
    )


def _lag2_zone(
    execution: tuple[CapitalizerM1Bar, ...],
    *,
    event: v3.M3MssEvent,
) -> v3.M1EntryZone | None:
    baseline = _ORIGINAL_ZONE(execution, event=event)
    if baseline is not None:
        return baseline

    displacement_indices = [
        index
        for index, bar in enumerate(execution)
        if event.displacement_opened_at
        <= bar.opened_at
        < event.displacement_closed_at
    ]
    if not displacement_indices:
        return None

    first_index = displacement_indices[0]
    ob_index: int | None = None
    for index in range(first_index - 1, -1, -1):
        bar = execution[index]
        opposing = (
            bar.close < bar.open
            if event.side.value == "LONG"
            else bar.close > bar.open
        )
        if opposing:
            ob_index = index
            break
    if ob_index is None:
        return None

    latest = event.confirmed_at + timedelta(
        minutes=MAX_CONFIRMATION_LAG_MINUTES
    )
    candidates: list[tuple[datetime, Decimal, Decimal]] = []
    for center in displacement_indices:
        if center <= 0 or center + 1 >= len(execution):
            continue
        first = execution[center - 1]
        third = execution[center + 1]
        if third.closed_at <= event.confirmed_at:
            continue
        if third.closed_at > latest:
            continue
        if event.side.value == "LONG":
            valid = first.high < third.low
            low, high = first.high, third.low
        else:
            valid = first.low > third.high
            low, high = third.high, first.low
        if valid:
            candidates.append((third.closed_at, low, high))

    if not candidates:
        return None

    formed_at, fvg_low, fvg_high = min(
        candidates,
        key=lambda item: item[0],
    )

    for center in range(1, len(execution) - 1):
        first = execution[center - 1]
        third = execution[center + 1]
        if third.closed_at <= event.confirmed_at:
            continue
        if third.closed_at > formed_at:
            break
        if _opposed_fvg(first, third, side=event.side.value):
            return None

    ob = execution[ob_index]
    overlap_candidate_low = max(ob.low, fvg_low)
    overlap_candidate_high = min(ob.high, fvg_high)
    overlap_low: Decimal | None
    overlap_high: Decimal | None
    if overlap_candidate_low > overlap_candidate_high:
        overlap_low = None
        overlap_high = None
    else:
        overlap_low = overlap_candidate_low
        overlap_high = overlap_candidate_high

    return v3.M1EntryZone(
        ob_opened_at=ob.opened_at,
        ob_low=ob.low,
        ob_high=ob.high,
        fvg_confirmed_at=formed_at,
        fvg_low=fvg_low,
        fvg_high=fvg_high,
        overlap_low=overlap_low,
        overlap_high=overlap_high,
    )


def _lag2_fill(
    execution: tuple[CapitalizerM1Bar, ...],
    *,
    event: v3.M3MssEvent,
    zone: v3.M1EntryZone,
    deadline: datetime,
) -> tuple[int, Decimal, str] | None:
    if zone.fvg_confirmed_at <= event.confirmed_at:
        return _ORIGINAL_FILL(
            execution,
            event=event,
            zone=zone,
            deadline=deadline,
        )

    ce = (zone.fvg_low + zone.fvg_high) / Decimal("2")
    ob_retest: Decimal | None = None
    if zone.overlap_low is not None and zone.overlap_high is not None:
        ob_retest = (
            zone.overlap_high
            if event.side.value == "LONG"
            else zone.overlap_low
        )

    for index, bar in enumerate(execution):
        if bar.opened_at < zone.fvg_confirmed_at:
            continue
        if bar.opened_at >= deadline:
            break
        if (
            ob_retest is not None
            and bar.low <= ob_retest <= bar.high
        ):
            return index, ob_retest, "OB_FVG_RETEST"
        if bar.low <= ce <= bar.high:
            return index, ce, "FVG_CE_50"
    return None


_ORIGINAL_ZONE = v3._m1_causal_zone
_ORIGINAL_FILL = v3._find_m1_fill


@contextmanager
def _lag2_patch() -> Iterator[None]:
    original_zone = v3._m1_causal_zone
    original_fill = v3._find_m1_fill
    try:
        v3._m1_causal_zone = _lag2_zone
        v3._find_m1_fill = _lag2_fill
        yield
    finally:
        v3._m1_causal_zone = original_zone
        v3._find_m1_fill = original_fill


def _is_lag2_trade(trade: v3.V3Trade) -> bool:
    return (
        datetime.fromisoformat(trade.m1_fvg_confirmed_at)
        > datetime.fromisoformat(trade.m3_mss_at)
    )


def build_market_report(
    m1_root: Path,
    *,
    session: CapitalizerSession,
) -> tuple[dict[str, Any], tuple[v3.V3Trade, ...]]:
    with _lag2_patch():
        report, trades = wait5.build_market_report(
            m1_root,
            session=session,
        )

    lag2_trades = tuple(trade for trade in trades if _is_lag2_trade(trade))
    report.update(
        {
            "identity": IDENTITY,
            "admission_source": ADMISSION_SOURCE,
            "max_confirmation_lag_minutes": MAX_CONFIRMATION_LAG_MINUTES,
            "lag2_raw_trades": len(lag2_trades),
            "variant_only_change": (
                "SOURCE_FIRST_SAME_DISPLACEMENT_M1_FVG_CONFIRMATION_LAG2"
            ),
            "same_source_first_mss_preserved": True,
            "same_original_m3_displacement_required": True,
            "same_original_causal_ob_required": True,
            "opposed_fvg_before_completion_rejected": True,
            "fill_before_fvg_confirmation_forbidden": True,
            "same_wait5_preserved": True,
            "same_stop_preserved": True,
            "same_target_preserved": True,
            "same_h1_deadline_preserved": True,
            "outcome_used_for_admission": False,
            "component_rule_frozen_outcome_free": True,
            "composite_rule_economics_previously_unread": True,
            "diagnostic_window_role": "CONSUMED_DEVELOPMENT_ONLY",
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
    stem = f"capitalizer-{symbol}-v3-source-first-wait5-fvg-lag2-2y-v1"
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
            "capitalizer-*-v3-source-first-wait5-fvg-lag2-2y-v1.json"
        )
    )
    if len(paths) != 9:
        raise ValueError(f"FVG_LAG2 matrix requires 9 reports, got {len(paths)}")
    reports = [
        dict(json.loads(path.read_text(encoding="utf-8")))
        for path in paths
    ]
    if {str(item["symbol"]) for item in reports} != v3.EXPECTED_SYMBOLS:
        raise ValueError("FVG_LAG2 universe mismatch")
    return reports


def _load_trades(root: Path) -> tuple[v3.V3Trade, ...]:
    rows: list[v3.V3Trade] = []
    for path in sorted(
        root.rglob(
            "capitalizer-*-v3-source-first-wait5-fvg-lag2-2y-v1-trades.jsonl"
        )
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
        raise ValueError("FVG_LAG2 experiment requires complete MAX3 metrics")

    selected_lag2 = tuple(item for item in max3 if _is_lag2_trade(item))
    per_session: dict[str, dict[str, Any]] = {}
    for session in CapitalizerSession:
        selected = tuple(item for item in max3 if item.session == session.value)
        per_session[session.value] = {
            "trades": len(selected),
            "lag2_trades": sum(_is_lag2_trade(item) for item in selected),
            "metrics": _metrics_dict(selected),
        }

    per_market: dict[str, dict[str, Any]] = {}
    for symbol in sorted(v3.EXPECTED_SYMBOLS):
        selected = tuple(item for item in max3 if item.symbol == symbol)
        per_market[symbol] = {
            "trades": len(selected),
            "lag2_trades": sum(_is_lag2_trade(item) for item in selected),
            "metrics": _metrics_dict(selected),
        }

    pf = Decimal(metrics.profit_factor)
    total = Decimal(metrics.total_r)
    mean = Decimal(metrics.mean_r)
    dd = Decimal(metrics.max_drawdown_r)

    lag2_metrics = v3._metrics(selected_lag2)
    return {
        "identity": MATRIX_IDENTITY,
        "admission_source": ADMISSION_SOURCE,
        "market_count": 9,
        "window_start": reports[0]["window_start"],
        "window_end_exclusive": reports[0]["window_end_exclusive"],
        "raw_trades": len(raw),
        "raw_lag2_trades": sum(int(report["lag2_raw_trades"]) for report in reports),
        "max3_selected_trades": len(max3),
        "max3_selected_lag2_trades": len(selected_lag2),
        "max3_metrics": asdict(metrics),
        "selected_lag2_metrics": (
            None if lag2_metrics is None else asdict(lag2_metrics)
        ),
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
            "max_drawdown_r": str(dd - WAIT5_BASELINE_DD_R),
            "losing_streak": metrics.max_losing_streak - WAIT5_BASELINE_LS,
        },
        "variant_only_change": (
            "SOURCE_FIRST_SAME_DISPLACEMENT_M1_FVG_CONFIRMATION_LAG2"
        ),
        "max_confirmation_lag_minutes": MAX_CONFIRMATION_LAG_MINUTES,
        "same_source_first_mss_preserved": True,
        "same_original_m3_displacement_required": True,
        "same_original_causal_ob_required": True,
        "opposed_fvg_before_completion_rejected": True,
        "fill_before_fvg_confirmation_forbidden": True,
        "same_wait5_preserved": True,
        "same_stop_preserved": True,
        "same_target_preserved": True,
        "same_h1_deadline_preserved": True,
        "outcome_used_for_admission": False,
        "component_rule_frozen_outcome_free": True,
        "composite_rule_economics_previously_unread": True,
        "diagnostic_window_role": "CONSUMED_DEVELOPMENT_ONLY",
        "fresh_holdout_required": True,
        "fresh_holdout_claimed": False,
        "economic_candidate": True,
        "rule_promotion_allowed": False,
        "trader_certified": False,
        "live_authorized": False,
        "real_capital_authorized": False,
    }


def write_matrix(report: dict[str, Any], output: Path) -> None:
    output.mkdir(parents=True, exist_ok=True)
    path = output / (
        "capitalizer-nine-market-v3-source-first-wait5-fvg-lag2-2y-v1.json"
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
                    "lag2_raw_trades": report["lag2_raw_trades"],
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
