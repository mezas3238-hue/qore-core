"""Outcome-free timing atlas for SOURCE_FIRST NO_M3_AFTER_CLOSEBACK blockers.

Population: residual SOURCE_FIRST M3 closebacks whose terminal blocker is
NO_M3_AFTER_CLOSEBACK.

The atlas asks whether the absence of an eligible M3 bar is an expected timing
consequence or a temporal-alignment defect:
- remaining minutes from M5 closeback to frozen H1 deadline;
- first M3 close strictly after closeback;
- whether that M3 bar opens before but closes after the H1 deadline;
- deadline overshoot in minutes.

No lifecycle is extended. No outcomes, fills, PnL, or economic selection are read.
"""

from __future__ import annotations

import argparse
import bisect
import json
from collections import Counter
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any

from qore.infrastructure.trader_lab.capitalizer_cibo_m1_reader_v1 import iter_cibo_m1
from qore.infrastructure.trader_lab.capitalizer_contract import CapitalizerSession
from qore.infrastructure.trader_lab.capitalizer_m3_mss_bottleneck_forensics_2y_v1 import (
    LOOKBACK_START,
    WINDOW_END,
)
from qore.infrastructure.trader_lab.capitalizer_strict_htf_gate_1y_v1 import (
    TFBar,
    _aggregate_tf,
)

IDENTITY = "QORE_CAPITALIZER_V3_SOURCE_FIRST_NO_M3_TIMING_ATLAS_2Y_V1"
MATRIX_IDENTITY = (
    "QORE_CAPITALIZER_NINE_MARKET_V3_SOURCE_FIRST_NO_M3_TIMING_ATLAS_2Y_V1"
)
EXPECTED_NO_M3 = 390


@dataclass(frozen=True, slots=True)
class NoM3TimingRow:
    symbol: str
    session: str
    operating_date: str
    closeback_at: str
    h1_deadline: str
    minutes_remaining: str
    remaining_band: str
    next_m3_opened_at: str | None
    next_m3_closed_at: str | None
    next_m3_overshoot_minutes: str | None
    next_m3_straddles_deadline: bool
    timing_alignment_defect: bool
    outcome_fields_read: bool = False


def _aware(value: str) -> datetime:
    return datetime.fromisoformat(value)


def _remaining_band(value: Decimal) -> str:
    if value <= 0:
        return "LE_0M"
    if value <= Decimal("1"):
        return "GT_0_TO_1M"
    if value <= Decimal("2"):
        return "GT_1_TO_2M"
    if value <= Decimal("3"):
        return "GT_2_TO_3M"
    return "GT_3M"


