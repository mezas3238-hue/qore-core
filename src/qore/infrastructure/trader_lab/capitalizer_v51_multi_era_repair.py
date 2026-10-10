"""V51 multi-era repair laboratory for the H1 -> M15 -> M1 Capitalizer Scalper.

Owner research override permits all historical windows to be used for diagnosis/repair.
This lab keeps certification thresholds unchanged and treats every opened historical era as
consumed research evidence.

The lab compares, on the same source-complete opportunity stream:
- V49_BASELINE: original M15 stop + nearest causal H1 witness;
- GEOMETRY_ONLY: V50 M1 execution invalidation + causal target ladder;
- COGNITIVE_GEOMETRY: the same geometry after V50 decision-time cognition.

No outcome participates in admission, geometry, MAX3 selection or policy choice.
"""

from __future__ import annotations

import argparse
import json
import math
from collections import Counter, defaultdict
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
from qore.infrastructure.trader_lab.capitalizer_experience_memory import (
    CapitalizerExperienceMemory,
)
from qore.infrastructure.trader_lab.capitalizer_generic_scalp_census_v48 import _aggregate
from qore.infrastructure.trader_lab.capitalizer_high_frequency_capacity_census_v49 import (
    DEFAULT_LOOKBACK,
)
from qore.infrastructure.trader_lab.capitalizer_high_frequency_trader_v49 import (
    materialize_trade_intent,
)
from qore.infrastructure.trader_lab.capitalizer_metacognition_v2 import (
    CapitalizerEpistemicReadiness,
)
from qore.infrastructure.trader_lab.capitalizer_v49_development_economics import (
    V49EconomicTrade,
)
from qore.infrastructure.trader_lab.capitalizer_v49_development_economics import (
    _replay_one as replay_v49,
)
from qore.infrastructure.trader_lab.capitalizer_v49_development_economics import (
    _session_bars as v49_session_bars,
)
from qore.infrastructure.trader_lab.capitalizer_v50_cognitive_geometry_economics import (
    COGNITIVE_GEOMETRY_ALLOWED,
    COST_STRESS_R,
    V50GTrade,
    _load_opportunities,
)
from qore.infrastructure.trader_lab.capitalizer_v50_cognitive_geometry_economics import (
    _portfolio as v50_portfolio,
)
from qore.infrastructure.trader_lab.capitalizer_v50_cognitive_geometry_economics import (
    _replay as replay_v50,
)
from qore.infrastructure.trader_lab.capitalizer_v50_cognitive_geometry_specialist import (
    V50GeometryDecision,
    propose_v50_geometry,
)
from qore.infrastructure.trader_lab.capitalizer_v50_cognitive_opportunity import (
    build_v50_cognitive_snapshot,
)

IDENTITY = "QORE_CAPITALIZER_V51_MULTI_ERA_REPAIR_LAB"
MATRIX_IDENTITY = "QORE_CAPITALIZER_V51_MULTI_ERA_REPAIR_MATRIX"
POLICIES = ("V49_BASELINE", "GEOMETRY_ONLY", "COGNITIVE_GEOMETRY")


@dataclass(frozen=True, slots=True)
class V51MarketReport:
    identity: str
    era: str
    symbol: str
    session: str
    window_start: str
    window_end_exclusive: str
    context_lookback_start: str
    source_opportunities: int
    baseline_trade_rows: int
    geometry_trade_rows: int
    geometry_decisions: tuple[tuple[str, int], ...]
    geometry_reasons: tuple[tuple[str, int], ...]
    cognitive_dispositions: tuple[tuple[str, int], ...]
    historical_research: bool = True
    outcome_used_for_admission: bool = False
    outcome_aware_selection: bool = False
    daily_used: bool = False
    h4_used: bool = False
    certification_authority: bool = False
    live_authorized: bool = False
    real_capital_authorized: bool = False

    def __post_init__(self) -> None:
        if self.identity != IDENTITY:
            raise ValueError("unexpected V51 identity")
        if not self.era:
            raise ValueError("V51 era must be non-empty")
        if not self.historical_research:
            raise ValueError("V51 is historical research only")
        if (
            self.outcome_used_for_admission
            or self.outcome_aware_selection
            or self.daily_used
            or self.h4_used
            or self.certification_authority
            or self.live_authorized
            or self.real_capital_authorized
        ):
            raise ValueError("V51 crossed its research boundary")


Trade = V49EconomicTrade | V50GTrade


def _capacity_metadata(root: Path) -> dict[str, Any]:
    paths = sorted(root.rglob("capitalizer-*-v49-hf-capacity.json"))
    if len(paths) != 1:
        raise ValueError("V51 market replay requires one V49 capacity report")
    return json.loads(paths[0].read_text(encoding="utf-8"))


