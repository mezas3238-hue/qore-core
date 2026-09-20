"""VT08 Index R68 — R58 risk-transport causal ablation.

R67 showed that the frozen R58/R59 identity failed R66 while the underlying
773-trade structural surface still had positive unweighted expectancy. R68 is
therefore a bounded mechanistic ablation of the R58 allocator, not a candidate
search.

The ablation keeps the exact signal surface, entries, exits, R47 demotions,
positive-risk floor, 0.25R request cap and 0.75R portfolio budget. It toggles
only already-existing R55/R58 promotion mechanisms one at a time:

- structural rearm minimum risk;
- FVG cross-index unanimous-with-side support;
- FVG H4 121-180 + CISD latency 4-7 support;
- CISD late revalidation.

No variant is promoted by score in this stage. R66 is consumed failure
evidence, not a fresh holdout. The purpose is causal attribution before any
NEW identity can be proposed.
"""

from __future__ import annotations

import argparse
import heapq
import json
from dataclasses import dataclass
from datetime import UTC, datetime
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
    vt08_index_r17_formation_quality_forensics as r17,
)
from qore.infrastructure.trader_lab import (
    vt08_index_r22_concurrent_stable_formation as r22,
)
from qore.infrastructure.trader_lab import (
    vt08_index_r31_source_complete_structural_concurrency as r31,
)
from qore.infrastructure.trader_lab import (
    vt08_index_r45_frozen_recent_2y_reproduction as r45,
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
    vt08_index_r59_candidate_freeze as freeze,
)
from qore.infrastructure.trader_lab import (
    vt08_index_r66_fresh_historical_holdout as r66,
)
from qore.infrastructure.trader_lab import (
    vt08_index_r67_r66_failure_forensics as r67,
)
from qore.infrastructure.trader_lab import (
    vt08_index_v6_ttrades_source_faithful as v6,
)
from qore.infrastructure.traders.vt08_index_c2_positional_r1 import (
    Vt08IndexC2R1Bar,
)

SCHEMA = "qore.trader_lab.vt08_index_r68_r58_risk_transport_ablation.v1"
IDENTITY = "VT08_INDEX_R68_R58_RISK_TRANSPORT_ABLATION_001"

PRIMARY_STRESS = Decimal("0.05")
SECONDARY_STRESS = Decimal("0.10")
MAX_REQUESTED_WEIGHT = r55.MAX_REQUESTED_WEIGHT
MIN_EFFECTIVE_WEIGHT = r55.MIN_EFFECTIVE_WEIGHT
PORTFOLIO_BUDGET_R = r55.PORTFOLIO_BUDGET_R


@dataclass(frozen=True, slots=True)
class PromotionPolicy:
    policy_id: str
    structural_rearm: bool
    fvg_cross_index: bool
    fvg_h4_cisd: bool
    late_revalidation: bool


POLICIES = (
    PromotionPolicy(
        "EXACT_R58",
        structural_rearm=True,
        fvg_cross_index=True,
        fvg_h4_cisd=True,
        late_revalidation=True,
    ),
    PromotionPolicy(
        "CAPPED_R47_BASE",
        structural_rearm=False,
        fvg_cross_index=False,
        fvg_h4_cisd=False,
        late_revalidation=False,
    ),
    PromotionPolicy(
        "ABLATE_REARM",
        structural_rearm=False,
        fvg_cross_index=True,
        fvg_h4_cisd=True,
        late_revalidation=True,
    ),
    PromotionPolicy(
        "ABLATE_FVG_CROSS",
        structural_rearm=True,
        fvg_cross_index=False,
        fvg_h4_cisd=True,
        late_revalidation=True,
    ),
    PromotionPolicy(
        "ABLATE_FVG_H4_CISD",
        structural_rearm=True,
        fvg_cross_index=True,
        fvg_h4_cisd=False,
        late_revalidation=True,
    ),
    PromotionPolicy(
        "ABLATE_LATE_REVALIDATION",
        structural_rearm=True,
        fvg_cross_index=True,
        fvg_h4_cisd=True,
        late_revalidation=False,
    ),
    PromotionPolicy(
        "LATE_REVALIDATION_ONLY",
        structural_rearm=False,
        fvg_cross_index=False,
        fvg_h4_cisd=False,
        late_revalidation=True,
    ),
)


