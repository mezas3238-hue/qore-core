"""R25 Turtle Soup XAUUSD driven directly by CIBO Native Memory V2.

The strategy supplies only its own setup, entry opportunity, and Protected
Swing.  CIBO Native Market Decision Memory V2 supplies destination viability
at 0.10R friction and the preferred structural lifecycle posture.

No R11/R16/R17/R20/R21/R22/R23 memory or label participates in a decision.
"""
from __future__ import annotations

import bisect
import json
import sys
from collections import Counter, defaultdict
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any, cast

from qore.infrastructure.trader_lab import (
    cibo_market_atlas_journey_extractor_v1 as journey,
)
from qore.infrastructure.trader_lab import (
    cibo_xauusd_native_market_decision_memory_v2 as native,
)
from qore.infrastructure.trader_lab import turtle_soup_xauusd_r1 as r1
from qore.infrastructure.trader_lab import turtle_soup_xauusd_r3_cibo_journey as r3
from qore.infrastructure.trader_lab import (
    turtle_soup_xauusd_r3_cibo_journey_binding_repair as repair,
)
from qore.infrastructure.trader_lab.ict_turtle_soup_r4_source_exact import (
    Bar,
    Side,
)

IDENTITY = "TURTLE_SOUP_XAUUSD_R25_CIBO_NATIVE_MEMORY_BRAIN_V1"
EVAL_OPEN = datetime(2024, 9, 17, tzinfo=UTC)
EVAL_CLOSE = datetime(2026, 9, 17, tzinfo=UTC)

ROBUST_PRIORITY = 2
MAJORITY_PRIORITY = 1


@dataclass(frozen=True, slots=True)
class DecisionTarget:
    native_target: native.NativeTarget
    memory_level: str
    classification: str
    posture: str
    mean_net_010_r: Decimal


@dataclass(frozen=True, slots=True)
class Simulation:
    trade: r3.RoutedTrade
    trail_moves: int


def _single(root: Path, name: str) -> Path:
    matches = list(root.rglob(name))
    if len(matches) != 1:
        raise ValueError(f"expected exactly one {name}, got {len(matches)}")
    return matches[0]


def _dt(value: str) -> datetime:
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("timestamp must be timezone-aware")
    return parsed.astimezone(UTC)


def _load_index(root: Path) -> dict[str, Any]:
    path = _single(root, "cibo-xauusd-native-memory-v2-decision-index.json")
    payload = json.loads(path.read_text())
    if not isinstance(payload, dict):
        raise ValueError("native decision index must be an object")
    return cast(dict[str, Any], payload)


def _load_raw_targets(root: Path) -> dict[str, list[dict[str, Any]]]:
    path = _single(root, "TARGET_DESTINATION_LEDGER_V2.jsonl")
    result: dict[str, list[dict[str, Any]]] = defaultdict(list)
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            row = json.loads(line)
            result[str(row["episode_id"])].append(row)
    return dict(result)


def _raid_bucket_to_native(value: str) -> str:
    # R2's finer low-raid buckets map exactly into the coarser native-market
    # anatomy buckets.  Values >0.50 cannot be inferred more finely, so query
    # backoff naturally handles them by using destination/geometry memory.
    if value in {"q1:<=0.05", "q2:<=0.10", "q3:<=0.25"}:
        return "q1:<=0.25"
    if value == "q4:<=0.50":
        return "q2:<=0.50"
    return "unmapped_gt_0.50"


