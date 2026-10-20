"""R2-T overlap decomposition for BTC_BEARISH and BTC_REF2_PLUS.

Uses only already-consumed BTC history 2018-2026 and preserves 2017-2018.

The lab asks whether the two eight-year survivors are redundant, nested or
complementary. It does not select a final composition.

Groups:
- BEARISH_ONLY;
- REF2_PLUS_ONLY;
- OVERLAP;
- NEITHER.

It also reports standalone, union and intersection summaries across the four
consumed 2Y regimes.
"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from qore.infrastructure.trader_lab.vt08_crt_pure_r2_model1_reference_lab import (
    Model1LabTrade,
    _resolve_trade,
    _summary,
    aggregate_complete_m15,
)
from qore.infrastructure.trader_lab.vt08_crt_pure_r2c_close_unmitigated_replay import (
    build_close_unmitigated_breach_groups,
)
from qore.infrastructure.trader_lab.vt08_crt_pure_r2e_source_multiplicity_census import (
    _aligned_sources,
    _c3_m15,
)
from qore.infrastructure.trader_lab.vt08_crt_pure_r2g_competition_lab import (
    select_competing_hypothesis,
)
from qore.infrastructure.trader_lab.vt08_crt_pure_r2j_market_context_validation import (
    BASE_POLICY,
    CandidateContext,
    CandidateId,
    _accept,
)
from qore.infrastructure.trader_lab.vt08_crt_pure_window_evidence import (
    build_parent_crts_for_window,
    load_m5_window,
)
from qore.infrastructure.traders.crt_pure_identity import CrtPureMarket

IDENTITY = "VT08_CRT_PURE_R2T_BTCUSD_SURVIVOR_OVERLAP_001"
SCHEMA = "qore.vt08.crt_pure.r2t_btcusd_survivor_overlap.v1"
MARKET = CrtPureMarket.BTCUSD

START = datetime(2018, 9, 21, 0, 0, tzinfo=UTC)
B2 = datetime(2020, 9, 21, 0, 0, tzinfo=UTC)
B3 = datetime(2022, 9, 21, 0, 0, tzinfo=UTC)
B4 = datetime(2024, 9, 21, 0, 0, tzinfo=UTC)
END = datetime(2026, 9, 21, 0, 0, tzinfo=UTC)


def _window(
    rows: tuple[Model1LabTrade, ...],
    start: datetime,
    end: datetime,
) -> tuple[Model1LabTrade, ...]:
    return tuple(
        row
        for row in rows
        if start <= datetime.fromisoformat(row.entry_opened_at) < end
    )


def _windows(rows: tuple[Model1LabTrade, ...]) -> dict[str, Any]:
    return {
        "full_8y": _summary(rows),
        "block_2018_20": _summary(_window(rows, START, B2)),
        "block_2020_22": _summary(_window(rows, B2, B3)),
        "block_2022_24": _summary(_window(rows, B3, B4)),
        "block_2024_26": _summary(_window(rows, B4, END)),
    }


def run_overlap() -> tuple[dict[str, tuple[Model1LabTrade, ...]], dict[str, Any]]:
    bars = load_m5_window(MARKET, start=START, end_exclusive=END)
    parents = build_parent_crts_for_window(
        MARKET,
        bars,
        start=START,
        end_exclusive=END,
    )
    m15 = aggregate_complete_m15(bars)
    m15_by_time = {bar.opened_at: bar for bar in m15}
    breaches = build_close_unmitigated_breach_groups(m15)

    groups: dict[str, list[Model1LabTrade]] = defaultdict(list)
    diagnostics: dict[str, int] = defaultdict(int)

    for parent in parents:
        diagnostics["parent_count"] += 1
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

        observation, confirmation, entry = selected
        context = CandidateContext(
            parent=parent,
            observation=observation,
            confirmation=confirmation,
            entry=entry,
            generation=observations.index(observation) + 1,
        )
        trade = _resolve_trade(
            parent=parent,
            group=observation.group,
            confirmation=confirmation,
            entry_bar=entry,
            c3_m15=c3_m15,
        )
        if trade is None:
            diagnostics["invalid_risk_geometry"] += 1
            continue

        bearish = _accept(CandidateId.BTC_BEARISH, context)
        ref2 = _accept(CandidateId.BTC_REF2_PLUS, context)

        if bearish:
            groups["BTC_BEARISH"].append(trade)
        if ref2:
            groups["BTC_REF2_PLUS"].append(trade)
        if bearish or ref2:
            groups["UNION"].append(trade)
        if bearish and ref2:
            groups["INTERSECTION"].append(trade)
            groups["OVERLAP"].append(trade)
        elif bearish:
            groups["BEARISH_ONLY"].append(trade)
        elif ref2:
            groups["REF2_PLUS_ONLY"].append(trade)
        else:
            groups["NEITHER"].append(trade)

        diagnostics["trade_classified"] += 1

    names = (
        "BTC_BEARISH",
        "BTC_REF2_PLUS",
        "UNION",
        "INTERSECTION",
        "BEARISH_ONLY",
        "REF2_PLUS_ONLY",
        "OVERLAP",
        "NEITHER",
    )
    frozen = {
        name: tuple(sorted(groups[name], key=lambda item: item.entry_opened_at))
        for name in names
    }

    bearish_ids = {trade.entry_opened_at for trade in frozen["BTC_BEARISH"]}
    ref_ids = {trade.entry_opened_at for trade in frozen["BTC_REF2_PLUS"]}
    union_ids = bearish_ids | ref_ids
    intersection_ids = bearish_ids & ref_ids

    report: dict[str, Any] = {
        "schema": SCHEMA,
        "identity": IDENTITY,
        "market": MARKET.value,
        "window_start": START.isoformat(),
        "window_end_exclusive": END.isoformat(),
        "base_competition_policy": BASE_POLICY.value,
        "diagnostics": dict(diagnostics),
        "groups": {name: _windows(frozen[name]) for name in names},
        "overlap_counts": {
            "bearish": len(bearish_ids),
            "ref2_plus": len(ref_ids),
            "union": len(union_ids),
            "intersection": len(intersection_ids),
            "jaccard": (
                0.0
                if not union_ids
                else round(len(intersection_ids) / len(union_ids), 8)
            ),
            "intersection_share_of_bearish": (
                0.0
                if not bearish_ids
                else round(len(intersection_ids) / len(bearish_ids), 8)
            ),
            "intersection_share_of_ref2_plus": (
                0.0
                if not ref_ids
                else round(len(intersection_ids) / len(ref_ids), 8)
            ),
        },
        "final_composition_selected": False,
        "fresh_2017_2018_preserved": True,
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

    groups, report = run_overlap()
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / "report.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n"
    )
    with (args.output / "trades.jsonl").open("w", encoding="utf-8") as handle:
        for group_name, rows in groups.items():
            for trade in rows:
                row = asdict(trade)
                row["overlap_group"] = group_name
                handle.write(json.dumps(row, sort_keys=True) + "\n")
    print("CRT_R2T_BTC_OVERLAP_JSON=" + json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    main()