def _requested_weight(
    item: r15.AssignedTrade,
    *,
    policy: PromotionPolicy,
    h4_by_symbol: dict[str, dict[datetime, Vt08IndexC2R1Bar]],
    reaction_bars: dict[str, tuple[Any, ...]],
    reaction_opened: dict[str, tuple[datetime, ...]],
) -> tuple[Decimal, tuple[str, ...]]:
    opportunity = item.opportunity
    signal = opportunity.signal
    r47_labels = r47._rule_labels(item, h4_by_symbol=h4_by_symbol)
    requested = min(item.weight, MAX_REQUESTED_WEIGHT)
    labels: list[str] = []

    if r47_labels:
        return requested, tuple(f"R47:{label}" for label in r47_labels)

    if policy.structural_rearm and int(opportunity.rearm_index) > 0:
        requested = max(requested, r55.REARM_MIN_WEIGHT)
        labels.append("STRUCTURAL_REARM")

    if str(opportunity.source_poi_kind) == "fvg":
        if policy.fvg_cross_index:
            cross_state = r47._cross_index_state(
                h4_by_symbol=h4_by_symbol,
                decision=signal.signal_at,
                side=signal.side,
            )
            if cross_state == "unanimous_with_side":
                requested = max(requested, r55.SUPPORTED_FVG_MIN_WEIGHT)
                labels.append("FVG_CROSS_INDEX_UNANIMOUS_WITH_SIDE")

        if (
            policy.fvg_h4_cisd
            and r17._bucket_h4_entry_latency(opportunity) == "121-180m"
            and r17._bucket_cisd_latency(opportunity) == "4-7"
        ):
            requested = max(requested, r55.SUPPORTED_FVG_MIN_WEIGHT)
            labels.append("FVG_H4_121_180_CISD_4_7")

    if policy.late_revalidation and r55._late_revalidation(
        item,
        bars=reaction_bars[item.symbol],
        opened=reaction_opened[item.symbol],
    ):
        requested = max(requested, r55.LATE_REVALIDATION_MIN_WEIGHT)
        labels.append("CISD_LATE_REVALIDATION")

    return max(MIN_EFFECTIVE_WEIGHT, requested), tuple(labels)


