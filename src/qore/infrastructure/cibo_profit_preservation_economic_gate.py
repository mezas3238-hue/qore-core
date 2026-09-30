"""Preregistered causal economic gate for GEN-C7 profit preservation.

Observed OOS paths alone do not identify a treatment effect. This gate accepts
only explicitly causal control/treatment summaries on an identical frozen
population and applies non-compensatory capital-preservation constraints.
Passing means eligibility for further research only.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from enum import StrEnum

from qore.infrastructure.cibo_compound_capital import CiboCompoundCapitalError
from qore.infrastructure.cibo_profit_preservation_shadow import (
    Genc7Action,
    genc7_policy_sha256,
)

GENC7_ECONOMIC_GATE_ID = (
    "CIBO_GENC7_PROFIT_PRESERVATION_NONCOMPENSATORY_ECONOMIC_GATE_V1"
)
GENC7_ECONOMIC_GATE_FROZEN_AT = datetime(2026, 9, 30, 19, 25, tzinfo=UTC)
GENC7_ECONOMIC_GATE_SHA256 = (
    "sha256:68d5e74113c51f8724a50e795e7f24df9f1bebab17ab405d82b492595f107063"
)


class Genc7EconomicRole(StrEnum):
    CONTROL = "CONTROL"
    TREATMENT = "TREATMENT"


class Genc7EconomicGateStatus(StrEnum):
    CONTROL = "CONTROL"
    ELIGIBLE_FOR_FURTHER_RESEARCH = "ELIGIBLE_FOR_FURTHER_RESEARCH"
    REJECTED_SAFETY_DETERIORATION = "REJECTED_SAFETY_DETERIORATION"
    REJECTED_NO_STRICT_ECONOMIC_IMPROVEMENT = (
        "REJECTED_NO_STRICT_ECONOMIC_IMPROVEMENT"
    )


@dataclass(frozen=True, slots=True)
class Genc7CausalEconomicObservation:
    candidate_id: str
    role: Genc7EconomicRole
    action: Genc7Action
    policy_sha256: str
    population_sha256: str
    provider_surface_sha256: str
    fold_ids: tuple[str, ...]
    horizon_start: datetime
    horizon_end: datetime
    realized_capital_delta_usd: Decimal
    realized_profit_delta_usd: Decimal
    ending_protected_floor_usd: Decimal
    minimum_base_capital_usd: Decimal
    minimum_compound_capital_usd: Decimal
    maximum_drawdown_usd: Decimal
    p99_drawdown_usd: Decimal
    peak_plausible_loss_usd: Decimal
    provider_cost_usd: Decimal
    minimum_optionality_usd: Decimal
    profit_retention_ratio: Decimal
    giveback_usd: Decimal
    capital_risk_time_productivity: Decimal
    causal_effect_identified: bool
    hindsight_retuned: bool = False
    weighted_score_used: bool = False
    productive_authority: bool = False
    certification_ready: bool = False

    def __post_init__(self) -> None:
        if not self.candidate_id:
            raise CiboCompoundCapitalError(
                "GEN-C7 economic candidate_id is required"
            )
        if type(self.role) is not Genc7EconomicRole:
            raise CiboCompoundCapitalError(
                "GEN-C7 economic role is invalid"
            )
        if type(self.action) is not Genc7Action:
            raise CiboCompoundCapitalError(
                "GEN-C7 economic action is invalid"
            )
        if self.role is Genc7EconomicRole.CONTROL:
            if self.action is not Genc7Action.HOLD_CURRENT_CAPITAL_STATE:
                raise CiboCompoundCapitalError(
                    "GEN-C7 economic control must HOLD current capital state"
                )
        elif self.action is Genc7Action.HOLD_CURRENT_CAPITAL_STATE:
            raise CiboCompoundCapitalError(
                "GEN-C7 economic treatment cannot masquerade as HOLD control"
            )
        if self.policy_sha256 != genc7_policy_sha256():
            raise CiboCompoundCapitalError(
                "GEN-C7 economic policy digest drift"
            )
        _sha(self.population_sha256, "population_sha256")
        _sha(self.provider_surface_sha256, "provider_surface_sha256")
        if not self.fold_ids or len(self.fold_ids) != len(set(self.fold_ids)):
            raise CiboCompoundCapitalError(
                "GEN-C7 economic fold ids must be non-empty and unique"
            )
        _aware(self.horizon_start, "horizon_start")
        _aware(self.horizon_end, "horizon_end")
        if self.horizon_end <= self.horizon_start:
            raise CiboCompoundCapitalError(
                "GEN-C7 economic horizon must be positive"
            )
        for name in (
            "ending_protected_floor_usd",
            "minimum_base_capital_usd",
            "minimum_compound_capital_usd",
            "maximum_drawdown_usd",
            "p99_drawdown_usd",
            "peak_plausible_loss_usd",
            "provider_cost_usd",
            "minimum_optionality_usd",
            "profit_retention_ratio",
            "giveback_usd",
        ):
            if getattr(self, name) < 0:
                raise CiboCompoundCapitalError(
                    f"GEN-C7 economic {name} must be non-negative"
                )
        if (
            not self.causal_effect_identified
            or self.hindsight_retuned
            or self.weighted_score_used
            or self.productive_authority
            or self.certification_ready
        ):
            raise CiboCompoundCapitalError(
                "GEN-C7 economic observation governance/causal drift"
            )


@dataclass(frozen=True, slots=True)
class Genc7EconomicGateRow:
    candidate_id: str
    action: Genc7Action
    status: Genc7EconomicGateStatus
    safety_no_worse: bool
    strict_economic_improvement: bool
    failed_dimensions: tuple[str, ...]
    weighted_score_used: bool = False
    production_promotion: bool = False


@dataclass(frozen=True, slots=True)
class Genc7EconomicGateReport:
    gate_id: str
    gate_sha256: str
    gate_frozen_at: datetime
    control_candidate_id: str
    rows: tuple[Genc7EconomicGateRow, ...]
    winner_candidate_id: None = None
    weighted_score_used: bool = False
    production_policy_selected: bool = False
    certification_ready: bool = False

    def __post_init__(self) -> None:
        if self.gate_id != GENC7_ECONOMIC_GATE_ID:
            raise CiboCompoundCapitalError(
                "GEN-C7 economic gate identity drift"
            )
        if self.gate_sha256 != GENC7_ECONOMIC_GATE_SHA256:
            raise CiboCompoundCapitalError(
                "GEN-C7 economic gate digest drift"
            )
        if self.gate_frozen_at != GENC7_ECONOMIC_GATE_FROZEN_AT:
            raise CiboCompoundCapitalError(
                "GEN-C7 economic gate freeze drift"
            )
        ids = tuple(row.candidate_id for row in self.rows)
        if len(ids) != len(set(ids)) or self.control_candidate_id not in ids:
            raise CiboCompoundCapitalError(
                "GEN-C7 economic gate rows/control are invalid"
            )
        if (
            self.winner_candidate_id is not None
            or self.weighted_score_used
            or self.production_policy_selected
            or self.certification_ready
        ):
            raise CiboCompoundCapitalError(
                "GEN-C7 economic gate cannot score/promote/certify"
            )


def evaluate_genc7_economic_gate(
    observations: tuple[Genc7CausalEconomicObservation, ...],
) -> Genc7EconomicGateReport:
    if not observations:
        raise CiboCompoundCapitalError(
            "GEN-C7 economic observations are required"
        )
    controls = tuple(
        item for item in observations if item.role is Genc7EconomicRole.CONTROL
    )
    if len(controls) != 1:
        raise CiboCompoundCapitalError(
            "GEN-C7 economic gate requires exactly one control"
        )
    control = controls[0]
    rows = tuple(_evaluate(control, item) for item in observations)
    return Genc7EconomicGateReport(
        gate_id=GENC7_ECONOMIC_GATE_ID,
        gate_sha256=GENC7_ECONOMIC_GATE_SHA256,
        gate_frozen_at=GENC7_ECONOMIC_GATE_FROZEN_AT,
        control_candidate_id=control.candidate_id,
        rows=rows,
    )


def _evaluate(
    control: Genc7CausalEconomicObservation,
    candidate: Genc7CausalEconomicObservation,
) -> Genc7EconomicGateRow:
    if candidate.candidate_id == control.candidate_id:
        return Genc7EconomicGateRow(
            candidate_id=candidate.candidate_id,
            action=candidate.action,
            status=Genc7EconomicGateStatus.CONTROL,
            safety_no_worse=True,
            strict_economic_improvement=False,
            failed_dimensions=(),
        )
    _require_comparable(control, candidate)

    failed: list[str] = []
    for name, candidate_value, control_value in (
        (
            "maximum_drawdown_usd",
            candidate.maximum_drawdown_usd,
            control.maximum_drawdown_usd,
        ),
        (
            "p99_drawdown_usd",
            candidate.p99_drawdown_usd,
            control.p99_drawdown_usd,
        ),
        (
            "peak_plausible_loss_usd",
            candidate.peak_plausible_loss_usd,
            control.peak_plausible_loss_usd,
        ),
        ("provider_cost_usd", candidate.provider_cost_usd, control.provider_cost_usd),
        ("giveback_usd", candidate.giveback_usd, control.giveback_usd),
    ):
        if candidate_value > control_value:
            failed.append(name)
    for name, candidate_value, control_value in (
        (
            "realized_capital_delta_usd",
            candidate.realized_capital_delta_usd,
            control.realized_capital_delta_usd,
        ),
        (
            "ending_protected_floor_usd",
            candidate.ending_protected_floor_usd,
            control.ending_protected_floor_usd,
        ),
        (
            "minimum_base_capital_usd",
            candidate.minimum_base_capital_usd,
            control.minimum_base_capital_usd,
        ),
        (
            "minimum_compound_capital_usd",
            candidate.minimum_compound_capital_usd,
            control.minimum_compound_capital_usd,
        ),
        (
            "minimum_optionality_usd",
            candidate.minimum_optionality_usd,
            control.minimum_optionality_usd,
        ),
        (
            "profit_retention_ratio",
            candidate.profit_retention_ratio,
            control.profit_retention_ratio,
        ),
    ):
        if candidate_value < control_value:
            failed.append(name)

    strict = any(
        (
            candidate.realized_capital_delta_usd
            > control.realized_capital_delta_usd,
            candidate.realized_profit_delta_usd
            > control.realized_profit_delta_usd,
            candidate.ending_protected_floor_usd
            > control.ending_protected_floor_usd,
            candidate.profit_retention_ratio > control.profit_retention_ratio,
            candidate.giveback_usd < control.giveback_usd,
            candidate.minimum_optionality_usd > control.minimum_optionality_usd,
            candidate.capital_risk_time_productivity
            > control.capital_risk_time_productivity,
        )
    )
    if failed:
        status = Genc7EconomicGateStatus.REJECTED_SAFETY_DETERIORATION
    elif not strict:
        status = (
            Genc7EconomicGateStatus.REJECTED_NO_STRICT_ECONOMIC_IMPROVEMENT
        )
    else:
        status = Genc7EconomicGateStatus.ELIGIBLE_FOR_FURTHER_RESEARCH

    return Genc7EconomicGateRow(
        candidate_id=candidate.candidate_id,
        action=candidate.action,
        status=status,
        safety_no_worse=not failed,
        strict_economic_improvement=strict,
        failed_dimensions=tuple(failed),
    )


def _require_comparable(
    control: Genc7CausalEconomicObservation,
    candidate: Genc7CausalEconomicObservation,
) -> None:
    if (
        candidate.policy_sha256 != control.policy_sha256
        or candidate.population_sha256 != control.population_sha256
        or candidate.provider_surface_sha256 != control.provider_surface_sha256
        or candidate.fold_ids != control.fold_ids
        or candidate.horizon_start != control.horizon_start
        or candidate.horizon_end != control.horizon_end
    ):
        raise CiboCompoundCapitalError(
            "GEN-C7 economic gate requires identical causal comparison surface"
        )


def _aware(value: datetime, name: str) -> None:
    if value.tzinfo is None or value.utcoffset() is None:
        raise CiboCompoundCapitalError(
            f"GEN-C7 economic {name} must be timezone-aware"
        )


def _sha(value: str, name: str) -> None:
    if (
        not value.startswith("sha256:")
        or len(value) != 71
        or any(char not in "0123456789abcdef" for char in value[7:])
    ):
        raise CiboCompoundCapitalError(
            f"GEN-C7 economic {name} must be canonical SHA-256"
        )
