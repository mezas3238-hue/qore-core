"""VT-08 Index V3 geometry-gated research candidate.

V3 is a new QORE research identity created after the V2 one-shot fresh holdout
was consumed and rejected.  It does not rewrite that decision.  The V3
admission gate is an empirical QORE containment discovered on consumed evidence,
not a claim that TTrades teaches numerical geometry thresholds.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from hashlib import sha256
from pathlib import Path
from zoneinfo import ZoneInfo

from qore.infrastructure.trader_lab.vt08_index_c2_positional_r1_backtest import ModeledTrade
from qore.infrastructure.trader_lab.vt08_index_qore_ambiguity_lab_v1 import (
    ClosurePolicy,
    Signal,
    SwingPolicy,
    _mean,
    _metrics,
    _signal,
)
from qore.infrastructure.trader_lab.vt08_index_v2_candidate import (
    _gap_exit,
    _in_partition,
    _intrabar_exit,
    _load_candidate_market,
)
from qore.infrastructure.traders.contracts import DemoTradingSetupSide
from qore.infrastructure.traders.vt08_index_c2_positional_r1 import (
    AUTHORIZED_MARKETS,
    OWNER_ENTRY_ANCHORS_NY,
    Vt08IndexC2R1Bar,
    _aggregate_contiguous_m15,
)
from qore.kernel.errors import InfrastructureError

SCHEMA = "qore.trader_lab.vt08_index_v3_geometry_candidate.v1"
CANDIDATE_ID = "VT08_INDEX_V3_QORE_GEOMETRY_001"
PARENT_REJECTED_CANDIDATE_ID = "VT08_INDEX_V2_QORE_CANDIDATE_001"
PARENT_REJECTED_RUN_ID = 34795405536
PARENT_REJECTED_ARTIFACT_ID = 10329479540
PARENT_REJECTED_ARTIFACT_DIGEST = (
    "sha256:6e52693c4231b9d2bc65ead4f57d95c08ab442751b185649108d970fcba2dcd5"
)
PRIMARY_SOURCE_SHA256 = (
    "bfe76fa4346ec4d7442886c21834aa26f0d82172bdb55666e8c77226cdf83271"
)
MIN_PROTECTED_SWING_RISK_FRACTION = Decimal("0.003")
MIN_CLOSURE_REFERENCE_RANGE_RATIO = Decimal("1.2")
TARGET_R_MULTIPLE = Decimal("2.5")
LIFECYCLE_M15_BARS = 16
STRESS_COST_R = Decimal("0.05")
_NY = ZoneInfo("America/New_York")

_RULE_MATERIAL = {
    "candidate_id": CANDIDATE_ID,
    "closure": ClosurePolicy.C2_OR_C3_BODY_CLOSE,
    "swing": SwingPolicy.FARTHEST_STRUCTURAL,
    "stop": "protected-swing-extreme",
    "minimum_protected_swing_risk_fraction": str(MIN_PROTECTED_SWING_RISK_FRACTION),
    "minimum_closure_reference_range_ratio": str(MIN_CLOSURE_REFERENCE_RANGE_RATIO),
    "target_r_multiple": str(TARGET_R_MULTIPLE),
    "lifecycle_m15_bars": LIFECYCLE_M15_BARS,
    "daily_policy": "unique-raw-signal-only",
    "markets": AUTHORIZED_MARKETS,
    "anchors_new_york": OWNER_ENTRY_ANCHORS_NY,
}
RULE_FINGERPRINT = sha256(
    json.dumps(
        _RULE_MATERIAL,
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
).hexdigest()


class Vt08IndexV3GeometryError(InfrastructureError):
    __slots__ = ()


def _geometry(
    signal: Signal,
    *,
    bars_by_open: dict[datetime, Vt08IndexC2R1Bar],
) -> dict[str, Decimal] | None:
    entry_bar = bars_by_open.get(signal.decision_at.astimezone(UTC))
    if entry_bar is None:
        return None
    entry = entry_bar.open
    stop = signal.protected_swing.price
    risk = entry - stop if signal.side is DemoTradingSetupSide.LONG else stop - entry
    if risk <= 0:
        return None

    local = signal.decision_at.astimezone(_NY)
    reference_offset = 8 if signal.closure_kind == "c2" else 12
    reference = _aggregate_contiguous_m15(
        bars_by_open,
        opened_at_local=local - timedelta(hours=reference_offset),
        count=16,
    )
    closure = _aggregate_contiguous_m15(
        bars_by_open,
        opened_at_local=local - timedelta(hours=4),
        count=16,
    )
    if reference is None or closure is None:
        return None
    reference_range = reference.high - reference.low
    closure_range = closure.high - closure.low
    if reference_range <= 0 or closure_range <= 0:
        return None

    return {
        "entry": entry,
        "risk": risk,
        "risk_fraction": risk / entry,
        "reference_range": reference_range,
        "closure_range": closure_range,
        "closure_reference_range_ratio": closure_range / reference_range,
    }


def _geometry_accepts(geometry: dict[str, Decimal]) -> bool:
    return (
        geometry["risk_fraction"] >= MIN_PROTECTED_SWING_RISK_FRACTION
        and geometry["closure_reference_range_ratio"]
        >= MIN_CLOSURE_REFERENCE_RANGE_RATIO
    )


def _model_v3(
    signal: Signal,
    *,
    bars_by_open: dict[datetime, Vt08IndexC2R1Bar],
) -> ModeledTrade | None:
    geometry = _geometry(signal, bars_by_open=bars_by_open)
    if geometry is None or not _geometry_accepts(geometry):
        return None
    entry = geometry["entry"]
    risk = geometry["risk"]
    stop = signal.protected_swing.price
    target = (
        entry + TARGET_R_MULTIPLE * risk
        if signal.side is DemoTradingSetupSide.LONG
        else entry - TARGET_R_MULTIPLE * risk
    )
    if target <= 0:
        return None

    retained: list[Vt08IndexC2R1Bar] = []
    cursor = signal.decision_at.astimezone(UTC)
    for _ in range(LIFECYCLE_M15_BARS):
        bar = bars_by_open.get(cursor)
        if bar is None:
            return None
        retained.append(bar)
        cursor = bar.closed_at.astimezone(UTC)

    exit_price = retained[-1].close
    exited_at = retained[-1].closed_at
    reason = "lifecycle"
    for bar in retained:
        resolved = _gap_exit(
            side=signal.side,
            bar=bar,
            stop=stop,
            target=target,
        )
        if resolved is None:
            resolved = _intrabar_exit(bar=bar, stop=stop, target=target)
        if resolved is not None:
            exit_price, reason = resolved
            exited_at = bar.closed_at
            break

    pnl = exit_price - entry if signal.side is DemoTradingSetupSide.LONG else entry - exit_price
    return ModeledTrade(
        symbol=signal.symbol,
        signal_at=signal.decision_at,
        exited_at=exited_at,
        anchor_hour_ny=signal.anchor,
        side=signal.side,
        entry=entry,
        stop=stop,
        target=target,
        exit_price=exit_price,
        exit_reason=reason,
        r_multiple=pnl / risk,
        return_rate=pnl / entry,
    )


def _market_trades(
    *,
    symbol: str,
    indexed: dict[datetime, Vt08IndexC2R1Bar],
    start_date: date | None,
    end_date_exclusive: date | None,
) -> tuple[tuple[ModeledTrade, ...], dict[str, int]]:
    decisions = tuple(
        opened
        for opened in indexed
        if opened.astimezone(_NY).minute == 0
        and opened.astimezone(_NY).hour in OWNER_ENTRY_ANCHORS_NY
        and _in_partition(
            opened,
            start_date=start_date,
            end_date_exclusive=end_date_exclusive,
        )
    )
    signals = tuple(
        signal
        for decision in decisions
        if (
            signal := _signal(
                symbol=symbol,
                bars_by_open=indexed,
                decision_at=decision,
                closure=ClosurePolicy.C2_OR_C3_BODY_CLOSE,
                swing=SwingPolicy.FARTHEST_STRUCTURAL,
            )
        )
        is not None
    )
    by_day: dict[date, list[Signal]] = defaultdict(list)
    for signal in signals:
        by_day[signal.decision_at.astimezone(_NY).date()].append(signal)

    diagnostics = Counter(
        {
            "decisions": len(decisions),
            "raw_signals": len(signals),
            "ambiguous_signal_days": 0,
            "geometry_rejected": 0,
            "modeled": 0,
        }
    )
    trades: list[ModeledTrade] = []
    for day in sorted(by_day):
        day_signals = sorted(by_day[day], key=lambda item: item.decision_at)
        if len(day_signals) != 1:
            diagnostics["ambiguous_signal_days"] += 1
            continue
        signal = day_signals[0]
        geometry = _geometry(signal, bars_by_open=indexed)
        if geometry is None or not _geometry_accepts(geometry):
            diagnostics["geometry_rejected"] += 1
            continue
        modeled = _model_v3(signal, bars_by_open=indexed)
        if modeled is None:
            continue
        if end_date_exclusive is not None and (
            modeled.exited_at.astimezone(_NY).date() >= end_date_exclusive
        ):
            continue
        trades.append(modeled)
        diagnostics["modeled"] += 1
    return tuple(trades), dict(diagnostics)


def _breakdown(
    ordered: tuple[ModeledTrade, ...],
    *,
    attribute: str,
) -> dict[str, dict[str, object]]:
    values = sorted({getattr(item, attribute) for item in ordered}, key=str)
    return {
        str(value): _metrics(tuple(item for item in ordered if getattr(item, attribute) == value))
        for value in values
    }


def build_v3_candidate_report(
    *,
    nas100: Path,
    sp500: Path,
    us30: Path,
    start_date: date | None = None,
    end_date_exclusive: date | None = None,
    expected_software_sha: str,
    minimum_evidence_days: int,
) -> dict[str, object]:
    paths = {"NAS100": nas100, "SP500": sp500, "US30": us30}
    all_trades: list[ModeledTrade] = []
    provenance: dict[str, object] = {}
    diagnostics: dict[str, object] = {}
    for symbol, path in paths.items():
        fingerprint, provider, checked_at, bars = _load_candidate_market(
            path,
            expected_symbol=symbol,
            expected_software_sha=expected_software_sha,
            minimum_evidence_days=minimum_evidence_days,
        )
        indexed = {item.opened_at.astimezone(UTC): item for item in bars}
        market_trades, market_diagnostics = _market_trades(
            symbol=symbol,
            indexed=indexed,
            start_date=start_date,
            end_date_exclusive=end_date_exclusive,
        )
        all_trades.extend(market_trades)
        diagnostics[symbol] = market_diagnostics
        provenance[symbol] = {
            "provider_symbol": provider,
            "account_fingerprint": fingerprint,
            "checked_at": checked_at.isoformat(),
            "software_sha": expected_software_sha,
            "m15_bars": len(bars),
            "trade_count": len(market_trades),
        }

    ordered = tuple(sorted(all_trades, key=lambda item: (item.signal_at, item.symbol)))
    n = len(ordered)
    quartiles = tuple(ordered[(n * i) // 4 : (n * (i + 1)) // 4] for i in range(4))
    return {
        "schema": SCHEMA,
        "candidate_id": CANDIDATE_ID,
        "rule_fingerprint": RULE_FINGERPRINT,
        "parent_rejected_candidate": {
            "candidate_id": PARENT_REJECTED_CANDIDATE_ID,
            "run_id": PARENT_REJECTED_RUN_ID,
            "artifact_id": PARENT_REJECTED_ARTIFACT_ID,
            "artifact_digest": PARENT_REJECTED_ARTIFACT_DIGEST,
        },
        "rules": {
            **_RULE_MATERIAL,
            "source_status": {
                "closure_swing_stop_lifecycle": "source-derived-or-prior-frozen",
                "numeric_geometry_gate": "qore-empirical-research-containment",
                "fixed_2_5r_target": "qore-empirical-research-containment",
                "not_a_universal_ttrades_rule": True,
            },
        },
        "partition": {
            "start_date": start_date.isoformat() if start_date is not None else None,
            "end_date_exclusive": (
                end_date_exclusive.isoformat() if end_date_exclusive is not None else None
            ),
        },
        "evidence_contract": {
            "expected_software_sha": expected_software_sha,
            "minimum_evidence_days": minimum_evidence_days,
            "primary_source_sha256": PRIMARY_SOURCE_SHA256,
        },
        "provenance": provenance,
        "diagnostics": diagnostics,
        "metrics": _metrics(ordered),
        "quartile_mean_r": [str(_mean(part)) for part in quartiles],
        "second_half_mean_r": str(_mean(ordered[n // 2 :])),
        "by_market": _breakdown(ordered, attribute="symbol"),
        "by_anchor": _breakdown(ordered, attribute="anchor_hour_ny"),
        "by_side": _breakdown(ordered, attribute="side"),
        "gap_exit_count": sum(item.exit_reason.endswith("-gap") for item in ordered),
        "trades": [item.payload() for item in ordered],
        "governance": {
            "research_only": True,
            "v2_rejection_reopened": False,
            "consumed_research_allowed": True,
            "fresh_validation_required": True,
            "demo_eligible": False,
            "live_authorized": False,
            "production_authorized": False,
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--nas100", type=Path, required=True)
    parser.add_argument("--sp500", type=Path, required=True)
    parser.add_argument("--us30", type=Path, required=True)
    parser.add_argument("--start-date", type=date.fromisoformat)
    parser.add_argument("--end-date-exclusive", type=date.fromisoformat)
    parser.add_argument("--expected-software-sha", required=True)
    parser.add_argument("--minimum-evidence-days", type=int, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    report = build_v3_candidate_report(
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
        json.dumps(
            report,
            ensure_ascii=True,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )
        + "\n",
        encoding="utf-8",
    )
    metrics = report["metrics"]
    assert isinstance(metrics, dict)
    print(
        json.dumps(
            {
                "candidate_id": report["candidate_id"],
                "sample": metrics["sample"],
                "rule_fingerprint": report["rule_fingerprint"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
