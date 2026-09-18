"""R17 CIBO journey-capacity memory for Turtle Soup XAUUSD.

Consumed-evidence research only.

The purpose is to teach the trader how far a journey actually travels through
the active CIBO liquidity ladder before Protected Swing invalidation or the
24-hour lifecycle boundary. The label is structural liquidity depth, never PnL.

The canonical observation entry is NEXT_SOURCE_OPEN because R16 showed that a
generic CISD retest does not add structural confirmation and frequently loses
capacity. This does not promote NEXT_SOURCE_OPEN as a live rule; R17 is a
memory-construction experiment over consumed evidence.

No automatic threshold search, return maximization, weekday/session blacklist,
or fresh-holdout consumption occurs here.
"""
from __future__ import annotations

import bisect
import json
import sys
from collections import Counter, defaultdict
from collections.abc import Sequence
from datetime import datetime, timedelta
from decimal import Decimal
from pathlib import Path
from statistics import median
from typing import Any

from qore.infrastructure.trader_lab import (
    cibo_market_atlas_journey_extractor_v1 as journey,
)
from qore.infrastructure.trader_lab import turtle_soup_xauusd_r1 as r1
from qore.infrastructure.trader_lab import turtle_soup_xauusd_r3_cibo_journey as r3
from qore.infrastructure.trader_lab import (
    turtle_soup_xauusd_r3_cibo_journey_binding_repair as repair,
)
from qore.infrastructure.trader_lab import (
    turtle_soup_xauusd_r5_regime_journey_validity_forensics as r5,
)
from qore.infrastructure.trader_lab import (
    turtle_soup_xauusd_r15_cibo_first_market_brain as r15,
)
from qore.infrastructure.trader_lab.ict_turtle_soup_r4_source_exact import Side

IDENTITY = "TURTLE_SOUP_XAUUSD_R17_CIBO_JOURNEY_CAPACITY_MEMORY_V1"

PERIODS = {
    "early_2016_2020": frozenset(range(2016, 2021)),
    "transition_2021_2023": frozenset(range(2021, 2024)),
    "recent_2024_2026": frozenset(range(2024, 2027)),
}

PROFILE_FEATURES = (
    "brain_posture",
    "source_timeframe",
    "side",
    "prior_body_alignment",
    "d1_trend_state_20",
    "h4_trend_state_20",
    "d1_range_5v20",
    "h4_range_3v20",
    "d1_efficiency_20",
    "h4_efficiency_20",
    "d1_location_20",
    "h4_location_20",
    "weekday",
    "session",
    "fvg_before_entry",
    "exact_equal_liquidity",
    "raid_depth_range_bucket",
    "reclaim_latency_bucket",
    "cisd_progress_bucket",
    "protected_risk_range_bucket",
    "source_range_state_bucket",
)


def _d(value: Any) -> Decimal:
    return Decimal(str(value))


def _period(year: int) -> str:
    for name, years in PERIODS.items():
        if year in years:
            return name
    return "outside"


def _median(values: Sequence[Decimal]) -> str | None:
    return None if not values else str(median(values))


def _stop_touched(side: Side, stop: Decimal, bar: Any) -> bool:
    if side is Side.LONG:
        return bool(bar.open <= stop or bar.low <= stop)
    return bool(bar.open >= stop or bar.high >= stop)


def _target_touched(side: Side, level: Decimal, bar: Any) -> bool:
    if side is Side.LONG:
        return bool(bar.open >= level or bar.high >= level)
    return bool(bar.open <= level or bar.low <= level)


