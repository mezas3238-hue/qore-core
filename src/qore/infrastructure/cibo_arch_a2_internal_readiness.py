"""Architect A2 internal-readiness audit.

This gate proves A2 has no hidden engineering debt before Phase22 scientific
evidence arrives.  A scientifically blocked row is acceptable only when it is
explicitly terminal EXTERNAL_DEPENDENCY_BLOCKED with non-empty evidence and
external blockers.  The gate never converts those blockers into PASS.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path

from qore.infrastructure.cibo_arch_a2_scientific_closure import (
    A2_WORKSTREAM_IDS,
)
from qore.infrastructure.cibo_arch_a_internal_readiness import (
    ArchitectAReadinessError,
    LEDGER_PATH,
)

_SCHEMA = "QORE_CIBO_ARCH_A2_INTERNAL_READINESS_V1"
_EXPECTED_MATURITY = (
    "TERMINAL_EXTERNAL_DEPENDENCY_BLOCKED_"
    "REAL_PHASE20D_SCIENTIFIC_EVIDENCE_REQUIRED"
)


@dataclass(frozen=True, slots=True)
class ArchitectA2InternalReadinessReport:
    schema: str
    workstream_count: int
    externally_blocked_count: int
    internally_open_ids: tuple[str, ...]
    missing_ids: tuple[str, ...]
    evidence_missing_ids: tuple[str, ...]
    blocker_missing_ids: tuple[str, ...]
    passed: bool
    scientific_closure_claimed: bool = False
    integration_authority: bool = False
    productive_authority: bool = False
    merge_authority: bool = False

    def __post_init__(self) -> None:
        if self.schema != _SCHEMA:
            raise ArchitectAReadinessError(
                "Architect A2 internal-readiness schema drift"
            )
        if self.workstream_count != len(A2_WORKSTREAM_IDS):
            raise ArchitectAReadinessError(
                "Architect A2 internal-readiness workstream count drift"
            )
        if (
            not isinstance(self.externally_blocked_count, int)
            or isinstance(self.externally_blocked_count, bool)
            or not 0 <= self.externally_blocked_count <= self.workstream_count
        ):
            raise ArchitectAReadinessError(
                "Architect A2 external blocker count invalid"
            )
        for name in (
            "internally_open_ids",
            "missing_ids",
            "evidence_missing_ids",
            "blocker_missing_ids",
        ):
            values = getattr(self, name)
            if (
                not isinstance(values, tuple)
                or any(item not in A2_WORKSTREAM_IDS for item in values)
                or len(values) != len(set(values))
            ):
                raise ArchitectAReadinessError(
                    f"Architect A2 internal-readiness {name} invalid"
                )
        expected = not (
            self.internally_open_ids
            or self.missing_ids
            or self.evidence_missing_ids
            or self.blocker_missing_ids
        )
        if self.passed != expected:
            raise ArchitectAReadinessError(
                "Architect A2 internal-readiness pass/debt drift"
            )
        if self.passed and self.externally_blocked_count != self.workstream_count:
            raise ArchitectAReadinessError(
                "Architect A2 ready state must remain exact 17 external blockers"
            )
        if any(
            (
                self.scientific_closure_claimed,
                self.integration_authority,
                self.productive_authority,
                self.merge_authority,
            )
        ):
            raise ArchitectAReadinessError(
                "Architect A2 readiness grants no closure/authority"
            )

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


def evaluate_architect_a2_internal_readiness(
    ledger_path: Path = LEDGER_PATH,
) -> ArchitectA2InternalReadinessReport:
    payload = json.loads(ledger_path.read_text(encoding="utf-8"))
    rows = payload.get("workstreams")
    if not isinstance(rows, list):
        raise ArchitectAReadinessError(
            "Architect A2 canonical workstreams array missing"
        )

    by_id: dict[str, dict[str, object]] = {}
    for raw in rows:
        if not isinstance(raw, dict):
            continue
        row_id = raw.get("id")
        if isinstance(row_id, str):
            if row_id in by_id:
                raise ArchitectAReadinessError(
                    "Architect A2 duplicate ledger workstream id"
                )
            by_id[row_id] = raw

    missing: list[str] = []
    internally_open: list[str] = []
    evidence_missing: list[str] = []
    blocker_missing: list[str] = []
    externally_blocked = 0

    for workstream_id in A2_WORKSTREAM_IDS:
        row = by_id.get(workstream_id)
        if row is None:
            missing.append(workstream_id)
            continue
        if row.get("mandatory") is not True:
            internally_open.append(workstream_id)
            continue
        if (
            row.get("terminal_disposition") != "EXTERNAL_DEPENDENCY_BLOCKED"
            or row.get("current_maturity") != _EXPECTED_MATURITY
        ):
            internally_open.append(workstream_id)
            continue
        externally_blocked += 1

        evidence = row.get("evidence_refs")
        if (
            not isinstance(evidence, list)
            or not evidence
            or any(not isinstance(item, str) or not item for item in evidence)
        ):
            evidence_missing.append(workstream_id)

        blockers = row.get("blockers")
        if (
            not isinstance(blockers, list)
            or not blockers
            or any(not isinstance(item, str) or not item for item in blockers)
        ):
            blocker_missing.append(workstream_id)

    passed = not (
        internally_open
        or missing
        or evidence_missing
        or blocker_missing
    )
    return ArchitectA2InternalReadinessReport(
        schema=_SCHEMA,
        workstream_count=len(A2_WORKSTREAM_IDS),
        externally_blocked_count=externally_blocked,
        internally_open_ids=tuple(internally_open),
        missing_ids=tuple(missing),
        evidence_missing_ids=tuple(evidence_missing),
        blocker_missing_ids=tuple(blocker_missing),
        passed=passed,
    )
