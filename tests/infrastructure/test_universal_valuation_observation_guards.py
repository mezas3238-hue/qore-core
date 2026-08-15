from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from typing import Any, cast
from uuid import UUID

import pytest

from qore.infrastructure.equity_fund_corporate_action_semantics import (
    EquityFundEvidenceRef,
    FundNavBasis,
    FundNavBasisCode,
)
from qore.infrastructure.market_data import Instrument
from qore.infrastructure.market_observation import (
    MarketObservationEvidenceReference,
    MarketObservationId,
    MarketPrice,
    MarketPriceSide,
    QualifiedQuoteTickObservation,
)
from qore.infrastructure.ports import (
    AdapterId,
    ExternalSourceDescriptor,
    PortName,
    SourceId,
)
from qore.infrastructure.universal_instrument_identity import (
    CanonicalIdentityRef,
    EconomicIdentityId,
    ExternalIdentifier,
    ExternalIdentifierKind,
    ExternalIdentifierNamespace,
    ExternalIdentifierValue,
    ExternalIdentityMappingRevision,
    IdentityEvidenceRef,
    IdentityMappingId,
    IdentityMappingRevision,
    ListingIdentity,
    ListingIdentityId,
    MarketVenueCode,
)
from qore.infrastructure.universal_valuation_observation import (
    ComputedValuationObservation,
    ComputedValuationProvenance,
    D05MarketPriceMeasure,
    D05OhlcPriceField,
    D05QuoteValuationSource,
    FundNavMeasure,
    FundNavValue,
    ImpliedVolatility,
    ImpliedVolatilityMeasure,
    ModelValueMeasure,
    ObservedValuationObservation,
    PublishedValuationSource,
    QuotedValuationValue,
    UniversalValuationObservationValidationError,
    ValuationAsOfDate,
    ValuationAsOfInstant,
    ValuationComputedInput,
    ValuationEvidenceRef,
    ValuationIdentityBinding,
    ValuationInputFingerprint,
    ValuationInputRoleCode,
    ValuationMethodologyFamily,
    ValuationMethodologyIdentity,
    ValuationMethodologySchemaVersion,
    ValuationModelOutputCode,
    ValuationObservationId,
    ValuationQuoteBasisCode,
    ValuationSoftwareRevision,
    ValuationSourceEvidenceRef,
    ValuationSourceObservationId,
)


def _uuid(value: int) -> UUID:
    return UUID(int=value)


def _economic_id(value: int = 10) -> EconomicIdentityId:
    return EconomicIdentityId(_uuid(value))


def _source(seed: int = 1) -> ExternalSourceDescriptor:
    return ExternalSourceDescriptor(
        adapter_id=AdapterId(_uuid(1000 + seed)),
        source_id=SourceId(_uuid(2000 + seed)),
        port_name=PortName("valuation.external"),
    )


def _binding(
    *,
    symbol: str = "EURUSD",
    economic_id: EconomicIdentityId | None = None,
    kind: ExternalIdentifierKind = ExternalIdentifierKind.LEGACY_QORE,
    namespace: str = "market-data.instrument",
    source: ExternalSourceDescriptor | None = None,
    effective_from: datetime | None = None,
    effective_until: datetime | None = None,
) -> ValuationIdentityBinding:
    target = economic_id or _economic_id()
    start = effective_from or datetime(2025, 1, 1, tzinfo=UTC)
    mapping = ExternalIdentityMappingRevision(
        mapping_id=IdentityMappingId(_uuid(3001)),
        revision=IdentityMappingRevision(1),
        parent_revision=None,
        external_identity=ExternalIdentifier(
            kind=kind,
            namespace=ExternalIdentifierNamespace(namespace),
            value=ExternalIdentifierValue(symbol),
            source=source,
        ),
        target=CanonicalIdentityRef(target),
        effective_from=start,
        effective_until=effective_until,
        recorded_at=start + timedelta(hours=1),
        evidence_ref=IdentityEvidenceRef(_uuid(3002)),
    )
    return ValuationIdentityBinding(mapping=mapping, economic_identity_id=target)


