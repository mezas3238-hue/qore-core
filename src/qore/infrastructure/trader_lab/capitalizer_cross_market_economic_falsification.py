"""Cross-market economic falsification for QORE Capitalizer.

This module reuses the frozen nine-market consumed dataset and evaluates the same structural
logic already studied on USDJPY without tuning per market:

1. R0 gross characterization;
2. Structural V2 cognition;
3. Structural V2 + PROFITABLE_SWING_LOCK;
4. Structural V2 with only NO_RECLAIM_FRESH + CISD ANY_CROSS_H1 removed;
5. the same timing-filtered set + PROFITABLE_SWING_LOCK.

The H1 boundary remains the natural source-timeframe duration (60 minutes). No market-specific
threshold, target, stop, or parameter is optimized. This is consumed-development falsification,
not a candidate, holdout, certification, or promotion decision.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from pathlib import Path

from qore.infrastructure.trader_lab.capitalizer_atlas_m5_reader import iter_atlas_m5
from qore.infrastructure.trader_lab.capitalizer_cognitive_v2_development import (
    _root_state_index,
    select_development_trades,
)
from qore.infrastructure.trader_lab.capitalizer_departure_timing_forensics import (
    H1_DURATION_MINUTES,
    _load_timing_rows,
    _timing_state,
)
from qore.infrastructure.trader_lab.capitalizer_microstructure_discovery import (
    designated_session,
)
from qore.infrastructure.trader_lab.capitalizer_position_lifecycle_forensics import (
    CapitalizerLifecycleMode,
    _bar_indices,
    _simulate_trade,
    _state_family,
    _year,
)
from qore.infrastructure.trader_lab.capitalizer_r0_gross_characterization import (
    CapitalizerR0Metrics,
    CapitalizerR0Trade,
    build_r0_trades,
    summarize_r0,
)
from qore.infrastructure.trader_lab.capitalizer_r0_root_cause_forensics import (
    _departure_episode_index,
)

IDENTITY = "QORE_CAPITALIZER_CROSS_MARKET_ECONOMIC_FALSIFICATION_V1"


@dataclass(frozen=True, slots=True)
class CapitalizerCrossMarketVariant:
    name: str
    metrics: CapitalizerR0Metrics


@dataclass(frozen=True, slots=True)
class CapitalizerCrossMarketAnnual:
    name: str
    year: int
    metrics: CapitalizerR0Metrics


@dataclass(frozen=True, slots=True)
class CapitalizerCrossMarketEconomicReport:
    identity: str
    symbol: str
    session: str
    h1_duration_minutes: int
    timing_boundary_semantics: str
    timing_excluded_trades: int
    variants: tuple[CapitalizerCrossMarketVariant, ...]
    annual: tuple[CapitalizerCrossMarketAnnual, ...]
    evidence_status: str = "CONSUMED_RESEARCH_EVIDENCE"
    cross_market_falsification_only: bool = True
    market_specific_tuning_used: bool = False
    numeric_threshold_optimization_used: bool = False
    target_changed: bool = False
    stop_contract_changed: bool = False
    costs_applied: bool = False
    candidate_frozen: bool = False
    fresh_holdout_claimed: bool = False
    rule_selected: bool = False
    promotion_allowed: bool = False


def _remove_noreclaim_cisd_cross_h1(
    *,
    state_family: str,
    timing_state: str,
) -> bool:
    return (
        state_family == "NO_RECLAIM_FRESH"
        and timing_state == "ANY_CROSS_H1"
    )


def _metrics(trades: tuple[CapitalizerR0Trade, ...]) -> CapitalizerR0Metrics:
    if not trades:
        raise ValueError("cross-market economic variant cannot be empty")
    return summarize_r0(trades).metrics


def _profit_lock(
    trades: tuple[CapitalizerR0Trade, ...],
    *,
    m5_root: Path,
) -> tuple[CapitalizerR0Trade, ...]:
    bars = tuple(iter_atlas_m5(m5_root))
    by_open, _ = _bar_indices(bars)
    return tuple(
        _simulate_trade(
            trade,
            bars=bars,
            by_open=by_open,
            mode=CapitalizerLifecycleMode.PROFITABLE_SWING_LOCK,
        )
        for trade in trades
    )


def build_cross_market_economic_report(
    *,
    m5_root: Path,
    journey_root: Path,
    target_root: Path,
) -> CapitalizerCrossMarketEconomicReport:
    r0 = build_r0_trades(
        m5_root=m5_root,
        journey_root=journey_root,
        target_root=target_root,
    )
    if not r0:
        raise ValueError("cross-market falsification requires R0 trades")

    state_index = _root_state_index(
        m5_root=m5_root,
        journey_root=journey_root,
        trades=r0,
    )
    structural, _, _, _ = select_development_trades(
        trades=r0,
        state_index=state_index,
        block_late_acceptance_repeat=True,
        block_journey_conflict=True,
        apply_session_ceiling=False,
    )
    if not structural:
        raise ValueError("Structural V2 cannot be empty")

    episode_index = _departure_episode_index(journey_root)
    timing = _load_timing_rows(journey_root)
    timing_selected = tuple(
        trade
        for trade in structural
        if not _remove_noreclaim_cisd_cross_h1(
            state_family=_state_family(trade, state_index),
            timing_state=_timing_state(
                trade,
                dimension="cisd",
                episode_index=episode_index,
                timing=timing,
            ),
        )
    )
    if not timing_selected:
        raise ValueError("timing falsification cannot remove all trades")

    structural_locked = _profit_lock(structural, m5_root=m5_root)
    timing_locked = _profit_lock(timing_selected, m5_root=m5_root)

    variant_trades: tuple[tuple[str, tuple[CapitalizerR0Trade, ...]], ...] = (
        ("R0_GROSS", r0),
        ("STRUCTURAL_V2", structural),
        ("STRUCTURAL_V2_PROFITABLE_SWING_LOCK", structural_locked),
        ("DROP_NORECLAIM_CISD_CROSS_H1", timing_selected),
        (
            "DROP_NORECLAIM_CISD_CROSS_H1_PROFITABLE_SWING_LOCK",
            timing_locked,
        ),
    )

    variants = tuple(
        CapitalizerCrossMarketVariant(name=name, metrics=_metrics(trades))
        for name, trades in variant_trades
    )

    annual: list[CapitalizerCrossMarketAnnual] = []
    for name, trades in variant_trades:
        years = sorted({_year(trade) for trade in trades})
        for year in years:
            subset = tuple(trade for trade in trades if _year(trade) == year)
            if subset:
                annual.append(
                    CapitalizerCrossMarketAnnual(
                        name=name,
                        year=year,
                        metrics=_metrics(subset),
                    )
                )

    symbol = r0[0].symbol
    return CapitalizerCrossMarketEconomicReport(
        identity=IDENTITY,
        symbol=symbol,
        session=designated_session(symbol).value,
        h1_duration_minutes=H1_DURATION_MINUTES,
        timing_boundary_semantics="SOURCE_TIMEFRAME_DURATION",
        timing_excluded_trades=len(structural) - len(timing_selected),
        variants=variants,
        annual=tuple(annual),
    )


def write_cross_market_economic_report(
    report: CapitalizerCrossMarketEconomicReport,
    output: Path,
) -> None:
    output.mkdir(parents=True, exist_ok=True)
    path = output / f"capitalizer-{report.symbol.lower()}-cross-market-economic-v1.json"
    path.write_text(
        json.dumps(asdict(report), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Capitalizer nine-market economic falsification cell"
    )
    parser.add_argument("m5_root", type=Path)
    parser.add_argument("journey_root", type=Path)
    parser.add_argument("target_root", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    report = build_cross_market_economic_report(
        m5_root=args.m5_root,
        journey_root=args.journey_root,
        target_root=args.target_root,
    )
    write_cross_market_economic_report(report, args.output)
    print(
        json.dumps(
            {
                "identity": report.identity,
                "symbol": report.symbol,
                "session": report.session,
                "timing_excluded_trades": report.timing_excluded_trades,
                "variants": {
                    row.name: asdict(row.metrics)
                    for row in report.variants
                },
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