def _trace_ladder(
    *,
    setup: r3.Setup,
    entry_at: datetime,
    entry: Decimal,
    ladder: Sequence[r3.TargetCandidate],
    evidence: Any,
    opens: Sequence[datetime],
) -> dict[str, Any]:
    side = setup.context.signal.side
    stop = setup.context.signal.protected_swing
    risk = abs(entry - stop)
    if risk <= 0:
        raise ValueError("R17 non-positive Protected Swing risk")

    left = bisect.bisect_left(opens, entry_at)
    right = bisect.bisect_left(
        opens,
        min(entry_at + timedelta(hours=24), r3.EVAL_CLOSE),
    )
    path = evidence.bars[left:right]
    touched: set[int] = set()
    first_touch_at: datetime | None = None
    invalidated = False

    for bar in path:
        # Preserve the system's conservative STOP_FIRST convention: no DOL
        # credit is given on the bar that first invalidates Protected Swing.
        if _stop_touched(side, stop, bar):
            invalidated = True
            break
        for rank, candidate in enumerate(ladder, start=1):
            if rank in touched:
                continue
            if _target_touched(side, candidate.level, bar):
                touched.add(rank)
                if first_touch_at is None:
                    first_touch_at = bar.closed_at

    max_rank = max(touched) if touched else 0
    nearest_r = abs(ladder[0].level - entry) / risk
    distances_r = [abs(item.level - entry) / risk for item in ladder]

    return {
        "active_dol_levels": len(ladder),
        "touched_dol_levels": len(touched),
        "max_dol_rank_touched": max_rank,
        "reached_rank_1": max_rank >= 1,
        "reached_rank_2": max_rank >= 2,
        "reached_rank_3": max_rank >= 3,
        "reached_rank_4": max_rank >= 4,
        "reached_rank_5": max_rank >= 5,
        "invalidated_before_rank_1": invalidated and max_rank == 0,
        "protected_swing_invalidated": invalidated,
        "first_dol_touch_minutes": (
            None
            if first_touch_at is None
            else str(
                Decimal(
                    str((first_touch_at - entry_at).total_seconds() / 60)
                )
            )
        ),
        "nearest_dol_r": str(nearest_r),
        "rank_2_dol_r": (
            None if len(distances_r) < 2 else str(distances_r[1])
        ),
        "rank_3_dol_r": (
            None if len(distances_r) < 3 else str(distances_r[2])
        ),
        "rank_4_dol_r": (
            None if len(distances_r) < 4 else str(distances_r[3])
        ),
        "rank_5_dol_r": (
            None if len(distances_r) < 5 else str(distances_r[4])
        ),
    }


def _profile(rows: Sequence[dict[str, Any]]) -> dict[str, Any]:
    n = len(rows)
    if not rows:
        return {"observations": 0}

    result: dict[str, Any] = {
        "observations": n,
        "median_active_dol_levels": _median(
            [_d(row["active_dol_levels"]) for row in rows]
        ),
        "median_max_dol_rank_touched": _median(
            [_d(row["max_dol_rank_touched"]) for row in rows]
        ),
        "median_nearest_dol_r": _median(
            [_d(row["nearest_dol_r"]) for row in rows]
        ),
        "invalidated_before_rank_1_rate": str(
            Decimal(
                sum(bool(row["invalidated_before_rank_1"]) for row in rows)
            )
            / Decimal(n)
        ),
    }
    for rank in range(1, 6):
        count = sum(bool(row[f"reached_rank_{rank}"]) for row in rows)
        result[f"reached_rank_{rank}"] = count
        result[f"reached_rank_{rank}_rate"] = str(
            Decimal(count) / Decimal(n)
        )
    first_touch = [
        _d(row["first_dol_touch_minutes"])
        for row in rows
        if row.get("first_dol_touch_minutes") is not None
    ]
    result["median_first_dol_touch_minutes"] = _median(first_touch)
    return result


def _feature_profiles(
    rows: Sequence[dict[str, Any]],
    feature: str,
) -> dict[str, Any]:
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        groups[str(row[feature])].append(row)
    return {
        value: {
            "all": _profile(items),
            **{
                period: _profile(
                    [row for row in items if row["period"] == period]
                )
                for period in PERIODS
            },
        }
        for value, items in sorted(groups.items())
    }


def _depth_distribution(rows: Sequence[dict[str, Any]]) -> dict[str, int]:
    return dict(
        sorted(
            Counter(str(row["max_dol_rank_touched"]) for row in rows).items(),
            key=lambda item: int(item[0]),
        )
    )


