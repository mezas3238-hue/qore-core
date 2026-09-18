"""R24 friction-resolved subtype brain for Turtle Soup XAUUSD.

Consumed-evidence research characterization only.

R24 consumes frozen R23 memories:
- hierarchical CAUTIOUS/MIXED subtype resolution;
- selected-DOL 0.10R friction-resilience memory.

Decision flow:
1. preserve R20 structural rearm;
2. resolve SUPPORTIVE directly; resolve CAUTIOUS/MIXED with the most-specific
   stable R23 subtype ancestor;
3. preserve R11 KNOWN_INVALID/CONFLICTED and low-capacity abstentions;
4. obtain R19's structural base target depth;
5. test the base DOL against frozen R23 resilience;
6. if base is not resilient, test the alternate available rank (1 <-> 2);
7. use a resilient target if one exists, otherwise abstain;
8. preserve R20 adaptive trailing.

No fresh holdout, realized-PnL target selection, or post-hoc economic ranking is
performed inside this replay.
"""
from __future__ import annotations

import json
import sys
from collections import Counter
from collections.abc import Sequence
from dataclasses import asdict
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any, cast

from qore.infrastructure.trader_lab import (
    cibo_market_atlas_journey_extractor_v1 as journey,
)
from qore.infrastructure.trader_lab import (
    cibo_xauusd_trader_memory_bridge_v1 as cibo_memory,
)
from qore.infrastructure.trader_lab import turtle_soup_xauusd_r1 as r1
from qore.infrastructure.trader_lab import turtle_soup_xauusd_r2_cibo_full as r2
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
from qore.infrastructure.trader_lab import (
    turtle_soup_xauusd_r19_full_cibo_memory_trailing_brain as r19,
)
from qore.infrastructure.trader_lab import (
    turtle_soup_xauusd_r20_adaptive_cibo_trailing_rearm as r20,
)
from qore.infrastructure.trader_lab import (
    turtle_soup_xauusd_r21_cautious_mixed_subtype_memory as r21,
)
from qore.infrastructure.trader_lab import (
    turtle_soup_xauusd_r23_hierarchical_friction_memory as r23,
)

IDENTITY = "TURTLE_SOUP_XAUUSD_R24_FRICTION_RESOLVED_FULL_CIBO_BRAIN_V1"
EVAL_OPEN = datetime(2024, 9, 17, tzinfo=UTC)
EVAL_CLOSE = datetime(2026, 9, 17, tzinfo=UTC)


def _find(root: Path, name: str) -> Path:
    direct = root / name
    if direct.exists():
        return direct
    matches = list(root.rglob(name))
    if len(matches) != 1:
        raise ValueError(f"expected exactly one {name}, got {len(matches)}")
    return matches[0]


def _load_r23(
    root: Path,
) -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, Any]], dict[str, Any]]:
    report = cast(
        dict[str, Any],
        json.loads(_find(root, "r23-hierarchical-friction-report.json").read_text()),
    )
    if report["identity"] != r23.IDENTITY:
        raise ValueError("unexpected R23 identity")
    subtype = cast(
        dict[str, dict[str, Any]],
        json.loads(_find(root, "r23-subtype-hierarchy.json").read_text()),
    )
    resilience = cast(
        dict[str, dict[str, Any]],
        json.loads(
            _find(root, "r23-friction-resilience-memory.json").read_text()
        ),
    )
    return subtype, resilience, report


def _subtype_row(
    *,
    memory_state: str,
    setup: r3.Setup,
    posture: str,
) -> dict[str, Any]:
    return {
        "memory_state": memory_state,
        "source_timeframe": setup.context.timeframe,
        "fvg_before_entry": setup.context.fvg_before_entry,
        "cisd_progress_bucket": setup.context.cisd_progress_bucket,
        "protected_risk_range_bucket": setup.context.protected_risk_range_bucket,
        "source_range_state_bucket": setup.context.source_range_state_bucket,
        "brain_posture": posture,
    }


def _entry_policy(
    *,
    memory_state: str,
    setup: r3.Setup,
    posture: str,
    subtype_hierarchy: dict[str, dict[str, Any]],
) -> tuple[str | None, str, str | None]:
    if memory_state == "SUPPORTIVE":
        return "NEXT_SOURCE_OPEN", "SUPPORTIVE_EXECUTE", None

    classification, level, _signature = r23.resolve_subtype(
        subtype_hierarchy,
        _subtype_row(
            memory_state=memory_state,
            setup=setup,
            posture=posture,
        ),
    )
    if classification == r21.RECOVERABLE:
        return (
            "NEXT_SOURCE_OPEN",
            "HIERARCHICAL_RECOVERABLE_EXECUTE",
            level,
        )
    if classification == r21.WAIT:
        return (
            "CISD_THRESHOLD_RETEST",
            "HIERARCHICAL_WAIT_FOR_CONFIRMATION",
            level,
        )
    if classification == r21.ABSTAIN:
        return None, "HIERARCHICAL_ABSTAIN_STRUCTURAL", level
    return None, "HIERARCHICAL_UNRESOLVED_WAIT_NEW_EVENT", level


