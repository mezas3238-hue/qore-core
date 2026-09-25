"""VT08 Index R16 — cross-window structural forensics.

Compares the same R8 2.5R execution architecture on the consumed 5Y and recent
2Y development windows. The purpose is to find structural cohorts whose raw
expectancy is directionally stable across both windows before any portfolio
risk governor is applied.

No candidate search or promotion occurs here.
"""

from __future__ import annotations

import argparse
import json
from collections.abc import Callable, Sequence
from decimal import Decimal
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from qore.infrastructure.trader_lab import vt08_index_cibo_2y_density_round4 as r4
from qore.infrastructure.trader_lab import vt08_index_cibo_2y_management_round5 as r5
from qore.infrastructure.trader_lab import vt08_index_r6_5y_failure_forensics as fx
from qore.infrastructure.trader_lab import vt08_index_r10_contextual_risk as r10
from qore.infrastructure.trader_lab import vt08_index_r15_dual_window_gate as r15

SCHEMA = "qore.trader_lab.vt08_index_r16_cross_window_forensics.v1"
IDENTITY = "VT08_INDEX_R16_CROSS_WINDOW_FORENSICS_001"
STRESS = Decimal("0.05")
_NY = ZoneInfo("America/New_York")


def _raw_values(
    stream: Sequence[tuple[r4.ExpandedOpportunity, r5.ManagedTrade]],
) -> tuple[Decimal, ...]:
    return tuple(
        outcome.r_multiple - STRESS for _opportunity, outcome in stream
    )


def _breakdown(
    stream: Sequence[tuple[r4.ExpandedOpportunity, r5.ManagedTrade]],
    contexts: Sequence[r10.Context],
    *,
    key_fn: Callable[[r4.ExpandedOpportunity, r10.Context], str],
) -> dict[str, Any]:
    values = _raw_values(stream)
    labels = sorted(
        {
            key_fn(opportunity, context)
            for (opportunity, _outcome), context in zip(
                stream,
                contexts,
                strict=True,
            )
        }
    )
    result: dict[str, Any] = {}
    for label in labels:
        indices = [
            index
            for index, ((opportunity, _outcome), context) in enumerate(
                zip(stream, contexts, strict=True)
            )
            if key_fn(opportunity, context) == label
        ]
        subset = tuple(values[index] for index in indices)
        result[label] = fx._metrics(subset)
    return result


def _stable_rows(
    five: dict[str, Any],
    two: dict[str, Any],
) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for label in sorted(set(five) & set(two)):
        f = five[label]
        t = two[label]
        f_pf = Decimal(str(f["profit_factor"] or "0"))
        t_pf = Decimal(str(t["profit_factor"] or "0"))
        f_total = Decimal(str(f["total_r"]))
        t_total = Decimal(str(t["total_r"]))
        result[label] = {
            "five_year": f,
            "recent_two_year": t,
            "positive_both": f_total > 0 and t_total > 0,
            "pf_above_1_both": f_pf > 1 and t_pf > 1,
            "pf_above_1_2_both": f_pf >= Decimal("1.20")
            and t_pf >= Decimal("1.20"),
            "min_profit_factor": str(min(f_pf, t_pf)),
        }
    return result


def _dimension_reports(
    stream: Sequence[tuple[r4.ExpandedOpportunity, r5.ManagedTrade]],
    contexts: Sequence[r10.Context],
) -> dict[str, dict[str, Any]]:
    return {
        "market": _breakdown(
            stream,
            contexts,
            key_fn=lambda o, _c: o.signal.symbol,
        ),
        "side": _breakdown(
            stream,
            contexts,
            key_fn=lambda o, _c: o.signal.side.value,
        ),
        "market_side": _breakdown(
            stream,
            contexts,
            key_fn=lambda o, _c: f"{o.signal.symbol}:{o.signal.side.value}",
        ),
        "anchor": _breakdown(
            stream,
            contexts,
            key_fn=lambda o, _c: str(
                o.signal.h4_opened_at.astimezone(_NY).hour
            ),
        ),
        "poi": _breakdown(
            stream,
            contexts,
            key_fn=lambda o, _c: str(o.source_poi_kind),
        ),
        "model_kind": _breakdown(
            stream,
            contexts,
            key_fn=lambda o, _c: o.signal.model_kind.value,
        ),
        "rearm": _breakdown(
            stream,
            contexts,
            key_fn=lambda o, _c: "rearm" if int(o.rearm_index) > 0 else "initial",
        ),
        "source_day": _breakdown(
            stream,
            contexts,
            key_fn=lambda _o, c: (
                "opposed" if c.previous_source_day_body_opposed else "aligned"
            ),
        ),
        "source_day_side": _breakdown(
            stream,
            contexts,
            key_fn=lambda o, c: (
                f"{'opposed' if c.previous_source_day_body_opposed else 'aligned'}:"
                f"{o.signal.side.value}"
            ),
        ),
        "market_source_day": _breakdown(
            stream,
            contexts,
            key_fn=lambda o, c: (
                f"{o.signal.symbol}:"
                f"{'opposed' if c.previous_source_day_body_opposed else 'aligned'}"
            ),
        ),
        "anchor_side": _breakdown(
            stream,
            contexts,
            key_fn=lambda o, _c: (
                f"{o.signal.h4_opened_at.astimezone(_NY).hour}:"
                f"{o.signal.side.value}"
            ),
        ),
    }


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
    five_stream, five_contexts, five_provenance = r15._five_year_stream(roots)
    two_stream, two_contexts, two_provenance = r15._two_year_stream(roots)

    five = _dimension_reports(five_stream, five_contexts)
    two = _dimension_reports(two_stream, two_contexts)
    stable = {
        dimension: _stable_rows(five[dimension], two[dimension])
        for dimension in sorted(five)
    }

    strong: list[dict[str, Any]] = []
    for dimension, rows in stable.items():
        for label, row in rows.items():
            if bool(row["pf_above_1_2_both"]):
                strong.append(
                    {
                        "dimension": dimension,
                        "label": label,
                        **row,
                    }
                )
    strong.sort(
        key=lambda row: (
            Decimal(str(row["min_profit_factor"])),
            min(
                int(row["five_year"]["sample"]),
                int(row["recent_two_year"]["sample"]),
            ),
        ),
        reverse=True,
    )

    return {
        "schema": SCHEMA,
        "identity": IDENTITY,
        "stress_r_per_trade": str(STRESS),
        "samples": {
            "five_year": len(five_stream),
            "recent_two_year": len(two_stream),
        },
        "five_year": five,
        "recent_two_year": two,
        "cross_window_stability": stable,
        "stable_pf_1_2_cohorts": strong,
        "stable_pf_1_2_cohort_count": len(strong),
        "provenance": {
            "five_year": five_provenance,
            "recent_two_year": two_provenance,
        },
        "governance": {
            "forensics_only": True,
            "parameter_search": False,
            "candidate_promotion": False,
            "both_windows_consumed": True,
            "fresh_holdout_claim": False,
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
                "samples": report["samples"],
                "stable_pf_1_2_cohort_count": report[
                    "stable_pf_1_2_cohort_count"
                ],
                "top_stable": report["stable_pf_1_2_cohorts"][:10],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
