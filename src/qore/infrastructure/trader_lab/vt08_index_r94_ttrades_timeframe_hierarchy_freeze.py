"""VT08 Index R94 — TTrades timeframe hierarchy source freeze.

Purpose
-------
Freeze the source boundary between a *fractal model* and lower-timeframe
refinement so density research cannot accidentally promote a union of separate
models as one VT08 strategy.

Primary-source findings frozen here:
1. TTrades' preferred/simple model is:
      Daily bias -> H4 swing/structure -> M15 execution.
2. General timeframe alignment uses one Bias -> Structure -> Entry chain.
3. H1 -> M5 is a valid alternative structural/entry pairing under a higher
   timeframe bias, not an extra independent setup to add automatically to every
   H4 -> M15 setup.
4. M1 can refine an already-established higher/middle-timeframe model; the
   lower timeframe provides entry precision and does not create a new narrative.
5. R92/R93 exact cascade unions are therefore density upper-bound diagnostics,
   not promotable candidate identities by themselves.

This module contains no market data, no PnL and no candidate. It exists to
prevent source-identity drift in later VT08 research.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

SCHEMA = "qore.trader_lab.vt08_index_r94_ttrades_timeframe_hierarchy_freeze.v1"
IDENTITY = "VT08_INDEX_R94_TTRADES_TIMEFRAME_HIERARCHY_FREEZE_001"

SOURCE_REFERENCES: tuple[dict[str, str], ...] = (
    {
        "title": "The Best Timeframes for TTrades Fractal Model (Simple)",
        "published": "2026-01-31",
        "url": (
            "https://ttrades.com/"
            "the-best-timeframes-for-ttrades-fractal-model-simple/"
        ),
        "relevance": (
            "preferred model: Daily bias, H4 swing structure, "
            "M15 execution"
        ),
    },
    {
        "title": (
            "Timeframe Alignment: How to Align Higher and Lower "
            "Time Frames for Precision Entries"
        ),
        "published": "2025-07-30",
        "url": (
            "https://ttrades.com/"
            "timeframe-alignment-how-to-align-higher-and-lower-time-frames-"
            "for-precision-entries/"
        ),
        "relevance": (
            "three-layer Bias -> Structure -> Entry architecture; "
            "explicit pairings include H4->M15, H1->M5, M15->M1"
        ),
    },
    {
        "title": (
            "Refining Entries with the Fractal Model: "
            "Precision with 1-Minute Inversions"
        ),
        "published": "2025-08-03",
        "url": (
            "https://ttrades.com/"
            "refining-entries-with-the-fractal-model-precision-with-"
            "1-minute-inversions/"
        ),
        "relevance": (
            "M1 is an execution refinement inside an already aligned "
            "higher/middle-timeframe model"
        ),
    },
    {
        "title": "TTrades Scalping Model - Simple Day Trading Strategy",
        "published": "2026-01-24",
        "url": (
            "https://ttrades.com/"
            "ttrades-scalping-model-simple-day-trading-strategy/"
        ),
        "relevance": (
            "hourly bias/structure -> M15 swing confirmation -> "
            "M1 execution; M1 is where trade is executed, not where "
            "the narrative is created"
        ),
    },
)


def payload() -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "identity": IDENTITY,
        "source_references": list(SOURCE_REFERENCES),
        "frozen_hierarchy": {
            "vt08_primary_model": {
                "bias_timeframe": "D1",
                "structure_timeframe": "H4",
                "entry_timeframe": "M15",
                "model_role": "PRIMARY_TTRADES_PREFERRED_MODEL",
            },
            "alternate_pairings": {
                "H1_M5": {
                    "valid_pairing": True,
                    "independent_additive_layer_to_H4_M15": False,
                },
                "M15_M1": {
                    "valid_pairing": True,
                    "independent_additive_layer_to_H4_M15": False,
                },
            },
            "lower_timeframe_refinement": {
                "allowed": True,
                "requires_preexisting_higher_timeframe_narrative": True,
                "creates_new_independent_narrative": False,
                "creates_new_setup_count_by_default": False,
            },
            "cascade_union": {
                "r92_r93_role": "DENSITY_UPPER_BOUND_DIAGNOSTIC",
                "promotable_as_candidate_without_model_selection_rule": False,
                "pnl_may_not_choose_timeframe_pairing": True,
            },
        },
        "vt08_owner_constraints": {
            "markets": ["NAS100", "SP500", "US30"],
            "owner_disabled_14_preserved": True,
            "forex_modified": False,
        },
        "governance": {
            "source_boundary_freeze": True,
            "market_data_consumed": False,
            "pnl_evaluated": False,
            "density_result_used_to_choose_model": False,
            "candidate_created": False,
            "trader_certified": False,
            "live_authorized": False,
            "real_capital_authorized": False,
            "production_authorized": False,
        },
        "decision": (
            "R94_TIMEFRAME_HIERARCHY_FROZEN_"
            "CASCADE_UNION_DIAGNOSTIC_ONLY"
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    report = payload()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(
        json.dumps(report, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    main()
