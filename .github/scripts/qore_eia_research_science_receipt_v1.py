"""Verify original GitHub Actions evidence before QORE Research / Lab handoff.

Never recompute a hypothesis using held-out prices. Reads only the published
outcome JSON from the successful 2026-10-13 source run via GitHub artifact.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import urllib.request
from pathlib import Path
from typing import Any

from qore.infrastructure.trader_lab.qore_eia_research_science_handoff_v1 import (
    PREREG_COMMIT,
    RESULT_RUN_COMMIT,
    SOURCE_ARTIFACT_ID,
    SOURCE_ARTIFACT_ZIP_SHA256,
    SOURCE_RUN_ID,
    ResearchHandoffError,
    build_handoff_receipt,
)

REPOSITORY = "mezas3238-hue/qore-core"
JSON_NAME = "qore_futures_a_eia_f1f2_prereg_dev_diag_only.json"


def _trusted_github_api(path: str) -> dict[str, Any]:
    token = os.environ.get("GITHUB_TOKEN", "")
    if not token:
        raise ResearchHandoffError("MISSING_ACTIONS_READ_TOKEN")
    url = f"https://api.github.com/repos/{REPOSITORY}/{path}"
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": "QORE-RESEARCH-SCIENCE-RECEIPT/1.0",
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        },
    )
    with urllib.request.urlopen(request, timeout=20) as response:
        content = response.read(80_001)
    if len(content) > 80_000:
        raise ResearchHandoffError("GITHUB_METADATA_OVERSIZE")
    answer: dict[str, Any] = json.loads(content)
    return answer


def _verify_original_source_run() -> None:
    run = _trusted_github_api(f"actions/runs/{SOURCE_RUN_ID}")
    if (
        run.get("head_sha") != RESULT_RUN_COMMIT
        or run.get("conclusion") != "success"
        or run.get("repository", {}).get("full_name") != REPOSITORY
    ):
        raise ResearchHandoffError("NOT_THE_ORIGINAL_SUCCESSFUL_RUN")
    artifact = _trusted_github_api(f"actions/artifacts/{SOURCE_ARTIFACT_ID}")
    if (
        artifact.get("digest") != f"sha256:{SOURCE_ARTIFACT_ZIP_SHA256}"
        or artifact.get("expired") is not False
        or artifact.get("workflow_run", {}).get("id") != SOURCE_RUN_ID
    ):
        raise ResearchHandoffError("SOURCE_ARTIFACT_DIGEST_OR_RUN_MISMATCH")
    # Git ancestry establishes ordering of committed prereg versus runner code,
    # not a claim of total researcher blindness outside the Git record.
    check = subprocess.run(
        ["git", "merge-base", "--is-ancestor", PREREG_COMMIT, RESULT_RUN_COMMIT],
        check=False,
        capture_output=True,
        timeout=10,
    )
    if check.returncode != 0:
        raise ResearchHandoffError("PREREG_IS_NOT_ANCESTOR_OF_RESULT_RUN")


def main() -> None:
    arg = argparse.ArgumentParser()
    arg.add_argument("--input", type=Path, required=True)
    arg.add_argument("--output", type=Path, required=True)
    args = arg.parse_args()
    _verify_original_source_run()
    if args.input.name != JSON_NAME:
        raise ResearchHandoffError("UNEXPECTED_RESULT_ARTIFACT_NAME")
    raw = json.loads(args.input.read_text(encoding="utf-8"))
    witness = build_handoff_receipt(raw)
    output = witness.to_json()
    output["github_artifact_digest_verified"] = True
    output["prereg_ancestor_verified"] = True
    output["scientific_closure_only_not_eligibility"] = True
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(output, sort_keys=True, indent=2) + "\n", encoding="utf-8"
    )
    print("QORE_RESEARCH_SCIENCE_STAGE", output["cibo_research_contract_stage"])
    print("TRADER_LAB_STATE", output["trader_lab_state"])
    print("EIA_PREREG_SCIENTIFIC_DECISION", output["qore_research_classification"])
    print("PROVENANCE_SOURCE_RUN", output["source_run_id"])
    print("TRADER_LAB_EVIDENCE_PRODUCED", output["trader_lab_stage_evidence_produced"])
    print("NO_OOS_NO_REAL_FILL_NO_CIBO_AUTHORITY_NO_DEMO")


if __name__ == "__main__":
    main()
