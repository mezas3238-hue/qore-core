"""VT08 Index R125 — targeted persistent-CISD replacement falsification.

R124 showed that source-valid retest execution improves the transport-adverse
R123 state but does not repair it on R66. R118/R123 identify the state as one
where the canonical V6 first-CISD reset discarded an earlier failed opposing
series whose adverse extreme was deeper than the final Protected Swing.

R78 already established that this reset is a QORE implementation choice rather
than an explicit TTrades requirement, and froze a persistent-series semantic.
R78 used it only to ADD signals when canonical CISD was absent and that broad
recovery was economically poor. R125 does NOT repeat that experiment.

R125 is a bounded replacement falsification on already-existing canonical
signals in exactly:

    SWEEP_REVERSAL | PRIOR_DEEPER_THAN_FINAL_PS

For those signals only, it reconstructs the R78 persistent opposing series from
the same canonical POI touch. A replacement is used only when:
- the target state is already known by canonical CISD confirmation;
- persistent CISD exists in the same H4;
- a valid continuation closes no earlier than that canonical CISD confirmation;
- SAME_C2 still satisfies the frozen H4-body rule;
- stop/entry geometry is valid.

Otherwise the exact canonical signal is retained. Density is therefore fixed.
The persistent replacement uses its own persistent-series extreme as Protected
Swing and the current canonical 2.5R target from the replacement entry/stop.
R102 weights remain frozen; no risk allocator recomputation is allowed.

Consumed-evidence falsification only. No candidate, certification, LIVE or real
capital authority is created.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
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
    vt08_index_r78_persistent_cisd_series as r78,
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
    vt08_index_v6_ttrades_source_faithful as v6,
)
from qore.infrastructure.traders.contracts import DemoTradingSetupSide
from qore.infrastructure.traders.vt08_index_c2_positional_r1 import (
    Vt08IndexC2R1Bar,
)

SCHEMA = "qore.trader_lab.vt08_index_r125_targeted_persistent_cisd.v1"
IDENTITY = "VT08_INDEX_R125_TARGETED_PERSISTENT_CISD_REPLACEMENT_001"

SOURCE_R124_RUN_ID = 36058115950
SOURCE_R124_ARTIFACT_ID = 10832559781
SOURCE_R124_ARTIFACT_DIGEST = (
    "sha256:e77c6302cf6b0b6e94332bc9ea0bad4f"
    "308ceccf85d111818e08e306b2cb7865"
)

TARGET_STATE = r124.TARGET_STATE
EXPECTED_TARGET_STATE = r124.EXPECTED_TARGET_STATE
EXPECTED_CANONICAL = r124.EXPECTED_CANONICAL
EXPECTED_STANDARD = r124.EXPECTED_STANDARD


def _build_persistent_replacement(
    item: r15.AssignedTrade,
    *,
    inside: tuple[Vt08IndexC2R1Bar, ...],
    bars: Sequence[Vt08IndexC2R1Bar],
    opened: Sequence[datetime],
) -> tuple[r15.AssignedTrade | None, str]:
    signal = item.opportunity.signal
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
        raise ValueError("R125 canonical POI touch missing")

    persistent = r78._persistent_first_cisd(
        inside,
        side=signal.side,
        start_index=touch_index,
    )
    if persistent is None:
        return None, "PERSISTENT_CISD_NONE"

    cisd_index, cisd_level, protected_swing = persistent
    continuation_index = v6._first_continuation(
        inside,
        side=signal.side,
        start_index=cisd_index + 1,
        protected_swing=protected_swing,
    )
    if continuation_index is None:
        return None, "PERSISTENT_CONTINUATION_NONE"

    continuation = inside[continuation_index]
    if (
        continuation.closed_at.astimezone(UTC)
        < signal.cisd_confirmed_at.astimezone(UTC)
    ):
        return None, "CONTINUATION_BEFORE_TARGET_STATE_KNOWN"

    entry = continuation.close
    if signal.model_kind is v6.H4ModelKind.SAME_C2:
        in_body = (
            entry > inside[0].open
            if signal.side is DemoTradingSetupSide.LONG
            else entry < inside[0].open
        )
        if not in_body:
            return None, "SAME_C2_BODY_RULE_FAIL"

    risk = abs(entry - protected_swing)
    if risk <= 0:
        return None, "INVALID_RISK"

    target = r108._target_price(
        entry=entry,
        stop=protected_swing,
        side=signal.side,
    )
    if target <= 0:
        return None, "INVALID_TARGET"

    replacement_signal = replace(
        signal,
        signal_at=continuation.closed_at.astimezone(UTC),
        entry=entry,
        stop=protected_swing,
        target=target,
        cisd_level=cisd_level,
        cisd_confirmed_at=inside[cisd_index].closed_at.astimezone(UTC),
        protected_swing_extreme=protected_swing,
    )
    replacement_outcome = r5._manage_trade(
        replacement_signal,
        bars=bars,
        opened=opened,
        policy=r8._target_policy(r108.TARGET_R),
    )
    replacement_item = replace(
        item,
        opportunity=replace(
            item.opportunity,
            signal=replacement_signal,
        ),
        outcome=replacement_outcome,
    )
    return replacement_item, "REPLACED"


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
        raise ValueError(f"R125 {window_id} canonical contract drift")

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
        raise ValueError(f"R125 {window_id} control density drift")

    standard_ids = r107._standard_ids(
        control,
        bars_by_symbol=bars_by_symbol,
    )
    if len(standard_ids) != EXPECTED_STANDARD[window_id]:
        raise ValueError(f"R125 {window_id} STANDARD drift")

    h4_cache = {
        symbol: r82._h4_bar_cache(bars)
        for symbol, bars in bars_by_symbol.items()
    }

    replayed: list[r15.AssignedTrade] = []
    target_before: list[r15.AssignedTrade] = []
    target_after: list[r15.AssignedTrade] = []
    replaced_before: list[r15.AssignedTrade] = []
    replaced_after: list[r15.AssignedTrade] = []
    reasons: Counter[str] = Counter()
    target_count = 0

    for item in control:
        identity = item.opportunity.identity()
        if identity not in standard_ids:
            replayed.append(item)
            continue

        state, inside = r124._state_for_item(
            item,
            indexed_by_symbol=indexed_by_symbol,
            h4_cache=h4_cache,
        )
        if state != TARGET_STATE:
            replayed.append(item)
            continue

        target_count += 1
        target_before.append(item)
        replacement, reason = _build_persistent_replacement(
            item,
            inside=inside,
            bars=bars_by_symbol[item.symbol],
            opened=opened_by_symbol[item.symbol],
        )
        reasons[reason] += 1
        if replacement is None:
            replayed.append(item)
            target_after.append(item)
            continue

        replayed.append(replacement)
        target_after.append(replacement)
        replaced_before.append(item)
        replaced_after.append(replacement)

    if target_count != EXPECTED_TARGET_STATE[window_id]:
        raise ValueError(
            f"R125 {window_id} target-state drift: "
            f"{target_count} != {EXPECTED_TARGET_STATE[window_id]}"
        )
    if sum(reasons.values()) != target_count:
        raise ValueError("R125 target-state routing mismatch")

    replayed_tuple = tuple(replayed)
    if len(replayed_tuple) != len(control):
        raise ValueError("R125 replay changed trade count")

    before_weights = {
        item.trade_id: item.weight
        for item in control
    }
    after_weights = {
        item.trade_id: item.weight
        for item in replayed_tuple
    }
    if before_weights != after_weights:
        raise ValueError("R125 frozen R102 weights changed")

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
    replaced_before_bundle = r108._cohort_bundle(replaced_before)
    replaced_after_bundle = r108._cohort_bundle(replaced_after)

    return {
        "window_id": window_id,
        "canonical_sample": expected,
        "standard_sample": len(standard_ids),
        "target_state": TARGET_STATE,
        "target_state_sample": target_count,
        "persistent_replacement_count": len(replaced_after),
        "canonical_fallback_count": target_count - len(replaced_after),
        "routing_reasons": dict(sorted(reasons.items())),
        "control_policy": r102.POLICY_EXPLICIT_FULL,
        "control_diagnostics": control_diag,
        "full_portfolio": {
            "baseline": baseline,
            "persistent_replacement": replay,
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
            "persistent_replacement": target_after_bundle,
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
        "replacement_available_only": {
            "canonical": replaced_before_bundle,
            "persistent": replaced_after_bundle,
            "primary_total_r_delta": _delta(
                replaced_after_bundle["primary"],
                replaced_before_bundle["primary"],
                field="total_r",
            ),
            "secondary_total_r_delta": _delta(
                replaced_after_bundle["secondary"],
                replaced_before_bundle["secondary"],
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
    if r124.IDENTITY != (
        "VT08_INDEX_R124_TARGETED_SOURCE_RETEST_ABLATION_001"
    ):
        raise ValueError("R125 R124 identity drift")
    if r78.IDENTITY != (
        "VT08_INDEX_R78_PERSISTENT_CISD_SERIES_RECOVERY_FALSIFICATION_001"
    ):
        raise ValueError("R125 R78 identity drift")

    roots = {
        "NAS100": nas100_root,
        "SP500": sp500_root,
        "US30": us30_root,
    }
    return {
        "schema": SCHEMA,
        "identity": IDENTITY,
        "source_r124": {
            "run_id": SOURCE_R124_RUN_ID,
            "artifact_id": SOURCE_R124_ARTIFACT_ID,
            "artifact_digest": SOURCE_R124_ARTIFACT_DIGEST,
            "decision": (
                "R124_TARGETED_SOURCE_RETEST_ABLATION_COMPLETE_"
                "NO_CANDIDATE_SELECTED"
            ),
        },
        "persistent_semantic_source": {
            "identity": r78.IDENTITY,
            "persistent_state_scope": "CURRENT_H4_ONLY",
            "failed_non_opposing_bar_resets_series": False,
            "series_open_preserved": True,
            "broad_r78_recovery_reused": False,
        },
        "preregistered_contract": {
            "target_state": TARGET_STATE,
            "target_state_known_by": "CANONICAL_CISD_CONFIRMATION",
            "replacement_continuation_must_not_precede_state_knowledge": True,
            "canonical_fallback_on_invalid_replacement": True,
            "canonical_signal_surface_preserved": True,
            "signals_suppressed": False,
            "trade_count_changed": False,
            "target_r": str(r108.TARGET_R),
            "risk_allocator": "R102_FIXED_WEIGHTS_NO_RECOMPUTE",
        },
        "five_year": _window(roots=roots, window_id="5Y"),
        "recent_two_year": _window(roots=roots, window_id="2Y"),
        "r66_failed_holdout": _window(roots=roots, window_id="R66"),
        "decision": (
            "R125_TARGETED_PERSISTENT_CISD_REPLACEMENT_COMPLETE_"
            "NO_CANDIDATE_SELECTED"
        ),
        "governance": {
            "research_only": True,
            "consumed_evidence_only": True,
            "fresh_holdout_claim": False,
            "single_preregistered_variant": True,
            "signals_suppressed": False,
            "trade_count_changed": False,
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
                    "replacement_count": report["five_year"][
                        "persistent_replacement_count"
                    ],
                    "reasons": report["five_year"]["routing_reasons"],
                    "full_delta": report["five_year"]["full_portfolio"][
                        "secondary_total_r_delta"
                    ],
                    "state_delta": report["five_year"][
                        "target_state_cohort"
                    ]["secondary_total_r_delta"],
                },
                "recent_two_year": {
                    "replacement_count": report["recent_two_year"][
                        "persistent_replacement_count"
                    ],
                    "reasons": report["recent_two_year"]["routing_reasons"],
                    "full_delta": report["recent_two_year"][
                        "full_portfolio"
                    ]["secondary_total_r_delta"],
                    "state_delta": report["recent_two_year"][
                        "target_state_cohort"
                    ]["secondary_total_r_delta"],
                },
                "r66": {
                    "replacement_count": report["r66_failed_holdout"][
                        "persistent_replacement_count"
                    ],
                    "reasons": report["r66_failed_holdout"][
                        "routing_reasons"
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
