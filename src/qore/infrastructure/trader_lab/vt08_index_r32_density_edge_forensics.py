"""VT08 Index R32 — source-complete density edge forensics.

R31 established that the 2,448-trade source-complete surface satisfies the
Owner density contract and retains positive raw expectancy, while governed
portfolio PF/DD are strong. Promotion still failed because temporal stability
is not complete, principally 2019.

R32 is diagnostic only. It does not select or suppress trades. It attributes
the source-complete 2.5R population by pre-existing methodology dimensions and
by two architecture labels:
- SOURCE_PRIORITY vs ADDITIONAL_SOURCE_POI: whether R8 priority architecture
  would have retained the same structural event.
- SEQUENTIAL_ADMITTED vs OCCUPANCY_SUPPRESSED: whether the event survives the
  historical one-active-position-per-symbol lifecycle at 2.5R.

No cohort discovered here may become an operational rule without a separate
causal preregistration.
"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from collections.abc import Callable, Sequence
from datetime import UTC
from decimal import Decimal
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from qore.infrastructure.trader_lab import vt08_index_cibo_2y_management_round5 as r5
from qore.infrastructure.trader_lab import vt08_index_concurrent_market_contract as contract
from qore.infrastructure.trader_lab import vt08_index_r6_5y_failure_forensics as fx
from qore.infrastructure.trader_lab import vt08_index_r6_five_year_validation as r6
from qore.infrastructure.trader_lab import vt08_index_r8_priority_poi_rearm_reset as r8
from qore.infrastructure.trader_lab import (
    vt08_index_r31_source_complete_structural_concurrency as r31,
)

SCHEMA = "qore.trader_lab.vt08_index_r32_density_edge_forensics.v1"
IDENTITY = "VT08_INDEX_R32_DENSITY_EDGE_FORENSICS_001"
PRIMARY_STRESS = Decimal("0.05")
SECONDARY_STRESS = Decimal("0.10")
TARGET_R = Decimal("2.5")
_NY = ZoneInfo("America/New_York")


def _sequential_admitted_ids(
    opportunities: Sequence[Any],
    *,
    bars: Sequence[Any],
) -> set[tuple[object, ...]]:
    opened = tuple(bar.opened_at.astimezone(UTC) for bar in bars)
    policy = r8._target_policy(TARGET_R)
    candidates = [
        (
            item,
            r5._manage_trade(
                item.signal,
                bars=bars,
                opened=opened,
                policy=policy,
            ),
        )
        for item in opportunities
    ]
    admitted: set[tuple[object, ...]] = set()
    last_exit = None
    for opportunity, outcome in sorted(
        candidates,
        key=lambda item: (
            item[0].signal.signal_at,
            item[0].signal.symbol,
            item[0].signal.entry,
            item[0].signal.stop,
        ),
    ):
        if last_exit is not None and opportunity.signal.signal_at < last_exit:
            continue
        admitted.add(opportunity.identity())
        last_exit = outcome.exited_at
    return admitted


def _metrics(rows: Sequence[dict[str, Any]], *, stress: Decimal) -> dict[str, Any]:
    ordered = sorted(
        rows,
        key=lambda row: (
            row["outcome"].exited_at.astimezone(UTC),
            row["opportunity"].signal.symbol,
            row["opportunity"].signal.signal_at,
        ),
    )
    values = tuple(row["outcome"].r_multiple - stress for row in ordered)
    return fx._metrics(values)


def _breakdown(
    rows: Sequence[dict[str, Any]],
    *,
    labeler: Callable[[dict[str, Any]], str],
) -> dict[str, dict[str, Any]]:
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        groups[labeler(row)].append(row)
    return {
        label: {
            "primary": _metrics(group, stress=PRIMARY_STRESS),
            "secondary": _metrics(group, stress=SECONDARY_STRESS),
        }
        for label, group in sorted(groups.items())
    }


def _year(row: dict[str, Any]) -> str:
    return str(row["outcome"].exited_at.astimezone(UTC).year)


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
    stream, _bars_by_symbol, _opened_by_symbol, provenance = (
        r31._build_source_complete_stream(roots=roots)
    )
    if not contract.validates_trade_count(years=5, sample=len(stream)):
        raise ValueError(f"R32 density drift: {len(stream)}")

    rows: list[dict[str, Any]] = []
    for symbol in contract.MARKETS:
        bars, _source = r6._load_cibo_m15_5y(roots[symbol], symbol=symbol)
        complete = r6._build_surface_5y(symbol=symbol, bars=bars)
        priority_ids = {
            item.identity() for item in r8._opportunities(symbol=symbol, bars=bars)
        }
        admitted_ids = _sequential_admitted_ids(complete, bars=bars)

        by_identity = {
            opportunity.identity(): outcome
            for opportunity, outcome in stream
            if opportunity.signal.symbol == symbol
        }
        if len(by_identity) != len(complete):
            raise ValueError(f"R32 stream identity mismatch for {symbol}")

        for opportunity in complete:
            identity = opportunity.identity()
            outcome = by_identity[identity]
            rows.append(
                {
                    "opportunity": opportunity,
                    "outcome": outcome,
                    "priority_status": (
                        "SOURCE_PRIORITY"
                        if identity in priority_ids
                        else "ADDITIONAL_SOURCE_POI"
                    ),
                    "occupancy_status": (
                        "SEQUENTIAL_ADMITTED"
                        if identity in admitted_ids
                        else "OCCUPANCY_SUPPRESSED"
                    ),
                }
            )

    rows.sort(
        key=lambda row: (
            row["opportunity"].signal.signal_at,
            row["opportunity"].signal.symbol,
            row["opportunity"].signal.entry,
        )
    )

    def poi(row: dict[str, Any]) -> str:
        return str(row["opportunity"].source_poi_kind)

    def side(row: dict[str, Any]) -> str:
        return str(row["opportunity"].signal.side.value)

    def market_label(row: dict[str, Any]) -> str:
        return str(row["opportunity"].signal.symbol)

    def anchor(row: dict[str, Any]) -> str:
        return str(row["opportunity"].signal.h4_opened_at.astimezone(_NY).hour)

    def model_kind(row: dict[str, Any]) -> str:
        return str(row["opportunity"].signal.model_kind.value)

    def rearm(row: dict[str, Any]) -> str:
        return "REARM" if int(row["opportunity"].rearm_index) > 0 else "INITIAL"

    def priority(row: dict[str, Any]) -> str:
        return str(row["priority_status"])

    def occupancy(row: dict[str, Any]) -> str:
        return str(row["occupancy_status"])

    def priority_year(row: dict[str, Any]) -> str:
        return f"{_year(row)}|{row['priority_status']}"

    def occupancy_year(row: dict[str, Any]) -> str:
        return f"{_year(row)}|{row['occupancy_status']}"

    def poi_year(row: dict[str, Any]) -> str:
        return f"{_year(row)}|{row['opportunity'].source_poi_kind}"

    return {
        "schema": SCHEMA,
        "identity": IDENTITY,
        "sample": len(rows),
        "target_r": str(TARGET_R),
        "aggregate": {
            "primary": _metrics(rows, stress=PRIMARY_STRESS),
            "secondary": _metrics(rows, stress=SECONDARY_STRESS),
        },
        "by_year": _breakdown(rows, labeler=_year),
        "by_market": _breakdown(rows, labeler=market_label),
        "by_side": _breakdown(rows, labeler=side),
        "by_anchor": _breakdown(rows, labeler=anchor),
        "by_poi": _breakdown(rows, labeler=poi),
        "by_model_kind": _breakdown(rows, labeler=model_kind),
        "by_rearm": _breakdown(rows, labeler=rearm),
        "by_priority_status": _breakdown(rows, labeler=priority),
        "by_occupancy_status": _breakdown(rows, labeler=occupancy),
        "by_year_priority_status": _breakdown(rows, labeler=priority_year),
        "by_year_occupancy_status": _breakdown(rows, labeler=occupancy_year),
        "by_year_poi": _breakdown(rows, labeler=poi_year),
        "provenance": provenance,
        "governance": {
            "forensics_only": True,
            "consumed_window": True,
            "fresh_holdout_claim": False,
            "cohort_to_rule_automatic": False,
            "trade_suppression_performed": False,
            "target_optimization_performed": False,
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
                "sample": report["sample"],
                "by_priority_status": report["by_priority_status"],
                "by_occupancy_status": report["by_occupancy_status"],
                "by_poi": report["by_poi"],
                "by_year_priority_status": report["by_year_priority_status"],
                "by_year_occupancy_status": report["by_year_occupancy_status"],
                "by_year_poi": report["by_year_poi"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
