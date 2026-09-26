"""Outcome-free atlas for M1 FVG confirmation lag across SOURCE_FIRST MSS.

Hypothesis under test (structural only):
V3 may miss an FVG centered inside the exact M3 displacement because the third
M1 candle needed to confirm the three-candle FVG can close one or two minutes
after the M3 MSS confirmation.

This atlas keeps the exact frozen SOURCE_FIRST MSS, original displacement, and
original causal opposing M1 OB. It does not search for a later unrelated impulse.

For each frozen FVG_MISSING row it asks whether a same-side FVG exists with:
- center candle inside the original M3 displacement window;
- third candle closing after MSS confirmation;
- third candle closing no later than MSS + 2 minutes;
- third candle closing before the original H1 deadline.

No trade outcome, fill outcome, realized R, stop/target result, or PnL is read.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from qore.infrastructure.trader_lab import (
    capitalizer_owner_h1_m3_m1_causal_reversal_1y_v3 as v3,
)
from qore.infrastructure.trader_lab import (
    capitalizer_v3_source_first_wait5_funnel_atlas_2y_v1 as funnel,
)
from qore.infrastructure.trader_lab.capitalizer_cibo_m1_reader_v1 import (
    CapitalizerM1Bar,
    iter_cibo_m1,
)
from qore.infrastructure.trader_lab.capitalizer_contract import CapitalizerSession
from qore.infrastructure.trader_lab.capitalizer_exposure_graph import CapitalizerSide
from qore.infrastructure.trader_lab.capitalizer_strict_htf_gate_1y_v1 import (
    TFBar,
    _aggregate_tf,
    _index_day_inputs,
    _pivots,
)
from qore.infrastructure.trader_lab.capitalizer_v3_source_first_cisd_v1 import (
    find_source_first_m3_mss,
)

IDENTITY = "QORE_CAPITALIZER_V3_SOURCE_FIRST_FVG_CONFIRMATION_LAG_ATLAS_2Y_V1"
MATRIX_IDENTITY = (
    "QORE_CAPITALIZER_NINE_MARKET_V3_SOURCE_FIRST_"
    "FVG_CONFIRMATION_LAG_ATLAS_2Y_V1"
)
EXPECTED_FVG_MISSING = 322
MAX_CONFIRMATION_LAG_MINUTES = 2


@dataclass(frozen=True, slots=True)
class FvgConfirmationLagRow:
    symbol: str
    session: str
    operating_date: str
    side: str
    source_first_mss_at: str
    h1_deadline: str
    displacement_opened_at: str
    displacement_closed_at: str
    causal_ob_present: bool
    lag_completion_present: bool
    lag_fvg_confirmed_at: str | None
    lag_minutes: int | None
    lag_fvg_low: str | None
    lag_fvg_high: str | None
    lag_ob_overlap: bool | None
    opposed_fvg_before_lag_completion: bool | None
    outcome_fields_read: bool = False


def _load_fvg_missing(root: Path) -> tuple[dict[str, Any], ...]:
    paths = sorted(
        root.rglob(
            "capitalizer-*-v3-source-first-wait5-funnel-atlas-2y-v1-rows.jsonl"
        )
    )
    if len(paths) != 1:
        raise ValueError("confirmation-lag atlas requires one frozen funnel ledger")
    rows: list[dict[str, Any]] = []
    with paths[0].open(encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            raw = json.loads(line)
            if not isinstance(raw, dict):
                raise ValueError("funnel row must be object")
            if raw.get("terminal_reason") == funnel.FVG_MISSING:
                rows.append(raw)
    return tuple(rows)


def _same_side_fvg(
    first: CapitalizerM1Bar,
    third: CapitalizerM1Bar,
    side: CapitalizerSide,
) -> tuple[bool, Any, Any]:
    if side is CapitalizerSide.LONG:
        return first.high < third.low, first.high, third.low
    return first.low > third.high, third.high, first.low


def _opposed_fvg(
    first: CapitalizerM1Bar,
    third: CapitalizerM1Bar,
    side: CapitalizerSide,
) -> bool:
    return bool(
        first.low > third.high
        if side is CapitalizerSide.LONG
        else first.high < third.low
    )


def _build_row(
    *,
    raw: dict[str, Any],
    execution: tuple[CapitalizerM1Bar, ...],
    m3: tuple[TFBar, ...],
    m3_closes: tuple[datetime, ...],
    m3_pivots: Any,
) -> FvgConfirmationLagRow:
    side = CapitalizerSide(str(raw["side"]))
    sweep_at = datetime.fromisoformat(str(raw["sweep_at"]))
    closeback_at = datetime.fromisoformat(str(raw["closeback_at"]))
    deadline = datetime.fromisoformat(str(raw["h1_deadline"]))
    frozen_mss = datetime.fromisoformat(str(raw["source_first_mss_at"]))

    event = find_source_first_m3_mss(
        m3,
        m3_closes,
        m3_pivots,
        sweep_at=sweep_at,
        after=closeback_at,
        before=deadline,
        side=side,
    )
    if event is None or event.confirmed_at != frozen_mss:
        raise ValueError("confirmation-lag SOURCE_FIRST MSS reconstruction mismatch")
    if v3._m1_causal_zone(execution, event=event) is not None:
        raise ValueError("confirmation-lag row unexpectedly has baseline V3 zone")

    displacement_indices = [
        index
        for index, bar in enumerate(execution)
        if event.displacement_opened_at
        <= bar.opened_at
        < event.displacement_closed_at
    ]
    if not displacement_indices:
        raise ValueError("confirmation-lag row lost M1 displacement bars")

    first_index = displacement_indices[0]
    ob_index: int | None = None
    for index in range(first_index - 1, -1, -1):
        bar = execution[index]
        opposing = (
            bar.close < bar.open
            if side is CapitalizerSide.LONG
            else bar.close > bar.open
        )
        if opposing:
            ob_index = index
            break
    if ob_index is None:
        return FvgConfirmationLagRow(
            symbol=str(raw["symbol"]),
            session=str(raw["session"]),
            operating_date=str(raw["operating_date"]),
            side=side.value,
            source_first_mss_at=event.confirmed_at.isoformat(),
            h1_deadline=deadline.isoformat(),
            displacement_opened_at=event.displacement_opened_at.isoformat(),
            displacement_closed_at=event.displacement_closed_at.isoformat(),
            causal_ob_present=False,
            lag_completion_present=False,
            lag_fvg_confirmed_at=None,
            lag_minutes=None,
            lag_fvg_low=None,
            lag_fvg_high=None,
            lag_ob_overlap=None,
            opposed_fvg_before_lag_completion=None,
        )

    ob = execution[ob_index]
    latest_allowed = min(
        event.confirmed_at + timedelta(minutes=MAX_CONFIRMATION_LAG_MINUTES),
        deadline,
    )

    candidate: tuple[datetime, Any, Any] | None = None
    for center in displacement_indices:
        if center <= 0 or center + 1 >= len(execution):
            continue
        first = execution[center - 1]
        third = execution[center + 1]
        if third.closed_at <= event.confirmed_at:
            continue
        if third.closed_at > latest_allowed:
            continue
        valid, low, high = _same_side_fvg(first, third, side)
        if valid and (
            candidate is None or third.closed_at < candidate[0]
        ):
            candidate = (third.closed_at, low, high)

    if candidate is None:
        return FvgConfirmationLagRow(
            symbol=str(raw["symbol"]),
            session=str(raw["session"]),
            operating_date=str(raw["operating_date"]),
            side=side.value,
            source_first_mss_at=event.confirmed_at.isoformat(),
            h1_deadline=deadline.isoformat(),
            displacement_opened_at=event.displacement_opened_at.isoformat(),
            displacement_closed_at=event.displacement_closed_at.isoformat(),
            causal_ob_present=True,
            lag_completion_present=False,
            lag_fvg_confirmed_at=None,
            lag_minutes=None,
            lag_fvg_low=None,
            lag_fvg_high=None,
            lag_ob_overlap=None,
            opposed_fvg_before_lag_completion=None,
        )

    formed_at, fvg_low, fvg_high = candidate
    overlap_low = max(ob.low, fvg_low)
    overlap_high = min(ob.high, fvg_high)
    overlap = overlap_low <= overlap_high

    opposed_before = False
    for center in range(1, len(execution) - 1):
        first = execution[center - 1]
        third = execution[center + 1]
        if third.closed_at <= event.confirmed_at:
            continue
        if third.closed_at > formed_at:
            break
        if _opposed_fvg(first, third, side):
            opposed_before = True
            break

    lag_minutes = int(
        (formed_at - event.confirmed_at).total_seconds() // 60
    )
    return FvgConfirmationLagRow(
        symbol=str(raw["symbol"]),
        session=str(raw["session"]),
        operating_date=str(raw["operating_date"]),
        side=side.value,
        source_first_mss_at=event.confirmed_at.isoformat(),
        h1_deadline=deadline.isoformat(),
        displacement_opened_at=event.displacement_opened_at.isoformat(),
        displacement_closed_at=event.displacement_closed_at.isoformat(),
        causal_ob_present=True,
        lag_completion_present=True,
        lag_fvg_confirmed_at=formed_at.isoformat(),
        lag_minutes=lag_minutes,
        lag_fvg_low=str(fvg_low),
        lag_fvg_high=str(fvg_high),
        lag_ob_overlap=overlap,
        opposed_fvg_before_lag_completion=opposed_before,
    )


def build_market_report(
    funnel_root: Path,
    m1_root: Path,
) -> tuple[dict[str, Any], tuple[FvgConfirmationLagRow, ...]]:
    frozen = _load_fvg_missing(funnel_root)
    if not frozen:
        raise ValueError("confirmation-lag atlas found no frozen rows")

    first_sweep = min(datetime.fromisoformat(str(row["sweep_at"])) for row in frozen)
    last_deadline = max(datetime.fromisoformat(str(row["h1_deadline"])) for row in frozen)
    all_bars = tuple(
        bar
        for bar in iter_cibo_m1(m1_root)
        if first_sweep - timedelta(days=2)
        <= bar.opened_at
        <= last_deadline + timedelta(minutes=5)
    )
    if not all_bars:
        raise ValueError("confirmation-lag atlas found no native M1")

    symbol = all_bars[0].symbol
    if any(bar.symbol != symbol for bar in all_bars):
        raise ValueError("confirmation-lag atlas requires one symbol")
    if any(str(row["symbol"]) != symbol for row in frozen):
        raise ValueError("confirmation-lag funnel/M1 symbol mismatch")

    session = CapitalizerSession(str(frozen[0]["session"]))
    m3 = _aggregate_tf(all_bars, minutes=3)
    m3_closes = tuple(item.closed_at for item in m3)
    m3_pivots = _pivots(m3)
    execution_by_day, _ = _index_day_inputs(all_bars, session=session)

    rows: list[FvgConfirmationLagRow] = []
    for raw in frozen:
        execution = execution_by_day.get(str(raw["operating_date"]), ())
        if not execution:
            raise ValueError("missing execution bars for confirmation-lag row")
        rows.append(
            _build_row(
                raw=raw,
                execution=execution,
                m3=m3,
                m3_closes=m3_closes,
                m3_pivots=m3_pivots,
            )
        )

    ordered = tuple(
        sorted(rows, key=lambda item: (item.source_first_mss_at, item.symbol))
    )
    lag = Counter(
        str(item.lag_minutes)
        for item in ordered
        if item.lag_minutes is not None
    )
    return {
        "identity": IDENTITY,
        "symbol": symbol,
        "session": session.value,
        "fvg_missing_rows": len(ordered),
        "causal_ob_present": sum(item.causal_ob_present for item in ordered),
        "lag_completion_present": sum(
            item.lag_completion_present for item in ordered
        ),
        "lag_completion_without_prior_opposed_fvg": sum(
            item.lag_completion_present
            and item.opposed_fvg_before_lag_completion is False
            for item in ordered
        ),
        "lag_ob_overlap": sum(item.lag_ob_overlap is True for item in ordered),
        "lag_minutes": dict(sorted(lag.items())),
        "max_confirmation_lag_minutes": MAX_CONFIRMATION_LAG_MINUTES,
        "same_original_m3_displacement_required": True,
        "same_original_causal_ob_required": True,
        "outcome_fields_read": False,
        "outcome_used_for_classification": False,
        "strategy_mutated": False,
        "diagnostic_only": True,
        "economic_candidate": False,
        "rule_promotion_allowed": False,
    }, ordered


def write_market(
    report: dict[str, Any],
    rows: tuple[FvgConfirmationLagRow, ...],
    output: Path,
) -> None:
    output.mkdir(parents=True, exist_ok=True)
    symbol = str(report["symbol"]).lower()
    stem = (
        f"capitalizer-{symbol}-v3-source-first-"
        "fvg-confirmation-lag-atlas-2y-v1"
    )
    (output / f"{stem}.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    with (output / f"{stem}-rows.jsonl").open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(asdict(row), sort_keys=True) + "\n")


def _load_reports(root: Path) -> list[dict[str, Any]]:
    paths = sorted(
        root.rglob(
            "capitalizer-*-v3-source-first-fvg-confirmation-lag-atlas-2y-v1.json"
        )
    )
    if len(paths) != 9:
        raise ValueError(
            f"confirmation-lag matrix requires 9 reports, got {len(paths)}"
        )
    return [dict(json.loads(path.read_text(encoding="utf-8"))) for path in paths]


def build_matrix(root: Path) -> dict[str, Any]:
    reports = _load_reports(root)
    total = sum(int(report["fvg_missing_rows"]) for report in reports)
    lag: Counter[str] = Counter()
    for report in reports:
        for key, value in dict(report["lag_minutes"]).items():
            lag[str(key)] += int(value)

    return {
        "identity": MATRIX_IDENTITY,
        "market_count": 9,
        "fvg_missing_rows": total,
        "fvg_missing_control_reproduced": total == EXPECTED_FVG_MISSING,
        "causal_ob_present": sum(int(r["causal_ob_present"]) for r in reports),
        "lag_completion_present": sum(
            int(r["lag_completion_present"]) for r in reports
        ),
        "lag_completion_without_prior_opposed_fvg": sum(
            int(r["lag_completion_without_prior_opposed_fvg"]) for r in reports
        ),
        "lag_ob_overlap": sum(int(r["lag_ob_overlap"]) for r in reports),
        "lag_minutes": dict(sorted(lag.items())),
        "max_confirmation_lag_minutes": MAX_CONFIRMATION_LAG_MINUTES,
        "markets": sorted(reports, key=lambda item: str(item["symbol"])),
        "same_original_m3_displacement_required": True,
        "same_original_causal_ob_required": True,
        "outcome_fields_read": False,
        "outcome_used_for_classification": False,
        "strategy_mutated": False,
        "diagnostic_only": True,
        "economic_candidate": False,
        "rule_promotion_allowed": False,
        "fresh_holdout_claimed": False,
        "live_authorized": False,
        "real_capital_authorized": False,
    }


def write_matrix(report: dict[str, Any], output: Path) -> None:
    output.mkdir(parents=True, exist_ok=True)
    path = output / (
        "capitalizer-nine-market-v3-source-first-"
        "fvg-confirmation-lag-atlas-2y-v1.json"
    )
    path.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)

    market = sub.add_parser("market")
    market.add_argument("funnel_root", type=Path)
    market.add_argument("m1_root", type=Path)
    market.add_argument("output", type=Path)

    matrix = sub.add_parser("matrix")
    matrix.add_argument("input_root", type=Path)
    matrix.add_argument("output", type=Path)

    args = parser.parse_args()
    if args.command == "market":
        report, rows = build_market_report(args.funnel_root, args.m1_root)
        write_market(report, rows, args.output)
        print(json.dumps(report, sort_keys=True))
        return

    report = build_matrix(args.input_root)
    write_matrix(report, args.output)
    print(json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    main()
