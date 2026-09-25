"""VT08 Index R121 — R120 transport-stable cohort risk ablation.

R120 isolated one STANDARD causal state with positive stressed economics in all
three consumed windows:

    CLOSE_BREAKOUT + PRIOR_DEEPER_THAN_FINAL_PS

R121 tests exactly one bounded transport hypothesis: whether that STANDARD
state may use the already-existing exact R58 requested-weight mechanisms while
all other STANDARD signals remain at the R102 R47-base request.

The control is R102 EXPLICIT_FULL_R58_STANDARD_BASE. The variant preserves:
- exact canonical signal counts 2448 / 1017 / 773;
- entries, stops, targets, markets and anchors;
- exact explicit-PS treatment from R102;
- existing 0.005R floor, 0.25R request cap and 0.75R portfolio budget;
- the same batch-time causal allocator;
- no released-risk or outcome-based reallocation.

No new risk constant, signal suppression, target/stop change, calendar rule,
candidate identity, certification or LIVE authorization is introduced.
R66 remains consumed failure evidence.
"""

from __future__ import annotations

import argparse
import heapq
import json
from collections import Counter
from collections.abc import Sequence
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

from qore.infrastructure.trader_lab import (
    vt08_index_r15_concurrent_portfolio_validation as r15,
)
from qore.infrastructure.trader_lab import (
    vt08_index_r22_concurrent_stable_formation as r22,
)
from qore.infrastructure.trader_lab import (
    vt08_index_r47_transport_safe_structural_demotion as r47,
)
from qore.infrastructure.trader_lab import (
    vt08_index_r55_distributed_causal_risk as r55,
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
    vt08_index_r102_source_confidence_risk_ablation as r102,
)
from qore.infrastructure.trader_lab import (
    vt08_index_r107_standard_economic_root_attribution as r107,
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
    vt08_index_v6_ttrades_source_faithful as v6,
)
from qore.infrastructure.trader_lab import (
    vt08_index_v7_ttrades_source_corrected as v7,
)
from qore.infrastructure.traders.vt08_index_c2_positional_r1 import (
    Vt08IndexC2R1Bar,
)

SCHEMA = "qore.trader_lab.vt08_index_r121_r120_cohort_risk_ablation.v1"
IDENTITY = "VT08_INDEX_R121_R120_COHORT_RISK_ABLATION_001"

SOURCE_R120_RUN_ID = 35792388753
SOURCE_R120_ARTIFACT_ID = 10722073618
SOURCE_R120_ARTIFACT_DIGEST = (
    "sha256:f9d86e1347a5634686d26d1dd9e1975"
    "b240146acd348e0294e45fd3369eaf3bd"
)

CONTROL_POLICY_ID = r102.POLICY_EXPLICIT_FULL
VARIANT_POLICY_ID = "R120_CLOSE_BREAKOUT_PRIOR_DEEPER_R58_PROMOTION"

EXPECTED_CANONICAL = {
    "5Y": 2448,
    "2Y": 1017,
    "R66": 773,
}
EXPECTED_COHORT = {
    "5Y": 504,
    "2Y": 178,
    "R66": 149,
}


def _transport_state(mechanism: str, relation: str) -> bool:
    return (
        mechanism == r120.MECHANISM_BREAKOUT
        and relation == "PRIOR_DEEPER_THAN_FINAL_PS"
    )


