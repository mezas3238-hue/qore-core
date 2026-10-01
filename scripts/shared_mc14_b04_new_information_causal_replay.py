#!/usr/bin/env python3
"""MC-14 replay using preregistered B04 cross-asset microstructure."""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Any

from shared_wp03_historical_causal_discovery import (
    MARKETS,
    PRE_WINDOW_MINUTES,
    TARGET_HORIZON_MINUTES,
    _load_bars,
    _parse_key,
    _regime,
    _source_state,
    _target_state,
)
from qore.infrastructure.core_stack_v2.dynamic_causal_graph import (
    CausalConcept,
)
from qore.infrastructure.core_stack_v2.mc14_b04_cross_asset_causal import (
    EXPECTED_WINDOW_COUNT,
    FROZEN_FEATURES,
    B04WindowFeatures,
    CausalMetricRow,
    CausalTargetRow,
    MINIMUM_EFFECT_BPS,
    MINIMUM_GROUP_COUNT,
    MINIMUM_STABILITY_BPS,
    extract_window_features,
    freeze_source_thresholds,
    partition_metrics,
)

IDENTITY = "QORE_SHARED_MC14_B04_NEW_INFORMATION_TEMPORAL_CAUSAL_REPLAY_001"
PREREGISTRATION = (
    "QORE_SHARED_MC14_B04_NEW_INFORMATION_TEMPORAL_CAUSAL_"
    "PREREGISTRATION_001"
)
IMPLEMENTATION_CONTRACT = (
    "QORE_SHARED_MC14_B04_REPLAY_IMPLEMENTATION_CONTRACT_001"
)
B04_RUN_ID = 36765098842
B04_GLOBAL_ARTIFACT_ID = 11129732922
B04_SHA = "aec788d073aedc31f609c1609af3f7d4d8e5ae30"

PARTITIONS = {
    "discovery": range(0, 1769),
    "validation": range(1769, 2359),
    "replication": range(2359, 2948),
}
FAMILIES = {
    "US2000_BREADTH_PROXY": (
        "H_BREADTH_LEADS_INDEX_REGIME_TRANSITION"
    ),
    "XAUUSD_DEFENSIVE_PROXY": (
        "H_DEFENSIVE_ROTATION_LEADS_INDEX_REGIME_TRANSITION"
    ),
}


def _bucket(value: float, low: float, high: float) -> str:
    if value < low:
        return "LOW"
    if value < high:
        return "MID"
    return "HIGH"


def _target_rows(
    *,
    evidence: dict[str, Path],
    source_times: dict[int, datetime],
) -> tuple[dict[int, CausalTargetRow], list[int]]:
    bars = {
        market: _load_bars(evidence[market])
        for market in MARKETS
    }
    indexes = {
        market: {
            _parse_key(bar.closed_key): index
            for index, bar in enumerate(rows)
        }
        for market, rows in bars.items()
    }
    rows: dict[int, CausalTargetRow] = {}
    missing: list[int] = []
    for window_index in range(EXPECTED_WINDOW_COUNT):
        source_at = source_times.get(window_index)
        if source_at is None:
            missing.append(window_index)
            continue

        market_indexes = {
            market: indexes[market].get(source_at)
            for market in MARKETS
        }
        if any(value is None for value in market_indexes.values()):
            missing.append(window_index)
            continue

        pre: dict[str, tuple[Any, ...]] = {}
        future: dict[str, tuple[Any, ...]] = {}
        valid = True
        for market in MARKETS:
            raw_index = market_indexes[market]
            if raw_index is None:
                valid = False
                break
            index = raw_index
            if (
                index < PRE_WINDOW_MINUTES - 1
                or index + TARGET_HORIZON_MINUTES
                >= len(bars[market])
            ):
                valid = False
                break
            pre[market] = tuple(
                bars[market][
                    index - PRE_WINDOW_MINUTES + 1 : index + 1
                ]
            )
            future[market] = tuple(
                bars[market][
                    index + 1 : index + 1 + TARGET_HORIZON_MINUTES
                ]
            )
            if (
                len(pre[market]) != PRE_WINDOW_MINUTES
                or len(future[market]) != TARGET_HORIZON_MINUTES
            ):
                valid = False
                break
        if not valid:
            missing.append(window_index)
            continue

        source_states, vol_ratio, coherence60 = _source_state(pre)
        target_states = _target_state(pre, future)
        hour = source_at.hour
        tod = (
            "Q0"
            if hour < 6
            else "Q1"
            if hour < 12
            else "Q2"
            if hour < 18
            else "Q3"
        )
        confounder = (
            f"VOL_{_bucket(vol_ratio, 0.75, 1.25)}"
            f"|COH_{_bucket(coherence60, 0.34, 0.67)}"
            f"|TOD_{tod}"
        )
        target_bps = max(
            target_states[CausalConcept.REVERSAL],
            target_states[CausalConcept.STRUCTURAL_FAILURE],
            target_states[CausalConcept.ANOMALY],
        )
        rows[window_index] = {
            "source_at": source_at.isoformat(),
            "target_bps": target_bps,
            "confounder_key": confounder,
            "regime_key": _regime(source_states),
        }
    return rows, missing


