from __future__ import annotations

import dataclasses
from datetime import UTC, datetime
from decimal import Decimal
from typing import cast

import pytest
from _governed_evidence_fixtures import dependent_evidence

from qore.infrastructure.cibo.contracts import (
    CiboEvidenceStatus,
    CiboFunctionalEvidence,
    CiboFunctionalValidationError,
    CiboGovernedEvidenceKind,
)
from qore.infrastructure.cibo.quantitative_intelligence import (
    CiboQuantitativeIntelligence,
    CiboQuantRequest,
    CiboQuantResult,
    CiboQuantTool,
)
from qore.infrastructure.cibo_trader_capability_profile import CiboEvidenceRef
from qore.kernel.result import Failure

_NOW = datetime(2026, 8, 9, 0, 0, tzinfo=UTC)
_INTEL = CiboQuantitativeIntelligence()


def _ref(name: str = "evidence:quant-input") -> CiboEvidenceRef:
    return CiboEvidenceRef(name)


def _dependent_evidence() -> CiboFunctionalEvidence:
    return dependent_evidence(
        CiboGovernedEvidenceKind.ECONOMIC,
        evidence_refs=(_ref(),),
        as_of=_NOW,
        reasons=("external.authority.required",),
    )


def _insufficient_evidence() -> CiboFunctionalEvidence:
    return CiboFunctionalEvidence(
        status=CiboEvidenceStatus.INSUFFICIENT,
        evidence_refs=(),
        as_of=_NOW,
        reasons=("not-enough-data",),
    )


def _request(
    *,
    parameters: tuple[tuple[str, str], ...] = (("window", "252"),),
    requested_at: datetime = _NOW,
) -> CiboQuantRequest:
    return CiboQuantRequest(
        request_code="quant.request.volatility",
        tool=CiboQuantTool.OPTION_VOLATILITY,
        input_refs=(_ref(),),
        parameters=parameters,
        requested_at=requested_at,
    )


def test_quant_tool_catalog_is_complete() -> None:
    expected = {
        "probability-statistics",
        "time-series",
        "distributions",
        "dependence-correlation",
        "portfolio-math",
        "option-volatility",
        "monte-carlo-bootstrap",
        "hypothesis-test",
        "regime-anomaly",
        "robustness-overfit-cost",
    }
    assert {tool.value for tool in CiboQuantTool} == expected


def test_dispatch_rejects_dependent_evidence() -> None:
    # Correction 003: an authoritative quant result requires SUFFICIENT
    # (authority-rooted) evidence, which CIBO cannot manufacture; the dispatcher
    # fails closed on evidence-dependent input.
    result = _INTEL.dispatch(
        _request(),
        result_code="quant.result.volatility",
        exact_value=Decimal("0.0421"),
        evidence=_dependent_evidence(),
        computed_at=_NOW,
    )
    assert isinstance(result, Failure)
    assert isinstance(result.error, CiboFunctionalValidationError)


@pytest.mark.parametrize("key", ["provider", "model", "rng", "seed", "retry", "sleep"])
def test_request_rejects_forbidden_parameter_key(key: str) -> None:
    with pytest.raises(CiboFunctionalValidationError):
        _request(parameters=((key, "value"),))


def test_dispatch_rejects_insufficient_evidence() -> None:
    result = _INTEL.dispatch(
        _request(),
        result_code="quant.result.volatility",
        exact_value=Decimal("0.0421"),
        evidence=_insufficient_evidence(),
        computed_at=_NOW,
    )
    assert isinstance(result, Failure)
    assert isinstance(result.error, CiboFunctionalValidationError)


def test_dispatch_rejects_wrong_request_type() -> None:
    result = _INTEL.dispatch(
        cast(CiboQuantRequest, object()),
        result_code="quant.result.volatility",
        exact_value=Decimal("0.0421"),
        evidence=_dependent_evidence(),
        computed_at=_NOW,
    )
    assert isinstance(result, Failure)
    assert isinstance(result.error, CiboFunctionalValidationError)


def test_result_requires_authority_rooted_evidence() -> None:
    # A quant result cannot be minted without SUFFICIENT evidence; the only
    # evidence-bearing conclusion CIBO can construct is EVIDENCE_DEPENDENT.
    with pytest.raises(CiboFunctionalValidationError):
        CiboQuantResult(
            request=_request(),
            result_code="quant.result.volatility",
            exact_value=Decimal("0.0421"),
            evidence=_dependent_evidence(),
            computed_at=_NOW,
        )


def test_request_has_no_provider_or_model_field() -> None:
    fields = {field.name for field in dataclasses.fields(CiboQuantRequest)}
    for forbidden in ("provider", "model", "rng", "seed", "retry", "sleep"):
        assert forbidden not in fields


def test_intelligence_grants_no_execution_or_risk_authority() -> None:
    assert not hasattr(_INTEL, "execute")
    assert not hasattr(_INTEL, "place_order")
    assert not hasattr(_INTEL, "authorize_risk")
    assert not hasattr(_INTEL, "decide")