def run(
    source_root: Path,
    target_root: Path,
    output: Path,
) -> dict[str, Any]:
    evidence, provenance = journey.load_raw_m5(source_root)
    if evidence.symbol != r3.SYMBOL or int(provenance["retained_bars"]) != 707716:
        raise ValueError("unexpected XAUUSD corpus")

    episodes, source_index = repair._load_targets_fail_closed(target_root)

    original_open, original_close = r1.EVAL_OPEN, r1.EVAL_CLOSE
    try:
        r1.EVAL_OPEN, r1.EVAL_CLOSE = r3.EVAL_OPEN, r3.EVAL_CLOSE
        setups, funnel = r3._build_setups(evidence)
    finally:
        r1.EVAL_OPEN, r1.EVAL_CLOSE = original_open, original_close

    opens = tuple(bar.opened_at for bar in evidence.bars)
    d1 = r5._aggregate(evidence.bars, "D1")
    h4 = r5._aggregate(evidence.bars, "H4")

    rows: list[dict[str, Any]] = []
    unmatched = 0
    no_fill = 0
    no_active_dol = 0

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
            unmatched += 1
            continue

        fill = r3._entry(
            setup,
            evidence,
            opens,
            "NEXT_SOURCE_OPEN",
        )
        if fill is None:
            no_fill += 1
            continue
        entry_at, entry = fill

        active = r15._all_active_targets(
            episodes[episode_id],
            at=entry_at,
            side=signal.side,
            anchor=entry,
        )
        ladder = r15._distinct_target_ladder(active, anchor=entry)
        if not ladder:
            no_active_dol += 1
            continue

        regime = r5._regime_features(
            {"entry_at": entry_at.isoformat(), "side": signal.side.value},
            d1,
            h4,
        )
        posture = r15._market_posture(regime)
        traced = _trace_ladder(
            setup=setup,
            entry_at=entry_at,
            entry=entry,
            ladder=ladder,
            evidence=evidence,
            opens=opens,
        )

        row: dict[str, Any] = {
            "entry_at": entry_at.isoformat(),
            "year": entry_at.year,
            "period": _period(entry_at.year),
            "brain_posture": posture,
            "source_timeframe": setup.context.timeframe,
            "side": signal.side.value,
            "prior_body_alignment": setup.context.prior_body_alignment,
            "weekday": setup.context.weekday,
            "session": setup.context.session,
            "fvg_before_entry": setup.context.fvg_before_entry,
            "exact_equal_liquidity": setup.context.exact_equal_liquidity,
            "raid_depth_range_bucket": setup.context.raid_depth_range_bucket,
            "reclaim_latency_bucket": setup.context.reclaim_latency_bucket,
            "cisd_progress_bucket": setup.context.cisd_progress_bucket,
            "protected_risk_range_bucket": (
                setup.context.protected_risk_range_bucket
            ),
            "source_range_state_bucket": (
                setup.context.source_range_state_bucket
            ),
            **regime,
            **traced,
        }
        rows.append(row)

    if len(setups) - unmatched != 12768:
        raise ValueError("R17 routed setup reproduction drift")

    payload = {
        "schema": "qore.turtle_soup_xauusd_r17.cibo_journey_capacity_memory.v1",
        "identity": IDENTITY,
        "evidence_status": (
            "CONSUMED_10Y_STRUCTURAL_LIQUIDITY_DEPTH_MEMORY_NOT_FRESH_HOLDOUT"
        ),
        "reproduction": {
            "retained_bars": int(provenance["retained_bars"]),
            "setups": len(setups),
            "routed_setups": len(setups) - unmatched,
            "unmatched": unmatched,
            "next_source_open_no_fill": no_fill,
            "no_active_dol": no_active_dol,
            "capacity_observations": len(rows),
            "ambiguous_bindings_fail_closed": repair._LAST_AMBIGUOUS_KEYS,
        },
        "full_capacity_profile": _profile(rows),
        "depth_distribution": _depth_distribution(rows),
        "temporal_capacity_profiles": {
            period: _profile(
                [row for row in rows if row["period"] == period]
            )
            for period in PERIODS
        },
        "feature_memory": {
            feature: _feature_profiles(rows, feature)
            for feature in PROFILE_FEATURES
        },
        "knowledge_contract": {
            "primary_label": (
                "MAX_DISTINCT_ACTIVE_CIBO_DOL_RANK_TOUCHED_BEFORE_PROTECTED_SWING_INVALIDATION_OR_24H"
            ),
            "canonical_observation_entry": "NEXT_SOURCE_OPEN",
            "canonical_entry_is_live_rule": False,
            "pnl_used": False,
            "profit_probability_used": False,
            "automatic_threshold_search": False,
            "return_maximising_feature_selection": False,
            "weekday_is_context_not_rule": True,
            "session_is_context_not_rule": True,
            "year_is_temporal_diagnostic_only": True,
            "post_entry_depth_is_training_label_only": True,
            "post_entry_depth_allowed_as_live_input": False,
            "rule_promoted": False,
        },
        "governance": {
            "research_memory_only": True,
            "fresh_holdout_consumed": False,
            "no_target_extension_rule_promoted": True,
            "no_weekday_filter_promoted": True,
            "no_session_filter_promoted": True,
            "demo_eligible": False,
            "live_authorized": False,
            "real_capital_authorized": False,
            "production_authorized": False,
        },
        "funnel": funnel,
    }

    output.mkdir(parents=True, exist_ok=True)
    (output / "r17-capacity-memory-report.json").write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n"
    )
    (output / "r17-capacity-ledger.json").write_text(
        json.dumps(rows, indent=2, sort_keys=True) + "\n"
    )
    return payload


def main() -> None:
    if len(sys.argv) != 4:
        raise SystemExit("usage: module SOURCE_ROOT TARGET_ROOT OUTPUT_DIR")
    print(
        json.dumps(
            run(Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])),
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