def _cohort_ids(
    assigned: Sequence[r15.AssignedTrade],
    *,
    bars_by_symbol: dict[str, Sequence[Vt08IndexC2R1Bar]],
) -> tuple[set[tuple[object, ...]], dict[str, int]]:
    standard_ids = r107._standard_ids(
        assigned,
        bars_by_symbol=bars_by_symbol,
    )
    indexed_by_symbol = {
        symbol: {
            bar.opened_at.astimezone(UTC): bar
            for bar in bars
        }
        for symbol, bars in bars_by_symbol.items()
    }
    h4_cache = {
        symbol: r82._h4_bar_cache(bars)
        for symbol, bars in bars_by_symbol.items()
    }

    cohort: set[tuple[object, ...]] = set()
    diagnostics: Counter[str] = Counter()

    for item in assigned:
        identity = item.opportunity.identity()
        if identity not in standard_ids:
            diagnostics["EXPLICIT_PS_NOT_CLASSIFIED"] += 1
            continue

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
            raise ValueError("R121 canonical H4 missing")

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
            raise ValueError("R121 POI touch missing")

        journey = r118._cisd_journey(
            inside,
            side=signal.side,
            start_index=touch_index,
        )
        if journey is None:
            raise ValueError("R121 canonical CISD journey missing")

        relation = r118._prior_extreme_relation(
            side=signal.side,
            final_extreme=Decimal(str(journey["extreme"])),
            failed_attempts=tuple(journey["failed_attempts"]),
        )
        diagnostics[f"MECHANISM:{mechanism}"] += 1
        diagnostics[f"RELATION:{relation}"] += 1
        diagnostics[f"STATE:{mechanism}|{relation}"] += 1

        if _transport_state(mechanism, relation):
            cohort.add(identity)

    diagnostics["STANDARD_CLASSIFIED"] = len(standard_ids)
    diagnostics["COHORT_MATCH"] = len(cohort)
    return cohort, dict(sorted(diagnostics.items()))


