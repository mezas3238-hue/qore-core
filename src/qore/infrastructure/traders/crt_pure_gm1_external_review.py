"""Read-only GitHub evidence verifier for the VT08 CRT seven-rule G-M1 dossier.

This is NOT a certification issuer. Identity roots must come from a protected,
out-of-band authority, never a file or flag supplied by the PR under review.
The live CLI reads GitHub HTTPS API itself; tests of the pure validator are not
proof that genuine actors approved anything. No orders, PnL, or sizing.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import re
from dataclasses import dataclass
from datetime import datetime
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

REPOSITORY = "mezas3238-hue/qore-core"
PR_NUMBER = 626
EXPECTED_HEAD = "agent/vt08-crt-pure-source-identity-001"
EXPECTED_BASE = "agent/vt08-crt-cognitive-architecture-freeze-001"
DOSSIER_PATH = (
    "docs/research/VT08_CRT_GM1_SEVEN_RULES_REVIEW_DOSSIER_2026-10-15.md"
)
_SHA = re.compile(r"^[0-9a-f]{40}$")
_API = "https://api.github.com"
_MAX_PAGES = 20


@dataclass(frozen=True, slots=True)
class Gm1ReviewAudit:
    head_sha: str
    dossier_sha256: str
    authenticated_witness: bool
    blockers: tuple[str, ...]
    gm1_pass: bool = False
    gm5_issued: bool = False
    capital_authorized: bool = False


def _identity(user: Any) -> int:
    if not isinstance(user, dict) or type(user.get("id")) is not int:
        return 0
    return int(user["id"])


def _timestamp(text: Any) -> datetime | None:
    if not isinstance(text, str) or not text:
        return None
    try:
        result = datetime.fromisoformat(text.replace("Z", "+00:00"))
        return result if result.tzinfo is not None else None
    except ValueError:
        return None


def validate_gm1_review_evidence(
    *,
    pull: dict[str, Any],
    reviews: list[dict[str, Any]],
    comments: list[dict[str, Any]],
    commits: list[dict[str, Any]],
    dossier: bytes,
    owner_id: int,
    reviewer_id: int,
) -> Gm1ReviewAudit:
    """Evaluate API-shaped evidence for diagnosis, not as an authority grant.

    Caller-provided snapshots are untrusted unless they came from the live
    authenticated HTTPS GitHub client with roots set out of band. Even a
    positive witness cannot issue a G-M1/G-M5 certificate.
    """
    blockers: list[str] = []
    sha = pull.get("head", {}).get("sha", "")
    head_ref = pull.get("head", {}).get("ref")
    base_repo = pull.get("base", {}).get("repo", {})
    repo_name = base_repo.get("full_name")
    head_repo = pull.get("head", {}).get("repo", {})
    if not isinstance(sha, str) or not _SHA.fullmatch(sha):
        sha = ""
        blockers.append("INVALID_HEAD_SHA")
    if (
        pull.get("number") != PR_NUMBER
        or repo_name != REPOSITORY
        or head_ref != EXPECTED_HEAD
        or pull.get("base", {}).get("ref") != EXPECTED_BASE
        or head_repo.get("full_name") != REPOSITORY
        or pull.get("state") != "open"
        or pull.get("merged_at") is not None
    ):
        blockers.append("WRONG_PR_OR_MUTATED_SCOPE")
    if not isinstance(dossier, bytes) or not dossier:
        blockers.append("DOSSIER_MISSING")
        digest = ""
    else:
        digest = hashlib.sha256(dossier).hexdigest()
    if type(owner_id) is not int or type(reviewer_id) is not int:
        blockers.append("TRUST_ROOTS_MISSING")
    elif owner_id <= 0 or reviewer_id <= 0 or owner_id == reviewer_id:
        blockers.append("TRUST_ROOTS_INVALID")
    if _identity(base_repo.get("owner")) != owner_id:
        blockers.append("OWNER_ID_NOT_REPO_OWNER")
    if reviewer_id == _identity(pull.get("user")):
        blockers.append("REVIEWER_IS_PR_AUTHOR")
    if not commits:
        blockers.append("COMMIT_PROVENANCE_MISSING")
    if commits and commits[-1].get("sha") != sha:
        blockers.append("COMMIT_HISTORY_HEAD_MISMATCH")
    if any(_identity(commit.get("author")) == 0 for commit in commits):
        blockers.append("UNLINKED_COMMIT_AUTHOR")
    if any(_identity(commit.get("author")) == reviewer_id for commit in commits):
        blockers.append("REVIEWER_CONTRIBUTED_TO_PR")
    if not sha or not digest:
        return Gm1ReviewAudit(sha, digest, False, tuple(blockers))

    expected_reviewer = f"VT08-GM1-REVIEW-V1 HEAD={sha} DOC_SHA256={digest}"
    expected_owner = f"VT08-GM1-OWNER-V1 HEAD={sha} DOC_SHA256={digest}"

    valid_reviews = [
        r for r in reviews
        if _identity(r.get("user")) == reviewer_id
        and _timestamp(r.get("submitted_at")) is not None
    ]
    valid_reviews.sort(key=lambda r: str(r.get("submitted_at")))
    latest_review = valid_reviews[-1] if valid_reviews else None
    if (
        latest_review is None
        or latest_review.get("state") != "APPROVED"
        or latest_review.get("commit_id") != sha
        or str(latest_review.get("body", "")).strip() != expected_reviewer
    ):
        blockers.append("INDEPENDENT_REVIEW_NOT_VERIFIED")

    # An unresolved subsequent CHANGES_REQUESTED invalidates this exact
    # approval even if another account previously approved the same SHA.
    approved_time = (
        _timestamp(latest_review.get("submitted_at"))
        if latest_review is not None else None
    )
    if approved_time is not None:
        for review in reviews:
            if review.get("state") != "CHANGES_REQUESTED":
                continue
            submitted = _timestamp(review.get("submitted_at"))
            if submitted is None or submitted > approved_time:
                blockers.append("SUBSEQUENT_CHANGES_REQUESTED")
                break

    owner_comments = [
        c for c in comments
        if _identity(c.get("user")) == owner_id
        and str(c.get("body", "")).strip().startswith("VT08-GM1-OWNER-V1")
    ]
    owner_comments.sort(key=lambda c: str(c.get("created_at", "")))
    owner_comment = owner_comments[-1] if owner_comments else None
    if (
        owner_comment is None
        or str(owner_comment.get("body", "")).strip() != expected_owner
        or _timestamp(owner_comment.get("created_at")) is None
        or approved_time is None
        or _timestamp(owner_comment.get("created_at")) <= approved_time
        or owner_comment.get("updated_at") != owner_comment.get("created_at")
    ):
        blockers.append("OWNER_ACCEPTANCE_NOT_VERIFIED")

    return Gm1ReviewAudit(
        sha,
        digest,
        not blockers,
        tuple(blockers),
    )


def _get_json(token: str, path: str) -> Any:
    if not path.startswith("/repos/" + REPOSITORY + "/"):
        raise ValueError("GitHub API scope not allowed")
    request = Request(
        _API + path,
        headers={
            "Authorization": "Bearer " + token,
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "qore-vt08-gm1-read-only-audit",
        },
        method="GET",
    )
    with urlopen(request, timeout=15) as response:
        payload = response.read(2_000_001)
    if len(payload) > 2_000_000:
        raise ValueError("GitHub API response too large")
    return json.loads(payload)


def _all_pages(token: str, resource: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for page in range(1, _MAX_PAGES + 1):
        data = _get_json(token, f"/repos/{REPOSITORY}/{resource}?per_page=100&page={page}")
        if not isinstance(data, list) or not all(isinstance(x, dict) for x in data):
            raise ValueError("unexpected GitHub pagination shape")
        rows.extend(data)
        if len(data) < 100:
            return rows
    raise ValueError("GitHub review pagination limit reached; deny by default")


def audit_gm1_live(token: str, owner_id: int, reviewer_id: int) -> Gm1ReviewAudit:
    """Only this entry point collects records over authenticated GitHub HTTPS."""
    root = f"/repos/{REPOSITORY}"
    pull = _get_json(token, root + f"/pulls/{PR_NUMBER}")
    if not isinstance(pull, dict):
        raise ValueError("GitHub pull not returned")
    sha = pull.get("head", {}).get("sha")
    if not isinstance(sha, str) or not _SHA.fullmatch(sha):
        raise ValueError("invalid PR head from API")
    reviews = _all_pages(token, f"pulls/{PR_NUMBER}/reviews")
    comments = _all_pages(token, f"issues/{PR_NUMBER}/comments")
    commits = _all_pages(token, f"pulls/{PR_NUMBER}/commits")
    raw_file = _get_json(token, root + f"/contents/{DOSSIER_PATH}?ref={sha}")
    if not isinstance(raw_file, dict) or raw_file.get("encoding") != "base64":
        raise ValueError("GitHub dossier missing or not base64")
    encoded = raw_file.get("content")
    if not isinstance(encoded, str):
        raise ValueError("GitHub dossier content missing")
    dossier = base64.b64decode(encoded, validate=False)
    if len(dossier) > 1_000_000:
        raise ValueError("dossier unexpectedly large")
    result = validate_gm1_review_evidence(
        pull=pull, reviews=reviews, comments=comments, commits=commits,
        dossier=dossier, owner_id=owner_id, reviewer_id=reviewer_id,
    )
    # Refetch to avoid a head move while evidence was being collected.
    current = _get_json(token, root + f"/pulls/{PR_NUMBER}")
    if not isinstance(current, dict) or current.get("head", {}).get("sha") != sha:
        return Gm1ReviewAudit(
            sha, result.dossier_sha256, False,
            result.blockers + ("PR_HEAD_MOVED_DURING_AUDIT",),
        )
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="VT08 G-M1 external proof audit (read-only)")
    parser.add_argument("--live", action="store_true", required=True)
    parser.parse_args()
    token = os.environ.get("GITHUB_TOKEN", "")
    owner = os.environ.get("VT08_TRUSTED_OWNER_ID", "")
    reviewer = os.environ.get("VT08_TRUSTED_REVIEWER_ID", "")
    if not token or not owner.isdecimal() or not reviewer.isdecimal():
        print(json.dumps({
            "authenticated_witness": False,
            "gm1_pass": False, "gm5_issued": False,
            "blockers": ["PROTECTED_CREDENTIALS_OR_TRUST_ROOTS_MISSING"],
        }))
        raise SystemExit(2)
    try:
        result = audit_gm1_live(token, int(owner), int(reviewer))
    except (HTTPError, URLError, ValueError, TypeError, KeyError) as exc:
        # No token, raw HTTP payload, or exception URL in logged diagnostics.
        print(json.dumps({
            "authenticated_witness": False,
            "gm1_pass": False, "gm5_issued": False,
            "blockers": ["GITHUB_EVIDENCE_UNAVAILABLE_OR_INVALID"],
            "error_type": type(exc).__name__,
        }))
        raise SystemExit(2) from None
    print(json.dumps({
        "head_sha": result.head_sha,
        "dossier_sha256": result.dossier_sha256,
        "authenticated_witness": result.authenticated_witness,
        "gm1_pass": False, "gm5_issued": False,
        "blockers": result.blockers,
    }, sort_keys=True))
    if not result.authenticated_witness:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
