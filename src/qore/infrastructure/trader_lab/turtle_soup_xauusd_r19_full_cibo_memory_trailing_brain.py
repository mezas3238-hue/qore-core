"""R19 full-CIBO-memory + structural trailing brain for Turtle Soup XAUUSD.

Consumed-evidence research only.

R19 fixes two architectural gaps identified after R18:
1. The trader consumes the official 10Y CIBO XAUUSD market-intelligence dossier
   through the governed CiboMemoryStore, not only lab-derived R16/R17 memories.
2. Position protection is dynamic. The initial stop remains the exact Protected
   Swing, but causally confirmed post-entry structure can only improve the stop:
   - a confirmed M5 swing beyond entry can lock capital/profit;
   - when an intermediate active CIBO DOL is conquered on the way to a farther
     target, the stop can lock that conquered liquidity level on the next bar.

No trailing move is effective on the same bar that creates its evidence. This
preserves causal ordering and avoids impossible intrabar knowledge.

Two sequential variants are produced from the same decision engine:
FULL_CIBO_STATIC and FULL_CIBO_TRAILING. This isolates the operational effect
of trailing from the effect of adding the full CIBO market memory.
"""
from __future__ import annotations

import bisect
import json
import sys
from collections import Counter
from collections.abc import Sequence
from dataclasses import asdict, dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any

from qore.infrastructure.trader_lab import (
    cibo_market_atlas_journey_extractor_v1 as journey,
)
from qore.infrastructure.trader_lab import (
    cibo_xauusd_trader_memory_bridge_v1 as cibo_memory,
)
from qore.infrastructure.trader_lab import turtle_soup_xauusd_r1 as r1
from qore.infrastructure.trader_lab import (
    turtle_soup_xauusd_r13_autonomous_2y_behavior_replay as recognition,
)
from qore.infrastructure.trader_lab import turtle_soup_xauusd_r3_cibo_journey as r3
from qore.infrastructure.trader_lab import (
    turtle_soup_xauusd_r3_cibo_journey_binding_repair as repair,
)
from qore.infrastructure.trader_lab import (
    turtle_soup_xauusd_r5_regime_journey_validity_forensics as r5,
)
from qore.infrastructure.trader_lab import (
    turtle_soup_xauusd_r11_situation_recognition_engine as r11,
)
from qore.infrastructure.trader_lab import (
    turtle_soup_xauusd_r15_cibo_first_market_brain as r15,
)
from qore.infrastructure.trader_lab import (
    turtle_soup_xauusd_r18_memory_driven_cibo_brain as r18,
)
from qore.infrastructure.trader_lab.ict_turtle_soup_r4_source_exact import Side

IDENTITY = "TURTLE_SOUP_XAUUSD_R19_FULL_CIBO_MEMORY_TRAILING_BRAIN_V1"
EVAL_OPEN = datetime(2024, 9, 17, tzinfo=UTC)
EVAL_CLOSE = datetime(2026, 9, 17, tzinfo=UTC)

VARIANT_STATIC = "FULL_CIBO_STATIC"
VARIANT_TRAILING = "FULL_CIBO_TRAILING"

TRAIL_PROTECTED_SWING = "CONFIRMED_M5_PROTECTED_SWING"
TRAIL_DOL_LOCK = "CONQUERED_DOL_LOCK"


@dataclass(frozen=True, slots=True)
class TrailEvent:
    occurred_at: datetime
    reason: str
    previous_stop: Decimal
    new_stop: Decimal

    def as_json(self) -> dict[str, str]:
        return {
            "occurred_at": self.occurred_at.isoformat(),
            "reason": self.reason,
            "previous_stop": str(self.previous_stop),
            "new_stop": str(self.new_stop),
        }


@dataclass(frozen=True, slots=True)
class Simulation:
    trade: r3.RoutedTrade
    trail_events: tuple[TrailEvent, ...]


def _find(root: Path, name: str) -> Path:
    direct = root / name
    if direct.exists():
        return direct
    matches = list(root.rglob(name))
    if len(matches) != 1:
        raise ValueError(f"expected exactly one {name}, got {len(matches)}")
    return matches[0]


