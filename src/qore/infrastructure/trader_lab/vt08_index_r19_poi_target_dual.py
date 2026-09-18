"""VT08 Index R19 — POI-specialist target architecture, dual-window screen.

R19 keeps the R8 opportunity generator but assigns a fixed target depth by
source POI family. The same target map is used on both consumed development
windows. This directly tests whether the recent-2Y failure is caused by forcing
the same 2.5R destination on CISD, FVG and relevant-swing formations.

No trailing, no soft exit and no risk governor are used in this round.
"""

from __future__ import annotations

import argparse
import itertools
import json
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC
from decimal import Decimal
from pathlib import Path
from typing import Any

from qore.infrastructure.trader_lab import vt08_index_cibo_2y_density_round4 as r4
from qore.infrastructure.trader_lab import vt08_index_cibo_2y_management_round5 as r5
from qore.infrastructure.trader_lab import vt08_index_r6_5y_failure_forensics as fx
from qore.infrastructure.trader_lab import vt08_index_r6_five_year_validation as v5y
from qore.infrastructure.trader_lab import vt08_index_r8_priority_poi_rearm_reset as r8
from qore.infrastructure.trader_lab import vt08_index_r14_recent_2y_replay as r2y
from qore.infrastructure.traders.vt08_index_c2_positional_r1 import Vt08IndexC2R1Bar

SCHEMA = "qore.trader_lab.vt08_index_r19_poi_target_dual.v1"
IDENTITY = "VT08_INDEX_R19_POI_TARGET_DUAL_001"
PRIMARY_STRESS = Decimal("0.05")
SECONDARY_STRESS = Decimal("0.10")
PF_MIN = Decimal("1.50")
DD_MAX = Decimal("6")
SECONDARY_PF_MIN = Decimal("1.30")
SECONDARY_DD_MAX = Decimal("8")
FIVE_YEAR_MIN_TRADES = 1500
FIVE_YEAR_MAX_TRADES = 1600
TWO_YEAR_MIN_TRADES = 600
TWO_YEAR_MAX_TRADES = 700


@dataclass(frozen=True, slots=True)
class PoiTargets:
    cisd: Decimal
    fvg: Decimal
    relevant_swing: Decimal

    @property
    def target_id(self) -> str:
        return (
            f"R19-C{self.cisd}-F{self.fvg}-S{self.relevant_swing}"
        )

    def for_opportunity(self, opportunity: r4.ExpandedOpportunity) -> Decimal:
        kind = str(opportunity.source_poi_kind)
        if kind == "cisd":
            return self.cisd
        if kind == "fvg":
            return self.fvg
        if kind == "relevant-swing":
            return self.relevant_swing
        raise ValueError(f"unsupported POI family: {kind}")

    def payload(self) -> dict[str, str]:
        return {
            "target_id": self.target_id,
            "cisd_target_r": str(self.cisd),
            "fvg_target_r": str(self.fvg),
            "relevant_swing_target_r": str(self.relevant_swing),
        }


def _maps() -> tuple[PoiTargets, ...]:
    return tuple(
        PoiTargets(cisd=cisd, fvg=fvg, relevant_swing=swing)
        for cisd, fvg, swing in itertools.product(
            (
                Decimal("0.75"),
                Decimal("1.00"),
                Decimal("1.25"),
                Decimal("1.50"),
                Decimal("1.75"),
                Decimal("2.00"),
            ),
            (
                Decimal("1.50"),
                Decimal("2.00"),
                Decimal("2.50"),
                Decimal("3.00"),
            ),
            (
                Decimal("1.00"),
                Decimal("1.50"),
                Decimal("2.00"),
                Decimal("2.50"),
            ),
        )
    )


def _policy(target: Decimal) -> r5.Policy:
    return r5.Policy(
        target_r=target,
        soft_close_loss_r=None,
        soft_close_until_mfe_r=None,
        deadline_bars=None,
        deadline_min_mfe_r=None,
        trail_name="OFF",
        trail_steps=(),
    )


def _sequential_symbol(
    opportunities: Sequence[r4.ExpandedOpportunity],
    *,
    bars: Sequence[Vt08IndexC2R1Bar],
    targets: PoiTargets,
) -> tuple[tuple[r4.ExpandedOpportunity, r5.ManagedTrade], ...]:
    opened = tuple(bar.opened_at.astimezone(UTC) for bar in bars)
    selected: list[tuple[r4.ExpandedOpportunity, r5.ManagedTrade]] = []
    last_exit = None
    for opportunity in opportunities:
        outcome = r5._manage_trade(
            opportunity.signal,
            bars=bars,
            opened=opened,
            policy=_policy(targets.for_opportunity(opportunity)),
        )
        if last_exit is not None and opportunity.signal.signal_at < last_exit:
            continue
        selected.append((opportunity, outcome))
        last_exit = outcome.exited_at
    return tuple(selected)


def _stream_for_window(
    roots: dict[str, Path],
    *,
    recent_two_year: bool,
    targets: PoiTargets,
) -> tuple[tuple[r4.ExpandedOpportunity, r5.ManagedTrade], ...]:
    selected: list[tuple[r4.ExpandedOpportunity, r5.ManagedTrade]] = []
    for symbol in ("NAS100", "SP500", "US30"):
        if recent_two_year:
            bars, _source = r2y._load_cibo_m15_2y(
                roots[symbol],
                symbol=symbol,
            )
            opportunities = r2y._opportunities_2y(
                symbol=symbol,
                bars=bars,
            )
        else:
            bars, _source = v5y._load_cibo_m15_5y(
                roots[symbol],
                symbol=symbol,
            )
            opportunities = r8._opportunities(
                symbol=symbol,
                bars=bars,
            )
        selected.extend(
            _sequential_symbol(
                opportunities,
                bars=bars,
                targets=targets,
            )
        )
    selected.sort(
        key=lambda item: (
            item[0].signal.signal_at,
            item[0].signal.symbol,
        )
    )
    return tuple(selected)


