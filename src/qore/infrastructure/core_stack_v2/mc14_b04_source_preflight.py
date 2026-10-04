"""Source-only preflight for the preregistered MC14 B04 replay."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from enum import StrEnum
from typing import Any, Final, Mapping

EXPECTED_B04_RUN_ID: Final = 36765098842
EXPECTED_B04_SHA: Final = "aec788d073aedc31f609c1609af3f7d4d8e5ae30"
EXPECTED_WINDOW_COUNT: Final = 2948
REQUIRED_FAMILIES: Final = (
    "US2000_BREADTH_PROXY",
    "XAUUSD_DEFENSIVE_PROXY",
)


class B04SourceDisposition(StrEnum):
    READY_FOR_SINGLE_GOVERNED_REPLAY = (
        "READY_FOR_SINGLE_GOVERNED_REPLAY"
    )
    INSUFFICIENT_DO_NOT_INFER = "INSUFFICIENT_DO_NOT_INFER"


@dataclass(frozen=True, slots=True)
class B04FamilySourcePreflight:
    family: str
    disposition: B04SourceDisposition
    window_count: int
    empty_bid_window_count: int
    empty_ask_window_count: int
    full_bid_ask_window_coverage: bool
    global_dataset_sha256: str
    target_or_outcome_read: bool
    r6_r5_read: bool
    fresh_holdout_opened: bool

    def __post_init__(self) -> None:
        if self.family not in REQUIRED_FAMILIES:
            raise ValueError("unexpected B04 family")
        if self.window_count != EXPECTED_WINDOW_COUNT:
            raise ValueError("B04 family window count drifted")
        if self.empty_bid_window_count < 0 or self.empty_ask_window_count < 0:
            raise ValueError("B04 empty-window counts cannot be negative")
        if len(self.global_dataset_sha256) != 64:
            raise ValueError("B04 dataset hash must be sha256 hex")
        if (
            self.target_or_outcome_read
            or self.r6_r5_read
            or self.fresh_holdout_opened
        ):
            raise ValueError("B04 source preflight crossed a protected boundary")
        complete = (
            self.empty_bid_window_count == 0
            and self.empty_ask_window_count == 0
            and self.full_bid_ask_window_coverage
        )
        expected = (
            B04SourceDisposition.READY_FOR_SINGLE_GOVERNED_REPLAY
            if complete
            else B04SourceDisposition.INSUFFICIENT_DO_NOT_INFER
        )
        if self.disposition is not expected:
            raise ValueError("B04 source disposition conflicts with coverage")

    def fingerprint(self) -> str:
        payload = asdict(self)
        payload["disposition"] = self.disposition.value
        raw = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(raw.encode()).hexdigest()


@dataclass(frozen=True, slots=True)
class B04SourcePreflight:
    workflow_run_id: int
    git_sha: str
    source_manifest_sha256: str
    reduced_evidence_sha256: str
    families: tuple[B04FamilySourcePreflight, ...]
    source_only: bool = True
    target_or_outcome_read: bool = False
    r6_r5_read: bool = False
    fresh_holdout_opened: bool = False
    broker_mutation: bool = False
    productive_authority: bool = False

    def __post_init__(self) -> None:
        if self.workflow_run_id != EXPECTED_B04_RUN_ID:
            raise ValueError("unexpected B04 workflow run")
        if self.git_sha != EXPECTED_B04_SHA:
            raise ValueError("unexpected B04 acquisition SHA")
        for name in (
            "source_manifest_sha256",
            "reduced_evidence_sha256",
        ):
            if len(getattr(self, name)) != 64:
                raise ValueError(f"{name} must be sha256 hex")
        if tuple(row.family for row in self.families) != REQUIRED_FAMILIES:
            raise ValueError("B04 families must preserve canonical order")
        if (
            not self.source_only
            or self.target_or_outcome_read
            or self.r6_r5_read
            or self.fresh_holdout_opened
            or self.broker_mutation
            or self.productive_authority
        ):
            raise ValueError("B04 source preflight violates research governance")

    @property
    def ready_families(self) -> tuple[str, ...]:
        return tuple(
            row.family
            for row in self.families
            if row.disposition
            is B04SourceDisposition.READY_FOR_SINGLE_GOVERNED_REPLAY
        )

    @property
    def insufficient_families(self) -> tuple[str, ...]:
        return tuple(
            row.family
            for row in self.families
            if row.disposition
            is B04SourceDisposition.INSUFFICIENT_DO_NOT_INFER
        )

    def fingerprint(self) -> str:
        payload = asdict(self)
        for row in payload["families"]:
            row["disposition"] = str(row["disposition"])
        raw = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(raw.encode()).hexdigest()


def _required_bool(payload: Mapping[str, Any], name: str) -> bool:
    value = payload.get(name)
    if type(value) is not bool:
        raise ValueError(f"{name} must be explicit bool")
    return value


def _required_int(payload: Mapping[str, Any], name: str) -> int:
    value = payload.get(name)
    if type(value) is not int:
        raise ValueError(f"{name} must be explicit int")
    return value


def _required_str(payload: Mapping[str, Any], name: str) -> str:
    value = payload.get(name)
    if not isinstance(value, str) or not value:
        raise ValueError(f"{name} must be explicit string")
    return value


def assess_b04_source_pack(
    payload: Mapping[str, Any],
) -> B04SourcePreflight:
    """Validate the sealed B04 source pack without reading any target."""

    sensors = payload.get("sensors")
    if not isinstance(sensors, Mapping):
        raise ValueError("B04 source pack requires sensors mapping")

    families: list[B04FamilySourcePreflight] = []
    for family in REQUIRED_FAMILIES:
        raw = sensors.get(family)
        if not isinstance(raw, Mapping):
            raise ValueError(f"B04 source pack missing {family}")
        if _required_str(raw, "status") != "source_only_complete":
            raise ValueError(f"B04 source family {family} is not source complete")

        empty_bid = _required_int(raw, "empty_bid_window_count")
        empty_ask = _required_int(raw, "empty_ask_window_count")
        full_coverage = _required_bool(raw, "full_bid_ask_window_coverage")
        disposition = (
            B04SourceDisposition.READY_FOR_SINGLE_GOVERNED_REPLAY
            if empty_bid == 0 and empty_ask == 0 and full_coverage
            else B04SourceDisposition.INSUFFICIENT_DO_NOT_INFER
        )
        families.append(
            B04FamilySourcePreflight(
                family=family,
                disposition=disposition,
                window_count=_required_int(raw, "window_count"),
                empty_bid_window_count=empty_bid,
                empty_ask_window_count=empty_ask,
                full_bid_ask_window_coverage=full_coverage,
                global_dataset_sha256=_required_str(
                    raw,
                    "global_dataset_sha256",
                ),
                target_or_outcome_read=_required_bool(
                    raw,
                    "target_or_outcome_read",
                ),
                r6_r5_read=_required_bool(raw, "r6_r5_read"),
                fresh_holdout_opened=_required_bool(
                    raw,
                    "fresh_holdout_opened",
                ),
            )
        )

    return B04SourcePreflight(
        workflow_run_id=_required_int(payload, "workflow_run_id"),
        git_sha=_required_str(payload, "git_sha"),
        source_manifest_sha256=_required_str(
            payload,
            "source_manifest_sha256",
        ),
        reduced_evidence_sha256=_required_str(
            payload,
            "reduced_evidence_sha256",
        ),
        families=tuple(families),
        target_or_outcome_read=_required_bool(
            payload,
            "target_or_outcome_read",
        ),
        r6_r5_read=_required_bool(payload, "r6_r5_read"),
        fresh_holdout_opened=_required_bool(
            payload,
            "fresh_holdout_opened",
        ),
        broker_mutation=_required_bool(payload, "broker_mutation"),
        productive_authority=_required_bool(
            payload,
            "productive_authority",
        ),
    )
