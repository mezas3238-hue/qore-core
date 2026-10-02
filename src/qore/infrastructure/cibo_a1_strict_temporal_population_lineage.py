"""Strict temporal-population lineage for CIBO Architect A1.

This module is a provenance contract only. It proves that one frozen A1
mechanism is evaluated on four distinct, ordered temporal populations without
retuning, outcome-aware population construction, fold pooling, or policy
identity drift. It does not decide whether the mechanism is economically
useful and grants no certification or productive authority.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict, dataclass
from datetime import datetime

from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)

GATE_ID = "CIBO_A1_STRICT_TEMPORAL_POPULATION_LINEAGE_V1"
CANONICAL_FOLDS = ("WF1", "WF2", "WF3", "WF4")
A1_WORKSTREAMS = (
    "T04",
    "T06",
    "T07",
    "T08",
    "T09",
    "T10",
    "T12",
    "T13",
    "T14",
    "T15",
    "T18",
    "GEN-C2",
    "GEN-C3",
    "GEN-C4",
    "GEN-C5",
    "GEN-C6",
    "GEN-C7",
    "TEMPORAL_REPLICATION",
)
_SHA256_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
_SHA1_RE = re.compile(r"^[0-9a-f]{40}$")


@dataclass(frozen=True, slots=True)
class A1TemporalPopulationFold:
    fold_id: str
    population_sha256: str
    candidate_id: str
    code_sha: str
    parameter_sha256: str
    protocol_binding_sha256: str
    treatment_identity: str
    decision_start_at: datetime
    decision_end_at: datetime
    outcomes_observed_through_at: datetime
    policy_frozen_before_population: bool
    retuned_after_population_start: bool
    outcomes_used_to_define_population: bool
    outcomes_pooled_across_folds: bool
    productive_authority: bool = False

    def __post_init__(self) -> None:
        if self.fold_id not in CANONICAL_FOLDS:
            raise CiboCapitalManagementError(
                "A1 temporal lineage fold must be WF1..WF4"
            )
        _sha256(self.population_sha256, "population_sha256")
        if not self.candidate_id:
            raise CiboCapitalManagementError(
                "A1 temporal lineage candidate_id is required"
            )
        if _SHA1_RE.fullmatch(self.code_sha) is None:
            raise CiboCapitalManagementError(
                "A1 temporal lineage code_sha must be a 40-char Git SHA"
            )
        _sha256(self.parameter_sha256, "parameter_sha256")
        _sha256(self.protocol_binding_sha256, "protocol_binding_sha256")
        if not self.treatment_identity:
            raise CiboCapitalManagementError(
                "A1 temporal lineage treatment identity is required"
            )
        _aware(self.decision_start_at, "decision_start_at")
        _aware(self.decision_end_at, "decision_end_at")
        _aware(
            self.outcomes_observed_through_at,
            "outcomes_observed_through_at",
        )
        if not (
            self.decision_start_at
            < self.decision_end_at
            <= self.outcomes_observed_through_at
        ):
            raise CiboCapitalManagementError(
                "A1 temporal lineage chronology is invalid"
            )
        if not self.policy_frozen_before_population:
            raise CiboCapitalManagementError(
                "A1 temporal lineage requires pre-population policy freeze"
            )
        if (
            self.retuned_after_population_start
            or self.outcomes_used_to_define_population
            or self.outcomes_pooled_across_folds
            or self.productive_authority
        ):
            raise CiboCapitalManagementError(
                "A1 temporal lineage governance contamination"
            )


@dataclass(frozen=True, slots=True)
class A1StrictTemporalPopulationLineageReport:
    gate_id: str
    workstream_id: str
    candidate_id: str
    code_sha: str
    parameter_sha256: str
    protocol_binding_sha256: str
    treatment_identity: str
    folds: tuple[A1TemporalPopulationFold, ...]
    lineage_valid: bool = True
    all_four_folds_required: bool = True
    fold_pooling_allowed: bool = False
    post_population_retune_allowed: bool = False
    outcome_aware_population_definition_allowed: bool = False
    productive_authority: bool = False
    live_authorized: bool = False
    real_capital_authorized: bool = False
    scientific_disposition_allowed_by_lineage_alone: bool = False

    def __post_init__(self) -> None:
        if self.gate_id != GATE_ID:
            raise CiboCapitalManagementError(
                "A1 temporal lineage gate identity drift"
            )
        if self.workstream_id not in A1_WORKSTREAMS:
            raise CiboCapitalManagementError(
                "A1 temporal lineage workstream is outside A1 ownership"
            )
        if tuple(item.fold_id for item in self.folds) != CANONICAL_FOLDS:
            raise CiboCapitalManagementError(
                "A1 temporal lineage requires ordered WF1..WF4"
            )
        if not self.lineage_valid or not self.all_four_folds_required:
            raise CiboCapitalManagementError(
                "A1 temporal lineage cannot weaken four-fold truth"
            )
        prohibited = (
            self.fold_pooling_allowed,
            self.post_population_retune_allowed,
            self.outcome_aware_population_definition_allowed,
            self.productive_authority,
            self.live_authorized,
            self.real_capital_authorized,
            self.scientific_disposition_allowed_by_lineage_alone,
        )
        if any(prohibited):
            raise CiboCapitalManagementError(
                "A1 temporal lineage report governance drift"
            )

    def fingerprint(self) -> str:
        payload = asdict(self)
        for fold in payload["folds"]:
            fold["decision_start_at"] = fold["decision_start_at"].isoformat()
            fold["decision_end_at"] = fold["decision_end_at"].isoformat()
            fold["outcomes_observed_through_at"] = (
                fold["outcomes_observed_through_at"].isoformat()
            )
        raw = json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        ).encode("utf-8")
        return "sha256:" + hashlib.sha256(raw).hexdigest()


def evaluate_a1_strict_temporal_population_lineage(
    *,
    workstream_id: str,
    folds: tuple[A1TemporalPopulationFold, ...],
) -> A1StrictTemporalPopulationLineageReport:
    """Validate immutable, disjoint WF1..WF4 population lineage."""

    if workstream_id not in A1_WORKSTREAMS:
        raise CiboCapitalManagementError(
            "A1 temporal lineage workstream is outside A1 ownership"
        )
    if len(folds) != 4 or tuple(item.fold_id for item in folds) != CANONICAL_FOLDS:
        raise CiboCapitalManagementError(
            "A1 temporal lineage requires exactly ordered WF1..WF4"
        )

    first = folds[0]
    for field_name in (
        "candidate_id",
        "code_sha",
        "parameter_sha256",
        "protocol_binding_sha256",
        "treatment_identity",
    ):
        expected = getattr(first, field_name)
        if any(getattr(item, field_name) != expected for item in folds[1:]):
            raise CiboCapitalManagementError(
                f"A1 temporal lineage {field_name} drift across folds"
            )

    populations = tuple(item.population_sha256 for item in folds)
    if len(set(populations)) != 4:
        raise CiboCapitalManagementError(
            "A1 temporal lineage requires four distinct populations"
        )

    for previous, current in zip(folds[:-1], folds[1:], strict=True):
        if previous.decision_end_at > current.decision_start_at:
            raise CiboCapitalManagementError(
                "A1 temporal lineage fold decision windows overlap"
            )

    return A1StrictTemporalPopulationLineageReport(
        gate_id=GATE_ID,
        workstream_id=workstream_id,
        candidate_id=first.candidate_id,
        code_sha=first.code_sha,
        parameter_sha256=first.parameter_sha256,
        protocol_binding_sha256=first.protocol_binding_sha256,
        treatment_identity=first.treatment_identity,
        folds=folds,
    )


def _sha256(value: str, field_name: str) -> None:
    if _SHA256_RE.fullmatch(value) is None:
        raise CiboCapitalManagementError(
            f"A1 temporal lineage {field_name} must be sha256:<64 hex>"
        )


def _aware(value: datetime, field_name: str) -> None:
    if value.tzinfo is None or value.utcoffset() is None:
        raise CiboCapitalManagementError(
            f"A1 temporal lineage {field_name} must be timezone-aware"
        )
