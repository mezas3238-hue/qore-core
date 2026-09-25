"""VT08 Index R75 — strict cross-index ambiguous-bias consensus falsification.

R74 falsified three local source-day fallback resolvers. R75 tests one new,
pre-registered causal mechanism only: when the target market's frozen daily
bias is unresolved in the two dominant R73 ambiguity families, consult the
other two index markets using the *existing frozen V7 daily-bias resolver* at
the same decision timestamp.

A target side is resolved only when both peers independently resolve and agree.
If either peer is unavailable/unresolved, or the peers disagree, the target
abstains. No peer fallback is allowed.

The target then uses the exact current source-complete opportunity generator:
same anchors, FVG/relevant-swing/CISD POIs, M15 CISD, Protected Swing,
structural rearm and 2.5R target. This laboratory measures the added structural
surface and its raw stressed economics on consumed evidence only.

R75 does not promote a resolver or create a candidate. It explicitly records
that cross-index dependency is introduced for research and must be falsified
before any future identity could use it.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from collections.abc import Sequence
from datetime import UTC
from decimal import Decimal
from pathlib import Path
from typing import Any

from qore.infrastructure.trader_lab import (
    vt08_index_cibo_2y_density_round4 as r4,
)
from qore.infrastructure.trader_lab import (
    vt08_index_concurrent_market_contract as contract,
)
from qore.infrastructure.trader_lab import (
    vt08_index_r6_five_year_validation as r6,
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
    vt08_index_r73_unresolved_daily_bias_families as r73,
)
from qore.infrastructure.trader_lab import (
    vt08_index_r74_ambiguous_bias_resolvers as r74,
)
from qore.infrastructure.trader_lab import (
    vt08_index_v6_ttrades_source_faithful as v6,
)
from qore.infrastructure.trader_lab import (
    vt08_index_v7_ttrades_source_corrected as v7,
)
from qore.infrastructure.traders.contracts import DemoTradingSetupSide
from qore.infrastructure.traders.vt08_index_c2_positional_r1 import (
    Vt08IndexC2R1Bar,
    resolve_daily_bias,
)

SCHEMA = "qore.trader_lab.vt08_index_r75_cross_index_bias_consensus.v1"
IDENTITY = "VT08_INDEX_R75_STRICT_CROSS_INDEX_AMBIGUOUS_BIAS_CONSENSUS_001"

SOURCE_R74_RUN_ID = 35512797040
SOURCE_R74_ARTIFACT_ID = 10605239547
SOURCE_R74_ARTIFACT_DIGEST = (
    "sha256:71e5508d180a975ad9c10e2432b1c1f69e4ae9246d3a0c94e094b76153b8e984"
)

TARGET_FAMILIES = r74.TARGET_FAMILIES
PRIMARY_STRESS = r74.PRIMARY_STRESS
SECONDARY_STRESS = r74.SECONDARY_STRESS


def _strict_peer_consensus(
    first: DemoTradingSetupSide | None,
    second: DemoTradingSetupSide | None,
) -> tuple[DemoTradingSetupSide | None, str]:
    if first is None or second is None:
        return None, "PEER_UNRESOLVED_OR_UNAVAILABLE"
    if first is not second:
        return None, "PEER_DISAGREEMENT"
    return first, "PEER_UNANIMOUS"


def _surface_for_symbol(
    *,
    symbol: str,
    bars_by_symbol: dict[str, Sequence[Vt08IndexC2R1Bar]],
    start_date: Any,
    end_date: Any,
) -> tuple[tuple[r4.ExpandedOpportunity, ...], dict[str, Any]]:
    indexed_by_symbol = {
        market: {
            bar.opened_at.astimezone(UTC): bar
            for bar in market_bars
        }
        for market, market_bars in bars_by_symbol.items()
    }
    indexed = indexed_by_symbol[symbol]
    h4 = v6._build_h4(indexed)
    h4_keys = tuple(sorted(h4))
    peers = tuple(market for market in contract.MARKETS if market != symbol)
    if len(peers) != 2:
        raise ValueError("R75 requires exactly two index peers")

    opportunities: list[r4.ExpandedOpportunity] = []
    reasons: Counter[str] = Counter()
    families: Counter[str] = Counter()
    sides: Counter[str] = Counter()
    by_anchor: dict[str, Counter[str]] = {}

    for opened in h4_keys:
        local = opened.astimezone(v7._NY)
        local_date = local.date()
        if not (start_date <= local_date < end_date):
            continue
        if local.hour not in r4.V7_ANCHORS:
            continue

        target_source_days = v7._latest_complete_source_days(
            indexed,
            before_local=local,
        )
        if target_source_days is None:
            continue
        previous, current = target_source_days
        if resolve_daily_bias(
            previous_day=previous,
            current_day=current,
        ) is not None:
            continue

        family = r73._family(previous, current)
        if family not in TARGET_FAMILIES:
            continue
        families[family] += 1

        peer_biases = tuple(
            v7._daily_bias(
                indexed_by_symbol[peer],
                before=opened,
            )
            for peer in peers
        )
        side, reason = _strict_peer_consensus(
            peer_biases[0],
            peer_biases[1],
        )
        reasons[reason] += 1
        anchor = str(local.hour)
        by_anchor.setdefault(anchor, Counter())[reason] += 1
        if side is None:
            continue
        sides[side.value] += 1

        opportunities.extend(
            r6._opportunities_for_h4_fast(
                symbol=symbol,
                indexed=indexed,
                h4=h4,
                h4_keys=h4_keys,
                h4_opened_at=opened,
                side=side,
            )
        )

    opportunities.sort(
        key=lambda item: (
            item.signal.signal_at,
            item.signal.symbol,
            item.signal.entry,
            item.signal.stop,
            item.rearm_index,
        )
    )
    identities = [item.identity() for item in opportunities]
    if len(set(identities)) != len(identities):
        raise ValueError(f"R75 duplicate consensus signal for {symbol}")

    return tuple(opportunities), {
        "peer_markets": list(peers),
        "target_family_slots": sum(families.values()),
        "families": dict(sorted(families.items())),
        "consensus_reasons": dict(sorted(reasons.items())),
        "resolved_side_slots": dict(sorted(sides.items())),
        "by_anchor": {
            anchor: dict(sorted(counter.items()))
            for anchor, counter in sorted(by_anchor.items())
        },
        "added_signal_count": len(opportunities),
    }


def _window(
    *,
    roots: dict[str, Path],
    window_id: str,
) -> dict[str, Any]:
    canonical, bars_by_symbol, provenance = r74._load_window(
        roots=roots,
        window_id=window_id,
    )
    start_date, end_date, canonical_sample = r74._window_contract(window_id)
    canonical_ids = {item[0].identity() for item in canonical}
    if len(canonical_ids) != canonical_sample:
        raise ValueError(f"R75 {window_id} canonical identity drift")

    added: list[tuple[r4.ExpandedOpportunity, Any]] = []
    diagnostics: dict[str, Any] = {}
    for symbol in contract.MARKETS:
        surface, diag = _surface_for_symbol(
            symbol=symbol,
            bars_by_symbol=bars_by_symbol,
            start_date=start_date,
            end_date=end_date,
        )
        diagnostics[symbol] = diag
        added.extend(
            r74._managed(
                surface,
                bars=bars_by_symbol[symbol],
            )
        )

    added.sort(
        key=lambda item: (
            item[0].signal.signal_at,
            item[0].signal.symbol,
            item[0].signal.entry,
            item[0].signal.stop,
        )
    )
    added_ids = [item[0].identity() for item in added]
    if len(set(added_ids)) != len(added_ids):
        raise ValueError(f"R75 {window_id} cross-market identity collision")
    if canonical_ids.intersection(added_ids):
        raise ValueError(f"R75 {window_id} added/canonical identity overlap")

    primary = r74._metrics(added, stress=PRIMARY_STRESS)
    secondary = r74._metrics(added, stress=SECONDARY_STRESS)
    primary_blocks = r74._period_blocks(
        added,
        start_date=start_date,
        end_date=end_date,
        stress=PRIMARY_STRESS,
    )
    secondary_blocks = r74._period_blocks(
        added,
        start_date=start_date,
        end_date=end_date,
        stress=SECONDARY_STRESS,
    )

    combined_sample = canonical_sample + len(added)
    low_5y, high_5y = contract.FIVE_YEAR_TRADE_RANGE
    if window_id == "5Y":
        density_gate = low_5y <= combined_sample <= high_5y
    elif window_id == "2Y":
        density_gate = combined_sample >= contract.TWO_YEAR_MIN_TRADES
    else:
        density_gate = combined_sample >= r66.MIN_TRADES

    return {
        "window_id": window_id,
        "canonical_sample": canonical_sample,
        "added_consensus_signals": len(added),
        "hypothetical_combined_sample": combined_sample,
        "density_gate": density_gate,
        "added_market_counts": r74._market_counts(added),
        "primary": primary,
        "secondary": secondary,
        "primary_blocks": primary_blocks,
        "secondary_blocks": secondary_blocks,
        "all_primary_blocks_positive": bool(primary_blocks) and all(
            Decimal(str(row["total_r"])) > 0
            for row in primary_blocks.values()
        ),
        "all_secondary_blocks_positive": bool(secondary_blocks) and all(
            Decimal(str(row["total_r"])) > 0
            for row in secondary_blocks.values()
        ),
        "diagnostics": diagnostics,
        "provenance": provenance,
    }


def build_report(
    *,
    nas100_root: Path,
    sp500_root: Path,
    us30_root: Path,
) -> dict[str, Any]:
    if not freeze.dependency_contract_matches():
        raise ValueError("R75 frozen R58/R59 dependency drift")
    if r67.SOURCE_R66_DECISION != (
        "FAIL_R66_FRESH_HOLDOUT_REJECT_FROZEN_IDENTITY"
    ):
        raise ValueError("R75 source failure decision drift")
    if r74.IDENTITY != (
        "VT08_INDEX_R74_AMBIGUOUS_DAILY_BIAS_RESOLVER_FALSIFICATION_001"
    ):
        raise ValueError("R75 R74 identity drift")

    roots = {
        "NAS100": nas100_root,
        "SP500": sp500_root,
        "US30": us30_root,
    }
    five = _window(roots=roots, window_id="5Y")
    two = _window(roots=roots, window_id="2Y")
    failed = _window(roots=roots, window_id="R66")

    structural_transport = all(
        Decimal(str(window["secondary"]["total_r"])) > 0
        and Decimal(str(window["secondary"]["profit_factor"] or "0"))
        > Decimal("1")
        and bool(window["all_secondary_blocks_positive"])
        for window in (five, two, failed)
    )
    density_transport = all(
        bool(window["density_gate"])
        for window in (five, two, failed)
    )

    return {
        "schema": SCHEMA,
        "identity": IDENTITY,
        "source_r74": {
            "identity": r74.IDENTITY,
            "run_id": SOURCE_R74_RUN_ID,
            "artifact_id": SOURCE_R74_ARTIFACT_ID,
            "artifact_digest": SOURCE_R74_ARTIFACT_DIGEST,
            "local_resolvers_falsified": list(r74.RESOLVERS),
        },
        "resolver_contract": {
            "target_families": list(TARGET_FAMILIES),
            "target_must_be_frozen_v7_unresolved": True,
            "peer_count": 2,
            "peer_resolver": "EXACT_FROZEN_V7_DAILY_BIAS_ONLY",
            "both_peers_must_resolve": True,
            "both_peers_must_agree": True,
            "peer_fallback_allowed": False,
            "features_available_before_entry": True,
            "outcome_used_to_choose_direction": False,
        },
        "five_year": five,
        "recent_two_year": two,
        "r66_failed_holdout": failed,
        "transport": {
            "secondary_positive_pf_gt_1_all_blocks_all_windows": (
                structural_transport
            ),
            "density_contract_all_windows": density_transport,
            "research_mechanism_survives_both": (
                structural_transport and density_transport
            ),
        },
        "decision": "R75_STRICT_PEER_CONSENSUS_FALSIFICATION_COMPLETE_NO_CANDIDATE",
        "governance": {
            "research_only": True,
            "consumed_evidence_only": True,
            "fresh_holdout_claim": False,
            "single_preregistered_resolver": True,
            "cross_index_dependency_introduced_for_research": True,
            "cross_index_dependency_promoted": False,
            "future_information_used": False,
            "outcome_used_to_choose_direction": False,
            "anchors_changed": False,
            "poi_families_changed": False,
            "cisd_changed": False,
            "protected_swing_changed": False,
            "target_changed": False,
            "risk_allocator_applied_to_added_signals": False,
            "canonical_signals_suppressed": False,
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
                    key: report["five_year"][key]
                    for key in (
                        "added_consensus_signals",
                        "hypothetical_combined_sample",
                        "density_gate",
                        "secondary",
                        "all_secondary_blocks_positive",
                        "added_market_counts",
                    )
                },
                "recent_two_year": {
                    key: report["recent_two_year"][key]
                    for key in (
                        "added_consensus_signals",
                        "hypothetical_combined_sample",
                        "density_gate",
                        "secondary",
                        "all_secondary_blocks_positive",
                        "added_market_counts",
                    )
                },
                "r66": {
                    key: report["r66_failed_holdout"][key]
                    for key in (
                        "added_consensus_signals",
                        "hypothetical_combined_sample",
                        "density_gate",
                        "secondary",
                        "all_secondary_blocks_positive",
                        "added_market_counts",
                    )
                },
                "transport": report["transport"],
                "decision": report["decision"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
