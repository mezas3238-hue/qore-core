"""R23 hierarchical subtype + friction-resilience memory for XAUUSD.

Consumed-evidence research only.

This memory solves two remaining R22 problems without PnL mining:

1. Hierarchical subtype generalization
   R21 exact CAUTIOUS/MIXED signatures are resolved using the most-specific
   temporally stable causal ancestor:
       exact -> core6 -> core5 -> anatomy4
   A level is stable only when the same structural label has a strict majority
   in early, transition, and recent periods with the fixed sample floor.

2. 0.10R target friction resilience
   For otherwise eligible setups, rank-1 and rank-2 active CIBO DOLs are
   studied structurally.  A target family/geometry is RESILIENT_010 only when:
   - each temporal block has the fixed minimum sample;
   - its selected-DOL hit rate exceeds the mathematical break-even hit
     requirement implied by planned RR and 0.10R friction in every block; and
   - the combined 95% Wilson lower bound also exceeds the combined break-even
     requirement.

No realized trade PnL, PF, drawdown, or economic threshold search is used to
fit either memory.  The target outcome is simply selected DOL reached or not
reached before original Protected Swing/lifecycle termination.
"""
from __future__ import annotations

import json
import math
import sys
from collections import Counter, defaultdict
from collections.abc import Sequence
from decimal import Decimal
from pathlib import Path
from statistics import median
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
    turtle_soup_xauusd_r21_cautious_mixed_subtype_memory as r21,
)

IDENTITY = "TURTLE_SOUP_XAUUSD_R23_HIERARCHICAL_FRICTION_MEMORY_V1"

PERIODS = (
    "early_2016_2020",
    "transition_2021_2023",
    "recent_2024_2026",
)
SUBTYPE_MIN_PER_PERIOD = 5
RESILIENCE_MIN_PER_PERIOD = 10
STRESS_FRICTION_R = Decimal("0.10")
WILSON_Z = 1.96

RESILIENT = "RESILIENT_010"
NON_RESILIENT = "NON_RESILIENT_010"
UNRESOLVED = "UNRESOLVED"

RR_CUTS = (
    Decimal("0.5"),
    Decimal("1.0"),
    Decimal("1.5"),
    Decimal("2.5"),
)

SUBTYPE_LEVELS: tuple[tuple[str, tuple[str, ...]], ...] = (
    (
        "exact",
        (
            "memory_state",
            "source_timeframe",
            "fvg_before_entry",
            "cisd_progress_bucket",
            "protected_risk_range_bucket",
            "source_range_state_bucket",
            "brain_posture",
        ),
    ),
    (
        "core6",
        (
            "memory_state",
            "source_timeframe",
            "fvg_before_entry",
            "cisd_progress_bucket",
            "protected_risk_range_bucket",
            "source_range_state_bucket",
        ),
    ),
    (
        "core5",
        (
            "memory_state",
            "fvg_before_entry",
            "cisd_progress_bucket",
            "protected_risk_range_bucket",
            "source_range_state_bucket",
        ),
    ),
    (
        "anatomy4",
        (
            "memory_state",
            "fvg_before_entry",
            "cisd_progress_bucket",
            "protected_risk_range_bucket",
        ),
    ),
)

RESILIENCE_LEVELS: tuple[tuple[str, tuple[str, ...]], ...] = (
    (
        "r1",
        (
            "memory_state",
            "source_timeframe",
            "target_rank",
            "target_route",
            "planned_rr_bucket",
        ),
    ),
    (
        "r2",
        (
            "memory_state",
            "target_rank",
            "target_route",
            "planned_rr_bucket",
        ),
    ),
    (
        "r3",
        (
            "target_rank",
            "target_route",
            "planned_rr_bucket",
        ),
    ),
    (
        "r4",
        (
            "target_rank",
            "planned_rr_bucket",
        ),
    ),
)

TARGET_REASONS = frozenset({"TARGET", "GAP_TARGET_CAPPED"})


def _period(year: int) -> str:
    if 2016 <= year <= 2020:
        return "early_2016_2020"
    if 2021 <= year <= 2023:
        return "transition_2021_2023"
    if 2024 <= year <= 2026:
        return "recent_2024_2026"
    return "outside"


def _key(row: dict[str, Any], fields: Sequence[str]) -> str:
    return "|".join(str(row[field]) for field in fields)


def _strict_majority(counts: Counter[str]) -> str | None:
    total = sum(counts.values())
    if total == 0:
        return None
    top = counts.most_common()
    if len(top) > 1 and top[0][1] == top[1][1]:
        return None
    if top[0][1] * 2 <= total:
        return None
    return top[0][0]


