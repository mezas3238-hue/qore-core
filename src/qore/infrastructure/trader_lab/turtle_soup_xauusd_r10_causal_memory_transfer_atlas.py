"""Temporal causal-memory transfer atlas for Turtle Soup XAUUSD R10.

This is a research-only bridge between CIBO's accumulated historical memory and
the Journey Intelligence layer. It asks a narrow question:

Can pre-registered structural clues learned from the earliest consumed period
retain the same association with journey capacity in later consumed periods?

The atlas does NOT search for thresholds. For each pre-registered feature, an
anchor is deterministically frozen from the 2016-2020 medians of two structural
labels (touched any active DOL vs invalidated before any active DOL). That
unchanged anchor is then evaluated in 2021-2023 and 2024-2026. Pre-registered
feature pairs are also evaluated as conjunctions. PnL is not used to calibrate,
select, rank, or promote anything.

Post-entry journey information is used only as the forensic label. All
explanatory features are known by entry.
"""

from __future__ import annotations

import json
import sys
from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Any, cast

from qore.infrastructure.trader_lab import turtle_soup_xauusd_r3_causal_regime_forensics as causal
from qore.infrastructure.trader_lab import turtle_soup_xauusd_r3_cibo_journey_binding_repair as repair
from qore.infrastructure.trader_lab import turtle_soup_xauusd_r5_regime_journey_validity_forensics as r5
from qore.infrastructure.trader_lab import turtle_soup_xauusd_r7_structural_abstention_lab as r7
from qore.infrastructure.trader_lab import turtle_soup_xauusd_r8_structural_break_counterfactual as r8
from qore.infrastructure.trader_lab import turtle_soup_xauusd_r9_causal_break_discriminator as r9
from qore.infrastructure.trader_lab import turtle_soup_xauusd_r9_cisd_sequence_forensics as cisd
from qore.infrastructure.trader_lab import turtle_soup_xauusd_r9_journey_divergence_forensics as divergence
from qore.infrastructure.trader_lab import turtle_soup_xauusd_r9_liquidity_significance_forensics as liquidity
from qore.infrastructure.trader_lab import turtle_soup_xauusd_r10_protected_swing_causality_forensics as ps
from qore.infrastructure.trader_lab.ict_turtle_soup_r4_source_exact import (
    SourceCandle,
    build_daily,
    build_h1,
    build_h4,
)

IDENTITY = "TURTLE_SOUP_XAUUSD_R10_CAUSAL_MEMORY_TRANSFER_ATLAS_V1"
EVIDENCE_STATUS = (
    "CONSUMED_CIBO_10Y_TEMPORAL_CAUSAL_MEMORY_TRANSFER_DIAGNOSTIC_NOT_FRESH_HOLDOUT"
)

CAPABLE = "TOUCHED_ANY_ACTIVE_DOL"
INVALIDATED = "INVALIDATED_BEFORE_ANY_ACTIVE_DOL"


@dataclass(frozen=True)
class FeatureSpec:
    code: str
    feature: str
    channel: str
    rationale: str


@dataclass(frozen=True)
class PairSpec:
    code: str
    left: str
    right: str
    rationale: str


A_FEATURES = (
    FeatureSpec(
        code="A_LIQUIDITY_DIRECTIONAL_WICK",
        feature="c1_directional_wick_fraction",
        channel="liquidity_significance",
        rationale="BREAK A prior forensics repeatedly associated stronger directional C1 wick with DOL-capable journeys.",
    ),
    FeatureSpec(
        code="A_LIQUIDITY_H4_PROXIMITY",
        feature="c1_nearest_prior_h4_boundary_source_fraction",
        channel="liquidity_significance",
        rationale="BREAK A prior forensics indicated DOL-capable C1 liquidity was closer to prior H4 structural boundary.",
    ),
    FeatureSpec(
        code="A_PS_OPPOSING_SERIES",
        feature="opposing_series_length",
        channel="protected_swing_causality",
        rationale="R10 Protected Swing forensics found a stable but moderate BREAK A opposing-series-length clue.",
    ),
    FeatureSpec(
        code="A_CISD_POST_RECLAIM_REVIOLATION",
        feature="post_reclaim_max_reviolation_source_fraction",
        channel="cisd_sequence",
        rationale="Tests whether reclaimed liquidity remains structurally defended through CISD confirmation.",
    ),
)

