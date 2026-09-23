"""Final causal recovery union before target optimization.

Recovery families:
1. causal closeback arbitration;
2. protected-swing geometry rescue;
3. rejected-WAIT parallel complete-cycle rearm.

The final union preserves one trade per market/H1 using earliest causal entry
arbitration, then applies portfolio MAX3/session/date. No ATR/body/CISD/swing/FVG
threshold relaxation and no target optimization are included.

This module closes the recovery phase and produces the frozen trade universe
that the next target-optimization phase must consume unchanged.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict
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
from qore.infrastructure.trader_lab.capitalizer_max_recovery_v2 import (
    ARBITRATION_MAX3,
    ARBITRATION_RAW,
    RecoveryTrade,
    _arbitrate_h1,
    _load_arbitration,
    _metrics,
    _portfolio_max3,
    _protected_additions,
)
from qore.infrastructure.trader_lab.capitalizer_strict_htf_gate_1y_v1 import (
    TFBar,
    _aggregate_tf,
    _index_day_inputs,
    _pivots,
)
from qore.infrastructure.trader_lab.capitalizer_v3_cisd_boundary_semantics_census_2y_v1 import (
    _reconstruct_closebacks,
)
from qore.infrastructure.trader_lab.capitalizer_v3_source_first_cisd_v1 import (
    find_source_first_m3_mss,
)
from qore.infrastructure.trader_lab.capitalizer_v3_source_first_wait_rearm_atlas_2y_v1 import (
    _new_closeback,
    _new_raid,
)

IDENTITY = "QORE_CAPITALIZER_MAX_RECOVERY_FINAL_2Y_V1"
MATRIX_IDENTITY = "QORE_CAPITALIZER_NINE_MARKET_MAX_RECOVERY_FINAL_2Y_V1"
EXPECTED_WAIT_REJECTED = 165
EXPECTED_WAIT_REARMS = 3
WAIT_MINUTES = 5
REJECTED_WAIT = {"WAIT_STOP_INVALIDATED", "WAIT_NO_REFILL"}


def _load_rejected_wait_rows(root: Path) -> tuple[dict[str, Any], ...]:
    paths = sorted(
        root.rglob(
            "capitalizer-*-v3-source-first-wait5-funnel-atlas-2y-v1-rows.jsonl"
        )
    )
    if len(paths) != 1:
        raise ValueError("MAX_RECOVERY_FINAL requires one funnel ledger")
    rows: list[dict[str, Any]] = []
    with paths[0].open(encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            raw = json.loads(line)
            if raw.get("terminal_reason") in REJECTED_WAIT:
                rows.append(raw)
    return tuple(rows)


def _rearm_additions(
    *,
    rejected_rows: tuple[dict[str, Any], ...],
    closebacks: dict[str, v3.SweepCloseback],
    execution_by_day: dict[str, tuple[CapitalizerM1Bar, ...]],
    m5: tuple[TFBar, ...],
    m5_closes: tuple[datetime, ...],
    m3: tuple[TFBar, ...],
    m3_closes: tuple[datetime, ...],
    m3_pivots: Any,
    buffer_price: Decimal,
) -> tuple[RecoveryTrade, ...]:
    additions: list[RecoveryTrade] = []

    for raw in rejected_rows:
        original = closebacks.get(str(raw["closeback_at"]))
        if original is None:
            raise ValueError("MAX_RECOVERY_FINAL missing rejected-WAIT closeback")

        day = str(raw["operating_date"])
        execution = execution_by_day.get(day, ())
        if not execution:
            raise ValueError("MAX_RECOVERY_FINAL missing rejected-WAIT day")

        original_mss = datetime.fromisoformat(str(raw["source_first_mss_at"]))
        deadline = datetime.fromisoformat(str(raw["h1_deadline"]))
        eligible_at = original_mss + timedelta(minutes=WAIT_MINUTES)
        side = CapitalizerSide(str(raw["side"]))

        raid = _new_raid(
            execution,
            after=eligible_at,
            before=deadline,
            liquidity_kind=original.reference.kind,
            original_extreme=original.sweep_extreme,
        )
        if raid is None:
            continue

        new_closeback = _new_closeback(
            m5,
            m5_closes,
            raid_at=raid.opened_at,
            deadline=deadline,
            liquidity_kind=original.reference.kind,
            liquidity_price=original.reference.price,
        )
        if new_closeback is None:
            continue

        mss = find_source_first_m3_mss(
            m3,
            m3_closes,
            m3_pivots,
            sweep_at=raid.opened_at,
            after=new_closeback,
            before=deadline,
            side=side,
        )
        if mss is None:
            continue

        zone = v3._m1_causal_zone(execution, event=mss)
        if zone is None:
            continue
        fill = v3._find_m1_fill(
            execution,
            event=mss,
            zone=zone,
            deadline=deadline,
        )
        if fill is None:
            continue

        entry_index, entry_price, _ = fill
        stop_price = (
            mss.broken_swing_price - buffer_price
            if side is CapitalizerSide.LONG
            else mss.broken_swing_price + buffer_price
        )
        valid_stop = (
            stop_price < entry_price
            if side is CapitalizerSide.LONG
            else stop_price > entry_price
        )
        if not valid_stop:
            continue

        risk = abs(entry_price - stop_price)
        if risk <= 0:
            raise ValueError("MAX_RECOVERY_FINAL rearm requires positive risk")
        target_price = (
            entry_price + Decimal("2") * risk
            if side is CapitalizerSide.LONG
            else entry_price - Decimal("2") * risk
        )
        realized, reason, _, ambiguous, exit_at = v3._lifecycle(
            execution,
            entry_index=entry_index,
            side=side,
            entry_price=entry_price,
            stop_price=stop_price,
            target_price=target_price,
            deadline=deadline,
        )
        additions.append(
            RecoveryTrade(
                symbol=str(raw["symbol"]),
                session=str(raw["session"]),
                operating_date=day,
                side=side.value,
                h1_open=(deadline - timedelta(hours=1)).isoformat(),
                h1_deadline=deadline.isoformat(),
                entry_at=execution[entry_index].opened_at.isoformat(),
                exit_at=exit_at.isoformat(),
                realized_gross_r=str(realized),
                exit_reason=reason,
                same_minute_stop_target_ambiguity=ambiguous,
                provenance="WAIT_REJECTED_PARALLEL_REARM",
            )
        )

    return tuple(
        sorted(
            additions,
            key=lambda item: (
                datetime.fromisoformat(item.entry_at),
                item.symbol,
            ),
        )
    )


def build_market_report(
    arbitration_root: Path,
    stop_root: Path,
    funnel_root: Path,
    m1_root: Path,
    *,
    session: CapitalizerSession,
) -> tuple[
    dict[str, Any],
    tuple[RecoveryTrade, ...],
]:
    arbitration = _load_arbitration(arbitration_root)
    stop_rows = protected_rescue._stop_rows(stop_root)
    invalid_funnel_rows = protected_rescue._funnel_rows(funnel_root)
    rejected_rows = _load_rejected_wait_rows(funnel_root)

    bars = tuple(iter_cibo_m1(m1_root))
    if not bars:
        raise ValueError("MAX_RECOVERY_FINAL requires native M1")
    symbol = bars[0].symbol
    if any(item.symbol != symbol for item in arbitration):
        raise ValueError("MAX_RECOVERY_FINAL arbitration/M1 symbol mismatch")

    execution_by_day, _ = _index_day_inputs(bars, session=session)
    protected = _protected_additions(
        stop_rows=stop_rows,
        funnel_rows=invalid_funnel_rows,
        execution_by_day=execution_by_day,
    )

    closebacks = _reconstruct_closebacks(all_bars=bars, session=session)
    m5 = _aggregate_tf(bars, minutes=5)
    m5_closes = tuple(item.closed_at for item in m5)
    m3 = _aggregate_tf(bars, minutes=3)
    m3_closes = tuple(item.closed_at for item in m3)
    m3_pivots = _pivots(m3)
    buffer_price = v3._stop_buffer(bars)
    rearms = _rearm_additions(
        rejected_rows=rejected_rows,
        closebacks=closebacks,
        execution_by_day=execution_by_day,
        m5=m5,
        m5_closes=m5_closes,
        m3=m3,
        m3_closes=m3_closes,
        m3_pivots=m3_pivots,
        buffer_price=buffer_price,
    )

    candidate, duplicate_h1, opposite_ties = _arbitrate_h1(
        tuple((*arbitration, *protected, *rearms))
    )
    provenance: dict[str, int] = {}
    for trade in candidate:
        provenance[trade.provenance] = provenance.get(trade.provenance, 0) + 1

    return {
        "identity": IDENTITY,
        "symbol": symbol,
        "session": session.value,
        "arbitration_raw": len(arbitration),
        "protected_rescue_raw": len(protected),
        "rejected_wait_population": len(rejected_rows),
        "wait_rearm_raw": len(rearms),
        "h1_arbitrated_raw": len(candidate),
        "duplicate_h1_candidates": duplicate_h1,
        "opposite_tie_fail_closed": opposite_ties,
        "selected_provenance": dict(sorted(provenance.items())),
        "one_trade_per_market_h1": True,
        "earliest_causal_entry_wins": True,
        "portfolio_max3_preserved": True,
        "threshold_relaxations_included": False,
        "target_changes_included": False,
        "outcome_used_for_admission": False,
        "recovery_phase_open": False,
        "recovery_phase_closed": True,
        "target_phase_ready": True,
        "trader_certified": False,
        "live_authorized": False,
        "real_capital_authorized": False,
    }, candidate


def write_market(
    report: dict[str, Any],
    candidate: tuple[RecoveryTrade, ...],
    output: Path,
) -> None:
    output.mkdir(parents=True, exist_ok=True)
    symbol = str(report["symbol"]).lower()
    stem = f"capitalizer-{symbol}-max-recovery-final-2y-v1"
    (output / f"{stem}.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    with (output / f"{stem}-trades.jsonl").open("w", encoding="utf-8") as handle:
        for trade in candidate:
            handle.write(json.dumps(asdict(trade), sort_keys=True) + "\n")


def _load_reports(root: Path) -> list[dict[str, Any]]:
    paths = sorted(root.rglob("capitalizer-*-max-recovery-final-2y-v1.json"))
    if len(paths) != 9:
        raise ValueError(
            f"MAX_RECOVERY_FINAL requires 9 reports, got {len(paths)}"
        )
    return [dict(json.loads(path.read_text(encoding="utf-8"))) for path in paths]


def _load_trades(root: Path) -> tuple[RecoveryTrade, ...]:
    paths = sorted(
        root.rglob("capitalizer-*-max-recovery-final-2y-v1-trades.jsonl")
    )
    if len(paths) != 9:
        raise ValueError(
            f"MAX_RECOVERY_FINAL requires 9 trade ledgers, got {len(paths)}"
        )
    rows: list[RecoveryTrade] = []
    for path in paths:
        with path.open(encoding="utf-8") as handle:
            for line in handle:
                if line.strip():
                    rows.append(RecoveryTrade(**json.loads(line)))
    return tuple(rows)


def build_matrix(root: Path) -> dict[str, Any]:
    reports = _load_reports(root)
    raw = _load_trades(root)
    max3 = _portfolio_max3(raw)
    metrics = _metrics(max3)
    if metrics is None:
        raise ValueError("MAX_RECOVERY_FINAL requires complete metrics")

    provenance: dict[str, int] = {}
    for trade in max3:
        provenance[trade.provenance] = provenance.get(trade.provenance, 0) + 1

    rejected_total = sum(int(item["rejected_wait_population"]) for item in reports)
    rearm_total = sum(int(item["wait_rearm_raw"]) for item in reports)

    return {
        "identity": MATRIX_IDENTITY,
        "market_count": 9,
        "raw_trades": len(raw),
        "max3_trades": len(max3),
        "max3_metrics": metrics,
        "max3_provenance": dict(sorted(provenance.items())),
        "rejected_wait_population": rejected_total,
        "rejected_wait_control_reproduced": rejected_total == EXPECTED_WAIT_REJECTED,
        "wait_rearm_raw": rearm_total,
        "wait_rearm_control_reproduced": rearm_total == EXPECTED_WAIT_REARMS,
        "duplicate_h1_candidates": sum(
            int(item["duplicate_h1_candidates"]) for item in reports
        ),
        "opposite_tie_fail_closed": sum(
            int(item["opposite_tie_fail_closed"]) for item in reports
        ),
        "delta_vs_arbitration": {
            "raw_trades": len(raw) - ARBITRATION_RAW,
            "max3_trades": len(max3) - ARBITRATION_MAX3,
        },
        "one_trade_per_market_h1": True,
        "earliest_causal_entry_wins": True,
        "portfolio_max3_preserved": True,
        "threshold_relaxations_included": False,
        "target_changes_included": False,
        "outcome_used_for_admission": False,
        "recovery_phase_open": False,
        "recovery_phase_closed": True,
        "target_phase_ready": True,
        "automatic_promotion_allowed": False,
        "trader_certified": False,
        "live_authorized": False,
        "real_capital_authorized": False,
    }


def write_matrix(report: dict[str, Any], output: Path) -> None:
    output.mkdir(parents=True, exist_ok=True)
    path = output / "capitalizer-nine-market-max-recovery-final-2y-v1.json"
    path.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)

    market = sub.add_parser("market")
    market.add_argument("arbitration_root", type=Path)
    market.add_argument("stop_root", type=Path)
    market.add_argument("funnel_root", type=Path)
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
        report, candidate = build_market_report(
            args.arbitration_root,
            args.stop_root,
            args.funnel_root,
            args.m1_root,
            session=CapitalizerSession(args.session),
        )
        write_market(report, candidate, args.output)
        print(json.dumps(report, sort_keys=True))
        return

    report = build_matrix(args.input_root)
    write_matrix(report, args.output)
    print(json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    main()
