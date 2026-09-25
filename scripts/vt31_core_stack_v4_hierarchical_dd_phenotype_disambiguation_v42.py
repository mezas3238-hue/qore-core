"""VT31 Shared hierarchical natural-DD phenotype disambiguation V42.

Phase-1 knowledge expansion only.

V41 catalogs single-view drawdown phenotypes. V42 composes every pair of those
causal views to learn higher-order forms that can disambiguate a parent
phenotype that is individually ambiguous.

The registry retains all pair phenotypes. A supported cross-fold pure subset is
reported separately when the exact pair:
- appears with >=2 losses in R8,
- appears with >=2 losses in R6,
- has zero winners in both folds.

This support criterion is descriptive knowledge, not a runtime policy.

No sizing, abstention, stop/target mutation, trailing, target extension, R5, or
fresh holdout.
"""
# ruff: noqa: E501
from __future__ import annotations

import argparse
import itertools
import json
from collections import defaultdict
from decimal import Decimal
from pathlib import Path
from typing import cast

import vt31_core_stack_v4_universal_dd_phenotype_registry_v41 as v41

SCHEMA = "qore.core_stack_v4.vt31.hierarchical_dd_phenotype_disambiguation.v42"
IDENTITY = "VT31_NAS100_SHARED_HIERARCHICAL_DD_PHENOTYPE_DISAMBIGUATION_V42"
ZERO = Decimal("0")

v33 = v41.v33
v26 = v41.v26
v18 = v41.v18

VIEW_MAP = dict(v41.ALL_VIEWS)
PAIR_VIEWS: tuple[tuple[str, str], ...] = tuple(
    itertools.combinations(VIEW_MAP.keys(), 2)
)


def _d(value: object) -> Decimal:
    return Decimal(str(value))


def _ratio(hit: int, total: int) -> str:
    return "0" if total == 0 else format(Decimal(hit) / Decimal(total), "f")


def _single_signature(
    sequence: dict[str, object],
    view_name: str,
) -> str:
    return v41._view_signature(sequence, VIEW_MAP[view_name])


def _pair_signature(
    sequence: dict[str, object],
    left: str,
    right: str,
) -> str:
    return (
        f"{left}[{_single_signature(sequence, left)}]"
        f"||{right}[{_single_signature(sequence, right)}]"
    )


def _temporal_labels(rows: list[dict[str, object]]) -> dict[str, str]:
    return v41._temporal_labels(rows)


def _stats(
    members: list[dict[str, object]],
    *,
    temporal: dict[str, str],
) -> dict[str, object]:
    return v41._bucket_stats(members, temporal_labels=temporal)


def _fold_pair_registry(
    rows: list[dict[str, object]],
) -> dict[tuple[str, str, str], dict[str, object]]:
    temporal = _temporal_labels(rows)
    registry: dict[tuple[str, str, str], dict[str, object]] = {}

    for left, right in PAIR_VIEWS:
        groups: dict[str, list[dict[str, object]]] = defaultdict(list)
        for row in rows:
            sequence = cast(dict[str, object], row["sequence"])
            groups[_pair_signature(sequence, left, right)].append(row)

        for signature, members in groups.items():
            registry[(left, right, signature)] = {
                "left_view": left,
                "right_view": right,
                "signature": signature,
                **_stats(members, temporal=temporal),
            }
    return registry


def _composition(losses: int, wins: int) -> str:
    return v41._combined_composition(losses, wins)


def _support_class(
    r8: dict[str, object] | None,
    r6: dict[str, object] | None,
    *,
    total_wins: int,
) -> str:
    if r8 is None or r6 is None:
        return "SINGLE_FOLD"
    r8_losses = int(r8["losses"])
    r6_losses = int(r6["losses"])
    if total_wins == 0 and r8_losses >= 2 and r6_losses >= 2:
        return "SUPPORTED_CROSS_FOLD_PURE"
    if total_wins == 0:
        return "CROSS_FOLD_PURE_LOW_SUPPORT"
    return "CROSS_FOLD_MIXED"


def _combined_pair_registry(
    r8: dict[tuple[str, str, str], dict[str, object]],
    r6: dict[tuple[str, str, str], dict[str, object]],
) -> list[dict[str, object]]:
    output: list[dict[str, object]] = []
    for key in sorted(set(r8) | set(r6)):
        a = r8.get(key)
        b = r6.get(key)
        folds = [item for item in (a, b) if item is not None]
        losses = sum(int(item["losses"]) for item in folds)
        wins = sum(int(item["wins"]) for item in folds)
        sample = sum(int(item["sample"]) for item in folds)
        loss_r = sum((_d(item["loss_r"]) for item in folds), ZERO)
        winner_r = sum((_d(item["winner_r"]) for item in folds), ZERO)
        top3 = sum(int(item["top3_dd_losses"]) for item in folds)
        max_dd = sum(int(item["max_dd_losses"]) for item in folds)
        unobservable = sum(int(item["unobservable_losses"]) for item in folds)
        output.append(
            {
                "left_view": key[0],
                "right_view": key[1],
                "signature": key[2],
                "fold_presence": v41._presence(a, b),
                "composition": _composition(losses, wins),
                "support_class": _support_class(a, b, total_wins=wins),
                "sample": sample,
                "losses": losses,
                "wins": wins,
                "loss_rate": _ratio(losses, sample),
                "loss_r": format(loss_r, "f"),
                "winner_r": format(winner_r, "f"),
                "top3_dd_losses": top3,
                "max_dd_losses": max_dd,
                "unobservable_losses": unobservable,
                "r8": a,
                "r6": b,
            }
        )
    output.sort(
        key=lambda row: (
            1 if row["support_class"] == "SUPPORTED_CROSS_FOLD_PURE" else 0,
            int(row["top3_dd_losses"]),
            int(row["losses"]),
            _d(row["loss_r"]),
        ),
        reverse=True,
    )
    return output