A_PAIRS = (
    PairSpec(
        code="A_PAIR_LIQUIDITY_WICK_X_PS_SERIES",
        left="A_LIQUIDITY_DIRECTIONAL_WICK",
        right="A_PS_OPPOSING_SERIES",
        rationale="Tests whether meaningful raid liquidity and developed protected-swing sequence reinforce each other.",
    ),
    PairSpec(
        code="A_PAIR_H4_PROXIMITY_X_PS_SERIES",
        left="A_LIQUIDITY_H4_PROXIMITY",
        right="A_PS_OPPOSING_SERIES",
        rationale="Tests structural-liquidity location together with protected-swing causality.",
    ),
    PairSpec(
        code="A_PAIR_PS_SERIES_X_CISD_DEFENSE",
        left="A_PS_OPPOSING_SERIES",
        right="A_CISD_POST_RECLAIM_REVIOLATION",
        rationale="Tests whether developed reversal sequence plus defended reclaim is more informative than either clue alone.",
    ),
    PairSpec(
        code="A_PAIR_LIQUIDITY_WICK_X_CISD_DEFENSE",
        left="A_LIQUIDITY_DIRECTIONAL_WICK",
        right="A_CISD_POST_RECLAIM_REVIOLATION",
        rationale="Tests meaningful C1 liquidity together with post-reclaim structural defense.",
    ),
)

B_FEATURES = (
    FeatureSpec(
        code="B_RAID_DEPTH_RELATIVE_C1",
        feature="raid_depth_c1_range_fraction",
        channel="liquidity_raid_anatomy",
        rationale="BREAK B prior evidence showed its more stable separation in raid magnitude relative to C1 rather than BREAK A's liquidity signature.",
    ),
    FeatureSpec(
        code="B_PS_CANDLE_RANGE",
        feature="ps_candle_range_source_fraction",
        channel="protected_swing_causality",
        rationale="R10 Protected Swing forensics retained a weak BREAK B range clue worth interaction testing, not standalone promotion.",
    ),
    FeatureSpec(
        code="B_CISD_CONFIRM_RANGE",
        feature="confirm_bar_range_vs_prior6_m5",
        channel="cisd_sequence",
        rationale="Tests whether CISD confirmation is an actual local expansion rather than a technical threshold crossing.",
    ),
    FeatureSpec(
        code="B_CISD_POST_RECLAIM_REVIOLATION",
        feature="post_reclaim_max_reviolation_source_fraction",
        channel="cisd_sequence",
        rationale="Tests whether the reclaimed raid remains defended through confirmation.",
    ),
)

B_PAIRS = (
    PairSpec(
        code="B_PAIR_RAID_DEPTH_X_PS_RANGE",
        left="B_RAID_DEPTH_RELATIVE_C1",
        right="B_PS_CANDLE_RANGE",
        rationale="Tests BREAK B raid anatomy together with Protected Swing impulse geometry.",
    ),
    PairSpec(
        code="B_PAIR_RAID_DEPTH_X_CISD_EXPANSION",
        left="B_RAID_DEPTH_RELATIVE_C1",
        right="B_CISD_CONFIRM_RANGE",
        rationale="Tests whether the raid is followed by genuine CISD expansion.",
    ),
    PairSpec(
        code="B_PAIR_PS_RANGE_X_CISD_EXPANSION",
        left="B_PS_CANDLE_RANGE",
        right="B_CISD_CONFIRM_RANGE",
        rationale="Tests Protected Swing impulse geometry together with confirmation expansion.",
    ),
    PairSpec(
        code="B_PAIR_RAID_DEPTH_X_CISD_DEFENSE",
        left="B_RAID_DEPTH_RELATIVE_C1",
        right="B_CISD_POST_RECLAIM_REVIOLATION",
        rationale="Tests raid anatomy together with post-reclaim defense.",
    ),
)

FAMILY_SPECS = {
    "BREAK_A_DEEP_RAID_MID_LATE_CISD": (A_FEATURES, A_PAIRS),
    "BREAK_B_MODERATE_RAID_MID_CISD_NORMAL_H4": (B_FEATURES, B_PAIRS),
}


@dataclass(frozen=True)
class FrozenAnchor:
    feature_code: str
    feature: str
    direction: str
    threshold: Decimal
    early_capable_median: Decimal
    early_invalidated_median: Decimal


def _d(value: Any) -> Decimal:
    return Decimal(str(value))


