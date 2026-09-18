"""R33 structural subfamily ensemble + pre-trade risk governor.

R33 preserves R30 as the high-authority core.  Additional trades are admitted
only when R30 abstains and the setup belongs to one of a small set of
predeclared structural Turtle Soup subfamilies found during consumed development
forensics.  Expansion always uses the actual nearest active rank-1 CIBO DOL,
STATIC lifecycle, exact C2/CISD, and the exact Protected Swing stop.

Risk governors never suppress a trade.  They only scale the risk unit from
information known before the trade: current scaled-equity drawdown.  This keeps
operation count genuine while limiting capital drawdown.

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
    turtle_soup_xauusd_r30_nearest_dol_coverage_lab as r30,
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

IDENTITY = "TURTLE_SOUP_XAUUSD_R33_SUBFAMILY_RISK_GOVERNOR_LAB_V1"
EVAL_OPEN = r26.EVAL_OPEN
EVAL_CLOSE = r26.EVAL_CLOSE

MIN_TRADES = 350
MIN_PF_010 = Decimal("1.90")
MAX_DD_010 = Decimal("6.0")

F1 = "SHALLOW_RAID_SMALL_BODY_OPPOSING_M5"
F2 = "LONG_DELAYED_RECLAIM_MEDIUM_BODY"
F3 = "ASIA_SHALLOW_RAID_DELAYED_RECLAIM"
F4 = "CLEAN_REJECTION_LOW_EFFICIENCY_OPPOSING_M5"
F5 = "OTHER_SESSION_SHALLOW_RAID_CONTROLLED_WICK"

FAMILY_SETS: dict[str, tuple[str, ...]] = {
    "R33_FOUR_FAMILY": (F1, F2, F3, F4),
    "R33_FIVE_FAMILY": (F1, F2, F3, F4, F5),
}

FAMILY_DEV_EVIDENCE: dict[str, dict[str, Any]] = {
    F1: {
        "rank1_10y_n": 275,
        "rank1_10y_pf_010": "1.262993549911129",
        "positive_chronological_quintiles": 4,
    },
    F2: {
        "rank1_10y_n": 224,
        "rank1_10y_pf_010": "1.3201911328370302",
        "positive_chronological_quintiles": 4,
    },
    F3: {
        "rank1_10y_n": 166,
        "rank1_10y_pf_010": "1.2818019007303165",
        "positive_chronological_quintiles": 4,
    },
    F4: {
        "rank1_10y_n": 133,
        "rank1_10y_pf_010": "1.6041545673474031",
        "positive_chronological_quintiles": 4,
    },
    F5: {
        "rank1_10y_n": 118,
        "rank1_10y_pf_010": "1.2862761652941648",
        "positive_chronological_quintiles": 4,
    },
}

GOVERNORS: dict[str, tuple[Decimal, Decimal, Decimal, Decimal]] = {
    # (first_dd, second_dd, middle_scale, deep_scale)
    "FIXED_1R": (
        Decimal("999"),
        Decimal("1000"),
        Decimal("1"),
        Decimal("1"),
    ),
    "DD_2_4_SCALE_075_050": (
        Decimal("2"),
        Decimal("4"),
        Decimal("0.75"),
        Decimal("0.50"),
    ),
    "DD_1P5_3_SCALE_075_050": (
        Decimal("1.5"),
        Decimal("3"),
        Decimal("0.75"),
        Decimal("0.50"),
    ),
    "DD_2_4_SCALE_075_025": (
        Decimal("2"),
        Decimal("4"),
        Decimal("0.75"),
        Decimal("0.25"),
    ),
    "DD_1_3_SCALE_075_025": (
        Decimal("1"),
        Decimal("3"),
        Decimal("0.75"),
        Decimal("0.25"),
    ),
}


@dataclass(frozen=True, slots=True)
class Decision:
    target: native.NativeTarget
    posture: str
    classification: str
    observations: int
    source: str
    family: str | None


def _single(root: Path, name: str) -> Path:
    matches = list(root.rglob(name))
    if len(matches) != 1:
        raise ValueError(f"expected exactly one {name}, got {len(matches)}")
    return matches[0]


def _load_cognitive(root: Path) -> dict[str, Any]:
    payload = json.loads(
        _single(
            root,
            "turtle-soup-xauusd-specialist-cognitive-memory-v3.json",
        ).read_text()
    )
    if not isinstance(payload, dict):
        raise ValueError("Cognitive V3 must be an object")
    return payload


def _matched_families(
    setup: r3.Setup,
    regime: dict[str, str],
) -> tuple[str, ...]:
    ctx = v1._setup_context(setup)
    matched: list[str] = []

    if (
        ctx["raid_depth_range_bucket"] == "q1:<=0.05"
        and ctx["body_fraction_bucket"] == "q1:<=0.25"
        and regime["m5_displacement_alignment"] == "opposed"
    ):
        matched.append(F1)

    if (
        ctx["side"] == "long"
        and ctx["reclaim_latency_bucket"] == "6-15m"
        and ctx["body_fraction_bucket"] == "q3:<=0.75"
    ):
        matched.append(F2)

    if (
        ctx["session"] == "asia"
        and ctx["raid_depth_range_bucket"] == "q2:<=0.10"
        and ctx["reclaim_latency_bucket"] == "6-15m"
    ):
        matched.append(F3)

    if (
        ctx["rejection_wick_bucket"] == "q2:<=0.25"
        and regime["m5_efficiency_state"] == "low"
        and regime["m5_displacement_alignment"] == "opposed"
    ):
        matched.append(F4)

    if (
        ctx["session"] == "other"
        and ctx["raid_depth_range_bucket"] == "q2:<=0.10"
        and ctx["rejection_wick_bucket"] == "q3:<=0.50"
    ):
        matched.append(F5)

    return tuple(matched)


def _choose(
    *,
    cognitive: dict[str, Any],
    setup: r3.Setup,
    ladder: Sequence[native.NativeTarget],
    regime: dict[str, str],
    allowed_families: Sequence[str],
) -> Decision | None:
    baseline = r30._nearest_validated(
        r30._validated_candidates(
            cognitive,
            setup,
            ladder=ladder,
            regime=regime,
        )
    )
    if baseline is not None:
        return Decision(
            target=baseline.target,
            posture=baseline.posture,
            classification=baseline.classification,
            observations=baseline.observations,
            source="R30_CORE",
            family=None,
        )

    matched = [
        family
        for family in _matched_families(setup, regime)
        if family in allowed_families
    ]
    if not matched:
        return None
    target = next((item for item in ladder if item.rank == 1), None)
    if target is None:
        return None
    family = sorted(matched)[0]
    return Decision(
        target=target,
        posture=native.POSTURE_STATIC,
        classification="CONSUMED_DEVELOPMENT_STRUCTURAL_SUBFAMILY",
        observations=int(FAMILY_DEV_EVIDENCE[family]["rank1_10y_n"]),
        source="R33_STRUCTURAL_EXPANSION",
        family=family,
    )


def _runtime_decision(decision: Decision) -> r26.SpecialistDecision:
    return r26.SpecialistDecision(
        target=decision.target,
        memory_level=decision.source,
        classification=decision.classification,
        posture=decision.posture,
        mean_net_010_r=Decimal(0),
        observations=decision.observations,
    )


def _risk_scale(
    drawdown: Decimal,
    governor: tuple[Decimal, Decimal, Decimal, Decimal],
) -> Decimal:
    first, second, middle, deep = governor
    if drawdown < first:
        return Decimal("1")
    if drawdown < second:
        return middle
    return deep


def _scaled_stat(
    trades: Sequence[r26.RuntimeTrade],
    governor_name: str,
) -> dict[str, Any]:
    governor = GOVERNORS[governor_name]
    equity = Decimal(0)
    peak = Decimal(0)
    max_dd = Decimal(0)
    gains = Decimal(0)
    losses = Decimal(0)
    losing_streak = 0
    max_losing_streak = 0
    scales: Counter[str] = Counter()

    for trade in trades:
        pretrade_dd = peak - equity
        scale = _risk_scale(pretrade_dd, governor)
        scales[str(scale)] += 1
        contribution = trade.net_010_r * scale
        equity += contribution
        peak = max(peak, equity)
        max_dd = max(max_dd, peak - equity)
        if contribution > 0:
            gains += contribution
            losing_streak = 0
        elif contribution < 0:
            losses += -contribution
            losing_streak += 1
            max_losing_streak = max(max_losing_streak, losing_streak)

    pf = None if losses == 0 else gains / losses
    n = len(trades)
    return {
        "trades": n,
        "total_scaled_net_010_r": str(equity),
        "mean_scaled_net_010_r": (
            None if n == 0 else str(equity / Decimal(n))
        ),
        "profit_factor_scaled_net_010": None if pf is None else str(pf),
        "max_drawdown_scaled_r": str(max_dd),
        "max_losing_streak": max_losing_streak,
        "risk_scale_counts": dict(scales),
        "minimum_risk_scale": min(
            (Decimal(key) for key in scales),
            default=Decimal(0),
        ).to_eng_string(),
    }


def _run_family_set(
    *,
    family_set: str,
    allowed_families: Sequence[str],
    cognitive: dict[str, Any],
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
        decision = _choose(
            cognitive=cognitive,
            setup=setup,
            ladder=ladder,
            regime=regime,
            allowed_families=allowed_families,
        )
        if decision is None:
            counts["ABSTAIN_NO_AUTHORITY_OR_SUBFAMILY"] += 1
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
        if decision.family is not None:
            counts[f"FAMILY_{decision.family}"] += 1
        counts[f"RANK_{runtime.target_rank}"] += 1

    risk_results: list[dict[str, Any]] = []
    for governor_name in GOVERNORS:
        stat = _scaled_stat(trades, governor_name)
        pf_raw = stat["profit_factor_scaled_net_010"]
        pf = None if pf_raw is None else Decimal(str(pf_raw))
        dd = Decimal(str(stat["max_drawdown_scaled_r"]))
        passed = bool(
            len(trades) >= MIN_TRADES
            and pf is not None
            and pf >= MIN_PF_010
            and dd <= MAX_DD_010
        )
        risk_results.append(
            {
                "governor": governor_name,
                "stats": stat,
                "acceptance_pass": passed,
            }
        )

    return {
        "family_set": family_set,
        "allowed_families": list(allowed_families),
        "decision_counts": dict(counts),
        "fixed_trade_stats": {
            "gross": r26._stat(trades, "gross_r"),
            "net_005": r26._stat(trades, "net_005_r"),
            "net_010": r26._stat(trades, "net_010_r"),
        },
        "risk_governors": risk_results,
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
        _run_family_set(
            family_set=name,
            allowed_families=families,
            cognitive=cognitive,
            setups=setups,
            evidence=evidence,
            opens=opens,
            tick=tick,
            target_rows=target_rows,
            source_index=source_index,
            frames=frames,
            frame_closes=frame_closes,
        )
        for name, families in FAMILY_SETS.items()
    ]

    passing: list[dict[str, Any]] = []
    for result in results:
        for risk in result["risk_governors"]:
            if risk["acceptance_pass"]:
                passing.append(
                    {
                        "family_set": result["family_set"],
                        "governor": risk["governor"],
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
        "schema": "qore.turtle_soup_xauusd.r33_subfamily_risk_governor.v1",
        "identity": IDENTITY,
        "window": {
            "open": EVAL_OPEN.isoformat(),
            "close": EVAL_CLOSE.isoformat(),
            "same_consumed_development_window": True,
        },
        "experiment_contract": {
            "fresh_holdout_consumed": False,
            "r30_core_preserved": True,
            "expansion_only_when_r30_abstains": True,
            "expansion_target_rank": 1,
            "actual_active_cibo_dol_price_used": True,
            "expansion_posture": native.POSTURE_STATIC,
            "entry_changed": False,
            "c2_changed": False,
            "cisd_changed": False,
            "protected_swing_changed": False,
            "structural_rearm_changed": False,
            "risk_governor_suppresses_trades": False,
            "risk_governor_pretrade_state_only": True,
            "family_sets_predeclared": {
                name: list(families)
                for name, families in FAMILY_SETS.items()
            },
            "family_consumed_development_evidence": FAMILY_DEV_EVIDENCE,
            "governors_predeclared": {
                name: {
                    "first_drawdown_r": str(rule[0]),
                    "second_drawdown_r": str(rule[1]),
                    "middle_scale": str(rule[2]),
                    "deep_scale": str(rule[3]),
                }
                for name, rule in GOVERNORS.items()
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
    (output / "r33-subfamily-risk-governor-report.json").write_text(
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
