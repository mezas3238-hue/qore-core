"""Causal projection from fresh Phase22 Trader geometry into CIBO capital inputs.

This module consumes only decision-time geometry plus the separately frozen
provider numeric model. The fresh structural outcome and exit path are
deliberately outside the projection, so future outcome changes cannot alter
the CIBO predecision surface.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from qore.infrastructure.account_wide_risk import TraderLineage
from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
    TraderOpportunityEnvelope,
)
from qore.infrastructure.cibo_phase22_fresh_opportunity_batch import (
    Phase22FreshOpportunity,
)
from qore.infrastructure.cibo_phase22_historical_policy_replay import (
    Phase22HistoricalCapitalInput,
)
from qore.infrastructure.cibo_phase22_historical_replay_sealing import (
    Phase22HistoricalReplayCandidateEvidence,
)
from qore.infrastructure.cibo_phase22_provider_execution_calibration_receipt import (
    PHASE22_PROVIDER_EXECUTION_CALIBRATION_RECEIPT,
)
from qore.infrastructure.cibo_phase22_provider_numeric_execution import (
    Phase22ProviderNumericExecutionSpec,
)
from qore.infrastructure.cibo_provider_economic_normalization import (
    ProviderEconomicEnvelope,
    ProviderEconomicObservation,
    normalize_provider_economics,
)

_BPS = Decimal("10000")
_VT31_MINIMUM_EXECUTION_STEPS = 4


@dataclass(frozen=True, slots=True)
class Phase22FreshCapitalProjection:
    candidate: Phase22HistoricalReplayCandidateEvidence
    provider_envelope: ProviderEconomicEnvelope
    provider_numeric_freeze_sha256: str

    def __post_init__(self) -> None:
        if (
            not self.provider_numeric_freeze_sha256.startswith("sha256:")
            or len(self.provider_numeric_freeze_sha256) != 71
        ):
            raise CiboCapitalManagementError(
                "Phase22 fresh capital projection provider freeze digest invalid"
            )
        capital = self.candidate.capital_input
        envelope = self.provider_envelope
        if capital.minimum_stop_risk_usd != envelope.minimum_stop_risk_usd:
            raise CiboCapitalManagementError(
                "Phase22 fresh projection minimum stop-risk drift"
            )
        if capital.minimum_margin_usd != envelope.minimum_margin_usd:
            raise CiboCapitalManagementError(
                "Phase22 fresh projection minimum margin drift"
            )

    @property
    def decision_provider_cost_proxy_usd(self) -> Decimal:
        return self.provider_envelope.minimum_execution_cost_usd


def _minimum_execution_steps(trader_id: TraderLineage) -> int:
    if trader_id is TraderLineage.VT31_NAS100:
        return _VT31_MINIMUM_EXECUTION_STEPS
    return 1


def _provider_observation(
    *,
    fresh: Phase22FreshOpportunity,
    spec: Phase22ProviderNumericExecutionSpec,
) -> ProviderEconomicObservation:
    if fresh.qore_symbol != spec.qore_symbol:
        raise CiboCapitalManagementError(
            "Phase22 fresh projection provider symbol drift"
        )
    slippage_per_volume = (
        fresh.entry_price
        * spec.contract_size_per_volume
        * spec.quote_to_usd
        * spec.worst_adverse_slippage_bps
        / _BPS
    )
    return ProviderEconomicObservation(
        provider_key="ctrader-demo",
        qore_symbol=fresh.qore_symbol,
        provider_symbol=spec.provider_symbol,
        bid=spec.bid,
        ask=spec.ask,
        contract_size=spec.contract_size_per_volume,
        tick_size=spec.derived_price_quantum,
        tick_value=spec.derived_value_per_quantum_usd,
        minimum_volume=spec.minimum_volume,
        maximum_volume=spec.maximum_volume,
        volume_step=spec.volume_step,
        margin_per_volume=spec.margin_per_volume_usd,
        commission_per_volume_usd=spec.commission_per_volume_usd,
        slippage_reserve_per_volume_usd=slippage_per_volume,
        observed_at=spec.observed_at,
    )


def project_phase22_fresh_capital_input(
    *,
    fresh: Phase22FreshOpportunity,
    spec: Phase22ProviderNumericExecutionSpec,
    provider_numeric_freeze_sha256: str,
) -> Phase22FreshCapitalProjection:
    """Project only predecision facts; never read structural outcome/exit fields."""

    if not isinstance(fresh, Phase22FreshOpportunity):
        raise CiboCapitalManagementError(
            "Phase22 fresh projection requires fresh opportunity"
        )
    if not isinstance(spec, Phase22ProviderNumericExecutionSpec):
        raise CiboCapitalManagementError(
            "Phase22 fresh projection requires provider numeric spec"
        )
    if (
        not provider_numeric_freeze_sha256.startswith("sha256:")
        or len(provider_numeric_freeze_sha256) != 71
    ):
        raise CiboCapitalManagementError(
            "Phase22 fresh projection provider freeze digest invalid"
        )

    steps = _minimum_execution_steps(fresh.trader_id)
    stop_loss_per_volume = (
        abs(fresh.entry_price - fresh.structural_stop)
        * spec.usd_value_per_price_unit_per_volume
    )
    if stop_loss_per_volume <= 0:
        raise CiboCapitalManagementError(
            "Phase22 fresh projection stop economics invalid"
        )

    opportunity = TraderOpportunityEnvelope(
        trader_id=fresh.trader_id,
        signal_fingerprint=fresh.signal_fingerprint,
        qore_symbol=fresh.qore_symbol,
        provider_symbol=spec.provider_symbol,
        side=fresh.side,
        entry_type=(
            "limit"
            if fresh.trader_id is TraderLineage.VT31_NAS100
            else "market"
        ),
        intended_entry=fresh.entry_price,
        stop_loss=fresh.structural_stop,
        take_profit=fresh.technical_target,
        stop_loss_per_volume=stop_loss_per_volume,
        margin_per_volume=spec.margin_per_volume_usd,
        volume_step=spec.volume_step,
        minimum_volume=spec.minimum_volume,
        maximum_volume=spec.maximum_volume,
        minimum_execution_steps=steps,
        decision_context=(
            ("phase22_candidate", "V2"),
            ("provider_numeric_freeze", provider_numeric_freeze_sha256),
        ),
    )
    observation = _provider_observation(fresh=fresh, spec=spec)
    normalized = normalize_provider_economics(
        opportunity=opportunity,
        observation=observation,
    )
    capital = Phase22HistoricalCapitalInput(
        opportunity=opportunity,
        minimum_stop_risk_usd=normalized.minimum_stop_risk_usd,
        minimum_margin_usd=normalized.minimum_margin_usd,
        concentration_group=fresh.qore_symbol,
        concentration_risk_usd=normalized.minimum_stop_risk_usd,
        provider_model_sha256=(
            PHASE22_PROVIDER_EXECUTION_CALIBRATION_RECEIPT.fingerprint()
        ),
    )
    candidate = Phase22HistoricalReplayCandidateEvidence(
        capital_input=capital,
        provider_observation=observation,
        provider_evidence_id=(
            f"phase22-provider-numeric:{provider_numeric_freeze_sha256}:"
            f"{fresh.qore_symbol}"
        ),
    )
    return Phase22FreshCapitalProjection(
        candidate=candidate,
        provider_envelope=normalized,
        provider_numeric_freeze_sha256=provider_numeric_freeze_sha256,
    )
