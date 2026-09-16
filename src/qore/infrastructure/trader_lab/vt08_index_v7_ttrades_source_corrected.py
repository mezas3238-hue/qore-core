"""VT-08 Index V7 source-corrected TTrades candidate."""

from __future__ import annotations

import argparse
import json
from collections.abc import Sequence
from datetime import UTC, date, datetime, time, timedelta
from decimal import Decimal
from hashlib import sha256
from pathlib import Path
from typing import cast
from zoneinfo import ZoneInfo

from qore.infrastructure.trader_lab import vt08_index_v6_ttrades_source_faithful as v6
from qore.infrastructure.trader_lab.vt08_index_v2_candidate import (
    _in_partition,
    _load_candidate_market,
)
from qore.infrastructure.traders.contracts import DemoTradingSetupSide
from qore.infrastructure.traders.vt08_index_c2_positional_r1 import (
    Vt08IndexC2R1Bar,
    resolve_daily_bias,
)
from qore.kernel.errors import InfrastructureError

SCHEMA = "qore.trader_lab.vt08_index_v7_ttrades_source_corrected.v1"
CANDIDATE_ID = "VT08_INDEX_V7_TTRADES_SOURCE_CORRECTED_001"
PRIMARY_SOURCE_SHA256 = v6.PRIMARY_SOURCE_SHA256
AUTHORIZED_MARKETS = v6.AUTHORIZED_MARKETS
H4_SOURCE_CYCLE_NY = (18, 22, 2, 6, 10, 14)
EXECUTABLE_H4_ANCHORS_NY = (22, 2, 6, 10)
TARGET_R_MULTIPLE = Decimal("2")
PRIMARY_STRESS_R = Decimal("0.05")
SECONDARY_STRESS_R = Decimal("0.10")
_NY = ZoneInfo("America/New_York")

