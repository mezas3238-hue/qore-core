"""R2-CB USDJPY cognitive WAIT first-M15 journey atlas.

Attribution only. No rule is promoted.

For every R2-BZ OOS opportunity whose initial sovereign cognitive action is WAIT,
observe one additional completed M15 bar from the planned entry open. The
observation is causal at the end of that M15.

States:
- INVALIDATED_BEFORE_REASSESS;
- DESTINATION_CONSUMED_BEFORE_REASSESS;
- otherwise first completed M15 close in normalized planned-R buckets.

Same-M15 STOP_FIRST is preserved. Final trade outcome is used only for
retrospective attribution and is never exposed to the decision state.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any

from qore.infrastructure.trader_lab import (
    vt08_crt_pure_r2bz_usdjpy_cognitive_experience_wf as r2bz,
)
from qore.infrastructure.trader_lab.vt08_crt_pure_r2bc_usdjpy_confirmation_geometry_atlas import (
    END,
    START,
)
from qore.infrastructure.trader_lab.vt08_crt_pure_r2_model1_reference_lab import (
    M15Bar,
    aggregate_complete_m15,
)
from qore.infrastructure.trader_lab.vt08_crt_pure_window_evidence import (
    load_m5_window,
)
from qore.infrastructure.traders.crt_pure_cognitive_contract import (
    CrtPureReasoningAction,
)

IDENTITY = "VT08_CRT_PURE_R2CB_USDJPY_WAIT_JOURNEY_ATLAS_001"
SCHEMA = "qore.vt08.crt_pure.r2cb_usdjpy_wait_journey_atlas.v1"


@dataclass(frozen=True, slots=True)
class WaitJourneyRecord:
    entry_opened_at: str
    state: str
    first_m15_close_r: float | None
    final_r: float
    final_exit_reason: str
    dead_on_arrival: bool


def _close_r(trade: Any, bar: M15Bar) -> float:
    bullish = trade.parent_direction == "BULLISH"
    entry = Decimal(trade.entry_price_relative)
    stop = Decimal(trade.stop_price_relative)
    risk = abs(entry - stop)
    if risk <= 0:
        raise RuntimeError("trade risk must be positive")
    close = Decimal(bar.close_price)
    value = (close - entry) / risk if bullish else (entry - close) / risk
    return round(float(value), 8)


def _bucket(value: float) -> str:
    if value < -0.50:
        return "CLOSE_LT_NEG_050R"
    if value < 0.0:
        return "CLOSE_NEG_050_TO_0R"
    if value < 0.25:
        return "CLOSE_0_TO_025R"
    if value < 0.50:
        return "CLOSE_025_TO_050R"
    return "CLOSE_GE_050R"


def _journey(record: Any, bar: M15Bar) -> WaitJourneyRecord:
    trade = record.trade
    bullish = trade.parent_direction == "BULLISH"
    stop = Decimal(trade.stop_price_relative)
    target = Decimal(trade.target_price_relative)
    if bullish:
        stop_hit = Decimal(bar.low_price) <= stop
        target_hit = Decimal(bar.high_price) >= target
    else:
        stop_hit = Decimal(bar.high_price) >= stop
        target_hit = Decimal(bar.low_price) <= target

    if stop_hit:
        state = "INVALIDATED_BEFORE_REASSESS"
        close_r = None
    elif target_hit:
        state = "DESTINATION_CONSUMED_BEFORE_REASSESS"
        close_r = None
    else:
        close_r = _close_r(trade, bar)
        state = _bucket(close_r)

    return WaitJourneyRecord(
        entry_opened_at=trade.entry_opened_at,
        state=state,
        first_m15_close_r=close_r,
        final_r=float(trade.r_multiple),
        final_exit_reason=trade.exit_reason,
        dead_on_arrival=record.dead_on_arrival,
    )


def _summary(rows: tuple[WaitJourneyRecord, ...]) -> dict[str, Any]:
    if not rows:
        return {
            "trades": 0,
            "total_r": 0.0,
            "mean_r": None,
            "profit_factor": None,
            "dead_on_arrival_rate": None,
        }
    values = [row.final_r for row in rows]
    gross_profit = sum(value for value in values if value > 0)
    gross_loss = -sum(value for value in values if value < 0)
    return {
        "trades": len(rows),
        "total_r": round(sum(values), 8),
        "mean_r": round(sum(values) / len(values), 8),
        "profit_factor": (
            None
            if gross_loss <= 0
            else round(gross_profit / gross_loss, 8)
        ),
        "dead_on_arrival_rate": round(
            sum(row.dead_on_arrival for row in rows) / len(rows),
            8,
        ),
    }


def run_atlas() -> tuple[tuple[WaitJourneyRecord, ...], dict[str, Any]]:
    records, _ = r2bz._build_records()
    m5 = load_m5_window(
        r2bz.MARKET,
        start=START - timedelta(days=2),
        end_exclusive=END + timedelta(days=1),
    )
    m15 = aggregate_complete_m15(m5)
    by_time = {bar.opened_at: bar for bar in m15}

    journey_rows: list[WaitJourneyRecord] = []
    missing_bar = 0
    folds: list[dict[str, Any]] = []

    for oos_year in range(
        START.year + r2bz.TRAINING_YEARS,
        END.year,
    ):
        training = r2bz._slice(
            records,
            r2bz._year_start(oos_year - r2bz.TRAINING_YEARS),
            r2bz._year_start(oos_year),
        )
        oos = r2bz._slice(
            records,
            r2bz._year_start(oos_year),
            r2bz._year_start(oos_year + 1),
        )
        model, _ = r2bz._fit(training)
        fold_rows: list[WaitJourneyRecord] = []
        for row in oos:
            decision = r2bz._decision(model, row)
            if decision.action is not CrtPureReasoningAction.WAIT:
                continue
            entry = datetime.fromisoformat(row.trade.entry_opened_at)
            bar = by_time.get(entry)
            if bar is None:
                missing_bar += 1
                continue
            item = _journey(row, bar)
            journey_rows.append(item)
            fold_rows.append(item)

        counts = Counter(item.state for item in fold_rows)
        folds.append(
            {
                "oos_start": r2bz._year_start(oos_year).isoformat(),
                "wait_count": len(fold_rows),
                "state_counts": dict(counts),
                "state_summaries": {
                    state: _summary(
                        tuple(item for item in fold_rows if item.state == state)
                    )
                    for state in sorted(counts)
                },
            }
        )

    rows = tuple(
        sorted(journey_rows, key=lambda item: item.entry_opened_at)
    )
    groups: defaultdict[str, list[WaitJourneyRecord]] = defaultdict(list)
    for journey_row in rows:
        groups[journey_row.state].append(journey_row)

    report: dict[str, Any] = {
        "schema": SCHEMA,
        "identity": IDENTITY,
        "market": r2bz.MARKET.value,
        "source_cognitive_identity": r2bz.IDENTITY,
        "observation_horizon": "FIRST_COMPLETED_M15_AFTER_INITIAL_WAIT",
        "same_m15_precedence": "STOP_FIRST",
        "wait_rows": len(rows),
        "missing_first_m15": missing_bar,
        "overall": _summary(rows),
        "states": {
            state: _summary(tuple(items))
            for state, items in sorted(groups.items())
        },
        "folds": folds,
        "future_outcome_used_for_decision": False,
        "attribution_only": True,
        "automatic_promotion": False,
        "research_only": True,
    }
    return rows, report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("output", type=Path)
    args = parser.parse_args()

    rows, report = run_atlas()
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / "report.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n"
    )
    with (args.output / "rows.jsonl").open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(asdict(row), sort_keys=True) + "\n")
    print(
        "CRT_R2CB_USDJPY_WAIT_JOURNEY_JSON="
        + json.dumps(report, sort_keys=True)
    )


if __name__ == "__main__":
    main()