def _provider_binding(source: ExternalSourceDescriptor) -> ValuationIdentityBinding:
    return _binding(
        symbol="provider-asset-1",
        kind=ExternalIdentifierKind.PROVIDER_NATIVE,
        namespace="valuation.instrument",
        source=source,
    )


def _quote(observed_at: datetime | None = None) -> QualifiedQuoteTickObservation:
    return QualifiedQuoteTickObservation(
        observation_id=MarketObservationId(_uuid(4001)),
        instrument=Instrument("EURUSD"),
        source=_source(2),
        observed_at=observed_at or datetime(2026, 1, 2, 12, tzinfo=UTC),
        bid=MarketPrice(Decimal("1.10")),
        ask=MarketPrice(Decimal("1.11")),
        evidence_ref=MarketObservationEvidenceReference(_uuid(4002)),
    )


def _nav_measure(value: str = "25") -> FundNavMeasure:
    return FundNavMeasure(
        value=FundNavValue(Decimal(value)),
        basis=FundNavBasis(
            currency_identity_id=_economic_id(501),
            unit_identity_id=_economic_id(502),
            basis=FundNavBasisCode("per-unit"),
            evidence_ref=EquityFundEvidenceRef(_uuid(503)),
        ),
    )


def _published(seed: int = 1) -> PublishedValuationSource:
    source = _source(10 + seed)
    return PublishedValuationSource(
        source_observation_id=ValuationSourceObservationId(_uuid(6000 + seed)),
        source=source,
        identity_binding=_provider_binding(source),
        as_of=ValuationAsOfDate(date(2026, 1, 2)),
        measure=_nav_measure(str(20 + seed)),
        evidence_ref=ValuationSourceEvidenceRef(_uuid(6100 + seed)),
    )


def _methodology() -> ValuationMethodologyIdentity:
    return ValuationMethodologyIdentity(
        family=ValuationMethodologyFamily("fund.nav.adjustment"),
        schema_version=ValuationMethodologySchemaVersion("v1"),
        software_revision=ValuationSoftwareRevision("abc1234"),
    )


def _provenance() -> ComputedValuationProvenance:
    return ComputedValuationProvenance(
        methodology=_methodology(),
        inputs=(
            ValuationComputedInput(
                role=ValuationInputRoleCode("source-nav"),
                source=_published(),
            ),
        ),
        evidence_ref=ValuationEvidenceRef(_uuid(7001)),
    )


def _computed() -> ComputedValuationObservation:
    return ComputedValuationObservation(
        observation_id=ValuationObservationId(_uuid(7101)),
        economic_identity_id=_economic_id(7102),
        as_of=ValuationAsOfDate(date(2026, 1, 2)),
        measure=_nav_measure("24.5"),
        provenance=_provenance(),
        recorded_at=datetime(2026, 1, 3, tzinfo=UTC),
        evidence_ref=ValuationEvidenceRef(_uuid(7103)),
    )


@pytest.mark.parametrize(
    "factory",
    [
        lambda: ValuationObservationId(cast(Any, "bad")),
        lambda: ValuationEvidenceRef(cast(Any, "bad")),
        lambda: ValuationSourceObservationId(cast(Any, "bad")),
        lambda: ValuationSourceEvidenceRef(cast(Any, "bad")),
    ],
)
def test_uuid_wrappers_reject_non_uuid(factory: Callable[[], object]) -> None:
    with pytest.raises(UniversalValuationObservationValidationError, match="UUID"):
        factory()


def test_code_family_schema_revision_and_fingerprint_guards_fail_closed() -> None:
    with pytest.raises(UniversalValuationObservationValidationError, match="canonical"):
        ValuationQuoteBasisCode("Bad Code")
    with pytest.raises(UniversalValuationObservationValidationError, match="dotted"):
        ValuationMethodologyFamily("Bad.Family")
    with pytest.raises(UniversalValuationObservationValidationError, match="v<integer>"):
        ValuationMethodologySchemaVersion("vNext")
    with pytest.raises(UniversalValuationObservationValidationError, match="revision"):
        ValuationSoftwareRevision("bad revision")
    with pytest.raises(UniversalValuationObservationValidationError, match="SHA-256"):
        ValuationInputFingerprint("not-a-digest")


