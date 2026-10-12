"""QORE Alpha2 UTC-001 gate evaluator: evidence-only, NEVER runtime authorization."""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Mapping


@dataclass(frozen=True)
class PeriodEvidence:
    """Every required year and OOS fold is an independent certification exam."""

    trades: int
    pf: float | None
    expectancy_r: float | None
    sharpe: float | None
    sortino: float | None
    payoff: float | None
    observed_dd_r: float | None
    mc_positive_probability: float | None
    mc_p95_dd_r: float | None
    net_pf: float | None
    net_expectancy_r: float | None
    sample_sufficient: bool
    loss_cluster_survived: bool
    returns_frequency_verified: bool
    monte_carlo_provenance_verified: bool
    transaction_costs_verified: bool
    anti_lookahead_verified: bool
    source_provenance_verified: bool


@dataclass(frozen=True)
class CertificationResult:
    status: str
    failed_gates: tuple[str, ...]


def _valid(value: float | None) -> bool:
    return value is not None and math.isfinite(value)


def certify(
    *,
    required_period_ids: tuple[str, ...],
    period_evidence: Mapping[str, PeriodEvidence],
    fresh_holdout_passed: bool,
    fresh_holdout_is_independent: bool,
    news_asof_verified: bool,
    risk_review_approved: bool,
    cibo_review_approved: bool,
    independent_validation_approved: bool,
    winner_preservation_required: bool,
    winner_count_preservation: float | None,
    winner_r_preservation: float | None,
    mae_mfe_complete: bool,
    loser_anatomy_complete: bool,
) -> CertificationResult:
    """Fail closed: no metric available or missing year/fold can be compensated."""
    failures: list[str] = []
    if not required_period_ids or len(set(required_period_ids)) != len(required_period_ids):
        failures.append("PERIOD_MANIFEST_INVALID")
    for name in required_period_ids:
        if name not in period_evidence:
            failures.append(f"{name}:MISSING_REQUIRED_PERIOD")
            continue
        p = period_evidence[name]
        numeric = {
            "PF": (p.pf, 1.50, "ge"),
            "EXPECTANCY_R": (p.expectancy_r, 0.15, "ge"),
            "SHARPE": (p.sharpe, 1.50, "ge"),
            "SORTINO": (p.sortino, 2.00, "ge"),
            "PAYOFF": (p.payoff, 1.50, "ge"),
            "OBSERVED_DD_R": (p.observed_dd_r, 6.00, "le"),
            "MC_POSITIVE": (p.mc_positive_probability, 0.90, "ge"),
            "MC_P95_DD_R": (p.mc_p95_dd_r, 15.0, "le"),
            "POST_COST_PF": (p.net_pf, 1.00, "gt"),
            "POST_COST_EXPECTANCY": (p.net_expectancy_r, 0.00, "gt"),
        }
        for gate, (v, threshold, mode) in numeric.items():
            if not _valid(v):
                failures.append(f"{name}:{gate}_MISSING_OR_NONFINITE")
            elif not {"ge": v >= threshold, "le": v <= threshold,
                      "gt": v > threshold}[mode]:
                failures.append(f"{name}:{gate}_FAIL")
        proofs = {
            "TRADES_POSITIVE": p.trades > 0,
            "SAMPLE_SUFFICIENT": p.sample_sufficient,
            "LOSS_CLUSTER_SURVIVAL": p.loss_cluster_survived,
            "RETURN_FREQUENCY_VERIFIED": p.returns_frequency_verified,
            "MC_SOURCE_VERIFIED": p.monte_carlo_provenance_verified,
            "TRANSACTION_COSTS_VERIFIED": p.transaction_costs_verified,
            "NO_LOOKAHEAD": p.anti_lookahead_verified,
            "SOURCE_PROVENANCE": p.source_provenance_verified,
        }
        for gate, passed in proofs.items():
            if not passed:
                failures.append(f"{name}:{gate}_FAIL")
    if set(period_evidence) != set(required_period_ids):
        failures.append("PERIOD_MANIFEST_MISMATCH")
    global_proofs = {
        "FRESH_HOLDOUT_PASSED": fresh_holdout_passed,
        "FRESH_HOLDOUT_INDEPENDENT": fresh_holdout_is_independent,
        "NEWS_ASOF": news_asof_verified,
        "RISK_REVIEW": risk_review_approved,
        "CIBO_REVIEW": cibo_review_approved,
        "INDEPENDENT_REVIEW": independent_validation_approved,
        "MAE_MFE": mae_mfe_complete,
        "LOSER_ANATOMY": loser_anatomy_complete,
    }
    for gate, passed in global_proofs.items():
        if not passed:
            failures.append(gate + "_FAIL")
    if winner_preservation_required:
        if (not _valid(winner_count_preservation) or
                winner_count_preservation < 0.80):
            failures.append("WINNER_COUNT_PRESERVATION_FAIL")
        if not _valid(winner_r_preservation) or winner_r_preservation < 0.90:
            failures.append("WINNER_R_PRESERVATION_FAIL")
    return CertificationResult(
        status="ACCEPTED" if not failures else "BLOCKED_OR_FAILED",
        failed_gates=tuple(failures),
    )