def _apply_variant(
    baseline: Sequence[r15.AssignedTrade],
    *,
    bars_by_symbol: dict[str, Sequence[Vt08IndexC2R1Bar]],
    cohort_ids: set[tuple[object, ...]],
) -> tuple[tuple[r15.AssignedTrade, ...], dict[str, Any]]:
    confidence = r102._confidence_states(
        baseline,
        bars_by_symbol=bars_by_symbol,
    )
    h4_by_symbol = {
        symbol: v6._build_h4(
            {
                bar.opened_at.astimezone(UTC): bar
                for bar in bars
            }
        )
        for symbol, bars in bars_by_symbol.items()
    }
    reaction_bars, reaction_opened = r55._reaction_bars(bars_by_symbol)

    ordered = sorted(
        baseline,
        key=lambda item: (
            item.opportunity.signal.signal_at.astimezone(UTC),
            item.symbol,
            item.trade_id,
        ),
    )

    active: dict[int, Decimal] = {}
    exit_heap: list[tuple[datetime, int]] = []
    assigned: list[r15.AssignedTrade] = []
    diagnostics: Counter[str] = Counter()
    cursor = 0
    next_trade_id = 0
    max_committed = Decimal()

    def settle(until: datetime) -> None:
        while exit_heap and exit_heap[0][0] <= until:
            _exit_at, trade_id = heapq.heappop(exit_heap)
            active.pop(trade_id, None)

    while cursor < len(ordered):
        batch_time = (
            ordered[cursor]
            .opportunity.signal.signal_at.astimezone(UTC)
        )
        settle(batch_time)
        end = cursor + 1
        while (
            end < len(ordered)
            and ordered[end]
            .opportunity.signal.signal_at.astimezone(UTC)
            == batch_time
        ):
            end += 1
        batch = ordered[cursor:end]

        requested: list[Decimal] = []
        for item in batch:
            identity = item.opportunity.identity()
            state = confidence[identity]
            base_request = r102._base_request(item)

            if state.explicit_ps_mechanism:
                value, labels = r55._requested_weight(
                    item,
                    h4_by_symbol=h4_by_symbol,
                    reaction_bars=reaction_bars,
                    reaction_opened=reaction_opened,
                )
                diagnostics["EXPLICIT_FULL_R58_REQUEST"] += 1
            elif identity in cohort_ids:
                value, labels = r55._requested_weight(
                    item,
                    h4_by_symbol=h4_by_symbol,
                    reaction_bars=reaction_bars,
                    reaction_opened=reaction_opened,
                )
                diagnostics["R120_COHORT_R58_REQUEST"] += 1
                if value > base_request:
                    diagnostics["R120_COHORT_PROMOTED_ABOVE_BASE"] += 1
                else:
                    diagnostics["R120_COHORT_NOT_PROMOTED"] += 1
            else:
                value = base_request
                labels = ()
                diagnostics["STANDARD_BASE_REQUEST"] += 1

            requested.append(value)
            for label in labels:
                if label.startswith("R47:"):
                    diagnostics["R47_DEMOTION_PROTECTED"] += 1
                else:
                    diagnostics[f"PROMOTION:{label}"] += 1

        active_risk = sum(active.values(), Decimal())
        weights, scaled = r22._allocate_batch(
            requested,
            active_risk=active_risk,
            budget=r102.PORTFOLIO_BUDGET_R,
        )
        diagnostics["BUDGET_SCALED_BATCH"] += int(scaled)
        if active_risk + sum(weights, Decimal()) > r102.PORTFOLIO_BUDGET_R:
            diagnostics["FLOOR_OVERAGE_BATCH"] += 1

        for item, weight in zip(batch, weights, strict=True):
            replacement = r15.AssignedTrade(
                trade_id=next_trade_id,
                opportunity=item.opportunity,
                outcome=item.outcome,
                context=item.context,
                weight=weight,
            )
            next_trade_id += 1
            assigned.append(replacement)
            active[replacement.trade_id] = weight
            heapq.heappush(
                exit_heap,
                (
                    replacement.exited_at.astimezone(UTC),
                    replacement.trade_id,
                ),
            )

        max_committed = max(
            max_committed,
            sum(active.values(), Decimal()),
        )
        cursor = end

    result = tuple(assigned)
    if len(result) != len(baseline):
        raise ValueError("R121 variant changed trade count")
    if any(item.weight < r102.MIN_EFFECTIVE_WEIGHT for item in result):
        raise ValueError("R121 fell below positive-risk floor")
    if any(item.weight > r102.MAX_REQUESTED_WEIGHT for item in result):
        raise ValueError("R121 exceeded request cap")

    diagnostics["ASSIGNED_TRADE_COUNT"] = len(result)
    diagnostics["SUPPRESSED_TRADE_COUNT"] = 0
    return result, {
        "policy_id": VARIANT_POLICY_ID,
        "counts": dict(sorted(diagnostics.items())),
        "minimum_effective_weight": str(
            min(item.weight for item in result)
        ),
        "maximum_effective_weight": str(
            max(item.weight for item in result)
        ),
        "mean_effective_weight": str(
            sum((item.weight for item in result), Decimal())
            / len(result)
        ),
        "max_committed_structural_risk_r": str(max_committed),
    }


def _metrics(
    assigned: tuple[r15.AssignedTrade, ...],
    *,
    bars_by_symbol: dict[str, Sequence[Vt08IndexC2R1Bar]],
    opened_by_symbol: dict[str, tuple[datetime, ...]],
    window_id: str,
) -> dict[str, Any]:
    if window_id == "5Y":
        return r47._window_metrics(
            assigned,
            bars_by_symbol=bars_by_symbol,
            opened_by_symbol=opened_by_symbol,
            years=5,
        )
    if window_id == "2Y":
        return r47._window_metrics(
            assigned,
            bars_by_symbol=bars_by_symbol,
            opened_by_symbol=opened_by_symbol,
            years=2,
        )
    if window_id == "R66":
        return r102._r66_metrics(
            assigned,
            bars_by_symbol=bars_by_symbol,
            opened_by_symbol=opened_by_symbol,
        )
    raise ValueError(f"R121 unsupported window {window_id}")


