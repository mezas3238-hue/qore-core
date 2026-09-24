"""R2-BR AUDUSD cap-2 passive OCO laboratory.

R2-BM established CONF_RANGE_MID as a real passive-entry economic lever.
R2-BO showed that terminal rearm only raises density from 164.13 to 167.60
trades/year and does not improve edge.

R2-AI previously demonstrated material multi-hypothesis capacity. R2-BR tests
that lever causally without allowing multiple realised trades per parent.

Control:
- exact R2-BM primary hypothesis + CONF_RANGE_MID passive order.

CAP2_CONCURRENT_OCO:
- keep the exact primary hypothesis;
- while its passive order is still unresolved, allow at most one genuinely later
  independent Model #1 source event to activate a second CONF_RANGE_MID order;
- secondary must be structurally valid and known before primary resolution;
- both orders use their own source-candle stop and 30m passive horizon;
- earliest observed fill wins; same-M5 tie goes to the primary order;
- once one fills, the other is cancelled (OCO);
- maximum one realised trade per parent;
- no rescue after missing evidence or invalid primary geometry;
- same fixed 1.5R target, C3 expiry and BE_CLOSE_075 management as R2-BM.

Research only. No automatic promotion.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from datetime import datetime, timedelta
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
    MARKET,
    START,
    YEARS,
    _level,
    _valid_risk,
)
from qore.infrastructure.trader_lab.vt08_crt_pure_r2bm_audusd_passive_entry_economics import (
    COST_STRESS_R,
    PassiveTrade,
    _stress,
    _summary,
    _temporal,
)
from qore.infrastructure.trader_lab.vt08_crt_pure_r2bo_audusd_passive_rearm_density import (
    ARM,
    _attempt_selected,
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
    _candidate_pairs,
    select_competing_hypothesis,
)
from qore.infrastructure.trader_lab.vt08_crt_pure_window_evidence import load_m5_window

IDENTITY = "VT08_CRT_PURE_R2BR_AUDUSD_CAP2_PASSIVE_OCO_001"
SCHEMA = "qore.vt08.crt_pure.r2br_audusd_cap2_passive_oco.v1"
MAX_PENDING_HYPOTHESES = 2
MAX_REALISED_TRADES_PER_PARENT = 1


def _secondary_candidate(
    *,
    parent: ParentCrt,
    observations: tuple[SourceObservation, ...],
    c3_m15: tuple[M15Bar, ...],
    primary: tuple[SourceObservation, M15Bar, M15Bar],
    primary_resolved_at: datetime,
) -> tuple[SourceObservation, M15Bar, M15Bar] | None:
    primary_observation, _, primary_decision = primary
    primary_source = primary_observation.group.source_candle

    eligible: list[tuple[SourceObservation, M15Bar, M15Bar]] = []
    for candidate in _candidate_pairs(
        parent=parent,
        observations=observations,
        c3_m15=c3_m15,
    ):
        observation, confirmation, decision_bar = candidate
        source = observation.group.source_candle
        if source.opened_at == primary_source.opened_at:
            continue
        if source.closed_at <= primary_source.closed_at:
            continue
        if decision_bar.opened_at <= primary_decision.opened_at:
            continue
        if decision_bar.opened_at >= primary_resolved_at:
            continue

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
            continue
        eligible.append(candidate)

    if not eligible:
        return None
    return min(
        eligible,
        key=lambda item: (
            item[2].opened_at,
            item[0].group.source_candle.closed_at,
            item[0].group.source_candle.opened_at,
        ),
    )


def _entry_time(trade: PassiveTrade | None) -> datetime | None:
    if trade is None:
        return None
    return datetime.fromisoformat(trade.entry_opened_at)


def _choose_oco(
    *,
    primary_trade: PassiveTrade | None,
    secondary_trade: PassiveTrade | None,
) -> tuple[PassiveTrade | None, str]:
    primary_time = _entry_time(primary_trade)
    secondary_time = _entry_time(secondary_trade)
    if primary_time is None and secondary_time is None:
        return None, "NO_FILL"
    if secondary_time is None:
        return primary_trade, "PRIMARY"
    if primary_time is None:
        return secondary_trade, "SECONDARY"
    if primary_time <= secondary_time:
        return primary_trade, "PRIMARY"
    return secondary_trade, "SECONDARY"


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
    diagnostics: dict[str, int] = {}

    def bump(key: str) -> None:
        diagnostics[key] = diagnostics.get(key, 0) + 1

    for parent in parents:
        bump("parent_count")
        c3_m15 = _c3_m15(parent, m15_by_time)
        observations = _aligned_sources(
            parent=parent,
            c3_m15=c3_m15,
            breaches=breaches,
        )
        primary = select_competing_hypothesis(
            policy=BASE_POLICY,
            parent=parent,
            observations=observations,
            c3_m15=c3_m15,
        )
        if primary is None:
            bump("no_primary")
            continue

        primary_trade, primary_state, primary_resolved_at = _attempt_selected(
            parent=parent,
            selected=primary,
            m5_by_time=m5_by_time,
        )
        bump(f"primary_{primary_state}")

        if primary_trade is not None:
            cap1.append(primary_trade)
            bump("cap1_trade")

        if primary_state in {
            "INVALID_STRUCTURAL_RISK",
            "MISSING_M5",
            "LIFECYCLE_UNAVAILABLE",
        }:
            bump("cap2_fail_closed_primary_state")
            if primary_trade is not None:
                cap2.append(primary_trade)
            continue

        secondary = _secondary_candidate(
            parent=parent,
            observations=observations,
            c3_m15=c3_m15,
            primary=primary,
            primary_resolved_at=primary_resolved_at,
        )
        secondary_trade: PassiveTrade | None = None
        if secondary is None:
            bump("no_concurrent_secondary")
        else:
            bump("secondary_activated")
            secondary_trade, secondary_state, _ = _attempt_selected(
                parent=parent,
                selected=secondary,
                m5_by_time=m5_by_time,
            )
            bump(f"secondary_{secondary_state}")

        chosen, winner = _choose_oco(
            primary_trade=primary_trade,
            secondary_trade=secondary_trade,
        )
        bump(f"oco_{winner}")
        if chosen is not None:
            cap2.append(chosen)
            bump("cap2_trade")

    cap1_rows = tuple(sorted(cap1, key=lambda row: row.entry_opened_at))
    cap2_rows = tuple(sorted(cap2, key=lambda row: row.entry_opened_at))

    def variant(rows: tuple[PassiveTrade, ...]) -> dict[str, Any]:
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
        "entry_arm": ARM.value,
        "primary_competition_policy": BASE_POLICY.value,
        "secondary_policy": (
            "EARLIEST_STRUCTURALLY_VALID_LATER_SOURCE_ACTIVATED_"
            "BEFORE_PRIMARY_RESOLUTION"
        ),
        "max_pending_hypotheses": MAX_PENDING_HYPOTHESES,
        "max_realised_trades_per_parent": MAX_REALISED_TRADES_PER_PARENT,
        "oco_fill_priority": "EARLIEST_OBSERVED_FILL_PRIMARY_WINS_SAME_M5_TIE",
        "terminal_rearm_combined": False,
        "bj_selector_combined": False,
        "diagnostics": diagnostics,
        "CAP1_CONTROL": variant(cap1_rows),
        "CAP2_CONCURRENT_OCO": variant(cap2_rows),
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
        for variant_name, rows in (
            ("CAP1_CONTROL", cap1),
            ("CAP2_CONCURRENT_OCO", cap2),
        ):
            for trade in rows:
                row = asdict(trade)
                row["capacity_variant"] = variant_name
                handle.write(json.dumps(row, sort_keys=True) + "\n")
    print("CRT_R2BR_CAP2_OCO_JSON=" + json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    main()