def _median(rows: Sequence[Mapping[str, Any]], feature: str) -> Decimal | None:
    values = sorted(_d(row[feature]) for row in rows if row.get(feature) is not None)
    if not values:
        return None
    middle = len(values) // 2
    if len(values) % 2:
        return values[middle]
    return (values[middle - 1] + values[middle]) / Decimal(2)


def _binary_rows(rows: Sequence[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        row
        for row in rows
        if row.get("outcome_class") in {CAPABLE, INVALIDATED}
    ]


def freeze_early_anchor(
    rows: Sequence[dict[str, Any]],
    spec: FeatureSpec,
) -> FrozenAnchor | None:
    """Freeze one deterministic 2016-20 morphology anchor.

    This is not a threshold search. The threshold is exactly the midpoint
    between the two early-period structural-label medians, and the favorable
    direction is whichever side contains the DOL-capable median.
    """
    early = [
        row
        for row in _binary_rows(rows)
        if int(row["year"]) in r9.EARLY_YEARS
    ]
    capable = [row for row in early if row["outcome_class"] == CAPABLE]
    invalidated = [row for row in early if row["outcome_class"] == INVALIDATED]
    capable_median = _median(capable, spec.feature)
    invalidated_median = _median(invalidated, spec.feature)
    if capable_median is None or invalidated_median is None:
        return None
    if capable_median == invalidated_median:
        return None
    direction = ">=" if capable_median > invalidated_median else "<="
    threshold = (capable_median + invalidated_median) / Decimal(2)
    return FrozenAnchor(
        feature_code=spec.code,
        feature=spec.feature,
        direction=direction,
        threshold=threshold,
        early_capable_median=capable_median,
        early_invalidated_median=invalidated_median,
    )


def _condition(row: Mapping[str, Any], anchor: FrozenAnchor) -> bool | None:
    raw = row.get(anchor.feature)
    if raw is None:
        return None
    value = _d(raw)
    return value >= anchor.threshold if anchor.direction == ">=" else value <= anchor.threshold


def _rate(rows: Sequence[dict[str, Any]]) -> Decimal | None:
    binary = _binary_rows(rows)
    if not binary:
        return None
    capable = sum(1 for row in binary if row["outcome_class"] == CAPABLE)
    return Decimal(capable) / Decimal(len(binary))


def _period_rows(rows: Sequence[dict[str, Any]], period: str) -> list[dict[str, Any]]:
    years = {
        "early_2016_2020": r9.EARLY_YEARS,
        "transition_2021_2023": r9.TRANSITION_YEARS,
        "recent_2024_2026": r9.RECENT_YEARS,
    }[period]
    return [row for row in _binary_rows(rows) if int(row["year"]) in years]


def evaluate_anchor(
    rows: Sequence[dict[str, Any]],
    anchor: FrozenAnchor,
) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for period in ("early_2016_2020", "transition_2021_2023", "recent_2024_2026"):
        period_rows = _period_rows(rows, period)
        valid = [
            (row, state)
            for row in period_rows
            if (state := _condition(row, anchor)) is not None
        ]
        matched = [row for row, state in valid if state]
        unmatched = [row for row, state in valid if not state]
        matched_rate = _rate(matched)
        unmatched_rate = _rate(unmatched)
        result[period] = {
            "eligible_rows": len(valid),
            "condition_true_n": len(matched),
            "condition_false_n": len(unmatched),
            "condition_true_capable_rate": None if matched_rate is None else str(matched_rate),
            "condition_false_capable_rate": None if unmatched_rate is None else str(unmatched_rate),
            "capable_rate_difference": (
                None
                if matched_rate is None or unmatched_rate is None
                else str(matched_rate - unmatched_rate)
            ),
        }
    return result


def evaluate_pair(
    rows: Sequence[dict[str, Any]],
    left: FrozenAnchor,
    right: FrozenAnchor,
) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for period in ("early_2016_2020", "transition_2021_2023", "recent_2024_2026"):
        period_rows = _period_rows(rows, period)
        valid: list[tuple[dict[str, Any], bool]] = []
        for row in period_rows:
            lstate = _condition(row, left)
            rstate = _condition(row, right)
            if lstate is None or rstate is None:
                continue
            valid.append((row, lstate and rstate))
        matched = [row for row, state in valid if state]
        unmatched = [row for row, state in valid if not state]
        matched_rate = _rate(matched)
        unmatched_rate = _rate(unmatched)
        result[period] = {
            "eligible_rows": len(valid),
            "conjunction_true_n": len(matched),
            "conjunction_false_n": len(unmatched),
            "conjunction_true_capable_rate": None if matched_rate is None else str(matched_rate),
            "conjunction_false_capable_rate": None if unmatched_rate is None else str(unmatched_rate),
            "capable_rate_difference": (
                None
                if matched_rate is None or unmatched_rate is None
                else str(matched_rate - unmatched_rate)
            ),
        }
    return result


def _family_report(
    rows: Sequence[dict[str, Any]],
    feature_specs: Sequence[FeatureSpec],
    pair_specs: Sequence[PairSpec],
) -> dict[str, Any]:
    anchors = {
        spec.code: anchor
        for spec in feature_specs
        if (anchor := freeze_early_anchor(rows, spec)) is not None
    }
    feature_reports = {
        spec.code: {
            "spec": asdict(spec),
            "anchor": None if spec.code not in anchors else asdict(anchors[spec.code]),
            "transfer": (
                None
                if spec.code not in anchors
                else evaluate_anchor(rows, anchors[spec.code])
            ),
        }
        for spec in feature_specs
    }
    pair_reports: dict[str, Any] = {}
    for spec in pair_specs:
        left = anchors.get(spec.left)
        right = anchors.get(spec.right)
        pair_reports[spec.code] = {
            "spec": asdict(spec),
            "transfer": (
                None
                if left is None or right is None
                else evaluate_pair(rows, left, right)
            ),
        }
    return {
        "binary_label_counts": {
            CAPABLE: sum(1 for row in rows if row.get("outcome_class") == CAPABLE),
            INVALIDATED: sum(1 for row in rows if row.get("outcome_class") == INVALIDATED),
            "excluded_other_diagnostic": sum(
                1
                for row in rows
                if row.get("outcome_class") not in {CAPABLE, INVALIDATED}
            ),
        },
        "feature_transfers": feature_reports,
        "pre_registered_pair_transfers": pair_reports,
    }


def _jsonable(value: Any) -> Any:
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, dict):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [_jsonable(item) for item in value]
    return value


