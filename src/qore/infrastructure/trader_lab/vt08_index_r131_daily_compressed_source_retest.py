"""VT08 Index R131 — targeted DAILY-COMPRESSED source-retest ablation.

R128 isolated CLOSE_BREAKOUT | NO_FAILED_ATTEMPT as the largest R66 B2 loss
driver. R129 showed that its strict adverse contexts are already 94.5-100% at
the existing 0.005R floor, so additional risk demotion is not a meaningful
repair.

After R130 improved LOW-concurrency execution only marginally, R131 moves to
the strongest strictly transport-adverse STRUCTURAL state from R128:
recent_daily_range_state=compressed. This state is causal and known before
entry from the frozen R46 feature vocabulary.

R131 changes one source-authorized variable only:
- exact STANDARD CLOSE_BREAKOUT | NO_FAILED_ATTEMPT trades with compressed
  recent daily range use the already-frozen R89/R108 continuation retest when
  available;
- if no causal retest occurs before Protected-Swing invalidation / H4 end, the
  canonical continuation-close fill remains in force;
- the same canonical Protected Swing and 2.5R target geometry are retained;
- R102 weights are frozen and not recomputed from retest outcomes;
- retest is an alternate fill of the same setup, never a second trade.

No signal is suppressed, no market/side/anchor is selected, and canonical
density remains 2448 / 1017 / 773. All windows are consumed evidence.
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
    vt08_index_r46_cross_window_transport_forensics as r46,
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
    vt08_index_r124_targeted_source_retest as r124,
)
from qore.infrastructure.trader_lab import (
    vt08_index_r128_close_breakout_no_attempt_context_transport as r128,
)
from qore.infrastructure.trader_lab import (
    vt08_index_r130_low_concurrent_source_retest as r130,
)
from qore.infrastructure.traders.vt08_index_c2_positional_r1 import (
    Vt08IndexC2R1Bar,
)

SCHEMA = "qore.trader_lab.vt08_index_r131_daily_compressed_source_retest.v1"
IDENTITY = "VT08_INDEX_R131_DAILY_COMPRESSED_SOURCE_RETEST_ABLATION_001"

SOURCE_R130_RUN_ID = 36077074851
SOURCE_R130_ARTIFACT_ID = 10839674224
SOURCE_R130_ARTIFACT_DIGEST = (
    "sha256:5cbf36ba630f60af21726d5dc4259d6d"
    "8e2024f92d405a003a6c60ba5a64cfa5"
)

TARGET_COHORT = r128.COHORT_STATE
TARGET_DAILY_RANGE_STATE = "compressed"
EXPECTED_TARGET = {"5Y": 104, "2Y": 50, "R66": 37}
EXPECTED_CANONICAL = r128.EXPECTED_CANONICAL
EXPECTED_STANDARD = r128.EXPECTED_STANDARD


def _feature_rows(
    *,
    stream: Sequence[tuple[Any, Any]],
    assigned: Sequence[Any],
    bars_by_symbol: dict[str, Sequence[Vt08IndexC2R1Bar]],
    window_id: str,
) -> tuple[dict[str, Any], ...]:
    trace = r46._causal_trace(stream)
    rows = r46._feature_rows(
        assigned=assigned,
        trace=trace,
        window_id=("2Y" if window_id == "R66" else window_id),
        bars_by_symbol=bars_by_symbol,
    )
    if len(rows) != len(assigned):
        raise ValueError("R131 feature alignment drift")
    return tuple(rows)


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
        raise ValueError(f"R131 {window_id} canonical contract drift")

    bars_by_symbol: dict[str, Sequence[Vt08IndexC2R1Bar]] = {
        symbol: tuple(bars)
        for symbol, bars in bars_by_symbol_raw.items()
    }
    opened_by_symbol: dict[str, tuple[datetime, ...]] = {
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
        raise ValueError(f"R131 {window_id} control density drift")

    standard_ids = r107._standard_ids(
        control,
        bars_by_symbol=bars_by_symbol,
    )
    if len(standard_ids) != EXPECTED_STANDARD[window_id]:
        raise ValueError(f"R131 {window_id} STANDARD drift")

    features = _feature_rows(
        stream=tuple(canonical),
        assigned=control,
        bars_by_symbol=bars_by_symbol,
        window_id=window_id,
    )
    h4_cache = {
        symbol: r82._h4_bar_cache(bars)
        for symbol, bars in bars_by_symbol.items()
    }

    replayed: list[Any] = []
    target_before: list[Any] = []
    target_after: list[Any] = []
    retest_before: list[Any] = []
    retest_after: list[Any] = []
    target_count = 0
    retest_count = 0
    fallback_count = 0

    for item, feature in zip(control, features, strict=True):
        identity = item.opportunity.identity()
        if identity not in standard_ids:
            replayed.append(item)
            continue

        state, inside = r124._state_for_item(
            item,
            indexed_by_symbol=indexed_by_symbol,
            h4_cache=h4_cache,
        )
        target = (
            state == TARGET_COHORT
            and str(feature["recent_daily_range_state"])
            == TARGET_DAILY_RANGE_STATE
        )
        if not target:
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
            raise ValueError("R131 continuation bar not found")

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

    if target_count != EXPECTED_TARGET[window_id]:
        raise ValueError(
            f"R131 {window_id} target drift: "
            f"{target_count} != {EXPECTED_TARGET[window_id]}"
        )
    if target_count != retest_count + fallback_count:
        raise ValueError("R131 target routing mismatch")

    replayed_tuple = tuple(replayed)
    if len(replayed_tuple) != len(control):
        raise ValueError("R131 replay changed trade count")

    before_weights = {
        item.trade_id: item.weight
        for item in control
    }
    after_weights = {
        item.trade_id: item.weight
        for item in replayed_tuple
    }
    if before_weights != after_weights:
        raise ValueError("R131 frozen R102 weights changed")

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
        "target_cohort": TARGET_COHORT,
        "target_daily_range_state": TARGET_DAILY_RANGE_STATE,
        "target_sample": target_count,
        "retest_count": retest_count,
        "fallback_count": fallback_count,
        "retest_fraction": str(
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
        "target_cohort_economics": {
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
            "baseline": retest_before_bundle,
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
    if r130.IDENTITY != (
        "VT08_INDEX_R130_LOW_CONCURRENT_SOURCE_RETEST_ABLATION_001"
    ):
        raise ValueError("R131 R130 identity drift")

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
        "source_r130": {
            "run_id": SOURCE_R130_RUN_ID,
            "artifact_id": SOURCE_R130_ARTIFACT_ID,
            "artifact_digest": SOURCE_R130_ARTIFACT_DIGEST,
            "decision": (
                "R130_LOW_CONCURRENT_SOURCE_RETEST_ABLATION_COMPLETE_"
                "NO_CANDIDATE_SELECTED"
            ),
        },
        "preregistered_contract": {
            "target_cohort": TARGET_COHORT,
            "recent_daily_range_state": TARGET_DAILY_RANGE_STATE,
            "recent_daily_range_state_definition": (
                "CAUSAL_RECENT_DAILY_RANGE_STATE_COMPRESSED"
            ),
            "same_setup_only": True,
            "retest_creates_second_trade": False,
            "canonical_fallback_when_no_retest": True,
            "same_protected_swing": True,
            "target_r": str(r108.TARGET_R),
            "risk_allocator": "R102_FIXED_WEIGHTS_NO_RECOMPUTE",
            "signals_suppressed": False,
            "trade_count_changed": False,
        },
        "five_year": five,
        "recent_two_year": two,
        "r66_failed_holdout": failed,
        "decision": (
            "R131_DAILY_COMPRESSED_SOURCE_RETEST_ABLATION_COMPLETE_"
            "NO_CANDIDATE_SELECTED"
        ),
        "governance": {
            "research_only": True,
            "consumed_evidence_only": True,
            "fresh_holdout_claim": False,
            "single_preregistered_variant": True,
            "calendar_or_year_runtime_feature": False,
            "signals_suppressed": False,
            "trade_count_changed": False,
            "risk_changed": False,
            "protected_swing_stop_changed": False,
            "target_r_changed": False,
            "market_removed": False,
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
                    "target_sample": report["five_year"]["target_sample"],
                    "retest_count": report["five_year"]["retest_count"],
                    "full_secondary_delta": report["five_year"][
                        "full_portfolio"
                    ]["secondary_total_r_delta"],
                    "target_secondary_delta": report["five_year"][
                        "target_cohort_economics"
                    ]["secondary_total_r_delta"],
                },
                "recent_two_year": {
                    "target_sample": report["recent_two_year"][
                        "target_sample"
                    ],
                    "retest_count": report["recent_two_year"][
                        "retest_count"
                    ],
                    "full_secondary_delta": report["recent_two_year"][
                        "full_portfolio"
                    ]["secondary_total_r_delta"],
                    "target_secondary_delta": report["recent_two_year"][
                        "target_cohort_economics"
                    ]["secondary_total_r_delta"],
                },
                "r66": {
                    "target_sample": report["r66_failed_holdout"][
                        "target_sample"
                    ],
                    "retest_count": report["r66_failed_holdout"][
                        "retest_count"
                    ],
                    "full_secondary_delta": report["r66_failed_holdout"][
                        "full_portfolio"
                    ]["secondary_total_r_delta"],
                    "target_secondary_delta": report[
                        "r66_failed_holdout"
                    ]["target_cohort_economics"][
                        "secondary_total_r_delta"
                    ],
                    "periods": report["r66_failed_holdout"][
                        "full_portfolio"
                    ]["targeted_retest"]["periods"],
                },
                "decision": report["decision"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
