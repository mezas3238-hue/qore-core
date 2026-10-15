"""Adversarial fixtures for the read-only G-M1 GitHub witness verifier.

A positive synthetic snapshot is ONLY a unit test, never independent approval.
"""

import hashlib
from copy import deepcopy

import pytest

from qore.infrastructure.traders.crt_pure_gm1_external_review import (
    validate_gm1_review_evidence,
)

SHA = "a" * 40
OWNER_ID = 17
REVIEWER_ID = 28
DOSSIER = b"Frozen seven-rule G-M1 review dossier"
DIGEST = hashlib.sha256(DOSSIER).hexdigest()
REVIEW = f"VT08-GM1-REVIEW-V1 HEAD={SHA} DOC_SHA256={DIGEST}"
OWNER = f"VT08-GM1-OWNER-V1 HEAD={SHA} DOC_SHA256={DIGEST}"


def fixture() -> dict:
    return {
        "pull": {
            "number": 626, "state": "open", "merged_at": None,
            "head": {
                "sha": SHA, "ref": "agent/vt08-crt-pure-source-identity-001",
                "repo": {"full_name": "mezas3238-hue/qore-core"},
            },
            "base": {
                "ref": "agent/vt08-crt-cognitive-architecture-freeze-001",
                "repo": {
                    "full_name": "mezas3238-hue/qore-core",
                    "owner": {"id": OWNER_ID},
                },
            },
            "user": {"id": OWNER_ID},
        },
        "reviews": [{
            "user": {"id": REVIEWER_ID}, "state": "APPROVED",
            "commit_id": SHA, "body": REVIEW,
            "submitted_at": "2026-10-15T18:00:00Z",
        }],
        "comments": [{
            "user": {"id": OWNER_ID}, "body": OWNER,
            "created_at": "2026-10-15T18:01:00Z",
            "updated_at": "2026-10-15T18:01:00Z",
        }],
        "commits": [{"sha": SHA, "author": {"id": OWNER_ID}}],
        "dossier": DOSSIER,
        "owner_id": OWNER_ID,
        "reviewer_id": REVIEWER_ID,
    }


def evaluate(data: dict):
    return validate_gm1_review_evidence(**data)


def test_valid_synthetic_witness_still_not_a_gate_certificate() -> None:
    outcome = evaluate(fixture())
    assert outcome.authenticated_witness
    assert outcome.blockers == ()
    assert not outcome.gm1_pass
    assert not outcome.gm5_issued
    assert not outcome.capital_authorized


@pytest.mark.parametrize("field,value,blocker", [
    ("owner_id", 0, "TRUST_ROOTS_INVALID"),
    ("reviewer_id", 0, "TRUST_ROOTS_INVALID"),
    ("reviewer_id", OWNER_ID, "TRUST_ROOTS_INVALID"),
    ("owner_id", 99, "OWNER_ID_NOT_REPO_OWNER"),
])
def test_external_id_roots_fail_closed(field: str, value: int, blocker: str) -> None:
    data = fixture()
    data[field] = value
    result = evaluate(data)
    assert not result.authenticated_witness
    assert blocker in result.blockers


def test_mutated_dossier_hash_cancels_both_signatures() -> None:
    data = fixture()
    data["dossier"] = b"changed G1 while keeping the old approvals"
    out = evaluate(data)
    assert not out.authenticated_witness
    assert "INDEPENDENT_REVIEW_NOT_VERIFIED" in out.blockers
    assert "OWNER_ACCEPTANCE_NOT_VERIFIED" in out.blockers


