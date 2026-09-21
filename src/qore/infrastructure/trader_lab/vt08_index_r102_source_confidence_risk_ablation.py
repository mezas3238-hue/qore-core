"""VT08 Index R102 — source-confidence risk transport causal ablation.

R100 corrected the density semantics without changing the canonical signal
surface: every aligned POI + CISD + continuation remains a STANDARD source-valid
opportunity, while explicit liquidity/FVG Protected-Swing mechanism evidence is
additional confirmation rather than a universal gate.

R83/R68 showed the remaining failure is economic transport, especially on the
consumed R66 window. R102 asks a bounded mechanistic question:

    Did R58 promote risk too broadly across STANDARD signals that are valid
    but lack the additional explicit PS mechanism evidence?

No signal may be removed. No entry, stop, target, market, anchor, calendar or
year rule changes. No new risk constants are introduced.

Four fixed policies are compared:
1. EXACT_R58_CONTROL
   Exact frozen R58 overlay on all signals.
2. R47_BASE_CONTROL
   Exact R47 base, no R55/R58 promotions.
3. EXPLICIT_FULL_R58_STANDARD_BASE
   Explicit-PS-mechanism signals may use the existing full R58 promotions;
   STANDARD-without-extra-mechanism signals stay at their capped R47 request.
4. EXPLICIT_LATE_ONLY_STANDARD_BASE
   Same confidence split, but the explicit subset may use only the already
   established late-CISD-revalidation promotion (R68's most transport-stable
   mechanism). STANDARD stays at capped R47 request.

All policies preserve:
- canonical sample counts 2448 / 1017 / 773;
- R47 structural demotions;
- positive risk floor 0.005R;
- request cap 0.25R;
- portfolio budget 0.75R;
- no signal suppression.

R66 is consumed failure evidence. This stage performs causal attribution only;
it does not select or freeze a replacement candidate.
"""

from __future__ import annotations

import argparse
import heapq
import json
from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass
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
    vt08_index_r59_candidate_freeze as freeze,
)
from qore.infrastructure.trader_lab import (
    vt08_index_r66_fresh_historical_holdout as r66,
)
from qore.infrastructure.trader_lab import (
    vt08_index_r67_r66_failure_forensics as r67,
)
from qore.infrastructure.trader_lab import (
    vt08_index_r68_r58_risk_transport_ablation as r68,
)
from qore.infrastructure.trader_lab import (
    vt08_index_r74_ambiguous_bias_resolvers as r74,
)
from qore.infrastructure.trader_lab import (
    vt08_index_r82_protected_swing_source_qualification as r82,
)
from qore.infrastructure.trader_lab import (
    vt08_index_r100_cisd_ps_semantics_correction as r100,
)
from qore.infrastructure.trader_lab import (
    vt08_index_v6_ttrades_source_faithful as v6,
)
from qore.infrastructure.traders.vt08_index_c2_positional_r1 import (
    Vt08IndexC2R1Bar,
)

SCHEMA = "qore.trader_lab.vt08_index_r102_source_confidence_risk_ablation.v1"
IDENTITY = "VT08_INDEX_R102_SOURCE_CONFIDENCE_RISK_TRANSPORT_ABLATION_001"

SOURCE_R100_RUN_ID = 35553739444
SOURCE_R100_ARTIFACT_ID = 10619881275
SOURCE_R100_ARTIFACT_DIGEST = (
    "sha256:c58d8e8844c5b99e46ae94653ded118b0f6564d285afe8ecbcdff227d657bb4b"
)

PRIMARY_STRESS = r68.PRIMARY_STRESS
SECONDARY_STRESS = r68.SECONDARY_STRESS
MAX_REQUESTED_WEIGHT = r55.MAX_REQUESTED_WEIGHT
MIN_EFFECTIVE_WEIGHT = r55.MIN_EFFECTIVE_WEIGHT
PORTFOLIO_BUDGET_R = r55.PORTFOLIO_BUDGET_R

