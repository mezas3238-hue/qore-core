"""VT08 B R23: non-operational, fail-closed dual source-review admission ledger.

Input is the originally preregistered 107 R19 blind packets, never a
performance-selected subset. A/B must independently provide signed source
findings. No authorized reviewer public keys have been provisioned: current
real packets therefore MUST remain WAIT, not auto-verified by the producer.

Review approval is NEVER methodology execution approval, an authenticated
27-field cognitive Situation, or permission to run trades.
"""
from __future__ import annotations

import json
import re
from datetime import UTC, datetime
from typing import Final

from qore.infrastructure.trader_lab.vt08_b_r19_blind_dual_rater_poi_queue_v1 import (
    MARKET_EXPECTED,
    SEED,
)
from qore.infrastructure.trader_lab.vt08_b_r19_blind_dual_rater_poi_queue_v1 import (
    SCHEMA as R19_SCHEMA,
)
from qore.infrastructure.trader_lab.vt08_b_r19_blind_dual_rater_poi_queue_v1 import (
    digest as digest_r19,
)

SCHEMA: Final = "qore.vt08.b.r23.dual_signed_source_review.v1"
BALLOT_SCHEMA: Final = "qore.vt08.b.r23.independent_source_ballot.v1"
SHA = re.compile(r"[0-9a-f]{64}\Z")
SIGNATURE = re.compile(r"[0-9a-f]{128}\Z")
SOURCE_DOMAINS: Final = (
    "https://ttrades.com/",
)
ROLES: Final = ("A_METHOD", "B_INDEPENDENT")
CLAIMS: Final = (
    "relevant_swing_selection",
    "qualitative_valid_separation",
    "important_poi_selected_before_cisd",
    "poi_reaction_vs_cisd_order",
    "opposing_series_creates_protected_swing",
    "breaker_source_sequence",
    "eq_regime_and_author_stop_basis",
    "untouched_htf_target_basis",
)
FINDINGS: Final = frozenset(("SUPPORTED", "REJECTED", "D_UNSPECIFIED"))

# This immutable trust-root slot is intentionally EMPTY. No A or B keys have
# been independently appointed/approved by the Owner for this project.
# Modifying this is a code-reviewed governance action, not API payload input.
APPROVED_RATER_ED25519_PUBLIC_KEYS: Final[dict[str, dict[str, str]]] = {
    "A_METHOD": {},
    "B_INDEPENDENT": {},
}
PINNED_R19_REPORT_DIGESTS: Final = {
    "EURJPY": "f553e6f8da86d7af30ce1f811257b0d05b892d03ee4d60d046d1f10bb65c5b7c",
    "USDCHF": "87d43288eecddce84c1fcc99578558cb03f1be69dbf5d438766582fbd8e14bc4",
    "NZDUSD": "cbba1ff00d19608968ed58c48b7eb5fdfd038e5187ab738b4710ae0b91e26e56",
    "CADJPY": "b16f7ffe78892c5eb53d2ecf33c2057e7a70e70140e2b1fd1e2ddd3673486e32",
    "USDCAD": "a5ed7db7cb965db87ffb949ea0644d24199114895fd3b3da3529c870781c01f9",
}


def _utc(value: object) -> datetime:
    if not isinstance(value, str):
        raise ValueError("R23 absent ISO-8601 time")
    try:
        result = datetime.fromisoformat(value)
    except ValueError as exc:
        raise ValueError("R23 invalid ISO-8601 time") from exc
    if result.utcoffset() is None:
        raise ValueError("R23 naive event/review time forbidden")
    return result.astimezone(UTC)


