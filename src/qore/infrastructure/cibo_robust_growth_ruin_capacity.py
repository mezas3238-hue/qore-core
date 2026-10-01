"""GEN-C9 robust growth / ruin / capacity science.

This engine compares preregistered capital-growth candidates on exactly the
same declared scenario set. It reports multi-dimensional evidence without
selecting a production winner, fitting to the World Cup target or claiming
market probabilities.

Research/shadow only. No sizing, Risk, execution, LIVE or real-capital
authority is granted.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import StrEnum

from qore.infrastructure.cibo_compound_capital import CiboCompoundCapitalError


class Genc9CandidateRole(StrEnum):
    CONTROL = "CONTROL"
    TREATMENT = "TREATMENT"


class Genc9GrowthFamily(StrEnum):
    CURRENT_CONTROL = "CURRENT_CONTROL"
    FRACTIONAL_GROWTH = "FRACTIONAL_GROWTH"
    DRAWDOWN_CONSTRAINED_GROWTH = "DRAWDOWN_CONSTRAINED_GROWTH"
    RISK_SENSITIVE_GROWTH = "RISK_SENSITIVE_GROWTH"
    DISTRIBUTIONALLY_ROBUST_GROWTH = "DISTRIBUTIONALLY_ROBUST_GROWTH"
    CAPACITY_SATURATION = "CAPACITY_SATURATION"


class Genc9Numeraire(StrEnum):
    PROVIDER_VALID_USD = "PROVIDER_VALID_USD"
    NORMALIZED_CAPITAL_UNITS = "NORMALIZED_CAPITAL_UNITS"


class Genc9ModelRiskDimension(StrEnum):
    ESTIMATION_ERROR = "ESTIMATION_ERROR"
    FAT_TAILS = "FAT_TAILS"
    SERIAL_DEPENDENCE = "SERIAL_DEPENDENCE"
    REGIME_SHIFT = "REGIME_SHIFT"
    EXECUTION_COST = "EXECUTION_COST"
    PROVIDER_LIMITS = "PROVIDER_LIMITS"


class Genc9ModelRiskStatus(StrEnum):
    EVIDENCED = "EVIDENCED"
    UNAVAILABLE = "UNAVAILABLE"


@dataclass(frozen=True, slots=True)
class Genc9CandidateDefinition:
    candidate_id: str
    role: Genc9CandidateRole
    family: Genc9GrowthFamily
    parameterization_sha256: str
    preregistered_at: datetime
    outcome_selected: bool = False
    world_cup_target_fitted: bool = False
    productive_authority: bool = False

    def __post_init__(self) -> None:
        if not self.candidate_id:
            raise CiboCompoundCapitalError(
                "GEN-C9 candidate identity is required"
            )
        if type(self.role) is not Genc9CandidateRole:
            raise CiboCompoundCapitalError(
                "GEN-C9 candidate role is invalid"
            )
        if type(self.family) is not Genc9GrowthFamily:
            raise CiboCompoundCapitalError(
                "GEN-C9 growth family is invalid"
            )
        _sha(self.parameterization_sha256, "parameterization_sha256")
        _aware(self.preregistered_at, "preregistered_at")
        if (
            self.outcome_selected
            or self.world_cup_target_fitted
            or self.productive_authority
        ):
            raise CiboCompoundCapitalError(
                "GEN-C9 candidate governance drift"
            )


@dataclass(frozen=True, slots=True)
class Genc9ModelRiskEvidence:
    dimension: Genc9ModelRiskDimension
    status: Genc9ModelRiskStatus
    evidence_sha256: str | None = None
    unavailable_reason: str | None = None

    def __post_init__(self) -> None:
        if type(self.dimension) is not Genc9ModelRiskDimension:
            raise CiboCompoundCapitalError(
                "GEN-C9 model-risk dimension is invalid"
            )
        if type(self.status) is not Genc9ModelRiskStatus:
            raise CiboCompoundCapitalError(
                "GEN-C9 model-risk status is invalid"
            )
        if self.status is Genc9ModelRiskStatus.EVIDENCED:
            if self.evidence_sha256 is None:
                raise CiboCompoundCapitalError(
                    "GEN-C9 evidenced model risk requires evidence SHA"
                )
            _sha(self.evidence_sha256, "model-risk evidence_sha256")
            if self.unavailable_reason is not None:
                raise CiboCompoundCapitalError(
                    "GEN-C9 evidenced model risk cannot be unavailable"
                )
        else:
            if not self.unavailable_reason:
                raise CiboCompoundCapitalError(
                    "GEN-C9 unavailable model risk requires reason"
                )
            if self.evidence_sha256 is not None:
                raise CiboCompoundCapitalError(
                    "GEN-C9 unavailable model risk cannot carry evidence SHA"
                )


@dataclass(frozen=True, slots=True)
class Genc9ScenarioDefinition:
    scenario_id: str
    scenario_evidence_sha256: str
    model_risks: tuple[Genc9ModelRiskEvidence, ...]
    market_probability_claimed: bool = False

    def __post_init__(self) -> None:
        if not self.scenario_id:
            raise CiboCompoundCapitalError(
                "GEN-C9 scenario identity is required"
            )
        _sha(self.scenario_evidence_sha256, "scenario_evidence_sha256")
        dimensions = tuple(item.dimension for item in self.model_risks)
        if len(dimensions) != len(set(dimensions)):
            raise CiboCompoundCapitalError(
                "GEN-C9 scenario model-risk dimensions must be unique"
            )
        if set(dimensions) != set(Genc9ModelRiskDimension):
            raise CiboCompoundCapitalError(
                "GEN-C9 scenario must declare every mandatory model risk"
            )
        if self.market_probability_claimed:
            raise CiboCompoundCapitalError(
                "GEN-C9 scenarios cannot claim market probability"
            )


@dataclass(frozen=True, slots=True)
class Genc9PathEvidence:
    candidate_id: str
    scenario_id: str
    evaluated_at: datetime
    numeraire: Genc9Numeraire
    initial_capital: Decimal
    ending_capital: Decimal
    minimum_capital: Decimal
    max_drawdown: Decimal
    max_time_underwater_minutes: Decimal
    max_recovery_minutes: Decimal
    peak_plausible_loss: Decimal
    ruin_boundary: Decimal
    ruin_occurred: bool
    capacity_breach: bool
    horizon_minutes: Decimal
    scenario_evidence_sha256: str
    causal_replay_sha256: str
    provider_economics_sha256: str | None = None
    future_leakage_used: bool = False
    market_probability_claimed: bool = False
    productive_authority: bool = False

    def __post_init__(self) -> None:
        if not self.candidate_id or not self.scenario_id:
            raise CiboCompoundCapitalError(
                "GEN-C9 path candidate/scenario identity is required"
            )
        _aware(self.evaluated_at, "evaluated_at")
        if type(self.numeraire) is not Genc9Numeraire:
            raise CiboCompoundCapitalError(
                "GEN-C9 path numeraire is invalid"
            )
        for name in (
            "initial_capital",
            "ending_capital",
            "minimum_capital",
            "max_drawdown",
            "max_time_underwater_minutes",
            "max_recovery_minutes",
            "peak_plausible_loss",
            "ruin_boundary",
            "horizon_minutes",
        ):
            value = getattr(self, name)
            if (
                not isinstance(value, Decimal)
                or not value.is_finite()
                or value < 0
            ):
                raise CiboCompoundCapitalError(
                    f"GEN-C9 path {name} must be finite non-negative Decimal"
                )
        if self.initial_capital <= 0 or self.horizon_minutes <= 0:
            raise CiboCompoundCapitalError(
                "GEN-C9 initial capital/horizon must be positive"
            )
        if self.peak_plausible_loss <= 0:
            raise CiboCompoundCapitalError(
                "GEN-C9 peak plausible loss must be positive"
            )
        if self.minimum_capital > min(
            self.initial_capital,
            self.ending_capital,
        ):
            raise CiboCompoundCapitalError(
                "GEN-C9 minimum capital is inconsistent"
            )
        if self.max_drawdown < self.initial_capital - self.minimum_capital:
            raise CiboCompoundCapitalError(
                "GEN-C9 max drawdown is inconsistent with minimum capital"
            )
        if self.ruin_boundary > self.initial_capital:
            raise CiboCompoundCapitalError(
                "GEN-C9 ruin boundary exceeds initial capital"
            )
        if self.ruin_occurred != (
            self.minimum_capital <= self.ruin_boundary
        ):
            raise CiboCompoundCapitalError(
                "GEN-C9 ruin flag does not match declared boundary"
            )
        for name in ("ruin_occurred", "capacity_breach"):
            if type(getattr(self, name)) is not bool:
                raise CiboCompoundCapitalError(
                    f"GEN-C9 {name} must be bool"
                )
        _sha(self.scenario_evidence_sha256, "scenario_evidence_sha256")
        _sha(self.causal_replay_sha256, "causal_replay_sha256")
        if self.numeraire is Genc9Numeraire.PROVIDER_VALID_USD:
            if self.provider_economics_sha256 is None:
                raise CiboCompoundCapitalError(
                    "GEN-C9 USD path requires provider economics evidence"
                )
            _sha(
                self.provider_economics_sha256,
                "provider_economics_sha256",
            )
        elif self.provider_economics_sha256 is not None:
            raise CiboCompoundCapitalError(
                "GEN-C9 normalized path cannot fabricate provider economics"
            )
        if (
            self.future_leakage_used
            or self.market_probability_claimed
            or self.productive_authority
        ):
            raise CiboCompoundCapitalError(
                "GEN-C9 path governance drift"
            )

    @property
    def ending_multiple(self) -> Decimal:
        return self.ending_capital / self.initial_capital

    @property
    def return_per_peak_plausible_loss(self) -> Decimal:
        return (
            self.ending_capital - self.initial_capital
        ) / self.peak_plausible_loss


@dataclass(frozen=True, slots=True)
class Genc9CandidateSummary:
    candidate_id: str
    role: Genc9CandidateRole
    family: Genc9GrowthFamily
    numeraire: Genc9Numeraire
    path_count: int
    scenario_ids: tuple[str, ...]
    minimum_ending_capital: Decimal
    median_ending_capital: Decimal
    minimum_ending_multiple: Decimal
    median_ending_multiple: Decimal
    p95_max_drawdown: Decimal
    p99_max_drawdown: Decimal
    maximum_drawdown: Decimal
    maximum_time_underwater_minutes: Decimal
    p95_recovery_minutes: Decimal
    ruin_path_count: int
    empirical_scenario_ruin_frequency: Decimal
    capacity_breach_path_count: int
    empirical_capacity_breach_frequency: Decimal
    positive_ending_delta_paths: int
    minimum_realized_capital: Decimal
    maximum_peak_plausible_loss: Decimal
    minimum_return_per_peak_plausible_loss: Decimal
    empirical_frequency_is_market_probability: bool = False
    economic_value_demonstrated: bool = False
    certification_ready: bool = False

    def __post_init__(self) -> None:
        if self.path_count <= 0 or self.path_count != len(self.scenario_ids):
            raise CiboCompoundCapitalError(
                "GEN-C9 summary path/scenario count drift"
            )
        if (
            self.empirical_frequency_is_market_probability
            or self.economic_value_demonstrated
            or self.certification_ready
        ):
            raise CiboCompoundCapitalError(
                "GEN-C9 descriptive summary cannot claim certification"
            )


@dataclass(frozen=True, slots=True)
class Genc9ResearchReport:
    research_id: str
    control_candidate_id: str
    numeraire: Genc9Numeraire
    scenario_ids: tuple[str, ...]
    summaries: tuple[Genc9CandidateSummary, ...]
    winner_candidate_id: None = None
    weighted_score_used: bool = False
    production_policy_selected: bool = False
    economic_gate_preregistered: bool = False
    value_demonstrated: bool = False
    oos_pass: bool = False
    stress_pass: bool = False
    temporal_replication_pass: bool = False
    certification_ready: bool = False

    def __post_init__(self) -> None:
        if not self.research_id or not self.control_candidate_id:
            raise CiboCompoundCapitalError(
                "GEN-C9 report identity/control is required"
            )
        if self.winner_candidate_id is not None:
            raise CiboCompoundCapitalError(
                "GEN-C9 V1 cannot select a winner"
            )
        if any(
            (
                self.weighted_score_used,
                self.production_policy_selected,
                self.economic_gate_preregistered,
                self.value_demonstrated,
                self.oos_pass,
                self.stress_pass,
                self.temporal_replication_pass,
                self.certification_ready,
            )
        ):
            raise CiboCompoundCapitalError(
                "GEN-C9 descriptive report cannot claim scientific closure"
            )


def evaluate_genc9_robust_growth(
    *,
    research_id: str,
    candidates: tuple[Genc9CandidateDefinition, ...],
    scenarios: tuple[Genc9ScenarioDefinition, ...],
    paths: tuple[Genc9PathEvidence, ...],
) -> Genc9ResearchReport:
    """Compare preregistered candidates without outcome-driven ranking."""

    if not research_id:
        raise CiboCompoundCapitalError(
            "GEN-C9 research_id is required"
        )
    if not candidates or not scenarios or not paths:
        raise CiboCompoundCapitalError(
            "GEN-C9 candidates/scenarios/paths are required"
        )
    candidate_ids = tuple(item.candidate_id for item in candidates)
    if len(candidate_ids) != len(set(candidate_ids)):
        raise CiboCompoundCapitalError(
            "GEN-C9 candidate ids must be unique"
        )
    scenario_ids = tuple(item.scenario_id for item in scenarios)
    if len(scenario_ids) != len(set(scenario_ids)):
        raise CiboCompoundCapitalError(
            "GEN-C9 scenario ids must be unique"
        )
    controls = tuple(
        item for item in candidates if item.role is Genc9CandidateRole.CONTROL
    )
    if len(controls) != 1:
        raise CiboCompoundCapitalError(
            "GEN-C9 requires exactly one control candidate"
        )
    scenario_by_id = {item.scenario_id: item for item in scenarios}
    by_candidate: dict[str, list[Genc9PathEvidence]] = {
        item.candidate_id: [] for item in candidates
    }
    definitions = {item.candidate_id: item for item in candidates}
    for path in paths:
        definition = definitions.get(path.candidate_id)
        if definition is None:
            raise CiboCompoundCapitalError(
                "GEN-C9 path references unknown candidate"
            )
        scenario = scenario_by_id.get(path.scenario_id)
        if scenario is None:
            raise CiboCompoundCapitalError(
                "GEN-C9 path references unknown scenario"
            )
        if path.scenario_evidence_sha256 != scenario.scenario_evidence_sha256:
            raise CiboCompoundCapitalError(
                "GEN-C9 path/scenario evidence digest drift"
            )
        if path.evaluated_at < definition.preregistered_at:
            raise CiboCompoundCapitalError(
                "GEN-C9 path predates candidate preregistration"
            )
        by_candidate[path.candidate_id].append(path)

    expected_set = set(scenario_ids)
    for candidate_id, rows in by_candidate.items():
        row_ids = tuple(item.scenario_id for item in rows)
        if len(row_ids) != len(set(row_ids)) or set(row_ids) != expected_set:
            raise CiboCompoundCapitalError(
                f"GEN-C9 scenario coverage drift for {candidate_id}"
            )

    all_numeraires = {item.numeraire for item in paths}
    if len(all_numeraires) != 1:
        raise CiboCompoundCapitalError(
            "GEN-C9 report cannot compare mixed numeraires"
        )
    numeraire = next(iter(all_numeraires))

    for scenario_id in scenario_ids:
        initial = {
            item.initial_capital
            for item in paths
            if item.scenario_id == scenario_id
        }
        horizons = {
            item.horizon_minutes
            for item in paths
            if item.scenario_id == scenario_id
        }
        if len(initial) != 1 or len(horizons) != 1:
            raise CiboCompoundCapitalError(
                "GEN-C9 candidates must share scenario initial state/horizon"
            )

    summaries = tuple(
        _summarize_candidate(
            definition=definition,
            paths=tuple(
                sorted(
                    by_candidate[definition.candidate_id],
                    key=lambda item: item.scenario_id,
                )
            ),
        )
        for definition in candidates
    )
    return Genc9ResearchReport(
        research_id=research_id,
        control_candidate_id=controls[0].candidate_id,
        numeraire=numeraire,
        scenario_ids=tuple(sorted(scenario_ids)),
        summaries=summaries,
        winner_candidate_id=None,
        weighted_score_used=False,
        production_policy_selected=False,
        economic_gate_preregistered=False,
        value_demonstrated=False,
        oos_pass=False,
        stress_pass=False,
        temporal_replication_pass=False,
        certification_ready=False,
    )


def _summarize_candidate(
    *,
    definition: Genc9CandidateDefinition,
    paths: tuple[Genc9PathEvidence, ...],
) -> Genc9CandidateSummary:
    endings = tuple(item.ending_capital for item in paths)
    multiples = tuple(item.ending_multiple for item in paths)
    drawdowns = tuple(item.max_drawdown for item in paths)
    recoveries = tuple(item.max_recovery_minutes for item in paths)
    return_per_loss = tuple(
        item.return_per_peak_plausible_loss for item in paths
    )
    count = len(paths)
    ruins = sum(item.ruin_occurred for item in paths)
    breaches = sum(item.capacity_breach for item in paths)
    return Genc9CandidateSummary(
        candidate_id=definition.candidate_id,
        role=definition.role,
        family=definition.family,
        numeraire=paths[0].numeraire,
        path_count=count,
        scenario_ids=tuple(item.scenario_id for item in paths),
        minimum_ending_capital=min(endings),
        median_ending_capital=_median(endings),
        minimum_ending_multiple=min(multiples),
        median_ending_multiple=_median(multiples),
        p95_max_drawdown=_nearest_rank(drawdowns, 95),
        p99_max_drawdown=_nearest_rank(drawdowns, 99),
        maximum_drawdown=max(drawdowns),
        maximum_time_underwater_minutes=max(
            item.max_time_underwater_minutes for item in paths
        ),
        p95_recovery_minutes=_nearest_rank(recoveries, 95),
        ruin_path_count=ruins,
        empirical_scenario_ruin_frequency=Decimal(ruins) / Decimal(count),
        capacity_breach_path_count=breaches,
        empirical_capacity_breach_frequency=(
            Decimal(breaches) / Decimal(count)
        ),
        positive_ending_delta_paths=sum(
            item.ending_capital > item.initial_capital for item in paths
        ),
        minimum_realized_capital=min(
            item.minimum_capital for item in paths
        ),
        maximum_peak_plausible_loss=max(
            item.peak_plausible_loss for item in paths
        ),
        minimum_return_per_peak_plausible_loss=min(return_per_loss),
        empirical_frequency_is_market_probability=False,
        economic_value_demonstrated=False,
        certification_ready=False,
    )


def _nearest_rank(
    values: tuple[Decimal, ...],
    percentile: int,
) -> Decimal:
    if not values or percentile <= 0 or percentile > 100:
        raise CiboCompoundCapitalError(
            "GEN-C9 nearest-rank input is invalid"
        )
    ordered = sorted(values)
    rank = (percentile * len(ordered) + 99) // 100
    return ordered[max(0, rank - 1)]


def _median(values: tuple[Decimal, ...]) -> Decimal:
    ordered = sorted(values)
    count = len(ordered)
    middle = count // 2
    if count % 2:
        return ordered[middle]
    return (ordered[middle - 1] + ordered[middle]) / Decimal(2)


def _aware(value: datetime, name: str) -> None:
    if (
        not isinstance(value, datetime)
        or value.tzinfo is None
        or value.utcoffset() is None
    ):
        raise CiboCompoundCapitalError(
            f"GEN-C9 {name} must be timezone-aware"
        )


def _sha(value: str, name: str) -> None:
    if (
        not isinstance(value, str)
        or not value.startswith("sha256:")
        or len(value) != 71
        or any(char not in "0123456789abcdef" for char in value[7:])
    ):
        raise CiboCompoundCapitalError(
            f"GEN-C9 {name} must be canonical SHA-256"
        )
