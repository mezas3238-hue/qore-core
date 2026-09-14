"""Hardened single-candidate replay for the frozen VT-08 Index V2 hypothesis.

This module does not reopen the 512-contract ambiguity search. It binds the
single development selection emitted by that consumed-evidence search and fixes
historical exit semantics for M15 gaps before any fresh holdout is opened.
"""

from __future__ import annotations

import argparse
import json
import re
from collections import defaultdict
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from zoneinfo import ZoneInfo

from qore.infrastructure.trader_lab.vt08_index_c2_positional_r1_backtest import (
    ModeledTrade,
    _array,
    _bool,
    _object,
    _parse_m15,
    _text,
    _timestamp,
)
from qore.infrastructure.trader_lab.vt08_index_qore_ambiguity_lab_v1 import (
    ClosurePolicy,
    DailyPolicy,
    LifecyclePolicy,
    Signal,
    StopPolicy,
    SwingPolicy,
    TargetPolicy,
    Variant,
    _adjudicate,
    _signal,
)
from qore.infrastructure.traders.contracts import DemoTradingSetupSide
from qore.infrastructure.traders.vt08_index_c2_positional_r1 import (
    AUTHORIZED_MARKETS,
    OWNER_ENTRY_ANCHORS_NY,
    Vt08IndexC2R1Bar,
)
from qore.kernel.errors import InfrastructureError

SCHEMA = "qore.trader_lab.vt08_index_v2_candidate.v1"
CANDIDATE_ID = "VT08_INDEX_V2_QORE_CANDIDATE_001"
DEVELOPMENT_SELECTION_ID = "V-32e621c9282c"
DEVELOPMENT_SOURCE_RUN_ID = 34789861277
DEVELOPMENT_ARTIFACT_ID = 10327652038
DEVELOPMENT_ARTIFACT_DIGEST = (
    "sha256:4a43aed58fa43374855ad906d26719e955a03e790398feb329132fd0d786b39b"
)
DEFAULT_EVIDENCE_SOFTWARE_SHA = "a5b9c6e0d65539c1f755dda8bb3d7ce7b1a839b0"
PRIMARY_SOURCE_SHA256 = (
    "bfe76fa4346ec4d7442886c21834aa26f0d82172bdb55666e8c77226cdf83271"
)
DEVELOPMENT_START = date(2024, 8, 13)
DEVELOPMENT_END_EXCLUSIVE = date(2026, 9, 12)
_NY = ZoneInfo("America/New_York")

SELECTED_VARIANT = Variant(
    ClosurePolicy.C2_OR_C3_BODY_CLOSE,
    SwingPolicy.FARTHEST_STRUCTURAL,
    StopPolicy.PROTECTED_SWING_EXTREME,
    TargetPolicy.R1_5,
    LifecyclePolicy.NEXT_H4_BOUNDARY,
    DailyPolicy.UNIQUE_ONLY,
)
if SELECTED_VARIANT.variant_id != DEVELOPMENT_SELECTION_ID:
    raise RuntimeError("frozen VT-08 Index candidate identity drifted")


class Vt08IndexV2CandidateError(InfrastructureError):
    __slots__ = ()