def test_decimal_and_timestamp_guards_reject_non_finite_and_naive_values() -> None:
    with pytest.raises(UniversalValuationObservationValidationError, match="finite Decimal"):
        FundNavValue(Decimal("NaN"))
    with pytest.raises(UniversalValuationObservationValidationError, match="timezone-aware"):
        ValuationAsOfInstant(datetime(2026, 1, 2, 12))
    with pytest.raises(UniversalValuationObservationValidationError, match="datetime"):
        ValuationAsOfInstant(cast(Any, date(2026, 1, 2)))


def test_d05_market_measure_type_guards_fail_closed() -> None:
    with pytest.raises(UniversalValuationObservationValidationError, match="MarketPrice"):
        D05MarketPriceMeasure(cast(Any, Decimal("1")), MarketPriceSide.BID)
    with pytest.raises(UniversalValuationObservationValidationError, match="MarketPriceSide"):
        D05MarketPriceMeasure(MarketPrice(Decimal("1")), cast(Any, "bid"))
    with pytest.raises(UniversalValuationObservationValidationError, match="ohlc_field"):
        D05MarketPriceMeasure(
            MarketPrice(Decimal("1")),
            MarketPriceSide.BID,
            cast(Any, "close"),
        )


def test_nav_and_implied_volatility_measure_type_guards_fail_closed() -> None:
    nav = _nav_measure()
    with pytest.raises(UniversalValuationObservationValidationError, match="FundNavValue"):
        FundNavMeasure(cast(Any, Decimal("1")), nav.basis)
    with pytest.raises(UniversalValuationObservationValidationError, match="FundNavBasis"):
        FundNavMeasure(nav.value, cast(Any, object()))

    iv = ImpliedVolatility(Decimal("0.2"))
    measure = ImpliedVolatilityMeasure(iv, _economic_id(8001))
    assert measure.logical_values()[0] == "implied-volatility"
    with pytest.raises(UniversalValuationObservationValidationError, match="ImpliedVolatility"):
        ImpliedVolatilityMeasure(cast(Any, Decimal("0.2")), _economic_id(8001))
    with pytest.raises(UniversalValuationObservationValidationError, match="EconomicIdentityId"):
        ImpliedVolatilityMeasure(iv, cast(Any, "underlying"))


def test_quoted_and_model_value_type_guards_fail_closed() -> None:
    basis = ValuationQuoteBasisCode("currency-per-unit")
    quote_id = _economic_id(8101)
    with pytest.raises(UniversalValuationObservationValidationError, match="quote identity"):
        QuotedValuationValue(Decimal("1"), cast(Any, "usd"), basis)
    with pytest.raises(UniversalValuationObservationValidationError, match="quote_basis"):
        QuotedValuationValue(Decimal("1"), quote_id, cast(Any, "basis"))

    quoted = QuotedValuationValue(Decimal("1"), quote_id, basis)
    output = ValuationModelOutputCode("theoretical-value")
    with pytest.raises(UniversalValuationObservationValidationError, match="QuotedValuationValue"):
        ModelValueMeasure(cast(Any, Decimal("1")), output)
    with pytest.raises(UniversalValuationObservationValidationError, match="output"):
        ModelValueMeasure(quoted, cast(Any, "theoretical-value"))


def test_identity_binding_rejects_wrong_types_and_mismatched_economic_target() -> None:
    valid = _binding()
    with pytest.raises(UniversalValuationObservationValidationError, match="mapping"):
        ValuationIdentityBinding(cast(Any, object()), _economic_id())
    with pytest.raises(UniversalValuationObservationValidationError, match="economic_identity_id"):
        ValuationIdentityBinding(valid.mapping, cast(Any, "economic"))
    with pytest.raises(UniversalValuationObservationValidationError, match="must equal"):
        ValuationIdentityBinding(valid.mapping, _economic_id(9999))


