"""Run the preregistered WP-05 V12 R8 information-gain experiment."""

from __future__ import annotations

import argparse
import hashlib
import json
from dataclasses import asdict
from datetime import UTC
from pathlib import Path
from typing import Any, cast

from shared_wp05_sequential_changepoint_v10 import _prepare_partition

from qore.infrastructure.core_stack_v2.active_perception_v12_information_gain import (
    INFORMATION_GAIN_IDENTITY,
    MICROSTRUCTURE_VETO_THRESHOLD_MICROS,
    evaluate_v12_information_gain_fold,
    fit_v12_microstructure_density,
    score_v12_microstructure_micros,
    select_v12_information_gain_candidate,
    summarize_v12_candidate_information_gain,
    v12_microstructure_density_fingerprint,
)
from qore.infrastructure.core_stack_v2.active_perception_v12_microstructure_representation import (
    REPRESENTATION_IDENTITY,
    v12_microstructure_candidate_fields,
)
from qore.infrastructure.core_stack_v2.temporal_hierarchy_mechanism_confirmation_v11 import (
    assess_v11_episode,
    fit_v11_mechanism_confirmation_model,
    v11_model_fingerprint,
    v11_representation_fingerprint,
)

TARGET_CONTRACT = "HIGHER_TIMEFRAME_STRUCTURAL_FAILURE_V2"
EXPECTED_REPRESENTATION_ARTIFACT_FINGERPRINT = (
    "cbc5b6d997c2a218df8aa76f489d408069ab36e4ccb67569172c92013221baf8"
)
EXPECTED_REPRESENTATION_CONTRACT_FINGERPRINT = (
    "22c566501246030218be3d33ba54c3b6cc1574507357248e3baf0fcf6e47277b"
)
EXPECTED_REPRESENTATION_ROWS_SHA256 = (
    "be2ee22e02c4e3ef6a1c82fd9536dfc51a6050fbfb127d0b53b7764d70388395"
)
EXPECTED_V11_MODEL_FINGERPRINT = (
    "cc74f7d3153dec34ebe8867efc27852ca8d5de95d471394f3d8ac9543147b01d"
)
EXPECTED_V11_REPRESENTATION_FINGERPRINT = (
    "1f1f2bd97e2f3541c7e37aca5571717a9908618ad1be2b4fce57cb9a09970ce8"
)
EXPECTED_ALIGNED_R8_COUNT = 6534


class V12InformationGainError(RuntimeError):
    """The frozen V12 R8 information-gain protocol failed closed."""


def _load_representation(path: Path) -> tuple[dict[str, dict[str, object]], int]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise V12InformationGainError("representation artifact must be JSON object")
    payload = cast(dict[str, Any], raw)
    if payload.get("identity") != REPRESENTATION_IDENTITY:
        raise V12InformationGainError("representation identity mismatch")
    if payload.get("status") != "source_only_frozen":
        raise V12InformationGainError("representation is not source-only frozen")
    if payload.get("representation_artifact_fingerprint_sha256") != (
        EXPECTED_REPRESENTATION_ARTIFACT_FINGERPRINT
    ):
        raise V12InformationGainError("representation artifact fingerprint drift")
    if payload.get("contract_fingerprint_sha256") != (
        EXPECTED_REPRESENTATION_CONTRACT_FINGERPRINT
    ):
        raise V12InformationGainError("representation contract fingerprint drift")
    if payload.get("rows_sha256") != EXPECTED_REPRESENTATION_ROWS_SHA256:
        raise V12InformationGainError("representation rows digest drift")
    if payload.get("target_or_outcome_read") is not False:
        raise V12InformationGainError("source-only representation read target/outcome")
    if payload.get("r6_r5_read") is not False:
        raise V12InformationGainError("source-only representation read R6/R5")
    if payload.get("fresh_holdout_opened") is not False:
        raise V12InformationGainError("source-only representation opened holdout")

    raw_rows = payload.get("rows")
    if not isinstance(raw_rows, list) or len(raw_rows) != 6804:
        raise V12InformationGainError("representation row population drift")
    by_time: dict[str, dict[str, object]] = {}
    for raw_row in raw_rows:
        if not isinstance(raw_row, dict):
            raise V12InformationGainError("representation row must be object")
        row = cast(dict[str, object], raw_row)
        evaluation_at = row.get("evaluation_at")
        if not isinstance(evaluation_at, str):
            raise V12InformationGainError("representation row lacks evaluation timestamp")
        if evaluation_at in by_time:
            raise V12InformationGainError("duplicate representation evaluation timestamp")
        by_time[evaluation_at] = row
    return by_time, len(raw_rows)


def _source_key(episode: Any) -> str:
    value = episode.checkpoints[0].as_of
    if value.tzinfo is None or value.utcoffset() is None:
        raise V12InformationGainError("V11 source timestamp must be timezone-aware")
    return value.astimezone(UTC).isoformat(timespec="microseconds")


