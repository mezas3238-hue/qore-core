"""UTC-001 universal trader certification gate.

QORE-UNIVERSAL-TRADER-CERTIFICATION-STANDARD-001 (UTC-001)

Certification is conjunctive. No global/combined metric can rescue a failed
required year or required OOS fold. Development has zero certification
authority. Every required temporal period must independently pass every hard
economic/survival gate. Missing evidence fails closed to INTERVENTION.

This module evaluates supplied evidence only. It never computes trades,
changes strategy logic, opens holdouts, or authorizes live/real capital.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum

IDENTITY = "QORE_UNIVERSAL_TRADER_CERTIFICATION_STANDARD_001"
VERSION = "UTC-001"

PF_MIN = Decimal("1.50")
EXPECTANCY_MIN = Decimal("0.15")
SHARPE_MIN = Decimal("1.50")
SORTINO_MIN = Decimal("2.00")
PAYOFF_MIN = Decimal("1.50")
OBSERVED_DD_MAX_R = Decimal("6")
MC_POSITIVE_MIN = Decimal("0.90")
MC_P95_DD_MAX_R = Decimal("15")
POST_COST_PF_MIN_EXCLUSIVE = Decimal("1.00")
POST_COST_EXPECTANCY_MIN_EXCLUSIVE = Decimal("0")
WINNER_COUNT_PRESERVATION_MIN = Decimal("0.80")
WINNER_R_PRESERVATION_MIN = Decimal("0.90")


class CertificationClassification(StrEnum):
    ACCEPTED = "ACCEPTED"
    INTERVENTION = "INTERVENTION — CONTINUE ENGINEERING"
    REJECTED = "REJECTED"


class GateStatus(StrEnum):
    PASS = "PASS"
    FAIL = "FAIL"
    MISSING = "MISSING"
    NOT_APPLICABLE = "NOT_APPLICABLE"


class PeriodKind(StrEnum):
    YEAR = "YEAR"
    OOS_FOLD = "OOS_FOLD"
    FRESH_HOLDOUT_YEAR = "FRESH_HOLDOUT_YEAR"
    FRESH_HOLDOUT_FOLD = "FRESH_HOLDOUT_FOLD"


@dataclass(frozen=True, slots=True)
class TemporalPeriodEvidence:
    period_id: str
    kind: PeriodKind
    window_start: str
    window_end_exclusive: str
    certification_required: bool = True
    trades: int | None = None
    wins: int | None = None
    losses: int | None = None
    breakeven: int | None = None
    win_rate: Decimal | None = None
    profit_factor: Decimal | None = None
    expectancy_r_per_trade: Decimal | None = None
    sharpe_annualized: Decimal | None = None
    sortino_annualized: Decimal | None = None
    observed_max_drawdown_r: Decimal | None = None
    average_winner_r: Decimal | None = None
    average_loser_r_abs: Decimal | None = None
    payoff_ratio: Decimal | None = None
    longest_losing_streak: int | None = None
    monte_carlo_positive_probability: Decimal | None = None
    monte_carlo_p95_drawdown_r: Decimal | None = None
    post_cost_profit_factor: Decimal | None = None
    post_cost_expectancy_r_per_trade: Decimal | None = None
    loss_cluster_gate_passed: bool | None = None
    sample_sufficiency_passed: bool | None = None
    cost_evidence_bound: bool = False
    cost_certification_blocked: bool = False
    development_only: bool = False
    consumed_for_engineering: bool = False
    fresh_holdout: bool = False

    def __post_init__(self) -> None:
        if not self.period_id:
            raise ValueError("period_id must be non-empty")
        if not self.window_start or not self.window_end_exclusive:
            raise ValueError("period window must be explicit")
        if self.trades is not None and self.trades < 0:
            raise ValueError("trades cannot be negative")
        for field_name in ("wins", "losses", "breakeven", "longest_losing_streak"):
            value = getattr(self, field_name)
            if value is not None and value < 0:
                raise ValueError(f"{field_name} cannot be negative")
        for field_name in (
            "win_rate",
            "profit_factor",
            "expectancy_r_per_trade",
            "sharpe_annualized",
            "sortino_annualized",
            "observed_max_drawdown_r",
            "average_winner_r",
            "average_loser_r_abs",
            "payoff_ratio",
            "monte_carlo_positive_probability",
            "monte_carlo_p95_drawdown_r",
            "post_cost_profit_factor",
            "post_cost_expectancy_r_per_trade",
        ):
            value = getattr(self, field_name)
            if value is not None and (
                not isinstance(value, Decimal) or not value.is_finite()
            ):
                raise ValueError(f"{field_name} must be finite Decimal or None")
        for field_name in ("win_rate", "monte_carlo_positive_probability"):
            value = getattr(self, field_name)
            if value is not None and not Decimal("0") <= value <= Decimal("1"):
                raise ValueError(f"{field_name} must be in [0,1]")
        for field_name in (
            "observed_max_drawdown_r",
            "average_winner_r",
            "average_loser_r_abs",
            "payoff_ratio",
            "monte_carlo_p95_drawdown_r",
        ):
            value = getattr(self, field_name)
            if value is not None and value < 0:
                raise ValueError(f"{field_name} cannot be negative")
        if self.development_only and self.certification_required:
            raise ValueError(
                "development-only evidence cannot have certification authority"
            )
        if self.fresh_holdout and self.development_only:
            raise ValueError("fresh holdout cannot be development-only")
        if self.cost_certification_blocked and self.cost_evidence_bound:
            raise ValueError(
                "cost certification cannot be both bound and blocked"
            )


@dataclass(frozen=True, slots=True)
class CandidateEvidence:
    periods: tuple[TemporalPeriodEvidence, ...]
    fresh_holdout_integrity_passed: bool | None = None
    fresh_holdout_opened_once: bool | None = None
    fresh_holdout_passed: bool | None = None
    anti_leakage_audit_passed: bool | None = None
    prohibited_outcome_aware_logic_detected: bool = False
    holdout_mining_detected: bool = False
    winner_preservation_required: bool = False
    winner_count_preservation: Decimal | None = None
    winner_r_preservation: Decimal | None = None
    temporal_stability_review_passed: bool | None = None
    mae_mfe_audit_complete: bool | None = None
    loser_anatomy_audit_complete: bool | None = None
    density_sufficient_after_quality: bool | None = None
    risk_review_passed: bool | None = None
    cibo_review_passed: bool | None = None
    independent_validation_passed: bool | None = None
    fatal_falsification: bool = False
    fatal_falsification_reason: str | None = None
    # Descriptive only. They deliberately have zero certification authority.
    descriptive_global_profit_factor: Decimal | None = None
    descriptive_global_expectancy_r_per_trade: Decimal | None = None
    descriptive_global_sharpe: Decimal | None = None
    descriptive_global_sortino: Decimal | None = None
    descriptive_global_max_drawdown_r: Decimal | None = None
    descriptive_global_payoff: Decimal | None = None
    descriptive_global_win_rate: Decimal | None = None

    def __post_init__(self) -> None:
        ids = tuple(row.period_id for row in self.periods)
        if len(ids) != len(set(ids)):
            raise ValueError("period_id values must be unique")
        for field_name in (
            "winner_count_preservation",
            "winner_r_preservation",
            "descriptive_global_profit_factor",
            "descriptive_global_expectancy_r_per_trade",
            "descriptive_global_sharpe",
            "descriptive_global_sortino",
            "descriptive_global_max_drawdown_r",
            "descriptive_global_payoff",
            "descriptive_global_win_rate",
        ):
            value = getattr(self, field_name)
            if value is not None and (
                not isinstance(value, Decimal) or not value.is_finite()
            ):
                raise ValueError(f"{field_name} must be finite Decimal or None")
        if (
            self.winner_count_preservation is not None
            and not Decimal("0") <= self.winner_count_preservation <= Decimal("1")
        ):
            raise ValueError("winner_count_preservation must be in [0,1]")
        if (
            self.winner_r_preservation is not None
            and self.winner_r_preservation < 0
        ):
            raise ValueError("winner_r_preservation cannot be negative")
        if self.fatal_falsification and not self.fatal_falsification_reason:
            raise ValueError("fatal falsification requires explicit reason")


@dataclass(frozen=True, slots=True)
class GateResult:
    gate: str
    status: GateStatus
    detail: str
    period_id: str | None = None


@dataclass(frozen=True, slots=True)
class CertificationDecision:
    identity: str
    version: str
    classification: CertificationClassification
    accepted: bool
    required_period_count: int
    passed_period_count: int
    failed_period_count: int
    missing_period_count: int
    failed_gate_count: int
    missing_gate_count: int
    gates: tuple[GateResult, ...]
    global_compensation_allowed: bool = False
    temporal_compensation_allowed: bool = False
    gate_compensation_allowed: bool = False


def _numeric_gate(
    *,
    period_id: str,
    gate: str,
    value: Decimal | None,
    passed: bool | None,
    detail: str,
) -> GateResult:
    if value is None:
        return GateResult(
            gate=gate,
            status=GateStatus.MISSING,
            detail="mandatory evidence missing",
            period_id=period_id,
        )
    return GateResult(
        gate=gate,
        status=GateStatus.PASS if passed is True else GateStatus.FAIL,
        detail=detail,
        period_id=period_id,
    )


def _boolean_gate(
    *,
    gate: str,
    value: bool | None,
    period_id: str | None = None,
) -> GateResult:
    if value is None:
        return GateResult(
            gate=gate,
            status=GateStatus.MISSING,
            detail="mandatory evidence missing",
            period_id=period_id,
        )
    return GateResult(
        gate=gate,
        status=GateStatus.PASS if value else GateStatus.FAIL,
        detail=str(value).lower(),
        period_id=period_id,
    )


def _period_gates(row: TemporalPeriodEvidence) -> tuple[GateResult, ...]:
    if not row.certification_required:
        return (
            GateResult(
                gate="certification_authority",
                status=GateStatus.NOT_APPLICABLE,
                detail=(
                    "development/reference/diagnostic evidence has zero "
                    "certification authority"
                ),
                period_id=row.period_id,
            ),
        )

    prefix = row.period_id
    gates: list[GateResult] = [
        _numeric_gate(
            period_id=prefix,
            gate="profit_factor",
            value=row.profit_factor,
            passed=(
                None
                if row.profit_factor is None
                else row.profit_factor >= PF_MIN
            ),
            detail=(
                "unknown"
                if row.profit_factor is None
                else f"{row.profit_factor} >= {PF_MIN}"
            ),
        ),
        _numeric_gate(
            period_id=prefix,
            gate="expectancy_r_per_trade",
            value=row.expectancy_r_per_trade,
            passed=(
                None
                if row.expectancy_r_per_trade is None
                else row.expectancy_r_per_trade >= EXPECTANCY_MIN
            ),
            detail=(
                "unknown"
                if row.expectancy_r_per_trade is None
                else f"{row.expectancy_r_per_trade} >= {EXPECTANCY_MIN}R"
            ),
        ),
        _numeric_gate(
            period_id=prefix,
            gate="sharpe_annualized",
            value=row.sharpe_annualized,
            passed=(
                None
                if row.sharpe_annualized is None
                else row.sharpe_annualized >= SHARPE_MIN
            ),
            detail=(
                "unknown"
                if row.sharpe_annualized is None
                else f"{row.sharpe_annualized} >= {SHARPE_MIN}"
            ),
        ),
        _numeric_gate(
            period_id=prefix,
            gate="sortino_annualized",
            value=row.sortino_annualized,
            passed=(
                None
                if row.sortino_annualized is None
                else row.sortino_annualized >= SORTINO_MIN
            ),
            detail=(
                "unknown"
                if row.sortino_annualized is None
                else f"{row.sortino_annualized} >= {SORTINO_MIN}"
            ),
        ),
        _numeric_gate(
            period_id=prefix,
            gate="payoff_ratio",
            value=row.payoff_ratio,
            passed=(
                None
                if row.payoff_ratio is None
                else row.payoff_ratio >= PAYOFF_MIN
            ),
            detail=(
                "unknown"
                if row.payoff_ratio is None
                else f"{row.payoff_ratio} >= {PAYOFF_MIN}"
            ),
        ),
        _numeric_gate(
            period_id=prefix,
            gate="observed_max_drawdown_r",
            value=row.observed_max_drawdown_r,
            passed=(
                None
                if row.observed_max_drawdown_r is None
                else row.observed_max_drawdown_r <= OBSERVED_DD_MAX_R
            ),
            detail=(
                "unknown"
                if row.observed_max_drawdown_r is None
                else f"{row.observed_max_drawdown_r} <= {OBSERVED_DD_MAX_R}R"
            ),
        ),
        _numeric_gate(
            period_id=prefix,
            gate="monte_carlo_positive_probability",
            value=row.monte_carlo_positive_probability,
            passed=(
                None
                if row.monte_carlo_positive_probability is None
                else row.monte_carlo_positive_probability >= MC_POSITIVE_MIN
            ),
            detail=(
                "unknown"
                if row.monte_carlo_positive_probability is None
                else (
                    f"{row.monte_carlo_positive_probability} >= "
                    f"{MC_POSITIVE_MIN}"
                )
            ),
        ),
        _numeric_gate(
            period_id=prefix,
            gate="monte_carlo_p95_drawdown_r",
            value=row.monte_carlo_p95_drawdown_r,
            passed=(
                None
                if row.monte_carlo_p95_drawdown_r is None
                else row.monte_carlo_p95_drawdown_r <= MC_P95_DD_MAX_R
            ),
            detail=(
                "unknown"
                if row.monte_carlo_p95_drawdown_r is None
                else (
                    f"{row.monte_carlo_p95_drawdown_r} <= "
                    f"{MC_P95_DD_MAX_R}R"
                )
            ),
        ),
    ]

    if row.cost_certification_blocked or not row.cost_evidence_bound:
        gates.extend(
            (
                GateResult(
                    gate="post_cost_profit_factor",
                    status=GateStatus.MISSING,
                    detail="COST CERTIFICATION = BLOCKED; bound cost evidence absent",
                    period_id=prefix,
                ),
                GateResult(
                    gate="post_cost_expectancy_r_per_trade",
                    status=GateStatus.MISSING,
                    detail="COST CERTIFICATION = BLOCKED; bound cost evidence absent",
                    period_id=prefix,
                ),
            )
        )
    else:
        gates.extend(
            (
                _numeric_gate(
                    period_id=prefix,
                    gate="post_cost_profit_factor",
                    value=row.post_cost_profit_factor,
                    passed=(
                        None
                        if row.post_cost_profit_factor is None
                        else row.post_cost_profit_factor
                        > POST_COST_PF_MIN_EXCLUSIVE
                    ),
                    detail=(
                        "unknown"
                        if row.post_cost_profit_factor is None
                        else (
                            f"{row.post_cost_profit_factor} > "
                            f"{POST_COST_PF_MIN_EXCLUSIVE}"
                        )
                    ),
                ),
                _numeric_gate(
                    period_id=prefix,
                    gate="post_cost_expectancy_r_per_trade",
                    value=row.post_cost_expectancy_r_per_trade,
                    passed=(
                        None
                        if row.post_cost_expectancy_r_per_trade is None
                        else row.post_cost_expectancy_r_per_trade
                        > POST_COST_EXPECTANCY_MIN_EXCLUSIVE
                    ),
                    detail=(
                        "unknown"
                        if row.post_cost_expectancy_r_per_trade is None
                        else (
                            f"{row.post_cost_expectancy_r_per_trade} > "
                            f"{POST_COST_EXPECTANCY_MIN_EXCLUSIVE}R"
                        )
                    ),
                ),
            )
        )

    gates.extend(
        (
            _boolean_gate(
                gate="loss_cluster_gate",
                value=row.loss_cluster_gate_passed,
                period_id=prefix,
            ),
            _boolean_gate(
                gate="sample_sufficiency",
                value=row.sample_sufficiency_passed,
                period_id=prefix,
            ),
        )
    )
    return tuple(gates)


def _candidate_gates(evidence: CandidateEvidence) -> tuple[GateResult, ...]:
    gates: list[GateResult] = [
        _boolean_gate(
            gate="fresh_holdout_integrity",
            value=evidence.fresh_holdout_integrity_passed,
        ),
        _boolean_gate(
            gate="fresh_holdout_opened_once",
            value=evidence.fresh_holdout_opened_once,
        ),
        _boolean_gate(
            gate="fresh_holdout_passed",
            value=evidence.fresh_holdout_passed,
        ),
        _boolean_gate(
            gate="anti_leakage_audit",
            value=evidence.anti_leakage_audit_passed,
        ),
        _boolean_gate(
            gate="temporal_stability_review",
            value=evidence.temporal_stability_review_passed,
        ),
        _boolean_gate(
            gate="mae_mfe_audit_complete",
            value=evidence.mae_mfe_audit_complete,
        ),
        _boolean_gate(
            gate="loser_anatomy_audit_complete",
            value=evidence.loser_anatomy_audit_complete,
        ),
        _boolean_gate(
            gate="density_sufficient_after_quality",
            value=evidence.density_sufficient_after_quality,
        ),
        _boolean_gate(
            gate="risk_review",
            value=evidence.risk_review_passed,
        ),
        _boolean_gate(
            gate="cibo_review",
            value=evidence.cibo_review_passed,
        ),
        _boolean_gate(
            gate="independent_validation",
            value=evidence.independent_validation_passed,
        ),
    ]

    if evidence.winner_preservation_required:
        gates.extend(
            (
                _numeric_gate(
                    period_id="CANDIDATE",
                    gate="winner_count_preservation",
                    value=evidence.winner_count_preservation,
                    passed=(
                        None
                        if evidence.winner_count_preservation is None
                        else evidence.winner_count_preservation
                        >= WINNER_COUNT_PRESERVATION_MIN
                    ),
                    detail=(
                        "unknown"
                        if evidence.winner_count_preservation is None
                        else (
                            f"{evidence.winner_count_preservation} >= "
                            f"{WINNER_COUNT_PRESERVATION_MIN}"
                        )
                    ),
                ),
                _numeric_gate(
                    period_id="CANDIDATE",
                    gate="winner_r_preservation",
                    value=evidence.winner_r_preservation,
                    passed=(
                        None
                        if evidence.winner_r_preservation is None
                        else evidence.winner_r_preservation
                        >= WINNER_R_PRESERVATION_MIN
                    ),
                    detail=(
                        "unknown"
                        if evidence.winner_r_preservation is None
                        else (
                            f"{evidence.winner_r_preservation} >= "
                            f"{WINNER_R_PRESERVATION_MIN}"
                        )
                    ),
                ),
            )
        )
    else:
        gates.extend(
            (
                GateResult(
                    gate="winner_count_preservation",
                    status=GateStatus.NOT_APPLICABLE,
                    detail="candidate does not remove/alter winner outcomes",
                ),
                GateResult(
                    gate="winner_r_preservation",
                    status=GateStatus.NOT_APPLICABLE,
                    detail="candidate does not remove/alter winner outcomes",
                ),
            )
        )
    return tuple(gates)


def evaluate_certification(
    evidence: CandidateEvidence,
) -> CertificationDecision:
    gates: list[GateResult] = []
    required_periods = tuple(
        row for row in evidence.periods if row.certification_required
    )
    if not required_periods:
        gates.append(
            GateResult(
                gate="required_temporal_periods",
                status=GateStatus.MISSING,
                detail="no certification-authoritative year/fold supplied",
            )
        )

    period_status: dict[str, GateStatus] = {}
    for row in evidence.periods:
        row_gates = _period_gates(row)
        gates.extend(row_gates)
        authoritative = tuple(
            gate
            for gate in row_gates
            if gate.status is not GateStatus.NOT_APPLICABLE
        )
        if not authoritative:
            period_status[row.period_id] = GateStatus.NOT_APPLICABLE
        elif any(gate.status is GateStatus.FAIL for gate in authoritative):
            period_status[row.period_id] = GateStatus.FAIL
        elif any(gate.status is GateStatus.MISSING for gate in authoritative):
            period_status[row.period_id] = GateStatus.MISSING
        else:
            period_status[row.period_id] = GateStatus.PASS

    gates.extend(_candidate_gates(evidence))

    if evidence.prohibited_outcome_aware_logic_detected:
        gates.append(
            GateResult(
                gate="prohibited_outcome_aware_logic",
                status=GateStatus.FAIL,
                detail="outcome-aware production/runtime logic detected",
            )
        )
    else:
        gates.append(
            GateResult(
                gate="prohibited_outcome_aware_logic",
                status=GateStatus.PASS,
                detail="not detected",
            )
        )

    if evidence.holdout_mining_detected:
        gates.append(
            GateResult(
                gate="holdout_mining",
                status=GateStatus.FAIL,
                detail="repeated holdout mining detected",
            )
        )
    else:
        gates.append(
            GateResult(
                gate="holdout_mining",
                status=GateStatus.PASS,
                detail="not detected",
            )
        )

    failed_gate_count = sum(g.status is GateStatus.FAIL for g in gates)
    missing_gate_count = sum(g.status is GateStatus.MISSING for g in gates)
    failed_period_count = sum(
        period_status.get(row.period_id) is GateStatus.FAIL
        for row in required_periods
    )
    missing_period_count = sum(
        period_status.get(row.period_id) is GateStatus.MISSING
        for row in required_periods
    )
    passed_period_count = sum(
        period_status.get(row.period_id) is GateStatus.PASS
        for row in required_periods
    )

    fatal = (
        evidence.fatal_falsification
        or evidence.prohibited_outcome_aware_logic_detected
        or evidence.holdout_mining_detected
    )
    accepted = (
        not fatal
        and len(required_periods) > 0
        and failed_gate_count == 0
        and missing_gate_count == 0
        and passed_period_count == len(required_periods)
    )

    if accepted:
        classification = CertificationClassification.ACCEPTED
    elif fatal:
        classification = CertificationClassification.REJECTED
    else:
        classification = CertificationClassification.INTERVENTION

    return CertificationDecision(
        identity=IDENTITY,
        version=VERSION,
        classification=classification,
        accepted=accepted,
        required_period_count=len(required_periods),
        passed_period_count=passed_period_count,
        failed_period_count=failed_period_count,
        missing_period_count=missing_period_count,
        failed_gate_count=failed_gate_count,
        missing_gate_count=missing_gate_count,
        gates=tuple(gates),
    )
