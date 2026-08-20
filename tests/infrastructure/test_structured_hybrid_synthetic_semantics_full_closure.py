from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

import pytest

import qore.infrastructure.structured_hybrid_synthetic_semantics as structured
import qore.infrastructure.universal_instrument_identity as identity


def _economic_id(seed: int) -> identity.EconomicIdentityId:
    return identity.EconomicIdentityId(UUID(int=seed))


def _feature_id(seed: int) -> structured.StructuredFeatureId:
    return structured.StructuredFeatureId(UUID(int=seed))


def _evidence(seed: int) -> structured.StructuredEvidenceRef:
    return structured.StructuredEvidenceRef(UUID(int=seed))


def _relationship(
    root: identity.EconomicIdentityId,
    target: identity.EconomicIdentityId,
    *,
    relationship_id: int,
    code: str,
    ordinal: int | None,
    effective_until: datetime | None = None,
) -> identity.IdentityRelationship:
    return identity.IdentityRelationship(
        relationship_id=identity.IdentityRelationshipId(UUID(int=relationship_id)),
        source_identity_id=root,
        target_identity_id=target,
        relationship=identity.IdentityRelationshipCode(code),
        effective_from=datetime(2026, 1, 1, tzinfo=UTC),
        effective_until=effective_until,
        evidence_ref=identity.IdentityEvidenceRef(
            UUID(int=relationship_id + 10_000)
        ),
        ordinal=ordinal,
    )


def _component(
    root: identity.EconomicIdentityId,
    target: identity.EconomicIdentityId,
    *,
    relationship_id: int,
    code: str,
    role: str,
    ordinal: int | None,
    effective_until: datetime | None = None,
) -> structured.StructuredComponentBinding:
    return structured.StructuredComponentBinding(
        root_identity_id=root,
        relationship=_relationship(
            root,
            target,
            relationship_id=relationship_id,
            code=code,
            ordinal=ordinal,
            effective_until=effective_until,
        ),
        role=structured.StructuredComponentRoleCode(role),
        evidence_ref=_evidence(relationship_id + 20_000),
    )


def _level(
    reference: identity.EconomicIdentityId,
    value: str,
    *,
    kind: structured.StructuredContractLevelKind,
    unit: str,
) -> structured.StructuredContractLevel:
    return structured.StructuredContractLevel(
        value=Decimal(value),
        kind=kind,
        reference_identity_id=reference,
        unit=structured.StructuredLevelUnitCode(unit),
    )


def _continuous() -> structured.StructuredObservationTerms:
    return structured.StructuredObservationTerms(
        mode=structured.StructuredObservationMode.CONTINUOUS
    )


def _discrete_dates() -> structured.StructuredObservationTerms:
    return structured.StructuredObservationTerms(
        mode=structured.StructuredObservationMode.DISCRETE,
        explicit_dates=(date(2026, 6, 1), date(2026, 3, 1)),
    )


def _discrete_schedule() -> structured.StructuredObservationTerms:
    return structured.StructuredObservationTerms(
        mode=structured.StructuredObservationMode.DISCRETE,
        schedule_code=structured.StructuredObservationScheduleCode(
            "issuer-schedule"
        ),
    )


def _capital(**overrides: Any) -> structured.StructuredCapitalProtectionFeature:
    values: dict[str, Any] = {
        "feature_id": _feature_id(201),
        "protected_identity_id": _economic_id(2),
        "protected_principal_ratio": structured.StructuredPositiveRatio(
            Decimal("1")
        ),
        "evidence_ref": _evidence(301),
    }
    values.update(overrides)
    return structured.StructuredCapitalProtectionFeature(**values)


def _conversion(**overrides: Any) -> structured.StructuredConversionFeature:
    values: dict[str, Any] = {
        "feature_id": _feature_id(202),
        "target_identity_id": _economic_id(3),
        "units_per_source_unit": structured.StructuredPositiveRatio(
            Decimal("0.25")
        ),
        "conversion_level": _level(
            _economic_id(30),
            "125",
            kind=structured.StructuredContractLevelKind.PRICE,
            unit="currency-per-unit",
        ),
        "evidence_ref": _evidence(302),
    }
    values.update(overrides)
    return structured.StructuredConversionFeature(**values)


def _barrier(**overrides: Any) -> structured.StructuredBarrierFeature:
    reference = _economic_id(4)
    values: dict[str, Any] = {
        "feature_id": _feature_id(203),
        "reference_identity_id": reference,
        "barrier_kind": structured.StructuredBarrierKindCode("knock-in"),
        "direction": structured.StructuredBarrierDirection.AT_OR_BELOW,
        "level": _level(
            reference,
            "70",
            kind=structured.StructuredContractLevelKind.LEVEL,
            unit="index-points",
        ),
        "observation": _continuous(),
        "evidence_ref": _evidence(303),
    }
    values.update(overrides)
    return structured.StructuredBarrierFeature(**values)