def _apply_policy(
    baseline: tuple[r15.AssignedTrade, ...],
    *,
    bars_by_symbol: dict[str, tuple[Vt08IndexC2R1Bar, ...]],
    policy: PromotionPolicy,
) -> tuple[tuple[r15.AssignedTrade, ...], dict[str, Any]]:
    h4_by_symbol = {
        symbol: v6._build_h4(
            {bar.opened_at.astimezone(UTC): bar for bar in bars}
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
    cursor = 0
    next_trade_id = 0
    rule_hits: dict[str, int] = {
        "STRUCTURAL_REARM": 0,
        "FVG_CROSS_INDEX_UNANIMOUS_WITH_SIDE": 0,
        "FVG_H4_121_180_CISD_4_7": 0,
        "CISD_LATE_REVALIDATION": 0,
        "R47_DEMOTION": 0,
    }
    budget_scaled_batches = 0
    floor_overage_batches = 0
    max_committed = Decimal()

    def settle(until: datetime) -> None:
        while exit_heap and exit_heap[0][0] <= until:
            _exit_at, trade_id = heapq.heappop(exit_heap)
            active.pop(trade_id, None)

    while cursor < len(ordered):
        batch_time = ordered[cursor].opportunity.signal.signal_at.astimezone(UTC)
        settle(batch_time)
        end = cursor + 1
        while (
            end < len(ordered)
            and ordered[end].opportunity.signal.signal_at.astimezone(UTC)
            == batch_time
        ):
            end += 1
        batch = ordered[cursor:end]

        requested: list[Decimal] = []
        for item in batch:
            value, labels = _requested_weight(
                item,
                policy=policy,
                h4_by_symbol=h4_by_symbol,
                reaction_bars=reaction_bars,
                reaction_opened=reaction_opened,
            )
            requested.append(value)
            for label in labels:
                if label.startswith("R47:"):
                    rule_hits["R47_DEMOTION"] += 1
                else:
                    rule_hits[label] += 1

        active_risk = sum(active.values(), Decimal())
        weights, scaled = r22._allocate_batch(
            requested,
            active_risk=active_risk,
            budget=PORTFOLIO_BUDGET_R,
        )
        budget_scaled_batches += int(scaled)
        if active_risk + sum(weights, Decimal()) > PORTFOLIO_BUDGET_R:
            floor_overage_batches += 1

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
                (replacement.exited_at.astimezone(UTC), replacement.trade_id),
            )

        max_committed = max(max_committed, sum(active.values(), Decimal()))
        cursor = end

    if len(assigned) != len(baseline):
        raise ValueError("R68 policy changed trade count")
    if any(item.weight < MIN_EFFECTIVE_WEIGHT for item in assigned):
        raise ValueError("R68 policy violated positive-risk floor")
    if any(item.weight > MAX_REQUESTED_WEIGHT for item in assigned):
        raise ValueError("R68 policy exceeded request cap")

    return tuple(assigned), {
        "policy_id": policy.policy_id,
        "sample": len(assigned),
        "rule_hits": rule_hits,
        "budget_scaled_batches": budget_scaled_batches,
        "floor_overage_batches": floor_overage_batches,
        "max_committed_structural_risk_r": str(max_committed),
        "minimum_effective_weight": str(min(item.weight for item in assigned)),
        "maximum_effective_weight": str(max(item.weight for item in assigned)),
        "mean_effective_weight": str(
            sum((item.weight for item in assigned), Decimal()) / len(assigned)
        ),
    }


def _weighted_metrics(
    assigned: tuple[r15.AssignedTrade, ...],
    *,
    stress: Decimal,
) -> dict[str, Any]:
    return fx._metrics(
        tuple(
            (item.outcome.r_multiple - stress) * item.weight
            for item in sorted(
                assigned,
                key=lambda row: (
                    row.exited_at.astimezone(UTC),
                    row.symbol,
                    row.trade_id,
                ),
            )
        )
    )


def _raw_metrics(
    assigned: tuple[r15.AssignedTrade, ...],
    *,
    stress: Decimal,
) -> dict[str, Any]:
    return fx._metrics(
        tuple(
            item.outcome.r_multiple - stress
            for item in sorted(
                assigned,
                key=lambda row: (
                    row.exited_at.astimezone(UTC),
                    row.symbol,
                    row.trade_id,
                ),
            )
        )
    )


def _availability(provenance: dict[str, Any]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for symbol, source in sorted(provenance.items()):
        counts = {
            int(size): int(count)
            for size, count in source["m15_bucket_size_counts"].items()
        }
        total = int(source["m15_buckets"])
        full = counts.get(3, 0)
        partial = total - full
        result[symbol] = {
            "m15_buckets": total,
            "complete_three_m5_buckets": full,
            "partial_m15_buckets": partial,
            "complete_fraction": str(Decimal(full) / Decimal(total)),
            "partial_fraction": str(Decimal(partial) / Decimal(total)),
            "raw_m5_rows_loaded": int(source["raw_m5_rows_loaded"]),
            "interpolated_prices": int(source["interpolated_prices"]),
            "synthetic_prices": int(source["synthetic_prices"]),
        }
    return result


def _window(
    *,
    stream: tuple[tuple[Any, Any], ...],
    bars_by_symbol: dict[str, tuple[Vt08IndexC2R1Bar, ...]],
    provenance: dict[str, Any],
) -> dict[str, Any]:
    base_r47, r47_diagnostics = r58._exact_r47(
        stream,
        bars_by_symbol=bars_by_symbol,
    )

    variants: dict[str, Any] = {}
    assigned_by_policy: dict[str, tuple[r15.AssignedTrade, ...]] = {}
    for policy in POLICIES:
        assigned, diagnostics = _apply_policy(
            base_r47,
            bars_by_symbol=bars_by_symbol,
            policy=policy,
        )
        assigned_by_policy[policy.policy_id] = assigned
        variants[policy.policy_id] = {
            "primary": _weighted_metrics(assigned, stress=PRIMARY_STRESS),
            "secondary": _weighted_metrics(assigned, stress=SECONDARY_STRESS),
            "diagnostics": diagnostics,
            "concentration": r55._concentration(assigned),
        }

    exact = assigned_by_policy["EXACT_R58"]
    exact_fingerprint = tuple(
        (
            item.opportunity.identity(),
            str(item.weight),
        )
        for item in exact
    )
    canonical_r58, _canonical_diag = r55._apply_candidate(
        base_r47,
        bars_by_symbol=bars_by_symbol,
    )
    canonical_fingerprint = tuple(
        (
            item.opportunity.identity(),
            str(item.weight),
        )
        for item in canonical_r58
    )
    if exact_fingerprint != canonical_fingerprint:
        raise ValueError("R68 EXACT_R58 ablation does not reproduce canonical R58")

    raw_primary = _raw_metrics(base_r47, stress=PRIMARY_STRESS)
    raw_secondary = _raw_metrics(base_r47, stress=SECONDARY_STRESS)
    r47_primary = _weighted_metrics(base_r47, stress=PRIMARY_STRESS)
    r47_secondary = _weighted_metrics(base_r47, stress=SECONDARY_STRESS)

    capped_secondary_total = Decimal(
        str(variants["CAPPED_R47_BASE"]["secondary"]["total_r"])
    )
    exact_secondary_total = Decimal(
        str(variants["EXACT_R58"]["secondary"]["total_r"])
    )

    return {
        "sample": len(base_r47),
        "raw_unweighted": {
            "primary": raw_primary,
            "secondary": raw_secondary,
        },
        "r47_weighted": {
            "primary": r47_primary,
            "secondary": r47_secondary,
            "diagnostics": r47_diagnostics,
        },
        "variants": variants,
        "exact_r58_secondary_delta_vs_capped_base_r": str(
            exact_secondary_total - capped_secondary_total
        ),
        "source_availability": _availability(provenance),
    }


def _variant_transport(
    five: dict[str, Any],
    two: dict[str, Any],
    failed: dict[str, Any],
) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for policy in POLICIES:
        policy_id = policy.policy_id
        windows = {
            "five_year": five["variants"][policy_id],
            "recent_two_year": two["variants"][policy_id],
            "r66": failed["variants"][policy_id],
        }
        result.append(
            {
                "policy_id": policy_id,
                "five_year_secondary_pf": windows["five_year"]["secondary"][
                    "profit_factor"
                ],
                "five_year_secondary_total_r": windows["five_year"]["secondary"][
                    "total_r"
                ],
                "recent_two_year_secondary_pf": windows[
                    "recent_two_year"
                ]["secondary"]["profit_factor"],
                "recent_two_year_secondary_total_r": windows[
                    "recent_two_year"
                ]["secondary"]["total_r"],
                "r66_secondary_pf": windows["r66"]["secondary"]["profit_factor"],
                "r66_secondary_total_r": windows["r66"]["secondary"]["total_r"],
                "positive_all_three_secondary": all(
                    Decimal(str(row["secondary"]["total_r"])) > 0
                    for row in windows.values()
                ),
                "pf_above_one_all_three_secondary": all(
                    Decimal(str(row["secondary"]["profit_factor"] or "0"))
                    > Decimal("1")
                    for row in windows.values()
                ),
            }
        )
    return result


def build_report(
    *,
    nas100_root: Path,
    sp500_root: Path,
    us30_root: Path,
) -> dict[str, Any]:
    if not freeze.dependency_contract_matches():
        raise ValueError("R68 frozen R59/R58 dependency drift")
    if freeze.CANDIDATE_ID != r58.CANDIDATE_ID:
        raise ValueError("R68 frozen candidate identity drift")
    if r67.SOURCE_R66_DECISION != (
        "FAIL_R66_FRESH_HOLDOUT_REJECT_FROZEN_IDENTITY"
    ):
        raise ValueError("R68 source R66 failure decision drift")

    roots = {
        "NAS100": nas100_root,
        "SP500": sp500_root,
        "US30": us30_root,
    }
    five_stream, five_bars, _five_opened, five_provenance = (
        r31._build_source_complete_stream(roots=roots)
    )
    two_stream, two_bars, _two_opened, two_provenance = (
        r45._build_source_complete_stream_2y(roots=roots)
    )
    failed_stream, failed_bars, _failed_opened, failed_provenance = (
        r66._build_stream(roots=roots)
    )

    five = _window(
        stream=five_stream,
        bars_by_symbol={key: tuple(value) for key, value in five_bars.items()},
        provenance=five_provenance,
    )
    two = _window(
        stream=two_stream,
        bars_by_symbol={key: tuple(value) for key, value in two_bars.items()},
        provenance=two_provenance,
    )
    failed = _window(
        stream=failed_stream,
        bars_by_symbol={key: tuple(value) for key, value in failed_bars.items()},
        provenance=failed_provenance,
    )

    if (five["sample"], two["sample"], failed["sample"]) != (2448, 1017, 773):
        raise ValueError("R68 source-complete sample drift")

    transport = _variant_transport(five, two, failed)

    return {
        "schema": SCHEMA,
        "identity": IDENTITY,
        "source_failure": {
            "r66_identity": r66.IDENTITY,
            "r66_decision": r67.SOURCE_R66_DECISION,
            "r66_run_id": r67.SOURCE_R66_RUN_ID,
            "r66_artifact_id": r67.SOURCE_R66_ARTIFACT_ID,
            "r66_artifact_digest": r67.SOURCE_R66_ARTIFACT_DIGEST,
        },
        "frozen_candidate": {
            "candidate_id": freeze.CANDIDATE_ID,
            "rule_fingerprint": freeze.CANDIDATE_RULE_FINGERPRINT,
            "freeze_id": freeze.FREEZE_ID,
            "modified": False,
        },
        "policies": [
            {
                "policy_id": policy.policy_id,
                "structural_rearm": policy.structural_rearm,
                "fvg_cross_index": policy.fvg_cross_index,
                "fvg_h4_cisd": policy.fvg_h4_cisd,
                "late_revalidation": policy.late_revalidation,
            }
            for policy in POLICIES
        ],
        "five_year": five,
        "recent_two_year": two,
        "r66_failed_holdout": failed,
        "variant_transport": transport,
        "decision": "R68_CAUSAL_ABLATION_COMPLETE_NO_CANDIDATE_SELECTED",
        "governance": {
            "forensics_only": True,
            "bounded_mechanistic_ablation": True,
            "variant_grid_is_not_an_optimizer": True,
            "r66_consumed_failure_evidence": True,
            "fresh_holdout_claim": False,
            "frozen_r58_r59_modified": False,
            "replacement_candidate_created": False,
            "signal_surface_changed": False,
            "signals_suppressed": False,
            "entries_changed": False,
            "stops_changed": False,
            "targets_changed": False,
            "calendar_or_year_runtime_feature": False,
            "future_outcome_used_for_risk": False,
            "positive_risk_floor_preserved": True,
            "portfolio_budget_preserved": True,
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

    summary = {
        "identity": IDENTITY,
        "samples": {
            "five_year": report["five_year"]["sample"],
            "recent_two_year": report["recent_two_year"]["sample"],
            "r66": report["r66_failed_holdout"]["sample"],
        },
        "raw_unweighted": {
            "five_year": report["five_year"]["raw_unweighted"],
            "recent_two_year": report["recent_two_year"]["raw_unweighted"],
            "r66": report["r66_failed_holdout"]["raw_unweighted"],
        },
        "exact_r58_secondary_delta_vs_capped_base_r": {
            "five_year": report["five_year"][
                "exact_r58_secondary_delta_vs_capped_base_r"
            ],
            "recent_two_year": report["recent_two_year"][
                "exact_r58_secondary_delta_vs_capped_base_r"
            ],
            "r66": report["r66_failed_holdout"][
                "exact_r58_secondary_delta_vs_capped_base_r"
            ],
        },
        "source_availability": {
            "five_year": report["five_year"]["source_availability"],
            "recent_two_year": report["recent_two_year"]["source_availability"],
            "r66": report["r66_failed_holdout"]["source_availability"],
        },
        "variant_transport": report["variant_transport"],
        "decision": report["decision"],
    }
    print(json.dumps(summary, sort_keys=True))


if __name__ == "__main__":
    main()
