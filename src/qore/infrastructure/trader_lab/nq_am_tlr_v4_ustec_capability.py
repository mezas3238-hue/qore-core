"""USTEC-native capability test for the AM-session low reversal architecture.

The primary candidate is frozen before economics. Diagnostic variants have zero
promotion authority. Research only; no execution authority.
"""

from __future__ import annotations

import argparse
import json
import random
from bisect import bisect_left
from collections import Counter
from dataclasses import asdict, dataclass
from datetime import UTC, date, datetime, time, timedelta
from decimal import Decimal
from enum import StrEnum
from pathlib import Path
from statistics import mean
from typing import Any

from qore.infrastructure.trader_lab import nq_am_temporal_liquidity_reversal_v1 as v1
from qore.infrastructure.trader_lab import nq_am_temporal_liquidity_reversal_v2 as v2
from qore.infrastructure.trader_lab.ict_turtle_soup_r4_source_exact import (
    Bar,
    Evidence,
    _max_drawdown,
    _profit_factor,
)

IDENTITY = "QORE_NQ_AM_TLR_V4_USTEC_CAPABILITY_001"
PROVIDER = "ctrader-demo"
PROVIDER_SYMBOL = "USTEC"
SYMBOL = "NAS100"
INSTRUMENT_CLASS = "CFD_INDEX_USTEC_CAPABILITY_DISCOVERY"

EVAL_OPEN_NY = date(2016, 4, 20)
EVAL_CLOSE_NY = date(2017, 4, 20)
ACQUISITION_OPEN = datetime(2016, 4, 19, 0, tzinfo=UTC)
ACQUISITION_CLOSE = datetime(2017, 4, 21, 0, tzinfo=UTC)
EVIDENCE_ID = "VT31_R8_FRESH_NAS100_ARTIFACT_10402199719_ONE_YEAR_SLICE"

PRIMARY_VARIANT = "ROLLING_AM_LOW_M2"
PRIMARY_FRICTION_R = Decimal("0.05")
STRESS_FRICTION_R = Decimal("0.10")
BOOTSTRAP_SEED = 20260929

FOLDS: tuple[tuple[str, date, date], ...] = (
    ("Y1", EVAL_OPEN_NY, EVAL_CLOSE_NY),
)


class OpeningSignature(StrEnum):
    NONE = "NONE"
    M1 = "M1"
    M2 = "M2"
    M5 = "M5"


class ReferenceModel(StrEnum):
    ROLLING_AM_LOW = "ROLLING_AM_LOW"
    NEAREST_PRIOR_DAILY_LOW = "NEAREST_PRIOR_DAILY_LOW"
    TWO_SD_OPENING_GAP_EXTENSION = "TWO_SD_OPENING_GAP_EXTENSION"


@dataclass(frozen=True, slots=True)
class CapabilityTrade:
    variant: str
    ny_day: date
    reference_model: str
    opening_signature: str
    reference_day: date
    reference_price: Decimal
    gap: Decimal
    sweep_at: datetime
    sweep_low: Decimal
    entry_at: datetime
    entry: Decimal
    stop: Decimal
    target: Decimal
    exit_at: datetime
    exit_price: Decimal
    exit_reason: str
    gross_r: Decimal
    primary_net_r: Decimal
    stress_net_r: Decimal
    mfe_r: Decimal
    mae_r: Decimal


@dataclass(frozen=True, slots=True)
class CapabilityRecord:
    variant: str
    ny_day: date
    terminal_stage: str
    reason: str
    trade: CapabilityTrade | None


def variant_name(reference: ReferenceModel, signature: OpeningSignature) -> str:
    return f"{reference.value}_{signature.value}"


def _window(
    bars: tuple[Bar, ...],
    opened: tuple[datetime, ...],
    start: datetime,
    end: datetime,
) -> tuple[Bar, ...]:
    left = bisect_left(opened, start)
    right = bisect_left(opened, end)
    return bars[left:right]


