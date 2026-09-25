"""VT08 Index R73 — unresolved daily-bias family forensics.

R72 proved that most no-bias anchor slots are genuine methodology abstentions,
not missing data: 968/1218 R66 no-bias slots had two complete source days but
resolve_daily_bias() returned None.

R73 classifies those unresolved cases using only the exact two completed
source-day bars already available to the frozen V7 resolver. It does not choose
a side, create a fallback, replay hypothetical PnL, or add signals.

The goal is to determine whether the ambiguity is one stable structural family
or several materially different causal states before any new identity is
considered.
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
    resolve_daily_bias,
)

SCHEMA = "qore.trader_lab.vt08_index_r73_unresolved_daily_bias_families.v1"
IDENTITY = "VT08_INDEX_R73_UNRESOLVED_DAILY_BIAS_FAMILIES_001"
NORMALIZATION_DAYS = Decimal("364")
SOURCE_R72_RUN_ID = 35506163421
SOURCE_R72_ARTIFACT_ID = 10604260215
SOURCE_R72_ARTIFACT_DIGEST = (
    "sha256:58713e79d2c2120b0519dc27bf93220f1bcd3e7365747fead22dacb6021eee41"
)
R72_AMBIGUOUS_COUNTS = {"5Y": 2410, "2Y": 1050, "R66": 968}


def _window_contract(window_id: str) -> tuple[date, date, int]:
    return r70._window_contract(window_id)


def _load_window(
    *,
    roots: dict[str, Path],
    window_id: str,
) -> dict[str, Sequence[Vt08IndexC2R1Bar]]:
    if window_id == "5Y":
        stream, bars, _opened, _provenance = (
            r31._build_source_complete_stream(roots=roots)
        )
    elif window_id == "2Y":
        stream, bars, _opened, _provenance = (
            r45._build_source_complete_stream_2y(roots=roots)
        )
    elif window_id == "R66":
        stream, bars, _opened, _provenance = r66._build_stream(roots=roots)
    else:
        raise ValueError(f"unsupported R73 window: {window_id}")
    if len(stream) != _window_contract(window_id)[2]:
        raise ValueError(f"R73 {window_id} canonical sample drift")
    return bars


def _family(
    previous: Vt08IndexC2R1Bar,
    current: Vt08IndexC2R1Bar,
) -> str:
    if resolve_daily_bias(previous_day=previous, current_day=current) is not None:
        return "RESOLVED"

    swept_high = current.high > previous.high
    swept_low = current.low < previous.low
    close_at_high = current.close == previous.high
    close_at_low = current.close == previous.low

    if swept_high and swept_low:
        return "DOUBLE_SWEEP_CLOSE_INSIDE"
    if swept_high and close_at_high:
        return "HIGH_SWEEP_CLOSE_AT_PREVIOUS_HIGH"
    if swept_low and close_at_low:
        return "LOW_SWEEP_CLOSE_AT_PREVIOUS_LOW"
    if not swept_high and not swept_low:
        if close_at_high:
            return "NO_SWEEP_CLOSE_AT_PREVIOUS_HIGH"
        if close_at_low:
            return "NO_SWEEP_CLOSE_AT_PREVIOUS_LOW"
        return "INSIDE_NO_EXTREME_SWEEP"
    if swept_high:
        return "HIGH_SWEEP_UNRESOLVED_BOUNDARY"
    if swept_low:
        return "LOW_SWEEP_UNRESOLVED_BOUNDARY"
    return "OTHER_UNRESOLVED"


def _shape(
    previous: Vt08IndexC2R1Bar,
    current: Vt08IndexC2R1Bar,
) -> dict[str, str]:
    previous_range = previous.high - previous.low
    current_range = current.high - current.low
    if previous_range <= 0:
        raise ValueError("R73 previous source-day range must be positive")

    midpoint = (previous.high + previous.low) / Decimal("2")
    if current.close > midpoint:
        close_location = "ABOVE_PREVIOUS_MID"
    elif current.close < midpoint:
        close_location = "BELOW_PREVIOUS_MID"
    else:
        close_location = "AT_PREVIOUS_MID"

    if current.close > current.open:
        body_direction = "BULLISH_BODY"
    elif current.close < current.open:
        body_direction = "BEARISH_BODY"
    else:
        body_direction = "DOJI_BODY"

    return {
        "close_location": close_location,
        "body_direction": body_direction,
        "range_ratio_bucket": (
            "COMPRESSED_LT_0_75"
            if current_range / previous_range < Decimal("0.75")
            else (
                "EXPANDED_GT_1_25"
                if current_range / previous_range > Decimal("1.25")
                else "NORMAL_0_75_TO_1_25"
            )
        ),
    }


def _market(
    *,
    bars: Sequence[Vt08IndexC2R1Bar],
    start_date: date,
    end_date: date,
) -> dict[str, Any]:
    indexed = {bar.opened_at.astimezone(UTC): bar for bar in bars}
    h4 = v6._build_h4(indexed)
    h4_keys = tuple(sorted(h4))

    family_counts: Counter[str] = Counter()
    by_anchor: dict[str, Counter[str]] = defaultdict(Counter)
    close_location: Counter[str] = Counter()
    body_direction: Counter[str] = Counter()
    range_state: Counter[str] = Counter()
    ambiguous_dates: set[date] = set()

    for opened in h4_keys:
        local = opened.astimezone(v7._NY)
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
        if resolve_daily_bias(previous_day=previous, current_day=current) is not None:
            continue

        family = _family(previous, current)
        shape = _shape(previous, current)
        anchor = str(local.hour)

        family_counts[family] += 1
        by_anchor[anchor][family] += 1
        close_location[shape["close_location"]] += 1
        body_direction[shape["body_direction"]] += 1
        range_state[shape["range_ratio_bucket"]] += 1
        ambiguous_dates.add(local_date)

    total = sum(family_counts.values())
    return {
        "ambiguous_anchor_slots": total,
        "ambiguous_ny_dates": len(ambiguous_dates),
        "families": dict(sorted(family_counts.items())),
        "by_anchor": {
            key: dict(sorted(value.items()))
            for key, value in sorted(by_anchor.items())
        },
        "close_location": dict(sorted(close_location.items())),
        "body_direction": dict(sorted(body_direction.items())),
        "range_state": dict(sorted(range_state.items())),
    }


def _window(
    *,
    roots: dict[str, Path],
    window_id: str,
) -> dict[str, Any]:
    bars = _load_window(roots=roots, window_id=window_id)
    start_date, end_date, sample = _window_contract(window_id)
    by_market = {
        symbol: _market(
            bars=bars[symbol],
            start_date=start_date,
            end_date=end_date,
        )
        for symbol in contract.MARKETS
    }
    aggregate: Counter[str] = Counter()
    for row in by_market.values():
        aggregate.update(row["families"])
    total = sum(aggregate.values())
    return {
        "window_id": window_id,
        "canonical_sample": sample,
        "ambiguous_anchor_slots": total,
        "families": dict(sorted(aggregate.items())),
        "by_market": by_market,
    }


def _share(payload: dict[str, Any], family: str) -> Decimal:
    total = int(payload["ambiguous_anchor_slots"])
    if total <= 0:
        return Decimal()
    return Decimal(int(payload["families"].get(family, 0))) / Decimal(total)


def _transport(
    five: dict[str, Any],
    two: dict[str, Any],
    failed: dict[str, Any],
) -> list[dict[str, Any]]:
    families = sorted(
        set(five["families"])
        | set(two["families"])
        | set(failed["families"])
    )
    rows = []
    for family in families:
        fs = _share(five, family)
        ts = _share(two, family)
        hs = _share(failed, family)
        rows.append(
            {
                "family": family,
                "five_year_count": int(five["families"].get(family, 0)),
                "recent_two_year_count": int(two["families"].get(family, 0)),
                "r66_count": int(failed["families"].get(family, 0)),
                "five_year_share": str(fs),
                "recent_two_year_share": str(ts),
                "r66_share": str(hs),
                "r66_share_minus_5y": str(hs - fs),
                "r66_share_minus_recent2y": str(hs - ts),
            }
        )
    rows.sort(key=lambda row: int(row["r66_count"]), reverse=True)
    return rows


def build_report(
    *,
    nas100_root: Path,
    sp500_root: Path,
    us30_root: Path,
) -> dict[str, Any]:
    if not freeze.dependency_contract_matches():
        raise ValueError("R73 frozen R58/R59 dependency drift")
    if r67.SOURCE_R66_DECISION != (
        "FAIL_R66_FRESH_HOLDOUT_REJECT_FROZEN_IDENTITY"
    ):
        raise ValueError("R73 source failure decision drift")

    roots = {
        "NAS100": nas100_root,
        "SP500": sp500_root,
        "US30": us30_root,
    }
    five = _window(roots=roots, window_id="5Y")
    two = _window(roots=roots, window_id="2Y")
    failed = _window(roots=roots, window_id="R66")

    if five["ambiguous_anchor_slots"] != R72_AMBIGUOUS_COUNTS["5Y"]:
        raise ValueError("R73 5Y ambiguity count drift from official R72")
    if two["ambiguous_anchor_slots"] != R72_AMBIGUOUS_COUNTS["2Y"]:
        raise ValueError("R73 recent2Y ambiguity count drift from official R72")
    if failed["ambiguous_anchor_slots"] != R72_AMBIGUOUS_COUNTS["R66"]:
        raise ValueError("R73 R66 ambiguity count drift from official R72")

    return {
        "schema": SCHEMA,
        "identity": IDENTITY,
        "source_failure": {
            "decision": r67.SOURCE_R66_DECISION,
            "r66_density_gate": r66.MIN_TRADES,
        },
        "source_r72": {
            "run_id": SOURCE_R72_RUN_ID,
            "artifact_id": SOURCE_R72_ARTIFACT_ID,
            "artifact_digest": SOURCE_R72_ARTIFACT_DIGEST,
            "official_ambiguous_counts": R72_AMBIGUOUS_COUNTS,
        },
        "resolver_contract": {
            "continuation_above_previous_high": "LONG",
            "continuation_below_previous_low": "SHORT",
            "single_low_sweep_reclaim": "LONG",
            "single_high_sweep_reject": "SHORT",
            "unresolved_cases_only_analyzed": True,
        },
        "five_year": five,
        "recent_two_year": two,
        "r66_failed_holdout": failed,
        "transport": _transport(five, two, failed),
        "decision": "R73_AMBIGUOUS_BIAS_FAMILIES_COMPLETE_NO_RESOLVER",
        "governance": {
            "forensics_only": True,
            "consumed_evidence_only": True,
            "fresh_holdout_claim": False,
            "fallback_bias_created": False,
            "resolver_candidate_created": False,
            "hypothetical_pnl_replayed": False,
            "outcome_used_to_pick_direction": False,
            "signals_added": False,
            "signals_suppressed": False,
            "calendar_or_year_runtime_feature": False,
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
                "five_year": report["five_year"],
                "recent_two_year": report["recent_two_year"],
                "r66": report["r66_failed_holdout"],
                "transport": report["transport"],
                "decision": report["decision"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
