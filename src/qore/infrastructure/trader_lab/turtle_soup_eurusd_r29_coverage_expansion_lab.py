"""R29 coverage-expansion lab for the frozen R28 development line.

Goal: increase the number of 2Y trades without degrading the R28 risk/quality
profile.  The fresh holdout remains sealed.

The lab does NOT loosen Turtle Soup anatomy, Protected Swing, causal CISD,
active CIBO DOL, structural rearm, or the pre-entry regime model.  It only tests
whether a structurally-supported anatomy profile that lacks its own economic
validation may be recovered when the broader Regime+Journey memory independently
validates the same target.

Fallback recovery is restricted to DOL rank 1 because it is the nearest active
destination and therefore the least extrapolative journey extension.  This is a
structural distance rule, not a PnL-ranked target rule.

Acceptance is declared before reading the experiment:
- at least 250 trades;
- net@0.10 PF >= 1.80;
- net@0.10 max DD <= 8R;
- net@0.10 max losing streak <= 3.
Among passing variants, choose the one with the most trades, then PF, then lower
DD.  If none pass, R28 remains frozen and no replacement is created.
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
    cibo_eurusd_native_market_decision_memory_v2 as native,
)
from qore.infrastructure.trader_lab import turtle_soup_eurusd_r1 as r1
from qore.infrastructure.trader_lab import turtle_soup_eurusd_r3_cibo_journey as r3
from qore.infrastructure.trader_lab import (
    turtle_soup_eurusd_r3_cibo_journey_binding_repair as repair,
)
from qore.infrastructure.trader_lab import (
    turtle_soup_eurusd_r26_specialist_memory_brain as r26,
)
from qore.infrastructure.trader_lab import (
    turtle_soup_eurusd_r28_validated_specialist_brain as r28,
)
from qore.infrastructure.trader_lab import (
    turtle_soup_eurusd_specialist_cognitive_memory_v2 as v2,
)
from qore.infrastructure.trader_lab import (
    turtle_soup_eurusd_specialist_memory_v1 as v1,
)
from qore.infrastructure.trader_lab.ict_turtle_soup_r4_source_exact import (
    SourceCandle,
    build_daily,
    build_h1,
    build_h4,
)

IDENTITY = "TURTLE_SOUP_EURUSD_R29_COVERAGE_EXPANSION_LAB_V1"
EVAL_OPEN = r26.EVAL_OPEN
EVAL_CLOSE = r26.EVAL_CLOSE

MIN_TRADES = 250
MIN_PF_010 = Decimal("1.80")
MAX_DD_010 = Decimal("8.0")
MAX_LS_010 = 3

BASELINE = "R28_BASELINE"
ROBUST_AGREE = "R29_ROBUST_REGIME_RANK1_POSTURE_AGREE"
VALIDATED_AGREE = "R29_VALIDATED_REGIME_RANK1_POSTURE_AGREE"
ROBUST = "R29_ROBUST_REGIME_RANK1"
VALIDATED = "R29_VALIDATED_REGIME_RANK1"
VARIANTS = (BASELINE, ROBUST_AGREE, VALIDATED_AGREE, ROBUST, VALIDATED)


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
        _single(root, "turtle-soup-eurusd-specialist-cognitive-memory-v3.json").read_text()
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


def _fallback(
    cognitive: dict[str, Any],
    setup: r3.Setup,
    *,
    target: native.NativeTarget,
    regime: dict[str, str],
    variant: str,
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
    if not bool(anatomy.get("structurally_supported", False)):
        return None
    validation = cast(dict[str, Any], context.get("economic_validation", {}))
    if not bool(validation.get("validated", False)):
        return None

    classification = str(validation.get("classification"))
    robust_only = variant in {ROBUST_AGREE, ROBUST}
    posture_agree = variant in {ROBUST_AGREE, VALIDATED_AGREE}
    if robust_only and classification != "ROBUST_VALIDATED_010":
        return None
    if posture_agree and anatomy["preferred_posture"] != context["preferred_posture"]:
        return None

    return Decision(
        target=target,
        memory_level="anatomy_regime+regime_journey",
        classification=classification,
        posture=str(anatomy["preferred_posture"]),
        observations=int(anatomy["observations"]),
        source="REGIME_JOURNEY_CORROBORATED_RANK1",
    )


def choose(
    cognitive: dict[str, Any],
    setup: r3.Setup,
    *,
    ladder: Sequence[native.NativeTarget],
    regime: dict[str, str],
    variant: str,
) -> Decision | None:
    baseline = r28.choose_decision(
        cognitive,
        setup,
        ladder=ladder,
        regime=regime,
    )
    if baseline is not None:
        return Decision(
            target=baseline.target,
            memory_level=baseline.memory_level,
            classification=baseline.classification,
            posture=baseline.posture,
            observations=baseline.observations,
            source="R28_AUTHORITATIVE",
        )
    if variant == BASELINE:
        return None

    recovered = [
        item
        for target in ladder
        if (
            item := _fallback(
                cognitive,
                setup,
                target=target,
                regime=regime,
                variant=variant,
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
    if evidence.symbol != "EURUSD" or int(provenance["retained_bars"]) != 745458:
        raise ValueError("unexpected EURUSD corpus")
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
        for variant in VARIANTS
    ]
    passing = [item for item in results if item["acceptance_pass"]]

    def rank(item: dict[str, Any]) -> tuple[int, Decimal, Decimal]:
        net = item["net_010"]
        return (
            int(net["trades"]),
            Decimal(str(net["profit_factor"])),
            -Decimal(str(net["max_drawdown_r"])),
        )

    selected = max(passing, key=rank) if passing else None
    payload = {
        "schema": "qore.turtle_soup_eurusd.r29_coverage_expansion_lab.v1",
        "identity": IDENTITY,
        "window": {
            "open": EVAL_OPEN.isoformat(),
            "close": EVAL_CLOSE.isoformat(),
            "same_consumed_development_window": True,
        },
        "experiment_contract": {
            "fresh_holdout_consumed": False,
            "r28_rules_relaxed": False,
            "protected_swing_changed": False,
            "c2_changed": False,
            "cisd_changed": False,
            "regime_model_changed": False,
            "fallback_requires_anatomy_structural_support": True,
            "fallback_requires_same_target_regime_journey_validation": True,
            "fallback_target_rank": 1,
            "fallback_reason": "NEAREST_ACTIVE_DOL_MINIMUM_JOURNEY_EXTRAPOLATION",
            "variants": list(VARIANTS),
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
    (output / "r29-coverage-expansion-lab-report.json").write_text(
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
