"""Build a CE2I Phase-2 sizing reconstruction report from DEMO sink JSONL."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from dataclasses import asdict
from decimal import Decimal
from pathlib import Path
from collections.abc import Mapping

from qore.infrastructure.cibo_capital_efficiency_reconstruction import (
    SIZING_PATH_CONTRACTS,
    ReconstructionStatus,
    SizingDecisionReconstruction,
    reconstruct_sizing_ledger,
)


def load_jsonl(path: Path) -> tuple[Mapping[str, object], ...]:
    rows: list[Mapping[str, object]] = []
    if not path.exists():
        return ()
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            stripped = line.strip()
            if not stripped:
                continue
            value = json.loads(stripped)
            if not isinstance(value, dict):
                raise ValueError("CE2I input JSONL rows must be objects")
            rows.append(value)
    return tuple(rows)


def build_summary(
    ledger: tuple[SizingDecisionReconstruction, ...],
) -> dict[str, object]:
    traders: dict[str, object] = {}
    for trader in SIZING_PATH_CONTRACTS:
        rows = tuple(item for item in ledger if item.trader == trader)
        complete = sum(
            item.status is ReconstructionStatus.COMPLETE
            for item in rows
        )
        partial = len(rows) - complete
        unused = sum(
            (
                item.unused_strategy_risk_usd
                for item in rows
                if item.unused_strategy_risk_usd is not None
            ),
            Decimal(0),
        )
        requested_risk = sum(
            (item.requested_stop_risk for item in rows),
            Decimal(0),
        )
        missing = Counter(
            field
            for item in rows
            for field in item.missing_fields
        )
        traders[trader] = {
            "observed_cases": len(rows),
            "complete_cases": complete,
            "partial_cases": partial,
            "requested_stop_risk_usd": format(requested_risk, "f"),
            "unused_strategy_risk_usd": format(unused, "f"),
            "missing_field_counts": dict(sorted(missing.items())),
        }
    return {
        "total_submit_cases": len(ledger),
        "complete_cases": sum(
            item.status is ReconstructionStatus.COMPLETE
            for item in ledger
        ),
        "partial_cases": sum(
            item.status is ReconstructionStatus.PARTIAL
            for item in ledger
        ),
        "traders": traders,
    }


def render_markdown(summary: Mapping[str, object]) -> str:
    lines = [
        "# CE2I Phase 2 — Sizing Reconstruction Report",
        "",
        f"- total submit cases: {summary['total_submit_cases']}",
        f"- complete cases: {summary['complete_cases']}",
        f"- partial cases: {summary['partial_cases']}",
        "",
        "| Trader | Cases | Complete | Partial | Requested stop risk | Unused strategy risk |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    traders = summary["traders"]
    if not isinstance(traders, dict):
        raise ValueError("CE2I summary traders must be dict")
    for trader in SIZING_PATH_CONTRACTS:
        row = traders[trader]
        if not isinstance(row, dict):
            raise ValueError("CE2I trader summary must be dict")
        lines.append(
            "| "
            + " | ".join(
                (
                    trader,
                    str(row["observed_cases"]),
                    str(row["complete_cases"]),
                    str(row["partial_cases"]),
                    str(row["requested_stop_risk_usd"]),
                    str(row["unused_strategy_risk_usd"]),
                )
            )
            + " |"
        )
    lines.extend(
        (
            "",
            "## Evidence gaps",
            "",
            "Missing fields are reported rather than inferred from current source.",
        )
    )
    for trader in SIZING_PATH_CONTRACTS:
        row = traders[trader]
        if not isinstance(row, dict):
            continue
        missing = row["missing_field_counts"]
        lines.append(f"- **{trader}**: {json.dumps(missing, sort_keys=True)}")
    return "\n".join(lines) + "\n"


def _jsonable(row: SizingDecisionReconstruction) -> dict[str, object]:
    value = asdict(row)
    value["status"] = row.status.value
    for key, item in tuple(value.items()):
        if isinstance(item, Decimal):
            value[key] = format(item, "f")
    return value


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--events",
        type=Path,
        default=Path("var/ctrader_demo_free/events.jsonl"),
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("artifacts/cibo_ce2i_phase2"),
    )
    args = parser.parse_args()

    events = load_jsonl(args.events)
    ledger = reconstruct_sizing_ledger(events)
    summary = build_summary(ledger)

    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / "sizing-reconstruction.json").write_text(
        json.dumps([_jsonable(item) for item in ledger], indent=2, sort_keys=True),
        encoding="utf-8",
    )
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