def _improves_stop(
    *,
    side: Side,
    previous: Decimal,
    candidate: Decimal,
    target: Decimal,
) -> bool:
    if side is Side.LONG:
        return previous < candidate < target
    return target < candidate < previous


def _better_stop(side: Side, first: Decimal, second: Decimal) -> Decimal:
    return max(first, second) if side is Side.LONG else min(first, second)


def _confirmed_swing_candidate(
    *,
    side: Side,
    bars: Sequence[Any],
    entry: Decimal,
    target: Decimal,
) -> Decimal | None:
    """Return a causally confirmed 3-bar swing that already protects capital.

    The middle bar is only known as a swing after the right-hand bar closes.
    Therefore the caller must activate this stop no earlier than the next bar.
    """
    if len(bars) < 3:
        return None
    left, middle, right = bars[-3], bars[-2], bars[-1]
    if side is Side.LONG:
        if middle.low < left.low and middle.low < right.low:
            level = Decimal(str(middle.low))
            if entry < level < target:
                return level
        return None
    if middle.high > left.high and middle.high > right.high:
        level = Decimal(str(middle.high))
        if target < level < entry:
            return level
    return None


def _memory_target_depth(
    *,
    setup: r3.Setup,
    regime: dict[str, str],
    ladder_size: int,
    memory: cibo_memory.CiboXauusdMemoryContext,
) -> tuple[int, str]:
    """Blend R18 structural depth with the official CIBO association memory.

    E1 dossier memory never decides entry permission. It may only make target
    depth more conservative or confirm a structurally supported extension.
    """
    rank, reason = r18._target_depth_decision(
        setup=setup,
        regime=regime,
        ladder_size=ladder_size,
    )
    if rank == 2 and memory.state == "CAUTIOUS":
        return 1, "RANK1_FULL_CIBO_MEMORY_CAUTION"
    if (
        rank == 1
        and memory.state == "SUPPORTIVE"
        and ladder_size >= 2
        and r18._displacement_context(setup)
        and setup.context.session in r18.EXTENSION_SESSIONS
        and setup.context.weekday != "Friday"
    ):
        return 2, "RANK2_FULL_CIBO_MEMORY_SUPPORTIVE_DISPLACEMENT"
    return rank, f"{reason}_FULL_CIBO_{memory.state}"


def _target_touched(
    *,
    side: Side,
    level: Decimal,
    bar: Any,
) -> bool:
    if side is Side.LONG:
        return bool(bar.open >= level or bar.high >= level)
    return bool(bar.open <= level or bar.low <= level)


def _stop_touched(
    *,
    side: Side,
    stop: Decimal,
    bar: Any,
) -> bool:
    if side is Side.LONG:
        return bool(bar.open <= stop or bar.low <= stop)
    return bool(bar.open >= stop or bar.high >= stop)


def _gross_at_price(
    *,
    side: Side,
    entry: Decimal,
    stop_initial: Decimal,
    price: Decimal,
) -> Decimal:
    risk = entry - stop_initial if side is Side.LONG else stop_initial - entry
    if risk <= 0:
        raise ValueError("non-positive initial risk")
    return (price - entry) / risk if side is Side.LONG else (entry - price) / risk


