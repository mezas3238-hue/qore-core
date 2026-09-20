"""Cross-market exposure falsification for the QORE Capitalizer MAX3 session contract.

This consumed-development lab starts from the enriched causal session-flow ledgers and asks
whether the drawdown added by a shared three-execution session budget is associated with
concurrent factor stacking that is already visible at candidate decision time.

Only categorical exposure relations from the existing Capitalizer Exposure Graph are tested:
- baseline MAX3 with no exposure rejection;
- reject candidates that add same-direction exposure to an already active shared factor;
- reject candidates that share any factor with an already active position.

No numeric exposure threshold, outcome-aware ranking, profit objective, cost model, QORE Risk
allocation, candidate freeze, fresh holdout, or promotion is introduced here. The experiment is
a falsification layer; QORE Risk remains sovereign.
"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from dataclasses import asdict, dataclass
from datetime import datetime
from decimal import Decimal
from pathlib import Path

from qore.infrastructure.trader_lab.capitalizer_contract import CapitalizerSession
from qore.infrastructure.trader_lab.capitalizer_exposure_graph import (
    CapitalizerExposurePosition,
    CapitalizerSide,
    factor_exposures,
)
from qore.infrastructure.trader_lab.capitalizer_portfolio_session_flow_viability import (
    PortfolioFlowMetrics,
    PortfolioFlowTrade,
    _expected_symbols,
    _metrics,
    _session_key,
)
from qore.infrastructure.trader_lab.capitalizer_session_clock import capitalizer_session_at
from qore.infrastructure.trader_lab.capitalizer_session_flow_viability import NEW_YORK

IDENTITY = "QORE_CAPITALIZER_PORTFOLIO_EXPOSURE_FORENSICS_V1"


@dataclass(frozen=True, slots=True)
class CapitalizerExposureCandidate:
    symbol: str
    side: CapitalizerSide
    signal_at: datetime
    entry_at: datetime
    exit_at: datetime
    event_labels: tuple[str, ...]
    planned_reward_r: Decimal
    state_family: str
    cisd_timing_state: str
    source_age_state: str
    boundary_type_state: str
    reclaim_phase: str
    realized_r: Decimal

    def __post_init__(self) -> None:
        PortfolioFlowTrade(
            symbol=self.symbol,
            entry_at=self.entry_at,
            exit_at=self.exit_at,
            realized_r=self.realized_r,
        )
        if self.signal_at.tzinfo is None or self.signal_at.utcoffset() is None:
            raise ValueError("candidate signal_at must be timezone-aware")
        if self.signal_at > self.entry_at:
            raise ValueError("candidate signal cannot follow entry")
        if self.planned_reward_r <= 0 or not self.planned_reward_r.is_finite():
            raise ValueError("candidate planned_reward_r must be positive finite")
        if not self.event_labels:
            raise ValueError("candidate event_labels must be non-empty")
        for name, value in (
            ("state_family", self.state_family),
            ("cisd_timing_state", self.cisd_timing_state),
            ("source_age_state", self.source_age_state),
            ("boundary_type_state", self.boundary_type_state),
            ("reclaim_phase", self.reclaim_phase),
        ):
            if not value:
                raise ValueError(f"candidate {name} must be non-empty")

    def as_trade(self) -> PortfolioFlowTrade:
        return PortfolioFlowTrade(
            symbol=self.symbol,
            entry_at=self.entry_at,
            exit_at=self.exit_at,
            realized_r=self.realized_r,
        )


@dataclass(frozen=True, slots=True)
class CapitalizerExposureAssessment:
    active_positions: int
    shared_factors: int
    same_direction_factors: int
    opposing_direction_factors: int
    neutralized_active_factors: int
    state: str


@dataclass(frozen=True, slots=True)
class CapitalizerExposurePolicyResult:
    policy: str
    tie_policy: str
    metrics: PortfolioFlowMetrics
    selected_trades: int
    rejected_by_exposure: int
    rejected_metrics: PortfolioFlowMetrics | None
    sessions: int
    sessions_reaching_three: int
    third_executions: int
    third_with_active_position: int
    third_with_same_direction_shared_factor: int
    positive_years: int
    years_observed: int


@dataclass(frozen=True, slots=True)
class CapitalizerExposureStateCell:
    policy: str
    tie_policy: str
    session: str
    ordinal: int
    symbol: str
    exposure_state: str
    trades: int
    metrics: PortfolioFlowMetrics


@dataclass(frozen=True, slots=True)
class CapitalizerPortfolioExposureForensicsReport:
    identity: str
    market_count: int
    symbols: tuple[str, ...]
    baseline_opportunities: int
    policy_results: tuple[CapitalizerExposurePolicyResult, ...]
    state_cells: tuple[CapitalizerExposureStateCell, ...]
    unit_r_exposure_proxy: bool = True
    causal_active_position_state_only: bool = True
    numeric_exposure_threshold_used: bool = False
    outcome_aware_ranking_used: bool = False
    max_executions_per_session: int = 3
    positive_pnl_is_not_stop_condition: bool = True
    governed_profit_objective_not_modeled: bool = True
    qore_risk_authority_granted: bool = False
    costs_applied: bool = False
    development_only: bool = True
    candidate_frozen: bool = False
    fresh_holdout_claimed: bool = False
    rule_selected: bool = False
    promotion_allowed: bool = False


def _load_candidates(root: Path) -> tuple[CapitalizerExposureCandidate, ...]:
    paths = sorted(root.rglob("capitalizer-*-session-flow-trades-v1.jsonl"))
    if not paths:
        raise ValueError("no enriched Capitalizer session-flow ledgers found")

    result: list[CapitalizerExposureCandidate] = []
    for path in paths:
        with path.open(encoding="utf-8") as handle:
            for line in handle:
                if not line.strip():
                    continue
                row = json.loads(line)
                labels = row.get("event_labels")
                if not isinstance(labels, list) or not all(
                    isinstance(item, str) and item for item in labels
                ):
                    raise ValueError("enriched ledger requires event_labels")
                try:
                    result.append(
                        CapitalizerExposureCandidate(
                            symbol=str(row["symbol"]),
                            side=CapitalizerSide(str(row["side"])),
                            signal_at=datetime.fromisoformat(str(row["signal_at"])),
                            entry_at=datetime.fromisoformat(str(row["entry_at"])),
                            exit_at=datetime.fromisoformat(str(row["exit_at"])),
                            event_labels=tuple(labels),
                            planned_reward_r=Decimal(str(row["planned_reward_r"])),
                            state_family=str(row["state_family"]),
                            cisd_timing_state=str(row["cisd_timing_state"]),
                            source_age_state=str(row["source_age_state"]),
                            boundary_type_state=str(row["boundary_type_state"]),
                            reclaim_phase=str(row["reclaim_phase"]),
                            realized_r=Decimal(str(row["realized_gross_r"])),
                        )
                    )
                except KeyError as exc:
                    raise ValueError(
                        f"enriched session-flow ledger missing {exc.args[0]}"
                    ) from exc

    symbols = {item.symbol for item in result}
    expected = _expected_symbols()
    if symbols != expected:
        raise ValueError(
            f"exposure universe mismatch missing={sorted(expected - symbols)} "
            f"extra={sorted(symbols - expected)}"
        )
    return tuple(result)


def _ordered(
    candidates: tuple[CapitalizerExposureCandidate, ...],
    *,
    tie_policy: str,
) -> tuple[CapitalizerExposureCandidate, ...]:
    if tie_policy not in {"SYMBOL_ASC", "SYMBOL_DESC"}:
        raise ValueError("unsupported exposure tie policy")
    grouped: dict[datetime, list[CapitalizerExposureCandidate]] = defaultdict(list)
    for candidate in candidates:
        grouped[candidate.entry_at].append(candidate)

    result: list[CapitalizerExposureCandidate] = []
    for entry_at in sorted(grouped):
        rows = sorted(
            grouped[entry_at],
            key=lambda item: item.symbol,
            reverse=tie_policy == "SYMBOL_DESC",
        )
        result.extend(rows)
    return tuple(result)


def _unit_position(candidate: CapitalizerExposureCandidate) -> CapitalizerExposurePosition:
    return CapitalizerExposurePosition(
        symbol=candidate.symbol,
        side=candidate.side,
        risk_r=Decimal("1"),
    )


def _assessment(
    candidate: CapitalizerExposureCandidate,
    active: tuple[CapitalizerExposureCandidate, ...],
) -> CapitalizerExposureAssessment:
    if not active:
        return CapitalizerExposureAssessment(
            active_positions=0,
            shared_factors=0,
            same_direction_factors=0,
            opposing_direction_factors=0,
            neutralized_active_factors=0,
            state="NO_ACTIVE_POSITION",
        )

    candidate_factors = {
        item.factor: item
        for item in factor_exposures((_unit_position(candidate),))
    }
    active_factors = {
        item.factor: item
        for item in factor_exposures(tuple(_unit_position(item) for item in active))
    }

    shared = 0
    same = 0
    opposing = 0
    neutralized = 0
    for factor, candidate_exposure in candidate_factors.items():
        active_exposure = active_factors.get(factor)
        if active_exposure is None or active_exposure.gross_r == 0:
            continue
        shared += 1
        if active_exposure.net_r == 0:
            neutralized += 1
        elif active_exposure.net_r * candidate_exposure.net_r > 0:
            same += 1
        else:
            opposing += 1

    if shared == 0:
        state = "NO_SHARED_FACTOR"
    elif same > 0 and opposing == 0 and neutralized == 0:
        state = "SHARED_FACTOR_SAME_DIRECTION"
    elif opposing > 0 and same == 0 and neutralized == 0:
        state = "SHARED_FACTOR_OPPOSING_DIRECTION"
    else:
        state = "SHARED_FACTOR_MIXED"

    return CapitalizerExposureAssessment(
        active_positions=len(active),
        shared_factors=shared,
        same_direction_factors=same,
        opposing_direction_factors=opposing,
        neutralized_active_factors=neutralized,
        state=state,
    )


def _blocks(policy: str, assessment: CapitalizerExposureAssessment) -> bool:
    if policy == "MAX3_BASELINE":
        return False
    if policy == "MAX3_BLOCK_SAME_DIRECTION_SHARED_FACTOR":
        return assessment.same_direction_factors > 0
    if policy == "MAX3_BLOCK_ANY_SHARED_FACTOR":
        return assessment.shared_factors > 0
    raise ValueError("unsupported exposure policy")


def _select(
    candidates: tuple[CapitalizerExposureCandidate, ...],
    *,
    policy: str,
    tie_policy: str,
) -> tuple[
    tuple[CapitalizerExposureCandidate, ...],
    tuple[CapitalizerExposureCandidate, ...],
    dict[str, tuple[CapitalizerExposureAssessment, int]],
]:
    per_session: dict[str, list[CapitalizerExposureCandidate]] = defaultdict(list)
    selected: list[CapitalizerExposureCandidate] = []
    rejected: list[CapitalizerExposureCandidate] = []
    accepted_context: dict[str, tuple[CapitalizerExposureAssessment, int]] = {}

    for candidate in _ordered(candidates, tie_policy=tie_policy):
        key = _session_key(candidate.as_trade())
        accepted = per_session[key]
        if len(accepted) >= 3:
            continue

        active = tuple(
            item for item in accepted if item.exit_at > candidate.entry_at
        )
        assessment = _assessment(candidate, active)
        if _blocks(policy, assessment):
            rejected.append(candidate)
            continue

        accepted.append(candidate)
        selected.append(candidate)
        accepted_context[
            f"{candidate.symbol}|{candidate.entry_at.isoformat()}|{len(accepted)}"
        ] = (assessment, len(accepted))

    return tuple(selected), tuple(rejected), accepted_context


def _policy_result(
    candidates: tuple[CapitalizerExposureCandidate, ...],
    *,
    policy: str,
    tie_policy: str,
) -> CapitalizerExposurePolicyResult:
    selected, rejected, context = _select(
        candidates,
        policy=policy,
        tie_policy=tie_policy,
    )
    trades = tuple(item.as_trade() for item in selected)
    rejected_trades = tuple(item.as_trade() for item in rejected)

    grouped: dict[str, int] = defaultdict(int)
    thirds = 0
    third_active = 0
    third_same = 0
    by_year: dict[int, Decimal] = defaultdict(lambda: Decimal("0"))
    for candidate in selected:
        key = _session_key(candidate.as_trade())
        grouped[key] += 1
        ordinal = grouped[key]
        if ordinal == 3:
            thirds += 1
            assessment, _ = context[
                f"{candidate.symbol}|{candidate.entry_at.isoformat()}|{ordinal}"
            ]
            if assessment.active_positions > 0:
                third_active += 1
            if assessment.same_direction_factors > 0:
                third_same += 1
        by_year[candidate.entry_at.astimezone(NEW_YORK).year] += candidate.realized_r

    return CapitalizerExposurePolicyResult(
        policy=policy,
        tie_policy=tie_policy,
        metrics=_metrics(trades),
        selected_trades=len(selected),
        rejected_by_exposure=len(rejected),
        rejected_metrics=_metrics(rejected_trades) if rejected_trades else None,
        sessions=len(grouped),
        sessions_reaching_three=sum(count >= 3 for count in grouped.values()),
        third_executions=thirds,
        third_with_active_position=third_active,
        third_with_same_direction_shared_factor=third_same,
        positive_years=sum(total > 0 for total in by_year.values()),
        years_observed=len(by_year),
    )


def _state_cells(
    candidates: tuple[CapitalizerExposureCandidate, ...],
    *,
    policy: str,
    tie_policy: str,
) -> tuple[CapitalizerExposureStateCell, ...]:
    selected, _, context = _select(
        candidates,
        policy=policy,
        tie_policy=tie_policy,
    )
    grouped: dict[
        tuple[str, int, str, str],
        list[PortfolioFlowTrade],
    ] = defaultdict(list)
    per_session: dict[str, int] = defaultdict(int)

    for candidate in selected:
        key = _session_key(candidate.as_trade())
        per_session[key] += 1
        ordinal = per_session[key]
        assessment, _ = context[
            f"{candidate.symbol}|{candidate.entry_at.isoformat()}|{ordinal}"
        ]
        session = capitalizer_session_at(candidate.entry_at)
        if session is None:
            raise ValueError("selected exposure candidate lost session identity")
        grouped[
            (session.value, ordinal, candidate.symbol, assessment.state)
        ].append(candidate.as_trade())

    return tuple(
        CapitalizerExposureStateCell(
            policy=policy,
            tie_policy=tie_policy,
            session=session,
            ordinal=ordinal,
            symbol=symbol,
            exposure_state=state,
            trades=len(rows),
            metrics=_metrics(tuple(rows)),
        )
        for (session, ordinal, symbol, state), rows in sorted(grouped.items())
    )


def build_portfolio_exposure_forensics_report(
    root: Path,
) -> CapitalizerPortfolioExposureForensicsReport:
    candidates = _load_candidates(root)
    policies = (
        "MAX3_BASELINE",
        "MAX3_BLOCK_SAME_DIRECTION_SHARED_FACTOR",
        "MAX3_BLOCK_ANY_SHARED_FACTOR",
    )
    results: list[CapitalizerExposurePolicyResult] = []
    cells: list[CapitalizerExposureStateCell] = []
    for tie_policy in ("SYMBOL_ASC", "SYMBOL_DESC"):
        for policy in policies:
            results.append(
                _policy_result(
                    candidates,
                    policy=policy,
                    tie_policy=tie_policy,
                )
            )
            cells.extend(
                _state_cells(
                    candidates,
                    policy=policy,
                    tie_policy=tie_policy,
                )
            )

    symbols = tuple(sorted({item.symbol for item in candidates}))
    return CapitalizerPortfolioExposureForensicsReport(
        identity=IDENTITY,
        market_count=len(symbols),
        symbols=symbols,
        baseline_opportunities=len(candidates),
        policy_results=tuple(results),
        state_cells=tuple(cells),
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Capitalizer portfolio exposure falsification"
    )
    parser.add_argument("input_root", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    report = build_portfolio_exposure_forensics_report(args.input_root)
    args.output.mkdir(parents=True, exist_ok=True)
    path = args.output / "capitalizer-portfolio-exposure-forensics-v1.json"
    path.write_text(
        json.dumps(asdict(report), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(asdict(report), sort_keys=True))


if __name__ == "__main__":
    main()
