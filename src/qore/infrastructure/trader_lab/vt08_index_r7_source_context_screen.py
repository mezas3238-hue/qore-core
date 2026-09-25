"""VT08 Index R7 — bounded source-context corrective screen.

R7 consumes the failed R6 5Y validation as DEVELOPMENT evidence. It does not
claim freshness. The screen is intentionally small and causal: it tests whether
the previously observed source-context clue (previous completed source-day body
opposed to the current side) can qualify only the cohorts that R6 forensics
identified as structurally weak.

Rearm trades are preserved unconditionally because R6 5Y forensics showed
positive expectancy for that structurally distinct event family.

No post-entry or outcome-derived feature is used for admission.
"""

from __future__ import annotations

import argparse
import itertools
import json
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

from qore.infrastructure.trader_lab import vt08_index_cibo_2y_management_round5 as r5
from qore.infrastructure.trader_lab import vt08_index_r6_5y_failure_forensics as fx
from qore.infrastructure.trader_lab import vt08_index_r6_five_year_validation as v5y
from qore.infrastructure.trader_lab import vt08_index_r6_governed_candidate_freeze as freeze
from qore.infrastructure.trader_lab import vt08_index_v4_regime_forensics as v4
from qore.infrastructure.trader_lab import vt08_index_v7_ttrades_source_corrected as v7
from qore.infrastructure.traders.contracts import DemoTradingSetupSide
from qore.infrastructure.traders.vt08_index_c2_positional_r1 import Vt08IndexC2R1Bar

SCHEMA = "qore.trader_lab.vt08_index_r7_source_context_screen.v1"
IDENTITY = "VT08_INDEX_R7_SOURCE_CONTEXT_SCREEN_001"
MIN_TRADES = 1500
MAX_TRADES = 1600
PRIMARY_STRESS = Decimal("0.05")
SECONDARY_STRESS = Decimal("0.10")
RAW_PF_MIN = Decimal("1.10")
GOVERNED_PF_MIN = Decimal("1.50")
GOVERNED_DD_MAX = Decimal("6")
SECONDARY_PF_MIN = Decimal("1.30")
SECONDARY_DD_MAX = Decimal("8")


@dataclass(frozen=True, slots=True)
class Screen:
    short_initial_requires_opposed: bool
    anchor6_initial_requires_opposed: bool
    anchor22_initial_requires_opposed: bool
    cisd_initial_requires_opposed: bool
    c2_expansion_initial_requires_opposed: bool

    @property
    def screen_id(self) -> str:
        bits = (
            int(self.short_initial_requires_opposed),
            int(self.anchor6_initial_requires_opposed),
            int(self.anchor22_initial_requires_opposed),
            int(self.cisd_initial_requires_opposed),
            int(self.c2_expansion_initial_requires_opposed),
        )
        return "R7S-" + "".join(str(bit) for bit in bits)

    def payload(self) -> dict[str, Any]:
        return {
            "screen_id": self.screen_id,
            "short_initial_requires_opposed": self.short_initial_requires_opposed,
            "anchor6_initial_requires_opposed": self.anchor6_initial_requires_opposed,
            "anchor22_initial_requires_opposed": self.anchor22_initial_requires_opposed,
            "cisd_initial_requires_opposed": self.cisd_initial_requires_opposed,
            "c2_expansion_initial_requires_opposed": (
                self.c2_expansion_initial_requires_opposed
            ),
        }


@dataclass(frozen=True, slots=True)
class Feature:
    previous_source_day_body_opposed: bool


def _screens() -> tuple[Screen, ...]:
    return tuple(
        Screen(*bits)
        for bits in itertools.product((False, True), repeat=5)
        if any(bits)
    )


def _feature(
    admission: fx.Admission,
    *,
    indexed: dict[datetime, Vt08IndexC2R1Bar],
) -> Feature:
    signal = admission.signal
    source_days = v7._latest_complete_source_days(
        indexed,
        before_local=signal.h4_opened_at.astimezone(v5y._NY),
    )
    if source_days is None:
        return Feature(previous_source_day_body_opposed=False)
    previous_day, _current_day = source_days
    return Feature(
        previous_source_day_body_opposed=(
            v4._body_aligned(previous_day, signal.side) is False
        )
    )


