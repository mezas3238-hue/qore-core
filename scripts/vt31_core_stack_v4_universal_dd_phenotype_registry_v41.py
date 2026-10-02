"""VT31 Shared universal natural-DD phenotype registry V41.

Phase-1 knowledge expansion only.

Goal: catalog as many causal drawdown forms as possible without turning them
into intervention rules. Every methodology-valid trade keeps its original
economics. Shared receives a universal phenotype registry describing exact
state sequences and categorical causal morphologies observed before losses.

Each phenotype is tagged by:
- outcome composition (PURE_LOSS / LOSS_DOMINANT / MIXED / WINNER_DOMINANT),
- fold presence (R8 / R6 / BOTH),
- temporal presence (early/late halves per fold),
- loss-R severity,
- top-DD and max-DD participation,
- unobservable-loss participation,
- winner-R contamination.

This is knowledge, not actuation. Ambiguous phenotypes remain in the registry
because Shared must learn to recognize them in live markets even when they are
not safe enough to trigger defensive action.

No sizing, capital weighting, abstention, stop/target mutation, trailing, target
extension, R5, or fresh holdout.
"""
# ruff: noqa: E501
from __future__ import annotations

import argparse
import json
from collections import defaultdict
from decimal import Decimal
from pathlib import Path
from typing import cast

import vt31_core_stack_v4_natural_dd_dual_fold_temporal_consensus_v40 as v40

SCHEMA = "qore.core_stack_v4.vt31.universal_natural_dd_phenotype_registry.v41"
IDENTITY = "VT31_NAS100_SHARED_UNIVERSAL_NATURAL_DD_PHENOTYPE_REGISTRY_V41"
ZERO = Decimal("0")

v39 = v40.v39
v38 = v39.v38
v34 = v38.v34
v33 = v38.v33
v30 = v33.v30
v26 = v38.v26
v18 = v38.v18

EXACT_VIEWS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("ENVIRONMENT_SEQUENCE", ("environment_state_sequence",)),
    ("TRAJECTORY_SEQUENCE", ("trajectory_state_sequence",)),
    ("ENVIRONMENT_TERMINAL_3", ("environment_terminal_3",)),
    ("TRAJECTORY_TERMINAL_3", ("trajectory_terminal_3",)),
)

MORPHOLOGY_VIEWS: tuple[tuple[str, tuple[str, ...]], ...] = tuple(v38.PROJECTIONS)
ALL_VIEWS = EXACT_VIEWS + MORPHOLOGY_VIEWS


def _d(value: object) -> Decimal:
    return Decimal(str(value))


def _ratio(hit: int, total: int) -> str:
    return "0" if total == 0 else format(Decimal(hit) / Decimal(total), "f")


def _view_signature(sequence: dict[str, object], keys: tuple[str, ...]) -> str:
    return "|".join(f"{key}={sequence.get(key, 'MISSING')}" for key in keys)


def _all_sequence_rows(
    prepared: list[dict[str, object]],
    *,
    sp_evidence: Path,
    us_evidence: Path,
) -> list[dict[str, object]]:
    excursions = v30._drawdown_excursions(prepared)
    base_rows = v30._signature_rows(prepared, excursions)
    by_signal = {str(row["signal_at"]): row for row in base_rows}
    sp_by_day = v18.v13._group_market(sp_evidence)
    us_by_day = v18.v13._group_market(us_evidence)

    output: list[dict[str, object]] = []
    for item in prepared:
        row = cast(dict[str, object], item["row"])
        base = by_signal[str(row["signal_at"])]
        sequence = v33._sequence(
            item=item,
            sp_by_day=sp_by_day,
            us_by_day=us_by_day,
        )
        output.append({**base, "sequence": sequence})
    output.sort(key=lambda row: str(row["signal_at"]))
    return output


def _temporal_labels(rows: list[dict[str, object]]) -> dict[str, str]:
    ordered = sorted(rows, key=lambda row: str(row["signal_at"]))
    cut = len(ordered) // 2
    labels: dict[str, str] = {}
    for index, row in enumerate(ordered):
        labels[str(row["signal_at"])] = "EARLY" if index < cut else "LATE"
    return labels


