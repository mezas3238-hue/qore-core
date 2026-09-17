"""Post-entry journey divergence forensics for R9 BREAK A/B.

Diagnostic only. This module never feeds post-entry information into an
operating rule. It asks where a pre-registered BREAK A/B journey actually
fails after entry: before the nearest active DOL, after one or more nearer
DOLs, or only at the selected destination. The result is used to decide
whether the unresolved defect is upstream setup validity or target hierarchy.
"""
from __future__ import annotations

import bisect
import json
import sys
from collections import Counter, defaultdict
from collections.abc import Mapping, Sequence
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

from qore.infrastructure.trader_lab import turtle_soup_xauusd_r3_causal_regime_forensics as causal
from qore.infrastructure.trader_lab import turtle_soup_xauusd_r3_cibo_journey as r3
from qore.infrastructure.trader_lab import turtle_soup_xauusd_r3_cibo_journey_binding_repair as repair
from qore.infrastructure.trader_lab import turtle_soup_xauusd_r5_regime_journey_validity_forensics as r5
from qore.infrastructure.trader_lab import turtle_soup_xauusd_r7_structural_abstention_lab as r7
from qore.infrastructure.trader_lab import turtle_soup_xauusd_r8_structural_break_counterfactual as r8
from qore.infrastructure.trader_lab import turtle_soup_xauusd_r9_causal_break_discriminator as r9
from qore.infrastructure.trader_lab.ict_turtle_soup_r4_source_exact import Side

IDENTITY = "TURTLE_SOUP_XAUUSD_R9_JOURNEY_DIVERGENCE_FORENSICS_V1"
EVIDENCE_STATUS = "CONSUMED_CIBO_10Y_POST_ENTRY_JOURNEY_DIAGNOSTIC_NOT_OPERATING_INPUT"

STOP_REASONS = frozenset({"STOP", "STOP_FIRST", "GAP_STOP"})
TARGET_REASONS = frozenset({"TARGET", "GAP_TARGET_CAPPED"})


def _d(value: Any) -> Decimal:
    return Decimal(str(value))


def _active_universe(
    trade: r3.RoutedTrade,
    rows: Sequence[r3.TargetCandidate],
    side: Side,
) -> list[r3.TargetCandidate]:
    active: dict[tuple[str, str, Decimal, datetime], r3.TargetCandidate] = {}
    for route in r3.TARGET_ROUTES:
        for candidate in r3._active_targets(
            rows,
            at=trade.entry_at,
            side=side,
            anchor=trade.entry,
            route=route,
        ):
            active[(candidate.kind, candidate.timeframe, candidate.level, candidate.known_at)] = candidate
    result = list(active.values())
    result.sort(key=lambda item: (abs(item.level - trade.entry), item.known_at, item.level))
    return result


def _candidate_touched(candidate: r3.TargetCandidate, side: Side, bar: Any) -> bool:
    if side is Side.LONG:
        return bar.open >= candidate.level or bar.high >= candidate.level
    return bar.open <= candidate.level or bar.low <= candidate.level


def _stop_touched(trade: r3.RoutedTrade, side: Side, bar: Any) -> bool:
    if side is Side.LONG:
        return bar.open <= trade.stop or bar.low <= trade.stop
    return bar.open >= trade.stop or bar.high >= trade.stop


def _favorable_extreme(entry: Decimal, side: Side, bars: Sequence[Any]) -> Decimal:
    if not bars:
        return entry
    if side is Side.LONG:
        return max(entry, *(bar.high for bar in bars))
    return min(entry, *(bar.low for bar in bars))


def _journey_stage(
    selected_reached: bool,
    touched_ranks: Sequence[int],
    exit_reason: str,
) -> str:
    if selected_reached:
        return "SELECTED_DOL_REACHED"
    if exit_reason in STOP_REASONS:
        if touched_ranks:
            return "NEARER_DOL_REACHED_THEN_INVALIDATED"
        return "INVALIDATED_BEFORE_ANY_ACTIVE_DOL"
    if touched_ranks:
        return "NEARER_DOL_REACHED_WITHOUT_SELECTED_DOL"
    return "NO_ACTIVE_DOL_REACHED_BEFORE_LIFECYCLE_EXIT"