def _strict_training_prefix(
    aligned: tuple[tuple[Any, dict[str, object]], ...],
    *,
    validation_start: int,
) -> tuple[tuple[Any, dict[str, object]], ...]:
    validation_source_min = aligned[validation_start][0].checkpoints[0].as_of
    training = tuple(
        item
        for item in aligned[:validation_start]
        if item[0].observed_at < validation_source_min
    )
    if len(training) < 100:
        raise V12InformationGainError(
            "chronological purge left insufficient V12 fold training evidence"
        )
    return training


def _final_model_fingerprint(
    *,
    selected_candidate: str,
    density_fingerprint: str,
) -> str:
    payload = {
        "identity": INFORMATION_GAIN_IDENTITY,
        "target_contract": TARGET_CONTRACT,
        "selected_candidate": selected_candidate,
        "v11_model_fingerprint": EXPECTED_V11_MODEL_FINGERPRINT,
        "v11_representation_fingerprint": EXPECTED_V11_REPRESENTATION_FINGERPRINT,
        "representation_artifact_fingerprint": (
            EXPECTED_REPRESENTATION_ARTIFACT_FINGERPRINT
        ),
        "microstructure_density_fingerprint": density_fingerprint,
        "microstructure_veto_threshold_micros": (
            MICROSTRUCTURE_VETO_THRESHOLD_MICROS
        ),
        "decision": "V11_CONFIRMED_AND_MICRO_LLR_GTE_ZERO",
        "r6_r5_read": False,
        "fresh_holdout_opened": False,
    }
    return hashlib.sha256(
        json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        ).encode("utf-8")
    ).hexdigest()