def _build_eth_daily_sessions(
    bars: tuple[Bar, ...],
) -> tuple[v2.EthDailySession, ...]:
    by_day: dict[date, list[Bar]] = {}
    for bar in bars:
        local = bar.opened_at.astimezone(v1.NY)
        wall = local.timetz().replace(tzinfo=None)
        if wall >= time(18, 0):
            trade_day = local.date() + timedelta(days=1)
        elif wall < time(17, 0):
            trade_day = local.date()
        else:
            continue
        by_day.setdefault(trade_day, []).append(bar)

    result: list[v2.EthDailySession] = []
    for trade_day, sample in sorted(by_day.items()):
        ordered = tuple(sorted(sample, key=lambda item: item.opened_at))
        opened_at, closed_at = v2._eth_bounds(trade_day)
        bounded = tuple(
            item for item in ordered if opened_at <= item.opened_at < closed_at
        )
        if not bounded:
            continue
        result.append(
            v2.EthDailySession(
                trade_day=trade_day,
                opened_at=opened_at,
                closed_at=closed_at,
                high=max(item.high for item in bounded),
                low=min(item.low for item in bounded),
                close=bounded[-1].close,
                bars=bounded,
            )
        )
    return tuple(result)


def _opening_signature_passes(
    bars: tuple[Bar, ...],
    *,
    signature: OpeningSignature,
    lower_octant: Decimal,
    lower_quadrant: Decimal,
) -> bool:
    if signature is OpeningSignature.NONE:
        return True
    count = {
        OpeningSignature.M1: 1,
        OpeningSignature.M2: 2,
        OpeningSignature.M5: 5,
    }[signature]
    if len(bars) < count:
        return False
    sample = bars[:count]
    return (
        max(item.high for item in sample) < lower_quadrant
        and max(item.close for item in sample) < lower_octant
    )


def _nearest_prior_daily_low(
    eth: tuple[v2.EthDailySession, ...],
    *,
    current_day: date,
    current_open: Decimal,
) -> tuple[date, Decimal] | None:
    candidates = [
        item
        for item in eth
        if item.trade_day < current_day and item.low < current_open
    ][-5:]
    if not candidates:
        return None
    selected = max(candidates, key=lambda item: item.low)
    return selected.trade_day, selected.low


def _reference(
    model: ReferenceModel,
    *,
    current: v1.RthSession,
    gap: Decimal,
    pre_macro: tuple[Bar, ...],
    eth: tuple[v2.EthDailySession, ...],
) -> tuple[date, Decimal] | None:
    if model is ReferenceModel.ROLLING_AM_LOW:
        if not pre_macro:
            return None
        return current.ny_day, min(item.low for item in pre_macro)
    if model is ReferenceModel.NEAREST_PRIOR_DAILY_LOW:
        return _nearest_prior_daily_low(
            eth,
            current_day=current.ny_day,
            current_open=current.open,
        )
    return current.ny_day, current.open - Decimal(2) * gap


