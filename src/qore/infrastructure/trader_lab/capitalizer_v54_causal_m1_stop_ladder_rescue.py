"""V54 pre-economic causal M1 stop-ladder rescue.

The current V50 dual-invalidation engine uses only the latest confirmed risk-side M1 pivot.
V54 asks whether WAIT_STOP_BREATHING opportunities can be rescued at the SAME decision
timestamp by a more senior, already-confirmed M1 pivot that satisfies the frozen 4x-8x local
noise band, remains inside M15 thesis risk, and retains a causal H1 destination >=1R.

No outcome or future bar participates.
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
from qore.infrastructure.trader_lab.capitalizer_contract import MAX_EXECUTIONS_PER_SESSION
from qore.infrastructure.trader_lab.capitalizer_experience_memory import (
    CapitalizerExperienceMemory,
)
from qore.infrastructure.trader_lab.capitalizer_exposure_graph import CapitalizerSide
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
from qore.infrastructure.trader_lab.capitalizer_v50_cognitive_geometry_specialist import (
    MAX_EXECUTION_STOP_NOISE,
    MIN_EXECUTION_STOP_NOISE,
    MIN_FULL_TARGET_R,
    V50GeometryDecision,
    propose_v50_geometry,
)
from qore.infrastructure.trader_lab.capitalizer_v50_cognitive_opportunity import (
    build_v50_cognitive_snapshot,
)

IDENTITY = "QORE_CAPITALIZER_V54_CAUSAL_M1_STOP_LADDER_RESCUE"
MATRIX_IDENTITY = "QORE_CAPITALIZER_V54_STOP_LADDER_RESCUE_MATRIX"


@dataclass(frozen=True, slots=True)
class V54Candidate:
    symbol: str
    session: str
    operating_date: str
    h1_state_from: str
    m15_setup_confirmed_at: str
    entry_at: str
    trigger_family: str
    candidate_kind: str
    stop_price: str
    stop_confirmed_at: str
    stop_to_noise_ratio: str
    target_price: str
    target_reward_r: str
    cognitive_disposition: str
    outcome_used: bool = False
    future_bar_used: bool = False
    post_entry_stop_widening: bool = False

    def __post_init__(self) -> None:
        if self.candidate_kind not in {"CURRENT_V50_READY", "STOP_LADDER_RESCUE"}:
            raise ValueError("unexpected V54 candidate kind")
        if (
            self.outcome_used
            or self.future_bar_used
            or self.post_entry_stop_widening
        ):
            raise ValueError("V54 crossed pre-economic causal boundary")


def _load_opportunities(root: Path) -> tuple[V49Opportunity, ...]:
    paths = sorted(root.rglob("capitalizer-*-v49-hf-capacity-opportunities.jsonl"))
    if len(paths) != 1:
        raise ValueError("V54 market requires one V49 opportunity ledger")
    rows: list[V49Opportunity] = []
    with paths[0].open(encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                rows.append(V49Opportunity(**json.loads(line)))
    return tuple(rows)


def _side(opportunity: V49Opportunity) -> CapitalizerSide:
    return (
        CapitalizerSide.LONG
        if opportunity.h1_state_direction == "BULLISH"
        else CapitalizerSide.SHORT
    )


def _confirmed_execution_pivots(
    bars: tuple[CapitalizerM1Bar, ...],
    *,
    side: CapitalizerSide,
    setup_confirmed_at: datetime,
    decision_at: datetime,
    entry_price: Decimal,
) -> tuple[tuple[datetime, Decimal], ...]:
    window = tuple(
        bar
        for bar in bars
        if bar.opened_at >= setup_confirmed_at and bar.closed_at <= decision_at
    )
    result: list[tuple[datetime, Decimal]] = []
    for index in range(1, len(window) - 1):
        left, center, right = window[index - 1], window[index], window[index + 1]
        if right.closed_at > decision_at:
            break
        if side is CapitalizerSide.LONG:
            pivot = center.low < left.low and center.low < right.low
            price = center.low
            risk_side = price < entry_price
        else:
            pivot = center.high > left.high and center.high > right.high
            price = center.high
            risk_side = price > entry_price
        if not (pivot and risk_side):
            continue

        # A senior pivot is usable at the current decision timestamp only if it has
        # remained structurally intact since its causal right-hand confirmation.
        # A pre-entry touch/breach would already have consumed that invalidation level.
        later = window[index + 2 :]
        intact = (
            all(item.low > price for item in later)
            if side is CapitalizerSide.LONG
            else all(item.high < price for item in later)
        )
        if intact:
            result.append((right.closed_at, price))
    return tuple(result)


def _choose_rescue(
    pivots: tuple[tuple[datetime, Decimal], ...],
    *,
    entry_price: Decimal,
    thesis_stop_price: Decimal,
    recent_range_ticks: Decimal,
    tick: Decimal,
    target_prices: tuple[Decimal, ...],
) -> tuple[datetime, Decimal, Decimal, Decimal, Decimal] | None:
    thesis_risk = abs(entry_price - thesis_stop_price)
    if thesis_risk <= 0 or recent_range_ticks <= 0 or tick <= 0:
        raise ValueError("V54 requires positive risk/noise geometry")

    for confirmed_at, stop_price in reversed(pivots):
        risk = abs(entry_price - stop_price)
        if risk <= 0 or risk >= thesis_risk:
            continue
        noise = (risk / tick) / recent_range_ticks
        if not (MIN_EXECUTION_STOP_NOISE <= noise <= MAX_EXECUTION_STOP_NOISE):
            continue
        for target_price in target_prices:
            reward_r = abs(target_price - entry_price) / risk
            if reward_r >= MIN_FULL_TARGET_R:
                return confirmed_at, stop_price, noise, target_price, reward_r
    return None


def build_market(
    *,
    capacity_root: Path,
    m1_root: Path,
) -> tuple[dict[str, Any], tuple[V54Candidate, ...]]:
    opportunities = _load_opportunities(capacity_root)
    if not opportunities:
        raise ValueError("V54 requires source-complete opportunities")
    symbol = opportunities[0].symbol
    session = opportunities[0].session

    bars = tuple(
        bar
        for bar in iter_cibo_m1(m1_root)
        if DEV_WINDOW_START - DEFAULT_LOOKBACK <= bar.opened_at < DEV_WINDOW_END
    )
    if not bars or any(item.symbol != symbol for item in bars):
        raise ValueError("V54 M1 source mismatch")
    h1 = _aggregate(bars, minutes=60)

    counters: Counter[str] = Counter()
    candidates: list[V54Candidate] = []
    reward_bins: Counter[str] = Counter()

    for opportunity in opportunities:
        snapshot = build_v50_cognitive_snapshot(
            opportunity,
            m1_bars=bars,
            h1_bars=h1,
            experience_memory=CapitalizerExperienceMemory(),
            metacognitive_readiness=CapitalizerEpistemicReadiness.WELL_SUPPORTED,
        )
        geometry = propose_v50_geometry(snapshot)
        entry_at = datetime.fromisoformat(opportunity.m1_trigger_confirmed_at)
        entry = Decimal(opportunity.decision_reference_price)
        completed = tuple(item for item in bars if item.closed_at <= entry_at)
        if not completed:
            raise ValueError("V54 requires completed decision-time M1")
        tick = Decimal(1).scaleb(-completed[-1].digits)

        if geometry.decision is V50GeometryDecision.READY:
            if (
                geometry.stop_price is None
                or geometry.stop_to_noise_ratio is None
                or geometry.t1 is None
                or geometry.t1_reward_r is None
                or snapshot.dual_invalidation.execution_anchor_confirmed_at is None
            ):
                raise ValueError("V54 current READY geometry missing payload")
            candidates.append(
                V54Candidate(
                    symbol=symbol,
                    session=session,
                    operating_date=opportunity.operating_date,
                    h1_state_from=opportunity.h1_state_from,
                    m15_setup_confirmed_at=opportunity.m15_setup_confirmed_at,
                    entry_at=opportunity.m1_trigger_confirmed_at,
                    trigger_family=opportunity.m1_trigger_family,
                    candidate_kind="CURRENT_V50_READY",
                    stop_price=str(geometry.stop_price),
                    stop_confirmed_at=(
                        snapshot.dual_invalidation.execution_anchor_confirmed_at.isoformat()
                    ),
                    stop_to_noise_ratio=str(geometry.stop_to_noise_ratio),
                    target_price=str(geometry.t1.price),
                    target_reward_r=str(geometry.t1_reward_r),
                    cognitive_disposition=snapshot.cognitive.disposition.value,
                )
            )
            counters["CURRENT_READY"] += 1
            continue

        if geometry.decision is not V50GeometryDecision.WAIT_STOP_BREATHING:
            counters[geometry.decision.value] += 1
            continue

        counters["WAIT_STOP_BREATHING"] += 1
        reason = geometry.reasons[0] if geometry.reasons else "UNKNOWN"
        counters[reason] += 1

        setup_at = datetime.fromisoformat(opportunity.m15_setup_confirmed_at)
        side = _side(opportunity)
        pivots = _confirmed_execution_pivots(
            completed,
            side=side,
            setup_confirmed_at=setup_at,
            decision_at=entry_at,
            entry_price=entry,
        )
        rescue = _choose_rescue(
            pivots,
            entry_price=entry,
            thesis_stop_price=Decimal(opportunity.m15_protected_swing_price),
            recent_range_ticks=snapshot.recent_m1_range_ticks,
            tick=tick,
            target_prices=tuple(
                item.price for item in snapshot.target_ladder.candidates
            ),
        )
        if rescue is None:
            counters["STOP_LADDER_NO_RESCUE"] += 1
            continue

        confirmed_at, stop_price, noise, target_price, reward_r = rescue
        counters["STOP_LADDER_RESCUE"] += 1
        counters[f"RESCUE_FROM:{reason}"] += 1
        if reward_r >= Decimal("2"):
            reward_bins["GE_2R"] += 1
        elif reward_r >= Decimal("1.5"):
            reward_bins["1_5_TO_2R"] += 1
        else:
            reward_bins["1_TO_1_5R"] += 1

        candidates.append(
            V54Candidate(
                symbol=symbol,
                session=session,
                operating_date=opportunity.operating_date,
                h1_state_from=opportunity.h1_state_from,
                m15_setup_confirmed_at=opportunity.m15_setup_confirmed_at,
                entry_at=opportunity.m1_trigger_confirmed_at,
                trigger_family=opportunity.m1_trigger_family,
                candidate_kind="STOP_LADDER_RESCUE",
                stop_price=str(stop_price),
                stop_confirmed_at=confirmed_at.isoformat(),
                stop_to_noise_ratio=str(noise),
                target_price=str(target_price),
                target_reward_r=str(reward_r),
                cognitive_disposition=snapshot.cognitive.disposition.value,
            )
        )

    report = {
        "identity": IDENTITY,
        "symbol": symbol,
        "session": session,
        "source_opportunities": len(opportunities),
        "current_v50_ready": counters["CURRENT_READY"],
        "wait_stop_breathing": counters["WAIT_STOP_BREATHING"],
        "inside_local_noise": counters["M1_EXECUTION_STOP_INSIDE_LOCAL_NOISE"],
        "too_wide_for_scalp": counters["M1_EXECUTION_STOP_TOO_WIDE_FOR_SCALP"],
        "stop_ladder_rescues": counters["STOP_LADDER_RESCUE"],
        "stop_ladder_no_rescue": counters["STOP_LADDER_NO_RESCUE"],
        "rescue_from_inside_noise": counters[
            "RESCUE_FROM:M1_EXECUTION_STOP_INSIDE_LOCAL_NOISE"
        ],
        "rescue_from_too_wide": counters[
            "RESCUE_FROM:M1_EXECUTION_STOP_TOO_WIDE_FOR_SCALP"
        ],
        "rescue_target_reward_bins": dict(sorted(reward_bins.items())),
        "candidate_rows": len(candidates),
        "decision_timeframes": ["H1", "M15", "M1"],
        "outcome_used": False,
        "future_bar_used": False,
        "post_entry_stop_widening": False,
        "economics_used": False,
        "runtime_policy_candidate": False,
    }
    return report, tuple(candidates)


def _parent_key(item: V54Candidate) -> tuple[str, str, str, str, str]:
    return (
        item.symbol,
        item.session,
        item.operating_date,
        item.h1_state_from,
        item.m15_setup_confirmed_at,
    )


def _portfolio(rows: tuple[V54Candidate, ...]) -> tuple[V54Candidate, ...]:
    by_parent: dict[tuple[str, str, str, str, str], V54Candidate] = {}
    for item in rows:
        parent_key = _parent_key(item)
        current = by_parent.get(parent_key)
        if current is None or datetime.fromisoformat(item.entry_at) < datetime.fromisoformat(
            current.entry_at
        ):
            by_parent[parent_key] = item

    grouped: dict[tuple[str, str], list[V54Candidate]] = defaultdict(list)
    for item in by_parent.values():
        grouped[(item.session, item.operating_date)].append(item)

    selected: list[V54Candidate] = []
    for session_day_key in sorted(grouped):
        candidates = sorted(
            grouped[session_day_key],
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


def build_matrix(root: Path) -> dict[str, Any]:
    report_paths = sorted(root.rglob("capitalizer-*-v54-market-report.json"))
    ledger_paths = sorted(root.rglob("capitalizer-*-v54-candidates.jsonl"))
    if len(report_paths) != 9 or len(ledger_paths) != 9:
        raise ValueError("V54 matrix requires nine market artifacts")
    reports = tuple(json.loads(path.read_text(encoding="utf-8")) for path in report_paths)
    rows: list[V54Candidate] = []
    for path in ledger_paths:
        with path.open(encoding="utf-8") as handle:
            for line in handle:
                if line.strip():
                    rows.append(V54Candidate(**json.loads(line)))
    selected = _portfolio(tuple(rows))
    return {
        "identity": MATRIX_IDENTITY,
        "source_opportunities": sum(int(row["source_opportunities"]) for row in reports),
        "current_v50_ready": sum(int(row["current_v50_ready"]) for row in reports),
        "wait_stop_breathing": sum(int(row["wait_stop_breathing"]) for row in reports),
        "inside_local_noise": sum(int(row["inside_local_noise"]) for row in reports),
        "too_wide_for_scalp": sum(int(row["too_wide_for_scalp"]) for row in reports),
        "stop_ladder_rescues": sum(int(row["stop_ladder_rescues"]) for row in reports),
        "rescue_from_inside_noise": sum(
            int(row["rescue_from_inside_noise"]) for row in reports
        ),
        "rescue_from_too_wide": sum(
            int(row["rescue_from_too_wide"]) for row in reports
        ),
        "candidate_rows_before_max3": len(rows),
        "portfolio_after_max3": len(selected),
        "portfolio_current_ready": sum(
            item.candidate_kind == "CURRENT_V50_READY" for item in selected
        ),
        "portfolio_stop_ladder_rescues": sum(
            item.candidate_kind == "STOP_LADDER_RESCUE" for item in selected
        ),
        "by_session": {
            session: sum(item.session == session for item in selected)
            for session in ("ASIA", "LONDON", "NEW_YORK")
        },
        "by_market": {
            symbol: sum(item.symbol == symbol for item in selected)
            for symbol in sorted({item.symbol for item in selected})
        },
        "outcome_used": False,
        "future_bar_used": False,
        "economics_used": False,
        "post_entry_stop_widening": False,
        "automatic_policy_promotion": False,
        "trader_certified": False,
        "live_authorized": False,
    }


def write_market(
    report: dict[str, Any],
    candidates: tuple[V54Candidate, ...],
    output: Path,
) -> None:
    output.mkdir(parents=True, exist_ok=True)
    symbol = str(report["symbol"]).lower()
    (output / f"capitalizer-{symbol}-v54-market-report.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    with (output / f"capitalizer-{symbol}-v54-candidates.jsonl").open(
        "w", encoding="utf-8"
    ) as handle:
        for item in candidates:
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
        report, candidates = build_market(
            capacity_root=args.capacity_root,
            m1_root=args.m1_root,
        )
        write_market(report, candidates, args.output)
        print(json.dumps(report, sort_keys=True))
        return

    result = build_matrix(args.input_root)
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / "capitalizer-v54-stop-ladder-rescue-matrix.json").write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
