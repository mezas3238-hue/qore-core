"""VT08 Index R80 — source-authorized 2R target transport falsification.

The TTrades/V6 source freeze specifies a fixed initial 2R target. The later
R31/R58 economic lineage uses a 2.5R research target. R80 tests exactly one
source-parity correction: replay the identical canonical structural signals
with 2R management, then let the same causal R34 -> R47 -> R58 allocator
architecture evolve from the resulting completed trades.

No target grid is searched. 2R is fixed before economic measurement because it
is the source-authorized value. Signal identity, daily bias, anchors, POIs,
CISD, Protected Swing, entries, stops, structural rearm, R47 demotions, R58
promotion rules, positive-risk floor and portfolio budget are unchanged.

All three windows are consumed evidence. This is falsification only and cannot
create a certified candidate.
"""

from __future__ import annotations

import argparse
import json
from collections.abc import Sequence
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Any

from qore.infrastructure.trader_lab import (
    vt08_index_cibo_2y_management_round5 as r5,
)
from qore.infrastructure.trader_lab import (
    vt08_index_r6_5y_failure_forensics as fx,
)
from qore.infrastructure.trader_lab import (
    vt08_index_r8_priority_poi_rearm_reset as r8,
)
from qore.infrastructure.trader_lab import (
    vt08_index_r15_concurrent_portfolio_validation as r15,
)
from qore.infrastructure.trader_lab import (
    vt08_index_r55_distributed_causal_risk as r55,
)
from qore.infrastructure.trader_lab import (
    vt08_index_r58_exact_r47_distributed_risk as r58,
)
from qore.infrastructure.trader_lab import (
    vt08_index_r59_candidate_freeze as freeze,
)
from qore.infrastructure.trader_lab import (
    vt08_index_r66_fresh_historical_holdout as r66,
)
from qore.infrastructure.trader_lab import (
    vt08_index_r67_r66_failure_forensics as r67,
)
from qore.infrastructure.trader_lab import (
    vt08_index_r74_ambiguous_bias_resolvers as r74,
)
from qore.infrastructure.trader_lab import (
    vt08_index_r79_fvg_reaction_ps_gap as r79,
)
from qore.infrastructure.trader_lab import (
    vt08_index_v6_ttrades_source_faithful as v6,
)
from qore.infrastructure.trader_lab import (
    vt08_index_v7_ttrades_source_corrected as v7,
)
from qore.infrastructure.traders.vt08_index_c2_positional_r1 import (
    Vt08IndexC2R1Bar,
)

SCHEMA = "qore.trader_lab.vt08_index_r80_source_2r_target_transport.v1"
IDENTITY = "VT08_INDEX_R80_SOURCE_AUTHORIZED_2R_TARGET_TRANSPORT_001"

SOURCE_R79_RUN_ID = 35516202970
SOURCE_R79_ARTIFACT_ID = 10606254504
SOURCE_R79_ARTIFACT_DIGEST = (
    "sha256:3389ebb2abf0faae3a494601bfb54b23bc30546094181d954dac4fe3ccc7632c"
)

CANONICAL_TARGET_R = Decimal("2.5")
SOURCE_TARGET_R = Decimal("2")
PRIMARY_STRESS = Decimal("0.05")
SECONDARY_STRESS = Decimal("0.10")

EXPECTED_BASELINE_SECONDARY = {
    "5Y": {
        "sample": 2448,
        "pf": "1.629558",
        "total_r": "19.570124",
    },
    "2Y": {
        "sample": 1017,
        "pf": "1.523140",
        "total_r": "6.066903",
    },
    "R66": {
        "sample": 773,
        "pf": "0.89946936",
        "total_r": "-1.3721915",
    },
}


