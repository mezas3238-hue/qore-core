from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

import pytest

from qore.infrastructure.cibo_trader_capability_profile import (
    CiboCapabilityProfileError,
    CiboCapabilityProfileValidationError,
    CiboCertificationState,
    CiboEconomicMetric,
    CiboEvidenceFreshness,
    CiboEvidenceFreshnessState,
    CiboEvidenceRef,
    CiboLabEvidenceRef,
    CiboLabEvidenceStage,
    CiboOperatingAction,
    CiboOperatingCondition,
    CiboRegimeEvidenceRef,
    CiboRegimeKind,
    CiboSpecialtyCode,
    CiboTimeframeCode,
    CiboTradeableMarketRef,
    CiboTraderCapabilityProfile,
    CiboTraderConfigFingerprint,
    build_cibo_trader_capability_profile,
)
from qore.infrastructure.research_evaluator_identity import (
    ResearchDecisionEvaluatorFamily,
    ResearchDecisionEvaluatorIdentity,
    ResearchDecisionEvaluatorSchemaVersion,
)
from qore.infrastructure.research_run import ResearchSoftwareRevision
from qore.kernel.result import Failure, Result, Success

_NOW = datetime(2026, 8, 9, 0, 0, tzinfo=UTC)


def _identity(suffix: str = "vt01") -> ResearchDecisionEvaluatorIdentity:
    return ResearchDecisionEvaluatorIdentity(
        family=ResearchDecisionEvaluatorFamily(f"virtual.trader.{suffix}"),
        schema_version=ResearchDecisionEvaluatorSchemaVersion("v1"),
        software_revision=ResearchSoftwareRevision("rev-1"),
    )


def _fingerprint(n: int = 1) -> CiboTraderConfigFingerprint:
    return CiboTraderConfigFingerprint(f"{n:064x}")


def _ref(value: str) -> CiboEvidenceRef:
    return CiboEvidenceRef(value)


def _build_profile(**overrides: Any) -> Result[
    CiboTraderCapabilityProfile,
    CiboCapabilityProfileError,
]:
    kwargs: dict[str, Any] = {
        "trader_identity": _identity(),
        "config_fingerprint": _fingerprint(),
        "specialty": CiboSpecialtyCode("trend-following"),
        "qualified_markets": (
            CiboTradeableMarketRef("EUR/USD"),
            CiboTradeableMarketRef("GBP/USD"),
        ),
        "qualified_timeframes": (
            CiboTimeframeCode("h1"),
            CiboTimeframeCode("d1"),
        ),
        "certification_state": CiboCertificationState.EVIDENCE_COLLECTED,
        "freshness": CiboEvidenceFreshness(
            state=CiboEvidenceFreshnessState.CURRENT,
            as_of=_NOW,
        ),
    }
    kwargs.update(overrides)
    return build_cibo_trader_capability_profile(**kwargs)


def _profile(**overrides: Any) -> CiboTraderCapabilityProfile:
    result = _build_profile(**overrides)
    assert isinstance(result, Success)
    return result.value


def test_valid_exact_capability_profile() -> None:
    profile = _profile()
    assert profile.trader_identity.family.value == "virtual.trader.vt01"
    assert profile.config_fingerprint.value == f"{1:064x}"
    assert profile.certification_state is CiboCertificationState.EVIDENCE_COLLECTED


def test_wrong_identity_type_rejected() -> None:
    result = build_cibo_trader_capability_profile(
        trader_identity="not-an-identity",  # type: ignore[arg-type]
        config_fingerprint=_fingerprint(),
        specialty=CiboSpecialtyCode("trend-following"),
        qualified_markets=(CiboTradeableMarketRef("EUR/USD"),),
        qualified_timeframes=(CiboTimeframeCode("h1"),),
        certification_state=CiboCertificationState.EVIDENCE_COLLECTED,
        freshness=CiboEvidenceFreshness(
            state=CiboEvidenceFreshnessState.CURRENT,
            as_of=_NOW,
        ),
    )
    assert isinstance(result, Failure)
    assert isinstance(result.error, CiboCapabilityProfileValidationError)


