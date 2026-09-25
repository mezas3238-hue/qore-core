"""VT08 Index R47 — transport-safe structural demotion candidate.

R46 showed that the frozen R43 candidate did not transport to 2024-2026.
R47 creates a NEW candidate identity from three preregistered structural
failure cohorts that were negative in BOTH consumed windows.

No calendar/year label is available to runtime. No signal is removed. Risk is
never increased or reallocated after a demotion. Each affected trade is capped
at the existing canonical 0.005R floor.

Preregistered R46 evidence (secondary -0.10R, R34 baseline):
- SP500 LONG + H4 entry latency 61-120m:
  5Y PF ~0.272 / -1.123R; 2Y PF ~0.238 / -0.796R.
- LONG + formation tier B_FVG_CISD_LATENCY_4_7 + H4 latency 61-120m:
  5Y PF ~0.814 / -0.670R; 2Y PF ~0.033 / -2.405R.
- SHORT + cross-index state unanimous against side:
  5Y PF ~0.731 / -2.183R; 2Y PF ~0.319 / -1.141R.

The two economic windows are consumed evidence. R47 is not a fresh holdout and
does not grant demo, live, production, or real-capital authority.
"""

from __future__ import annotations

import argparse
import json
from collections.abc import Sequence
from datetime import UTC, datetime
from decimal import Decimal
from hashlib import sha256
from pathlib import Path
from typing import Any

from qore.infrastructure.trader_lab import vt08_index_concurrent_market_contract as contract
from qore.infrastructure.trader_lab import vt08_index_r6_5y_failure_forensics as fx
from qore.infrastructure.trader_lab import vt08_index_r15_concurrent_portfolio_validation as r15
from qore.infrastructure.trader_lab import vt08_index_r17_formation_quality_forensics as r17
from qore.infrastructure.trader_lab import vt08_index_r25_r23_failure_forensics as r25
from qore.infrastructure.trader_lab import (
    vt08_index_r31_source_complete_structural_concurrency as r31,
)
from qore.infrastructure.trader_lab import vt08_index_r34_hybrid_formation_poi_health as r34
from qore.infrastructure.trader_lab import vt08_index_r35_five_year_temporal_contract as r35
from qore.infrastructure.trader_lab import vt08_index_r43_sp500_long_stability_prior as r43
from qore.infrastructure.trader_lab import (
    vt08_index_r45_frozen_recent_2y_reproduction as r45,
)
from qore.infrastructure.trader_lab import vt08_index_v6_ttrades_source_faithful as v6
from qore.infrastructure.traders.contracts import DemoTradingSetupSide
from qore.infrastructure.traders.vt08_index_c2_positional_r1 import Vt08IndexC2R1Bar

SCHEMA = "qore.trader_lab.vt08_index_r47_transport_safe_structural_demotion.v1"
IDENTITY = "VT08_INDEX_R47_TRANSPORT_SAFE_STRUCTURAL_DEMOTION_001"
CANDIDATE_ID = "VT08_INDEX_R47_TRANSPORT_SAFE_STRUCTURAL_DEMOTION_001"

PRIMARY_STRESS = Decimal("0.05")
SECONDARY_STRESS = Decimal("0.10")
PF_PRIMARY_MIN = Decimal("1.50")
PF_SECONDARY_MIN = Decimal("1.30")
PORTFOLIO_DD_MAX = Decimal("6")
MIN_EFFECTIVE_WEIGHT = Decimal("0.005")

SOURCE_R46_RUN_ID = 35438709936
SOURCE_R46_ARTIFACT_ID = 10583481521
SOURCE_R46_ARTIFACT_DIGEST = (
    "sha256:3bfe175b7f2270ed57b0a4345a0bc722f3f5dbc110c1413bc1b068aba78c8052"
)
SOURCE_R46_HEAD_SHA = "5ae49f183f117f53f69e9aaac4a4a35bb30a9d81"

RULES = {
    "sp500_long_h4_entry_61_120_to_floor": True,
    "tier_b_long_h4_entry_61_120_to_floor": True,
    "short_cross_index_unanimous_against_to_floor": True,
    "demotion_floor_r": str(MIN_EFFECTIVE_WEIGHT),
    "freed_risk_reallocated": False,
    "signals_suppressed": False,
    "calendar_feature_used": False,
}