def _load_window_bars(
    root: Path,
    *,
    window_start: datetime,
    window_end: datetime,
) -> tuple[CapitalizerM1Bar, ...]:
    lookback_start = window_start - DEFAULT_LOOKBACK
    return tuple(
        bar
        for bar in iter_cibo_m1(root)
        if lookback_start <= bar.opened_at < window_end
    )


def build_market(
    *,
    capacity_root: Path,
    m1_root: Path,
    era: str,
) -> tuple[V51MarketReport, tuple[V49EconomicTrade, ...], tuple[V50GTrade, ...]]:
    meta = _capacity_metadata(capacity_root)
    window_start = datetime.fromisoformat(str(meta["window_start"]))
    window_end = datetime.fromisoformat(str(meta["window_end_exclusive"]))
    opportunities = _load_opportunities(capacity_root)
    if not opportunities:
        raise ValueError("V51 requires source-complete opportunities")

    symbol = opportunities[0].symbol
    session = opportunities[0].session
    if any(item.symbol != symbol or item.session != session for item in opportunities):
        raise ValueError("V51 market input must contain one symbol/session")

    bars = _load_window_bars(
        m1_root,
        window_start=window_start,
        window_end=window_end,
    )
    if not bars or any(bar.symbol != symbol for bar in bars):
        raise ValueError("V51 retained M1 market mismatch")
    opened = tuple(item.opened_at for item in bars)
    h1 = _aggregate(bars, minutes=60)

    baseline: list[V49EconomicTrade] = []
    geometry_rows: list[V50GTrade] = []
    geometry_counts: Counter[str] = Counter()
    geometry_reasons: Counter[str] = Counter()
    dispositions: Counter[str] = Counter()

    for opportunity in opportunities:
        intent = materialize_trade_intent(opportunity)
        base_window = v49_session_bars(bars, opened, intent=intent)
        base_trade = replay_v49(base_window, intent)
        if base_trade is not None:
            baseline.append(base_trade)

        snapshot = build_v50_cognitive_snapshot(
            opportunity,
            m1_bars=bars,
            h1_bars=h1,
            experience_memory=CapitalizerExperienceMemory(),
            metacognitive_readiness=CapitalizerEpistemicReadiness.WELL_SUPPORTED,
        )
        disposition = snapshot.cognitive.disposition
        dispositions[disposition.value] += 1
        geometry = propose_v50_geometry(snapshot)
        geometry_counts[geometry.decision.value] += 1
        geometry_reasons.update(geometry.reasons)
        if geometry.decision is not V50GeometryDecision.READY:
            continue
        if geometry.stop_price is None or geometry.t1 is None:
            raise ValueError("V51 READY geometry missing stop/target")

        for policy in ("GEOMETRY_ONLY", "COGNITIVE_GEOMETRY"):
            if (
                policy == "COGNITIVE_GEOMETRY"
                and disposition not in COGNITIVE_GEOMETRY_ALLOWED
            ):
                continue
            trade = replay_v50(
                policy=policy,
                opportunity=opportunity,
                bars=bars,
                stop=geometry.stop_price,
                target=geometry.t1.price,
                disposition=disposition,
            )
            if trade is not None:
                geometry_rows.append(trade)

    report = V51MarketReport(
        identity=IDENTITY,
        era=era,
        symbol=symbol,
        session=session,
        window_start=window_start.isoformat(),
        window_end_exclusive=window_end.isoformat(),
        context_lookback_start=(window_start - DEFAULT_LOOKBACK).isoformat(),
        source_opportunities=len(opportunities),
        baseline_trade_rows=len(baseline),
        geometry_trade_rows=len(geometry_rows),
        geometry_decisions=tuple(sorted(geometry_counts.items())),
        geometry_reasons=tuple(sorted(geometry_reasons.items())),
        cognitive_dispositions=tuple(sorted(dispositions.items())),
    )
    return report, tuple(baseline), tuple(geometry_rows)


def _portfolio_baseline(
    trades: tuple[V49EconomicTrade, ...],
) -> tuple[V49EconomicTrade, ...]:
    grouped: dict[tuple[str, str], list[V49EconomicTrade]] = defaultdict(list)
    for trade in trades:
        grouped[(trade.session, trade.operating_date)].append(trade)
    selected: list[V49EconomicTrade] = []
    for key in sorted(grouped):
        rows = sorted(
            grouped[key],
            key=lambda item: (
                datetime.fromisoformat(item.entry_at),
                item.symbol,
                item.trigger_family,
            ),
        )
        selected.extend(rows[:3])
    return tuple(
        sorted(
            selected,
            key=lambda item: (
                datetime.fromisoformat(item.entry_at),
                item.symbol,
            ),
        )
    )


