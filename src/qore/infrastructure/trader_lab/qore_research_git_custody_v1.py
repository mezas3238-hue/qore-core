"""Read-only Git custody: real historical EIA commit + empty prereg draft baseline.

This module proves only Git object ancestry and exact committed bytes.
It DOES NOT prove outcome blindness, data rights, economic edge, or source as-of.
An empty draft manifest is not a sealed preregistration for any new candidate.
"""
from __future__ import annotations

import hashlib
import json
import re
import subprocess
from typing import Any, NoReturn

from qore.infrastructure.trader_lab.qore_research_prereg_draft_gate_v1 import (
    MANIFEST_SCHEMA,
)
from qore.infrastructure.trader_lab.qore_research_zero_budget_intake_v1 import (
    ResearchIntakeError,
)

SCHEMA = "qore.research.git-custody-readonly.v1"
EIA_PREREG_COMMIT = "00065e6df7450cac707f983858ca39eed7b30c47"
EIA_RESULT_COMMIT = "25b8d2fc18c02992ff1115bbb117cc42438de891"
EIA_PREREG_PATH = (
    "docs/research/"
    "QORE_FUTURES_A_EIA_WTI_NG_F1F2_PREDICTIVE_SCREEN_PREREG_2026-10-13.md"
)
EIA_PREREG_BLOB_SHA = "cb73347a17d7d08292efce2a5843827b35a5e34d"
DRAFT_BASELINE_COMMIT = "19ed90def222f18591c5bb7b03c8928e8a597c77"
DRAFT_PATH = "docs/research/QORE_RESEARCH_PREREG_DRAFTS_2026-10-13.json"
DRAFT_BASELINE_BLOB_SHA = "f23e2ef9995776d913848a24f7811cbd8fc392e5"
_HEX40 = re.compile(r"[a-f0-9]{40}\Z")


def _fail(code: str) -> NoReturn:
    raise ResearchIntakeError("GIT_CUSTODY_" + code)


def _git(*parts: str) -> bytes:
    """No shell, no network, no writes; fixed verbs and only pinned refs/paths."""
    try:
        run = subprocess.run(
            ["git", *parts], capture_output=True, check=False, timeout=12,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise ResearchIntakeError("GIT_CUSTODY_COMMAND_UNAVAILABLE") from exc
    if run.returncode != 0:
        _fail("GIT_COMMAND_FAILED")
    return run.stdout


def _strict_sha(value: Any) -> str:
    if type(value) is not str or not _HEX40.fullmatch(value):
        _fail("INVALID_COMMIT_SHA")
    return value


def _blob(revision: str, path: str, expected: str) -> bytes:
    # Rev-parse verifies the Git object type and content identity, not a
    # self-declared SHA256 supplied in JSON by an untrusted caller.
    obj = _git("rev-parse", f"{revision}:{path}").decode("ascii").strip()
    if obj != expected:
        _fail("HISTORICAL_BLOB_CHANGED_OR_MISSING")
    data = _git("show", f"{revision}:{path}")
    computed = hashlib.sha1(  # nosec: Git SHA-1 object identifier, not a signature
        b"blob " + str(len(data)).encode("ascii") + b"\x00" + data
    ).hexdigest()
    if computed != obj:
        _fail("GIT_BLOB_BYTES_MISMATCH")
    return data


def _ancestor(before: str, after: str) -> None:
    # Exit 0 denotes ancestry. Other codes MUST fail closed; do not treat
    # equal commits as a prereg-before-outcome ordering.
    if before == after:
        _fail("EQUAL_COMMITS_NOT_CAUSAL_ORDER")
    try:
        run = subprocess.run(
            ["git", "merge-base", "--is-ancestor", before, after],
            capture_output=True, check=False, timeout=12,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise ResearchIntakeError("GIT_CUSTODY_ANCESTRY_UNAVAILABLE") from exc
    if run.returncode != 0:
        _fail("NOT_ANCESTOR")


def verify_readonly_git_custody(head_sha: str) -> dict[str, Any]:
    """Verify two real Git witnesses on the checked-out HEAD.

    The historical EIA prereg is compared to its old RESULT commit; the
    second independent witness verifies that a newly created EMPTY DRAFT
    manifest has not been modified since its seed commit. They are NOT
    one continuous prereg for a future candidate.
    """
    checked = _strict_sha(head_sha)
    current = _git("rev-parse", "HEAD").decode("ascii").strip()
    if current != checked:
        _fail("GITHUB_SHA_HEAD_MISMATCH")
    _ancestor(EIA_PREREG_COMMIT, EIA_RESULT_COMMIT)
    historical = _blob(EIA_PREREG_COMMIT, EIA_PREREG_PATH, EIA_PREREG_BLOB_SHA)
    if (
        b"NO" not in historical
        or b"EIA" not in historical
        or b"H1_WTI" not in historical
        or b"H1_NG" not in historical
    ):
        _fail("EIA_PREREG_CONTENT_MISMATCH")
    _ancestor(DRAFT_BASELINE_COMMIT, checked)
    seeded = _blob(DRAFT_BASELINE_COMMIT, DRAFT_PATH, DRAFT_BASELINE_BLOB_SHA)
    now = _blob(checked, DRAFT_PATH, DRAFT_BASELINE_BLOB_SHA)
    # GH checkout may be modified by a script: do not trust working tree if
    # it disagrees with HEAD (even though the Git blob remains pinned).
    if _git("status", "--porcelain", "--", DRAFT_PATH).strip():
        _fail("WORKTREE_MANIFEST_DIRTY")
    try:
        parsed = json.loads(seeded)
    except (UnicodeError, ValueError) as exc:
        raise ResearchIntakeError("GIT_CUSTODY_MANIFEST_JSON_INVALID") from exc
    if (
        type(parsed) is not dict
        or set(parsed) != {"schema", "drafts"}
        or parsed["schema"] != MANIFEST_SCHEMA
        or parsed["drafts"] != []
        or now != seeded
    ):
        _fail("MANIFEST_NONEMPTY_OR_CHANGED")
    result: dict[str, Any] = {
        "schema": SCHEMA,
        "verified_head_commit": checked,
        "historical_eia_prereg_commit": EIA_PREREG_COMMIT,
        "historical_eia_result_commit": EIA_RESULT_COMMIT,
        "historical_eia_prereg_blob_sha": EIA_PREREG_BLOB_SHA,
        "historical_eia_prereg_is_ancestor": True,
        "draft_manifest_baseline_commit": DRAFT_BASELINE_COMMIT,
        "draft_manifest_blob_sha": DRAFT_BASELINE_BLOB_SHA,
        "draft_manifest_unchanged_since_baseline": True,
        "draft_count": 0,
        "new_prereg_scientifically_frozen": False,
        "new_outcome_experiment_executed": False,
        "historical_outcome_retested": False,
        "first_publication_asof_certified": False,
        "source_license_verified": False,
        "can_open_holdout": False,
        "can_promote_trader": False,
        "market_data_spend_usd": 0,
    }
    canonical = json.dumps(
        result, sort_keys=True, separators=(",", ":"), allow_nan=False
    )
    result["custody_receipt_sha256"] = hashlib.sha256(
        canonical.encode("utf-8")
    ).hexdigest()
    return result
