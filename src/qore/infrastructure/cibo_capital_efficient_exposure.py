"""CEL-1 / CEL-2 capital-efficient exposure economics for CIBO.

This module makes three economic quantities explicit and non-interchangeable:

NOTIONAL EXPOSURE
MARGIN OCCUPANCY
STRESSED ECONOMIC LOSS

It composes existing provider-normalized economics and GEN-C4 marginal capital
evidence. It does not replace GEN-C6, change its frozen policy, size a position,
authorize Risk, or mutate Execution.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import datetime
from decimal import Decimal

from qore.infrastructure.cibo_compound_capital import CiboCompoundCapitalError
from qore.infrastructure.cibo_marginal_capital_utility_evidence import (
    MarginalCapitalUtilityEvidence,
)
from qore.infrastructure.cibo_provider_economic_normalization import (
    ProviderEconomicEnvelope,
)


def _positive(value: Decimal, name: str) -> None:
    if (
        not isinstance(value, Decimal)
        or not value.is_finite()
        or value <= 0
    ):
        raise CiboCompoundCapitalError(
            f"CEL {name} must be finite positive Decimal"
        )


def _nonnegative(value: Decimal, name: str) -> None:
    if (
        not isinstance(value, Decimal)
        or not value.is_finite()
        or value < 0
    ):
        raise CiboCompoundCapitalError(
            f"CEL {name} must be finite non-negative Decimal"
        )


def _aware(value: datetime, name: str) -> None:
    if value.tzinfo is None or value.utcoffset() is None:
        raise CiboCompoundCapitalError(
            f"CEL {name} must be timezone-aware"
        )


@dataclass(frozen=True, slots=True)
class CiboStressedLossScenarioEvidence:
    """Pre-outcome loss scenarios; values come from evidence, never defaults."""

    scenario_id: str
    observed_at: datetime
    produced_at: datetime
    gap_through_stop_loss_usd: Decimal
    stressed_execution_cost_usd: Decimal
    liquidity_shock_loss_usd: Decimal
    portfolio_convergence_increment_usd: Decimal
    forced_liquidation_loss_usd: Decimal
    evidence_sha256: str
    source: str
    calibrated: bool = False
    fresh_oos_validated: bool = False
    outcome_present: bool = False
    productive_authority: bool = False

    def __post_init__(self) -> None:
        if not self.scenario_id or not self.source:
            raise CiboCompoundCapitalError(
                "CEL stressed scenario identity/source is required"
            )
        _aware(self.observed_at, "stressed scenario observed_at")
        _aware(self.produced_at, "stressed scenario produced_at")
        if self.produced_at < self.observed_at:
            raise CiboCompoundCapitalError(
                "CEL stressed scenario cannot be produced before observation"
            )
        for name in (
            "gap_through_stop_loss_usd",
            "stressed_execution_cost_usd",
            "liquidity_shock_loss_usd",
            "portfolio_convergence_increment_usd",
            "forced_liquidation_loss_usd",
        ):
            _nonnegative(getattr(self, name), name)
        if (
            not isinstance(self.evidence_sha256, str)
            or not self.evidence_sha256.startswith("sha256:")
            or len(self.evidence_sha256) != 71
            or any(
                char not in "0123456789abcdef"
                for char in self.evidence_sha256[7:]
            )
        ):
            raise CiboCompoundCapitalError(
                "CEL stressed scenario evidence_sha256 must be canonical"
            )
        for name in (
            "calibrated",
            "fresh_oos_validated",
            "outcome_present",
            "productive_authority",
        ):
            if type(getattr(self, name)) is not bool:
                raise CiboCompoundCapitalError(
                    f"CEL stressed scenario {name} must be bool"
                )
        if self.outcome_present or self.productive_authority:
            raise CiboCompoundCapitalError(
                "CEL stressed scenario must be pre-outcome research evidence"
            )

    def fingerprint(self) -> str:
        payload = asdict(self)
        payload["observed_at"] = self.observed_at.isoformat()
        payload["produced_at"] = self.produced_at.isoformat()
        payload = {
            key: str(value) if isinstance(value, Decimal) else value
            for key, value in payload.items()
        }
        raw = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        return "sha256:" + hashlib.sha256(raw.encode()).hexdigest()


@dataclass(frozen=True, slots=True)
class CiboCapitalEfficientExposureState:
    """One causal exposure unit with notional/margin/loss kept separate."""

    state_id: str
    decision_at: datetime
    provider_key: str
    qore_symbol: str
    provider_symbol: str
    executable_volume: Decimal
    notional_exposure_usd: Decimal
    margin_occupancy_usd: Decimal
    structural_stop_loss_usd: Decimal
    normal_execution_cost_usd: Decimal
    base_plausible_loss_usd: Decimal
    stressed_economic_loss_usd: Decimal
    gap_scenario_loss_usd: Decimal
    liquidity_scenario_loss_usd: Decimal
    convergence_scenario_loss_usd: Decimal
    liquidation_scenario_loss_usd: Decimal
    notional_to_margin: Decimal
    notional_to_stressed_loss: Decimal
    margin_to_stressed_loss: Decimal
    provider_evidence_sha256: str
    marginal_evidence_sha256: str
    stress_evidence_sha256: str
    low_margin_is_low_risk: bool = False
    outcome_present: bool = False
    sizing_authority: bool = False
    capital_authority: bool = False
    risk_authority: bool = False
    execution_authority: bool = False

    def __post_init__(self) -> None:
        if (
            not self.state_id
            or not self.provider_key
            or not self.qore_symbol
            or not self.provider_symbol
        ):
            raise CiboCompoundCapitalError(
                "CEL exposure state identity is required"
            )
        _aware(self.decision_at, "exposure decision_at")
        for name in (
            "executable_volume",
            "notional_exposure_usd",
            "margin_occupancy_usd",
            "structural_stop_loss_usd",
            "base_plausible_loss_usd",
            "stressed_economic_loss_usd",
            "notional_to_margin",
            "notional_to_stressed_loss",
            "margin_to_stressed_loss",
        ):
            _positive(getattr(self, name), name)
        for name in (
            "normal_execution_cost_usd",
            "gap_scenario_loss_usd",
            "liquidity_scenario_loss_usd",
            "convergence_scenario_loss_usd",
            "liquidation_scenario_loss_usd",
        ):
            _nonnegative(getattr(self, name), name)
        if self.stressed_economic_loss_usd < self.base_plausible_loss_usd:
            raise CiboCompoundCapitalError(
                "CEL stressed loss cannot understate base plausible loss"
            )
        for name in (
            "provider_evidence_sha256",
            "marginal_evidence_sha256",
            "stress_evidence_sha256",
        ):
            value = getattr(self, name)
            if (
                not isinstance(value, str)
                or not value.startswith("sha256:")
                or len(value) != 71
            ):
                raise CiboCompoundCapitalError(
                    f"CEL {name} must be canonical SHA-256"
                )
        if self.low_margin_is_low_risk:
            raise CiboCompoundCapitalError(
                "CEL forbids LOW MARGIN == LOW RISK"
            )
        if (
            self.outcome_present
            or self.sizing_authority
            or self.capital_authority
            or self.risk_authority
            or self.execution_authority
        ):
            raise CiboCompoundCapitalError(
                "CEL exposure state cannot carry outcome or runtime authority"
            )

    def fingerprint(self) -> str:
        payload = asdict(self)
        payload["decision_at"] = self.decision_at.isoformat()
        payload = {
            key: str(value) if isinstance(value, Decimal) else value
            for key, value in payload.items()
        }
        raw = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        return "sha256:" + hashlib.sha256(raw.encode()).hexdigest()


def build_capital_efficient_exposure_state(
    *,
    state_id: str,
    decision_at: datetime,
    envelope: ProviderEconomicEnvelope,
    executable_volume: Decimal,
    marginal_evidence: MarginalCapitalUtilityEvidence,
    stress: CiboStressedLossScenarioEvidence,
) -> CiboCapitalEfficientExposureState:
    """Bind provider economics + GEN-C4 + stress evidence without outcomes."""

    if not isinstance(envelope, ProviderEconomicEnvelope):
        raise CiboCompoundCapitalError(
            "CEL exposure requires ProviderEconomicEnvelope"
        )
    if not isinstance(marginal_evidence, MarginalCapitalUtilityEvidence):
        raise CiboCompoundCapitalError(
            "CEL exposure requires GEN-C4 marginal evidence"
        )
    if not isinstance(stress, CiboStressedLossScenarioEvidence):
        raise CiboCompoundCapitalError(
            "CEL exposure requires stressed loss evidence"
        )
    _aware(decision_at, "exposure decision_at")
    _positive(executable_volume, "executable_volume")
    if executable_volume < envelope.minimum_executable_volume:
        raise CiboCompoundCapitalError(
            "CEL exposure volume is below provider/methodology minimum"
        )
    if executable_volume > envelope.maximum_volume:
        raise CiboCompoundCapitalError(
            "CEL exposure volume exceeds provider maximum"
        )
    steps = executable_volume / envelope.volume_step
    if steps != steps.to_integral_value():
        raise CiboCompoundCapitalError(
            "CEL exposure volume is not provider-step aligned"
        )
    if envelope.observed_at > decision_at:
        raise CiboCompoundCapitalError(
            "CEL provider economics arrive from the future"
        )
    if stress.observed_at > decision_at or stress.produced_at > decision_at:
        raise CiboCompoundCapitalError(
            "CEL stress evidence arrives from the future"
        )
    if marginal_evidence.decision_at != decision_at:
        raise CiboCompoundCapitalError(
            "CEL marginal evidence decision-time binding drift"
        )
    if marginal_evidence.outcome_present:
        raise CiboCompoundCapitalError(
            "CEL exposure cannot consume outcome-bearing marginal evidence"
        )

    notional = envelope.notional_per_volume_usd * executable_volume
    margin = envelope.margin_per_volume_usd * executable_volume
    stop = envelope.cibo_stop_loss_per_volume_usd * executable_volume
    execution = envelope.execution_cost_per_volume_usd * executable_volume

    if marginal_evidence.incremental_stop_risk_usd != stop:
        raise CiboCompoundCapitalError(
            "CEL GEN-C4/provider stop-risk binding drift"
        )
    if marginal_evidence.incremental_margin_usd != margin:
        raise CiboCompoundCapitalError(
            "CEL GEN-C4/provider margin binding drift"
        )
    if marginal_evidence.incremental_execution_cost_usd != execution:
        raise CiboCompoundCapitalError(
            "CEL GEN-C4/provider execution-cost binding drift"
        )

    base = stop + execution
    gap = stress.gap_through_stop_loss_usd + stress.stressed_execution_cost_usd
    liquidity = (
        stress.liquidity_shock_loss_usd + stress.stressed_execution_cost_usd
    )
    convergence = base + stress.portfolio_convergence_increment_usd
    liquidation = (
        stress.forced_liquidation_loss_usd
        + stress.stressed_execution_cost_usd
    )
    stressed = max(base, gap, liquidity, convergence, liquidation)
    if stressed <= 0:
        raise CiboCompoundCapitalError(
            "CEL stressed economic loss must be positive"
        )

    provider_payload = {
        "provider_key": envelope.provider_key,
        "qore_symbol": envelope.qore_symbol,
        "provider_symbol": envelope.provider_symbol,
        "observed_at": envelope.observed_at.isoformat(),
        "notional_per_volume_usd": str(envelope.notional_per_volume_usd),
        "margin_per_volume_usd": str(envelope.margin_per_volume_usd),
        "cibo_stop_loss_per_volume_usd": str(
            envelope.cibo_stop_loss_per_volume_usd
        ),
        "execution_cost_per_volume_usd": str(
            envelope.execution_cost_per_volume_usd
        ),
        "volume_step": str(envelope.volume_step),
        "minimum_executable_volume": str(
            envelope.minimum_executable_volume
        ),
        "maximum_volume": str(envelope.maximum_volume),
    }
    provider_sha = "sha256:" + hashlib.sha256(
        json.dumps(
            provider_payload,
            sort_keys=True,
            separators=(",", ":"),
        ).encode()
    ).hexdigest()

    marginal_payload = {
        "evidence_id": marginal_evidence.evidence_id,
        "signal_fingerprint": marginal_evidence.signal_fingerprint,
        "decision_at": marginal_evidence.decision_at.isoformat(),
        "stop_risk": str(marginal_evidence.incremental_stop_risk_usd),
        "margin": str(marginal_evidence.incremental_margin_usd),
        "execution_cost": str(
            marginal_evidence.incremental_execution_cost_usd
        ),
        "outcome_present": marginal_evidence.outcome_present,
    }
    marginal_sha = "sha256:" + hashlib.sha256(
        json.dumps(
            marginal_payload,
            sort_keys=True,
            separators=(",", ":"),
        ).encode()
    ).hexdigest()

    return CiboCapitalEfficientExposureState(
        state_id=state_id,
        decision_at=decision_at,
        provider_key=envelope.provider_key,
        qore_symbol=envelope.qore_symbol,
        provider_symbol=envelope.provider_symbol,
        executable_volume=executable_volume,
        notional_exposure_usd=notional,
        margin_occupancy_usd=margin,
        structural_stop_loss_usd=stop,
        normal_execution_cost_usd=execution,
        base_plausible_loss_usd=base,
        stressed_economic_loss_usd=stressed,
        gap_scenario_loss_usd=gap,
        liquidity_scenario_loss_usd=liquidity,
        convergence_scenario_loss_usd=convergence,
        liquidation_scenario_loss_usd=liquidation,
        notional_to_margin=notional / margin,
        notional_to_stressed_loss=notional / stressed,
        margin_to_stressed_loss=margin / stressed,
        provider_evidence_sha256=provider_sha,
        marginal_evidence_sha256=marginal_sha,
        stress_evidence_sha256=stress.fingerprint(),
    )