def test_wrong_config_fingerprint_type_rejected() -> None:
    result = build_cibo_trader_capability_profile(
        trader_identity=_identity(),
        config_fingerprint="a" * 64,  # type: ignore[arg-type]
        specialty=CiboSpecialtyCode("trend-following"),
        qualified_markets=(CiboTradeableMarketRef("EUR/USD"),),
        qualified_timeframes=(CiboTimeframeCode("h1"),),
        certification_state=CiboCertificationState.EVIDENCE_COLLECTED,
        freshness=CiboEvidenceFreshness(
            state=CiboEvidenceFreshnessState.CURRENT,
            as_of=_NOW,
        ),
    )
    assert isinstance(result, Failure)
    assert isinstance(result.error, CiboCapabilityProfileValidationError)


def test_markets_must_be_tuple_not_list() -> None:
    result = _build_profile(qualified_markets=[CiboTradeableMarketRef("EUR/USD")])
    assert isinstance(result, Failure)
    assert isinstance(result.error, CiboCapabilityProfileValidationError)


def test_canonical_ordering_of_markets() -> None:
    profile = _profile(
        qualified_markets=(
            CiboTradeableMarketRef("GBP/USD"),
            CiboTradeableMarketRef("EUR/USD"),
        ),
    )
    assert tuple(m.value for m in profile.qualified_markets) == ("EUR/USD", "GBP/USD")


def test_canonical_ordering_of_lab_evidence() -> None:
    profile = _profile(
        certified_lab_evidence=(
            CiboLabEvidenceRef(CiboLabEvidenceStage.OOS, _ref("evidence:oos")),
            CiboLabEvidenceRef(CiboLabEvidenceStage.REPLAY, _ref("evidence:replay")),
        ),
    )
    assert tuple(e.stage for e in profile.certified_lab_evidence) == (
        CiboLabEvidenceStage.REPLAY,
        CiboLabEvidenceStage.OOS,
    )


def test_duplicate_market_rejected() -> None:
    result = _build_profile(
        qualified_markets=(
            CiboTradeableMarketRef("EUR/USD"),
            CiboTradeableMarketRef("EUR/USD"),
        ),
    )
    assert isinstance(result, Failure)
    assert isinstance(result.error, CiboCapabilityProfileValidationError)


def test_duplicate_lab_evidence_rejected() -> None:
    result = _build_profile(
        certified_lab_evidence=(
            CiboLabEvidenceRef(CiboLabEvidenceStage.OOS, _ref("evidence:oos")),
            CiboLabEvidenceRef(CiboLabEvidenceStage.OOS, _ref("evidence:oos")),
        ),
    )
    assert isinstance(result, Failure)
    assert isinstance(result.error, CiboCapabilityProfileValidationError)


def test_economic_metric_requires_certified_backing() -> None:
    result = _build_profile(
        economic_metrics=(
            CiboEconomicMetric(
                metric_code="net-sharpe",
                value=Decimal("1.5"),
                evidence_ref=_ref("evidence:economic-unbacked"),
            ),
        ),
    )
    assert isinstance(result, Failure)
    assert isinstance(result.error, CiboCapabilityProfileValidationError)


def test_economic_metric_with_certified_backing_ok() -> None:
    economic = _ref("evidence:economic")
    profile = _profile(
        certified_lab_evidence=(
            CiboLabEvidenceRef(CiboLabEvidenceStage.ECONOMIC, economic),
        ),
        economic_metrics=(
            CiboEconomicMetric(
                metric_code="net-sharpe",
                value=Decimal("1.5"),
                evidence_ref=economic,
            ),
        ),
    )
    assert profile.economic_metrics[0].value == Decimal("1.5")