def _autocall(**overrides: Any) -> structured.StructuredAutocallFeature:
    reference = _economic_id(4)
    values: dict[str, Any] = {
        "feature_id": _feature_id(204),
        "reference_identity_id": reference,
        "trigger_level": _level(
            reference,
            "100",
            kind=structured.StructuredContractLevelKind.LEVEL,
            unit="index-points",
        ),
        "observation": _discrete_dates(),
        "redemption_ratio": structured.StructuredPositiveRatio(
            Decimal("1.05")
        ),
        "evidence_ref": _evidence(304),
    }
    values.update(overrides)
    return structured.StructuredAutocallFeature(**values)


def _participation(
    **overrides: Any,
) -> structured.StructuredParticipationFeature:
    values: dict[str, Any] = {
        "feature_id": _feature_id(205),
        "reference_identity_id": _economic_id(5),
        "direction": structured.StructuredParticipationDirection.INVERSE,
        "participation_ratio": structured.StructuredPositiveRatio(
            Decimal("2")
        ),
        "evidence_ref": _evidence(305),
    }
    values.update(overrides)
    return structured.StructuredParticipationFeature(**values)


def _redemption(**overrides: Any) -> structured.StructuredRedemptionFeature:
    values: dict[str, Any] = {
        "feature_id": _feature_id(206),
        "redemption_identity_id": _economic_id(6),
        "redemption_ratio": structured.StructuredPositiveRatio(Decimal("1")),
        "redemption_date": date(2027, 1, 15),
        "evidence_ref": _evidence(306),
    }
    values.update(overrides)
    return structured.StructuredRedemptionFeature(**values)


def _full_terms() -> structured.StructuredHybridSyntheticTerms:
    root = _economic_id(1)
    components = (
        _component(
            root,
            _economic_id(2),
            relationship_id=101,
            code="component.principal",
            role="principal",
            ordinal=11,
            effective_until=datetime(2027, 1, 1, tzinfo=UTC),
        ),
        _component(
            root,
            _economic_id(3),
            relationship_id=102,
            code="component.conversion",
            role="conversion",
            ordinal=None,
        ),
        _component(
            root,
            _economic_id(4),
            relationship_id=103,
            code="market.reference",
            role="reference",
            ordinal=7,
        ),
        _component(
            root,
            _economic_id(5),
            relationship_id=104,
            code="component.participation",
            role="participation",
            ordinal=None,
        ),
        _component(
            root,
            _economic_id(6),
            relationship_id=105,
            code="redemption.reference",
            role="redemption",
            ordinal=2,
        ),
    )
    features: tuple[structured.StructuredFeature, ...] = (
        _capital(),
        _conversion(),
        _barrier(),
        _autocall(),
        _participation(),
        _redemption(),
    )
    return structured.StructuredHybridSyntheticTerms(
        terms_id=structured.StructuredTermsId(UUID(int=10)),
        instrument_identity_id=root,
        components=tuple(reversed(components)),
        features=tuple(reversed(features)),
        evidence_ref=_evidence(999),
    )


_EXPECTED_COMPONENT_101: tuple[object, ...] = (
    (str(UUID(int=1)),),
    (
        (str(UUID(int=101)),),
        (str(UUID(int=1)),),
        (str(UUID(int=2)),),
        ("component.principal",),
        "2026-01-01T00:00:00.000000+00:00",
        "2027-01-01T00:00:00.000000+00:00",
        (str(UUID(int=10_101)),),
        11,
    ),
    ("principal",),
    (str(UUID(int=20_101)),),
)

_EXPECTED_COMPONENT_102: tuple[object, ...] = (
    (str(UUID(int=1)),),
    (
        (str(UUID(int=102)),),
        (str(UUID(int=1)),),
        (str(UUID(int=3)),),
        ("component.conversion",),
        "2026-01-01T00:00:00.000000+00:00",
        None,
        (str(UUID(int=10_102)),),
        None,
    ),
    ("conversion",),
    (str(UUID(int=20_102)),),
)

_EXPECTED_COMPONENT_103: tuple[object, ...] = (
    (str(UUID(int=1)),),
    (
        (str(UUID(int=103)),),
        (str(UUID(int=1)),),
        (str(UUID(int=4)),),
        ("market.reference",),
        "2026-01-01T00:00:00.000000+00:00",
        None,
        (str(UUID(int=10_103)),),
        7,
    ),
    ("reference",),
    (str(UUID(int=20_103)),),
)

