"""R2-BL USDJPY PF root-cause and pre-stop path forensics.

Independent USDJPY analysis over its own 2014-2026 high-density population.

Questions:
- What fraction of gross loss is full structural -1R stops?
- Which timing/reference/delay cohorts carry the loss?
- Do full-stop trades fail immediately, or do they establish favorable completed
  M15 progress before reversing?

No AUDUSD state or rule is transferred.
No filter or management rule is promoted.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any

from qore.infrastructure.trader_lab.vt08_crt_pure_r2_model1_reference_lab import (
    M15Bar,
    Model1LabTrade,
    _summary,
    aggregate_complete_m15,
)
from qore.infrastructure.trader_lab.vt08_crt_pure_r2af_audusd_target_family import (
    TARGET_MULTIPLE,
    TargetArm,
    _resolve_fixed_target,
)
from qore.infrastructure.trader_lab.vt08_crt_pure_r2aq_high_density_historical_validation import (
    ValidationWindow,
    _rolling_parents,
)
from qore.infrastructure.trader_lab.vt08_crt_pure_r2c_close_unmitigated_replay import (
    build_close_unmitigated_breach_groups,
)
from qore.infrastructure.trader_lab.vt08_crt_pure_r2e_source_multiplicity_census import (
    _aligned_sources,
    _c3_m15,
)
from qore.infrastructure.trader_lab.vt08_crt_pure_r2g_competition_lab import (
    CompetitionPolicy,
    select_competing_hypothesis,
)
from qore.infrastructure.trader_lab.vt08_crt_pure_window_evidence import load_m5_window
from qore.infrastructure.traders.crt_pure_identity import CrtPureMarket

IDENTITY = "VT08_CRT_PURE_R2BL_USDJPY_PF_ROOT_CAUSE_001"
SCHEMA = "qore.vt08.crt_pure.r2bl_usdjpy_pf_root_cause.v1"
MARKET = CrtPureMarket.USDJPY
START = datetime(2014, 9, 21, 0, 0, tzinfo=UTC)
END = datetime(2026, 9, 21, 0, 0, tzinfo=UTC)
YEARS = 12
ARM = TargetArm.FIXED_1_5R
MULTIPLE = TARGET_MULTIPLE[ARM]
BASE_POLICY = CompetitionPolicy.NEWEST_SUPERSEDES_CONFIRMATION_FIRST


@dataclass(frozen=True, slots=True)
class PathRecord:
    trade: Model1LabTrade
    max_completed_close_r_before_exit: float
    completed_bars_before_exit: int


def _r_at_price(
    *,
    bullish: bool,
    entry: Decimal,
    risk: Decimal,
    price: Decimal,
) -> Decimal:
    if bullish:
        return (price - entry) / risk
    return (entry - price) / risk


def _trace(
    *,
    trade: Model1LabTrade,
    bars: tuple[M15Bar, ...],
) -> PathRecord:
    bullish = trade.parent_direction == "BULLISH"
    entry = Decimal(trade.entry_price_relative)
    stop = Decimal(trade.stop_price_relative)
    target = Decimal(trade.target_price_relative)
    risk = abs(entry - stop)
    if risk <= 0:
        raise RuntimeError("trade risk must be positive")

    closes: list[Decimal] = []
    entry_time = datetime.fromisoformat(trade.entry_opened_at)

    for bar in bars:
        if bar.opened_at < entry_time:
            continue
        if bullish:
            stop_hit = Decimal(bar.low_price) <= stop
            target_hit = Decimal(bar.high_price) >= target
        else:
            stop_hit = Decimal(bar.high_price) >= stop
            target_hit = Decimal(bar.low_price) <= target

        # Preserve source replay precedence. The close of an exit bar is never
        # available before the exit.
        if stop_hit or target_hit:
            break

        closes.append(
            _r_at_price(
                bullish=bullish,
                entry=entry,
                risk=risk,
                price=Decimal(bar.close_price),
            )
        )

    return PathRecord(
        trade=trade,
        max_completed_close_r_before_exit=round(
            float(max(closes, default=Decimal("0"))),
            8,
        ),
        completed_bars_before_exit=len(closes),
    )


def _metrics(rows: tuple[Model1LabTrade, ...]) -> dict[str, Any]:
    values = [float(row.r_multiple) for row in rows]
    gross_profit = sum(value for value in values if value > 0)
    gross_loss = -sum(value for value in values if value < 0)
    return {
        **_summary(rows),
        "gross_profit_r": round(gross_profit, 8),
        "gross_loss_r": round(gross_loss, 8),
        "mean_r": (
            0.0 if not values else round(sum(values) / len(values), 8)
        ),
    }


def _delay_bucket(trade: Model1LabTrade) -> str:
    source = datetime.fromisoformat(trade.source_opened_at)
    confirmation = datetime.fromisoformat(trade.confirmation_opened_at)
    bars = round((confirmation - source).total_seconds() / (15 * 60))
    if bars == 1:
        return "D1"
    if bars == 2:
        return "D2"
    return "D3_PLUS"


def _reference_bucket(trade: Model1LabTrade) -> str:
    return "REF1" if trade.reference_count == 1 else "REF2_PLUS"


def _group(
    trades: tuple[Model1LabTrade, ...],
    key_name: str,
) -> dict[str, dict[str, Any]]:
    groups: dict[str, list[Model1LabTrade]] = defaultdict(list)
    for trade in trades:
        if key_name == "timing":
            key = trade.timing_triplet
        elif key_name == "reference":
            key = _reference_bucket(trade)
        elif key_name == "delay":
            key = _delay_bucket(trade)
        elif key_name == "direction":
            key = trade.parent_direction
        else:
            raise ValueError(key_name)
        groups[key].append(trade)
    return {
        key: _metrics(tuple(rows))
        for key, rows in sorted(groups.items())
    }


def _path_class(record: PathRecord) -> str:
    trade = record.trade
    if trade.exit_reason != "STOP" or abs(float(trade.r_multiple) + 1.0) > 1e-9:
        return "NOT_FULL_STOP"
    value = record.max_completed_close_r_before_exit
    if value <= 0:
        return "FULL_STOP_NEVER_POSITIVE_CLOSE"
    if value < 0.25:
        return "FULL_STOP_POSITIVE_LT_025"
    if value < 0.50:
        return "FULL_STOP_REACHED_025_LT_050"
    if value < 0.75:
        return "FULL_STOP_REACHED_050_LT_075"
    if value < 1.00:
        return "FULL_STOP_REACHED_075_LT_100"
    return "FULL_STOP_REACHED_GE_100"


def run_forensics() -> tuple[
    tuple[PathRecord, ...],
    dict[str, Any],
]:
    window = ValidationWindow(market=MARKET, start=START, end=END)
    bars = load_m5_window(
        MARKET,
        start=START - timedelta(days=2),
        end_exclusive=END + timedelta(days=1),
    )
    parents = _rolling_parents(
        market=MARKET,
        bars=bars,
        window=window,
    )
    m15 = aggregate_complete_m15(bars)
    m15_by_time = {bar.opened_at: bar for bar in m15}
    breaches = build_close_unmitigated_breach_groups(m15)

    records: list[PathRecord] = []
    diagnostics: Counter[str] = Counter()
    diagnostics["parent_count"] = len(parents)

    for parent in parents:
        c3_m15 = _c3_m15(parent, m15_by_time)
        observations = _aligned_sources(
            parent=parent,
            c3_m15=c3_m15,
            breaches=breaches,
        )
        selected = select_competing_hypothesis(
            policy=BASE_POLICY,
            parent=parent,
            observations=observations,
            c3_m15=c3_m15,
        )
        if selected is None:
            diagnostics["no_selected_hypothesis"] += 1
            continue

        observation, confirmation, entry_bar = selected
        trade = _resolve_fixed_target(
            arm=ARM,
            multiple=MULTIPLE,
            parent=parent,
            group=observation.group,
            confirmation=confirmation,
            entry_bar=entry_bar,
            c3_m15=c3_m15,
        )
        if trade is None:
            diagnostics["invalid_structural_geometry"] += 1
            continue

        records.append(_trace(trade=trade, bars=c3_m15))
        diagnostics["trade_created"] += 1

    frozen = tuple(
        sorted(records, key=lambda record: record.trade.entry_opened_at)
    )
    trades = tuple(record.trade for record in frozen)
    full_stops = tuple(
        record
        for record in frozen
        if record.trade.exit_reason == "STOP"
        and abs(float(record.trade.r_multiple) + 1.0) <= 1e-9
    )
    path_counts: Counter[str] = Counter(
        _path_class(record) for record in frozen
    )
    overall = _metrics(trades)
    original_stop_loss = -sum(
        float(record.trade.r_multiple) for record in full_stops
    )
    target_gain = sum(
        float(trade.r_multiple)
        for trade in trades
        if trade.exit_reason == f"TARGET_{ARM.value}"
    )
    c3_net = sum(
        float(trade.r_multiple)
        for trade in trades
        if trade.exit_reason == "C3_CLOSE"
    )

    report: dict[str, Any] = {
        "schema": SCHEMA,
        "identity": IDENTITY,
        "market": MARKET.value,
        "window_start": START.isoformat(),
        "window_end_exclusive": END.isoformat(),
        "years": YEARS,
        "population": {
            "timing": "ROLLING_H4",
            "target": ARM.value,
            "competition": BASE_POLICY.value,
            "protection": "OFF",
            "expiry": "C3_CLOSE",
        },
        "diagnostics": dict(diagnostics),
        "overall": overall,
        "trades_per_year": round(len(trades) / YEARS, 8),
        "pf_loss_mechanism": {
            "full_stop_count": len(full_stops),
            "original_stop_loss_r": round(original_stop_loss, 8),
            "full_stop_share_of_gross_loss": (
                None
                if float(overall["gross_loss_r"]) <= 0
                else round(
                    original_stop_loss / float(overall["gross_loss_r"]),
                    8,
                )
            ),
            "fixed_1_5r_target_gain_r": round(target_gain, 8),
            "c3_close_net_r": round(c3_net, 8),
        },
        "cohorts": {
            "timing": _group(trades, "timing"),
            "reference": _group(trades, "reference"),
            "delay": _group(trades, "delay"),
            "direction": _group(trades, "direction"),
        },
        "full_stop_path": {
            "count": len(full_stops),
            "classes": {
                key: value
                for key, value in sorted(path_counts.items())
                if key != "NOT_FULL_STOP"
            },
            "median_max_completed_close_r": (
                None
                if not full_stops
                else sorted(
                    record.max_completed_close_r_before_exit
                    for record in full_stops
                )[len(full_stops) // 2]
            ),
        },
        "audusd_rule_transfer": False,
        "filter_promoted": False,
        "management_promoted": False,
        "research_only": True,
        "candidate_certified": False,
        "demo_eligible": False,
        "live_authorized": False,
        "real_capital_authorized": False,
        "production_authorized": False,
    }
    return frozen, report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("output", type=Path)
    args = parser.parse_args()

    records, report = run_forensics()
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / "report.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n"
    )
    with (args.output / "paths.jsonl").open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(
                json.dumps(asdict(record), sort_keys=True, default=str) + "\n"
            )
    print("CRT_R2BL_USDJPY_ROOT_CAUSE_JSON=" + json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    main()
