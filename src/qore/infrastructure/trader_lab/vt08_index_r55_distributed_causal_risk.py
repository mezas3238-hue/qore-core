"""VT08 Index R55 — distributed causal risk candidate.

R55 is a new development candidate built only after R51 exposed concentration
fragility and R53/R54 reused existing Core laboratories to isolate causal
supporting structures. It preserves the complete R47 trade surface and does not
change entries, stops, targets, or structural rearm mechanics.

The candidate uses only pre-entry information:
- retain every R47 structural demotion at the 0.005R floor;
- cap every remaining requested trade at 0.25R;
- give non-demoted structural rearm at least the frozen tier-C 0.10R weight;
- give supported FVG states 0.25R when either cross-index H4 state is unanimous
  with the trade side, or the existing R17 dual-latency state is
  H4 121-180m + CISD 4-7 M15 bars;
- give a CISD late-revalidation state 0.25R when the existing Reaction Atlas
  detects a favorable liquidity-take no more than 15 minutes before entry,
  after the already-confirmed CISD, with R17 continuation latency 5+.

The 0.10R and 0.25R levels are existing Core quality/risk ladder values. The
portfolio budget remains the existing 0.75R QORE budget. All evidence windows
are consumed development evidence; R55 is not a fresh holdout or certification.
"""

from __future__ import annotations

import argparse
import heapq
import json
from collections.abc import Sequence
from datetime import UTC, datetime
from decimal import Decimal
from hashlib import sha256
from pathlib import Path
from typing import Any

from qore.infrastructure.trader_lab import vt08_index_market_journey_atlas as journey
from qore.infrastructure.trader_lab import vt08_index_r6_5y_failure_forensics as fx
from qore.infrastructure.trader_lab import vt08_index_r15_concurrent_portfolio_validation as r15
from qore.infrastructure.trader_lab import vt08_index_r17_formation_quality_forensics as r17
from qore.infrastructure.trader_lab import vt08_index_r22_concurrent_stable_formation as r22
from qore.infrastructure.trader_lab import vt08_index_r24_open_position_pressure as r24
from qore.infrastructure.trader_lab import vt08_index_v6_ttrades_source_faithful as v6
from qore.infrastructure.trader_lab import (
    vt08_index_r31_source_complete_structural_concurrency as r31,
)
from qore.infrastructure.trader_lab import (
    vt08_index_r45_frozen_recent_2y_reproduction as r45,
)
from qore.infrastructure.trader_lab import (
    vt08_index_r46_cross_window_transport_forensics as r46,
)
from qore.infrastructure.trader_lab import (
    vt08_index_r47_transport_safe_structural_demotion as r47,
)
from qore.infrastructure.trader_lab import vt08_index_r48_candidate_freeze as freeze
from qore.infrastructure.trader_lab import (
    vt08_index_r53_cisd_reaction_quality_forensics as r53,
)
from qore.infrastructure.traders.vt08_index_c2_positional_r1 import Vt08IndexC2R1Bar

SCHEMA = "qore.trader_lab.vt08_index_r55_distributed_causal_risk.v1"
IDENTITY = "VT08_INDEX_R55_DISTRIBUTED_CAUSAL_RISK_001"
CANDIDATE_ID = IDENTITY

PRIMARY_STRESS = Decimal("0.05")
SECONDARY_STRESS = Decimal("0.10")
EXTRA_STRESSES = (Decimal("0.15"), Decimal("0.20"))
MAX_REQUESTED_WEIGHT = Decimal("0.25")
REARM_MIN_WEIGHT = Decimal("0.10")
SUPPORTED_FVG_MIN_WEIGHT = Decimal("0.25")
LATE_REVALIDATION_MIN_WEIGHT = Decimal("0.25")
MIN_EFFECTIVE_WEIGHT = Decimal("0.005")
PORTFOLIO_BUDGET_R = Decimal("0.75")
EXTRA_STRESS_PF_MIN = Decimal("1.30")
TOP_WINNER_REMOVAL_COUNT = 3

