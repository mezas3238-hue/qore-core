"""Materialize the immutable pre-outcome Phase22 V4 execution manifest envelope."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
from pathlib import Path
from typing import Any

from qore.infrastructure.cibo_phase22_v4_execution_manifest import (
    build_phase22_v4_execution_manifest,
)

SCHEMA = "qore.cibo.phase22.v4-execution-manifest-freeze.v1"
SOVEREIGN_BRANCH = "agent/cibo-integrator-ab-001"
_SHA1_RE = re.compile(r"^[0-9a-f]{40}$")


def canonical_sha256(payload: dict[str, Any]) -> str:
    raw = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("utf-8")
    return "sha256:" + hashlib.sha256(raw).hexdigest()


def build_freeze_payload(*, source_head_sha: str) -> dict[str, Any]:
    if _SHA1_RE.fullmatch(source_head_sha) is None:
        raise ValueError("V4 execution manifest freeze source HEAD invalid")
    manifest = build_phase22_v4_execution_manifest()
    payload: dict[str, Any] = {
        "schema": SCHEMA,
        "source_head_sha": source_head_sha,
        "target_branch": SOVEREIGN_BRANCH,
        "candidate_id": manifest.candidate_id,
        "execution_manifest_sha256": manifest.fingerprint(),
        "execution_manifest": manifest.payload(),
        "exact_seven_trader_bindings": True,
        "source_receipt_bound": True,
        "policy_frozen": True,
        "advanced_scientific_eligibility_frozen": True,
        "provider_calibration_bound": True,
        "provider_numeric_freeze_bound": True,
        "parity_manifest_bound": True,
        "vt31_six_field_abi_bound": True,
        "v4_store_namespace_required": True,
        "v2_store_reuse_authorized": False,
        "v3_store_reuse_authorized": False,
        "fresh_outcomes_executed": False,
        "owner_authorization_present": False,
        "broker_mutation_authorized": False,
        "live_authorized": False,
        "real_capital_authorized": False,
        "production_authorized": False,
        "merge_authorized": False,
        "productive_authority": False,
    }
    payload["freeze_sha256"] = canonical_sha256(payload)
    return payload


def _git_head(repo_root: Path) -> str:
    return subprocess.check_output(
        ("git", "-C", str(repo_root), "rev-parse", "HEAD"),
        text=True,
    ).strip()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    parser.add_argument("--source-head", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    repo_root = args.repo_root.resolve()
    actual = _git_head(repo_root)
    if actual != args.source_head:
        raise SystemExit(
            f"V4 manifest source HEAD drift: expected={args.source_head} actual={actual}"
        )
    payload = build_freeze_payload(source_head_sha=args.source_head)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "source_head_sha": payload["source_head_sha"],
                "execution_manifest_sha256": payload[
                    "execution_manifest_sha256"
                ],
                "freeze_sha256": payload["freeze_sha256"],
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