def _simulate_trailing(
    setup: r3.Setup,
    *,
    entry_at: datetime,
    entry: Decimal,
    target_row: r3.TargetCandidate,
    target_rank: int,
    ladder: Sequence[r3.TargetCandidate],
    evidence: Any,
    opens: Sequence[datetime],
) -> Simulation | None:
    side = setup.context.signal.side
    initial_stop = setup.context.signal.protected_swing
    target = target_row.level
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
    pending_stop: Decimal | None = None
    pending_reason: str | None = None
    trail_events: list[TrailEvent] = []
    observed_bars: list[Any] = []
    touched_intermediate: set[int] = set()

    exit_at = path[-1].closed_at
    exit_price = path[-1].close
    exit_reason = "TIME_24H"
    gross = _gross_at_price(
        side=side,
        entry=entry,
        stop_initial=initial_stop,
        price=exit_price,
    )

    for bar in path:
        # Evidence created on the prior completed bar becomes actionable only now.
        if (
            pending_stop is not None
            and _improves_stop(
                side=side,
                previous=current_stop,
                candidate=pending_stop,
                target=target,
            )
        ):
            previous = current_stop
            current_stop = pending_stop
            trail_events.append(
                TrailEvent(
                    occurred_at=bar.opened_at,
                    reason=pending_reason or "STRUCTURAL_TRAIL",
                    previous_stop=previous,
                    new_stop=current_stop,
                )
            )
        pending_stop = None
        pending_reason = None

        if side is Side.LONG:
            if bar.open <= current_stop:
                exit_at = bar.opened_at
                exit_price = bar.open
                exit_reason = (
                    "GAP_TRAILING_STOP"
                    if current_stop != initial_stop
                    else "GAP_STOP"
                )
                gross = _gross_at_price(
                    side=side,
                    entry=entry,
                    stop_initial=initial_stop,
                    price=exit_price,
                )
                break
            if bar.open >= target:
                exit_at = bar.opened_at
                exit_price = target
                exit_reason = "GAP_TARGET_CAPPED"
                gross = reward / risk
                break
            stop_touch = bar.low <= current_stop
            target_touch = bar.high >= target
        else:
            if bar.open >= current_stop:
                exit_at = bar.opened_at
                exit_price = bar.open
                exit_reason = (
                    "GAP_TRAILING_STOP"
                    if current_stop != initial_stop
                    else "GAP_STOP"
                )
                gross = _gross_at_price(
                    side=side,
                    entry=entry,
                    stop_initial=initial_stop,
                    price=exit_price,
                )
                break
            if bar.open <= target:
                exit_at = bar.opened_at
                exit_price = target
                exit_reason = "GAP_TARGET_CAPPED"
                gross = reward / risk
                break
            stop_touch = bar.high >= current_stop
            target_touch = bar.low <= target

        if stop_touch and target_touch:
            exit_at = bar.closed_at
            exit_price = current_stop
            exit_reason = (
                "TRAILING_STOP_FIRST"
                if current_stop != initial_stop
                else "STOP_FIRST"
            )
            gross = _gross_at_price(
                side=side,
                entry=entry,
                stop_initial=initial_stop,
                price=exit_price,
            )
            break
        if stop_touch:
            exit_at = bar.closed_at
            exit_price = current_stop
            exit_reason = (
                "TRAILING_STOP"
                if current_stop != initial_stop
                else "STOP"
            )
            gross = _gross_at_price(
                side=side,
                entry=entry,
                stop_initial=initial_stop,
                price=exit_price,
            )
            break
        if target_touch:
            exit_at = bar.closed_at
            exit_price = target
            exit_reason = "TARGET"
            gross = reward / risk
            break

        observed_bars.append(bar)

        # Causal DOL lock: a conquered intermediate liquidity level can only
        # protect from the next bar onward.
        if target_rank > 1:
            for rank, candidate in enumerate(ladder[: target_rank - 1], start=1):
                if rank in touched_intermediate:
                    continue
                if _target_touched(side=side, level=candidate.level, bar=bar):
                    touched_intermediate.add(rank)
                    candidate_stop = candidate.level
                    if _improves_stop(
                        side=side,
                        previous=current_stop,
                        candidate=candidate_stop,
                        target=target,
                    ):
                        if pending_stop is None:
                            pending_stop = candidate_stop
                            pending_reason = TRAIL_DOL_LOCK
                        else:
                            better = _better_stop(side, pending_stop, candidate_stop)
                            if better != pending_stop:
                                pending_stop = better
                                pending_reason = TRAIL_DOL_LOCK

        swing = _confirmed_swing_candidate(
            side=side,
            bars=observed_bars,
            entry=entry,
            target=target,
        )
        if (
            swing is not None
            and _improves_stop(
                side=side,
                previous=current_stop,
                candidate=swing,
                target=target,
            )
        ):
            if pending_stop is None:
                pending_stop = swing
                pending_reason = TRAIL_PROTECTED_SWING
            else:
                better = _better_stop(side, pending_stop, swing)
                if better != pending_stop:
                    pending_stop = better
                    pending_reason = TRAIL_PROTECTED_SWING

    trade = r3.RoutedTrade(
        source_timeframe=setup.context.timeframe,
        side=side.value,
        entry_mode="NEXT_SOURCE_OPEN",
        target_route=r15._candidate_route(target_row),
        episode_id=target_row.episode_id,
        entry_at=entry_at,
        exit_at=exit_at,
        entry=entry,
        stop=initial_stop,
        target=target,
        target_kind=target_row.kind,
        target_timeframe=target_row.timeframe,
        gross_r=gross,
        primary_net_r=gross - r3.PRIMARY_FRICTION_R,
        stress_net_r=gross - r3.STRESS_FRICTION_R,
        exit_reason=exit_reason,
        session_bucket=setup.context.signal.session_bucket,
        prior_body_alignment=setup.context.signal.prior_body_alignment,
    )
    return Simulation(trade=trade, trail_events=tuple(trail_events))


