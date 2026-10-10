"""Session compatibility routing falsification for QORE Capitalizer.

Consumed-development evidence only. This lab converts a small set of pair/session/side
relationships into causal admission-time veto hypotheses. The router sees only candidates
already accepted earlier in the same session plus currently active positions; it never sees
future candidates or outcomes.

The hypotheses are intentionally narrow and separately reported:
- core weak side-pair vetoes observed consistently across deterministic tie policies;
- an extended weak-pair veto set for falsification;
- core vetoes plus the previously isolated XAUUSD New York ordinal-2 same-direction
  shared-factor state.

This module does not optimize numeric thresholds, rank by realized outcomes at runtime,
invent a profit objective, grant QORE Risk authority, freeze a candidate, claim a fresh
holdout, or promote a rule.
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

IDENTITY = "QORE_CAPITALIZER_SESSION_COMPATIBILITY_ROUTING_FORENSICS_V1"

POLICIES = (
    "MAX3_BASELINE",
    "BLOCK_ASIA_WEAK_SIDE_PAIR_ONLY_V1",
    "BLOCK_LONDON_WEAK_SIDE_PAIR_ONLY_V1",
    "BLOCK_NEW_YORK_WEAK_SIDE_PAIR_ONLY_V1",
    "BLOCK_LONDON_PLUS_NEW_YORK_WEAK_PAIRS_V1",
    "BLOCK_CORE_WEAK_SIDE_PAIRS_V1",
    "BLOCK_EXTENDED_WEAK_SIDE_PAIRS_V1",
    "BLOCK_CORE_WEAK_SIDE_PAIRS_PLUS_XAUUSD_ORD2_SHARED_V1",
)

PairState = tuple[str, CapitalizerSide, str, CapitalizerSide]

CORE_WEAK_SIDE_PAIRS: dict[str, frozenset[PairState]] = {
    "ASIA": frozenset(
        {
            ("AUDJPY", CapitalizerSide.SHORT, "USDJPY", CapitalizerSide.LONG),
        }
    ),
    "LONDON": frozenset(
        {
            ("EURUSD", CapitalizerSide.SHORT, "GBPUSD", CapitalizerSide.LONG),
        }
    ),
    "NEW_YORK": frozenset(
        {
            ("NAS100", CapitalizerSide.SHORT, "XAUUSD", CapitalizerSide.SHORT),
        }
    ),
}

EXTENDED_WEAK_SIDE_PAIRS: dict[str, frozenset[PairState]] = {
    "ASIA": frozenset(
        {
            *CORE_WEAK_SIDE_PAIRS["ASIA"],
            ("AUDJPY", CapitalizerSide.LONG, "AUDUSD", CapitalizerSide.SHORT),
            ("GBPJPY", CapitalizerSide.SHORT, "USDJPY", CapitalizerSide.LONG),
            ("AUDJPY", CapitalizerSide.SHORT, "GBPJPY", CapitalizerSide.LONG),
        }
    ),
    "LONDON": CORE_WEAK_SIDE_PAIRS["LONDON"],
    "NEW_YORK": frozenset(
        {
            *CORE_WEAK_SIDE_PAIRS["NEW_YORK"],
            ("NAS100", CapitalizerSide.SHORT, "USDCAD", CapitalizerSide.SHORT),
        }
    ),
}

ASIA_WEAK_ONLY: dict[str, frozenset[PairState]] = {
    "ASIA": CORE_WEAK_SIDE_PAIRS["ASIA"],
}
LONDON_WEAK_ONLY: dict[str, frozenset[PairState]] = {
    "LONDON": CORE_WEAK_SIDE_PAIRS["LONDON"],
}
NEW_YORK_WEAK_ONLY: dict[str, frozenset[PairState]] = {
    "NEW_YORK": CORE_WEAK_SIDE_PAIRS["NEW_YORK"],
}

LONDON_PLUS_NEW_YORK_WEAK: dict[str, frozenset[PairState]] = {
    "LONDON": CORE_WEAK_SIDE_PAIRS["LONDON"],
    "NEW_YORK": CORE_WEAK_SIDE_PAIRS["NEW_YORK"],
}


@dataclass(frozen=True, slots=True)
class CapitalizerCompatibilityPolicyResult:
    policy: str
    tie_policy: str
    metrics: PortfolioFlowMetrics
    selected_trades: int
    rejected_by_compatibility: int
    rejected_metrics: PortfolioFlowMetrics | None
    sessions: int
    sessions_reaching_three: int
    positive_years: int
    years_observed: int


@dataclass(frozen=True, slots=True)
class CapitalizerCompatibilityRejectionCell:
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
class CapitalizerSessionCompatibilityRoutingReport:
    identity: str
    market_count: int
    symbols: tuple[str, ...]
    baseline_opportunities: int
    policy_results: tuple[CapitalizerCompatibilityPolicyResult, ...]
    rejection_cells: tuple[CapitalizerCompatibilityRejectionCell, ...]
    max_executions_per_session: int = 3
    prior_session_acceptances_only: bool = True
    active_position_state_is_causal: bool = True
    future_candidates_visible: bool = False
    pair_states_are_categorical: bool = True
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


def _canonical_pair(
    first: CapitalizerExposureCandidate,
    second: CapitalizerExposureCandidate,
) -> PairState:
    if first.symbol < second.symbol:
        return first.symbol, first.side, second.symbol, second.side
    return second.symbol, second.side, first.symbol, first.side


def _weak_pair_reason(
    candidate: CapitalizerExposureCandidate,
    prior: tuple[CapitalizerExposureCandidate, ...],
    *,
    table: dict[str, frozenset[PairState]],
) -> str | None:
    session = capitalizer_session_at(candidate.entry_at)
    if session is None:
        raise ValueError("compatibility candidate lost Capitalizer session")
    weak = table.get(session.value, frozenset())
    for accepted in prior:
        state = _canonical_pair(accepted, candidate)
        if state in weak:
            left, left_side, right, right_side = state
            return (
                f"WEAK_PAIR:{session.value}:"
                f"{left}_{left_side.value}+{right}_{right_side.value}"
            )
    return None


def _xauusd_ordinal2_shared_reason(
    candidate: CapitalizerExposureCandidate,
    *,
    ordinal: int,
    assessment: CapitalizerExposureAssessment,
) -> str | None:
    session = capitalizer_session_at(candidate.entry_at)
    if session is None:
        raise ValueError("compatibility candidate lost Capitalizer session")
    if (
        session.value == "NEW_YORK"
        and candidate.symbol == "XAUUSD"
        and ordinal == 2
        and assessment.same_direction_factors > 0
    ):
        return "XAUUSD_NY_ORD2_SAME_DIRECTION_SHARED_FACTOR"
    return None


def _rejection_reason(
    *,
    policy: str,
    candidate: CapitalizerExposureCandidate,
    prior: tuple[CapitalizerExposureCandidate, ...],
    ordinal: int,
    assessment: CapitalizerExposureAssessment,
) -> str | None:
    if policy == "MAX3_BASELINE":
        return None
    if policy == "BLOCK_ASIA_WEAK_SIDE_PAIR_ONLY_V1":
        return _weak_pair_reason(candidate, prior, table=ASIA_WEAK_ONLY)
    if policy == "BLOCK_LONDON_WEAK_SIDE_PAIR_ONLY_V1":
        return _weak_pair_reason(candidate, prior, table=LONDON_WEAK_ONLY)
    if policy == "BLOCK_NEW_YORK_WEAK_SIDE_PAIR_ONLY_V1":
        return _weak_pair_reason(candidate, prior, table=NEW_YORK_WEAK_ONLY)
    if policy == "BLOCK_LONDON_PLUS_NEW_YORK_WEAK_PAIRS_V1":
        return _weak_pair_reason(candidate, prior, table=LONDON_PLUS_NEW_YORK_WEAK)
    if policy == "BLOCK_CORE_WEAK_SIDE_PAIRS_V1":
        return _weak_pair_reason(candidate, prior, table=CORE_WEAK_SIDE_PAIRS)
    if policy == "BLOCK_EXTENDED_WEAK_SIDE_PAIRS_V1":
        return _weak_pair_reason(candidate, prior, table=EXTENDED_WEAK_SIDE_PAIRS)
    if policy == "BLOCK_CORE_WEAK_SIDE_PAIRS_PLUS_XAUUSD_ORD2_SHARED_V1":
        weak = _weak_pair_reason(candidate, prior, table=CORE_WEAK_SIDE_PAIRS)
        if weak is not None:
            return weak
        return _xauusd_ordinal2_shared_reason(
            candidate,
            ordinal=ordinal,
            assessment=assessment,
        )
    raise ValueError("unsupported compatibility policy")


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
        raise ValueError("unsupported compatibility policy")

    per_session: dict[str, list[CapitalizerExposureCandidate]] = defaultdict(list)
    selected: list[CapitalizerExposureCandidate] = []
    rejected: list[tuple[CapitalizerExposureCandidate, str, int]] = []

    for candidate in _ordered(candidates, tie_policy=tie_policy):
        key = _session_key(candidate.as_trade())
        accepted = per_session[key]
        if len(accepted) >= 3:
            continue

        ordinal = len(accepted) + 1
        active = tuple(item for item in accepted if item.exit_at > candidate.entry_at)
        assessment = _assessment(candidate, active)
        reason = _rejection_reason(
            policy=policy,
            candidate=candidate,
            prior=tuple(accepted),
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
) -> CapitalizerCompatibilityPolicyResult:
    selected, rejected = _select(candidates, policy=policy, tie_policy=tie_policy)
    trades = tuple(item.as_trade() for item in selected)
    rejected_trades = tuple(item.as_trade() for item, _, _ in rejected)

    session_counts: dict[str, int] = defaultdict(int)
    by_year: dict[int, Decimal] = defaultdict(lambda: Decimal("0"))
    for candidate in selected:
        session_counts[_session_key(candidate.as_trade())] += 1
        by_year[candidate.entry_at.astimezone(NEW_YORK).year] += candidate.realized_r

    return CapitalizerCompatibilityPolicyResult(
        policy=policy,
        tie_policy=tie_policy,
        metrics=_metrics(trades),
        selected_trades=len(selected),
        rejected_by_compatibility=len(rejected),
        rejected_metrics=_metrics(rejected_trades) if rejected_trades else None,
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
) -> tuple[CapitalizerCompatibilityRejectionCell, ...]:
    _, rejected = _select(candidates, policy=policy, tie_policy=tie_policy)
    grouped: dict[
        tuple[str, str, str, CapitalizerSide, int],
        list[CapitalizerExposureCandidate],
    ] = defaultdict(list)

    for candidate, reason, ordinal in rejected:
        session = capitalizer_session_at(candidate.entry_at)
        if session is None:
            raise ValueError("rejected compatibility candidate lost session")
        grouped[
            (reason, session.value, candidate.symbol, candidate.side, ordinal)
        ].append(candidate)

    return tuple(
        CapitalizerCompatibilityRejectionCell(
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


def build_session_compatibility_routing_report(
    root: Path,
) -> CapitalizerSessionCompatibilityRoutingReport:
    candidates = _load_candidates(root)
    results: list[CapitalizerCompatibilityPolicyResult] = []
    cells: list[CapitalizerCompatibilityRejectionCell] = []

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
    return CapitalizerSessionCompatibilityRoutingReport(
        identity=IDENTITY,
        market_count=len(symbols),
        symbols=symbols,
        baseline_opportunities=len(candidates),
        policy_results=tuple(results),
        rejection_cells=tuple(cells),
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Capitalizer causal session compatibility routing falsification"
    )
    parser.add_argument("input_root", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    report = build_session_compatibility_routing_report(args.input_root)
    args.output.mkdir(parents=True, exist_ok=True)
    path = args.output / "capitalizer-session-compatibility-routing-v1.json"
    path.write_text(
        json.dumps(asdict(report), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(asdict(report), sort_keys=True))


if __name__ == "__main__":
    main()
