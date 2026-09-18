"""R38 AUDJPY structural fragility risk correction.

R38 preserves the R37/R36 AUDJPY signal population and applies a non-zero
pre-entry risk overlay derived from consumed R37 drawdown forensics. It never
suppresses a trade and never uses post-entry outcome information.

Every trade still uses the real active CIBO DOL, exact C2/CISD, exact Protected
Swing stop, NEXT_SOURCE_OPEN entry, single-position busy handling and structural
rearm.

Fresh holdout remains sealed.
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
from typing import Any

from qore.infrastructure.trader_lab import (
    cibo_market_atlas_journey_extractor_v1 as journey,
)
from qore.infrastructure.trader_lab import (
    cibo_audjpy_native_market_decision_memory_v2 as native,
)
from qore.infrastructure.trader_lab import turtle_soup_audjpy_r1 as r1
from qore.infrastructure.trader_lab import turtle_soup_audjpy_r3_cibo_journey as r3
from qore.infrastructure.trader_lab import (
    turtle_soup_audjpy_r3_cibo_journey_binding_repair as repair,
)
from qore.infrastructure.trader_lab import (
    turtle_soup_audjpy_r26_specialist_memory_brain as r26,
)
from qore.infrastructure.trader_lab import (
    turtle_soup_audjpy_r32_causal_memory_defragmentation as r32,
)
from qore.infrastructure.trader_lab import (
    turtle_soup_audjpy_r34_coarse_causal_memory as r34,
)
from qore.infrastructure.trader_lab import (
    turtle_soup_audjpy_specialist_cognitive_memory_v2 as v2,
)
from qore.infrastructure.trader_lab import (
    turtle_soup_audjpy_specialist_memory_v1 as v1,
)
from qore.infrastructure.trader_lab.ict_turtle_soup_r4_source_exact import (
    SourceCandle,
    build_daily,
    build_h1,
    build_h4,
)

IDENTITY = "TURTLE_SOUP_AUDJPY_R38_STRUCTURAL_FRAGILITY_RISK_CORRECTION_V1"
EVAL_OPEN = r26.EVAL_OPEN
EVAL_CLOSE = r26.EVAL_CLOSE

MIN_TRADES = 350
MIN_PF_010 = Decimal("1.90")
MAX_DD_010 = Decimal("6.0")
MAX_LS_010 = 3

CORE = "R32_CORE_ROUTE_TYPES"
DIRECTION = "R34_DIRECTION_REGIME_ROUTE_TYPES"
TIMEFRAME = "R34_TIMEFRAME_REGIME_ROUTE_TYPES"
MINIMAL = "R34_MINIMAL_ROUTE_TYPES"
RANGE_FALSIFIED = "R34_RANGE_ROUTE_TYPES"
ROBUST = "ROBUST_VALIDATED_010"
MAJORITY = "MAJORITY_VALIDATED_010"

# Predeclared authority frontier derived from consumed AUDJPY forensics.
# R32 CORE has the strongest positive pooled-memory PF; lower-dimensional
# positive R34 memories may only expand coverage after higher authority abstains.
ENSEMBLES: dict[str, tuple[tuple[str, tuple[str, ...]], ...]] = {
    "R38_FROZEN_SIGNAL_BASELINE": (
        (CORE, (ROBUST, MAJORITY)),
        (DIRECTION, (ROBUST, MAJORITY)),
        (TIMEFRAME, (ROBUST, MAJORITY)),
    ),
}

# (core, robust expansion, majority expansion). Scaling changes capital risk,
# never signal count or execution eligibility.
RISK_POLICIES: dict[str, tuple[Decimal, Decimal, Decimal]] = {
    "AUDJPY_CONFIDENCE_100_075_025": (
        Decimal("1"),
        Decimal("0.75"),
        Decimal("0.25"),
    ),
}

F1 = "M5_EFFICIENCY_MEDIUM"
F2 = "D1_RANGE_EXPANDED"
F3 = "PROJECTED_R_Q2_LE_1"
FRAGILITY_FLAGS = (F1, F2, F3)
# Non-zero risk-only overlay by number of simultaneous pre-entry fragility flags.
FRAGILITY_POLICY = (
    Decimal("1"),
    Decimal("0.20"),
    Decimal("0.05"),
    Decimal("0.01"),
)



@dataclass(frozen=True, slots=True)
class Decision:
    target: native.NativeTarget
    posture: str
    classification: str
    observations: int
    source_scheme: str
    authority_tier: str
    fragility_flags: tuple[str, ...]


def _single(root: Path, name: str) -> Path:
    matches = list(root.rglob(name))
    if len(matches) != 1:
        raise ValueError(f"expected exactly one {name}, got {len(matches)}")
    return matches[0]


def _fragility_flags(
    setup: r3.Setup,
    regime: dict[str, str],
) -> tuple[str, ...]:
    ctx = v1._setup_context(setup)
    flags: list[str] = []
    if regime["m5_efficiency_state"] == "medium":
        flags.append(F1)
    if regime["d1_range_state"] == "expanded":
        flags.append(F2)
    if ctx["strategy_projected_r_bucket"] == "q2:<=1.0":
        flags.append(F3)
    return tuple(flags)


def _choose_layer(
    *,
    setup: r3.Setup,
    ladder: Sequence[native.NativeTarget],
    regime: dict[str, str],
    fields: Sequence[str],
    route_mode: str,
    memory: dict[tuple[str, str], Any],
    allowed_classes: Sequence[str],
    scheme: str,
    is_core: bool,
) -> Decision | None:
    ctx = v1._setup_context(setup)
    row = {**ctx, **regime}
    signature = r34._signature(row, fields)
    candidates: list[Decision] = []
    allowed = set(allowed_classes)
    for target in ladder:
        profile = memory.get(
            (signature, r34._target_family_runtime(target, route_mode))
        )
        if (
            profile is None
            or not profile.validated
            or profile.classification not in allowed
        ):
            continue
        candidates.append(
            Decision(
                target=target,
                posture=profile.posture,
                classification=profile.classification,
                observations=profile.observations,
                source_scheme=scheme,
                authority_tier="CORE" if is_core else "EXPANSION",
                fragility_flags=_fragility_flags(setup, regime),
            )
        )
    if not candidates:
        return None
    return min(
        candidates,
        key=lambda item: (
            item.target.rank,
            -item.observations,
            item.target.route,
        ),
    )


def _choose(
    *,
    setup: r3.Setup,
    ladder: Sequence[native.NativeTarget],
    regime: dict[str, str],
    layers: Sequence[tuple[str, tuple[str, ...]]],
    memories: dict[
        str,
        tuple[
            tuple[str, ...],
            str,
            dict[tuple[str, str], Any],
            dict[str, Any],
        ],
    ],
) -> Decision | None:
    for index, (scheme, allowed_classes) in enumerate(layers):
        fields, route_mode, memory, _summary = memories[scheme]
        decision = _choose_layer(
            setup=setup,
            ladder=ladder,
            regime=regime,
            fields=fields,
            route_mode=route_mode,
            memory=memory,
            allowed_classes=allowed_classes,
            scheme=scheme,
            is_core=index == 0,
        )
        if decision is not None:
            return decision
    return None


def _runtime_decision(decision: Decision) -> r26.SpecialistDecision:
    return r26.SpecialistDecision(
        target=decision.target,
        memory_level=f"r38:{decision.source_scheme}",
        classification=decision.classification,
        posture=decision.posture,
        mean_net_010_r=Decimal(0),
        observations=decision.observations,
    )


def _risk_scale(decision: Decision, policy_name: str) -> Decimal:
    core, robust, majority = RISK_POLICIES[policy_name]
    if decision.authority_tier == "CORE":
        base = core
    elif decision.classification == ROBUST:
        base = robust
    elif decision.classification == MAJORITY:
        base = majority
    else:
        raise ValueError(
            f"unexpected expansion classification {decision.classification}"
        )
    overlay = FRAGILITY_POLICY[
        min(len(decision.fragility_flags), len(FRAGILITY_POLICY) - 1)
    ]
    return base * overlay


def _scaled_stat(
    attributed: Sequence[tuple[r26.RuntimeTrade, Decision]],
    policy_name: str,
) -> dict[str, Any]:
    equity = Decimal(0)
    peak = Decimal(0)
    max_dd = Decimal(0)
    gains = Decimal(0)
    losses = Decimal(0)
    losing = 0
    max_losing = 0
    scale_counts: Counter[str] = Counter()
    source_counts: Counter[str] = Counter()
    class_counts: Counter[str] = Counter()
    fragility_count_distribution: Counter[str] = Counter()
    fragility_flag_counts: Counter[str] = Counter()

    for trade, decision in attributed:
        scale = _risk_scale(decision, policy_name)
        scale_counts[str(scale)] += 1
        source_counts[decision.source_scheme] += 1
        class_counts[f"{decision.authority_tier}:{decision.classification}"] += 1
        fragility_count_distribution[str(len(decision.fragility_flags))] += 1
        for flag in decision.fragility_flags:
            fragility_flag_counts[flag] += 1
        value = trade.net_010_r * scale
        equity += value
        peak = max(peak, equity)
        max_dd = max(max_dd, peak - equity)
        if value > 0:
            gains += value
            losing = 0
        elif value < 0:
            losses += -value
            losing += 1
            max_losing = max(max_losing, losing)

    pf = None if losses == 0 else gains / losses
    return {
        "trades": len(attributed),
        "total_scaled_net_010_r": str(equity),
        "mean_scaled_net_010_r": (
            None if not attributed else str(equity / Decimal(len(attributed)))
        ),
        "profit_factor_scaled_net_010": None if pf is None else str(pf),
        "max_drawdown_scaled_r": str(max_dd),
        "max_losing_streak": max_losing,
        "risk_scale_counts": dict(scale_counts),
        "source_counts": dict(source_counts),
        "authority_class_counts": dict(class_counts),
        "fragility_flag_count_distribution": dict(fragility_count_distribution),
        "fragility_flag_counts": dict(fragility_flag_counts),
    }


def _unscaled_stat(
    attributed: Sequence[tuple[r26.RuntimeTrade, Decision]],
    *,
    scheme: str | None = None,
    authority_tier: str | None = None,
    classification: str | None = None,
) -> dict[str, Any]:
    trades = [
        trade
        for trade, decision in attributed
        if (scheme is None or decision.source_scheme == scheme)
        and (authority_tier is None or decision.authority_tier == authority_tier)
        and (classification is None or decision.classification == classification)
    ]
    return {
        "trades": len(trades),
        "net_010": r26._stat(trades, "net_010_r"),
    }


def _run_ensemble(
    *,
    ensemble_name: str,
    layers: Sequence[tuple[str, tuple[str, ...]]],
    memories: dict[
        str,
        tuple[
            tuple[str, ...],
            str,
            dict[tuple[str, str], Any],
            dict[str, Any],
        ],
    ],
    setups: Sequence[r3.Setup],
    evidence: Any,
    opens: Sequence[datetime],
    tick: Decimal,
    target_rows: dict[str, list[dict[str, Any]]],
    source_index: dict[tuple[datetime, str, str, Decimal], str],
    frames: dict[str, tuple[SourceCandle, ...]],
    frame_closes: dict[str, tuple[datetime, ...]],
) -> dict[str, Any]:
    busy_until = EVAL_OPEN
    trailing_exit_at: datetime | None = None
    attributed: list[tuple[r26.RuntimeTrade, Decision]] = []
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
        decision = _choose(
            setup=setup,
            ladder=ladder,
            regime=regime,
            layers=layers,
            memories=memories,
        )
        if decision is None:
            counts["ABSTAIN_NO_ENSEMBLE_AUTHORITY"] += 1
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
        attributed.append((runtime, decision))
        counts["EXECUTE"] += 1
        counts[f"SOURCE_{decision.source_scheme}"] += 1
        counts[f"TIER_{decision.authority_tier}"] += 1
        counts[f"CLASS_{decision.classification}"] += 1
        counts[f"RANK_{runtime.target_rank}"] += 1

    risk_results: list[dict[str, Any]] = []
    for policy_name in RISK_POLICIES:
        stats = _scaled_stat(attributed, policy_name)
        raw_pf = stats["profit_factor_scaled_net_010"]
        pf = None if raw_pf is None else Decimal(str(raw_pf))
        dd = Decimal(str(stats["max_drawdown_scaled_r"]))
        passed = bool(
            len(attributed) >= MIN_TRADES
            and pf is not None
            and pf >= MIN_PF_010
            and dd <= MAX_DD_010
        )
        risk_results.append(
            {
                "policy": policy_name,
                "stats": stats,
                "acceptance_pass": passed,
            }
        )

    return {
        "ensemble": ensemble_name,
        "layers": [
            {
                "scheme": scheme,
                "allowed_validation_classes": list(classes),
            }
            for scheme, classes in layers
        ],
        "decision_counts": dict(counts),
        "forensics": {
            "core": _unscaled_stat(attributed, authority_tier="CORE"),
            "expansion": _unscaled_stat(attributed, authority_tier="EXPANSION"),
            "expansion_robust": _unscaled_stat(
                attributed,
                authority_tier="EXPANSION",
                classification=ROBUST,
            ),
            "expansion_majority": _unscaled_stat(
                attributed,
                authority_tier="EXPANSION",
                classification=MAJORITY,
            ),
            "by_scheme": {
                scheme: _unscaled_stat(attributed, scheme=scheme)
                for scheme, _classes in layers
            },
        },
        "risk_policies": risk_results,
    }


def run(
    raw_root: Path,
    target_root: Path,
    v2_root: Path,
    output: Path,
) -> dict[str, Any]:
    evidence, provenance = journey.load_raw_m5(raw_root)
    if evidence.symbol != "AUDJPY" or int(provenance["retained_bars"]) != 745468:
        raise ValueError("unexpected AUDJPY corpus")

    observations = r34._load_observations(v2_root)
    target_rows = r26._load_targets(target_root)
    _episodes, source_index = repair._load_targets_fail_closed(target_root)

    memories: dict[str, tuple[tuple[str, ...], str, dict[Any, Any], dict[str, Any]]] = {}
    core_fields, core_route_mode = r32.SCHEMES[CORE]
    core_memory, core_summary = r32._build_memory(
        observations,
        fields=core_fields,
        route_mode=core_route_mode,
    )
    memories[CORE] = (core_fields, core_route_mode, core_memory, core_summary)
    for scheme in (DIRECTION, TIMEFRAME, MINIMAL):
        fields, route_mode = r34.SCHEMES[scheme]
        memory, summary = r34._build_memory(
            observations,
            fields=fields,
            route_mode=route_mode,
        )
        memories[scheme] = (fields, route_mode, memory, summary)

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
        _run_ensemble(
            ensemble_name=name,
            layers=layers,
            memories=memories,
            setups=setups,
            evidence=evidence,
            opens=opens,
            tick=tick,
            target_rows=target_rows,
            source_index=source_index,
            frames=frames,
            frame_closes=frame_closes,
        )
        for name, layers in ENSEMBLES.items()
    ]

    passing: list[dict[str, Any]] = []
    for result in results:
        for risk in result["risk_policies"]:
            if risk["acceptance_pass"]:
                passing.append(
                    {
                        "ensemble": result["ensemble"],
                        "policy": risk["policy"],
                        "stats": risk["stats"],
                    }
                )

    def ranking(item: dict[str, Any]) -> tuple[int, Decimal, Decimal]:
        stats = item["stats"]
        return (
            int(stats["trades"]),
            Decimal(str(stats["profit_factor_scaled_net_010"])),
            -Decimal(str(stats["max_drawdown_scaled_r"])),
        )

    selected = max(passing, key=ranking) if passing else None
    payload = {
        "schema": "qore.turtle_soup_audjpy.r38_structural_fragility_risk_correction.v1",
        "identity": IDENTITY,
        "window": {
            "open": EVAL_OPEN.isoformat(),
            "close": EVAL_CLOSE.isoformat(),
            "same_consumed_development_window": True,
        },
        "experiment_contract": {
            "fresh_holdout_consumed": False,
            "r32_core_is_primary_authority": True,
            "r34_direction_is_expansion_only": True,
            "r34_range_falsified_for_recent_development": True,
            "r34_range_used_for_authority": False,
            "expansion_only_when_higher_authority_layer_abstains": True,
            "actual_active_cibo_dol_price_used": True,
            "nearest_validated_dol_within_each_layer": True,
            "entry_changed": False,
            "c2_changed": False,
            "cisd_changed": False,
            "protected_swing_changed": False,
            "structural_rearm_changed": False,
            "single_position_busy_preserved": True,
            "risk_governor_suppresses_trades": False,
            "risk_governor_uses_current_signal_outcome": False,
            "risk_governor_uses_prior_trade_outcomes": False,
            "fragility_uses_pre_entry_context_only": True,
            "fragility_flags_predeclared": list(FRAGILITY_FLAGS),
            "fragility_policy_0_1_2_3plus": [
                str(value) for value in FRAGILITY_POLICY
            ],
            "r37_forensic_rationale": {
                "zero_flags": {"trades": 168, "pf_010": "1.986623483472833890319685209"},
                "one_flag": {"trades": 167, "pf_010": "0.9130873925731141882327674395"},
                "two_flags": {"trades": 77, "pf_010": "0.6748701325665054596110530377"},
                "three_flags": {"trades": 10, "pf_010": "0.5851752867308636909869812969"},
            },
            "authority_tiers_frozen_before_replay": True,
            "ensembles_predeclared": {
                name: [
                    {
                        "scheme": scheme,
                        "allowed_validation_classes": list(classes),
                    }
                    for scheme, classes in layers
                ]
                for name, layers in ENSEMBLES.items()
            },
            "risk_policies_predeclared": {
                name: {
                    "core_scale": str(rule[0]),
                    "robust_expansion_scale": str(rule[1]),
                    "majority_expansion_scale": str(rule[2]),
                }
                for name, rule in RISK_POLICIES.items()
            },
        },
        "predeclared_acceptance": {
            "minimum_trades": MIN_TRADES,
            "minimum_scaled_net_010_profit_factor": str(MIN_PF_010),
            "maximum_scaled_net_010_drawdown_r": str(MAX_DD_010),
            "losing_streak": "DIAGNOSTIC_NOT_HARD_GATE",
            "selection_order": "MOST_TRADES_THEN_HIGHER_PF_THEN_LOWER_DD",
        },
        "results": results,
        "selected": selected,
        "reproduction": {
            "retained_bars": int(provenance["retained_bars"]),
            "observations": len(observations),
            "setups_10y": len(setups),
            "funnel": funnel,
        },
        "governance": {
            "research_only": True,
            "candidate_replacement_allowed_only_if_acceptance_pass": True,
            "candidate_replaced": False,
            "eligible_for_candidate_freeze": selected is not None,
            "fresh_holdout_consumed": False,
            "demo_eligible": False,
            "live_authorized": False,
            "real_capital_authorized": False,
            "production_authorized": False,
        },
    }
    output.mkdir(parents=True, exist_ok=True)
    (output / "r38-structural-fragility-risk-correction-report.json").write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n"
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
