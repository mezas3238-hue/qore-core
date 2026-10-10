"""Ninth audit: diagnose all 381 shadow-sensor vs V49 CISD mismatches.

Every difference is retained in the source census: earlier / later / same
instant differing family / missing, with 15-30-60 min future MFE/MAE for BOTH
timestamps. No trade is re-executed; observation labels are POST-HOC ONLY.
Input ledgers and market-native M1 must be independently sourced and pinned.
"""

from __future__ import annotations

import argparse
import bisect
import json
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any

from qore.infrastructure.trader_lab.capitalizer_cibo_m1_reader_v1 import (
    CapitalizerM1Bar,
    iter_cibo_m1,
)
from qore.infrastructure.trader_lab.capitalizer_high_frequency_capacity_census_v49 import (
    DEV_WINDOW_END,
    DEV_WINDOW_START,
    V49Opportunity,
)
from qore.infrastructure.trader_lab.capitalizer_scalper_h1_timing_session_diagnostic_v1 import (
    HORIZONS,
    aware,
    session_end_at,
)
from qore.infrastructure.trader_lab.capitalizer_scalper_v49_v50_g_waterfall_v1 import (
    _jsonl,
    source_id,
)

IDENTITY = "QORE_SCALPER_NINTH_381_CISD_SOURCE_MISMATCH_FORENSIC_V1"
DIFFERENCE_TYPES = (
    "SENSOR_EARLIER_THAN_V49",
    "SENSOR_LATER_THAN_V49",
    "SAME_TIME_DIFFERENT_FAMILY",
    "SENSOR_NOT_DETECTED",
    "MATCHED",
)


@dataclass(frozen=True, slots=True)
class HorizonExcursion:
    horizon_minutes: int
    native_contiguous_m1: bool
    signed_final_price: str | None
    mfe_price: str | None
    mae_price: str | None
    mfe_r_original_m15_stop: str | None
    mae_r_original_m15_stop: str | None
    risk_geometry_valid_at_observation: bool
    uses_ex_post_bars: bool = True
    authorizes_entry: bool = False

    def __post_init__(self) -> None:
        if not self.uses_ex_post_bars or self.authorizes_entry:
            raise ValueError("future excursions are research observations only")


@dataclass(frozen=True, slots=True)
class SourceCISDDiscrepancy:
    source_opportunity_id: str
    symbol: str
    session: str
    operating_date: str
    original_family: str
    sensor_family: str | None
    original_entry_at: str
    sensor_first_cisd_at: str | None
    direction: str
    h1_basis: str
    m15_confirmed_at: str
    classification: str
    sensor_minus_original_minutes: str | None
    sensor_event_not_necessarily_valid_under_v49_window: bool
    original_excur: tuple[HorizonExcursion, ...]
    sensor_excur: tuple[HorizonExcursion, ...]
    input_was_a_paper_order: bool = False
    outcome_used_to_admit_trade: bool = False

    def __post_init__(self) -> None:
        if (
            self.classification not in DIFFERENCE_TYPES
            or self.input_was_a_paper_order
            or self.outcome_used_to_admit_trade
        ):
            raise ValueError("forensic record must not authorize trading")


def classify(
    original_at: datetime,
    original_family: str,
    sensor_at: datetime | None,
    sensor_family: str | None,
) -> str:
    """Source-direction conflicts cannot occur in this H1-side-only adapter."""

    if sensor_at is None or sensor_family is None:
        return "SENSOR_NOT_DETECTED"
    if sensor_at < original_at:
        return "SENSOR_EARLIER_THAN_V49"
    if sensor_at > original_at:
        return "SENSOR_LATER_THAN_V49"
    if sensor_family != original_family:
        return "SAME_TIME_DIFFERENT_FAMILY"
    return "MATCHED"


