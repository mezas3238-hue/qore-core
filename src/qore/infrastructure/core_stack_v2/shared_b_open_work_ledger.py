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
            len(self.evidence_refs) != len(set(self.evidence_refs))
            or any(not item.strip() for item in self.evidence_refs)
        ):
            raise ValueError("evidence_refs must be non-empty/unique")
        if (
            len(self.blockers) != len(set(self.blockers))
            or any(not item.strip() for item in self.blockers)
        ):
            raise ValueError("blockers must be non-empty/unique")
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
        ("run:36765098842",),
        (
            "US2000 acquisition is 16/16 shards GREEN; XAUUSD 32-shard matrix "
            "and final offline aggregate are still in progress",
        ),
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
            "artifact:11112587007",
            "artifact:11115769948",
            "artifact:11115828701",
            "artifact:11119439556",
            "artifact:11124554816",
            "artifact:11124811192",
            "artifact:11124952981",
            "artifact:11125151831",
            "artifact:11125412870",
            "run:36754912247",
            "run:36755839843",
            "run:36764899352",
            "run:36774358236",
            "run:36775105295",
            "run:36775310025",
            "run:36775635034",
            "run:36775855021",
        ),
        (
            "85/177 sensors have current reference mappings but not full "
            "tradable/listing/calendar/historical identity",
            "5/177 GC dated contracts are verified but front/roll/continuous "
            "identity remains unresolved",
            "2/25 index sensors are preserved as legacy lineages without "
            "current automatic reference binding",
            "12/25 index sensors still lack explicit provider-to-official-index "
            "binding evidence",
            "73 cryptocurrency sensors now have explicit provider unit/scale "
            "semantics but canonical/provider-neutral identity remains unproven",
        ),
    ),
    SharedBWorkItem(
        "B-07",
        "Global market hours and canonical calendars",
        SharedBWorkStatus.EXTERNALLY_BLOCKED,
        (
            "artifact:11123210080",
            "artifact:11128361589",
            "run:36623131862",
            "run:36765945116",
            "run:36782105126",
        ),
        (
            "exact 177-sensor calendar worklist is frozen but verified canonical "
            "calendar bindings remain 0/177",
            "60 FX sensors require governed distributed-OTC weekly market-state "
            "semantics rather than a fabricated single venue",
            "11 current official indices still require official calculation-calendar binding",
            "2 legacy indices require historical versioned calendars and cannot inherit current calendars",
            "12 indices remain identity-blocked before calendar binding",
            "73 crypto sensors remain identity/market-structure blocked before canonical temporal semantics",
            "5 dated futures require versioned session/holiday calendars and 14 commodity "
            "reference objects require explicit temporal semantics",
        ),
    ),
    SharedBWorkItem(
        "B-08",
        "Temporal synchronization and comparability",
        SharedBWorkStatus.PARTIAL_EVIDENCE_OPEN,
        (
            "artifact:11124500250",
            "artifact:11128361589",
            "run:36623131862",
            "run:36767735668",
            "run:36782105126",
        ),
        (
            "source-clock integrity is sealed for 3 sensors / 41 shards / "
            "203185 real ticks; exact calendar blockers are now classified for 177/177 "
            "sensors but verified calendar bindings remain 0/177",
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
        (
            "artifact:11115754374",
            "artifact:11119762780",
            "run:36755357039",
            "run:36764279123",
        ),
        (
            "stale-relation empirical isolation remains gated by B-07/B-08 "
            "canonical temporal comparability",
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
        SharedBWorkStatus.ARCHITECTURE_VALIDATED_EVIDENCE_OPEN,
        (
            "artifact:11116897631",
            "run:36757804153",
        ),
        (
            "empirical population waits for B-07/B-08 canonical temporal comparability",
        ),
    ),
    SharedBWorkItem(
        "B-14",
        "Agricultural world",
        SharedBWorkStatus.EXTERNALLY_BLOCKED,
        (
            "artifact:11059457712",
            "artifact:11126270432",
            "run:36623645085",
            "run:36777269692",
        ),
        (
            "current authorized provider exposes zero agricultural/soft/livestock candidates",
        ),
    ),
    SharedBWorkItem(
        "B-15",
        "Commodity world",
        SharedBWorkStatus.PARTIAL_EVIDENCE_OPEN,
        (
            "artifact:11115769948",
            "artifact:11128416668",
            "run:36755839843",
            "run:36782329462",
        ),
        (
            "energy tradable product identity remains unresolved",
            "all 5 sealed dated GC contracts are now proven expired before SEP-2026; "
            "the current provider chain/front contract is absent from the observed set",
            "GC roll and continuous-series semantics remain unresolved and cannot be "
            "inferred from contract-month ordering",
        ),
    ),
    SharedBWorkItem(
        "B-16",
        "Active Perception sensor-side acquisition",
        SharedBWorkStatus.PARTIAL_EVIDENCE_OPEN,
        (
            "artifact:11112547465",
            "artifact:11113260581",
            "artifact:11116986748",
            "run:36757173753",
        ),
        (
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
        SharedBWorkStatus.COMPLETE_AND_PROVEN,
        (
            "artifact:11116344955",
            "artifact:11120521150",
            "run:36756742481",
            "run:36764365409",
        ),
    ),
    SharedBWorkItem(
        "B-19",
        "Sensor-side Blindspot Engine",
        SharedBWorkStatus.COMPLETE_AND_PROVEN,
        (
            "artifact:11116344955",
            "artifact:11120391213",
            "run:36756742481",
            "run:36764376550",
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
            "artifact:11117991672",
            "artifact:11121310503",
            "artifact:11125588197",
            "artifact:11126485523",
            "run:36746337433",
            "run:36758248635",
            "run:36765319771",
            "run:36776003986",
            "run:36777484441",
        ),
        (
            "current sealed provenance explicitly covers 18/24 B workstream IDs; "
            "B-04/B-07/B-08/B-21/B-22/B-24 still lack final coverage",
            "total provenance cannot close before all mandatory B workstreams have "
            "a terminal or explicitly governed blocked disposition",
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
        SharedBWorkStatus.COMPLETE_AND_PROVEN,
        (
            "artifact:11117192542",
            "run:36757894898",
        ),
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
                "evidence_refs": tuple(sorted(item.evidence_refs)),
                "blockers": tuple(sorted(item.blockers)),
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