def _evaluate(
    evidence: Evidence,
    opened: tuple[datetime, ...],
    current: v1.RthSession,
    previous: v1.RthSession,
    eth: tuple[v2.EthDailySession, ...],
    *,
    reference_model: ReferenceModel,
    opening_signature: OpeningSignature,
) -> CapabilityRecord:
    name = variant_name(reference_model, opening_signature)
    gap = previous.settle - current.open
    if gap <= 0:
        return CapabilityRecord(name, current.ny_day, "gap", "not-gap-down", None)

    lower_octant = current.open + gap / Decimal(8)
    lower_quadrant = current.open + gap / Decimal(4)
    early = _window(
        evidence.bars,
        opened,
        current.open_at,
        v1._at_ny(current.ny_day, v1.EARLY_GAP_END),
    )
    if not _opening_signature_passes(
        early,
        signature=opening_signature,
        lower_octant=lower_octant,
        lower_quadrant=lower_quadrant,
    ):
        return CapabilityRecord(
            name,
            current.ny_day,
            "opening-signature",
            "opening-delivery-signature-failed",
            None,
        )

    macro_open = v1._at_ny(current.ny_day, v1.MACRO_FIRST_HALF_OPEN)
    macro_close = v1._at_ny(current.ny_day, v1.MACRO_CLOSE)
    expiry = v1._at_ny(current.ny_day, v1.AM_EXPIRY)
    pre_macro = _window(evidence.bars, opened, current.open_at, macro_open)
    reference = _reference(
        reference_model,
        current=current,
        gap=gap,
        pre_macro=pre_macro,
        eth=eth,
    )
    if reference is None:
        return CapabilityRecord(
            name,
            current.ny_day,
            "reference",
            "reference-unavailable",
            None,
        )
    reference_day, reference_price = reference

    macro = _window(evidence.bars, opened, macro_open, macro_close)
    sweep = next((bar for bar in macro if bar.low < reference_price), None)
    if sweep is None:
        return CapabilityRecord(
            name,
            current.ny_day,
            "sweep",
            "no-macro-penetration",
            None,
        )

    after_sweep = tuple(
        bar for bar in macro if bar.opened_at >= sweep.opened_at
    )
    if any(bar.close <= reference_price for bar in after_sweep):
        return CapabilityRecord(
            name,
            current.ny_day,
            "acceptance",
            "body-accepted-below-reference",
            None,
        )

    ifvg_context = _window(
        evidence.bars,
        opened,
        sweep.opened_at - timedelta(minutes=v1.FVG_LOOKBACK_MINUTES),
        macro_close,
    )
    ifvg = v1._ifvg_entry(
        ifvg_context,
        sweep_at=sweep.opened_at,
        deadline=macro_close,
    )
    if ifvg is None:
        return CapabilityRecord(
            name,
            current.ny_day,
            "ifvg",
            "no-causal-ifvg-entry",
            None,
        )
    _, entry_at, entry = ifvg

    risk_path = _window(
        evidence.bars,
        opened,
        sweep.opened_at,
        entry_at,
    )
    if not risk_path:
        return CapabilityRecord(
            name,
            current.ny_day,
            "geometry",
            "missing-sweep-to-entry-path",
            None,
        )
    sweep_low = min(item.low for item in risk_path)
    stop = sweep_low - v1._tick_size(evidence.digits)
    target = current.open
    if entry <= stop or target <= entry:
        return CapabilityRecord(
            name,
            current.ny_day,
            "geometry",
            "invalid-entry-stop-target",
            None,
        )

    post_entry = _window(evidence.bars, opened, entry_at, expiry)
    if not post_entry:
        return CapabilityRecord(
            name,
            current.ny_day,
            "data",
            "missing-post-entry-path",
            None,
        )
    exit_at, exit_price, exit_reason, gross_r, mfe_r, mae_r = v1._simulate(
        post_entry,
        entry_at=entry_at,
        expiry=expiry,
        entry=entry,
        stop=stop,
        target=target,
    )
    trade = CapabilityTrade(
        variant=name,
        ny_day=current.ny_day,
        reference_model=reference_model.value,
        opening_signature=opening_signature.value,
        reference_day=reference_day,
        reference_price=reference_price,
        gap=gap,
        sweep_at=sweep.opened_at,
        sweep_low=sweep_low,
        entry_at=entry_at,
        entry=entry,
        stop=stop,
        target=target,
        exit_at=exit_at,
        exit_price=exit_price,
        exit_reason=exit_reason,
        gross_r=gross_r,
        primary_net_r=gross_r - PRIMARY_FRICTION_R,
        stress_net_r=gross_r - STRESS_FRICTION_R,
        mfe_r=mfe_r,
        mae_r=mae_r,
    )
    return CapabilityRecord(name, current.ny_day, "trade", "trade", trade)


def replay(
    evidence: Evidence,
    *,
    eval_open_ny: date,
    eval_close_ny: date,
) -> list[CapabilityRecord]:
    sessions = v1.build_rth_sessions(evidence.bars)
    eth = _build_eth_daily_sessions(evidence.bars)
    opened = tuple(item.opened_at for item in evidence.bars)
    records: list[CapabilityRecord] = []
    for index in range(1, len(sessions)):
        current = sessions[index]
        if not eval_open_ny <= current.ny_day < eval_close_ny:
            continue
        for reference_model in ReferenceModel:
            for opening_signature in OpeningSignature:
                records.append(
                    _evaluate(
                        evidence,
                        opened,
                        current,
                        sessions[index - 1],
                        eth,
                        reference_model=reference_model,
                        opening_signature=opening_signature,
                    )
                )
    return records


def _bootstrap_mean_ci(values: list[Decimal]) -> tuple[float | None, float | None]:
    if not values:
        return None, None
    if len(values) == 1:
        value = float(values[0])
        return value, value
    rng = random.Random(BOOTSTRAP_SEED)
    raw = [float(item) for item in values]
    estimates: list[float] = []
    for _ in range(2000):
        estimates.append(mean(rng.choice(raw) for _ in raw))
    estimates.sort()
    return (
        estimates[int(0.025 * (len(estimates) - 1))],
        estimates[int(0.975 * (len(estimates) - 1))],
    )


def _fold(day: date) -> str | None:
    for name, opened, closed in FOLDS:
        if opened <= day < closed:
            return name
    return None


