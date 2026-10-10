"""V48 three-session pre-economic coverage gate.

Capitalizer's identity requires ASIA, LONDON and NEW_YORK capability across the frozen
nine-market universe. This gate does not force a trade in every session or market. It
requires that the census actually covers every configured market and that each session
demonstrates at least one source-complete opportunity before V48 can claim three-session
operability.

No outcomes, economics, Fresh Holdout, capital sizing or execution authority are used.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from qore.infrastructure.trader_lab.capitalizer_human_decision_graph_v48 import V48Session

IDENTITY = "QORE_CAPITALIZER_V48_THREE_SESSION_COVERAGE_GATE"

SESSION_MARKETS: dict[V48Session, tuple[str, ...]] = {
    V48Session.ASIA: ("USDJPY", "AUDJPY", "AUDUSD", "GBPJPY"),
    V48Session.LONDON: ("EURUSD", "GBPUSD"),
    V48Session.NEW_YORK: ("XAUUSD", "USDCAD", "NAS100"),
}


class V48ThreeSessionCoverageDecision(StrEnum):
    COMPLETE_PRE_ECONOMIC = "COMPLETE_PRE_ECONOMIC"
    INCOMPLETE = "INCOMPLETE"


@dataclass(frozen=True, slots=True)
class V48SessionMarketCoverage:
    session: V48Session
    market: str
    source_complete_opportunities: int

    def __post_init__(self) -> None:
        if self.session not in SESSION_MARKETS:
            raise ValueError("coverage row must use a configured trading session")
        if self.market not in SESSION_MARKETS[self.session]:
            raise ValueError("market does not belong to session identity")
        if self.source_complete_opportunities < 0:
            raise ValueError("opportunity count cannot be negative")


@dataclass(frozen=True, slots=True)
class V48ThreeSessionCoverageAssessment:
    decision: V48ThreeSessionCoverageDecision
    missing_market_rows: tuple[str, ...]
    empty_sessions: tuple[V48Session, ...]
    session_opportunity_totals: tuple[tuple[V48Session, int], ...]
    outcome_used: bool = False
    economics_used: bool = False
    fresh_holdout_used: bool = False
    forces_trade_quota: bool = False

    def __post_init__(self) -> None:
        complete = (
            self.decision is V48ThreeSessionCoverageDecision.COMPLETE_PRE_ECONOMIC
        )
        if complete != (not self.missing_market_rows and not self.empty_sessions):
            raise ValueError("three-session decision/payload mismatch")
        if self.outcome_used or self.economics_used or self.fresh_holdout_used:
            raise ValueError("three-session coverage gate must remain pre-economic")
        if self.forces_trade_quota:
            raise ValueError("MAX3 is a ceiling; coverage gate cannot force trades")


def assess_three_session_coverage(
    rows: tuple[V48SessionMarketCoverage, ...],
) -> V48ThreeSessionCoverageAssessment:
    seen: dict[tuple[V48Session, str], int] = {}
    for row in rows:
        key = (row.session, row.market)
        if key in seen:
            raise ValueError("duplicate session/market coverage row")
        seen[key] = row.source_complete_opportunities

    missing = tuple(
        f"{session.value}:{market}"
        for session, markets in SESSION_MARKETS.items()
        for market in markets
        if (session, market) not in seen
    )

    totals = tuple(
        (
            session,
            sum(seen.get((session, market), 0) for market in markets),
        )
        for session, markets in SESSION_MARKETS.items()
    )
    empty_sessions = tuple(session for session, total in totals if total <= 0)
    complete = not missing and not empty_sessions

    return V48ThreeSessionCoverageAssessment(
        decision=(
            V48ThreeSessionCoverageDecision.COMPLETE_PRE_ECONOMIC
            if complete
            else V48ThreeSessionCoverageDecision.INCOMPLETE
        ),
        missing_market_rows=missing,
        empty_sessions=empty_sessions,
        session_opportunity_totals=totals,
    )


@dataclass(frozen=True, slots=True)
class V48ThreeSessionCoverageGate:
    identity: str = IDENTITY
    required_sessions: tuple[V48Session, ...] = (
        V48Session.ASIA,
        V48Session.LONDON,
        V48Session.NEW_YORK,
    )
    max_executions_per_session: int = 3
    quota_required: bool = False
    economics_authorized: bool = False
    fresh_holdout_authorized: bool = False

    def __post_init__(self) -> None:
        if self.identity != IDENTITY:
            raise ValueError("three-session gate identity is frozen")
        if set(self.required_sessions) != set(SESSION_MARKETS):
            raise ValueError("three-session identity must cover Asia, London and New York")
        if self.max_executions_per_session != 3:
            raise ValueError("Capitalizer MAX3 per session ceiling is frozen")
        if self.quota_required:
            raise ValueError("MAX3 is a ceiling, not a quota")
        if self.economics_authorized or self.fresh_holdout_authorized:
            raise ValueError("coverage gate grants no economic or Fresh authority")


V48_THREE_SESSION_COVERAGE_GATE = V48ThreeSessionCoverageGate()
