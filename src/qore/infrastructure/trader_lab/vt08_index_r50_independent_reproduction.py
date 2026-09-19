"""VT08 Index R50 — independent frozen-candidate reproduction.

This validator deliberately does not call R47's rule-label or rule-application
functions. It independently reconstructs the frozen structural demotions from
R48, applies them to the same source-complete R34 baseline, and then compares
the complete trade ledger against the canonical R47 implementation.

The purpose is implementation independence, branch-level quality binding, and drift detection. The evidence is
consumed validation evidence; it is not a fresh holdout and grants no operating
authority.
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
from qore.infrastructure.trader_lab import vt08_index_r43_sp500_long_stability_prior as r43
from qore.infrastructure.trader_lab import (
    vt08_index_r45_frozen_recent_2y_reproduction as r45,
)
from qore.infrastructure.trader_lab import (
    vt08_index_r47_transport_safe_structural_demotion as r47,
)
from qore.infrastructure.trader_lab import vt08_index_r48_candidate_freeze as freeze
from qore.infrastructure.trader_lab import vt08_index_v6_ttrades_source_faithful as v6
from qore.infrastructure.traders.contracts import DemoTradingSetupSide
from qore.infrastructure.traders.vt08_index_c2_positional_r1 import Vt08IndexC2R1Bar

SCHEMA = "qore.trader_lab.vt08_index_r50_independent_reproduction.v1"
IDENTITY = "VT08_INDEX_R50_R47_INDEPENDENT_REPRODUCTION_001"
MIN_EFFECTIVE_WEIGHT = Decimal("0.005")
PRIMARY_STRESS = Decimal("0.05")
SECONDARY_STRESS = Decimal("0.10")


def _independent_latest_completed_h4(
    h4: dict[datetime, Vt08IndexC2R1Bar],
    *,
    decision: datetime,
) -> Vt08IndexC2R1Bar | None:
    eligible = tuple(
        bar
        for opened, bar in sorted(h4.items())
        if opened.astimezone(UTC) < decision.astimezone(UTC)
        and bar.closed_at.astimezone(UTC) <= decision.astimezone(UTC)
    )
    return eligible[-1] if eligible else None


def _independent_cross_index_state(
    *,
    h4_by_symbol: dict[str, dict[datetime, Vt08IndexC2R1Bar]],
    decision: datetime,
    side: DemoTradingSetupSide,
) -> str:
    expected = 1 if side is DemoTradingSetupSide.LONG else -1
    signs: list[int] = []
    for symbol in contract.MARKETS:
        bar = _independent_latest_completed_h4(
            h4_by_symbol[symbol],
            decision=decision,
        )
        if bar is None:
            return "insufficient"
        signs.append((bar.close > bar.open) - (bar.close < bar.open))
    if signs and all(value == expected for value in signs):
        return "unanimous_with_side"
    if signs and all(value == -expected for value in signs):
        return "unanimous_against_side"
    return "mixed"


def _independent_labels(
    item: r15.AssignedTrade,
    *,
    h4_by_symbol: dict[str, dict[datetime, Vt08IndexC2R1Bar]],
) -> tuple[str, ...]:
    opportunity = item.opportunity
    signal = opportunity.signal
    latency = r17._bucket_h4_entry_latency(opportunity)
    tier = r25._quality_tier(opportunity)
    labels: list[str] = []

    if (
        item.symbol == "SP500"
        and signal.side is DemoTradingSetupSide.LONG
        and latency == "61-120m"
    ):
        labels.append("SP500_LONG_H4_61_120")

    if (
        signal.side is DemoTradingSetupSide.LONG
        and tier == "B_FVG_CISD_LATENCY_4_7"
        and latency == "61-120m"
    ):
        labels.append("B_LONG_H4_61_120")

    if (
        signal.side is DemoTradingSetupSide.SHORT
        and _independent_cross_index_state(
            h4_by_symbol=h4_by_symbol,
            decision=signal.signal_at,
            side=signal.side,
        )
        == "unanimous_against_side"
    ):
        labels.append("SHORT_CROSS_INDEX_UNANIMOUS_AGAINST")

    return tuple(labels)


def _independent_apply(
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
    output: list[r15.AssignedTrade] = []
    hits: dict[str, int] = {
        "SP500_LONG_H4_61_120": 0,
        "B_LONG_H4_61_120": 0,
        "SHORT_CROSS_INDEX_UNANIMOUS_AGAINST": 0,
    }
    reduced = 0

    for item in baseline:
        labels = _independent_labels(item, h4_by_symbol=h4_by_symbol)
        for label in labels:
            hits[label] += 1
        weight = min(item.weight, MIN_EFFECTIVE_WEIGHT) if labels else item.weight
        if weight > item.weight:
            raise ValueError("independent validator increased R47 risk")
        reduced += int(weight < item.weight)
        output.append(
            r15.AssignedTrade(
                trade_id=item.trade_id,
                opportunity=item.opportunity,
                outcome=item.outcome,
                context=item.context,
                weight=weight,
            )
        )

    if len(output) != len(baseline):
        raise ValueError("independent validator changed source-complete count")
    if any(item.weight < MIN_EFFECTIVE_WEIGHT for item in output):
        raise ValueError("independent validator created pseudo-skip risk")

    return tuple(output), {
        "assigned_trade_count": len(output),
        "risk_reduced_count": reduced,
        "suppressed_trade_count": 0,
        "risk_increase_count": 0,
        "rule_hits": hits,
    }


def _ledger_rows(
    assigned: Sequence[r15.AssignedTrade],
) -> list[dict[str, Any]]:
    return [
        {
            "trade_id": item.trade_id,
            "symbol": item.symbol,
            "signal_at": item.signal_at.isoformat(),
            "exited_at": item.exited_at.isoformat(),
            "side": item.opportunity.signal.side.value,
            "poi": str(item.opportunity.source_poi_kind),
            "rearm_index": int(item.opportunity.rearm_index),
            "weight": str(item.weight),
            "outcome_r": str(item.outcome.r_multiple),
        }
        for item in assigned
    ]


def _ledger_fingerprint(
    assigned: Sequence[r15.AssignedTrade],
) -> str:
    return sha256(
        json.dumps(
            _ledger_rows(assigned),
            sort_keys=True,
            separators=(",", ":"),
        ).encode()
    ).hexdigest()


def _canonical_match(
    independent: Sequence[r15.AssignedTrade],
    canonical: Sequence[r15.AssignedTrade],
) -> dict[str, Any]:
    if len(independent) != len(canonical):
        return {
            "pass": False,
            "mismatch_count": abs(len(independent) - len(canonical)),
            "first_mismatch": "length",
        }
    mismatches: list[dict[str, Any]] = []
    for left, right in zip(independent, canonical, strict=True):
        if (
            left.trade_id != right.trade_id
            or left.symbol != right.symbol
            or left.signal_at != right.signal_at
            or left.exited_at != right.exited_at
            or left.weight != right.weight
            or left.outcome.r_multiple != right.outcome.r_multiple
        ):
            mismatches.append(
                {
                    "trade_id_independent": left.trade_id,
                    "trade_id_canonical": right.trade_id,
                    "symbol_independent": left.symbol,
                    "symbol_canonical": right.symbol,
                    "weight_independent": str(left.weight),
                    "weight_canonical": str(right.weight),
                }
            )
    return {
        "pass": not mismatches,
        "mismatch_count": len(mismatches),
        "first_mismatch": mismatches[0] if mismatches else None,
    }


def _window(
    *,
    stream: Sequence[Any],
    bars_by_symbol: dict[str, Sequence[Vt08IndexC2R1Bar]],
) -> dict[str, Any]:
    _base_row, baseline = r34._row(stream, overlay=r43.BASE_POI_OVERLAY)
    independent, diagnostics = _independent_apply(
        baseline,
        bars_by_symbol=bars_by_symbol,
    )
    canonical, canonical_diagnostics = r47._apply_transport_rules(
        baseline,
        bars_by_symbol=bars_by_symbol,
    )
    match = _canonical_match(independent, canonical)
    return {
        "sample": len(independent),
        "primary": fx._metrics(
            r15._realized_values(independent, stress=PRIMARY_STRESS)
        ),
        "secondary": fx._metrics(
            r15._realized_values(independent, stress=SECONDARY_STRESS)
        ),
        "ledger_fingerprint": _ledger_fingerprint(independent),
        "canonical_ledger_fingerprint": _ledger_fingerprint(canonical),
        "canonical_match": match,
        "independent_diagnostics": diagnostics,
        "canonical_diagnostics": canonical_diagnostics,
    }


def build_report(
    *,
    nas100_root: Path,
    sp500_root: Path,
    us30_root: Path,
) -> dict[str, Any]:
    if not freeze.dependency_contract_matches():
        raise ValueError("R50 R48 freeze dependency drift")
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

    five = _window(
        stream=five_stream,
        bars_by_symbol={key: tuple(value) for key, value in five_bars.items()},
    )
    two = _window(
        stream=two_stream,
        bars_by_symbol={key: tuple(value) for key, value in two_bars.items()},
    )

    exact_economics = (
        five["sample"] == freeze.FIVE_YEAR["sample"]
        and two["sample"] == freeze.RECENT_TWO_YEAR["sample"]
        and str(five["primary"]["profit_factor"]) == freeze.FIVE_YEAR["primary_pf"]
        and str(five["secondary"]["profit_factor"]) == freeze.FIVE_YEAR["secondary_pf"]
        and str(two["primary"]["profit_factor"]) == freeze.RECENT_TWO_YEAR["primary_pf"]
        and str(two["secondary"]["profit_factor"]) == freeze.RECENT_TWO_YEAR["secondary_pf"]
    )
    independent_match = (
        bool(five["canonical_match"]["pass"])
        and bool(two["canonical_match"]["pass"])
        and five["ledger_fingerprint"] == five["canonical_ledger_fingerprint"]
        and two["ledger_fingerprint"] == two["canonical_ledger_fingerprint"]
    )
    pass_gate = exact_economics and independent_match

    return {
        "schema": SCHEMA,
        "identity": IDENTITY,
        "candidate": {
            "candidate_id": freeze.CANDIDATE_ID,
            "candidate_rule_fingerprint": freeze.CANDIDATE_RULE_FINGERPRINT,
            "freeze_id": freeze.FREEZE_ID,
            "rules_changed": False,
            "retuning_performed": False,
        },
        "five_year": five,
        "recent_two_year": two,
        "exact_frozen_economics": exact_economics,
        "independent_trade_ledger_match": independent_match,
        "independent_validation_pass": pass_gate,
        "decision": (
            "PASS_INDEPENDENT_REPRODUCTION"
            if pass_gate
            else "FAIL_INDEPENDENT_REPRODUCTION"
        ),
        "provenance": {
            "five_year": five_provenance,
            "recent_two_year": two_provenance,
        },
        "governance": {
            "independent_rule_application_implementation": True,
            "canonical_rule_application_used_for_comparison_only": True,
            "candidate_frozen": True,
            "retuning_performed": False,
            "fresh_holdout_claim": False,
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
                "five_year": report["five_year"],
                "recent_two_year": report["recent_two_year"],
                "exact_frozen_economics": report["exact_frozen_economics"],
                "independent_trade_ledger_match": report[
                    "independent_trade_ledger_match"
                ],
                "independent_validation_pass": report[
                    "independent_validation_pass"
                ],
                "decision": report["decision"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