def _bucket_stats(
    members: list[dict[str, object]],
    *,
    temporal_labels: dict[str, str],
) -> dict[str, object]:
    losses = [row for row in members if row["outcome"] == "LOSS"]
    winners = [row for row in members if row["outcome"] == "WIN"]
    flats = [row for row in members if row["outcome"] == "FLAT"]
    top3_losses = [
        row for row in losses if bool(row["in_top3_dd_excursions"])
    ]
    max_dd_losses = [
        row for row in losses if bool(row["in_max_dd_excursion"])
    ]
    unobservable_losses = [
        row for row in losses if bool(row["unobservable_loss"])
    ]
    loss_r = -sum((_d(row["baseline_r"]) for row in losses), ZERO)
    winner_r = sum((_d(row["baseline_r"]) for row in winners), ZERO)

    early_losses = sum(
        temporal_labels[str(row["signal_at"])] == "EARLY"
        for row in losses
    )
    late_losses = len(losses) - early_losses
    early_winners = sum(
        temporal_labels[str(row["signal_at"])] == "EARLY"
        for row in winners
    )
    late_winners = len(winners) - early_winners

    if not winners and losses:
        composition = "PURE_LOSS"
    elif len(losses) > len(winners):
        composition = "LOSS_DOMINANT"
    elif len(losses) == len(winners):
        composition = "MIXED_BALANCED"
    else:
        composition = "WINNER_DOMINANT"

    return {
        "sample": len(members),
        "losses": len(losses),
        "wins": len(winners),
        "flats": len(flats),
        "composition": composition,
        "loss_rate": _ratio(len(losses), len(members)),
        "loss_r": format(loss_r, "f"),
        "winner_r": format(winner_r, "f"),
        "top3_dd_losses": len(top3_losses),
        "max_dd_losses": len(max_dd_losses),
        "unobservable_losses": len(unobservable_losses),
        "early_losses": early_losses,
        "late_losses": late_losses,
        "early_winners": early_winners,
        "late_winners": late_winners,
    }


def _fold_registry(
    rows: list[dict[str, object]],
) -> dict[tuple[str, str], dict[str, object]]:
    temporal = _temporal_labels(rows)
    registry: dict[tuple[str, str], dict[str, object]] = {}

    for view_name, keys in ALL_VIEWS:
        groups: dict[str, list[dict[str, object]]] = defaultdict(list)
        for row in rows:
            sequence = cast(dict[str, object], row["sequence"])
            groups[_view_signature(sequence, keys)].append(row)
        for signature, members in groups.items():
            registry[(view_name, signature)] = {
                "view": view_name,
                "keys": keys,
                "signature": signature,
                **_bucket_stats(members, temporal_labels=temporal),
            }
    return registry


def _presence(
    r8: dict[str, object] | None,
    r6: dict[str, object] | None,
) -> str:
    if r8 is not None and r6 is not None:
        return "BOTH_FOLDS"
    if r8 is not None:
        return "R8_ONLY"
    return "R6_ONLY"


def _combined_composition(
    losses: int,
    wins: int,
) -> str:
    if losses > 0 and wins == 0:
        return "PURE_LOSS"
    if losses > wins:
        return "LOSS_DOMINANT"
    if losses == wins:
        return "MIXED_BALANCED"
    return "WINNER_DOMINANT"


def _temporal_stability(
    r8: dict[str, object] | None,
    r6: dict[str, object] | None,
) -> str:
    buckets = 0
    loss_buckets = 0
    winner_buckets = 0
    for fold in (r8, r6):
        if fold is None:
            continue
        for key in ("early_losses", "late_losses"):
            buckets += 1
            if int(fold[key]) > 0:
                loss_buckets += 1
        for key in ("early_winners", "late_winners"):
            if int(fold[key]) > 0:
                winner_buckets += 1

    if loss_buckets >= 4:
        temporal = "LOSS_PRESENT_ALL_HALVES"
    elif loss_buckets >= 3:
        temporal = "LOSS_PRESENT_MOST_HALVES"
    elif loss_buckets >= 2:
        temporal = "LOSS_PRESENT_MULTIPLE_HALVES"
    else:
        temporal = "LOSS_LOCALIZED"

    if winner_buckets == 0:
        return temporal + "_NO_WINNER_HALF"
    return temporal + "_WINNER_OVERLAP"


