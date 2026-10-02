"""Read-only CE2I T11 runtime guard for capability replay.

T11 must be consulted whenever execution-efficient exposure is eligible. This
guard consumes the already-normalized provider economics and refuses to
authorize additional exposure until the independent gross-edge and nonlinear
market-impact inputs are proven.

It is deliberately shadow-only in the capability exam: it records whether T11
would cap exposure at the minimal seed, but never changes CMA/Risk decisions and
never grants broker/LIVE/real-capital authority.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum

from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)
from qore.infrastructure.cibo_provider_economic_normalization import (
    ProviderEconomicEnvelope,
)


class T11RuntimeDisposition(StrEnum):
    MINIMAL_SEED_ONLY = "MINIMAL_SEED_ONLY"
    ADVANCED_EXPOSURE_ALLOWED = "ADVANCED_EXPOSURE_ALLOWED"


@dataclass(frozen=True, slots=True)
class T11RuntimeGuardDecision:
    qore_symbol: str
    requested_volume: Decimal
    linear_execution_cost_per_volume_usd: Decimal
    minimum_execution_cost_usd: Decimal
    disposition: T11RuntimeDisposition
    gross_edge_model_ready: bool
    market_impact_model_ready: bool
    advanced_exposure_authorized: bool
    blockers: tuple[str, ...]
    productive_authority: bool = False

    def __post_init__(self) -> None:
        if not self.qore_symbol:
            raise CiboCapitalManagementError(
                "T11 runtime guard qore_symbol is required"
            )
        for name in (
            "requested_volume",
            "linear_execution_cost_per_volume_usd",
            "minimum_execution_cost_usd",
        ):
            value = getattr(self, name)
            if (
                not isinstance(value, Decimal)
                or not value.is_finite()
                or value < 0
            ):
                raise CiboCapitalManagementError(
                    f"T11 runtime guard {name} invalid"
                )
        if self.requested_volume <= 0:
            raise CiboCapitalManagementError(
                "T11 runtime guard requested_volume must be positive"
            )
        expected = self.gross_edge_model_ready and self.market_impact_model_ready
        if self.advanced_exposure_authorized != expected:
            raise CiboCapitalManagementError(
                "T11 runtime guard authority/readiness drift"
            )
        expected_disposition = (
            T11RuntimeDisposition.ADVANCED_EXPOSURE_ALLOWED
            if expected
            else T11RuntimeDisposition.MINIMAL_SEED_ONLY
        )
        if self.disposition is not expected_disposition:
            raise CiboCapitalManagementError(
                "T11 runtime guard disposition/readiness drift"
            )
        if expected and self.blockers:
            raise CiboCapitalManagementError(
                "T11 ready state cannot retain blockers"
            )
        if not expected and not self.blockers:
            raise CiboCapitalManagementError(
                "T11 fail-closed state requires blockers"
            )
        if self.productive_authority:
            raise CiboCapitalManagementError(
                "T11 runtime guard grants no productive authority"
            )


def evaluate_t11_runtime_exposure_guard(
    *,
    qore_symbol: str,
    requested_volume: Decimal,
    provider_envelope: ProviderEconomicEnvelope,
    gross_edge_model_ready: bool = False,
    market_impact_model_ready: bool = False,
) -> T11RuntimeGuardDecision:
    """Consult T11 without fabricating its unresolved nonlinear science."""

    if not isinstance(provider_envelope, ProviderEconomicEnvelope):
        raise CiboCapitalManagementError(
            "T11 runtime guard requires provider economic envelope"
        )
    if (
        not isinstance(requested_volume, Decimal)
        or not requested_volume.is_finite()
        or requested_volume <= 0
    ):
        raise CiboCapitalManagementError(
            "T11 runtime guard requested volume invalid"
        )
    blockers: list[str] = []
    if not gross_edge_model_ready:
        blockers.append("T11_GROSS_EDGE_MODEL_NOT_IDENTIFIED")
    if not market_impact_model_ready:
        blockers.append("T11_MARKET_IMPACT_MODEL_NOT_IDENTIFIED")
    ready = gross_edge_model_ready and market_impact_model_ready
    return T11RuntimeGuardDecision(
        qore_symbol=qore_symbol,
        requested_volume=requested_volume,
        linear_execution_cost_per_volume_usd=(
            provider_envelope.execution_cost_per_volume_usd
        ),
        minimum_execution_cost_usd=provider_envelope.minimum_execution_cost_usd,
        disposition=(
            T11RuntimeDisposition.ADVANCED_EXPOSURE_ALLOWED
            if ready
            else T11RuntimeDisposition.MINIMAL_SEED_ONLY
        ),
        gross_edge_model_ready=gross_edge_model_ready,
        market_impact_model_ready=market_impact_model_ready,
        advanced_exposure_authorized=ready,
        blockers=tuple(blockers),
    )