def test_identity_binding_rejects_unrelated_or_mismatched_listing_binding() -> None:
    valid = _binding()
    unrelated_listing = ListingIdentity(
        listing_id=ListingIdentityId(_uuid(8201)),
        economic_identity_id=valid.economic_identity_id,
        venue=MarketVenueCode("test-venue"),
        display_symbol="EURUSD",
        valid_from=datetime(2025, 1, 1, tzinfo=UTC),
        valid_until=None,
        evidence_ref=IdentityEvidenceRef(_uuid(8202)),
    )
    with pytest.raises(UniversalValuationObservationValidationError, match="must not carry"):
        ValuationIdentityBinding(
            valid.mapping,
            valid.economic_identity_id,
            unrelated_listing,
        )


def test_d05_binding_rejects_wrong_kind_namespace_and_expired_mapping() -> None:
    quote = _quote()
    with pytest.raises(UniversalValuationObservationValidationError, match="LEGACY_QORE"):
        D05QuoteValuationSource(
            quote,
            MarketPriceSide.BID,
            _binding(
                kind=ExternalIdentifierKind.PROVIDER_NATIVE,
                source=_source(30),
            ),
        )
    with pytest.raises(UniversalValuationObservationValidationError, match="namespace"):
        D05QuoteValuationSource(
            quote,
            MarketPriceSide.BID,
            _binding(namespace="wrong.namespace"),
        )
    with pytest.raises(UniversalValuationObservationValidationError, match="outside"):
        D05QuoteValuationSource(
            quote,
            MarketPriceSide.BID,
            _binding(effective_until=quote.observed_at),
        )


def test_d05_quote_source_rejects_wrong_observation_and_binding_types() -> None:
    with pytest.raises(UniversalValuationObservationValidationError, match="QualifiedQuote"):
        D05QuoteValuationSource(
            cast(Any, object()),
            MarketPriceSide.BID,
            _binding(),
        )
    with pytest.raises(
        UniversalValuationObservationValidationError,
        match="ValuationIdentityBinding",
    ):
        D05QuoteValuationSource(
            _quote(),
            MarketPriceSide.BID,
            cast(Any, object()),
        )


def test_published_source_type_guards_fail_closed() -> None:
    source = _source(40)
    binding = _provider_binding(source)
    as_of = ValuationAsOfDate(date(2026, 1, 2))
    measure = _nav_measure()
    evidence = ValuationSourceEvidenceRef(_uuid(8301))
    source_id = ValuationSourceObservationId(_uuid(8302))

    cases: tuple[tuple[Any, ...], ...] = (
        (cast(Any, _uuid(1)), source, binding, as_of, measure, evidence),
        (source_id, cast(Any, object()), binding, as_of, measure, evidence),
        (source_id, source, cast(Any, object()), as_of, measure, evidence),
        (source_id, source, binding, cast(Any, "2026-01-02"), measure, evidence),
        (source_id, source, binding, as_of, cast(Any, Decimal("1")), evidence),
        (source_id, source, binding, as_of, measure, cast(Any, _uuid(2))),
    )
    for args in cases:
        with pytest.raises(UniversalValuationObservationValidationError):
            PublishedValuationSource(*args)


def test_observed_observation_type_and_timestamp_guards_fail_closed() -> None:
    source = _published(2)
    evidence = ValuationEvidenceRef(_uuid(8401))
    observation_id = ValuationObservationId(_uuid(8402))

    with pytest.raises(UniversalValuationObservationValidationError, match="observation_id"):
        ObservedValuationObservation(
            cast(Any, _uuid(1)),
            source,
            datetime(2026, 1, 3, tzinfo=UTC),
            evidence,
        )
    with pytest.raises(UniversalValuationObservationValidationError, match="source"):
        ObservedValuationObservation(
            observation_id,
            cast(Any, object()),
            datetime(2026, 1, 3, tzinfo=UTC),
            evidence,
        )
    with pytest.raises(UniversalValuationObservationValidationError, match="timezone-aware"):
        ObservedValuationObservation(
            observation_id,
            source,
            datetime(2026, 1, 3),
            evidence,
        )
    with pytest.raises(UniversalValuationObservationValidationError, match="evidence_ref"):
        ObservedValuationObservation(
            observation_id,
            source,
            datetime(2026, 1, 3, tzinfo=UTC),
            cast(Any, _uuid(2)),
        )