def _planned_rr(
    *,
    setup: r3.Setup,
    entry: Decimal,
    target: r3.TargetCandidate,
) -> Decimal:
    side = setup.context.signal.side
    stop = setup.context.signal.protected_swing
    risk = entry - stop if side.value == "long" else stop - entry
    reward = target.level - entry if side.value == "long" else entry - target.level
    if risk <= 0 or reward <= 0:
        return Decimal(0)
    return reward / risk


def _resilience_row(
    *,
    memory_state: str,
    setup: r3.Setup,
    rank: int,
    target: r3.TargetCandidate,
    planned_rr: Decimal,
) -> dict[str, Any]:
    return {
        "memory_state": memory_state,
        "source_timeframe": setup.context.timeframe,
        "target_rank": rank,
        "target_route": r15._candidate_route(target),
        "planned_rr_bucket": r2._bucket(planned_rr, r23.RR_CUTS),
    }


def _rank_resilience(
    *,
    memory_state: str,
    setup: r3.Setup,
    rank: int,
    target: r3.TargetCandidate,
    entry: Decimal,
    resilience_hierarchy: dict[str, dict[str, Any]],
) -> tuple[str, str | None, Decimal]:
    planned_rr = _planned_rr(setup=setup, entry=entry, target=target)
    if planned_rr <= 0:
        return r23.NON_RESILIENT, None, planned_rr
    classification, level, _signature = r23.resolve_resilience(
        resilience_hierarchy,
        _resilience_row(
            memory_state=memory_state,
            setup=setup,
            rank=rank,
            target=target,
            planned_rr=planned_rr,
        ),
    )
    return classification, level, planned_rr


def choose_target_rank(
    *,
    base_rank: int,
    ladder: Sequence[r3.TargetCandidate],
    memory_state: str,
    setup: r3.Setup,
    entry: Decimal,
    resilience_hierarchy: dict[str, dict[str, Any]],
) -> tuple[int | None, str, dict[str, Any]]:
    available = [rank for rank in (1, 2) if rank <= len(ladder)]
    if base_rank not in available:
        base_rank = available[0]

    diagnostics: dict[str, Any] = {}
    for rank in available:
        classification, level, planned_rr = _rank_resilience(
            memory_state=memory_state,
            setup=setup,
            rank=rank,
            target=ladder[rank - 1],
            entry=entry,
            resilience_hierarchy=resilience_hierarchy,
        )
        diagnostics[str(rank)] = {
            "classification": classification,
            "level": level,
            "planned_rr": str(planned_rr),
            "target_route": r15._candidate_route(ladder[rank - 1]),
        }

    if diagnostics[str(base_rank)]["classification"] == r23.RESILIENT:
        return base_rank, "BASE_TARGET_RESILIENT_010", diagnostics

    alternate = 2 if base_rank == 1 else 1
    if (
        alternate in available
        and diagnostics[str(alternate)]["classification"] == r23.RESILIENT
    ):
        reason = (
            "EXTEND_TO_RESILIENT_RANK2"
            if alternate == 2
            else "CONTRACT_TO_RESILIENT_RANK1"
        )
        return alternate, reason, diagnostics

    return None, "ABSTAIN_NO_RESILIENT_DOL_010", diagnostics


def _stats(
    trades: Sequence[r3.RoutedTrade],
    attr: str = "primary_net_r",
) -> dict[str, Any]:
    return r3._stat(trades, attr)


