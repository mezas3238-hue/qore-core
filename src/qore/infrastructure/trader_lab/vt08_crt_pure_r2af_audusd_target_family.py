"""R2-AF AUDUSD target-family laboratory.

The entry population is frozen:
- AUDUSD;
- EFF1D 0.10 <= efficiency < 0.20;
- R2-G NEWEST_SUPERSEDES_CONFIRMATION_FIRST;
- current source structural stop;
- current midpoint geometry must be valid before any arm is evaluated.

Only the target changes.

Frozen arms:
- C1 midpoint control;
- fixed 1.0R;
- fixed 1.5R;
- fixed 2.0R.

All arms keep C3-close expiry and STOP_FIRST precedence. A fixed-R arm cannot
rescue an entry rejected by the current midpoint geometry; this keeps target as
the single changed dimension.

Development window: consumed 2016-2026 evidence.
No winner is selected automatically.
"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from dataclasses import asdict
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from enum import StrEnum
from pathlib import Path
from typing import Any

from qore.infrastructure.trader_lab.vt08_crt_pure_r2_model1_reference_lab import (
    BreachGroup,
    M15Bar,
    Model1LabTrade,
    ParentCrt,
    _resolve_trade,
    _summary,
    aggregate_complete_m15,
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
from qore.infrastructure.trader_lab.vt08_crt_pure_r2q_usdjpy_multi_regime_atlas import (
    _context,
)
from qore.infrastructure.trader_lab.vt08_crt_pure_window_evidence import (
    build_parent_crts_for_window,
    load_m5_window,
)
from qore.infrastructure.traders.crt_pure_identity import CrtPureMarket
from qore.infrastructure.traders.crt_pure_methodology_candidate import (
    CrtPureCandidateDirection,
)

IDENTITY = "VT08_CRT_PURE_R2AF_AUDUSD_TARGET_FAMILY_001"
SCHEMA = "qore.vt08.crt_pure.r2af_audusd_target_family.v1"
MARKET = CrtPureMarket.AUDUSD
BASE_POLICY = CompetitionPolicy.NEWEST_SUPERSEDES_CONFIRMATION_FIRST

START = datetime(2016, 9, 21, 0, 0, tzinfo=UTC)
END = datetime(2026, 9, 21, 0, 0, tzinfo=UTC)
FETCH_START = START - timedelta(days=25)
YEAR_BOUNDARIES: tuple[datetime, ...] = tuple(
    datetime(year, 9, 21, 0, 0, tzinfo=UTC)
    for year in range(2016, 2027)
)

EFF1_LOW = Decimal("0.10")
EFF1_HIGH = Decimal("0.20")


class TargetArm(StrEnum):
    MIDPOINT_CONTROL = "MIDPOINT_CONTROL"
    FIXED_1R = "FIXED_1R"
    FIXED_1_5R = "FIXED_1_5R"
    FIXED_2R = "FIXED_2R"


TARGET_MULTIPLE: dict[TargetArm, Decimal] = {
    TargetArm.FIXED_1R: Decimal("1.0"),
    TargetArm.FIXED_1_5R: Decimal("1.5"),
    TargetArm.FIXED_2R: Decimal("2.0"),
}
ARMS: tuple[TargetArm, ...] = (
    TargetArm.MIDPOINT_CONTROL,
    TargetArm.FIXED_1R,
    TargetArm.FIXED_1_5R,
    TargetArm.FIXED_2R,
)


def _resolve_fixed_target(
    *,
    arm: TargetArm,
    multiple: Decimal,
    parent: ParentCrt,
    group: BreachGroup,
    confirmation: M15Bar,
    entry_bar: M15Bar,
    c3_m15: tuple[M15Bar, ...],
) -> Model1LabTrade | None:
    entry = entry_bar.open_price
    direction = parent.direction
    if direction is CrtPureCandidateDirection.BULLISH:
        stop = group.source_candle.low_price
        if stop >= entry:
            return None
        risk = entry - stop
        target = Decimal(entry) + multiple * Decimal(risk)
    else:
        stop = group.source_candle.high_price
        if stop <= entry:
            return None
        risk = stop - entry
        target = Decimal(entry) - multiple * Decimal(risk)

    exit_reason = "C3_CLOSE"
    exit_price = Decimal(c3_m15[-1].close_price)
    r_value: Decimal | None = None

    for bar in c3_m15:
        if bar.opened_at < entry_bar.opened_at:
            continue
        if direction is CrtPureCandidateDirection.BULLISH:
            stop_hit = bar.low_price <= stop
            target_hit = Decimal(bar.high_price) >= target
        else:
            stop_hit = bar.high_price >= stop
            target_hit = Decimal(bar.low_price) <= target

        if stop_hit:
            exit_reason = "STOP"
            exit_price = Decimal(stop)
            r_value = Decimal("-1")
            break
        if target_hit:
            exit_reason = f"TARGET_{arm.value}"
            exit_price = target
            r_value = multiple
            break

    if r_value is None:
        r_value = (
            (exit_price - Decimal(entry)) / Decimal(risk)
            if direction is CrtPureCandidateDirection.BULLISH
            else (Decimal(entry) - exit_price) / Decimal(risk)
        )

    return Model1LabTrade(
        schema=SCHEMA,
        identity=f"{IDENTITY}:{arm.value}",
        market=parent.market.value,
        reference_policy=group.policy.name,
        reference_count=len(group.references),
        reference_ids=tuple(item.evidence_id for item in group.references),
        parent_direction=direction.value,
        timing_triplet=parent.triplet,
        c3_opened_at=parent.c3_opened_at.isoformat(),
        source_opened_at=group.source_candle.opened_at.isoformat(),
        confirmation_opened_at=confirmation.opened_at.isoformat(),
        entry_opened_at=entry_bar.opened_at.isoformat(),
        entry_price_relative=entry,
        stop_price_relative=stop,
        target_price_relative=str(target),
        exit_price_relative=str(exit_price),
        exit_reason=exit_reason,
        r_multiple=round(float(r_value), 8),
    )


def _retag_control(trade: Model1LabTrade) -> Model1LabTrade:
    return Model1LabTrade(
        schema=SCHEMA,
        identity=f"{IDENTITY}:{TargetArm.MIDPOINT_CONTROL.value}",
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
    )


def _window(
    rows: tuple[Model1LabTrade, ...],
    start: datetime,
    end: datetime,
) -> tuple[Model1LabTrade, ...]:
    return tuple(
        row
        for row in rows
        if start <= datetime.fromisoformat(row.entry_opened_at) < end
    )


def _annual(rows: tuple[Model1LabTrade, ...]) -> dict[str, dict[str, Any]]:
    return {
        f"{left.year}_{right.year}": _summary(_window(rows, left, right))
        for left, right in zip(
            YEAR_BOUNDARIES[:-1],
            YEAR_BOUNDARIES[1:],
            strict=True,
        )
    }


def run_lab() -> tuple[dict[TargetArm, tuple[Model1LabTrade, ...]], dict[str, Any]]:
    bars = load_m5_window(MARKET, start=FETCH_START, end_exclusive=END)
    parents = build_parent_crts_for_window(
        MARKET,
        bars,
        start=START,
        end_exclusive=END,
    )
    m15 = aggregate_complete_m15(bars)
    m15_by_time = {bar.opened_at: bar for bar in m15}
    times = tuple(bar.opened_at for bar in m15)
    breaches = build_close_unmitigated_breach_groups(m15)

    rows: dict[TargetArm, list[Model1LabTrade]] = {
        arm: [] for arm in ARMS
    }
    diagnostics: dict[str, int] = defaultdict(int)

    for parent in parents:
        diagnostics["parent_count"] += 1
        context = _context(parent=parent, m15=m15, times=times)
        if context is None:
            diagnostics["insufficient_context"] += 1
            continue
        if not EFF1_LOW <= context[2] < EFF1_HIGH:
            diagnostics["outside_frozen_eff1_regime"] += 1
            continue

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
            diagnostics["no_selected_hypothesis"] += 1
            continue

        observation, confirmation, entry = selected
        control = _resolve_trade(
            parent=parent,
            group=observation.group,
            confirmation=confirmation,
            entry_bar=entry,
            c3_m15=c3_m15,
        )
        if control is None:
            diagnostics["midpoint_geometry_rejected"] += 1
            continue

        rows[TargetArm.MIDPOINT_CONTROL].append(_retag_control(control))
        for arm, multiple in TARGET_MULTIPLE.items():
            trade = _resolve_fixed_target(
                arm=arm,
                multiple=multiple,
                parent=parent,
                group=observation.group,
                confirmation=confirmation,
                entry_bar=entry,
                c3_m15=c3_m15,
            )
            if trade is None:
                raise RuntimeError(
                    "fixed target rejected a midpoint-eligible structural risk"
                )
            rows[arm].append(trade)
        diagnostics["entry_population_created"] += 1

    frozen = {
        arm: tuple(sorted(trades, key=lambda item: item.entry_opened_at))
        for arm, trades in rows.items()
    }
    arms: dict[str, Any] = {}
    annual_stable: list[str] = []
    for arm in ARMS:
        trades = frozen[arm]
        annual = _annual(trades)
        all_positive = all(float(item["total_r"]) > 0 for item in annual.values())
        if all_positive:
            annual_stable.append(arm.value)
        arms[arm.value] = {
            "full_10y": _summary(trades),
            "annual": annual,
            "all_annual_windows_positive": all_positive,
        }

    report: dict[str, Any] = {
        "schema": SCHEMA,
        "identity": IDENTITY,
        "market": MARKET.value,
        "window_start": START.isoformat(),
        "window_end_exclusive": END.isoformat(),
        "base_competition_policy": BASE_POLICY.value,
        "frozen_eff1_bounds": [str(EFF1_LOW), str(EFF1_HIGH)],
        "single_changed_dimension": "TARGET_DESTINATION",
        "same_entry_population_all_arms": True,
        "same_stop_all_arms": True,
        "same_expiry_all_arms": True,
        "stop_first_all_arms": True,
        "arms_frozen_before_results": [arm.value for arm in ARMS],
        "diagnostics": dict(diagnostics),
        "arms": arms,
        "annual_stable_arms": annual_stable,
        "automatic_winner_ranking": False,
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
    parser.add_argument("output", type=Path)
    args = parser.parse_args()

    arms, report = run_lab()
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / "report.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n"
    )
    with (args.output / "trades.jsonl").open("w", encoding="utf-8") as handle:
        for arm in ARMS:
            for trade in arms[arm]:
                row = asdict(trade)
                row["target_arm"] = arm.value
                handle.write(json.dumps(row, sort_keys=True) + "\n")
    print("CRT_R2AF_AUDUSD_TARGET_JSON=" + json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    main()
