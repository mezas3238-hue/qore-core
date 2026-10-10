"""Causal candidate-competition falsification for QORE Capitalizer.

This consumed-development lab follows the portfolio exposure characterization and tests a
small set of categorical, market/session/ordinal hypotheses. These hypotheses are deliberately
kept separate so a weak cell can be falsified without turning broad correlation into a veto.

No numeric optimization threshold, outcome-aware ranking, profit objective, cost model, QORE
Risk authority, candidate freeze, holdout claim, or promotion is introduced.
"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from dataclasses import asdict, dataclass
from decimal import Decimal
from pathlib import Path

from qore.infrastructure.trader_lab.capitalizer_portfolio_exposure_forensics import (
    CapitalizerExposureAssessment,
    CapitalizerExposureCandidate,
    _assessment,
    _load_candidates,
    _ordered,
)
from qore.infrastructure.trader_lab.capitalizer_portfolio_session_flow_viability import (
    PortfolioFlowMetrics,
    _metrics,
    _session_key,
)
from qore.infrastructure.trader_lab.capitalizer_session_clock import capitalizer_session_at
from qore.infrastructure.trader_lab.capitalizer_session_flow_viability import NEW_YORK

IDENTITY = "QORE_CAPITALIZER_PORTFOLIO_COMPETITION_FORENSICS_V1"

POLICIES = (
    "MAX3_BASELINE",
    "BLOCK_XAUUSD_NY_ORD2_SAME_DIRECTION_SHARED_FACTOR",
    "BLOCK_XAUUSD_NY_ORD2_ANY_SHARED_FACTOR",
    "BLOCK_GBPJPY_ASIA_ORD3",
    "BLOCK_ASIA_JPY_ORD3",
    "COMBINED_XAUUSD_ANY_SHARED_AND_GBPJPY_ORD3",
    "COMBINED_XAUUSD_ANY_SHARED_AND_ASIA_JPY_ORD3",
)


@dataclass(frozen=True, slots=True)
class CapitalizerCompetitionPolicyResult:
    policy: str
    tie_policy: str
    metrics: PortfolioFlowMetrics
    selected_trades: int
    rejected_by_competition: int
    rejected_metrics: PortfolioFlowMetrics | None
    sessions: int
    sessions_reaching_three: int
    positive_years: int
    years_observed: int


@dataclass(frozen=True, slots=True)
class CapitalizerCompetitionRejectedCell:
    policy: str
    tie_policy: str
    reason: str
    symbol: str
    session: str
    ordinal: int
    trades: int
    metrics: PortfolioFlowMetrics


@dataclass(frozen=True, slots=True)
class CapitalizerPortfolioCompetitionForensicsReport:
    identity: str
    market_count: int
    symbols: tuple[str, ...]
    baseline_opportunities: int
    policies: tuple[CapitalizerCompetitionPolicyResult, ...]
    rejected_cells: tuple[CapitalizerCompetitionRejectedCell, ...]
    max_executions_per_session: int = 3
    categorical_hypotheses_only: bool = True
    numeric_threshold_optimization_used: bool = False
    outcome_aware_ranking_used: bool = False
    positive_pnl_is_not_stop_condition: bool = True
    governed_profit_objective_not_modeled: bool = True
    qore_risk_authority_granted: bool = False
    costs_applied: bool = False
    development_only: bool = True
    candidate_frozen: bool = False
    fresh_holdout_claimed: bool = False
    rule_selected: bool = False
    promotion_allowed: bool = False


def _block_reason(
    *,
    policy: str,
    candidate: CapitalizerExposureCandidate,
    ordinal: int,
    assessment: CapitalizerExposureAssessment,
) -> str | None:
    session = capitalizer_session_at(candidate.entry_at)
    if session is None:
        raise ValueError("competition candidate lost Capitalizer session identity")
    session_name = session.value

    xau_same = (
        candidate.symbol == "XAUUSD"
        and session_name == "NEW_YORK"
        and ordinal == 2
        and assessment.same_direction_factors > 0
    )
    xau_any = (
        candidate.symbol == "XAUUSD"
        and session_name == "NEW_YORK"
        and ordinal == 2
        and assessment.shared_factors > 0
    )
    gbpjpy_third = (
        candidate.symbol == "GBPJPY"
        and session_name == "ASIA"
        and ordinal == 3
    )
    asia_jpy_third = (
        candidate.symbol in {"AUDJPY", "GBPJPY"}
        and session_name == "ASIA"
        and ordinal == 3
    )

    if policy == "MAX3_BASELINE":
        return None
    if policy == "BLOCK_XAUUSD_NY_ORD2_SAME_DIRECTION_SHARED_FACTOR":
        return "XAUUSD_NY_ORD2_SAME_DIRECTION_SHARED_FACTOR" if xau_same else None
    if policy == "BLOCK_XAUUSD_NY_ORD2_ANY_SHARED_FACTOR":
        return "XAUUSD_NY_ORD2_ANY_SHARED_FACTOR" if xau_any else None
    if policy == "BLOCK_GBPJPY_ASIA_ORD3":
        return "GBPJPY_ASIA_ORD3" if gbpjpy_third else None
    if policy == "BLOCK_ASIA_JPY_ORD3":
        return "ASIA_JPY_ORD3" if asia_jpy_third else None
    if policy == "COMBINED_XAUUSD_ANY_SHARED_AND_GBPJPY_ORD3":
        if xau_any:
            return "XAUUSD_NY_ORD2_ANY_SHARED_FACTOR"
        return "GBPJPY_ASIA_ORD3" if gbpjpy_third else None
    if policy == "COMBINED_XAUUSD_ANY_SHARED_AND_ASIA_JPY_ORD3":
        if xau_any:
            return "XAUUSD_NY_ORD2_ANY_SHARED_FACTOR"
        return "ASIA_JPY_ORD3" if asia_jpy_third else None
    raise ValueError("unsupported competition policy")


def _select(
    candidates: tuple[CapitalizerExposureCandidate, ...],
    *,
    policy: str,
    tie_policy: str,
) -> tuple[
    tuple[CapitalizerExposureCandidate, ...],
    tuple[tuple[CapitalizerExposureCandidate, str, int], ...],
]:
    if policy not in POLICIES:
        raise ValueError("unsupported competition policy")

    per_session: dict[str, list[CapitalizerExposureCandidate]] = defaultdict(list)
    selected: list[CapitalizerExposureCandidate] = []
    rejected: list[tuple[CapitalizerExposureCandidate, str, int]] = []

    for candidate in _ordered(candidates, tie_policy=tie_policy):
        key = _session_key(candidate.as_trade())
        accepted = per_session[key]
        if len(accepted) >= 3:
            continue

        ordinal = len(accepted) + 1
        active = tuple(
            item for item in accepted if item.exit_at > candidate.entry_at
        )
        assessment = _assessment(candidate, active)
        reason = _block_reason(
            policy=policy,
            candidate=candidate,
            ordinal=ordinal,
            assessment=assessment,
        )
        if reason is not None:
            rejected.append((candidate, reason, ordinal))
            continue

        accepted.append(candidate)
        selected.append(candidate)

    return tuple(selected), tuple(rejected)


def _policy_result(
    candidates: tuple[CapitalizerExposureCandidate, ...],
    *,
    policy: str,
    tie_policy: str,
) -> CapitalizerCompetitionPolicyResult:
    selected, rejected = _select(
        candidates,
        policy=policy,
        tie_policy=tie_policy,
    )
    trades = tuple(item.as_trade() for item in selected)
    rejected_trades = tuple(item.as_trade() for item, _, _ in rejected)

    session_counts: dict[str, int] = defaultdict(int)
    by_year: dict[int, Decimal] = defaultdict(lambda: Decimal("0"))
    for candidate in selected:
        session_counts[_session_key(candidate.as_trade())] += 1
        by_year[candidate.entry_at.astimezone(NEW_YORK).year] += candidate.realized_r

    return CapitalizerCompetitionPolicyResult(
        policy=policy,
        tie_policy=tie_policy,
        metrics=_metrics(trades),
        selected_trades=len(selected),
        rejected_by_competition=len(rejected),
        rejected_metrics=_metrics(rejected_trades) if rejected_trades else None,
        sessions=len(session_counts),
        sessions_reaching_three=sum(
            count >= 3 for count in session_counts.values()
        ),
        positive_years=sum(total > 0 for total in by_year.values()),
        years_observed=len(by_year),
    )


def _rejected_cells(
    candidates: tuple[CapitalizerExposureCandidate, ...],
    *,
    policy: str,
    tie_policy: str,
) -> tuple[CapitalizerCompetitionRejectedCell, ...]:
    _, rejected = _select(candidates, policy=policy, tie_policy=tie_policy)
    grouped: dict[
        tuple[str, str, str, int],
        list[CapitalizerExposureCandidate],
    ] = defaultdict(list)

    for candidate, reason, ordinal in rejected:
        session = capitalizer_session_at(candidate.entry_at)
        if session is None:
            raise ValueError("rejected competition candidate lost session")
        grouped[(reason, candidate.symbol, session.value, ordinal)].append(candidate)

    return tuple(
        CapitalizerCompetitionRejectedCell(
            policy=policy,
            tie_policy=tie_policy,
            reason=reason,
            symbol=symbol,
            session=session,
            ordinal=ordinal,
            trades=len(rows),
            metrics=_metrics(tuple(item.as_trade() for item in rows)),
        )
        for (reason, symbol, session, ordinal), rows in sorted(grouped.items())
    )


def build_portfolio_competition_forensics_report(
    root: Path,
) -> CapitalizerPortfolioCompetitionForensicsReport:
    candidates = _load_candidates(root)
    policy_rows: list[CapitalizerCompetitionPolicyResult] = []
    cells: list[CapitalizerCompetitionRejectedCell] = []

    for tie_policy in ("SYMBOL_ASC", "SYMBOL_DESC"):
        for policy in POLICIES:
            policy_rows.append(
                _policy_result(
                    candidates,
                    policy=policy,
                    tie_policy=tie_policy,
                )
            )
            cells.extend(
                _rejected_cells(
                    candidates,
                    policy=policy,
                    tie_policy=tie_policy,
                )
            )

    symbols = tuple(sorted({item.symbol for item in candidates}))
    return CapitalizerPortfolioCompetitionForensicsReport(
        identity=IDENTITY,
        market_count=len(symbols),
        symbols=symbols,
        baseline_opportunities=len(candidates),
        policies=tuple(policy_rows),
        rejected_cells=tuple(cells),
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Capitalizer portfolio candidate-competition falsification"
    )
    parser.add_argument("input_root", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    report = build_portfolio_competition_forensics_report(args.input_root)
    args.output.mkdir(parents=True, exist_ok=True)
    path = args.output / "capitalizer-portfolio-competition-forensics-v1.json"
    path.write_text(
        json.dumps(asdict(report), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(asdict(report), sort_keys=True))


if __name__ == "__main__":
    main()