def test_economic_metric_value_must_be_decimal_not_float() -> None:
    economic = _ref("evidence:economic")
    with pytest.raises(CiboCapabilityProfileValidationError):
        _profile(
            certified_lab_evidence=(
                CiboLabEvidenceRef(CiboLabEvidenceStage.ECONOMIC, economic),
            ),
            economic_metrics=(
                CiboEconomicMetric(
                    metric_code="net-sharpe",
                    value=1.5,  # type: ignore[arg-type]
                    evidence_ref=economic,
                ),
            ),
        )


def test_bool_does_not_launder_as_int_in_fingerprint_domain() -> None:
    # Fingerprint is an exact str value object; a bool/int cannot satisfy it.
    with pytest.raises(CiboCapabilityProfileValidationError):
        CiboTraderConfigFingerprint(True)  # type: ignore[arg-type]


def test_evidence_ref_rejects_sensitive_material() -> None:
    with pytest.raises(CiboCapabilityProfileValidationError):
        CiboEvidenceRef("evidence:token=abc123")


def test_profile_cannot_manufacture_demo_eligible() -> None:
    # DEMO_ELIGIBLE does not exist on the profile's certification state enum.
    profile = _profile(certification_state=CiboCertificationState.PROMOTION_RECOMMENDED)
    assert not hasattr(CiboCertificationState, "DEMO_ELIGIBLE")
    assert profile.certification_state is CiboCertificationState.PROMOTION_RECOMMENDED


def test_deterministic_equality_for_identical_inputs() -> None:
    left = _profile(
        qualified_markets=(
            CiboTradeableMarketRef("GBP/USD"),
            CiboTradeableMarketRef("EUR/USD"),
        ),
    )
    right = _profile(
        qualified_markets=(
            CiboTradeableMarketRef("EUR/USD"),
            CiboTradeableMarketRef("GBP/USD"),
        ),
    )
    assert left == right
    assert left.logical_values() == right.logical_values()


def test_regime_and_operating_conditions_retained() -> None:
    regime = CiboRegimeEvidenceRef(CiboRegimeKind.WEAK, _ref("evidence:regime-weak"))
    suspend = CiboOperatingCondition(
        action=CiboOperatingAction.SUSPEND,
        reason_code="evidence-degraded",
        evidence_ref=_ref("evidence:degraded"),
    )
    profile = _profile(
        regime_evidence=(regime,),
        operating_conditions=(suspend,),
        limitations=("insufficient-monitoring",),
    )
    assert profile.regime_evidence == (regime,)
    assert profile.operating_conditions == (suspend,)
    assert profile.limitations == ("insufficient-monitoring",)


def test_failure_result_from_builder() -> None:
    result = build_cibo_trader_capability_profile(
        trader_identity=_identity(),
        config_fingerprint=_fingerprint(),
        specialty=CiboSpecialtyCode("trend-following"),
        qualified_markets=(),  # empty -> invalid
        qualified_timeframes=(CiboTimeframeCode("h1"),),
        certification_state=CiboCertificationState.EVIDENCE_COLLECTED,
        freshness=CiboEvidenceFreshness(
            state=CiboEvidenceFreshnessState.CURRENT,
            as_of=_NOW,
        ),
    )
    assert isinstance(result, Failure)


def test_success_result_from_builder() -> None:
    result = build_cibo_trader_capability_profile(
        trader_identity=_identity(),
        config_fingerprint=_fingerprint(),
        specialty=CiboSpecialtyCode("trend-following"),
        qualified_markets=(CiboTradeableMarketRef("EUR/USD"),),
        qualified_timeframes=(CiboTimeframeCode("h1"),),
        certification_state=CiboCertificationState.EVIDENCE_COLLECTED,
        freshness=CiboEvidenceFreshness(
            state=CiboEvidenceFreshnessState.CURRENT,
            as_of=_NOW,
        ),
    )
    assert isinstance(result, Success)
    assert isinstance(result.value, CiboTraderCapabilityProfile)
