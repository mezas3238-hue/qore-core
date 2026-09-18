"""R30 nearest-DOL coverage expansion lab.

R30 keeps the R28 causal/regime/lifecycle architecture and tests a more
conservative destination hierarchy: among economically validated targets at the
same authority level, choose the nearest active validated DOL (lowest rank).
This minimizes journey extrapolation.

Coverage recovery is allowed only for rank-1 targets when:
1) the Anatomy+Regime profile has enough structural observations, quarters and
   Protected-Swing reachability under a predeclared threshold;
2) the broader Regime+Journey profile independently validates the same target at
   full-lifecycle 0.10R;
3) entry/C2/CISD/Protected-Swing/rearm remain unchanged.

All thresholds and acceptance gates are fixed before replay.
"""
from __future__ import annotations

import json
import sys
from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass
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
    turtle_soup_xauusd_specialist_cognitive_memory_v3 as v3,
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

IDENTITY = "TURTLE_SOUP_XAUUSD_R30_NEAREST_DOL_COVERAGE_LAB_V1"
EVAL_OPEN = r26.EVAL_OPEN
EVAL_CLOSE = r26.EVAL_CLOSE

MIN_TRADES = 250
MIN_PF_010 = Decimal("1.80")
MAX_DD_010 = Decimal("8.0")
MAX_LS_010 = 3

NEAREST_BASELINE = "R30_NEAREST_VALIDATED_BASELINE"
OBS16_REACH055 = "R30_OBS16_REACH055_CONTEXT_VALIDATED"
OBS12_REACH060 = "R30_OBS12_REACH060_CONTEXT_VALIDATED"
OBS12_REACH055 = "R30_OBS12_REACH055_CONTEXT_VALIDATED"
OBS8_REACH065 = "R30_OBS8_REACH065_CONTEXT_VALIDATED"

VARIANT_RULES: dict[str, tuple[int | None, Decimal | None]] = {
    NEAREST_BASELINE: (None, None),
    OBS16_REACH055: (16, Decimal("0.55")),
    OBS12_REACH060: (12, Decimal("0.60")),
    OBS12_REACH055: (12, Decimal("0.55")),
    OBS8_REACH065: (8, Decimal("0.65")),
}

LEVEL_PRIORITY = {
    "exact_regime": 3,
    "causal_core_regime": 2,
    "anatomy_regime": 1,
}


@dataclass(frozen=True, slots=True)
class Decision:
    target: native.NativeTarget
    memory_level: str
    classification: str
    posture: str
    observations: int
    source: str


def _single(root: Path, name: str) -> Path:
    matches = list(root.rglob(name))
    if len(matches) != 1:
        raise ValueError(f"expected exactly one {name}, got {len(matches)}")
    return matches[0]


def _load_cognitive(root: Path) -> dict[str, Any]:
    payload = json.loads(
        _single(root, "turtle-soup-xauusd-specialist-cognitive-memory-v3.json").read_text()
    )
    if not isinstance(payload, dict):
        raise ValueError("cognitive V3 must be an object")
    return cast(dict[str, Any], payload)


def _profile_at_level(
    cognitive: dict[str, Any],
    row: dict[str, Any],
    level_name: str,
) -> dict[str, Any] | None:
    fields = dict(v2.LEVELS)[level_name]
    signature = v2._key(row, fields)
    item = cast(dict[str, Any], cognitive[level_name]["signatures"]).get(signature)
    if item is None:
        return None
    return cast(dict[str, Any], item["targets"]).get(v2._target_key(row))


def _validated_candidates(
    cognitive: dict[str, Any],
    setup: r3.Setup,
    *,
    ladder: Sequence[native.NativeTarget],
    regime: dict[str, str],
) -> list[Decision]:
    result: list[Decision] = []
    for target in ladder:
        row = {
            **v1._setup_context(setup),
            **regime,
            "target_rank": target.rank,
            "target_route": target.route,
        }
        profile, level, _ = v3.resolve_validated(cognitive, row)
        if profile is None or level is None:
            continue
        validation = cast(dict[str, Any], profile["economic_validation"])
        result.append(
            Decision(
                target=target,
                memory_level=level,
                classification=str(validation["classification"]),
                posture=str(profile["preferred_posture"]),
                observations=int(profile["observations"]),
                source="R28_VALIDATED_NEAREST_DOL",
            )
        )
    return result


