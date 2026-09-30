"""V50-G consumed-development cognitive geometry economic replay.

Predeclared in PR #623 comment 5916196907 before opening V50-G outcomes.

This experiment isolates whether causal V50 stop/target repair improves the economics of the
unchanged V49 H1->M15->M1 source opportunities.

No holdout is accessed. No outcome participates in candidate admission or geometry selection.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

from qore.infrastructure.trader_lab.capitalizer_cibo_m1_reader_v1 import (
    CapitalizerM1Bar,
    iter_cibo_m1,
)
from qore.infrastructure.trader_lab.capitalizer_experience_memory import (
    CapitalizerExperienceMemory,
)
from qore.infrastructure.trader_lab.capitalizer_generic_scalp_census_v48 import _aggregate
from qore.infrastructure.trader_lab.capitalizer_high_frequency_capacity_census_v49 import (
    DEFAULT_LOOKBACK,
    DEV_WINDOW_END,
    DEV_WINDOW_START,
    V49Opportunity,
)
from qore.infrastructure.trader_lab.capitalizer_metacognition_v2 import (
    CapitalizerEpistemicReadiness,
)
from qore.infrastructure.trader_lab.capitalizer_session_clock import capitalizer_session_at
from qore.infrastructure.trader_lab.capitalizer_v50_cognitive_geometry_specialist import (
    V50GeometryDecision,
    propose_v50_geometry,
)
from qore.infrastructure.trader_lab.capitalizer_v50_cognitive_hf_bridge import (
    V50CognitiveDisposition,
)
from qore.infrastructure.trader_lab.capitalizer_v50_cognitive_opportunity import (
    build_v50_cognitive_snapshot,
)

IDENTITY = "QORE_CAPITALIZER_V50_G_COGNITIVE_GEOMETRY_ECONOMICS"
MATRIX_IDENTITY = "QORE_CAPITALIZER_V50_G_COGNITIVE_GEOMETRY_MATRIX"
POLICIES = ("GEOMETRY_ONLY", "COGNITIVE_GEOMETRY")
COST_STRESS_R = (
    Decimal("0"),
    Decimal("0.01"),
    Decimal("0.025"),
    Decimal("0.05"),
)
COGNITIVE_GEOMETRY_ALLOWED = {
    V50CognitiveDisposition.PASS_TO_COMPETITION,
    V50CognitiveDisposition.REFINE_STOP_GEOMETRY,
    V50CognitiveDisposition.REFINE_TARGET_LADDER,
}


@dataclass(frozen=True, slots=True)
class V50GTrade:
    policy: str
    symbol: str
    session: str
    operating_date: str
    entry_at: str
    exit_at: str
    entry_price: str
    stop_price: str
    target_price: str
    planned_reward_r: str
    realized_gross_r: str
    exit_reason: str
    m1_bars_held: int
    cognitive_disposition: str
    geometry_decision: str
    trigger_family: str
    h1_basis: str
    same_bar_stop_target_ambiguity: bool = False
    outcome_used_for_admission: bool = False
    fresh_holdout_used: bool = False

    def __post_init__(self) -> None:
        if self.policy not in POLICIES:
            raise ValueError("unknown V50-G policy")
        if self.outcome_used_for_admission or self.fresh_holdout_used:
            raise ValueError("V50-G crossed epistemic boundary")


def _load_opportunities(root: Path) -> tuple[V49Opportunity, ...]:
    paths = sorted(root.rglob("capitalizer-*-v49-hf-capacity-opportunities.jsonl"))
    if len(paths) != 1:
        raise ValueError("V50-G market replay requires one opportunity ledger")
    rows: list[V49Opportunity] = []
    with paths[0].open(encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                rows.append(V49Opportunity(**json.loads(line)))
    return tuple(
        sorted(
            rows,
            key=lambda item: (
                datetime.fromisoformat(item.m1_trigger_confirmed_at),
                item.symbol,
                item.m1_trigger_family,
            ),
        )
    )


def _session_bars(
    bars: tuple[CapitalizerM1Bar, ...],
    *,
    entry_at: datetime,
    expected_session: str,
) -> tuple[CapitalizerM1Bar, ...]:
    result: list[CapitalizerM1Bar] = []
    started = False
    for bar in bars:
        if bar.opened_at < entry_at:
            continue
        observed = capitalizer_session_at(bar.opened_at)
        if observed is None or observed.value != expected_session:
            if started:
                break
            continue
        started = True
        result.append(bar)
    return tuple(result)


def _replay(
    *,
    policy: str,
    opportunity: V49Opportunity,
    bars: tuple[CapitalizerM1Bar, ...],
    stop: Decimal,
    target: Decimal,
    disposition: V50CognitiveDisposition,
) -> V50GTrade | None:
    entry_at = datetime.fromisoformat(opportunity.m1_trigger_confirmed_at)
    entry = Decimal(opportunity.decision_reference_price)
    risk = abs(entry - stop)
    reward = abs(target - entry)
    if risk <= 0 or reward <= 0:
        raise ValueError("V50-G requires positive risk/reward")

    window = _session_bars(
        bars,
        entry_at=entry_at,
        expected_session=opportunity.session,
    )
    if not window:
        return None

    is_long = opportunity.h1_state_direction == "BULLISH"
    ambiguity = False
    held = 0
    for bar in window:
        held += 1
        stop_hit = bar.low <= stop if is_long else bar.high >= stop
        target_hit = bar.high >= target if is_long else bar.low <= target
        if stop_hit:
            ambiguity = target_hit
            realized = Decimal("-1")
            reason = "STOP"
            exit_at = bar.closed_at
            break
        if target_hit:
            realized = reward / risk
            reason = "TARGET"
            exit_at = bar.closed_at
            break
    else:
        last = window[-1]
        delta = last.close - entry if is_long else entry - last.close
        realized = delta / risk
        reason = "SESSION_EXIT"
        exit_at = last.closed_at

    return V50GTrade(
        policy=policy,
        symbol=opportunity.symbol,
        session=opportunity.session,
        operating_date=opportunity.operating_date,
        entry_at=entry_at.isoformat(),
        exit_at=exit_at.isoformat(),
        entry_price=str(entry),
        stop_price=str(stop),
        target_price=str(target),
        planned_reward_r=str(reward / risk),
        realized_gross_r=str(realized),
        exit_reason=reason,
        m1_bars_held=held,
        cognitive_disposition=disposition.value,
        geometry_decision=V50GeometryDecision.READY.value,
        trigger_family=opportunity.m1_trigger_family,
        h1_basis=opportunity.h1_state_basis,
        same_bar_stop_target_ambiguity=ambiguity,
    )


def build_market(
    *,
    capacity_root: Path,
    m1_root: Path,
) -> tuple[dict[str, Any], tuple[V50GTrade, ...]]:
    opportunities = _load_opportunities(capacity_root)
    if not opportunities:
        raise ValueError("V50-G requires source-complete opportunities")
    symbol = opportunities[0].symbol
    session = opportunities[0].session

    lookback_start = DEV_WINDOW_START - DEFAULT_LOOKBACK
    bars = tuple(
        bar
        for bar in iter_cibo_m1(m1_root)
        if lookback_start <= bar.opened_at < DEV_WINDOW_END
    )
    if not bars or any(bar.symbol != symbol for bar in bars):
        raise ValueError("V50-G M1 market mismatch")
    h1 = _aggregate(bars, minutes=60)

    trades: list[V50GTrade] = []
    geometry_counts: Counter[str] = Counter()
    disposition_counts: Counter[str] = Counter()
    missing_session_bars = 0

    for opportunity in opportunities:
        snapshot = build_v50_cognitive_snapshot(
            opportunity,
            m1_bars=bars,
            h1_bars=h1,
            experience_memory=CapitalizerExperienceMemory(),
            metacognitive_readiness=CapitalizerEpistemicReadiness.WELL_SUPPORTED,
        )
        disposition = snapshot.cognitive.disposition
        disposition_counts[disposition.value] += 1
        geometry = propose_v50_geometry(snapshot)
        geometry_counts[geometry.decision.value] += 1

        if geometry.decision is not V50GeometryDecision.READY:
            continue
        if (
            geometry.stop_price is None
            or geometry.t1 is None
        ):
            raise ValueError("V50-G READY geometry missing stop/target")

        for policy in POLICIES:
            if (
                policy == "COGNITIVE_GEOMETRY"
                and disposition not in COGNITIVE_GEOMETRY_ALLOWED
            ):
                continue
            trade = _replay(
                policy=policy,
                opportunity=opportunity,
                bars=bars,
                stop=geometry.stop_price,
                target=geometry.t1.price,
                disposition=disposition,
            )
            if trade is None:
                missing_session_bars += 1
                continue
            trades.append(trade)

    return {
        "identity": IDENTITY,
        "symbol": symbol,
        "session": session,
        "window_start": DEV_WINDOW_START.isoformat(),
        "window_end_exclusive": DEV_WINDOW_END.isoformat(),
        "context_lookback_start": lookback_start.isoformat(),
        "source_opportunities": len(opportunities),
        "geometry_decisions": sorted(geometry_counts.items()),
        "cognitive_dispositions": sorted(disposition_counts.items()),
        "geometry_ready": geometry_counts[V50GeometryDecision.READY.value],
        "policy_trade_rows_before_max3": {
            policy: sum(item.policy == policy for item in trades)
            for policy in POLICIES
        },
        "missing_session_bars": missing_session_bars,
        "entry_changed": False,
        "daily_used": False,
        "h4_used": False,
        "outcome_used_for_admission": False,
        "reserved_holdout_reopened": False,
        "fresh_holdout_used": False,
        "development_only": True,
        "rule_promotion_allowed": False,
        "trader_certified": False,
        "live_authorized": False,
    }, tuple(trades)


def _metrics(rows: tuple[V50GTrade, ...], *, cost_r: Decimal = Decimal("0")) -> dict[str, Any]:
    if not rows:
        return {
            "trades": 0,
            "profit_factor": None,
            "total_r": "0",
            "expectancy_r": None,
            "max_drawdown_r": "0",
            "max_losing_streak": 0,
            "wins": 0,
            "losses": 0,
            "stops": 0,
            "targets": 0,
            "session_exits": 0,
        }
    ordered = tuple(
        sorted(
            rows,
            key=lambda item: (
                datetime.fromisoformat(item.exit_at),
                datetime.fromisoformat(item.entry_at),
                item.symbol,
            ),
        )
    )
    values = tuple(Decimal(item.realized_gross_r) - cost_r for item in ordered)
    gp = sum((value for value in values if value > 0), Decimal("0"))
    gl = -sum((value for value in values if value < 0), Decimal("0"))
    total = sum(values, Decimal("0"))
    equity = Decimal("0")
    peak = Decimal("0")
    dd = Decimal("0")
    streak = 0
    max_streak = 0
    for value in values:
        equity += value
        peak = max(peak, equity)
        dd = max(dd, peak - equity)
        if value < 0:
            streak += 1
            max_streak = max(max_streak, streak)
        else:
            streak = 0
    return {
        "trades": len(rows),
        "profit_factor": None if gl == 0 else str(gp / gl),
        "total_r": str(total),
        "expectancy_r": str(total / Decimal(len(rows))),
        "max_drawdown_r": str(dd),
        "max_losing_streak": max_streak,
        "wins": sum(value > 0 for value in values),
        "losses": sum(value < 0 for value in values),
        "stops": sum(item.exit_reason == "STOP" for item in rows),
        "targets": sum(item.exit_reason == "TARGET" for item in rows),
        "session_exits": sum(item.exit_reason == "SESSION_EXIT" for item in rows),
        "median_planned_reward_r": str(
            sorted(Decimal(item.planned_reward_r) for item in rows)[len(rows) // 2]
        ),
        "same_bar_ambiguities": sum(
            item.same_bar_stop_target_ambiguity for item in rows
        ),
    }


def _portfolio(rows: tuple[V50GTrade, ...], *, policy: str) -> tuple[V50GTrade, ...]:
    grouped: dict[tuple[str, str], list[V50GTrade]] = defaultdict(list)
    for item in rows:
        if item.policy == policy:
            grouped[(item.session, item.operating_date)].append(item)
    selected: list[V50GTrade] = []
    for key in sorted(grouped):
        candidates = sorted(
            grouped[key],
            key=lambda item: (
                datetime.fromisoformat(item.entry_at),
                item.symbol,
                item.trigger_family,
            ),
        )
        selected.extend(candidates[:3])
    return tuple(
        sorted(
            selected,
            key=lambda item: (
                datetime.fromisoformat(item.entry_at),
                item.symbol,
            ),
        )
    )


def build_matrix(root: Path) -> dict[str, Any]:
    paths = sorted(root.rglob("capitalizer-*-v50-g-trades.jsonl"))
    if len(paths) != 9:
        raise ValueError(f"V50-G matrix requires 9 trade ledgers, got {len(paths)}")
    rows: list[V50GTrade] = []
    for path in paths:
        with path.open(encoding="utf-8") as handle:
            for line in handle:
                if line.strip():
                    rows.append(V50GTrade(**json.loads(line)))
    all_rows = tuple(rows)

    policies: dict[str, Any] = {}
    for policy in POLICIES:
        selected = _portfolio(all_rows, policy=policy)
        policies[policy] = {
            "gross": _metrics(selected),
            "cost_stress": [
                {
                    "cost_r_per_trade": str(cost),
                    "metrics": _metrics(selected, cost_r=cost),
                }
                for cost in COST_STRESS_R
            ],
            "by_session": {
                session: _metrics(
                    tuple(item for item in selected if item.session == session)
                )
                for session in ("ASIA", "LONDON", "NEW_YORK")
            },
            "by_market": {
                symbol: _metrics(
                    tuple(item for item in selected if item.symbol == symbol)
                )
                for symbol in sorted({item.symbol for item in selected})
            },
        }

    return {
        "identity": MATRIX_IDENTITY,
        "window_start": DEV_WINDOW_START.isoformat(),
        "window_end_exclusive": DEV_WINDOW_END.isoformat(),
        "policies": policies,
        "entry_changed": False,
        "decision_timeframes": ["H1", "M15", "M1"],
        "outcome_aware_selection": False,
        "reserved_holdout_reopened": False,
        "fresh_holdout_used": False,
        "development_only": True,
        "automatic_policy_promotion": False,
        "trader_certified": False,
        "live_authorized": False,
        "real_capital_authorized": False,
    }


def write_market(report: dict[str, Any], trades: tuple[V50GTrade, ...], output: Path) -> None:
    output.mkdir(parents=True, exist_ok=True)
    symbol = str(report["symbol"]).lower()
    (output / f"capitalizer-{symbol}-v50-g-report.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    with (output / f"capitalizer-{symbol}-v50-g-trades.jsonl").open(
        "w",
        encoding="utf-8",
    ) as handle:
        for trade in trades:
            handle.write(json.dumps(asdict(trade), sort_keys=True) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)

    market = sub.add_parser("market")
    market.add_argument("capacity_root", type=Path)
    market.add_argument("m1_root", type=Path)
    market.add_argument("output", type=Path)

    matrix = sub.add_parser("matrix")
    matrix.add_argument("input_root", type=Path)
    matrix.add_argument("output", type=Path)

    args = parser.parse_args()
    if args.command == "market":
        report, trades = build_market(
            capacity_root=args.capacity_root,
            m1_root=args.m1_root,
        )
        write_market(report, trades, args.output)
        print(json.dumps(report, sort_keys=True))
        return

    report = build_matrix(args.input_root)
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / "capitalizer-v50-g-matrix.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    main()