def _metrics(trades: list[CapabilityTrade]) -> dict[str, Any]:
    ordered = sorted(trades, key=lambda item: item.entry_at)
    primary = [item.primary_net_r for item in ordered]
    stress = [item.stress_net_r for item in ordered]
    pf = _profit_factor(primary)
    stress_pf = _profit_factor(stress)
    by_fold: dict[str, dict[str, Any]] = {}
    for fold_name, _, _ in FOLDS:
        fold_values = [
            item.primary_net_r
            for item in ordered
            if _fold(item.ny_day) == fold_name
        ]
        fold_pf = _profit_factor(fold_values)
        by_fold[fold_name] = {
            "trades": len(fold_values),
            "total_r": str(sum(fold_values, Decimal(0))),
            "pf": None if fold_pf is None else str(fold_pf),
        }
    low_ci, high_ci = _bootstrap_mean_ci(primary)
    return {
        "trade_count": len(ordered),
        "wins": sum(value > 0 for value in primary),
        "losses": sum(value < 0 for value in primary),
        "breakeven": sum(value == 0 for value in primary),
        "primary_total_r": str(sum(primary, Decimal(0))),
        "primary_mean_r": (
            None
            if not primary
            else str(sum(primary, Decimal(0)) / Decimal(len(primary)))
        ),
        "primary_pf": None if pf is None else str(pf),
        "primary_max_drawdown_r": str(_max_drawdown(primary)),
        "stress_total_r": str(sum(stress, Decimal(0))),
        "stress_pf": None if stress_pf is None else str(stress_pf),
        "bootstrap_primary_mean_r_95ci": [low_ci, high_ci],
        "mean_mfe_r": (
            None
            if not ordered
            else str(
                sum((item.mfe_r for item in ordered), Decimal(0))
                / Decimal(len(ordered))
            )
        ),
        "mean_mae_r": (
            None
            if not ordered
            else str(
                sum((item.mae_r for item in ordered), Decimal(0))
                / Decimal(len(ordered))
            )
        ),
        "exit_reasons": dict(
            sorted(Counter(item.exit_reason for item in ordered).items())
        ),
        "by_fold": by_fold,
    }


def _adjudicate_primary(metrics: dict[str, Any]) -> dict[str, Any]:
    trades = int(metrics["trade_count"])
    total_r = Decimal(str(metrics["primary_total_r"]))
    max_dd = Decimal(str(metrics["primary_max_drawdown_r"]))
    pf_raw = metrics["primary_pf"]
    pf = None if pf_raw is None else Decimal(str(pf_raw))
    positive_folds = sum(
        Decimal(str(item["total_r"])) > 0
        for item in metrics["by_fold"].values()
    )
    supported = (
        trades >= 8
        and pf is not None
        and pf > Decimal("1.15")
        and total_r > 0
        and max_dd <= Decimal("8")

    )
    if trades < 8:
        label = "INSUFFICIENT_SAMPLE"
    elif supported:
        label = "USTEC_CAPABILITY_SUPPORTED"
    else:
        label = "USTEC_CAPABILITY_NOT_SUPPORTED"
    return {
        "label": label,
        "supported": supported,
        "positive_yearly_folds": positive_folds,
        "requirements": {
            "trade_count_gte": 8,
            "primary_pf_gt": "1.15",
            "primary_total_r_gt": "0",
            "primary_max_drawdown_r_lte": "8",
            "positive_yearly_folds_gte": 1,
        },
    }


def summarize(records: list[CapabilityRecord]) -> dict[str, Any]:
    variants: dict[str, dict[str, Any]] = {}
    for reference_model in ReferenceModel:
        for opening_signature in OpeningSignature:
            name = variant_name(reference_model, opening_signature)
            rows = [item for item in records if item.variant == name]
            trades = [item.trade for item in rows if item.trade is not None]
            variants[name] = {
                **_metrics(trades),
                "stage_funnel": dict(
                    sorted(Counter(item.terminal_stage for item in rows).items())
                ),
                "reason_funnel": dict(
                    sorted(Counter(item.reason for item in rows).items())
                ),
                "promotion_authority": name == PRIMARY_VARIANT,
            }

    primary = variants[PRIMARY_VARIANT]
    return {
        "schema": "qore.nq_am_tlr_v4.ustec_capability.v1",
        "identity": IDENTITY,
        "provider": PROVIDER,
        "provider_symbol": PROVIDER_SYMBOL,
        "instrument_class": INSTRUMENT_CLASS,
        "evaluation_open_ny": EVAL_OPEN_NY.isoformat(),
        "evaluation_close_ny": EVAL_CLOSE_NY.isoformat(),
        "primary_variant": PRIMARY_VARIANT,
        "primary_adjudication": _adjudicate_primary(primary),
        "variants": variants,
        "diagnostic_selection_authority": False,
        "demo_eligible": False,
        "live_authorized": False,
        "real_capital_authorized": False,
        "production_authorized": False,
    }