def _nearest_validated(
    candidates: Sequence[Decision],
) -> Decision | None:
    if not candidates:
        return None
    best_level = max(LEVEL_PRIORITY[item.memory_level] for item in candidates)
    same_level = [
        item for item in candidates if LEVEL_PRIORITY[item.memory_level] == best_level
    ]
    return min(
        same_level,
        key=lambda item: (
            item.target.rank,
            -item.observations,
            item.target.route,
        ),
    )


def _recovery(
    cognitive: dict[str, Any],
    setup: r3.Setup,
    *,
    target: native.NativeTarget,
    regime: dict[str, str],
    min_observations: int,
    min_reach: Decimal,
) -> Decision | None:
    if target.rank != 1:
        return None
    row = {
        **v1._setup_context(setup),
        **regime,
        "target_rank": target.rank,
        "target_route": target.route,
    }
    anatomy = _profile_at_level(cognitive, row, "anatomy_regime")
    context = _profile_at_level(cognitive, row, "regime_journey")
    if anatomy is None or context is None:
        return None

    observations = int(anatomy["observations"])
    quarters = int(anatomy["distinct_quarters"])
    reach = Decimal(str(anatomy["static_protected_swing_reach_rate"]))
    if observations < min_observations or quarters < 4 or reach < min_reach:
        return None

    context_validation = cast(dict[str, Any], context.get("economic_validation", {}))
    if not bool(context_validation.get("validated", False)):
        return None

    return Decision(
        target=target,
        memory_level="anatomy_regime+regime_journey",
        classification=str(context_validation["classification"]),
        posture=str(anatomy["preferred_posture"]),
        observations=observations,
        source=(
            f"RECOVERED_RANK1_OBS{min_observations}_"
            f"REACH{str(min_reach).replace('.', '')}"
        ),
    )


def choose(
    cognitive: dict[str, Any],
    setup: r3.Setup,
    *,
    ladder: Sequence[native.NativeTarget],
    regime: dict[str, str],
    variant: str,
) -> Decision | None:
    baseline = _nearest_validated(
        _validated_candidates(
            cognitive,
            setup,
            ladder=ladder,
            regime=regime,
        )
    )
    if baseline is not None:
        return baseline

    min_observations, min_reach = VARIANT_RULES[variant]
    if min_observations is None or min_reach is None:
        return None
    recovered = [
        item
        for target in ladder
        if (
            item := _recovery(
                cognitive,
                setup,
                target=target,
                regime=regime,
                min_observations=min_observations,
                min_reach=min_reach,
            )
        )
        is not None
    ]
    if not recovered:
        return None
    return max(recovered, key=lambda item: (item.observations, item.target.route))


def _runtime_decision(decision: Decision) -> r26.SpecialistDecision:
    return r26.SpecialistDecision(
        target=decision.target,
        memory_level=decision.memory_level,
        classification=decision.classification,
        posture=decision.posture,
        mean_net_010_r=Decimal(0),
        observations=decision.observations,
    )


