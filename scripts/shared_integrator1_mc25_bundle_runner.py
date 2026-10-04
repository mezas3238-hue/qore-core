#!/usr/bin/env python3
"""Integrator-1 glue runner for canonical MC25 V3B performance stress.

The runner only reconstructs sealed consumed inputs from a frozen Shared Lab
dataset bundle and invokes the canonical producer script. It does not redefine
the stress scenarios, gates, representation, probe, targets or promotion law.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path
from typing import Any

SCHEMA = "QORE_SHARED_INTEGRATOR_1_MC25_CONSUMED_BUNDLE_001"
EXPECTED_ARTIFACTS = {
    "freeze": 10906064254,
    "holdout_e": 10908500161,
    "replication_d": 10908077821,
    "r8_consumed_market_evidence": 10402199719,
    "r6_consumed_market_evidence": 10389112524,
    "r5_consumed_market_evidence": 10380044761,
    "lineage_integrity_stress": 11128707360,
}
REQUIRED = (
    "freeze/wp04-predictive-nonlinear-probe-v3b.json",
    "freeze/SHA256SUMS",
    "holdout/result/wp04-v3b-holdout-e.json",
    "holdout/result/SHA256SUMS",
    "holdout/fresh/NAS100/market-evidence.json",
    "holdout/fresh/SP500/market-evidence.json",
    "holdout/fresh/US30/market-evidence.json",
    "replication/result/wp04-v3b-replication-d.json",
    "replication/result/SHA256SUMS",
    "replication/fresh/NAS100/market-evidence.json",
    "replication/fresh/SP500/market-evidence.json",
    "replication/fresh/US30/market-evidence.json",
    "r8/fresh/EVIDENCE-SHA256SUMS",
    "r8/fresh/NAS100/market-evidence.json",
    "r8/fresh/SP500/market-evidence.json",
    "r8/fresh/US30/market-evidence.json",
    "r6/fresh/EVIDENCE-SHA256SUMS",
    "r6/fresh/NAS100/market-evidence.json",
    "r6/fresh/SP500/market-evidence.json",
    "r6/fresh/US30/market-evidence.json",
    "r5/fresh/EVIDENCE-SHA256SUMS",
    "r5/fresh/NAS100/market-evidence.json",
    "r5/fresh/SP500/market-evidence.json",
    "r5/fresh/US30/market-evidence.json",
    "lineage/result/mc25-wp04-v3b-lineage-integrity-stress.json",
)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _verify_sums(base: Path, sums: Path) -> None:
    for raw in sums.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line:
            continue
        parts = line.split(maxsplit=1)
        if len(parts) != 2:
            raise ValueError(f"invalid checksum row in {sums}: {raw!r}")
        expected, name = parts
        name = name.lstrip("*")
        target = (base / name).resolve()
        if base.resolve() not in target.parents and target != base.resolve():
            raise ValueError(f"checksum escapes bundle root: {name}")
        if not target.is_file():
            raise ValueError(f"checksummed file missing: {target}")
        actual = _sha256(target)
        if actual != expected:
            raise ValueError(f"sha256 mismatch for {target}: {actual} != {expected}")


def _load(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return payload


def _validate_bundle(root: Path) -> None:
    manifest = _load(root / "MC25-BUNDLE-MANIFEST.json")
    if manifest.get("schema") != SCHEMA:
        raise ValueError("MC25 bundle schema mismatch")
    if manifest.get("source_artifacts") != EXPECTED_ARTIFACTS:
        raise ValueError("MC25 source artifact lineage mismatch")
    for relative in REQUIRED:
        if not (root / relative).is_file():
            raise ValueError(f"MC25 bundle required file missing: {relative}")

    _verify_sums(root / "freeze", root / "freeze" / "SHA256SUMS")
    _verify_sums(
        root / "holdout" / "result",
        root / "holdout" / "result" / "SHA256SUMS",
    )
    _verify_sums(
        root / "replication" / "result",
        root / "replication" / "result" / "SHA256SUMS",
    )
    for partition in ("r8", "r6", "r5"):
        _verify_sums(
            root / partition,
            root / partition / "fresh" / "EVIDENCE-SHA256SUMS",
        )

    lineage = _load(
        root / "lineage" / "result"
        / "mc25-wp04-v3b-lineage-integrity-stress.json"
    )
    if lineage.get("status") != "MC25_WP04_V3B_LINEAGE_INTEGRITY_STRESS_PASS":
        raise ValueError("MC25 lineage-integrity stress is not sealed PASS")
    if lineage.get("lineage_integrity_stress_pass") is not True:
        raise ValueError("MC25 lineage-integrity pass flag missing")
    if lineage.get("promotion_allowed") is not False:
        raise ValueError("lineage stage must not grant promotion")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    if not zipfile.is_zipfile(args.dataset):
        raise SystemExit("MC25 Shared Lab dataset must be a ZIP")

    with tempfile.TemporaryDirectory(prefix="qore-i1-mc25-") as tmp:
        root = Path(tmp)
        with zipfile.ZipFile(args.dataset) as archive:
            archive.extractall(root)
        _validate_bundle(root)

        command = [
            sys.executable,
            "scripts/shared_mc25_wp04_v3b_performance_stress.py",
            "--freeze",
            str(root / "freeze" / "wp04-predictive-nonlinear-probe-v3b.json"),
            "--holdout-result",
            str(root / "holdout" / "result" / "wp04-v3b-holdout-e.json"),
            "--replication-result",
            str(root / "replication" / "result" / "wp04-v3b-replication-d.json"),
        ]
        for partition in ("r8", "r6", "r5"):
            command += [
                f"--{partition}-nas",
                str(root / partition / "fresh" / "NAS100" / "market-evidence.json"),
                f"--{partition}-sp",
                str(root / partition / "fresh" / "SP500" / "market-evidence.json"),
                f"--{partition}-us",
                str(root / partition / "fresh" / "US30" / "market-evidence.json"),
            ]
        for prefix, folder in (("holdout", "holdout"), ("replication", "replication")):
            command += [
                f"--{prefix}-nas",
                str(root / folder / "fresh" / "NAS100" / "market-evidence.json"),
                f"--{prefix}-sp",
                str(root / folder / "fresh" / "SP500" / "market-evidence.json"),
                f"--{prefix}-us",
                str(root / folder / "fresh" / "US30" / "market-evidence.json"),
            ]
        command += ["--output", str(args.output)]
        completed = subprocess.run(command, check=False)
        raise SystemExit(completed.returncode)


if __name__ == "__main__":
    main()
