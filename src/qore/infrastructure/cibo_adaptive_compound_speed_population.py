"""Descriptive fresh population for GEN-C8 adaptive compound speed.

This module reports durable pre-outcome C8 decisions only. It does not inspect
economic outcomes, fit thresholds or claim utility/certification.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

from qore.infrastructure.cibo_adaptive_compound_speed_shadow import (
    GENC8_POLICY_FROZEN_AT,
    GENC8_POLICY_ID,
    Genc8SpeedPosture,
    genc8_policy_sha256,
)
from qore.infrastructure.cibo_adaptive_compound_speed_store import (
    Genc8ShadowDecisionSeal,
    VersionedGenc8ShadowBook,
)
from qore.infrastructure.cibo_compound_capital import CiboCompoundCapitalError


class Genc8PopulationStatus(StrEnum):
    EMPTY = "EMPTY"
    COLLECTING = "COLLECTING"


@dataclass(frozen=True, slots=True)
class Genc8PopulationReport:
    status: Genc8PopulationStatus
    policy_id: str
    policy_sha256: str
    policy_frozen_at: datetime
    decision_count: int
    treatment_control_divergence_count: int
    pause_count: int
    defensive_count: int
    cautious_count: int
    normal_count: int
    accelerated_count: int
    first_decision_at: datetime | None
    last_decision_at: datetime | None
    calendar_span_days: int
    decision_calendar_days: int
    account_keys: tuple[str, ...]
    blocker_counts: tuple[tuple[str, int], ...]
    descriptive_only: bool = True
    real_outcome_binding_complete: bool = False
    economic_utility_ready: bool = False
    stress_pass: bool = False
    temporal_replication_pass: bool = False
    certification_ready: bool = False

    def __post_init__(self) -> None:
        if type(self.status) is not Genc8PopulationStatus:
            raise CiboCompoundCapitalError(
                "GEN-C8 population status is invalid"
            )
        if self.policy_id != GENC8_POLICY_ID:
            raise CiboCompoundCapitalError(
                "GEN-C8 population policy identity drift"
            )
        if self.policy_sha256 != genc8_policy_sha256():
            raise CiboCompoundCapitalError(
                "GEN-C8 population policy digest drift"
            )
        if self.policy_frozen_at != GENC8_POLICY_FROZEN_AT:
            raise CiboCompoundCapitalError(
                "GEN-C8 population policy freeze drift"
            )
        for name in (
            "decision_count",
            "treatment_control_divergence_count",
            "pause_count",
            "defensive_count",
            "cautious_count",
            "normal_count",
            "accelerated_count",
            "calendar_span_days",
            "decision_calendar_days",
        ):
            value = getattr(self, name)
            if (
                not isinstance(value, int)
                or isinstance(value, bool)
                or value < 0
            ):
                raise CiboCompoundCapitalError(
                    f"GEN-C8 population {name} must be non-negative int"
                )
        posture_count = (
            self.pause_count
            + self.defensive_count
            + self.cautious_count
            + self.normal_count
            + self.accelerated_count
        )
        if posture_count != self.decision_count:
            raise CiboCompoundCapitalError(
                "GEN-C8 population posture partition drift"
            )
        if self.treatment_control_divergence_count > self.decision_count:
            raise CiboCompoundCapitalError(
                "GEN-C8 population divergence exceeds decisions"
            )
        if (self.first_decision_at is None) != (
            self.last_decision_at is None
        ):
            raise CiboCompoundCapitalError(
                "GEN-C8 population decision range is incomplete"
            )
        if self.first_decision_at is not None:
            _aware(self.first_decision_at, "first_decision_at")
            assert self.last_decision_at is not None
            _aware(self.last_decision_at, "last_decision_at")
            if self.first_decision_at < self.policy_frozen_at:
                raise CiboCompoundCapitalError(
                    "GEN-C8 population contains pre-freeze decision"
                )
            if self.last_decision_at < self.first_decision_at:
                raise CiboCompoundCapitalError(
                    "GEN-C8 population decision range is reversed"
                )
        if len(self.account_keys) != len(set(self.account_keys)):
            raise CiboCompoundCapitalError(
                "GEN-C8 population account keys must be unique"
            )
        blocker_keys = tuple(item[0] for item in self.blocker_counts)
        if len(blocker_keys) != len(set(blocker_keys)):
            raise CiboCompoundCapitalError(
                "GEN-C8 population blocker keys must be unique"
            )
        for key, count in self.blocker_counts:
            if (
                not key
                or not isinstance(count, int)
                or isinstance(count, bool)
                or count <= 0
            ):
                raise CiboCompoundCapitalError(
                    "GEN-C8 population blocker counts are invalid"
                )
        for name in (
            "descriptive_only",
            "real_outcome_binding_complete",
            "economic_utility_ready",
            "stress_pass",
            "temporal_replication_pass",
            "certification_ready",
        ):
            if type(getattr(self, name)) is not bool:
                raise CiboCompoundCapitalError(
                    f"GEN-C8 population {name} must be bool"
                )
        if (
            not self.descriptive_only
            or self.real_outcome_binding_complete
            or self.economic_utility_ready
            or self.stress_pass
            or self.temporal_replication_pass
            or self.certification_ready
        ):
            raise CiboCompoundCapitalError(
                "GEN-C8 descriptive population cannot claim scientific pass"
            )


def describe_genc8_population(
    *,
    book: VersionedGenc8ShadowBook,
) -> Genc8PopulationReport:
    if not isinstance(book, VersionedGenc8ShadowBook):
        raise CiboCompoundCapitalError(
            "GEN-C8 population requires canonical durable book"
        )
    seals: list[Genc8ShadowDecisionSeal] = []
    for record in book.records:
        seal = book.seal_for_decision(record.decision_id)
        if seal is None:
            raise CiboCompoundCapitalError(
                "GEN-C8 durable decision seal missing"
            )
        seals.append(seal)

    if not seals:
        return Genc8PopulationReport(
            status=Genc8PopulationStatus.EMPTY,
            policy_id=GENC8_POLICY_ID,
            policy_sha256=genc8_policy_sha256(),
            policy_frozen_at=GENC8_POLICY_FROZEN_AT,
            decision_count=0,
            treatment_control_divergence_count=0,
            pause_count=0,
            defensive_count=0,
            cautious_count=0,
            normal_count=0,
            accelerated_count=0,
            first_decision_at=None,
            last_decision_at=None,
            calendar_span_days=0,
            decision_calendar_days=0,
            account_keys=(),
            blocker_counts=(),
            descriptive_only=True,
            real_outcome_binding_complete=False,
            economic_utility_ready=False,
            stress_pass=False,
            temporal_replication_pass=False,
            certification_ready=False,
        )

    ordered = tuple(sorted(seals, key=lambda item: item.decision_at))
    first = ordered[0].decision_at
    last = ordered[-1].decision_at
    actions = tuple(item.treatment_posture for item in ordered)
    blockers = Counter(
        blocker
        for item in ordered
        for blocker in item.blocker_codes
    )

    return Genc8PopulationReport(
        status=Genc8PopulationStatus.COLLECTING,
        policy_id=GENC8_POLICY_ID,
        policy_sha256=genc8_policy_sha256(),
        policy_frozen_at=GENC8_POLICY_FROZEN_AT,
        decision_count=len(ordered),
        treatment_control_divergence_count=sum(
            1 for item in ordered if item.treatment_differs_from_control
        ),
        pause_count=actions.count(Genc8SpeedPosture.PAUSE),
        defensive_count=actions.count(Genc8SpeedPosture.DEFENSIVE),
        cautious_count=actions.count(Genc8SpeedPosture.CAUTIOUS),
        normal_count=actions.count(Genc8SpeedPosture.NORMAL),
        accelerated_count=actions.count(Genc8SpeedPosture.ACCELERATED),
        first_decision_at=first,
        last_decision_at=last,
        calendar_span_days=(last.date() - first.date()).days + 1,
        decision_calendar_days=len(
            {item.decision_at.date() for item in ordered}
        ),
        account_keys=tuple(
            sorted(
                {
                    f"{item.account_provider_key}:{item.account_ref}"
                    for item in ordered
                }
            )
        ),
        blocker_counts=tuple(sorted(blockers.items())),
        descriptive_only=True,
        real_outcome_binding_complete=False,
        economic_utility_ready=False,
        stress_pass=False,
        temporal_replication_pass=False,
        certification_ready=False,
    )


def _aware(value: datetime, name: str) -> None:
    if (
        not isinstance(value, datetime)
        or value.tzinfo is None
        or value.utcoffset() is None
    ):
        raise CiboCompoundCapitalError(
            f"GEN-C8 population {name} must be timezone-aware"
        )