_EXPECTED_COMPONENT_104: tuple[object, ...] = (
    (str(UUID(int=1)),),
    (
        (str(UUID(int=104)),),
        (str(UUID(int=1)),),
        (str(UUID(int=5)),),
        ("component.participation",),
        "2026-01-01T00:00:00.000000+00:00",
        None,
        (str(UUID(int=10_104)),),
        None,
    ),
    ("participation",),
    (str(UUID(int=20_104)),),
)

_EXPECTED_COMPONENT_105: tuple[object, ...] = (
    (str(UUID(int=1)),),
    (
        (str(UUID(int=105)),),
        (str(UUID(int=1)),),
        (str(UUID(int=6)),),
        ("redemption.reference",),
        "2026-01-01T00:00:00.000000+00:00",
        None,
        (str(UUID(int=10_105)),),
        2,
    ),
    ("redemption",),
    (str(UUID(int=20_105)),),
)

_EXPECTED_CAPITAL: tuple[object, ...] = (
    "capital-protection",
    (str(UUID(int=201)),),
    (str(UUID(int=2)),),
    ("1",),
    (str(UUID(int=301)),),
)

_EXPECTED_CONVERSION_LEVEL: tuple[object, ...] = (
    "125",
    "price",
    (str(UUID(int=30)),),
    ("currency-per-unit",),
)

_EXPECTED_CONVERSION: tuple[object, ...] = (
    "conversion",
    (str(UUID(int=202)),),
    (str(UUID(int=3)),),
    ("0.25",),
    _EXPECTED_CONVERSION_LEVEL,
    (str(UUID(int=302)),),
)

_EXPECTED_BARRIER: tuple[object, ...] = (
    "barrier",
    (str(UUID(int=203)),),
    (str(UUID(int=4)),),
    ("knock-in",),
    "at-or-below",
    ("70", "level", (str(UUID(int=4)),), ("index-points",)),
    ("continuous", (), None),
    (str(UUID(int=303)),),
)

_EXPECTED_AUTOCALL: tuple[object, ...] = (
    "autocall",
    (str(UUID(int=204)),),
    (str(UUID(int=4)),),
    ("100", "level", (str(UUID(int=4)),), ("index-points",)),
    ("discrete", ("2026-03-01", "2026-06-01"), None),
    ("1.05",),
    (str(UUID(int=304)),),
)

_EXPECTED_PARTICIPATION: tuple[object, ...] = (
    "participation",
    (str(UUID(int=205)),),
    (str(UUID(int=5)),),
    "inverse",
    ("2",),
    (str(UUID(int=305)),),
)

_EXPECTED_REDEMPTION: tuple[object, ...] = (
    "redemption",
    (str(UUID(int=206)),),
    (str(UUID(int=6)),),
    ("1",),
    "2027-01-15",
    (str(UUID(int=306)),),
)


class _NonCanonicalUUID(UUID):
    def __str__(self) -> str:
        return "forged-noncanonical-uuid-material"


def test_full_closure_local_uuid_material_requires_exact_uuid_type() -> None:
    exact = UUID(int=8)
    forged = _NonCanonicalUUID(int=8)

    assert structured.StructuredTermsId(exact).logical_values() == (
        str(UUID(int=8)),
    )
    assert structured.StructuredFeatureId(exact).logical_values() == (
        str(UUID(int=8)),
    )
    assert structured.StructuredEvidenceRef(exact).logical_values() == (
        str(UUID(int=8)),
    )
    assert isinstance(forged, UUID)
    assert str(forged) == "forged-noncanonical-uuid-material"

    with pytest.raises(
        structured.StructuredHybridSyntheticValidationError,
        match="structured terms id must be UUID",
    ):
        structured.StructuredTermsId(forged)
    with pytest.raises(
        structured.StructuredHybridSyntheticValidationError,
        match="structured feature id must be UUID",
    ):
        structured.StructuredFeatureId(forged)
    with pytest.raises(
        structured.StructuredHybridSyntheticValidationError,
        match="structured evidence ref must be UUID",
    ):
        structured.StructuredEvidenceRef(forged)


def test_full_closure_observation_projections_are_independent() -> None:
    assert _continuous().logical_values() == ("continuous", (), None)
    assert _discrete_dates().logical_values() == (
        "discrete",
        ("2026-03-01", "2026-06-01"),
        None,
    )
    assert _discrete_schedule().logical_values() == (
        "discrete",
        (),
        ("issuer-schedule",),
    )


