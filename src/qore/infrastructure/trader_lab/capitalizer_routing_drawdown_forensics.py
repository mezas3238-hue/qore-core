"""Residual drawdown forensics for QORE Capitalizer compatibility routing.

Consumed-development evidence only. This lab reconstructs the exact realized-equity peak-to-
trough interval responsible for maximum drawdown under selected MAX3 routing hypotheses and
attributes that interval by session, market, side, and session ordinal.

It is diagnostic only. It does not derive a new admission rule, optimize thresholds, rank by
future outcomes, change the Owner MAX3 contract, grant QORE Risk authority, freeze a candidate,
claim a fresh holdout, or promote anything.
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
)
from qore.infrastructure.trader_lab.capitalizer_portfolio_session_flow_viability import (
    _session_key,
)
from qore.infrastructure.trader_lab.capitalizer_session_clock import capitalizer_session_at
from qore.infrastructure.trader_lab.capitalizer_session_compatibility_routing import (
    _select,
)

IDENTITY = "QORE_CAPITALIZER_ROUTING_DRAWDOWN_FORENSICS_V1"

POLICIES = (
    "MAX3_BASELINE",
    "BLOCK_LONDON_PLUS_NEW_YORK_WEAK_PAIRS_V1",
    "BLOCK_EXTENDED_WEAK_SIDE_PAIRS_V1",
)


@dataclass(frozen=True, slots=True)
class CapitalizerDrawdownEpisode:
    policy: str
    tie_policy: str
    peak_equity_r: str
    trough_equity_r: str
    drawdown_r: str
    peak_exit_at: str | None
    trough_exit_at: str
    trades_in_episode: int
    winning_trades: int
    losing_trades: int
    flat_trades: int
    episode_total_r: str
    first_episode_exit_at: str


@dataclass(frozen=True, slots=True)
class CapitalizerDrawdownContribution:
    policy: str
    tie_policy: str
    session: str
    symbol: str
    side: str
    ordinal: int
    trades: int
    total_r: str
    mean_r: str
    winners: int
    losers: int


@dataclass(frozen=True, slots=True)
class CapitalizerDrawdownSessionContribution:
    policy: str
    tie_policy: str
    session: str
    trades: int
    total_r: str
    winners: int
    losers: int


@dataclass(frozen=True, slots=True)
class CapitalizerRoutingDrawdownForensicsReport:
    identity: str
    market_count: int
    symbols: tuple[str, ...]
    episodes: tuple[CapitalizerDrawdownEpisode, ...]
    contribution_cells: tuple[CapitalizerDrawdownContribution, ...]
    session_contributions: tuple[CapitalizerDrawdownSessionContribution, ...]
    realized_exit_order_used: bool = True
    max3_contract_preserved: bool = True
    exact_peak_to_trough_only: bool = True
    diagnostic_only: bool = True
    numeric_threshold_optimization_used: bool = False
    outcome_aware_runtime_ranking_used: bool = False
    new_rule_selected: bool = False
    qore_risk_authority_granted: bool = False
    costs_applied: bool = False
    development_only: bool = True
    candidate_frozen: bool = False
    fresh_holdout_claimed: bool = False
    promotion_allowed: bool = False


def _ordinal_index(
    selected: tuple[CapitalizerExposureCandidate, ...],
) -> dict[CapitalizerExposureCandidate, int]:
    per_session: dict[str, int] = defaultdict(int)
    result: dict[CapitalizerExposureCandidate, int] = {}
    for candidate in selected:
        key = _session_key(candidate.as_trade())
        per_session[key] += 1
        result[candidate] = per_session[key]
    return result


def _max_drawdown_episode(
    selected: tuple[CapitalizerExposureCandidate, ...],
) -> tuple[
    Decimal,
    Decimal,
    Decimal,
    CapitalizerExposureCandidate | None,
    CapitalizerExposureCandidate,
    tuple[CapitalizerExposureCandidate, ...],
]:
    exits = tuple(
        sorted(
            selected,
            key=lambda item: (item.exit_at, item.entry_at, item.symbol),
        )
    )
    if not exits:
        raise ValueError("drawdown forensics requires selected trades")

    equity = Decimal("0")
    peak = Decimal("0")
    peak_candidate: CapitalizerExposureCandidate | None = None
    peak_index = -1
    max_dd = Decimal("0")
    max_peak = Decimal("0")
    max_peak_candidate: CapitalizerExposureCandidate | None = None
    max_peak_index = -1
    trough_candidate = exits[0]
    trough_index = 0
    trough_equity = Decimal("0")

    for index, candidate in enumerate(exits):
        equity += candidate.realized_r
        if equity > peak:
            peak = equity
            peak_candidate = candidate
            peak_index = index

        drawdown = peak - equity
        if drawdown > max_dd:
            max_dd = drawdown
            max_peak = peak
            max_peak_candidate = peak_candidate
            max_peak_index = peak_index
            trough_candidate = candidate
            trough_index = index
            trough_equity = equity

    start_index = max_peak_index + 1
    episode = exits[start_index : trough_index + 1]
    if not episode:
        raise ValueError("maximum drawdown episode cannot be empty")

    return (
        max_peak,
        trough_equity,
        max_dd,
        max_peak_candidate,
        trough_candidate,
        episode,
    )


def _episode_row(
    *,
    policy: str,
    tie_policy: str,
    selected: tuple[CapitalizerExposureCandidate, ...],
) -> tuple[
    CapitalizerDrawdownEpisode,
    tuple[CapitalizerExposureCandidate, ...],
]:
    (
        peak,
        trough,
        drawdown,
        peak_candidate,
        trough_candidate,
        episode,
    ) = _max_drawdown_episode(selected)

    total = sum((item.realized_r for item in episode), Decimal("0"))
    return (
        CapitalizerDrawdownEpisode(
            policy=policy,
            tie_policy=tie_policy,
            peak_equity_r=str(peak),
            trough_equity_r=str(trough),
            drawdown_r=str(drawdown),
            peak_exit_at=(
                peak_candidate.exit_at.isoformat()
                if peak_candidate is not None
                else None
            ),
            trough_exit_at=trough_candidate.exit_at.isoformat(),
            trades_in_episode=len(episode),
            winning_trades=sum(item.realized_r > 0 for item in episode),
            losing_trades=sum(item.realized_r < 0 for item in episode),
            flat_trades=sum(item.realized_r == 0 for item in episode),
            episode_total_r=str(total),
            first_episode_exit_at=episode[0].exit_at.isoformat(),
        ),
        episode,
    )


def _contributions(
    *,
    policy: str,
    tie_policy: str,
    selected: tuple[CapitalizerExposureCandidate, ...],
    episode: tuple[CapitalizerExposureCandidate, ...],
) -> tuple[CapitalizerDrawdownContribution, ...]:
    ordinals = _ordinal_index(selected)
    grouped: dict[
        tuple[str, str, CapitalizerSide, int],
        list[CapitalizerExposureCandidate],
    ] = defaultdict(list)

    for candidate in episode:
        session = capitalizer_session_at(candidate.entry_at)
        if session is None:
            raise ValueError("drawdown candidate lost Capitalizer session")
        grouped[
            (
                session.value,
                candidate.symbol,
                candidate.side,
                ordinals[candidate],
            )
        ].append(candidate)

    return tuple(
        CapitalizerDrawdownContribution(
            policy=policy,
            tie_policy=tie_policy,
            session=session,
            symbol=symbol,
            side=side.value,
            ordinal=ordinal,
            trades=len(rows),
            total_r=str(sum((item.realized_r for item in rows), Decimal("0"))),
            mean_r=str(
                sum((item.realized_r for item in rows), Decimal("0"))
                / Decimal(len(rows))
            ),
            winners=sum(item.realized_r > 0 for item in rows),
            losers=sum(item.realized_r < 0 for item in rows),
        )
        for (session, symbol, side, ordinal), rows in sorted(
            grouped.items(),
            key=lambda entry: tuple(str(value) for value in entry[0]),
        )
    )


def _session_contributions(
    *,
    policy: str,
    tie_policy: str,
    episode: tuple[CapitalizerExposureCandidate, ...],
) -> tuple[CapitalizerDrawdownSessionContribution, ...]:
    grouped: dict[str, list[CapitalizerExposureCandidate]] = defaultdict(list)
    for candidate in episode:
        session = capitalizer_session_at(candidate.entry_at)
        if session is None:
            raise ValueError("drawdown candidate lost Capitalizer session")
        grouped[session.value].append(candidate)

    return tuple(
        CapitalizerDrawdownSessionContribution(
            policy=policy,
            tie_policy=tie_policy,
            session=session,
            trades=len(rows),
            total_r=str(sum((item.realized_r for item in rows), Decimal("0"))),
            winners=sum(item.realized_r > 0 for item in rows),
            losers=sum(item.realized_r < 0 for item in rows),
        )
        for session, rows in sorted(grouped.items())
    )


def build_routing_drawdown_forensics_report(
    root: Path,
) -> CapitalizerRoutingDrawdownForensicsReport:
    candidates = _load_candidates(root)
    episodes: list[CapitalizerDrawdownEpisode] = []
    cells: list[CapitalizerDrawdownContribution] = []
    session_cells: list[CapitalizerDrawdownSessionContribution] = []

    for tie_policy in ("SYMBOL_ASC", "SYMBOL_DESC"):
        for policy in POLICIES:
            selected, _ = _select(
                candidates,
                policy=policy,
                tie_policy=tie_policy,
            )
            episode_row, episode = _episode_row(
                policy=policy,
                tie_policy=tie_policy,
                selected=selected,
            )
            episodes.append(episode_row)
            cells.extend(
                _contributions(
                    policy=policy,
                    tie_policy=tie_policy,
                    selected=selected,
                    episode=episode,
                )
            )
            session_cells.extend(
                _session_contributions(
                    policy=policy,
                    tie_policy=tie_policy,
                    episode=episode,
                )
            )

    symbols = tuple(sorted({item.symbol for item in candidates}))
    return CapitalizerRoutingDrawdownForensicsReport(
        identity=IDENTITY,
        market_count=len(symbols),
        symbols=symbols,
        episodes=tuple(episodes),
        contribution_cells=tuple(cells),
        session_contributions=tuple(session_cells),
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Capitalizer residual realized drawdown attribution"
    )
    parser.add_argument("input_root", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    report = build_routing_drawdown_forensics_report(args.input_root)
    args.output.mkdir(parents=True, exist_ok=True)
    path = args.output / "capitalizer-routing-drawdown-forensics-v1.json"
    path.write_text(
        json.dumps(asdict(report), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(asdict(report), sort_keys=True))


if __name__ == "__main__":
    main()