def _stable_subtype(rows: Sequence[dict[str, Any]]) -> dict[str, Any]:
    period_counts: dict[str, Counter[str]] = {
        period: Counter() for period in PERIODS
    }
    for row in rows:
        period = str(row["period"])
        if period in period_counts:
            period_counts[period][str(row["structural_label"])] += 1

    majorities: dict[str, str | None] = {}
    sufficient = True
    for period in PERIODS:
        counts = period_counts[period]
        if sum(counts.values()) < SUBTYPE_MIN_PER_PERIOD:
            sufficient = False
        majorities[period] = _strict_majority(counts)

    labels = {label for label in majorities.values() if label is not None}
    stable = (
        sufficient
        and len(labels) == 1
        and all(majorities[p] is not None for p in PERIODS)
    )
    return {
        "classification": next(iter(labels)) if stable else r21.UNRESOLVED,
        "stable": stable,
        "observations": len(rows),
        "period_counts": {
            period: dict(period_counts[period]) for period in PERIODS
        },
        "period_majorities": majorities,
    }


def _build_hierarchy(
    ledger: Sequence[dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    hierarchy: dict[str, dict[str, Any]] = {}
    for level_name, fields in SUBTYPE_LEVELS:
        grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for row in ledger:
            grouped[_key(row, fields)].append(row)
        models = {
            signature: {
                **_stable_subtype(rows),
                "fields": list(fields),
                "values": {field: rows[0][field] for field in fields},
            }
            for signature, rows in sorted(grouped.items())
        }
        hierarchy[level_name] = {
            "fields": list(fields),
            "signatures": models,
            "stable_counts": dict(
                Counter(
                    str(item["classification"])
                    for item in models.values()
                    if bool(item["stable"])
                )
            ),
        }
    return hierarchy


def resolve_subtype(
    hierarchy: dict[str, dict[str, Any]],
    row: dict[str, Any],
) -> tuple[str, str | None, str | None]:
    for level_name, fields in SUBTYPE_LEVELS:
        signature = _key(row, fields)
        level = hierarchy[level_name]
        item = cast(dict[str, Any], level["signatures"]).get(signature)
        if item is not None and bool(item["stable"]):
            return str(item["classification"]), level_name, signature
    return r21.UNRESOLVED, None, None


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


def _break_even_hit_requirement(rr: Decimal) -> Decimal:
    if rr <= 0:
        return Decimal(1)
    return (Decimal(1) + STRESS_FRICTION_R) / (rr + Decimal(1))


def _wilson_lower(hits: int, total: int) -> float:
    if total <= 0:
        return 0.0
    p = hits / total
    z2 = WILSON_Z * WILSON_Z
    denom = 1.0 + z2 / total
    centre = p + z2 / (2.0 * total)
    adjust = WILSON_Z * math.sqrt(
        (p * (1.0 - p) + z2 / (4.0 * total)) / total
    )
    return (centre - adjust) / denom


def _period_resilience(rows: Sequence[dict[str, Any]]) -> dict[str, Any]:
    n = len(rows)
    if n == 0:
        return {
            "n": 0,
            "hits": 0,
            "hit_rate": None,
            "median_planned_rr": None,
            "median_break_even_hit_requirement": None,
        }
    hits = sum(bool(row["selected_dol_reached"]) for row in rows)
    rrs = [Decimal(str(row["planned_rr"])) for row in rows]
    median_rr = median(rrs)
    requirements = [_break_even_hit_requirement(rr) for rr in rrs]
    requirement = median(requirements)
    return {
        "n": n,
        "hits": hits,
        "hit_rate": str(Decimal(hits) / Decimal(n)),
        "median_planned_rr": str(median_rr),
        "median_break_even_hit_requirement": str(requirement),
        "wilson_lower_95": str(Decimal(str(_wilson_lower(hits, n)))),
    }


def _resilience_classification(
    rows: Sequence[dict[str, Any]],
) -> dict[str, Any]:
    by_period = {
        period: [row for row in rows if row["period"] == period]
        for period in PERIODS
    }
    profiles = {
        period: _period_resilience(by_period[period]) for period in PERIODS
    }
    sufficient = all(
        int(profiles[period]["n"]) >= RESILIENCE_MIN_PER_PERIOD
        for period in PERIODS
    )
    period_pass: dict[str, bool] = {}
    period_fail: dict[str, bool] = {}
    for period in PERIODS:
        profile = profiles[period]
        if not profile["n"]:
            period_pass[period] = False
            period_fail[period] = False
            continue
        rate = Decimal(str(profile["hit_rate"]))
        requirement = Decimal(str(profile["median_break_even_hit_requirement"]))
        period_pass[period] = rate > requirement
        period_fail[period] = rate < requirement

    combined = _period_resilience(rows)
    combined_lb = Decimal(str(combined["wilson_lower_95"]))
    combined_req = Decimal(str(combined["median_break_even_hit_requirement"]))

    if (
        sufficient
        and all(period_pass.values())
        and combined_lb > combined_req
    ):
        classification = RESILIENT
    elif sufficient and all(period_fail.values()):
        classification = NON_RESILIENT
    else:
        classification = UNRESOLVED

    return {
        "classification": classification,
        "observations": len(rows),
        "period_profiles": profiles,
        "combined": combined,
        "minimum_per_period": RESILIENCE_MIN_PER_PERIOD,
        "stress_friction_r": str(STRESS_FRICTION_R),
        "combined_wilson_lower_must_exceed_break_even": True,
    }


def _build_resilience_hierarchy(
    observations: Sequence[dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    hierarchy: dict[str, dict[str, Any]] = {}
    for level_name, fields in RESILIENCE_LEVELS:
        grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for row in observations:
            grouped[_key(row, fields)].append(row)
        models = {
            signature: {
                **_resilience_classification(rows),
                "fields": list(fields),
                "values": {field: rows[0][field] for field in fields},
            }
            for signature, rows in sorted(grouped.items())
        }
        hierarchy[level_name] = {
            "fields": list(fields),
            "signatures": models,
            "classification_counts": dict(
                Counter(
                    str(item["classification"]) for item in models.values()
                )
            ),
        }
    return hierarchy


def resolve_resilience(
    hierarchy: dict[str, dict[str, Any]],
    row: dict[str, Any],
) -> tuple[str, str | None, str | None]:
    for level_name, fields in RESILIENCE_LEVELS:
        signature = _key(row, fields)
        level = hierarchy[level_name]
        item = cast(dict[str, Any], level["signatures"]).get(signature)
        if item is not None and item["classification"] != UNRESOLVED:
            return str(item["classification"]), level_name, signature
    return UNRESOLVED, None, None


def _load_r21_ledger(root: Path) -> list[dict[str, Any]]:
    matches = list(root.rglob("r21-cautious-mixed-subtype-ledger.json"))
    if len(matches) != 1:
        raise ValueError("R23 requires one frozen R21 ledger")
    return cast(list[dict[str, Any]], json.loads(matches[0].read_text()))


def run(
    source_root: Path,
    target_root: Path,
    dossier_root: Path,
    r21_root: Path,
    output: Path,
) -> dict[str, Any]:
    evidence, provenance = journey.load_raw_m5(source_root)
    if evidence.symbol != r3.SYMBOL or int(provenance["retained_bars"]) != 707716:
        raise ValueError("unexpected XAUUSD corpus")

    r21_ledger = _load_r21_ledger(r21_root)
    subtype_hierarchy = _build_hierarchy(r21_ledger)

    memory_store, dossier_manifest = cibo_memory.build_memory_store(dossier_root)
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

    observations: list[dict[str, Any]] = []
    counts: Counter[str] = Counter()

    for setup in setups:
        signal = setup.context.signal
        episode_id = source_index.get(
            (
                signal.cisd_at,
                signal.side.value,
                setup.context.timeframe,
                signal.target,
            )
        )
        if episode_id is None:
            counts["UNMATCHED_CAUSAL_EPISODE"] += 1
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

        subtype_row = {
            "memory_state": memory.state,
            "source_timeframe": setup.context.timeframe,
            "fvg_before_entry": setup.context.fvg_before_entry,
            "cisd_progress_bucket": setup.context.cisd_progress_bucket,
            "protected_risk_range_bucket": (
                setup.context.protected_risk_range_bucket
            ),
            "source_range_state_bucket": setup.context.source_range_state_bucket,
            "brain_posture": posture,
        }

        if memory.state == "SUPPORTIVE":
            subtype_class = "SUPPORTIVE"
            subtype_level = None
        else:
            subtype_class, subtype_level, _sig = resolve_subtype(
                subtype_hierarchy,
                subtype_row,
            )
            if subtype_class != r21.RECOVERABLE:
                counts[f"SKIP_SUBTYPE_{subtype_class}"] += 1
                continue

        if (
            setup.context.protected_risk_range_bucket
            in r18.LOW_CAPACITY_RISK_BUCKETS
        ):
            counts["SKIP_LOW_CAPACITY_PROTECTED_SWING"] += 1
            continue

        fill = r3._entry(setup, evidence, opens, "NEXT_SOURCE_OPEN")
        if fill is None:
            counts["SKIP_NO_IMMEDIATE_FILL"] += 1
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
            counts["SKIP_NO_ACTIVE_DOL"] += 1
            continue

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
            counts["SKIP_KNOWN_INVALID"] += 1
            continue
        if assessment.state is r11.SituationState.CONFLICTED:
            counts["SKIP_CONFLICTED"] += 1
            continue

        max_rank = min(2, len(ladder))
        for rank in range(1, max_rank + 1):
            target = ladder[rank - 1]
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
                counts["SKIP_INVALID_EXECUTION_GEOMETRY"] += 1
                continue

            planned_rr = _planned_rr(setup=setup, entry=entry, target=target)
            if planned_rr <= 0:
                continue
            observation = {
                "entry_at": entry_at.isoformat(),
                "year": entry_at.year,
                "period": _period(entry_at.year),
                "memory_state": memory.state,
                "subtype_classification": subtype_class,
                "subtype_level": subtype_level,
                "source_timeframe": setup.context.timeframe,
                "target_rank": rank,
                "target_route": r15._candidate_route(target),
                "planned_rr": str(planned_rr),
                "planned_rr_bucket": r2._bucket(planned_rr, RR_CUTS),
                "selected_dol_reached": trade.exit_reason in TARGET_REASONS,
            }
            observations.append(observation)

    resilience_hierarchy = _build_resilience_hierarchy(observations)

    resolved_subtypes: Counter[str] = Counter()
    for row in r21_ledger:
        cls, level, _sig = resolve_subtype(subtype_hierarchy, row)
        resolved_subtypes[f"{level or 'none'}:{cls}"] += 1

    resolved_resilience: Counter[str] = Counter()
    for row in observations:
        cls, level, _sig = resolve_resilience(resilience_hierarchy, row)
        resolved_resilience[f"{level or 'none'}:{cls}"] += 1

    payload = {
        "schema": "qore.turtle_soup_xauusd_r23.hierarchical_friction_memory.v1",
        "identity": IDENTITY,
        "evidence_status": (
            "CONSUMED_10Y_HIERARCHICAL_STRUCTURAL_AND_FRICTION_MEMORY"
        ),
        "subtype_hierarchy_contract": {
            "levels": [
                {"name": name, "fields": list(fields)}
                for name, fields in SUBTYPE_LEVELS
            ],
            "most_specific_stable_ancestor_wins": True,
            "minimum_per_period": SUBTYPE_MIN_PER_PERIOD,
            "strict_majority_each_period": True,
            "same_label_all_periods": True,
            "pnl_used": False,
        },
        "friction_resilience_contract": {
            "stress_friction_r": str(STRESS_FRICTION_R),
            "target_ranks_studied": [1, 2],
            "planned_rr_buckets": [str(cut) for cut in RR_CUTS],
            "selected_dol_reached_is_structural_label": True,
            "break_even_formula": "(1+friction)/(planned_rr+1)",
            "minimum_per_period": RESILIENCE_MIN_PER_PERIOD,
            "hit_rate_must_exceed_break_even_each_period": True,
            "combined_wilson_lower_95_must_exceed_break_even": True,
            "realized_pnl_used": False,
            "profit_factor_used": False,
            "drawdown_used": False,
            "automatic_threshold_search": False,
        },
        "reproduction": {
            "retained_bars": int(provenance["retained_bars"]),
            "setups": len(setups),
            "r21_ledger_rows": len(r21_ledger),
            "resilience_observations": len(observations),
            "counts": dict(counts),
            "ambiguous_bindings_fail_closed": repair._LAST_AMBIGUOUS_KEYS,
        },
        "subtype_hierarchy": subtype_hierarchy,
        "subtype_resolution_counts": dict(resolved_subtypes),
        "resilience_hierarchy": resilience_hierarchy,
        "resilience_resolution_counts": dict(resolved_resilience),
        "dossier_manifest": dossier_manifest,
        "governance": {
            "research_memory_only": True,
            "fresh_holdout_consumed": False,
            "rule_promoted": False,
            "demo_eligible": False,
            "live_authorized": False,
            "real_capital_authorized": False,
            "production_authorized": False,
        },
        "funnel": funnel,
    }

    output.mkdir(parents=True, exist_ok=True)
    (output / "r23-hierarchical-friction-report.json").write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n"
    )
    (output / "r23-subtype-hierarchy.json").write_text(
        json.dumps(subtype_hierarchy, indent=2, sort_keys=True) + "\n"
    )
    (output / "r23-friction-resilience-memory.json").write_text(
        json.dumps(resilience_hierarchy, indent=2, sort_keys=True) + "\n"
    )
    (output / "r23-friction-observations.json").write_text(
        json.dumps(observations, indent=2, sort_keys=True) + "\n"
    )
    return payload


def main() -> None:
    if len(sys.argv) != 6:
        raise SystemExit(
            "usage: module SOURCE_ROOT TARGET_ROOT DOSSIER_ROOT R21_ROOT OUTPUT_DIR"
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