def _snapshot(metrics: dict[str, Any]) -> dict[str, Any]:
    result = {
        "sample": metrics["sample"],
        "primary_pf": metrics["primary"]["profit_factor"],
        "secondary_pf": metrics["secondary"]["profit_factor"],
        "primary_total_r": metrics["primary"]["total_r"],
        "secondary_total_r": metrics["secondary"]["total_r"],
        "primary_mtm_dd_r": metrics[
            "primary_conservative_mark_to_market"
        ]["max_drawdown_r"],
        "secondary_mtm_dd_r": metrics[
            "secondary_conservative_mark_to_market"
        ]["max_drawdown_r"],
    }
    if "temporal_pass" in metrics:
        result["temporal_pass"] = metrics["temporal_pass"]
    if "all_primary_blocks_positive" in metrics:
        result["all_primary_blocks_positive"] = metrics[
            "all_primary_blocks_positive"
        ]
        result["all_secondary_blocks_positive"] = metrics[
            "all_secondary_blocks_positive"
        ]
    return result


def _window(
    *,
    roots: dict[str, Path],
    window_id: str,
) -> dict[str, Any]:
    stream, bars_by_symbol_raw, provenance = r74._load_window(
        roots=roots,
        window_id=window_id,
    )
    _start, _end, expected = r74._window_contract(window_id)
    if expected != EXPECTED_CANONICAL[window_id]:
        raise ValueError(f"R121 {window_id} canonical contract drift")

    bars_by_symbol: dict[str, Sequence[Vt08IndexC2R1Bar]] = {
        symbol: tuple(bars)
        for symbol, bars in bars_by_symbol_raw.items()
    }
    opened_by_symbol = {
        symbol: tuple(bar.opened_at.astimezone(UTC) for bar in bars)
        for symbol, bars in bars_by_symbol.items()
    }

    base, _base_diag = r58._exact_r47(
        tuple(stream),
        bars_by_symbol=bars_by_symbol,
    )
    base = tuple(base)
    control, control_diag = r102._apply_confidence_policy(
        base,
        bars_by_symbol=bars_by_symbol,
        policy_id=CONTROL_POLICY_ID,
    )
    control = tuple(control)
    if len(control) != expected:
        raise ValueError(f"R121 {window_id} control density drift")

    cohort_ids, cohort_diag = _cohort_ids(
        control,
        bars_by_symbol=bars_by_symbol,
    )
    if len(cohort_ids) != EXPECTED_COHORT[window_id]:
        raise ValueError(
            f"R121 {window_id} R120 cohort drift: "
            f"{len(cohort_ids)} != {EXPECTED_COHORT[window_id]}"
        )

    variant, variant_diag = _apply_variant(
        base,
        bars_by_symbol=bars_by_symbol,
        cohort_ids=cohort_ids,
    )
    if len(variant) != expected:
        raise ValueError(f"R121 {window_id} variant density drift")

    control_metrics = _metrics(
        control,
        bars_by_symbol=bars_by_symbol,
        opened_by_symbol=opened_by_symbol,
        window_id=window_id,
    )
    variant_metrics = _metrics(
        variant,
        bars_by_symbol=bars_by_symbol,
        opened_by_symbol=opened_by_symbol,
        window_id=window_id,
    )

    return {
        "window_id": window_id,
        "sample": expected,
        "r120_cohort_sample": len(cohort_ids),
        "r120_cohort_diagnostics": cohort_diag,
        "control": {
            "policy_id": CONTROL_POLICY_ID,
            "metrics": control_metrics,
            "snapshot": _snapshot(control_metrics),
            "diagnostics": control_diag,
        },
        "variant": {
            "policy_id": VARIANT_POLICY_ID,
            "metrics": variant_metrics,
            "snapshot": _snapshot(variant_metrics),
            "diagnostics": variant_diag,
        },
        "secondary_total_r_delta_vs_control": str(
            Decimal(str(variant_metrics["secondary"]["total_r"]))
            - Decimal(str(control_metrics["secondary"]["total_r"]))
        ),
        "provenance": provenance,
    }