def _single_registry_map(
    single_registry: list[dict[str, object]],
) -> dict[tuple[str, str], dict[str, object]]:
    return {
        (str(row["view"]), str(row["signature"])): row
        for row in single_registry
    }


def _parent_classes(
    pair: dict[str, object],
    *,
    single_map: dict[tuple[str, str], dict[str, object]],
) -> tuple[str, str]:
    left_view = str(pair["left_view"])
    right_view = str(pair["right_view"])
    signature = str(pair["signature"])

    # Pair signature embeds exact parent signatures between [ ].
    left_prefix = left_view + "["
    middle = "]||" + right_view + "["
    if not signature.startswith(left_prefix) or middle not in signature:
        return ("UNKNOWN", "UNKNOWN")
    left_sig, right_part = signature[len(left_prefix):].split(middle, 1)
    right_sig = right_part[:-1] if right_part.endswith("]") else right_part

    left = single_map.get((left_view, left_sig))
    right = single_map.get((right_view, right_sig))
    return (
        "UNKNOWN" if left is None else str(left["composition"]),
        "UNKNOWN" if right is None else str(right["composition"]),
    )


def _coverage(
    rows8: list[dict[str, object]],
    rows6: list[dict[str, object]],
    *,
    pairs: list[dict[str, object]],
    single_registry: list[dict[str, object]],
) -> dict[str, object]:
    all_rows = rows8 + rows6
    losses = [row for row in all_rows if row["outcome"] == "LOSS"]
    winners = [row for row in all_rows if row["outcome"] == "WIN"]

    supported = {
        (
            str(row["left_view"]),
            str(row["right_view"]),
            str(row["signature"]),
        )
        for row in pairs
        if row["support_class"] == "SUPPORTED_CROSS_FOLD_PURE"
    }

    single_pure = {
        (str(row["view"]), str(row["signature"]))
        for row in single_registry
        if row["composition"] == "PURE_LOSS"
    }

    pair_loss_signals: set[str] = set()
    pair_winner_signals: set[str] = set()
    single_pure_loss_signals: set[str] = set()

    for row in all_rows:
        sequence = cast(dict[str, object], row["sequence"])
        signal = str(row["signal_at"])

        if any(
            (
                view_name,
                _single_signature(sequence, view_name),
            )
            in single_pure
            for view_name in VIEW_MAP
        ):
            if row["outcome"] == "LOSS":
                single_pure_loss_signals.add(signal)

        matched_supported = any(
            (
                left,
                right,
                _pair_signature(sequence, left, right),
            )
            in supported
            for left, right in PAIR_VIEWS
        )
        if matched_supported:
            if row["outcome"] == "LOSS":
                pair_loss_signals.add(signal)
            elif row["outcome"] == "WIN":
                pair_winner_signals.add(signal)

    incremental = pair_loss_signals - single_pure_loss_signals
    return {
        "total_losses": len(losses),
        "total_winners": len(winners),
        "supported_pure_pair_loss_coverage_count": len(pair_loss_signals),
        "supported_pure_pair_loss_coverage": _ratio(
            len(pair_loss_signals),
            len(losses),
        ),
        "supported_pure_pair_winner_overlap_count": len(pair_winner_signals),
        "single_pure_loss_coverage_count": len(single_pure_loss_signals),
        "incremental_losses_beyond_single_view_pure": len(incremental),
        "incremental_loss_coverage_beyond_single_view_pure": _ratio(
            len(incremental),
            len(losses),
        ),
    }


def _summary(
    pair_registry: list[dict[str, object]],
    *,
    single_registry: list[dict[str, object]],
) -> dict[str, object]:
    single_map = _single_registry_map(single_registry)
    supported = [
        row
        for row in pair_registry
        if row["support_class"] == "SUPPORTED_CROSS_FOLD_PURE"
    ]
    ambiguity_resolvers = 0
    for row in supported:
        left_class, right_class = _parent_classes(row, single_map=single_map)
        if left_class != "PURE_LOSS" or right_class != "PURE_LOSS":
            ambiguity_resolvers += 1

    support_counts: dict[str, int] = defaultdict(int)
    composition_counts: dict[str, int] = defaultdict(int)
    for row in pair_registry:
        support_counts[str(row["support_class"])] += 1
        composition_counts[str(row["composition"])] += 1

    return {
        "pair_view_count": len(PAIR_VIEWS),
        "pair_phenotype_count": len(pair_registry),
        "support_class_counts": dict(sorted(support_counts.items())),
        "composition_counts": dict(sorted(composition_counts.items())),
        "supported_cross_fold_pure_pairs": len(supported),
        "supported_pure_pairs_that_resolve_ambiguous_parent": ambiguity_resolvers,
    }


