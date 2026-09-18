"""R16 structural decision forensics for the CIBO-first XAUUSD brain.

Consumed-evidence research only. This module does NOT fit a PnL model and does
not promote a trading rule. It counterfactually evaluates every causally
available R3 action to answer two structural questions:

1. Entry timing: when does NEXT_SOURCE_OPEN preserve journey capacity versus
   CISD_THRESHOLD_RETEST, and when does waiting destroy it?
2. DOL semantics: which target families/ranks are reached as part of the
   journey, especially SWING_H4 versus nearer destinations?

The outcome label is structural capacity (touching at least one active CIBO DOL
before invalidation/lifecycle end), not return. PnL is intentionally omitted.
"""
from __future__ import annotations

import json
import sys
from collections import Counter, defaultdict
from collections.abc import Mapping, Sequence
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
    turtle_soup_xauusd_r9_journey_divergence_forensics as divergence,
)
from qore.infrastructure.trader_lab import (
    turtle_soup_xauusd_r15_cibo_first_market_brain as r15,
)

IDENTITY = "TURTLE_SOUP_XAUUSD_R16_STRUCTURAL_DECISION_FORENSICS_V1"
PERIODS = {
    "early_2016_2020": frozenset(range(2016, 2021)),
    "transition_2021_2023": frozenset(range(2021, 2024)),
    "recent_2024_2026": frozenset(range(2024, 2027)),
}


def _d(value: Any) -> Decimal:
    return Decimal(str(value))


def _median(values: Sequence[Decimal]) -> str | None:
    return None if not values else str(median(values))


def _period(year: int) -> str:
    for name, years in PERIODS.items():
        if year in years:
            return name
    return "outside"


def _capacity(path: Mapping[str, Any]) -> bool:
    return int(path["touched_dol_count"]) > 0


