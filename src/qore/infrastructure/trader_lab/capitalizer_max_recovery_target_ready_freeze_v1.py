"""Target-ready freeze for the final recovered Capitalizer universe.

This adapter MUST NOT change trade selection. It consumes the frozen
MAX_RECOVERY_FINAL ledger and attaches the entry/stop geometry that already
belonged to each selected trade so later target experiments can vary only the
target.

No target optimization or outcome-based admission happens here.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any

from qore.infrastructure.trader_lab import (
    capitalizer_owner_h1_m3_m1_causal_reversal_1y_v3 as v3,
)
from qore.infrastructure.trader_lab import (
    capitalizer_v3_source_first_wait5_protected_swing_rescue_2y_v1 as protected_rescue,
)
from qore.infrastructure.trader_lab.capitalizer_cibo_m1_reader_v1 import (
    CapitalizerM1Bar,
    iter_cibo_m1,
)
from qore.infrastructure.trader_lab.capitalizer_contract import CapitalizerSession
from qore.infrastructure.trader_lab.capitalizer_exposure_graph import CapitalizerSide
from qore.infrastructure.trader_lab.capitalizer_m3_mss_bottleneck_forensics_2y_v1 import (
    LOOKBACK_START,
    WINDOW_END,
)
from qore.infrastructure.trader_lab.capitalizer_max_recovery_final_2y_v1 import (
    _load_rearm_rows,
)
from qore.infrastructure.trader_lab.capitalizer_max_recovery_v2 import RecoveryTrade
from qore.infrastructure.trader_lab.capitalizer_strict_htf_gate_1y_v1 import (
    TFBar,
    _aggregate_tf,
    _index_day_inputs,
    _pivots,
)
from qore.infrastructure.trader_lab.capitalizer_v3_source_first_cisd_v1 import (
    find_source_first_m3_mss,
)

IDENTITY = "QORE_CAPITALIZER_MAX_RECOVERY_TARGET_READY_FREEZE_V1"
MATRIX_IDENTITY = (
    "QORE_CAPITALIZER_NINE_MARKET_MAX_RECOVERY_TARGET_READY_FREEZE_V1"
)
WAIT_MINUTES = 5


@dataclass(frozen=True, slots=True)
class TargetReadyTrade:
    symbol: str
    session: str
    operating_date: str
    side: str
    h1_open: str
    h1_deadline: str
    entry_at: str
    entry_price: str
    stop_price: str
    risk_price: str
    baseline_target_price: str
    baseline_target_r: str
    provenance: str


def _key(
    *,
    provenance: str,
    operating_date: str,
    h1_open: str,
    entry_at: str,
    side: str,
) -> tuple[str, str, str, str, str]:
    return (provenance, operating_date, h1_open, entry_at, side)


def _load_final(root: Path) -> tuple[RecoveryTrade, ...]:
    paths = sorted(
        root.rglob("capitalizer-*-max-recovery-final-2y-v1-trades.jsonl")
    )
    if len(paths) != 1:
        raise ValueError("target-ready freeze requires one final recovery ledger")
    rows: list[RecoveryTrade] = []
    with paths[0].open(encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                rows.append(RecoveryTrade(**json.loads(line)))
    return tuple(rows)


def _arbitration_details(
    root: Path,
) -> dict[tuple[str, str, str, str, str], TargetReadyTrade]:
    paths = sorted(
        root.rglob(
            "capitalizer-*-v3-source-first-no-rearm-"
            "closeback-arbitration-2y-v1-trades.jsonl"
        )
    )
    if len(paths) != 1:
        raise ValueError("target-ready freeze requires one arbitration ledger")
    result: dict[tuple[str, str, str, str, str], TargetReadyTrade] = {}
    with paths[0].open(encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            raw = json.loads(line)
            entry = Decimal(str(raw["entry_price"]))
            stop = Decimal(str(raw["stop_price"]))
            risk = abs(entry - stop)
            target = (
                entry + Decimal("2") * risk
                if str(raw["side"]) == "LONG"
                else entry - Decimal("2") * risk
            )
            trade = TargetReadyTrade(
                symbol=str(raw["symbol"]),
                session=str(raw["session"]),
                operating_date=str(raw["operating_date"]),
                side=str(raw["side"]),
                h1_open=str(raw["h1_open"]),
                h1_deadline=str(raw["h1_deadline"]),
                entry_at=str(raw["entry_at"]),
                entry_price=str(entry),
                stop_price=str(stop),
                risk_price=str(risk),
                baseline_target_price=str(target),
                baseline_target_r="2",
                provenance="CAUSAL_ARBITRATION_BASE",
            )
            result[
                _key(
                    provenance=trade.provenance,
                    operating_date=trade.operating_date,
                    h1_open=trade.h1_open,
                    entry_at=trade.entry_at,
                    side=trade.side,
                )
            ] = trade
    return result


def _protected_details(
    *,
    stop_root: Path,
    funnel_root: Path,
    execution_by_day: dict[str, tuple[CapitalizerM1Bar, ...]],
) -> dict[tuple[str, str, str, str, str], TargetReadyTrade]:
    stop_rows = protected_rescue._stop_rows(stop_root)
    funnel_rows = protected_rescue._funnel_rows(funnel_root)
    funnel_by_key = {
        protected_rescue._funnel_key(row): row for row in funnel_rows
    }
    result: dict[tuple[str, str, str, str, str], TargetReadyTrade] = {}

    for row in stop_rows:
        if row.get("protected_at_mss_stop_valid") is not True:
            continue
        protected_raw = row.get("protected_at_mss_stop_price")
        if protected_raw is None:
            continue
        funnel = funnel_by_key.get(protected_rescue._stop_key(row))
        if funnel is None:
            raise ValueError("target-ready protected row missing funnel")

        day = str(row["operating_date"])
        execution = execution_by_day.get(day, ())
        entry_at = datetime.fromisoformat(str(row["final_fill_at"]))
        mss_at = datetime.fromisoformat(str(row["source_first_mss_at"]))
        deadline = datetime.fromisoformat(str(funnel["h1_deadline"]))
        side = str(row["side"])
        entry = Decimal(str(row["entry_price"]))
        stop = Decimal(str(protected_raw))

        prefill = tuple(
            bar for bar in execution if mss_at <= bar.opened_at < entry_at
        )
        if any(
            protected_rescue._stop_hit(bar, side=side, stop_price=stop)
            for bar in prefill
        ):
            continue

        risk = abs(entry - stop)
        target = (
            entry + Decimal("2") * risk
            if side == "LONG"
            else entry - Decimal("2") * risk
        )
        trade = TargetReadyTrade(
            symbol=str(row["symbol"]),
            session=str(row["session"]),
            operating_date=day,
            side=side,
            h1_open=(deadline - timedelta(hours=1)).isoformat(),
            h1_deadline=deadline.isoformat(),
            entry_at=entry_at.isoformat(),
            entry_price=str(entry),
            stop_price=str(stop),
            risk_price=str(risk),
            baseline_target_price=str(target),
            baseline_target_r="2",
            provenance="PROTECTED_SWING_GEOMETRY_RESCUE",
        )
        result[
            _key(
                provenance=trade.provenance,
                operating_date=trade.operating_date,
                h1_open=trade.h1_open,
                entry_at=trade.entry_at,
                side=trade.side,
            )
        ] = trade
    return result


def _rearm_details(
    *,
    rearm_root: Path,
    bars: tuple[CapitalizerM1Bar, ...],
    session: CapitalizerSession,
    execution_by_day: dict[str, tuple[CapitalizerM1Bar, ...]],
) -> dict[tuple[str, str, str, str, str], TargetReadyTrade]:
    rearm_rows = _load_rearm_rows(rearm_root)
    m3: tuple[TFBar, ...] = _aggregate_tf(bars, minutes=3)
    m3_closes = tuple(item.closed_at for item in m3)
    m3_pivots = _pivots(m3)
    buffer_price = v3._stop_buffer(bars)
    result: dict[tuple[str, str, str, str, str], TargetReadyTrade] = {}

    for raw in rearm_rows:
        day = str(raw["operating_date"])
        execution = execution_by_day.get(day, ())
        if not execution:
            raise ValueError("target-ready rearm missing execution day")

        raid_raw = raw.get("new_raid_at")
        closeback_raw = raw.get("new_closeback_at")
        mss_raw = raw.get("new_mss_at")
        fill_raw = raw.get("new_fill_at")
        if not all(
            isinstance(value, str)
            for value in (raid_raw, closeback_raw, mss_raw, fill_raw)
        ):
            raise ValueError("target-ready executable rearm ledger incomplete")

        raid_at = datetime.fromisoformat(raid_raw)
        closeback_at = datetime.fromisoformat(closeback_raw)
        expected_mss_at = datetime.fromisoformat(mss_raw)
        expected_fill_at = datetime.fromisoformat(fill_raw)
        deadline = datetime.fromisoformat(str(raw["h1_deadline"]))
        side = CapitalizerSide(str(raw["side"]))

        mss = find_source_first_m3_mss(
            m3,
            m3_closes,
            m3_pivots,
            sweep_at=raid_at,
            after=closeback_at,
            before=deadline,
            side=side,
        )
        if mss is None or mss.confirmed_at != expected_mss_at:
            raise ValueError("target-ready rearm MSS mismatch")

        zone = v3._m1_causal_zone(execution, event=mss)
        if zone is None:
            raise ValueError("target-ready rearm FVG mismatch")
        fill = v3._find_m1_fill(
            execution,
            event=mss,
            zone=zone,
            deadline=deadline,
        )
        if fill is None:
            raise ValueError("target-ready rearm fill mismatch")
        entry_index, entry, _ = fill
        entry_at = execution[entry_index].opened_at
        if entry_at != expected_fill_at:
            raise ValueError("target-ready rearm timestamp mismatch")

        stop = (
            mss.broken_swing_price - buffer_price
            if side is CapitalizerSide.LONG
            else mss.broken_swing_price + buffer_price
        )
        valid = (
            stop < entry if side is CapitalizerSide.LONG else stop > entry
        )
        if not valid:
            raise ValueError("target-ready rearm stop mismatch")

        risk = abs(entry - stop)
        target = (
            entry + Decimal("2") * risk
            if side is CapitalizerSide.LONG
            else entry - Decimal("2") * risk
        )
        trade = TargetReadyTrade(
            symbol=str(raw["symbol"]),
            session=str(raw["session"]),
            operating_date=day,
            side=side.value,
            h1_open=(deadline - timedelta(hours=1)).isoformat(),
            h1_deadline=deadline.isoformat(),
            entry_at=entry_at.isoformat(),
            entry_price=str(entry),
            stop_price=str(stop),
            risk_price=str(risk),
            baseline_target_price=str(target),
            baseline_target_r="2",
            provenance="WAIT_REJECTED_PARALLEL_REARM",
        )
        result[
            _key(
                provenance=trade.provenance,
                operating_date=trade.operating_date,
                h1_open=trade.h1_open,
                entry_at=trade.entry_at,
                side=trade.side,
            )
        ] = trade
    return result

def build_market_report(
    final_root: Path,
    arbitration_root: Path,
    stop_root: Path,
    funnel_root: Path,
    rearm_root: Path,
    m1_root: Path,
    *,
    session: CapitalizerSession,
) -> tuple[dict[str, Any], tuple[TargetReadyTrade, ...]]:
    frozen = _load_final(final_root)
    bars = tuple(
        bar
        for bar in iter_cibo_m1(m1_root)
        if LOOKBACK_START <= bar.opened_at < WINDOW_END + timedelta(days=1)
    )
    if not bars:
        raise ValueError("target-ready freeze requires native M1")
    symbol = bars[0].symbol
    execution_by_day, _ = _index_day_inputs(bars, session=session)

    details: dict[tuple[str, str, str, str, str], TargetReadyTrade] = {}
    for source in (
        _arbitration_details(arbitration_root),
        _protected_details(
            stop_root=stop_root,
            funnel_root=funnel_root,
            execution_by_day=execution_by_day,
        ),
        _rearm_details(
            rearm_root=rearm_root,
            bars=bars,
            session=session,
            execution_by_day=execution_by_day,
        ),
    ):
        for key, detail_trade in source.items():
            if key in details:
                raise ValueError("target-ready geometry key collision")
            details[key] = detail_trade

    selected: list[TargetReadyTrade] = []
    for frozen_trade in frozen:
        if frozen_trade.symbol != symbol:
            raise ValueError("target-ready final/M1 symbol mismatch")
        key = _key(
            provenance=frozen_trade.provenance,
            operating_date=frozen_trade.operating_date,
            h1_open=frozen_trade.h1_open,
            entry_at=frozen_trade.entry_at,
            side=frozen_trade.side,
        )
        detail = details.get(key)
        if detail is None:
            raise ValueError("target-ready geometry missing for selected trade")
        selected.append(detail)

    ordered = tuple(
        sorted(
            selected,
            key=lambda item: (
                datetime.fromisoformat(item.entry_at),
                item.symbol,
            ),
        )
    )
    return {
        "identity": IDENTITY,
        "symbol": symbol,
        "session": session.value,
        "final_recovery_trades": len(frozen),
        "target_ready_trades": len(ordered),
        "selection_changed": False,
        "entry_changed": False,
        "stop_changed": False,
        "target_changed": False,
        "baseline_target_r": "2",
        "recovery_phase_closed": True,
        "target_phase_ready": True,
        "outcome_used_for_admission": False,
        "live_authorized": False,
        "real_capital_authorized": False,
    }, ordered


def write_market(
    report: dict[str, Any],
    trades: tuple[TargetReadyTrade, ...],
    output: Path,
) -> None:
    output.mkdir(parents=True, exist_ok=True)
    symbol = str(report["symbol"]).lower()
    stem = f"capitalizer-{symbol}-max-recovery-target-ready-freeze-v1"
    (output / f"{stem}.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    with (output / f"{stem}-trades.jsonl").open("w", encoding="utf-8") as handle:
        for trade in trades:
            handle.write(json.dumps(asdict(trade), sort_keys=True) + "\n")


def build_matrix(root: Path) -> dict[str, Any]:
    reports = sorted(
        root.rglob(
            "capitalizer-*-max-recovery-target-ready-freeze-v1.json"
        )
    )
    if len(reports) != 9:
        raise ValueError(f"target-ready matrix requires 9 reports, got {len(reports)}")
    payloads = [
        dict(json.loads(path.read_text(encoding="utf-8"))) for path in reports
    ]
    return {
        "identity": MATRIX_IDENTITY,
        "market_count": 9,
        "final_recovery_trades": sum(
            int(item["final_recovery_trades"]) for item in payloads
        ),
        "target_ready_trades": sum(
            int(item["target_ready_trades"]) for item in payloads
        ),
        "counts_match": all(
            int(item["final_recovery_trades"]) == int(item["target_ready_trades"])
            for item in payloads
        ),
        "selection_changed": False,
        "entry_changed": False,
        "stop_changed": False,
        "target_changed": False,
        "baseline_target_r": "2",
        "recovery_phase_closed": True,
        "target_phase_ready": True,
        "outcome_used_for_admission": False,
        "live_authorized": False,
        "real_capital_authorized": False,
    }


def write_matrix(report: dict[str, Any], output: Path) -> None:
    output.mkdir(parents=True, exist_ok=True)
    path = output / "capitalizer-nine-market-max-recovery-target-ready-freeze-v1.json"
    path.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    market = sub.add_parser("market")
    market.add_argument("final_root", type=Path)
    market.add_argument("arbitration_root", type=Path)
    market.add_argument("stop_root", type=Path)
    market.add_argument("funnel_root", type=Path)
    market.add_argument("rearm_root", type=Path)
    market.add_argument("m1_root", type=Path)
    market.add_argument("output", type=Path)
    market.add_argument(
        "--session",
        required=True,
        choices=[item.value for item in CapitalizerSession],
    )
    matrix = sub.add_parser("matrix")
    matrix.add_argument("input_root", type=Path)
    matrix.add_argument("output", type=Path)
    args = parser.parse_args()
    if args.command == "market":
        report, trades = build_market_report(
            args.final_root,
            args.arbitration_root,
            args.stop_root,
            args.funnel_root,
            args.rearm_root,
            args.m1_root,
            session=CapitalizerSession(args.session),
        )
        write_market(report, trades, args.output)
        print(json.dumps(report, sort_keys=True))
        return
    report = build_matrix(args.input_root)
    write_matrix(report, args.output)
    print(json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    main()
