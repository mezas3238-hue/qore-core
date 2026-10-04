"""Fail-closed readiness gates for Architect-B WORLD_PERCEPTION_FREEZE.

B-21, B-22 and B-24 form a sequential topology. Provenance cannot require a
future B-22/B-24 artifact before those artifacts are legitimately emitted.
Therefore 22/24 provenance coverage is the exact pre-freeze topology when the
only missing workstream pointers are B-22 and B-24.

This module grants no Shared certification, productive, trading, sizing, Risk,
CIBO, execution, broker-mutation or protected-holdout authority.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from typing import Final

from qore.infrastructure.core_stack_v2.shared_b_open_work_ledger import (
    B_WORK_ITEMS,
    SharedBWorkItem,
    SharedBWorkStatus,
)
from qore.infrastructure.core_stack_v2.shared_integrator_b_provenance_coverage import (
    BProvenanceCoverage,
)

PRE_FREEZE_REQUIRED_IDS: Final = tuple(
    f"B-{index:02d}" for index in range(1, 22)
) + ("B-23",)
DOWNSTREAM_GATE_IDS: Final = ("B-22", "B-24")


@dataclass(frozen=True, slots=True)
class SharedBWorldPerceptionFreezeAssessment:
    upstream_required_ids: tuple[str, ...]
    upstream_nonterminal_ids: tuple[str, ...]
    provenance_covered_ids: tuple[str, ...]
    provenance_missing_ids: tuple[str, ...]
    pre_freeze_provenance_complete: bool
    deterministic_replay_verified: bool
    explicit_unknowns_preserved: bool
    authority_free_outputs: bool
    freeze_authorized: bool
    protected_holdout_opened: bool = False
    productive_authority: bool = False
    certification_authority: bool = False

    def __post_init__(self) -> None:
        if self.upstream_required_ids != PRE_FREEZE_REQUIRED_IDS:
            raise ValueError("freeze assessment upstream topology drift")
        expected = (
            not self.upstream_nonterminal_ids
            and self.pre_freeze_provenance_complete
            and self.deterministic_replay_verified
            and self.explicit_unknowns_preserved
            and self.authority_free_outputs
        )
        if self.freeze_authorized != expected:
            raise ValueError("freeze authorization does not match prerequisites")
        if (
            self.protected_holdout_opened
            or self.productive_authority
            or self.certification_authority
        ):
            raise ValueError("B freeze gate carries forbidden authority")

    def fingerprint(self) -> str:
        raw = json.dumps(
            asdict(self),
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        ).encode("utf-8")
        return hashlib.sha256(raw).hexdigest()


@dataclass(frozen=True, slots=True)
class SharedBFinalHandoffAssessment:
    pre_handoff_required_ids: tuple[str, ...]
    pre_handoff_nonterminal_ids: tuple[str, ...]
    provenance_missing_ids: tuple[str, ...]
    pre_handoff_provenance_complete: bool
    world_perception_freeze_present: bool
    deterministic_replay_verified: bool
    explicit_unknowns_preserved: bool
    authority_free_outputs: bool
    handoff_authorized: bool
    protected_holdout_opened: bool = False
    productive_authority: bool = False
    certification_authority: bool = False

    def __post_init__(self) -> None:
        expected_ids = tuple(f"B-{index:02d}" for index in range(1, 24))
        if self.pre_handoff_required_ids != expected_ids:
            raise ValueError("handoff assessment topology drift")
        expected = (
            not self.pre_handoff_nonterminal_ids
            and self.pre_handoff_provenance_complete
            and self.world_perception_freeze_present
            and self.deterministic_replay_verified
            and self.explicit_unknowns_preserved
            and self.authority_free_outputs
        )
        if self.handoff_authorized != expected:
            raise ValueError("handoff authorization does not match prerequisites")
        if (
            self.protected_holdout_opened
            or self.productive_authority
            or self.certification_authority
        ):
            raise ValueError("B final handoff gate carries forbidden authority")

    def fingerprint(self) -> str:
        raw = json.dumps(
            asdict(self),
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        ).encode("utf-8")
        return hashlib.sha256(raw).hexdigest()


def _rows_by_id(
    items: tuple[SharedBWorkItem, ...],
) -> dict[str, SharedBWorkItem]:
    rows = {item.work_id: item for item in items}
    expected = {f"B-{index:02d}" for index in range(1, 25)}
    if set(rows) != expected:
        raise ValueError("B freeze gate requires exact B-01..B-24 ledger")
    return rows


def assess_world_perception_freeze(
    *,
    provenance_coverage: BProvenanceCoverage,
    deterministic_replay_verified: bool,
    explicit_unknowns_preserved: bool,
    authority_free_outputs: bool,
    items: tuple[SharedBWorkItem, ...] = B_WORK_ITEMS,
) -> SharedBWorldPerceptionFreezeAssessment:
    """Assess B-22 readiness without requiring future B-22/B-24 pointers."""

    rows = _rows_by_id(items)
    upstream_nonterminal = tuple(
        work_id
        for work_id in PRE_FREEZE_REQUIRED_IDS
        if rows[work_id].status is not SharedBWorkStatus.COMPLETE_AND_PROVEN
    )
    covered = set(provenance_coverage.covered_ids)
    missing = tuple(provenance_coverage.missing_ids)
    pre_freeze_provenance_complete = (
        set(PRE_FREEZE_REQUIRED_IDS) <= covered
        and set(missing) <= set(DOWNSTREAM_GATE_IDS)
        and not provenance_coverage.missing_terminal_ids
        and not provenance_coverage.missing_external_blocked_ids
    )
    freeze_authorized = (
        not upstream_nonterminal
        and pre_freeze_provenance_complete
        and deterministic_replay_verified
        and explicit_unknowns_preserved
        and authority_free_outputs
    )
    return SharedBWorldPerceptionFreezeAssessment(
        upstream_required_ids=PRE_FREEZE_REQUIRED_IDS,
        upstream_nonterminal_ids=upstream_nonterminal,
        provenance_covered_ids=provenance_coverage.covered_ids,
        provenance_missing_ids=missing,
        pre_freeze_provenance_complete=pre_freeze_provenance_complete,
        deterministic_replay_verified=deterministic_replay_verified,
        explicit_unknowns_preserved=explicit_unknowns_preserved,
        authority_free_outputs=authority_free_outputs,
        freeze_authorized=freeze_authorized,
    )


def assess_final_b_handoff(
    *,
    provenance_coverage: BProvenanceCoverage,
    world_perception_freeze_present: bool,
    deterministic_replay_verified: bool,
    explicit_unknowns_preserved: bool,
    authority_free_outputs: bool,
    items: tuple[SharedBWorkItem, ...] = B_WORK_ITEMS,
) -> SharedBFinalHandoffAssessment:
    """Assess B-24 readiness after B-22 without requiring B-24 self-provenance."""

    rows = _rows_by_id(items)
    required_ids = tuple(f"B-{index:02d}" for index in range(1, 24))
    nonterminal = tuple(
        work_id
        for work_id in required_ids
        if rows[work_id].status is not SharedBWorkStatus.COMPLETE_AND_PROVEN
    )
    covered = set(provenance_coverage.covered_ids)
    missing = tuple(provenance_coverage.missing_ids)
    provenance_complete = (
        set(required_ids) <= covered
        and set(missing) <= {"B-24"}
        and not provenance_coverage.missing_terminal_ids
        and not provenance_coverage.missing_external_blocked_ids
    )
    handoff_authorized = (
        not nonterminal
        and provenance_complete
        and world_perception_freeze_present
        and deterministic_replay_verified
        and explicit_unknowns_preserved
        and authority_free_outputs
    )
    return SharedBFinalHandoffAssessment(
        pre_handoff_required_ids=required_ids,
        pre_handoff_nonterminal_ids=nonterminal,
        provenance_missing_ids=missing,
        pre_handoff_provenance_complete=provenance_complete,
        world_perception_freeze_present=world_perception_freeze_present,
        deterministic_replay_verified=deterministic_replay_verified,
        explicit_unknowns_preserved=explicit_unknowns_preserved,
        authority_free_outputs=authority_free_outputs,
        handoff_authorized=handoff_authorized,
    )