def _evaluate_family(
    *,
    family: str,
    feature_rows: tuple[B04WindowFeatures, ...],
    target_rows: dict[int, CausalTargetRow],
) -> dict[str, object]:
    complete = [row for row in feature_rows if row.complete]
    missing_feature_windows = [
        row.window_index
        for row in feature_rows
        if not row.complete
    ]
    target_missing = [
        index
        for index in range(EXPECTED_WINDOW_COUNT)
        if index not in target_rows
    ]
    if missing_feature_windows or target_missing:
        return {
            "family": family,
            "hypothesis_id": FAMILIES[family],
            "status": "INSUFFICIENT_DO_NOT_INFER",
            "complete_feature_window_count": len(complete),
            "missing_feature_window_count": len(
                missing_feature_windows
            ),
            "missing_feature_window_indices": (
                missing_feature_windows
            ),
            "missing_target_window_count": len(target_missing),
            "missing_target_window_indices": target_missing,
            "relations": [],
        }

    by_index = {
        row.window_index: row
        for row in feature_rows
    }
    relations: list[dict[str, Any]] = []
    replicated: list[dict[str, Any]] = []
    discovery_candidates = 0
    validation_passes = 0

    insufficient_features = 0
    falsified_features = 0

    for feature in FROZEN_FEATURES:
        discovery_values = [
            by_index[index].feature(feature)
            for index in PARTITIONS["discovery"]
        ]
        try:
            low, high = freeze_source_thresholds(discovery_values)
        except ValueError as exc:
            insufficient_features += 1
            relations.append(
                {
                    "feature": feature,
                    "status": "INSUFFICIENT_SOURCE_DIVERSITY",
                    "reason": str(exc),
                    "source_threshold_low": None,
                    "source_threshold_high": None,
                    "discovery": None,
                    "validation": None,
                    "replication": None,
                    "discovery_candidate": False,
                    "validation_same_sign_pass": False,
                    "replication_same_sign_pass": False,
                }
            )
            continue

        discovery_rows: list[CausalMetricRow] = [
            {
                "source": by_index[index].feature(feature),
                "target_bps": target_rows[index]["target_bps"],
                "confounder_key": target_rows[index]["confounder_key"],
                "regime_key": target_rows[index]["regime_key"],
            }
            for index in PARTITIONS["discovery"]
        ]
        discovery = partition_metrics(
            discovery_rows,
            low=low,
            high=high,
        )
        if bool(discovery["insufficient"]):
            insufficient_features += 1
            relations.append(
                {
                    "feature": feature,
                    "status": "INSUFFICIENT_DISCOVERY_GROUP_COUNT",
                    "reason": discovery["insufficient_reason"],
                    "source_threshold_low": low,
                    "source_threshold_high": high,
                    "discovery": discovery,
                    "validation": None,
                    "replication": None,
                    "discovery_candidate": False,
                    "validation_same_sign_pass": False,
                    "replication_same_sign_pass": False,
                }
            )
            continue

        discovery_pass = bool(discovery["material_same_sign"])
        if not discovery_pass:
            falsified_features += 1
            relations.append(
                {
                    "feature": feature,
                    "status": "FALSIFIED_AT_DISCOVERY",
                    "reason": "NO_DISCOVERY_CANDIDATE",
                    "source_threshold_low": low,
                    "source_threshold_high": high,
                    "discovery": discovery,
                    "validation": None,
                    "replication": None,
                    "discovery_candidate": False,
                    "validation_same_sign_pass": False,
                    "replication_same_sign_pass": False,
                }
            )
            continue

        discovery_candidates += 1
        effect_value = discovery["effect_bps"]
        if effect_value is None:
            raise AssertionError("material discovery lost effect")
        reference_sign = (
            1 if effect_value > 0 else -1 if effect_value < 0 else 0
        )

        validation_rows: list[CausalMetricRow] = [
            {
                "source": by_index[index].feature(feature),
                "target_bps": target_rows[index]["target_bps"],
                "confounder_key": target_rows[index]["confounder_key"],
                "regime_key": target_rows[index]["regime_key"],
            }
            for index in PARTITIONS["validation"]
        ]
        validation = partition_metrics(
            validation_rows,
            low=low,
            high=high,
            reference_sign=reference_sign,
        )
        if bool(validation["insufficient"]):
            insufficient_features += 1
            relations.append(
                {
                    "feature": feature,
                    "status": "INSUFFICIENT_VALIDATION_GROUP_COUNT",
                    "reason": validation["insufficient_reason"],
                    "source_threshold_low": low,
                    "source_threshold_high": high,
                    "discovery": discovery,
                    "validation": validation,
                    "replication": None,
                    "discovery_candidate": True,
                    "validation_same_sign_pass": False,
                    "replication_same_sign_pass": False,
                }
            )
            continue

        validation_pass = bool(validation["material_same_sign"])
        if not validation_pass:
            falsified_features += 1
            relations.append(
                {
                    "feature": feature,
                    "status": "FALSIFIED_AT_VALIDATION",
                    "reason": "VALIDATION_FAILURE",
                    "source_threshold_low": low,
                    "source_threshold_high": high,
                    "discovery": discovery,
                    "validation": validation,
                    "replication": None,
                    "discovery_candidate": True,
                    "validation_same_sign_pass": False,
                    "replication_same_sign_pass": False,
                }
            )
            continue

        validation_passes += 1
        replication_rows: list[CausalMetricRow] = [
            {
                "source": by_index[index].feature(feature),
                "target_bps": target_rows[index]["target_bps"],
                "confounder_key": target_rows[index]["confounder_key"],
                "regime_key": target_rows[index]["regime_key"],
            }
            for index in PARTITIONS["replication"]
        ]
        replication = partition_metrics(
            replication_rows,
            low=low,
            high=high,
            reference_sign=reference_sign,
        )
        if bool(replication["insufficient"]):
            insufficient_features += 1
            relations.append(
                {
                    "feature": feature,
                    "status": "INSUFFICIENT_REPLICATION_GROUP_COUNT",
                    "reason": replication["insufficient_reason"],
                    "source_threshold_low": low,
                    "source_threshold_high": high,
                    "discovery": discovery,
                    "validation": validation,
                    "replication": replication,
                    "discovery_candidate": True,
                    "validation_same_sign_pass": True,
                    "replication_same_sign_pass": False,
                }
            )
            continue

        replication_pass = bool(replication["material_same_sign"])
        relation = {
            "feature": feature,
            "status": (
                "TEMPORALLY_REPLICATED_RESEARCH_RELATION"
                if replication_pass
                else "FALSIFIED_AT_REPLICATION"
            ),
            "reason": (
                "DISCOVERY_VALIDATION_REPLICATION_PASS"
                if replication_pass
                else "REPLICATION_FAILURE"
            ),
            "source_threshold_low": low,
            "source_threshold_high": high,
            "discovery": discovery,
            "validation": validation,
            "replication": replication,
            "discovery_candidate": True,
            "validation_same_sign_pass": True,
            "replication_same_sign_pass": replication_pass,
        }
        relations.append(relation)
        if replication_pass:
            replicated.append(relation)
        else:
            falsified_features += 1

    if replicated:
        status = "TEMPORALLY_REPLICATED_RESEARCH_RELATION_FOUND"
        reason = (
            "FROZEN_RELATION_PASSED_"
            "DISCOVERY_VALIDATION_REPLICATION"
        )
    elif insufficient_features:
        status = "INSUFFICIENT_DO_NOT_INFER"
        reason = "ONE_OR_MORE_FROZEN_FEATURES_NOT_COMPARABLY_EVALUABLE"
    elif discovery_candidates == 0:
        status = "FALSIFIED_AND_CLOSED_FOR_THIS_MECHANISM"
        reason = "NO_DISCOVERY_CANDIDATE"
    elif validation_passes == 0:
        status = "FALSIFIED_AND_CLOSED_FOR_THIS_MECHANISM"
        reason = "VALIDATION_FAILURE"
    else:
        status = "FALSIFIED_AND_CLOSED_FOR_THIS_MECHANISM"
        reason = "REPLICATION_FAILURE"

    return {
        "family": family,
        "hypothesis_id": FAMILIES[family],
        "status": status,
        "reason": reason,
        "complete_feature_window_count": len(complete),
        "missing_feature_window_count": 0,
        "missing_target_window_count": 0,
        "discovery_candidate_count": discovery_candidates,
        "validation_pass_count": validation_passes,
        "replicated_relation_count": len(replicated),
        "insufficient_feature_count": insufficient_features,
        "falsified_feature_count": falsified_features,
        "relations": relations,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--us2000-root", type=Path, required=True)
    parser.add_argument("--xauusd-root", type=Path, required=True)
    parser.add_argument("--r8-nas", type=Path, required=True)
    parser.add_argument("--r8-sp", type=Path, required=True)
    parser.add_argument("--r8-us", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    features = {
        "US2000_BREADTH_PROXY": extract_window_features(
            root=args.us2000_root
        ),
        "XAUUSD_DEFENSIVE_PROXY": extract_window_features(
            root=args.xauusd_root
        ),
    }
    source_times: dict[int, datetime] = {}
    source_time_mismatches = []
    for index in range(EXPECTED_WINDOW_COUNT):
        candidates = {
            rows[index].source_at
            for rows in features.values()
            if rows[index].source_at.year > 1
        }
        if len(candidates) == 1:
            source_times[index] = next(iter(candidates))
        elif len(candidates) > 1:
            source_time_mismatches.append(index)

    target_rows, missing_target_windows = _target_rows(
        evidence={
            "NAS100": args.r8_nas,
            "SP500": args.r8_sp,
            "US30": args.r8_us,
        },
        source_times=source_times,
    )
    family_results = {
        family: _evaluate_family(
            family=family,
            feature_rows=rows,
            target_rows=target_rows,
        )
        for family, rows in features.items()
    }
    replicated = sum(
        int(
            result["status"]
            == "TEMPORALLY_REPLICATED_RESEARCH_RELATION_FOUND"
        )
        for result in family_results.values()
    )
    insufficient = sum(
        int(result["status"] == "INSUFFICIENT_DO_NOT_INFER")
        for result in family_results.values()
    )
    falsified = sum(
        int(
            result["status"]
            == "FALSIFIED_AND_CLOSED_FOR_THIS_MECHANISM"
        )
        for result in family_results.values()
    )

    payload = {
        "identity": IDENTITY,
        "preregistration_identity": PREREGISTRATION,
        "implementation_contract_identity": IMPLEMENTATION_CONTRACT,
        "b04_run_id": B04_RUN_ID,
        "b04_global_artifact_id": B04_GLOBAL_ARTIFACT_ID,
        "b04_git_sha": B04_SHA,
        "frozen_feature_names": list(FROZEN_FEATURES),
        "frozen_temporal_partitions": {
            name: {
                "start_index": values.start,
                "end_index_inclusive": values.stop - 1,
                "count": len(values),
            }
            for name, values in PARTITIONS.items()
        },
        "frozen_gates": {
            "minimum_effect_bps": MINIMUM_EFFECT_BPS,
            "minimum_group_count": MINIMUM_GROUP_COUNT,
            "minimum_stability_bps": MINIMUM_STABILITY_BPS,
        },
        "source_cutoff_rule": (
            "MAX_REQUEST_TO_AT_MINUS_15_MINUTES"
        ),
        "post_source_ticks_used_in_features": False,
        "future_market_used_in_feature_construction": False,
        "future_market_used_offline_for_research_evaluation": True,
        "trade_pnl_used": False,
        "r6_r5_read": False,
        "protected_certification_holdout_opened": False,
        "source_time_mismatch_count": len(
            source_time_mismatches
        ),
        "source_time_mismatch_indices": source_time_mismatches,
        "missing_target_window_count": len(
            missing_target_windows
        ),
        "family_results": family_results,
        "replicated_family_count": replicated,
        "insufficient_family_count": insufficient,
        "falsified_family_count": falsified,
        "mc14_completed_and_proven": False,
        "knowledge_auto_promotion": False,
        "shared_methodology_authority": False,
        "shared_sizing_authority": False,
        "shared_risk_authority": False,
        "shared_order_authority": False,
        "shared_execution_authority": False,
        "productive_authority": False,
        "next_gate": (
            "INDEPENDENT_GOVERNED_CONFIRMATION_OF_REPLICATED_RELATION"
            if replicated
            else "NEW_INFORMATION_OR_REPRESENTATION_REQUIRED"
            if falsified and not insufficient
            else "RESOLVE_NONCOMPARABLE_SOURCE_COVERAGE"
        ),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, sort_keys=True, indent=2) + "\n"
    )
    print(
        json.dumps(
            {
                "identity": IDENTITY,
                "replicated_family_count": replicated,
                "insufficient_family_count": insufficient,
                "falsified_family_count": falsified,
                "next_gate": payload["next_gate"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
