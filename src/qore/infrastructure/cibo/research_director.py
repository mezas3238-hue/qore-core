"""CF-11 Research Director: deterministic forward-only scientific experimentation.

The Research Director advances a research plan along a fixed lineage of stages
only with explicit evidence. It can never self-promote: there is no DEMO_ELIGIBLE
state on this contract, and the terminal DEMO stage is a lineage stage that still
requires sufficient evidence, not an eligibility grant.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from re import fullmatch

from qore.infrastructure.cibo.contracts import (
    CiboEvidenceStatus,
    CiboFunctionalBlockedError,
    CiboFunctionalError,
    CiboFunctionalEvidence,
    CiboFunctionalValidationError,
)
from qore.infrastructure.cibo_trader_capability_profile import CiboEvidenceRef
from qore.kernel.result import Failure, Result, Success

_CODE_RE = r"[a-z][a-z0-9._-]*"
_SENSITIVE_PARTS = (
    "authorization:",
    "bearer ",
    "client_secret",
    "password=",
    "private_key",
    "secret=",
    "token=",
)


class CiboResearchStage(StrEnum):
    """The research lineage from observation to demo. There is no DEMO_ELIGIBLE stage."""

    OBSERVATION = "observation"
    HYPOTHESIS = "hypothesis"
    FORMALIZATION = "formalization"
    DATA = "data"
    EXPERIMENT = "experiment"
    REPLAY_BACKTEST = "replay-backtest"
    ADVERSARIAL = "adversarial"
    OOS = "oos"
    STRESS = "stress"
    MONTE_CARLO = "monte-carlo"
    ECONOMIC = "economic"
    TRADER_LAB = "trader-lab"
    DEMO = "demo"


_STAGE_ORDER = {stage: index for index, stage in enumerate(CiboResearchStage)}
_SUFFICIENT_REQUIRED_STAGES = frozenset(
    {CiboResearchStage.TRADER_LAB, CiboResearchStage.DEMO}
)


def _validate_timestamp(value: datetime, *, field_name: str) -> None:
    if type(value) is not datetime:
        raise CiboFunctionalValidationError(f"{field_name} must be a datetime")
    if value.tzinfo is None or value.utcoffset() is None:
        raise CiboFunctionalValidationError(f"{field_name} must be timezone-aware")


def _validate_code(value: str, *, field_name: str) -> str:
    if not isinstance(value, str) or fullmatch(_CODE_RE, value) is None:
        raise CiboFunctionalValidationError(
            f"{field_name} must use canonical lowercase syntax"
        )
    if any(part in value for part in _SENSITIVE_PARTS):
        raise CiboFunctionalValidationError(
            f"{field_name} must not contain sensitive material"
        )
    return value


def _validate_data_requirements(
    values: tuple[CiboEvidenceRef, ...],
    *,
    field_name: str,
) -> tuple[CiboEvidenceRef, ...]:
    if not isinstance(values, tuple) or any(
        not isinstance(item, CiboEvidenceRef) for item in values
    ):
        raise CiboFunctionalValidationError(
            f"{field_name} must be a tuple of CiboEvidenceRef"
        )
    if len(set(values)) != len(values):
        raise CiboFunctionalValidationError(f"{field_name} must not contain duplicates")
    return tuple(sorted(values, key=lambda item: item.value))


@dataclass(frozen=True, slots=True)
class CiboResearchPlan:
    """An immutable research plan bound to a hypothesis, data needs, stage and evidence."""

    plan_code: str
    question_code: str
    hypothesis_code: str
    data_requirements: tuple[CiboEvidenceRef, ...]
    stage: CiboResearchStage
    evidence: CiboFunctionalEvidence
    updated_at: datetime

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "plan_code",
            _validate_code(self.plan_code, field_name="research plan code"),
        )
        object.__setattr__(
            self,
            "question_code",
            _validate_code(self.question_code, field_name="research question code"),
        )
        object.__setattr__(
            self,
            "hypothesis_code",
            _validate_code(self.hypothesis_code, field_name="research hypothesis code"),
        )
        object.__setattr__(
            self,
            "data_requirements",
            _validate_data_requirements(
                self.data_requirements,
                field_name="research data requirements",
            ),
        )
        if type(self.stage) is not CiboResearchStage:
            raise CiboFunctionalValidationError(
                "research plan requires CiboResearchStage"
            )
        if not isinstance(self.evidence, CiboFunctionalEvidence):
            raise CiboFunctionalValidationError(
                "research plan requires CiboFunctionalEvidence"
            )
        CiboFunctionalEvidence.__post_init__(self.evidence)
        _validate_timestamp(self.updated_at, field_name="research updated_at")
        if (
            self.stage in _SUFFICIENT_REQUIRED_STAGES
            and self.evidence.status is not CiboEvidenceStatus.SUFFICIENT
        ):
            raise CiboFunctionalValidationError(
                "trader-lab/demo stage requires sufficient evidence"
            )

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.plan_code,
            self.question_code,
            self.hypothesis_code,
            tuple(item.logical_values() for item in self.data_requirements),
            self.stage.value,
            self.evidence.logical_values(),
            self.updated_at.isoformat(),
        )


@dataclass(frozen=True, slots=True)
class CiboResearchDirector:
    """Deterministic, stateless research-director orchestration.

    It only advances stages forward with explicit evidence, never backward, and it
    can never emit a DEMO_ELIGIBLE result: DEMO is a terminal lineage stage, not an
    eligibility grant.
    """

    def advance(
        self,
        plan: CiboResearchPlan,
        *,
        to_stage: CiboResearchStage,
        evidence: CiboFunctionalEvidence,
        updated_at: datetime,
    ) -> Result[CiboResearchPlan, CiboFunctionalError]:
        """Advance a research plan forward one or more stages with explicit evidence."""
        if not isinstance(plan, CiboResearchPlan):
            return Failure(
                CiboFunctionalValidationError("research advance requires CiboResearchPlan")
            )
        if type(to_stage) is not CiboResearchStage:
            return Failure(
                CiboFunctionalValidationError("research advance requires CiboResearchStage")
            )
        try:
            CiboResearchPlan.__post_init__(plan)
            if not isinstance(evidence, CiboFunctionalEvidence):
                raise CiboFunctionalValidationError(
                    "research advance requires CiboFunctionalEvidence"
                )
            CiboFunctionalEvidence.__post_init__(evidence)
            _validate_timestamp(updated_at, field_name="research updated_at")
            if updated_at < plan.updated_at:
                raise CiboFunctionalValidationError(
                    "research stage cannot move backward in time"
                )
            if _STAGE_ORDER[to_stage] < _STAGE_ORDER[plan.stage]:
                raise CiboFunctionalBlockedError("research stage cannot move backward")
            if (
                to_stage in _SUFFICIENT_REQUIRED_STAGES
                and evidence.status is not CiboEvidenceStatus.SUFFICIENT
            ):
                raise CiboFunctionalBlockedError(
                    "trader-lab/demo advancement requires sufficient evidence"
                )
            return Success(
                CiboResearchPlan(
                    plan_code=plan.plan_code,
                    question_code=plan.question_code,
                    hypothesis_code=plan.hypothesis_code,
                    data_requirements=plan.data_requirements,
                    stage=to_stage,
                    evidence=evidence,
                    updated_at=updated_at,
                )
            )
        except CiboFunctionalError as error:
            return Failure(error)

    def logical_values(self) -> tuple[object, ...]:
        return ()