PREREGISTERED_EVIDENCE = {
    "SP500_LONG_H4_61_120": {
        "five_year_secondary_pf": "0.2722411278561011",
        "five_year_secondary_total_r": "-1.1227500000000004",
        "two_year_secondary_pf": "0.23827751196172242",
        "two_year_secondary_total_r": "-0.7959999999999999",
    },
    "B_LONG_H4_61_120": {
        "five_year_secondary_pf": "0.8143347312237894",
        "five_year_secondary_total_r": "-0.6696250000000005",
        "two_year_secondary_pf": "0.032582461786001604",
        "two_year_secondary_total_r": "-2.4050000000000002",
    },
    "SHORT_CROSS_INDEX_UNANIMOUS_AGAINST": {
        "five_year_secondary_pf": "0.7313120348205479",
        "five_year_secondary_total_r": "-2.183490084985836",
        "two_year_secondary_pf": "0.31885356023287054",
        "two_year_secondary_total_r": "-1.1407500000000004",
    },
}


def _fingerprint_payload() -> dict[str, Any]:
    return {
        "candidate_id": CANDIDATE_ID,
        "base_allocator": r34.IDENTITY,
        "base_poi_overlay": r43.BASE_POI_OVERLAY.payload(),
        "rules": RULES,
        "source_r46_run_id": SOURCE_R46_RUN_ID,
        "source_r46_artifact_id": SOURCE_R46_ARTIFACT_ID,
        "source_r46_artifact_digest": SOURCE_R46_ARTIFACT_DIGEST,
        "source_r46_head_sha": SOURCE_R46_HEAD_SHA,
    }


RULE_FINGERPRINT = sha256(
    json.dumps(
        _fingerprint_payload(),
        sort_keys=True,
        separators=(",", ":"),
    ).encode()
).hexdigest()


def _latest_completed_h4(
    h4: dict[datetime, Vt08IndexC2R1Bar],
    *,
    decision: datetime,
) -> Vt08IndexC2R1Bar | None:
    rows = [
        h4[key]
        for key in sorted(h4)
        if h4[key].closed_at.astimezone(UTC) <= decision.astimezone(UTC)
    ]
    return rows[-1] if rows else None


def _cross_index_state(
    *,
    h4_by_symbol: dict[str, dict[datetime, Vt08IndexC2R1Bar]],
    decision: datetime,
    side: DemoTradingSetupSide,
) -> str:
    wanted = 1 if side is DemoTradingSetupSide.LONG else -1
    signs: list[int] = []
    for symbol in contract.MARKETS:
        bar = _latest_completed_h4(
            h4_by_symbol[symbol],
            decision=decision,
        )
        if bar is None:
            return "insufficient"
        signs.append((bar.close > bar.open) - (bar.close < bar.open))
    if all(value == wanted for value in signs):
        return "unanimous_with_side"
    if all(value == -wanted for value in signs):
        return "unanimous_against_side"
    return "mixed"


def _rule_labels(
    item: r15.AssignedTrade,
    *,
    h4_by_symbol: dict[str, dict[datetime, Vt08IndexC2R1Bar]],
) -> tuple[str, ...]:
    opportunity = item.opportunity
    signal = opportunity.signal
    h4_latency = r17._bucket_h4_entry_latency(opportunity)
    tier = r25._quality_tier(opportunity)
    labels: list[str] = []

    if (
        item.symbol == "SP500"
        and signal.side is DemoTradingSetupSide.LONG
        and h4_latency == "61-120m"
    ):
        labels.append("SP500_LONG_H4_61_120")

    if (
        signal.side is DemoTradingSetupSide.LONG
        and tier == "B_FVG_CISD_LATENCY_4_7"
        and h4_latency == "61-120m"
    ):
        labels.append("B_LONG_H4_61_120")

    if signal.side is DemoTradingSetupSide.SHORT:
        state = _cross_index_state(
            h4_by_symbol=h4_by_symbol,
            decision=signal.signal_at,
            side=signal.side,
        )
        if state == "unanimous_against_side":
            labels.append("SHORT_CROSS_INDEX_UNANIMOUS_AGAINST")

    return tuple(labels)


