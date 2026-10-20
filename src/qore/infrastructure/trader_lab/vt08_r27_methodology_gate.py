"""VT08 R27 methodological review gate; fail closed without authentic evidence.

This gate does not infer TTrades validity from geometric candidates.
"""
from __future__ import annotations
from datetime import datetime, timezone
from urllib.parse import urlparse


def _instant(value):
    if not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed.astimezone(timezone.utc) if parsed.tzinfo else None


REQUIRED = (
    "reference_swing",
    "significant_poi",
    "protected_swing",
    "causal_cisd",
    "conditional_eq",
    "positional_entry",
    "stop_invalidation",
    "untouched_target",
)


def adjudicate(packet: dict, *, trusted_reviewers: frozenset[str] = frozenset()) -> dict:
    if not isinstance(packet, dict):
        raise ValueError("R27 packet must be a mapping")
    identity = ("case_id_sha256", "market", "decision_as_of_utc", "source_sha256")
    if any(not isinstance(packet.get(k), str) or not packet[k] for k in identity):
        raise ValueError("R27 missing original case identity or causal cutoff")
    cutoff = _instant(packet["decision_as_of_utc"])
    if cutoff is None:
        raise ValueError("R27 invalid causal cutoff")
    evidence = packet.get("rule_evidence")
    if not isinstance(evidence, dict):
        raise ValueError("R27 missing per-rule evidence")
    missing = []
    for rule in REQUIRED:
        item = evidence.get(rule)
        if not isinstance(item, dict):
            missing.append(rule)
            continue
        url = item.get("primary_author_url")
        parsed_url = urlparse(url) if isinstance(url, str) else None
        available = _instant(item.get("available_at_utc"))
        if (item.get("verdict") != "AUTHOR_SOURCE_VALIDATED"
                or not isinstance(item.get("primary_author_url"), str)
                or parsed_url is None
                or parsed_url.scheme != "https"
                or parsed_url.hostname not in ("ttrades.com", "www.ttrades.com")
                or not isinstance(item.get("author_section"), str)
                or not item["author_section"].strip()
                or not isinstance(item.get("source_bar_ids"), list)
                or not item["source_bar_ids"]
                or not all(isinstance(x, str) and x for x in item["source_bar_ids"])
                or available is None
                or available > cutoff):
            missing.append(rule)
    reviewers = packet.get("independent_reviews")
    signed = False
    if isinstance(reviewers, list) and len(reviewers) == 2:
        a, b = reviewers
        signed = (
            all(isinstance(x, dict) for x in (a, b))
            and all(isinstance(x.get("reviewer_id"), str)
                    and x["reviewer_id"] for x in (a, b))
            and a["reviewer_id"] != b["reviewer_id"]
            and a["reviewer_id"] in trusted_reviewers
            and b["reviewer_id"] in trusted_reviewers
            and all(isinstance(x.get("signed_evidence"), str)
                    and x["signed_evidence"].strip()
                    and x.get("verdict") == "PASS" for x in (a, b))
        )
    blocked = sorted(set(missing))
    if packet.get("unresolved_disagreements"):
        blocked.append("unresolved_disagreements")
    if not signed:
        blocked.append("independent_A_B_signoffs")
    if not trusted_reviewers:
        blocked.append("trusted_reviewer_roster_missing")
    # Packet-supplied verification flags are untrusted. Require a separately
    # injected, authenticated verifier result; no such verifier is wired yet.
    blocked.append("external_signature_verifier_not_connected")
    return {
        "case_id_sha256": packet["case_id_sha256"],
        "methodology_gate": "PASS" if not blocked else "BLOCKED",
        "blocked_reasons": blocked,
        "cognitive_gate": "NOT_EVALUATED",
        "economic_gate": "NOT_EVALUATED",
        "trade_authorized": False,
    }