def _stats(
    trades: Sequence[r3.RoutedTrade],
    attr: str = "primary_net_r",
) -> dict[str, Any]:
    return r3._stat(trades, attr)


def _variant_summary(executed: Sequence[dict[str, Any]]) -> dict[str, Any]:
    trades = [item["trade"] for item in executed]
    trail_events = [
        event
        for item in executed
        for event in item.get("trail_events", ())
    ]
    trail_exit_reasons = {
        "TRAILING_STOP",
        "GAP_TRAILING_STOP",
        "TRAILING_STOP_FIRST",
    }
    trailing_exits = [
        trade for trade in trades if trade.exit_reason in trail_exit_reasons
    ]
    return {
        "executed_trades": len(trades),
        "gross": _stats(trades, "gross_r"),
        "primary_005r": _stats(trades, "primary_net_r"),
        "stress_010r": _stats(trades, "stress_net_r"),
        "trail_moves": len(trail_events),
        "positions_with_trail": sum(
            bool(item.get("trail_events")) for item in executed
        ),
        "trail_reason_counts": dict(
            Counter(event.reason for event in trail_events)
        ),
        "trailing_stop_exits": len(trailing_exits),
        "trailing_exits_gross_nonnegative": sum(
            trade.gross_r >= 0 for trade in trailing_exits
        ),
        "exit_reason_counts": dict(
            Counter(trade.exit_reason for trade in trades)
        ),
        "memory_state_counts": dict(
            Counter(str(item["memory_state"]) for item in executed)
        ),
        "target_rank_counts": dict(
            Counter(str(item["target_ladder_rank"]) for item in executed)
        ),
        "brain_reason_counts": dict(
            Counter(str(item["brain_reason"]) for item in executed)
        ),
    }


