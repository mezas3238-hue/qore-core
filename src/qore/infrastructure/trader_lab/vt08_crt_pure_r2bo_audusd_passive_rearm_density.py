"""R2-BO AUDUSD passive-entry density restoration.

R2-BM established CONF_RANGE_MID as the strongest passive entry arm, but density
fell to 164.13 trades/year. This lab tests a causal density-restoration mechanism
without combining with the R2-BJ suitability selector.

The first hypothesis follows the frozen
NEWEST_SUPERSEDES_CONFIRMATION_FIRST policy. If its CONF_RANGE_MID passive order
does not fill within 30 minutes, or is invalidated by the original structural
stop before fill, the first attempt is terminal. A second attempt is allowed only
from a genuinely later source event that becomes known after that first passive
attempt resolves. The same competition policy is then applied to that later
source population.

Invariants:
- maximum two passive attempts per parent;
- maximum one realised trade per parent;
- no second attempt after a fill;
- no fallback after invalid structural geometry or missing M5 evidence;
- second attempt requires a new source event after first-attempt resolution;
- same CONF_RANGE_MID entry, structural stop, fixed 1.5R target, C3 expiry and
  BE_CLOSE_075 management as R2-BM.

Research only. No automatic promotion.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from dataclasses import asdict
from datetime import timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any

from qore.infrastructure.trader_lab.vt08_crt_pure_r2_model1_reference_lab import (
    M15Bar,
    ParentCrt,
    aggregate_complete_m15,
)
from qore.infrastructure.trader_lab.vt08_crt_pure_r2aq_high_density_historical_validation import (
    ValidationWindow,
    _rolling_parents,
)
from qore.infrastructure.trader_lab.vt08_crt_pure_r2bk_audusd_passive_entry_capacity import (
    BASE_POLICY,
    END,
    HORIZON,
    MARKET,
    START,
    YEARS,
    EntryArm,
    _level,
    _valid_risk,
)
from qore.infrastructure.trader_lab.vt08_crt_pure_r2bm_audusd_passive_entry_economics import (
    COST_STRESS_R,
    PassiveTrade,
    _simulate,
    _stress,
    _summary,
    _temporal,
)
from qore.infrastructure.trader_lab.vt08_crt_pure_r2c_close_unmitigated_replay import (
    build_close_unmitigated_breach_groups,
)
from qore.infrastructure.trader_lab.vt08_crt_pure_r2e_source_multiplicity_census import (
    SourceObservation,
    _aligned_sources,
    _c3_m15,
)
from qore.infrastructure.trader_lab.vt08_crt_pure_r2g_competition_lab import (
    select_competing_hypothesis,
)
from qore.infrastructure.trader_lab.vt08_crt_pure_window_evidence import load_m5_window
from qore.infrastructure.traders.crt_pure_methodology_candidate import (
    CrtPureCandidateDirection,
)

IDENTITY = "VT08_CRT_PURE_R2BO_AUDUSD_PASSIVE_REARM_DENSITY_001"
SCHEMA = "qore.vt08.crt_pure.r2bo_audusd_passive_rearm_density.v1"
ARM = EntryArm.CONF_RANGE_MID
MAX_ATTEMPTS_PER_PARENT = 2


def _stop_touched(
    *,
    bullish: bool,
    stop: Decimal,
    bar: Any,
) -> bool:
    if bullish:
        return Decimal(bar.low_price) <= stop
    return Decimal(bar.high_price) >= stop


def _attempt_fill(
    *,
    level: Decimal,
    stop: Decimal,
    bullish: bool,
    decision_at: Any,
    c3_closed_at: Any,
    m5_by_time: dict[Any, Any],
) -> tuple[Any | None, str, Any]:
    end = min(decision_at + HORIZON, c3_closed_at)
    cursor = decision_at
    while cursor < end:
        bar = m5_by_time.get(cursor)
        if bar is None:
            return None, "MISSING_M5", cursor
        level_touched = Decimal(bar.low_price) <= level <= Decimal(bar.high_price)
        stop_touched = _stop_touched(
            bullish=bullish,
            stop=stop,
            bar=bar,
        )
        if level_touched:
            return (
                cursor,
                "FILL_AND_STOP_SAME_M5" if stop_touched else "FILL",
                cursor,
            )
        if stop_touched:
            return (
                None,
                "STOP_INVALIDATED_BEFORE_FILL",
                cursor + timedelta(minutes=5),
            )
        cursor += timedelta(minutes=5)
    return None, "NO_FILL_WITHIN_30M", end


def _later_observations(
    observations: tuple[SourceObservation, ...],
    *,
    resolved_at: Any,
) -> tuple[SourceObservation, ...]:
    return tuple(
        observation
        for observation in observations
        if observation.group.source_candle.closed_at > resolved_at
    )


def _retag_reference_count(
    trade: PassiveTrade,
    *,
    reference_count: int,
) -> PassiveTrade:
    return PassiveTrade(
        **{
            **asdict(trade),
            "reference_count": reference_count,
        }
    )


def _attempt_selected(
    *,
    parent: ParentCrt,
    selected: tuple[SourceObservation, M15Bar, M15Bar],
    m5_by_time: dict[Any, Any],
) -> tuple[PassiveTrade | None, str, Any]:
    observation, confirmation, decision_bar = selected
    source = observation.group.source_candle
    level = _level(
        arm=ARM,
        source=source,
        confirmation=confirmation,
        entry_bar=decision_bar,
    )
    if not _valid_risk(
        parent=parent,
        source=source,
        entry=level,
    ):
        return None, "INVALID_STRUCTURAL_RISK", decision_bar.opened_at

    bullish = parent.direction is CrtPureCandidateDirection.BULLISH
    stop = Decimal(
        source.low_price if bullish else source.high_price
    )
    fill_at, state, resolved_at = _attempt_fill(
        level=level,
        stop=stop,
        bullish=bullish,
        decision_at=decision_bar.opened_at,
        c3_closed_at=parent.c3_closed_at,
        m5_by_time=m5_by_time,
    )
    if fill_at is None:
        return None, state, resolved_at

    trade = _simulate(
        arm=ARM,
        parent=parent,
        source=source,
        confirmation=confirmation,
        decision_bar=decision_bar,
        fill_at=fill_at,
        level=level,
        m5_by_time=m5_by_time,
    )
    if trade is None:
        return None, "LIFECYCLE_UNAVAILABLE", resolved_at
    return (
        _retag_reference_count(
            trade,
            reference_count=len(observation.group.references),
        ),
        state,
        resolved_at,
    )


def run_lab() -> tuple[
    tuple[PassiveTrade, ...],
    tuple[PassiveTrade, ...],
    dict[str, Any],
]:
    window = ValidationWindow(market=MARKET, start=START, end=END)
    bars = load_m5_window(
        MARKET,
        start=START - timedelta(days=2),
        end_exclusive=END + timedelta(days=1),
    )
    m5_by_time = {bar.opened_at: bar for bar in bars}
    parents = _rolling_parents(
        market=MARKET,
        bars=bars,
        window=window,
    )
    m15 = aggregate_complete_m15(bars)
    m15_by_time = {bar.opened_at: bar for bar in m15}
    breaches = build_close_unmitigated_breach_groups(m15)

    cap1: list[PassiveTrade] = []
    cap2: list[PassiveTrade] = []
    diagnostics: Counter[str] = Counter()

    for parent in parents:
        diagnostics["parent_count"] += 1
        c3_m15 = _c3_m15(parent, m15_by_time)
        observations = _aligned_sources(
            parent=parent,
            c3_m15=c3_m15,
            breaches=breaches,
        )
        first = select_competing_hypothesis(
            policy=BASE_POLICY,
            parent=parent,
            observations=observations,
            c3_m15=c3_m15,
        )
        if first is None:
            diagnostics["no_first_selected_hypothesis"] += 1
            continue

        first_trade, first_state, resolved_at = _attempt_selected(
            parent=parent,
            selected=first,
            m5_by_time=m5_by_time,
        )
        diagnostics[f"first_{first_state}"] += 1
        if first_trade is not None:
            cap1.append(first_trade)
            cap2.append(first_trade)
            diagnostics["cap1_trade"] += 1
            diagnostics["cap2_trade_from_first"] += 1
            continue

        if first_state not in {
            "NO_FILL_WITHIN_30M",
            "STOP_INVALIDATED_BEFORE_FILL",
        }:
            diagnostics["rearm_forbidden_after_first_state"] += 1
            continue

        later = _later_observations(
            observations,
            resolved_at=resolved_at,
        )
        if not later:
            diagnostics["no_later_source_after_resolution"] += 1
            continue

        second = select_competing_hypothesis(
            policy=BASE_POLICY,
            parent=parent,
            observations=later,
            c3_m15=c3_m15,
        )
        if second is None:
            diagnostics["no_second_selected_hypothesis"] += 1
            continue

        diagnostics["second_attempt"] += 1
        second_trade, second_state, _ = _attempt_selected(
            parent=parent,
            selected=second,
            m5_by_time=m5_by_time,
        )
        diagnostics[f"second_{second_state}"] += 1
        if second_trade is not None:
            cap2.append(second_trade)
            diagnostics["cap2_trade_from_second"] += 1

    cap1_rows = tuple(sorted(cap1, key=lambda row: row.entry_opened_at))
    cap2_rows = tuple(sorted(cap2, key=lambda row: row.entry_opened_at))

    def report_variant(rows: tuple[PassiveTrade, ...]) -> dict[str, Any]:
        return {
            "economics": _summary(rows),
            "trades_per_year": round(len(rows) / YEARS, 8),
            "temporal": _temporal(rows),
            "cost_stress": {
                f"COST_{cost:.2f}R": _stress(rows, cost)
                for cost in COST_STRESS_R
            },
        }

    report: dict[str, Any] = {
        "schema": SCHEMA,
        "identity": IDENTITY,
        "market": MARKET.value,
        "window_start": START.isoformat(),
        "window_end_exclusive": END.isoformat(),
        "years": YEARS,
        "entry_arm_frozen_from_r2bm": ARM.value,
        "base_competition_policy": BASE_POLICY.value,
        "max_attempts_per_parent": MAX_ATTEMPTS_PER_PARENT,
        "max_realised_trades_per_parent": 1,
        "second_attempt_requires_first_terminal_no_fill": True,
        "second_attempt_requires_new_source_after_resolution": True,
        "fallback_after_invalid_geometry": False,
        "fallback_after_missing_m5": False,
        "bj_selector_combined": False,
        "diagnostics": dict(diagnostics),
        "CAP1_CONTROL": report_variant(cap1_rows),
        "CAP2_CAUSAL_REARM": report_variant(cap2_rows),
        "automatic_promotion": False,
        "research_only": True,
        "candidate_certified": False,
        "demo_eligible": False,
        "live_authorized": False,
        "real_capital_authorized": False,
        "production_authorized": False,
    }
    return cap1_rows, cap2_rows, report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("output", type=Path)
    args = parser.parse_args()

    cap1, cap2, report = run_lab()
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / "report.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n"
    )
    with (args.output / "trades.jsonl").open("w", encoding="utf-8") as handle:
        for variant, rows in (("CAP1_CONTROL", cap1), ("CAP2_CAUSAL_REARM", cap2)):
            for trade in rows:
                row = asdict(trade)
                row["density_variant"] = variant
                handle.write(json.dumps(row, sort_keys=True) + "\n")
    print("CRT_R2BO_PASSIVE_REARM_JSON=" + json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    main()
