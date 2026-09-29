"""Run preregistered WP-05 V14 cross-market microstructure information gain."""

from __future__ import annotations

import argparse
import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, cast

from shared_wp05_sequential_changepoint_v10 import _prepare_partition

from qore.infrastructure.core_stack_v2.active_perception_v14_information_gain import (
    V14_CALIBRATION_TRUE_CONFIRMATION_RETENTION_BPS,
    V14_DISCOVERY_FRACTION_BPS,
    V14_INFORMATION_GAIN_IDENTITY,
    V14_POOLED_INCREMENTAL_FALSE_VETO_BPS,
    V14FoldEvaluation,
    V14PeerCheckpointDensity,
    evaluate_v14_fold,
    fit_v14_peer_checkpoint_density,
    peer_confirmation_score_micros,
    pooled_v14_false_veto_bps,
    select_v14_peer_confirmation_threshold_micros,
    v14_density_set_fingerprint,
)
from qore.infrastructure.core_stack_v2.active_perception_v14_observability import (
    V14_CHECKPOINTS_MINUTES,
)
from qore.infrastructure.core_stack_v2.active_perception_v14_peer_acquisition import (
    V14PeerFamily,
)
from qore.infrastructure.core_stack_v2.active_perception_v14_representation import (
    V14_REPRESENTATION_IDENTITY,
)
from qore.infrastructure.core_stack_v2.temporal_hierarchy_mechanism_confirmation_v11 import (
    V11MechanismConfirmationModel,
    assess_v11_episode,
    fit_v11_mechanism_confirmation_model,
    v11_model_fingerprint,
    v11_representation_fingerprint,
)

TARGET_CONTRACT = "HIGHER_TIMEFRAME_STRUCTURAL_FAILURE_V2"
EXPECTED_ALIGNED_R8_COUNT = 6397
EXPECTED_V11_MODEL_FINGERPRINT = (
    "cc74f7d3153dec34ebe8867efc27852ca8d5de95d471394f3d8ac9543147b01d"
)
EXPECTED_V11_REPRESENTATION_FINGERPRINT = (
    "1f1f2bd97e2f3541c7e37aca5571717a9908618ad1be2b4fce57cb9a09970ce8"
)
MIN_CALIBRATION_TRUE_CONFIRMATIONS = 50


class V14InformationGainError(RuntimeError):
    """V14 scientific protocol failed closed."""


@dataclass(frozen=True, slots=True)
class _AlignedEpisode:
    episode: Any
    row: dict[str, object]

    @property
    def source_at(self) -> datetime:
        return cast(datetime, self.episode.checkpoints[0].as_of)

    @property
    def observed_at(self) -> datetime:
        return cast(datetime, self.episode.observed_at)

    @property
    def label(self) -> bool:
        return bool(self.episode.terminal_failure)


@dataclass(frozen=True, slots=True)
class _FittedFoldModel:
    v11: V11MechanismConfirmationModel
    densities: tuple[V14PeerCheckpointDensity, ...]
    peer_confirmation_threshold_micros: int
    calibration_true_confirmation_count: int
    calibration_true_confirmation_retention_bps: int
    discovery_count: int
    calibration_count: int
    purged_discovery_count: int
    discovery_observed_max: datetime
    calibration_source_min: datetime