def _load_candidate_market(
    path: Path,
    *,
    expected_symbol: str,
    expected_software_sha: str,
    minimum_evidence_days: int,
) -> tuple[str, str, datetime, tuple[Vt08IndexC2R1Bar, ...]]:
    """Load one DEMO M15 dataset without rewriting acquisition provenance."""

    if re.fullmatch(r"[0-9a-f]{40}", expected_software_sha) is None:
        raise Vt08IndexV2CandidateError("expected software SHA must be lowercase git SHA")
    if type(minimum_evidence_days) is not int or minimum_evidence_days < 0:
        raise Vt08IndexV2CandidateError("minimum evidence days must be non-negative int")
    try:
        decoded: object = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise Vt08IndexV2CandidateError("cannot read market evidence") from error
    payload = _object(decoded, name="market evidence")
    if payload.get("schema") != "qore.ctrader_demo.vt08_crt_h4_amd_v2_evidence.v3":
        raise Vt08IndexV2CandidateError("unexpected VT-08 market evidence schema")
    if payload.get("environment") != "demo":
        raise Vt08IndexV2CandidateError("market evidence must be DEMO")
    if not _bool(payload.get("read_only"), name="read_only"):
        raise Vt08IndexV2CandidateError("market evidence must be read-only")
    if _bool(payload.get("account_is_live"), name="account_is_live"):
        raise Vt08IndexV2CandidateError("LIVE evidence is prohibited")
    if expected_symbol not in AUTHORIZED_MARKETS:
        raise Vt08IndexV2CandidateError("market is outside frozen Index scope")
    if _text(payload.get("canonical_symbol"), name="canonical_symbol") != expected_symbol:
        raise Vt08IndexV2CandidateError("canonical symbol mismatch")
    observed_sha = _text(payload.get("software_sha"), name="software_sha")
    if observed_sha != expected_software_sha:
        raise Vt08IndexV2CandidateError("market evidence software SHA drifted")
    source_hash = _text(payload.get("primary_source_sha256"), name="primary_source_sha256")
    if source_hash != PRIMARY_SOURCE_SHA256:
        raise Vt08IndexV2CandidateError("primary source identity drifted")
    provider_symbol = _text(
        payload.get("provider_symbol_name"),
        name="provider_symbol_name",
    )
    fingerprint = _text(
        payload.get("account_fingerprint"),
        name="account_fingerprint",
    )
    if re.fullmatch(r"[0-9a-f]{64}", fingerprint) is None:
        raise Vt08IndexV2CandidateError("account fingerprint must be SHA-256")
    checked_at = _timestamp(payload.get("checked_at"), name="checked_at")
    periods = _object(payload.get("periods"), name="periods")
    if set(periods) != {"M15"}:
        raise Vt08IndexV2CandidateError("candidate accepts M15 evidence only")
    rows = _array(periods.get("M15"), name="periods.M15")
    bars = tuple(_parse_m15(row) for row in rows)
    if not bars:
        raise Vt08IndexV2CandidateError("M15 evidence is empty")
    if bars != tuple(sorted(bars, key=lambda item: item.opened_at)):
        raise Vt08IndexV2CandidateError("M15 evidence must be chronological")
    if len({item.opened_at for item in bars}) != len(bars):
        raise Vt08IndexV2CandidateError("M15 evidence contains duplicate opens")
    if bars[-1].closed_at - bars[0].opened_at < timedelta(days=minimum_evidence_days):
        raise Vt08IndexV2CandidateError("M15 evidence is shorter than frozen minimum")
    return fingerprint, provider_symbol, checked_at, bars


def _gap_exit(
    *,
    side: DemoTradingSetupSide,
    bar: Vt08IndexC2R1Bar,
    stop: Decimal,
    target: Decimal,
) -> tuple[Decimal, str] | None:
    """Resolve an opening gap before intrabar touch semantics."""

    if side is DemoTradingSetupSide.LONG:
        if bar.open <= stop:
            return bar.open, "stop-gap"
        if bar.open >= target:
            return target, "target-gap"
    else:
        if bar.open >= stop:
            return bar.open, "stop-gap"
        if bar.open <= target:
            return target, "target-gap"
    return None


def _intrabar_exit(
    *,
    bar: Vt08IndexC2R1Bar,
    stop: Decimal,
    target: Decimal,
) -> tuple[Decimal, str] | None:
    """Apply the frozen conservative same-M15-bar STOP-first ordering."""

    if bar.low <= stop <= bar.high:
        return stop, "stop"
    if bar.low <= target <= bar.high:
        return target, "target"
    return None


def _model_hardened(
    signal: Signal,
    *,
    bars_by_open: dict[datetime, Vt08IndexC2R1Bar],
) -> ModeledTrade | None:
    entry_bar = bars_by_open.get(signal.decision_at.astimezone(UTC))
    if entry_bar is None:
        return None

    entry = entry_bar.open
    stop = signal.protected_swing.price
    risk = entry - stop if signal.side is DemoTradingSetupSide.LONG else stop - entry
    if risk <= 0:
        return None
    target = (
        entry + SELECTED_VARIANT.target.multiple * risk
        if signal.side is DemoTradingSetupSide.LONG
        else entry - SELECTED_VARIANT.target.multiple * risk
    )
    if target <= 0:
        return None

    retained: list[Vt08IndexC2R1Bar] = []
    cursor = signal.decision_at.astimezone(UTC)
    for _ in range(SELECTED_VARIANT.lifecycle.m15_bars):
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


def _in_partition(
    decision_at: datetime,
    *,
    start_date: date | None,
    end_date_exclusive: date | None,
) -> bool:
    day = decision_at.astimezone(_NY).date()
    if start_date is not None and day < start_date:
        return False
    if end_date_exclusive is not None and day >= end_date_exclusive:
        return False
    return True