def _run_variant(
    *,
    variant: str,
    setups: Sequence[r3.Setup],
    evidence: Any,
    opens: Sequence[datetime],
    tick: Decimal,
    target_rows: dict[str, list[dict[str, Any]]],
    source_index: dict[tuple[datetime, str, str, Decimal], str],
    cognitive: dict[str, Any],
    frames: dict[str, tuple[SourceCandle, ...]],
    frame_closes: dict[str, tuple[datetime, ...]],
) -> dict[str, Any]:
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
            (signal.cisd_at, signal.side.value, setup.context.timeframe, signal.target)
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
            row={"strategy_entry_at": entry_at.isoformat(), "side": signal.side.value},
            bars=evidence.bars,
            opens=opens,
            frames=frames,
            frame_closes=frame_closes,
        )
        decision = choose(
            cognitive,
            setup,
            ladder=ladder,
            regime=regime,
            variant=variant,
        )
        if decision is None:
            counts["ABSTAIN_NO_VALIDATED_MEMORY"] += 1
            continue

        runtime = r26._simulate(
            setup,
            decision=_runtime_decision(decision),
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
        counts[f"SOURCE_{decision.source}"] += 1
        counts[f"POSTURE_{runtime.posture}"] += 1
        counts[f"RANK_{runtime.target_rank}"] += 1

    net = r26._stat(trades, "net_010_r")
    pf = None if net["profit_factor"] is None else Decimal(str(net["profit_factor"]))
    dd = Decimal(str(net["max_drawdown_r"]))
    passed = bool(
        len(trades) >= MIN_TRADES
        and pf is not None
        and pf >= MIN_PF_010
        and dd <= MAX_DD_010
        and int(net["max_losing_streak"]) <= MAX_LS_010
    )
    return {
        "variant": variant,
        "rule": {
            "minimum_anatomy_observations": VARIANT_RULES[variant][0],
            "minimum_anatomy_reach": (
                None
                if VARIANT_RULES[variant][1] is None
                else str(VARIANT_RULES[variant][1])
            ),
            "minimum_distinct_quarters": 4,
            "recovery_target_rank": 1,
            "context_validation_required": True,
        },
        "decision_counts": dict(counts),
        "gross": r26._stat(trades, "gross_r"),
        "net_005": r26._stat(trades, "net_005_r"),
        "net_010": net,
        "acceptance_pass": passed,
    }


def run(
    raw_root: Path,
    target_root: Path,
    cognitive_root: Path,
    output: Path,
) -> dict[str, Any]:
    evidence, provenance = journey.load_raw_m5(raw_root)
    if evidence.symbol != "XAUUSD" or int(provenance["retained_bars"]) != 707716:
        raise ValueError("unexpected XAUUSD corpus")
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

    results = [
        _run_variant(
            variant=variant,
            setups=setups,
            evidence=evidence,
            opens=opens,
            tick=tick,
            target_rows=target_rows,
            source_index=source_index,
            cognitive=cognitive,
            frames=frames,
            frame_closes=frame_closes,
        )
        for variant in VARIANT_RULES
    ]
    passing = [item for item in results if item["acceptance_pass"]]

    def ranking(item: dict[str, Any]) -> tuple[int, Decimal, Decimal]:
        net = item["net_010"]
        return (
            int(net["trades"]),
            Decimal(str(net["profit_factor"])),
            -Decimal(str(net["max_drawdown_r"])),
        )

    selected = max(passing, key=ranking) if passing else None
    payload = {
        "schema": "qore.turtle_soup_xauusd.r30_nearest_dol_coverage_lab.v1",
        "identity": IDENTITY,
        "window": {
            "open": EVAL_OPEN.isoformat(),
            "close": EVAL_CLOSE.isoformat(),
            "same_consumed_development_window": True,
        },
        "experiment_contract": {
            "fresh_holdout_consumed": False,
            "nearest_validated_dol_policy": True,
            "nearest_dol_reason": "MINIMUM_JOURNEY_EXTRAPOLATION",
            "entry_changed": False,
            "c2_changed": False,
            "cisd_changed": False,
            "protected_swing_changed": False,
            "regime_model_changed": False,
            "economic_magnitude_ranks_targets": False,
            "recovery_requires_rank1": True,
            "recovery_requires_anatomy_structure": True,
            "recovery_requires_same_target_regime_journey_validation": True,
            "variant_rules": {
                name: {
                    "minimum_observations": rule[0],
                    "minimum_reach": None if rule[1] is None else str(rule[1]),
                }
                for name, rule in VARIANT_RULES.items()
            },
        },
        "predeclared_acceptance": {
            "minimum_trades": MIN_TRADES,
            "minimum_net_010_profit_factor": str(MIN_PF_010),
            "maximum_net_010_drawdown_r": str(MAX_DD_010),
            "maximum_net_010_losing_streak": MAX_LS_010,
            "selection_order": "MOST_TRADES_THEN_HIGHER_PF_THEN_LOWER_DD",
        },
        "results": results,
        "selected_variant": None if selected is None else selected["variant"],
        "selected_result": selected,
        "reproduction": {
            "retained_bars": int(provenance["retained_bars"]),
            "setups_10y": len(setups),
            "funnel": funnel,
        },
        "governance": {
            "research_only": True,
            "candidate_replacement_allowed_only_if_acceptance_pass": True,
            "candidate_replaced": False,
            "fresh_holdout_consumed": False,
            "demo_eligible": False,
            "live_authorized": False,
            "real_capital_authorized": False,
            "production_authorized": False,
        },
    }
    output.mkdir(parents=True, exist_ok=True)
    (output / "r30-nearest-dol-coverage-lab-report.json").write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n"
    )
    return payload


def main() -> None:
    if len(sys.argv) != 5:
        raise SystemExit(
            "usage: module RAW_ROOT TARGET_ROOT COGNITIVE_V3_ROOT OUTPUT_DIR"
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
