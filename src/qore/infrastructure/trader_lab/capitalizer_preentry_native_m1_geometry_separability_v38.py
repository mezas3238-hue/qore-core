"""Cross-era STOP/TARGET separability with new native-M1 geometry for V38.

V37 falsified the existing 45D V11 representation at approximately chance AUC.
V38 keeps the identical cross-era protocol and adds only the frozen 12D
outcome-free geometry extracted from the current MAX_RECOVERY methodology.

This remains an information-frontier experiment, not an admission policy.
"""

from __future__ import annotations

import argparse
import json
import math
from dataclasses import asdict, replace
from pathlib import Path
from typing import Any

from qore.infrastructure.trader_lab import (
    capitalizer_factor_journey_probe_ranker_v11 as v11,
)
from qore.infrastructure.trader_lab import (
    capitalizer_preentry_full_stop_causal_separability_v37 as v37,
)
from qore.infrastructure.trader_lab import (
    capitalizer_preentry_native_m1_geometry_collector_v38 as collector,
)
from qore.infrastructure.trader_lab import (
    capitalizer_regularized_causal_state_space_v25 as v25,
)
from qore.infrastructure.trader_lab import (
    capitalizer_sequence_failure_memory_abstention_v13 as v13,
)

IDENTITY = "QORE_CAPITALIZER_PREENTRY_NATIVE_M1_GEOMETRY_SEPARABILITY_V38"
V11_DIMENSION = 45
M1_GEOMETRY_DIMENSION = 12
FEATURE_DIMENSION = V11_DIMENSION + M1_GEOMETRY_DIMENSION


