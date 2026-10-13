"""GitHub Actions wrapper for real read-only Git object custody evidence.

Git SHA/blob ancestry is NOT proof that market outcomes were never viewed.
Validates the checked-out branch and official GitHub Actions environment, then
issues a hashed research continuity witness without enabling any experiment.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

from qore.infrastructure.trader_lab.qore_research_git_custody_v1 import (
    verify_readonly_git_custody,
)
from qore.infrastructure.trader_lab.qore_research_zero_budget_intake_v1 import (
    ResearchIntakeError,
)

_REPOSITORY = "mezas3238-hue/qore-core"
_REF = "refs/heads/research/qore-cf11-git-custody-readonly-20261013"


def main() -> None:
    if (
        os.environ.get("GITHUB_REPOSITORY") != _REPOSITORY
        or os.environ.get("GITHUB_REF") != _REF
        or os.environ.get("GITHUB_EVENT_NAME") not in ("push", "workflow_dispatch")
        or os.environ.get("GITHUB_ACTIONS") != "true"
    ):
        raise ResearchIntakeError("GIT_CUSTODY_UNTRUSTED_CI_ENVIRONMENT")
    commit = os.environ.get("GITHUB_SHA", "")
    receipt = verify_readonly_git_custody(commit)
    if (
        receipt["draft_count"] != 0
        or receipt["new_prereg_scientifically_frozen"] is not False
        or receipt["can_open_holdout"] is not False
        or receipt["can_promote_trader"] is not False
        or receipt["market_data_spend_usd"] != 0
    ):
        raise ResearchIntakeError("GIT_CUSTODY_FALSE_RESEARCH_PROMOTION")
    destination = Path(os.environ["RUNNER_TEMP"]) / "qore_git_custody_readonly.json"
    destination.write_text(json.dumps(receipt, sort_keys=True, indent=2) + "\n")
    print("GIT_CUSTODY_EIA_PREREG_BEFORE_ORIGINAL_RESULT_VERIFIED")
    print("GIT_CUSTODY_FUTURE_PREREG_DRAFT_MANIFEST_STILL_EMPTY_VERIFIED")
    print("GIT_CUSTODY_RECEIPT_SHA256", receipt["custody_receipt_sha256"])
    print("NO_NEW_PREREG_NO_NEW_OUTCOME_NO_LIVE_NO_HOLDOUT")


if __name__ == "__main__":
    main()
