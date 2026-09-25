"""VT08 Index R126 — targeted source-authorized 2R management ablation.

R123 isolated one STANDARD causal state with negative stressed economics in all
three consumed windows:

    SWEEP_REVERSAL | PRIOR_DEEPER_THAN_FINAL_PS

R124 (targeted source retest) and R125 (targeted persistent-CISD replacement)
both improved this state but failed to repair R66. R126 therefore isolates the
remaining source-authorized management question without changing signal or
risk geometry.

TTrades/V6 source material freezes 2R as the initial fixed target. The current
R100+ research lineage uses 2.5R. R126 changes one variable only:
- exact target-state trades are replayed with the source-authorized 2R target;
- entry, Protected-Swing stop, POI, CISD, continuation, market, side and anchor
  remain the exact canonical values;
- all other STANDARD and Explicit-PS trades remain canonical 2.5R;
- R102 effective weights remain frozen and are never recomputed;
- signal count is fixed at 2448 / 1017 / 773.

No target grid is searched. 2R is fixed by source before economic measurement.
All windows are consumed evidence; this is falsification only and cannot create
certification, LIVE or real-capital authority.
"""

from __future__ import annotations

import argparse
import json
from collections.abc import Sequence
from dataclasses import replace
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

from qore.infrastructure.trader_lab import (
    vt08_index_cibo_2y_management_round5 as r5,
)
from qore.infrastructure.trader_lab import (
    vt08_index_r8_priority_poi_rearm_reset as r8,
)
from qore.infrastructure.trader_lab import (
    vt08_index_r15_concurrent_portfolio_validation as r15,
)
from qore.infrastructure.trader_lab import (
    vt08_index_r58_exact_r47_distributed_risk as r58,
)
from qore.infrastructure.trader_lab import (
    vt08_index_r74_ambiguous_bias_resolvers as r74,
)
from qore.infrastructure.trader_lab import (
    vt08_index_r80_source_2r_target_transport as r80,
)
from qore.infrastructure.trader_lab import (
    vt08_index_r82_protected_swing_source_qualification as r82,
)
from qore.infrastructure.trader_lab import (
    vt08_index_r102_source_confidence_risk_ablation as r102,
)
from qore.infrastructure.trader_lab import (
    vt08_index_r107_standard_economic_root_attribution as r107,
)
from qore.infrastructure.trader_lab import (
    vt08_index_r108_standard_source_retest_execution_replay as r108,
)
from qore.infrastructure.trader_lab import (
    vt08_index_r124_targeted_source_retest as r124,
)
from qore.infrastructure.trader_lab import (
    vt08_index_r125_targeted_persistent_cisd as r125,
)
from qore.infrastructure.traders.contracts import DemoTradingSetupSide
from qore.infrastructure.traders.vt08_index_c2_positional_r1 import (
    Vt08IndexC2R1Bar,
)

SCHEMA = "qore.trader_lab.vt08_index_r126_targeted_source_2r.v1"
IDENTITY = "VT08_INDEX_R126_TARGETED_SOURCE_AUTHORIZED_2R_ABLATION_001"

SOURCE_R125_RUN_ID = 36059043366
SOURCE_R125_ARTIFACT_ID = 10834116084
SOURCE_R125_ARTIFACT_DIGEST = (
    "sha256:203ac657aefac8762fb3f38c66f90931"
    "21626d5ed7460cea48fdc596b61c0192"
)

TARGET_STATE = r124.TARGET_STATE
EXPECTED_TARGET_STATE = r124.EXPECTED_TARGET_STATE
EXPECTED_CANONICAL = r124.EXPECTED_CANONICAL
EXPECTED_STANDARD = r124.EXPECTED_STANDARD
SOURCE_TARGET_R = r80.SOURCE_TARGET_R


def _target_price(
    *,
    entry: Decimal,
    stop: Decimal,
    side: DemoTradingSetupSide,
) -> Decimal:
    risk = abs(entry - stop)
    if risk <= 0:
        raise ValueError("R126 invalid canonical risk")
    if side is DemoTradingSetupSide.LONG:
        return entry + SOURCE_TARGET_R * risk
    return entry - SOURCE_TARGET_R * risk


def _replay_2r(
    item: r15.AssignedTrade,
    *,
    bars: Sequence[Vt08IndexC2R1Bar],
    opened: Sequence[datetime],
) -> r15.AssignedTrade:
    signal = item.opportunity.signal
    new_signal = replace(
        signal,
        target=_target_price(
            entry=signal.entry,
            stop=signal.stop,
            side=signal.side,
        ),
    )
    new_outcome = r5._manage_trade(
        new_signal,
        bars=bars,
        opened=opened,
        policy=r8._target_policy(SOURCE_TARGET_R),
    )
    return replace(
        item,
        opportunity=replace(
            item.opportunity,
            signal=new_signal,
        ),
        outcome=new_outcome,
    )