def _replay_target(
    stream: Sequence[tuple[Any, r5.ManagedTrade]],
    *,
    bars_by_symbol: dict[str, Sequence[Vt08IndexC2R1Bar]],
    target_r: Decimal,
) -> tuple[tuple[Any, r5.ManagedTrade], ...]:
    policy = r8._target_policy(target_r)
    opened_by_symbol = {
        symbol: tuple(bar.opened_at for bar in bars)
        for symbol, bars in bars_by_symbol.items()
    }
    replayed: list[tuple[Any, r5.ManagedTrade]] = []
    for opportunity, _old_outcome in stream:
        symbol = str(opportunity.signal.symbol)
        replayed.append(
            (
                opportunity,
                r5._manage_trade(
                    opportunity.signal,
                    bars=bars_by_symbol[symbol],
                    opened=opened_by_symbol[symbol],
                    policy=policy,
                ),
            )
        )

    before_ids = [item[0].identity() for item in stream]
    after_ids = [item[0].identity() for item in replayed]
    if before_ids != after_ids:
        raise ValueError("R80 target replay changed structural signal identity")
    return tuple(replayed)


def _apply_exact_allocator(
    stream: Sequence[tuple[Any, r5.ManagedTrade]],
    *,
    bars_by_symbol: dict[str, Sequence[Vt08IndexC2R1Bar]],
) -> tuple[tuple[r15.AssignedTrade, ...], dict[str, Any]]:
    base_r47, r47_diagnostics = r58._exact_r47(
        tuple(stream),
        bars_by_symbol=bars_by_symbol,
    )
    assigned, r58_diagnostics = r55._apply_candidate(
        base_r47,
        bars_by_symbol=bars_by_symbol,
    )
    return tuple(assigned), {
        "r47": r47_diagnostics,
        "r58": r58_diagnostics,
        "concentration": r55._concentration(tuple(assigned)),
    }


def _weighted_metrics(
    assigned: Sequence[r15.AssignedTrade],
    *,
    stress: Decimal,
) -> dict[str, Any]:
    ordered = sorted(
        assigned,
        key=lambda row: (
            row.exited_at,
            row.symbol,
            row.trade_id,
        ),
    )
    return fx._metrics(
        tuple(
            (item.outcome.r_multiple - stress) * item.weight
            for item in ordered
        )
    )


def _boundaries(
    *,
    window_id: str,
    start_date: date,
    end_date: date,
) -> tuple[date, ...]:
    if window_id == "R66":
        return (
            r66.START_DATE,
            r66.BLOCK_BOUNDARY,
            r66.END_DATE_EXCLUSIVE,
        )
    years = 5 if window_id == "5Y" else 2
    return tuple(
        date(
            start_date.year + index,
            start_date.month,
            start_date.day,
        )
        for index in range(years)
    ) + (end_date,)


def _weighted_blocks(
    assigned: Sequence[r15.AssignedTrade],
    *,
    window_id: str,
    start_date: date,
    end_date: date,
    stress: Decimal,
) -> dict[str, Any]:
    boundaries = _boundaries(
        window_id=window_id,
        start_date=start_date,
        end_date=end_date,
    )
    result: dict[str, Any] = {}
    for index in range(len(boundaries) - 1):
        block_start = boundaries[index]
        block_end = boundaries[index + 1]
        rows = [
            item
            for item in assigned
            if block_start
            <= item.exited_at.astimezone(v7._NY).date()
            < block_end
        ]
        result[f"P{index + 1}"] = {
            "start_date": block_start.isoformat(),
            "end_date_exclusive": block_end.isoformat(),
            **_weighted_metrics(rows, stress=stress),
        }
    return result


