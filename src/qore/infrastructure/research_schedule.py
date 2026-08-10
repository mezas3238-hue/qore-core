from __future__ import annotations

from dataclasses import dataclass

from qore.infrastructure.research_lineage_errors import ResearchLineageValidationError

_SUPPORTED_SCHEDULES = frozenset({"schedule-a.event-available-at.v1"})
_SUPPORTED_START_POLICIES = frozenset({"w1.no-warmup.v1"})


@dataclass(frozen=True, slots=True)
class ResearchScheduleSemantics:
    identity: str

    def __post_init__(self) -> None:
        if not isinstance(self.identity, str):
            raise ResearchLineageValidationError("schedule identity must be str")
        if self.identity not in _SUPPORTED_SCHEDULES:
            raise ResearchLineageValidationError(
                f"unsupported Phase 1A schedule: {self.identity!r}"
            )


@dataclass(frozen=True, slots=True)
class ResearchStartPolicy:
    identity: str

    def __post_init__(self) -> None:
        if not isinstance(self.identity, str):
            raise ResearchLineageValidationError("start-policy identity must be str")
        if self.identity not in _SUPPORTED_START_POLICIES:
            raise ResearchLineageValidationError(
                f"unsupported Phase 1A start policy: {self.identity!r}"
            )


SCHEDULE_A_V1 = ResearchScheduleSemantics(
    identity="schedule-a.event-available-at.v1"
)
W1_NO_WARMUP_V1 = ResearchStartPolicy(identity="w1.no-warmup.v1")