@pytest.mark.parametrize("mutation,blocker", [
    ("old_sha", "INDEPENDENT_REVIEW_NOT_VERIFIED"),
    ("fake_reviewer", "INDEPENDENT_REVIEW_NOT_VERIFIED"),
    ("wrong_review_body", "INDEPENDENT_REVIEW_NOT_VERIFIED"),
    ("pending_review", "INDEPENDENT_REVIEW_NOT_VERIFIED"),
    ("owner_too_early", "OWNER_ACCEPTANCE_NOT_VERIFIED"),
    ("wrong_owner", "OWNER_ACCEPTANCE_NOT_VERIFIED"),
    ("wrong_pr", "WRONG_PR_OR_MUTATED_SCOPE"),
    ("wrong_branch", "WRONG_PR_OR_MUTATED_SCOPE"),
    ("wrong_base", "WRONG_PR_OR_MUTATED_SCOPE"),
    ("wrong_repo", "WRONG_PR_OR_MUTATED_SCOPE"),
    ("history_head_mismatch", "COMMIT_HISTORY_HEAD_MISMATCH"),
    ("reviewer_is_author", "REVIEWER_IS_PR_AUTHOR"),
    ("reviewer_is_committer", "REVIEWER_CONTRIBUTED_TO_PR"),
    ("unlinked_committer", "UNLINKED_COMMIT_AUTHOR"),
    ("no_commits", "COMMIT_PROVENANCE_MISSING"),
])
def test_attestation_attacks_deny_witness(mutation: str, blocker: str) -> None:
    data = deepcopy(fixture())
    if mutation == "old_sha":
        data["reviews"][0]["commit_id"] = "b" * 40
    elif mutation == "fake_reviewer":
        data["reviews"][0]["user"]["id"] = 47
    elif mutation == "wrong_review_body":
        data["reviews"][0]["body"] += " EXTRA"
    elif mutation == "pending_review":
        data["reviews"][0]["state"] = "COMMENTED"
    elif mutation == "owner_too_early":
        data["comments"][0]["created_at"] = "2026-10-15T17:00:00Z"
    elif mutation == "wrong_owner":
        data["comments"][0]["user"]["id"] = 90
    elif mutation == "wrong_pr":
        data["pull"]["number"] = 627
    elif mutation == "wrong_branch":
        data["pull"]["head"]["ref"] = "agent/untrusted-branch"
    elif mutation == "wrong_base":
        data["pull"]["base"]["ref"] = "main"
    elif mutation == "wrong_repo":
        data["pull"]["head"]["repo"]["full_name"] = "random/fork"
    elif mutation == "history_head_mismatch":
        data["commits"][0]["sha"] = "b" * 40
    elif mutation == "reviewer_is_author":
        data["pull"]["user"]["id"] = REVIEWER_ID
    elif mutation == "reviewer_is_committer":
        data["commits"] = [{"author": {"id": REVIEWER_ID}}]
    elif mutation == "unlinked_committer":
        data["commits"] = [{"author": None}]
    elif mutation == "no_commits":
        data["commits"] = []
    result = evaluate(data)
    assert not result.authenticated_witness
    assert blocker in result.blockers


def test_subsequent_changes_requested_revoke_witness() -> None:
    data = fixture()
    data["reviews"].append({
        "user": {"id": 51}, "state": "CHANGES_REQUESTED",
        "commit_id": SHA, "body": "Objection",
        "submitted_at": "2026-10-15T18:00:15Z",
    })
    result = evaluate(data)
    assert not result.authenticated_witness
    assert "SUBSEQUENT_CHANGES_REQUESTED" in result.blockers


def test_latest_trusted_reviewer_decision_wins() -> None:
    data = fixture()
    data["reviews"].append({
        "user": {"id": REVIEWER_ID}, "state": "COMMENTED",
        "commit_id": SHA, "body": REVIEW,
        "submitted_at": "2026-10-15T18:02:00Z",
    })
    assert "INDEPENDENT_REVIEW_NOT_VERIFIED" in evaluate(data).blockers


def test_claimed_owner_comment_edited_after_initial_signoff_denies() -> None:
    data = fixture()
    data["comments"][0]["updated_at"] = "2026-10-15T18:05:00Z"
    assert "OWNER_ACCEPTANCE_NOT_VERIFIED" in evaluate(data).blockers
