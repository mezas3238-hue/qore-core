"""Two-year V3 M3-MSS bottleneck atlas.

Reuses the already validated 1Y M3 diagnosis logic and only expands the diagnostic
window to 2024-09-17 .. 2026-09-17. Research-only; V3 rules are unchanged.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from dataclasses import asdict
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Any

from qore.infrastructure.trader_lab.capitalizer_cibo_m1_reader_v1 import (
    iter_cibo_m1,
)
from qore.infrastructure.trader_lab.capitalizer_contract import (
    CapitalizerSession,
)
from qore.infrastructure.trader_lab.capitalizer_full_ict_density_scanner_1y_v1 import (
    _aggregate_h1,
)
from qore.infrastructure.trader_lab.capitalizer_m3_mss_bottleneck_forensics_1y_v1 import (
    FAILURE_NAMES,
    ClosebackDiagnostic,
    _scan_day,
)
from qore.infrastructure.trader_lab.capitalizer_owner_h1_m3_m1_causal_reversal_1y_v3 import (
    EXPECTED_SYMBOLS,
    _build_h1_swings,
    _stop_buffer,
)
from qore.infrastructure.trader_lab.capitalizer_strict_htf_gate_1y_v1 import (
    _aggregate_tf,
    _index_day_inputs,
    _pivots,
)

IDENTITY = "QORE_CAPITALIZER_M3_MSS_BOTTLENECK_FORENSICS_2Y_V1"
MATRIX_IDENTITY = (
    "QORE_CAPITALIZER_NINE_MARKET_M3_MSS_BOTTLENECK_FORENSICS_2Y_V1"
)
WINDOW_START = datetime(2024, 9, 17, 0, 0, tzinfo=UTC)
WINDOW_END = datetime(2026, 9, 17, 0, 0, tzinfo=UTC)
LOOKBACK_START = WINDOW_START - timedelta(days=21)


def _summarize(
    *,
    symbol: str,
    session: CapitalizerSession,
    diagnostics: tuple[ClosebackDiagnostic, ...],
) -> dict[str, Any]:
    independent: Counter[str] = Counter()
    first: Counter[str] = Counter()
    signatures: Counter[str] = Counter()
    attr_map = {
        "DIRECTION": "direction_failed",
        "SWING_BREAK": "swing_break_failed",
        "CISD": "cisd_failed",
        "BODY_LT_60": "body_failed",
        "ATR_LE_1_2": "atr_failed",
    }
    for item in diagnostics:
        first[item.first_blocker] += 1
        failed = [
            name
            for name, attr in attr_map.items()
            if bool(getattr(item, attr))
        ]
        for name in failed:
            independent[name] += 1
        signatures["+".join(failed) if failed else "NONE"] += 1

    valid = sum(item.valid_m3_within_h1 for item in diagnostics)
    return {
        "identity": IDENTITY,
        "symbol": symbol,
        "session": session.value,
        "window_start": WINDOW_START.isoformat(),
        "window_end_exclusive": WINDOW_END.isoformat(),
        "m5_closebacks": len(diagnostics),
        "valid_m3_mss": valid,
        "rejected_m3_mss": len(diagnostics) - valid,
        "valid_retention": 0.0 if not diagnostics else valid / len(diagnostics),
        "independent_failures": {
            name: independent[name] for name in FAILURE_NAMES
        },
        "first_blockers": dict(sorted(first.items())),
        "failure_signatures": dict(
            sorted(signatures.items(), key=lambda item: (-item[1], item[0]))
        ),
        "window_expired_late_mss": sum(
            item.window_expired_late_mss for item in diagnostics
        ),
        "closebacks_with_zero_m3_bars_remaining": sum(
            float(item.minutes_remaining_after_closeback) < 3.0
            for item in diagnostics
        ),
        "thresholds_changed": False,
        "session_windows_changed": False,
        "outcome_aware_selection_used": False,
        "late_mss_used_for_admission": False,
        "methodology_research_only": True,
        "diagnostic_window_role": "CONSUMED_DIAGNOSTIC_RESEARCH",
    }


def build_market_report(
    m1_root: Path,
    *,
    session: CapitalizerSession,
) -> tuple[dict[str, Any], tuple[ClosebackDiagnostic, ...]]:
    all_bars = tuple(
        bar
        for bar in iter_cibo_m1(m1_root)
        if LOOKBACK_START <= bar.opened_at < WINDOW_END + timedelta(days=1)
    )
    if not all_bars:
        raise ValueError("2Y M3 bottleneck found no native M1")
    symbol = all_bars[0].symbol
    if any(bar.symbol != symbol for bar in all_bars):
        raise ValueError("2Y M3 bottleneck requires one symbol per M1 root")

    h1 = _aggregate_h1(all_bars)
    h1_swings = _build_h1_swings(h1)
    m5 = _aggregate_tf(all_bars, minutes=5)
    m3 = _aggregate_tf(all_bars, minutes=3)
    m3_pivots = _pivots(m3)
    m5_closes = tuple(item.closed_at for item in m5)
    m3_closes = tuple(item.closed_at for item in m3)
    buffer_price = _stop_buffer(all_bars)
    execution_by_day, reference_by_day = _index_day_inputs(
        all_bars,
        session=session,
    )

    grouped_dates = sorted(
        key
        for key in execution_by_day
        if WINDOW_START.date().isoformat()
        <= key
        < WINDOW_END.date().isoformat()
    )

    diagnostics: list[ClosebackDiagnostic] = []
    for value in grouped_dates:
        operating_day = date.fromisoformat(value)
        diagnostics.extend(
            _scan_day(
                symbol=symbol,
                session=session,
                operating_day=operating_day,
                prior_session=reference_by_day.get(value),
                execution=execution_by_day.get(value, ()),
                all_bars=all_bars,
                h1_swings=h1_swings,
                m5=m5,
                m5_closes=m5_closes,
                m3=m3,
                m3_closes=m3_closes,
                m3_pivots=m3_pivots,
                buffer_price=buffer_price,
            )
        )

    ordered = tuple(sorted(diagnostics, key=lambda item: item.closeback_at))
    return _summarize(
        symbol=symbol,
        session=session,
        diagnostics=ordered,
    ), ordered


def write_market(
    report: dict[str, Any],
    diagnostics: tuple[ClosebackDiagnostic, ...],
    output: Path,
) -> None:
    output.mkdir(parents=True, exist_ok=True)
    symbol = str(report["symbol"]).lower()
    stem = f"capitalizer-{symbol}-m3-mss-bottleneck-forensics-2y-v1"
    (output / f"{stem}.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    with (output / f"{stem}-closebacks.jsonl").open("w", encoding="utf-8") as handle:
        for item in diagnostics:
            handle.write(json.dumps(asdict(item), sort_keys=True) + "\n")


def _load_reports(root: Path) -> list[dict[str, Any]]:
    paths = sorted(
        root.rglob("capitalizer-*-m3-mss-bottleneck-forensics-2y-v1.json")
    )
    if len(paths) != 9:
        raise ValueError(f"2Y M3 matrix requires 9 reports, got {len(paths)}")
    reports = [
        dict(json.loads(path.read_text(encoding="utf-8")))
        for path in paths
    ]
    if {str(item["symbol"]) for item in reports} != EXPECTED_SYMBOLS:
        raise ValueError("2Y M3 universe mismatch")
    return reports


def _sum_nested(reports: list[dict[str, Any]], key: str) -> dict[str, int]:
    total: Counter[str] = Counter()
    for report in reports:
        raw = report[key]
        if not isinstance(raw, dict):
            raise ValueError(f"{key} must be a dict")
        for name, value in raw.items():
            total[str(name)] += int(value)
    return dict(sorted(total.items()))


def build_matrix(root: Path) -> dict[str, Any]:
    reports = _load_reports(root)
    closebacks = sum(int(item["m5_closebacks"]) for item in reports)
    valid = sum(int(item["valid_m3_mss"]) for item in reports)
    rejected = sum(int(item["rejected_m3_mss"]) for item in reports)

    per_session: dict[str, dict[str, Any]] = {}
    for session in CapitalizerSession:
        members = [
            item for item in reports if item["session"] == session.value
        ]
        per_session[session.value] = {
            "m5_closebacks": sum(int(item["m5_closebacks"]) for item in members),
            "valid_m3_mss": sum(int(item["valid_m3_mss"]) for item in members),
            "rejected_m3_mss": sum(int(item["rejected_m3_mss"]) for item in members),
            "first_blockers": _sum_nested(members, "first_blockers"),
            "independent_failures": _sum_nested(members, "independent_failures"),
            "window_expired_late_mss": sum(
                int(item["window_expired_late_mss"]) for item in members
            ),
        }

    return {
        "identity": MATRIX_IDENTITY,
        "window_start": WINDOW_START.isoformat(),
        "window_end_exclusive": WINDOW_END.isoformat(),
        "market_count": 9,
        "m5_closebacks": closebacks,
        "valid_m3_mss": valid,
        "rejected_m3_mss": rejected,
        "valid_retention": 0.0 if closebacks == 0 else valid / closebacks,
        "independent_failures": _sum_nested(reports, "independent_failures"),
        "first_blockers": _sum_nested(reports, "first_blockers"),
        "failure_signatures": _sum_nested(reports, "failure_signatures"),
        "window_expired_late_mss": sum(
            int(item["window_expired_late_mss"]) for item in reports
        ),
        "closebacks_with_zero_m3_bars_remaining": sum(
            int(item["closebacks_with_zero_m3_bars_remaining"])
            for item in reports
        ),
        "per_session": per_session,
        "markets": sorted(reports, key=lambda item: str(item["symbol"])),
        "thresholds_changed": False,
        "session_windows_changed": False,
        "outcome_aware_selection_used": False,
        "late_mss_used_for_admission": False,
        "methodology_research_only": True,
        "diagnostic_window_role": "CONSUMED_DIAGNOSTIC_RESEARCH",
    }


def write_matrix(report: dict[str, Any], output: Path) -> None:
    output.mkdir(parents=True, exist_ok=True)
    path = output / "capitalizer-nine-market-m3-mss-bottleneck-forensics-2y-v1.json"
    path.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    market = sub.add_parser("market")
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
        report, diagnostics = build_market_report(
            args.m1_root,
            session=CapitalizerSession(args.session),
        )
        write_market(report, diagnostics, args.output)
        print(json.dumps(report, sort_keys=True))
        return

    report = build_matrix(args.input_root)
    write_matrix(report, args.output)
    print(json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    main()
