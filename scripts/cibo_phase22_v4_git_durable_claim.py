"""CLI for the Phase22 V4 Git-backed durable claim barrier."""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path

from qore.infrastructure.cibo_phase22_v4_git_durable_claim import (
    prepare_phase22_v4_git_claim_files,
    verify_phase22_v4_git_durable_claim,
)


def main() -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)

    prepare = sub.add_parser("prepare")
    prepare.add_argument("--repo-root", type=Path, required=True)
    prepare.add_argument("--runner-git-sha", required=True)
    prepare.add_argument("--run-id", type=int, required=True)
    prepare.add_argument("--run-attempt", type=int, required=True)
    prepare.add_argument("--started-at", required=True)
    prepare.add_argument("--store-root", type=Path, required=True)

    verify = sub.add_parser("verify")
    verify.add_argument("--repo-root", type=Path, required=True)
    verify.add_argument("--branch", required=True)
    verify.add_argument("--remote", default="origin")
    verify.add_argument("--expected-run-id", type=int)
    verify.add_argument("--expected-run-attempt", type=int)
    verify.add_argument("--output", type=Path)

    args = parser.parse_args()
    if args.command == "prepare":
        claim = prepare_phase22_v4_git_claim_files(
            repo_root=args.repo_root,
            runner_git_sha=args.runner_git_sha,
            run_id=args.run_id,
            run_attempt=args.run_attempt,
            started_at=datetime.fromisoformat(args.started_at),
            store_root=args.store_root,
        )
        print(json.dumps({"claim_sha256": claim.fingerprint()}, sort_keys=True))
        return 0

    evidence = verify_phase22_v4_git_durable_claim(
        repo_root=args.repo_root,
        branch_name=args.branch,
        remote_name=args.remote,
        expected_run_id=args.expected_run_id,
        expected_run_attempt=args.expected_run_attempt,
    )
    payload = {
        "source_head_sha": evidence.source_head_sha,
        "claim_commit_sha": evidence.claim_commit_sha,
        "remote_head_sha": evidence.remote_head_sha,
        "branch_name": evidence.branch_name,
        "claim_receipt_sha256": evidence.claim_receipt_sha256,
        "claim_file_sha256": evidence.claim_file_sha256,
        "consumption_file_sha256": evidence.consumption_file_sha256,
        "changed_paths": list(evidence.changed_paths),
        "remote_claim_observed": evidence.remote_claim_observed,
        "durable_claim_proven": evidence.durable_claim_proven,
        "productive_authority": evidence.productive_authority,
        "evidence_sha256": evidence.fingerprint(),
    }
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(
            json.dumps(payload, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    print(json.dumps(payload, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
