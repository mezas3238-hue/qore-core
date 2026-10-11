"""Nine-market post-hoc H1-target/structural-M15-stop audit for V49.

V49 takes the FIRST (most recent) still-untouched H1 candle-extreme witness;
it does not select a reward multiple, and no partial exits or break-even exist.
This auditor preserves every source/ledger identity and does not adjust rules.
"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from dataclasses import asdict, dataclass
from decimal import Decimal
from pathlib import Path
from statistics import median
from typing import Any

from qore.infrastructure.trader_lab.capitalizer_high_frequency_capacity_census_v49 import (
    V49Opportunity,
)
from qore.infrastructure.trader_lab.capitalizer_scalper_v49_v50_g_waterfall_v1 import (
    source_id,
)
from qore.infrastructure.trader_lab.capitalizer_scalper_winner_retention_v1 import (
    _load_sources,
    _load_trades,
    _origin,
    _source_table,
)
from qore.infrastructure.trader_lab.capitalizer_v49_development_economics import (
    V49EconomicTrade,
    _portfolio_select,
)

IDENTITY = "QORE_SCALPER_A2_H1_TARGET_M15_STOP_ASYMMETRY_V1"
RR_BANDS = (Decimal("0.25"), Decimal("0.5"), Decimal("1"), Decimal("1.5"), Decimal("2"))


@dataclass(frozen=True, slots=True)
class TargetGeometryRow:
    source_opportunity_id: str
    symbol: str
    session: str
    trigger_family: str
    entry_at: str
    h1_state_basis: str
    exit_reason: str
    m15_stop_risk_price: str
    h1_destination_distance_price: str
    planned_target_r: str
    realized_gross_r: str
    selected_by_frozen_max3: bool
    full_target_exit_no_partials: bool
    observed_after_simulation_only: bool = True

    def __post_init__(self) -> None:
        if self.exit_reason not in ("STOP", "TARGET", "SESSION_EXIT"):
            raise ValueError("unknown V49 exit")
        if self.full_target_exit_no_partials != (self.exit_reason == "TARGET"):
            raise ValueError("TARGET must be a full exit under frozen V49")
        if not self.observed_after_simulation_only:
            raise ValueError("historical target analysis cannot authorize entries")


def _source_matches(
    source: V49Opportunity,
    trade: V49EconomicTrade,
) -> TargetGeometryRow:
    entry = Decimal(source.decision_reference_price)
    stop = Decimal(source.m15_protected_swing_price)
    target = Decimal(source.structural_target_witness_price)
    if (entry != Decimal(trade.entry_price)
        or stop != Decimal(trade.stop_price)
        or target != Decimal(trade.target_price)
        or trade.h1_state_basis != source.h1_state_basis
        or trade.trigger_family != source.m1_trigger_family
        or trade.entry_at != source.m1_trigger_confirmed_at
        or trade.symbol != source.symbol
        or trade.session != source.session):
        raise ValueError("V49 trade/source stop/target identity mismatch")
    expected_long = source.h1_state_direction == "BULLISH"
    if (trade.direction == "LONG") != expected_long or trade.direction not in ("LONG", "SHORT"):
        raise ValueError("source H1 bias and V49 trade direction disagree")
    if not (stop < entry < target if expected_long else target < entry < stop):
        raise ValueError("source stop and target on incorrect side of entry")
    risk = abs(entry - stop)
    room = abs(target - entry)
    expected_r = room / risk
    if risk <= 0 or room <= 0:
        raise ValueError("invalid structural R geometry")
    if abs(Decimal(trade.planned_reward_r) - expected_r) > Decimal("1e-18"):
        raise ValueError("planned reward R does not match the unchanged source prices")
    if trade.exit_reason == "TARGET" and abs(
        Decimal(trade.realized_gross_r) - expected_r
    ) > Decimal("1e-18"):
        raise ValueError("V49 full target exit does not pay planned reward")
    if trade.exit_reason == "STOP" and Decimal(trade.realized_gross_r) != -1:
        raise ValueError("V49 STOP exit must pay -1R")
    return TargetGeometryRow(
        source_opportunity_id=source_id(source),
        symbol=source.symbol,
        session=source.session,
        trigger_family=source.m1_trigger_family,
        entry_at=trade.entry_at,
        h1_state_basis=source.h1_state_basis,
        exit_reason=trade.exit_reason,
        m15_stop_risk_price=str(risk),
        h1_destination_distance_price=str(room),
        planned_target_r=str(expected_r),
        realized_gross_r=trade.realized_gross_r,
        selected_by_frozen_max3=False,
        full_target_exit_no_partials=trade.exit_reason == "TARGET",
    )


def _summary(rows: tuple[TargetGeometryRow, ...]) -> dict[str, Any]:
    if not rows:
        return {"count": 0}
    rr = sorted(Decimal(item.planned_target_r) for item in rows)
    target_rows = tuple(item for item in rows if item.exit_reason == "TARGET")
    stop_rows = tuple(item for item in rows if item.exit_reason == "STOP")
    session_rows = tuple(item for item in rows if item.exit_reason == "SESSION_EXIT")
    target_payout = sum(
        (Decimal(item.realized_gross_r) for item in target_rows), Decimal(0)
    )
    def average(v: tuple[Decimal, ...]) -> str | None:
        return str(sum(v, Decimal(0)) / len(v)) if v else None
    return {
        "count": len(rows),
        "planned_target_r_mean": average(tuple(rr)),
        "planned_target_r_median": str(median(rr)),
        "planned_target_r_p10": str(rr[int((len(rr)-1)*0.1)]),
        "planned_target_r_p90": str(rr[int((len(rr)-1)*0.9)]),
        "planned_target_r_below": {
            str(k): sum(x < k for x in rr) for k in RR_BANDS
        },
        "target_exits": len(target_rows),
        "target_exits_mean_realized_r": (
            str(target_payout / len(target_rows)) if target_rows else None
        ),
        "target_exits_total_gross_r": str(target_payout),
        "target_exits_planned_r_below_one": sum(
            Decimal(row.planned_target_r) < 1 for row in target_rows
        ),
        "stop_exits": len(stop_rows),
        "session_exits": len(session_rows),
        "mean_realized_r": average(tuple(
            Decimal(row.realized_gross_r) for row in rows
        )),
        "no_partial_exits_observed": True,
        "no_break_even_exit_rule_in_v49": True,
    }


def report_source_target_geometry(
    sources: tuple[V49Opportunity, ...],
    economic_trades: tuple[V49EconomicTrade, ...],
    *,
    expected_markets: int = 9,
) -> tuple[dict[str, Any], tuple[TargetGeometryRow, ...]]:
    markets = {item.symbol for item in sources}
    if expected_markets < 1 or len(markets) != expected_markets:
        raise ValueError("target audit market coverage mismatch")
    if len({source_id(item) for item in sources}) != len(sources):
        raise ValueError("ambiguous V49 source IDs")
    ids = _source_table(sources)
    lookup = {source_id(item): item for item in sources}
    selected = tuple(trade for _, trade in _portfolio_select(economic_trades))
    selected_ids = {_origin(trade, ids) for trade in selected}
    if len(selected_ids) != len(selected):
        raise ValueError("MAX3 selected same source twice")
    rows: list[TargetGeometryRow] = []
    observed: set[str] = set()
    for trade in economic_trades:
        identifier = _origin(trade, ids)
        if identifier in observed:
            raise ValueError("same V49 source replayed multiple times")
        observed.add(identifier)
        item = _source_matches(lookup[identifier], trade)
        rows.append(TargetGeometryRow(
            **{**asdict(item), "selected_by_frozen_max3": identifier in selected_ids}
        ))
    if len(rows) != len(sources) or observed != set(lookup):
        raise ValueError("source/market trade universe not complete")
    chosen = tuple(item for item in rows if item.selected_by_frozen_max3)
    excluded = tuple(item for item in rows if not item.selected_by_frozen_max3)
    if len(rows) == 2876 and expected_markets == 9 and (
        len(chosen) != 2020 or len(excluded) != 856
    ):
        raise ValueError("frozen 9-market V49 MAX3 denominators mismatch")
    dimension: dict[str, dict[str, list[TargetGeometryRow]]] = {
        "session": defaultdict(list),
        "market": defaultdict(list),
        "trigger_family": defaultdict(list),
        "exit_reason": defaultdict(list),
        "h1_basis": defaultdict(list),
    }
    for row in chosen:
        dimension["session"][row.session].append(row)
        dimension["market"][row.symbol].append(row)
        dimension["trigger_family"][row.trigger_family].append(row)
        dimension["exit_reason"][row.exit_reason].append(row)
        dimension["h1_basis"][row.h1_state_basis].append(row)
    return {
        "identity": IDENTITY,
        "source_opportunities": len(sources),
        "economic_replays": len(rows),
        "selected_after_max3": len(chosen),
        "excluded_before_max3": len(excluded),
        "selected": _summary(chosen),
        "excluded": _summary(excluded),
        "selected_by": {
            k: {v: _summary(tuple(items)) for v, items in sorted(group.items())}
            for k, group in dimension.items()
        },
        "target_source": "V49_CAUSAL_H1_CANDLE_HIGH_LOW_WITNESS",
        "stop_source": "V49_M15_PROTECTED_SWING",
        "h1_target_witness_independently_replayed_with_m1": False,
        "cannot_claim_h1_swing_pivot_confirmation": True,
        "does_not_establish_target_reachable_or_exit_policy_improvement": True,
        "no_source_entry_or_exit_policy_changed": True,
        "trader_certified": False,
        "live_authorized": False,
    }, tuple(rows)


def build_target_audit(
    root: Path,
    *,
    expected_markets: int = 9,
) -> tuple[dict[str, Any], tuple[TargetGeometryRow, ...]]:
    sources_by_market = _load_sources(root, expected_markets)
    sources = tuple(
        x for symbol in sorted(sources_by_market) for x in sources_by_market[symbol]
    )
    loaded = _load_trades(
        root,
        "capitalizer-*-v49-development-economics-trades.jsonl",
        set(sources_by_market),
        V49EconomicTrade,
    )
    trades = tuple(row for row in loaded if isinstance(row, V49EconomicTrade))
    if len(trades) != len(loaded):
        raise ValueError("foreign V50-G trade type in V49 control")
    return report_source_target_geometry(
        sources, trades, expected_markets=expected_markets,
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("v49_control_root", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    report, rows = build_target_audit(args.v49_control_root)
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / "scalper-a2-v49-target-asymmetry.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    with (args.output / "scalper-a2-v49-target-asymmetry-source-rows.jsonl").open(
        "w", encoding="utf-8"
    ) as f:
        for row in rows:
            f.write(json.dumps(asdict(row), sort_keys=True) + "\n")
    print(json.dumps({
        "identity": IDENTITY,
        "selected": report["selected"],
        "source_opportunities": report["source_opportunities"],
        "trader_certified": False,
    }, sort_keys=True))


if __name__ == "__main__":
    main()
