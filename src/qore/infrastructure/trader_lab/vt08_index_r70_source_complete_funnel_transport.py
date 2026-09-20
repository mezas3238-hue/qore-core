"""VT08 Index R70 — source-complete funnel transport forensics.

R69 proved that provider incompleteness explains only part of the R66 density
shortfall. R70 instruments the exact current source-complete opportunity
generator across the three consumed windows to identify where structural
conversion breaks.

This is diagnostics only. It does not add anchors, POIs, signals, risk or
management rules. It reproduces the same V7 daily bias, 02/06/10 NY anchors,
source-complete FVG/relevant-swing/CISD POIs, structural rearm, M15 CISD,
protected swing and first causal continuation used by the current 2,448 /
1,017 / 773 signal surfaces.

All stages are causal and observable at or before signal creation. Outcomes
are not used in the funnel.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import UTC, date
from decimal import Decimal
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

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
    vt08_index_r69_r66_density_causal_decomposition as r69,
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
)

SCHEMA = "qore.trader_lab.vt08_index_r70_source_complete_funnel_transport.v1"
IDENTITY = "VT08_INDEX_R70_SOURCE_COMPLETE_FUNNEL_TRANSPORT_FORENSICS_001"
_NY = ZoneInfo("America/New_York")
NORMALIZATION_DAYS = Decimal("364")

STAGE_KEYS = (
    "anchor_slots",
    "bias_ready_slots",
    "no_bias_slots",
    "poi_ready_slots",
    "no_poi_slots",
    "poi_instances",
    "poi_touched_instances",
    "poi_not_touched_instances",
    "touch_attempts",
    "cisd_confirmed_attempts",
    "no_cisd_attempts",
    "continuation_attempts",
    "no_continuation_or_ps_invalidated_attempts",
    "same_c2_body_pass_attempts",
    "same_c2_still_in_wick_attempts",
    "positive_risk_attempts",
    "non_positive_risk_attempts",
    "signal_attempts",
    "unique_signals",
)


@dataclass(slots=True)
class Funnel:
    counters: Counter[str] = field(default_factory=Counter)
    identities: set[tuple[object, ...]] = field(default_factory=set)

    def bump(self, key: str, value: int = 1) -> None:
        self.counters[key] += value

    def add_identity(self, identity: tuple[object, ...]) -> None:
        self.identities.add(identity)

    def payload(self) -> dict[str, Any]:
        counters = {
            key: int(self.counters.get(key, 0))
            for key in STAGE_KEYS
        }
        counters["unique_signals"] = len(self.identities)
        slots = counters["anchor_slots"]
        poi_instances = counters["poi_instances"]
        touch_attempts = counters["touch_attempts"]
        return {
            **counters,
            "signals_per_anchor_slot": (
                str(Decimal(counters["unique_signals"]) / Decimal(slots))
                if slots
                else "0"
            ),
            "signals_per_poi_instance": (
                str(
                    Decimal(counters["unique_signals"])
                    / Decimal(poi_instances)
                )
                if poi_instances
                else "0"
            ),
            "signals_per_touch_attempt": (
                str(
                    Decimal(counters["unique_signals"])
                    / Decimal(touch_attempts)
                )
                if touch_attempts
                else "0"
            ),
        }


def _merge(target: Funnel, source: Funnel) -> None:
    target.counters.update(source.counters)
    target.identities.update(source.identities)


def _window_contract(
    window_id: str,
) -> tuple[date, date, int]:
    if window_id == "5Y":
        return r6.START_DATE, r6.END_DATE_EXCLUSIVE, 2448
    if window_id == "2Y":
        return r45.START_DATE, r45.END_DATE_EXCLUSIVE, 1017
    if window_id == "R66":
        return r66.START_DATE, r66.END_DATE_EXCLUSIVE, 773
    raise ValueError(f"unsupported R70 window: {window_id}")


def _load_window(
    *,
    roots: dict[str, Path],
    window_id: str,
) -> tuple[
    dict[str, Sequence[Vt08IndexC2R1Bar]],
    dict[str, Any],
    dict[str, int],
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
        raise ValueError(f"unsupported R70 window: {window_id}")

    counts = Counter(str(item[0].signal.symbol) for item in stream)
    expected = _window_contract(window_id)[2]
    if len(stream) != expected:
        raise ValueError(
            f"R70 {window_id} canonical surface drift: {len(stream)}"
        )
    return bars, provenance, dict(sorted(counts.items()))


def _identity(
    *,
    symbol: str,
    signal_at: Any,
    side: DemoTradingSetupSide,
    entry: Decimal,
    stop: Decimal,
) -> tuple[object, ...]:
    return (
        symbol,
        signal_at.astimezone(UTC),
        side.value,
        entry,
        stop,
    )


def _instrument_market(
    *,
    symbol: str,
    bars: Sequence[Vt08IndexC2R1Bar],
    start_date: date,
    end_date_exclusive: date,
) -> dict[str, Any]:
    indexed = {bar.opened_at.astimezone(UTC): bar for bar in bars}
    h4 = v6._build_h4(indexed)
    h4_keys = tuple(sorted(h4))
    side_cache: dict[date, DemoTradingSetupSide | None] = {}

    overall = Funnel()
    by_anchor: dict[str, Funnel] = defaultdict(Funnel)
    by_poi: dict[str, Funnel] = defaultdict(Funnel)

    for opened in h4_keys:
        local = opened.astimezone(_NY)
        local_date = local.date()
        if not (start_date <= local_date < end_date_exclusive):
            continue
        if local.hour not in r4.V7_ANCHORS:
            continue

        anchor = str(local.hour)
        slot = Funnel()
        slot.bump("anchor_slots")

        if local_date not in side_cache:
            side_cache[local_date] = v7._daily_bias(indexed, before=opened)
        side = side_cache[local_date]
        if side is None:
            slot.bump("no_bias_slots")
            _merge(overall, slot)
            _merge(by_anchor[anchor], slot)
            continue
        slot.bump("bias_ready_slots")

        pois = r6._source_pois_fast(
            indexed,
            h4,
            h4_keys,
            h4_opened_at=opened,
            side=side,
        )
        if not pois:
            slot.bump("no_poi_slots")
            _merge(overall, slot)
            _merge(by_anchor[anchor], slot)
            continue
        slot.bump("poi_ready_slots")

        h4_bar = h4[opened.astimezone(UTC)]
        inside = r6._bars_between_fast(
            indexed,
            start=opened,
            end=h4_bar.closed_at,
        )
        model_kind = r6._completed_h4_model_fast(
            indexed,
            h4,
            h4_keys,
            current_h4_open=opened,
            side=side,
        )
        if model_kind is None:
            model_kind = v6.H4ModelKind.SAME_C2

        for poi in pois:
            poi_key = poi.kind.value
            poi_funnel = Funnel()
            poi_funnel.bump("poi_instances")
            touches_all = r4._touch_indices(
                inside,
                poi,
                start_index=0,
            )
            if not touches_all:
                poi_funnel.bump("poi_not_touched_instances")
                _merge(slot, poi_funnel)
                _merge(by_poi[poi_key], poi_funnel)
                continue

            poi_funnel.bump("poi_touched_instances")
            cursor = 0
            while cursor < len(inside):
                touches = r4._touch_indices(
                    inside,
                    poi,
                    start_index=cursor,
                )
                if not touches:
                    break
                touch_index = touches[0]
                poi_funnel.bump("touch_attempts")

                cisd = v6._first_cisd(
                    inside,
                    side=side,
                    start_index=touch_index,
                )
                if cisd is None:
                    poi_funnel.bump("no_cisd_attempts")
                    cursor = touch_index + 1
                    continue
                cisd_index, _cisd_level, protected_swing = cisd
                poi_funnel.bump("cisd_confirmed_attempts")

                continuation_index = v6._first_continuation(
                    inside,
                    side=side,
                    start_index=cisd_index + 1,
                    protected_swing=protected_swing,
                )
                if continuation_index is None:
                    poi_funnel.bump(
                        "no_continuation_or_ps_invalidated_attempts"
                    )
                    cursor = touch_index + 1
                    continue
                poi_funnel.bump("continuation_attempts")

                continuation = inside[continuation_index]
                entry = continuation.close
                if model_kind is v6.H4ModelKind.SAME_C2:
                    in_body = (
                        entry > h4_bar.open
                        if side is DemoTradingSetupSide.LONG
                        else entry < h4_bar.open
                    )
                    if not in_body:
                        poi_funnel.bump("same_c2_still_in_wick_attempts")
                        cursor = touch_index + 1
                        continue
                poi_funnel.bump("same_c2_body_pass_attempts")

                risk = (
                    entry - protected_swing
                    if side is DemoTradingSetupSide.LONG
                    else protected_swing - entry
                )
                if risk <= 0:
                    poi_funnel.bump("non_positive_risk_attempts")
                    cursor = touch_index + 1
                    continue
                poi_funnel.bump("positive_risk_attempts")
                poi_funnel.bump("signal_attempts")
                identity = _identity(
                    symbol=symbol,
                    signal_at=continuation.closed_at,
                    side=side,
                    entry=entry,
                    stop=protected_swing,
                )
                poi_funnel.add_identity(identity)
                cursor = continuation_index + 1

            _merge(slot, poi_funnel)
            _merge(by_poi[poi_key], poi_funnel)

        _merge(overall, slot)
        _merge(by_anchor[anchor], slot)

    return {
        "overall": overall.payload(),
        "by_anchor": {
            key: funnel.payload()
            for key, funnel in sorted(by_anchor.items())
        },
        "by_poi": {
            key: funnel.payload()
            for key, funnel in sorted(by_poi.items())
        },
    }


def _window(
    *,
    roots: dict[str, Path],
    window_id: str,
) -> dict[str, Any]:
    bars_by_symbol, provenance, canonical_counts = _load_window(
        roots=roots,
        window_id=window_id,
    )
    start_date, end_date, expected = _window_contract(window_id)
    days = (end_date - start_date).days

    market_reports: dict[str, Any] = {}
    aggregate = Funnel()
    for symbol in contract.MARKETS:
        report = _instrument_market(
            symbol=symbol,
            bars=bars_by_symbol[symbol],
            start_date=start_date,
            end_date_exclusive=end_date,
        )
        market_reports[symbol] = report

        # Reconstruct aggregate identities by re-running only the market
        # counters would lose identity sets, so canonical market counts are
        # used for aggregate unique-signal total after stage counters sum.
        market_payload = report["overall"]
        for key in STAGE_KEYS:
            if key != "unique_signals":
                aggregate.bump(key, int(market_payload[key]))

    payload = aggregate.payload()
    payload["unique_signals"] = sum(canonical_counts.values())
    payload["signals_per_anchor_slot"] = (
        str(
            Decimal(payload["unique_signals"])
            / Decimal(payload["anchor_slots"])
        )
        if payload["anchor_slots"]
        else "0"
    )
    payload["signals_per_poi_instance"] = (
        str(
            Decimal(payload["unique_signals"])
            / Decimal(payload["poi_instances"])
        )
        if payload["poi_instances"]
        else "0"
    )
    payload["signals_per_touch_attempt"] = (
        str(
            Decimal(payload["unique_signals"])
            / Decimal(payload["touch_attempts"])
        )
        if payload["touch_attempts"]
        else "0"
    )

    instrumented_counts = {
        symbol: int(market_reports[symbol]["overall"]["unique_signals"])
        for symbol in contract.MARKETS
    }
    if instrumented_counts != canonical_counts:
        raise ValueError(
            f"R70 {window_id} funnel signal reconstruction drift: "
            f"{instrumented_counts} != {canonical_counts}"
        )
    if sum(instrumented_counts.values()) != expected:
        raise ValueError(f"R70 {window_id} expected sample drift")

    return {
        "window_id": window_id,
        "start_date": start_date.isoformat(),
        "end_date_exclusive": end_date.isoformat(),
        "days": days,
        "trades_per_364d": str(
            Decimal(expected) * NORMALIZATION_DAYS / Decimal(days)
        ),
        "canonical_signal_count": expected,
        "canonical_market_counts": canonical_counts,
        "aggregate": payload,
        "by_market": market_reports,
        "provenance": provenance,
    }


def _ratio(current: Any, baseline: Any) -> str | None:
    denominator = Decimal(str(baseline))
    if denominator == 0:
        return None
    return str(Decimal(str(current)) / denominator)


def _transport(
    five: dict[str, Any],
    two: dict[str, Any],
    failed: dict[str, Any],
) -> dict[str, Any]:
    stage_rows: list[dict[str, Any]] = []
    for symbol in contract.MARKETS:
        f = five["by_market"][symbol]["overall"]
        t = two["by_market"][symbol]["overall"]
        h = failed["by_market"][symbol]["overall"]
        for key in (
            "anchor_slots",
            "bias_ready_slots",
            "poi_instances",
            "poi_touched_instances",
            "touch_attempts",
            "cisd_confirmed_attempts",
            "continuation_attempts",
            "signal_attempts",
            "unique_signals",
        ):
            stage_rows.append(
                {
                    "symbol": symbol,
                    "stage": key,
                    "five_year": f[key],
                    "recent_two_year": t[key],
                    "r66": h[key],
                    "r66_vs_5y_ratio": _ratio(h[key], f[key]),
                    "r66_vs_recent2y_ratio": _ratio(h[key], t[key]),
                }
            )

    conversion_rows: list[dict[str, Any]] = []
    for symbol in contract.MARKETS:
        f = five["by_market"][symbol]["overall"]
        t = two["by_market"][symbol]["overall"]
        h = failed["by_market"][symbol]["overall"]
        for key in (
            "signals_per_anchor_slot",
            "signals_per_poi_instance",
            "signals_per_touch_attempt",
        ):
            conversion_rows.append(
                {
                    "symbol": symbol,
                    "metric": key,
                    "five_year": f[key],
                    "recent_two_year": t[key],
                    "r66": h[key],
                    "r66_vs_5y_ratio": _ratio(h[key], f[key]),
                    "r66_vs_recent2y_ratio": _ratio(h[key], t[key]),
                }
            )

    conversion_rows.sort(
        key=lambda row: (
            Decimal(str(row["r66_vs_5y_ratio"] or "999")),
            Decimal(str(row["r66_vs_recent2y_ratio"] or "999")),
        )
    )
    return {
        "stage_transport": stage_rows,
        "conversion_transport_ranked": conversion_rows,
    }


def build_report(
    *,
    nas100_root: Path,
    sp500_root: Path,
    us30_root: Path,
) -> dict[str, Any]:
    if not freeze.dependency_contract_matches():
        raise ValueError("R70 frozen R58/R59 dependency drift")
    if r67.SOURCE_R66_DECISION != (
        "FAIL_R66_FRESH_HOLDOUT_REJECT_FROZEN_IDENTITY"
    ):
        raise ValueError("R70 R66 source failure decision drift")
    if r69.R66_DENSITY_GATE != 1000:
        raise ValueError("R70 R66 density gate drift")

    roots = {
        "NAS100": nas100_root,
        "SP500": sp500_root,
        "US30": us30_root,
    }
    five = _window(roots=roots, window_id="5Y")
    two = _window(roots=roots, window_id="2Y")
    failed = _window(roots=roots, window_id="R66")
    transport = _transport(five, two, failed)

    return {
        "schema": SCHEMA,
        "identity": IDENTITY,
        "source_failure": {
            "decision": r67.SOURCE_R66_DECISION,
            "r66_density_gate": r69.R66_DENSITY_GATE,
            "r66_observed_sample": 773,
        },
        "generator_contract": {
            "anchors_new_york": list(r4.V7_ANCHORS),
            "daily_bias": "V7_SOURCE_CORRECTED",
            "poi_families": [
                v6.PoiKind.FVG.value,
                v6.PoiKind.RELEVANT_SWING.value,
                v6.PoiKind.CISD.value,
            ],
            "source_poi_lookback_h4": 3,
            "structural_rearm": True,
            "m15_cisd_required": True,
            "protected_swing_required": True,
            "first_causal_continuation_required": True,
            "same_c2_body_requirement": True,
        },
        "five_year": five,
        "recent_two_year": two,
        "r66_failed_holdout": failed,
        "transport": transport,
        "decision": "R70_FUNNEL_FORENSICS_COMPLETE_NO_CANDIDATE",
        "governance": {
            "forensics_only": True,
            "consumed_evidence_only": True,
            "fresh_holdout_claim": False,
            "generator_modified": False,
            "anchors_added": False,
            "poi_families_added": False,
            "lookback_changed": False,
            "signals_added": False,
            "signals_suppressed": False,
            "risk_changed": False,
            "management_changed": False,
            "calendar_or_year_runtime_feature": False,
            "post_entry_outcome_used": False,
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
                    "sample": report["five_year"]["canonical_signal_count"],
                    "market_counts": report["five_year"][
                        "canonical_market_counts"
                    ],
                    "aggregate": report["five_year"]["aggregate"],
                },
                "recent_two_year": {
                    "sample": report["recent_two_year"][
                        "canonical_signal_count"
                    ],
                    "market_counts": report["recent_two_year"][
                        "canonical_market_counts"
                    ],
                    "aggregate": report["recent_two_year"]["aggregate"],
                },
                "r66": {
                    "sample": report["r66_failed_holdout"][
                        "canonical_signal_count"
                    ],
                    "market_counts": report["r66_failed_holdout"][
                        "canonical_market_counts"
                    ],
                    "aggregate": report["r66_failed_holdout"]["aggregate"],
                },
                "conversion_transport_ranked": report["transport"][
                    "conversion_transport_ranked"
                ],
                "decision": report["decision"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