def excursions(
    bars: tuple[CapitalizerM1Bar, ...],
    opened: tuple[datetime, ...],
    *,
    at: datetime | None,
    session: str,
    side: int,
    stop: Decimal,
) -> tuple[HorizonExcursion, ...]:
    """Stage close must exist, followed by exactly HORIZON contiguous M1 bars."""

    def missing(h: int) -> HorizonExcursion:
        return HorizonExcursion(h, False, None, None, None, None, None, False)

    if at is None:
        return tuple(missing(h) for h in HORIZONS)
    i = bisect.bisect_left(opened, at)
    if i <= 0 or bars[i-1].closed_at != at:
        return tuple(missing(h) for h in HORIZONS)
    entry = bars[i-1].close
    signed_risk = (entry - stop) * side
    valid_risk = signed_risk > 0
    results: list[HorizonExcursion] = []
    for h in HORIZONS:
        if at + timedelta(minutes=h) > session_end_at(at, session):
            results.append(missing(h))
            continue
        span = bars[i:i+h]
        if len(span) != h or any(
            b.opened_at != at + timedelta(minutes=k)
            for k, b in enumerate(span)
        ):
            results.append(missing(h))
            continue
        final = (span[-1].close - entry) * side
        favorable = (
            max((b.high for b in span), default=entry) - entry
            if side == 1 else entry - min((b.low for b in span), default=entry)
        )
        adverse = (
            entry - min((b.low for b in span), default=entry)
            if side == 1 else max((b.high for b in span), default=entry) - entry
        )
        mfe = max(Decimal(0), favorable)
        mae = max(Decimal(0), adverse)
        results.append(HorizonExcursion(
            horizon_minutes=h,
            native_contiguous_m1=True,
            signed_final_price=str(final),
            mfe_price=str(mfe), mae_price=str(mae),
            mfe_r_original_m15_stop=str(mfe / signed_risk)
            if valid_risk else None,
            mae_r_original_m15_stop=str(mae / signed_risk)
            if valid_risk else None,
            risk_geometry_valid_at_observation=valid_risk,
        ))
    return tuple(results)


def market(
    source_root: Path,
    sensor_root: Path,
    native_m1: Path,
) -> tuple[dict[str, Any], tuple[SourceCISDDiscrepancy, ...]]:
    source_files = sorted(source_root.rglob(
        "capitalizer-*-v49-hf-capacity-opportunities.jsonl"
    ))
    sensor_files = sorted(sensor_root.rglob("scalper-entry-sensors-rows.jsonl"))
    if len(source_files) != 1 or len(sensor_files) != 1:
        raise ValueError("need exactly one market original source and sensor ledger")
    sources = tuple(V49Opportunity(**r) for r in _jsonl(source_files[0]))
    reported = tuple(_jsonl(sensor_files[0]))
    observed = {r["source_opportunity_id"]: r for r in reported}
    if not sources or len(observed) != len(sources) or len(reported) != len(sources):
        raise ValueError("sensor and original source ID population diverges")
    native = tuple(
        b for b in iter_cibo_m1(native_m1)
        if DEV_WINDOW_START-timedelta(days=2) <= b.opened_at < DEV_WINDOW_END
    )
    symbol = sources[0].symbol
    if not native or any(b.symbol != symbol for b in native):
        raise ValueError("native M1 market missing or mismatched")
    times = tuple(b.opened_at for b in native)
    rows: list[SourceCISDDiscrepancy] = []
    counts: Counter[str] = Counter()
    by_pair: Counter[str] = Counter()
    for source in sources:
        sid = source_id(source)
        if sid not in observed:
            raise ValueError("missing sensor source ID")
        sensor = observed[sid]
        if (
            sensor["symbol"] != source.symbol
            or sensor["original_trigger_family"] != source.m1_trigger_family
            or sensor["original_entry_at"] != source.m1_trigger_confirmed_at
        ):
            raise ValueError("wrong source sensor original trade identity")
        at = aware(source.m1_trigger_confirmed_at)
        sensor_raw = sensor["first_source_cisd_confirmed_at"]
        sensor_at = aware(sensor_raw) if sensor_raw is not None else None
        family = sensor["first_source_cisd_family"]
        kind = classify(at, source.m1_trigger_family, sensor_at, family)
        if bool(sensor["sensor_source_identity_match"]) != (kind == "MATCHED"):
            raise ValueError("sensor-source mismatch flag inconsistent")
        if sensor_at is not None and sensor_at > at:
            # A predecision as-of sensor at original entry cannot report later
            # events; this must fail CLOSED, not become a late-signal group.
            raise ValueError("sensor reported future event after original entry")
        if sensor_at is not None and sensor_at < aware(source.m15_setup_confirmed_at):
            raise ValueError("M1 sensor event precedes confirmed M15 setup")
        side = 1 if source.h1_state_direction == "BULLISH" else -1
        stop = Decimal(source.m15_protected_swing_price)
        original_exc = excursions(
            native, times, at=at, session=source.session, side=side, stop=stop
        )
        sensor_exc = excursions(
            native, times, at=sensor_at, session=source.session,
            side=side, stop=stop,
        )
        counts[kind] += 1
        by_pair[f"{source.m1_trigger_family}->{family or 'NONE'}"] += 1
        rows.append(SourceCISDDiscrepancy(
            source_opportunity_id=sid, symbol=source.symbol,
            session=source.session, operating_date=source.operating_date,
            original_family=source.m1_trigger_family,
            sensor_family=family,
            original_entry_at=source.m1_trigger_confirmed_at,
            sensor_first_cisd_at=sensor_raw,
            direction=source.h1_state_direction,
            h1_basis=source.h1_state_basis,
            m15_confirmed_at=source.m15_setup_confirmed_at,
            classification=kind,
            sensor_minus_original_minutes=(
                str((sensor_at-at).total_seconds()/60)
                if sensor_at is not None else None
            ),
            sensor_event_not_necessarily_valid_under_v49_window=(kind != "MATCHED"),
            original_excur=original_exc,
            sensor_excur=sensor_exc,
        ))
    if len({r.source_opportunity_id for r in rows}) != len(sources):
        raise ValueError("duplicate source identity")
    return {
        "identity": IDENTITY, "symbol": symbol, "sources": len(sources),
        "classified": len(rows), "classification": dict(sorted(counts.items())),
        "family_transitions": dict(sorted(by_pair.items())),
        "paper_trades_changed": 0, "future_bars_used_only_for_labels": True,
        "causal_replay_policy_changed": False,
        "live_authorized": False, "trader_certified": False,
    }, tuple(rows)