def _evaluate(
    stream: Sequence[tuple[Any, r5.ManagedTrade]],
    *,
    bars_by_symbol: dict[str, Sequence[Vt08IndexC2R1Bar]],
    window_id: str,
) -> dict[str, Any]:
    start_date, end_date, expected_sample = r74._window_contract(window_id)
    if len(stream) != expected_sample:
        raise ValueError(f"R80 {window_id} sample drift")

    assigned, diagnostics = _apply_exact_allocator(
        stream,
        bars_by_symbol=bars_by_symbol,
    )
    if len(assigned) != expected_sample:
        raise ValueError(f"R80 {window_id} allocator changed trade count")

    primary = _weighted_metrics(assigned, stress=PRIMARY_STRESS)
    secondary = _weighted_metrics(assigned, stress=SECONDARY_STRESS)
    primary_blocks = _weighted_blocks(
        assigned,
        window_id=window_id,
        start_date=start_date,
        end_date=end_date,
        stress=PRIMARY_STRESS,
    )
    secondary_blocks = _weighted_blocks(
        assigned,
        window_id=window_id,
        start_date=start_date,
        end_date=end_date,
        stress=SECONDARY_STRESS,
    )
    return {
        "sample": len(assigned),
        "primary": primary,
        "secondary": secondary,
        "primary_blocks": primary_blocks,
        "secondary_blocks": secondary_blocks,
        "all_primary_blocks_positive": all(
            Decimal(str(row["total_r"])) > 0
            for row in primary_blocks.values()
        ),
        "all_secondary_blocks_positive": all(
            Decimal(str(row["total_r"])) > 0
            for row in secondary_blocks.values()
        ),
        "allocator_diagnostics": diagnostics,
    }


def _window(
    *,
    roots: dict[str, Path],
    window_id: str,
) -> dict[str, Any]:
    canonical, bars_by_symbol, provenance = r74._load_window(
        roots=roots,
        window_id=window_id,
    )
    bars = {
        key: tuple(value)
        for key, value in bars_by_symbol.items()
    }

    baseline = _evaluate(
        canonical,
        bars_by_symbol=bars,
        window_id=window_id,
    )
    expected = EXPECTED_BASELINE_SECONDARY[window_id]
    if baseline["sample"] != expected["sample"]:
        raise ValueError(f"R80 {window_id} baseline sample mismatch")
    baseline_pf = Decimal(str(baseline["secondary"]["profit_factor"] or "0"))
    baseline_total = Decimal(str(baseline["secondary"]["total_r"]))
    if abs(baseline_pf - Decimal(expected["pf"])) > Decimal("0.00001"):
        raise ValueError(f"R80 {window_id} canonical PF reproduction drift")
    if abs(baseline_total - Decimal(expected["total_r"])) > Decimal("0.00001"):
        raise ValueError(f"R80 {window_id} canonical total reproduction drift")

    source_stream = _replay_target(
        canonical,
        bars_by_symbol=bars,
        target_r=SOURCE_TARGET_R,
    )
    source = _evaluate(
        source_stream,
        bars_by_symbol=bars,
        window_id=window_id,
    )

    return {
        "window_id": window_id,
        "canonical_2_5r": baseline,
        "source_2r": source,
        "secondary_delta": {
            "pf": str(
                Decimal(str(source["secondary"]["profit_factor"] or "0"))
                - baseline_pf
            ),
            "total_r": str(
                Decimal(str(source["secondary"]["total_r"]))
                - baseline_total
            ),
        },
        "provenance": provenance,
    }


