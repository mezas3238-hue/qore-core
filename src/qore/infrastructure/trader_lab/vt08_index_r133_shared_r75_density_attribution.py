"""VT08 Index R133 — Shared attribution on R75 added-density surface.

R132 proved two things:
- Shared/Core can be consumed causally by VT08 through an authority-free adapter.
- Raw density recovery mechanisms cannot simply be appended: R75's strict
  cross-index ambiguous-bias surface is negative in aggregate.

R133 asks whether that added R75 density is uniformly bad or whether Shared
market context separates transportable sub-surfaces before entry.

No signal is created, removed or reweighted here. The exact R75 added signals
and exact R75 managed outcomes are classified using the exact R132 causal
context adapter. Outcome/PnL are attached only after classification for
research attribution.

The objective is density quality discovery, not candidate selection.
"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from collections.abc import Sequence
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace
from typing import Any

from qore.infrastructure.trader_lab import (
    vt08_index_concurrent_market_contract as contract,
)
from qore.infrastructure.trader_lab import (
    vt08_index_r74_ambiguous_bias_resolvers as r74,
)
from qore.infrastructure.trader_lab import (
    vt08_index_r75_cross_index_ambiguous_bias_consensus as r75,
)
from qore.infrastructure.trader_lab import (
    vt08_index_r132_full_intelligence_bridge as r132,
)
from qore.infrastructure.traders.vt08_index_c2_positional_r1 import (
    Vt08IndexC2R1Bar,
)

SCHEMA = "qore.trader_lab.vt08_index_r133_shared_r75_density_attribution.v1"
IDENTITY = "VT08_INDEX_R133_SHARED_R75_ADDED_DENSITY_ATTRIBUTION_001"

SOURCE_R132_RUN_ID = 36174146167
SOURCE_R132_ARTIFACT_ID = 10881626079
SOURCE_R132_ARTIFACT_DIGEST = (
    "sha256:346dc6605d59203b6069fb9a00434dc"
    "9c9eb696cf5b18b1a7d348ee9417dadfc"
)
MIN_TRANSPORT_SAMPLE = 10


def _metrics(rows: Sequence[dict[str, Any]]) -> dict[str, Any]:
    values = tuple(Decimal(str(row["secondary_r"])) for row in rows)
    gains = sum((value for value in values if value > 0), Decimal())
    losses = -sum((value for value in values if value < 0), Decimal())
    equity = Decimal()
    peak = Decimal()
    drawdown = Decimal()
    streak = 0
    max_streak = 0
    for value in values:
        equity += value
        peak = max(peak, equity)
        drawdown = max(drawdown, peak - equity)
        if value < 0:
            streak += 1
            max_streak = max(max_streak, streak)
        else:
            streak = 0
    total = sum(values, Decimal())
    return {
        "sample": len(values),
        "wins": sum(value > 0 for value in values),
        "losses": sum(value < 0 for value in values),
        "total_r": str(total),
        "profit_factor": str(gains / losses) if losses else None,
        "max_drawdown_r": str(drawdown),
        "max_losing_streak": max_streak,
    }


def _group(
    rows: Sequence[dict[str, Any]],
    field: str,
) -> dict[str, Any]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[str(row[field])].append(row)
    return {
        key: _metrics(items)
        for key, items in sorted(grouped.items())
    }


def _group_pair(
    rows: Sequence[dict[str, Any]],
) -> dict[str, Any]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        key = f"{row['future_state']}|{row['broad_regime']}"
        grouped[key].append(row)
    return {
        key: _metrics(items)
        for key, items in sorted(grouped.items())
    }


def _period_label(
    *,
    window_id: str,
    exit_date: Any,
    start_date: Any,
    end_date: Any,
) -> str:
    if window_id == "R66":
        boundary = start_date.replace(year=start_date.year + 1)
        return "B1" if exit_date < boundary else "B2"
    span = 5 if (end_date - start_date).days > 1000 else 2
    for index in range(span):
        left = start_date.replace(year=start_date.year + index)
        right = (
            start_date.replace(year=start_date.year + index + 1)
            if index + 1 < span
            else end_date
        )
        if left <= exit_date < right:
            return f"Y{index + 1}"
    raise ValueError("R133 exit date outside expected period")


def _period_group(
    rows: Sequence[dict[str, Any]],
) -> dict[str, Any]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[str(row["period"])].append(row)
    return {
        key: _metrics(items)
        for key, items in sorted(grouped.items())
    }


def _added_stream(
    *,
    roots: dict[str, Path],
    window_id: str,
) -> tuple[
    tuple[tuple[Any, Any], ...],
    dict[str, Sequence[Vt08IndexC2R1Bar]],
    dict[str, Any],
    Any,
    Any,
]:
    _canonical, bars_by_symbol, provenance = r74._load_window(
        roots=roots,
        window_id=window_id,
    )
    start_date, end_date, _expected = r74._window_contract(window_id)

    added: list[tuple[Any, Any]] = []
    for symbol in contract.MARKETS:
        surface, _diag = r75._surface_for_symbol(
            symbol=symbol,
            bars_by_symbol=bars_by_symbol,
            start_date=start_date,
            end_date=end_date,
        )
        added.extend(
            r74._managed(
                surface,
                bars=bars_by_symbol[symbol],
            )
        )
    added.sort(
        key=lambda item: (
            item[1].exited_at,
            item[0].signal.symbol,
            item[0].signal.signal_at,
        )
    )
    return (
        tuple(added),
        bars_by_symbol,
        provenance,
        start_date,
        end_date,
    )


def _window(
    *,
    roots: dict[str, Path],
    window_id: str,
) -> dict[str, Any]:
    (
        added,
        bars_by_symbol,
        provenance,
        start_date,
        end_date,
    ) = _added_stream(
        roots=roots,
        window_id=window_id,
    )

    states: dict[
        str,
        tuple[
            Sequence[Vt08IndexC2R1Bar],
            Sequence[Any],
        ],
    ] = {
        symbol: (
            tuple(bars),
            tuple(bar.closed_at for bar in bars),
        )
        for symbol, bars in bars_by_symbol.items()
    }

    rows: list[dict[str, Any]] = []
    for opportunity, trade in added:
        wrapper = SimpleNamespace(
            symbol=opportunity.signal.symbol,
            opportunity=opportunity,
        )
        context = r132._context(wrapper, states=states)
        secondary = trade.r_multiple - r75.SECONDARY_STRESS
        rows.append(
            {
                "symbol": opportunity.signal.symbol,
                "side": opportunity.signal.side.value,
                "signal_at": opportunity.signal.signal_at.isoformat(),
                "exited_at": trade.exited_at.isoformat(),
                "period": _period_label(
                    window_id=window_id,
                    exit_date=trade.exited_at.astimezone(
                        r74._NY
                    ).date(),
                    start_date=start_date,
                    end_date=end_date,
                ),
                "secondary_r": str(secondary),
                **context,
            }
        )

    expected = r75._window(
        roots=roots,
        window_id=window_id,
    )
    if len(rows) != int(expected["added_consensus_signals"]):
        raise ValueError(f"R133 {window_id} R75 surface drift")

    return {
        "window_id": window_id,
        "sample": len(rows),
        "raw_secondary": _metrics(rows),
        "by_competing_future": _group(rows, "future_state"),
        "by_broad_regime": _group(rows, "broad_regime"),
        "by_future_x_regime": _group_pair(rows),
        "by_period": _period_group(rows),
        "canonical_reference": expected["canonical_sample"],
        "hypothetical_raw_combined_sample": expected[
            "hypothetical_combined_sample"
        ],
        "provenance": provenance,
    }


def _transport(
    windows: dict[str, dict[str, Any]],
    *,
    field: str,
) -> dict[str, Any]:
    labels = set.intersection(
        *(
            set(window[field])
            for window in windows.values()
        )
    )
    results: dict[str, Any] = {}
    for label in sorted(labels):
        cells = {
            window_id: window[field][label]
            for window_id, window in windows.items()
        }
        sample_ok = all(
            int(cell["sample"]) >= MIN_TRANSPORT_SAMPLE
            for cell in cells.values()
        )
        economic_positive = all(
            Decimal(str(cell["total_r"])) > 0
            and Decimal(str(cell["profit_factor"] or "0")) > 1
            for cell in cells.values()
        )
        if sample_ok:
            results[label] = {
                "cells": cells,
                "sample_gate": sample_ok,
                "secondary_positive_all_windows": economic_positive,
            }
    return results


def build_report(
    *,
    nas100_root: Path,
    sp500_root: Path,
    us30_root: Path,
) -> dict[str, Any]:
    if r132.IDENTITY != (
        "VT08_INDEX_R132_FULL_INTELLIGENCE_CAUSAL_BRIDGE_001"
    ):
        raise ValueError("R133 R132 identity drift")

    roots = {
        "NAS100": nas100_root,
        "SP500": sp500_root,
        "US30": us30_root,
    }
    windows = {
        "5Y": _window(roots=roots, window_id="5Y"),
        "2Y": _window(roots=roots, window_id="2Y"),
        "R66": _window(roots=roots, window_id="R66"),
    }
    return {
        "schema": SCHEMA,
        "identity": IDENTITY,
        "source_r132": {
            "run_id": SOURCE_R132_RUN_ID,
            "artifact_id": SOURCE_R132_ARTIFACT_ID,
            "artifact_digest": SOURCE_R132_ARTIFACT_DIGEST,
        },
        "classification_contract": {
            "source_surface": "R75_STRICT_CROSS_INDEX_AMBIGUOUS_BIAS",
            "shared_context": r132.IDENTITY,
            "classification_before_outcome_attachment": True,
            "trade_outcome_used_for_classification": False,
            "pnl_used_for_classification": False,
            "risk_weighting_applied": False,
            "signal_suppression": False,
            "candidate_selected": False,
        },
        "five_year": windows["5Y"],
        "recent_two_year": windows["2Y"],
        "r66_failed_holdout": windows["R66"],
        "transport_by_competing_future": _transport(
            windows,
            field="by_competing_future",
        ),
        "transport_by_broad_regime": _transport(
            windows,
            field="by_broad_regime",
        ),
        "transport_by_future_x_regime": _transport(
            windows,
            field="by_future_x_regime",
        ),
        "decision": (
            "R133_SHARED_R75_ADDED_DENSITY_ATTRIBUTION_COMPLETE_"
            "NO_CANDIDATE_SELECTED"
        ),
        "governance": {
            "research_only": True,
            "consumed_evidence_only": True,
            "fresh_holdout_claim": False,
            "candidate_created": False,
            "trader_certified": False,
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
                "five_year": report["five_year"]["raw_secondary"],
                "recent_two_year": report["recent_two_year"]["raw_secondary"],
                "r66": report["r66_failed_holdout"]["raw_secondary"],
                "transport_future": report[
                    "transport_by_competing_future"
                ],
                "transport_regime": report[
                    "transport_by_broad_regime"
                ],
                "decision": report["decision"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
