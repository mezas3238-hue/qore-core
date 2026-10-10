"""V54 structural partial + causal H1 runner lifecycle lab.

This lab isolates lifecycle on the frozen V50-G Cognitive-Geometry population.
Admission, H1/M15/M1 source opportunity, entry, execution stop and T1 are unchanged.

Policies:
- FULL_T1_CONTROL: frozen V50-G full exit at T1.
- PARTIAL50_STRUCTURAL_T2_BE: when a causal runner already exists at decision time,
  realize 50% at T1, move the remaining 50% stop to entry after the completed T1 bar,
  and target the exact frozen H1 runner. No future-derived T2 and no stop widening.
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
from qore.infrastructure.trader_lab.capitalizer_v49_development_economics import (
    V49EconomicTrade,
)
from qore.infrastructure.trader_lab.capitalizer_v50_cognitive_geometry_economics import (
    COGNITIVE_GEOMETRY_ALLOWED,
    COST_STRESS_R,
    _session_bars,
)
from qore.infrastructure.trader_lab.capitalizer_v50_cognitive_geometry_economics import (
    _replay as replay_full_t1,
)
from qore.infrastructure.trader_lab.capitalizer_v50_cognitive_geometry_specialist import (
    V50GeometryDecision,
    V50GeometryProposal,
    propose_v50_geometry,
)
from qore.infrastructure.trader_lab.capitalizer_v50_cognitive_opportunity import (
    build_v50_cognitive_snapshot,
)
from qore.infrastructure.trader_lab.capitalizer_v51_multi_era_repair import (
    _metrics as v51_metrics,
)

IDENTITY = "QORE_CAPITALIZER_V54_STRUCTURAL_PARTIAL_RUNNER"
MATRIX_IDENTITY = "QORE_CAPITALIZER_V54_STRUCTURAL_PARTIAL_RUNNER_MATRIX"
CONTROL = "FULL_T1_CONTROL"
TREATMENT = "PARTIAL50_STRUCTURAL_T2_BE"
POLICIES = (CONTROL, TREATMENT)


@dataclass(frozen=True, slots=True)
class V54LifecycleTrade:
    policy: str
    symbol: str
    session: str
    operating_date: str
    h1_state_from: str
    m15_setup_confirmed_at: str
    entry_at: str
    exit_at: str
    entry_price: str
    stop_price: str
    t1_price: str
    t1_reward_r: str
    runner_price: str | None
    runner_reward_r: str | None
    realized_gross_r: str
    exit_reason: str
    m1_bars_held: int
    trigger_family: str
    h1_basis: str
    runner_available_at_entry: bool
    same_bar_stop_t1_ambiguity: bool = False
    same_bar_t1_runner_ambiguity: bool = False
    same_bar_be_runner_ambiguity: bool = False
    outcome_used_for_selection: bool = False
    future_target_used: bool = False
    post_entry_stop_widening: bool = False
    recovery_sizing_used: bool = False

    def __post_init__(self) -> None:
        if self.policy not in POLICIES:
            raise ValueError("unexpected V54 lifecycle policy")
        if (
            self.outcome_used_for_selection
            or self.future_target_used
            or self.post_entry_stop_widening
            or self.recovery_sizing_used
        ):
            raise ValueError("V54 lifecycle crossed frozen causal boundary")


def _load_opportunities(root: Path) -> tuple[V49Opportunity, ...]:
    paths = sorted(root.rglob("capitalizer-*-v49-hf-capacity-opportunities.jsonl"))
    if len(paths) != 1:
        raise ValueError("V54 lifecycle market requires one V49 opportunity ledger")
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


def _touch(
    bar: CapitalizerM1Bar,
    *,
    price: Decimal,
    is_long: bool,
    upper: bool,
) -> bool:
    if is_long:
        return bar.high >= price if upper else bar.low <= price
    return bar.low <= price if upper else bar.high >= price


def _treatment_replay(
    *,
    opportunity: V49Opportunity,
    bars: tuple[CapitalizerM1Bar, ...],
    geometry: V50GeometryProposal,
) -> V54LifecycleTrade | None:
    if (
        geometry.decision is not V50GeometryDecision.READY
        or geometry.stop_price is None
        or geometry.t1 is None
        or geometry.t1_reward_r is None
    ):
        raise ValueError("V54 treatment requires READY V50 geometry")

    entry_at = datetime.fromisoformat(opportunity.m1_trigger_confirmed_at)
    entry = Decimal(opportunity.decision_reference_price)
    stop = geometry.stop_price
    t1 = geometry.t1.price
    runner = None if geometry.runner is None else geometry.runner.price
    runner_r = geometry.runner_reward_r
    risk = abs(entry - stop)
    if risk <= 0:
        raise ValueError("V54 treatment requires positive risk")

    window = _session_bars(
        bars,
        entry_at=entry_at,
        expected_session=opportunity.session,
    )
    if not window:
        return None

    is_long = opportunity.h1_state_direction == "BULLISH"
    t1_r = geometry.t1_reward_r
    held = 0
    stop_t1_ambiguity = False
    t1_runner_ambiguity = False
    be_runner_ambiguity = False
    t1_reached = False
    realized = Decimal("0")

    for bar in window:
        held += 1

        if not t1_reached:
            stop_hit = _touch(bar, price=stop, is_long=is_long, upper=False)
            t1_hit = _touch(bar, price=t1, is_long=is_long, upper=True)
            if stop_hit:
                stop_t1_ambiguity = t1_hit
                realized = Decimal("-1")
                exit_reason = "STOP"
                exit_at = bar.closed_at
                break
            if t1_hit:
                if runner is None or runner_r is None:
                    realized = t1_r
                    exit_reason = "T1_FULL_NO_RUNNER"
                    exit_at = bar.closed_at
                    break

                runner_same_bar = _touch(
                    bar,
                    price=runner,
                    is_long=is_long,
                    upper=True,
                )
                if runner_same_bar:
                    # Runner activates only after the completed T1 bar. Cap ambiguous
                    # same-bar credit at the already-earned full T1 control outcome.
                    t1_runner_ambiguity = True
                    realized = t1_r
                    exit_reason = "T1_RUNNER_SAME_BAR_CAPPED_AT_T1"
                    exit_at = bar.closed_at
                    break

                realized = t1_r / Decimal("2")
                t1_reached = True
                continue
        else:
            if runner is None or runner_r is None:
                raise ValueError("V54 runner state missing frozen runner")
            be_hit = _touch(bar, price=entry, is_long=is_long, upper=False)
            runner_hit = _touch(bar, price=runner, is_long=is_long, upper=True)
            if be_hit:
                be_runner_ambiguity = runner_hit
                exit_reason = (
                    "RUNNER_BE_FIRST_AMBIGUOUS"
                    if runner_hit
                    else "RUNNER_BREAK_EVEN"
                )
                exit_at = bar.closed_at
                break
            if runner_hit:
                realized += runner_r / Decimal("2")
                exit_reason = "RUNNER_TARGET"
                exit_at = bar.closed_at
                break
    else:
        last = window[-1]
        if not t1_reached:
            delta = last.close - entry if is_long else entry - last.close
            realized = delta / risk
            exit_reason = "SESSION_EXIT_BEFORE_T1"
        else:
            delta = last.close - entry if is_long else entry - last.close
            runner_leg_r = max(Decimal("0"), delta / risk)
            realized += runner_leg_r / Decimal("2")
            exit_reason = "RUNNER_SESSION_EXIT"
        exit_at = last.closed_at

    return V54LifecycleTrade(
        policy=TREATMENT,
        symbol=opportunity.symbol,
        session=opportunity.session,
        operating_date=opportunity.operating_date,
        h1_state_from=opportunity.h1_state_from,
        m15_setup_confirmed_at=opportunity.m15_setup_confirmed_at,
        entry_at=entry_at.isoformat(),
        exit_at=exit_at.isoformat(),
        entry_price=str(entry),
        stop_price=str(stop),
        t1_price=str(t1),
        t1_reward_r=str(t1_r),
        runner_price=None if runner is None else str(runner),
        runner_reward_r=None if runner_r is None else str(runner_r),
        realized_gross_r=str(realized),
        exit_reason=exit_reason,
        m1_bars_held=held,
        trigger_family=opportunity.m1_trigger_family,
        h1_basis=opportunity.h1_state_basis,
        runner_available_at_entry=runner is not None,
        same_bar_stop_t1_ambiguity=stop_t1_ambiguity,
        same_bar_t1_runner_ambiguity=t1_runner_ambiguity,
        same_bar_be_runner_ambiguity=be_runner_ambiguity,
    )


def _control_record(
    *,
    opportunity: V49Opportunity,
    geometry: V50GeometryProposal,
    replay: Any,
) -> V54LifecycleTrade:
    if geometry.t1 is None or geometry.t1_reward_r is None:
        raise ValueError("V54 control missing T1")
    return V54LifecycleTrade(
        policy=CONTROL,
        symbol=replay.symbol,
        session=replay.session,
        operating_date=replay.operating_date,
        h1_state_from=opportunity.h1_state_from,
        m15_setup_confirmed_at=opportunity.m15_setup_confirmed_at,
        entry_at=replay.entry_at,
        exit_at=replay.exit_at,
        entry_price=replay.entry_price,
        stop_price=replay.stop_price,
        t1_price=str(geometry.t1.price),
        t1_reward_r=str(geometry.t1_reward_r),
        runner_price=None if geometry.runner is None else str(geometry.runner.price),
        runner_reward_r=(
            None
            if geometry.runner_reward_r is None
            else str(geometry.runner_reward_r)
        ),
        realized_gross_r=replay.realized_gross_r,
        exit_reason=replay.exit_reason,
        m1_bars_held=replay.m1_bars_held,
        trigger_family=replay.trigger_family,
        h1_basis=replay.h1_basis,
        runner_available_at_entry=geometry.runner is not None,
        same_bar_stop_t1_ambiguity=replay.same_bar_stop_target_ambiguity,
    )


def build_market(
    *,
    capacity_root: Path,
    m1_root: Path,
) -> tuple[dict[str, Any], tuple[V54LifecycleTrade, ...]]:
    opportunities = _load_opportunities(capacity_root)
    if not opportunities:
        raise ValueError("V54 lifecycle requires source opportunities")
    symbol = opportunities[0].symbol
    session = opportunities[0].session

    bars = tuple(
        bar
        for bar in iter_cibo_m1(m1_root)
        if DEV_WINDOW_START - DEFAULT_LOOKBACK <= bar.opened_at < DEV_WINDOW_END
    )
    if not bars or any(item.symbol != symbol for item in bars):
        raise ValueError("V54 lifecycle M1 source mismatch")
    h1 = _aggregate(bars, minutes=60)

    rows: list[V54LifecycleTrade] = []
    counters: Counter[str] = Counter()

    for opportunity in opportunities:
        snapshot = build_v50_cognitive_snapshot(
            opportunity,
            m1_bars=bars,
            h1_bars=h1,
            experience_memory=CapitalizerExperienceMemory(),
            metacognitive_readiness=CapitalizerEpistemicReadiness.WELL_SUPPORTED,
        )
        geometry = propose_v50_geometry(snapshot)
        if geometry.decision is not V50GeometryDecision.READY:
            continue
        if (
            geometry.stop_price is None
            or geometry.t1 is None
            or geometry.t1_reward_r is None
        ):
            raise ValueError("V54 READY geometry missing frozen stop/T1 payload")
        if snapshot.cognitive.disposition not in COGNITIVE_GEOMETRY_ALLOWED:
            continue

        control = replay_full_t1(
            policy="COGNITIVE_GEOMETRY",
            opportunity=opportunity,
            bars=bars,
            stop=geometry.stop_price,
            target=geometry.t1.price,
            disposition=snapshot.cognitive.disposition,
        )
        treatment = _treatment_replay(
            opportunity=opportunity,
            bars=bars,
            geometry=geometry,
        )
        if control is None or treatment is None:
            counters["MISSING_SESSION_REPLAY"] += 1
            continue
        rows.append(
            _control_record(
                opportunity=opportunity,
                geometry=geometry,
                replay=control,
            )
        )
        rows.append(treatment)
        counters["PAIRED_CANDIDATES"] += 1
        counters["RUNNER_AVAILABLE"] += geometry.runner is not None

    return {
        "identity": IDENTITY,
        "symbol": symbol,
        "session": session,
        "source_opportunities": len(opportunities),
        "paired_candidates": counters["PAIRED_CANDIDATES"],
        "runner_available_at_entry": counters["RUNNER_AVAILABLE"],
        "missing_session_replay": counters["MISSING_SESSION_REPLAY"],
        "decision_timeframes": ["H1", "M15", "M1"],
        "same_admission_population": True,
        "same_entry": True,
        "same_initial_stop": True,
        "same_t1": True,
        "outcome_used_for_selection": False,
        "future_target_used": False,
        "post_entry_stop_widening": False,
        "recovery_sizing_used": False,
        "historical_research": True,
        "automatic_policy_promotion": False,
        "certification_authority": False,
        "live_authorized": False,
        "real_capital_authorized": False,
    }, tuple(rows)


def _portfolio(
    rows: tuple[V54LifecycleTrade, ...],
    *,
    policy: str,
) -> tuple[V54LifecycleTrade, ...]:
    grouped: dict[tuple[str, str], list[V54LifecycleTrade]] = defaultdict(list)
    for item in rows:
        if item.policy == policy:
            grouped[(item.session, item.operating_date)].append(item)
    selected: list[V54LifecycleTrade] = []
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


def _as_v49(item: V54LifecycleTrade) -> V49EconomicTrade:
    direction = (
        "LONG"
        if Decimal(item.stop_price) < Decimal(item.entry_price)
        else "SHORT"
    )
    return V49EconomicTrade(
        symbol=item.symbol,
        session=item.session,
        operating_date=item.operating_date,
        ordinal_candidate_at=item.entry_at,
        direction=direction,
        entry_at=item.entry_at,
        exit_at=item.exit_at,
        entry_price=item.entry_price,
        stop_price=item.stop_price,
        target_price=item.t1_price,
        planned_reward_r=item.t1_reward_r,
        realized_gross_r=item.realized_gross_r,
        exit_reason=item.exit_reason,
        m1_bars_held=item.m1_bars_held,
        trigger_family=item.trigger_family,
        h1_state_basis=item.h1_basis,
        same_bar_stop_target_ambiguity=item.same_bar_stop_t1_ambiguity,
    )


def _metrics(
    rows: tuple[V54LifecycleTrade, ...],
    *,
    cost_r: Decimal = Decimal("0"),
) -> dict[str, Any]:
    return v51_metrics(
        tuple(_as_v49(item) for item in rows),
        cost_r=cost_r,
    )


def _key(item: V54LifecycleTrade) -> tuple[str, str, str, str, str, str]:
    return (
        item.symbol,
        item.session,
        item.operating_date,
        item.h1_state_from,
        item.m15_setup_confirmed_at,
        item.entry_at,
    )


def _preservation(
    control: tuple[V54LifecycleTrade, ...],
    treatment: tuple[V54LifecycleTrade, ...],
) -> dict[str, Any]:
    treatment_by_key = {_key(item): item for item in treatment}
    winners = tuple(
        item for item in control if Decimal(item.realized_gross_r) > 0
    )
    losses = tuple(
        item for item in control if Decimal(item.realized_gross_r) < 0
    )
    preserved = tuple(
        item
        for item in winners
        if (
            (candidate := treatment_by_key.get(_key(item))) is not None
            and Decimal(candidate.realized_gross_r) > 0
        )
    )
    winner_r = sum(
        (Decimal(item.realized_gross_r) for item in winners),
        Decimal("0"),
    )
    treatment_winner_r = sum(
        (
            Decimal(treatment_by_key[_key(item)].realized_gross_r)
            for item in preserved
        ),
        Decimal("0"),
    )
    recalled_losses = tuple(
        item
        for item in losses
        if (
            (candidate := treatment_by_key.get(_key(item))) is None
            or Decimal(candidate.realized_gross_r) >= 0
        )
    )
    return {
        "same_selected_population": {
            _key(item) for item in control
        } == {
            _key(item) for item in treatment
        },
        "winner_count_preservation": (
            None
            if not winners
            else str(Decimal(len(preserved)) / Decimal(len(winners)))
        ),
        "winner_r_preservation": (
            None if winner_r == 0 else str(treatment_winner_r / winner_r)
        ),
        "loss_recall": (
            None
            if not losses
            else str(Decimal(len(recalled_losses)) / Decimal(len(losses)))
        ),
    }


def _exit_counts(rows: tuple[V54LifecycleTrade, ...]) -> dict[str, int]:
    return dict(sorted(Counter(item.exit_reason for item in rows).items()))


def _load_rows(root: Path) -> tuple[V54LifecycleTrade, ...]:
    paths = sorted(root.rglob("capitalizer-*-v54-lifecycle-trades.jsonl"))
    if len(paths) != 9:
        raise ValueError("V54 lifecycle matrix requires nine trade ledgers")
    rows: list[V54LifecycleTrade] = []
    for path in paths:
        with path.open(encoding="utf-8") as handle:
            for line in handle:
                if line.strip():
                    rows.append(V54LifecycleTrade(**json.loads(line)))
    return tuple(rows)


def build_matrix(root: Path) -> dict[str, Any]:
    all_rows = _load_rows(root)
    control = _portfolio(all_rows, policy=CONTROL)
    treatment = _portfolio(all_rows, policy=TREATMENT)
    if {_key(item) for item in control} != {_key(item) for item in treatment}:
        raise ValueError("V54 A/B portfolio population mismatch")

    policies: dict[str, Any] = {}
    for policy, selected in ((CONTROL, control), (TREATMENT, treatment)):
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
            "by_calendar_year": {
                year: _metrics(
                    tuple(
                        item
                        for item in selected
                        if datetime.fromisoformat(item.entry_at).year == int(year)
                    )
                )
                for year in sorted(
                    {
                        str(datetime.fromisoformat(item.entry_at).year)
                        for item in selected
                    }
                )
            },
            "exit_counts": _exit_counts(selected),
            "runner_available_at_entry": sum(
                item.runner_available_at_entry for item in selected
            ),
            "same_bar_stop_t1_ambiguities": sum(
                item.same_bar_stop_t1_ambiguity for item in selected
            ),
            "same_bar_t1_runner_ambiguities": sum(
                item.same_bar_t1_runner_ambiguity for item in selected
            ),
            "same_bar_be_runner_ambiguities": sum(
                item.same_bar_be_runner_ambiguity for item in selected
            ),
        }

    return {
        "identity": MATRIX_IDENTITY,
        "policies": policies,
        "preservation_treatment_vs_control": _preservation(control, treatment),
        "decision_timeframes": ["H1", "M15", "M1"],
        "same_admission_population": True,
        "same_entry": True,
        "same_initial_stop": True,
        "same_t1": True,
        "outcome_used_for_selection": False,
        "future_target_used": False,
        "post_entry_stop_widening": False,
        "recovery_sizing_used": False,
        "historical_research": True,
        "automatic_policy_promotion": False,
        "certification_authority": False,
        "live_authorized": False,
        "real_capital_authorized": False,
    }


def write_market(
    report: dict[str, Any],
    rows: tuple[V54LifecycleTrade, ...],
    output: Path,
) -> None:
    output.mkdir(parents=True, exist_ok=True)
    symbol = str(report["symbol"]).lower()
    (output / f"capitalizer-{symbol}-v54-lifecycle-report.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    with (output / f"capitalizer-{symbol}-v54-lifecycle-trades.jsonl").open(
        "w", encoding="utf-8"
    ) as handle:
        for item in rows:
            handle.write(json.dumps(asdict(item), sort_keys=True) + "\n")


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
        report, rows = build_market(
            capacity_root=args.capacity_root,
            m1_root=args.m1_root,
        )
        write_market(report, rows, args.output)
        print(json.dumps(report, sort_keys=True))
        return

    result = build_matrix(args.input_root)
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / "capitalizer-v54-structural-partial-runner-matrix.json").write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
