"""VT08 Index R124 — targeted source-retest execution ablation.

R123 proved that the only mechanism/relation state with negative stressed
economics in all three consumed windows is:

    SWEEP_REVERSAL | PRIOR_DEEPER_THAN_FINAL_PS

and that this state is already 98-100% saturated at the existing 0.005R risk
floor. Further sizing demotion therefore cannot materially repair it.

R124 changes one variable only in a bounded consumed-evidence ablation:
STANDARD trades in that exact causal state use the already-frozen R108 source
retest execution when a valid retest occurs. If no causal retest occurs before
Protected-Swing invalidation / H4 end, the original continuation-close entry
remains in force.

Contracts:
- exact canonical signal surface is preserved;
- no signal is suppressed and no second trade is created;
- only the exact R123 adverse state is eligible for reroute;
- explicit-PS and all other STANDARD states remain unchanged;
- stop stays the original Protected Swing;
- target stays exactly 2.5R from whichever valid entry is used;
- R102 effective weights are frozen, not recomputed;
- R108 same-fill-bar target-credit prohibition is retained;
- no market, side, anchor, year, calendar, target, stop, or risk grid search.

This is research-only consumed evidence and cannot create certification or
LIVE/real-capital authority.
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
    vt08_index_r15_concurrent_portfolio_validation as r15,
)
from qore.infrastructure.trader_lab import (
    vt08_index_r58_exact_r47_distributed_risk as r58,
)
from qore.infrastructure.trader_lab import (
    vt08_index_r74_ambiguous_bias_resolvers as r74,
)
from qore.infrastructure.trader_lab import (
    vt08_index_r82_protected_swing_source_qualification as r82,
)
from qore.infrastructure.trader_lab import (
    vt08_index_r89_execution_path_coverage as r89,
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
    vt08_index_r118_pre_cisd_failed_attempt_journey as r118,
)
from qore.infrastructure.trader_lab import (
    vt08_index_r119_previous_source_day_alignment as r119,
)
from qore.infrastructure.trader_lab import (
    vt08_index_r120_daily_bias_mechanism as r120,
)
from qore.infrastructure.trader_lab import (
    vt08_index_r123_causal_state_risk_saturation as r123,
)
from qore.infrastructure.trader_lab import (
    vt08_index_v7_ttrades_source_corrected as v7,
)
from qore.infrastructure.traders.vt08_index_c2_positional_r1 import (
    Vt08IndexC2R1Bar,
)

SCHEMA = "qore.trader_lab.vt08_index_r124_targeted_source_retest.v1"
IDENTITY = "VT08_INDEX_R124_TARGETED_SOURCE_RETEST_ABLATION_001"

SOURCE_R123_RUN_ID = 36057291367
SOURCE_R123_ARTIFACT_ID = 10832868254
SOURCE_R123_ARTIFACT_DIGEST = (
    "sha256:fe8f42308f272443732f2706ec9e8170"
    "fea66c9d8023d419aa388042d84e9bd1"
)

TARGET_STATE = "SWEEP_REVERSAL|PRIOR_DEEPER_THAN_FINAL_PS"
EXPECTED_TARGET_STATE = {
    "5Y": 235,
    "2Y": 110,
    "R66": 101,
}
EXPECTED_CANONICAL = r108.EXPECTED_CANONICAL
EXPECTED_STANDARD = r108.EXPECTED_STANDARD


def _is_target_state(*, mechanism: str, relation: str) -> bool:
    return (
        mechanism == r120.MECHANISM_REVERSAL
        and relation == "PRIOR_DEEPER_THAN_FINAL_PS"
    )


def _state_for_item(
    item: r15.AssignedTrade,
    *,
    indexed_by_symbol: dict[str, dict[datetime, Vt08IndexC2R1Bar]],
    h4_cache: dict[str, dict[datetime, tuple[Vt08IndexC2R1Bar, ...]]],
) -> tuple[str, tuple[Vt08IndexC2R1Bar, ...]]:
    signal = item.opportunity.signal
    previous_day, current_day = r119._source_days(
        indexed_by_symbol[item.symbol],
        before_local=signal.h4_opened_at.astimezone(v7._NY),
    )
    mechanism = r120._bias_mechanism(
        previous_day=previous_day,
        current_day=current_day,
        side=signal.side,
    )
    inside = h4_cache[item.symbol].get(
        signal.h4_opened_at.astimezone(UTC)
    )
    if inside is None:
        raise ValueError("R124 canonical H4 missing")
    touch_index = next(
        (
            index
            for index, bar in enumerate(inside)
            if bar.opened_at.astimezone(UTC)
            == item.opportunity.poi_touch_at.astimezone(UTC)
        ),
        None,
    )
    if touch_index is None:
        raise ValueError("R124 POI touch missing")
    journey = r118._cisd_journey(
        inside,
        side=signal.side,
        start_index=touch_index,
    )
    if journey is None:
        raise ValueError("R124 canonical CISD journey missing")
    relation = r118._prior_extreme_relation(
        side=signal.side,
        final_extreme=Decimal(str(journey["extreme"])),
        failed_attempts=tuple(journey["failed_attempts"]),
    )
    return f"{mechanism}|{relation}", inside


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
        raise ValueError(f"R124 {window_id} canonical contract drift")

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
        raise ValueError(f"R124 {window_id} control density drift")

    standard_ids = r107._standard_ids(
        control,
        bars_by_symbol=bars_by_symbol,
    )
    if len(standard_ids) != EXPECTED_STANDARD[window_id]:
        raise ValueError(f"R124 {window_id} STANDARD drift")

    h4_cache = {
        symbol: r82._h4_bar_cache(bars)
        for symbol, bars in bars_by_symbol.items()
    }

    replayed: list[r15.AssignedTrade] = []
    target_before: list[r15.AssignedTrade] = []
    target_after: list[r15.AssignedTrade] = []
    retest_before: list[r15.AssignedTrade] = []
    retest_after: list[r15.AssignedTrade] = []
    target_count = 0
    retest_count = 0
    fallback_count = 0

    for item in control:
        identity = item.opportunity.identity()
        if identity not in standard_ids:
            replayed.append(item)
            continue

        state, inside = _state_for_item(
            item,
            indexed_by_symbol=indexed_by_symbol,
            h4_cache=h4_cache,
        )
        if state != TARGET_STATE:
            replayed.append(item)
            continue

        target_count += 1
        target_before.append(item)
        signal = item.opportunity.signal

        continuation_index = next(
            (
                index
                for index, bar in enumerate(inside)
                if bar.closed_at.astimezone(UTC)
                == signal.signal_at.astimezone(UTC)
            ),
            None,
        )
        if continuation_index is None or continuation_index <= 0:
            raise ValueError("R124 continuation bar not found")

        retest_index = r89._retest_fill_index(
            inside,
            continuation_index=continuation_index,
            side=signal.side,
            protected_swing=signal.protected_swing_extreme,
            model_kind=signal.model_kind,
            h4_open=inside[0].open,
        )
        if retest_index is None:
            replayed.append(item)
            target_after.append(item)
            fallback_count += 1
            continue

        retest_level = r89._continuation_breakout_level(
            inside,
            continuation_index=continuation_index,
            side=signal.side,
        )
        fill_bar = inside[retest_index]
        new_signal = r108._build_retest_signal(
            signal,
            retest_level=retest_level,
            retest_window_opened_at=fill_bar.opened_at,
        )
        new_outcome = r108._manage_retest(
            new_signal,
            fill_bar=fill_bar,
            bars=bars_by_symbol[item.symbol],
            opened=opened_by_symbol[item.symbol],
        )
        replayed_item = replace(
            item,
            opportunity=replace(
                item.opportunity,
                signal=new_signal,
            ),
            outcome=new_outcome,
        )
        replayed.append(replayed_item)
        target_after.append(replayed_item)
        retest_before.append(item)
        retest_after.append(replayed_item)
        retest_count += 1

    if target_count != EXPECTED_TARGET_STATE[window_id]:
        raise ValueError(
            f"R124 {window_id} target-state drift: "
            f"{target_count} != {EXPECTED_TARGET_STATE[window_id]}"
        )
    if target_count != retest_count + fallback_count:
        raise ValueError("R124 target routing count mismatch")

    replayed_tuple = tuple(replayed)
    if len(replayed_tuple) != len(control):
        raise ValueError("R124 replay changed trade count")

    before_weights = {
        item.trade_id: item.weight
        for item in control
    }
    after_weights = {
        item.trade_id: item.weight
        for item in replayed_tuple
    }
    if before_weights != after_weights:
        raise ValueError("R124 frozen R102 weights changed")

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
    retest_before_bundle = r108._cohort_bundle(retest_before)
    retest_after_bundle = r108._cohort_bundle(retest_after)

    return {
        "window_id": window_id,
        "canonical_sample": expected,
        "standard_sample": len(standard_ids),
        "target_state": TARGET_STATE,
        "target_state_sample": target_count,
        "target_state_retest_count": retest_count,
        "target_state_close_fallback_count": fallback_count,
        "target_state_retest_fraction": str(
            Decimal(retest_count) / Decimal(target_count)
        ),
        "control_policy": r102.POLICY_EXPLICIT_FULL,
        "control_diagnostics": control_diag,
        "full_portfolio": {
            "baseline": baseline,
            "targeted_retest": replay,
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
            "baseline": target_before_bundle,
            "targeted_retest": target_after_bundle,
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
        "retest_available_only": {
            "baseline_close": retest_before_bundle,
            "retest": retest_after_bundle,
            "primary_total_r_delta": _delta(
                retest_after_bundle["primary"],
                retest_before_bundle["primary"],
                field="total_r",
            ),
            "secondary_total_r_delta": _delta(
                retest_after_bundle["secondary"],
                retest_before_bundle["secondary"],
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
    if r123.IDENTITY != (
        "VT08_INDEX_R123_R120_CAUSAL_STATE_RISK_SATURATION_001"
    ):
        raise ValueError("R124 R123 identity drift")
    if r108.TARGET_R != Decimal("2.5"):
        raise ValueError("R124 R108 target drift")

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
        "source_r123": {
            "run_id": SOURCE_R123_RUN_ID,
            "artifact_id": SOURCE_R123_ARTIFACT_ID,
            "artifact_digest": SOURCE_R123_ARTIFACT_DIGEST,
            "decision": (
                "R123_R120_CAUSAL_STATE_RISK_SATURATION_COMPLETE_"
                "NO_RULE_CHANGE"
            ),
        },
        "preregistered_contract": {
            "target_state": TARGET_STATE,
            "same_setup_only": True,
            "retest_creates_second_trade": False,
            "target_state_only_rerouted": True,
            "other_standard_unchanged": True,
            "explicit_ps_unchanged": True,
            "no_retest_fallback": "CANONICAL_CONTINUATION_CLOSE",
            "stop": "SAME_PROTECTED_SWING",
            "target_r": str(r108.TARGET_R),
            "risk_allocator": "R102_FIXED_WEIGHTS_NO_RECOMPUTE",
            "retest_bar_target_credit": False,
            "signal_surface_changed": False,
            "signals_suppressed": False,
        },
        "five_year": five,
        "recent_two_year": two,
        "r66_failed_holdout": failed,
        "decision": (
            "R124_TARGETED_SOURCE_RETEST_ABLATION_COMPLETE_"
            "NO_CANDIDATE_SELECTED"
        ),
        "governance": {
            "research_only": True,
            "consumed_evidence_only": True,
            "fresh_holdout_claim": False,
            "single_preregistered_variant": True,
            "signal_surface_changed": False,
            "signals_suppressed": False,
            "trade_count_changed": False,
            "retest_double_counted": False,
            "risk_changed": False,
            "protected_swing_stop_changed": False,
            "target_r_changed": False,
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
                    "routing": {
                        "sample": report["five_year"]["target_state_sample"],
                        "retest": report["five_year"][
                            "target_state_retest_count"
                        ],
                        "fallback": report["five_year"][
                            "target_state_close_fallback_count"
                        ],
                    },
                    "full_delta": report["five_year"]["full_portfolio"][
                        "secondary_total_r_delta"
                    ],
                    "state_delta": report["five_year"][
                        "target_state_cohort"
                    ]["secondary_total_r_delta"],
                },
                "recent_two_year": {
                    "routing": {
                        "sample": report["recent_two_year"][
                            "target_state_sample"
                        ],
                        "retest": report["recent_two_year"][
                            "target_state_retest_count"
                        ],
                        "fallback": report["recent_two_year"][
                            "target_state_close_fallback_count"
                        ],
                    },
                    "full_delta": report["recent_two_year"][
                        "full_portfolio"
                    ]["secondary_total_r_delta"],
                    "state_delta": report["recent_two_year"][
                        "target_state_cohort"
                    ]["secondary_total_r_delta"],
                },
                "r66": {
                    "routing": {
                        "sample": report["r66_failed_holdout"][
                            "target_state_sample"
                        ],
                        "retest": report["r66_failed_holdout"][
                            "target_state_retest_count"
                        ],
                        "fallback": report["r66_failed_holdout"][
                            "target_state_close_fallback_count"
                        ],
                    },
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