def _market_trades(
    *,
    symbol: str,
    indexed: dict[datetime, Vt08IndexC2R1Bar],
    start_date: date | None,
    end_date_exclusive: date | None,
) -> tuple[ModeledTrade, ...]:
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
                closure=SELECTED_VARIANT.closure,
                swing=SELECTED_VARIANT.swing,
            )
        )
        is not None
    )
    by_day: dict[date, list[Signal]] = defaultdict(list)
    for signal in signals:
        by_day[signal.decision_at.astimezone(_NY).date()].append(signal)

    trades: list[ModeledTrade] = []
    for day in sorted(by_day):
        day_signals = sorted(by_day[day], key=lambda item: item.decision_at)
        if len(day_signals) != 1:
            continue
        modeled = _model_hardened(day_signals[0], bars_by_open=indexed)
        if modeled is None:
            continue
        if end_date_exclusive is not None and (
            modeled.exited_at.astimezone(_NY).date() >= end_date_exclusive
        ):
            continue
        trades.append(modeled)
    return tuple(trades)


def build_candidate_report(
    *,
    nas100: Path,
    sp500: Path,
    us30: Path,
    start_date: date | None = None,
    end_date_exclusive: date | None = None,
    expected_software_sha: str = DEFAULT_EVIDENCE_SOFTWARE_SHA,
    minimum_evidence_days: int = 730,
) -> dict[str, object]:
    paths = {"NAS100": nas100, "SP500": sp500, "US30": us30}
    all_trades: list[ModeledTrade] = []
    provenance: dict[str, object] = {}
    for symbol, path in paths.items():
        fingerprint, provider, checked_at, bars = _load_candidate_market(
            path,
            expected_symbol=symbol,
            expected_software_sha=expected_software_sha,
            minimum_evidence_days=minimum_evidence_days,
        )
        indexed = {item.opened_at.astimezone(UTC): item for item in bars}
        market_trades = _market_trades(
            symbol=symbol,
            indexed=indexed,
            start_date=start_date,
            end_date_exclusive=end_date_exclusive,
        )
        all_trades.extend(market_trades)
        provenance[symbol] = {
            "provider_symbol": provider,
            "account_fingerprint": fingerprint,
            "checked_at": checked_at.isoformat(),
            "software_sha": expected_software_sha,
            "m15_bars": len(bars),
            "trade_count": len(market_trades),
        }

    ordered = tuple(sorted(all_trades, key=lambda item: (item.signal_at, item.symbol)))
    adjudication = _adjudicate(ordered)
    return {
        "schema": SCHEMA,
        "candidate_id": CANDIDATE_ID,
        "development_selection_id": DEVELOPMENT_SELECTION_ID,
        "variant": SELECTED_VARIANT.payload(),
        "evidence_contract": {
            "expected_software_sha": expected_software_sha,
            "minimum_evidence_days": minimum_evidence_days,
            "primary_source_sha256": PRIMARY_SOURCE_SHA256,
        },
        "partition": {
            "start_date": start_date.isoformat() if start_date is not None else None,
            "end_date_exclusive": (
                end_date_exclusive.isoformat() if end_date_exclusive is not None else None
            ),
        },
        "provenance": provenance,
        "adjudication": adjudication,
        "gap_exit_count": sum(item.exit_reason.endswith("-gap") for item in ordered),
        "trades": [item.payload() for item in ordered],
        "governance": {
            "research_only": True,
            "development_selection_reopened": False,
            "fresh_holdout_opened": False,
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
    parser.add_argument(
        "--expected-software-sha",
        default=DEFAULT_EVIDENCE_SOFTWARE_SHA,
    )
    parser.add_argument("--minimum-evidence-days", type=int, default=730)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    report = build_candidate_report(
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
        json.dumps(report, sort_keys=True, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )
    adjudication = report["adjudication"]
    if not isinstance(adjudication, dict):
        raise Vt08IndexV2CandidateError("candidate adjudication must be an object")
    metric_values = adjudication.get("metrics")
    if not isinstance(metric_values, dict):
        raise Vt08IndexV2CandidateError("candidate metrics must be an object")
    print(
        json.dumps(
            {
                "candidate_id": CANDIDATE_ID,
                "selection": DEVELOPMENT_SELECTION_ID,
                "sample": metric_values.get("sample"),
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
