"""R26 Turtle Soup AUDJPY driven by the dedicated Specialist Cognitive Memory.

The strategy supplies its setup, actual NEXT_SOURCE_OPEN entry and exact
Protected Swing.  The dedicated Turtle Soup AUDJPY specialist memory supplies:
- whether the current situation has authoritative historical support;
- which active CIBO DOL rank is supported;
- which lifecycle posture (STATIC / LET_RUN / PROTECT) is supported.

Only exact / causal_core / anatomy memory can authorize a trade.
compact_anatomy is context-only and can never authorize entry.
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
    cibo_audjpy_native_market_decision_memory_v2 as native,
)
from qore.infrastructure.trader_lab import turtle_soup_audjpy_r1 as r1
from qore.infrastructure.trader_lab import turtle_soup_audjpy_r2_cibo_full as r2
from qore.infrastructure.trader_lab import turtle_soup_audjpy_r3_cibo_journey as r3
from qore.infrastructure.trader_lab import (
    turtle_soup_audjpy_r3_cibo_journey_binding_repair as repair,
)
from qore.infrastructure.trader_lab import (
    turtle_soup_audjpy_specialist_memory_v1 as specialist,
)
from qore.infrastructure.trader_lab.ict_turtle_soup_r4_source_exact import (
    Bar,
    Side,
)

IDENTITY = "TURTLE_SOUP_AUDJPY_R26_SPECIALIST_MEMORY_BRAIN_V1"
EVAL_OPEN = datetime(2024, 9, 17, tzinfo=UTC)
EVAL_CLOSE = datetime(2026, 9, 17, tzinfo=UTC)

LEVEL_PRIORITY = {
    "exact": 3,
    "causal_core": 2,
    "anatomy": 1,
}
CLASS_PRIORITY = {
    "ROBUST_POSITIVE_010": 2,
    "MAJORITY_POSITIVE_010": 1,
}


@dataclass(frozen=True, slots=True)
class SpecialistDecision:
    target: native.NativeTarget
    memory_level: str
    classification: str
    posture: str
    mean_net_010_r: Decimal
    observations: int


@dataclass(frozen=True, slots=True)
class RuntimeTrade:
    entry_at: datetime
    exit_at: datetime
    side: str
    posture: str
    memory_level: str
    classification: str
    target_rank: int
    target_route: str
    gross_r: Decimal
    net_005_r: Decimal
    net_010_r: Decimal
    exit_reason: str
    trail_moves: int


def _single(root: Path, name: str) -> Path:
    matches = list(root.rglob(name))
    if len(matches) != 1:
        raise ValueError(f"expected exactly one {name}, got {len(matches)}")
    return matches[0]


def _load_cognitive(root: Path) -> dict[str, Any]:
    payload = json.loads(
        _single(
            root,
            "turtle-soup-audjpy-specialist-cognitive-memory.json",
        ).read_text()
    )
    if not isinstance(payload, dict):
        raise ValueError("specialist cognitive memory must be an object")
    return cast(dict[str, Any], payload)


def _load_targets(root: Path) -> dict[str, list[dict[str, Any]]]:
    result: dict[str, list[dict[str, Any]]] = defaultdict(list)
    path = _single(root, "TARGET_DESTINATION_LEDGER_V2.jsonl")
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                row = json.loads(line)
                result[str(row["episode_id"])].append(row)
    return dict(result)


def _query_row(
    setup: r3.Setup,
    *,
    target: native.NativeTarget,
    entry: Decimal,
) -> dict[str, Any]:
    side = setup.context.signal.side
    stop = setup.context.signal.protected_swing
    risk = entry - stop if side is Side.LONG else stop - entry
    reward = target.level - entry if side is Side.LONG else entry - target.level
    rr = Decimal(0) if risk <= 0 or reward <= 0 else reward / risk
    return {
        **specialist._setup_context(setup),
        "target_rank": target.rank,
        "target_route": target.route,
        "rr_bucket": r2._bucket(rr, native.RR_CUTS),
    }


def _decision_for_target(
    cognitive: dict[str, Any],
    setup: r3.Setup,
    *,
    target: native.NativeTarget,
    entry: Decimal,
) -> SpecialistDecision | None:
    row = _query_row(setup, target=target, entry=entry)
    item, level, _signature = specialist.resolve_authoritative(cognitive, row)
    if item is None or level is None:
        return None
    posture = item.get("preferred_posture")
    if posture is None:
        return None
    model = item["postures"][str(posture)]
    classification = str(model["classification"])
    if classification not in CLASS_PRIORITY:
        return None
    mean = Decimal(str(model["combined"]["mean_net_010_r"]))
    return SpecialistDecision(
        target=target,
        memory_level=level,
        classification=classification,
        posture=str(posture),
        mean_net_010_r=mean,
        observations=int(item["observations"]),
    )


def choose_decision(
    cognitive: dict[str, Any],
    setup: r3.Setup,
    *,
    ladder: Sequence[native.NativeTarget],
    entry: Decimal,
) -> SpecialistDecision | None:
    candidates = [
        decision
        for target in ladder
        if (
            decision := _decision_for_target(
                cognitive,
                setup,
                target=target,
                entry=entry,
            )
        )
        is not None
    ]
    if not candidates:
        return None

    def priority(
        decision: SpecialistDecision,
    ) -> tuple[int, int, Decimal, int, int]:
        return (
            LEVEL_PRIORITY[decision.memory_level],
            CLASS_PRIORITY[decision.classification],
            decision.mean_net_010_r,
            decision.observations,
            -decision.target.rank,
        )

    return max(candidates, key=priority)


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


def _simulate(
    setup: r3.Setup,
    *,
    decision: SpecialistDecision,
    ladder: Sequence[native.NativeTarget],
    entry_at: datetime,
    entry: Decimal,
    evidence: Any,
    opens: Sequence[datetime],
) -> RuntimeTrade | None:
    side = setup.context.signal.side
    initial_stop = setup.context.signal.protected_swing
    target = decision.target.level
    risk = entry - initial_stop if side is Side.LONG else initial_stop - entry
    reward = target - entry if side is Side.LONG else entry - target
    if risk <= 0 or reward <= 0:
        return None

    left = bisect.bisect_left(opens, entry_at)
    right = bisect.bisect_left(
        opens,
        min(entry_at + timedelta(hours=24), EVAL_CLOSE),
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
                    "GAP_TRAIL"
                    if current_stop != initial_stop
                    else "GAP_STOP"
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
                    "GAP_TRAIL"
                    if current_stop != initial_stop
                    else "GAP_STOP"
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
                "TRAIL_STOP"
                if current_stop != initial_stop
                else "STOP"
            )
            break
        if target_touch:
            exit_at = bar.closed_at
            exit_price = target
            exit_reason = "TARGET"
            break

        observed.append(bar)

        if (
            decision.posture != native.POSTURE_STATIC
            and decision.target.rank > 1
        ):
            for earlier in ladder[: decision.target.rank - 1]:
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
                        pending = (
                            earlier.level
                            if pending is None
                            else native._better_stop(side, pending, earlier.level)
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
    return RuntimeTrade(
        entry_at=entry_at,
        exit_at=exit_at,
        side=side.value,
        posture=decision.posture,
        memory_level=decision.memory_level,
        classification=decision.classification,
        target_rank=decision.target.rank,
        target_route=decision.target.route,
        gross_r=gross,
        net_005_r=gross - Decimal("0.05"),
        net_010_r=gross - Decimal("0.10"),
        exit_reason=exit_reason,
        trail_moves=trail_moves,
    )


def _stat(trades: Sequence[RuntimeTrade], attr: str) -> dict[str, Any]:
    if not trades:
        return {
            "trades": 0,
            "total_r": "0",
            "mean_r": "0",
            "profit_factor": None,
            "max_drawdown_r": "0",
            "max_losing_streak": 0,
        }
    values = [cast(Decimal, getattr(trade, attr)) for trade in trades]
    gains = sum((value for value in values if value > 0), Decimal(0))
    losses = -sum((value for value in values if value < 0), Decimal(0))
    equity = Decimal(0)
    peak = Decimal(0)
    drawdown = Decimal(0)
    losing = 0
    max_losing = 0
    for value in values:
        equity += value
        peak = max(peak, equity)
        drawdown = max(drawdown, peak - equity)
        if value < 0:
            losing += 1
            max_losing = max(max_losing, losing)
        else:
            losing = 0
    return {
        "trades": len(trades),
        "total_r": str(sum(values, Decimal(0))),
        "mean_r": str(sum(values, Decimal(0)) / Decimal(len(values))),
        "profit_factor": None if losses == 0 else str(gains / losses),
        "max_drawdown_r": str(drawdown),
        "max_losing_streak": max_losing,
    }


def run(
    raw_root: Path,
    target_root: Path,
    specialist_root: Path,
    output: Path,
) -> dict[str, Any]:
    evidence, provenance = journey.load_raw_m5(raw_root)
    if evidence.symbol != "AUDJPY" or int(provenance["retained_bars"]) != 745468:
        raise ValueError("unexpected AUDJPY corpus")

    report = json.loads(
        _single(
            specialist_root,
            "turtle-soup-audjpy-specialist-memory-report.json",
        ).read_text()
    )
    if report["identity"] != specialist.IDENTITY:
        raise ValueError("unexpected specialist memory identity")
    cognitive = _load_cognitive(specialist_root)
    target_rows = _load_targets(target_root)
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
    trades: list[RuntimeTrade] = []
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

        ladder = specialist._active_ladder(
            target_rows.get(episode_id, ()),
            at=entry_at,
            side=signal.side,
            entry=entry,
            tick=tick,
        )
        if not ladder:
            counts["ABSTAIN_NO_ACTIVE_DOL"] += 1
            continue

        decision = choose_decision(
            cognitive,
            setup,
            ladder=ladder,
            entry=entry,
        )
        if decision is None:
            counts["ABSTAIN_NO_AUTHORITATIVE_SPECIALIST_MEMORY"] += 1
            continue

        runtime = _simulate(
            setup,
            decision=decision,
            ladder=ladder,
            entry_at=entry_at,
            entry=entry,
            evidence=evidence,
            opens=opens,
        )
        if runtime is None:
            counts["ABSTAIN_INVALID_GEOMETRY"] += 1
            continue
        if runtime.entry_at < busy_until:
            counts["ABSTAIN_SINGLE_POSITION_BUSY"] += 1
            continue

        busy_until = runtime.exit_at
        if "TRAIL" in runtime.exit_reason:
            trailing_exit_at = runtime.exit_at
        trades.append(runtime)
        counts["EXECUTE"] += 1
        counts[f"LEVEL_{runtime.memory_level}"] += 1
        counts[f"CLASS_{runtime.classification}"] += 1
        counts[f"POSTURE_{runtime.posture}"] += 1
        counts[f"RANK_{runtime.target_rank}"] += 1

    def by(field: str) -> dict[str, Any]:
        values = sorted({str(getattr(trade, field)) for trade in trades})
        return {
            value: {
                "gross": _stat(
                    [trade for trade in trades if str(getattr(trade, field)) == value],
                    "gross_r",
                ),
                "net_005": _stat(
                    [trade for trade in trades if str(getattr(trade, field)) == value],
                    "net_005_r",
                ),
                "net_010": _stat(
                    [trade for trade in trades if str(getattr(trade, field)) == value],
                    "net_010_r",
                ),
            }
            for value in values
        }

    payload = {
        "schema": "qore.turtle_soup_audjpy_r26.specialist_memory_brain.v1",
        "identity": IDENTITY,
        "window": {
            "open": EVAL_OPEN.isoformat(),
            "close": EVAL_CLOSE.isoformat(),
            "duration_years": 2,
        },
        "decision_sources": {
            "strategy": "TURTLE_SOUP_AUDJPY",
            "specialist_memory": specialist.COGNITIVE_IDENTITY,
            "master_memory_remains_immutable": True,
            "r22_memory_used": False,
            "r23_memory_used": False,
            "r25_result_used": False,
        },
        "decision_contract": {
            "authoritative_levels": list(specialist.AUTHORITATIVE_LEVELS),
            "context_only_levels": list(specialist.CONTEXT_ONLY_LEVELS),
            "context_only_can_authorize": False,
            "actual_strategy_entry": True,
            "exact_protected_swing": True,
            "structural_rearm": True,
            "posture_from_specialist_memory": True,
            "target_from_active_cibo_dol_ladder": True,
        },
        "behavior": {
            "decision_counts": dict(counts),
            "gross": _stat(trades, "gross_r"),
            "net_005": _stat(trades, "net_005_r"),
            "net_010": _stat(trades, "net_010_r"),
            "exit_reason_counts": dict(
                Counter(trade.exit_reason for trade in trades)
            ),
            "trail_moves": sum(trade.trail_moves for trade in trades),
            "by_memory_level": by("memory_level"),
            "by_classification": by("classification"),
            "by_posture": by("posture"),
            "by_target_rank": by("target_rank"),
            "by_target_route": by("target_route"),
        },
        "reproduction": {
            "retained_bars": int(provenance["retained_bars"]),
            "setups_10y": len(setups),
            "funnel": funnel,
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
    }
    output.mkdir(parents=True, exist_ok=True)
    (output / "r26-specialist-memory-brain-report.json").write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n"
    )
    (output / "r26-specialist-memory-brain-trades.json").write_text(
        json.dumps(
            [
                {
                    "entry_at": trade.entry_at.isoformat(),
                    "exit_at": trade.exit_at.isoformat(),
                    "side": trade.side,
                    "posture": trade.posture,
                    "memory_level": trade.memory_level,
                    "classification": trade.classification,
                    "target_rank": trade.target_rank,
                    "target_route": trade.target_route,
                    "gross_r": str(trade.gross_r),
                    "net_005_r": str(trade.net_005_r),
                    "net_010_r": str(trade.net_010_r),
                    "exit_reason": trade.exit_reason,
                    "trail_moves": trade.trail_moves,
                }
                for trade in trades
            ],
            indent=2,
            sort_keys=True,
        )
        + "\n"
    )
    return payload


def main() -> None:
    if len(sys.argv) != 5:
        raise SystemExit(
            "usage: module RAW_ROOT TARGET_ROOT SPECIALIST_MEMORY_ROOT OUTPUT_DIR"
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