def _metrics(
    stream: Sequence[tuple[r4.ExpandedOpportunity, r5.ManagedTrade]],
    *,
    stress: Decimal,
) -> dict[str, Any]:
    values = tuple(
        outcome.r_multiple - stress
        for _opportunity, outcome in stream
    )
    return fx._metrics(values)


def _metric_pass(
    row: dict[str, Any],
    *,
    pf_min: Decimal,
    dd_max: Decimal,
) -> bool:
    return (
        Decimal(str(row["total_r"])) > 0
        and Decimal(str(row["profit_factor"] or "0")) >= pf_min
        and Decimal(str(row["max_drawdown_r"])) <= dd_max
    )


def _candidate(
    roots: dict[str, Path],
    *,
    targets: PoiTargets,
) -> dict[str, Any]:
    five_stream = _stream_for_window(
        roots,
        recent_two_year=False,
        targets=targets,
    )
    two_stream = _stream_for_window(
        roots,
        recent_two_year=True,
        targets=targets,
    )
    five_primary = _metrics(five_stream, stress=PRIMARY_STRESS)
    five_secondary = _metrics(five_stream, stress=SECONDARY_STRESS)
    two_primary = _metrics(two_stream, stress=PRIMARY_STRESS)
    two_secondary = _metrics(two_stream, stress=SECONDARY_STRESS)

    five_density = FIVE_YEAR_MIN_TRADES <= len(five_stream) <= FIVE_YEAR_MAX_TRADES
    two_density = TWO_YEAR_MIN_TRADES <= len(two_stream) <= TWO_YEAR_MAX_TRADES
    five_pass = (
        five_density
        and _metric_pass(five_primary, pf_min=PF_MIN, dd_max=DD_MAX)
        and _metric_pass(
            five_secondary,
            pf_min=SECONDARY_PF_MIN,
            dd_max=SECONDARY_DD_MAX,
        )
    )
    two_pass = (
        two_density
        and _metric_pass(two_primary, pf_min=PF_MIN, dd_max=DD_MAX)
        and _metric_pass(
            two_secondary,
            pf_min=SECONDARY_PF_MIN,
            dd_max=SECONDARY_DD_MAX,
        )
    )
    return {
        "targets": targets.payload(),
        "five_year": {
            "sample": len(five_stream),
            "primary": five_primary,
            "secondary": five_secondary,
        },
        "recent_two_year": {
            "sample": len(two_stream),
            "primary": two_primary,
            "secondary": two_secondary,
        },
        "five_year_density_pass": five_density,
        "recent_two_year_density_pass": two_density,
        "five_year_pass": five_pass,
        "recent_two_year_pass": two_pass,
        "dual_window_pass": five_pass and two_pass,
    }


def _rank(
    row: dict[str, Any],
) -> tuple[int, int, Decimal, Decimal, Decimal]:
    five = row["five_year"]["primary"]
    two = row["recent_two_year"]["primary"]
    min_pf = min(
        Decimal(str(five["profit_factor"] or "0")),
        Decimal(str(two["profit_factor"] or "0")),
    )
    worst_dd = max(
        Decimal(str(five["max_drawdown_r"])),
        Decimal(str(two["max_drawdown_r"])),
    )
    return (
        int(bool(row["dual_window_pass"])),
        int(
            bool(row["five_year_density_pass"])
            and bool(row["recent_two_year_density_pass"])
        ),
        min_pf,
        -worst_dd,
        Decimal(str(five["total_r"])) + Decimal(str(two["total_r"])),
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
    rows = [
        _candidate(roots, targets=targets)
        for targets in _maps()
    ]
    rows.sort(key=_rank, reverse=True)
    goals = [row for row in rows if bool(row["dual_window_pass"])]
    return {
        "schema": SCHEMA,
        "identity": IDENTITY,
        "map_count": len(rows),
        "dual_window_candidate_count": len(goals),
        "contract": {
            "five_year_density": [FIVE_YEAR_MIN_TRADES, FIVE_YEAR_MAX_TRADES],
            "two_year_density": [TWO_YEAR_MIN_TRADES, TWO_YEAR_MAX_TRADES],
            "primary_pf_minimum": str(PF_MIN),
            "primary_dd_max_r": str(DD_MAX),
            "secondary_pf_minimum": str(SECONDARY_PF_MIN),
            "secondary_dd_max_r": str(SECONDARY_DD_MAX),
            "same_target_map_both_windows": True,
        },
        "best": rows[0],
        "top_20": rows[:20],
        "dual_window_candidates": goals[:20],
        "governance": {
            "development_only": True,
            "same_entry_architecture": True,
            "poi_specialist_targets_only": True,
            "same_rules_both_windows": True,
            "risk_governor_used": False,
            "both_windows_consumed": True,
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
                "map_count": report["map_count"],
                "dual_window_candidate_count": report["dual_window_candidate_count"],
                "best": report["best"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
