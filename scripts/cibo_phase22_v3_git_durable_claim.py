from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from datetime import datetime
from pathlib import Path

from qore.infrastructure.cibo_phase22_v3_git_durable_claim import (
    prepare_phase22_v3_git_claim_files,
    verify_phase22_v3_git_durable_claim,
)


def main() -> None:
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
    verify.add_argument("--output", type=Path, required=True)
    verify.add_argument("--expected-run-id", type=int)
    verify.add_argument("--expected-run-attempt", type=int)

    args = parser.parse_args()
    if args.command == "prepare":
        claim = prepare_phase22_v3_git_claim_files(
            repo_root=args.repo_root,
            runner_git_sha=args.runner_git_sha,
            run_id=args.run_id,
            run_attempt=args.run_attempt,
            started_at=datetime.fromisoformat(args.started_at),
            store_root=args.store_root,
        )
        print(
            json.dumps(
                {
                    "candidate_id": claim.candidate_id,
                    "claim_receipt_sha256": claim.fingerprint(),
                    "claim_committed": claim.consumption_claim().claim_committed,
                    "outcomes_emitted": claim.consumption_claim().outcomes_emitted,
                    "fresh_access_authorized": False,
                },
                sort_keys=True,
            )
        )
        return

    evidence = verify_phase22_v3_git_durable_claim(
        repo_root=args.repo_root,
        branch_name=args.branch,
        remote_name=args.remote,
        expected_run_id=args.expected_run_id,
        expected_run_attempt=args.expected_run_attempt,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema": "qore.cibo.phase22.v3-git-durable-claim-evidence.v1",
        **asdict(evidence),
        "fingerprint": evidence.fingerprint(),
    }
    args.output.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "claim_commit_sha": evidence.claim_commit_sha,
                "source_head_sha": evidence.source_head_sha,
                "durable_claim_proven": evidence.durable_claim_proven,
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