def _one_horizon(
    rows: tuple[SourceCISDDiscrepancy, ...], h: int
) -> dict[str, Any]:
    pairs: list[tuple[HorizonExcursion, HorizonExcursion]] = []
    for row in rows:
        a = next(x for x in row.sensor_excur if x.horizon_minutes == h)
        b = next(x for x in row.original_excur if x.horizon_minutes == h)
        if a.native_contiguous_m1 and b.native_contiguous_m1:
            pairs.append((a,b))
    if not pairs:
        return {"paired_n": 0, "source_positive": None, "original_positive": None}
    def average(attribute: str, idx: int) -> str:
        values = [
            Decimal(v) for pair in pairs
            if (v := getattr(pair[idx], attribute)) is not None
        ]
        return str(sum(values, Decimal(0))/len(values)) if values else "NA"
    n = len(pairs)
    source_pos = sum(Decimal(a.signed_final_price or "0") > 0 for a,b in pairs)
    original_pos = sum(Decimal(b.signed_final_price or "0") > 0 for a,b in pairs)
    return {
        "paired_n": n,
        "source_positive": source_pos,
        "original_positive": original_pos,
        "source_positive_fraction": str(Decimal(source_pos)/n),
        "original_positive_fraction": str(Decimal(original_pos)/n),
        "source_minus_original_pp": str(
            Decimal(100)*(source_pos-original_pos)/n
        ),
        "source_mean_mfe_price": average("mfe_price",0),
        "original_mean_mfe_price": average("mfe_price",1),
        "source_mean_mae_price": average("mae_price",0),
        "original_mean_mae_price": average("mae_price",1),
        "source_mean_mfe_original_stop_r": average("mfe_r_original_m15_stop",0),
        "original_mean_mfe_original_stop_r": average("mfe_r_original_m15_stop",1),
        "source_mean_mae_original_stop_r": average("mae_r_original_m15_stop",0),
        "original_mean_mae_original_stop_r": average("mae_r_original_m15_stop",1),
        "source_valid_risk_geometry": sum(a.risk_geometry_valid_at_observation for a,b in pairs),
        "original_valid_risk_geometry": sum(b.risk_geometry_valid_at_observation for a,b in pairs),
        "NOT_ACTIONABLE": True,
    }


