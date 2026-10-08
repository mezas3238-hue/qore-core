#!/usr/bin/env python3
"""Inventory slow legacy CIBO GitHub workflows; never mislabel cached replay as new evidence."""
from __future__ import annotations

import json
import os
import re
import subprocess
from pathlib import Path

ROOT = Path(".github/workflows")
MIGRATED = {
    "carrier36509-dual-medium-rescue-ridge",
    "carrier36509-rescue-dd-envelope-ridge",
    "carrier37082-medium-trough-context2-ridge",
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



def _check_changed_workflow_regressions() -> list[str]:
    """Compare new/modified workflows with the actual event parent, not a
    stale repository-wide count while other research architects are working.
    Existing legacy jobs are inventory backlog, but adding new/extra
    fanout is a performance regression.
    """
    event_path = os.environ.get("GITHUB_EVENT_PATH")
    if not event_path:
        return []
    event = json.loads(Path(event_path).read_text(encoding="utf-8"))
    if os.environ.get("GITHUB_EVENT_NAME") == "pull_request":
        # Checkout of a pull request points at a synthetic merge commit.
        # Its first parent is the real target-branch baseline; event.before
        # is not the PR merge base and may be unavailable in the checkout.
        base = subprocess.run(
            ["git", "rev-parse", "HEAD^1"],
            check=True, text=True, capture_output=True,
        ).stdout.strip()
    else:
        base = event.get("before")
    if not base or not re.fullmatch(r"[0-9a-f]{40}", base) or base == "0" * 40:
        return []
    if subprocess.run(
        ["git", "cat-file", "-e", f"{base}^{{commit}}"],
        check=False, capture_output=True,
    ).returncode:
        subprocess.run(
            ["git", "fetch", "--no-tags", "origin", base],
            check=True, text=True, capture_output=True,
        )
    diff = subprocess.run(
        ["git", "diff", "--name-only", base, "HEAD", "--", ".github/workflows"],
        check=False, text=True, capture_output=True,
    )
    if diff.returncode:
        raise RuntimeError("cannot verify performance baseline: " + diff.stderr)
    changed = diff.stdout.splitlines()
    errors = []
    for raw_path in changed:
        file = Path(raw_path)
        if not file.name.startswith("cibo-trader-lab-") or file.suffix != ".yml":
            continue
        if not file.is_file():
            continue
        current = file.read_text(encoding="utf-8")
        old_result = subprocess.run(
            ["git", "show", f"{base}:{raw_path}"],
            check=False, text=True, capture_output=True,
        )
        previous = old_result.stdout if old_result.returncode == 0 else ""
        old_count = len(FANOUT.findall(previous)) if LEGACY_PY in previous else 0
        new_count = len(FANOUT.findall(current)) if LEGACY_PY in current else 0
        if new_count > old_count:
            errors.append(
                f"new oversubscribed replay fanout: {raw_path} "
                f"({old_count} -> {new_count}); use the batched runner"
            )
    return errors


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
            # The 2026-10-08 36509 incident proved that a job can
            # report "success" with no Rank/Upload stage declared.
            # Fail closed for every batched research workflow, not just
            # a static allowlist: science requires published evidence.
            ranking = re.search(r"(?m)^      - name: Rank\b", body)
            upload = re.search(
                r"(?m)^      - uses: actions/upload-artifact@v4\s*$", body
            )
            rank_offset = ranking.start() if ranking else -1
            upload_offset = upload.start() if upload else -1
            if not ranking or not upload or upload_offset <= rank_offset:
                errors.append(
                    f"missing ordered Rank/Upload evidence gates: {file}"
                )
            if ("if-no-files-found: error" not in body
                    or 'result/*.json' not in body):
                errors.append(
                    f"missing mandatory JSON artifact fail-closed gate: {file}"
                )
        else:
            other.append(sample)
    errors.extend(_check_changed_workflow_regressions())
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
