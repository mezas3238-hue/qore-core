"""R32 causal memory de-fragmentation coverage lab.

R32 does not relax Turtle Soup execution rules.  It tests whether the specialist
memory is over-fragmented by exact CIBO route strings and high-dimensional
anatomy signatures.

The actual trade always uses the real active CIBO DOL price.  Route
normalization is used only to pool historical evidence for structurally
equivalent destinations before full-lifecycle 0.10R validation.

All memory schemes and economic/risk gates are declared before replay.
"""
from __future__ import annotations

import json
import sys
from collections import Counter, defaultdict
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
    cibo_gbpjpy_native_market_decision_memory_v2 as native,
)
from qore.infrastructure.trader_lab import turtle_soup_gbpjpy_r1 as r1
from qore.infrastructure.trader_lab import turtle_soup_gbpjpy_r3_cibo_journey as r3
from qore.infrastructure.trader_lab import (
    turtle_soup_gbpjpy_r3_cibo_journey_binding_repair as repair,
)
from qore.infrastructure.trader_lab import (
    turtle_soup_gbpjpy_r26_specialist_memory_brain as r26,
)
from qore.infrastructure.trader_lab import (
    turtle_soup_gbpjpy_specialist_cognitive_memory_v2 as v2,
)
from qore.infrastructure.trader_lab import (
    turtle_soup_gbpjpy_specialist_cognitive_memory_v3 as v3,
)
from qore.infrastructure.trader_lab import (
    turtle_soup_gbpjpy_specialist_memory_v1 as v1,
)
from qore.infrastructure.trader_lab.ict_turtle_soup_r4_source_exact import (
    SourceCandle,
    build_daily,
    build_h1,
    build_h4,
)

IDENTITY = "TURTLE_SOUP_GBPJPY_R32_CAUSAL_MEMORY_DEFRAGMENTATION_LAB_V1"
EVAL_OPEN = r26.EVAL_OPEN
EVAL_CLOSE = r26.EVAL_CLOSE

MIN_TRADES = 350
MIN_PF_010 = Decimal("1.90")
MAX_DD_010 = Decimal("6.0")
MAX_LS_010 = 3

MIN_OBSERVATIONS = 20
MIN_DISTINCT_QUARTERS = 4
MIN_REACH = Decimal("0.50")

SCHEMES: dict[str, tuple[tuple[str, ...], str]] = {
    "R32_ANATOMY_ROUTE_TYPES_HORIZON": (
        (
            "timeframe",
            "prior_body_alignment",
            "cisd_progress_bucket",
            "protected_risk_range_bucket",
            "source_range_state_bucket",
            "h4_range_state",
            "d1_range_state",
            "m5_volatility_state",
        ),
        "TYPES_AND_HORIZONS",
    ),
    "R32_ANATOMY_ROUTE_TYPES": (
        (
            "timeframe",
            "prior_body_alignment",
            "cisd_progress_bucket",
            "protected_risk_range_bucket",
            "source_range_state_bucket",
            "h4_range_state",
            "d1_range_state",
            "m5_volatility_state",
        ),
        "TYPES_ONLY",
    ),
    "R32_CORE_ROUTE_TYPES": (
        (
            "timeframe",
            "prior_body_alignment",
            "cisd_progress_bucket",
            "protected_risk_range_bucket",
            "h4_range_state",
            "d1_range_state",
            "m5_volatility_state",
        ),
        "TYPES_ONLY",
    ),
    "R32_REGIME_ROUTE_TYPES": (
        (
            "timeframe",
            "prior_body_alignment",
            "protected_risk_range_bucket",
            "h4_range_state",
            "d1_range_state",
            "m5_volatility_state",
        ),
        "TYPES_ONLY",
    ),
}


@dataclass(frozen=True, slots=True)
class Profile:
    observations: int
    distinct_quarters: int
    reach_rate: Decimal
    posture: str
    classification: str
    validated: bool


@dataclass(frozen=True, slots=True)
class Decision:
    target: native.NativeTarget
    posture: str
    classification: str
    observations: int
    source: str


def _single(root: Path, name: str) -> Path:
    matches = list(root.rglob(name))
    if len(matches) != 1:
        raise ValueError(f"expected exactly one {name}, got {len(matches)}")
    return matches[0]