def _summary(rows: tuple[SourceCISDDiscrepancy, ...]) -> dict[str, Any]:
    return {
        "n": len(rows),
        "horizon": {str(h): _one_horizon(rows, h) for h in HORIZONS},
        "original_family": dict(sorted(Counter(r.original_family for r in rows).items())),
        "sensor_family": dict(sorted(Counter(r.sensor_family or "NONE" for r in rows).items())),
        "timing_negative_count": sum(
            Decimal(r.sensor_minus_original_minutes) < 0 for r in rows
            if r.sensor_minus_original_minutes is not None
        ),
    }


def aggregate(root: Path) -> dict[str, Any]:
    reports = [json.loads(p.read_text(encoding="utf-8"))
               for p in sorted(root.rglob("scalper-cisd-381-market.json"))]
    if len(reports) != 9 or len({r["symbol"] for r in reports}) != 9:
        raise ValueError("expected exact nine markets")
    rows = tuple(
        SourceCISDDiscrepancy(
            **{**raw,
               "original_excur": tuple(HorizonExcursion(**x)
                                       for x in raw["original_excur"]),
               "sensor_excur": tuple(HorizonExcursion(**x)
                                     for x in raw["sensor_excur"])}
        )
        for p in sorted(root.rglob("scalper-cisd-381-rows.jsonl"))
        for raw in _jsonl(p)
    )
    if len(rows) != 2876 or len({r.source_opportunity_id for r in rows}) != 2876:
        raise ValueError("not all frozen source identities retained")
    mismatch = tuple(r for r in rows if r.classification != "MATCHED")
    if len(mismatch) != 381:
        raise ValueError("cannot silently alter previously observed 381 mismatches")
    grouped: dict[str, list[SourceCISDDiscrepancy]] = defaultdict(list)
    for r in mismatch:
        grouped[r.classification].append(r)
    return {
        "identity": IDENTITY,
        "sources": len(rows), "total_mismatches": len(mismatch),
        "matched_sources": len(rows)-len(mismatch),
        "type_counts": dict(sorted(Counter(r.classification for r in mismatch).items())),
        "direction_conflicts_observable": False,
        "direction_conflicts_not_measured_because_sensor_inherits_h1_direction": True,
        "paired_all_discrepancies": _summary(mismatch),
        "by_type": {k:_summary(tuple(v)) for k,v in grouped.items()},
        "by_original_family": {
            k:_summary(tuple(r for r in mismatch if r.original_family == k))
            for k in sorted({r.original_family for r in mismatch})
        },
        "by_market": {
            k:_summary(tuple(r for r in mismatch if r.symbol == k))
            for k in sorted({r.symbol for r in mismatch})
        },
        "trades_reexecuted": 0, "authorizes_early_entries": False,
        "uses_future_outcomes_for_admission": False,
        "cognitive_master_frame_evaluated": False,
        "certification": "NO_CERTIFICABLE",
    }


def main() -> None:
    p=argparse.ArgumentParser()
    sub=p.add_subparsers(dest="mode",required=True)
    a=sub.add_parser("market")
    a.add_argument("control",type=Path)
    a.add_argument("sensors",type=Path)
    a.add_argument("native_m1",type=Path)
    a.add_argument("output",type=Path)
    b=sub.add_parser("matrix")
    b.add_argument("inputs",type=Path)
    b.add_argument("output",type=Path)
    args=p.parse_args()
    args.output.mkdir(parents=True,exist_ok=True)
    if args.mode=="market":
        report,rows=market(args.control,args.sensors,args.native_m1)
        (args.output/"scalper-cisd-381-market.json").write_text(
            json.dumps(report,indent=2,sort_keys=True)+"\n",encoding="utf-8"
        )
        with (args.output/"scalper-cisd-381-rows.jsonl").open("w",encoding="utf-8") as f:
            for r in rows:
                f.write(json.dumps(asdict(r),sort_keys=True)+"\n")
        print(json.dumps(report,sort_keys=True))
    else:
        report=aggregate(args.inputs)
        (args.output/"scalper-cisd-381-nine-market.json").write_text(
            json.dumps(report,indent=2,sort_keys=True)+"\n",encoding="utf-8"
        )
        print(json.dumps(report,sort_keys=True))


if __name__=="__main__":
    main()