def _load_blockers(root: Path) -> tuple[dict[str, Any], ...]:
    paths = sorted(
        root.rglob(
            "capitalizer-*-v3-source-first-residual-m3-bottleneck-atlas-2y-v1-rows.jsonl"
        )
    )
    if len(paths) != 1:
        raise ValueError("no-M3 timing atlas requires one residual ledger per market")
    rows: list[dict[str, Any]] = []
    with paths[0].open(encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            raw = json.loads(line)
            if not isinstance(raw, dict):
                raise ValueError("residual row must be an object")
            if raw.get("terminal_blocker") == "NO_M3_AFTER_CLOSEBACK":
                rows.append(raw)
    return tuple(rows)


def _build_row(
    raw: dict[str, Any],
    *,
    symbol: str,
    session: CapitalizerSession,
    m3: tuple[TFBar, ...],
    m3_closes: tuple[datetime, ...],
) -> NoM3TimingRow:
    closeback_at = _aware(str(raw["closeback_at"]))
    deadline = _aware(str(raw["h1_deadline"]))
    remaining = Decimal(str((deadline - closeback_at).total_seconds())) / Decimal("60")

    index = bisect.bisect_right(m3_closes, closeback_at)
    next_bar = m3[index] if index < len(m3) else None
    next_open = None if next_bar is None else next_bar.opened_at
    next_close = None if next_bar is None else next_bar.closed_at

    overshoot: Decimal | None = None
    straddles = False
    if next_bar is not None:
        overshoot = Decimal(
            str((next_bar.closed_at - deadline).total_seconds())
        ) / Decimal("60")
        straddles = next_bar.opened_at < deadline < next_bar.closed_at

    # A defect would mean more than one full M3 duration remained but no completed
    # M3 bar existed before deadline. That should be impossible under aligned data.
    defect = remaining > Decimal("3") and (
        next_bar is None or next_bar.closed_at > deadline
    )

    return NoM3TimingRow(
        symbol=symbol,
        session=session.value,
        operating_date=str(raw["operating_date"]),
        closeback_at=closeback_at.isoformat(),
        h1_deadline=deadline.isoformat(),
        minutes_remaining=str(remaining),
        remaining_band=_remaining_band(remaining),
        next_m3_opened_at=None if next_open is None else next_open.isoformat(),
        next_m3_closed_at=None if next_close is None else next_close.isoformat(),
        next_m3_overshoot_minutes=None if overshoot is None else str(overshoot),
        next_m3_straddles_deadline=straddles,
        timing_alignment_defect=defect,
    )


def build_market_report(
    residual_root: Path,
    m1_root: Path,
    *,
    session: CapitalizerSession,
) -> tuple[dict[str, Any], tuple[NoM3TimingRow, ...]]:
    frozen = _load_blockers(residual_root)
    if not frozen:
        raise ValueError("no-M3 timing atlas found no blockers")

    all_bars = tuple(
        bar
        for bar in iter_cibo_m1(m1_root)
        if LOOKBACK_START <= bar.opened_at < WINDOW_END + timedelta(days=1)
    )
    if not all_bars:
        raise ValueError("no-M3 timing atlas found no native M1")
    symbol = all_bars[0].symbol
    if any(bar.symbol != symbol for bar in all_bars):
        raise ValueError("no-M3 timing atlas requires one market")
    if any(str(row["symbol"]) != symbol for row in frozen):
        raise ValueError("no-M3 timing residual/M1 symbol mismatch")
    if any(str(row["session"]) != session.value for row in frozen):
        raise ValueError("no-M3 timing session mismatch")

    m3 = _aggregate_tf(all_bars, minutes=3)
    m3_closes = tuple(item.closed_at for item in m3)
    rows = tuple(
        _build_row(
            row,
            symbol=symbol,
            session=session,
            m3=m3,
            m3_closes=m3_closes,
        )
        for row in frozen
    )
    bands = Counter(item.remaining_band for item in rows)
    return {
        "identity": IDENTITY,
        "symbol": symbol,
        "session": session.value,
        "no_m3_blockers": len(rows),
        "remaining_bands": dict(sorted(bands.items())),
        "next_m3_straddles_deadline": sum(
            item.next_m3_straddles_deadline for item in rows
        ),
        "timing_alignment_defects": sum(
            item.timing_alignment_defect for item in rows
        ),
        "deadline_extended": False,
        "m3_alignment_changed": False,
        "outcome_fields_read": False,
        "outcome_used_for_classification": False,
        "strategy_mutated": False,
        "diagnostic_only": True,
        "economic_candidate": False,
        "rule_promotion_allowed": False,
        "fresh_holdout_claimed": False,
        "live_authorized": False,
        "real_capital_authorized": False,
    }, rows


def write_market(
    report: dict[str, Any],
    rows: tuple[NoM3TimingRow, ...],
    output: Path,
) -> None:
    output.mkdir(parents=True, exist_ok=True)
    symbol = str(report["symbol"]).lower()
    stem = f"capitalizer-{symbol}-v3-source-first-no-m3-timing-atlas-2y-v1"
    (output / f"{stem}.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    with (output / f"{stem}-rows.jsonl").open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(asdict(row), sort_keys=True) + "\n")


def _load_reports(root: Path) -> list[dict[str, Any]]:
    paths = sorted(
        root.rglob("capitalizer-*-v3-source-first-no-m3-timing-atlas-2y-v1.json")
    )
    if len(paths) != 9:
        raise ValueError(f"no-M3 timing matrix requires 9 reports, got {len(paths)}")
    return [dict(json.loads(path.read_text(encoding="utf-8"))) for path in paths]


def build_matrix(root: Path) -> dict[str, Any]:
    reports = _load_reports(root)
    total = sum(int(item["no_m3_blockers"]) for item in reports)
    bands: Counter[str] = Counter()
    for report in reports:
        for key, value in dict(report["remaining_bands"]).items():
            bands[str(key)] += int(value)
    return {
        "identity": MATRIX_IDENTITY,
        "market_count": 9,
        "no_m3_blockers": total,
        "no_m3_control_reproduced": total == EXPECTED_NO_M3,
        "remaining_bands": dict(sorted(bands.items())),
        "next_m3_straddles_deadline": sum(
            int(item["next_m3_straddles_deadline"]) for item in reports
        ),
        "timing_alignment_defects": sum(
            int(item["timing_alignment_defects"]) for item in reports
        ),
        "markets": sorted(reports, key=lambda item: str(item["symbol"])),
        "deadline_extended": False,
        "m3_alignment_changed": False,
        "outcome_fields_read": False,
        "outcome_used_for_classification": False,
        "strategy_mutated": False,
        "diagnostic_only": True,
        "economic_candidate": False,
        "rule_promotion_allowed": False,
        "fresh_holdout_claimed": False,
        "live_authorized": False,
        "real_capital_authorized": False,
    }


def write_matrix(report: dict[str, Any], output: Path) -> None:
    output.mkdir(parents=True, exist_ok=True)
    path = output / "capitalizer-nine-market-v3-source-first-no-m3-timing-atlas-2y-v1.json"
    path.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)

    market = sub.add_parser("market")
    market.add_argument("residual_root", type=Path)
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
        report, rows = build_market_report(
            args.residual_root,
            args.m1_root,
            session=CapitalizerSession(args.session),
        )
        write_market(report, rows, args.output)
        print(json.dumps(report, sort_keys=True))
        return

    report = build_matrix(args.input_root)
    write_matrix(report, args.output)
    print(json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    main()
