"""Triad-aware admission routing falsification for QORE Capitalizer.

Consumed-development evidence only. This lab tests whether a specific ASIA three-market
interaction explains residual MAX3 drawdown after pair/session compatibility routing.

The structural hypothesis is intentionally narrow:
- when the ASIA basket contains AUDJPY, GBPJPY, and USDJPY;
- AUDJPY and USDJPY point to the same trade side;
- GBPJPY points to the opposite trade side;
the third admission completes a conflicted JPY triad.

Both mirror orientations are one categorical state, not two fitted outcome rules. The veto is
evaluated only when the third candidate arrives, using prior accepted candidates in the same
session. It therefore has no future-candidate visibility.

The lab also composes this triad hypothesis with the existing London+New York and extended
weak-pair routing hypotheses. No numeric threshold optimization, outcome-aware runtime ranking,
profit objective, cost model, QORE Risk authority, candidate freeze, fresh holdout claim, or
promotion is introduced.
"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from dataclasses import asdict, dataclass
from decimal import Decimal
from pathlib import Path

from qore.infrastructure.trader_lab.capitalizer_exposure_graph import CapitalizerSide
from qore.infrastructure.trader_lab.capitalizer_portfolio_exposure_forensics import (
    CapitalizerExposureCandidate,
    _load_candidates,
    _ordered,
)
from qore.infrastructure.trader_lab.capitalizer_portfolio_session_flow_viability import (
    PortfolioFlowMetrics,
    _metrics,
    _session_key,
)
from qore.infrastructure.trader_lab.capitalizer_session_clock import capitalizer_session_at
from qore.infrastructure.trader_lab.capitalizer_session_compatibility_routing import (
    EXTENDED_WEAK_SIDE_PAIRS,
    LONDON_PLUS_NEW_YORK_WEAK,
    _weak_pair_reason,
)
from qore.infrastructure.trader_lab.capitalizer_session_flow_viability import NEW_YORK

IDENTITY = "QORE_CAPITALIZER_TRIAD_COMPATIBILITY_ROUTING_FORENSICS_V1"

POLICIES = (
    "MAX3_BASELINE",
    "BLOCK_ASIA_JPY_SPLIT_GBP_OPPOSES_V1",
    "BLOCK_LONDON_PLUS_NEW_YORK_WEAK_PAIRS_V1",
    "BLOCK_LONDON_NY_PLUS_ASIA_JPY_SPLIT_V1",
    "BLOCK_EXTENDED_WEAK_SIDE_PAIRS_V1",
    "BLOCK_EXTENDED_WEAK_PAIRS_PLUS_ASIA_JPY_SPLIT_V1",
)


@dataclass(frozen=True, slots=True)
class CapitalizerTriadRoutingPolicyResult:
    policy: str
    tie_policy: str
    metrics: PortfolioFlowMetrics
    selected_trades: int
    rejected_by_routing: int
    rejected_metrics: PortfolioFlowMetrics | None
    rejected_by_pair_state: int
    rejected_by_triad_state: int
    sessions: int
    sessions_reaching_three: int
    positive_years: int
    years_observed: int


@dataclass(frozen=True, slots=True)
class CapitalizerTriadRoutingRejectionCell:
    policy: str
    tie_policy: str
    reason: str
    session: str
    symbol: str
    side: str
    ordinal_if_accepted: int
    trades: int
    metrics: PortfolioFlowMetrics


@dataclass(frozen=True, slots=True)
class CapitalizerTriadCompatibilityRoutingReport:
    identity: str
    market_count: int
    symbols: tuple[str, ...]
    baseline_opportunities: int
    policy_results: tuple[CapitalizerTriadRoutingPolicyResult, ...]
    rejection_cells: tuple[CapitalizerTriadRoutingRejectionCell, ...]
    max_executions_per_session: int = 3
    asia_jpy_split_state_categorical: bool = True
    mirror_orientations_share_one_rule: bool = True
    third_admission_only: bool = True
    prior_session_acceptances_only: bool = True
    future_candidates_visible: bool = False
    numeric_threshold_optimization_used: bool = False
    outcome_aware_runtime_ranking_used: bool = False
    positive_pnl_is_not_stop_condition: bool = True
    governed_profit_objective_not_modeled: bool = True
    qore_risk_authority_granted: bool = False
    costs_applied: bool = False
    development_only: bool = True
    candidate_frozen: bool = False
    fresh_holdout_claimed: bool = False
    rule_selected: bool = False
    promotion_allowed: bool = False


def _asia_jpy_split_reason(
    candidate: CapitalizerExposureCandidate,
    prior: tuple[CapitalizerExposureCandidate, ...],
) -> str | None:
    if len(prior) != 2:
        return None

    session = capitalizer_session_at(candidate.entry_at)
    if session is None:
        raise ValueError("triad routing candidate lost Capitalizer session")
    if session.value != "ASIA":
        return None

    rows = prior + (candidate,)
    if len({row.symbol for row in rows}) != 3:
        return None
    if {row.symbol for row in rows} != {"AUDJPY", "GBPJPY", "USDJPY"}:
        return None

    sides = {row.symbol: row.side for row in rows}
    if (
        sides["AUDJPY"] is sides["USDJPY"]
        and sides["GBPJPY"] is not sides["AUDJPY"]
    ):
        return "ASIA_JPY_SPLIT_GBP_OPPOSES_AUDJPY_USDJPY"
    return None


def _rejection_reason(
    *,
    policy: str,
    candidate: CapitalizerExposureCandidate,
    prior: tuple[CapitalizerExposureCandidate, ...],
) -> str | None:
    if policy == "MAX3_BASELINE":
        return None
    if policy == "BLOCK_ASIA_JPY_SPLIT_GBP_OPPOSES_V1":
        return _asia_jpy_split_reason(candidate, prior)
    if policy == "BLOCK_LONDON_PLUS_NEW_YORK_WEAK_PAIRS_V1":
        return _weak_pair_reason(
            candidate,
            prior,
            table=LONDON_PLUS_NEW_YORK_WEAK,
        )
    if policy == "BLOCK_LONDON_NY_PLUS_ASIA_JPY_SPLIT_V1":
        pair_reason = _weak_pair_reason(
            candidate,
            prior,
            table=LONDON_PLUS_NEW_YORK_WEAK,
        )
        if pair_reason is not None:
            return pair_reason
        return _asia_jpy_split_reason(candidate, prior)
    if policy == "BLOCK_EXTENDED_WEAK_SIDE_PAIRS_V1":
        return _weak_pair_reason(
            candidate,
            prior,
            table=EXTENDED_WEAK_SIDE_PAIRS,
        )
    if policy == "BLOCK_EXTENDED_WEAK_PAIRS_PLUS_ASIA_JPY_SPLIT_V1":
        pair_reason = _weak_pair_reason(
            candidate,
            prior,
            table=EXTENDED_WEAK_SIDE_PAIRS,
        )
        if pair_reason is not None:
            return pair_reason
        return _asia_jpy_split_reason(candidate, prior)
    raise ValueError("unsupported triad routing policy")


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
        raise ValueError("unsupported triad routing policy")

    per_session: dict[str, list[CapitalizerExposureCandidate]] = defaultdict(list)
    selected: list[CapitalizerExposureCandidate] = []
    rejected: list[tuple[CapitalizerExposureCandidate, str, int]] = []

    for candidate in _ordered(candidates, tie_policy=tie_policy):
        key = _session_key(candidate.as_trade())
        accepted = per_session[key]
        if len(accepted) >= 3:
            continue

        ordinal = len(accepted) + 1
        reason = _rejection_reason(
            policy=policy,
            candidate=candidate,
            prior=tuple(accepted),
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
) -> CapitalizerTriadRoutingPolicyResult:
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

    pair_rejections = sum(reason.startswith("WEAK_PAIR:") for _, reason, _ in rejected)
    triad_rejections = sum(
        reason == "ASIA_JPY_SPLIT_GBP_OPPOSES_AUDJPY_USDJPY"
        for _, reason, _ in rejected
    )

    return CapitalizerTriadRoutingPolicyResult(
        policy=policy,
        tie_policy=tie_policy,
        metrics=_metrics(trades),
        selected_trades=len(selected),
        rejected_by_routing=len(rejected),
        rejected_metrics=_metrics(rejected_trades) if rejected_trades else None,
        rejected_by_pair_state=pair_rejections,
        rejected_by_triad_state=triad_rejections,
        sessions=len(session_counts),
        sessions_reaching_three=sum(count >= 3 for count in session_counts.values()),
        positive_years=sum(total > 0 for total in by_year.values()),
        years_observed=len(by_year),
    )


def _rejection_cells(
    candidates: tuple[CapitalizerExposureCandidate, ...],
    *,
    policy: str,
    tie_policy: str,
) -> tuple[CapitalizerTriadRoutingRejectionCell, ...]:
    _, rejected = _select(
        candidates,
        policy=policy,
        tie_policy=tie_policy,
    )
    grouped: dict[
        tuple[str, str, str, CapitalizerSide, int],
        list[CapitalizerExposureCandidate],
    ] = defaultdict(list)

    for candidate, reason, ordinal in rejected:
        session = capitalizer_session_at(candidate.entry_at)
        if session is None:
            raise ValueError("triad routing rejection lost session")
        grouped[
            (reason, session.value, candidate.symbol, candidate.side, ordinal)
        ].append(candidate)

    return tuple(
        CapitalizerTriadRoutingRejectionCell(
            policy=policy,
            tie_policy=tie_policy,
            reason=reason,
            session=session,
            symbol=symbol,
            side=side.value,
            ordinal_if_accepted=ordinal,
            trades=len(rows),
            metrics=_metrics(tuple(item.as_trade() for item in rows)),
        )
        for (reason, session, symbol, side, ordinal), rows in sorted(
            grouped.items(),
            key=lambda entry: tuple(str(value) for value in entry[0]),
        )
    )


def build_triad_compatibility_routing_report(
    root: Path,
) -> CapitalizerTriadCompatibilityRoutingReport:
    candidates = _load_candidates(root)
    results: list[CapitalizerTriadRoutingPolicyResult] = []
    cells: list[CapitalizerTriadRoutingRejectionCell] = []

    for tie_policy in ("SYMBOL_ASC", "SYMBOL_DESC"):
        for policy in POLICIES:
            results.append(
                _policy_result(
                    candidates,
                    policy=policy,
                    tie_policy=tie_policy,
                )
            )
            cells.extend(
                _rejection_cells(
                    candidates,
                    policy=policy,
                    tie_policy=tie_policy,
                )
            )

    symbols = tuple(sorted({item.symbol for item in candidates}))
    return CapitalizerTriadCompatibilityRoutingReport(
        identity=IDENTITY,
        market_count=len(symbols),
        symbols=symbols,
        baseline_opportunities=len(candidates),
        policy_results=tuple(results),
        rejection_cells=tuple(cells),
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Capitalizer triad-aware compatibility routing falsification"
    )
    parser.add_argument("input_root", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    report = build_triad_compatibility_routing_report(args.input_root)
    args.output.mkdir(parents=True, exist_ok=True)
    path = args.output / "capitalizer-triad-compatibility-routing-v1.json"
    path.write_text(
        json.dumps(asdict(report), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(asdict(report), sort_keys=True))


if __name__ == "__main__":
    main()