def _summary(executed: Sequence[dict[str, Any]]) -> dict[str, Any]:
    trades = [item["trade"] for item in executed]
    by_memory: dict[str, Any] = {}
    for state in ("SUPPORTIVE", "MIXED", "CAUTIOUS"):
        rows = [
            item["trade"] for item in executed if item["memory_state"] == state
        ]
        by_memory[state] = {
            "trades": len(rows),
            "gross": _stats(rows, "gross_r"),
            "primary_005r": _stats(rows, "primary_net_r"),
            "stress_010r": _stats(rows, "stress_net_r"),
        }
    return {
        "executed_trades": len(trades),
        "gross": _stats(trades, "gross_r"),
        "primary_005r": _stats(trades, "primary_net_r"),
        "stress_010r": _stats(trades, "stress_net_r"),
        "trail_moves": sum(len(item["trail_events"]) for item in executed),
        "positions_with_trail": sum(bool(item["trail_events"]) for item in executed),
        "memory_state_counts": dict(
            Counter(str(item["memory_state"]) for item in executed)
        ),
        "entry_policy_counts": dict(
            Counter(str(item["entry_policy"]) for item in executed)
        ),
        "target_decision_counts": dict(
            Counter(str(item["target_decision"]) for item in executed)
        ),
        "target_rank_counts": dict(
            Counter(str(item["target_ladder_rank"]) for item in executed)
        ),
        "target_route_counts": dict(
            Counter(item["trade"].target_route for item in executed)
        ),
        "exit_reason_counts": dict(
            Counter(item["trade"].exit_reason for item in executed)
        ),
        "by_memory_state": by_memory,
    }


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
            "trail_events": [event.as_json() for event in item["trail_events"]],
            "memory_state": item["memory_state"],
            "entry_policy": item["entry_policy"],
            "subtype_level": item["subtype_level"],
            "target_decision": item["target_decision"],
            "target_ladder_rank": item["target_ladder_rank"],
            "target_resilience": item["target_resilience"],
            "brain_reason": item["brain_reason"],
            "intelligence_state": item["intelligence_state"],
            "brain_posture": item["brain_posture"],
            "weekday": item["weekday"],
            "session": item["session"],
        }
    )
    return converted


