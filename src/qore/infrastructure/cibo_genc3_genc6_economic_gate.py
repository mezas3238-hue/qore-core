"""Non-compensatory 4/4 economic gate for CIBO GEN-C3..GEN-C6.

The underlying engines and OOS binders deliberately do not claim economic
utility. This gate is the separate preregistered evaluator. It consumes only
causally identified, provider-valid fold summaries and never grants runtime,
Risk, execution, merge or certification authority.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from enum import StrEnum

from qore.infrastructure.cibo_compound_capital import CiboCompoundCapitalError

GATE_ID = "CIBO_GENC3_GENC6_NONCOMPENSATORY_ECONOMIC_GATE_V1"
GATE_FROZEN_AT = datetime(2026, 9, 30, 20, 5, tzinfo=UTC)
GATE_SHA256 = (
    "sha256:6d77b29b321d1dfc36f92adf7a81cdf62cf2221e"
    "ce3e4631d23daf999c8819af"
)
_CANONICAL_FOLDS = ("WF1", "WF2", "WF3", "WF4")
_SHA256_RE = re.compile(r"^sha256:[0-9a-f]{64}$")


class Genc3To6Workstream(StrEnum):
    GENC3 = "GEN-C3"
    GENC4 = "GEN-C4"
    GENC5 = "GEN-C5"
    GENC6 = "GEN-C6"


class Genc3To6EconomicRole(StrEnum):
    CONTROL = "CONTROL"
    TREATMENT = "TREATMENT"


class Genc3To6EconomicStatus(StrEnum):
    CONTROL = "CONTROL"
    ELIGIBLE_FOR_FURTHER_RESEARCH = "ELIGIBLE_FOR_FURTHER_RESEARCH"
    REJECTED_SAFETY_DETERIORATION = "REJECTED_SAFETY_DETERIORATION"
    REJECTED_NOT_STRICT_4_OF_4 = "REJECTED_NOT_STRICT_4_OF_4"


@dataclass(frozen=True, slots=True)
class Genc3To6FoldEconomicObservation:
    candidate_id: str
    workstream: Genc3To6Workstream
    role: Genc3To6EconomicRole
    fold_id: str
    population_sha256: str
    provider_surface_sha256: str
    causal_horizon_sha256: str
    protocol_binding_sha256: str
    realized_net_delta_usd: Decimal
    ending_realized_capital_usd: Decimal
    maximum_drawdown_usd: Decimal
    p99_drawdown_usd: Decimal
    peak_plausible_loss_usd: Decimal
    peak_margin_occupancy_usd: Decimal
    provider_cost_usd: Decimal
    capital_minutes: Decimal
    minimum_liquid_reserve_usd: Decimal
    minimum_optionality_usd: Decimal
    p95_recovery_minutes: Decimal
    capital_risk_time_productivity: Decimal
    causal_effect_identified: bool
    treatment_preregistered_before_outcomes: bool
    portfolio_cycle_complete: bool = False
    marginal_unit_identified: bool = False
    chronological_sequence_preserved: bool = False
    true_scarcity_observed: bool = False
    future_outcome_used: bool = False
    weighted_score_used: bool = False
    productive_authority: bool = False
    certification_ready: bool = False

    def __post_init__(self) -> None:
        if not self.candidate_id:
            raise CiboCompoundCapitalError(
                "GEN-C3..C6 economic candidate identity is required"
            )
        if type(self.workstream) is not Genc3To6Workstream:
            raise CiboCompoundCapitalError(
                "GEN-C3..C6 economic workstream is invalid"
            )
        if type(self.role) is not Genc3To6EconomicRole:
            raise CiboCompoundCapitalError(
                "GEN-C3..C6 economic role is invalid"
            )
        if self.fold_id not in _CANONICAL_FOLDS:
            raise CiboCompoundCapitalError(
                "GEN-C3..C6 economic fold must be WF1..WF4"
            )
        for name in (
            "population_sha256",
            "provider_surface_sha256",
            "causal_horizon_sha256",
            "protocol_binding_sha256",
        ):
            _sha(getattr(self, name), name)

        for name in (
            "ending_realized_capital_usd",
            "maximum_drawdown_usd",
            "p99_drawdown_usd",
            "peak_plausible_loss_usd",
            "peak_margin_occupancy_usd",
            "provider_cost_usd",
            "capital_minutes",
            "minimum_liquid_reserve_usd",
            "minimum_optionality_usd",
            "p95_recovery_minutes",
            "capital_risk_time_productivity",
        ):
            value = getattr(self, name)
            if (
                not isinstance(value, Decimal)
                or not value.is_finite()
                or value < 0
            ):
                raise CiboCompoundCapitalError(
                    f"GEN-C3..C6 economic {name} must be finite non-negative"
                )
        if (
            not isinstance(self.realized_net_delta_usd, Decimal)
            or not self.realized_net_delta_usd.is_finite()
        ):
            raise CiboCompoundCapitalError(
                "GEN-C3..C6 realized net delta must be finite Decimal"
            )
        for name in (
            "causal_effect_identified",
            "treatment_preregistered_before_outcomes",
            "portfolio_cycle_complete",
            "marginal_unit_identified",
            "chronological_sequence_preserved",
            "true_scarcity_observed",
            "future_outcome_used",
            "weighted_score_used",
            "productive_authority",
            "certification_ready",
        ):
            if type(getattr(self, name)) is not bool:
                raise CiboCompoundCapitalError(
                    f"GEN-C3..C6 economic {name} must be bool"
                )
        if (
            not self.causal_effect_identified
            or not self.treatment_preregistered_before_outcomes
            or self.future_outcome_used
            or self.weighted_score_used
            or self.productive_authority
            or self.certification_ready
        ):
            raise CiboCompoundCapitalError(
                "GEN-C3..C6 economic observation governance/causal drift"
            )
        required_condition = {
            Genc3To6Workstream.GENC3: self.portfolio_cycle_complete,
            Genc3To6Workstream.GENC4: self.marginal_unit_identified,
            Genc3To6Workstream.GENC5: self.chronological_sequence_preserved,
            Genc3To6Workstream.GENC6: self.true_scarcity_observed,
        }[self.workstream]
        if not required_condition:
            raise CiboCompoundCapitalError(
                f"{self.workstream.value} economic mechanism condition missing"
            )


@dataclass(frozen=True, slots=True)
class Genc3To6CandidateVerdict:
    workstream: Genc3To6Workstream
    candidate_id: str
    status: Genc3To6EconomicStatus
    passed_fold_ids: tuple[str, ...]
    failed_fold_ids: tuple[str, ...]
    failed_dimensions: tuple[str, ...]
    winner_selected: bool = False
    production_promotion: bool = False

    def __post_init__(self) -> None:
        if type(self.workstream) is not Genc3To6Workstream or not self.candidate_id:
            raise CiboCompoundCapitalError(
                "GEN-C3..C6 economic verdict identity is invalid"
            )
        if type(self.status) is not Genc3To6EconomicStatus:
            raise CiboCompoundCapitalError(
                "GEN-C3..C6 economic verdict status is invalid"
            )
        for values, label in (
            (self.passed_fold_ids, "passed folds"),
            (self.failed_fold_ids, "failed folds"),
            (self.failed_dimensions, "failed dimensions"),
        ):
            if not isinstance(values, tuple) or any(
                not isinstance(item, str) or not item for item in values
            ):
                raise CiboCompoundCapitalError(
                    f"GEN-C3..C6 economic verdict {label} are invalid"
                )
            if len(values) != len(set(values)):
                raise CiboCompoundCapitalError(
                    f"GEN-C3..C6 economic verdict {label} must be unique"
                )
        passed = set(self.passed_fold_ids)
        failed = set(self.failed_fold_ids)
        canonical = set(_CANONICAL_FOLDS)
        if (
            not passed <= canonical
            or not failed <= canonical
            or passed & failed
            or self.passed_fold_ids
            != tuple(item for item in _CANONICAL_FOLDS if item in passed)
            or self.failed_fold_ids
            != tuple(item for item in _CANONICAL_FOLDS if item in failed)
        ):
            raise CiboCompoundCapitalError(
                "GEN-C3..C6 economic verdict fold identity drift"
            )
        for name in ("winner_selected", "production_promotion"):
            if type(getattr(self, name)) is not bool:
                raise CiboCompoundCapitalError(
                    f"GEN-C3..C6 economic verdict {name} must be bool"
                )
        if self.winner_selected or self.production_promotion:
            raise CiboCompoundCapitalError(
                "GEN-C3..C6 economic verdict cannot select/promote"
            )
        if self.status is Genc3To6EconomicStatus.CONTROL:
            if (
                self.passed_fold_ids != _CANONICAL_FOLDS
                or self.failed_fold_ids
                or self.failed_dimensions
            ):
                raise CiboCompoundCapitalError(
                    "GEN-C3..C6 CONTROL verdict fold drift"
                )
            return
        if passed | failed != canonical:
            raise CiboCompoundCapitalError(
                "GEN-C3..C6 treatment verdict requires WF1..WF4 disposition"
            )
        for dimension in self.failed_dimensions:
            fold_id, separator, _name = dimension.partition(":")
            if not separator or fold_id not in failed:
                raise CiboCompoundCapitalError(
                    "GEN-C3..C6 failed dimension/fold drift"
                )
        safety_failed = any(
            not item.endswith(":NO_STRICT_IMPROVEMENT")
            for item in self.failed_dimensions
        )
        expected_status = (
            Genc3To6EconomicStatus.REJECTED_SAFETY_DETERIORATION
            if safety_failed
            else (
                Genc3To6EconomicStatus.REJECTED_NOT_STRICT_4_OF_4
                if self.passed_fold_ids != _CANONICAL_FOLDS
                else Genc3To6EconomicStatus.ELIGIBLE_FOR_FURTHER_RESEARCH
            )
        )
        if self.status is not expected_status:
            raise CiboCompoundCapitalError(
                "GEN-C3..C6 economic verdict status/fold drift"
            )


@dataclass(frozen=True, slots=True)
class Genc3To6EconomicGateReport:
    gate_id: str
    gate_sha256: str
    gate_frozen_at: datetime
    verdicts: tuple[Genc3To6CandidateVerdict, ...]
    weighted_score_used: bool = False
    winner_selected: bool = False
    production_policy_selected: bool = False
    certification_ready: bool = False

    def __post_init__(self) -> None:
        if self.gate_id != GATE_ID:
            raise CiboCompoundCapitalError(
                "GEN-C3..C6 economic gate identity drift"
            )
        if self.gate_sha256 != GATE_SHA256:
            raise CiboCompoundCapitalError(
                "GEN-C3..C6 economic gate digest drift"
            )
        if self.gate_frozen_at != GATE_FROZEN_AT:
            raise CiboCompoundCapitalError(
                "GEN-C3..C6 economic gate freeze drift"
            )
        if (
            not isinstance(self.verdicts, tuple)
            or not self.verdicts
            or any(
                not isinstance(item, Genc3To6CandidateVerdict)
                for item in self.verdicts
            )
        ):
            raise CiboCompoundCapitalError(
                "GEN-C3..C6 economic gate requires canonical verdicts"
            )
        keys = tuple(
            (item.workstream, item.candidate_id) for item in self.verdicts
        )
        if len(keys) != len(set(keys)):
            raise CiboCompoundCapitalError(
                "GEN-C3..C6 economic verdict identities must be unique"
            )
        for workstream in {item.workstream for item in self.verdicts}:
            controls = tuple(
                item
                for item in self.verdicts
                if item.workstream is workstream
                and item.status is Genc3To6EconomicStatus.CONTROL
            )
            if len(controls) != 1:
                raise CiboCompoundCapitalError(
                    "GEN-C3..C6 economic gate requires one control verdict per workstream"
                )
        if (
            self.weighted_score_used
            or self.winner_selected
            or self.production_policy_selected
            or self.certification_ready
        ):
            raise CiboCompoundCapitalError(
                "GEN-C3..C6 economic gate cannot score/promote/certify"
            )


def evaluate_genc3_genc6_economic_gate(
    observations: tuple[Genc3To6FoldEconomicObservation, ...],
) -> Genc3To6EconomicGateReport:
    """Require non-compensatory economic improvement independently in 4/4 folds."""

    if not observations:
        raise CiboCompoundCapitalError(
            "GEN-C3..C6 economic observations are required"
        )

    verdicts: list[Genc3To6CandidateVerdict] = []
    for workstream in sorted(
        {item.workstream for item in observations},
        key=lambda item: item.value,
    ):
        rows = tuple(
            item for item in observations if item.workstream is workstream
        )
        controls = {
            item.candidate_id
            for item in rows
            if item.role is Genc3To6EconomicRole.CONTROL
        }
        if len(controls) != 1:
            raise CiboCompoundCapitalError(
                f"{workstream.value} economic gate requires one control candidate"
            )
        control_id = next(iter(controls))
        control_rows = _four_fold_rows(
            tuple(item for item in rows if item.candidate_id == control_id)
        )
        verdicts.append(
            Genc3To6CandidateVerdict(
                workstream=workstream,
                candidate_id=control_id,
                status=Genc3To6EconomicStatus.CONTROL,
                passed_fold_ids=_CANONICAL_FOLDS,
                failed_fold_ids=(),
                failed_dimensions=(),
            )
        )

        treatment_ids = sorted(
            {
                item.candidate_id
                for item in rows
                if item.role is Genc3To6EconomicRole.TREATMENT
            }
        )
        if not treatment_ids:
            raise CiboCompoundCapitalError(
                f"{workstream.value} economic gate requires treatment candidate"
            )
        for candidate_id in treatment_ids:
            treatment_rows = _four_fold_rows(
                tuple(item for item in rows if item.candidate_id == candidate_id)
            )
            verdicts.append(
                _evaluate_candidate(
                    workstream=workstream,
                    candidate_id=candidate_id,
                    control_rows=control_rows,
                    treatment_rows=treatment_rows,
                )
            )

    return Genc3To6EconomicGateReport(
        gate_id=GATE_ID,
        gate_sha256=GATE_SHA256,
        gate_frozen_at=GATE_FROZEN_AT,
        verdicts=tuple(verdicts),
    )


def _four_fold_rows(
    rows: tuple[Genc3To6FoldEconomicObservation, ...],
) -> dict[str, Genc3To6FoldEconomicObservation]:
    by_fold = {item.fold_id: item for item in rows}
    if len(rows) != 4 or tuple(sorted(by_fold)) != _CANONICAL_FOLDS:
        raise CiboCompoundCapitalError(
            "GEN-C3..C6 economic candidate requires exactly WF1..WF4"
        )
    if len({item.candidate_id for item in rows}) != 1:
        raise CiboCompoundCapitalError(
            "GEN-C3..C6 economic candidate identity drift across folds"
        )
    return by_fold


def _evaluate_candidate(
    *,
    workstream: Genc3To6Workstream,
    candidate_id: str,
    control_rows: dict[str, Genc3To6FoldEconomicObservation],
    treatment_rows: dict[str, Genc3To6FoldEconomicObservation],
) -> Genc3To6CandidateVerdict:
    passed: list[str] = []
    failed: list[str] = []
    failed_dimensions: list[str] = []
    safety_failed = False

    for fold_id in _CANONICAL_FOLDS:
        control = control_rows[fold_id]
        treatment = treatment_rows[fold_id]
        _require_comparable(control, treatment)

        dimensions: list[str] = []
        for name, treatment_value, control_value in (
            (
                "maximum_drawdown_usd",
                treatment.maximum_drawdown_usd,
                control.maximum_drawdown_usd,
            ),
            (
                "p99_drawdown_usd",
                treatment.p99_drawdown_usd,
                control.p99_drawdown_usd,
            ),
            (
                "peak_plausible_loss_usd",
                treatment.peak_plausible_loss_usd,
                control.peak_plausible_loss_usd,
            ),
            (
                "peak_margin_occupancy_usd",
                treatment.peak_margin_occupancy_usd,
                control.peak_margin_occupancy_usd,
            ),
            (
                "provider_cost_usd",
                treatment.provider_cost_usd,
                control.provider_cost_usd,
            ),
        ):
            if treatment_value > control_value:
                dimensions.append(name)
        for name, treatment_value, control_value in (
            (
                "realized_net_delta_usd",
                treatment.realized_net_delta_usd,
                control.realized_net_delta_usd,
            ),
            (
                "ending_realized_capital_usd",
                treatment.ending_realized_capital_usd,
                control.ending_realized_capital_usd,
            ),
            (
                "minimum_liquid_reserve_usd",
                treatment.minimum_liquid_reserve_usd,
                control.minimum_liquid_reserve_usd,
            ),
            (
                "minimum_optionality_usd",
                treatment.minimum_optionality_usd,
                control.minimum_optionality_usd,
            ),
        ):
            if treatment_value < control_value:
                dimensions.append(name)

        strict = any(
            (
                treatment.realized_net_delta_usd
                > control.realized_net_delta_usd,
                treatment.ending_realized_capital_usd
                > control.ending_realized_capital_usd,
                treatment.capital_risk_time_productivity
                > control.capital_risk_time_productivity,
                treatment.capital_minutes < control.capital_minutes,
                treatment.minimum_liquid_reserve_usd
                > control.minimum_liquid_reserve_usd,
                treatment.minimum_optionality_usd
                > control.minimum_optionality_usd,
                treatment.p95_recovery_minutes
                < control.p95_recovery_minutes,
            )
        )
        if dimensions:
            safety_failed = True
            failed.append(fold_id)
            failed_dimensions.extend(
                f"{fold_id}:{dimension}" for dimension in dimensions
            )
        elif not strict:
            failed.append(fold_id)
            failed_dimensions.append(f"{fold_id}:NO_STRICT_IMPROVEMENT")
        else:
            passed.append(fold_id)

    if safety_failed:
        status = Genc3To6EconomicStatus.REJECTED_SAFETY_DETERIORATION
    elif failed:
        status = Genc3To6EconomicStatus.REJECTED_NOT_STRICT_4_OF_4
    else:
        status = Genc3To6EconomicStatus.ELIGIBLE_FOR_FURTHER_RESEARCH
    return Genc3To6CandidateVerdict(
        workstream=workstream,
        candidate_id=candidate_id,
        status=status,
        passed_fold_ids=tuple(passed),
        failed_fold_ids=tuple(failed),
        failed_dimensions=tuple(failed_dimensions),
    )


def _require_comparable(
    control: Genc3To6FoldEconomicObservation,
    treatment: Genc3To6FoldEconomicObservation,
) -> None:
    if (
        control.workstream is not treatment.workstream
        or control.fold_id != treatment.fold_id
        or control.population_sha256 != treatment.population_sha256
        or control.provider_surface_sha256 != treatment.provider_surface_sha256
        or control.causal_horizon_sha256 != treatment.causal_horizon_sha256
        or control.protocol_binding_sha256 != treatment.protocol_binding_sha256
    ):
        raise CiboCompoundCapitalError(
            "GEN-C3..C6 economic gate requires identical causal comparison surface"
        )


def _sha(value: str, name: str) -> None:
    if not isinstance(value, str) or _SHA256_RE.fullmatch(value) is None:
        raise CiboCompoundCapitalError(
            f"GEN-C3..C6 economic {name} must be canonical SHA-256"
        )
