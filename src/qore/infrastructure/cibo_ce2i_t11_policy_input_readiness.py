"""Fail-closed provenance contract for unresolved CE2I T11 policy inputs.

The execution-efficient cap consumes gross edge and nonlinear market impact.
Those values must never be invented from the linear cost model. This module
defines the evidence required before either input can be considered identified.

It does not estimate edge or impact, choose volume, or grant runtime authority.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)
from qore.infrastructure.cibo_ce2i_t11_execution_cost_calibration import (
    CiboT11ExecutionCostCalibration,
)


@dataclass(frozen=True, slots=True)
class T11GrossEdgeModelEvidence:
    qore_symbol: str
    as_of: datetime
    gross_edge_per_volume_usd: Decimal
    calibration_observations: int
    calibration_artifact_sha256: str
    model_artifact_sha256: str
    calibrated: bool
    fresh_oos_validated: bool
    temporal_stability_validated: bool
    outcome_leakage_detected: bool = False
    productive_authority: bool = False

    def __post_init__(self) -> None:
        if not isinstance(self.qore_symbol, str) or not self.qore_symbol:
            raise CiboCapitalManagementError(
                "T11 gross-edge qore_symbol is required"
            )
        _aware(self.as_of, "gross-edge as_of")
        if (
            not isinstance(self.gross_edge_per_volume_usd, Decimal)
            or not self.gross_edge_per_volume_usd.is_finite()
        ):
            raise CiboCapitalManagementError(
                "T11 gross edge must be finite Decimal"
            )
        if (
            not isinstance(self.calibration_observations, int)
            or isinstance(self.calibration_observations, bool)
            or self.calibration_observations < 0
        ):
            raise CiboCapitalManagementError(
                "T11 gross-edge observation count invalid"
            )
        _sha(self.calibration_artifact_sha256, "calibration_artifact_sha256")
        _sha(self.model_artifact_sha256, "model_artifact_sha256")
        for name in (
            "calibrated",
            "fresh_oos_validated",
            "temporal_stability_validated",
            "outcome_leakage_detected",
            "productive_authority",
        ):
            if type(getattr(self, name)) is not bool:
                raise CiboCapitalManagementError(
                    f"T11 gross-edge {name} must be bool"
                )
        if self.outcome_leakage_detected or self.productive_authority:
            raise CiboCapitalManagementError(
                "T11 gross-edge evidence cannot contain leakage/authority"
            )

    @property
    def ready(self) -> bool:
        return (
            self.calibration_observations > 0
            and self.calibrated
            and self.fresh_oos_validated
            and self.temporal_stability_validated
        )


@dataclass(frozen=True, slots=True)
class T11MarketImpactModelEvidence:
    qore_symbol: str
    frozen_at: datetime
    impact_cost_per_volume_squared_usd: Decimal
    empirical_observations: int
    distinct_volume_levels: int
    provider_execution_artifact_sha256: str
    model_artifact_sha256: str
    provider_bound: bool
    calibrated: bool
    fresh_oos_validated: bool
    target_aware: bool = False
    holdout_outcomes_used: bool = False
    productive_authority: bool = False

    def __post_init__(self) -> None:
        if not isinstance(self.qore_symbol, str) or not self.qore_symbol:
            raise CiboCapitalManagementError(
                "T11 market-impact qore_symbol is required"
            )
        _aware(self.frozen_at, "market-impact frozen_at")
        if (
            not isinstance(self.impact_cost_per_volume_squared_usd, Decimal)
            or not self.impact_cost_per_volume_squared_usd.is_finite()
            or self.impact_cost_per_volume_squared_usd < 0
        ):
            raise CiboCapitalManagementError(
                "T11 market-impact coefficient must be non-negative Decimal"
            )
        for name in ("empirical_observations", "distinct_volume_levels"):
            value = getattr(self, name)
            if (
                not isinstance(value, int)
                or isinstance(value, bool)
                or value < 0
            ):
                raise CiboCapitalManagementError(
                    f"T11 market-impact {name} invalid"
                )
        _sha(
            self.provider_execution_artifact_sha256,
            "provider_execution_artifact_sha256",
        )
        _sha(self.model_artifact_sha256, "model_artifact_sha256")
        for name in (
            "provider_bound",
            "calibrated",
            "fresh_oos_validated",
            "target_aware",
            "holdout_outcomes_used",
            "productive_authority",
        ):
            if type(getattr(self, name)) is not bool:
                raise CiboCapitalManagementError(
                    f"T11 market-impact {name} must be bool"
                )
        if (
            self.target_aware
            or self.holdout_outcomes_used
            or self.productive_authority
        ):
            raise CiboCapitalManagementError(
                "T11 market-impact evidence cannot use target/holdout/authority"
            )

    @property
    def ready(self) -> bool:
        return (
            self.empirical_observations > 0
            and self.distinct_volume_levels >= 2
            and self.provider_bound
            and self.calibrated
            and self.fresh_oos_validated
        )


@dataclass(frozen=True, slots=True)
class T11PolicyInputReadiness:
    frozen_at: datetime
    required_symbols: tuple[str, ...]
    linear_cost_model_ready: bool
    gross_edge_model_ready: bool
    market_impact_model_ready: bool
    gross_edge_symbols_ready: tuple[str, ...]
    market_impact_symbols_ready: tuple[str, ...]
    t11_policy_inputs_ready: bool
    historical_2017_execution_terms_proven: bool
    productive_authority: bool
    blockers: tuple[str, ...]

    def __post_init__(self) -> None:
        _aware(self.frozen_at, "policy-input frozen_at")
        if self.required_symbols != tuple(sorted(set(self.required_symbols))):
            raise CiboCapitalManagementError(
                "T11 policy-input required symbols must be sorted unique"
            )
        for name in (
            "linear_cost_model_ready",
            "gross_edge_model_ready",
            "market_impact_model_ready",
            "t11_policy_inputs_ready",
            "historical_2017_execution_terms_proven",
            "productive_authority",
        ):
            if type(getattr(self, name)) is not bool:
                raise CiboCapitalManagementError(
                    f"T11 policy-input {name} must be bool"
                )
        expected = all(
            (
                self.linear_cost_model_ready,
                self.gross_edge_model_ready,
                self.market_impact_model_ready,
            )
        )
        if self.t11_policy_inputs_ready != expected:
            raise CiboCapitalManagementError(
                "T11 policy-input readiness drift"
            )
        if (
            self.historical_2017_execution_terms_proven
            or self.productive_authority
        ):
            raise CiboCapitalManagementError(
                "T11 policy-input bridge cannot claim history/authority"
            )


def assess_t11_policy_input_readiness(
    *,
    linear_cost: CiboT11ExecutionCostCalibration,
    gross_edge_evidence: tuple[T11GrossEdgeModelEvidence, ...],
    market_impact_evidence: tuple[T11MarketImpactModelEvidence, ...],
    frozen_at: datetime,
) -> T11PolicyInputReadiness:
    """Require complete independent provenance for T11 nonlinear inputs."""

    if not isinstance(linear_cost, CiboT11ExecutionCostCalibration):
        raise CiboCapitalManagementError(
            "T11 policy-input readiness requires linear-cost calibration"
        )
    _aware(frozen_at, "policy-input frozen_at")
    if any(
        not isinstance(item, T11GrossEdgeModelEvidence)
        for item in gross_edge_evidence
    ):
        raise CiboCapitalManagementError(
            "T11 gross-edge evidence must be canonical"
        )
    if any(
        not isinstance(item, T11MarketImpactModelEvidence)
        for item in market_impact_evidence
    ):
        raise CiboCapitalManagementError(
            "T11 market-impact evidence must be canonical"
        )
    if any(item.as_of > frozen_at for item in gross_edge_evidence):
        raise CiboCapitalManagementError(
            "T11 gross-edge evidence postdates freeze"
        )
    if any(item.frozen_at > frozen_at for item in market_impact_evidence):
        raise CiboCapitalManagementError(
            "T11 market-impact evidence postdates freeze"
        )

    required = tuple(sorted(item.qore_symbol for item in linear_cost.symbols))
    _unique_symbols(gross_edge_evidence, "gross-edge")
    _unique_symbols(market_impact_evidence, "market-impact")
    required_set = set(required)
    if any(item.qore_symbol not in required_set for item in gross_edge_evidence):
        raise CiboCapitalManagementError(
            "T11 gross-edge evidence outside frozen symbol universe"
        )
    if any(
        item.qore_symbol not in required_set
        for item in market_impact_evidence
    ):
        raise CiboCapitalManagementError(
            "T11 market-impact evidence outside frozen symbol universe"
        )
    gross_ready = tuple(
        sorted(item.qore_symbol for item in gross_edge_evidence if item.ready)
    )
    impact_ready = tuple(
        sorted(item.qore_symbol for item in market_impact_evidence if item.ready)
    )
    gross_complete = bool(required) and set(required).issubset(gross_ready)
    impact_complete = bool(required) and set(required).issubset(impact_ready)
    linear_ready = linear_cost.linear_cost_model_ready

    blockers: list[str] = []
    if not linear_ready:
        blockers.append("T11_LINEAR_COST_MODEL_NOT_READY")
    if not gross_complete:
        blockers.append("T11_GROSS_EDGE_MODEL_NOT_IDENTIFIED")
    if not impact_complete:
        blockers.append("T11_MARKET_IMPACT_MODEL_NOT_IDENTIFIED")
    blockers.append("T11_HISTORICAL_2017_EXECUTION_TERMS_NOT_PROVEN")

    return T11PolicyInputReadiness(
        frozen_at=frozen_at,
        required_symbols=required,
        linear_cost_model_ready=linear_ready,
        gross_edge_model_ready=gross_complete,
        market_impact_model_ready=impact_complete,
        gross_edge_symbols_ready=gross_ready,
        market_impact_symbols_ready=impact_ready,
        t11_policy_inputs_ready=(
            linear_ready and gross_complete and impact_complete
        ),
        historical_2017_execution_terms_proven=False,
        productive_authority=False,
        blockers=tuple(blockers),
    )


def _unique_symbols(values: tuple[object, ...], label: str) -> None:
    symbols = tuple(getattr(item, "qore_symbol", None) for item in values)
    if any(not isinstance(item, str) or not item for item in symbols):
        raise CiboCapitalManagementError(
            f"T11 {label} evidence contains invalid symbol"
        )
    if len(symbols) != len(set(symbols)):
        raise CiboCapitalManagementError(
            f"T11 {label} evidence duplicates symbol"
        )


def _aware(value: datetime, name: str) -> None:
    if value.tzinfo is None or value.utcoffset() is None:
        raise CiboCapitalManagementError(f"T11 {name} must be timezone-aware")


def _sha(value: str, name: str) -> None:
    if (
        not isinstance(value, str)
        or not value.startswith("sha256:")
        or len(value) != 71
        or any(char not in "0123456789abcdef" for char in value[7:])
    ):
        raise CiboCapitalManagementError(
            f"T11 {name} must be canonical SHA-256"
        )
