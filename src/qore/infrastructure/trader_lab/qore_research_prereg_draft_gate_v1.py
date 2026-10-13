"""Fail-closed preregistration DRAFT gate for QORE Research.

A valid draft is NOT a Git-frozen preregistration, source entitlement,
statistical result, verified chronology, runnable experiment, or trader.
The only attestation function here requires an actual repository Git witness.
No data downloads, market outcomes, Risk grants, capital, or live operations.
"""
from __future__ import annotations

import hashlib
import json
import re
import subprocess
from datetime import date
from typing import Any

from qore.infrastructure.trader_lab.qore_research_zero_budget_intake_v1 import (
    ResearchIntakeError,
)

MANIFEST_SCHEMA = "qore.research.prereg-drafts.v1"
RECEIPT_SCHEMA = "qore.research.prereg-draft-receipt.v1"
_QUEUE_SCHEMA = "qore.research.zero-budget-intake-ledger.v1"
_SHA = re.compile(r"[a-f0-9]{40}\Z")
_HASH = re.compile(r"[a-f0-9]{64}\Z")
_CODE = re.compile(r"[a-z][a-z0-9._-]{2,100}\Z")
_TEXT = re.compile(r"[a-zA-Z0-9][^\x00-\x1f]{19,1023}\Z")
_DATE = re.compile(r"\d{4}-\d{2}-\d{2}\Z")
_ALL_ROOTS = frozenset(("CL", "NG", "GC", "HG", "ZC", "ZS"))
_FIELDS = frozenset((
    "proposal_code", "question_code", "hypothesis_code", "version",
    "hypothesis", "market_mechanism", "data_requirement_code", "roots",
    "primary_outcome", "exposure", "comparison", "direction",
    "sample_unit", "statistical_test", "alpha_ppm", "family_size",
    "multiple_testing", "minimum_effect_ppm", "minimum_group_events",
    "train_start", "train_end", "diagnostic_start", "diagnostic_end",
    "holdout_start", "holdout_end",
    "data_license_verified", "first_publication_asof_verified",
    "source_snapshot_sha256", "inspected_outcomes",
    "fresh_holdout_consumed", "experiment_runnable", "budget_usd",
))


def _fail(message: str) -> None:
    raise ResearchIntakeError("PREREG_" + message)


def _canonical(payload: Any) -> bytes:
    return json.dumps(
        payload, sort_keys=True, separators=(",", ":"), allow_nan=False,
    ).encode("utf-8")


def _code(value: Any, name: str) -> None:
    if type(value) is not str or not _CODE.fullmatch(value):
        _fail("BAD_CODE_" + name)


def _date(value: Any, name: str) -> date:
    if type(value) is not str or not _DATE.fullmatch(value):
        _fail("BAD_DATE_" + name)
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise ResearchIntakeError("PREREG_BAD_DATE_" + name) from exc


def _queue_index(ledger: dict[str, Any]) -> dict[str, dict[str, Any]]:
    if type(ledger) is not dict or ledger.get("schema") != _QUEUE_SCHEMA:
        _fail("UNTRUSTED_QUEUE")
    if type(ledger.get("ledger_sha256")) is not str:
        _fail("UNTRUSTED_QUEUE")
    digest = ledger["ledger_sha256"]
    if not _HASH.fullmatch(digest):
        _fail("UNTRUSTED_QUEUE")
    copy = {k: v for k, v in ledger.items() if k != "ledger_sha256"}
    if hashlib.sha256(_canonical(copy)).hexdigest() != digest:
        _fail("QUEUE_HASH_MISMATCH")
    if any(ledger.get(flag) is not False for flag in (
        "economic_replay_performed", "eia_fresh_holdout_opened",
        "stale_fx_holdout_opened", "production_execution_enabled",
    )):
        _fail("UNSAFE_QUEUE_FLAGS")
    if ledger.get("spent_usd") != 0 or ledger.get("estimated_traders_promoted") != 0:
        _fail("UNSAFE_QUEUE_STATE")
    entries = ledger.get("entries")
    if type(entries) is not list or len(entries) < 2 or len(entries) > 22:
        _fail("INVALID_QUEUE_ENTRIES")
    result: dict[str, dict[str, Any]] = {}
    for item in entries:
        if type(item) is not dict or type(item.get("code")) is not str:
            _fail("INVALID_QUEUE_ENTRY")
        if item["code"] in result:
            _fail("DUPLICATE_QUEUE_IDENTITY")
        result[item["code"]] = item
    if result.get("research.eia.futures-a-f1f2-closure", {}).get("status") != "closed_no_support":
        _fail("REOPENED_EIA")
    if result.get("research.futures-a.native-6roots-d1", {}).get("status") != "source_blocked":
        _fail("UNBLOCKED_CME")
    return result