def _path_diagnostic(
    trade: r3.RoutedTrade,
    target_rows: Sequence[r3.TargetCandidate],
    evidence: Any,
    opens: Sequence[datetime],
) -> dict[str, Any]:
    side = Side(trade.side)
    active = _active_universe(trade, target_rows, side)
    selected_index = next(
        (
            index
            for index, item in enumerate(active)
            if item.level == trade.target
            and item.kind == trade.target_kind
            and item.timeframe == trade.target_timeframe
        ),
        None,
    )
    if selected_index is None:
        raise ValueError("selected DOL absent from active universe")
    selected_rank = selected_index + 1
    left = bisect.bisect_left(opens, trade.entry_at)
    right = bisect.bisect_left(opens, trade.exit_at)
    # Include the exit bar so target touches can be observed, but preserve the
    # system STOP_FIRST convention by checking invalidation before any DOL on
    # a stop bar.
    if right < len(evidence.bars):
        right += 1
    path = list(evidence.bars[left:right])
    touched: set[int] = set()
    clean_bars: list[Any] = []
    selected_reached = False
    first_touch_at: datetime | None = None
    for bar in path:
        if _stop_touched(trade, side, bar) and trade.exit_reason in STOP_REASONS and bar.closed_at >= trade.exit_at:
            break
        clean_bars.append(bar)
        for rank, candidate in enumerate(active, start=1):
            if rank in touched:
                continue
            if _candidate_touched(candidate, side, bar):
                touched.add(rank)
                if first_touch_at is None:
                    first_touch_at = bar.closed_at
        if selected_rank in touched:
            selected_reached = True
            if trade.exit_reason in TARGET_REASONS:
                break

    favorable = _favorable_extreme(trade.entry, side, clean_bars)
    mfe_abs = favorable - trade.entry if side is Side.LONG else trade.entry - favorable
    risk = abs(trade.entry - trade.stop)
    reward = abs(trade.target - trade.entry)
    nearest = active[0]
    nearest_distance = abs(nearest.level - trade.entry)
    touched_ranks = sorted(touched)
    return {
        "active_dol_count": len(active),
        "selected_dol_rank": selected_rank,
        "selected_dol_reached": selected_reached,
        "nearest_dol_kind": nearest.kind,
        "nearest_dol_timeframe": nearest.timeframe,
        "nearest_dol_distance_abs": nearest_distance,
        "nearest_dol_distance_r": nearest_distance / risk if risk > 0 else None,
        "touched_dol_count": len(touched_ranks),
        "touched_dol_ranks": touched_ranks,
        "max_dol_rank_touched": max(touched_ranks) if touched_ranks else 0,
        "first_dol_touch_at": first_touch_at,
        "mfe_abs_before_exit": mfe_abs,
        "mfe_r_before_exit": mfe_abs / risk if risk > 0 else None,
        "mfe_selected_target_fraction": mfe_abs / reward if reward > 0 else None,
        "journey_failure_stage": _journey_stage(selected_reached, touched_ranks, trade.exit_reason),
    }


def _stat(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    values = [_d(row["primary_net_r"]) for row in rows]
    gp = sum((value for value in values if value > 0), Decimal(0))
    gl = -sum((value for value in values if value < 0), Decimal(0))
    total = sum(values, Decimal(0))
    return {
        "trades": len(rows),
        "total_primary_r": str(total),
        "mean_primary_r": str(total / len(rows)) if rows else None,
        "profit_factor": str(gp / gl) if gl > 0 else None,
    }


def _median(rows: Sequence[Mapping[str, Any]], key: str) -> str | None:
    values = sorted(_d(row[key]) for row in rows if row.get(key) is not None)
    if not values:
        return None
    middle = len(values) // 2
    if len(values) % 2:
        return str(values[middle])
    return str((values[middle - 1] + values[middle]) / Decimal(2))


def _stage_report(rows: Sequence[dict[str, Any]]) -> dict[str, Any]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[str(row["journey_failure_stage"])].append(row)
    return {
        stage: {
            **_stat(items),
            "share": str(Decimal(len(items)) / len(rows)) if rows else None,
            "median_mfe_r": _median(items, "mfe_r_before_exit"),
            "median_mfe_target_fraction": _median(items, "mfe_selected_target_fraction"),
            "median_selected_dol_rank": _median(items, "selected_dol_rank"),
        }
        for stage, items in sorted(grouped.items())
    }


def _period(rows: Sequence[dict[str, Any]], years: frozenset[int]) -> list[dict[str, Any]]:
    return [row for row in rows if int(row["year"]) in years]


def _family_report(rows: Sequence[dict[str, Any]]) -> dict[str, Any]:
    return {
        "full": _stage_report(rows),
        "historical_2016_2023": _stage_report(_period(rows, r9.HISTORICAL_YEARS)),
        "recent_2024_2026": _stage_report(_period(rows, r9.RECENT_YEARS)),
        "by_year": {
            str(year): _stage_report([row for row in rows if int(row["year"]) == year])
            for year in range(2016, 2027)
        },
        "overall_path_medians": {
            "historical_mfe_r": _median(_period(rows, r9.HISTORICAL_YEARS), "mfe_r_before_exit"),
            "recent_mfe_r": _median(_period(rows, r9.RECENT_YEARS), "mfe_r_before_exit"),
            "historical_mfe_target_fraction": _median(_period(rows, r9.HISTORICAL_YEARS), "mfe_selected_target_fraction"),
            "recent_mfe_target_fraction": _median(_period(rows, r9.RECENT_YEARS), "mfe_selected_target_fraction"),
        },
    }


def _jsonable(value: Any) -> Any:
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, dict):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(item) for item in value]
    return value