def _apply_transport_rules(
    baseline: Sequence[r15.AssignedTrade],
    *,
    bars_by_symbol: dict[str, Sequence[Vt08IndexC2R1Bar]],
) -> tuple[tuple[r15.AssignedTrade, ...], dict[str, Any]]:
    h4_by_symbol = {
        symbol: v6._build_h4(
            {
                bar.opened_at.astimezone(UTC): bar
                for bar in bars
            }
        )
        for symbol, bars in bars_by_symbol.items()
    }
    result: list[r15.AssignedTrade] = []
    rule_hits = {
        "SP500_LONG_H4_61_120": 0,
        "B_LONG_H4_61_120": 0,
        "SHORT_CROSS_INDEX_UNANIMOUS_AGAINST": 0,
    }
    reduced = 0
    unchanged = 0
    overlaps = 0
    released_risk = Decimal()

    for item in baseline:
        labels = _rule_labels(item, h4_by_symbol=h4_by_symbol)
        for label in labels:
            rule_hits[label] += 1
        overlaps += int(len(labels) > 1)

        weight = item.weight
        if labels:
            weight = min(weight, MIN_EFFECTIVE_WEIGHT)
        if weight > item.weight:
            raise ValueError("R47 structural demotion may never increase risk")
        if weight < item.weight:
            reduced += 1
            released_risk += item.weight - weight
        else:
            unchanged += 1

        result.append(
            r15.AssignedTrade(
                trade_id=item.trade_id,
                opportunity=item.opportunity,
                outcome=item.outcome,
                context=item.context,
                weight=weight,
            )
        )

    if len(result) != len(baseline):
        raise ValueError("R47 changed source-complete trade count")
    if any(item.weight < MIN_EFFECTIVE_WEIGHT for item in result):
        raise ValueError("R47 fell below canonical positive-risk floor")

    return tuple(result), {
        "assigned_trade_count": len(result),
        "suppressed_trade_count": 0,
        "risk_increase_count": 0,
        "risk_reduced_count": reduced,
        "risk_unchanged_count": unchanged,
        "overlap_rule_trade_count": overlaps,
        "released_risk_not_reallocated_r": str(released_risk),
        "rule_hits": rule_hits,
        "minimum_effective_weight": str(min(item.weight for item in result)),
        "maximum_effective_weight": str(max(item.weight for item in result)),
        "mean_effective_weight": str(
            sum((item.weight for item in result), Decimal()) / len(result)
        ),
    }


