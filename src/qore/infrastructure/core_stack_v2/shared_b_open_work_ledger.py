"""Architect-B exclusive open-work ledger.

This ledger is intentionally separate from Shared's master completion authority.
It prevents the B lane from claiming completion while mandatory B-owned work
remains partial, in progress, open, or externally blocked.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from enum import StrEnum
from typing import Final


class SharedBWorkStatus(StrEnum):
    COMPLETE_AND_PROVEN = "COMPLETE_AND_PROVEN"
    PARTIAL_EVIDENCE_OPEN = "PARTIAL_EVIDENCE_OPEN"
    ARCHITECTURE_VALIDATED_EVIDENCE_OPEN = "ARCHITECTURE_VALIDATED_EVIDENCE_OPEN"
    IN_PROGRESS = "IN_PROGRESS"
    EXTERNALLY_BLOCKED = "EXTERNALLY_BLOCKED"
    OPEN = "OPEN"


@dataclass(frozen=True, slots=True)
class SharedBWorkItem:
    work_id: str
    title: str
    status: SharedBWorkStatus
    evidence_refs: tuple[str, ...]
    blockers: tuple[str, ...] = ()
    mandatory: bool = True

    def __post_init__(self) -> None:
        if not self.work_id.startswith("B-"):
            raise ValueError("B work id must use B-NN")
        if not self.title.strip():
            raise ValueError("B work title must be non-empty")
        if (
            self.evidence_refs
            != tuple(sorted(set(self.evidence_refs)))
            or any(not item.strip() for item in self.evidence_refs)
        ):
            raise ValueError("evidence_refs must be unique/canonical")
        if (
            self.blockers != tuple(sorted(set(self.blockers)))
            or any(not item.strip() for item in self.blockers)
        ):
            raise ValueError("blockers must be unique/canonical")
        if (
            self.status is SharedBWorkStatus.COMPLETE_AND_PROVEN
            and self.blockers
        ):
            raise ValueError("complete B work cannot retain blockers")
        if (
            self.status
            in {
                SharedBWorkStatus.PARTIAL_EVIDENCE_OPEN,
                SharedBWorkStatus.ARCHITECTURE_VALIDATED_EVIDENCE_OPEN,
                SharedBWorkStatus.IN_PROGRESS,
                SharedBWorkStatus.EXTERNALLY_BLOCKED,
                SharedBWorkStatus.OPEN,
            }
            and self.mandatory
            and not self.blockers
        ):
            raise ValueError(
                "mandatory incomplete B work must state explicit blockers"
            )


B_WORK_ITEMS: Final = (
    SharedBWorkItem(
        "B-01",
        "Revalidate branch, PR and owner directives",
        SharedBWorkStatus.COMPLETE_AND_PROVEN,
        ("base:7d1b54cfa5453c0eb5c0662438ed15e7d656da61",),
    ),
    SharedBWorkItem(
        "B-02",
        "Provider catalogue identity and drift freeze",
        SharedBWorkStatus.COMPLETE_AND_PROVEN,
        (
            "artifact:11110976806",
            "artifact:11111176548",
            "run:36742519707",
        ),
    ),
    SharedBWorkItem(
        "B-03",
        "Post-V14 cross-asset source availability",
        SharedBWorkStatus.COMPLETE_AND_PROVEN,
        (
            "artifact:11112547465",
            "artifact:11113260581",
            "run:36746337433",
        ),
    ),
    SharedBWorkItem(
        "B-04",
        "Full R8 US2000 and XAUUSD source acquisition",
        SharedBWorkStatus.IN_PROGRESS,
        ("run:36753726027",),
        ("32-shard acquisition/reduction not yet complete",),
    ),
    SharedBWorkItem(
        "B-05",
        "Global sensor registry discovery freeze",
        SharedBWorkStatus.COMPLETE_AND_PROVEN,
        ("artifact:11112621544", "run:36745412605"),
    ),
    SharedBWorkItem(
        "B-06",
        "Global instrument identity",
        SharedBWorkStatus.PARTIAL_EVIDENCE_OPEN,
        (
            "artifact:11115769948",
            "artifact:11115828701",
            "artifact:11112587007",
            "run:36754912247",
            "run:36755839843",
        ),
        (
            "canonical identity is not resolved for the full 177-sensor provider universe",
            "energy tradable product identities remain unresolved",
            "futures front/roll/continuous identity remains unresolved",
        ),
    ),
    SharedBWorkItem(
        "B-07",
        "Global market hours and canonical calendars",
        SharedBWorkStatus.EXTERNALLY_BLOCKED,
        ("run:36623131862",),
        (
            "canonical calendar registry is incomplete",
            "distributed OTC FX cannot be assigned a fabricated single venue calendar",
        ),
    ),
    SharedBWorkItem(
        "B-08",
        "Temporal synchronization and comparability",
        SharedBWorkStatus.PARTIAL_EVIDENCE_OPEN,
        ("run:36623131862",),
        (
            "cadence policy registry is not frozen",
            "canonical calendar binding remains incomplete",
            "comparability policy registry is not frozen",
            "liquidity policy registry is not frozen",
            "temporal skew policy registry is not frozen",
        ),
    ),
    SharedBWorkItem(
        "B-09",
        "Global data health, freshness and degraded mode",
        SharedBWorkStatus.PARTIAL_EVIDENCE_OPEN,
        ("artifact:11115754374", "run:36755357039"),
        (
            "new additive degraded states still require dedicated real cross-asset replication",
        ),
    ),
    SharedBWorkItem(
        "B-10",
        "Global relational graph population",
        SharedBWorkStatus.ARCHITECTURE_VALIDATED_EVIDENCE_OPEN,
        ("artifact:11116372968", "run:36755296952"),
        (
            "empirical global relation population waits for canonical temporal comparability",
        ),
    ),
    SharedBWorkItem(
        "B-11",
        "Relationship lifecycle population",
        SharedBWorkStatus.ARCHITECTURE_VALIDATED_EVIDENCE_OPEN,
        ("artifact:11116372968", "run:36755296952"),
        (
            "lifecycle architecture is validated but empirical global population remains open",
        ),
    ),
    SharedBWorkItem(
        "B-12",
        "Lead-lag observability population",
        SharedBWorkStatus.ARCHITECTURE_VALIDATED_EVIDENCE_OPEN,
        ("artifact:11116372968", "run:36755296952"),
        (
            "lead-lag architecture is validated but empirical global population remains open",
        ),
    ),
    SharedBWorkItem(
        "B-13",
        "Cross-asset structural-divergence observation inputs",
        SharedBWorkStatus.OPEN,
        ("run:36746337433",),
        (
            "requires temporally comparable multi-family observations before population",
        ),
    ),
    SharedBWorkItem(
        "B-14",
        "Agricultural world",
        SharedBWorkStatus.EXTERNALLY_BLOCKED,
        ("artifact:11059457712", "run:36623645085"),
        (
            "current authorized provider exposes zero agricultural/soft/livestock candidates",
        ),
    ),
    SharedBWorkItem(
        "B-15",
        "Commodity world",
        SharedBWorkStatus.PARTIAL_EVIDENCE_OPEN,
        ("artifact:11115769948", "run:36755839843"),
        (
            "energy tradable product identity remains unresolved",
            "GC front/roll/continuous-series semantics remain unresolved",
        ),
    ),
    SharedBWorkItem(
        "B-16",
        "Active Perception sensor-side acquisition",
        SharedBWorkStatus.IN_PROGRESS,
        (
            "artifact:11112547465",
            "artifact:11113260581",
            "run:36757173753",
        ),
        (
            "B-16/B-17 boundary workflow has not yet produced final evidence",
            "global 177-sensor causal qualification remains incomplete",
        ),
    ),
    SharedBWorkItem(
        "B-17",
        "Attention and sensor resource budget",
        SharedBWorkStatus.COMPLETE_AND_PROVEN,
        ("artifact:11105226668", "run:36730806113"),
    ),
    SharedBWorkItem(
        "B-18",
        "Core and Broker observational cognition",
        SharedBWorkStatus.ARCHITECTURE_VALIDATED_EVIDENCE_OPEN,
        ("artifact:11116344955", "run:36756742481"),
        (
            "real runtime Core/Broker replication remains open",
        ),
    ),
    SharedBWorkItem(
        "B-19",
        "Sensor-side Blindspot Engine",
        SharedBWorkStatus.PARTIAL_EVIDENCE_OPEN,
        ("artifact:11116344955", "run:36756742481"),
        (
            "second-order coverage-inventory completeness is not yet proven",
        ),
    ),
    SharedBWorkItem(
        "B-20",
        "Unknown-world and missing-observation semantics",
        SharedBWorkStatus.COMPLETE_AND_PROVEN,
        ("artifact:11116344955", "run:36756742481"),
    ),
    SharedBWorkItem(
        "B-21",
        "Deterministic replay and total provenance audit",
        SharedBWorkStatus.PARTIAL_EVIDENCE_OPEN,
        (
            "artifact:11112547465",
            "artifact:11113260581",
            "run:36746337433",
        ),
        (
            "global sensor-universe replay/provenance audit remains incomplete",
        ),
    ),
    SharedBWorkItem(
        "B-22",
        "Global World Perception freeze",
        SharedBWorkStatus.OPEN,
        (),
        ("all mandatory B work must close before freeze",),
    ),
    SharedBWorkItem(
        "B-23",
        "B-only zero-open-work audit",
        SharedBWorkStatus.IN_PROGRESS,
        (),
        ("B-only ledger validation is being established",),
    ),
    SharedBWorkItem(
        "B-24",
        "Handoff to A plus final integration",
        SharedBWorkStatus.OPEN,
        (),
        ("WORLD_PERCEPTION_FREEZE does not yet exist",),
    ),
)


def build_shared_b_open_work_ledger() -> dict[str, object]:
    expected_ids = tuple(f"B-{index:02d}" for index in range(1, 25))
    actual_ids = tuple(item.work_id for item in B_WORK_ITEMS)
    if actual_ids != expected_ids:
        raise ValueError("B ledger must contain exact ordered B-01..B-24")

    mandatory = tuple(item for item in B_WORK_ITEMS if item.mandatory)
    incomplete = tuple(
        item
        for item in mandatory
        if item.status is not SharedBWorkStatus.COMPLETE_AND_PROVEN
    )
    status_counts = {
        status.value: sum(item.status is status for item in B_WORK_ITEMS)
        for status in SharedBWorkStatus
    }
    payload: dict[str, object] = {
        "identity": "SHARED_B_GLOBAL_WORLD_PERCEPTION_OPEN_WORK_LEDGER_001",
        "mandatory_item_count": len(mandatory),
        "completed_and_proven_count": len(mandatory) - len(incomplete),
        "required_open_count": len(incomplete),
        "zero_open_required_work": not incomplete,
        "b_lane_complete": not incomplete,
        "shared_certification_authority": False,
        "final_shared_holdout_authority": False,
        "status_counts": status_counts,
        "items": [
            {
                "work_id": item.work_id,
                "title": item.title,
                "status": item.status.value,
                "mandatory": item.mandatory,
                "evidence_refs": item.evidence_refs,
                "blockers": item.blockers,
            }
            for item in B_WORK_ITEMS
        ],
    }
    raw = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("utf-8")
    payload["ledger_fingerprint_sha256"] = hashlib.sha256(raw).hexdigest()
    return payload
