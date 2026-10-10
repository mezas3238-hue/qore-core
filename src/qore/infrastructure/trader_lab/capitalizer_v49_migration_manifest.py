"""V49 migration manifest from the V48 reconstruction.

V48 evidence is preserved, not rewritten. V49 changes the active Trader identity according to
the Owner's high-frequency mandate: H1/M15/M1 only. Daily/H4 research remains historical
evidence or a possible future non-Scalper research family, but cannot gate Capitalizer V49.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

IDENTITY = "QORE_CAPITALIZER_V49_MIGRATION_MANIFEST"


class V49MigrationAction(StrEnum):
    PRESERVE = "PRESERVE"
    SUPERSEDE_FOR_V49 = "SUPERSEDE_FOR_V49"
    REUSE_PRIMITIVE_ONLY = "REUSE_PRIMITIVE_ONLY"


@dataclass(frozen=True, slots=True)
class V49MigrationItem:
    item_id: str
    action: V49MigrationAction
    rationale: str


ITEMS: tuple[V49MigrationItem, ...] = (
    V49MigrationItem(
        "PROVIDER_NATIVE_M1_EXACT_TICKS_CAUSAL_TIMESTAMPS",
        V49MigrationAction.PRESERVE,
        "Execution truth and anti-lookahead infrastructure remain mandatory.",
    ),
    V49MigrationItem(
        "SESSION_CALENDAR_DST_AND_NINE_MARKET_IDENTITY",
        V49MigrationAction.PRESERVE,
        "Three sessions and nine markets remain the Capitalizer operating universe.",
    ),
    V49MigrationItem(
        "MAX3_SESSION_CEILING",
        V49MigrationAction.PRESERVE,
        "MAX3 remains a ceiling and never a quota.",
    ),
    V49MigrationItem(
        "V48_H1_M15_M1_CAUSAL_PRIMITIVES",
        V49MigrationAction.REUSE_PRIMITIVE_ONLY,
        "CISD/FVG/sweep primitives are reusable, but V48 one-shot topology is not.",
    ),
    V49MigrationItem(
        "V48_DAILY_H4_ASIA_LONDON_DECISION_ROUTES",
        V49MigrationAction.SUPERSEDE_FOR_V49,
        "Owner defines the Scalper decision stack as H1/M15/M1 only.",
    ),
    V49MigrationItem(
        "V48_159_PER_YEAR_DENSITY_PROFILE",
        V49MigrationAction.SUPERSEDE_FOR_V49,
        "Owner rejected 159/year as incompatible with the intended high-frequency Scalper.",
    ),
    V49MigrationItem(
        "FRESH_H1_EVENT_PER_TRADE_TOPOLOGY",
        V49MigrationAction.SUPERSEDE_FOR_V49,
        "H1 becomes persistent context capable of supporting multiple M15/M1 opportunities.",
    ),
    V49MigrationItem(
        "DAILY_OR_H4_TARGET_DEPENDENCY",
        V49MigrationAction.SUPERSEDE_FOR_V49,
        "Targets for V49 must be derived from H1/M15/M1 intraday structure only.",
    ),
)


@dataclass(frozen=True, slots=True)
class V49MigrationManifest:
    identity: str = IDENTITY
    items: tuple[V49MigrationItem, ...] = ITEMS
    v48_evidence_deleted: bool = False
    v48_results_rewritten: bool = False
    daily_h4_active_in_v49: bool = False
    fresh_holdout_authorized: bool = False
    economics_authorized: bool = False
    live_authorized: bool = False

    def __post_init__(self) -> None:
        if self.identity != IDENTITY:
            raise ValueError("V49 migration identity is frozen")
        ids = tuple(item.item_id for item in self.items)
        if len(ids) != len(set(ids)):
            raise ValueError("V49 migration items must be unique")
        if self.v48_evidence_deleted or self.v48_results_rewritten:
            raise ValueError("V49 must preserve historical evidence")
        if self.daily_h4_active_in_v49:
            raise ValueError("Daily/H4 cannot remain active V49 decision layers")
        if self.fresh_holdout_authorized or self.economics_authorized or self.live_authorized:
            raise ValueError("migration grants no certification/deployment authority")


V49_MIGRATION_MANIFEST = V49MigrationManifest()