SOURCE_R51_RUN_ID = 35449205440
SOURCE_R51_ARTIFACT_ID = 10586424229
SOURCE_R51_ARTIFACT_DIGEST = (
    "sha256:c55f8a761f2c441218858b71ea4b3e0c1e9a22dbdad9a99cfad3f27602f3b979"
)
SOURCE_R54_RUN_ID = 35454611934
SOURCE_R54_ARTIFACT_ID = 10587507821
SOURCE_R54_ARTIFACT_DIGEST = (
    "sha256:a5977432566f3695417743db6f356886df7fc8e31b82599d51efa210d8f0a0a4"
)

RULES: dict[str, object] = {
    "preserve_r47_demotions": True,
    "max_requested_weight_r": str(MAX_REQUESTED_WEIGHT),
    "non_demoted_rearm_min_weight_r": str(REARM_MIN_WEIGHT),
    "fvg_cross_index_unanimous_with_side_min_weight_r": str(
        SUPPORTED_FVG_MIN_WEIGHT
    ),
    "fvg_h4_121_180_and_cisd_4_7_min_weight_r": str(
        SUPPORTED_FVG_MIN_WEIGHT
    ),
    "late_cisd_revalidation_min_weight_r": str(LATE_REVALIDATION_MIN_WEIGHT),
    "portfolio_budget_r": str(PORTFOLIO_BUDGET_R),
    "minimum_effective_weight_r": str(MIN_EFFECTIVE_WEIGHT),
    "signals_suppressed": False,
    "freed_risk_opportunistically_reallocated": False,
    "calendar_or_year_runtime_feature": False,
}


def _fingerprint_payload() -> dict[str, object]:
    return {
        "candidate_id": CANDIDATE_ID,
        "r47_candidate_id": freeze.CANDIDATE_ID,
        "r47_rule_fingerprint": freeze.CANDIDATE_RULE_FINGERPRINT,
        "rules": RULES,
        "source_r51_run_id": SOURCE_R51_RUN_ID,
        "source_r51_artifact_id": SOURCE_R51_ARTIFACT_ID,
        "source_r51_artifact_digest": SOURCE_R51_ARTIFACT_DIGEST,
        "source_r54_run_id": SOURCE_R54_RUN_ID,
        "source_r54_artifact_id": SOURCE_R54_ARTIFACT_ID,
        "source_r54_artifact_digest": SOURCE_R54_ARTIFACT_DIGEST,
    }


RULE_FINGERPRINT = sha256(
    json.dumps(
        _fingerprint_payload(),
        sort_keys=True,
        separators=(",", ":"),
    ).encode()
).hexdigest()


def _reaction_bars(
    bars_by_symbol: dict[str, Sequence[Vt08IndexC2R1Bar]],
) -> tuple[
    dict[str, tuple[journey.Bar, ...]],
    dict[str, tuple[datetime, ...]],
]:
    converted = {
        symbol: r53._as_reaction_bars(tuple(bars))
        for symbol, bars in bars_by_symbol.items()
    }
    opened = {
        symbol: tuple(bar.opened_at for bar in bars)
        for symbol, bars in converted.items()
    }
    return converted, opened


def _late_revalidation(
    item: r15.AssignedTrade,
    *,
    bars: Sequence[journey.Bar],
    opened: Sequence[datetime],
) -> bool:
    opportunity = item.opportunity
    if str(opportunity.source_poi_kind) != "cisd":
        return False
    if r17._bucket_continuation_latency(opportunity) != "5+":
        return False
    context = r53._reaction_context(
        item,
        bars=bars,
        opened=opened,
    )
    if not bool(context["fresh_liquidity_take_15m"]):
        return False
    raw_reaction_at = context.get("reaction_at")
    if raw_reaction_at is None:
        return False
    reaction_at = datetime.fromisoformat(
        str(raw_reaction_at).replace("Z", "+00:00")
    )
    if reaction_at.tzinfo is None:
        reaction_at = reaction_at.replace(tzinfo=UTC)
    return (
        reaction_at.astimezone(UTC)
        > opportunity.signal.cisd_confirmed_at.astimezone(UTC)
    )


