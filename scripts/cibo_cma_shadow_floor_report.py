"""Generate a passive CIBO CMA shadow economic-floor report."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from qore.infrastructure.cibo_cma_shadow_floor_report import (
    build_summary,
    load_reports,
    render_markdown,
)


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
