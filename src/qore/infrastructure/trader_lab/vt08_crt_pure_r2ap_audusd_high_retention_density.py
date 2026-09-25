"""R2-AP AUDUSD high-retention density candidate.

Frozen before combination outcomes.

Evidence lineage:
- R2-AJ proved ROLLING_H4 is the dominant density-capacity lever.
- R2-AL showed FIXED_2R is the strongest broad structural-target arm for AUDUSD.
- Independent R2-X 6Y single-bucket screening found MANIP_0_10_TO_0_25 as the
  only one-bucket exclusion that retained >=60% of the unfiltered midpoint
  population while leaving all three 2Y blocks positive.

R2-AP tests transfer of that already-identified toxic state onto a different
combination:
    ROLLING_H4 + FIXED_2R + reject MANIP_0_10_TO_0_25.

The combination is frozen before its PnL is observed.

Research only.
"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from dataclasses import asdict
from datetime import UTC, datetime, timedelta
from decimal import Decimal
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
from qore.infrastructure.trader_lab.vt08_crt_pure_r2aj_timing_lattice_density import (
    TimingLattice,
    _parents,
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
from qore.infrastructure.trader_lab.vt08_crt_pure_window_evidence import load_m5_window
from qore.infrastructure.traders.crt_pure_identity import CrtPureMarket

IDENTITY = "VT08_CRT_PURE_R2AP_AUDUSD_HIGH_RETENTION_DENSITY_001"
SCHEMA = "qore.vt08.crt_pure.r2ap_audusd_high_retention_density.v1"
MARKET = CrtPureMarket.AUDUSD
START = datetime(2020, 9, 21, 0, 0, tzinfo=UTC)
END = datetime(2026, 9, 21, 0, 0, tzinfo=UTC)
BASE_POLICY = CompetitionPolicy.NEWEST_SUPERSEDES_CONFIRMATION_FIRST
LATTICE = TimingLattice.ROLLING_H4
ARM = TargetArm.FIXED_2R
TARGET_MULTIPLE_2R = TARGET_MULTIPLE[ARM]
MANIP_LOW = Decimal("0.10")
MANIP_HIGH = Decimal("0.25")

YEAR_BOUNDARIES: tuple[datetime, ...] = tuple(
    datetime(year, 9, 21, 0, 0, tzinfo=UTC)
    for year in range(2020, 2027)
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


def _is_toxic_manipulation(context: tuple[Any, ...]) -> bool:
    manipulation = context[12]
    if not isinstance(manipulation, Decimal):
        raise TypeError("manipulation depth must be Decimal")
    return MANIP_LOW <= manipulation < MANIP_HIGH


def run_lab() -> tuple[
    tuple[Model1LabTrade, ...],
    tuple[Model1LabTrade, ...],
    dict[str, Any],
]:
    bars = load_m5_window(
        MARKET,
        start=START - timedelta(days=25),
        end_exclusive=END + timedelta(days=2),
    )
    parents = _parents(
        market=MARKET,
        bars=bars,
        lattice=LATTICE,
    )
    m15 = aggregate_complete_m15(bars)
    m15_by_time = {bar.opened_at: bar for bar in m15}
    times = tuple(bar.opened_at for bar in m15)
    breaches = build_close_unmitigated_breach_groups(m15)

    control: list[Model1LabTrade] = []
    candidate: list[Model1LabTrade] = []
    diagnostics: dict[str, int] = defaultdict(int)
    diagnostics["parent_count"] = len(parents)

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
            diagnostics["no_selected_hypothesis"] += 1
            continue

        observation, confirmation, entry = selected
        trade = _resolve_fixed_target(
            arm=ARM,
            multiple=TARGET_MULTIPLE_2R,
            parent=parent,
            group=observation.group,
            confirmation=confirmation,
            entry_bar=entry,
            c3_m15=c3_m15,
        )
        if trade is None:
            diagnostics["invalid_structural_geometry"] += 1
            continue

        diagnostics["control_trade_created"] += 1
        control.append(trade)

        context = _context(parent=parent, m15=m15, times=times)
        if context is None:
            diagnostics["candidate_insufficient_context"] += 1
            continue
        if _is_toxic_manipulation(context):
            diagnostics["candidate_toxic_manip_rejected"] += 1
            continue

        diagnostics["candidate_trade_created"] += 1
        candidate.append(trade)

    control_frozen = tuple(
        sorted(control, key=lambda item: item.entry_opened_at)
    )
    candidate_frozen = tuple(
        sorted(candidate, key=lambda item: item.entry_opened_at)
    )
    control_annual = _annual(control_frozen)
    candidate_annual = _annual(candidate_frozen)

    report: dict[str, Any] = {
        "schema": SCHEMA,
        "identity": IDENTITY,
        "market": MARKET.value,
        "window_start": START.isoformat(),
        "window_end_exclusive": END.isoformat(),
        "timing_lattice": LATTICE.value,
        "target_arm": ARM.value,
        "base_competition_policy": BASE_POLICY.value,
        "max_selected_hypotheses_per_parent": 1,
        "toxic_state_exclusion": {
            "dimension": "MANIPULATION_DEPTH_TO_C1",
            "lower_inclusive": str(MANIP_LOW),
            "upper_exclusive": str(MANIP_HIGH),
            "provenance": "R2-X_6Y_SINGLE_BUCKET_SCREEN",
        },
        "combination_frozen_before_outcomes": True,
        "diagnostics": dict(diagnostics),
        "control_rolling_fixed_2r": {
            "full_6y": _summary(control_frozen),
            "annual": control_annual,
            "trades_per_year": round(len(control_frozen) / 6, 8),
            "positive_annual_windows": sum(
                float(item["total_r"]) > 0 for item in control_annual.values()
            ),
        },
        "candidate": {
            "full_6y": _summary(candidate_frozen),
            "annual": candidate_annual,
            "trades_per_year": round(len(candidate_frozen) / 6, 8),
            "retention_vs_control": (
                None
                if not control_frozen
                else round(len(candidate_frozen) / len(control_frozen), 8)
            ),
            "positive_annual_windows": sum(
                float(item["total_r"]) > 0 for item in candidate_annual.values()
            ),
        },
        "automatic_promotion": False,
        "research_only": True,
        "candidate_certified": False,
        "demo_eligible": False,
        "live_authorized": False,
        "real_capital_authorized": False,
        "production_authorized": False,
    }
    return control_frozen, candidate_frozen, report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("output", type=Path)
    args = parser.parse_args()

    control, candidate, report = run_lab()
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / "report.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n"
    )
    with (args.output / "trades.jsonl").open("w", encoding="utf-8") as handle:
        for label, rows in (("CONTROL", control), ("CANDIDATE", candidate)):
            for trade in rows:
                row = asdict(trade)
                row["population"] = label
                handle.write(json.dumps(row, sort_keys=True) + "\n")
    print("CRT_R2AP_AUDUSD_DENSITY_JSON=" + json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    main()