def _requested_weight(
    item: r15.AssignedTrade,
    *,
    h4_by_symbol: dict[str, dict[datetime, Vt08IndexC2R1Bar]],
    reaction_bars: dict[str, tuple[journey.Bar, ...]],
    reaction_opened: dict[str, tuple[datetime, ...]],
) -> tuple[Decimal, tuple[str, ...]]:
    opportunity = item.opportunity
    signal = opportunity.signal
    r47_labels = r47._rule_labels(
        item,
        h4_by_symbol=h4_by_symbol,
    )
    requested = min(item.weight, MAX_REQUESTED_WEIGHT)
    labels: list[str] = []

    if r47_labels:
        return requested, tuple(f"R47:{label}" for label in r47_labels)

    if int(opportunity.rearm_index) > 0:
        requested = max(requested, REARM_MIN_WEIGHT)
        labels.append("STRUCTURAL_REARM")

    if str(opportunity.source_poi_kind) == "fvg":
        cross_state = r47._cross_index_state(
            h4_by_symbol=h4_by_symbol,
            decision=signal.signal_at,
            side=signal.side,
        )
        if cross_state == "unanimous_with_side":
            requested = max(requested, SUPPORTED_FVG_MIN_WEIGHT)
            labels.append("FVG_CROSS_INDEX_UNANIMOUS_WITH_SIDE")

        if (
            r17._bucket_h4_entry_latency(opportunity) == "121-180m"
            and r17._bucket_cisd_latency(opportunity) == "4-7"
        ):
            requested = max(requested, SUPPORTED_FVG_MIN_WEIGHT)
            labels.append("FVG_H4_121_180_CISD_4_7")

    if _late_revalidation(
        item,
        bars=reaction_bars[item.symbol],
        opened=reaction_opened[item.symbol],
    ):
        requested = max(requested, LATE_REVALIDATION_MIN_WEIGHT)
        labels.append("CISD_LATE_REVALIDATION")

    return max(MIN_EFFECTIVE_WEIGHT, requested), tuple(labels)


def _apply_candidate(
    baseline: Sequence[r15.AssignedTrade],
    *,
    bars_by_symbol: dict[str, Sequence[Vt08IndexC2R1Bar]],
) -> tuple[tuple[r15.AssignedTrade, ...], dict[str, object]]:
    h4_by_symbol = {
        symbol: v6._build_h4(
            {
                bar.opened_at.astimezone(UTC): bar
                for bar in bars
            }
        )
        for symbol, bars in bars_by_symbol.items()
    }
    reaction_bars, reaction_opened = _reaction_bars(bars_by_symbol)
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
    cap_reductions = 0
    risk_increases = 0
    risk_decreases = 0
    budget_scaled_batches = 0
    floor_overage_batches = 0
    max_committed = Decimal()

    def settle(until: datetime) -> None:
        while exit_heap and exit_heap[0][0] <= until:
            _exit_at, trade_id = heapq.heappop(exit_heap)
            active.pop(trade_id, None)

    while cursor < len(ordered):
        batch_time = ordered[cursor].opportunity.signal.signal_at.astimezone(
            UTC
        )
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
        batch_labels: list[tuple[str, ...]] = []
        for item in batch:
            value, labels = _requested_weight(
                item,
                h4_by_symbol=h4_by_symbol,
                reaction_bars=reaction_bars,
                reaction_opened=reaction_opened,
            )
            requested.append(value)
            batch_labels.append(labels)
            cap_reductions += int(item.weight > MAX_REQUESTED_WEIGHT)
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
            risk_increases += int(weight > item.weight)
            risk_decreases += int(weight < item.weight)
            replaced = r15.AssignedTrade(
                trade_id=next_trade_id,
                opportunity=item.opportunity,
                outcome=item.outcome,
                context=item.context,
                weight=weight,
            )
            next_trade_id += 1
            assigned.append(replaced)
            active[replaced.trade_id] = weight
            heapq.heappush(
                exit_heap,
                (
                    replaced.exited_at.astimezone(UTC),
                    replaced.trade_id,
                ),
            )

        max_committed = max(
            max_committed,
            sum(active.values(), Decimal()),
        )
        cursor = end

    if len(assigned) != len(baseline):
        raise ValueError("R55 changed source-complete trade count")
    if any(item.weight < MIN_EFFECTIVE_WEIGHT for item in assigned):
        raise ValueError("R55 fell below canonical positive-risk floor")
    if any(item.weight > MAX_REQUESTED_WEIGHT for item in assigned):
        raise ValueError("R55 exceeded concentration cap after allocation")

    return tuple(assigned), {
        "assigned_trade_count": len(assigned),
        "suppressed_trade_count": 0,
        "cap_reduction_count": cap_reductions,
        "risk_increase_count": risk_increases,
        "risk_decrease_count": risk_decreases,
        "budget_scaled_batches": budget_scaled_batches,
        "floor_overage_batches": floor_overage_batches,
        "max_committed_structural_risk_r": str(max_committed),
        "minimum_effective_weight": str(
            min(item.weight for item in assigned)
        ),
        "maximum_effective_weight": str(
            max(item.weight for item in assigned)
        ),
        "mean_effective_weight": str(
            sum((item.weight for item in assigned), Decimal())
            / len(assigned)
        ),
        "rule_hits": rule_hits,
    }