def run(source_root: Path, target_root: Path, output: Path) -> dict[str, Any]:
    evidence, selected, reproduction = causal._reproduce_selected(source_root, target_root)
    episodes, _ = repair._load_targets_fail_closed(target_root)
    opens = tuple(bar.opened_at for bar in evidence.bars)

    h1 = build_h1(evidence.bars)
    h4 = build_h4(evidence.bars)
    daily = build_daily(h4)
    frames: dict[str, Sequence[SourceCandle]] = {"H1": h1, "H4": h4}
    frame_indexes = {
        timeframe: {candle.opened_at: index for index, candle in enumerate(candles)}
        for timeframe, candles in frames.items()
    }
    frame_by_open = {
        timeframe: {candle.opened_at: candle for candle in candles}
        for timeframe, candles in frames.items()
    }
    h1_opens = tuple(candle.opened_at for candle in h1)
    h4_opens = tuple(candle.opened_at for candle in h4)
    d1_opens = tuple(candle.opened_at for candle in daily)
    d1_regime = r5._aggregate(evidence.bars, "D1")
    h4_regime = r5._aggregate(evidence.bars, "H4")

    families: dict[str, list[dict[str, Any]]] = {
        name: [] for name in r8.BREAK_FAMILIES
    }
    retained = 0

    for setup, trade in selected:
        base = causal._record(setup, trade, evidence.bars, opens)
        base.update(r5._regime_features(base, d1_regime, h4_regime))
        if r7._is_abstain(base):
            continue
        retained += 1
        family = next(
            (
                name
                for name, signature in r8.BREAK_FAMILIES.items()
                if r8._matches(base, signature)
            ),
            None,
        )
        if family is None:
            continue

        timeframe = setup.context.timeframe
        c1 = frame_by_open[timeframe].get(setup.context.signal.c1_opened_at)
        if c1 is None:
            raise ValueError("R10 memory atlas missing C1")

        target_rows = episodes.get(trade.episode_id)
        if not target_rows:
            raise ValueError("R10 memory atlas missing target episode")

        prior20 = r9._mean_prior_source_range(
            frames[timeframe],
            frame_indexes[timeframe],
            setup.source.opened_at,
        )
        row: dict[str, Any] = dict(base)
        row.update(
            r9._continuous_record(
                setup,
                trade,
                c1,
                prior20,
                h1,
                h1_opens,
                h4,
                h4_opens,
                d1_regime,
                h4_regime,
                target_rows,
            )
        )
        path = divergence._path_diagnostic(
            trade,
            target_rows,
            evidence,
            opens,
        )
        row["journey_failure_stage"] = path["journey_failure_stage"]
        row["outcome_class"] = ps._outcome_class(str(path["journey_failure_stage"]))
        row.update(
            liquidity._features(
                setup,
                c1,
                frames,
                frame_indexes,
                h1,
                h4,
                daily,
                h4_opens,
                d1_opens,
            )
        )
        row.update(cisd._sequence_features(setup, c1))
        row.update(ps._ps_features(setup, trade))
        row["family"] = family
        row["year"] = datetime.fromisoformat(str(base["entry_at"])).year
        families[family].append(row)

    if retained != 5612:
        raise ValueError(f"R10 memory atlas R7 retained drift: {retained}")
    expected = {
        "BREAK_A_DEEP_RAID_MID_LATE_CISD": 151,
        "BREAK_B_MODERATE_RAID_MID_CISD_NORMAL_H4": 88,
    }
    for family, expected_count in expected.items():
        if len(families[family]) != expected_count:
            raise ValueError(
                f"R10 memory atlas family drift {family}: "
                f"{len(families[family])} != {expected_count}"
            )

    payload = {
        "schema": "qore.turtle_soup_xauusd_r10.causal_memory_transfer_atlas.v1",
        "identity": IDENTITY,
        "evidence_status": EVIDENCE_STATUS,
        "reproduction": {
            **reproduction,
            "r7_retained": retained,
            "break_a_trades": len(
                families["BREAK_A_DEEP_RAID_MID_LATE_CISD"]
            ),
            "break_b_trades": len(
                families["BREAK_B_MODERATE_RAID_MID_CISD_NORMAL_H4"]
            ),
        },
        "question": (
            "DO_PRE_REGISTERED_CAUSAL_CLUES_LEARNED_FROM_EARLY_CONSUMED_HISTORY_"
            "TRANSFER_WITHOUT_RECALIBRATION_TO_LATER_CONSUMED_PERIODS"
        ),
        "anchor_contract": {
            "calibration_period": "2016-2020_CONSUMED_DIAGNOSTIC",
            "threshold_rule": "MIDPOINT_OF_EARLY_CAPABLE_AND_INVALIDATED_MEDIANS",
            "direction_rule": "SIDE_CONTAINING_EARLY_DOL_CAPABLE_MEDIAN",
            "automatic_threshold_search": False,
            "pnl_used_for_calibration": False,
            "later_period_recalibration": False,
            "year_allowed_as_operating_input": False,
        },
        "families": {
            family: _family_report(
                rows,
                FAMILY_SPECS[family][0],
                FAMILY_SPECS[family][1],
            )
            for family, rows in families.items()
        },
        "interpretation_contract": {
            "post_entry_path_used_only_as_structural_label": True,
            "post_entry_path_allowed_as_operating_input": False,
            "all_explanatory_features_known_by_entry": True,
            "pnl_used_for_feature_selection": False,
            "pair_list_pre_registered_in_code": True,
            "automatic_pair_search": False,
            "candidate_rule_promoted": False,
            "transfer_success_is_not_trade_permission": True,
        },
        "governance": {
            "diagnostic_only": True,
            "fresh_holdout_consumed": False,
            "demo_eligible": False,
            "live_authorized": False,
            "real_capital_authorized": False,
            "production_authorized": False,
        },
    }

    output.mkdir(parents=True, exist_ok=True)
    (output / "causal-memory-transfer-atlas.json").write_text(
        json.dumps(_jsonable(payload), indent=2, sort_keys=True) + "\n"
    )
    for family, filename in (
        ("BREAK_A_DEEP_RAID_MID_LATE_CISD", "break-a-memory-cases.json"),
        ("BREAK_B_MODERATE_RAID_MID_CISD_NORMAL_H4", "break-b-memory-cases.json"),
    ):
        (output / filename).write_text(
            json.dumps(_jsonable(families[family]), indent=2, sort_keys=True)
            + "\n"
        )
    return cast(dict[str, Any], _jsonable(payload))


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
