"""Causal monetary factor-magnitude audit for CE2I T08.

This module identifies observable factor notional without translating stop risk
into factor exposure. It grants no portfolio-netting credit and never infers a
correlation state. Missing USD conversion or contract-denomination evidence
remains explicit and fail-closed.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import StrEnum

from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
    TraderOpportunityEnvelope,
)
from qore.infrastructure.cibo_ce2i_phase19_factor_topology import (
    FactorDirection,
    directional_factor_exposures,
)
from qore.infrastructure.cibo_provider_economic_normalization import (
    ProviderEconomicObservation,
    normalize_provider_economics,
)


class T08FactorVolumeBasis(StrEnum):
    MINIMUM_EXECUTABLE_CANDIDATE = "MINIMUM_EXECUTABLE_CANDIDATE"


@dataclass(frozen=True, slots=True)
class FactorUsdConversion:
    factor_id: str
    usd_per_native_unit: Decimal
    observed_at: datetime
    evidence_ref: str

    def __post_init__(self) -> None:
        if not self.factor_id or not self.evidence_ref:
            raise CiboCapitalManagementError(
                "T08 conversion factor/evidence identity is required"
            )
        _positive(self.usd_per_native_unit, "usd_per_native_unit")
        _aware(self.observed_at, "conversion observed_at")


@dataclass(frozen=True, slots=True)
class MonetaryFactorExposure:
    factor_id: str
    direction: FactorDirection
    native_unit: str
    signed_native_amount: Decimal
    signed_notional_usd: Decimal | None
    usd_conversion_evidence_ref: str | None

    def __post_init__(self) -> None:
        if not self.factor_id or not self.native_unit:
            raise CiboCapitalManagementError(
                "T08 factor/native-unit identity is required"
            )
        if type(self.direction) is not FactorDirection:
            raise CiboCapitalManagementError(
                "T08 factor direction must be canonical"
            )
        _finite_nonzero(self.signed_native_amount, "signed_native_amount")
        if self.direction is FactorDirection.LONG:
            if self.signed_native_amount <= 0:
                raise CiboCapitalManagementError(
                    "T08 LONG factor exposure must be positive"
                )
        elif self.signed_native_amount >= 0:
            raise CiboCapitalManagementError(
                "T08 SHORT factor exposure must be negative"
            )
        if self.signed_notional_usd is None:
            if self.usd_conversion_evidence_ref is not None:
                raise CiboCapitalManagementError(
                    "T08 unresolved USD notional cannot cite conversion"
                )
        else:
            _finite_nonzero(
                self.signed_notional_usd,
                "signed_notional_usd",
            )
            if (self.signed_notional_usd > 0) != (
                self.signed_native_amount > 0
            ):
                raise CiboCapitalManagementError(
                    "T08 USD notional direction must match native exposure"
                )
            if not self.usd_conversion_evidence_ref:
                raise CiboCapitalManagementError(
                    "T08 resolved USD notional requires conversion provenance"
                )


@dataclass(frozen=True, slots=True)
class Phase20T08FactorMagnitudeAudit:
    signal_fingerprint: str
    qore_symbol: str
    volume_basis: T08FactorVolumeBasis
    volume: Decimal
    observed_at: datetime
    exposures: tuple[MonetaryFactorExposure, ...]
    native_magnitude_identified: bool
    usd_magnitude_complete: bool
    risk_equivalent_identified: bool
    correlation_state_identified: bool
    netting_credit_authorized: bool
    blockers: tuple[str, ...]

    def __post_init__(self) -> None:
        if not self.signal_fingerprint or not self.qore_symbol:
            raise CiboCapitalManagementError(
                "T08 magnitude audit signal/symbol is required"
            )
        if type(self.volume_basis) is not T08FactorVolumeBasis:
            raise CiboCapitalManagementError(
                "T08 magnitude audit volume basis is invalid"
            )
        _positive(self.volume, "volume")
        _aware(self.observed_at, "audit observed_at")
        for name in (
            "native_magnitude_identified",
            "usd_magnitude_complete",
            "risk_equivalent_identified",
            "correlation_state_identified",
            "netting_credit_authorized",
        ):
            if type(getattr(self, name)) is not bool:
                raise CiboCapitalManagementError(
                    f"T08 magnitude audit {name} must be bool"
                )
        if self.native_magnitude_identified != bool(self.exposures):
            raise CiboCapitalManagementError(
                "T08 native magnitude/exposure accounting drift"
            )
        if self.usd_magnitude_complete != (
            bool(self.exposures)
            and all(
                item.signed_notional_usd is not None
                for item in self.exposures
            )
        ):
            raise CiboCapitalManagementError(
                "T08 USD magnitude completeness accounting drift"
            )
        if (
            self.risk_equivalent_identified
            or self.correlation_state_identified
            or self.netting_credit_authorized
        ):
            raise CiboCapitalManagementError(
                "T08 magnitude audit cannot grant risk/correlation/netting"
            )
        if not self.blockers:
            raise CiboCapitalManagementError(
                "T08 non-promoting magnitude audit must retain blockers"
            )


_PAIR_FACTORS: dict[str, tuple[str, str]] = {
    "AUDJPY": ("AUD", "JPY"),
    "EURUSD": ("EUR", "USD"),
    "GBPJPY": ("GBP", "JPY"),
    "GBPUSD": ("GBP", "USD"),
    "XAUUSD": ("XAU", "USD"),
}


def assess_minimum_seed_factor_magnitude(
    *,
    opportunity: TraderOpportunityEnvelope,
    observation: ProviderEconomicObservation,
    decision_at: datetime,
    provider_evidence_ref: str,
    conversions: tuple[FactorUsdConversion, ...] = (),
) -> Phase20T08FactorMagnitudeAudit:
    """Measure minimum-seed factor notional without manufacturing risk credit."""

    if not isinstance(opportunity, TraderOpportunityEnvelope):
        raise CiboCapitalManagementError(
            "T08 magnitude requires TraderOpportunityEnvelope"
        )
    if not isinstance(observation, ProviderEconomicObservation):
        raise CiboCapitalManagementError(
            "T08 magnitude requires ProviderEconomicObservation"
        )
    _aware(decision_at, "decision_at")
    if not provider_evidence_ref:
        raise CiboCapitalManagementError(
            "T08 provider evidence reference is required"
        )
    if observation.observed_at > decision_at:
        raise CiboCapitalManagementError(
            "T08 provider observation cannot postdate decision"
        )
    conversion_map = _conversion_map(
        conversions=conversions,
        decision_at=decision_at,
    )
    normalized = normalize_provider_economics(
        opportunity=opportunity,
        observation=observation,
    )
    volume = normalized.minimum_executable_volume
    symbol = opportunity.qore_symbol.strip().upper()

    if symbol == "NAS100":
        return Phase20T08FactorMagnitudeAudit(
            signal_fingerprint=opportunity.signal_fingerprint,
            qore_symbol=symbol,
            volume_basis=T08FactorVolumeBasis.MINIMUM_EXECUTABLE_CANDIDATE,
            volume=volume,
            observed_at=decision_at,
            exposures=(),
            native_magnitude_identified=False,
            usd_magnitude_complete=False,
            risk_equivalent_identified=False,
            correlation_state_identified=False,
            netting_credit_authorized=False,
            blockers=(
                "PROVIDER_CONTRACT_DENOMINATION_REQUIRED:NAS100",
                "FACTOR_NOTIONAL_TO_SIGNED_RISK_USD_MAPPING_NOT_IDENTIFIED",
                "CAUSAL_CORRELATION_STATE_NOT_IDENTIFIED",
                "FRESH_OOS_NETTING_UTILITY_ANALYSIS_REQUIRED",
            ),
        )

    factors = _PAIR_FACTORS.get(symbol)
    if factors is None:
        raise CiboCapitalManagementError(
            "T08 magnitude symbol is outside frozen factor universe"
        )
    base_factor, quote_factor = factors
    topology = directional_factor_exposures(
        qore_symbol=symbol,
        side=opportunity.side,
    )
    topology_map = {item.factor: item.direction for item in topology}
    if set(topology_map) != {base_factor, quote_factor}:
        raise CiboCapitalManagementError(
            "T08 magnitude/topology factor mismatch"
        )

    base_amount = observation.contract_size * volume
    quote_amount = base_amount * opportunity.intended_entry
    side_sign = Decimal(1) if opportunity.side == "long" else Decimal(-1)
    signed_amounts = {
        base_factor: side_sign * base_amount,
        quote_factor: -side_sign * quote_amount,
    }

    exposures: list[MonetaryFactorExposure] = []
    missing_conversion: list[str] = []
    for factor in (base_factor, quote_factor):
        conversion = _resolve_conversion(
            factor=factor,
            base_factor=base_factor,
            quote_factor=quote_factor,
            quote_per_base=opportunity.intended_entry,
            provider_key=observation.provider_key,
            symbol=symbol,
            observed_at=observation.observed_at,
            provider_evidence_ref=provider_evidence_ref,
            external=conversion_map,
        )
        native_amount = signed_amounts[factor]
        usd_notional = (
            None
            if conversion is None
            else native_amount * conversion.usd_per_native_unit
        )
        if conversion is None:
            missing_conversion.append(factor)
        exposures.append(
            MonetaryFactorExposure(
                factor_id=factor,
                direction=topology_map[factor],
                native_unit=factor,
                signed_native_amount=native_amount,
                signed_notional_usd=usd_notional,
                usd_conversion_evidence_ref=(
                    None if conversion is None else conversion.evidence_ref
                ),
            )
        )

    blockers = [
        *(f"USD_CONVERSION_REQUIRED:{item}" for item in missing_conversion),
        "FACTOR_NOTIONAL_TO_SIGNED_RISK_USD_MAPPING_NOT_IDENTIFIED",
        "CAUSAL_CORRELATION_STATE_NOT_IDENTIFIED",
        "FRESH_OOS_NETTING_UTILITY_ANALYSIS_REQUIRED",
    ]
    return Phase20T08FactorMagnitudeAudit(
        signal_fingerprint=opportunity.signal_fingerprint,
        qore_symbol=symbol,
        volume_basis=T08FactorVolumeBasis.MINIMUM_EXECUTABLE_CANDIDATE,
        volume=volume,
        observed_at=decision_at,
        exposures=tuple(exposures),
        native_magnitude_identified=True,
        usd_magnitude_complete=not missing_conversion,
        risk_equivalent_identified=False,
        correlation_state_identified=False,
        netting_credit_authorized=False,
        blockers=tuple(blockers),
    )


def _conversion_map(
    *,
    conversions: tuple[FactorUsdConversion, ...],
    decision_at: datetime,
) -> dict[str, FactorUsdConversion]:
    result: dict[str, FactorUsdConversion] = {}
    for item in conversions:
        if not isinstance(item, FactorUsdConversion):
            raise CiboCapitalManagementError(
                "T08 conversion evidence must be canonical"
            )
        if item.observed_at > decision_at:
            raise CiboCapitalManagementError(
                "T08 conversion evidence cannot postdate decision"
            )
        if item.factor_id in result:
            raise CiboCapitalManagementError(
                "T08 duplicate factor conversion evidence"
            )
        result[item.factor_id] = item
    return result


def _resolve_conversion(
    *,
    factor: str,
    base_factor: str,
    quote_factor: str,
    quote_per_base: Decimal,
    provider_key: str,
    symbol: str,
    observed_at: datetime,
    provider_evidence_ref: str,
    external: dict[str, FactorUsdConversion],
) -> FactorUsdConversion | None:
    if factor == "USD":
        return FactorUsdConversion(
            factor_id="USD",
            usd_per_native_unit=Decimal(1),
            observed_at=observed_at,
            evidence_ref="intrinsic:USD",
        )
    if quote_factor == "USD" and factor == base_factor:
        return FactorUsdConversion(
            factor_id=factor,
            usd_per_native_unit=quote_per_base,
            observed_at=observed_at,
            evidence_ref=(
                f"{provider_evidence_ref}:direct:{provider_key}:{symbol}"
            ),
        )
    if base_factor == "USD" and factor == quote_factor:
        return FactorUsdConversion(
            factor_id=factor,
            usd_per_native_unit=Decimal(1) / quote_per_base,
            observed_at=observed_at,
            evidence_ref=(
                f"{provider_evidence_ref}:inverse:{provider_key}:{symbol}"
            ),
        )
    return external.get(factor)


def _positive(value: Decimal, name: str) -> None:
    if (
        not isinstance(value, Decimal)
        or not value.is_finite()
        or value <= 0
    ):
        raise CiboCapitalManagementError(
            f"T08 {name} must be finite positive Decimal"
        )


def _finite_nonzero(value: Decimal, name: str) -> None:
    if (
        not isinstance(value, Decimal)
        or not value.is_finite()
        or value == 0
    ):
        raise CiboCapitalManagementError(
            f"T08 {name} must be finite non-zero Decimal"
        )


def _aware(value: datetime, name: str) -> None:
    if (
        not isinstance(value, datetime)
        or value.tzinfo is None
        or value.utcoffset() is None
    ):
        raise CiboCapitalManagementError(
            f"T08 {name} must be timezone-aware"
        )
