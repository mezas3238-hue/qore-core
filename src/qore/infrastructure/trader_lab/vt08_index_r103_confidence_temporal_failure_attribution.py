"""VT08 Index R103 — source-confidence temporal failure attribution.

R102 established a causal improvement without changing the signal surface:
EXPLICIT_FULL_R58_STANDARD_BASE turned consumed R66 positive at both 0.05R and
0.10R stress while preserving 2448 / 1017 / 773 signals and low DD. It still
failed the five-year temporal contract and R66 block/PF gates.

R103 does not create another policy. It freezes the R102 confidence policy and
attributes the remaining failure by:
- temporal block;
- STANDARD vs explicit PS-mechanism confidence;
- market, side, anchor;
- wick state;
- whether final risk increased, decreased or stayed equal to exact R47 base.

No policy selection or PnL-driven filter is permitted in this stage.
"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from collections.abc import Callable, Sequence
from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

from qore.infrastructure.trader_lab import (
    vt08_index_r6_5y_failure_forensics as fx,
)
from qore.infrastructure.trader_lab import (
    vt08_index_r15_concurrent_portfolio_validation as r15,
)
from qore.infrastructure.trader_lab import (
    vt08_index_r35_five_year_temporal_contract as r35,
)
from qore.infrastructure.trader_lab import (
    vt08_index_r45_frozen_recent_2y_reproduction as r45,
)
from qore.infrastructure.trader_lab import (
    vt08_index_r58_exact_r47_distributed_risk as r58,
)
from qore.infrastructure.trader_lab import (
    vt08_index_r66_fresh_historical_holdout as r66,
)
from qore.infrastructure.trader_lab import (
    vt08_index_r74_ambiguous_bias_resolvers as r74,
)
from qore.infrastructure.trader_lab import (
    vt08_index_r82_protected_swing_source_qualification as r82,
)
from qore.infrastructure.trader_lab import (
    vt08_index_r99_standard_ideal_wick_state as r99,
)
from qore.infrastructure.trader_lab import (
    vt08_index_r102_source_confidence_risk_ablation as r102,
)
from qore.infrastructure.trader_lab import (
    vt08_index_v7_ttrades_source_corrected as v7,
)
from qore.infrastructure.traders.vt08_index_c2_positional_r1 import (
    Vt08IndexC2R1Bar,
)

SCHEMA = "qore.trader_lab.vt08_index_r103_confidence_temporal_failure_attribution.v1"
IDENTITY = "VT08_INDEX_R103_SOURCE_CONFIDENCE_TEMPORAL_FAILURE_ATTRIBUTION_001"

SOURCE_R102_RUN_ID = 35554460252
SOURCE_R102_ARTIFACT_ID = 10619927443
SOURCE_R102_ARTIFACT_DIGEST = (
    "sha256:cb9c87bca14b6ab00cb910bf5dde8e380dd3453ecc833f3402c545ae197106a4"
)
POLICY_ID = r102.POLICY_EXPLICIT_FULL


def _weighted_metrics(
    rows: Sequence[r15.AssignedTrade],
    *,
    stress: Decimal,
) -> dict[str, Any]:
    values = tuple(
        (row.outcome.r_multiple - stress) * row.weight
        for row in sorted(
            rows,
            key=lambda item: (
                item.exited_at.astimezone(UTC),
                item.symbol,
                item.trade_id,
            ),
        )
    )
    return fx._metrics(values)


def _group_metrics(
    rows: Sequence[r15.AssignedTrade],
    *,
    key_fn: Callable[[r15.AssignedTrade], str],
) -> dict[str, Any]:
    grouped: dict[str, list[r15.AssignedTrade]] = defaultdict(list)
    for row in rows:
        grouped[key_fn(row)].append(row)
    return {
        key: {
            "sample": len(items),
            "primary": _weighted_metrics(
                items,
                stress=r102.PRIMARY_STRESS,
            ),
            "secondary": _weighted_metrics(
                items,
                stress=r102.SECONDARY_STRESS,
            ),
        }
        for key, items in sorted(grouped.items())
    }


def _block_boundaries(window_id: str) -> tuple[date, ...]:
    if window_id == "5Y":
        return r35._annual_boundaries()
    if window_id == "2Y":
        return (
            r45.START_DATE,
            date(2025, 9, 15),
            r45.END_DATE_EXCLUSIVE,
        )
    if window_id == "R66":
        return (
            r66.START_DATE,
            r66.BLOCK_BOUNDARY,
            r66.END_DATE_EXCLUSIVE,
        )
    raise ValueError(f"R103 unsupported window: {window_id}")


def _block_name(window_id: str, index: int) -> str:
    return f"B{index + 1}" if window_id == "R66" else f"Y{index + 1}"


def _wick_state(
    item: r15.AssignedTrade,
    *,
    h4_cache: dict[str, dict[datetime, tuple[Vt08IndexC2R1Bar, ...]]],
) -> str:
    signal = item.opportunity.signal
    inside = h4_cache[item.symbol].get(
        signal.h4_opened_at.astimezone(UTC)
    )
    if inside is None:
        raise ValueError("R103 canonical H4 missing for wick state")
    observed = r99._observed_through_signal(
        inside,
        signal_at=signal.signal_at,
    )
    state, _adverse, _directional = r99._wick_state(
        observed,
        side=signal.side,
        h4_open=inside[0].open,
        entry=signal.entry,
    )
    return state


def _window(
    *,
    roots: dict[str, Path],
    window_id: str,
) -> dict[str, Any]:
    stream, bars_by_symbol, provenance = r74._load_window(
        roots=roots,
        window_id=window_id,
    )
    _start, _end, expected = r74._window_contract(window_id)
    bars: dict[str, Sequence[Vt08IndexC2R1Bar]] = {
        key: tuple(value)
        for key, value in bars_by_symbol.items()
    }

    base, _base_diag = r58._exact_r47(
        tuple(stream),
        bars_by_symbol=bars,
    )
    base = tuple(base)
    assigned, policy_diag = r102._apply_confidence_policy(
        base,
        bars_by_symbol=bars,
        policy_id=POLICY_ID,
    )
    assigned = tuple(assigned)
    if len(assigned) != expected:
        raise ValueError(f"R103 {window_id} sample drift")

    base_by_identity = {
        item.opportunity.identity(): item
        for item in base
    }
    if len(base_by_identity) != expected:
        raise ValueError("R103 R47 identity collision")

    h4_cache = {
        symbol: r82._h4_bar_cache(symbol_bars)
        for symbol, symbol_bars in bars.items()
    }
    confidence: dict[tuple[object, ...], str] = {}
    family: dict[tuple[object, ...], str] = {}
    wick: dict[tuple[object, ...], str] = {}
    risk_change: dict[tuple[object, ...], str] = {}

    for item in assigned:
        identity = item.opportunity.identity()
        classification = r82._classify_opportunity(
            item.opportunity,
            h4_bars=h4_cache[item.symbol],
        )
        old_family = str(classification["family"])
        family[identity] = old_family
        confidence[identity] = (
            "STANDARD_WITHOUT_EXTRA_PS"
            if old_family == r82.FAMILY_UNQUALIFIED
            else "EXPLICIT_PS_MECHANISM"
        )
        wick[identity] = _wick_state(
            item,
            h4_cache=h4_cache,
        )
        base_item = base_by_identity[identity]
        if item.weight > base_item.weight:
            risk_change[identity] = "RISK_INCREASED_VS_R47"
        elif item.weight < base_item.weight:
            risk_change[identity] = "RISK_DECREASED_VS_R47"
        else:
            risk_change[identity] = "RISK_UNCHANGED_VS_R47"

    boundaries = _block_boundaries(window_id)
    blocks: dict[str, Any] = {}
    for index in range(len(boundaries) - 1):
        start = boundaries[index]
        end = boundaries[index + 1]
        rows = tuple(
            item
            for item in assigned
            if start
            <= item.exited_at.astimezone(v7._NY).date()
            < end
        )
        block_id = _block_name(window_id, index)

        blocks[block_id] = {
            "start_date": start.isoformat(),
            "end_date_exclusive": end.isoformat(),
            "sample": len(rows),
            "primary": _weighted_metrics(
                rows,
                stress=r102.PRIMARY_STRESS,
            ),
            "secondary": _weighted_metrics(
                rows,
                stress=r102.SECONDARY_STRESS,
            ),
            "by_confidence": _group_metrics(
                rows,
                key_fn=lambda row: confidence[
                    row.opportunity.identity()
                ],
            ),
            "by_market": _group_metrics(
                rows,
                key_fn=lambda row: row.symbol,
            ),
            "by_side": _group_metrics(
                rows,
                key_fn=lambda row: row.opportunity.signal.side.value,
            ),
            "by_anchor": _group_metrics(
                rows,
                key_fn=lambda row: str(
                    row.opportunity.signal.h4_opened_at
                    .astimezone(v7._NY).hour
                ),
            ),
            "by_market_side": _group_metrics(
                rows,
                key_fn=lambda row: (
                    f"{row.symbol}|"
                    f"{row.opportunity.signal.side.value}"
                ),
            ),
            "by_wick_state": _group_metrics(
                rows,
                key_fn=lambda row: wick[
                    row.opportunity.identity()
                ],
            ),
            "by_old_ps_family": _group_metrics(
                rows,
                key_fn=lambda row: family[
                    row.opportunity.identity()
                ],
            ),
            "by_risk_change_vs_r47": _group_metrics(
                rows,
                key_fn=lambda row: risk_change[
                    row.opportunity.identity()
                ],
            ),
        }

    return {
        "window_id": window_id,
        "sample": expected,
        "policy_id": POLICY_ID,
        "policy_diagnostics": policy_diag,
        "blocks": blocks,
        "provenance": provenance,
    }


def _negative_blocks(section: dict[str, Any]) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for block_id, block in section["blocks"].items():
        primary_total = Decimal(
            str(block["primary"]["total_r"])
        )
        secondary_total = Decimal(
            str(block["secondary"]["total_r"])
        )
        if primary_total <= 0 or secondary_total <= 0:
            result.append(
                {
                    "block_id": block_id,
                    "primary_total_r": str(primary_total),
                    "secondary_total_r": str(secondary_total),
                    "by_confidence": block["by_confidence"],
                    "by_market": block["by_market"],
                    "by_side": block["by_side"],
                    "by_anchor": block["by_anchor"],
                    "by_market_side": block["by_market_side"],
                    "by_wick_state": block["by_wick_state"],
                    "by_risk_change_vs_r47": block[
                        "by_risk_change_vs_r47"
                    ],
                }
            )
    return result


def build_report(
    *,
    nas100_root: Path,
    sp500_root: Path,
    us30_root: Path,
) -> dict[str, Any]:
    if r102.IDENTITY != (
        "VT08_INDEX_R102_SOURCE_CONFIDENCE_RISK_TRANSPORT_ABLATION_001"
    ):
        raise ValueError("R103 R102 identity drift")

    roots = {
        "NAS100": nas100_root,
        "SP500": sp500_root,
        "US30": us30_root,
    }
    five = _window(roots=roots, window_id="5Y")
    two = _window(roots=roots, window_id="2Y")
    failed = _window(roots=roots, window_id="R66")

    return {
        "schema": SCHEMA,
        "identity": IDENTITY,
        "source_r102": {
            "run_id": SOURCE_R102_RUN_ID,
            "artifact_id": SOURCE_R102_ARTIFACT_ID,
            "artifact_digest": SOURCE_R102_ARTIFACT_DIGEST,
            "policy_under_attribution": POLICY_ID,
        },
        "five_year": five,
        "recent_two_year": two,
        "r66_failed_holdout": failed,
        "negative_blocks": {
            "five_year": _negative_blocks(five),
            "recent_two_year": _negative_blocks(two),
            "r66": _negative_blocks(failed),
        },
        "decision": "R103_CONFIDENCE_TEMPORAL_FAILURE_ATTRIBUTION_COMPLETE_NO_RULE_CHANGE",
        "governance": {
            "forensics_only": True,
            "consumed_evidence_only": True,
            "fresh_holdout_claim": False,
            "policy_changed": False,
            "signals_suppressed": False,
            "pnl_used_for_runtime_rule": False,
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
        json.dumps(report, indent=2, sort_keys=True, allow_nan=False)
        + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "identity": IDENTITY,
                "negative_blocks": report["negative_blocks"],
                "decision": report["decision"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