def test_full_closure_component_projection_reconstructs_umi02_material() -> None:
    component = _component(
        _economic_id(1),
        _economic_id(2),
        relationship_id=101,
        code="component.principal",
        role="principal",
        ordinal=11,
        effective_until=datetime(2027, 1, 1, tzinfo=UTC),
    )
    assert component.logical_values() == _EXPECTED_COMPONENT_101


def test_full_closure_all_six_feature_projections_are_independent() -> None:
    assert _capital().logical_values() == _EXPECTED_CAPITAL
    assert _conversion().logical_values() == _EXPECTED_CONVERSION
    assert _barrier().logical_values() == _EXPECTED_BARRIER
    assert _autocall().logical_values() == _EXPECTED_AUTOCALL
    assert _participation().logical_values() == _EXPECTED_PARTICIPATION
    assert _redemption().logical_values() == _EXPECTED_REDEMPTION


def test_full_closure_optional_feature_projection_slots_are_discriminated() -> None:
    assert _conversion(conversion_level=None).logical_values() == (
        "conversion",
        (str(UUID(int=202)),),
        (str(UUID(int=3)),),
        ("0.25",),
        None,
        (str(UUID(int=302)),),
    )
    assert _redemption(redemption_date=None).logical_values() == (
        "redemption",
        (str(UUID(int=206)),),
        (str(UUID(int=6)),),
        ("1",),
        None,
        (str(UUID(int=306)),),
    )


def test_full_closure_top_level_projection_and_order_are_independent() -> None:
    assert _full_terms().logical_values() == (
        "structured-hybrid-synthetic",
        (str(UUID(int=10)),),
        (str(UUID(int=1)),),
        (
            _EXPECTED_COMPONENT_101,
            _EXPECTED_COMPONENT_102,
            _EXPECTED_COMPONENT_103,
            _EXPECTED_COMPONENT_104,
            _EXPECTED_COMPONENT_105,
        ),
        (
            _EXPECTED_CAPITAL,
            _EXPECTED_CONVERSION,
            _EXPECTED_BARRIER,
            _EXPECTED_AUTOCALL,
            _EXPECTED_PARTICIPATION,
            _EXPECTED_REDEMPTION,
        ),
        (str(UUID(int=999)),),
    )


def test_full_closure_all_25_uncovered_feature_guards_are_directly_hit() -> None:
    error = structured.StructuredHybridSyntheticValidationError

    with pytest.raises(error, match="capital protection feature_id"):
        _capital(feature_id=object())
    with pytest.raises(error, match="capital protection ratio"):
        _capital(protected_principal_ratio=object())
    with pytest.raises(error, match="capital protection evidence_ref"):
        _capital(evidence_ref=object())

    with pytest.raises(error, match="conversion feature_id"):
        _conversion(feature_id=object())
    with pytest.raises(error, match="conversion units_per_source_unit"):
        _conversion(units_per_source_unit=object())
    with pytest.raises(error, match="conversion_level"):
        _conversion(conversion_level=object())
    with pytest.raises(error, match="conversion evidence_ref"):
        _conversion(evidence_ref=object())

    with pytest.raises(error, match="barrier feature_id"):
        _barrier(feature_id=object())
    with pytest.raises(error, match="barrier kind"):
        _barrier(barrier_kind=object())
    with pytest.raises(error, match="barrier direction"):
        _barrier(direction=object())
    with pytest.raises(error, match="barrier level"):
        _barrier(level=object())
    with pytest.raises(error, match="barrier observation"):
        _barrier(observation=object())
    with pytest.raises(error, match="barrier evidence_ref"):
        _barrier(evidence_ref=object())

    with pytest.raises(error, match="autocall feature_id"):
        _autocall(feature_id=object())
    with pytest.raises(error, match="autocall trigger_level"):
        _autocall(trigger_level=object())
    with pytest.raises(error, match="autocall observation"):
        _autocall(observation=object())
    with pytest.raises(error, match="autocall redemption_ratio"):
        _autocall(redemption_ratio=object())
    with pytest.raises(error, match="autocall evidence_ref"):
        _autocall(evidence_ref=object())

    with pytest.raises(error, match="participation feature_id"):
        _participation(feature_id=object())
    with pytest.raises(error, match="participation direction"):
        _participation(direction=object())
    with pytest.raises(error, match="participation ratio"):
        _participation(participation_ratio=object())
    with pytest.raises(error, match="participation evidence_ref"):
        _participation(evidence_ref=object())

    with pytest.raises(error, match="redemption feature_id"):
        _redemption(feature_id=object())
    with pytest.raises(error, match="redemption ratio"):
        _redemption(redemption_ratio=object())
    with pytest.raises(error, match="redemption evidence_ref"):
        _redemption(evidence_ref=object())
