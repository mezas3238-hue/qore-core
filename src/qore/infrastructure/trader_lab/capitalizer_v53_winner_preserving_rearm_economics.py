"""V53 winner-preserving V50-R economic replay.

V52 falsified simple admission filtering. V53 tests transformation instead:
preserve the parent H1/M15 thesis, allow V50-R to wait for a later source-valid M1 execution,
rebuild V50 stop/target geometry causally, and then re-run portfolio MAX3.

Winner preservation is measured by parent thesis, not by unchanged M1 entry timestamp.
"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from dataclasses import asdict, dataclass
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

from qore.infrastructure.trader_lab.capitalizer_cibo_m1_reader_v1 import (
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
from qore.infrastructure.trader_lab.capitalizer_v50_m1_rearm_capacity import (
    V50RearmAttempt,
)
from qore.infrastructure.trader_lab.capitalizer_v51_multi_era_repair import (
    _metrics as v51_metrics,
)

IDENTITY = "QORE_CAPITALIZER_V53_WINNER_PRESERVING_REARM_ECONOMICS"
MATRIX_IDENTITY = "QORE_CAPITALIZER_V53_WINNER_PRESERVING_REARM_MATRIX"


@dataclass(frozen=True, slots=True)
class V53TradeRecord:
    source_policy: str
    symbol: str
    session: str
    operating_date: str
    h1_state_from: str
    m15_setup_confirmed_at: str
    attempt_index: int
    direction: str
    entry_at: str
    exit_at: str
    entry_price: str
    stop_price: str
    target_price: str
    planned_reward_r: str
    realized_gross_r: str
    exit_reason: str
    m1_bars_held: int
    trigger_family: str
    h1_state_basis: str
    same_bar_stop_target_ambiguity: bool = False
    outcome_used_for_selection: bool = False
    stop_widened: bool = False
    recovery_sizing_used: bool = False

    def __post_init__(self) -> None:
        if self.source_policy not in {"V49_BASELINE", "V50_R_TRANSFORMED"}:
            raise ValueError("unexpected V53 source policy")
        if self.attempt_index < 1:
            raise ValueError("V53 attempt index must be >=1")
        if (
            self.outcome_used_for_selection
            or self.stop_widened
            or self.recovery_sizing_used
        ):
            raise ValueError("V53 crossed the frozen research boundary")


def _parent_key(item: V53TradeRecord) -> tuple[str, str, str, str, str]:
    return (
        item.symbol,
        item.session,
        item.operating_date,
        item.h1_state_from,
        item.m15_setup_confirmed_at,
    )


def _trade_key(
    symbol: str,
    entry_at: str,
    trigger_family: str,
) -> tuple[str, str, str]:
    return (symbol, entry_at, trigger_family)


def _load_opportunities(root: Path) -> tuple[V49Opportunity, ...]:
    paths = sorted(root.rglob("capitalizer-*-v49-hf-capacity-opportunities.jsonl"))
    if len(paths) != 1:
        raise ValueError("V53 market replay requires one V49 opportunity ledger")
    rows: list[V49Opportunity] = []
    with paths[0].open(encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                rows.append(V49Opportunity(**json.loads(line)))
    return tuple(rows)


def _load_baseline_trades(root: Path) -> tuple[V49EconomicTrade, ...]:
    paths = sorted(root.rglob("capitalizer-*-v49-development-economics-trades.jsonl"))
    if len(paths) != 1:
        raise ValueError("V53 market replay requires one V49 economic ledger")
    rows: list[V49EconomicTrade] = []
    with paths[0].open(encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                rows.append(V49EconomicTrade(**json.loads(line)))
    return tuple(rows)


def _load_attempts(root: Path) -> tuple[V50RearmAttempt, ...]:
    paths = sorted(root.rglob("capitalizer-*-v50-r-rearm-capacity-attempts.jsonl"))
    if len(paths) != 1:
        raise ValueError("V53 market replay requires one V50-R attempt ledger")
    rows: list[V50RearmAttempt] = []
    with paths[0].open(encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                rows.append(V50RearmAttempt(**json.loads(line)))
    return tuple(rows)


def _baseline_records(
    opportunities: tuple[V49Opportunity, ...],
    trades: tuple[V49EconomicTrade, ...],
) -> tuple[V53TradeRecord, ...]:
    lookup: dict[tuple[str, str, str], list[V49Opportunity]] = defaultdict(list)
    for item in opportunities:
        lookup[
            _trade_key(
                item.symbol,
                item.m1_trigger_confirmed_at,
                item.m1_trigger_family,
            )
        ].append(item)

    consumed_by_key: defaultdict[tuple[str, str, str], int] = defaultdict(int)
    result: list[V53TradeRecord] = []
    for trade in trades:
        key = _trade_key(trade.symbol, trade.entry_at, trade.trigger_family)
        matches = lookup.get(key, [])
        index = consumed_by_key[key]
        if index >= len(matches):
            raise ValueError("V53 baseline trade missing V49 parent opportunity")
        opportunity = matches[index]
        consumed_by_key[key] += 1
        result.append(
            V53TradeRecord(
                source_policy="V49_BASELINE",
                symbol=trade.symbol,
                session=trade.session,
                operating_date=trade.operating_date,
                h1_state_from=opportunity.h1_state_from,
                m15_setup_confirmed_at=opportunity.m15_setup_confirmed_at,
                attempt_index=1,
                direction=trade.direction,
                entry_at=trade.entry_at,
                exit_at=trade.exit_at,
                entry_price=trade.entry_price,
                stop_price=trade.stop_price,
                target_price=trade.target_price,
                planned_reward_r=trade.planned_reward_r,
                realized_gross_r=trade.realized_gross_r,
                exit_reason=trade.exit_reason,
                m1_bars_held=trade.m1_bars_held,
                trigger_family=trade.trigger_family,
                h1_state_basis=trade.h1_state_basis,
                same_bar_stop_target_ambiguity=(
                    trade.same_bar_stop_target_ambiguity
                ),
            )
        )
    return tuple(result)


def _direction(attempt: V50RearmAttempt) -> tuple[str, str]:
    decision = Decimal(attempt.decision_reference_price)
    protected = Decimal(attempt.m15_protected_swing_price)
    if protected < decision:
        return "BULLISH", "LONG"
    if protected > decision:
        return "BEARISH", "SHORT"
    raise ValueError("V53 cannot infer direction from zero thesis risk")


def _attempt_opportunity(attempt: V50RearmAttempt) -> tuple[V49Opportunity, str]:
    state_direction, trade_direction = _direction(attempt)
    return (
        V49Opportunity(
            symbol=attempt.symbol,
            session=attempt.session,
            operating_date=attempt.operating_date,
            h1_state_direction=state_direction,
            h1_state_from=attempt.h1_state_from,
            h1_state_until=attempt.h1_state_until,
            h1_state_basis=attempt.h1_state_basis,
            m15_setup_confirmed_at=attempt.m15_setup_confirmed_at,
            m15_protected_swing_price=attempt.m15_protected_swing_price,
            m1_trigger_confirmed_at=attempt.trigger_confirmed_at,
            m1_trigger_family=attempt.trigger_family,
            decision_reference_price=attempt.decision_reference_price,
            structural_target_witness_price=attempt.structural_target_witness_price,
        ),
        trade_direction,
    )


def build_market(
    *,
    capacity_root: Path,
    baseline_root: Path,
    rearm_root: Path,
    m1_root: Path,
) -> tuple[dict[str, Any], tuple[V53TradeRecord, ...], tuple[V53TradeRecord, ...]]:
    opportunities = _load_opportunities(capacity_root)
    baseline_trades = _load_baseline_trades(baseline_root)
    attempts = _load_attempts(rearm_root)
    if not opportunities:
        raise ValueError("V53 requires V49 opportunities")

    symbol = opportunities[0].symbol
    session = opportunities[0].session
    baseline = _baseline_records(opportunities, baseline_trades)

    bars = tuple(
        bar
        for bar in iter_cibo_m1(m1_root)
        if DEV_WINDOW_START - DEFAULT_LOOKBACK <= bar.opened_at < DEV_WINDOW_END
    )
    if not bars or any(item.symbol != symbol for item in bars):
        raise ValueError("V53 M1 source mismatch")
    h1 = _aggregate(bars, minutes=60)

    # V50-R is allowed to emit several attempts per parent thesis, but only the first
    # cognitive-geometry READY attempt is economically executable.
    first_ready: dict[tuple[str, str, str, str, str], V50RearmAttempt] = {}
    for attempt in attempts:
        if not attempt.cognitive_geometry_ready:
            continue
        key = (
            attempt.symbol,
            attempt.session,
            attempt.operating_date,
            attempt.h1_state_from,
            attempt.m15_setup_confirmed_at,
        )
        current = first_ready.get(key)
        if current is None or (
            datetime.fromisoformat(attempt.trigger_confirmed_at),
            attempt.attempt_index,
        ) < (
            datetime.fromisoformat(current.trigger_confirmed_at),
            current.attempt_index,
        ):
            first_ready[key] = attempt

    transformed: list[V53TradeRecord] = []
    reconstruction_mismatch = 0
    missing_session_bars = 0
    for attempt in first_ready.values():
        opportunity, trade_direction = _attempt_opportunity(attempt)
        snapshot = build_v50_cognitive_snapshot(
            opportunity,
            m1_bars=bars,
            h1_bars=h1,
            experience_memory=CapitalizerExperienceMemory(),
            metacognitive_readiness=CapitalizerEpistemicReadiness.WELL_SUPPORTED,
        )
        geometry = propose_v50_geometry(snapshot)
        if (
            geometry.decision is not V50GeometryDecision.READY
            or geometry.stop_price is None
            or geometry.t1 is None
            or snapshot.cognitive.disposition not in COGNITIVE_GEOMETRY_ALLOWED
        ):
            reconstruction_mismatch += 1
            continue
        if snapshot.cognitive.disposition.value != attempt.cognitive_disposition:
            reconstruction_mismatch += 1
            continue

        replay = replay_v50(
            policy="COGNITIVE_GEOMETRY",
            opportunity=opportunity,
            bars=bars,
            stop=geometry.stop_price,
            target=geometry.t1.price,
            disposition=snapshot.cognitive.disposition,
        )
        if replay is None:
            missing_session_bars += 1
            continue
        transformed.append(
            V53TradeRecord(
                source_policy="V50_R_TRANSFORMED",
                symbol=replay.symbol,
                session=replay.session,
                operating_date=replay.operating_date,
                h1_state_from=attempt.h1_state_from,
                m15_setup_confirmed_at=attempt.m15_setup_confirmed_at,
                attempt_index=attempt.attempt_index,
                direction=trade_direction,
                entry_at=replay.entry_at,
                exit_at=replay.exit_at,
                entry_price=replay.entry_price,
                stop_price=replay.stop_price,
                target_price=replay.target_price,
                planned_reward_r=replay.planned_reward_r,
                realized_gross_r=replay.realized_gross_r,
                exit_reason=replay.exit_reason,
                m1_bars_held=replay.m1_bars_held,
                trigger_family=replay.trigger_family,
                h1_state_basis=replay.h1_basis,
                same_bar_stop_target_ambiguity=(
                    replay.same_bar_stop_target_ambiguity
                ),
            )
        )

    report = {
        "identity": IDENTITY,
        "symbol": symbol,
        "session": session,
        "v49_opportunities": len(opportunities),
        "baseline_trade_rows": len(baseline),
        "v50_r_attempt_rows": len(attempts),
        "cognitive_ready_parent_theses": len(first_ready),
        "transformed_trade_rows": len(transformed),
        "reconstruction_mismatch": reconstruction_mismatch,
        "missing_session_bars": missing_session_bars,
        "decision_timeframes": ["H1", "M15", "M1"],
        "outcome_used_for_selection": False,
        "stop_widened": False,
        "recovery_sizing_used": False,
        "historical_research": True,
        "certification_authority": False,
        "live_authorized": False,
        "real_capital_authorized": False,
    }
    return report, baseline, tuple(transformed)


def _as_v49(item: V53TradeRecord) -> V49EconomicTrade:
    return V49EconomicTrade(
        symbol=item.symbol,
        session=item.session,
        operating_date=item.operating_date,
        ordinal_candidate_at=item.entry_at,
        direction=item.direction,
        entry_at=item.entry_at,
        exit_at=item.exit_at,
        entry_price=item.entry_price,
        stop_price=item.stop_price,
        target_price=item.target_price,
        planned_reward_r=item.planned_reward_r,
        realized_gross_r=item.realized_gross_r,
        exit_reason=item.exit_reason,
        m1_bars_held=item.m1_bars_held,
        trigger_family=item.trigger_family,
        h1_state_basis=item.h1_state_basis,
        same_bar_stop_target_ambiguity=item.same_bar_stop_target_ambiguity,
    )


def _portfolio(rows: tuple[V53TradeRecord, ...]) -> tuple[V53TradeRecord, ...]:
    by_parent: dict[tuple[str, str, str, str, str], V53TradeRecord] = {}
    for item in rows:
        key = _parent_key(item)
        current = by_parent.get(key)
        if current is None or (
            datetime.fromisoformat(item.entry_at),
            item.attempt_index,
        ) < (
            datetime.fromisoformat(current.entry_at),
            current.attempt_index,
        ):
            by_parent[key] = item

    grouped: dict[tuple[str, str], list[V53TradeRecord]] = defaultdict(list)
    for item in by_parent.values():
        grouped[(item.session, item.operating_date)].append(item)

    selected: list[V53TradeRecord] = []
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


def _metrics(rows: tuple[V53TradeRecord, ...], *, cost_r: Decimal = Decimal("0")) -> dict[str, Any]:
    return v51_metrics(tuple(_as_v49(item) for item in rows), cost_r=cost_r)


def _preservation(
    baseline: tuple[V53TradeRecord, ...],
    candidate: tuple[V53TradeRecord, ...],
    *,
    raw_candidate: tuple[V53TradeRecord, ...],
) -> dict[str, Any]:
    candidate_by_parent = {_parent_key(item): item for item in candidate}
    raw_parent_keys = {_parent_key(item) for item in raw_candidate}
    baseline_parent_keys = {_parent_key(item) for item in baseline}

    winners = tuple(
        item for item in baseline if Decimal(item.realized_gross_r) > 0
    )
    losses = tuple(
        item for item in baseline if Decimal(item.realized_gross_r) < 0
    )
    stops = tuple(item for item in baseline if item.exit_reason == "STOP")

    preserved_winners = tuple(
        item
        for item in winners
        if (
            (candidate_item := candidate_by_parent.get(_parent_key(item))) is not None
            and Decimal(candidate_item.realized_gross_r) > 0
        )
    )
    baseline_winner_r = sum(
        (Decimal(item.realized_gross_r) for item in winners),
        Decimal("0"),
    )
    transformed_winner_r = sum(
        (
            Decimal(candidate_by_parent[_parent_key(item)].realized_gross_r)
            for item in preserved_winners
        ),
        Decimal("0"),
    )

    recalled_losses = tuple(
        item
        for item in losses
        if (
            (candidate_item := candidate_by_parent.get(_parent_key(item))) is None
            or Decimal(candidate_item.realized_gross_r) >= 0
        )
    )
    recalled_stops = tuple(
        item
        for item in stops
        if (
            (candidate_item := candidate_by_parent.get(_parent_key(item))) is None
            or Decimal(candidate_item.realized_gross_r) >= 0
        )
    )
    displaced_winners = sum(
        _parent_key(item) in raw_parent_keys
        and _parent_key(item) not in candidate_by_parent
        for item in winners
    )
    transformed_winner_to_loser = sum(
        (
            candidate_item := candidate_by_parent.get(_parent_key(item))
        ) is not None
        and Decimal(candidate_item.realized_gross_r) <= 0
        for item in winners
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
            else str(Decimal(len(preserved_winners)) / Decimal(len(winners)))
        ),
        "winner_r_preservation": (
            None
            if baseline_winner_r == 0
            else str(transformed_winner_r / baseline_winner_r)
        ),
        "loss_recall": (
            None
            if not losses
            else str(Decimal(len(recalled_losses)) / Decimal(len(losses)))
        ),
        "full_stop_recall": (
            None
            if not stops
            else str(Decimal(len(recalled_stops)) / Decimal(len(stops)))
        ),
        "baseline_winners_displaced_by_recompetition": displaced_winners,
        "baseline_winners_transformed_to_nonwinner": transformed_winner_to_loser,
        "new_parent_theses_selected": sum(
            _parent_key(item) not in baseline_parent_keys for item in candidate
        ),
    }


def _load_records(root: Path, suffix: str) -> tuple[V53TradeRecord, ...]:
    paths = sorted(root.rglob(f"capitalizer-*-{suffix}.jsonl"))
    if len(paths) != 9:
        raise ValueError(f"V53 aggregate requires 9 {suffix} ledgers, got {len(paths)}")
    rows: list[V53TradeRecord] = []
    for path in paths:
        with path.open(encoding="utf-8") as handle:
            for line in handle:
                if line.strip():
                    rows.append(V53TradeRecord(**json.loads(line)))
    return tuple(rows)


def build_matrix(root: Path) -> dict[str, Any]:
    baseline_raw = _load_records(root, "v53-baseline")
    transformed_raw = _load_records(root, "v53-transformed")
    baseline = _portfolio(baseline_raw)
    transformed = _portfolio(transformed_raw)

    result = {
        "identity": MATRIX_IDENTITY,
        "baseline": {
            "metrics": _metrics(baseline),
            "trades_after_max3": len(baseline),
        },
        "transformed": {
            "metrics": _metrics(transformed),
            "trades_after_max3": len(transformed),
            "cost_stress": [
                {
                    "cost_r_per_trade": str(cost),
                    "metrics": _metrics(transformed, cost_r=cost),
                }
                for cost in COST_STRESS_R
            ],
            "by_session": {
                session: _metrics(
                    tuple(item for item in transformed if item.session == session)
                )
                for session in ("ASIA", "LONDON", "NEW_YORK")
            },
            "by_market": {
                symbol: _metrics(
                    tuple(item for item in transformed if item.symbol == symbol)
                )
                for symbol in sorted({item.symbol for item in transformed})
            },
            "first_attempt": _metrics(
                tuple(item for item in transformed if item.attempt_index == 1)
            ),
            "recovered_after_rearm": _metrics(
                tuple(item for item in transformed if item.attempt_index > 1)
            ),
        },
        "preservation_vs_v49": _preservation(
            baseline,
            transformed,
            raw_candidate=transformed_raw,
        ),
        "decision_timeframes": ["H1", "M15", "M1"],
        "parent_thesis_identity_used_for_preservation": True,
        "outcome_used_for_selection": False,
        "stop_widened": False,
        "recovery_sizing_used": False,
        "historical_research": True,
        "automatic_policy_promotion": False,
        "certification_authority": False,
        "final_independent_or_prospective_oos_required": True,
        "live_authorized": False,
        "real_capital_authorized": False,
    }
    return result


def write_market(
    report: dict[str, Any],
    baseline: tuple[V53TradeRecord, ...],
    transformed: tuple[V53TradeRecord, ...],
    output: Path,
) -> None:
    output.mkdir(parents=True, exist_ok=True)
    symbol = str(report["symbol"]).lower()
    (output / f"capitalizer-{symbol}-v53-market-report.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    for suffix, rows in (
        ("v53-baseline", baseline),
        ("v53-transformed", transformed),
    ):
        with (output / f"capitalizer-{symbol}-{suffix}.jsonl").open(
            "w", encoding="utf-8"
        ) as handle:
            for item in rows:
                handle.write(json.dumps(asdict(item), sort_keys=True) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)

    market = sub.add_parser("market")
    market.add_argument("capacity_root", type=Path)
    market.add_argument("baseline_root", type=Path)
    market.add_argument("rearm_root", type=Path)
    market.add_argument("m1_root", type=Path)
    market.add_argument("output", type=Path)

    matrix = sub.add_parser("matrix")
    matrix.add_argument("input_root", type=Path)
    matrix.add_argument("output", type=Path)

    args = parser.parse_args()
    if args.command == "market":
        report, baseline, transformed = build_market(
            capacity_root=args.capacity_root,
            baseline_root=args.baseline_root,
            rearm_root=args.rearm_root,
            m1_root=args.m1_root,
        )
        write_market(report, baseline, transformed, args.output)
        print(json.dumps(report, sort_keys=True))
        return

    result = build_matrix(args.input_root)
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / "capitalizer-v53-winner-preserving-rearm-matrix.json").write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
