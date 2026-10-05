"""Canonical execution order for the CIBO capability program.

Owner-mandated order:

1. CEILING_DISCOVERY
   Discover the real economic/intelligence ceiling of native CIBO.
   No pass target is imposed. The purpose is diagnosis and capability mapping.

2. POST_CEILING_REFINEMENT
   Refine CIBO using only causal findings from the burned/research ceiling study.
   No Fresh OOS/certification claims are allowed here.

3. EXAM_1_ALL_TRADER_RESCUE
   Seven-Trader rescue exam: every managed Trader contribution must finish > 0.

4. EXAM_3_NEGATIVE_TRADER_ONLY_RESCUE
   Only Traders with frozen negative unmanaged baselines are admitted.
   CIBO must make every managed contribution > 0.

5. EXAM_2_2000_PERCENT_10M
   Final growth exam: +2000% net return within at most 10 calendar months.

The order is strict. A later stage cannot be considered valid before all prior
stages are explicitly closed.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum

from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)
from qore.infrastructure.cibo_ceiling_discovery import (
    CiboCeilingDiscoveryEvidence,
)


class CiboCapabilityProgramStage(IntEnum):
    CEILING_DISCOVERY = 1
    POST_CEILING_REFINEMENT = 2
    EXAM_1_ALL_TRADER_RESCUE = 3
    EXAM_3_NEGATIVE_TRADER_ONLY_RESCUE = 4
    EXAM_2_2000_PERCENT_10M = 5


CIBO_CAPABILITY_PROGRAM_ORDER: tuple[CiboCapabilityProgramStage, ...] = (
    CiboCapabilityProgramStage.CEILING_DISCOVERY,
    CiboCapabilityProgramStage.POST_CEILING_REFINEMENT,
    CiboCapabilityProgramStage.EXAM_1_ALL_TRADER_RESCUE,
    CiboCapabilityProgramStage.EXAM_3_NEGATIVE_TRADER_ONLY_RESCUE,
    CiboCapabilityProgramStage.EXAM_2_2000_PERCENT_10M,
)


@dataclass(frozen=True, slots=True)
class CiboCapabilityProgramProgress:
    current_stage: CiboCapabilityProgramStage
    closed_stages: tuple[CiboCapabilityProgramStage, ...] = ()

    def __post_init__(self) -> None:
        if type(self.current_stage) is not CiboCapabilityProgramStage:
            raise CiboCapitalManagementError(
                "capability program current stage must be canonical"
            )
        if any(
            type(stage) is not CiboCapabilityProgramStage
            for stage in self.closed_stages
        ):
            raise CiboCapitalManagementError(
                "capability program closed stage must be canonical"
            )
        if len(set(self.closed_stages)) != len(self.closed_stages):
            raise CiboCapitalManagementError(
                "capability program closed stages contain duplicates"
            )

        current_index = CIBO_CAPABILITY_PROGRAM_ORDER.index(
            self.current_stage
        )
        expected_prior = CIBO_CAPABILITY_PROGRAM_ORDER[:current_index]
        if self.closed_stages != expected_prior:
            raise CiboCapitalManagementError(
                "CIBO capability program stage order violated"
            )

    @property
    def ceiling_discovery_active(self) -> bool:
        return (
            self.current_stage
            is CiboCapabilityProgramStage.CEILING_DISCOVERY
        )

    @property
    def examinations_unlocked(self) -> bool:
        return (
            CiboCapabilityProgramStage.CEILING_DISCOVERY
            in self.closed_stages
            and CiboCapabilityProgramStage.POST_CEILING_REFINEMENT
            in self.closed_stages
        )


DEFAULT_CIBO_CAPABILITY_PROGRAM_PROGRESS = CiboCapabilityProgramProgress(
    current_stage=CiboCapabilityProgramStage.CEILING_DISCOVERY,
    closed_stages=(),
)


def enter_post_ceiling_refinement(
    evidence: CiboCeilingDiscoveryEvidence,
) -> CiboCapabilityProgramProgress:
    """Close CEILING_DISCOVERY only with admissible intrinsic-ceiling evidence."""

    if not isinstance(evidence, CiboCeilingDiscoveryEvidence):
        raise CiboCapitalManagementError(
            "post-ceiling refinement requires canonical ceiling evidence"
        )
    if not evidence.ceiling_discovery_ready_to_close:
        raise CiboCapitalManagementError(
            "CEILING_DISCOVERY cannot close before intrinsic ceiling is proven"
        )
    return CiboCapabilityProgramProgress(
        current_stage=CiboCapabilityProgramStage.POST_CEILING_REFINEMENT,
        closed_stages=(CiboCapabilityProgramStage.CEILING_DISCOVERY,),
    )