def _combined_registry(
    r8_registry: dict[tuple[str, str], dict[str, object]],
    r6_registry: dict[tuple[str, str], dict[str, object]],
) -> list[dict[str, object]]:
    output: list[dict[str, object]] = []
    for key in sorted(set(r8_registry) | set(r6_registry)):
        a = r8_registry.get(key)
        b = r6_registry.get(key)
        losses = sum(int(x["losses"]) for x in (a, b) if x is not None)
        wins = sum(int(x["wins"]) for x in (a, b) if x is not None)
        loss_r = sum((_d(x["loss_r"]) for x in (a, b) if x is not None), ZERO)
        winner_r = sum((_d(x["winner_r"]) for x in (a, b) if x is not None), ZERO)
        top3 = sum(
            int(x["top3_dd_losses"])
            for x in (a, b)
            if x is not None
        )
        max_dd = sum(
            int(x["max_dd_losses"])
            for x in (a, b)
            if x is not None
        )
        unobservable = sum(
            int(x["unobservable_losses"])
            for x in (a, b)
            if x is not None
        )
        sample = sum(int(x["sample"]) for x in (a, b) if x is not None)
        output.append(
            {
                "view": key[0],
                "signature": key[1],
                "keys": (a or b)["keys"],
                "fold_presence": _presence(a, b),
                "temporal_stability": _temporal_stability(a, b),
                "composition": _combined_composition(losses, wins),
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
            1 if row["composition"] == "PURE_LOSS" else 0,
            int(row["top3_dd_losses"]),
            int(row["losses"]),
            _d(row["loss_r"]),
        ),
        reverse=True,
    )
    return output


def _signature_set(
    rows: list[dict[str, object]],
    registry: list[dict[str, object]],
    *,
    allowed_compositions: set[str],
) -> set[str]:
    allowed = {
        (str(item["view"]), str(item["signature"]))
        for item in registry
        if str(item["composition"]) in allowed_compositions
    }
    signals: set[str] = set()
    for row in rows:
        sequence = cast(dict[str, object], row["sequence"])
        for view_name, keys in ALL_VIEWS:
            signature = _view_signature(sequence, keys)
            if (view_name, signature) in allowed:
                signals.add(str(row["signal_at"]))
                break
    return signals


def _coverage_summary(
    rows8: list[dict[str, object]],
    rows6: list[dict[str, object]],
    registry: list[dict[str, object]],
) -> dict[str, object]:
    all_rows = rows8 + rows6
    losses = [row for row in all_rows if row["outcome"] == "LOSS"]
    winners = [row for row in all_rows if row["outcome"] == "WIN"]

    pure_signals = _signature_set(
        all_rows,
        registry,
        allowed_compositions={"PURE_LOSS"},
    )
    loss_biased_signals = _signature_set(
        all_rows,
        registry,
        allowed_compositions={"PURE_LOSS", "LOSS_DOMINANT"},
    )
    any_loss_form_signatures = {
        (str(item["view"]), str(item["signature"]))
        for item in registry
        if int(item["losses"]) > 0
    }

    recognized_any: set[str] = set()
    for row in all_rows:
        if row["outcome"] != "LOSS":
            continue
        sequence = cast(dict[str, object], row["sequence"])
        if any(
            (
                view_name,
                _view_signature(sequence, keys),
            )
            in any_loss_form_signatures
            for view_name, keys in ALL_VIEWS
        ):
            recognized_any.add(str(row["signal_at"]))

    pure_losses = [
        row for row in losses if str(row["signal_at"]) in pure_signals
    ]
    biased_losses = [
        row for row in losses if str(row["signal_at"]) in loss_biased_signals
    ]
    pure_winners = [
        row for row in winners if str(row["signal_at"]) in pure_signals
    ]
    biased_winners = [
        row for row in winners if str(row["signal_at"]) in loss_biased_signals
    ]

    return {
        "total_losses": len(losses),
        "total_winners": len(winners),
        "losses_with_any_registered_dd_form": len(recognized_any),
        "any_registered_dd_form_loss_coverage": _ratio(
            len(recognized_any),
            len(losses),
        ),
        "losses_with_at_least_one_pure_loss_phenotype": len(pure_losses),
        "pure_loss_phenotype_coverage": _ratio(
            len(pure_losses),
            len(losses),
        ),
        "winners_sharing_at_least_one_pure_loss_phenotype": len(pure_winners),
        "losses_with_at_least_one_loss_biased_phenotype": len(biased_losses),
        "loss_biased_phenotype_coverage": _ratio(
            len(biased_losses),
            len(losses),
        ),
        "winners_sharing_loss_biased_phenotypes": len(biased_winners),
    }