def _window_metrics(
    assigned: tuple[r15.AssignedTrade, ...],
    *,
    bars_by_symbol: dict[str, Sequence[Vt08IndexC2R1Bar]],
    opened_by_symbol: dict[str, tuple[Any, ...]],
    years: int,
) -> dict[str, Any]:
    primary = fx._metrics(
        r15._realized_values(assigned, stress=PRIMARY_STRESS)
    )
    secondary = fx._metrics(
        r15._realized_values(assigned, stress=SECONDARY_STRESS)
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
    if years == 5:
        primary_blocks = r35._five_full_year_blocks(
            assigned,
            stress=PRIMARY_STRESS,
        )
        secondary_blocks = r35._five_full_year_blocks(
            assigned,
            stress=SECONDARY_STRESS,
        )
        temporal_pass = (
            r35._all_blocks_positive(primary_blocks)
            and r35._all_blocks_positive(secondary_blocks)
        )
    elif years == 2:
        primary_blocks = r45._two_year_blocks(
            assigned,
            stress=PRIMARY_STRESS,
        )
        secondary_blocks = r45._two_year_blocks(
            assigned,
            stress=SECONDARY_STRESS,
        )
        temporal_pass = (
            r45._all_blocks_positive(primary_blocks)
            and r45._all_blocks_positive(secondary_blocks)
        )
    else:
        raise ValueError(f"unsupported R47 window years={years}")

    density_pass = contract.validates_trade_count(
        years=years,
        sample=len(assigned),
    )
    economic_pass = (
        density_pass
        and Decimal(str(primary["profit_factor"] or "0")) >= PF_PRIMARY_MIN
        and Decimal(str(secondary["profit_factor"] or "0")) >= PF_SECONDARY_MIN
        and Decimal(str(primary_mtm["max_drawdown_r"])) <= PORTFOLIO_DD_MAX
        and Decimal(str(secondary_mtm["max_drawdown_r"])) <= PORTFOLIO_DD_MAX
        and temporal_pass
    )
    return {
        "sample": len(assigned),
        "primary": primary,
        "secondary": secondary,
        "primary_conservative_mark_to_market": primary_mtm,
        "secondary_conservative_mark_to_market": secondary_mtm,
        "primary_blocks": primary_blocks,
        "secondary_blocks": secondary_blocks,
        "density_pass": density_pass,
        "temporal_pass": temporal_pass,
        "economic_pass": economic_pass,
    }


def build_report(
    *,
    nas100_root: Path,
    sp500_root: Path,
    us30_root: Path,
) -> dict[str, Any]:
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

    five_base_row, five_baseline = r34._row(
        five_stream,
        overlay=r43.BASE_POI_OVERLAY,
    )
    two_base_row, two_baseline = r34._row(
        two_stream,
        overlay=r43.BASE_POI_OVERLAY,
    )

    five_assigned, five_diagnostics = _apply_transport_rules(
        five_baseline,
        bars_by_symbol=five_bars,
    )
    two_assigned, two_diagnostics = _apply_transport_rules(
        two_baseline,
        bars_by_symbol=two_bars,
    )

    five = _window_metrics(
        five_assigned,
        bars_by_symbol=five_bars,
        opened_by_symbol=five_opened,
        years=5,
    )
    two = _window_metrics(
        two_assigned,
        bars_by_symbol=two_bars,
        opened_by_symbol=two_opened,
        years=2,
    )
    goal_pass = (
        bool(five["economic_pass"])
        and bool(two["economic_pass"])
        and int(five_diagnostics["suppressed_trade_count"]) == 0
        and int(two_diagnostics["suppressed_trade_count"]) == 0
        and int(five_diagnostics["risk_increase_count"]) == 0
        and int(two_diagnostics["risk_increase_count"]) == 0
    )

    return {
        "schema": SCHEMA,
        "identity": IDENTITY,
        "candidate": {
            "candidate_id": CANDIDATE_ID,
            "rule_fingerprint": RULE_FINGERPRINT,
            "base_allocator": r34.IDENTITY,
            "r42_r43_static_priors_inherited": False,
            "rules": RULES,
            "preregistered_evidence": PREREGISTERED_EVIDENCE,
            "source_r46": {
                "run_id": SOURCE_R46_RUN_ID,
                "artifact_id": SOURCE_R46_ARTIFACT_ID,
                "artifact_digest": SOURCE_R46_ARTIFACT_DIGEST,
                "head_sha": SOURCE_R46_HEAD_SHA,
            },
        },
        "five_year": {
            **five,
            "baseline_r34": five_base_row,
            "diagnostics": five_diagnostics,
            "provenance": five_provenance,
        },
        "recent_two_year": {
            **two,
            "baseline_r34": two_base_row,
            "diagnostics": two_diagnostics,
            "provenance": two_provenance,
        },
        "goal_pass": goal_pass,
        "decision": (
            "PASS_DUAL_WINDOW_DEVELOPMENT_GATE"
            if goal_pass
            else "REJECT_OR_CONTINUE_RESEARCH"
        ),
        "governance": {
            "new_candidate_identity": True,
            "r43_r44_modified": False,
            "five_year_window_consumed": True,
            "two_year_window_consumed": True,
            "fresh_holdout_claim": False,
            "grid_search_used": False,
            "calendar_or_year_runtime_feature": False,
            "post_entry_outcome_runtime_feature": False,
            "all_signals_preserved": True,
            "zero_risk_allowed": False,
            "freed_risk_reallocated": False,
            "candidate_frozen": False,
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
                "candidate": report["candidate"],
                "five_year": {
                    key: report["five_year"][key]
                    for key in (
                        "sample",
                        "primary",
                        "secondary",
                        "primary_conservative_mark_to_market",
                        "secondary_conservative_mark_to_market",
                        "primary_blocks",
                        "secondary_blocks",
                        "economic_pass",
                    )
                },
                "recent_two_year": {
                    key: report["recent_two_year"][key]
                    for key in (
                        "sample",
                        "primary",
                        "secondary",
                        "primary_conservative_mark_to_market",
                        "secondary_conservative_mark_to_market",
                        "primary_blocks",
                        "secondary_blocks",
                        "economic_pass",
                    )
                },
                "goal_pass": report["goal_pass"],
                "decision": report["decision"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