def _active_ladder(
    rows: Sequence[dict[str, Any]],
    *,
    at: datetime,
    side: Side,
    entry: Decimal,
    tick: Decimal,
) -> list[native.NativeTarget]:
    by_price: dict[Decimal, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        known = _dt(str(row["candidate_known_at"]))
        if known > at:
            continue
        touched_at = (
            None
            if row.get("touch_m5_opened_at") is None
            else _dt(str(row["touch_m5_opened_at"]))
        )
        if touched_at is not None and touched_at < at:
            continue
        level = Decimal(str(row["candidate_price"]))
        ahead = level > entry if side is Side.LONG else level < entry
        if ahead:
            by_price[level].append(row)

    grouped = sorted(by_price.items(), key=lambda item: abs(item[0] - entry))
    ladder: list[native.NativeTarget] = []
    for rank, (level, members) in enumerate(grouped, start=1):
        if rank > native.MAX_TARGET_RANK:
            break
        touched_rows = [
            row for row in members if row.get("touch_m5_opened_at") is not None
        ]
        touch_at = (
            None
            if not touched_rows
            else min(_dt(str(row["touch_m5_opened_at"])) for row in touched_rows)
        )
        ladder.append(
            native.NativeTarget(
                rank=rank,
                level=level,
                route=native._route(members),
                distance_ticks=abs(level - entry) / tick,
                touched=bool(touched_rows),
                touch_at=touch_at,
            )
        )
    return ladder


def _query_row(
    setup: r3.Setup,
    *,
    target: native.NativeTarget,
    entry: Decimal,
) -> dict[str, Any]:
    context = setup.context
    side = setup.context.signal.side
    stop = setup.context.signal.protected_swing
    risk = entry - stop if side is Side.LONG else stop - entry
    reward = target.level - entry if side is Side.LONG else entry - target.level
    rr = Decimal(0) if risk <= 0 or reward <= 0 else reward / risk
    return {
        "timeframe": context.timeframe,
        "reference_type": "prior-candle",
        "side": context.side,
        "session": context.session,
        "prior_body_alignment": context.prior_body_alignment,
        "fvg": context.fvg_before_entry,
        "equal_liquidity": context.exact_equal_liquidity,
        "reclaim_bucket": context.reclaim_latency_bucket,
        "cisd_progress_bucket": context.cisd_progress_bucket,
        "raid_depth_bucket": _raid_bucket_to_native(
            context.raid_depth_range_bucket
        ),
        "protected_risk_bucket": context.protected_risk_range_bucket,
        "body_bucket": context.body_fraction_bucket,
        "wick_bucket": context.rejection_wick_bucket,
        "close_bucket": context.close_location_bucket,
        "target_rank": target.rank,
        "target_route": target.route,
        "rr_bucket": native._bucket(rr, native.RR_CUTS),
    }


def _candidate_decision(
    index: dict[str, Any],
    row: dict[str, Any],
    target: native.NativeTarget,
) -> DecisionTarget | None:
    item, level, _signature = native.resolve_index(index, row)
    if item is None or level is None:
        return None
    classification = str(item["classification"])
    posture = item.get("preferred_posture")
    if classification not in {native.ROBUST, native.MAJORITY} or posture is None:
        return None
    mean = item.get("mean_net_010_r")
    if mean is None:
        return None
    return DecisionTarget(
        native_target=target,
        memory_level=level,
        classification=classification,
        posture=str(posture),
        mean_net_010_r=Decimal(str(mean)),
    )


def choose_target(
    index: dict[str, Any],
    setup: r3.Setup,
    *,
    ladder: Sequence[native.NativeTarget],
    entry: Decimal,
) -> DecisionTarget | None:
    decisions: list[DecisionTarget] = []
    for target in ladder:
        decision = _candidate_decision(
            index,
            _query_row(setup, target=target, entry=entry),
            target,
        )
        if decision is not None:
            decisions.append(decision)
    if not decisions:
        return None

    def priority(item: DecisionTarget) -> tuple[int, Decimal, int]:
        class_priority = (
            ROBUST_PRIORITY if item.classification == native.ROBUST else MAJORITY_PRIORITY
        )
        # Native CIBO directly resolves whether the destination compensates
        # 0.10R. Within the same temporal-confidence class, use its retained
        # expected net outcome; rank is only a deterministic tie-breaker.
        return (
            class_priority,
            item.mean_net_010_r,
            -item.native_target.rank,
        )

    return max(decisions, key=priority)


def _structurally_rearmed(
    setup: r3.Setup,
    trailing_exit_at: datetime | None,
) -> bool:
    if trailing_exit_at is None:
        return True
    signal = setup.context.signal
    return bool(
        signal.raid_at > trailing_exit_at
        and signal.c2_opened_at > trailing_exit_at
    )


def _simulate_trade(
    setup: r3.Setup,
    *,
    entry_at: datetime,
    entry: Decimal,
    decision: DecisionTarget,
    ladder: Sequence[native.NativeTarget],
    evidence: Any,
    opens: Sequence[datetime],
) -> Simulation | None:
    side = setup.context.signal.side
    initial_stop = setup.context.signal.protected_swing
    target = decision.native_target.level
    risk = entry - initial_stop if side is Side.LONG else initial_stop - entry
    reward = target - entry if side is Side.LONG else entry - target
    if risk <= 0 or reward <= 0:
        return None

    left = bisect.bisect_left(opens, entry_at)
    right = bisect.bisect_left(
        opens,
        min(entry_at + timedelta(hours=24), r3.EVAL_CLOSE),
    )
    path = list(evidence.bars[left:right])
    if not path:
        return None

    current_stop = initial_stop
    pending: Decimal | None = None
    observed: list[Bar] = []
    conquered: set[int] = set()
    trail_moves = 0
    exit_at = path[-1].closed_at
    exit_price = path[-1].close
    exit_reason = "TIME_24H"

    for bar in path:
        if pending is not None and native._improves_stop(
            side=side,
            previous=current_stop,
            candidate=pending,
            target=target,
        ):
            current_stop = pending
            trail_moves += 1
        pending = None

        if side is Side.LONG:
            if bar.open <= current_stop:
                exit_at = bar.opened_at
                exit_price = bar.open
                exit_reason = (
                    "GAP_TRAIL" if current_stop != initial_stop else "GAP_STOP"
                )
                break
            if bar.open >= target:
                exit_at = bar.opened_at
                exit_price = target
                exit_reason = "TARGET"
                break
            stop_touch = bar.low <= current_stop
            target_touch = bar.high >= target
        else:
            if bar.open >= current_stop:
                exit_at = bar.opened_at
                exit_price = bar.open
                exit_reason = (
                    "GAP_TRAIL" if current_stop != initial_stop else "GAP_STOP"
                )
                break
            if bar.open <= target:
                exit_at = bar.opened_at
                exit_price = target
                exit_reason = "TARGET"
                break
            stop_touch = bar.high >= current_stop
            target_touch = bar.low <= target

        if stop_touch and target_touch:
            exit_at = bar.closed_at
            exit_price = current_stop
            exit_reason = (
                "TRAIL_STOP_FIRST"
                if current_stop != initial_stop
                else "STOP_FIRST"
            )
            break
        if stop_touch:
            exit_at = bar.closed_at
            exit_price = current_stop
            exit_reason = (
                "TRAIL_STOP" if current_stop != initial_stop else "STOP"
            )
            break
        if target_touch:
            exit_at = bar.closed_at
            exit_price = target
            exit_reason = "TARGET"
            break

        observed.append(bar)

        if decision.posture != native.POSTURE_STATIC and decision.native_target.rank > 1:
            for earlier in ladder[: decision.native_target.rank - 1]:
                if earlier.rank in conquered:
                    continue
                if native._target_touch(side, earlier.level, bar):
                    conquered.add(earlier.rank)
                    if native._improves_stop(
                        side=side,
                        previous=current_stop,
                        candidate=earlier.level,
                        target=target,
                    ):
                        if pending is None:
                            pending = earlier.level
                        else:
                            pending = native._better_stop(
                                side, pending, earlier.level
                            )

        if decision.posture == native.POSTURE_PROTECT:
            swing = native._swing_candidate(
                side=side,
                bars=observed,
                entry=entry,
                target=target,
            )
            if (
                swing is not None
                and native._improves_stop(
                    side=side,
                    previous=current_stop,
                    candidate=swing,
                    target=target,
                )
            ):
                pending = (
                    swing
                    if pending is None
                    else native._better_stop(side, pending, swing)
                )

    gross = (
        (exit_price - entry) / risk
        if side is Side.LONG
        else (entry - exit_price) / risk
    )
    trade = r3.RoutedTrade(
        source_timeframe=setup.context.timeframe,
        side=side.value,
        entry_mode="NEXT_SOURCE_OPEN",
        target_route=decision.native_target.route,
        episode_id="CIBO_NATIVE_V2",
        entry_at=entry_at,
        exit_at=exit_at,
        entry=entry,
        stop=initial_stop,
        target=target,
        target_kind="CIBO_NATIVE_DISTINCT_DOL",
        target_timeframe="MULTI",
        gross_r=gross,
        primary_net_r=gross - r3.PRIMARY_FRICTION_R,
        stress_net_r=gross - r3.STRESS_FRICTION_R,
        exit_reason=exit_reason,
        session_bucket=setup.context.signal.session_bucket,
        prior_body_alignment=setup.context.signal.prior_body_alignment,
    )
    return Simulation(trade=trade, trail_moves=trail_moves)


def _stats(trades: Sequence[r3.RoutedTrade], attr: str) -> dict[str, Any]:
    return r3._stat(trades, attr)


def run(
    raw_root: Path,
    target_root: Path,
    memory_root: Path,
    output: Path,
) -> dict[str, Any]:
    evidence, provenance = journey.load_raw_m5(raw_root)
    if evidence.symbol != "XAUUSD" or int(provenance["retained_bars"]) != 707716:
        raise ValueError("unexpected XAUUSD corpus")
    index = _load_index(memory_root)
    raw_targets = _load_raw_targets(target_root)
    _episodes, source_index = repair._load_targets_fail_closed(target_root)

    original_open, original_close = r1.EVAL_OPEN, r1.EVAL_CLOSE
    try:
        r1.EVAL_OPEN, r1.EVAL_CLOSE = r3.EVAL_OPEN, r3.EVAL_CLOSE
        setups, funnel = r3._build_setups(evidence)
    finally:
        r1.EVAL_OPEN, r1.EVAL_CLOSE = original_open, original_close

    opens = tuple(bar.opened_at for bar in evidence.bars)
    tick = Decimal(1).scaleb(-evidence.digits)
    busy_until = EVAL_OPEN
    trailing_exit_at: datetime | None = None
    trades: list[r3.RoutedTrade] = []
    decisions: list[dict[str, Any]] = []
    counts: Counter[str] = Counter()

    for setup in setups:
        signal = setup.context.signal
        if not (EVAL_OPEN <= signal.entry_at < EVAL_CLOSE):
            continue

        if not _structurally_rearmed(setup, trailing_exit_at):
            counts["ABSTAIN_NOT_STRUCTURALLY_REARMED"] += 1
            continue

        episode_id = source_index.get(
            (
                signal.cisd_at,
                signal.side.value,
                setup.context.timeframe,
                signal.target,
            )
        )
        if episode_id is None:
            counts["ABSTAIN_NO_CIBO_EPISODE"] += 1
            continue

        fill = r3._entry(setup, evidence, opens, "NEXT_SOURCE_OPEN")
        if fill is None:
            counts["ABSTAIN_NO_ENTRY"] += 1
            continue
        entry_at, entry = fill

        ladder = _active_ladder(
            raw_targets.get(episode_id, ()),
            at=entry_at,
            side=signal.side,
            entry=entry,
            tick=tick,
        )
        if not ladder:
            counts["ABSTAIN_NO_ACTIVE_DOL"] += 1
            continue

        decision = choose_target(index, setup, ladder=ladder, entry=entry)
        if decision is None:
            counts["ABSTAIN_CIBO_NATIVE_NO_POSITIVE_010"] += 1
            continue

        sim = _simulate_trade(
            setup,
            entry_at=entry_at,
            entry=entry,
            decision=decision,
            ladder=ladder,
            evidence=evidence,
            opens=opens,
        )
        if sim is None:
            counts["ABSTAIN_INVALID_GEOMETRY"] += 1
            continue
        trade = sim.trade
        if trade.entry_at < busy_until:
            counts["ABSTAIN_SINGLE_POSITION_BUSY"] += 1
            continue

        busy_until = trade.exit_at
        if "TRAIL" in trade.exit_reason:
            trailing_exit_at = trade.exit_at
        counts["EXECUTE"] += 1
        counts[f"MEMORY_{decision.classification}"] += 1
        counts[f"POSTURE_{decision.posture}"] += 1
        counts[f"LEVEL_{decision.memory_level}"] += 1
        counts[f"RANK_{decision.native_target.rank}"] += 1
        trades.append(trade)
        decisions.append(
            {
                "entry_at": entry_at.isoformat(),
                "exit_at": trade.exit_at.isoformat(),
                "side": trade.side,
                "memory_level": decision.memory_level,
                "classification": decision.classification,
                "posture": decision.posture,
                "mean_net_010_memory": str(decision.mean_net_010_r),
                "target_rank": decision.native_target.rank,
                "target_route": decision.native_target.route,
                "entry": str(entry),
                "stop": str(trade.stop),
                "target": str(trade.target),
                "gross_r": str(trade.gross_r),
                "net_005_r": str(trade.primary_net_r),
                "net_010_r": str(trade.stress_net_r),
                "exit_reason": trade.exit_reason,
                "trail_moves": sim.trail_moves,
            }
        )

    payload = {
        "schema": "qore.turtle_soup_xauusd_r25.cibo_native_memory_brain.v1",
        "identity": IDENTITY,
        "window": {
            "open": EVAL_OPEN.isoformat(),
            "close": EVAL_CLOSE.isoformat(),
            "duration_years": 2,
        },
        "decision_sources": {
            "strategy_setup": "TURTLE_SOUP_SOURCE_CONTRACT",
            "market_memory": native.IDENTITY,
            "target_destination": r3.TARGET_IDENTITY,
            "r11_memory_used": False,
            "r16_memory_used": False,
            "r17_memory_used": False,
            "r20_memory_used": False,
            "r21_memory_used": False,
            "r22_memory_used": False,
            "r23_memory_used": False,
        },
        "decision_contract": {
            "entry_mode": "NEXT_SOURCE_OPEN",
            "cibo_selects_target": True,
            "cibo_selects_management_posture": True,
            "cibo_memory_is_net_010_aware": True,
            "negative_or_unresolved_memory_abstains": True,
            "structural_rearm_preserved": True,
            "single_position_constraint": True,
            "fresh_holdout_used": False,
        },
        "reproduction": {
            "retained_bars": int(provenance["retained_bars"]),
            "setups_10y": len(setups),
        },
        "behavior": {
            "decision_counts": dict(counts),
            "executed_trades": len(trades),
            "gross": _stats(trades, "gross_r"),
            "primary_005r": _stats(trades, "primary_net_r"),
            "stress_010r": _stats(trades, "stress_net_r"),
        },
        "governance": {
            "research_only": True,
            "same_consumed_2y_window": True,
            "fresh_holdout_consumed": False,
            "candidate_promoted": False,
            "demo_eligible": False,
            "live_authorized": False,
            "real_capital_authorized": False,
            "production_authorized": False,
        },
        "funnel": funnel,
    }

    output.mkdir(parents=True, exist_ok=True)
    (output / "r25-cibo-native-brain-report.json").write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n"
    )
    (output / "r25-cibo-native-brain-decisions.json").write_text(
        json.dumps(decisions, indent=2, sort_keys=True) + "\n"
    )
    return payload


def main() -> None:
    if len(sys.argv) != 5:
        raise SystemExit(
            "usage: module RAW_ROOT TARGET_ROOT NATIVE_MEMORY_ROOT OUTPUT_DIR"
        )
    print(
        json.dumps(
            run(
                Path(sys.argv[1]),
                Path(sys.argv[2]),
                Path(sys.argv[3]),
                Path(sys.argv[4]),
            ),
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