def _run_variant(
    *,
    variant: str,
    setups: Sequence[r3.Setup],
    evidence: Any,
    opens: Sequence[datetime],
    episodes: dict[str, list[r3.TargetCandidate]],
    source_index: dict[tuple[datetime, str, str, Decimal], str],
    recognition_ctx: dict[str, Any],
    memory_store: Any,
) -> tuple[list[dict[str, Any]], dict[str, int]]:
    d1 = recognition_ctx["d1_regime"]
    h4 = recognition_ctx["h4_regime"]
    counts: Counter[str] = Counter()
    executed: list[dict[str, Any]] = []
    busy_until = EVAL_OPEN

    for setup in setups:
        signal = setup.context.signal
        if not (EVAL_OPEN <= signal.entry_at < EVAL_CLOSE):
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
            counts["ABSTAIN_NO_CAUSAL_CIBO_EPISODE"] += 1
            continue

        fill = r3._entry(setup, evidence, opens, "NEXT_SOURCE_OPEN")
        if fill is None:
            counts["ABSTAIN_NO_IMMEDIATE_FILL"] += 1
            continue
        entry_at, entry = fill

        target_rows = episodes[episode_id]
        active = r15._all_active_targets(
            target_rows,
            at=entry_at,
            side=signal.side,
            anchor=entry,
        )
        ladder = r15._distinct_target_ladder(active, anchor=entry)
        if not ladder:
            counts["ABSTAIN_NO_ACTIVE_DOL"] += 1
            continue

        regime = r5._regime_features(
            {"entry_at": entry_at.isoformat(), "side": signal.side.value},
            d1,
            h4,
        )
        posture = r15._market_posture(regime)

        provisional = r15._provisional_trade(
            setup,
            entry_mode="NEXT_SOURCE_OPEN",
            entry_at=entry_at,
            entry=entry,
            target=ladder[0],
        )
        assessment, _recognition_row = recognition._assess(
            setup=setup,
            trade=provisional,
            evidence=evidence,
            opens=opens,
            episodes=episodes,
            ctx=recognition_ctx,
        )
        if assessment.state is r11.SituationState.KNOWN_INVALID:
            counts["ABSTAIN_KNOWN_INVALID"] += 1
            continue
        if assessment.state is r11.SituationState.CONFLICTED:
            counts["ABSTAIN_CONFLICTED"] += 1
            continue
        if (
            setup.context.protected_risk_range_bucket
            in r18.LOW_CAPACITY_RISK_BUCKETS
        ):
            counts["ABSTAIN_LOW_CAPACITY_PROTECTED_SWING"] += 1
            continue

        memory = cibo_memory.context_memory(
            memory_store,
            timeframe=setup.context.timeframe,
            side=signal.side.value,
            session=setup.context.session,
            prior_body_alignment=setup.context.prior_body_alignment,
            fvg_before_entry=setup.context.fvg_before_entry,
            exact_equal_liquidity=setup.context.exact_equal_liquidity,
        )
        rank, reason = _memory_target_depth(
            setup=setup,
            regime=regime,
            ladder_size=len(ladder),
            memory=memory,
        )
        target = ladder[rank - 1]

        if variant == VARIANT_STATIC:
            trade = r15._simulate_selected(
                setup,
                entry_mode="NEXT_SOURCE_OPEN",
                entry_at=entry_at,
                entry=entry,
                target_row=target,
                evidence=evidence,
                opens=opens,
            )
            if trade is None:
                counts["ABSTAIN_INVALID_EXECUTION_GEOMETRY"] += 1
                continue
            simulation = Simulation(trade=trade, trail_events=())
        elif variant == VARIANT_TRAILING:
            sim = _simulate_trailing(
                setup,
                entry_at=entry_at,
                entry=entry,
                target_row=target,
                target_rank=rank,
                ladder=ladder,
                evidence=evidence,
                opens=opens,
            )
            if sim is None:
                counts["ABSTAIN_INVALID_EXECUTION_GEOMETRY"] += 1
                continue
            simulation = sim
        else:
            raise ValueError(f"unsupported R19 variant: {variant}")

        trade = simulation.trade
        if trade.entry_at < busy_until:
            counts["ABSTAIN_SINGLE_POSITION_BUSY"] += 1
            continue

        busy_until = trade.exit_at
        counts["EXECUTE"] += 1
        executed.append(
            {
                "trade": trade,
                "trail_events": simulation.trail_events,
                "brain_reason": reason,
                "target_ladder_rank": rank,
                "memory_state": memory.state,
                "memory_support_votes": memory.support_votes,
                "memory_caution_votes": memory.caution_votes,
                "memory_mixed_votes": memory.mixed_votes,
                "memory_dimensions": [
                    {"dimension": name, "value": value}
                    for name, value, _summary in memory.dimensions
                ],
                "intelligence_state": assessment.state.value,
                "intelligence_mechanism": assessment.mechanism_code,
                "brain_posture": posture,
                "weekday": setup.context.weekday,
                "session": setup.context.session,
                "regime": regime,
            }
        )
    return executed, dict(counts)