def _utc(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise V14InformationGainError("V14 timestamps must be timezone-aware")
    return value.astimezone(UTC)


def _source_key(episode: Any) -> str:
    return _utc(episode.checkpoints[0].as_of).isoformat(timespec="microseconds")


def _load_representation(
    path: Path,
    *,
    expected_fingerprint: str,
) -> dict[str, dict[str, object]]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise V14InformationGainError("V14 representation must be JSON object")
    payload = cast(dict[str, Any], raw)
    if payload.get("identity") != V14_REPRESENTATION_IDENTITY:
        raise V14InformationGainError("V14 representation identity mismatch")
    if payload.get("status") != "source_only_frozen":
        raise V14InformationGainError("V14 representation is not frozen")
    if payload.get("representation_artifact_fingerprint_sha256") != expected_fingerprint:
        raise V14InformationGainError("V14 representation fingerprint drift")
    if payload.get("row_count") != 6804:
        raise V14InformationGainError("V14 representation population drift")
    if payload.get("checkpoints_minutes") != [0, 3, 5, 10, 15]:
        raise V14InformationGainError("V14 checkpoint schedule drift")
    if payload.get("raw_feature_cell_count") != 460:
        raise V14InformationGainError("V14 representation width drift")
    for key in (
        "target_or_outcome_read",
        "r6_r5_read",
        "fresh_holdout_opened",
        "scientific_v14_outcomes_opened",
    ):
        if payload.get(key) is not False:
            raise V14InformationGainError(f"V14 source representation violation: {key}")
    rows = payload.get("rows")
    if not isinstance(rows, list) or len(rows) != 6804:
        raise V14InformationGainError("V14 representation rows missing")
    by_source: dict[str, dict[str, object]] = {}
    for raw_row in rows:
        if not isinstance(raw_row, dict):
            raise V14InformationGainError("V14 representation row must be object")
        row = cast(dict[str, object], raw_row)
        source_at = row.get("source_at")
        if not isinstance(source_at, str):
            raise V14InformationGainError("V14 row lacks source timestamp")
        if source_at in by_source:
            raise V14InformationGainError("duplicate V14 source timestamp")
        by_source[source_at] = row
    return by_source


def _align(
    *,
    episodes: tuple[Any, ...],
    rows_by_source: dict[str, dict[str, object]],
) -> tuple[_AlignedEpisode, ...]:
    ordered = tuple(sorted(episodes, key=lambda item: item.checkpoints[0].as_of))
    aligned: list[_AlignedEpisode] = []
    for episode in ordered:
        row = rows_by_source.get(_source_key(episode))
        if row is None:
            raise V14InformationGainError(
                "authoritative V11 episode lacks V14 peer row"
            )
        aligned.append(_AlignedEpisode(episode=episode, row=row))
    if len(aligned) != EXPECTED_ALIGNED_R8_COUNT:
        raise V14InformationGainError("V14 aligned R8 population drift")
    return tuple(aligned)


def _outer_training_prefix(
    aligned: tuple[_AlignedEpisode, ...],
    *,
    validation_start: int,
) -> tuple[_AlignedEpisode, ...]:
    validation_source_min = aligned[validation_start].source_at
    training = tuple(
        item
        for item in aligned[:validation_start]
        if item.observed_at < validation_source_min
    )
    if len(training) < 300:
        raise V14InformationGainError("V14 outer purge leaves insufficient training")
    return training


def _inner_discovery_calibration(
    training: tuple[_AlignedEpisode, ...],
) -> tuple[
    tuple[_AlignedEpisode, ...],
    tuple[_AlignedEpisode, ...],
    int,
    datetime,
    datetime,
]:
    split = len(training) * V14_DISCOVERY_FRACTION_BPS // 10_000
    if split < 100 or len(training) - split < 50:
        raise V14InformationGainError("V14 inner split lacks evidence")
    raw_discovery = training[:split]
    calibration = training[split:]
    calibration_source_min = _utc(calibration[0].source_at)
    discovery = tuple(
        item
        for item in raw_discovery
        if _utc(item.observed_at) < calibration_source_min
    )
    purged = len(raw_discovery) - len(discovery)
    if len(discovery) < 100:
        raise V14InformationGainError("V14 maturity purge leaves insufficient discovery")
    discovery_observed_max = max(_utc(item.observed_at) for item in discovery)
    if discovery_observed_max >= calibration_source_min:
        raise V14InformationGainError("V14 inner maturity purge is not strict")
    return (
        discovery,
        calibration,
        purged,
        discovery_observed_max,
        calibration_source_min,
    )


def _baseline_confirmation_minute(
    *,
    model: V11MechanismConfirmationModel,
    episode: Any,
) -> int | None:
    return assess_v11_episode(model=model, episode=episode).first_confirmation_minute


def _fit_fold_model(
    training: tuple[_AlignedEpisode, ...],
) -> _FittedFoldModel:
    train_episodes = tuple(item.episode for item in training)
    v11 = fit_v11_mechanism_confirmation_model(
        fitted_at=max(item.observed_at for item in train_episodes),
        fit_partition="r8",
        episodes=train_episodes,
    )
    (
        discovery,
        calibration,
        purged,
        discovery_observed_max,
        calibration_source_min,
    ) = _inner_discovery_calibration(training)

    if _utc(v11.discovery_observed_max) != discovery_observed_max:
        raise V14InformationGainError("V14 discovery boundary diverged from V11")
    if _utc(v11.calibration_source_min) != calibration_source_min:
        raise V14InformationGainError("V14 calibration boundary diverged from V11")

    discovery_rows = tuple(item.row for item in discovery)
    discovery_labels = tuple(item.label for item in discovery)
    densities = tuple(
        fit_v14_peer_checkpoint_density(
            peer=peer,
            checkpoint_minutes=minute,
            rows=discovery_rows,
            labels=discovery_labels,
        )
        for peer in V14PeerFamily
        for minute in V14_CHECKPOINTS_MINUTES
    )

    true_scores: list[int] = []
    for item in calibration:
        confirmation = _baseline_confirmation_minute(
            model=v11,
            episode=item.episode,
        )
        if not item.label or confirmation is None:
            continue
        true_scores.append(
            peer_confirmation_score_micros(
                densities=densities,
                row=item.row,
                confirmation_minute=confirmation,
            )
        )

    if len(true_scores) < MIN_CALIBRATION_TRUE_CONFIRMATIONS:
        raise V14InformationGainError(
            "V14 calibration lacks minimum true V11 confirmations"
        )
    threshold, retention = select_v14_peer_confirmation_threshold_micros(
        true_scores
    )
    if retention < V14_CALIBRATION_TRUE_CONFIRMATION_RETENTION_BPS:
        raise V14InformationGainError("V14 calibration retention drift")

    return _FittedFoldModel(
        v11=v11,
        densities=densities,
        peer_confirmation_threshold_micros=threshold,
        calibration_true_confirmation_count=len(true_scores),
        calibration_true_confirmation_retention_bps=retention,
        discovery_count=len(discovery),
        calibration_count=len(calibration),
        purged_discovery_count=purged,
        discovery_observed_max=discovery_observed_max,
        calibration_source_min=calibration_source_min,
    )


def _evaluate_fold(
    *,
    fold_index: int,
    model: _FittedFoldModel,
    validation: tuple[_AlignedEpisode, ...],
) -> V14FoldEvaluation:
    labels: list[bool] = []
    confirmation_minutes: list[int | None] = []
    peer_scores: list[int | None] = []
    for item in validation:
        confirmation = _baseline_confirmation_minute(
            model=model.v11,
            episode=item.episode,
        )
        score = (
            None
            if confirmation is None
            else peer_confirmation_score_micros(
                densities=model.densities,
                row=item.row,
                confirmation_minute=confirmation,
            )
        )
        labels.append(item.label)
        confirmation_minutes.append(confirmation)
        peer_scores.append(score)
    return evaluate_v14_fold(
        fold_index=fold_index,
        labels=tuple(labels),
        baseline_confirmation_minutes=tuple(confirmation_minutes),
        peer_confirmation_scores_micros=tuple(peer_scores),
        peer_confirmation_threshold_micros=(
            model.peer_confirmation_threshold_micros
        ),
    )


def _final_model_fingerprint(
    *,
    representation_fingerprint: str,
    density_fingerprint: str,
    threshold_micros: int,
) -> str:
    payload = {
        "identity": V14_INFORMATION_GAIN_IDENTITY,
        "target_contract": TARGET_CONTRACT,
        "representation_fingerprint": representation_fingerprint,
        "v11_model_fingerprint": EXPECTED_V11_MODEL_FINGERPRINT,
        "v11_representation_fingerprint": EXPECTED_V11_REPRESENTATION_FINGERPRINT,
        "density_set_fingerprint": density_fingerprint,
        "peer_confirmation_threshold_micros": threshold_micros,
        "peer_confirmation_law": "MIN_US500_US30_AT_V11_CONFIRMATION_CHECKPOINT",
        "retention_law": "SCORE_GTE_THRESHOLD",
        "checkpoints_minutes": list(V14_CHECKPOINTS_MINUTES),
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
    expected_representation_fingerprint: str,
    evidence_paths: dict[str, Path],
) -> dict[str, object]:
    rows_by_source = _load_representation(
        representation_path,
        expected_fingerprint=expected_representation_fingerprint,
    )
    episodes, partition_range = _prepare_partition(
        partition="r8",
        evidence_paths=evidence_paths,
    )
    if partition_range.get("target_contract") != TARGET_CONTRACT:
        raise V14InformationGainError("V14 target contract drift")
    if partition_range.get("fresh_holdout_opened") != 0:
        raise V14InformationGainError("V14 opened fresh holdout")
    if partition_range.get("episode_count") != EXPECTED_ALIGNED_R8_COUNT:
        raise V14InformationGainError("authoritative V11 episode count drift")
    if partition_range.get("eligible_source_count") != 6534:
        raise V14InformationGainError("authoritative V11 source count drift")

    aligned = _align(episodes=episodes, rows_by_source=rows_by_source)
    full_v11 = fit_v11_mechanism_confirmation_model(
        fitted_at=max(item.observed_at for item in aligned),
        fit_partition="r8",
        episodes=tuple(item.episode for item in aligned),
    )
    full_v11_fp = v11_model_fingerprint(full_v11)
    if full_v11_fp != EXPECTED_V11_MODEL_FINGERPRINT:
        raise V14InformationGainError("authoritative V11 model fingerprint drift")
    if v11_representation_fingerprint() != EXPECTED_V11_REPRESENTATION_FINGERPRINT:
        raise V14InformationGainError("V11 representation fingerprint drift")

    n = len(aligned)
    boundaries = tuple(n * index // 5 for index in range(6))
    fold_payloads: list[dict[str, object]] = []
    fold_evaluations = []

    for fold_index in range(4):
        validation_start = boundaries[fold_index + 1]
        validation_end = boundaries[fold_index + 2]
        validation = aligned[validation_start:validation_end]
        training = _outer_training_prefix(
            aligned,
            validation_start=validation_start,
        )
        model = _fit_fold_model(training)
        evaluation = _evaluate_fold(
            fold_index=fold_index,
            model=model,
            validation=validation,
        )
        fold_evaluations.append(evaluation)
        fold_payloads.append(
            {
                "fold_index": fold_index,
                "training_count_after_outer_purge": len(training),
                "validation_count": len(validation),
                "validation_source_min": _utc(validation[0].source_at).isoformat(
                    timespec="microseconds"
                ),
                "validation_source_max": _utc(validation[-1].source_at).isoformat(
                    timespec="microseconds"
                ),
                "discovery_count": model.discovery_count,
                "calibration_count": model.calibration_count,
                "purged_discovery_count": model.purged_discovery_count,
                "discovery_observed_max": model.discovery_observed_max.isoformat(
                    timespec="microseconds"
                ),
                "calibration_source_min": model.calibration_source_min.isoformat(
                    timespec="microseconds"
                ),
                "calibration_true_confirmation_count": (
                    model.calibration_true_confirmation_count
                ),
                "calibration_true_confirmation_retention_bps": (
                    model.calibration_true_confirmation_retention_bps
                ),
                "peer_confirmation_threshold_micros": (
                    model.peer_confirmation_threshold_micros
                ),
                "density_set_fingerprint_sha256": v14_density_set_fingerprint(
                    model.densities
                ),
                "evaluation": asdict(evaluation),
            }
        )

    pooled_veto = pooled_v14_false_veto_bps(tuple(fold_evaluations))
    r8_pass = (
        all(item.gate_pass for item in fold_evaluations)
        and pooled_veto >= V14_POOLED_INCREMENTAL_FALSE_VETO_BPS
    )
    result: dict[str, object] = {
        "schema": "qore.shared.wp05.v14.cross_market_microstructure.r8.v1",
        "identity": V14_INFORMATION_GAIN_IDENTITY,
        "target_contract": TARGET_CONTRACT,
        "representation_fingerprint_sha256": expected_representation_fingerprint,
        "aligned_target_count": len(aligned),
        "v11_model_fingerprint_sha256": full_v11_fp,
        "v11_representation_fingerprint_sha256": (
            EXPECTED_V11_REPRESENTATION_FINGERPRINT
        ),
        "folds": fold_payloads,
        "pooled_incremental_false_confirmation_veto_bps": pooled_veto,
        "r8_information_gain_pass": r8_pass,
        "protocol_pass": True,
        "r6_r5_read": False,
        "fresh_holdout_opened": False,
        "shared_methodology_authority": False,
        "shared_sizing_authority": False,
        "shared_risk_authority": False,
        "shared_order_authority": False,
        "shared_execution_authority": False,
    }
    if not r8_pass:
        result.update(
            {
                "status": "WP05_V14_CROSS_MARKET_MICROSTRUCTURE_FALSIFIED",
                "reason": "FOUR_FOLD_INFORMATION_GAIN_GATE_FAILED",
            }
        )
        return result

    final_model = _fit_fold_model(aligned)
    density_fp = v14_density_set_fingerprint(final_model.densities)
    model_fp = _final_model_fingerprint(
        representation_fingerprint=expected_representation_fingerprint,
        density_fingerprint=density_fp,
        threshold_micros=final_model.peer_confirmation_threshold_micros,
    )
    result.update(
        {
            "status": "WP05_V14_CROSS_MARKET_MICROSTRUCTURE_FROZEN",
            "final_density_set": [asdict(item) for item in final_model.densities],
            "final_density_set_fingerprint_sha256": density_fp,
            "final_peer_confirmation_threshold_micros": (
                final_model.peer_confirmation_threshold_micros
            ),
            "final_calibration_true_confirmation_count": (
                final_model.calibration_true_confirmation_count
            ),
            "final_calibration_true_confirmation_retention_bps": (
                final_model.calibration_true_confirmation_retention_bps
            ),
            "final_v14_model_fingerprint_sha256": model_fp,
            "next_authorized_step": (
                "R6_R5_SOURCE_ONLY_V14_PEER_ACQUISITION_WITH_OUTCOMES_CLOSED"
            ),
        }
    )
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--representation", type=Path, required=True)
    parser.add_argument("--expected-representation-fingerprint", required=True)
    parser.add_argument("--r8-nas", type=Path, required=True)
    parser.add_argument("--r8-sp", type=Path, required=True)
    parser.add_argument("--r8-us", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    payload = run(
        representation_path=args.representation,
        expected_representation_fingerprint=args.expected_representation_fingerprint,
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
                "r8_information_gain_pass": payload["r8_information_gain_pass"],
                "pooled_incremental_false_confirmation_veto_bps": payload[
                    "pooled_incremental_false_confirmation_veto_bps"
                ],
                "folds": payload["folds"],
                "final_v14_model_fingerprint_sha256": payload.get(
                    "final_v14_model_fingerprint_sha256"
                ),
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
