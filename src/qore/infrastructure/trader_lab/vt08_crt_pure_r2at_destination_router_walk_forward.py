"""R2-AT causal destination-router walk-forward for VT08 CRT PURE FX.

Frozen before outcomes.

The high-density rolling-H4 entry population is unchanged. No entry is filtered.
Each annual OOS fold selects one fixed target arm using only the immediately
preceding 3 years:

- FIXED_1R
- FIXED_1_5R
- FIXED_2R

Selection rule:
- sum training R for each arm over the same structurally-valid entry population;
- choose the arm with greatest aggregate training Total-R;
- deterministic tie-break by arm value;
- freeze that destination before evaluating the next OOS year.

This preserves 100% entry density while allowing Destination intelligence to
adapt causally to regime history.

Engineering characterization only; older untouched holdout remains required.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from qore.infrastructure.trader_lab.vt08_crt_pure_r2_model1_reference_lab import (
    Model1LabTrade,
    _summary,
    aggregate_complete_m15,
)
from qore.infrastructure.trader_lab.vt08_crt_pure_r2af_audusd_target_family import (
    TARGET_MULTIPLE,
    TargetArm,
    _resolve_fixed_target,
)
from qore.infrastructure.trader_lab.vt08_crt_pure_r2aq_high_density_historical_validation import (
    ValidationWindow,
    _rolling_parents,
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
from qore.infrastructure.trader_lab.vt08_crt_pure_window_evidence import load_m5_window
from qore.infrastructure.traders.crt_pure_identity import CrtPureMarket

IDENTITY = "VT08_CRT_PURE_R2AT_DESTINATION_ROUTER_WALK_FORWARD_001"
SCHEMA = "qore.vt08.crt_pure.r2at_destination_router_walk_forward.v1"
BASE_POLICY = CompetitionPolicy.NEWEST_SUPERSEDES_CONFIRMATION_FIRST
TRAINING_YEARS = 3
BASELINE_ARM = TargetArm.FIXED_1_5R
ARMS: tuple[TargetArm, ...] = (
    TargetArm.FIXED_1R,
    TargetArm.FIXED_1_5R,
    TargetArm.FIXED_2R,
)


@dataclass(frozen=True, slots=True)
class MarketPeriod:
    market: CrtPureMarket
    start: datetime
    end: datetime


PERIODS: dict[CrtPureMarket, MarketPeriod] = {
    CrtPureMarket.AUDUSD: MarketPeriod(
        market=CrtPureMarket.AUDUSD,
        start=datetime(2016, 9, 21, 0, 0, tzinfo=UTC),
        end=datetime(2026, 9, 21, 0, 0, tzinfo=UTC),
    ),
    CrtPureMarket.USDJPY: MarketPeriod(
        market=CrtPureMarket.USDJPY,
        start=datetime(2014, 9, 21, 0, 0, tzinfo=UTC),
        end=datetime(2026, 9, 21, 0, 0, tzinfo=UTC),
    ),
}


@dataclass(frozen=True, slots=True)
class DestinationRecord:
    entry_opened_at: str
    trades: tuple[tuple[str, Model1LabTrade], ...]

    def trade_for(self, arm: TargetArm) -> Model1LabTrade:
        mapping = dict(self.trades)
        return mapping[arm.value]


def _year_start(year: int) -> datetime:
    return datetime(year, 9, 21, 0, 0, tzinfo=UTC)


def _slice(
    records: tuple[DestinationRecord, ...],
    start: datetime,
    end: datetime,
) -> tuple[DestinationRecord, ...]:
    return tuple(
        record
        for record in records
        if start <= datetime.fromisoformat(record.entry_opened_at) < end
    )


def _arm_trades(
    records: tuple[DestinationRecord, ...],
    arm: TargetArm,
) -> tuple[Model1LabTrade, ...]:
    return tuple(record.trade_for(arm) for record in records)


def _select_arm(
    training: tuple[DestinationRecord, ...],
) -> tuple[TargetArm, dict[str, float]]:
    totals = {
        arm: round(
            sum(record.trade_for(arm).r_multiple for record in training),
            8,
        )
        for arm in ARMS
    }
    selected = sorted(
        ARMS,
        key=lambda arm: (-totals[arm], arm.value),
    )[0]
    return selected, {arm.value: totals[arm] for arm in ARMS}


def _build_records(market: CrtPureMarket) -> tuple[DestinationRecord, ...]:
    period = PERIODS[market]
    window = ValidationWindow(
        market=market,
        start=period.start,
        end=period.end,
    )
    bars = load_m5_window(
        market,
        start=period.start - timedelta(days=2),
        end_exclusive=period.end + timedelta(days=2),
    )
    parents = _rolling_parents(market=market, bars=bars, window=window)
    m15 = aggregate_complete_m15(bars)
    m15_by_time = {bar.opened_at: bar for bar in m15}
    breaches = build_close_unmitigated_breach_groups(m15)

    records: list[DestinationRecord] = []
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
        if selected is None:
            continue

        observation, confirmation, entry = selected
        arm_trades: list[tuple[str, Model1LabTrade]] = []
        for arm in ARMS:
            trade = _resolve_fixed_target(
                arm=arm,
                multiple=TARGET_MULTIPLE[arm],
                parent=parent,
                group=observation.group,
                confirmation=confirmation,
                entry_bar=entry,
                c3_m15=c3_m15,
            )
            if trade is None:
                arm_trades = []
                break
            arm_trades.append((arm.value, trade))

        if not arm_trades:
            continue
        records.append(
            DestinationRecord(
                entry_opened_at=entry.opened_at.isoformat(),
                trades=tuple(arm_trades),
            )
        )

    return tuple(sorted(records, key=lambda item: item.entry_opened_at))


def run_walk_forward(
    market: CrtPureMarket,
) -> tuple[tuple[DestinationRecord, ...], dict[str, Any]]:
    period = PERIODS[market]
    records = _build_records(market)
    baseline_oos: list[Model1LabTrade] = []
    routed_oos: list[Model1LabTrade] = []
    folds: list[dict[str, Any]] = []

    for oos_year in range(period.start.year + TRAINING_YEARS, period.end.year):
        training_start = _year_start(oos_year - TRAINING_YEARS)
        training_end = _year_start(oos_year)
        oos_start = _year_start(oos_year)
        oos_end = _year_start(oos_year + 1)

        training = _slice(records, training_start, training_end)
        oos = _slice(records, oos_start, oos_end)
        selected_arm, training_totals = _select_arm(training)

        baseline = _arm_trades(oos, BASELINE_ARM)
        routed = _arm_trades(oos, selected_arm)
        baseline_oos.extend(baseline)
        routed_oos.extend(routed)

        folds.append(
            {
                "training_start": training_start.isoformat(),
                "training_end_exclusive": training_end.isoformat(),
                "oos_start": oos_start.isoformat(),
                "oos_end_exclusive": oos_end.isoformat(),
                "training_trades": len(training),
                "training_total_r_by_arm": training_totals,
                "selected_destination": selected_arm.value,
                "oos_trades": len(oos),
                "oos_baseline": _summary(baseline),
                "oos_routed": _summary(routed),
            }
        )

    baseline_frozen = tuple(
        sorted(baseline_oos, key=lambda item: item.entry_opened_at)
    )
    routed_frozen = tuple(
        sorted(routed_oos, key=lambda item: item.entry_opened_at)
    )
    report: dict[str, Any] = {
        "schema": SCHEMA,
        "identity": IDENTITY,
        "market": market.value,
        "period_start": period.start.isoformat(),
        "period_end_exclusive": period.end.isoformat(),
        "training_years": TRAINING_YEARS,
        "candidate_destinations": [arm.value for arm in ARMS],
        "baseline_destination": BASELINE_ARM.value,
        "entry_population_identical_across_destinations": True,
        "selection_rule": "MAX_3Y_TRAINING_TOTAL_R_DETERMINISTIC_TIEBREAK",
        "folds": folds,
        "combined_oos_baseline": _summary(baseline_frozen),
        "combined_oos_routed": _summary(routed_frozen),
        "entry_density_retention": 1.0,
        "walk_forward_no_future_leakage": True,
        "final_untouched_certification_claim": False,
        "automatic_promotion": False,
        "research_only": True,
        "candidate_certified": False,
        "demo_eligible": False,
        "live_authorized": False,
        "real_capital_authorized": False,
        "production_authorized": False,
    }
    return records, report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("market", choices=[item.value for item in PERIODS])
    parser.add_argument("output", type=Path)
    args = parser.parse_args()

    market = CrtPureMarket(args.market)
    records, report = run_walk_forward(market)
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / "report.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n"
    )
    with (args.output / "records.jsonl").open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(
                json.dumps(asdict(record), sort_keys=True, default=str) + "\n"
            )
    print("CRT_R2AT_DESTINATION_JSON=" + json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    main()
