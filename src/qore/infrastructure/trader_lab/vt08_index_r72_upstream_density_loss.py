"""VT08 Index R72 — upstream density loss decomposition.

R69 showed that incomplete M5 coverage explains only part of R66's 227-trade
density shortfall. R70 localized the largest downstream conversion break to
SP500, while R71 falsified keeping an old CISD alive through a wick->body WAIT.

R72 moves upstream and decomposes two large pre-signal losses in the exact
frozen source-complete generator:
- anchor slots with no daily bias;
- bias-ready anchor slots with no source POI.

No fallback bias, synthetic source day, new POI, signal or candidate is created.
The purpose is to distinguish provider/source-day availability failures from
genuine methodology abstention before changing architecture.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from collections.abc import Sequence
from datetime import UTC, date
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
    vt08_index_v6_ttrades_source_faithful as v6,
)
from qore.infrastructure.trader_lab import (
    vt08_index_v7_ttrades_source_corrected as v7,
)
from qore.infrastructure.traders.vt08_index_c2_positional_r1 import (
    Vt08IndexC2R1Bar,
)

SCHEMA = "qore.trader_lab.vt08_index_r72_upstream_density_loss.v1"
IDENTITY = "VT08_INDEX_R72_UPSTREAM_DENSITY_LOSS_FORENSICS_001"
NORMALIZATION_DAYS = Decimal("364")


def _window_contract(window_id: str) -> tuple[date, date, int]:
    return r70._window_contract(window_id)


def _load_window(
    *,
    roots: dict[str, Path],
    window_id: str,
) -> tuple[
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
        raise ValueError(f"unsupported R72 window: {window_id}")
    expected = _window_contract(window_id)[2]
    if len(stream) != expected:
        raise ValueError(f"R72 {window_id} canonical surface drift")
    return bars, provenance


def _source_day_reason(
    indexed: dict[Any, Vt08IndexC2R1Bar],
    *,
    before: Any,
) -> str:
    source_days = v7._latest_complete_source_days(
        indexed,
        before_local=before.astimezone(v7._NY),
    )
    if source_days is None:
        return "NO_TWO_COMPLETE_SOURCE_DAYS"
    bias = v7.resolve_daily_bias(
        previous_day=source_days[0],
        current_day=source_days[1],
    )
    if bias is None:
        return "AMBIGUOUS_RESOLVED_DAILY_BIAS"
    return "BIAS_AVAILABLE"


def _poi_presence(
    indexed: dict[Any, Vt08IndexC2R1Bar],
    h4: dict[Any, Vt08IndexC2R1Bar],
    h4_keys: tuple[Any, ...],
    *,
    opened: Any,
    side: Any,
) -> tuple[str, ...]:
    prior_keys = r6._prior_h4_keys_fast(
        h4_keys,
        before=opened,
        count=3,
    )
    if len(prior_keys) < 3:
        return ("INSUFFICIENT_H4_HISTORY",)
    pois = r6._source_pois_fast(
        indexed,
        h4,
        h4_keys,
        h4_opened_at=opened,
        side=side,
    )
    if not pois:
        return ("NO_FVG_SWING_OR_CISD",)
    return tuple(sorted({poi.kind.value for poi in pois}))


def _market(
    *,
    bars: Sequence[Vt08IndexC2R1Bar],
    start_date: date,
    end_date: date,
) -> dict[str, Any]:
    indexed = {bar.opened_at.astimezone(UTC): bar for bar in bars}
    h4 = v6._build_h4(indexed)
    h4_keys = tuple(sorted(h4))
    bias_cache: dict[date, Any] = {}

    aggregate: Counter[str] = Counter()
    by_anchor: dict[str, Counter[str]] = defaultdict(Counter)
    no_bias_reason: Counter[str] = Counter()
    no_bias_reason_by_anchor: dict[str, Counter[str]] = defaultdict(Counter)
    no_poi_reason: Counter[str] = Counter()
    no_poi_reason_by_anchor: dict[str, Counter[str]] = defaultdict(Counter)
    poi_family_slots: Counter[str] = Counter()

    for opened in h4_keys:
        local = opened.astimezone(v7._NY)
        local_date = local.date()
        if not (start_date <= local_date < end_date):
            continue
        if local.hour not in r4.V7_ANCHORS:
            continue

        anchor = str(local.hour)
        aggregate["anchor_slots"] += 1
        by_anchor[anchor]["anchor_slots"] += 1

        if local_date not in bias_cache:
            bias_cache[local_date] = v7._daily_bias(indexed, before=opened)
        side = bias_cache[local_date]
        if side is None:
            aggregate["no_bias_slots"] += 1
            by_anchor[anchor]["no_bias_slots"] += 1
            reason = _source_day_reason(indexed, before=opened)
            no_bias_reason[reason] += 1
            no_bias_reason_by_anchor[anchor][reason] += 1
            continue

        aggregate["bias_ready_slots"] += 1
        by_anchor[anchor]["bias_ready_slots"] += 1
        presence = _poi_presence(
            indexed,
            h4,
            h4_keys,
            opened=opened,
            side=side,
        )
        if presence in {
            ("INSUFFICIENT_H4_HISTORY",),
            ("NO_FVG_SWING_OR_CISD",),
        }:
            aggregate["no_poi_slots"] += 1
            by_anchor[anchor]["no_poi_slots"] += 1
            reason = presence[0]
            no_poi_reason[reason] += 1
            no_poi_reason_by_anchor[anchor][reason] += 1
            continue

        aggregate["poi_ready_slots"] += 1
        by_anchor[anchor]["poi_ready_slots"] += 1
        for family in presence:
            poi_family_slots[family] += 1

    slots = aggregate["anchor_slots"]
    return {
        "aggregate": dict(sorted(aggregate.items())),
        "by_anchor": {
            key: dict(sorted(value.items()))
            for key, value in sorted(by_anchor.items())
        },
        "no_bias_reason": dict(sorted(no_bias_reason.items())),
        "no_bias_reason_by_anchor": {
            key: dict(sorted(value.items()))
            for key, value in sorted(no_bias_reason_by_anchor.items())
        },
        "no_poi_reason": dict(sorted(no_poi_reason.items())),
        "no_poi_reason_by_anchor": {
            key: dict(sorted(value.items()))
            for key, value in sorted(no_poi_reason_by_anchor.items())
        },
        "poi_family_ready_slot_count": dict(sorted(poi_family_slots.items())),
        "no_bias_fraction": (
            str(Decimal(aggregate["no_bias_slots"]) / Decimal(slots))
            if slots else "0"
        ),
        "no_poi_fraction_of_bias_ready": (
            str(
                Decimal(aggregate["no_poi_slots"])
                / Decimal(aggregate["bias_ready_slots"])
            )
            if aggregate["bias_ready_slots"] else "0"
        ),
    }


def _window(
    *,
    roots: dict[str, Path],
    window_id: str,
) -> dict[str, Any]:
    bars_by_symbol, provenance = _load_window(
        roots=roots,
        window_id=window_id,
    )
    start_date, end_date, sample = _window_contract(window_id)
    days = (end_date - start_date).days
    by_market = {
        symbol: _market(
            bars=bars_by_symbol[symbol],
            start_date=start_date,
            end_date=end_date,
        )
        for symbol in contract.MARKETS
    }

    no_bias = sum(
        int(row["aggregate"].get("no_bias_slots", 0))
        for row in by_market.values()
    )
    coverage_no_bias = sum(
        int(row["no_bias_reason"].get("NO_TWO_COMPLETE_SOURCE_DAYS", 0))
        for row in by_market.values()
    )
    ambiguous_no_bias = sum(
        int(row["no_bias_reason"].get("AMBIGUOUS_RESOLVED_DAILY_BIAS", 0))
        for row in by_market.values()
    )
    no_poi = sum(
        int(row["aggregate"].get("no_poi_slots", 0))
        for row in by_market.values()
    )
    structural_no_poi = sum(
        int(row["no_poi_reason"].get("NO_FVG_SWING_OR_CISD", 0))
        for row in by_market.values()
    )

    return {
        "window_id": window_id,
        "start_date": start_date.isoformat(),
        "end_date_exclusive": end_date.isoformat(),
        "days": days,
        "canonical_sample": sample,
        "trades_per_364d": str(
            Decimal(sample) * NORMALIZATION_DAYS / Decimal(days)
        ),
        "no_bias_slots": no_bias,
        "no_bias_due_source_day_availability": coverage_no_bias,
        "no_bias_due_ambiguous_methodology": ambiguous_no_bias,
        "no_poi_slots": no_poi,
        "no_poi_due_absent_source_structure": structural_no_poi,
        "by_market": by_market,
        "provenance": provenance,
    }


def _transport(
    five: dict[str, Any],
    two: dict[str, Any],
    failed: dict[str, Any],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for symbol in contract.MARKETS:
        for metric in (
            "no_bias_fraction",
            "no_poi_fraction_of_bias_ready",
        ):
            f = Decimal(str(five["by_market"][symbol][metric]))
            t = Decimal(str(two["by_market"][symbol][metric]))
            h = Decimal(str(failed["by_market"][symbol][metric]))
            rows.append(
                {
                    "symbol": symbol,
                    "metric": metric,
                    "five_year": str(f),
                    "recent_two_year": str(t),
                    "r66": str(h),
                    "r66_minus_5y": str(h - f),
                    "r66_minus_recent2y": str(h - t),
                }
            )
    rows.sort(
        key=lambda row: max(
            Decimal(str(row["r66_minus_5y"])),
            Decimal(str(row["r66_minus_recent2y"])),
        ),
        reverse=True,
    )
    return rows


def build_report(
    *,
    nas100_root: Path,
    sp500_root: Path,
    us30_root: Path,
) -> dict[str, Any]:
    if not freeze.dependency_contract_matches():
        raise ValueError("R72 frozen R58/R59 dependency drift")
    if r67.SOURCE_R66_DECISION != (
        "FAIL_R66_FRESH_HOLDOUT_REJECT_FROZEN_IDENTITY"
    ):
        raise ValueError("R72 source failure decision drift")

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
        "source_failure": {
            "decision": r67.SOURCE_R66_DECISION,
            "r66_density_gate": r66.MIN_TRADES,
        },
        "five_year": five,
        "recent_two_year": two,
        "r66_failed_holdout": failed,
        "transport": _transport(five, two, failed),
        "decision": "R72_UPSTREAM_DENSITY_FORENSICS_COMPLETE_NO_CANDIDATE",
        "governance": {
            "forensics_only": True,
            "consumed_evidence_only": True,
            "fresh_holdout_claim": False,
            "fallback_bias_created": False,
            "synthetic_source_day_created": False,
            "poi_definition_changed": False,
            "signals_added": False,
            "signals_suppressed": False,
            "risk_changed": False,
            "management_changed": False,
            "calendar_or_year_runtime_feature": False,
            "replacement_candidate_created": False,
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
                        "canonical_sample",
                        "no_bias_slots",
                        "no_bias_due_source_day_availability",
                        "no_bias_due_ambiguous_methodology",
                        "no_poi_slots",
                        "no_poi_due_absent_source_structure",
                    )
                },
                "recent_two_year": {
                    key: report["recent_two_year"][key]
                    for key in (
                        "canonical_sample",
                        "no_bias_slots",
                        "no_bias_due_source_day_availability",
                        "no_bias_due_ambiguous_methodology",
                        "no_poi_slots",
                        "no_poi_due_absent_source_structure",
                    )
                },
                "r66": {
                    key: report["r66_failed_holdout"][key]
                    for key in (
                        "canonical_sample",
                        "no_bias_slots",
                        "no_bias_due_source_day_availability",
                        "no_bias_due_ambiguous_methodology",
                        "no_poi_slots",
                        "no_poi_due_absent_source_structure",
                    )
                },
                "r66_by_market": report["r66_failed_holdout"]["by_market"],
                "transport": report["transport"],
                "decision": report["decision"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
