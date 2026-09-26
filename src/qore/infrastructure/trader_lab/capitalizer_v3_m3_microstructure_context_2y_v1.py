"""Join frozen V3 2Y M3 bottleneck diagnostics to existing M5 microstructure observations.

This is an adapter around already-built CORE laboratories. It does not change V3, thresholds,
sessions, entries, stops, targets, or outcomes. It asks which completed-M5 microstructure
states are present at closeback time for VALID and rejected M3 populations.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from decimal import Decimal
from pathlib import Path
from statistics import median
from typing import Any

from qore.infrastructure.trader_lab.capitalizer_m3_mss_bottleneck_forensics_2y_v1 import (
    IDENTITY as BOTTLENECK_IDENTITY,
)
from qore.infrastructure.trader_lab.capitalizer_m3_mss_bottleneck_forensics_2y_v1 import (
    WINDOW_END,
    WINDOW_START,
)
from qore.infrastructure.trader_lab.capitalizer_microstructure_discovery import (
    CapitalizerM5MicroObservation,
    scan_microstructure,
)

IDENTITY = "QORE_CAPITALIZER_V3_M3_MICROSTRUCTURE_CONTEXT_2Y_V1"
MATRIX_IDENTITY = "QORE_CAPITALIZER_NINE_MARKET_V3_M3_MICROSTRUCTURE_CONTEXT_2Y_V1"


@dataclass(frozen=True, slots=True)
class ContextRow:
    symbol: str
    session: str
    operating_date: str
    closeback_at: str
    side: str
    first_blocker: str
    valid_m3_within_h1: bool
    microstructure_signature: str
    body_fraction: str
    close_location: str
    previous_range_ratio: str | None
    outcome_used_for_selection: bool = False


def _signature(item: CapitalizerM5MicroObservation) -> str:
    if not item.events:
        return "NONE"
    return "+".join(event.value for event in item.events)


def _load_closebacks(root: Path) -> tuple[dict[str, Any], ...]:
    summaries = sorted(
        root.rglob("capitalizer-*-m3-mss-bottleneck-forensics-2y-v1.json")
    )
    ledgers = sorted(
        root.rglob("capitalizer-*-m3-mss-bottleneck-forensics-2y-v1-closebacks.jsonl")
    )
    if len(summaries) != 1 or len(ledgers) != 1:
        raise ValueError("microstructure adapter requires one 2Y bottleneck market artifact")
    summary = json.loads(summaries[0].read_text(encoding="utf-8"))
    if summary.get("identity") != BOTTLENECK_IDENTITY:
        raise ValueError("unexpected bottleneck identity")
    if summary.get("thresholds_changed") is not False:
        raise ValueError("adapter requires unchanged V3 thresholds")

    rows: list[dict[str, Any]] = []
    with ledgers[0].open(encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                raw = json.loads(line)
                if not isinstance(raw, dict):
                    raise ValueError("closeback row must be object")
                rows.append(raw)
    if len(rows) != int(summary["m5_closebacks"]):
        raise ValueError("closeback ledger count disagrees with summary")
    return tuple(rows)


def _micro_index(
    observations: tuple[CapitalizerM5MicroObservation, ...],
) -> dict[str, CapitalizerM5MicroObservation]:
    result: dict[str, CapitalizerM5MicroObservation] = {}
    for item in observations:
        if not WINDOW_START <= item.decision_at < WINDOW_END:
            continue
        key = item.decision_at.isoformat()
        if key in result:
            raise ValueError("duplicate microstructure decision timestamp")
        result[key] = item
    return result


def _metrics(rows: tuple[ContextRow, ...]) -> dict[str, Any]:
    if not rows:
        return {
            "observations": 0,
            "median_body_fraction": None,
            "median_close_location": None,
            "median_previous_range_ratio": None,
        }
    ratios = tuple(
        Decimal(item.previous_range_ratio)
        for item in rows
        if item.previous_range_ratio is not None
    )
    return {
        "observations": len(rows),
        "median_body_fraction": str(
            median(Decimal(item.body_fraction) for item in rows)
        ),
        "median_close_location": str(
            median(Decimal(item.close_location) for item in rows)
        ),
        "median_previous_range_ratio": None if not ratios else str(median(ratios)),
    }


def build_market_report(
    bottleneck_root: Path,
    m5_root: Path,
) -> tuple[dict[str, Any], tuple[ContextRow, ...]]:
    closebacks = _load_closebacks(bottleneck_root)
    observations = scan_microstructure(m5_root)
    index = _micro_index(observations)
    if not closebacks:
        raise ValueError("microstructure adapter requires closebacks")

    symbol = str(closebacks[0]["symbol"])
    session = str(closebacks[0]["session"])
    rows: list[ContextRow] = []
    missing = 0
    for item in closebacks:
        closeback_at = str(item["closeback_at"])
        micro = index.get(closeback_at)
        if micro is None:
            missing += 1
            continue
        rows.append(
            ContextRow(
                symbol=symbol,
                session=session,
                operating_date=str(item["operating_date"]),
                closeback_at=closeback_at,
                side=str(item["side"]),
                first_blocker=str(item["first_blocker"]),
                valid_m3_within_h1=bool(item["valid_m3_within_h1"]),
                microstructure_signature=_signature(micro),
                body_fraction=str(micro.body_fraction),
                close_location=str(micro.close_location),
                previous_range_ratio=(
                    None
                    if micro.previous_range_ratio is None
                    else str(micro.previous_range_ratio)
                ),
            )
        )

    ordered = tuple(sorted(rows, key=lambda item: item.closeback_at))
    by_blocker: dict[str, Any] = {}
    for blocker in sorted({item.first_blocker for item in ordered}):
        subset = tuple(item for item in ordered if item.first_blocker == blocker)
        by_blocker[blocker] = {
            **_metrics(subset),
            "signatures": dict(
                Counter(item.microstructure_signature for item in subset).most_common()
            ),
        }

    valid = tuple(item for item in ordered if item.valid_m3_within_h1)
    rejected = tuple(item for item in ordered if not item.valid_m3_within_h1)
    report = {
        "identity": IDENTITY,
        "symbol": symbol,
        "session": session,
        "window_start": WINDOW_START.isoformat(),
        "window_end_exclusive": WINDOW_END.isoformat(),
        "source_closebacks": len(closebacks),
        "context_rows": len(ordered),
        "missing_microstructure_rows": missing,
        "coverage": str(
            Decimal(len(ordered)) / Decimal(len(closebacks))
        ),
        "valid_metrics": _metrics(valid),
        "rejected_metrics": _metrics(rejected),
        "by_first_blocker": by_blocker,
        "valid_signatures": dict(
            Counter(item.microstructure_signature for item in valid).most_common()
        ),
        "rejected_signatures": dict(
            Counter(item.microstructure_signature for item in rejected).most_common()
        ),
        "strategy_mutated": False,
        "thresholds_mutated": False,
        "outcome_used_for_selection": False,
        "diagnostic_only": True,
        "rule_promotion_allowed": False,
    }
    return report, ordered


def write_market(
    report: dict[str, Any],
    rows: tuple[ContextRow, ...],
    output: Path,
) -> None:
    output.mkdir(parents=True, exist_ok=True)
    symbol = str(report["symbol"]).lower()
    stem = f"capitalizer-{symbol}-v3-m3-microstructure-context-2y-v1"
    (output / f"{stem}.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    with (output / f"{stem}-rows.jsonl").open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(asdict(row), sort_keys=True) + "\n")


def _load_market_reports(root: Path) -> list[dict[str, Any]]:
    paths = sorted(root.rglob("capitalizer-*-v3-m3-microstructure-context-2y-v1.json"))
    if len(paths) != 9:
        raise ValueError(f"microstructure matrix requires 9 reports, got {len(paths)}")
    return [dict(json.loads(path.read_text(encoding="utf-8"))) for path in paths]


def build_matrix(root: Path) -> dict[str, Any]:
    reports = _load_market_reports(root)
    blocker_totals: dict[str, Counter[str]] = defaultdict(Counter)
    for report in reports:
        raw = report["by_first_blocker"]
        if not isinstance(raw, dict):
            raise ValueError("by_first_blocker must be mapping")
        for blocker, payload in raw.items():
            if not isinstance(payload, dict):
                raise ValueError("blocker payload must be mapping")
            signatures = payload["signatures"]
            if not isinstance(signatures, dict):
                raise ValueError("signatures must be mapping")
            for signature, count in signatures.items():
                blocker_totals[str(blocker)][str(signature)] += int(count)

    return {
        "identity": MATRIX_IDENTITY,
        "window_start": WINDOW_START.isoformat(),
        "window_end_exclusive": WINDOW_END.isoformat(),
        "market_count": 9,
        "source_closebacks": sum(int(item["source_closebacks"]) for item in reports),
        "context_rows": sum(int(item["context_rows"]) for item in reports),
        "missing_microstructure_rows": sum(
            int(item["missing_microstructure_rows"]) for item in reports
        ),
        "microstructure_by_first_blocker": {
            blocker: dict(counter.most_common())
            for blocker, counter in sorted(blocker_totals.items())
        },
        "markets": sorted(reports, key=lambda item: str(item["symbol"])),
        "strategy_mutated": False,
        "thresholds_mutated": False,
        "outcome_used_for_selection": False,
        "diagnostic_only": True,
        "rule_promotion_allowed": False,
    }


def write_matrix(report: dict[str, Any], output: Path) -> None:
    output.mkdir(parents=True, exist_ok=True)
    path = output / "capitalizer-nine-market-v3-m3-microstructure-context-2y-v1.json"
    path.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    market = sub.add_parser("market")
    market.add_argument("bottleneck_root", type=Path)
    market.add_argument("m5_root", type=Path)
    market.add_argument("output", type=Path)
    matrix = sub.add_parser("matrix")
    matrix.add_argument("input_root", type=Path)
    matrix.add_argument("output", type=Path)
    args = parser.parse_args()

    if args.command == "market":
        report, rows = build_market_report(
            args.bottleneck_root,
            args.m5_root,
        )
        write_market(report, rows, args.output)
        print(json.dumps(report, sort_keys=True))
        return

    report = build_matrix(args.input_root)
    write_matrix(report, args.output)
    print(json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    main()