def _json_item(item: dict[str, Any]) -> dict[str, Any]:
    trade: r3.RoutedTrade = item["trade"]
    raw = asdict(trade)
    converted = {
        key: (
            value.isoformat()
            if isinstance(value, datetime)
            else str(value)
            if isinstance(value, Decimal)
            else value
        )
        for key, value in raw.items()
    }
    converted.update(
        {
            "trail_events": [
                event.as_json() for event in item.get("trail_events", ())
            ],
            "brain_reason": item["brain_reason"],
            "target_ladder_rank": item["target_ladder_rank"],
            "memory_state": item["memory_state"],
            "memory_support_votes": item["memory_support_votes"],
            "memory_caution_votes": item["memory_caution_votes"],
            "memory_mixed_votes": item["memory_mixed_votes"],
            "memory_dimensions": item["memory_dimensions"],
            "intelligence_state": item["intelligence_state"],
            "intelligence_mechanism": item["intelligence_mechanism"],
            "brain_posture": item["brain_posture"],
            "weekday": item["weekday"],
            "session": item["session"],
        }
    )
    return converted


def _paired_comparison(
    static: Sequence[dict[str, Any]],
    trailing: Sequence[dict[str, Any]],
) -> dict[str, Any]:
    def key(item: dict[str, Any]) -> tuple[str, datetime, Decimal]:
        trade: r3.RoutedTrade = item["trade"]
        return (trade.episode_id, trade.entry_at, trade.target)

    s = {key(item): item["trade"] for item in static}
    t = {key(item): item["trade"] for item in trailing}
    shared = sorted(set(s) & set(t), key=lambda x: (x[1], x[0], x[2]))
    gross_delta = sum(
        (t[k].gross_r - s[k].gross_r for k in shared),
        Decimal(0),
    )
    improved = sum(t[k].gross_r > s[k].gross_r for k in shared)
    worsened = sum(t[k].gross_r < s[k].gross_r for k in shared)
    unchanged = len(shared) - improved - worsened
    return {
        "shared_same_entry_target": len(shared),
        "gross_r_delta_trailing_minus_static": str(gross_delta),
        "improved": improved,
        "worsened": worsened,
        "unchanged": unchanged,
    }


