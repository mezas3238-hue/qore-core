#!/usr/bin/env python3
"""Inventory slow legacy CIBO GitHub workflows; never mislabel cached replay as new evidence."""
from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(".github/workflows")
MAX_LEGACY_FANOUT = 92  # Measured baseline on 2026-10-08. Never allow growth.

MIGRATED = {
    "carrier37655-medium-context-stop-ridge",
    "carrier37655-medium-balanced-regime-ridge",
    "carrier37655-medium-extreme-cluster-ridge",
    "carrier37772-attack-context-stop-ridge",
    "carrier37655-attack-2020-context2-ridge",
    "carrier37810-crs15-pressure-depth-ridge",
    "carrier37990-medium-stop-fine-ridge",
    "carrier37772-pressure-cliff-micro-ridge",
    "carrier37990-dual-pressure-2021-ridge",
    "carrier37772-direct-cap-taper-ridge",
    "carrier37772-h1-balanced-522-ridge",
}
FANOUT = re.compile(r"(?m)^\s*run_case\s+[^\n]+\s+&\s*$")
LEGACY_PY = 'python scripts/cibo_trader_lab_three_mode_ceiling.py'


def main() -> None:
    all_files = sorted(ROOT.glob("cibo-trader-lab-*.yml"))
    slow = []
    migrated = []
    other = []
    errors = []
    for file in all_files:
        body = file.read_text(encoding="utf-8")
        sample = {
            "workflow": file.name,
            "cases": len(FANOUT.findall(body)),
            "legacy_python": LEGACY_PY in body,
            "uses_fast_batch": "python scripts/cibo_trader_lab_batch_runner.py" in body,
        }
        if sample["cases"] and sample["legacy_python"]:
            slow.append(sample)
        elif sample["uses_fast_batch"]:
            migrated.append(sample)
        else:
            other.append(sample)
    if len(slow) > MAX_LEGACY_FANOUT:
        errors.append(
            f"legacy oversubscribed workflow count increased: {len(slow)} > "
            f"{MAX_LEGACY_FANOUT}; new research must use prepared batch"
        )
    for name in sorted(MIGRATED):
        f = ROOT / f"cibo-trader-lab-{name}.yml"
        if not f.is_file():
            errors.append(f"migrated workflow missing: {f}")
            continue
        txt = f.read_text(encoding="utf-8")
        if (FANOUT.search(txt) is not None or LEGACY_PY in txt
                or "python scripts/cibo_trader_lab_batch_runner.py" not in txt
                or "timeout-minutes: 3" not in txt
                or "--m5-cache-dir" not in txt):
            errors.append(f"performance contract regression: {f}")
    report = {
        "schema": "qore.cibo.trader_lab.runtime_audit.v1",
        "scanned": len(all_files),
        "legacy_oversubscribed": len(slow),
        "fast_batch": len(migrated),
        "other": len(other),
        "top_legacy": sorted(slow, key=lambda x: -x["cases"])[:30],
        "all_legacy": slow,
        "migrated_slo_contracts": len(MIGRATED),
        "errors": errors,
    }
    path = Path("cibo-trader-lab-runtime-audit.json")
    path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print("QORE_CIBO_TRADER_LAB_RUNTIME_AUDIT=" + json.dumps(
        {k: v for k, v in report.items() if k != "all_legacy"}, sort_keys=True
    ))
    if errors:
        raise SystemExit("CIBO migrated fast-path audit FAILED")


if __name__ == "__main__":
    main()
