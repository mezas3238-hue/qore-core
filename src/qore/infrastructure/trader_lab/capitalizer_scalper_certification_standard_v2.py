"""Executable certification gate for QORE Capitalizer Cognitive Scalper V1.

This module encodes the Owner-frozen edge-first certification standard. It does
not compute trading outcomes and cannot promote a trader by itself. It evaluates
explicit evidence supplied by research workflows and fails closed on missing
mandatory evidence.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum

IDENTITY = "QORE_CAPITALIZER_SCALPER_CERTIFICATION_STANDARD_V2"

PF_PER_OOS_MIN = Decimal("1.50")
PF_COMBINED_OOS_MIN = Decimal("1.70")
EXPECTANCY_MIN_EXCLUSIVE = Decimal("0")
SHARPE_OOS_MIN = Decimal("1.50")
SORTINO_OOS_MIN = Decimal("2.00")
OBSERVED_DD_MAX_R = Decimal("10")
OWNER_ACCEPTANCE_DD_MAX_R = Decimal("6")
PAYOFF_MIN = Decimal("1.20")
MC_POSITIVE_MIN = Decimal("0.90")
MC_P95_DD_MAX_R = Decimal("15")
POST_COST_PF_MIN_EXCLUSIVE = Decimal("1")
POST_COST_EXPECTANCY_MIN_EXCLUSIVE = Decimal("0")
WINNER_COUNT_PRESERVATION_MIN = Decimal("0.80")
WINNER_R_PRESERVATION_MIN = Decimal("0.90")


class CertificationClassification(StrEnum):
    ACCEPTED = "ACCEPTED"
    INTERVENTION = "INTERVENTION — CONTINUE WORK"
    REJECTED = "REJECTED"


class GateStatus(StrEnum):
    PASS = "PASS"
    FAIL = "FAIL"
    MISSING = "MISSING"
    NOT_APPLICABLE = "NOT_APPLICABLE"


@dataclass(frozen=True, slots=True)
class OosEraEvidence:
    era: str
    profit_factor: Decimal | None = None
    expectancy_r_per_trade: Decimal | None = None
    sharpe_annualized: Decimal | None = None
    sortino_annualized: Decimal | None = None
    observed_max_drawdown_r: Decimal | None = None
    payoff_ratio: Decimal | None = None
    payoff_compensation_verified: bool = False

    def __post_init__(self) -> None:
        if not self.era:
            raise ValueError("OOS era name must be non-empty")
        for field_name in (
            "profit_factor",
            "expectancy_r_per_trade",
            "sharpe_annualized",
            "sortino_annualized",
            "observed_max_drawdown_r",
            "payoff_ratio",
        ):
            value = getattr(self, field_name)
            if value is not None and (
                not isinstance(value, Decimal) or not value.is_finite()
            ):
                raise ValueError(f"{field_name} must be finite Decimal or None")
        if (
            self.observed_max_drawdown_r is not None
            and self.observed_max_drawdown_r < 0
        ):
            raise ValueError("observed_max_drawdown_r cannot be negative")
        if self.payoff_ratio is not None and self.payoff_ratio < 0:
            raise ValueError("payoff_ratio cannot be negative")


@dataclass(frozen=True, slots=True)
class CertificationEvidence:
    oos_eras: tuple[OosEraEvidence, ...]
    combined_oos_profit_factor: Decimal | None = None
    owner_observed_max_drawdown_r: Decimal | None = None
    author_fidelity_audit_passed: bool | None = None
    monte_carlo_positive_probability: Decimal | None = None
    monte_carlo_p95_drawdown_r: Decimal | None = None
    post_cost_profit_factor: Decimal | None = None
    post_cost_expectancy_r_per_trade: Decimal | None = None
    temporal_stability_verified: bool | None = None
    anti_leakage_audit_passed: bool | None = None
    prohibited_outcome_aware_logic_detected: bool = False
    catastrophic_loss_clustering_absent: bool | None = None
    mae_mfe_audit_complete: bool | None = None
    loser_anatomy_audit_complete: bool | None = None
    density_sufficient_after_quality: bool | None = None
    fresh_holdout_integrity_verified: bool | None = None
    fresh_holdout_evaluated_once: bool | None = None
    fresh_holdout_passed: bool | None = None
    winner_preservation_required: bool = False
    winner_count_preservation: Decimal | None = None
    winner_r_preservation: Decimal | None = None
    risk_review_passed: bool | None = None
    cibo_review_passed: bool | None = None
    independent_validation_passed: bool | None = None
    fatal_falsification: bool = False
    fatal_falsification_reason: str | None = None

    def __post_init__(self) -> None:
        names = tuple(row.era for row in self.oos_eras)
        if len(set(names)) != len(names):
            raise ValueError("OOS era names must be unique")
        for field_name in (
            "combined_oos_profit_factor",
            "owner_observed_max_drawdown_r",
            "monte_carlo_positive_probability",
            "monte_carlo_p95_drawdown_r",
            "post_cost_profit_factor",
            "post_cost_expectancy_r_per_trade",
            "winner_count_preservation",
            "winner_r_preservation",
        ):
            value = getattr(self, field_name)
            if value is not None and (
                not isinstance(value, Decimal) or not value.is_finite()
            ):
                raise ValueError(f"{field_name} must be finite Decimal or None")
        if (
            self.owner_observed_max_drawdown_r is not None
            and self.owner_observed_max_drawdown_r < 0
        ):
            raise ValueError("Owner observed drawdown must be non-negative")
        for field_name in (
            "monte_carlo_positive_probability",
            "winner_count_preservation",
        ):
            value = getattr(self, field_name)
            if value is not None and not Decimal("0") <= value <= Decimal("1"):
                raise ValueError(f"{field_name} must be in [0, 1]")
        if (
            self.winner_r_preservation is not None
            and self.winner_r_preservation < 0
        ):
            raise ValueError("winner_r_preservation must be non-negative")
        if (
            self.monte_carlo_p95_drawdown_r is not None
            and self.monte_carlo_p95_drawdown_r < 0
        ):
            raise ValueError("monte_carlo_p95_drawdown_r cannot be negative")
        if self.fatal_falsification and not self.fatal_falsification_reason:
            raise ValueError("fatal falsification requires a reason")


@dataclass(frozen=True, slots=True)
class GateResult:
    gate: str
    status: GateStatus
    detail: str


@dataclass(frozen=True, slots=True)
class CertificationDecision:
    identity: str
    classification: CertificationClassification
    gates: tuple[GateResult, ...]
    accepted: bool
    missing_gate_count: int
    failed_gate_count: int


def _numeric_gate(
    *,
    name: str,
    value: Decimal | None,
    predicate: bool | None,
    detail_when_present: str,
) -> GateResult:
    if value is None:
        return GateResult(name, GateStatus.MISSING, "mandatory evidence missing")
    return GateResult(
        name,
        GateStatus.PASS if predicate is True else GateStatus.FAIL,
        detail_when_present,
    )


def _boolean_gate(name: str, value: bool | None) -> GateResult:
    if value is None:
        return GateResult(name, GateStatus.MISSING, "mandatory evidence missing")
    return GateResult(
        name,
        GateStatus.PASS if value else GateStatus.FAIL,
        str(value).lower(),
    )


def _era_gates(row: OosEraEvidence) -> tuple[GateResult, ...]:
    prefix = f"OOS[{row.era}]"
    payoff_present = row.payoff_ratio
    gates = [
        _numeric_gate(
            name=f"{prefix}.profit_factor",
            value=row.profit_factor,
            predicate=(
                None
                if row.profit_factor is None
                else row.profit_factor >= PF_PER_OOS_MIN
            ),
            detail_when_present=(
                "unknown"
                if row.profit_factor is None
                else f"{row.profit_factor} >= {PF_PER_OOS_MIN}"
            ),
        ),
        _numeric_gate(
            name=f"{prefix}.expectancy",
            value=row.expectancy_r_per_trade,
            predicate=(
                None
                if row.expectancy_r_per_trade is None
                else row.expectancy_r_per_trade > EXPECTANCY_MIN_EXCLUSIVE
            ),
            detail_when_present=(
                "unknown"
                if row.expectancy_r_per_trade is None
                else f"{row.expectancy_r_per_trade} > 0R/trade"
            ),
        ),
        _numeric_gate(
            name=f"{prefix}.sharpe",
            value=row.sharpe_annualized,
            predicate=(
                None
                if row.sharpe_annualized is None
                else row.sharpe_annualized >= SHARPE_OOS_MIN
            ),
            detail_when_present=(
                "unknown"
                if row.sharpe_annualized is None
                else f"{row.sharpe_annualized} >= {SHARPE_OOS_MIN}"
            ),
        ),
        _numeric_gate(
            name=f"{prefix}.sortino",
            value=row.sortino_annualized,
            predicate=(
                None
                if row.sortino_annualized is None
                else row.sortino_annualized >= SORTINO_OOS_MIN
            ),
            detail_when_present=(
                "unknown"
                if row.sortino_annualized is None
                else f"{row.sortino_annualized} >= {SORTINO_OOS_MIN}"
            ),
        ),
        _numeric_gate(
            name=f"{prefix}.observed_max_drawdown",
            value=row.observed_max_drawdown_r,
            predicate=(
                None
                if row.observed_max_drawdown_r is None
                else row.observed_max_drawdown_r <= OBSERVED_DD_MAX_R
            ),
            detail_when_present=(
                "unknown"
                if row.observed_max_drawdown_r is None
                else f"{row.observed_max_drawdown_r} <= {OBSERVED_DD_MAX_R}R"
            ),
        ),
    ]
    if payoff_present is None and not row.payoff_compensation_verified:
        gates.append(
            GateResult(
                f"{prefix}.payoff",
                GateStatus.MISSING,
                "payoff missing and no reviewed statistical-compensation evidence",
            )
        )
    elif row.payoff_compensation_verified:
        gates.append(
            GateResult(
                f"{prefix}.payoff",
                GateStatus.PASS,
                "reviewed statistical-compensation evidence verified",
            )
        )
    else:
        assert payoff_present is not None
        gates.append(
            GateResult(
                f"{prefix}.payoff",
                (
                    GateStatus.PASS
                    if payoff_present >= PAYOFF_MIN
                    else GateStatus.FAIL
                ),
                f"{payoff_present} >= {PAYOFF_MIN}",
            )
        )
    return tuple(gates)


def evaluate_certification(
    evidence: CertificationEvidence,
) -> CertificationDecision:
    gates: list[GateResult] = []

    if not evidence.oos_eras:
        gates.append(
            GateResult(
                "oos_eras",
                GateStatus.MISSING,
                "at least one designated OOS era is required",
            )
        )
    for era in evidence.oos_eras:
        gates.extend(_era_gates(era))

    gates.extend(
        [
            _boolean_gate(
                "author_fidelity_audit",
                evidence.author_fidelity_audit_passed,
            ),
            _numeric_gate(
                name="owner_acceptance_drawdown",
                value=evidence.owner_observed_max_drawdown_r,
                predicate=(
                    None
                    if evidence.owner_observed_max_drawdown_r is None
                    else (
                        evidence.owner_observed_max_drawdown_r
                        <= OWNER_ACCEPTANCE_DD_MAX_R
                    )
                ),
                detail_when_present=(
                    "unknown"
                    if evidence.owner_observed_max_drawdown_r is None
                    else (
                        f"{evidence.owner_observed_max_drawdown_r} "
                        f"<= {OWNER_ACCEPTANCE_DD_MAX_R}R (Owner acceptance)"
                    )
                ),
            ),
            _numeric_gate(
                name="combined_oos_profit_factor",
                value=evidence.combined_oos_profit_factor,
                predicate=(
                    None
                    if evidence.combined_oos_profit_factor is None
                    else (
                        evidence.combined_oos_profit_factor
                        >= PF_COMBINED_OOS_MIN
                    )
                ),
                detail_when_present=(
                    "unknown"
                    if evidence.combined_oos_profit_factor is None
                    else (
                        f"{evidence.combined_oos_profit_factor} "
                        f">= {PF_COMBINED_OOS_MIN}"
                    )
                ),
            ),
            _numeric_gate(
                name="monte_carlo_positive_probability",
                value=evidence.monte_carlo_positive_probability,
                predicate=(
                    None
                    if evidence.monte_carlo_positive_probability is None
                    else (
                        evidence.monte_carlo_positive_probability
                        >= MC_POSITIVE_MIN
                    )
                ),
                detail_when_present=(
                    "unknown"
                    if evidence.monte_carlo_positive_probability is None
                    else (
                        f"{evidence.monte_carlo_positive_probability} "
                        f">= {MC_POSITIVE_MIN}"
                    )
                ),
            ),
            _numeric_gate(
                name="monte_carlo_p95_drawdown",
                value=evidence.monte_carlo_p95_drawdown_r,
                predicate=(
                    None
                    if evidence.monte_carlo_p95_drawdown_r is None
                    else evidence.monte_carlo_p95_drawdown_r <= MC_P95_DD_MAX_R
                ),
                detail_when_present=(
                    "unknown"
                    if evidence.monte_carlo_p95_drawdown_r is None
                    else (
                        f"{evidence.monte_carlo_p95_drawdown_r} "
                        f"<= {MC_P95_DD_MAX_R}R"
                    )
                ),
            ),
            _numeric_gate(
                name="post_cost_profit_factor",
                value=evidence.post_cost_profit_factor,
                predicate=(
                    None
                    if evidence.post_cost_profit_factor is None
                    else (
                        evidence.post_cost_profit_factor
                        > POST_COST_PF_MIN_EXCLUSIVE
                    )
                ),
                detail_when_present=(
                    "unknown"
                    if evidence.post_cost_profit_factor is None
                    else f"{evidence.post_cost_profit_factor} > 1"
                ),
            ),
            _numeric_gate(
                name="post_cost_expectancy",
                value=evidence.post_cost_expectancy_r_per_trade,
                predicate=(
                    None
                    if evidence.post_cost_expectancy_r_per_trade is None
                    else (
                        evidence.post_cost_expectancy_r_per_trade
                        > POST_COST_EXPECTANCY_MIN_EXCLUSIVE
                    )
                ),
                detail_when_present=(
                    "unknown"
                    if evidence.post_cost_expectancy_r_per_trade is None
                    else (
                        f"{evidence.post_cost_expectancy_r_per_trade} "
                        "> 0R/trade"
                    )
                ),
            ),
            _boolean_gate(
                "temporal_stability",
                evidence.temporal_stability_verified,
            ),
            _boolean_gate(
                "anti_leakage_audit",
                evidence.anti_leakage_audit_passed,
            ),
            _boolean_gate(
                "loss_clustering_survival",
                evidence.catastrophic_loss_clustering_absent,
            ),
            _boolean_gate(
                "mae_mfe_audit",
                evidence.mae_mfe_audit_complete,
            ),
            _boolean_gate(
                "loser_anatomy_audit",
                evidence.loser_anatomy_audit_complete,
            ),
            _boolean_gate(
                "density_after_quality",
                evidence.density_sufficient_after_quality,
            ),
            _boolean_gate(
                "fresh_holdout_integrity",
                evidence.fresh_holdout_integrity_verified,
            ),
            _boolean_gate(
                "fresh_holdout_opened_once",
                evidence.fresh_holdout_evaluated_once,
            ),
            _boolean_gate(
                "fresh_holdout_pass",
                evidence.fresh_holdout_passed,
            ),
            _boolean_gate("risk_review", evidence.risk_review_passed),
            _boolean_gate("cibo_review", evidence.cibo_review_passed),
            _boolean_gate(
                "independent_validation",
                evidence.independent_validation_passed,
            ),
        ]
    )

    if evidence.winner_preservation_required:
        gates.extend(
            [
                _numeric_gate(
                    name="winner_count_preservation",
                    value=evidence.winner_count_preservation,
                    predicate=(
                        None
                        if evidence.winner_count_preservation is None
                        else (
                            evidence.winner_count_preservation
                            >= WINNER_COUNT_PRESERVATION_MIN
                        )
                    ),
                    detail_when_present=(
                        "unknown"
                        if evidence.winner_count_preservation is None
                        else (
                            f"{evidence.winner_count_preservation} "
                            f">= {WINNER_COUNT_PRESERVATION_MIN}"
                        )
                    ),
                ),
                _numeric_gate(
                    name="winner_r_preservation",
                    value=evidence.winner_r_preservation,
                    predicate=(
                        None
                        if evidence.winner_r_preservation is None
                        else (
                            evidence.winner_r_preservation
                            >= WINNER_R_PRESERVATION_MIN
                        )
                    ),
                    detail_when_present=(
                        "unknown"
                        if evidence.winner_r_preservation is None
                        else (
                            f"{evidence.winner_r_preservation} "
                            f">= {WINNER_R_PRESERVATION_MIN}"
                        )
                    ),
                ),
            ]
        )
    else:
        gates.extend(
            [
                GateResult(
                    "winner_count_preservation",
                    GateStatus.NOT_APPLICABLE,
                    "candidate does not change admission/outcome intelligence",
                ),
                GateResult(
                    "winner_r_preservation",
                    GateStatus.NOT_APPLICABLE,
                    "candidate does not change admission/outcome intelligence",
                ),
            ]
        )

    if evidence.prohibited_outcome_aware_logic_detected:
        gates.append(
            GateResult(
                "prohibited_outcome_aware_logic",
                GateStatus.FAIL,
                "prohibited outcome-aware runtime logic detected",
            )
        )
    else:
        gates.append(
            GateResult(
                "prohibited_outcome_aware_logic",
                GateStatus.PASS,
                "none detected",
            )
        )

    if evidence.fatal_falsification:
        gates.append(
            GateResult(
                "fatal_falsification",
                GateStatus.FAIL,
                evidence.fatal_falsification_reason or "fatal falsification",
            )
        )
    else:
        gates.append(
            GateResult(
                "fatal_falsification",
                GateStatus.PASS,
                "none declared",
            )
        )

    failed = tuple(gate for gate in gates if gate.status is GateStatus.FAIL)
    missing = tuple(gate for gate in gates if gate.status is GateStatus.MISSING)
    fatal = (
        evidence.fatal_falsification
        or evidence.prohibited_outcome_aware_logic_detected
    )
    mandatory = tuple(
        gate
        for gate in gates
        if gate.status is not GateStatus.NOT_APPLICABLE
    )
    all_pass = bool(mandatory) and all(
        gate.status is GateStatus.PASS for gate in mandatory
    )

    if fatal:
        classification = CertificationClassification.REJECTED
    elif all_pass:
        classification = CertificationClassification.ACCEPTED
    else:
        classification = CertificationClassification.INTERVENTION

    return CertificationDecision(
        identity=IDENTITY,
        classification=classification,
        gates=tuple(gates),
        accepted=classification is CertificationClassification.ACCEPTED,
        missing_gate_count=len(missing),
        failed_gate_count=len(failed),
    )
