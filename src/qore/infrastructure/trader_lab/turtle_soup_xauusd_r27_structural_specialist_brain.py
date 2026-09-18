"""R27 Turtle Soup XAUUSD — structural specialist-memory brain.

R27 consumes Specialist Cognitive Memory V2.  Entry authority, destination and
management are chosen without gross/net/PF inputs.  Economic metrics are
computed only after the replay for validation.
"""
from __future__ import annotations

import json
import sys
from collections import Counter
from collections.abc import Sequence
from datetime import datetime
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
from qore.infrastructure.trader_lab import (
    turtle_soup_xauusd_r26_specialist_memory_brain as r26,
)
from qore.infrastructure.trader_lab import (
    turtle_soup_xauusd_specialist_cognitive_memory_v2 as v2,
)
from qore.infrastructure.trader_lab import (
    turtle_soup_xauusd_specialist_memory_v1 as v1,
)
from qore.infrastructure.trader_lab.ict_turtle_soup_r4_source_exact import (
    SourceCandle,
    build_daily,
    build_h1,
    build_h4,
)

IDENTITY = "TURTLE_SOUP_XAUUSD_R27_STRUCTURAL_SPECIALIST_BRAIN_V1"
EVAL_OPEN = r26.EVAL_OPEN
EVAL_CLOSE = r26.EVAL_CLOSE

LEVEL_PRIORITY = {
    "exact_regime": 3,
    "causal_core_regime": 2,
    "anatomy_regime": 1,
}


def _single(root: Path, name: str) -> Path:
    matches = list(root.rglob(name))
    if len(matches) != 1:
        raise ValueError(f"expected exactly one {name}, got {len(matches)}")
    return matches[0]


def _load_cognitive(root: Path) -> dict[str, Any]:
    payload = json.loads(
        _single(root, "turtle-soup-xauusd-specialist-cognitive-memory-v2.json").read_text()
    )
    if not isinstance(payload, dict):
        raise ValueError("cognitive V2 must be an object")
    return cast(dict[str, Any], payload)


def _query_row(
    setup: r3.Setup,
    *,
    target: native.NativeTarget,
    regime: dict[str, str],
) -> dict[str, Any]:
    return {
        **v1._setup_context(setup),
        **regime,
        "target_rank": target.rank,
        "target_route": target.route,
    }


def choose_decision(
    cognitive: dict[str, Any],
    setup: r3.Setup,
    *,
    ladder: Sequence[native.NativeTarget],
    regime: dict[str, str],
) -> r26.SpecialistDecision | None:
    candidates: list[tuple[r26.SpecialistDecision, Decimal]] = []
    for target in ladder:
        row = _query_row(setup, target=target, regime=regime)
        profile, level, _ = v2.resolve_authoritative(cognitive, row)
        if profile is None or level is None:
            continue
        reach = Decimal(str(profile["static_protected_swing_reach_rate"]))
        candidates.append(
            (
                r26.SpecialistDecision(
                    target=target,
                    memory_level=level,
                    classification="STRUCTURAL_REACHABILITY",
                    posture=str(profile["preferred_posture"]),
                    mean_net_010_r=Decimal(0),
                    observations=int(profile["observations"]),
                ),
                reach,
            )
        )
    if not candidates:
        return None

    def priority(
        item: tuple[r26.SpecialistDecision, Decimal],
    ) -> tuple[int, int, Decimal, int]:
        decision, reach = item
        return (
            LEVEL_PRIORITY[decision.memory_level],
            decision.target.rank,
            reach,
            decision.observations,
        )

    return max(candidates, key=priority)[0]