def test_methodology_identity_and_computed_input_type_guards_fail_closed() -> None:
    family = ValuationMethodologyFamily("fund.nav.adjustment")
    schema = ValuationMethodologySchemaVersion("v1")
    revision = ValuationSoftwareRevision("abc1234")
    with pytest.raises(UniversalValuationObservationValidationError, match="family"):
        ValuationMethodologyIdentity(cast(Any, "family"), schema, revision)
    with pytest.raises(UniversalValuationObservationValidationError, match="schema_version"):
        ValuationMethodologyIdentity(family, cast(Any, "v1"), revision)
    with pytest.raises(UniversalValuationObservationValidationError, match="software_revision"):
        ValuationMethodologyIdentity(family, schema, cast(Any, "abc1234"))

    source = _published(3)
    with pytest.raises(UniversalValuationObservationValidationError, match="role"):
        ValuationComputedInput(cast(Any, "role"), source)


def test_computed_provenance_shape_and_type_guards_fail_closed() -> None:
    methodology = _methodology()
    evidence = ValuationEvidenceRef(_uuid(8501))
    item = ValuationComputedInput(ValuationInputRoleCode("source-nav"), _published(4))

    with pytest.raises(UniversalValuationObservationValidationError, match="methodology"):
        ComputedValuationProvenance(cast(Any, object()), (item,), evidence)
    with pytest.raises(UniversalValuationObservationValidationError, match="non-empty tuple"):
        ComputedValuationProvenance(methodology, (), evidence)
    with pytest.raises(UniversalValuationObservationValidationError, match="non-empty tuple"):
        ComputedValuationProvenance(methodology, cast(Any, [item]), evidence)
    with pytest.raises(UniversalValuationObservationValidationError, match="item type"):
        ComputedValuationProvenance(methodology, (cast(Any, object()),), evidence)
    with pytest.raises(UniversalValuationObservationValidationError, match="evidence_ref"):
        ComputedValuationProvenance(methodology, (item,), cast(Any, _uuid(2)))


def test_computed_observation_type_and_timestamp_guards_fail_closed() -> None:
    valid = _computed()
    common = (
        valid.observation_id,
        valid.economic_identity_id,
        valid.as_of,
        valid.measure,
        valid.provenance,
        valid.recorded_at,
        valid.evidence_ref,
    )
    cases: tuple[tuple[Any, ...], ...] = (
        (cast(Any, _uuid(1)), *common[1:]),
        (common[0], cast(Any, "economic"), *common[2:]),
        (*common[:2], cast(Any, "2026-01-02"), *common[3:]),
        (*common[:3], cast(Any, Decimal("1")), *common[4:]),
        (*common[:4], cast(Any, object()), *common[5:]),
        (*common[:5], datetime(2026, 1, 3), common[6]),
        (*common[:6], cast(Any, _uuid(2))),
    )
    for args in cases:
        with pytest.raises(UniversalValuationObservationValidationError):
            ComputedValuationObservation(*args)


def test_computed_observation_logical_values_materialize_retained_lineage() -> None:
    observation = _computed()
    logical = observation.logical_values()

    assert logical[0] == "computed"
    assert observation.observation_id.logical_values() in logical
    assert observation.economic_identity_id.logical_values() in logical
    assert observation.as_of.logical_values() in logical
    assert observation.measure.logical_values() in logical
    assert observation.provenance.logical_values() in logical
    assert observation.evidence_ref.logical_values() in logical
    assert observation.provenance.input_fingerprint.value in str(logical)


def test_exact_d05_ohlc_selector_enum_is_closed() -> None:
    assert set(D05OhlcPriceField) == {
        D05OhlcPriceField.OPEN,
        D05OhlcPriceField.HIGH,
        D05OhlcPriceField.LOW,
        D05OhlcPriceField.CLOSE,
    }