_RULE_MATERIAL = {
    "candidate_id": CANDIDATE_ID,
    "markets": AUTHORIZED_MARKETS,
    "h4_source_cycle_new_york": H4_SOURCE_CYCLE_NY,
    "executable_h4_anchors_new_york": EXECUTABLE_H4_ANCHORS_NY,
    "daily_open_context_hour_new_york": 18,
    "owner_disabled_execution_anchor_new_york": 14,
    "daily_bias": "previous-day-close-continuation-or-sweep-reversal",
    "source_day": "18:00-to-17:00-ny-available-bars",
    "source_day_allowed_missing_slots": ("16:15-ny-broker-maintenance",),
    "source_day_synthesized_ohlc": False,
    "poi_priority": ("fvg", "relevant-swing", "cisd"),
    "relevant_swing_window_h4": 3,
    "c2": "sweep-prior-extreme-close-back-inside",
    "c3": "body-engulf-without-directional-extreme-sweep-after-c2-failure",
    "wick_confirmation": "m15-cisd-protected-swing-no-numeric-wick-threshold",
    "same_c2_body_transition": "long-close-above-h4-open-short-close-below-h4-open",
    "execution": "first-causal-m15-continuation-closure",
    "entry": "continuation-close",
    "stop": "protected-swing-extreme",
    "target_r": "2",
    "same_bar_ambiguity": "stop-first",
    "forced_h4_lifecycle": False,
    "daily_unique_only": False,
    "v3_geometry": False,
    "d1_peer_count_gate": False,
    "smt_mandatory": False,
    "source_refs": v6.SOURCE_REFS,
}
RULE_FINGERPRINT = sha256(
    json.dumps(
        _RULE_MATERIAL,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("utf-8")
).hexdigest()


class Vt08IndexV7Error(InfrastructureError):
    __slots__ = ()


def _expected_source_day_slots(end_date: date) -> tuple[datetime, ...]:
    start_local = datetime.combine(
        end_date - timedelta(days=1), time(hour=18), tzinfo=_NY
    )
    end_local = datetime.combine(end_date, time(hour=17), tzinfo=_NY)
    cursor = start_local.astimezone(UTC)
    end_utc = end_local.astimezone(UTC)
    slots: list[datetime] = []
    while cursor < end_utc:
        slots.append(cursor)
        cursor += timedelta(minutes=15)
    return tuple(slots)


def _is_allowed_maintenance_gap(opened_at_utc: datetime, *, end_date: date) -> bool:
    local = opened_at_utc.astimezone(_NY)
    return (
        local.date() == end_date
        and local.hour == 16
        and local.minute == 15
        and local.second == 0
    )


def _source_day(
    indexed: dict[datetime, Vt08IndexC2R1Bar], *, end_date: date
) -> tuple[Vt08IndexC2R1Bar, tuple[datetime, ...]] | None:
    slots = _expected_source_day_slots(end_date)
    rows: list[Vt08IndexC2R1Bar] = []
    missing: list[datetime] = []
    for opened_at in slots:
        bar = indexed.get(opened_at)
        if bar is None:
            missing.append(opened_at)
            continue
        if bar.opened_at.astimezone(UTC) != opened_at:
            return None
        if bar.closed_at.astimezone(UTC) != opened_at + timedelta(minutes=15):
            return None
        rows.append(bar)
    if not rows or len(missing) > 1:
        return None
    if missing and not _is_allowed_maintenance_gap(missing[0], end_date=end_date):
        return None
    expected_start = slots[0]
    expected_close = slots[-1] + timedelta(minutes=15)
    if rows[0].opened_at.astimezone(UTC) != expected_start:
        return None
    if rows[-1].closed_at.astimezone(UTC) != expected_close:
        return None
    return (
        Vt08IndexC2R1Bar(
            opened_at=rows[0].opened_at,
            closed_at=rows[-1].closed_at,
            open=rows[0].open,
            high=max(item.high for item in rows),
            low=min(item.low for item in rows),
            close=rows[-1].close,
        ),
        tuple(missing),
    )


def _latest_complete_source_days(
    indexed: dict[datetime, Vt08IndexC2R1Bar], *, before_local: datetime
) -> tuple[Vt08IndexC2R1Bar, Vt08IndexC2R1Bar] | None:
    end_date = before_local.astimezone(_NY).date() - timedelta(days=1)
    retained: list[Vt08IndexC2R1Bar] = []
    for offset in range(14):
        result = _source_day(indexed, end_date=end_date - timedelta(days=offset))
        if result is None:
            continue
        retained.append(result[0])
        if len(retained) == 2:
            current_day, previous_day = retained
            return previous_day, current_day
    return None


def _daily_bias(
    indexed: dict[datetime, Vt08IndexC2R1Bar], *, before: datetime
) -> DemoTradingSetupSide | None:
    source_days = _latest_complete_source_days(indexed, before_local=before)
    if source_days is None:
        return None
    return resolve_daily_bias(
        previous_day=source_days[0], current_day=source_days[1]
    )


def _signal_for_h4(
    *,
    symbol: str,
    indexed: dict[datetime, Vt08IndexC2R1Bar],
    h4: dict[datetime, Vt08IndexC2R1Bar],
    h4_opened_at: datetime,
) -> v6.CandidateSignal | None:
    if h4_opened_at.astimezone(_NY).hour not in EXECUTABLE_H4_ANCHORS_NY:
        return None
    h4_bar = h4.get(h4_opened_at.astimezone(UTC))
    if h4_bar is None:
        return None
    side = _daily_bias(indexed, before=h4_opened_at)
    if side is None:
        return None
    poi = v6._source_poi_for_h4(
        indexed, h4, h4_opened_at=h4_opened_at, side=side
    )
    if poi is None:
        return None
    bars = v6._bars_between(indexed, start=h4_opened_at, end=h4_bar.closed_at)
    if not bars:
        return None
    touch_index = v6._poi_touch_index(bars, poi)
    if touch_index is None:
        return None
    model_kind = v6._completed_h4_model(
        indexed, h4, current_h4_open=h4_opened_at, side=side
    )
    if model_kind is None:
        model_kind = v6.H4ModelKind.SAME_C2
    cisd = v6._first_cisd(bars, side=side, start_index=touch_index)
    if cisd is None:
        return None
    cisd_index, cisd_level, protected_swing = cisd
    continuation_index = v6._first_continuation(
        bars,
        side=side,
        start_index=cisd_index + 1,
        protected_swing=protected_swing,
    )
    if continuation_index is None:
        return None
    continuation = bars[continuation_index]
    entry = continuation.close
    if model_kind is v6.H4ModelKind.SAME_C2:
        in_body = (
            entry > h4_bar.open
            if side is DemoTradingSetupSide.LONG
            else entry < h4_bar.open
        )
        if not in_body:
            return None
    risk = (
        entry - protected_swing
        if side is DemoTradingSetupSide.LONG
        else protected_swing - entry
    )
    if risk <= 0:
        return None
    target = (
        entry + TARGET_R_MULTIPLE * risk
        if side is DemoTradingSetupSide.LONG
        else entry - TARGET_R_MULTIPLE * risk
    )
    if target <= 0:
        return None
    return v6.CandidateSignal(
        symbol=symbol,
        side=side,
        model_kind=model_kind,
        h4_opened_at=h4_opened_at,
        signal_at=continuation.closed_at,
        entry=entry,
        stop=protected_swing,
        target=target,
        poi=poi,
        cisd_level=cisd_level,
        cisd_confirmed_at=bars[cisd_index].closed_at,
        protected_swing_extreme=protected_swing,
    )


def _session_diagnostics(
    indexed: dict[datetime, Vt08IndexC2R1Bar],
    *,
    start_date: date,
    end_date_exclusive: date,
) -> dict[str, object]:
    cursor = start_date
    accepted = 0
    maintenance_gap = 0
    rejected = 0
    while cursor < end_date_exclusive:
        result = _source_day(indexed, end_date=cursor)
        if result is None:
            rejected += 1
        else:
            accepted += 1
            if result[1]:
                maintenance_gap += 1
        cursor += timedelta(days=1)
    return {
        "days_checked": accepted + rejected,
        "accepted_source_days": accepted,
        "accepted_with_16_15_maintenance_gap": maintenance_gap,
        "rejected_source_days": rejected,
        "synthesized_ohlc_bars": 0,
    }


def _market_report(
    *,
    symbol: str,
    bars: Sequence[Vt08IndexC2R1Bar],
    start_date: date,
    end_date_exclusive: date,
) -> dict[str, object]:
    indexed = {bar.opened_at.astimezone(UTC): bar for bar in bars}
    h4 = v6._build_h4(indexed)
    signals: list[v6.CandidateSignal] = []
    for opened in sorted(h4):
        if opened.astimezone(_NY).hour not in EXECUTABLE_H4_ANCHORS_NY:
            continue
        if not _in_partition(
            opened,
            start_date=start_date,
            end_date_exclusive=end_date_exclusive,
        ):
            continue
        signal = _signal_for_h4(
            symbol=symbol,
            indexed=indexed,
            h4=h4,
            h4_opened_at=opened,
        )
        if signal is not None:
            signals.append(signal)
    ordered_signals = tuple(
        sorted(signals, key=lambda item: (item.signal_at, item.symbol))
    )
    trades = tuple(
        trade
        for signal in ordered_signals
        if (
            trade := v6._model_trade(
                signal,
                indexed=indexed,
                end_date_exclusive=end_date_exclusive,
            )
        )
        is not None
    )
    return {
        "h4_complete_bars": len(h4),
        "signals": [item.payload() for item in ordered_signals],
        "trades": trades,
        "session_reconstruction": _session_diagnostics(
            indexed,
            start_date=start_date,
            end_date_exclusive=end_date_exclusive,
        ),
    }


def build_report(
    *,
    nas100: Path,
    sp500: Path,
    us30: Path,
    start_date: date,
    end_date_exclusive: date,
    expected_software_sha: str,
    minimum_evidence_days: int,
) -> dict[str, object]:
    paths = {"NAS100": nas100, "SP500": sp500, "US30": us30}
    provenance: dict[str, object] = {}
    all_trades: list[v6.ModeledV6Trade] = []
    market_reports: dict[str, object] = {}
    for symbol in AUTHORIZED_MARKETS:
        fingerprint, provider, checked_at, bars = _load_candidate_market(
            paths[symbol],
            expected_symbol=symbol,
            expected_software_sha=expected_software_sha,
            minimum_evidence_days=minimum_evidence_days,
        )
        market_report = _market_report(
            symbol=symbol,
            bars=bars,
            start_date=start_date,
            end_date_exclusive=end_date_exclusive,
        )
        trades = cast(tuple[v6.ModeledV6Trade, ...], market_report["trades"])
        all_trades.extend(trades)
        signals = cast(list[object], market_report["signals"])
        market_reports[symbol] = {
            "h4_complete_bars": market_report["h4_complete_bars"],
            "signal_count": len(signals),
            "session_reconstruction": market_report["session_reconstruction"],
        }
        provenance[symbol] = {
            "provider_symbol": provider,
            "account_fingerprint": fingerprint,
            "checked_at": checked_at.astimezone(UTC).isoformat(),
            "software_sha": expected_software_sha,
            "m15_bars": len(bars),
        }
    ordered = tuple(
        sorted(all_trades, key=lambda item: (item.signal.signal_at, item.signal.symbol))
    )
    n = len(ordered)
    return {
        "schema": SCHEMA,
        "candidate_id": CANDIDATE_ID,
        "rule_fingerprint": RULE_FINGERPRINT,
        "rules": _RULE_MATERIAL,
        "partition": {
            "start_date": start_date.isoformat(),
            "end_date_exclusive": end_date_exclusive.isoformat(),
        },
        "provenance": provenance,
        "market_reports": market_reports,
        "metrics_raw": v6._metrics(ordered),
        "metrics_primary_stress": v6._metrics(ordered, stress=PRIMARY_STRESS_R),
        "metrics_secondary_stress": v6._metrics(ordered, stress=SECONDARY_STRESS_R),
        "by_market_primary_stress": v6._breakdown(
            ordered, key="symbol", stress=PRIMARY_STRESS_R
        ),
        "by_side_primary_stress": v6._breakdown(
            ordered, key="side", stress=PRIMARY_STRESS_R
        ),
        "by_anchor_primary_stress": v6._breakdown(
            ordered, key="anchor", stress=PRIMARY_STRESS_R
        ),
        "by_model_primary_stress": v6._breakdown(
            ordered, key="model_kind", stress=PRIMARY_STRESS_R
        ),
        "halves_primary_stress": [
            v6._metrics(ordered[: n // 2], stress=PRIMARY_STRESS_R),
            v6._metrics(ordered[n // 2 :], stress=PRIMARY_STRESS_R),
        ],
        "quartile_mean_r_primary_stress": v6._quartile_means(
            ordered, stress=PRIMARY_STRESS_R
        ),
        "boundary_mark_count": sum(
            item.exit_reason == "boundary-mark" for item in ordered
        ),
        "trades": [item.payload() for item in ordered],
        "governance": {
            "research_only": True,
            "fresh_holdout_required": True,
            "live_authorized": False,
            "real_capital_authorized": False,
            "production_authorized": False,
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--nas100", type=Path, required=True)
    parser.add_argument("--sp500", type=Path, required=True)
    parser.add_argument("--us30", type=Path, required=True)
    parser.add_argument("--start-date", type=date.fromisoformat, required=True)
    parser.add_argument("--end-date-exclusive", type=date.fromisoformat, required=True)
    parser.add_argument("--expected-software-sha", required=True)
    parser.add_argument("--minimum-evidence-days", type=int, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    report = build_report(
        nas100=args.nas100,
        sp500=args.sp500,
        us30=args.us30,
        start_date=args.start_date,
        end_date_exclusive=args.end_date_exclusive,
        expected_software_sha=args.expected_software_sha,
        minimum_evidence_days=args.minimum_evidence_days,
    )
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(
        json.dumps(report, sort_keys=True, separators=(",", ":"), allow_nan=False)
        + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "candidate_id": CANDIDATE_ID,
                "rule_fingerprint": RULE_FINGERPRINT,
                "sample": cast(dict[str, object], report["metrics_raw"])["sample"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