def run(
    *,
    r8_trades: Path,
    r6_trades: Path,
    r8_nas: Path,
    r8_sp: Path,
    r8_us: Path,
    r6_nas: Path,
    r6_sp: Path,
    r6_us: Path,
    daily_path: Path,
) -> dict[str, object]:
    daily = v33.v32.v31.v30.v28.v27.v26.v23.v22.v21.v20.v19.v18.v2.v3._load_daily(
        daily_path
    )
    r8_source = v18._load_cross_rows(
        trades=r8_trades,
        nas=r8_nas,
        sp=r8_sp,
        us=r8_us,
        daily=daily,
    )
    r6_source = v18._load_cross_rows(
        trades=r6_trades,
        nas=r6_nas,
        sp=r6_sp,
        us=r6_us,
        daily=daily,
    )
    if len(r8_source) != 228 or len(r6_source) != 278:
        raise AssertionError("VT31 R8/R6 challenge-set drift")

    p8, _ = v26._prepare(
        r8_source,
        nas_evidence=r8_nas,
        sp_evidence=r8_sp,
        us_evidence=r8_us,
    )
    p6, _ = v26._prepare(
        r6_source,
        nas_evidence=r6_nas,
        sp_evidence=r6_sp,
        us_evidence=r6_us,
    )
    rows8 = v41._all_sequence_rows(p8, sp_evidence=r8_sp, us_evidence=r8_us)
    rows6 = v41._all_sequence_rows(p6, sp_evidence=r6_sp, us_evidence=r6_us)

    single8 = v41._fold_registry(rows8)
    single6 = v41._fold_registry(rows6)
    single_registry = v41._combined_registry(single8, single6)

    pair8 = _fold_pair_registry(rows8)
    pair6 = _fold_pair_registry(rows6)
    pairs = _combined_pair_registry(pair8, pair6)

    return {
        "schema": SCHEMA,
        "identity": IDENTITY,
        "research_phase": "PHASE_1_NATURAL_DD_INTELLIGENCE",
        "status": "HIERARCHICAL_DD_PHENOTYPE_DISAMBIGUATION_NO_ACTUATION",
        "challenge_set": {"r8": 228, "r6": 278},
        "single_view_count": len(VIEW_MAP),
        "pair_view_count": len(PAIR_VIEWS),
        "registry_summary": _summary(
            pairs,
            single_registry=single_registry,
        ),
        "coverage_summary": _coverage(
            rows8,
            rows6,
            pairs=pairs,
            single_registry=single_registry,
        ),
        "supported_cross_fold_pure_pairs": [
            row
            for row in pairs
            if row["support_class"] == "SUPPORTED_CROSS_FOLD_PURE"
        ],
        "pair_phenotype_registry": pairs,
        "phase_1_contract": {
            "same_trade_universe": True,
            "same_initial_position_size": True,
            "sizing_used": False,
            "capital_weighting_used": False,
            "entry_abstention_used": False,
            "stop_geometry_mutated": False,
            "target_geometry_mutated": False,
            "trailing_used": False,
            "target_extension_used": False,
            "realized_dd_reduction_claimed": False,
            "runtime_outcome_input_used": False,
            "future_market_input_used": False,
            "outcomes_used_offline_for_phenotype_labeling_only": True,
            "registry_is_not_runtime_policy": True,
            "r5_opened": False,
            "new_holdout_opened": False,
        },
        "governance": {
            "vt31_is_falsification_lab_only": True,
            "live_authorized": False,
            "production_authorized": False,
            "real_capital_authorized": False,
            "merge_authorized": False,
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--r8-trades", type=Path, required=True)
    parser.add_argument("--r6-trades", type=Path, required=True)
    parser.add_argument("--r8-nas", type=Path, required=True)
    parser.add_argument("--r8-sp", type=Path, required=True)
    parser.add_argument("--r8-us", type=Path, required=True)
    parser.add_argument("--r6-nas", type=Path, required=True)
    parser.add_argument("--r6-sp", type=Path, required=True)
    parser.add_argument("--r6-us", type=Path, required=True)
    parser.add_argument("--daily-path", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    payload = run(
        r8_trades=args.r8_trades,
        r6_trades=args.r6_trades,
        r8_nas=args.r8_nas,
        r8_sp=args.r8_sp,
        r8_us=args.r8_us,
        r6_nas=args.r6_nas,
        r6_sp=args.r6_sp,
        r6_us=args.r6_us,
        daily_path=args.daily_path,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, sort_keys=True, indent=2) + "\n")
    print(
        json.dumps(
            {
                "status": payload["status"],
                "registry_summary": payload["registry_summary"],
                "coverage_summary": payload["coverage_summary"],
                "top_supported_pairs": payload[
                    "supported_cross_fold_pure_pairs"
                ][:25],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