def validate_draft(spec: dict[str, Any], queue: dict[str, dict[str, Any]]) -> str:
    """Return content SHA-256 only, NEVER permission to run a hypothesis."""
    if type(spec) is not dict or set(spec) != _FIELDS:
        _fail("DRAFT_FIELDS_MISMATCH")
    for field in ("proposal_code", "question_code", "hypothesis_code",
                  "data_requirement_code"):
        _code(spec[field], field)
    if not spec["proposal_code"].startswith("research.proposal."):
        _fail("NOT_A_NEW_PROPOSAL")
    entry = queue.get(spec["proposal_code"])
    if (
        entry is None or entry.get("status") != "proposal_only"
        or entry.get("question_code") != spec["question_code"]
        or entry.get("data_requirement_code") != spec["data_requirement_code"]
        or entry.get("experiment_runnable") is not False
        or entry.get("trader_certified") is not False
        or entry.get("can_open_fresh_holdout") is not False
    ):
        _fail("PROPOSAL_NOT_IN_SOURCE_FIRST_QUEUE")
    for field in (
        "hypothesis", "market_mechanism", "primary_outcome",
        "exposure", "comparison", "sample_unit",
    ):
        if type(spec[field]) is not str or not _TEXT.fullmatch(spec[field]):
            _fail("MISSING_FALSIFIABLE_DEFINITION_" + field)
    if type(spec["version"]) is not int or spec["version"] != 1:
        _fail("VERSION_REQUIRES_NEW_GOVERNANCE")
    roots = spec["roots"]
    if (type(roots) is not list or len(roots) not in (2, 6)
            or len(roots) != entry.get("research_root_count")
            or any(type(root) is not str for root in roots)
            or len(set(roots)) != len(roots)
            or not set(roots).issubset(_ALL_ROOTS)
            or roots != sorted(roots)):
        _fail("INVALID_NATIVE_ROOTS")
    if (spec["direction"] not in ("greater", "less")
            or spec["statistical_test"] not in (
                "fisher_exact", "blocked_permutation",
            ) or spec["multiple_testing"] != "bonferroni"):
        _fail("MISSING_FIXED_INFERENCE_RULE")
    for name in ("alpha_ppm", "family_size", "minimum_effect_ppm",
                 "minimum_group_events"):
        if type(spec[name]) is not int:
            _fail("NONINTEGER_INFERENCE_SETTING")
    if not (1 <= spec["alpha_ppm"] <= 50000 and
            1 <= spec["family_size"] <= 20 and
            0 <= spec["minimum_effect_ppm"] <= 1000000 and
            8 <= spec["minimum_group_events"] <= 1000000):
        _fail("INVALID_INFERENCE_THRESHOLDS")
    windows = [_date(spec[k], k) for k in (
        "train_start", "train_end", "diagnostic_start",
        "diagnostic_end", "holdout_start", "holdout_end",
    )]
    if not (windows[0] <= windows[1] < windows[2] <=
            windows[3] < windows[4] <= windows[5]):
        _fail("OVERLAPPING_OR_REVERSED_SPLITS")
    if (spec["data_requirement_code"] == "eia.f1f2.reference-close-only"
            or spec["hypothesis_code"] ==
            "research.hypothesis.backwardation-predicts-f1-up"):
        _fail("ARCHIVED_HYPOTHESIS_REUSE")
    for name in (
        "data_license_verified", "first_publication_asof_verified",
        "inspected_outcomes", "fresh_holdout_consumed", "experiment_runnable",
    ):
        if spec[name] is not False:
            _fail("UNAUTHORIZED_DATA_OR_EXECUTION_" + name)
    if spec["source_snapshot_sha256"] is not None or (
        type(spec["budget_usd"]) is not int or spec["budget_usd"] != 0
    ):
        _fail("FAKE_SOURCE_ATTESTATION_OR_SPEND")
    return hashlib.sha256(_canonical(spec)).hexdigest()