def run(
    raw_root: Path,
    target_root: Path,
    cognitive_root: Path,
    output: Path,
) -> dict[str, Any]:
    evidence, provenance = journey.load_raw_m5(raw_root)
    if evidence.symbol != "XAUUSD" or int(provenance["retained_bars"]) != 707716:
        raise ValueError("unexpected XAUUSD corpus")

    memory_report = json.loads(
        _single(
            cognitive_root,
            "turtle-soup-xauusd-specialist-cognitive-memory-v2-report.json",
        ).read_text()
    )
    if memory_report["identity"] != v2.IDENTITY:
        raise ValueError("unexpected Specialist Cognitive Memory V2 identity")
    if memory_report["decision_contract"]["economic_fields_authorize_trade"]:
        raise ValueError("economic fields cannot authorize R27")
    cognitive = _load_cognitive(cognitive_root)

    target_rows = r26._load_targets(target_root)
    _episodes, source_index = repair._load_targets_fail_closed(target_root)

    original_open, original_close = r1.EVAL_OPEN, r1.EVAL_CLOSE
    try:
        r1.EVAL_OPEN, r1.EVAL_CLOSE = r3.EVAL_OPEN, r3.EVAL_CLOSE
        setups, funnel = r3._build_setups(evidence)
    finally:
        r1.EVAL_OPEN, r1.EVAL_CLOSE = original_open, original_close

    opens = tuple(bar.opened_at for bar in evidence.bars)
    tick = Decimal(1).scaleb(-evidence.digits)
    h4 = build_h4(evidence.bars)
    frames: dict[str, tuple[SourceCandle, ...]] = {
        "H1": build_h1(evidence.bars),
        "H4": h4,
        "D1": build_daily(h4),
    }
    frame_closes = {
        timeframe: tuple(candle.closed_at for candle in candles)
        for timeframe, candles in frames.items()
    }

    busy_until = EVAL_OPEN
    trailing_exit_at: datetime | None = None
    trades: list[r26.RuntimeTrade] = []
    counts: Counter[str] = Counter()

    for setup in setups:
        signal = setup.context.signal
        if not (EVAL_OPEN <= signal.entry_at < EVAL_CLOSE):
            continue
        if not r26._structurally_rearmed(setup, trailing_exit_at):
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

        ladder = v1._active_ladder(
            target_rows.get(episode_id, ()),
            at=entry_at,
            side=signal.side,
            entry=entry,
            tick=tick,
        )
        if not ladder:
            counts["ABSTAIN_NO_ACTIVE_DOL"] += 1
            continue

        regime = v2._regime_context(
            row={
                "strategy_entry_at": entry_at.isoformat(),
                "side": signal.side.value,
            },
            bars=evidence.bars,
            opens=opens,
            frames=frames,
            frame_closes=frame_closes,
        )
        decision = choose_decision(
            cognitive,
            setup,
            ladder=ladder,
            regime=regime,
        )
        if decision is None:
            counts["ABSTAIN_NO_STRUCTURAL_SPECIALIST_AUTHORITY"] += 1
            continue

        runtime = r26._simulate(
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
        counts[f"POSTURE_{runtime.posture}"] += 1
        counts[f"RANK_{runtime.target_rank}"] += 1

    def by(field: str) -> dict[str, Any]:
        values = sorted({str(getattr(trade, field)) for trade in trades})
        return {
            value: {
                "gross": r26._stat(
                    [trade for trade in trades if str(getattr(trade, field)) == value],
                    "gross_r",
                ),
                "net_005": r26._stat(
                    [trade for trade in trades if str(getattr(trade, field)) == value],
                    "net_005_r",
                ),
                "net_010": r26._stat(
                    [trade for trade in trades if str(getattr(trade, field)) == value],
                    "net_010_r",
                ),
            }
            for value in values
        }

    payload = {
        "schema": "qore.turtle_soup_xauusd_r27.structural_specialist_brain.v1",
        "identity": IDENTITY,
        "window": {
            "open": EVAL_OPEN.isoformat(),
            "close": EVAL_CLOSE.isoformat(),
            "duration_years": 2,
        },
        "decision_sources": {
            "strategy": "TURTLE_SOUP_XAUUSD",
            "specialist_memory": v2.IDENTITY,
            "master_memory_remains_immutable": True,
            "r22_memory_used": False,
            "r23_memory_used": False,
            "r25_result_used": False,
            "r26_result_used_as_decision_input": False,
        },
        "decision_contract": {
            "authority_is_structural": True,
            "gross_r_authorizes_trade": False,
            "net_r_authorizes_trade": False,
            "profit_factor_authorizes_trade": False,
            "calendar_year_regime_rule": False,
            "regime_is_pre_entry": True,
            "target_support_is_protected_swing_reachability": True,
            "management_is_structural_non_inferiority": True,
            "actual_strategy_entry": True,
            "exact_protected_swing": True,
            "structural_rearm": True,
            "target_from_active_cibo_dol_ladder": True,
            "context_only_can_authorize": False,
        },
        "behavior": {
            "decision_counts": dict(counts),
            "gross": r26._stat(trades, "gross_r"),
            "net_005": r26._stat(trades, "net_005_r"),
            "net_010": r26._stat(trades, "net_010_r"),
            "exit_reason_counts": dict(Counter(trade.exit_reason for trade in trades)),
            "trail_moves": sum(trade.trail_moves for trade in trades),
            "by_memory_level": by("memory_level"),
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
    (output / "r27-structural-specialist-brain-report.json").write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n"
    )
    (output / "r27-structural-specialist-brain-trades.json").write_text(
        json.dumps(
            [
                {
                    "entry_at": trade.entry_at.isoformat(),
                    "exit_at": trade.exit_at.isoformat(),
                    "side": trade.side,
                    "posture": trade.posture,
                    "memory_level": trade.memory_level,
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
            "usage: module RAW_ROOT TARGET_ROOT COGNITIVE_V2_ROOT OUTPUT_DIR"
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