def _eligible(
    admission: fx.Admission,
    feature: Feature,
    screen: Screen,
) -> bool:
    # Preserve structurally distinct rearm events exactly.
    if int(admission.opportunity.rearm_index) > 0:
        return True

    signal = admission.signal
    opposed = feature.previous_source_day_body_opposed
    anchor = signal.h4_opened_at.astimezone(v5y._NY).hour
    is_short = signal.side is DemoTradingSetupSide.SHORT
    is_cisd = str(admission.opportunity.source_poi_kind) == "cisd"
    is_c2_expansion = signal.model_kind.value == "c2-closure-next-h4-expansion"

    if screen.short_initial_requires_opposed and is_short and not opposed:
        return False
    if screen.anchor6_initial_requires_opposed and anchor == 6 and not opposed:
        return False
    if screen.anchor22_initial_requires_opposed and anchor == 22 and not opposed:
        return False
    if screen.cisd_initial_requires_opposed and is_cisd and not opposed:
        return False
    if (
        screen.c2_expansion_initial_requires_opposed
        and is_c2_expansion
        and not opposed
    ):
        return False
    return True


def _metrics(values: Sequence[Decimal]) -> dict[str, Any]:
    return fx._metrics(tuple(values))


def _governed(
    admissions: Sequence[fx.Admission],
    outcomes: Sequence[r5.ManagedTrade],
    *,
    stress: Decimal,
) -> tuple[fx.GovernedTrace, ...]:
    return fx._governor_trace(
        admissions,
        outcomes,
        stress=stress,
    )


def _year_stability(
    admissions: Sequence[fx.Admission],
    values: Sequence[Decimal],
) -> dict[str, Any]:
    years = sorted(
        {
            item.signal.signal_at.astimezone(v5y._NY).year
            for item in admissions
        }
    )
    result: dict[str, Any] = {}
    for year in years:
        subset = tuple(
            value
            for item, value in zip(admissions, values, strict=True)
            if item.signal.signal_at.astimezone(v5y._NY).year == year
        )
        result[str(year)] = _metrics(subset)
    return result


def _candidate_row(
    admissions: Sequence[fx.Admission],
    outcomes: Sequence[r5.ManagedTrade],
    features: Sequence[Feature],
    screen: Screen,
) -> dict[str, Any]:
    indices = [
        index
        for index, (admission, feature) in enumerate(
            zip(admissions, features, strict=True)
        )
        if _eligible(admission, feature, screen)
    ]
    selected_admissions = tuple(admissions[index] for index in indices)
    selected_outcomes = tuple(outcomes[index] for index in indices)
    raw_primary_values = tuple(
        outcome.r_multiple - PRIMARY_STRESS
        for outcome in selected_outcomes
    )
    raw_secondary_values = tuple(
        outcome.r_multiple - SECONDARY_STRESS
        for outcome in selected_outcomes
    )
    gov_primary_trace = _governed(
        selected_admissions,
        selected_outcomes,
        stress=PRIMARY_STRESS,
    )
    gov_secondary_trace = _governed(
        selected_admissions,
        selected_outcomes,
        stress=SECONDARY_STRESS,
    )
    gov_primary_values = tuple(item.value for item in gov_primary_trace)
    gov_secondary_values = tuple(item.value for item in gov_secondary_trace)
    raw_primary = _metrics(raw_primary_values)
    governed_primary = _metrics(gov_primary_values)
    governed_secondary = _metrics(gov_secondary_values)
    density_pass = MIN_TRADES <= len(indices) <= MAX_TRADES
    raw_pf = Decimal(str(raw_primary["profit_factor"] or "0"))
    gp_pf = Decimal(str(governed_primary["profit_factor"] or "0"))
    gp_dd = Decimal(str(governed_primary["max_drawdown_r"]))
    gs_pf = Decimal(str(governed_secondary["profit_factor"] or "0"))
    gs_dd = Decimal(str(governed_secondary["max_drawdown_r"]))
    year_rows = _year_stability(selected_admissions, raw_primary_values)
    positive_years = sum(
        Decimal(str(row["total_r"])) > 0 for row in year_rows.values()
    )
    return {
        "screen": screen.payload(),
        "sample": len(indices),
        "removed": len(admissions) - len(indices),
        "density_pass": density_pass,
        "raw_primary": raw_primary,
        "raw_secondary": _metrics(raw_secondary_values),
        "governed_primary": governed_primary,
        "governed_secondary": governed_secondary,
        "positive_raw_years": positive_years,
        "raw_by_year": year_rows,
        "governor_lock_in_primary": fx._governor_lock_in(
            selected_admissions,
            gov_primary_trace,
        ),
        "goal_pass": (
            density_pass
            and raw_pf >= RAW_PF_MIN
            and gp_pf >= GOVERNED_PF_MIN
            and gp_dd <= GOVERNED_DD_MAX
            and gs_pf >= SECONDARY_PF_MIN
            and gs_dd <= SECONDARY_DD_MAX
            and positive_years >= 4
        ),
    }