def _values(rows: tuple[Trade, ...], *, cost_r: Decimal = Decimal("0")) -> tuple[Decimal, ...]:
    return tuple(Decimal(item.realized_gross_r) - cost_r for item in rows)


def _risk_adjusted(
    rows: tuple[Trade, ...],
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
            "zero_trade_days_included": False,
            "annualization_factor": 252,
            "sharpe_annualized": None,
            "sortino_annualized": None,
        }
    mean = fmean(values)
    sigma = pstdev(values) if len(values) > 1 else 0.0
    downside = math.sqrt(fmean([min(0.0, value) ** 2 for value in values]))
    annual = math.sqrt(252.0)
    return {
        "daily_observations": len(values),
        "zero_trade_days_included": False,
        "annualization_factor": 252,
        "risk_free_assumption_r": "0",
        "mar_r": "0",
        "sharpe_annualized": None if sigma == 0 else str(mean / sigma * annual),
        "sortino_annualized": None if downside == 0 else str(mean / downside * annual),
    }


def _metrics(rows: tuple[Trade, ...], *, cost_r: Decimal = Decimal("0")) -> dict[str, Any]:
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
    values = _values(ordered, cost_r=cost_r)
    wins_v = tuple(value for value in values if value > 0)
    losses_v = tuple(value for value in values if value < 0)
    gp = sum(wins_v, Decimal("0"))
    gl = -sum(losses_v, Decimal("0"))
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

    avg_win = None if not wins_v else gp / Decimal(len(wins_v))
    avg_loss = None if not losses_v else gl / Decimal(len(losses_v))
    payoff = (
        None
        if avg_win is None or avg_loss is None or avg_loss == 0
        else avg_win / avg_loss
    )
    return {
        "trades": len(rows),
        "wins": len(wins_v),
        "losses": len(losses_v),
        "win_rate": str(Decimal(len(wins_v)) / Decimal(len(rows))),
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


def _key(item: Trade) -> tuple[str, str, str, str, str]:
    return (
        item.session,
        item.operating_date,
        item.symbol,
        item.entry_at,
        item.trigger_family,
    )


def _preservation(
    baseline: tuple[V49EconomicTrade, ...],
    candidate: tuple[V50GTrade, ...],
) -> dict[str, Any]:
    candidate_by_key = {_key(item): item for item in candidate}
    candidate_keys = set(candidate_by_key)
    winners = tuple(
        item for item in baseline if Decimal(item.realized_gross_r) > 0
    )
    winner_r = sum((Decimal(item.realized_gross_r) for item in winners), Decimal("0"))
    preserved = tuple(
        item
        for item in winners
        if _key(item) in candidate_by_key
        and Decimal(candidate_by_key[_key(item)].realized_gross_r) > 0
    )
    preserved_candidate_r = sum(
        (
            Decimal(candidate_by_key[_key(item)].realized_gross_r)
            for item in preserved
        ),
        Decimal("0"),
    )
    stops = tuple(item for item in baseline if item.exit_reason == "STOP")
    avoided_stops = tuple(
        item
        for item in stops
        if _key(item) not in candidate_keys
        or Decimal(candidate_by_key[_key(item)].realized_gross_r) >= 0
    )
    return {
        "density_retention": (
            None
            if not baseline
            else str(Decimal(len(candidate)) / Decimal(len(baseline)))
        ),
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


def _certification_diagnostic(metrics: dict[str, Any]) -> dict[str, Any]:
    pf = None if metrics["profit_factor"] is None else Decimal(metrics["profit_factor"])
    expectancy = None if metrics["expectancy_r"] is None else Decimal(metrics["expectancy_r"])
    dd = Decimal(metrics["max_drawdown_r"])
    payoff = None if metrics["payoff_ratio"] is None else Decimal(metrics["payoff_ratio"])
    risk = metrics["risk_adjusted"]
    sharpe = (
        None
        if risk["sharpe_annualized"] is None
        else Decimal(risk["sharpe_annualized"])
    )
    sortino = (
        None
        if risk["sortino_annualized"] is None
        else Decimal(risk["sortino_annualized"])
    )
    return {
        "pf_ge_1_50": pf is not None and pf >= Decimal("1.50"),
        "expectancy_positive": expectancy is not None and expectancy > 0,
        "dd_le_10r": dd <= Decimal("10"),
        "payoff_ge_1_20": payoff is not None and payoff >= Decimal("1.20"),
        "sharpe_ge_1_50": sharpe is not None and sharpe >= Decimal("1.50"),
        "sortino_ge_2_00": sortino is not None and sortino >= Decimal("2.00"),
        "research_only_not_certification": True,
    }


def build_matrix(root: Path, *, era: str) -> dict[str, Any]:
    report_paths = sorted(root.rglob("capitalizer-*-v51-market-report.json"))
    baseline_paths = sorted(root.rglob("capitalizer-*-v51-baseline.jsonl"))
    geometry_paths = sorted(root.rglob("capitalizer-*-v51-geometry.jsonl"))
    if len(report_paths) != 9 or len(baseline_paths) != 9 or len(geometry_paths) != 9:
        raise ValueError("V51 matrix requires nine market artifacts")

    reports = tuple(json.loads(path.read_text(encoding="utf-8")) for path in report_paths)
    baseline_rows: list[V49EconomicTrade] = []
    geometry_rows: list[V50GTrade] = []
    for path in baseline_paths:
        with path.open(encoding="utf-8") as handle:
            for line in handle:
                if line.strip():
                    baseline_rows.append(V49EconomicTrade(**json.loads(line)))
    for path in geometry_paths:
        with path.open(encoding="utf-8") as handle:
            for line in handle:
                if line.strip():
                    geometry_rows.append(V50GTrade(**json.loads(line)))

    baseline = _portfolio_baseline(tuple(baseline_rows))
    policy_rows: dict[str, tuple[Trade, ...]] = {"V49_BASELINE": baseline}
    for policy in ("GEOMETRY_ONLY", "COGNITIVE_GEOMETRY"):
        policy_rows[policy] = v50_portfolio(tuple(geometry_rows), policy=policy)

    policies: dict[str, Any] = {}
    for policy, selected in policy_rows.items():
        gross = _metrics(selected)
        block: dict[str, Any] = {
            "gross": gross,
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
            "certification_diagnostic": _certification_diagnostic(gross),
        }
        if policy != "V49_BASELINE":
            candidate = tuple(item for item in selected if isinstance(item, V50GTrade))
            block["preservation_vs_v49"] = _preservation(baseline, candidate)
        policies[policy] = block

    windows = {(row["window_start"], row["window_end_exclusive"]) for row in reports}
    if len(windows) != 1:
        raise ValueError("V51 market reports disagree on era window")
    window_start, window_end = next(iter(windows))
    geometry_decisions: Counter[str] = Counter()
    geometry_reasons: Counter[str] = Counter()
    for row in reports:
        geometry_decisions.update(dict(row["geometry_decisions"]))
        geometry_reasons.update(dict(row["geometry_reasons"]))

    return {
        "identity": MATRIX_IDENTITY,
        "era": era,
        "window_start": window_start,
        "window_end_exclusive": window_end,
        "decision_timeframes": ["H1", "M15", "M1"],
        "source_opportunities": sum(int(row["source_opportunities"]) for row in reports),
        "policies": policies,
        "geometry_decisions": dict(sorted(geometry_decisions.items())),
        "geometry_reasons": dict(sorted(geometry_reasons.items())),
        "historical_research": True,
        "all_historical_windows_authorized_for_repair": True,
        "outcome_used_for_admission": False,
        "outcome_aware_selection": False,
        "automatic_policy_promotion": False,
        "certification_authority": False,
        "final_independent_or_prospective_oos_still_required": True,
        "live_authorized": False,
        "real_capital_authorized": False,
    }


def write_market(
    report: V51MarketReport,
    baseline: tuple[V49EconomicTrade, ...],
    geometry: tuple[V50GTrade, ...],
    output: Path,
) -> None:
    output.mkdir(parents=True, exist_ok=True)
    symbol = report.symbol.lower()
    (output / f"capitalizer-{symbol}-v51-market-report.json").write_text(
        json.dumps(asdict(report), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    with (output / f"capitalizer-{symbol}-v51-baseline.jsonl").open(
        "w", encoding="utf-8"
    ) as handle:
        for item in baseline:
            handle.write(json.dumps(asdict(item), sort_keys=True) + "\n")
    with (output / f"capitalizer-{symbol}-v51-geometry.jsonl").open(
        "w", encoding="utf-8"
    ) as handle:
        for item in geometry:
            handle.write(json.dumps(asdict(item), sort_keys=True) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)

    market = sub.add_parser("market")
    market.add_argument("capacity_root", type=Path)
    market.add_argument("m1_root", type=Path)
    market.add_argument("output", type=Path)
    market.add_argument("--era", required=True)

    matrix = sub.add_parser("matrix")
    matrix.add_argument("input_root", type=Path)
    matrix.add_argument("output", type=Path)
    matrix.add_argument("--era", required=True)

    args = parser.parse_args()
    if args.command == "market":
        report, baseline, geometry = build_market(
            capacity_root=args.capacity_root,
            m1_root=args.m1_root,
            era=args.era,
        )
        write_market(report, baseline, geometry, args.output)
        print(json.dumps(asdict(report), sort_keys=True))
        return

    result = build_matrix(args.input_root, era=args.era)
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / "capitalizer-v51-multi-era-repair-matrix.json").write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
