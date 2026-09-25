#!/usr/bin/env python3
"""Build read-only cTrader DEMO LIVE behavior reports from existing ledgers."""

from __future__ import annotations

import argparse
import json
from collections.abc import Iterable
from pathlib import Path

from qore.infrastructure.ctrader_demo_live_behavior_lab import (
    LiveBehaviorEvent,
    build_case_reports,
    case_reports_as_json,
    normalize_runtime_event,
)


def _read_jsonl(path: Path, *, source: str) -> tuple[LiveBehaviorEvent, ...]:
    if not path.exists():
        return ()
    rows: list[LiveBehaviorEvent] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            stripped = line.strip()
            if not stripped:
                continue
            try:
                raw = json.loads(stripped)
            except json.JSONDecodeError as error:
                raise RuntimeError(
                    f"{path}:{line_number}: invalid JSONL row"
                ) from error
            if not isinstance(raw, dict):
                raise RuntimeError(f"{path}:{line_number}: row must be object")
            rows.append(normalize_runtime_event(raw, source=source))
    return tuple(rows)


def _deduplicate(events: Iterable[LiveBehaviorEvent]) -> tuple[LiveBehaviorEvent, ...]:
    seen: set[str] = set()
    rows: list[LiveBehaviorEvent] = []
    for event in sorted(events, key=lambda item: item.observed_at):
        key = json.dumps(
            event.as_json(),
            sort_keys=True,
            separators=(",", ":"),
            default=str,
        )
        if key in seen:
            continue
        seen.add(key)
        rows.append(event)
    return tuple(rows)


def _markdown(reports) -> str:
    lines = [
        "# cTrader DEMO LIVE Behavior Lab",
        "",
        "Read-only reconstruction from existing cTrader DEMO runtime/execution evidence.",
        "This report does not change strategy, CIBO, Risk, orders, stops or targets.",
        "",
        f"Cases reconstructed: **{len(reports)}**",
        "",
    ]
    for report in reports:
        lines.extend(
            [
                f"## {report.case_id}",
                "",
                f"- Trader: {report.trader or 'UNKNOWN'}",
                f"- Symbol: {report.symbol or 'UNKNOWN'}",
                f"- First observed: {report.first_observed_at.isoformat()}",
                f"- Last observed: {report.last_observed_at.isoformat()}",
                f"- Events: {report.event_count}",
                f"- Stages: {json.dumps(report.stages, sort_keys=True)}",
                (
                    "- Requested volumes: "
                    f"{', '.join(report.requested_volumes) or 'NOT_OBSERVED'}"
                ),
                (
                    "- Requested stop risk: "
                    f"{', '.join(report.requested_stop_risks) or 'NOT_OBSERVED'}"
                ),
                (
                    "- Protection events: "
                    f"{', '.join(report.protection_events) or 'NOT_OBSERVED'}"
                ),
                (
                    "- Partial-close events: "
                    f"{', '.join(report.partial_close_events) or 'NOT_OBSERVED'}"
                ),
                f"- Exit events: {', '.join(report.exit_events) or 'NOT_OBSERVED'}",
                f"- Fault events: {', '.join(report.fault_events) or 'NONE'}",
                f"- Position path samples: {report.path_sample_count}",
                f"- Max unrealized PnL: {report.max_unrealized_pnl or 'NOT_OBSERVED'}",
                f"- Min unrealized PnL: {report.min_unrealized_pnl or 'NOT_OBSERVED'}",
                (
                    "- Max favorable price delta: "
                    f"{report.max_favorable_price_delta or 'NOT_OBSERVED'}"
                ),
                (
                    "- Max adverse price delta: "
                    f"{report.max_adverse_price_delta or 'NOT_OBSERVED'}"
                ),
                f"- Stop history: {', '.join(report.stop_history) or 'NOT_OBSERVED'}",
                f"- Volume history: {', '.join(report.volume_history) or 'NOT_OBSERVED'}",
                "",
                "Observations:",
            ]
        )
        if report.observations:
            lines.extend(f"- {item}" for item in report.observations)
        else:
            lines.append("- none")
        lines.extend(["", "Event sequence:", ""])
        lines.extend(f"1. {name}" for name in report.event_names)
        lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument(
        "--runtime-events",
        type=Path,
        default=None,
        help="Override runtime JSONL path.",
    )
    parser.add_argument(
        "--sink-events",
        type=Path,
        default=None,
        help="Override cTrader DEMO execution JSONL path.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="Override report directory.",
    )
    args = parser.parse_args()

    root = args.root.resolve()
    runtime_path = args.runtime_events or (
        root / "artifacts" / "ctrader_demo_free_runtime_events.jsonl"
    )
    sink_path = args.sink_events or (
        root / "var" / "ctrader_demo_free" / "events.jsonl"
    )
    output = args.output_dir or (
        root / "artifacts" / "ctrader_demo_live_behavior_lab"
    )
    output.mkdir(parents=True, exist_ok=True)

    events = _deduplicate(
        (
            *_read_jsonl(runtime_path, source="runtime"),
            *_read_jsonl(sink_path, source="sink"),
        )
    )
    reports = build_case_reports(events)

    (output / "events.normalized.json").write_text(
        json.dumps(
            [event.as_json() for event in events],
            indent=2,
            sort_keys=True,
            default=str,
        )
        + "\n",
        encoding="utf-8",
    )
    (output / "case-report.json").write_text(
        json.dumps(
            case_reports_as_json(reports),
            indent=2,
            sort_keys=True,
            default=str,
        )
        + "\n",
        encoding="utf-8",
    )
    (output / "case-report.md").write_text(
        _markdown(reports) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "runtime_events": str(runtime_path),
                "sink_events": str(sink_path),
                "event_count": len(events),
                "case_count": len(reports),
                "output_dir": str(output),
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