def run(source_root: Path, target_root: Path, output: Path) -> dict[str, Any]:
    evidence, selected, reproduction = causal._reproduce_selected(source_root, target_root)
    episodes, _source_index = repair._load_targets_fail_closed(target_root)
    opens = tuple(bar.opened_at for bar in evidence.bars)
    d1 = r5._aggregate(evidence.bars, "D1")
    h4 = r5._aggregate(evidence.bars, "H4")
    family_rows: dict[str, list[dict[str, Any]]] = {name: [] for name in r8.BREAK_FAMILIES}
    retained = 0
    for setup, trade in selected:
        row = causal._record(setup, trade, evidence.bars, opens)
        row.update(r5._regime_features(row, d1, h4))
        if r7._is_abstain(row):
            continue
        retained += 1
        family = next(
            (name for name, signature in r8.BREAK_FAMILIES.items() if r8._matches(row, signature)),
            None,
        )
        if family is None:
            continue
        target_rows = episodes.get(trade.episode_id)
        if not target_rows:
            raise ValueError("selected episode missing in journey divergence forensics")
        row.update(_path_diagnostic(trade, target_rows, evidence, opens))
        row["family"] = family
        row["year"] = datetime.fromisoformat(str(row["entry_at"])).year
        family_rows[family].append(row)

    if retained != 5612:
        raise ValueError(f"R7 retained drift: {retained}")
    expected = {
        "BREAK_A_DEEP_RAID_MID_LATE_CISD": 151,
        "BREAK_B_MODERATE_RAID_MID_CISD_NORMAL_H4": 88,
    }
    for name, count in expected.items():
        if len(family_rows[name]) != count:
            raise ValueError(f"family drift {name}: {len(family_rows[name])} != {count}")

    payload = {
        "schema": "qore.turtle_soup_xauusd_r9.journey_divergence_forensics.v1",
        "identity": IDENTITY,
        "evidence_status": EVIDENCE_STATUS,
        "reproduction": {
            **reproduction,
            "r7_retained": retained,
            "break_a_trades": len(family_rows["BREAK_A_DEEP_RAID_MID_LATE_CISD"]),
            "break_b_trades": len(family_rows["BREAK_B_MODERATE_RAID_MID_CISD_NORMAL_H4"]),
        },
        "question": "DO_RECENT_BREAK_A_B_JOURNEYS_FAIL_BEFORE_ANY_ACTIVE_DOL_OR_AFTER_REACHING_NEARER_INTERMEDIATE_DOL",
        "families": {name: _family_report(rows) for name, rows in family_rows.items()},
        "interpretation_contract": {
            "post_entry_path_is_diagnostic_only": True,
            "post_entry_path_allowed_as_operating_input": False,
            "same_bar_ambiguity": "STOP_FIRST_NO_DOL_TOUCH_CREDIT_ON_STOP_BAR",
            "automatic_threshold_search": False,
            "candidate_rule_promoted": False,
        },
        "governance": {
            "diagnostic_only": True,
            "fresh_holdout_consumed": False,
            "year_or_date_allowed_as_operating_rule": False,
            "demo_eligible": False,
            "live_authorized": False,
            "real_capital_authorized": False,
            "production_authorized": False,
        },
    }
    output.mkdir(parents=True, exist_ok=True)
    (output / "journey-divergence-report.json").write_text(
        json.dumps(_jsonable(payload), indent=2, sort_keys=True) + "\n"
    )
    for family, name in (
        ("BREAK_A_DEEP_RAID_MID_LATE_CISD", "break-a-journeys.json"),
        ("BREAK_B_MODERATE_RAID_MID_CISD_NORMAL_H4", "break-b-journeys.json"),
    ):
        (output / name).write_text(
            json.dumps(_jsonable(family_rows[family]), indent=2, sort_keys=True) + "\n"
        )
    return _jsonable(payload)


def main() -> None:
    if len(sys.argv) != 4:
        raise SystemExit("usage: module SOURCE_ROOT TARGET_ROOT OUTPUT_DIR")
    print(json.dumps(run(Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])), sort_keys=True))


if __name__ == "__main__":
    main()
