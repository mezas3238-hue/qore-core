"""R31 temporal-validation coverage lab.

R31 keeps the R28/R30 causal architecture and nearest validated DOL policy.
It tests predeclared temporal-stability definitions for already structurally
defined memory profiles.  No economic magnitude is used to rank targets.

Acceptance remains fixed:
- >=250 trades
- PF@0.10 >=1.80
- max DD@0.10 <=8R
- max losing streak <=3

The fresh holdout remains sealed.
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

IDENTITY = "TURTLE_SOUP_XAUUSD_R31_TEMPORAL_VALIDATION_COVERAGE_LAB_V1"
EVAL_OPEN = r26.EVAL_OPEN
EVAL_CLOSE = r26.EVAL_CLOSE

MIN_TRADES = 250
MIN_PF_010 = Decimal("1.80")
MAX_DD_010 = Decimal("8.0")
MAX_LS_010 = 3

VARIANTS: dict[str, dict[str, Any]] = {
    "R31_TERCILE_2OF3_ORIGINAL_SUPPORT": {
        "parts": 3,
        "minimum_positive_parts": 2,
        "minimum_observations": 20,
        "minimum_quarters": 4,
        "minimum_reach": Decimal("0.50"),
    },
    "R31_QUARTILE_2OF4_ORIGINAL_SUPPORT": {
        "parts": 4,
        "minimum_positive_parts": 2,
        "minimum_observations": 20,
        "minimum_quarters": 4,
        "minimum_reach": Decimal("0.50"),
    },
    "R31_QUINTILE_3OF5_ORIGINAL_SUPPORT": {
        "parts": 5,
        "minimum_positive_parts": 3,
        "minimum_observations": 20,
        "minimum_quarters": 4,
        "minimum_reach": Decimal("0.50"),
    },
    "R31_QUARTILE_2OF4_OBS16_REACH055": {
        "parts": 4,
        "minimum_positive_parts": 2,
        "minimum_observations": 16,
        "minimum_quarters": 4,
        "minimum_reach": Decimal("0.55"),
    },
    "R31_QUINTILE_3OF5_OBS16_REACH055": {
        "parts": 5,
        "minimum_positive_parts": 3,
        "minimum_observations": 16,
        "minimum_quarters": 4,
        "minimum_reach": Decimal("0.55"),
    },
    "R31_QUARTILE_2OF4_OBS12_REACH060": {
        "parts": 4,
        "minimum_positive_parts": 2,
        "minimum_observations": 12,
        "minimum_quarters": 4,
        "minimum_reach": Decimal("0.60"),
    },
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
    posture: str
    observations: int


def _single(root: Path, name: str) -> Path:
    matches = list(root.rglob(name))
    if len(matches) != 1:
        raise ValueError(f"expected exactly one {name}, got {len(matches)}")
    return matches[0]


def _load_v2(root: Path) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    cognitive = json.loads(
        _single(root, "turtle-soup-xauusd-specialist-cognitive-memory-v2.json").read_text()
    )
    observations: list[dict[str, Any]] = []
    with _single(
        root, "turtle-soup-xauusd-specialist-observations-v2.jsonl"
    ).open(encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                observations.append(json.loads(line))
    if len(observations) != 34850:
        raise ValueError("unexpected Specialist Cognitive V2 observation count")
    return cast(dict[str, Any], cognitive), observations


def _equal_parts(
    rows: Sequence[dict[str, Any]],
    parts: int,
) -> list[list[dict[str, Any]]]:
    ordered = sorted(rows, key=lambda row: str(row["strategy_entry_at"]))
    n = len(ordered)
    result = []
    for index in range(parts):
        left = (index * n) // parts
        right = ((index + 1) * n) // parts
        chunk = ordered[left:right]
        if not chunk:
            return []
        result.append(chunk)
    return result


def _mean(rows: Sequence[dict[str, Any]], field: str) -> Decimal:
    return sum((Decimal(str(row[field])) for row in rows), Decimal(0)) / Decimal(len(rows))


def _validated(
    rows: Sequence[dict[str, Any]],
    *,
    posture: str,
    rule: dict[str, Any],
) -> bool:
    if len(rows) < int(rule["minimum_observations"]):
        return False
    quarters = {
        f"{datetime.fromisoformat(str(row['strategy_entry_at'])).year}-Q"
        f"{((datetime.fromisoformat(str(row['strategy_entry_at'])).month - 1) // 3) + 1}"
        for row in rows
    }
    if len(quarters) < int(rule["minimum_quarters"]):
        return False

    static_reach = (
        Decimal(
            sum(bool(row["STATIC_target_reached"]) for row in rows)
        )
        / Decimal(len(rows))
    )
    if static_reach < cast(Decimal, rule["minimum_reach"]):
        return False

    field = f"{posture}_net_010_r"
    combined = _mean(rows, field)
    if combined <= 0:
        return False
    chunks = _equal_parts(rows, int(rule["parts"]))
    if not chunks:
        return False
    positive = sum(_mean(chunk, field) > 0 for chunk in chunks)
    return positive >= int(rule["minimum_positive_parts"])


def _validated_sets(
    cognitive: dict[str, Any],
    observations: Sequence[dict[str, Any]],
    rule: dict[str, Any],
) -> dict[str, set[tuple[str, str]]]:
    grouped: dict[tuple[str, str, str], list[dict[str, Any]]] = defaultdict(list)
    for level, fields in v2.LEVELS:
        if level not in v2.AUTHORITATIVE_LEVELS:
            continue
        for row in observations:
            grouped[(level, v2._key(row, fields), v2._target_key(row))].append(row)

    result: dict[str, set[tuple[str, str]]] = {
        level: set() for level in v2.AUTHORITATIVE_LEVELS
    }
    for (level, signature, target_key), rows in grouped.items():
        item = cast(dict[str, Any], cognitive[level]["signatures"]).get(signature)
        if item is None:
            continue
        profile = cast(dict[str, Any], item["targets"]).get(target_key)
        if profile is None:
            continue
        posture = str(profile["preferred_posture"])
        if _validated(rows, posture=posture, rule=rule):
            result[level].add((signature, target_key))
    return result


def _profile(
    cognitive: dict[str, Any],
    row: dict[str, Any],
    level: str,
) -> tuple[str, dict[str, Any] | None]:
    fields = dict(v2.LEVELS)[level]
    signature = v2._key(row, fields)
    item = cast(dict[str, Any], cognitive[level]["signatures"]).get(signature)
    if item is None:
        return signature, None
    return signature, cast(dict[str, Any], item["targets"]).get(v2._target_key(row))


def choose(
    cognitive: dict[str, Any],
    validated: dict[str, set[tuple[str, str]]],
    setup: r3.Setup,
    *,
    ladder: Sequence[native.NativeTarget],
    regime: dict[str, str],
) -> Decision | None:
    candidates: list[Decision] = []
    for target in ladder:
        row = {
            **v1._setup_context(setup),
            **regime,
            "target_rank": target.rank,
            "target_route": target.route,
        }
        target_key = v2._target_key(row)
        for level in v2.AUTHORITATIVE_LEVELS:
            signature, profile = _profile(cognitive, row, level)
            if profile is None or (signature, target_key) not in validated[level]:
                continue
            candidates.append(
                Decision(
                    target=target,
                    memory_level=level,
                    posture=str(profile["preferred_posture"]),
                    observations=int(profile["observations"]),
                )
            )
            break
    if not candidates:
        return None
    best_level = max(LEVEL_PRIORITY[item.memory_level] for item in candidates)
    same = [
        item for item in candidates if LEVEL_PRIORITY[item.memory_level] == best_level
    ]
    return min(
        same,
        key=lambda item: (
            item.target.rank,
            -item.observations,
            item.target.route,
        ),
    )


def _runtime_decision(decision: Decision) -> r26.SpecialistDecision:
    return r26.SpecialistDecision(
        target=decision.target,
        memory_level=decision.memory_level,
        classification="R31_TEMPORAL_VALIDATED",
        posture=decision.posture,
        mean_net_010_r=Decimal(0),
        observations=decision.observations,
    )


def _run_variant(
    *,
    name: str,
    rule: dict[str, Any],
    setups: Sequence[r3.Setup],
    evidence: Any,
    opens: Sequence[datetime],
    tick: Decimal,
    target_rows: dict[str, list[dict[str, Any]]],
    source_index: dict[tuple[datetime, str, str, Decimal], str],
    cognitive: dict[str, Any],
    observations: Sequence[dict[str, Any]],
    frames: dict[str, tuple[SourceCandle, ...]],
    frame_closes: dict[str, tuple[datetime, ...]],
) -> dict[str, Any]:
    valid = _validated_sets(cognitive, observations, rule)
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
            valid,
            setup,
            ladder=ladder,
            regime=regime,
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
        counts[f"LEVEL_{runtime.memory_level}"] += 1
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
        "variant": name,
        "rule": {
            key: (str(value) if isinstance(value, Decimal) else value)
            for key, value in rule.items()
        },
        "validated_profile_counts": {
            level: len(items) for level, items in valid.items()
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
    cognitive_v2_root: Path,
    output: Path,
) -> dict[str, Any]:
    evidence, provenance = journey.load_raw_m5(raw_root)
    if evidence.symbol != "XAUUSD" or int(provenance["retained_bars"]) != 707716:
        raise ValueError("unexpected XAUUSD corpus")
    cognitive, observations = _load_v2(cognitive_v2_root)
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
            name=name,
            rule=rule,
            setups=setups,
            evidence=evidence,
            opens=opens,
            tick=tick,
            target_rows=target_rows,
            source_index=source_index,
            cognitive=cognitive,
            observations=observations,
            frames=frames,
            frame_closes=frame_closes,
        )
        for name, rule in VARIANTS.items()
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
        "schema": "qore.turtle_soup_xauusd.r31_temporal_validation_coverage_lab.v1",
        "identity": IDENTITY,
        "window": {
            "open": EVAL_OPEN.isoformat(),
            "close": EVAL_CLOSE.isoformat(),
            "same_consumed_development_window": True,
        },
        "experiment_contract": {
            "fresh_holdout_consumed": False,
            "nearest_validated_dol_policy": True,
            "entry_changed": False,
            "c2_changed": False,
            "cisd_changed": False,
            "protected_swing_changed": False,
            "regime_model_changed": False,
            "management_posture_changed_by_economic_validation": False,
            "economic_magnitude_ranks_targets": False,
            "combined_net_010_must_be_positive": True,
            "variants_predeclared": {
                name: {
                    key: (str(value) if isinstance(value, Decimal) else value)
                    for key, value in rule.items()
                }
                for name, rule in VARIANTS.items()
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
            "specialist_observations": len(observations),
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
    (output / "r31-temporal-validation-coverage-lab-report.json").write_text(
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