def collect(output: Path) -> dict[str, Any]:
    evidence = v1._collect_m1(
        PROVIDER_SYMBOL,
        acquisition_open=ACQUISITION_OPEN,
        acquisition_close=ACQUISITION_CLOSE,
    )
    payload = v1.evidence_payload(
        evidence,
        evidence_id=EVIDENCE_ID,
        acquisition_open=ACQUISITION_OPEN,
        acquisition_close=ACQUISITION_CLOSE,
        eval_open_ny=EVAL_OPEN_NY,
        eval_close_ny=EVAL_CLOSE_NY,
        evidence_status="USTEC_CAPABILITY_DISCOVERY_CONSUMED",
    )
    payload["identity"] = IDENTITY
    payload["schema"] = "qore.nq_am_tlr_v4.ustec_evidence.v1"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(payload, separators=(",", ":"), sort_keys=True) + "\n"
    )
    return {
        "identity": IDENTITY,
        "evidence_id": EVIDENCE_ID,
        "bars": len(evidence.bars),
        "first_bar": evidence.bars[0].opened_at.isoformat(),
        "last_bar": evidence.bars[-1].closed_at.isoformat(),
    }


def load_evidence(path: Path) -> tuple[Evidence, dict[str, Any]]:
    payload = json.loads(path.read_text())
    if payload.get("provider_symbol_name") != PROVIDER_SYMBOL:
        raise ValueError("existing holdout is not USTEC")
    if payload.get("read_only") is not True:
        raise ValueError("existing holdout must be read-only")
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
        if ACQUISITION_OPEN
        <= datetime.fromisoformat(str(item["opened_at"])).astimezone(UTC)
        < ACQUISITION_CLOSE
    )
    return Evidence(
        symbol=SYMBOL,
        digits=int(payload["symbol"]["digits"]),
        bars=bars,
    ), payload


def _json_value(value: Any) -> Any:
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, date):
        return value.isoformat()
    return value


def write_study(evidence_path: Path, output: Path) -> dict[str, Any]:
    evidence, payload = load_evidence(evidence_path)
    records = replay(
        evidence,
        eval_open_ny=EVAL_OPEN_NY,
        eval_close_ny=EVAL_CLOSE_NY,
    )
    summary = summarize(records)
    summary["evidence_id"] = EVIDENCE_ID
    summary["evidence_status"] = "EXISTING_CORE_USTEC_HOLDOUT_REUSE"
    summary["source_artifact_id"] = 10402199719
    summary["source_run_id"] = 34981033027
    summary["source_artifact_sha256"] = (
        "9f5df4eba1882cb498b4e3657176f34a7c27083f3ac1af7856ebddf01447f34d"
    )
    output.mkdir(parents=True, exist_ok=True)
    (output / "summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n"
    )
    trades = [item.trade for item in records if item.trade is not None]
    (output / "trades.json").write_text(
        json.dumps(
            [
                {key: _json_value(value) for key, value in asdict(item).items()}
                for item in trades
            ],
            indent=2,
            sort_keys=True,
        )
        + "\n"
    )
    (output / "records.json").write_text(
        json.dumps(
            [
                {
                    "variant": item.variant,
                    "ny_day": item.ny_day.isoformat(),
                    "terminal_stage": item.terminal_stage,
                    "reason": item.reason,
                    "has_trade": item.trade is not None,
                }
                for item in records
            ],
            indent=2,
            sort_keys=True,
        )
        + "\n"
    )
    return summary


def main() -> None:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    collect_parser = sub.add_parser("collect")
    collect_parser.add_argument("output", type=Path)
    study_parser = sub.add_parser("study")
    study_parser.add_argument("evidence", type=Path)
    study_parser.add_argument("output", type=Path)
    args = parser.parse_args()
    if args.command == "collect":
        print(json.dumps(collect(args.output), sort_keys=True))
        return
    if args.command == "study":
        print(json.dumps(write_study(args.evidence, args.output), sort_keys=True))
        return
    raise SystemExit("unknown command")


if __name__ == "__main__":
    main()