def run(
    *,
    representation_path: Path,
    evidence_paths: dict[str, Path],
) -> dict[str, object]:
    rows_by_time, representation_row_count = _load_representation(
        representation_path
    )
    episodes, partition_range = _prepare_partition(
        partition="r8",
        evidence_paths=evidence_paths,
    )
    if partition_range.get("target_contract") != TARGET_CONTRACT:
        raise V12InformationGainError("R8 target contract drift")
    if partition_range.get("fresh_holdout_opened") != 0:
        raise V12InformationGainError("R8 preparation opened fresh holdout")

    ordered_episodes = tuple(
        sorted(episodes, key=lambda item: item.checkpoints[0].as_of)
    )
    aligned_list: list[tuple[Any, dict[str, object]]] = []
    used_times: set[str] = set()
    for episode in ordered_episodes:
        key = _source_key(episode)
        row = rows_by_time.get(key)
        if row is None:
            raise V12InformationGainError(
                "Target-V2 episode lacks exact frozen representation row"
            )
        aligned_list.append((episode, row))
        used_times.add(key)
    aligned = tuple(aligned_list)
    if len(aligned) != EXPECTED_ALIGNED_R8_COUNT:
        raise V12InformationGainError("aligned R8 population drift")

    full_v11 = fit_v11_mechanism_confirmation_model(
        fitted_at=max(item.observed_at for item, _row in aligned),
        fit_partition="r8",
        episodes=tuple(item for item, _row in aligned),
    )
    full_v11_fingerprint = v11_model_fingerprint(full_v11)
    if full_v11_fingerprint != EXPECTED_V11_MODEL_FINGERPRINT:
        raise V12InformationGainError("authoritative V11 model fingerprint drift")
    if v11_representation_fingerprint() != (
        EXPECTED_V11_REPRESENTATION_FINGERPRINT
    ):
        raise V12InformationGainError("authoritative V11 representation drift")

    n = len(aligned)
    boundaries = tuple(n * index // 5 for index in range(6))
    candidate_results = []
    fold_boundaries: list[dict[str, object]] = []

    for candidate in v12_microstructure_candidate_fields():
        folds = []
        for fold_index in range(4):
            validation_start = boundaries[fold_index + 1]
            validation_end = boundaries[fold_index + 2]
            validation = aligned[validation_start:validation_end]
            training = _strict_training_prefix(
                aligned,
                validation_start=validation_start,
            )
            validation_source_min = validation[0][0].checkpoints[0].as_of
            training_observed_max = max(
                item.observed_at for item, _row in training
            )
            if training_observed_max >= validation_source_min:
                raise V12InformationGainError(
                    "V12 fold maturity purge boundary is not strict"
                )

            train_episodes = tuple(item for item, _row in training)
            fold_v11 = fit_v11_mechanism_confirmation_model(
                fitted_at=max(item.observed_at for item in train_episodes),
                fit_partition="r8",
                episodes=train_episodes,
            )
            micro = fit_v12_microstructure_density(
                candidate=candidate,
                rows=tuple(row for _item, row in training),
                labels=tuple(bool(item.terminal_failure) for item, _row in training),
            )
            labels = tuple(
                bool(item.terminal_failure) for item, _row in validation
            )
            baseline_declared = tuple(
                assess_v11_episode(
                    model=fold_v11,
                    episode=item,
                ).first_confirmation_minute
                is not None
                for item, _row in validation
            )
            scores = tuple(
                score_v12_microstructure_micros(micro, row)
                for _item, row in validation
            )
            folds.append(
                evaluate_v12_information_gain_fold(
                    fold_index=fold_index,
                    labels=labels,
                    baseline_declared=baseline_declared,
                    microstructure_scores_micros=scores,
                )
            )
            if candidate == "M0_QUOTE_STATE":
                fold_boundaries.append(
                    {
                        "fold_index": fold_index,
                        "training_count_after_maturity_purge": len(training),
                        "validation_count": len(validation),
                        "training_observed_max": training_observed_max.astimezone(
                            UTC
                        ).isoformat(timespec="microseconds"),
                        "validation_source_min": validation_source_min.astimezone(
                            UTC
                        ).isoformat(timespec="microseconds"),
                        "validation_source_max": validation[-1][
                            0
                        ].checkpoints[0].as_of.astimezone(UTC).isoformat(
                            timespec="microseconds"
                        ),
                    }
                )

        candidate_results.append(
            summarize_v12_candidate_information_gain(
                candidate=candidate,
                folds=tuple(folds),
            )
        )

    selected = select_v12_information_gain_candidate(candidate_results)
    result: dict[str, object] = {
        "schema": "qore.shared.wp05.active_perception.v12.r8_information_gain.v1",
        "identity": INFORMATION_GAIN_IDENTITY,
        "target_contract": TARGET_CONTRACT,
        "representation_artifact_fingerprint_sha256": (
            EXPECTED_REPRESENTATION_ARTIFACT_FINGERPRINT
        ),
        "representation_row_count": representation_row_count,
        "aligned_target_count": len(aligned),
        "representation_only_anchor_count": representation_row_count - len(used_times),
        "v11_model_fingerprint_sha256": full_v11_fingerprint,
        "v11_representation_fingerprint_sha256": (
            EXPECTED_V11_REPRESENTATION_FINGERPRINT
        ),
        "fold_boundaries": fold_boundaries,
        "candidate_results": [asdict(item) for item in candidate_results],
        "selected_candidate": selected,
        "microstructure_veto_threshold_micros": (
            MICROSTRUCTURE_VETO_THRESHOLD_MICROS
        ),
        "protocol_pass": True,
        "r6_r5_read": False,
        "fresh_holdout_opened": False,
        "shared_methodology_authority": False,
        "shared_sizing_authority": False,
        "shared_risk_authority": False,
        "shared_order_authority": False,
        "shared_execution_authority": False,
    }

    if selected is None:
        result.update(
            {
                "status": "WP05_V12_R8_INFORMATION_GAIN_FALSIFIED",
                "r8_information_gain_pass": False,
                "reason": "NO_PREREGISTERED_M0_M3_CANDIDATE_PASSED",
            }
        )
        return result

    final_density = fit_v12_microstructure_density(
        candidate=selected,
        rows=tuple(row for _item, row in aligned),
        labels=tuple(bool(item.terminal_failure) for item, _row in aligned),
    )
    density_fingerprint = v12_microstructure_density_fingerprint(final_density)
    result.update(
        {
            "status": "WP05_V12_R8_INFORMATION_GAIN_FROZEN",
            "r8_information_gain_pass": True,
            "final_microstructure_density": asdict(final_density),
            "final_microstructure_density_fingerprint_sha256": density_fingerprint,
            "final_v12_model_fingerprint_sha256": _final_model_fingerprint(
                selected_candidate=selected,
                density_fingerprint=density_fingerprint,
            ),
            "next_authorized_step": (
                "R6_R5_SOURCE_ONLY_SENSOR_ACQUISITION_WITH_OUTCOMES_CLOSED"
            ),
        }
    )
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--representation", type=Path, required=True)
    parser.add_argument("--r8-nas", type=Path, required=True)
    parser.add_argument("--r8-sp", type=Path, required=True)
    parser.add_argument("--r8-us", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    payload = run(
        representation_path=args.representation,
        evidence_paths={
            "NAS100": args.r8_nas,
            "SP500": args.r8_sp,
            "US30": args.r8_us,
        },
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "status": payload["status"],
                "protocol_pass": payload["protocol_pass"],
                "aligned_target_count": payload["aligned_target_count"],
                "selected_candidate": payload["selected_candidate"],
                "candidate_results": payload["candidate_results"],
                "final_v12_model_fingerprint_sha256": payload.get(
                    "final_v12_model_fingerprint_sha256"
                ),
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