def _canonical(value: object) -> bytes:
    return json.dumps(
        value, ensure_ascii=True, sort_keys=True, separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def _ballot_digest(ballot: dict[str, object]) -> bytes:
    body = dict(ballot)
    body.pop("ed25519_signature", None)
    return _canonical(body)


def _assert_ballot(
    ballot: dict[str, object], packet: dict[str, object],
    market: str, r19_sha: str, role: str,
) -> tuple[str, tuple[str, ...]]:
    if (
        ballot.get("schema") != BALLOT_SCHEMA
        or ballot.get("market") != market
        or ballot.get("case_id_sha256") != packet["case_id_sha256"]
        or ballot.get("r19_source_report_sha256") != r19_sha
        or ballot.get("reviewer_role") != role
    ):
        raise ValueError("R23 reviewer/source/role identity mismatch")
    if set(ballot) != {
        "schema", "market", "case_id_sha256", "r19_source_report_sha256",
        "reviewer_role", "reviewer_key_id", "reviewed_at_utc",
        "findings", "ed25519_signature",
    }:
        raise ValueError("R23 ballot cannot contain unsigned or mutable instructions")
    signing = _utc(ballot["reviewed_at_utc"])
    decision = _utc(packet["c3_opened_at_utc"])
    if signing < decision:
        raise ValueError("R23 review signed before complete source window was observable")
    findings = ballot.get("findings")
    if not isinstance(findings, dict) or set(findings) != set(CLAIMS):
        raise ValueError("R23 review omitted mandatory methodology claims")
    selected: list[str] = []
    for claim in CLAIMS:
        item = findings[claim]
        if not isinstance(item, dict) or set(item) != {
            "disposition", "author_source_url", "author_section",
            "source_bar_ids", "latest_source_available_at_utc", "reason",
        }:
            raise ValueError("R23 finding without full source attribution")
        state = item.get("disposition")
        if state not in FINDINGS:
            raise ValueError("R23 non-adjudicated source finding state")
        if not isinstance(item.get("author_source_url"), str) or not (
            item["author_source_url"].startswith(SOURCE_DOMAINS)
        ):
            raise ValueError("R23 methodology cannot import foreign-rule URL")
        if not isinstance(item.get("author_section"), str) or not (
            item["author_section"].strip()
        ):
            raise ValueError("R23 missing original source section")
        if not isinstance(item.get("reason"), str) or len(item["reason"].strip()) < 20:
            raise ValueError("R23 missing meaningful independent review rationale")
        ids = item.get("source_bar_ids")
        if (
            not isinstance(ids, list) or not ids
            or any(not isinstance(v, str) or SHA.fullmatch(v) is None for v in ids)
            or len(set(ids)) != len(ids)
        ):
            raise ValueError("R23 no unique source raw bar IDs in finding")
        available = _utc(item["latest_source_available_at_utc"])
        if available > decision:
            raise ValueError("R23 source claim uses future evidence past C3 decision")
        selected.append(str(state))
    key_id = ballot.get("reviewer_key_id")
    if not isinstance(key_id, str) or not key_id:
        raise ValueError("R23 independent reviewer key ID required")
    pub = APPROVED_RATER_ED25519_PUBLIC_KEYS.get(role, {}).get(key_id)
    if not isinstance(pub, str) or re.fullmatch("[0-9a-f]{64}", pub) is None:
        raise ValueError("R23 reviewer key NOT APPROVED by immutable source governance")
    sig = ballot.get("ed25519_signature")
    if not isinstance(sig, str) or SIGNATURE.fullmatch(sig) is None:
        raise ValueError("R23 missing cryptographic review signature")
    # The optional crypto runtime is ONLY imported after a governance-pinned
    # key exists. An unapproved forged string never requires crypto installed.
    from cryptography.exceptions import InvalidSignature
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

    try:
        Ed25519PublicKey.from_public_bytes(bytes.fromhex(pub)).verify(
            bytes.fromhex(sig), _ballot_digest(ballot),
        )
    except (InvalidSignature, ValueError) as exc:
        raise ValueError("R23 altered/forged reviewer signature") from exc
    return pub, tuple(selected)


def audit_dual_source_review(
    original_r19: dict[str, object],
    *,
    market: str,
    submitted_ballots: list[dict[str, object]],
) -> dict[str, object]:
    """Audit full 107 sample, with no authority granted from CI fixtures.

    A successful 8-claim A/B source REVIEW (when trustworthy signed keys are
    someday authorized) is still NOT a full TTrades setup, Situation or PnL.
    """
    if market not in MARKET_EXPECTED:
        raise ValueError("R23 unauthorized VT08 research market")
    n, r18_sha = MARKET_EXPECTED[market]
    r19_sha = PINNED_R19_REPORT_DIGESTS[market]
    if (
        original_r19.get("schema") != R19_SCHEMA
        or original_r19.get("market") != market
        or original_r19.get("seed") != SEED
        or digest_r19(original_r19) != r19_sha
        or original_r19.get("original_r18_sha256") != r18_sha
        or original_r19.get("original_r18_cases") != n
        or original_r19.get("rater_A_signed") != 0
        or original_r19.get("rater_B_signed") != 0
        or original_r19.get("source_complete_entries") != 0
        or original_r19.get("cognitive_admissions") != 0
        or original_r19.get("broker_fills") != 0
        or original_r19.get("holdout_7y_accessed") is not False
        or original_r19.get("sizing_used") is not False
    ):
        raise ValueError("R23 input is not original fixed source-only blind sample")
    packets = original_r19.get("review_packets")
    if not isinstance(packets, list) or len(packets) != original_r19.get(
        "selected_source_only_cases"
    ):
        raise ValueError("R23 frozen 107 review universe missing")
    lookup: dict[str, dict[str, object]] = {}
    for packet in packets:
        if not isinstance(packet, dict) or packet.get("market") != market:
            raise ValueError("R23 cross-market blind packet")
        cid = packet.get("case_id_sha256")
        if not isinstance(cid, str) or SHA.fullmatch(cid) is None or cid in lookup:
            raise ValueError("R23 duplicated/corrupt case identity")
        if (
            packet.get("human_rater_A_source_signoff") is not None
            or packet.get("human_rater_B_independent_signoff") is not None
            or packet.get("source_complete") is not False
            or packet.get("cognitive_ready") is not False
            or packet.get("orders_authorized") is not False
        ):
            raise ValueError("R23 original sample falsely attests methodology")
        lookup[cid] = packet
    votes: dict[str, dict[str, tuple[str, tuple[str, ...]]]] = {}
    if not isinstance(submitted_ballots, list):
        raise ValueError("R23 submitted ballots must be a list")
    for ballot in submitted_ballots:
        if not isinstance(ballot, dict):
            raise ValueError("R23 ballot must be JSON object")
        cid = ballot.get("case_id_sha256")
        role = ballot.get("reviewer_role")
        if not isinstance(cid, str) or cid not in lookup or role not in ROLES:
            raise ValueError("R23 ballot outside original case or reviewer role")
        target = votes.setdefault(cid, {})
        if role in target:
            raise ValueError("R23 duplicate review attempted to overwrite prior decision")
        target[role] = _assert_ballot(ballot, lookup[cid], market, r19_sha, role)
    cases: list[dict[str, object]] = []
    counts = {"WAIT_UNREVIEWED": 0, "WAIT_SECOND_REVIEWER": 0,
              "WAIT_DISAGREEMENT_OR_D": 0, "SOURCE_REVIEW_REJECTED": 0,
              "DUAL_SOURCE_REVIEW_CONSISTENT_ONLY": 0}
    for cid in sorted(lookup):
        signed = votes.get(cid, {})
        if not signed:
            status = "WAIT_UNREVIEWED"
        elif len(signed) != 2:
            status = "WAIT_SECOND_REVIEWER"
        elif signed["A_METHOD"][0] == signed["B_INDEPENDENT"][0]:
            raise ValueError("R23 same signer cannot impersonate two independent raters")
        elif "REJECTED" in signed["A_METHOD"][1] or (
            "REJECTED" in signed["B_INDEPENDENT"][1]
        ):
            status = "SOURCE_REVIEW_REJECTED"
        elif signed["A_METHOD"][1] != signed["B_INDEPENDENT"][1] or (
            "D_UNSPECIFIED" in signed["A_METHOD"][1]
        ):
            status = "WAIT_DISAGREEMENT_OR_D"
        else:
            status = "DUAL_SOURCE_REVIEW_CONSISTENT_ONLY"
        counts[status] += 1
        cases.append({
            "case_id_sha256": cid,
            "market": market,
            "source_review_status": status,
            "two_cryptographically_verified_independent_signers": len(signed) == 2,
            "TTrades_methodology_source_complete": False,
            "cognitive_admission_authorized": False,
            "broker_orders_authorized": False,
        })
    if sum(counts.values()) != len(packets):
        raise ValueError("R23 source-review denominator changed")
    return {
        "schema": SCHEMA,
        "market": market,
        "original_preregistered_cases": len(packets),
        "original_r19_sha256": r19_sha,
        "source_review_status_counts": counts,
        "approved_rater_keys_A": len(APPROVED_RATER_ED25519_PUBLIC_KEYS["A_METHOD"]),
        "approved_rater_keys_B": len(APPROVED_RATER_ED25519_PUBLIC_KEYS["B_INDEPENDENT"]),
        "author_complete_entries": 0,
        "real_cognitive_admissions": 0,
        "broker_fills": 0,
        "economic_gates_evaluated": False,
        "holdout_7y_accessed": False,
        "sizing_used": False,
        "case_review_register": cases,
        "verdict": "REVIEW_CONTRACT_ONLY_NOT_SOURCE_OR_COGNITIVE_CERTIFICATION",
    }
