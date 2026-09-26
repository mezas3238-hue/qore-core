"""Generate a passive CIBO CMA shadow economic-floor report."""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any

from qore.infrastructure.cibo_cma_shadow_floor import classify_behavior_case
from qore.infrastructure.ctrader_demo_live_behavior_lab import LiveBehaviorCaseReport


def load_reports(path: Path) -> tuple[LiveBehaviorCaseReport, ...]:
    if not path.exists():
        return ()
    raw = json.loads(path.read_text(encoding="utf-8"))
    rows: object
    if isinstance(raw, list):
        rows = raw
    elif isinstance(raw, dict):
        rows = raw.get("cases", raw.get("reports", []))
    else:
        raise ValueError("case report root must be list/object")
    if not isinstance(rows, list):
        raise ValueError("case report rows must be list")
    return tuple(_parse_report(item) for item in rows)


def build_summary(
    reports: tuple[LiveBehaviorCaseReport, ...],
) -> dict[str, object]:
    by_trader: dict[str, Counter[str]] = defaultdict(Counter)
    for report in reports:
        observation = classify_behavior_case(report)
        counter = by_trader[observation.trader]
        counter["cases"] += 1
        counter[observation.status.value] += 1

    return {
        "total_cases": len(reports),
        "traders": {
            trader: dict(sorted(counter.items()))
            for trader, counter in sorted(by_trader.items())
        },
    }


def render_markdown(summary: dict[str, object]) -> str:
    traders = summary.get("traders")
    if not isinstance(traders, dict):
        raise ValueError("summary traders must be object")
    lines = [
        "# CIBO CMA Phase 7 — Shadow Economic Floor Report",
        "",
        f"- total cases: {summary['total_cases']}",
        "",
        "| Trader | Cases | Base recovered | Base not recovered | Insufficient |",
        "|---|---:|---:|---:|---:|",
    ]
    for trader, raw in sorted(traders.items()):
        if not isinstance(raw, dict):
            raise ValueError("trader summary must be object")
        lines.append(
            "| "
            + " | ".join(
                (
                    str(trader),
                    str(raw.get("cases", 0)),
                    str(raw.get("BASE_RECOVERED", 0)),
                    str(raw.get("BASE_NOT_RECOVERED", 0)),
                    str(raw.get("INSUFFICIENT_EVIDENCE", 0)),
                )
            )
            + " |"
        )
    lines.extend(
        (
            "",
            "Open/non-final historical cases remain insufficient by design.",
            "This report has no sizing or broker mutation authority.",
            "",
        )
    )
    return "\n".join(lines)


def _parse_report(value: object) -> LiveBehaviorCaseReport:
    if not isinstance(value, dict):
        raise ValueError("case report row must be object")
    return LiveBehaviorCaseReport(
        case_id=_text(value, "case_id"),
        trader=_optional_text(value.get("trader")),
        symbol=_optional_text(value.get("symbol")),
        first_observed_at=_datetime(value, "first_observed_at"),
        last_observed_at=_datetime(value, "last_observed_at"),
        event_count=_int(value, "event_count"),
        stages=_str_int_dict(value.get("stages")),
        event_names=_str_tuple(value.get("event_names")),
        requested_volumes=_str_tuple(value.get("requested_volumes")),
        requested_stop_risks=_str_tuple(value.get("requested_stop_risks")),
        protection_events=_str_tuple(value.get("protection_events")),
        partial_close_events=_str_tuple(value.get("partial_close_events")),
        exit_events=_str_tuple(value.get("exit_events")),
        fault_events=_str_tuple(value.get("fault_events")),
        settlement_events=_str_tuple(value.get("settlement_events")),
        realized_net_pnl=_optional_text(value.get("realized_net_pnl")),
        settlement_prices=_str_tuple(value.get("settlement_prices")),
        settled_source_volumes=_str_tuple(value.get("settled_source_volumes")),
        estimated_initial_risk_pnl=_optional_text(
            value.get("estimated_initial_risk_pnl")
        ),
        estimated_remaining_stop_pnl=_optional_text(
            value.get("estimated_remaining_stop_pnl")
        ),
        estimated_economic_floor_pnl=_optional_text(
            value.get("estimated_economic_floor_pnl")
        ),
        estimated_economic_floor_r=_optional_text(
            value.get("estimated_economic_floor_r")
        ),
        path_sample_count=_int(value, "path_sample_count"),
        max_unrealized_pnl=_optional_text(value.get("max_unrealized_pnl")),
        min_unrealized_pnl=_optional_text(value.get("min_unrealized_pnl")),
        max_favorable_price_delta=_optional_text(
            value.get("max_favorable_price_delta")
        ),
        max_adverse_price_delta=_optional_text(
            value.get("max_adverse_price_delta")
        ),
        stop_history=_str_tuple(value.get("stop_history")),
        volume_history=_str_tuple(value.get("volume_history")),
        observations=_str_tuple(value.get("observations")),
    )


def _text(value: dict[str, Any], key: str) -> str:
    raw = value.get(key)
    if not isinstance(raw, str) or not raw:
        raise ValueError(f"{key} must be text")
    return raw


def _optional_text(value: object) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError("optional text field must be string/null")
    return value


def _datetime(value: dict[str, Any], key: str) -> datetime:
    raw = _text(value, key)
    parsed = datetime.fromisoformat(raw)
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError(f"{key} must be timezone-aware")
    return parsed


def _int(value: dict[str, Any], key: str) -> int:
    raw = value.get(key)
    if not isinstance(raw, int) or isinstance(raw, bool):
        raise ValueError(f"{key} must be int")
    return raw


def _str_tuple(value: object) -> tuple[str, ...]:
    if value is None:
        return ()
    if not isinstance(value, list):
        raise ValueError("tuple source must be list")
    if not all(isinstance(item, str) for item in value):
        raise ValueError("tuple source items must be strings")
    return tuple(value)


def _str_int_dict(value: object) -> dict[str, int]:
    if value is None:
        return {}
    if not isinstance(value, dict):
        raise ValueError("stages must be object")
    result: dict[str, int] = {}
    for key, raw in value.items():
        if not isinstance(key, str):
            raise ValueError("stage key must be string")
        if not isinstance(raw, int) or isinstance(raw, bool):
            raise ValueError("stage count must be int")
        result[key] = raw
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("case_report", type=Path)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("artifacts/cibo_cma_phase7_shadow"),
    )
    args = parser.parse_args()

    reports = load_reports(args.case_report)
    summary = build_summary(reports)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / "summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    (args.output_dir / "summary.md").write_text(
        render_markdown(summary),
        encoding="utf-8",
    )
    print(json.dumps(summary, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