def _stress_metrics(
    assigned: Sequence[r15.AssignedTrade],
    *,
    stress: Decimal,
) -> dict[str, Any]:
    return fx._metrics(
        tuple(
            (item.outcome.r_multiple - stress) * item.weight
            for item in sorted(
                assigned,
                key=lambda row: (
                    row.exited_at,
                    row.symbol,
                    row.trade_id,
                ),
            )
        )
    )


def _concentration(
    assigned: Sequence[r15.AssignedTrade],
) -> dict[str, object]:
    values = [
        (item.outcome.r_multiple - SECONDARY_STRESS) * item.weight
        for item in sorted(
            assigned,
            key=lambda row: (
                row.exited_at,
                row.symbol,
                row.trade_id,
            ),
        )
    ]
    positive = sorted(
        (value for value in values if value > 0),
        reverse=True,
    )
    total = sum(values, Decimal())
    removed = list(values)
    contribution = sum(
        positive[:TOP_WINNER_REMOVAL_COUNT],
        Decimal(),
    )
    for value in positive[:TOP_WINNER_REMOVAL_COUNT]:
        removed.remove(value)
    leave = fx._metrics(tuple(removed))
    return {
        "terminal_r": str(total),
        "top_3_winner_contribution_r": str(contribution),
        "top_3_winner_fraction_of_terminal": (
            str(contribution / total) if total > 0 else None
        ),
        "leave_top_3_out": leave,
        "leave_top_3_positive": Decimal(str(leave["total_r"])) > 0,
    }


def _window(
    *,
    r43_assigned: Sequence[r15.AssignedTrade],
    bars_by_symbol: dict[str, Sequence[Vt08IndexC2R1Bar]],
    opened_by_symbol: dict[str, tuple[Any, ...]],
    years: int,
) -> dict[str, object]:
    r47_assigned, r47_diagnostics = r47._apply_transport_rules(
        r43_assigned,
        bars_by_symbol=bars_by_symbol,
    )
    candidate, diagnostics = _apply_candidate(
        r47_assigned,
        bars_by_symbol=bars_by_symbol,
    )
    economic = r47._window_metrics(
        candidate,
        bars_by_symbol=bars_by_symbol,
        opened_by_symbol=opened_by_symbol,
        years=years,
    )
    concentration = _concentration(candidate)
    extra = {
        str(stress): _stress_metrics(candidate, stress=stress)
        for stress in EXTRA_STRESSES
    }
    extra_pass = all(
        Decimal(str(metrics["total_r"])) > 0
        and Decimal(str(metrics["profit_factor"] or "0"))
        >= EXTRA_STRESS_PF_MIN
        for metrics in extra.values()
    )
    return {
        "sample": len(candidate),
        "economic": economic,
        "r47_diagnostics": r47_diagnostics,
        "r55_diagnostics": diagnostics,
        "concentration": concentration,
        "extra_stress": extra,
        "extra_stress_pass": extra_pass,
        "window_pass": (
            bool(economic["economic_pass"])
            and bool(concentration["leave_top_3_positive"])
            and extra_pass
        ),
    }