def _rank(row: dict[str, Any]) -> tuple[int, int, Decimal, Decimal, Decimal]:
    raw = row["raw_primary"]
    gp = row["governed_primary"]
    return (
        int(bool(row["goal_pass"])),
        int(bool(row["density_pass"])),
        Decimal(str(raw["profit_factor"] or "0")),
        Decimal(str(gp["profit_factor"] or "0")),
        -Decimal(str(gp["max_drawdown_r"])),
    )


def build_report(
    *,
    nas100_root: Path,
    sp500_root: Path,
    us30_root: Path,
) -> dict[str, Any]:
    roots = {
        "NAS100": nas100_root,
        "SP500": sp500_root,
        "US30": us30_root,
    }
    bars_by_symbol: dict[str, Sequence[Vt08IndexC2R1Bar]] = {}
    opened_by_symbol: dict[str, tuple[datetime, ...]] = {}
    indexed_by_symbol: dict[str, dict[datetime, Vt08IndexC2R1Bar]] = {}
    provenance: dict[str, Any] = {}
    for symbol in ("NAS100", "SP500", "US30"):
        bars, source = v5y._load_cibo_m15_5y(roots[symbol], symbol=symbol)
        bars_by_symbol[symbol] = bars
        opened_by_symbol[symbol] = tuple(
            bar.opened_at.astimezone(UTC) for bar in bars
        )
        indexed_by_symbol[symbol] = {
            bar.opened_at.astimezone(UTC): bar for bar in bars
        }
        provenance[symbol] = source

    admissions = fx._admissions(bars_by_symbol=bars_by_symbol)
    outcomes = fx._managed(
        admissions,
        bars_by_symbol=bars_by_symbol,
        opened_by_symbol=opened_by_symbol,
    )
    features = tuple(
        _feature(
            admission,
            indexed=indexed_by_symbol[admission.signal.symbol],
        )
        for admission in admissions
    )
    opposed_count = sum(
        feature.previous_source_day_body_opposed for feature in features
    )

    rows = [
        _candidate_row(admissions, outcomes, features, screen)
        for screen in _screens()
    ]
    rows.sort(key=_rank, reverse=True)
    goals = [row for row in rows if bool(row["goal_pass"])]

    return {
        "schema": SCHEMA,
        "identity": IDENTITY,
        "source_failure": {
            "candidate_id": freeze.CANDIDATE_ID,
            "five_year_forensics_run": 35343338395,
            "five_year_forensics_artifact": 10546426128,
            "sample": len(admissions),
        },
        "window": {
            "start_date": v5y.START_DATE.isoformat(),
            "end_date_exclusive": v5y.END_DATE_EXCLUSIVE.isoformat(),
            "status": "CONSUMED_DEVELOPMENT",
            "fresh_certification_holdout": False,
        },
        "feature_evidence": {
            "previous_source_day_body_opposed_count": opposed_count,
            "previous_source_day_body_opposed_share": str(
                Decimal(opposed_count) / Decimal(len(features))
            ),
            "feature_is_pre_entry": True,
            "prior_evidence_origin": (
                "VT08 V4 three-window aggregate screen; not invented from R6 losses"
            ),
        },
        "screen_count": len(rows),
        "goal_candidate_count": len(goals),
        "best": rows[0] if rows else None,
        "top_10": rows[:10],
        "goal_candidates": goals[:10],
        "provenance": provenance,
        "governance": {
            "development_only": True,
            "bounded_causal_screen": True,
            "post_entry_features_used": False,
            "five_year_window_consumed": True,
            "fresh_holdout_claim": False,
            "candidate_promoted": False,
            "live_authorized": False,
            "real_capital_authorized": False,
            "production_authorized": False,
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--nas100-root", type=Path, required=True)
    parser.add_argument("--sp500-root", type=Path, required=True)
    parser.add_argument("--us30-root", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    report = build_report(
        nas100_root=args.nas100_root,
        sp500_root=args.sp500_root,
        us30_root=args.us30_root,
    )
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(
        json.dumps(report, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "identity": IDENTITY,
                "screen_count": report["screen_count"],
                "goal_candidate_count": report["goal_candidate_count"],
                "best": report["best"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