POLICY_EXACT_R58 = "EXACT_R58_CONTROL"
POLICY_R47 = "R47_BASE_CONTROL"
POLICY_EXPLICIT_FULL = "EXPLICIT_FULL_R58_STANDARD_BASE"
POLICY_EXPLICIT_LATE = "EXPLICIT_LATE_ONLY_STANDARD_BASE"
POLICIES = (
    POLICY_EXACT_R58,
    POLICY_R47,
    POLICY_EXPLICIT_FULL,
    POLICY_EXPLICIT_LATE,
)


@dataclass(frozen=True, slots=True)
class ConfidenceState:
    explicit_ps_mechanism: bool
    old_family: str


def _confidence_states(
    baseline: Sequence[r15.AssignedTrade],
    *,
    bars_by_symbol: dict[str, Sequence[Vt08IndexC2R1Bar]],
) -> dict[tuple[object, ...], ConfidenceState]:
    h4_cache = {
        symbol: r82._h4_bar_cache(bars)
        for symbol, bars in bars_by_symbol.items()
    }
    result: dict[tuple[object, ...], ConfidenceState] = {}
    for item in baseline:
        classification = r82._classify_opportunity(
            item.opportunity,
            h4_bars=h4_cache[item.symbol],
        )
        family = str(classification["family"])
        key = item.opportunity.identity()
        state = ConfidenceState(
            explicit_ps_mechanism=family != r82.FAMILY_UNQUALIFIED,
            old_family=family,
        )
        prior = result.get(key)
        if prior is not None and prior != state:
            raise ValueError("R102 confidence classification collision")
        result[key] = state
    if len(result) != len(baseline):
        raise ValueError("R102 confidence identity collision")
    return result


def _base_request(item: r15.AssignedTrade) -> Decimal:
    return max(
        MIN_EFFECTIVE_WEIGHT,
        min(item.weight, MAX_REQUESTED_WEIGHT),
    )


def _late_only_request(
    item: r15.AssignedTrade,
    *,
    h4_by_symbol: dict[str, dict[datetime, Vt08IndexC2R1Bar]],
    reaction_bars: dict[str, tuple[Any, ...]],
    reaction_opened: dict[str, tuple[datetime, ...]],
) -> tuple[Decimal, tuple[str, ...]]:
    base = _base_request(item)
    r47_labels = r47._rule_labels(
        item,
        h4_by_symbol=h4_by_symbol,
    )
    if r47_labels:
        return base, tuple(f"R47:{label}" for label in r47_labels)

    if r55._late_revalidation(
        item,
        bars=reaction_bars[item.symbol],
        opened=reaction_opened[item.symbol],
    ):
        return (
            max(base, r55.LATE_REVALIDATION_MIN_WEIGHT),
            ("CISD_LATE_REVALIDATION",),
        )
    return base, ()


