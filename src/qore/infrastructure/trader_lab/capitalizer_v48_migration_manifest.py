"""V48 migration manifest: preserve execution truth, supersede composition errors.

V48 is a surgical reconstruction. Provider truth, causality and validation infrastructure
are retained. Historical V2/V47 composition files are preserved as evidence but are not
authoritative for the new source-faithful route graph.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

IDENTITY = "QORE_CAPITALIZER_V48_MIGRATION_MANIFEST"


class V48MigrationAction(StrEnum):
    PRESERVE = "PRESERVE"
    SUPERSEDE_FOR_V48 = "SUPERSEDE_FOR_V48"
    REUSE_PRIMITIVE_ONLY = "REUSE_PRIMITIVE_ONLY"


@dataclass(frozen=True, slots=True)
class V48MigrationItem:
    item_id: str
    action: V48MigrationAction
    rationale: str

    def __post_init__(self) -> None:
        if not self.item_id or not self.item_id == self.item_id.upper():
            raise ValueError("migration item id must be non-empty uppercase")
        if not self.rationale:
            raise ValueError("migration item requires rationale")


ITEMS: tuple[V48MigrationItem, ...] = (
    V48MigrationItem(
        "PROVIDER_NATIVE_M1_AND_EXACT_TICKS",
        V48MigrationAction.PRESERVE,
        "Execution truth is independent of the strategy-composition defect.",
    ),
    V48MigrationItem(
        "TIMESTAMP_AND_ANTI_LOOKAHEAD_DISCIPLINE",
        V48MigrationAction.PRESERVE,
        "Causal evidence timing remains mandatory.",
    ),
    V48MigrationItem(
        "SESSION_CALENDAR_AND_DST_INFRASTRUCTURE",
        V48MigrationAction.PRESERVE,
        "Calendar conversion is valid infrastructure; route-specific eligibility changes.",
    ),
    V48MigrationItem(
        "STRUCTURAL_STOP_PRIMITIVES",
        V48MigrationAction.PRESERVE,
        "Protected-swing invalidation remains source-supported.",
    ),
    V48MigrationItem(
        "STRUCTURAL_TARGET_CANDIDATE_GENERATION",
        V48MigrationAction.REUSE_PRIMITIVE_ONLY,
        (
            "Causal untouched HTF candidate construction is useful, but the exactly-one "
            "resolution policy is superseded."
        ),
    ),
    V48MigrationItem(
        "OOS_PARTITIONS_UTC_MONTE_CARLO_COST_STRESS",
        V48MigrationAction.PRESERVE,
        "Validation infrastructure remains valid and Fresh Holdout stays sealed.",
    ),
    V48MigrationItem(
        "MAX3_SESSION_CEILING",
        V48MigrationAction.PRESERVE,
        "Owner portfolio ceiling remains governance, never a density quota.",
    ),
    V48MigrationItem(
        "SOURCE_STRATEGY_GRAMMAR_V2",
        V48MigrationAction.SUPERSEDE_FOR_V48,
        "Universal H1-M15-M1 source grammar conflicts with session-specific TTrades routes.",
    ),
    V48MigrationItem(
        "DUAL_SOURCE_ENTRY_ACCEPTANCE_V1",
        V48MigrationAction.SUPERSEDE_FOR_V48,
        "Full ICT AND full TTrades conjunction has no conjunction-level source provenance.",
    ),
    V48MigrationItem(
        "SOURCE_OBSERVATION_CONTRACT_V2",
        V48MigrationAction.SUPERSEDE_FOR_V48,
        "It freezes universal H1/M15/M1 observations that do not belong to every route.",
    ),
    V48MigrationItem(
        "SOURCE_FAITHFUL_TRADER_DESIGN_V2",
        V48MigrationAction.SUPERSEDE_FOR_V48,
        "Its source closure generalized one model into the entire Trader.",
    ),
    V48MigrationItem(
        "SOURCE_SESSION_CONTEXT_V2_GLOBAL_VETO",
        V48MigrationAction.SUPERSEDE_FOR_V48,
        "ICT killzones cannot globally veto source-valid TTrades session routes.",
    ),
    V48MigrationItem(
        "STRUCTURAL_TARGET_EXACTLY_ONE_RESOLUTION",
        V48MigrationAction.SUPERSEDE_FOR_V48,
        "Exactly-one price/kind is a QORE disambiguation rule, not a proven source rule.",
    ),
    V48MigrationItem(
        "M1_MSS_FVG_OB_UNIVERSAL_TRIAD",
        V48MigrationAction.SUPERSEDE_FOR_V48,
        "M1 entry techniques must remain route-specific alternatives where source says so.",
    ),
)


@dataclass(frozen=True, slots=True)
class V48MigrationManifest:
    identity: str = IDENTITY
    items: tuple[V48MigrationItem, ...] = ITEMS
    historical_files_deleted: bool = False
    v47_evidence_rewritten: bool = False
    fresh_holdout_authorized: bool = False
    live_authorized: bool = False

    def __post_init__(self) -> None:
        if self.identity != IDENTITY:
            raise ValueError("V48 migration identity is frozen")
        ids = tuple(item.item_id for item in self.items)
        if len(ids) != len(set(ids)):
            raise ValueError("V48 migration items must be unique")
        if self.historical_files_deleted or self.v47_evidence_rewritten:
            raise ValueError("V48 must preserve historical evidence")
        if self.fresh_holdout_authorized or self.live_authorized:
            raise ValueError("migration manifest grants no certification/deployment authority")


V48_MIGRATION_MANIFEST = V48MigrationManifest()