def run(
    source_root: Path,
    target_root: Path,
    dossier_root: Path,
    r18_root: Path,
    output: Path,
) -> dict[str, Any]:
    evidence, provenance = journey.load_raw_m5(source_root)
    if evidence.symbol != r3.SYMBOL or int(provenance["retained_bars"]) != 707716:
        raise ValueError("unexpected XAUUSD corpus")

    memory_store, dossier_manifest = cibo_memory.build_memory_store(dossier_root)
    memory_manifest = cibo_memory.memory_store_manifest(memory_store)

    r18_report = json.loads(
        _find(r18_root, "r18-memory-brain-report.json").read_text()
    )
    if r18_report["identity"] != r18.IDENTITY:
        raise ValueError("unexpected R18 reference identity")

    episodes_raw, source_index = repair._load_targets_fail_closed(target_root)
    episodes: dict[str, list[r3.TargetCandidate]] = {
        key: list(value) for key, value in episodes_raw.items()
    }

    original_open, original_close = r1.EVAL_OPEN, r1.EVAL_CLOSE
    try:
        r1.EVAL_OPEN, r1.EVAL_CLOSE = r3.EVAL_OPEN, r3.EVAL_CLOSE
        setups, funnel = r3._build_setups(evidence)
    finally:
        r1.EVAL_OPEN, r1.EVAL_CLOSE = original_open, original_close

    opens = tuple(bar.opened_at for bar in evidence.bars)
    recognition_ctx = recognition._prepare_recognition_context(evidence)

    static, static_counts = _run_variant(
        variant=VARIANT_STATIC,
        setups=setups,
        evidence=evidence,
        opens=opens,
        episodes=episodes,
        source_index=source_index,
        recognition_ctx=recognition_ctx,
        memory_store=memory_store,
    )
    trailing, trailing_counts = _run_variant(
        variant=VARIANT_TRAILING,
        setups=setups,
        evidence=evidence,
        opens=opens,
        episodes=episodes,
        source_index=source_index,
        recognition_ctx=recognition_ctx,
        memory_store=memory_store,
    )

    static_summary = _variant_summary(static)
    trailing_summary = _variant_summary(trailing)
    comparison = _paired_comparison(static, trailing)

    payload = {
        "schema": "qore.turtle_soup_xauusd_r19.full_cibo_memory_trailing_brain.v1",
        "identity": IDENTITY,
        "window": {
            "open": EVAL_OPEN.isoformat(),
            "close": EVAL_CLOSE.isoformat(),
            "duration_years": 2,
        },
        "full_cibo_memory": {
            "bridge": memory_manifest,
            "dossier_manifest": dossier_manifest,
            "official_dossier_run_id": cibo_memory.DOSSIER_RUN_ID,
            "official_dossier_artifact_id": cibo_memory.DOSSIER_ARTIFACT_ID,
            "official_dossier_digest": cibo_memory.DOSSIER_DIGEST,
            "memory_store_used_by_decision_engine": True,
            "transient_llm_context_used_as_memory": False,
        },
        "trailing_contract": {
            "initial_stop": "EXACT_PROTECTED_SWING",
            "stop_can_only_improve": True,
            "stop_can_never_be_widened": True,
            "confirmed_m5_swing_requires_right_bar_close": True,
            "new_stop_effective_no_earlier_than_next_bar": True,
            "intermediate_dol_can_lock_conquered_level": True,
            "same_bar_future_knowledge_used": False,
            "runtime_lifecycle_compatibility": (
                "MONOTONIC_TARGET_NONCROSSING_CLIENT_POSITION_LIFECYCLE_SEMANTICS"
            ),
        },
        "decision_contract": {
            "r3_pnl_router_used": False,
            "r11_known_invalid_respected": True,
            "r11_conflicted_respected": True,
            "full_cibo_e1_memory_controls_entry_permission": False,
            "full_cibo_e1_memory_can_adjust_target_depth": True,
            "low_capacity_protected_swing_is_widened": False,
            "fixed_r_target_used": False,
            "target_is_active_cibo_dol": True,
            "pnl_score_used": False,
            "profit_probability_used": False,
            "year_as_trade_feature": False,
            "fresh_holdout_used": False,
        },
        "reproduction": {
            "retained_bars": int(provenance["retained_bars"]),
            "setups_10y": len(setups),
            "ambiguous_bindings_fail_closed": repair._LAST_AMBIGUOUS_KEYS,
        },
        "reference_r18": {
            "run_id": 35290461593,
            "artifact_id": 10525534199,
            "identity": r18_report["identity"],
            "behavior": r18_report["behavior"],
            "economics": r18_report["economics"],
        },
        "variants": {
            VARIANT_STATIC: {
                "decision_counts": static_counts,
                **static_summary,
            },
            VARIANT_TRAILING: {
                "decision_counts": trailing_counts,
                **trailing_summary,
            },
        },
        "trailing_vs_static_same_trade": comparison,
        "governance": {
            "research_only": True,
            "consumed_10y_memory_used": True,
            "same_2y_consumed_replay": True,
            "fresh_holdout_consumed": False,
            "dossier_evidence_tier": "E1_ASSOCIATION_ONLY",
            "rule_promoted": False,
            "demo_eligible": False,
            "live_authorized": False,
            "real_capital_authorized": False,
            "production_authorized": False,
        },
        "funnel": funnel,
    }

    output.mkdir(parents=True, exist_ok=True)
    (output / "r19-full-cibo-trailing-report.json").write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n"
    )
    (output / "r19-full-cibo-static-trades.json").write_text(
        json.dumps([_json_item(item) for item in static], indent=2, sort_keys=True)
        + "\n"
    )
    (output / "r19-full-cibo-trailing-trades.json").write_text(
        json.dumps([_json_item(item) for item in trailing], indent=2, sort_keys=True)
        + "\n"
    )
    return payload


def main() -> None:
    if len(sys.argv) != 6:
        raise SystemExit(
            "usage: module SOURCE_ROOT TARGET_ROOT DOSSIER_ROOT R18_ROOT OUTPUT_DIR"
        )
    print(
        json.dumps(
            run(
                Path(sys.argv[1]),
                Path(sys.argv[2]),
                Path(sys.argv[3]),
                Path(sys.argv[4]),
                Path(sys.argv[5]),
            ),
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