def _route_family(route: str, mode: str) -> str:
    parts = [piece for piece in route.split("+") if piece]
    parsed: list[tuple[str, str]] = []
    for part in parts:
        if ":" not in part:
            raise ValueError(f"unexpected DOL route component: {part}")
        kind, horizon = part.rsplit(":", 1)
        parsed.append((kind, horizon))
    kinds = sorted({kind for kind, _ in parsed})
    if mode == "TYPES_ONLY":
        return "+".join(kinds)
    if mode == "TYPES_AND_HORIZONS":
        horizons = sorted({horizon for _, horizon in parsed})
        return f"{'+'.join(kinds)}@{'+'.join(horizons)}"
    raise ValueError(f"unknown route-family mode {mode}")


def _quarter(value: str) -> str:
    at = datetime.fromisoformat(value)
    return f"{at.year}-Q{((at.month - 1) // 3) + 1}"


def _signature(row: dict[str, Any], fields: Sequence[str]) -> str:
    return "|".join(str(row[field]) for field in fields)


def _target_family(row: dict[str, Any], route_mode: str) -> str:
    return (
        f"{int(row['target_rank'])}|"
        f"{_route_family(str(row['target_route']), route_mode)}"
    )


def _target_family_runtime(target: native.NativeTarget, route_mode: str) -> str:
    return f"{target.rank}|{_route_family(target.route, route_mode)}"