def run(
    source_root: Path,
    target_root: Path,
    dossier_root: Path,
    r23_root: Path,
    r22_root: Path,
    output: Path,
) -> dict[str, Any]:
    evidence, provenance = journey.load_raw_m5(source_root)
    if evidence.symbol != r3.SYMBOL or int(provenance["retained_bars"]) != 707716:
        raise ValueError("unexpected XAUUSD corpus")

    memory_store, dossier_manifest = cibo_memory.build_memory_store(dossier_root)
    subtype_hierarchy, resilience_hierarchy, r23_report = _load_r23(r23_root)

    r22_report = cast(
        dict[str, Any],
        json.loads(_find(r22_root, "r22-subtype-resolved-report.json").read_text()),
    )
    if r22_report["identity"] != "TURTLE_SOUP_XAUUSD_R22_SUBTYPE_RESOLVED_FULL_CIBO_BRAIN_V1":
        raise ValueError("unexpected R22 reference identity")

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
    d1 = recognition_ctx["d1_regime"]
    h4 = recognition_ctx["h4_regime"]

    counts: Counter[str] = Counter()
    executed: list[dict[str, Any]] = []
    busy_until = EVAL_OPEN
    trailing_exit_at: datetime | None = None

    for setup in setups:
        signal = setup.context.signal
        if not (EVAL_OPEN <= signal.entry_at < EVAL_CLOSE):
            continue

        if not r20._structurally_rearmed(
            setup=setup,
            trailing_exit_at=trailing_exit_at,
        ):
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
            counts["ABSTAIN_NO_CAUSAL_CIBO_EPISODE"] += 1
            continue

        regime = r5._regime_features(
            {"entry_at": signal.entry_at.isoformat(), "side": signal.side.value},
            d1,
            h4,
        )
        posture = r15._market_posture(regime)
        memory = cibo_memory.context_memory(
            memory_store,
            timeframe=setup.context.timeframe,
            side=signal.side.value,
            session=setup.context.session,
            prior_body_alignment=setup.context.prior_body_alignment,
            fvg_before_entry=setup.context.fvg_before_entry,
            exact_equal_liquidity=setup.context.exact_equal_liquidity,
        )

        entry_mode, entry_policy, subtype_level = _entry_policy(
            memory_state=memory.state,
            setup=setup,
            posture=posture,
            subtype_hierarchy=subtype_hierarchy,
        )
        counts[entry_policy] += 1
        if entry_mode is None:
            continue

        if (
            setup.context.protected_risk_range_bucket
            in r18.LOW_CAPACITY_RISK_BUCKETS
        ):
            counts["ABSTAIN_LOW_CAPACITY_PROTECTED_SWING"] += 1
            continue

        fill = r3._entry(setup, evidence, opens, entry_mode)
        if fill is None:
            counts["ABSTAIN_SELECTED_ENTRY_NOT_FILLED"] += 1
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

        provisional = r15._provisional_trade(
            setup,
            entry_mode=entry_mode,
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

        base_rank, brain_reason = r19._memory_target_depth(
            setup=setup,
            regime=regime,
            ladder_size=len(ladder),
            memory=memory,
        )
        selected_rank, target_decision, target_resilience = choose_target_rank(
            base_rank=base_rank,
            ladder=ladder,
            memory_state=memory.state,
            setup=setup,
            entry=entry,
            resilience_hierarchy=resilience_hierarchy,
        )
        counts[target_decision] += 1
        if selected_rank is None:
            continue

        target = ladder[selected_rank - 1]
        simulation = r20._simulate_adaptive(
            setup,
            entry_at=entry_at,
            entry=entry,
            target_row=target,
            target_rank=selected_rank,
            ladder=ladder,
            memory_state=memory.state,
            evidence=evidence,
            opens=opens,
        )
        if simulation is None:
            counts["ABSTAIN_INVALID_EXECUTION_GEOMETRY"] += 1
            continue

        trade = simulation.trade
        if trade.entry_mode != entry_mode:
            trade = r3.RoutedTrade(
                source_timeframe=trade.source_timeframe,
                side=trade.side,
                entry_mode=entry_mode,
                target_route=trade.target_route,
                episode_id=trade.episode_id,
                entry_at=trade.entry_at,
                exit_at=trade.exit_at,
                entry=trade.entry,
                stop=trade.stop,
                target=trade.target,
                target_kind=trade.target_kind,
                target_timeframe=trade.target_timeframe,
                gross_r=trade.gross_r,
                primary_net_r=trade.primary_net_r,
                stress_net_r=trade.stress_net_r,
                exit_reason=trade.exit_reason,
                session_bucket=trade.session_bucket,
                prior_body_alignment=trade.prior_body_alignment,
            )

        if trade.entry_at < busy_until:
            counts["ABSTAIN_SINGLE_POSITION_BUSY"] += 1
            continue

        busy_until = trade.exit_at
        if trade.exit_reason in r20.TRAIL_EXIT_REASONS:
            trailing_exit_at = trade.exit_at
        counts["EXECUTE"] += 1
        executed.append(
            {
                "trade": trade,
                "trail_events": simulation.trail_events,
                "memory_state": memory.state,
                "entry_policy": entry_policy,
                "subtype_level": subtype_level,
                "target_decision": target_decision,
                "target_ladder_rank": selected_rank,
                "target_resilience": target_resilience,
                "brain_reason": brain_reason,
                "intelligence_state": assessment.state.value,
                "brain_posture": posture,
                "weekday": setup.context.weekday,
                "session": setup.context.session,
            }
        )

    behavior = {
        "decision_counts": dict(counts),
        **_summary(executed),
    }
    payload = {
        "schema": "qore.turtle_soup_xauusd_r24.friction_resolved_full_cibo_brain.v1",
        "identity": IDENTITY,
        "window": {
            "open": EVAL_OPEN.isoformat(),
            "close": EVAL_CLOSE.isoformat(),
            "duration_years": 2,
        },
        "r23_memory": {
            "identity": r23.IDENTITY,
            "stress_friction_r": r23_report["friction_resilience_contract"][
                "stress_friction_r"
            ],
            "subtype_most_specific_stable_ancestor": True,
            "target_resilience_memory_used": True,
        },
        "decision_contract": {
            "supportive_executes_without_subtype_gate": True,
            "cautious_mixed_hierarchical_resolution": True,
            "unresolved_waits_new_event": True,
            "base_target_kept_when_resilient_010": True,
            "alternate_rank_used_only_when_resilient_010": True,
            "no_resilient_rank_causes_abstention": True,
            "r11_known_invalid_respected": True,
            "r11_conflicted_respected": True,
            "adaptive_trailing_preserved": True,
            "structural_rearm_preserved": True,
            "realized_pnl_target_selection": False,
            "fresh_holdout_used": False,
        },
        "reproduction": {
            "retained_bars": int(provenance["retained_bars"]),
            "setups_10y": len(setups),
            "ambiguous_bindings_fail_closed": repair._LAST_AMBIGUOUS_KEYS,
        },
        "reference_r22": {
            "behavior": r22_report["behavior"],
        },
        "behavior": behavior,
        "dossier_manifest": dossier_manifest,
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
    (output / "r24-friction-resolved-report.json").write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n"
    )
    (output / "r24-friction-resolved-trades.json").write_text(
        json.dumps([_json_item(item) for item in executed], indent=2, sort_keys=True)
        + "\n"
    )
    return payload


def main() -> None:
    if len(sys.argv) != 7:
        raise SystemExit(
            "usage: module SOURCE_ROOT TARGET_ROOT DOSSIER_ROOT R23_ROOT R22_ROOT OUTPUT_DIR"
        )
    print(
        json.dumps(
            run(
                Path(sys.argv[1]),
                Path(sys.argv[2]),
                Path(sys.argv[3]),
                Path(sys.argv[4]),
                Path(sys.argv[5]),
                Path(sys.argv[6]),
            ),
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
