"""Fail-closed scientific-value examination contract for B-16 sensors.

A provider symbol is never scientifically qualified merely because identity,
calendar and replayable source evidence exist. Those prerequisites only make a
sensor eligible to enter a preregistered research examination.

The examination is generic and outcome-disciplined:
- final Shared certification holdouts are forbidden;
- no PnL, Trader methodology or trading authority may enter the sensor exam;
- all gates are frozen before research labels are opened;
- every validation fold must pass independently;
- stress and temporal replication are mandatory;
- PASS proves scientific sensor value only. It never creates productive,
  trading, sizing, Risk, CIBO, execution or broker authority.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import datetime
from enum import StrEnum
from typing import Any, Final, cast

EXPECTED_WORKLIST: Final = "SHARED_B_SENSOR_QUALIFICATION_WORKLIST_001"
REQUIRED_MINIMUM_FOLDS: Final = 4


class SensorScientificExamStatus(StrEnum):
    NOT_ELIGIBLE = "NOT_ELIGIBLE"
    PREREGISTERED_READY = "PREREGISTERED_READY"
    PASS = "PASS"
    FAIL = "FAIL"


@dataclass(frozen=True, slots=True)
class SensorScientificValuePreregistration:
    sensor_key: str
    provider_symbol: str
    worklist_fingerprint_sha256: str
    research_target_id: str
    research_dataset_id: str
    discovery_partition_id: str
    calibration_partition_id: str
    validation_fold_ids: tuple[str, ...]
    minimum_fold_sample_count: int
    minimum_incremental_value_bps: int
    minimum_preservation_bps: int
    preregistered_at: datetime
    research_labels_opened_at: datetime | None = None
    final_shared_holdout_opened: bool = False
    pnl_target_used: bool = False
    trader_methodology_target_used: bool = False

    def __post_init__(self) -> None:
        for name in (
            "sensor_key",
            "provider_symbol",
            "research_target_id",
            "research_dataset_id",
            "discovery_partition_id",
            "calibration_partition_id",
        ):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{name} must be non-empty")
        if len(self.worklist_fingerprint_sha256) != 64:
            raise ValueError("worklist fingerprint must be SHA256")
        int(self.worklist_fingerprint_sha256, 16)
        if (
            len(self.validation_fold_ids) < REQUIRED_MINIMUM_FOLDS
            or len(self.validation_fold_ids) != len(set(self.validation_fold_ids))
            or any(not item.strip() for item in self.validation_fold_ids)
        ):
            raise ValueError("scientific exam requires >=4 unique validation folds")
        if type(self.minimum_fold_sample_count) is not int or self.minimum_fold_sample_count <= 0:
            raise ValueError("minimum fold sample count must be positive")
        for name in ("minimum_incremental_value_bps", "minimum_preservation_bps"):
            value = getattr(self, name)
            if type(value) is not int or not 0 <= value <= 10_000:
                raise ValueError(f"{name} outside 0..10000")
        if self.preregistered_at.tzinfo is None or self.preregistered_at.utcoffset() is None:
            raise ValueError("preregistered_at must be timezone-aware")
        if self.research_labels_opened_at is not None:
            if (
                self.research_labels_opened_at.tzinfo is None
                or self.research_labels_opened_at.utcoffset() is None
            ):
                raise ValueError("research_labels_opened_at must be timezone-aware")
            if self.research_labels_opened_at < self.preregistered_at:
                raise ValueError("research labels were opened before preregistration")
        if (
            self.final_shared_holdout_opened
            or self.pnl_target_used
            or self.trader_methodology_target_used
        ):
            raise ValueError("scientific sensor exam carries forbidden target/holdout state")

    def fingerprint(self) -> str:
        payload = asdict(self)
        payload["preregistered_at"] = self.preregistered_at.isoformat()
        payload["research_labels_opened_at"] = (
            None
            if self.research_labels_opened_at is None
            else self.research_labels_opened_at.isoformat()
        )
        raw = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
        return hashlib.sha256(raw).hexdigest()


@dataclass(frozen=True, slots=True)
class SensorScientificFoldEvidence:
    fold_id: str
    sample_count: int
    incremental_value_bps: int
    preservation_bps: int
    anti_leakage_pass: bool
    deterministic_replay_pass: bool

    def __post_init__(self) -> None:
        if not self.fold_id.strip():
            raise ValueError("fold_id must be non-empty")
        if type(self.sample_count) is not int or self.sample_count < 0:
            raise ValueError("sample_count must be non-negative")
        for name in ("incremental_value_bps", "preservation_bps"):
            value = getattr(self, name)
            if type(value) is not int or not -10_000 <= value <= 10_000:
                raise ValueError(f"{name} outside -10000..10000")


@dataclass(frozen=True, slots=True)
class SensorScientificValueResult:
    sensor_key: str
    provider_symbol: str
    preregistration_fingerprint_sha256: str
    status: SensorScientificExamStatus
    fold_passes: tuple[bool, ...]
    stress_pass: bool
    temporal_replication_pass: bool
    scientific_value_proven: bool
    sensor_admission_authority: bool = False
    trade_authority: bool = False
    sizing_authority: bool = False
    risk_authority: bool = False
    cibo_authority: bool = False
    execution_authority: bool = False
    productive_authority: bool = False

    def __post_init__(self) -> None:
        if len(self.preregistration_fingerprint_sha256) != 64:
            raise ValueError("preregistration fingerprint must be SHA256")
        expected = (
            self.status is SensorScientificExamStatus.PASS
            and bool(self.fold_passes)
            and all(self.fold_passes)
            and self.stress_pass
            and self.temporal_replication_pass
        )
        if self.scientific_value_proven != expected:
            raise ValueError("scientific_value_proven does not match exam result")
        if (
            self.sensor_admission_authority
            or self.trade_authority
            or self.sizing_authority
            or self.risk_authority
            or self.cibo_authority
            or self.execution_authority
            or self.productive_authority
        ):
            raise ValueError("scientific value result carries forbidden authority")


def _find_sensor_record(
    worklist: dict[str, object],
    *,
    provider_symbol: str,
) -> dict[str, Any]:
    if worklist.get("identity") != EXPECTED_WORKLIST:
        raise ValueError("unexpected B16 qualification worklist identity")
    fingerprint = worklist.get("worklist_fingerprint_sha256")
    if not isinstance(fingerprint, str) or len(fingerprint) != 64:
        raise ValueError("worklist fingerprint missing")
    records = worklist.get("records")
    if not isinstance(records, list):
        raise ValueError("worklist records missing")
    matches = [
        cast(dict[str, Any], row)
        for row in records
        if isinstance(row, dict) and row.get("provider_symbol") == provider_symbol
    ]
    if len(matches) != 1:
        raise ValueError("provider symbol must resolve to exactly one worklist row")
    return matches[0]


def assess_sensor_exam_eligibility(
    *,
    worklist: dict[str, object],
    preregistration: SensorScientificValuePreregistration,
) -> SensorScientificValueResult:
    row = _find_sensor_record(
        worklist,
        provider_symbol=preregistration.provider_symbol,
    )
    if worklist["worklist_fingerprint_sha256"] != preregistration.worklist_fingerprint_sha256:
        raise ValueError("preregistration does not bind exact worklist")
    eligible = (
        row.get("state") == "READY_FOR_SCIENTIFIC_VALUE_EXAM"
        and row.get("identity_ready") is True
        and row.get("calendar_ready") is True
        and row.get("real_source_evidence_status")
        == "FULL_REAL_BID_ASK_HISTORY_EVIDENCE"
        and row.get("scientific_value_proven") is False
        and row.get("sensor_admitted") is False
    )
    return SensorScientificValueResult(
        sensor_key=preregistration.sensor_key,
        provider_symbol=preregistration.provider_symbol,
        preregistration_fingerprint_sha256=preregistration.fingerprint(),
        status=(
            SensorScientificExamStatus.PREREGISTERED_READY
            if eligible
            else SensorScientificExamStatus.NOT_ELIGIBLE
        ),
        fold_passes=(),
        stress_pass=False,
        temporal_replication_pass=False,
        scientific_value_proven=False,
    )


def evaluate_sensor_scientific_value(
    *,
    worklist: dict[str, object],
    preregistration: SensorScientificValuePreregistration,
    folds: tuple[SensorScientificFoldEvidence, ...],
    stress_pass: bool,
    temporal_replication_pass: bool,
) -> SensorScientificValueResult:
    readiness = assess_sensor_exam_eligibility(
        worklist=worklist,
        preregistration=preregistration,
    )
    if readiness.status is not SensorScientificExamStatus.PREREGISTERED_READY:
        raise ValueError("sensor is not eligible for scientific-value exam")
    if preregistration.research_labels_opened_at is None:
        raise ValueError("research labels must be opened only after preregistration")
    by_id = {item.fold_id: item for item in folds}
    if len(by_id) != len(folds):
        raise ValueError("duplicate scientific validation fold")
    if tuple(sorted(by_id)) != tuple(sorted(preregistration.validation_fold_ids)):
        raise ValueError("validation fold identity drift")

    fold_passes = tuple(
        (
            by_id[fold_id].sample_count >= preregistration.minimum_fold_sample_count
            and by_id[fold_id].incremental_value_bps
            >= preregistration.minimum_incremental_value_bps
            and by_id[fold_id].preservation_bps
            >= preregistration.minimum_preservation_bps
            and by_id[fold_id].anti_leakage_pass
            and by_id[fold_id].deterministic_replay_pass
        )
        for fold_id in preregistration.validation_fold_ids
    )
    passed = (
        all(fold_passes)
        and stress_pass
        and temporal_replication_pass
    )
    return SensorScientificValueResult(
        sensor_key=preregistration.sensor_key,
        provider_symbol=preregistration.provider_symbol,
        preregistration_fingerprint_sha256=preregistration.fingerprint(),
        status=(
            SensorScientificExamStatus.PASS
            if passed
            else SensorScientificExamStatus.FAIL
        ),
        fold_passes=fold_passes,
        stress_pass=stress_pass,
        temporal_replication_pass=temporal_replication_pass,
        scientific_value_proven=passed,
    )