def _load_observations(v2_root: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with _single(
        v2_root,
        "turtle-soup-gbpjpy-specialist-observations-v2.jsonl",
    ).open(encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                rows.append(json.loads(line))
    if len(rows) != 41302:
        raise ValueError("Cognitive V2 observation drift")
    return rows


def _build_memory(
    rows: Sequence[dict[str, Any]],
    *,
    fields: Sequence[str],
    route_mode: str,
) -> tuple[dict[tuple[str, str], Profile], dict[str, Any]]:
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[
            (
                _signature(row, fields),
                _target_family(row, route_mode),
            )
        ].append(row)

    memory: dict[tuple[str, str], Profile] = {}
    classifications: Counter[str] = Counter()
    supported = 0
    for key, members in grouped.items():
        quarters = {_quarter(str(row["strategy_entry_at"])) for row in members}
        reached = sum(
            bool(row[f"{native.POSTURE_STATIC}_target_reached"])
            for row in members
        )
        reach = Decimal(reached) / Decimal(len(members))
        posture, _stats = v2._structural_posture(members)
        structural = (
            len(members) >= MIN_OBSERVATIONS
            and len(quarters) >= MIN_DISTINCT_QUARTERS
            and reach >= MIN_REACH
        )
        if structural:
            supported += 1
            validation = v3._validation(members, posture=posture)
            classification = str(validation["classification"])
            validated = bool(validation["validated"])
        else:
            classification = "NOT_EVALUATED_STRUCTURALLY_UNSUPPORTED"
            validated = False
        classifications[classification] += 1
        memory[key] = Profile(
            observations=len(members),
            distinct_quarters=len(quarters),
            reach_rate=reach,
            posture=posture,
            classification=classification,
            validated=validated,
        )
    summary = {
        "profiles": len(memory),
        "structurally_supported_profiles": supported,
        "classification_counts": dict(classifications),
        "validated_profiles": sum(item.validated for item in memory.values()),
    }
    return memory, summary


def _choose(
    *,
    setup: r3.Setup,
    ladder: Sequence[native.NativeTarget],
    regime: dict[str, str],
    fields: Sequence[str],
    route_mode: str,
    memory: dict[tuple[str, str], Profile],
) -> Decision | None:
    row = {**v1._setup_context(setup), **regime}
    signature = _signature(row, fields)
    candidates: list[Decision] = []
    for target in ladder:
        profile = memory.get(
            (signature, _target_family_runtime(target, route_mode))
        )
        if profile is None or not profile.validated:
            continue
        candidates.append(
            Decision(
                target=target,
                posture=profile.posture,
                classification=profile.classification,
                observations=profile.observations,
                source="R32_POOLED_CAUSAL_MEMORY",
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


def _runtime_decision(decision: Decision) -> r26.SpecialistDecision:
    return r26.SpecialistDecision(
        target=decision.target,
        memory_level="r32_pooled_causal_memory",
        classification=decision.classification,
        posture=decision.posture,
        mean_net_010_r=Decimal(0),
        observations=decision.observations,
    )


def _run_scheme(
    *,
    scheme: str,
    fields: Sequence[str],
    route_mode: str,
    memory: dict[tuple[str, str], Profile],
    memory_summary: dict[str, Any],
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
            setup=setup,
            ladder=ladder,
            regime=regime,
            fields=fields,
            route_mode=route_mode,
            memory=memory,
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
        counts[f"POSTURE_{runtime.posture}"] += 1
        counts[f"RANK_{runtime.target_rank}"] += 1
        counts[f"SOURCE_{decision.source}"] += 1

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
        "scheme": scheme,
        "fields": list(fields),
        "route_family_mode": route_mode,
        "memory_summary": memory_summary,
        "decision_counts": dict(counts),
        "gross": r26._stat(trades, "gross_r"),
        "net_005": r26._stat(trades, "net_005_r"),
        "net_010": net,
        "acceptance_pass": passed,
    }


def run(
    raw_root: Path,
    target_root: Path,
    v2_root: Path,
    output: Path,
) -> dict[str, Any]:
    evidence, provenance = journey.load_raw_m5(raw_root)
    if evidence.symbol != "GBPJPY" or int(provenance["retained_bars"]) != 745478:
        raise ValueError("unexpected GBPJPY corpus")
    observations = _load_observations(v2_root)
    target_rows = r26._load_targets(target_root)
    _episodes, source_index = repair._load_targets_fail_closed(target_root)

    memories: dict[
        str,
        tuple[
            tuple[str, ...],
            str,
            dict[tuple[str, str], Profile],
            dict[str, Any],
        ],
    ] = {}
    for scheme, (fields, route_mode) in SCHEMES.items():
        memory, summary = _build_memory(
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

    results: list[dict[str, Any]] = []
    for scheme, (fields, route_mode, memory, summary) in memories.items():
        results.append(
            _run_scheme(
                scheme=scheme,
                fields=fields,
                route_mode=route_mode,
                memory=memory,
                memory_summary=summary,
                setups=setups,
                evidence=evidence,
                opens=opens,
                tick=tick,
                target_rows=target_rows,
                source_index=source_index,
                frames=frames,
                frame_closes=frame_closes,
            )
        )

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
        "schema": "qore.turtle_soup_gbpjpy.r32_causal_memory_defragmentation.v1",
        "identity": IDENTITY,
        "window": {
            "open": EVAL_OPEN.isoformat(),
            "close": EVAL_CLOSE.isoformat(),
            "same_consumed_development_window": True,
        },
        "experiment_contract": {
            "fresh_holdout_consumed": False,
            "actual_dol_price_always_used": True,
            "route_family_only_pools_memory": True,
            "entry_changed": False,
            "c2_changed": False,
            "cisd_changed": False,
            "protected_swing_changed": False,
            "structural_rearm_changed": False,
            "regime_features_pre_entry_only": True,
            "economic_validation": "FULL_LIFECYCLE_010_EQUAL_COUNT_TERCILES_2_OF_3",
            "nearest_validated_dol_policy": True,
            "minimum_observations": MIN_OBSERVATIONS,
            "minimum_distinct_quarters": MIN_DISTINCT_QUARTERS,
            "minimum_static_protected_swing_reach": str(MIN_REACH),
            "schemes_predeclared": {
                key: {
                    "fields": list(value[0]),
                    "route_family_mode": value[1],
                }
                for key, value in SCHEMES.items()
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
        "selected_scheme": None if selected is None else selected["scheme"],
        "selected_result": selected,
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
            "fresh_holdout_consumed": False,
            "demo_eligible": False,
            "live_authorized": False,
            "real_capital_authorized": False,
            "production_authorized": False,
        },
    }
    output.mkdir(parents=True, exist_ok=True)
    (output / "r32-causal-memory-defragmentation-report.json").write_text(
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
