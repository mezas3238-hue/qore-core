"""Aggregate the frozen V49 Trader over the reserved 1Y holdout.

Input is nine market-level V49 capacity artifacts generated with the exact frozen holdout
window. The aggregate materializes deterministic trade intents and applies the portfolio
MAX3/session/day ceiling.

The report answers one question only: how many trades did the frozen V49 Trader admit in
the 1Y reserved holdout? No trade outcomes or economics are opened.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from qore.infrastructure.trader_lab.capitalizer_contract import (
    CapitalizerSession,
    allowed_markets,
)
from qore.infrastructure.trader_lab.capitalizer_high_frequency_capacity_census_v49 import (
    IDENTITY as CAPACITY_IDENTITY,
)
from qore.infrastructure.trader_lab.capitalizer_high_frequency_capacity_census_v49 import (
    V49Opportunity,
)
from qore.infrastructure.trader_lab.capitalizer_high_frequency_trader_v49 import (
    V49TradeIntent,
    select_portfolio_trade_intents,
)
from qore.infrastructure.trader_lab.capitalizer_v49_holdout_contract import (
    HOLDOUT_END,
    HOLDOUT_START,
    V49_RESERVED_HOLDOUT_1Y,
)
from qore.infrastructure.trader_lab.capitalizer_v49_holdout_contract import (
    IDENTITY as HOLDOUT_IDENTITY,
)

IDENTITY = "QORE_CAPITALIZER_V49_RESERVED_HOLDOUT_REPLAY_1Y"


@dataclass(frozen=True, slots=True)
class V49HoldoutReplayReport:
    identity: str
    holdout_contract_identity: str
    methodology_git_sha: str
    window_start: str
    window_end_exclusive: str
    market_count: int
    session_count: int
    candidate_opportunities: int
    executed_trades: int
    executed_by_session: tuple[tuple[str, int], ...]
    executed_by_market: tuple[tuple[str, int], ...]
    active_trading_days: int
    sessions_hitting_max3: int
    max_trades_one_day: int
    decision_timeframes: tuple[str, ...] = ("H1", "M15", "M1")
    fresh_holdout_used: bool = False
    outcome_used: bool = False
    economics_used: bool = False
    daily_used: bool = False
    h4_used: bool = False
    methodology_mutation_allowed: bool = False
    live_authorized: bool = False
    real_capital_authorized: bool = False

    def __post_init__(self) -> None:
        if self.identity != IDENTITY:
            raise ValueError("unexpected V49 holdout replay identity")
        if self.holdout_contract_identity != HOLDOUT_IDENTITY:
            raise ValueError("holdout report must use frozen V49 contract")
        if len(self.methodology_git_sha) < 7:
            raise ValueError("holdout replay requires methodology git SHA")
        if self.market_count != 9 or self.session_count != 3:
            raise ValueError("holdout replay requires 9 markets and 3 sessions")
        if self.executed_trades > self.candidate_opportunities:
            raise ValueError("executed trades cannot exceed candidates")
        if self.decision_timeframes != ("H1", "M15", "M1"):
            raise ValueError("V49 holdout must remain H1/M15/M1 only")
        if (
            self.fresh_holdout_used
            or self.outcome_used
            or self.economics_used
            or self.daily_used
            or self.h4_used
            or self.methodology_mutation_allowed
            or self.live_authorized
            or self.real_capital_authorized
        ):
            raise ValueError("holdout report crossed its epistemic/governance boundary")


def _read_market_reports(root: Path) -> tuple[dict[str, Any], ...]:
    paths = sorted(root.rglob("capitalizer-*-v49-hf-capacity.json"))
    if len(paths) != 9:
        raise ValueError(f"V49 holdout requires 9 market reports, got {len(paths)}")
    rows = tuple(json.loads(path.read_text(encoding="utf-8")) for path in paths)
    if any(row.get("identity") != CAPACITY_IDENTITY for row in rows):
        raise ValueError("unexpected market capacity identity in holdout")
    return rows


def _read_opportunities(root: Path) -> tuple[V49Opportunity, ...]:
    rows: list[V49Opportunity] = []
    paths = sorted(root.rglob("capitalizer-*-v49-hf-capacity-opportunities.jsonl"))
    if len(paths) != 9:
        raise ValueError(f"V49 holdout requires 9 opportunity ledgers, got {len(paths)}")
    for path in paths:
        with path.open(encoding="utf-8") as handle:
            for line in handle:
                if line.strip():
                    rows.append(V49Opportunity(**json.loads(line)))
    return tuple(sorted(rows, key=lambda item: item.m1_trigger_confirmed_at))


def _expected_universe() -> set[tuple[str, str]]:
    return {
        (session.value, symbol)
        for session in CapitalizerSession
        for symbol in allowed_markets(session)
    }


def build_holdout_report(
    root: Path,
    *,
    methodology_git_sha: str,
) -> tuple[V49HoldoutReplayReport, tuple[V49TradeIntent, ...]]:
    contract = V49_RESERVED_HOLDOUT_1Y
    reports = _read_market_reports(root)
    opportunities = _read_opportunities(root)

    observed = {(str(row["session"]), str(row["symbol"])) for row in reports}
    if observed != _expected_universe():
        raise ValueError("V49 holdout market/session universe mismatch")

    expected_start = HOLDOUT_START.isoformat()
    expected_end = HOLDOUT_END.isoformat()
    for row in reports:
        if row.get("window_start") != expected_start:
            raise ValueError("market report used wrong holdout start")
        if row.get("window_end_exclusive") != expected_end:
            raise ValueError("market report used wrong holdout end")
        if row.get("fresh_holdout_used") is not False:
            raise ValueError("protected Fresh Holdout must remain sealed")
        if row.get("outcome_used") is not False or row.get("economics_used") is not False:
            raise ValueError("market holdout report opened outcomes/economics")
        if row.get("daily_used") is not False or row.get("h4_used") is not False:
            raise ValueError("V49 holdout cannot use Daily/H4")

    expected_candidates = sum(
        int(row["source_complete_opportunities"])
        for row in reports
    )
    if expected_candidates != len(opportunities):
        raise ValueError("market reports do not reconcile with opportunity ledgers")

    trades = select_portfolio_trade_intents(opportunities)
    by_session: Counter[str] = Counter(item.session for item in trades)
    by_market: Counter[str] = Counter(item.symbol for item in trades)
    by_day: Counter[str] = Counter(item.operating_date for item in trades)
    by_session_day: Counter[tuple[str, str]] = Counter(
        (item.session, item.operating_date) for item in trades
    )

    report = V49HoldoutReplayReport(
        identity=IDENTITY,
        holdout_contract_identity=contract.identity,
        methodology_git_sha=methodology_git_sha,
        window_start=expected_start,
        window_end_exclusive=expected_end,
        market_count=9,
        session_count=3,
        candidate_opportunities=len(opportunities),
        executed_trades=len(trades),
        executed_by_session=tuple(sorted(by_session.items())),
        executed_by_market=tuple(sorted(by_market.items())),
        active_trading_days=len(by_day),
        sessions_hitting_max3=sum(
            count == 3 for count in by_session_day.values()
        ),
        max_trades_one_day=max(by_day.values(), default=0),
    )
    return report, trades


def write_holdout_report(
    report: V49HoldoutReplayReport,
    trades: tuple[V49TradeIntent, ...],
    output: Path,
) -> None:
    output.mkdir(parents=True, exist_ok=True)
    (output / "capitalizer-v49-reserved-holdout-1y-report.json").write_text(
        json.dumps(asdict(report), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    with (output / "capitalizer-v49-reserved-holdout-1y-trades.jsonl").open(
        "w",
        encoding="utf-8",
    ) as handle:
        for item in trades:
            handle.write(json.dumps(asdict(item), default=str, sort_keys=True) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("input_root", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--git-sha", required=True)
    args = parser.parse_args()

    report, trades = build_holdout_report(
        args.input_root,
        methodology_git_sha=args.git_sha,
    )
    write_holdout_report(report, trades, args.output)
    print(json.dumps(asdict(report), sort_keys=True))


if __name__ == "__main__":
    main()
