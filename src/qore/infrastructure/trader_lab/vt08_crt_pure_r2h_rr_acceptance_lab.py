"""R2-H projected reward/risk acceptance family for VT08 CRT PURE.

The methodology and R2-G competition model remain fixed. This lab changes one
engineering dimension only: the minimum projected reward/risk available from the
causal entry slot to the frozen C1 50% target, using the source-candle structural stop.

Base competition policy:
    NEWEST_SUPERSEDES_CONFIRMATION_FIRST

Threshold family is declared before replay outcomes:
    0.00, 0.50, 0.75, 1.00, 1.25, 1.50, 2.00 R

No threshold changes stop, target, confirmation, timing, or parent CRT semantics.
Research only. No demo/live/production/capital authority.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from dataclasses import asdict
from datetime import datetime
from decimal import Decimal
from hashlib import sha256
from pathlib import Path
from typing import Any

from qore.infrastructure.trader_lab.vt08_crt_pure_2y_replay import (
    END_EXCLUSIVE,
    FOLD_1_END,
    START,
    ReplayBar,
    _midpoint,
    load_two_year_m5,
)
from qore.infrastructure.trader_lab.vt08_crt_pure_r2_model1_reference_lab import (
    M15Bar,
    Model1LabTrade,
    ParentCrt,
    _resolve_trade,
    _summary,
    aggregate_complete_m15,
    build_parent_crts,
)
from qore.infrastructure.trader_lab.vt08_crt_pure_r2c_close_unmitigated_replay import (
    build_close_unmitigated_breach_groups,
)
from qore.infrastructure.trader_lab.vt08_crt_pure_r2e_source_multiplicity_census import (
    _aligned_sources,
    _c3_m15,
)
from qore.infrastructure.trader_lab.vt08_crt_pure_r2g_competition_lab import (
    CompetitionPolicy,
    select_competing_hypothesis,
)
from qore.infrastructure.traders.crt_pure_identity import CrtPureMarket
from qore.infrastructure.traders.crt_pure_methodology_candidate import (
    CrtPureCandidateDirection,
)

IDENTITY = "VT08_CRT_PURE_R2H_PROJECTED_RR_ACCEPTANCE_001"
SCHEMA = "qore.vt08.crt_pure.r2h_projected_rr_acceptance.v1"
BASE_POLICY = CompetitionPolicy.NEWEST_SUPERSEDES_CONFIRMATION_FIRST
RR_THRESHOLDS: tuple[Decimal, ...] = (
    Decimal("0.00"),
    Decimal("0.50"),
    Decimal("0.75"),
    Decimal("1.00"),
    Decimal("1.25"),
    Decimal("1.50"),
    Decimal("2.00"),
)
THRESHOLD_MANIFEST = "|".join(format(item, "f") for item in RR_THRESHOLDS)
THRESHOLD_DIGEST = sha256(THRESHOLD_MANIFEST.encode("utf-8")).hexdigest()


def projected_rr(
    *,
    parent: ParentCrt,
    source: M15Bar,
    entry: M15Bar,
) -> Decimal | None:
    target = _midpoint(parent.c1.high_price, parent.c1.low_price)
    entry_price = Decimal(entry.open_price)
    if parent.direction is CrtPureCandidateDirection.BULLISH:
        risk = entry_price - Decimal(source.low_price)
        reward = target - entry_price
    else:
        risk = Decimal(source.high_price) - entry_price
        reward = entry_price - target
    if risk <= 0 or reward <= 0:
        return None
    return reward / risk


def _retag(
    trade: Model1LabTrade,
    *,
    threshold: Decimal,
) -> Model1LabTrade:
    return Model1LabTrade(
        schema=SCHEMA,
        identity=f"{IDENTITY}:RR_GE_{format(threshold, 'f')}",
        market=trade.market,
        reference_policy=trade.reference_policy,
        reference_count=trade.reference_count,
        reference_ids=trade.reference_ids,
        parent_direction=trade.parent_direction,
        timing_triplet=trade.timing_triplet,
        c3_opened_at=trade.c3_opened_at,
        source_opened_at=trade.source_opened_at,
        confirmation_opened_at=trade.confirmation_opened_at,
        entry_opened_at=trade.entry_opened_at,
        entry_price_relative=trade.entry_price_relative,
        stop_price_relative=trade.stop_price_relative,
        target_price_relative=trade.target_price_relative,
        exit_price_relative=trade.exit_price_relative,
        exit_reason=trade.exit_reason,
        r_multiple=trade.r_multiple,
        research_only=True,
        promotion_forbidden_from_lab_pnl=True,
    )


def _fold(
    trades: tuple[Model1LabTrade, ...],
    start: datetime,
    end: datetime,
) -> tuple[Model1LabTrade, ...]:
    return tuple(
        trade
        for trade in trades
        if start <= datetime.fromisoformat(trade.entry_opened_at) < end
    )


def run_rr_family(
    market: CrtPureMarket,
    bars: tuple[ReplayBar, ...],
) -> tuple[dict[Decimal, tuple[Model1LabTrade, ...]], dict[str, Any]]:
    parents = build_parent_crts(market, bars)
    m15 = aggregate_complete_m15(bars)
    m15_by_time = {bar.opened_at: bar for bar in m15}
    breaches = build_close_unmitigated_breach_groups(m15)

    trades: dict[Decimal, list[Model1LabTrade]] = {
        threshold: [] for threshold in RR_THRESHOLDS
    }
    counters: dict[Decimal, Counter[str]] = {
        threshold: Counter() for threshold in RR_THRESHOLDS
    }

    for parent in parents:
        c3_m15 = _c3_m15(parent, m15_by_time)
        observations = _aligned_sources(
            parent=parent,
            c3_m15=c3_m15,
            breaches=breaches,
        )
        selected = select_competing_hypothesis(
            policy=BASE_POLICY,
            parent=parent,
            observations=observations,
            c3_m15=c3_m15,
        )
        for threshold in RR_THRESHOLDS:
            counter = counters[threshold]
            counter["parent_count"] += 1
            if selected is None:
                counter["no_selected_confirmed_hypothesis"] += 1
                continue

            observation, confirmation, entry = selected
            rr = projected_rr(
                parent=parent,
                source=observation.group.source_candle,
                entry=entry,
            )
            if rr is None:
                counter["invalid_projected_geometry"] += 1
                continue
            counter["valid_projected_geometry"] += 1
            if rr < threshold:
                counter["below_rr_threshold"] += 1
                continue
            counter["rr_threshold_pass"] += 1

            trade = _resolve_trade(
                parent=parent,
                group=observation.group,
                confirmation=confirmation,
                entry_bar=entry,
                c3_m15=c3_m15,
            )
            if trade is None:
                counter["resolve_trade_rejected"] += 1
                continue
            counter["trade_created"] += 1
            trades[threshold].append(_retag(trade, threshold=threshold))

    frozen = {
        threshold: tuple(sorted(rows, key=lambda item: item.entry_opened_at))
        for threshold, rows in trades.items()
    }
    arms: dict[str, Any] = {}
    for threshold in RR_THRESHOLDS:
        rows = frozen[threshold]
        key = f"RR_GE_{format(threshold, 'f')}"
        arms[key] = {
            "minimum_projected_rr": format(threshold, "f"),
            "diagnostics": dict(counters[threshold]),
            "full_2y": _summary(rows),
            "year_1": _summary(_fold(rows, START, FOLD_1_END)),
            "year_2": _summary(_fold(rows, FOLD_1_END, END_EXCLUSIVE)),
        }

    report: dict[str, Any] = {
        "schema": SCHEMA,
        "identity": IDENTITY,
        "market": market.value,
        "base_competition_policy": BASE_POLICY.value,
        "single_changed_dimension": "MINIMUM_PROJECTED_RR_TO_C1_MIDPOINT",
        "threshold_manifest": THRESHOLD_MANIFEST,
        "threshold_digest": THRESHOLD_DIGEST,
        "threshold_family_declared_before_outcomes": True,
        "thresholds": [format(item, "f") for item in RR_THRESHOLDS],
        "arms": arms,
        "automatic_winner_selection": False,
        "research_only": True,
        "candidate_certified": False,
        "demo_eligible": False,
        "live_authorized": False,
        "real_capital_authorized": False,
        "production_authorized": False,
    }
    return frozen, report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("market", choices=[item.value for item in CrtPureMarket])
    parser.add_argument("output", type=Path)
    args = parser.parse_args()

    market = CrtPureMarket(args.market)
    family, report = run_rr_family(market, load_two_year_m5(market))
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / "report.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n"
    )
    with (args.output / "trades.jsonl").open("w", encoding="utf-8") as handle:
        for threshold in RR_THRESHOLDS:
            for trade in family[threshold]:
                row = asdict(trade)
                row["minimum_projected_rr"] = format(threshold, "f")
                handle.write(json.dumps(row, sort_keys=True) + "\n")
    print("CRT_R2H_RR_ACCEPTANCE_JSON=" + json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    main()
