"""Source-gated R2 readiness for VT08 CRT PURE.

R2 is deliberately stricter than the already-closed common Strategy Identity.
A Model #1 economic replay is not source-ready until the old-high/old-low
reference-selection contract is deterministic without outcome leakage.
"""

from __future__ import annotations

from dataclasses import dataclass

from qore.infrastructure.traders.crt_pure_source_registry import (
    CrtPureConceptId,
    promotable_concepts,
)


CRT_PURE_R2_MODEL1_REQUIRED_CONCEPTS: tuple[CrtPureConceptId, ...] = (
    CrtPureConceptId.REFERENCE_RANGE,
    CrtPureConceptId.LIQUIDATION_SWEEP,
    CrtPureConceptId.RECLAIM_CLOSE_BACK_INSIDE,
    CrtPureConceptId.CANDLE_1_2_3,
    CrtPureConceptId.ENTRY_FAMILIES,
    CrtPureConceptId.MODEL_1_ENTRY,
    CrtPureConceptId.MODEL_1_TIMEFRAME_ALIGNMENT,
    CrtPureConceptId.MODEL_1_REFERENCE_SELECTION,
    CrtPureConceptId.STRUCTURAL_STOP,
    CrtPureConceptId.STRUCTURAL_DESTINATION,
)


@dataclass(frozen=True, slots=True)
class CrtPureR2Readiness:
    ready: bool
    unresolved: tuple[CrtPureConceptId, ...]
    grants_replay_authority: bool = False
    grants_deployment_authority: bool = False

    def __post_init__(self) -> None:
        if self.ready != (not self.unresolved):
            raise ValueError("R2 readiness must equal absence of unresolved concepts")
        if self.grants_replay_authority:
            raise ValueError("source readiness alone cannot grant replay authority")
        if self.grants_deployment_authority:
            raise ValueError("R2 readiness cannot grant deployment authority")


def model1_r2_readiness() -> CrtPureR2Readiness:
    promoted = set(promotable_concepts())
    unresolved = tuple(
        concept
        for concept in CRT_PURE_R2_MODEL1_REQUIRED_CONCEPTS
        if concept not in promoted
    )
    return CrtPureR2Readiness(
        ready=not unresolved,
        unresolved=unresolved,
    )