def _load_period_geometry(
    root: Path,
    *,
    slug: str,
) -> dict[tuple[str, str], collector.SelectedGeometry]:
    paths = sorted(
        root.rglob(f"capitalizer-v38-{slug}-selected-geometry.jsonl")
    )
    if len(paths) != 1:
        raise ValueError(
            f"V38 requires one selected geometry ledger for {slug}, "
            f"got {len(paths)}"
        )
    rows: list[collector.SelectedGeometry] = []
    with paths[0].open(encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            raw = json.loads(line)
            if not isinstance(raw, dict):
                raise ValueError("V38 selected geometry row must be object")
            nested = raw.get("geometry")
            if not isinstance(nested, dict):
                raise ValueError("V38 selected geometry missing nested row")
            from qore.infrastructure.trader_lab import (
                capitalizer_preentry_native_m1_geometry_v38 as geometry,
            )

            raw["geometry"] = geometry.from_json_dict(nested)
            rows.append(collector.SelectedGeometry(**raw))
    by_key = {(row.symbol, row.entry_at): row for row in rows}
    if len(by_key) != len(rows):
        raise ValueError("V38 selected geometry duplicate entrant identity")
    return by_key


def _extend_states(
    states: tuple[v37.LabeledEntryState, ...],
    geometry_by_key: dict[tuple[str, str], collector.SelectedGeometry],
) -> tuple[v37.LabeledEntryState, ...]:
    state_keys = {(row.symbol, row.entry_at) for row in states}
    missing = state_keys - set(geometry_by_key)
    if missing:
        raise ValueError(
            "V38 STOP/TARGET state missing causal geometry: "
            f"{len(missing)}"
        )

    result: list[v37.LabeledEntryState] = []
    for row in states:
        selected = geometry_by_key[(row.symbol, row.entry_at)]
        extra = tuple(float(value) for value in selected.geometry.vector)
        if len(row.vector) != V11_DIMENSION:
            raise ValueError("V38 V11 feature dimension drift")
        if len(extra) != M1_GEOMETRY_DIMENSION:
            raise ValueError("V38 native-M1 feature dimension drift")
        vector = (*row.vector, *extra)
        if len(vector) != FEATURE_DIMENSION:
            raise ValueError("V38 combined feature dimension drift")
        if any(not math.isfinite(value) for value in vector):
            raise ValueError("V38 combined vector contains non-finite value")
        result.append(replace(row, vector=vector))
    return tuple(result)


def build_report(
    development_root: Path,
    validation_root: Path,
    reserved_root: Path,
    development_validation_context_root: Path,
    reserved_context_root: Path,
    selected_geometry_root: Path,
) -> tuple[dict[str, Any], tuple[v37.LabeledEntryState, ...]]:
    windows, contextual_model = v13._load_windows(
        development_root,
        validation_root,
        reserved_root,
        development_validation_context_root,
        reserved_context_root,
    )

    simultaneous: dict[tuple[str, str, str], tuple[Any, ...]] = {}
    for period, (ledgers, _contexts) in windows.items():
        simultaneous.update(
            v11._simultaneous_map(period=period, ledgers=ledgers)
        )

    previous = dict(v11._SIMULTANEOUS)
    v11._SIMULTANEOUS.clear()
    v11._SIMULTANEOUS.update(simultaneous)
    try:
        base_states = {
            period: v37._surface_entry_states(
                period=period,
                ledgers=ledgers,
                contexts=contexts,
                contextual_model=contextual_model,
            )
            for period, (ledgers, contexts) in windows.items()
        }
    finally:
        v11._SIMULTANEOUS.clear()
        v11._SIMULTANEOUS.update(previous)

    slug_by_period = {
        "DEVELOPMENT_2024_2026": "development",
        "CONSUMED_VALIDATION_2022_2024": "validation",
        "CONSUMED_RESERVED_2020_2022": "reserved",
    }
    if set(base_states) != set(slug_by_period):
        raise ValueError("V38 period universe drift")

    states_by_period: dict[str, tuple[v37.LabeledEntryState, ...]] = {}
    for period, states in base_states.items():
        geometry_by_key = _load_period_geometry(
            selected_geometry_root,
            slug=slug_by_period[period],
        )
        # Coverage is checked against all selected entrants upstream. STOP/TARGET
        # states are a strict subset because flat/session exits are not labels.
        states_by_period[period] = _extend_states(states, geometry_by_key)

    models = {
        period: v25._fit_model(
            period=f"{period}:V38_NATIVE_M1_FULL_STOP_RISK",
            examples=v37._training_examples(states),
        )
        for period, states in states_by_period.items()
    }
    heldout = tuple(
        v37._heldout_report(
            heldout=period,
            states_by_period=states_by_period,
            models=models,
        )
        for period in states_by_period
    )
    representation_supported = all(
        row.both_external_auc_lower95_above_chance
        and row.consensus_auc_lower95_above_chance
        and row.target_count_preservation_at_least_90pct
        and row.risk_tail_enriched_above_base
        for row in heldout
    )

    all_states = tuple(
        row
        for period in states_by_period
        for row in states_by_period[period]
    )
    report = {
        "identity": IDENTITY,
        "evaluation": "PREENTRY_STOP_VS_TARGET_CAUSAL_SEPARABILITY",
        "feature_source": "V11_45D_PLUS_CURRENT_NATIVE_M1_GEOMETRY_12D",
        "v11_feature_dimension": V11_DIMENSION,
        "native_m1_geometry_dimension": M1_GEOMETRY_DIMENSION,
        "feature_dimension": FEATURE_DIMENSION,
        "training_label": "ORIGINAL_EXIT_REASON_STOP_VS_TARGET",
        "stop_target_labels_used_as_features": False,
        "current_outcome_visible_to_features": False,
        "future_exit_visible_to_features": False,
        "future_mfe_mae_visible_to_features": False,
        "symbol_identity_feature_used": False,
        "date_identity_feature_used": False,
        "two_external_worlds_required": True,
        "l2_prior_strength_effective_trades": str(
            v25.L2_PRIOR_STRENGTH
        ),
        "fixed_diagnostic_risk_quantile": str(v37.RISK_QUANTILE),
        "threshold_grid_searched": False,
        "policy_economics_run": False,
        "admission_changed": False,
        "sizing_changed": False,
        "protection_changed": False,
        "fresh_holdout_opened": False,
        "heldout_results": [asdict(row) for row in heldout],
        "representation_transport_supported": representation_supported,
        "candidate_count": 0,
        "runtime_policy_candidate": False,
        "trader_certified": False,
        "next_phase": (
            "PREDECLARE_WINNER_PRESERVING_CAUSAL_ABSTENTION_V39"
            if representation_supported
            else (
                "CURRENT_NATIVE_M1_GEOMETRY_REPRESENTATION_FALSIFIED_"
                "REQUIRE_RICHER_CAUSAL_INFORMATION"
            )
        ),
    }
    return report, all_states


def write_report(
    report: dict[str, Any],
    states: tuple[v37.LabeledEntryState, ...],
    output: Path,
) -> None:
    output.mkdir(parents=True, exist_ok=True)
    stem = "capitalizer-preentry-native-m1-geometry-separability-v38"
    (output / f"{stem}.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    with (output / f"{stem}-states.jsonl").open(
        "w",
        encoding="utf-8",
    ) as handle:
        for row in states:
            handle.write(json.dumps(asdict(row), sort_keys=True) + "\n")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("development_root", type=Path)
    parser.add_argument("validation_root", type=Path)
    parser.add_argument("reserved_root", type=Path)
    parser.add_argument("development_validation_context_root", type=Path)
    parser.add_argument("reserved_context_root", type=Path)
    parser.add_argument("selected_geometry_root", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()

    report, states = build_report(
        args.development_root,
        args.validation_root,
        args.reserved_root,
        args.development_validation_context_root,
        args.reserved_context_root,
        args.selected_geometry_root,
    )
    write_report(report, states, args.output)
    print(json.dumps(report, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
