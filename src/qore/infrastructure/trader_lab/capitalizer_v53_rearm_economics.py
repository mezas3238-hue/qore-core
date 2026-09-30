"""V53 causal re-arm economic replay for the high-frequency Capitalizer Scalper.

V53 is predeclared before authoritative V50-R capacity/economic outcomes.

It converts V50-R's pre-economic attempt ledger into two outcome-blind candidate populations:
- GEOMETRY_REARM: first Geometry READY attempt for each parent M15 setup;
- COGNITIVE_REARM: first Cognitive-Geometry READY attempt for each parent M15 setup.

The selected attempt is fixed before terminal outcome replay. Stop/target geometry is rebuilt
causally at that attempt timestamp from retained provider-native M1. Portfolio MAX3 is then
recompeted chronologically across all nine markets.

No outcome participates in attempt choice, geometry, or portfolio selection.
"""

from __future__ import annotations

import argparse
import json
import math
from collections import defaultdict
from dataclasses import asdict, dataclass
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from statistics import fmean, pstdev
from typing import Any

from qore.infrastructure.trader_lab.capitalizer_cibo_m1_reader_v1 import (
    CapitalizerM1Bar,
    iter_cibo_m1,
)
from qore.infrastructure.trader_lab.capitalizer_contract import MAX_EXECUTIONS_PER_SESSION
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
from qore.infrastructure.trader_lab.capitalizer_v49_development_economics import (
    V49EconomicTrade,
)
from qore.infrastructure.trader_lab.capitalizer_v50_cognitive_geometry_economics import (
    COST_STRESS_R,
)
from qore.infrastructure.trader_lab.capitalizer_v50_cognitive_geometry_economics import (
    _replay as replay_v50_geometry,
)
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
from qore.infrastructure.trader_lab.capitalizer_v50_m1_rearm_capacity import (
    V50RearmAttempt,
)

IDENTITY = "QORE_CAPITALIZER_V53_REARM_ECONOMICS"
MATRIX_IDENTITY = "QORE_CAPITALIZER_V53_NINE_MARKET_REARM_ECONOMICS"
POLICIES = ("GEOMETRY_REARM", "COGNITIVE_REARM")
COGNITIVE_ALLOWED = {
    V50CognitiveDisposition.PASS_TO_COMPETITION,
    V50CognitiveDisposition.REFINE_STOP_GEOMETRY,
    V50CognitiveDisposition.REFINE_TARGET_LADDER,
}


@dataclass(frozen=True, slots=True)
class V53RearmTrade:
    policy: str
    symbol: str
    session: str
    operating_date: str
    h1_state_from: str
    m15_setup_confirmed_at: str
    parent_first_trigger_at: str
    entry_at: str
    exit_at: str
    attempt_index: int
    entry_price: str
    stop_price: str
    target_price: str
    planned_reward_r: str
    realized_gross_r: str
    exit_reason: str
    trigger_family: str
    cognitive_disposition: str
    same_bar_stop_target_ambiguity: bool = False
    outcome_used_for_selection: bool = False
    future_used_for_geometry: bool = False

    def __post_init__(self) -> None:
        if self.policy not in POLICIES:
            raise ValueError("unknown V53 policy")
        if self.attempt_index < 1:
            raise ValueError("V53 attempt index must be >= 1")
        if self.outcome_used_for_selection or self.future_used_for_geometry:
            raise ValueError("V53 crossed epistemic boundary")


def _setup_key(
    item: V50RearmAttempt,
) -> tuple[str, str, str, str, str]:
    return (
        item.symbol,
        item.session,
        item.operating_date,
        item.h1_state_from,
        item.m15_setup_confirmed_at,
    )