def build_report(
    *,
    nas100_root: Path,
    sp500_root: Path,
    us30_root: Path,
) -> dict[str, Any]:
    if not freeze.dependency_contract_matches():
        raise ValueError("R80 frozen R58/R59 dependency drift")
    if r67.SOURCE_R66_DECISION != (
        "FAIL_R66_FRESH_HOLDOUT_REJECT_FROZEN_IDENTITY"
    ):
        raise ValueError("R80 source failure decision drift")
    if r79.IDENTITY != (
        "VT08_INDEX_R79_FVG_REACTION_PROTECTED_SWING_GAP_FORENSICS_001"
    ):
        raise ValueError("R80 R79 identity drift")
    if v6.TARGET_R_MULTIPLE != Decimal("2"):
        raise ValueError("R80 V6 source target drift")
    if SOURCE_TARGET_R != v6.TARGET_R_MULTIPLE:
        raise ValueError("R80 source target not bound to V6")

    roots = {
        "NAS100": nas100_root,
        "SP500": sp500_root,
        "US30": us30_root,
    }
    five = _window(roots=roots, window_id="5Y")
    two = _window(roots=roots, window_id="2Y")
    failed = _window(roots=roots, window_id="R66")

    source_windows = (
        five["source_2r"],
        two["source_2r"],
        failed["source_2r"],
    )
    secondary_positive_all = all(
        Decimal(str(row["secondary"]["total_r"])) > 0
        and Decimal(str(row["secondary"]["profit_factor"] or "0"))
        > Decimal("1")
        for row in source_windows
    )
    all_blocks_positive_all = all(
        bool(row["all_secondary_blocks_positive"])
        for row in source_windows
    )

    return {
        "schema": SCHEMA,
        "identity": IDENTITY,
        "source_r79": {
            "identity": r79.IDENTITY,
            "run_id": SOURCE_R79_RUN_ID,
            "artifact_id": SOURCE_R79_ARTIFACT_ID,
            "artifact_digest": SOURCE_R79_ARTIFACT_DIGEST,
        },
        "target_contract": {
            "canonical_research_target_r": str(CANONICAL_TARGET_R),
            "source_authorized_target_r": str(SOURCE_TARGET_R),
            "target_grid_searched": False,
            "v6_target_bound": True,
        },
        "five_year": five,
        "recent_two_year": two,
        "r66_failed_holdout": failed,
        "transport": {
            "source_2r_secondary_positive_pf_gt_1_all_windows": (
                secondary_positive_all
            ),
            "source_2r_all_secondary_blocks_positive_all_windows": (
                all_blocks_positive_all
            ),
            "source_2r_survives_basic_transport": (
                secondary_positive_all and all_blocks_positive_all
            ),
        },
        "decision": "R80_SOURCE_2R_TARGET_TRANSPORT_COMPLETE_NO_CANDIDATE",
        "governance": {
            "research_only": True,
            "consumed_evidence_only": True,
            "fresh_holdout_claim": False,
            "single_source_authorized_target": True,
            "future_information_used": False,
            "signal_surface_changed": False,
            "signals_suppressed": False,
            "daily_bias_changed": False,
            "anchors_changed": False,
            "poi_changed": False,
            "cisd_changed": False,
            "protected_swing_changed": False,
            "entry_changed": False,
            "stop_changed": False,
            "allocator_architecture_changed": False,
            "target_changed_for_research": True,
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
                "five_year": {
                    "canonical_secondary": report["five_year"][
                        "canonical_2_5r"
                    ]["secondary"],
                    "source_2r_secondary": report["five_year"]["source_2r"][
                        "secondary"
                    ],
                    "source_blocks_positive": report["five_year"]["source_2r"][
                        "all_secondary_blocks_positive"
                    ],
                },
                "recent_two_year": {
                    "canonical_secondary": report["recent_two_year"][
                        "canonical_2_5r"
                    ]["secondary"],
                    "source_2r_secondary": report["recent_two_year"]["source_2r"][
                        "secondary"
                    ],
                    "source_blocks_positive": report["recent_two_year"][
                        "source_2r"
                    ]["all_secondary_blocks_positive"],
                },
                "r66": {
                    "canonical_secondary": report["r66_failed_holdout"][
                        "canonical_2_5r"
                    ]["secondary"],
                    "source_2r_secondary": report["r66_failed_holdout"][
                        "source_2r"
                    ]["secondary"],
                    "source_blocks_positive": report["r66_failed_holdout"][
                        "source_2r"
                    ]["all_secondary_blocks_positive"],
                },
                "transport": report["transport"],
                "decision": report["decision"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