def _structural_profile(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    filled = [row for row in rows if bool(row["filled"])]
    capable = [row for row in filled if bool(row["dol_capable"])]
    selected = [row for row in filled if bool(row["selected_dol_reached"])]
    invalid = [
        row
        for row in filled
        if row["journey_failure_stage"] == "INVALIDATED_BEFORE_ANY_ACTIVE_DOL"
    ]
    return {
        "attempts": len(rows),
        "fills": len(filled),
        "fill_rate": (
            None if not rows else str(Decimal(len(filled)) / Decimal(len(rows)))
        ),
        "dol_capable": len(capable),
        "dol_capable_rate": (
            None
            if not filled
            else str(Decimal(len(capable)) / Decimal(len(filled)))
        ),
        "selected_dol_reached": len(selected),
        "selected_dol_reached_rate": (
            None
            if not filled
            else str(Decimal(len(selected)) / Decimal(len(filled)))
        ),
        "invalidated_before_any_dol": len(invalid),
        "invalidated_before_any_dol_rate": (
            None
            if not filled
            else str(Decimal(len(invalid)) / Decimal(len(filled)))
        ),
        "median_fill_latency_minutes": _median(
            [_d(row["fill_latency_minutes"]) for row in filled]
        ),
        "median_selected_dol_rank": _median(
            [_d(row["selected_dol_rank"]) for row in filled]
        ),
        "median_nearest_dol_r": _median(
            [
                _d(row["nearest_dol_distance_r"])
                for row in filled
                if row.get("nearest_dol_distance_r") is not None
            ]
        ),
        "median_selected_rr": _median(
            [_d(row["selected_rr"]) for row in filled]
        ),
        "stage_counts": dict(
            Counter(str(row["journey_failure_stage"]) for row in filled)
        ),
    }


def _group_profiles(
    rows: Sequence[dict[str, Any]],
    key: str,
) -> dict[str, Any]:
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        groups[str(row[key])].append(row)
    return {
        name: {
            "all": _structural_profile(items),
            **{
                period: _structural_profile(
                    [item for item in items if item["period"] == period]
                )
                for period in PERIODS
            },
        }
        for name, items in sorted(groups.items())
    }


def _paired_entry_report(rows: Sequence[dict[str, Any]]) -> dict[str, Any]:
    by_key: dict[
        tuple[str, str],
        dict[str, dict[str, Any]],
    ] = defaultdict(dict)
    for row in rows:
        key = (str(row["setup_id"]), str(row["target_route"]))
        by_key[key][str(row["entry_mode"])] = row

    pairs: list[dict[str, Any]] = []
    for modes in by_key.values():
        immediate = modes.get("NEXT_SOURCE_OPEN")
        retest = modes.get("CISD_THRESHOLD_RETEST")
        if immediate is None or retest is None:
            continue
        if not immediate["filled"] or not retest["filled"]:
            continue
        immediate_capable = bool(immediate["dol_capable"])
        retest_capable = bool(retest["dol_capable"])
        if immediate_capable and not retest_capable:
            contrast = "IMMEDIATE_PRESERVES_RETEST_LOSES_CAPACITY"
        elif retest_capable and not immediate_capable:
            contrast = "RETEST_RECOVERS_CAPACITY"
        elif immediate_capable and retest_capable:
            contrast = "BOTH_CAPABLE"
        else:
            contrast = "NEITHER_CAPABLE"
        pairs.append(
            {
                "period": immediate["period"],
                "brain_posture": immediate["brain_posture"],
                "target_route": immediate["target_route"],
                "contrast": contrast,
                "immediate_fill_latency_minutes": immediate["fill_latency_minutes"],
                "retest_fill_latency_minutes": retest["fill_latency_minutes"],
                "immediate_nearest_dol_r": immediate["nearest_dol_distance_r"],
                "retest_nearest_dol_r": retest["nearest_dol_distance_r"],
                "immediate_selected_rr": immediate["selected_rr"],
                "retest_selected_rr": retest["selected_rr"],
            }
        )

    counts = Counter(str(row["contrast"]) for row in pairs)
    return {
        "filled_same_setup_route_pairs": len(pairs),
        "contrast_counts": dict(counts),
        "by_period": {
            period: dict(
                Counter(
                    row["contrast"]
                    for row in pairs
                    if row["period"] == period
                )
            )
            for period in PERIODS
        },
        "by_brain_posture": {
            posture: dict(
                Counter(
                    row["contrast"]
                    for row in pairs
                    if row["brain_posture"] == posture
                )
            )
            for posture in sorted({str(row["brain_posture"]) for row in pairs})
        },
        "pairs": pairs,
    }


def _same_setup_target_family_report(
    rows: Sequence[dict[str, Any]],
) -> dict[str, Any]:
    by_key: dict[
        tuple[str, str],
        dict[str, dict[str, Any]],
    ] = defaultdict(dict)
    for row in rows:
        if not row["filled"]:
            continue
        key = (str(row["setup_id"]), str(row["entry_mode"]))
        by_key[key][str(row["target_route"])] = row

    comparisons: list[dict[str, Any]] = []
    for routes in by_key.values():
        h4 = routes.get("SWING_H4")
        if h4 is None:
            continue
        other_rows = [
            row
            for name, row in routes.items()
            if name != "SWING_H4"
        ]
        if not other_rows:
            continue
        nearest_other = min(
            other_rows,
            key=lambda row: _d(row["selected_dol_rank"]),
        )
        comparisons.append(
            {
                "period": h4["period"],
                "brain_posture": h4["brain_posture"],
                "entry_mode": h4["entry_mode"],
                "swing_h4_capable": h4["dol_capable"],
                "swing_h4_selected_reached": h4["selected_dol_reached"],
                "swing_h4_rank": h4["selected_dol_rank"],
                "swing_h4_rr": h4["selected_rr"],
                "other_route": nearest_other["target_route"],
                "other_capable": nearest_other["dol_capable"],
                "other_selected_reached": nearest_other["selected_dol_reached"],
                "other_rank": nearest_other["selected_dol_rank"],
                "other_rr": nearest_other["selected_rr"],
            }
        )

    return {
        "same_setup_entry_comparisons": len(comparisons),
        "swing_h4_selected_reached": sum(
            bool(row["swing_h4_selected_reached"]) for row in comparisons
        ),
        "other_selected_reached": sum(
            bool(row["other_selected_reached"]) for row in comparisons
        ),
        "swing_h4_capable": sum(
            bool(row["swing_h4_capable"]) for row in comparisons
        ),
        "other_capable": sum(
            bool(row["other_capable"]) for row in comparisons
        ),
        "by_period": {
            period: {
                "n": len(part := [
                    row for row in comparisons if row["period"] == period
                ]),
                "swing_h4_selected_reached_rate": (
                    None
                    if not part
                    else str(
                        Decimal(
                            sum(bool(row["swing_h4_selected_reached"]) for row in part)
                        )
                        / Decimal(len(part))
                    )
                ),
                "other_selected_reached_rate": (
                    None
                    if not part
                    else str(
                        Decimal(
                            sum(bool(row["other_selected_reached"]) for row in part)
                        )
                        / Decimal(len(part))
                    )
                ),
            }
            for period in PERIODS
        },
        "comparisons": comparisons,
    }


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

        target_rows = episodes[episode_id]
        regime = r5._regime_features(
            {"entry_at": signal.entry_at.isoformat(), "side": signal.side.value},
            d1,
            h4,
        )
        posture = r15._market_posture(regime)
        year = signal.entry_at.year
        setup_id = (
            f"{setup.context.timeframe}:{signal.side.value}:"
            f"{signal.c1_opened_at.isoformat()}:{signal.c2_opened_at.isoformat()}"
        )

        for action in r3.ACTIONS:
            entry_mode, target_route = action
            _value, trade, reason = r3._simulate(
                setup,
                target_rows,
                evidence,
                opens,
                action,
            )
            if trade is None:
                rows.append(
                    {
                        "setup_id": setup_id,
                        "year": year,
                        "period": _period(year),
                        "brain_posture": posture,
                        "entry_mode": entry_mode,
                        "target_route": target_route,
                        "filled": False,
                        "reason": reason,
                        "d1_trend_state_20": regime["d1_trend_state_20"],
                        "h4_trend_state_20": regime["h4_trend_state_20"],
                        "d1_range_5v20": regime["d1_range_5v20"],
                        "h4_range_3v20": regime["h4_range_3v20"],
                        "d1_efficiency_20": regime["d1_efficiency_20"],
                        "h4_efficiency_20": regime["h4_efficiency_20"],
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
                    }
                )
                continue

            path = divergence._path_diagnostic(
                trade,
                target_rows,
                evidence,
                opens,
            )
            risk = abs(trade.entry - trade.stop)
            reward = abs(trade.target - trade.entry)
            rows.append(
                {
                    "setup_id": setup_id,
                    "year": year,
                    "period": _period(year),
                    "brain_posture": posture,
                    "entry_mode": entry_mode,
                    "target_route": target_route,
                    "filled": True,
                    "reason": reason,
                    "fill_latency_minutes": str(
                        Decimal(
                            str(
                                (
                                    trade.entry_at - signal.entry_at
                                ).total_seconds()
                                / 60
                            )
                        )
                    ),
                    "dol_capable": _capacity(path),
                    "selected_dol_reached": bool(path["selected_dol_reached"]),
                    "journey_failure_stage": str(path["journey_failure_stage"]),
                    "selected_dol_rank": int(path["selected_dol_rank"]),
                    "active_dol_count": int(path["active_dol_count"]),
                    "nearest_dol_distance_r": (
                        None
                        if path["nearest_dol_distance_r"] is None
                        else str(path["nearest_dol_distance_r"])
                    ),
                    "selected_rr": (
                        None if risk <= 0 else str(reward / risk)
                    ),
                    "d1_trend_state_20": regime["d1_trend_state_20"],
                    "h4_trend_state_20": regime["h4_trend_state_20"],
                    "d1_range_5v20": regime["d1_range_5v20"],
                    "h4_range_3v20": regime["h4_range_3v20"],
                    "d1_efficiency_20": regime["d1_efficiency_20"],
                    "h4_efficiency_20": regime["h4_efficiency_20"],
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
                }
            )

    expected_routed = len(setups) - unmatched
    if expected_routed != 12768:
        raise ValueError(
            f"R16 routed setup drift: {expected_routed} != 12768"
        )

    filled_rows = [row for row in rows if row["filled"]]
    entry_pair = _paired_entry_report(rows)
    target_compare = _same_setup_target_family_report(rows)

    payload = {
        "schema": "qore.turtle_soup_xauusd_r16.structural_decision_forensics.v1",
        "identity": IDENTITY,
        "evidence_status": (
            "CONSUMED_10Y_COUNTERFACTUAL_STRUCTURAL_CAPACITY_NOT_FRESH_HOLDOUT"
        ),
        "reproduction": {
            "retained_bars": int(provenance["retained_bars"]),
            "setups": len(setups),
            "routed_setups": expected_routed,
            "unmatched": unmatched,
            "action_rows": len(rows),
            "filled_action_rows": len(filled_rows),
            "ambiguous_bindings_fail_closed": repair._LAST_AMBIGUOUS_KEYS,
        },
        "entry_mode_profiles": _group_profiles(rows, "entry_mode"),
        "target_route_profiles": _group_profiles(rows, "target_route"),
        "brain_posture_profiles": _group_profiles(rows, "brain_posture"),
        "entry_mode_same_setup_route_contrast": entry_pair,
        "swing_h4_same_setup_entry_contrast": target_compare,
        "context_diagnostics": {
            "weekday": _group_profiles(rows, "weekday"),
            "session": _group_profiles(rows, "session"),
            "cisd_progress_bucket": _group_profiles(
                rows, "cisd_progress_bucket"
            ),
            "source_range_state_bucket": _group_profiles(
                rows, "source_range_state_bucket"
            ),
        },
        "interpretation_contract": {
            "primary_label": "TOUCHED_ANY_ACTIVE_CIBO_DOL_BEFORE_INVALIDATION_OR_LIFECYCLE_EXIT",
            "pnl_used": False,
            "return_maximising_selection": False,
            "automatic_threshold_search": False,
            "post_entry_path_used_as_diagnostic_label_only": True,
            "post_entry_path_allowed_as_operating_input": False,
            "calendar_period_is_diagnostic_partition_only": True,
            "rule_promoted": False,
        },
        "governance": {
            "diagnostic_only": True,
            "fresh_holdout_consumed": False,
            "no_entry_rule_promoted": True,
            "no_target_rule_promoted": True,
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
    (output / "r16-structural-decision-report.json").write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n"
    )
    (output / "r16-action-ledger.json").write_text(
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
