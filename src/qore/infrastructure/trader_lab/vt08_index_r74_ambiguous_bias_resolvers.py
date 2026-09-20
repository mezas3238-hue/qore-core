"""VT08 Index R74 — ambiguous daily-bias resolver falsification.

R73 showed that unresolved daily bias is dominated by two stable families:
INSIDE_NO_EXTREME_SWEEP and DOUBLE_SWEEP_CLOSE_INSIDE. R74 evaluates three
pre-registered, pre-entry-only directional resolvers on those unresolved source
days without selecting a winner by outcome:

1. BODY_DIRECTION: current completed source-day body.
2. PREVIOUS_MIDPOINT: current close location vs previous source-day midpoint.
3. BODY_MID_CONSENSUS: only act when 1 and 2 agree.

All resolvers use only the same two completed source-day OHLC bars that already
exist before the executable H4 anchor. The exact current source-complete
opportunity generator, POI families, CISD, Protected Swing, rearm, 2.5R target
and stop-first execution are reused.

This is consumed-evidence falsification only. No resolver is promoted here.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from collections.abc import Callable, Sequence
from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from qore.infrastructure.trader_lab import (
    vt08_index_cibo_2y_density_round4 as r4,
)
from qore.infrastructure.trader_lab import (
    vt08_index_cibo_2y_management_round5 as r5,
)
from qore.infrastructure.trader_lab import (
    vt08_index_concurrent_market_contract as contract,
)
from qore.infrastructure.trader_lab import (
    vt08_index_r6_5y_failure_forensics as fx,
)
from qore.infrastructure.trader_lab import (
    vt08_index_r6_five_year_validation as r6,
)
from qore.infrastructure.trader_lab import (
    vt08_index_r8_priority_poi_rearm_reset as r8,
)
from qore.infrastructure.trader_lab import (
    vt08_index_r31_source_complete_structural_concurrency as r31,
)
from qore.infrastructure.trader_lab import (
    vt08_index_r45_frozen_recent_2y_reproduction as r45,
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
    vt08_index_r70_source_complete_funnel_transport as r70,
)
from qore.infrastructure.trader_lab import (
    vt08_index_r73_unresolved_daily_bias_families as r73,
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

SCHEMA = "qore.trader_lab.vt08_index_r74_ambiguous_bias_resolvers.v1"
IDENTITY = "VT08_INDEX_R74_AMBIGUOUS_DAILY_BIAS_RESOLVER_FALSIFICATION_001"
PRIMARY_STRESS = Decimal("0.05")
SECONDARY_STRESS = Decimal("0.10")
TARGET_R = r31.TARGET_R
_NY = ZoneInfo("America/New_York")

TARGET_FAMILIES = (
    "INSIDE_NO_EXTREME_SWEEP",
    "DOUBLE_SWEEP_CLOSE_INSIDE",
)
RESOLVERS = (
    "BODY_DIRECTION",
    "PREVIOUS_MIDPOINT",
    "BODY_MID_CONSENSUS",
)


def _body_direction(
    previous: Vt08IndexC2R1Bar,
    current: Vt08IndexC2R1Bar,
) -> DemoTradingSetupSide | None:
    del previous
    if current.close > current.open:
        return DemoTradingSetupSide.LONG
    if current.close < current.open:
        return DemoTradingSetupSide.SHORT
    return None


def _previous_midpoint(
    previous: Vt08IndexC2R1Bar,
    current: Vt08IndexC2R1Bar,
) -> DemoTradingSetupSide | None:
    midpoint = (previous.high + previous.low) / Decimal("2")
    if current.close > midpoint:
        return DemoTradingSetupSide.LONG
    if current.close < midpoint:
        return DemoTradingSetupSide.SHORT
    return None


def _body_mid_consensus(
    previous: Vt08IndexC2R1Bar,
    current: Vt08IndexC2R1Bar,
) -> DemoTradingSetupSide | None:
    body = _body_direction(previous, current)
    midpoint = _previous_midpoint(previous, current)
    return body if body is not None and body is midpoint else None


def _resolver(
    name: str,
) -> Callable[
    [Vt08IndexC2R1Bar, Vt08IndexC2R1Bar],
    DemoTradingSetupSide | None,
]:
    mapping = {
        "BODY_DIRECTION": _body_direction,
        "PREVIOUS_MIDPOINT": _previous_midpoint,
        "BODY_MID_CONSENSUS": _body_mid_consensus,
    }
    try:
        return mapping[name]
    except KeyError as exc:
        raise ValueError(f"unsupported R74 resolver: {name}") from exc


def _window_contract(window_id: str) -> tuple[date, date, int]:
    return r70._window_contract(window_id)


def _load_window(
    *,
    roots: dict[str, Path],
    window_id: str,
) -> tuple[
    tuple[tuple[Any, r5.ManagedTrade], ...],
    dict[str, Sequence[Vt08IndexC2R1Bar]],
    dict[str, Any],
]:
    if window_id == "5Y":
        stream, bars, _opened, provenance = (
            r31._build_source_complete_stream(roots=roots)
        )
    elif window_id == "2Y":
        stream, bars, _opened, provenance = (
            r45._build_source_complete_stream_2y(roots=roots)
        )
    elif window_id == "R66":
        stream, bars, _opened, provenance = r66._build_stream(roots=roots)
    else:
        raise ValueError(f"unsupported R74 window: {window_id}")
    if len(stream) != _window_contract(window_id)[2]:
        raise ValueError(f"R74 {window_id} canonical sample drift")
    return stream, bars, provenance


def _managed(
    opportunities: Sequence[r4.ExpandedOpportunity],
    *,
    bars: Sequence[Vt08IndexC2R1Bar],
) -> tuple[tuple[r4.ExpandedOpportunity, r5.ManagedTrade], ...]:
    opened = tuple(bar.opened_at.astimezone(UTC) for bar in bars)
    policy = r8._target_policy(TARGET_R)
    return tuple(
        (
            opportunity,
            r5._manage_trade(
                opportunity.signal,
                bars=bars,
                opened=opened,
                policy=policy,
            ),
        )
        for opportunity in opportunities
    )


def _ambiguous_surface(
    *,
    symbol: str,
    bars: Sequence[Vt08IndexC2R1Bar],
    start_date: date,
    end_date: date,
    resolver_name: str,
) -> tuple[tuple[r4.ExpandedOpportunity, ...], dict[str, Any]]:
    indexed = {bar.opened_at.astimezone(UTC): bar for bar in bars}
    h4 = v6._build_h4(indexed)
    h4_keys = tuple(sorted(h4))
    resolve = _resolver(resolver_name)

    opportunities: list[r4.ExpandedOpportunity] = []
    family_slots: Counter[str] = Counter()
    resolved_slots: Counter[str] = Counter()
    abstained_slots: Counter[str] = Counter()
    side_slots: Counter[str] = Counter()
    resolved_dates: set[date] = set()

    for opened in h4_keys:
        local = opened.astimezone(_NY)
        local_date = local.date()
        if not (start_date <= local_date < end_date):
            continue
        if local.hour not in r4.V7_ANCHORS:
            continue

        source_days = v7._latest_complete_source_days(
            indexed,
            before_local=local,
        )
        if source_days is None:
            continue
        previous, current = source_days
        if resolve_daily_bias(
            previous_day=previous,
            current_day=current,
        ) is not None:
            continue

        family = r73._family(previous, current)
        if family not in TARGET_FAMILIES:
            continue
        family_slots[family] += 1

        side = resolve(previous, current)
        if side is None:
            abstained_slots[family] += 1
            continue
        resolved_slots[family] += 1
        side_slots[side.value] += 1
        resolved_dates.add(local_date)

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
        raise ValueError(
            f"R74 duplicate ambiguous resolver identity for {symbol}"
        )

    return tuple(opportunities), {
        "family_slots": dict(sorted(family_slots.items())),
        "resolved_slots": dict(sorted(resolved_slots.items())),
        "abstained_slots": dict(sorted(abstained_slots.items())),
        "side_slots": dict(sorted(side_slots.items())),
        "resolved_ny_dates": len(resolved_dates),
        "signal_count": len(opportunities),
    }


def _metrics(
    stream: Sequence[tuple[r4.ExpandedOpportunity, r5.ManagedTrade]],
    *,
    stress: Decimal,
) -> dict[str, Any]:
    ordered = sorted(
        stream,
        key=lambda item: (
            item[1].exited_at.astimezone(UTC),
            item[0].signal.symbol,
            item[0].signal.signal_at,
        ),
    )
    return fx._metrics(
        tuple(item[1].r_multiple - stress for item in ordered)
    )


def _period_blocks(
    stream: Sequence[tuple[r4.ExpandedOpportunity, r5.ManagedTrade]],
    *,
    start_date: date,
    end_date: date,
    stress: Decimal,
) -> dict[str, Any]:
    if start_date == r66.START_DATE and end_date == r66.END_DATE_EXCLUSIVE:
        boundaries = (
            r66.START_DATE,
            r66.BLOCK_BOUNDARY,
            r66.END_DATE_EXCLUSIVE,
        )
    else:
        years = 5 if (end_date - start_date).days > 1000 else 2
        boundaries = tuple(
            date(
                start_date.year + index,
                start_date.month,
                start_date.day,
            )
            for index in range(years)
        ) + (end_date,)
    result: dict[str, Any] = {}
    for index in range(len(boundaries) - 1):
        block_start = boundaries[index]
        block_end = boundaries[index + 1]
        rows = [
            item
            for item in stream
            if block_start
            <= item[1].exited_at.astimezone(_NY).date()
            < block_end
        ]
        result[f"P{index + 1}"] = {
            "start_date": block_start.isoformat(),
            "end_date_exclusive": block_end.isoformat(),
            **_metrics(rows, stress=stress),
        }
    return result


def _market_counts(
    stream: Sequence[tuple[r4.ExpandedOpportunity, r5.ManagedTrade]],
) -> dict[str, int]:
    return dict(
        sorted(
            Counter(
                str(item[0].signal.symbol)
                for item in stream
            ).items()
        )
    )


def _window(
    *,
    roots: dict[str, Path],
    window_id: str,
    resolver_name: str,
) -> dict[str, Any]:
    canonical, bars_by_symbol, provenance = _load_window(
        roots=roots,
        window_id=window_id,
    )
    start_date, end_date, canonical_sample = _window_contract(window_id)

    added: list[tuple[r4.ExpandedOpportunity, r5.ManagedTrade]] = []
    diagnostics: dict[str, Any] = {}
    for symbol in contract.MARKETS:
        opportunities, diag = _ambiguous_surface(
            symbol=symbol,
            bars=bars_by_symbol[symbol],
            start_date=start_date,
            end_date=end_date,
            resolver_name=resolver_name,
        )
        diagnostics[symbol] = diag
        added.extend(
            _managed(opportunities, bars=bars_by_symbol[symbol])
        )

    added.sort(
        key=lambda item: (
            item[0].signal.signal_at,
            item[0].signal.symbol,
            item[0].signal.entry,
            item[0].signal.stop,
        )
    )
    identities = [item[0].identity() for item in added]
    if len(set(identities)) != len(identities):
        raise ValueError(f"R74 {window_id} cross-market identity collision")

    primary = _metrics(added, stress=PRIMARY_STRESS)
    secondary = _metrics(added, stress=SECONDARY_STRESS)
    primary_blocks = _period_blocks(
        added,
        start_date=start_date,
        end_date=end_date,
        stress=PRIMARY_STRESS,
    )
    secondary_blocks = _period_blocks(
        added,
        start_date=start_date,
        end_date=end_date,
        stress=SECONDARY_STRESS,
    )

    return {
        "window_id": window_id,
        "canonical_sample": canonical_sample,
        "added_ambiguous_signals": len(added),
        "hypothetical_combined_sample": canonical_sample + len(added),
        "market_counts": _market_counts(added),
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


def _resolver_report(
    *,
    roots: dict[str, Path],
    resolver_name: str,
) -> dict[str, Any]:
    five = _window(
        roots=roots,
        window_id="5Y",
        resolver_name=resolver_name,
    )
    two = _window(
        roots=roots,
        window_id="2Y",
        resolver_name=resolver_name,
    )
    failed = _window(
        roots=roots,
        window_id="R66",
        resolver_name=resolver_name,
    )

    transport_positive = all(
        Decimal(str(window["secondary"]["total_r"])) > 0
        and Decimal(
            str(window["secondary"]["profit_factor"] or "0")
        ) > Decimal("1")
        for window in (five, two, failed)
    )
    return {
        "resolver": resolver_name,
        "five_year": five,
        "recent_two_year": two,
        "r66_failed_holdout": failed,
        "secondary_positive_pf_gt_1_all_windows": transport_positive,
    }


def build_report(
    *,
    nas100_root: Path,
    sp500_root: Path,
    us30_root: Path,
) -> dict[str, Any]:
    if not freeze.dependency_contract_matches():
        raise ValueError("R74 frozen R58/R59 dependency drift")
    if r67.SOURCE_R66_DECISION != (
        "FAIL_R66_FRESH_HOLDOUT_REJECT_FROZEN_IDENTITY"
    ):
        raise ValueError("R74 source failure decision drift")
    if r73.R72_AMBIGUOUS_COUNTS != {
        "5Y": 2410,
        "2Y": 1050,
        "R66": 968,
    }:
        raise ValueError("R74 R73 ambiguity source drift")

    roots = {
        "NAS100": nas100_root,
        "SP500": sp500_root,
        "US30": us30_root,
    }
    reports = [
        _resolver_report(
            roots=roots,
            resolver_name=resolver_name,
        )
        for resolver_name in RESOLVERS
    ]

    return {
        "schema": SCHEMA,
        "identity": IDENTITY,
        "source_r73": {
            "identity": r73.IDENTITY,
            "target_families": list(TARGET_FAMILIES),
            "official_ambiguous_counts": r73.R72_AMBIGUOUS_COUNTS,
        },
        "resolver_contract": {
            "resolvers_preregistered": list(RESOLVERS),
            "body_direction": (
                "bullish completed source-day body -> LONG; "
                "bearish -> SHORT; doji -> abstain"
            ),
            "previous_midpoint": (
                "close above prior source-day midpoint -> LONG; "
                "below -> SHORT; equal -> abstain"
            ),
            "body_mid_consensus": (
                "resolve only when body direction and midpoint direction agree"
            ),
            "features_available_before_entry": True,
            "outcome_used_to_choose_direction": False,
            "resolver_selected_by_pnl": False,
        },
        "resolvers": reports,
        "decision": "R74_RESOLVER_FALSIFICATION_COMPLETE_NO_SELECTION",
        "governance": {
            "research_only": True,
            "consumed_evidence_only": True,
            "fresh_holdout_claim": False,
            "bounded_preregistered_resolvers": True,
            "future_information_used": False,
            "outcome_used_to_choose_direction": False,
            "resolver_selected_by_pnl": False,
            "anchors_changed": False,
            "poi_families_changed": False,
            "cisd_changed": False,
            "protected_swing_changed": False,
            "target_changed": False,
            "risk_allocator_changed": False,
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
                "resolvers": [
                    {
                        "resolver": row["resolver"],
                        "five_year": {
                            key: row["five_year"][key]
                            for key in (
                                "added_ambiguous_signals",
                                "hypothetical_combined_sample",
                                "secondary",
                                "all_secondary_blocks_positive",
                            )
                        },
                        "recent_two_year": {
                            key: row["recent_two_year"][key]
                            for key in (
                                "added_ambiguous_signals",
                                "hypothetical_combined_sample",
                                "secondary",
                                "all_secondary_blocks_positive",
                            )
                        },
                        "r66": {
                            key: row["r66_failed_holdout"][key]
                            for key in (
                                "added_ambiguous_signals",
                                "hypothetical_combined_sample",
                                "secondary",
                                "all_secondary_blocks_positive",
                            )
                        },
                        "secondary_positive_pf_gt_1_all_windows": row[
                            "secondary_positive_pf_gt_1_all_windows"
                        ],
                    }
                    for row in report["resolvers"]
                ],
                "decision": report["decision"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
