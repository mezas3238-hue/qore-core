"""CF-07 — Economic / Profitability Intelligence.

CIBO assesses economic performance only from explicit, sufficient evidence. When
evidence is not sufficient no profitability number may be asserted: the assessment
is ``INSUFFICIENT_EVIDENCE`` with every metric ``None``. Fabricated P&L is rejected.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import StrEnum

from qore.infrastructure.cibo.contracts import (
    CiboEvidenceStatus,
    CiboFunctionalError,
    CiboFunctionalEvidence,
    CiboFunctionalValidationError,
    _validate_evidence_refs,
    _validate_timestamp,
)
from qore.infrastructure.cibo_trader_capability_profile import CiboEvidenceRef
from qore.kernel.result import Failure, Result, Success

_METRIC_FIELDS = frozenset(
    {"gross_pnl", "net_pnl", "expectancy", "drawdown", "costs", "risk_adjusted"}
)


class CiboEconomicStatus(StrEnum):
    """Economic assessment status; never a fabricated profitability claim."""

    SUFFICIENT_EVIDENCE = "sufficient-evidence"
    INSUFFICIENT_EVIDENCE = "insufficient-evidence"


def _validate_decimal(value: Decimal, *, field_name: str) -> None:
    if not isinstance(value, Decimal) or not value.is_finite():
        raise CiboFunctionalValidationError(f"{field_name} must be a finite Decimal")


def _decimal_logical(value: Decimal | None) -> str | None:
    if value is None:
        return None
    normalized = Decimal(0) if value == 0 else value.normalize()
    return format(normalized, "f")


def _revalidate_evidence(evidence: CiboFunctionalEvidence) -> None:
    try:
        CiboFunctionalEvidence.__post_init__(evidence)
    except CiboFunctionalError:
        raise
    except (AttributeError, TypeError):
        raise CiboFunctionalValidationError(
            "evidence must be a valid CiboFunctionalEvidence"
        ) from None


def _validate_metrics(metrics: dict[str, Decimal]) -> dict[str, Decimal]:
    if not isinstance(metrics, dict):
        raise CiboFunctionalValidationError("metrics must be a dict of economic values")
    result: dict[str, Decimal] = {}
    for key, value in metrics.items():
        if not isinstance(key, str) or key not in _METRIC_FIELDS:
            raise CiboFunctionalValidationError(
                "metrics must use known economic metric codes"
            )
        _validate_decimal(value, field_name=f"metric {key}")
        result[key] = value
    return result


@dataclass(frozen=True, slots=True)
class CiboEconomicAssessment:
    """Evidence-backed economic assessment; abstains rather than fabricate P&L."""

    status: CiboEconomicStatus
    gross_pnl: Decimal | None
    net_pnl: Decimal | None
    expectancy: Decimal | None
    drawdown: Decimal | None
    costs: Decimal | None
    risk_adjusted: Decimal | None
    attribution_refs: tuple[CiboEvidenceRef, ...]
    evidence: CiboFunctionalEvidence
    assessed_at: datetime

    def __post_init__(self) -> None:
        if type(self.status) is not CiboEconomicStatus:
            raise CiboFunctionalValidationError(
                "economic assessment requires CiboEconomicStatus"
            )
        metrics = (
            ("gross_pnl", self.gross_pnl),
            ("net_pnl", self.net_pnl),
            ("expectancy", self.expectancy),
            ("drawdown", self.drawdown),
            ("costs", self.costs),
            ("risk_adjusted", self.risk_adjusted),
        )
        for name, value in metrics:
            if value is not None:
                _validate_decimal(value, field_name=name)
        object.__setattr__(
            self,
            "attribution_refs",
            _validate_evidence_refs(self.attribution_refs, field_name="attribution refs"),
        )
        if not isinstance(self.evidence, CiboFunctionalEvidence):
            raise CiboFunctionalValidationError(
                "economic assessment requires CiboFunctionalEvidence"
            )
        _revalidate_evidence(self.evidence)
        _validate_timestamp(self.assessed_at, field_name="economic assessed_at")
        present = tuple(value is not None for _, value in metrics)
        if self.status is CiboEconomicStatus.SUFFICIENT_EVIDENCE:
            if not any(present):
                raise CiboFunctionalValidationError(
                    "sufficient economic assessment requires at least one metric"
                )
            if self.evidence.status is not CiboEvidenceStatus.SUFFICIENT:
                raise CiboFunctionalValidationError(
                    "sufficient economic assessment requires sufficient evidence"
                )
            if not self.attribution_refs:
                raise CiboFunctionalValidationError(
                    "sufficient economic assessment requires attribution refs"
                )
            return
        if any(present):
            raise CiboFunctionalValidationError(
                "insufficient economic assessment must not fabricate metrics"
            )

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.status.value,
            _decimal_logical(self.gross_pnl),
            _decimal_logical(self.net_pnl),
            _decimal_logical(self.expectancy),
            _decimal_logical(self.drawdown),
            _decimal_logical(self.costs),
            _decimal_logical(self.risk_adjusted),
            tuple(item.logical_values() for item in self.attribution_refs),
            self.evidence.logical_values(),
            self.assessed_at.isoformat(),
        )


@dataclass(frozen=True, slots=True)
class CiboEconomicIntelligence:
    """Deterministic, stateless economic intelligence."""

    def assess(
        self,
        *,
        metrics: dict[str, Decimal],
        evidence: CiboFunctionalEvidence,
        attribution_refs: tuple[CiboEvidenceRef, ...],
        assessed_at: datetime,
    ) -> Result[CiboEconomicAssessment, CiboFunctionalError]:
        """Assess economics from supplied metrics; reject fabricated P&L.

        A non-empty metric map requires sufficient evidence; without it the
        metrics would be fabricated and the assessment fails closed. An empty
        metric map yields an ``INSUFFICIENT_EVIDENCE`` assessment with all metrics
        ``None``.
        """
        if not isinstance(evidence, CiboFunctionalEvidence):
            return Failure(
                CiboFunctionalValidationError("evidence must be CiboFunctionalEvidence")
            )
        try:
            _revalidate_evidence(evidence)
            normalized_refs = _validate_evidence_refs(
                attribution_refs,
                field_name="attribution refs",
            )
            normalized_metrics = _validate_metrics(metrics)
            _validate_timestamp(assessed_at, field_name="assessed_at")
        except CiboFunctionalError as error:
            return Failure(error)
        if normalized_metrics:
            if evidence.status is not CiboEvidenceStatus.SUFFICIENT:
                return Failure(
                    CiboFunctionalValidationError(
                        "fabricated economic metrics rejected without sufficient evidence"
                    )
                )
            status = CiboEconomicStatus.SUFFICIENT_EVIDENCE
        else:
            status = CiboEconomicStatus.INSUFFICIENT_EVIDENCE
        try:
            return Success(
                CiboEconomicAssessment(
                    status=status,
                    gross_pnl=normalized_metrics.get("gross_pnl"),
                    net_pnl=normalized_metrics.get("net_pnl"),
                    expectancy=normalized_metrics.get("expectancy"),
                    drawdown=normalized_metrics.get("drawdown"),
                    costs=normalized_metrics.get("costs"),
                    risk_adjusted=normalized_metrics.get("risk_adjusted"),
                    attribution_refs=normalized_refs,
                    evidence=evidence,
                    assessed_at=assessed_at,
                )
            )
        except CiboFunctionalError as error:
            return Failure(error)
