"""Write Git-anchored source-unverified prospective research specifications.

Compares manifest bytes to committed HEAD content. It does not access EIA,
broker, any market price, strategy outcome, original holdout or an account.
"""
from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path
from typing import Any

from qore.infrastructure.trader_lab.qore_research_prereg_source_gate_v1 import (
    ResearchIntakeError,
    freeze_prereg_manifest,
)

PROPOSAL_PATH = "docs/research/QORE_RESEARCH_ZERO_BUDGET_PROPOSALS_2026-10-13.json"
PREREG_PATH = "docs/research/QORE_RESEARCH_FUTURE_HYPOTHESES_PREREG_2026-10-13.json"


def _git(*args: str) -> bytes:
    return subprocess.run(
        ["git", *args],
        capture_output=True, check=True, timeout=12,
    ).stdout


def _read_committed_json(path: str) -> dict[str, Any]:
    expected = _git("show", f"HEAD:{path}")
    observed = Path(path).read_bytes()
    if observed != expected:
        raise ResearchIntakeError(f"MANIFEST_NOT_IDENTICAL_TO_GIT_HEAD_{path}")
    if len(observed) > 512_000:
        raise ResearchIntakeError("MANIFEST_TOO_LARGE")
    value: Any = json.loads(observed)
    if type(value) is not dict:
        raise ResearchIntakeError("MANIFEST_NOT_AN_OBJECT")
    return value


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    head_sha = _git("rev-parse", "HEAD").decode("ascii").strip()
    if not _git("status", "--porcelain", "--", PROPOSAL_PATH, PREREG_PATH) == b"":
        raise ResearchIntakeError("MANIFEST_WORKTREE_IS_DIRTY")
    proposals = _read_committed_json(PROPOSAL_PATH)
    manifest = _read_committed_json(PREREG_PATH)
    receipt = freeze_prereg_manifest(
        manifest, proposals, git_commit_sha=head_sha,
    )
    if (
        receipt["data_spend_usd"] != 0
        or receipt["source_market_authority_obtained"] is not False
        or receipt["economic_backtest_executed"] is not False
        or receipt["holdout_read"] is not False
    ):
        raise ResearchIntakeError("SOURCE_OR_ECONOMIC_PRIVILEGES_FORGED")
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(
        json.dumps(receipt, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print("GIT_PREREG_HEAD", head_sha)
    print("PREREG_COUNT", receipt["frozen_count"])
    print("RECEIPT_SHA256", receipt["receipt_sha256"])
    print("ZERO_BUDGET_SPEC_ONLY_SOURCE_AUTHORITY_REQUIRED_NO_PRICES_NO_HOLDOUT")


if __name__ == "__main__":
    main()