def build_report(
    *,
    nas100_root: Path,
    sp500_root: Path,
    us30_root: Path,
) -> dict[str, object]:
    if not freeze.dependency_contract_matches():
        raise ValueError("R55 frozen R47 dependency contract drift")
    if r24.BASE_RISK.portfolio_risk_budget_r != PORTFOLIO_BUDGET_R:
        raise ValueError("R55 portfolio budget drift")

    roots = {
        "NAS100": nas100_root,
        "SP500": sp500_root,
        "US30": us30_root,
    }
    five_stream, five_bars, five_opened, five_provenance = (
        r31._build_source_complete_stream(roots=roots)
    )
    two_stream, two_bars, two_opened, two_provenance = (
        r45._build_source_complete_stream_2y(roots=roots)
    )
    five_r43, _five_trace = r46._frozen_assignment(five_stream)
    two_r43, _two_trace = r46._frozen_assignment(two_stream)

    five = _window(
        r43_assigned=five_r43,
        bars_by_symbol={
            key: tuple(value)
            for key, value in five_bars.items()
        },
        opened_by_symbol=five_opened,
        years=5,
    )
    two = _window(
        r43_assigned=two_r43,
        bars_by_symbol={
            key: tuple(value)
            for key, value in two_bars.items()
        },
        opened_by_symbol=two_opened,
        years=2,
    )

    development_pass = bool(five["window_pass"]) and bool(two["window_pass"])
    return {
        "schema": SCHEMA,
        "identity": IDENTITY,
        "candidate_id": CANDIDATE_ID,
        "rule_fingerprint": RULE_FINGERPRINT,
        "rules": RULES,
        "five_year": five,
        "recent_two_year": two,
        "development_pass": development_pass,
        "source_evidence": {
            "r47_freeze": {
                "run_id": freeze.SOURCE_RUN_ID,
                "artifact_id": freeze.SOURCE_ARTIFACT_ID,
                "artifact_digest": freeze.SOURCE_ARTIFACT_DIGEST,
            },
            "r51_concentration": {
                "run_id": SOURCE_R51_RUN_ID,
                "artifact_id": SOURCE_R51_ARTIFACT_ID,
                "artifact_digest": SOURCE_R51_ARTIFACT_DIGEST,
            },
            "r54_semantic_sequence": {
                "run_id": SOURCE_R54_RUN_ID,
                "artifact_id": SOURCE_R54_ARTIFACT_ID,
                "artifact_digest": SOURCE_R54_ARTIFACT_DIGEST,
            },
        },
        "provenance": {
            "five_year": five_provenance,
            "recent_two_year": two_provenance,
        },
        "governance": {
            "development_only": True,
            "consumed_evidence_only": True,
            "fresh_holdout_claim": False,
            "existing_core_labs_reused": True,
            "entry_changed": False,
            "stop_changed": False,
            "target_changed": False,
            "structural_rearm_mechanics_changed": False,
            "same_symbol_structural_concurrency_preserved": True,
            "signals_suppressed": False,
            "zero_risk_allowed": False,
            "post_entry_outcome_runtime_feature": False,
            "calendar_or_year_runtime_feature": False,
            "freed_risk_opportunistically_reallocated": False,
            "certified": False,
            "demo_eligible": False,
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
                "candidate_id": CANDIDATE_ID,
                "rule_fingerprint": RULE_FINGERPRINT,
                "development_pass": report["development_pass"],
                "five_year": report["five_year"],
                "recent_two_year": report["recent_two_year"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