def _delta(
    after: dict[str, Any],
    before: dict[str, Any],
    *,
    field: str,
) -> str:
    return str(
        Decimal(str(after[field]))
        - Decimal(str(before[field]))
    )


def _window(
    *,
    roots: dict[str, Path],
    window_id: str,
) -> dict[str, Any]:
    canonical, bars_by_symbol_raw, provenance = r74._load_window(
        roots=roots,
        window_id=window_id,
    )
    start_date, end_date, expected = r74._window_contract(window_id)
    if expected != EXPECTED_CANONICAL[window_id]:
        raise ValueError(f"R126 {window_id} canonical contract drift")

    bars_by_symbol: dict[str, Sequence[Vt08IndexC2R1Bar]] = {
        symbol: tuple(bars)
        for symbol, bars in bars_by_symbol_raw.items()
    }
    opened_by_symbol = {
        symbol: tuple(bar.opened_at.astimezone(UTC) for bar in bars)
        for symbol, bars in bars_by_symbol.items()
    }
    indexed_by_symbol = {
        symbol: {
            bar.opened_at.astimezone(UTC): bar
            for bar in bars
        }
        for symbol, bars in bars_by_symbol.items()
    }

    base, _base_diag = r58._exact_r47(
        tuple(canonical),
        bars_by_symbol=bars_by_symbol,
    )
    control, control_diag = r102._apply_confidence_policy(
        tuple(base),
        bars_by_symbol=bars_by_symbol,
        policy_id=r102.POLICY_EXPLICIT_FULL,
    )
    control = tuple(control)
    if len(control) != expected:
        raise ValueError(f"R126 {window_id} control density drift")

    standard_ids = r107._standard_ids(
        control,
        bars_by_symbol=bars_by_symbol,
    )
    if len(standard_ids) != EXPECTED_STANDARD[window_id]:
        raise ValueError(f"R126 {window_id} STANDARD drift")

    h4_cache = {
        symbol: r82._h4_bar_cache(bars)
        for symbol, bars in bars_by_symbol.items()
    }

    replayed: list[r15.AssignedTrade] = []
    target_before: list[r15.AssignedTrade] = []
    target_after: list[r15.AssignedTrade] = []
    target_count = 0

    for item in control:
        identity = item.opportunity.identity()
        if identity not in standard_ids:
            replayed.append(item)
            continue

        state, _inside = r124._state_for_item(
            item,
            indexed_by_symbol=indexed_by_symbol,
            h4_cache=h4_cache,
        )
        if state != TARGET_STATE:
            replayed.append(item)
            continue

        target_count += 1
        target_before.append(item)
        replacement = _replay_2r(
            item,
            bars=bars_by_symbol[item.symbol],
            opened=opened_by_symbol[item.symbol],
        )
        replayed.append(replacement)
        target_after.append(replacement)

    if target_count != EXPECTED_TARGET_STATE[window_id]:
        raise ValueError(
            f"R126 {window_id} target-state drift: "
            f"{target_count} != {EXPECTED_TARGET_STATE[window_id]}"
        )

    replayed_tuple = tuple(replayed)
    if len(replayed_tuple) != len(control):
        raise ValueError("R126 replay changed trade count")

    before_weights = {
        item.trade_id: item.weight
        for item in control
    }
    after_weights = {
        item.trade_id: item.weight
        for item in replayed_tuple
    }
    if before_weights != after_weights:
        raise ValueError("R126 frozen R102 weights changed")

    baseline = r108._bundle(
        control,
        bars_by_symbol=bars_by_symbol,
        opened_by_symbol=opened_by_symbol,
        window_id=window_id,
        start_date=start_date,
        end_date=end_date,
    )
    replay = r108._bundle(
        replayed_tuple,
        bars_by_symbol=bars_by_symbol,
        opened_by_symbol=opened_by_symbol,
        window_id=window_id,
        start_date=start_date,
        end_date=end_date,
    )
    target_before_bundle = r108._cohort_bundle(target_before)
    target_after_bundle = r108._cohort_bundle(target_after)

    converted_to_target = sum(
        before.outcome.exit_reason != "target"
        and after.outcome.exit_reason == "target"
        for before, after in zip(
            target_before,
            target_after,
            strict=True,
        )
    )
    changed_outcome_count = sum(
        (
            before.outcome.r_multiple != after.outcome.r_multiple
            or before.outcome.exited_at != after.outcome.exited_at
            or before.outcome.exit_reason != after.outcome.exit_reason
        )
        for before, after in zip(
            target_before,
            target_after,
            strict=True,
        )
    )

    return {
        "window_id": window_id,
        "canonical_sample": expected,
        "standard_sample": len(standard_ids),
        "target_state": TARGET_STATE,
        "target_state_sample": target_count,
        "source_target_r": str(SOURCE_TARGET_R),
        "changed_outcome_count": changed_outcome_count,
        "converted_to_2r_target_count": converted_to_target,
        "control_policy": r102.POLICY_EXPLICIT_FULL,
        "control_diagnostics": control_diag,
        "full_portfolio": {
            "baseline_2_5r": baseline,
            "targeted_source_2r": replay,
            "primary_total_r_delta": _delta(
                replay["primary"],
                baseline["primary"],
                field="total_r",
            ),
            "secondary_total_r_delta": _delta(
                replay["secondary"],
                baseline["secondary"],
                field="total_r",
            ),
        },
        "target_state_cohort": {
            "baseline_2_5r": target_before_bundle,
            "source_2r": target_after_bundle,
            "primary_total_r_delta": _delta(
                target_after_bundle["primary"],
                target_before_bundle["primary"],
                field="total_r",
            ),
            "secondary_total_r_delta": _delta(
                target_after_bundle["secondary"],
                target_before_bundle["secondary"],
                field="total_r",
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
    if r125.IDENTITY != (
        "VT08_INDEX_R125_TARGETED_PERSISTENT_CISD_REPLACEMENT_001"
    ):
        raise ValueError("R126 R125 identity drift")
    if SOURCE_TARGET_R != Decimal("2"):
        raise ValueError("R126 source target drift")
    if r80.CANONICAL_TARGET_R != Decimal("2.5"):
        raise ValueError("R126 canonical target drift")

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
        "source_r125": {
            "run_id": SOURCE_R125_RUN_ID,
            "artifact_id": SOURCE_R125_ARTIFACT_ID,
            "artifact_digest": SOURCE_R125_ARTIFACT_DIGEST,
            "decision": (
                "R125_TARGETED_PERSISTENT_CISD_REPLACEMENT_COMPLETE_"
                "NO_CANDIDATE_SELECTED"
            ),
        },
        "source_contract": {
            "source_target_r": str(SOURCE_TARGET_R),
            "canonical_research_target_r": str(r80.CANONICAL_TARGET_R),
            "target_grid_searched": False,
            "target_state": TARGET_STATE,
            "entry_changed": False,
            "protected_swing_stop_changed": False,
            "risk_allocator": "R102_FIXED_WEIGHTS_NO_RECOMPUTE",
            "signal_surface_changed": False,
            "signals_suppressed": False,
        },
        "five_year": five,
        "recent_two_year": two,
        "r66_failed_holdout": failed,
        "decision": (
            "R126_TARGETED_SOURCE_AUTHORIZED_2R_ABLATION_COMPLETE_"
            "NO_CANDIDATE_SELECTED"
        ),
        "governance": {
            "research_only": True,
            "consumed_evidence_only": True,
            "fresh_holdout_claim": False,
            "single_preregistered_variant": True,
            "signals_suppressed": False,
            "trade_count_changed": False,
            "entry_changed": False,
            "protected_swing_stop_changed": False,
            "risk_changed": False,
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
                    "changed": report["five_year"]["changed_outcome_count"],
                    "converted": report["five_year"][
                        "converted_to_2r_target_count"
                    ],
                    "full_delta": report["five_year"]["full_portfolio"][
                        "secondary_total_r_delta"
                    ],
                    "state_delta": report["five_year"][
                        "target_state_cohort"
                    ]["secondary_total_r_delta"],
                },
                "recent_two_year": {
                    "changed": report["recent_two_year"][
                        "changed_outcome_count"
                    ],
                    "converted": report["recent_two_year"][
                        "converted_to_2r_target_count"
                    ],
                    "full_delta": report["recent_two_year"][
                        "full_portfolio"
                    ]["secondary_total_r_delta"],
                    "state_delta": report["recent_two_year"][
                        "target_state_cohort"
                    ]["secondary_total_r_delta"],
                },
                "r66": {
                    "changed": report["r66_failed_holdout"][
                        "changed_outcome_count"
                    ],
                    "converted": report["r66_failed_holdout"][
                        "converted_to_2r_target_count"
                    ],
                    "full_delta": report["r66_failed_holdout"][
                        "full_portfolio"
                    ]["secondary_total_r_delta"],
                    "state_delta": report["r66_failed_holdout"][
                        "target_state_cohort"
                    ]["secondary_total_r_delta"],
                },
                "decision": report["decision"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