def build_report(
    *,
    nas100_root: Path,
    sp500_root: Path,
    us30_root: Path,
) -> dict[str, Any]:
    if r120.IDENTITY != (
        "VT08_INDEX_R120_DAILY_BIAS_MECHANISM_ATTRIBUTION_001"
    ):
        raise ValueError("R121 R120 identity drift")
    if r102.IDENTITY != (
        "VT08_INDEX_R102_SOURCE_CONFIDENCE_RISK_TRANSPORT_ABLATION_001"
    ):
        raise ValueError("R121 R102 identity drift")

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
        "source_r120": {
            "run_id": SOURCE_R120_RUN_ID,
            "artifact_id": SOURCE_R120_ARTIFACT_ID,
            "artifact_digest": SOURCE_R120_ARTIFACT_DIGEST,
            "decision": (
                "R120_DAILY_BIAS_MECHANISM_COMPLETE_NO_RULE_CHANGE"
            ),
        },
        "hypothesis": {
            "mechanism": r120.MECHANISM_BREAKOUT,
            "prior_extreme_relation": "PRIOR_DEEPER_THAN_FINAL_PS",
            "standard_only": True,
            "action": "ALLOW_EXISTING_EXACT_R58_REQUESTED_WEIGHT",
            "new_risk_constants": False,
        },
        "contracts": {
            "control_policy": CONTROL_POLICY_ID,
            "variant_policy": VARIANT_POLICY_ID,
            "canonical_signal_counts": EXPECTED_CANONICAL,
            "expected_r120_cohort_counts": EXPECTED_COHORT,
            "minimum_effective_weight_r": str(
                r102.MIN_EFFECTIVE_WEIGHT
            ),
            "maximum_requested_weight_r": str(
                r102.MAX_REQUESTED_WEIGHT
            ),
            "portfolio_budget_r": str(r102.PORTFOLIO_BUDGET_R),
        },
        "five_year": five,
        "recent_two_year": two,
        "r66_failed_holdout": failed,
        "decision": (
            "R121_R120_COHORT_RISK_ABLATION_COMPLETE_"
            "NO_CANDIDATE_SELECTED"
        ),
        "governance": {
            "research_only": True,
            "consumed_evidence_only": True,
            "fresh_holdout_claim": False,
            "single_preregistered_variant": True,
            "canonical_signal_surface_preserved": True,
            "signals_suppressed": False,
            "entries_changed": False,
            "stops_changed": False,
            "targets_changed": False,
            "markets_changed": False,
            "anchors_changed": False,
            "calendar_or_year_rule_created": False,
            "new_risk_constants_introduced": False,
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
                    "cohort": report["five_year"]["r120_cohort_sample"],
                    "control": report["five_year"]["control"]["snapshot"],
                    "variant": report["five_year"]["variant"]["snapshot"],
                    "secondary_total_r_delta": report["five_year"][
                        "secondary_total_r_delta_vs_control"
                    ],
                },
                "recent_two_year": {
                    "cohort": report["recent_two_year"][
                        "r120_cohort_sample"
                    ],
                    "control": report["recent_two_year"]["control"][
                        "snapshot"
                    ],
                    "variant": report["recent_two_year"]["variant"][
                        "snapshot"
                    ],
                    "secondary_total_r_delta": report[
                        "recent_two_year"
                    ]["secondary_total_r_delta_vs_control"],
                },
                "r66": {
                    "cohort": report["r66_failed_holdout"][
                        "r120_cohort_sample"
                    ],
                    "control": report["r66_failed_holdout"]["control"][
                        "snapshot"
                    ],
                    "variant": report["r66_failed_holdout"]["variant"][
                        "snapshot"
                    ],
                    "secondary_total_r_delta": report[
                        "r66_failed_holdout"
                    ]["secondary_total_r_delta_vs_control"],
                },
                "decision": report["decision"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
