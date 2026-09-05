"""CF-10 Quantitative Intelligence: provider-neutral deterministic exact computation.

This module is an orchestration boundary only. It binds a fully-specified,
deterministic quantitative request to a pre-computed exact ``Decimal`` result and
certified evidence. It performs no statistical math of its own, consults no
provider, uses no random source, and grants no execution authority: a quantitative
result is an observation, never an order or a Risk decision.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from re import fullmatch

from qore.infrastructure.cibo.contracts import (
    CiboEvidenceStatus,
    CiboFunctionalError,
    CiboFunctionalEvidence,
    CiboFunctionalValidationError,
)
from qore.infrastructure.cibo_trader_capability_profile import CiboEvidenceRef
from qore.kernel.result import Failure, Result, Success

_CODE_RE = r"[a-z][a-z0-9._-]*"
_PARAM_VALUE_RE = r"[a-z0-9][a-z0-9._:+-]*"
_SENSITIVE_PARTS = (
    "authorization:",
    "bearer ",
    "client_secret",
    "password=",
    "private_key",
    "secret=",
    "token=",
)
_FORBIDDEN_PARAM_KEY_PARTS = ("provider", "model", "rng", "seed", "retry", "sleep")


class CiboQuantTool(StrEnum):
    """Deterministic quantitative tool families; no provider/model selection is encoded."""

    PROBABILITY_STATISTICS = "probability-statistics"
    TIME_SERIES = "time-series"
    DISTRIBUTIONS = "distributions"
    DEPENDENCE_CORRELATION = "dependence-correlation"
    PORTFOLIO_MATH = "portfolio-math"
    OPTION_VOLATILITY = "option-volatility"
    MONTE_CARLO_BOOTSTRAP = "monte-carlo-bootstrap"
    HYPOTHESIS_TEST = "hypothesis-test"
    REGIME_ANOMALY = "regime-anomaly"
    ROBUSTNESS_OVERFIT_COST = "robustness-overfit-cost"


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


def _validate_input_refs(
    values: tuple[CiboEvidenceRef, ...],
    *,
    field_name: str,
) -> tuple[CiboEvidenceRef, ...]:
    if not isinstance(values, tuple) or not values or any(
        not isinstance(item, CiboEvidenceRef) for item in values
    ):
        raise CiboFunctionalValidationError(
            f"{field_name} must be a non-empty tuple of CiboEvidenceRef"
        )
    if len(set(values)) != len(values):
        raise CiboFunctionalValidationError(f"{field_name} must not contain duplicates")
    return tuple(sorted(values, key=lambda item: item.value))


def _validate_parameter(value: tuple[str, str], *, field_name: str) -> tuple[str, str]:
    if not isinstance(value, tuple) or len(value) != 2:
        raise CiboFunctionalValidationError(f"{field_name} must be a (key, value) pair")
    key, val = value
    if not isinstance(key, str) or not isinstance(val, str):
        raise CiboFunctionalValidationError(
            f"{field_name} must contain exactly two strings"
        )
    if fullmatch(_CODE_RE, key) is None:
        raise CiboFunctionalValidationError(
            f"{field_name} key must use canonical lowercase syntax"
        )
    lowered = key.lower()
    if any(part in lowered for part in _FORBIDDEN_PARAM_KEY_PARTS):
        raise CiboFunctionalValidationError(
            f"{field_name} key carries a forbidden provider/model/RNG field"
        )
    if any(part in lowered for part in _SENSITIVE_PARTS):
        raise CiboFunctionalValidationError(
            f"{field_name} key must not contain sensitive material"
        )
    if fullmatch(_PARAM_VALUE_RE, val) is None:
        raise CiboFunctionalValidationError(
            f"{field_name} value must use canonical token syntax"
        )
    if any(part in val.lower() for part in _SENSITIVE_PARTS):
        raise CiboFunctionalValidationError(
            f"{field_name} value must not contain sensitive material"
        )
    return (key, val)


def _validate_parameters(
    values: tuple[tuple[str, str], ...],
    *,
    field_name: str,
) -> tuple[tuple[str, str], ...]:
    if not isinstance(values, tuple):
        raise CiboFunctionalValidationError(f"{field_name} must be a tuple")
    normalized = tuple(_validate_parameter(item, field_name=field_name) for item in values)
    keys = tuple(key for key, _ in normalized)
    if len(set(keys)) != len(keys):
        raise CiboFunctionalValidationError(f"{field_name} keys must be unique")
    return tuple(sorted(normalized, key=lambda item: (item[0], item[1])))


def _validate_exact_decimal(value: Decimal | None, *, field_name: str) -> Decimal:
    if not isinstance(value, Decimal) or not value.is_finite():
        raise CiboFunctionalValidationError(f"{field_name} must be a finite Decimal")
    return value


def _canonical_decimal(value: Decimal) -> str:
    normalized = Decimal(0) if value == 0 else value.normalize()
    return format(normalized, "f")


@dataclass(frozen=True, slots=True)
class CiboQuantRequest:
    """A deterministic, fully-specified quantitative computation request.

    Parameters are explicit ``(key, value)`` pairs only; there is no provider/model
    field and no random/seed/retry/sleep knob by construction. The actual math is
    supplied deterministically by the caller, never hidden inside this contract.
    """

    request_code: str
    tool: CiboQuantTool
    input_refs: tuple[CiboEvidenceRef, ...]
    parameters: tuple[tuple[str, str], ...]
    requested_at: datetime

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "request_code",
            _validate_code(self.request_code, field_name="quant request code"),
        )
        if type(self.tool) is not CiboQuantTool:
            raise CiboFunctionalValidationError("quant request requires CiboQuantTool")
        object.__setattr__(
            self,
            "input_refs",
            _validate_input_refs(self.input_refs, field_name="quant input refs"),
        )
        object.__setattr__(
            self,
            "parameters",
            _validate_parameters(self.parameters, field_name="quant parameters"),
        )
        _validate_timestamp(self.requested_at, field_name="quant requested_at")

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.request_code,
            self.tool.value,
            tuple(item.logical_values() for item in self.input_refs),
            self.parameters,
            self.requested_at.isoformat(),
        )


@dataclass(frozen=True, slots=True)
class CiboQuantResult:
    """An exact quantitative result bound to sufficient evidence.

    The exact ``Decimal`` value is required: prose substitution is not permitted,
    and the evidence must be SUFFICIENT for the result to be authoritative.
    """

    request: CiboQuantRequest
    result_code: str
    exact_value: Decimal | None
    evidence: CiboFunctionalEvidence
    computed_at: datetime

    def __post_init__(self) -> None:
        if not isinstance(self.request, CiboQuantRequest):
            raise CiboFunctionalValidationError("quant result requires CiboQuantRequest")
        CiboQuantRequest.__post_init__(self.request)
        object.__setattr__(
            self,
            "result_code",
            _validate_code(self.result_code, field_name="quant result code"),
        )
        _validate_exact_decimal(self.exact_value, field_name="quant exact value")
        if not isinstance(self.evidence, CiboFunctionalEvidence):
            raise CiboFunctionalValidationError(
                "quant result requires CiboFunctionalEvidence"
            )
        CiboFunctionalEvidence.__post_init__(self.evidence)
        if self.evidence.status is not CiboEvidenceStatus.SUFFICIENT:
            raise CiboFunctionalValidationError(
                "quant result requires sufficient evidence"
            )
        _validate_timestamp(self.computed_at, field_name="quant computed_at")
        if self.computed_at < self.request.requested_at:
            raise CiboFunctionalValidationError(
                "quant computed_at must not predate requested_at"
            )

    def logical_values(self) -> tuple[object, ...]:
        exact = _validate_exact_decimal(self.exact_value, field_name="quant exact value")
        return (
            self.request.logical_values(),
            self.result_code,
            _canonical_decimal(exact),
            self.evidence.logical_values(),
            self.computed_at.isoformat(),
        )


@dataclass(frozen=True, slots=True)
class CiboQuantitativeIntelligence:
    """Stateless, deterministic quantitative-intelligence orchestration.

    It accepts a pre-computed exact result and binds it to evidence; it performs no
    math, no provider call, and no random sampling. A request carrying a forbidden
    parameter key, a non-Decimal value, or a missing exact value is rejected.
    """

    def dispatch(
        self,
        request: CiboQuantRequest,
        *,
        result_code: str,
        exact_value: Decimal | None,
        evidence: CiboFunctionalEvidence,
        computed_at: datetime,
    ) -> Result[CiboQuantResult, CiboFunctionalError]:
        """Bind a pre-computed exact result to a deterministic request and evidence."""
        if not isinstance(request, CiboQuantRequest):
            return Failure(
                CiboFunctionalValidationError("quant dispatch requires CiboQuantRequest")
            )
        try:
            CiboQuantRequest.__post_init__(request)
            if not isinstance(evidence, CiboFunctionalEvidence):
                raise CiboFunctionalValidationError(
                    "quant dispatch requires CiboFunctionalEvidence"
                )
            CiboFunctionalEvidence.__post_init__(evidence)
            if evidence.status is not CiboEvidenceStatus.SUFFICIENT:
                raise CiboFunctionalValidationError(
                    "quant dispatch requires sufficient evidence"
                )
            exact = _validate_exact_decimal(exact_value, field_name="quant exact value")
            normalized_code = _validate_code(result_code, field_name="quant result code")
            _validate_timestamp(computed_at, field_name="quant computed_at")
            if computed_at < request.requested_at:
                raise CiboFunctionalValidationError(
                    "quant computed_at must not predate requested_at"
                )
            return Success(
                CiboQuantResult(
                    request=request,
                    result_code=normalized_code,
                    exact_value=exact,
                    evidence=evidence,
                    computed_at=computed_at,
                )
            )
        except CiboFunctionalError as error:
            return Failure(error)

    def logical_values(self) -> tuple[object, ...]:
        return ()
