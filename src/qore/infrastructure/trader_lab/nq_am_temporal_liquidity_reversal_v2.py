"""QORE NQ AM Temporal Liquidity Reversal V2.

Source-fidelity repair of V1. V2 replaces the prior-RTH-low liquidity model
with completed electronic-hours daily lows, matching the reviewed source's
explicit use of a prior daily low. Research only; fresh holdout remains sealed.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from datetime import UTC, date, datetime, time, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any, Sequence

from qore.infrastructure.trader_lab import nq_am_temporal_liquidity_reversal_v1 as v1
from qore.infrastructure.trader_lab.ict_turtle_soup_r4_source_exact import Bar, Evidence

IDENTITY = "QORE_NQ_AM_TEMPORAL_LIQUIDITY_REVERSAL_V2"
SOURCE_VIDEO_ID = v1.SOURCE_VIDEO_ID
SOURCE_OPERATION = v1.SOURCE_OPERATION
SYMBOL = v1.SYMBOL
PROVIDER_SYMBOL = v1.PROVIDER_SYMBOL
PROVIDER = v1.PROVIDER
INSTRUMENT_CLASS = v1.INSTRUMENT_CLASS

ETH_OPEN = time(18, 0)
ETH_CLOSE = time(17, 0)
DAILY_REFERENCE_LOOKBACK = 5

DEV_EVIDENCE_ID = "NQ_AM_TLR_V2_CONSUMED_DEV_2024_08_13_2025_08_13"
DEV_EVAL_OPEN_NY = v1.DEV_EVAL_OPEN_NY
DEV_EVAL_CLOSE_NY = v1.DEV_EVAL_CLOSE_NY
DEV_ACQUISITION_OPEN = v1.DEV_ACQUISITION_OPEN
DEV_ACQUISITION_CLOSE = v1.DEV_ACQUISITION_CLOSE

Variant = v1.Variant
RthSession = v1.RthSession
BearishFvg = v1.BearishFvg
Trade = v1.Trade
DayRecord = v1.DayRecord


@dataclass(frozen=True, slots=True)
class EthDailySession:
    trade_day: date
    opened_at: datetime
    closed_at: datetime
    high: Decimal
    low: Decimal
    close: Decimal
    bars: tuple[Bar, ...]


def _eth_bounds(trade_day: date) -> tuple[datetime, datetime]:
    opened = datetime.combine(
        trade_day - timedelta(days=1), ETH_OPEN, tzinfo=v1.NY
    ).astimezone(UTC)
    closed = datetime.combine(trade_day, ETH_CLOSE, tzinfo=v1.NY).astimezone(UTC)
    return opened, closed


def build_eth_daily_sessions(
    bars: Sequence[Bar], trade_days: Sequence[date]
) -> tuple[EthDailySession, ...]:
    sessions: list[EthDailySession] = []
    for trade_day in sorted(set(trade_days)):
        opened_at, closed_at = _eth_bounds(trade_day)
        sample = tuple(
            item for item in bars if opened_at <= item.opened_at < closed_at
        )
        if not sample:
            continue
        sessions.append(
            EthDailySession(
                trade_day=trade_day,
                opened_at=opened_at,
                closed_at=closed_at,
                high=max(item.high for item in sample),
                low=min(item.low for item in sample),
                close=sample[-1].close,
                bars=sample,
            )
        )
    return tuple(sessions)


def _daily_context_bullish(previous: EthDailySession, current_open: Decimal) -> bool:
    midpoint = (previous.high + previous.low) / Decimal(2)
    return previous.close >= midpoint and previous.high > current_open


def _untouched_daily_reference(
    sessions: Sequence[EthDailySession],
    *,
    current_day: date,
    current_open_at: datetime,
    current_open: Decimal,
    all_bars: Sequence[Bar],
    extension_2: Decimal,
    gap: Decimal,
    variant: Variant,
) -> tuple[EthDailySession, Decimal] | None:
    prior = [item for item in sessions if item.trade_day < current_day]
    candidates: list[EthDailySession] = []
    for item in prior[-DAILY_REFERENCE_LOOKBACK:]:
        if item.low >= current_open:
            continue
        touched = any(
            bar.low <= item.low
            for bar in all_bars
            if item.closed_at <= bar.opened_at < current_open_at
        )
        if not touched:
            candidates.append(item)
    if not candidates:
        return None
    if variant is Variant.NO_GAP_EXTENSION:
        selected = max(candidates, key=lambda item: item.low)
        return selected, selected.low

    tolerance = gap / Decimal(4)
    aligned = [
        item for item in candidates if abs(item.low - extension_2) <= tolerance
    ]
    if not aligned:
        return None
    selected = min(
        aligned,
        key=lambda item: (abs(item.low - extension_2), -item.trade_day.toordinal()),
    )
    return selected, selected.low


def _record(
    current: RthSession,
    variant: Variant,
    *,
    terminal_stage: str,
    reason: str,
    eligible: bool = False,
    gap: Decimal | None = None,
    reference_day: date | None = None,
    reference_low: Decimal | None = None,
    extension_2: Decimal | None = None,
    sweep_at: datetime | None = None,
    sweep_low: Decimal | None = None,
    rejection_confirmed: bool = False,
    ifvg_confirmed: bool = False,
    entry_at: datetime | None = None,
    false_bottom: bool = False,
    trade: Trade | None = None,
) -> DayRecord:
    return DayRecord(
        ny_day=current.ny_day,
        variant=variant.value,
        eligible=eligible,
        terminal_stage=terminal_stage,
        reason=reason,
        gap=gap,
        reference_day=reference_day,
        reference_low=reference_low,
        extension_2=extension_2,
        sweep_at=sweep_at,
        sweep_low=sweep_low,
        rejection_confirmed=rejection_confirmed,
        ifvg_confirmed=ifvg_confirmed,
        entry_at=entry_at,
        false_bottom=false_bottom,
        trade=trade,
    )


def evaluate_day(
    evidence: Evidence,
    rth_sessions: Sequence[RthSession],
    eth_sessions: Sequence[EthDailySession],
    index: int,
    *,
    variant: Variant = Variant.FULL,
) -> DayRecord:
    current = rth_sessions[index]
    previous_rth = rth_sessions[index - 1]
    previous_eth = next(
        (item for item in reversed(eth_sessions) if item.trade_day < current.ny_day),
        None,
    )
    if previous_eth is None:
        return _record(
            current,
            variant,
            terminal_stage="data",
            reason="missing-prior-eth-day",
        )
    if not _daily_context_bullish(previous_eth, current.open):
        return _record(
            current,
            variant,
            terminal_stage="context",
            reason="eth-daily-context-not-bullish",
        )

    gap = previous_rth.settle - current.open
    if gap <= 0:
        return _record(
            current,
            variant,
            terminal_stage="gap",
            reason="not-gap-down",
        )

    lower_octant = current.open + gap / Decimal(8)
    lower_quadrant = current.open + gap / Decimal(4)
    extension_2 = current.open - Decimal(2) * gap
    early = v1._bars_between(
        evidence.bars,
        current.open_at,
        v1._at_ny(current.ny_day, v1.EARLY_GAP_END),
    )
    if not early:
        return _record(
            current,
            variant,
            terminal_stage="data",
            reason="missing-early-rth-bars",
        )
    if variant is not Variant.NO_RTH_GAP_CONTEXT:
        if max(item.high for item in early) >= lower_quadrant:
            return _record(
                current,
                variant,
                terminal_stage="gap-repair",
                reason="lower-quadrant-repaired",
                eligible=True,
                gap=gap,
                extension_2=extension_2,
            )
        if max(item.close for item in early) >= lower_octant:
            return _record(
                current,
                variant,
                terminal_stage="gap-repair",
                reason="lowest-octant-body-accepted",
                eligible=True,
                gap=gap,
                extension_2=extension_2,
            )

    reference = _untouched_daily_reference(
        eth_sessions,
        current_day=current.ny_day,
        current_open_at=current.open_at,
        current_open=current.open,
        all_bars=evidence.bars,
        extension_2=extension_2,
        gap=gap,
        variant=variant,
    )
    if reference is None:
        return _record(
            current,
            variant,
            terminal_stage="daily-liquidity-confluence",
            reason="no-untouched-eth-daily-low-at-2sd-cluster",
            eligible=True,
            gap=gap,
            extension_2=extension_2,
        )
    ref_session, ref_low = reference

    macro_open = v1._at_ny(current.ny_day, v1.MACRO_FIRST_HALF_OPEN)
    first_half_close = v1._at_ny(current.ny_day, v1.MACRO_FIRST_HALF_CLOSE)
    sweep_search_open = (
        v1._at_ny(current.ny_day, v1.EARLY_GAP_END)
        if variant is Variant.NO_MACRO
        else macro_open
    )
    if variant is not Variant.NO_MACRO:
        pre_macro = v1._bars_between(evidence.bars, current.open_at, macro_open)
        if any(item.low < ref_low for item in pre_macro):
            return _record(
                current,
                variant,
                terminal_stage="timing",
                reason="daily-sellside-swept-before-macro",
                eligible=True,
                gap=gap,
                reference_day=ref_session.trade_day,
                reference_low=ref_low,
                extension_2=extension_2,
            )

    sweep_window = v1._bars_between(
        evidence.bars,
        sweep_search_open,
        first_half_close,
    )
    sweep = next((item for item in sweep_window if item.low < ref_low), None)
    if sweep is None:
        return _record(
            current,
            variant,
            terminal_stage="sweep",
            reason="no-daily-sellside-sweep",
            eligible=True,
            gap=gap,
            reference_day=ref_session.trade_day,
            reference_low=ref_low,
            extension_2=extension_2,
        )
    after_sweep = tuple(
        item for item in sweep_window if item.opened_at >= sweep.opened_at
    )
    sweep_low = min(item.low for item in after_sweep)
    acceptance_floor = max(ref_low, extension_2)
    rejection = all(item.close > acceptance_floor for item in after_sweep)
    if variant is not Variant.NO_ACCEPTANCE_TEST and not rejection:
        return _record(
            current,
            variant,
            terminal_stage="acceptance",
            reason="body-accepted-below-daily-reference-or-2sd",
            eligible=True,
            gap=gap,
            reference_day=ref_session.trade_day,
            reference_low=ref_low,
            extension_2=extension_2,
            sweep_at=sweep.opened_at,
            sweep_low=sweep_low,
        )

    deadline = v1._at_ny(current.ny_day, v1.MACRO_CLOSE)
    zone: BearishFvg | None
    if variant is Variant.NO_IFVG:
        entry_bar = next(
            (
                item
                for item in evidence.bars
                if first_half_close <= item.opened_at < deadline
                and item.close > acceptance_floor
            ),
            None,
        )
        if entry_bar is None:
            return _record(
                current,
                variant,
                terminal_stage="entry",
                reason="no-post-rejection-entry-bar",
                eligible=True,
                gap=gap,
                reference_day=ref_session.trade_day,
                reference_low=ref_low,
                extension_2=extension_2,
                sweep_at=sweep.opened_at,
                sweep_low=sweep_low,
                rejection_confirmed=rejection,
            )
        zone = None
        entry_at = entry_bar.closed_at
        entry_price = entry_bar.close
    else:
        ifvg = v1._ifvg_entry(
            evidence.bars,
            sweep_at=sweep.opened_at,
            deadline=deadline,
        )
        if ifvg is None:
            return _record(
                current,
                variant,
                terminal_stage="ifvg",
                reason="no-causal-ifvg-inversion-entry",
                eligible=True,
                gap=gap,
                reference_day=ref_session.trade_day,
                reference_low=ref_low,
                extension_2=extension_2,
                sweep_at=sweep.opened_at,
                sweep_low=sweep_low,
                rejection_confirmed=rejection,
                false_bottom=v1._false_bottom(
                    evidence.bars,
                    start=first_half_close,
                    expiry=v1._at_ny(current.ny_day, v1.AM_EXPIRY),
                    sweep_low=sweep_low,
                    target=current.open,
                ),
            )
        zone, entry_at, entry_price = ifvg

    tick = v1._tick_size(evidence.digits)
    stop = sweep_low - tick
    target = current.open
    if entry_price <= stop or target <= entry_price:
        return _record(
            current,
            variant,
            terminal_stage="geometry",
            reason="invalid-entry-stop-target-geometry",
            eligible=True,
            gap=gap,
            reference_day=ref_session.trade_day,
            reference_low=ref_low,
            extension_2=extension_2,
            sweep_at=sweep.opened_at,
            sweep_low=sweep_low,
            rejection_confirmed=rejection,
            ifvg_confirmed=zone is not None,
            entry_at=entry_at,
        )

    expiry = v1._at_ny(current.ny_day, v1.AM_EXPIRY)
    exit_at, exit_price, exit_reason, gross_r, mfe_r, mae_r = v1._simulate(
        evidence.bars,
        entry_at=entry_at,
        expiry=expiry,
        entry=entry_price,
        stop=stop,
        target=target,
    )
    trade = Trade(
        ny_day=current.ny_day,
        variant=variant.value,
        entry_at=entry_at,
        exit_at=exit_at,
        reference_day=ref_session.trade_day,
        reference_low=ref_low,
        gap=gap,
        gap_lower_octant=lower_octant,
        gap_lower_quadrant=lower_quadrant,
        gap_extension_2=extension_2,
        sweep_at=sweep.opened_at,
        sweep_low=sweep_low,
        ifvg_created_at=None if zone is None else zone.created_at,
        ifvg_low=None if zone is None else zone.low,
        ifvg_high=None if zone is None else zone.high,
        entry=entry_price,
        stop=stop,
        target=target,
        exit_price=exit_price,
        gross_r=gross_r,
        primary_net_r=gross_r - v1.PRIMARY_FRICTION_R,
        stress_net_r=gross_r - v1.STRESS_FRICTION_R,
        mfe_r=mfe_r,
        mae_r=mae_r,
        exit_reason=exit_reason,
    )
    return _record(
        current,
        variant,
        terminal_stage="trade",
        reason="trade",
        eligible=True,
        gap=gap,
        reference_day=ref_session.trade_day,
        reference_low=ref_low,
        extension_2=extension_2,
        sweep_at=sweep.opened_at,
        sweep_low=sweep_low,
        rejection_confirmed=rejection,
        ifvg_confirmed=zone is not None,
        entry_at=entry_at,
        false_bottom=v1._false_bottom(
            evidence.bars,
            start=entry_at,
            expiry=expiry,
            sweep_low=sweep_low,
            target=target,
        ),
        trade=trade,
    )


def replay(
    evidence: Evidence,
    *,
    eval_open_ny: date,
    eval_close_ny: date,
    variant: Variant = Variant.FULL,
) -> list[DayRecord]:
    rth = v1.build_rth_sessions(evidence.bars)
    trade_days = [item.ny_day for item in rth]
    eth = build_eth_daily_sessions(evidence.bars, trade_days)
    records: list[DayRecord] = []
    for index in range(1, len(rth)):
        if eval_open_ny <= rth[index].ny_day < eval_close_ny:
            records.append(
                evaluate_day(
                    evidence,
                    rth,
                    eth,
                    index,
                    variant=variant,
                )
            )
    return records


def _load_evidence(path: Path) -> tuple[Evidence, dict[str, Any]]:
    payload = json.loads(path.read_text())
    if payload.get("identity") != IDENTITY:
        raise ValueError("unexpected candidate identity")
    raw = payload.get("periods", {}).get("M1")
    if not isinstance(raw, list) or not raw:
        raise ValueError("M1 evidence missing")
    bars = tuple(
        Bar(
            opened_at=datetime.fromisoformat(str(item["opened_at"])).astimezone(UTC),
            closed_at=datetime.fromisoformat(str(item["closed_at"])).astimezone(UTC),
            open=Decimal(str(item["open"])),
            high=Decimal(str(item["high"])),
            low=Decimal(str(item["low"])),
            close=Decimal(str(item["close"])),
        )
        for item in raw
    )
    return (
        Evidence(
            symbol=SYMBOL,
            digits=int(payload["symbol"]["digits"]),
            bars=bars,
        ),
        payload,
    )


def collect_dev(output: Path) -> dict[str, Any]:
    evidence = v1._collect_m1(
        PROVIDER_SYMBOL,
        acquisition_open=DEV_ACQUISITION_OPEN,
        acquisition_close=DEV_ACQUISITION_CLOSE,
    )
    payload = v1.evidence_payload(
        evidence,
        evidence_id=DEV_EVIDENCE_ID,
        acquisition_open=DEV_ACQUISITION_OPEN,
        acquisition_close=DEV_ACQUISITION_CLOSE,
        eval_open_ny=DEV_EVAL_OPEN_NY,
        eval_close_ny=DEV_EVAL_CLOSE_NY,
        evidence_status="CONSUMED_DEVELOPMENT_ONLY",
    )
    payload["identity"] = IDENTITY
    payload["schema"] = "qore.nq_am_temporal_liquidity_reversal.v2.evidence.v1"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(payload, separators=(",", ":"), sort_keys=True) + "\n"
    )
    return {
        "identity": IDENTITY,
        "evidence_id": DEV_EVIDENCE_ID,
        "bars": len(evidence.bars),
        "first_bar": evidence.bars[0].opened_at.isoformat(),
        "last_bar": evidence.bars[-1].closed_at.isoformat(),
    }


def _json_value(value: Any) -> Any:
    return v1._json_value(value)


def write_replay(
    evidence_path: Path,
    output: Path,
    *,
    variant: Variant,
) -> dict[str, Any]:
    evidence, payload = _load_evidence(evidence_path)
    eval_open = date.fromisoformat(str(payload["evaluation_open_ny"]))
    eval_close = date.fromisoformat(str(payload["evaluation_close_ny"]))
    records = replay(
        evidence,
        eval_open_ny=eval_open,
        eval_close_ny=eval_close,
        variant=variant,
    )
    summary = v1.summarize(records)
    summary.update(
        {
            "schema": "qore.nq_am_temporal_liquidity_reversal.v2.result.v1",
            "identity": IDENTITY,
            "evidence_id": payload["evidence_id"],
            "evidence_status": payload["evidence_status"],
            "provider": PROVIDER,
            "instrument_class": INSTRUMENT_CLASS,
            "evaluation_open_ny": eval_open.isoformat(),
            "evaluation_close_ny": eval_close.isoformat(),
            "demo_eligible": False,
            "live_authorized": False,
            "real_capital_authorized": False,
            "production_authorized": False,
        }
    )
    output.mkdir(parents=True, exist_ok=True)
    (output / "summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n"
    )
    (output / "day-records.json").write_text(
        json.dumps(
            [
                {key: _json_value(val) for key, val in asdict(item).items()}
                for item in records
            ],
            indent=2,
            sort_keys=True,
        )
        + "\n"
    )
    return summary


def write_ablation_suite(
    evidence_path: Path,
    output: Path,
) -> dict[str, Any]:
    results = {
        variant.value: write_replay(
            evidence_path,
            output / variant.value.lower(),
            variant=variant,
        )
        for variant in Variant
    }
    payload = {
        "schema": "qore.nq_am_temporal_liquidity_reversal.v2.ablation.v1",
        "identity": IDENTITY,
        "selection_authority": False,
        "variants": results,
    }
    output.mkdir(parents=True, exist_ok=True)
    (output / "ablation.json").write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n"
    )
    return payload


def main() -> None:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    collect = sub.add_parser("collect-dev")
    collect.add_argument("output", type=Path)
    ablate = sub.add_parser("ablate")
    ablate.add_argument("evidence", type=Path)
    ablate.add_argument("output", type=Path)
    args = parser.parse_args()
    if args.command == "collect-dev":
        print(json.dumps(collect_dev(args.output), sort_keys=True))
        return
    if args.command == "ablate":
        print(
            json.dumps(
                write_ablation_suite(args.evidence, args.output),
                sort_keys=True,
            )
        )
        return
    raise SystemExit("unknown command")


if __name__ == "__main__":
    main()