def _registry_summary(registry: list[dict[str, object]]) -> dict[str, object]:
    composition_counts: dict[str, int] = defaultdict(int)
    fold_counts: dict[str, int] = defaultdict(int)
    temporal_counts: dict[str, int] = defaultdict(int)
    for row in registry:
        composition_counts[str(row["composition"])] += 1
        fold_counts[str(row["fold_presence"])] += 1
        temporal_counts[str(row["temporal_stability"])] += 1

    return {
        "phenotype_count": len(registry),
        "composition_counts": dict(sorted(composition_counts.items())),
        "fold_presence_counts": dict(sorted(fold_counts.items())),
        "temporal_stability_counts": dict(sorted(temporal_counts.items())),
        "pure_cross_fold_phenotypes": sum(
            row["composition"] == "PURE_LOSS"
            and row["fold_presence"] == "BOTH_FOLDS"
            for row in registry
        ),
        "pure_cross_fold_all_halves_phenotypes": sum(
            row["composition"] == "PURE_LOSS"
            and row["fold_presence"] == "BOTH_FOLDS"
            and str(row["temporal_stability"]).startswith(
                "LOSS_PRESENT_ALL_HALVES"
            )
            for row in registry
        ),
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

    rows8 = _all_sequence_rows(
        p8,
        sp_evidence=r8_sp,
        us_evidence=r8_us,
    )
    rows6 = _all_sequence_rows(
        p6,
        sp_evidence=r6_sp,
        us_evidence=r6_us,
    )
    reg8 = _fold_registry(rows8)
    reg6 = _fold_registry(rows6)
    registry = _combined_registry(reg8, reg6)

    return {
        "schema": SCHEMA,
        "identity": IDENTITY,
        "research_phase": "PHASE_1_NATURAL_DD_INTELLIGENCE",
        "status": "UNIVERSAL_DD_PHENOTYPE_REGISTRY_NO_ACTUATION",
        "challenge_set": {"r8": 228, "r6": 278},
        "view_count": len(ALL_VIEWS),
        "views": [
            {"name": name, "keys": keys}
            for name, keys in ALL_VIEWS
        ],
        "registry_summary": _registry_summary(registry),
        "coverage_summary": _coverage_summary(rows8, rows6, registry),
        "phenotype_registry": registry,
        "top_pure_cross_fold_phenotypes": [
            row
            for row in registry
            if row["composition"] == "PURE_LOSS"
            and row["fold_presence"] == "BOTH_FOLDS"
        ][:50],
        "top_loss_dominant_cross_fold_phenotypes": [
            row
            for row in registry
            if row["composition"] == "LOSS_DOMINANT"
            and row["fold_presence"] == "BOTH_FOLDS"
        ][:50],
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
            "ambiguous_dd_forms_retained_for_knowledge": True,
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
                "top_pure_cross_fold_phenotypes": payload[
                    "top_pure_cross_fold_phenotypes"
                ][:20],
                "top_loss_dominant_cross_fold_phenotypes": payload[
                    "top_loss_dominant_cross_fold_phenotypes"
                ][:20],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