def _load_attempts(root: Path) -> tuple[V50RearmAttempt, ...]:
    paths = sorted(root.rglob("capitalizer-*-v50-r-rearm-capacity-attempts.jsonl"))
    if len(paths) != 1:
        raise ValueError("V53 market replay requires one V50-R attempt ledger")
    rows: list[V50RearmAttempt] = []
    with paths[0].open(encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                rows.append(V50RearmAttempt(**json.loads(line)))
    return tuple(
        sorted(
            rows,
            key=lambda item: (
                datetime.fromisoformat(item.trigger_confirmed_at),
                item.symbol,
                item.attempt_index,
            ),
        )
    )


def _selected_attempts(
    rows: tuple[V50RearmAttempt, ...],
    *,
    policy: str,
) -> tuple[tuple[V50RearmAttempt, str], ...]:
    if policy not in POLICIES:
        raise ValueError("unknown V53 policy")

    grouped: dict[
        tuple[str, str, str, str, str], list[V50RearmAttempt]
    ] = defaultdict(list)
    for item in rows:
        grouped[_setup_key(item)].append(item)

    selected: list[tuple[V50RearmAttempt, str]] = []
    for key in sorted(grouped):
        attempts = sorted(
            grouped[key],
            key=lambda item: (
                datetime.fromisoformat(item.trigger_confirmed_at),
                item.attempt_index,
            ),
        )
        first_trigger_at = attempts[0].trigger_confirmed_at
        chosen: V50RearmAttempt | None = None
        for item in attempts:
            ready = (
                item.geometry_ready
                if policy == "GEOMETRY_REARM"
                else item.cognitive_geometry_ready
            )
            if ready:
                chosen = item
                break
        if chosen is not None:
            selected.append((chosen, first_trigger_at))

    return tuple(
        sorted(
            selected,
            key=lambda pair: (
                datetime.fromisoformat(pair[0].trigger_confirmed_at),
                pair[0].symbol,
            ),
        )
    )


def _direction(item: V50RearmAttempt) -> str:
    entry = Decimal(item.decision_reference_price)
    thesis_stop = Decimal(item.m15_protected_swing_price)
    if thesis_stop < entry:
        return "BULLISH"
    if thesis_stop > entry:
        return "BEARISH"
    raise ValueError("V53 cannot infer direction from zero thesis risk")


def _opportunity(item: V50RearmAttempt) -> V49Opportunity:
    return V49Opportunity(
        symbol=item.symbol,
        session=item.session,
        operating_date=item.operating_date,
        h1_state_direction=_direction(item),
        h1_state_from=item.h1_state_from,
        h1_state_until=item.h1_state_until,
        h1_state_basis=item.h1_state_basis,
        m15_setup_confirmed_at=item.m15_setup_confirmed_at,
        m15_protected_swing_price=item.m15_protected_swing_price,
        m1_trigger_confirmed_at=item.trigger_confirmed_at,
        m1_trigger_family=item.trigger_family,
        decision_reference_price=item.decision_reference_price,
        structural_target_witness_price=item.structural_target_witness_price,
    )


def build_market(
    *,
    rearm_root: Path,
    m1_root: Path,
) -> tuple[dict[str, Any], tuple[V53RearmTrade, ...]]:
    attempts = _load_attempts(rearm_root)
    if not attempts:
        raise ValueError("V53 requires V50-R attempts")
    symbol = attempts[0].symbol
    session = attempts[0].session
    if any(item.symbol != symbol or item.session != session for item in attempts):
        raise ValueError("V53 market input must contain one symbol/session")

    lookback_start = DEV_WINDOW_START - DEFAULT_LOOKBACK
    bars = tuple(
        bar
        for bar in iter_cibo_m1(m1_root)
        if lookback_start <= bar.opened_at < DEV_WINDOW_END
    )
    if not bars or any(bar.symbol != symbol for bar in bars):
        raise ValueError("V53 provider-native M1 market mismatch")
    h1 = _aggregate(bars, minutes=60)

    trades: list[V53RearmTrade] = []
    populations: dict[str, int] = {}
    for policy in POLICIES:
        chosen = _selected_attempts(attempts, policy=policy)
        populations[policy] = len(chosen)
        for attempt, parent_first_trigger_at in chosen:
            opportunity = _opportunity(attempt)
            snapshot = build_v50_cognitive_snapshot(
                opportunity,
                m1_bars=bars,
                h1_bars=h1,
                experience_memory=CapitalizerExperienceMemory(),
                metacognitive_readiness=CapitalizerEpistemicReadiness.WELL_SUPPORTED,
            )
            geometry = propose_v50_geometry(snapshot)
            if geometry.decision is not V50GeometryDecision.READY:
                raise ValueError("V53 selected attempt no longer reconstructs READY geometry")
            if geometry.stop_price is None or geometry.t1 is None:
                raise ValueError("V53 READY geometry missing stop/target")
            if (
                policy == "COGNITIVE_REARM"
                and snapshot.cognitive.disposition not in COGNITIVE_ALLOWED
            ):
                raise ValueError("V53 cognitive attempt no longer cognition-compatible")

            replay_policy = (
                "GEOMETRY_ONLY"
                if policy == "GEOMETRY_REARM"
                else "COGNITIVE_GEOMETRY"
            )
            replay = replay_v50_geometry(
                policy=replay_policy,
                opportunity=opportunity,
                bars=bars,
                stop=geometry.stop_price,
                target=geometry.t1.price,
                disposition=snapshot.cognitive.disposition,
            )
            if replay is None:
                continue

            trades.append(
                V53RearmTrade(
                    policy=policy,
                    symbol=replay.symbol,
                    session=replay.session,
                    operating_date=replay.operating_date,
                    h1_state_from=attempt.h1_state_from,
                    m15_setup_confirmed_at=attempt.m15_setup_confirmed_at,
                    parent_first_trigger_at=parent_first_trigger_at,
                    entry_at=replay.entry_at,
                    exit_at=replay.exit_at,
                    attempt_index=attempt.attempt_index,
                    entry_price=replay.entry_price,
                    stop_price=replay.stop_price,
                    target_price=replay.target_price,
                    planned_reward_r=replay.planned_reward_r,
                    realized_gross_r=replay.realized_gross_r,
                    exit_reason=replay.exit_reason,
                    trigger_family=replay.trigger_family,
                    cognitive_disposition=replay.cognitive_disposition,
                    same_bar_stop_target_ambiguity=(
                        replay.same_bar_stop_target_ambiguity
                    ),
                )
            )

    return {
        "identity": IDENTITY,
        "symbol": symbol,
        "session": session,
        "window_start": DEV_WINDOW_START.isoformat(),
        "window_end_exclusive": DEV_WINDOW_END.isoformat(),
        "selected_setups_before_max3": populations,
        "trade_rows_before_max3": {
            policy: sum(item.policy == policy for item in trades)
            for policy in POLICIES
        },
        "one_execution_max_per_m15_setup": True,
        "outcome_used_for_selection": False,
        "future_used_for_geometry": False,
        "historical_research": True,
        "automatic_policy_promotion": False,
        "trader_certified": False,
        "live_authorized": False,
        "real_capital_authorized": False,
    }, tuple(trades)


def _portfolio(
    rows: tuple[V53RearmTrade, ...],
    *,
    policy: str,
) -> tuple[V53RearmTrade, ...]:
    grouped: dict[tuple[str, str], list[V53RearmTrade]] = defaultdict(list)
    for item in rows:
        if item.policy == policy:
            grouped[(item.session, item.operating_date)].append(item)

    selected: list[V53RearmTrade] = []
    for key in sorted(grouped):
        candidates = sorted(
            grouped[key],
            key=lambda item: (
                datetime.fromisoformat(item.entry_at),
                item.symbol,
                item.attempt_index,
            ),
        )
        selected.extend(candidates[:MAX_EXECUTIONS_PER_SESSION])
    return tuple(
        sorted(
            selected,
            key=lambda item: (
                datetime.fromisoformat(item.entry_at),
                item.symbol,
            ),
        )
    )


def _risk_adjusted(
    rows: tuple[V53RearmTrade, ...],
    *,
    cost_r: Decimal = Decimal("0"),
) -> dict[str, Any]:
    daily: dict[str, Decimal] = defaultdict(lambda: Decimal("0"))
    for item in rows:
        daily[item.operating_date] += Decimal(item.realized_gross_r) - cost_r
    values = [float(value) for _, value in sorted(daily.items())]
    if not values:
        return {
            "daily_observations": 0,
            "annualization_factor": 252,
            "zero_trade_days_included": False,
            "sharpe_annualized": None,
            "sortino_annualized": None,
        }
    mean = fmean(values)
    sigma = pstdev(values) if len(values) > 1 else 0.0
    downside = math.sqrt(fmean([min(0.0, value) ** 2 for value in values]))
    annual = math.sqrt(252.0)
    return {
        "daily_observations": len(values),
        "annualization_factor": 252,
        "zero_trade_days_included": False,
        "risk_free_assumption_r": "0",
        "mar_r": "0",
        "sharpe_annualized": None if sigma == 0 else str(mean / sigma * annual),
        "sortino_annualized": None if downside == 0 else str(mean / downside * annual),
    }


def _metrics(
    rows: tuple[V53RearmTrade, ...],
    *,
    cost_r: Decimal = Decimal("0"),
) -> dict[str, Any]:
    if not rows:
        return {
            "trades": 0,
            "wins": 0,
            "losses": 0,
            "profit_factor": None,
            "total_r": "0",
            "expectancy_r": None,
            "max_drawdown_r": "0",
            "max_losing_streak": 0,
            "payoff_ratio": None,
            "stops": 0,
            "targets": 0,
            "session_exits": 0,
            "risk_adjusted": _risk_adjusted(rows, cost_r=cost_r),
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
    wins = tuple(value for value in values if value > 0)
    losses = tuple(value for value in values if value < 0)
    gp = sum(wins, Decimal("0"))
    gl = -sum(losses, Decimal("0"))
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

    avg_win = None if not wins else gp / Decimal(len(wins))
    avg_loss = None if not losses else gl / Decimal(len(losses))
    payoff = (
        None
        if avg_win is None or avg_loss is None or avg_loss == 0
        else avg_win / avg_loss
    )
    return {
        "trades": len(rows),
        "wins": len(wins),
        "losses": len(losses),
        "win_rate": str(Decimal(len(wins)) / Decimal(len(rows))),
        "profit_factor": None if gl == 0 else str(gp / gl),
        "total_r": str(total),
        "expectancy_r": str(total / Decimal(len(rows))),
        "max_drawdown_r": str(dd),
        "max_losing_streak": max_streak,
        "average_winner_r": None if avg_win is None else str(avg_win),
        "average_loser_r": None if avg_loss is None else str(avg_loss),
        "payoff_ratio": None if payoff is None else str(payoff),
        "stops": sum(item.exit_reason == "STOP" for item in rows),
        "targets": sum(item.exit_reason == "TARGET" for item in rows),
        "session_exits": sum(item.exit_reason == "SESSION_EXIT" for item in rows),
        "risk_adjusted": _risk_adjusted(rows, cost_r=cost_r),
    }


def _load_baseline(root: Path) -> tuple[V49EconomicTrade, ...]:
    paths = sorted(root.rglob("capitalizer-*-v49-development-economics-trades.jsonl"))
    if len(paths) != 9:
        raise ValueError("V53 matrix requires nine V49 baseline ledgers")
    rows: list[V49EconomicTrade] = []
    for path in paths:
        with path.open(encoding="utf-8") as handle:
            for line in handle:
                if line.strip():
                    rows.append(V49EconomicTrade(**json.loads(line)))

    grouped: dict[tuple[str, str], list[V49EconomicTrade]] = defaultdict(list)
    for item in rows:
        grouped[(item.session, item.operating_date)].append(item)
    selected: list[V49EconomicTrade] = []
    for key in sorted(grouped):
        candidates = sorted(
            grouped[key],
            key=lambda item: (
                datetime.fromisoformat(item.entry_at),
                item.symbol,
                item.trigger_family,
            ),
        )
        selected.extend(candidates[:MAX_EXECUTIONS_PER_SESSION])
    return tuple(
        sorted(
            selected,
            key=lambda item: (
                datetime.fromisoformat(item.entry_at),
                item.symbol,
            ),
        )
    )


def _preservation(
    baseline: tuple[V49EconomicTrade, ...],
    candidate: tuple[V53RearmTrade, ...],
) -> dict[str, Any]:
    candidate_by_source = {
        (item.symbol, item.parent_first_trigger_at): item for item in candidate
    }
    winners = tuple(
        item for item in baseline if Decimal(item.realized_gross_r) > 0
    )
    winner_r = sum(
        (Decimal(item.realized_gross_r) for item in winners),
        Decimal("0"),
    )
    preserved = tuple(
        item
        for item in winners
        if (item.symbol, item.entry_at) in candidate_by_source
        and Decimal(
            candidate_by_source[(item.symbol, item.entry_at)].realized_gross_r
        )
        > 0
    )
    preserved_candidate_r = sum(
        (
            Decimal(
                candidate_by_source[
                    (item.symbol, item.entry_at)
                ].realized_gross_r
            )
            for item in preserved
        ),
        Decimal("0"),
    )

    stops = tuple(item for item in baseline if item.exit_reason == "STOP")
    avoided_stops = tuple(
        item
        for item in stops
        if (item.symbol, item.entry_at) not in candidate_by_source
        or Decimal(
            candidate_by_source[(item.symbol, item.entry_at)].realized_gross_r
        )
        >= 0
    )
    return {
        "winner_count_preservation": (
            None
            if not winners
            else str(Decimal(len(preserved)) / Decimal(len(winners)))
        ),
        "winner_r_preservation": (
            None if winner_r == 0 else str(preserved_candidate_r / winner_r)
        ),
        "baseline_full_stops": len(stops),
        "avoided_baseline_full_stops": len(avoided_stops),
        "loss_recall": (
            None
            if not stops
            else str(Decimal(len(avoided_stops)) / Decimal(len(stops)))
        ),
    }


def build_matrix(
    root: Path,
    *,
    baseline_root: Path,
) -> dict[str, Any]:
    paths = sorted(root.rglob("capitalizer-*-v53-rearm-trades.jsonl"))
    if len(paths) != 9:
        raise ValueError(f"V53 matrix requires nine trade ledgers, got {len(paths)}")
    rows: list[V53RearmTrade] = []
    for path in paths:
        with path.open(encoding="utf-8") as handle:
            for line in handle:
                if line.strip():
                    rows.append(V53RearmTrade(**json.loads(line)))
    all_rows = tuple(rows)
    baseline = _load_baseline(baseline_root)

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
            "by_attempt_class": {
                "FIRST_ATTEMPT": _metrics(
                    tuple(item for item in selected if item.attempt_index == 1)
                ),
                "REARMED": _metrics(
                    tuple(item for item in selected if item.attempt_index > 1)
                ),
            },
            "preservation_vs_v49": _preservation(baseline, selected),
        }

    return {
        "identity": MATRIX_IDENTITY,
        "window_start": DEV_WINDOW_START.isoformat(),
        "window_end_exclusive": DEV_WINDOW_END.isoformat(),
        "policies": policies,
        "decision_timeframes": ["H1", "M15", "M1"],
        "one_execution_max_per_m15_setup": True,
        "chronological_portfolio_max3": True,
        "outcome_used_for_selection": False,
        "future_used_for_geometry": False,
        "historical_research": True,
        "automatic_policy_promotion": False,
        "trader_certified": False,
        "live_authorized": False,
        "real_capital_authorized": False,
    }


def write_market(
    report: dict[str, Any],
    trades: tuple[V53RearmTrade, ...],
    output: Path,
) -> None:
    output.mkdir(parents=True, exist_ok=True)
    symbol = str(report["symbol"]).lower()
    (output / f"capitalizer-{symbol}-v53-rearm-report.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    with (output / f"capitalizer-{symbol}-v53-rearm-trades.jsonl").open(
        "w",
        encoding="utf-8",
    ) as handle:
        for item in trades:
            handle.write(json.dumps(asdict(item), sort_keys=True) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)

    market = sub.add_parser("market")
    market.add_argument("rearm_root", type=Path)
    market.add_argument("m1_root", type=Path)
    market.add_argument("output", type=Path)

    matrix = sub.add_parser("matrix")
    matrix.add_argument("input_root", type=Path)
    matrix.add_argument("baseline_root", type=Path)
    matrix.add_argument("output", type=Path)

    args = parser.parse_args()
    if args.command == "market":
        report, trades = build_market(
            rearm_root=args.rearm_root,
            m1_root=args.m1_root,
        )
        write_market(report, trades, args.output)
        print(json.dumps(report, sort_keys=True))
        return

    result = build_matrix(args.input_root, baseline_root=args.baseline_root)
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / "capitalizer-v53-rearm-economic-matrix.json").write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