def build_draft_receipt(
    manifest: dict[str, Any], ledger: dict[str, Any],
) -> dict[str, Any]:
    """Strict one-to-one draft linkage to the authenticated intake ledger.

    NO Git seal or first-outcome ordering is claimed by this digest.
    """
    queue = _queue_index(ledger)
    if (
        type(manifest) is not dict
        or set(manifest) != {"schema", "drafts"}
        or manifest["schema"] != MANIFEST_SCHEMA
        or type(manifest["drafts"]) is not list
        or len(manifest["drafts"]) > 20
    ):
        _fail("BAD_MANIFEST")
    drafts = manifest["drafts"]
    proposal_codes = sorted(
        code for code, entry in queue.items()
        if entry.get("status") == "proposal_only"
    )
    if len(drafts) != len(proposal_codes):
        _fail("DRAFT_PROPOSAL_ONE_TO_ONE_REQUIRED")
    witness: list[dict[str, str]] = []
    codes: list[str] = []
    hypotheses: list[str] = []
    for spec in drafts:
        digest = validate_draft(spec, queue)
        codes.append(spec["proposal_code"])
        hypotheses.append(spec["hypothesis_code"])
        witness.append({"proposal_code": spec["proposal_code"], "draft_sha256": digest})
    if codes != proposal_codes or len(set(hypotheses)) != len(hypotheses):
        _fail("DUPLICATED_OR_UNSORTED_DRAFTS")
    receipt: dict[str, Any] = {
        "schema": RECEIPT_SCHEMA,
        "intake_ledger_sha256": ledger["ledger_sha256"],
        "draft_manifest_sha256": hashlib.sha256(_canonical(manifest)).hexdigest(),
        "draft_count": len(drafts),
        "drafts": witness,
        "provenance_git_ancestor_attested": False,
        "scientific_prereg_frozen": False,
        "data_rights_certified": False,
        "can_execute": False,
        "can_open_holdout": False,
        "economic_backtest_performed": False,
        "risk_or_cibo_authority": False,
        "trader_lab_eligible": False,
        "market_data_spend_usd": 0,
    }
    receipt["receipt_sha256"] = hashlib.sha256(_canonical(receipt)).hexdigest()
    return receipt


def verify_prereg_before_outcome_git(
    prereg_commit: str, outcome_commit: str, *,
    prereg_path: str, draft_sha256: str, proposal_code: str,
) -> bool:
    """Verify Git ancestry plus exact spec bytes at historical prereg commit.

    Does NOT establish data entitlement or that humans never viewed outcomes.
    Caller must separately verify trusted GitHub run identity and commit refs.
    This function never changes the DRAFT receipt's immutable false flags.
    """
    if not all(type(x) is str and _SHA.fullmatch(x) for x in (
        prereg_commit, outcome_commit,
    )) or prereg_commit == outcome_commit:
        _fail("INVALID_OR_EQUAL_GIT_COMMITS")
    if not isinstance(prereg_path, str) or not re.fullmatch(
        r"docs/research/[A-Za-z0-9_.-]+\.json", prereg_path
    ):
        _fail("BAD_PREREG_PATH")
    if type(draft_sha256) is not str or not _HASH.fullmatch(draft_sha256):
        _fail("BAD_DRAFT_DIGEST")
    _code(proposal_code, "proposal")
    try:
        ancestor = subprocess.run(
            ["git", "merge-base", "--is-ancestor", prereg_commit, outcome_commit],
            capture_output=True, check=False, timeout=10,
        )
        historical = subprocess.run(
            ["git", "show", f"{prereg_commit}:{prereg_path}"],
            capture_output=True, check=False, timeout=10,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise ResearchIntakeError("PREREG_GIT_WITNESS_UNAVAILABLE") from exc
    if ancestor.returncode != 0 or historical.returncode != 0:
        _fail("GIT_ANCESTRY_OR_SOURCE_NOT_VERIFIED")
    try:
        frozen = json.loads(historical.stdout)
    except (UnicodeError, ValueError) as exc:
        raise ResearchIntakeError("PREREG_BAD_HISTORICAL_MANIFEST") from exc
    if (
        type(frozen) is not dict or frozen.get("schema") != MANIFEST_SCHEMA
        or type(frozen.get("drafts")) is not list
    ):
        _fail("BAD_HISTORICAL_MANIFEST")
    matches = [
        spec for spec in frozen["drafts"]
        if type(spec) is dict and spec.get("proposal_code") == proposal_code
    ]
    if len(matches) != 1 or hashlib.sha256(
        _canonical(matches[0])
    ).hexdigest() != draft_sha256:
        _fail("HISTORICAL_DRAFT_WAS_CHANGED")
    return True