def _apply_confidence_policy(
    baseline: Sequence[r15.AssignedTrade],
    *,
    bars_by_symbol: dict[str, Sequence[Vt08IndexC2R1Bar]],
    policy_id: str,
) -> tuple[tuple[r15.AssignedTrade, ...], dict[str, Any]]:
    if policy_id not in (POLICY_EXPLICIT_FULL, POLICY_EXPLICIT_LATE):
        raise ValueError(f"R102 unsupported confidence policy: {policy_id}")

    confidence = _confidence_states(
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
    reaction_bars, reaction_opened = r55._reaction_bars(
        bars_by_symbol
    )

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
    diagnostics: Counter[str] = Counter()
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
            state = confidence[item.opportunity.identity()]
            if not state.explicit_ps_mechanism:
                value = _base_request(item)
                labels: tuple[str, ...] = ()
                diagnostics["STANDARD_BASE_REQUEST"] += 1
            elif policy_id == POLICY_EXPLICIT_FULL:
                value, labels = r55._requested_weight(
                    item,
                    h4_by_symbol=h4_by_symbol,
                    reaction_bars=reaction_bars,
                    reaction_opened=reaction_opened,
                )
                diagnostics["EXPLICIT_FULL_R58_REQUEST"] += 1
            else:
                value, labels = _late_only_request(
                    item,
                    h4_by_symbol=h4_by_symbol,
                    reaction_bars=reaction_bars,
                    reaction_opened=reaction_opened,
                )
                diagnostics["EXPLICIT_LATE_ONLY_REQUEST"] += 1

            requested.append(value)
            if value > _base_request(item):
                diagnostics["PROMOTED_ABOVE_BASE_REQUEST"] += 1
            for label in labels:
                if label.startswith("R47:"):
                    diagnostics["R47_DEMOTION_PROTECTED"] += 1
                else:
                    diagnostics[f"PROMOTION:{label}"] += 1

        active_risk = sum(active.values(), Decimal())
        weights, scaled = r22._allocate_batch(
            requested,
            active_risk=active_risk,
            budget=PORTFOLIO_BUDGET_R,
        )
        diagnostics["BUDGET_SCALED_BATCH"] += int(scaled)
        if active_risk + sum(weights, Decimal()) > PORTFOLIO_BUDGET_R:
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
        raise ValueError("R102 confidence policy changed trade count")
    if any(item.weight < MIN_EFFECTIVE_WEIGHT for item in result):
        raise ValueError("R102 violated positive-risk floor")
    if any(item.weight > MAX_REQUESTED_WEIGHT for item in result):
        raise ValueError("R102 exceeded request cap")

    diagnostics["ASSIGNED_TRADE_COUNT"] = len(result)
    diagnostics["SUPPRESSED_TRADE_COUNT"] = 0
    return result, {
        "policy_id": policy_id,
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


def _r66_metrics(
    assigned: tuple[r15.AssignedTrade, ...],
    *,
    bars_by_symbol: dict[str, Sequence[Vt08IndexC2R1Bar]],
    opened_by_symbol: dict[str, tuple[datetime, ...]],
) -> dict[str, Any]:
    primary = r68._weighted_metrics(
        assigned,
        stress=PRIMARY_STRESS,
    )
    secondary = r68._weighted_metrics(
        assigned,
        stress=SECONDARY_STRESS,
    )
    primary_mtm = r15._portfolio_mark_to_market(
        assigned,
        bars_by_symbol=bars_by_symbol,
        opened_by_symbol=opened_by_symbol,
        stress=PRIMARY_STRESS,
        adverse=True,
    )
    secondary_mtm = r15._portfolio_mark_to_market(
        assigned,
        bars_by_symbol=bars_by_symbol,
        opened_by_symbol=opened_by_symbol,
        stress=SECONDARY_STRESS,
        adverse=True,
    )
    primary_blocks = r66._holdout_blocks(
        assigned,
        stress=PRIMARY_STRESS,
    )
    secondary_blocks = r66._holdout_blocks(
        assigned,
        stress=SECONDARY_STRESS,
    )
    return {
        "sample": len(assigned),
        "primary": primary,
        "secondary": secondary,
        "primary_conservative_mark_to_market": primary_mtm,
        "secondary_conservative_mark_to_market": secondary_mtm,
        "primary_blocks": primary_blocks,
        "secondary_blocks": secondary_blocks,
        "all_primary_blocks_positive": r66._blocks_positive(
            primary_blocks
        ),
        "all_secondary_blocks_positive": r66._blocks_positive(
            secondary_blocks
        ),
    }


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
    if len(stream) != expected:
        raise ValueError(f"R102 {window_id} sample drift")

    bars = {
        key: tuple(value)
        for key, value in bars_by_symbol.items()
    }
    opened = {
        symbol: tuple(
            bar.opened_at.astimezone(UTC)
            for bar in symbol_bars
        )
        for symbol, symbol_bars in bars.items()
    }

    base, r47_diagnostics = r58._exact_r47(
        tuple(stream),
        bars_by_symbol=bars,
    )
    base = tuple(base)
    exact_r58, r58_diagnostics = r55._apply_candidate(
        base,
        bars_by_symbol=bars,
    )
    exact_r58 = tuple(exact_r58)

    variants: dict[str, tuple[r15.AssignedTrade, ...]] = {
        POLICY_R47: base,
        POLICY_EXACT_R58: exact_r58,
    }
    diagnostics: dict[str, Any] = {
        POLICY_R47: r47_diagnostics,
        POLICY_EXACT_R58: r58_diagnostics,
    }
    for policy_id in (
        POLICY_EXPLICIT_FULL,
        POLICY_EXPLICIT_LATE,
    ):
        assigned, policy_diag = _apply_confidence_policy(
            base,
            bars_by_symbol=bars,
            policy_id=policy_id,
        )
        variants[policy_id] = assigned
        diagnostics[policy_id] = policy_diag

    results: dict[str, Any] = {}
    for policy_id, assigned in variants.items():
        if len(assigned) != expected:
            raise ValueError(
                f"R102 {window_id} {policy_id} changed sample"
            )
        if window_id == "5Y":
            metrics = r47._window_metrics(
                assigned,
                bars_by_symbol=bars,
                opened_by_symbol=opened,
                years=5,
            )
        elif window_id == "2Y":
            metrics = r47._window_metrics(
                assigned,
                bars_by_symbol=bars,
                opened_by_symbol=opened,
                years=2,
            )
        else:
            metrics = _r66_metrics(
                assigned,
                bars_by_symbol=bars,
                opened_by_symbol=opened,
            )

        results[policy_id] = {
            "metrics": metrics,
            "concentration": r55._concentration(assigned),
            "diagnostics": diagnostics[policy_id],
        }

    return {
        "window_id": window_id,
        "sample": expected,
        "policies": results,
        "provenance": provenance,
    }


def _transport_summary(
    five: dict[str, Any],
    two: dict[str, Any],
    failed: dict[str, Any],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for policy_id in POLICIES:
        five_metrics = five["policies"][policy_id]["metrics"]
        two_metrics = two["policies"][policy_id]["metrics"]
        failed_metrics = failed["policies"][policy_id]["metrics"]
        rows.append(
            {
                "policy_id": policy_id,
                "samples": {
                    "five_year": int(five_metrics["sample"]),
                    "recent_two_year": int(two_metrics["sample"]),
                    "r66": int(failed_metrics["sample"]),
                },
                "five_year": {
                    "primary_pf": five_metrics["primary"][
                        "profit_factor"
                    ],
                    "secondary_pf": five_metrics["secondary"][
                        "profit_factor"
                    ],
                    "secondary_total_r": five_metrics["secondary"][
                        "total_r"
                    ],
                    "primary_mtm_dd_r": five_metrics[
                        "primary_conservative_mark_to_market"
                    ]["max_drawdown_r"],
                    "secondary_mtm_dd_r": five_metrics[
                        "secondary_conservative_mark_to_market"
                    ]["max_drawdown_r"],
                    "temporal_pass": five_metrics["temporal_pass"],
                },
                "recent_two_year": {
                    "primary_pf": two_metrics["primary"][
                        "profit_factor"
                    ],
                    "secondary_pf": two_metrics["secondary"][
                        "profit_factor"
                    ],
                    "secondary_total_r": two_metrics["secondary"][
                        "total_r"
                    ],
                    "primary_mtm_dd_r": two_metrics[
                        "primary_conservative_mark_to_market"
                    ]["max_drawdown_r"],
                    "secondary_mtm_dd_r": two_metrics[
                        "secondary_conservative_mark_to_market"
                    ]["max_drawdown_r"],
                    "temporal_pass": two_metrics["temporal_pass"],
                },
                "r66": {
                    "primary_pf": failed_metrics["primary"][
                        "profit_factor"
                    ],
                    "secondary_pf": failed_metrics["secondary"][
                        "profit_factor"
                    ],
                    "primary_total_r": failed_metrics["primary"][
                        "total_r"
                    ],
                    "secondary_total_r": failed_metrics["secondary"][
                        "total_r"
                    ],
                    "primary_mtm_dd_r": failed_metrics[
                        "primary_conservative_mark_to_market"
                    ]["max_drawdown_r"],
                    "secondary_mtm_dd_r": failed_metrics[
                        "secondary_conservative_mark_to_market"
                    ]["max_drawdown_r"],
                    "all_primary_blocks_positive": failed_metrics[
                        "all_primary_blocks_positive"
                    ],
                    "all_secondary_blocks_positive": failed_metrics[
                        "all_secondary_blocks_positive"
                    ],
                },
            }
        )
    return rows


def build_report(
    *,
    nas100_root: Path,
    sp500_root: Path,
    us30_root: Path,
) -> dict[str, Any]:
    if not freeze.dependency_contract_matches():
        raise ValueError("R102 frozen R58/R59 dependency drift")
    if r67.SOURCE_R66_DECISION != (
        "FAIL_R66_FRESH_HOLDOUT_REJECT_FROZEN_IDENTITY"
    ):
        raise ValueError("R102 source R66 failure decision drift")
    if r100.IDENTITY != (
        "VT08_INDEX_R100_CISD_PROTECTED_SWING_SEMANTICS_CORRECTION_001"
    ):
        raise ValueError("R102 R100 semantics drift")

    roots = {
        "NAS100": nas100_root,
        "SP500": sp500_root,
        "US30": us30_root,
    }
    five = _window(roots=roots, window_id="5Y")
    two = _window(roots=roots, window_id="2Y")
    failed = _window(roots=roots, window_id="R66")

    if (
        five["sample"],
        two["sample"],
        failed["sample"],
    ) != (2448, 1017, 773):
        raise ValueError("R102 canonical density drift")

    return {
        "schema": SCHEMA,
        "identity": IDENTITY,
        "source_r100": {
            "run_id": SOURCE_R100_RUN_ID,
            "artifact_id": SOURCE_R100_ARTIFACT_ID,
            "artifact_digest": SOURCE_R100_ARTIFACT_DIGEST,
        },
        "confidence_contract": {
            "standard_cisd_is_source_valid": True,
            "explicit_ps_mechanism_is_extra_confirmation": True,
            "signals_suppressed": False,
            "entries_changed": False,
            "stops_changed": False,
            "targets_changed": False,
            "new_risk_constants_introduced": False,
            "minimum_effective_weight_r": str(MIN_EFFECTIVE_WEIGHT),
            "maximum_requested_weight_r": str(MAX_REQUESTED_WEIGHT),
            "portfolio_budget_r": str(PORTFOLIO_BUDGET_R),
            "late_revalidation_min_weight_r": str(
                r55.LATE_REVALIDATION_MIN_WEIGHT
            ),
        },
        "policies": list(POLICIES),
        "five_year": five,
        "recent_two_year": two,
        "r66_failed_holdout": failed,
        "transport_summary": _transport_summary(
            five,
            two,
            failed,
        ),
        "decision": "R102_SOURCE_CONFIDENCE_RISK_ABLATION_COMPLETE_NO_CANDIDATE_SELECTED",
        "governance": {
            "forensics_only": True,
            "bounded_mechanistic_ablation": True,
            "variant_grid_is_not_an_optimizer": True,
            "r66_consumed_failure_evidence": True,
            "fresh_holdout_claim": False,
            "canonical_signal_surface_preserved": True,
            "signals_suppressed": False,
            "future_outcome_used_for_risk": False,
            "numeric_risk_search": False,
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
                "transport_summary": report["transport_summary"],
                "decision": report["decision"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
