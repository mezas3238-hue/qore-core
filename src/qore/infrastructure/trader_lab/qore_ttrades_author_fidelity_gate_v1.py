"""Fail-closed author-source fidelity authorization gate (NO economic replay).

This is an auditable governance check: it does NOT implement TTrades or prove
strategy profitability. It prevents an author-exact claim without primary
sources, independent code, example fixtures and unseen holdout.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any

IDENTITY = "TTRADES_2026_02_07_SCALPING_MODEL_DAILY_CONTEXT_H1_BIAS_M15_SWING_M1_EXECUTION"
SCHEMA = "qore.scalper.ttrades.author_fidelity.v1"
EXACT_RULES = {f"TT{i:02d}" for i in range(2, 11)}
QORE_RULES = {f"TT{i:02d}" for i in range(11, 14)}
EVIDENCE_RULES = {"TT14", "TT15"}
IDS = {"TT01"} | EXACT_RULES | QORE_RULES | EVIDENCE_RULES
REQUIRED_SOURCE_IDS = {f"A{i}" for i in range(8)}
EVIDENCE_FLAGS = (
    "author_fidelity_certified",
    "independent_first_online_engine_verified",
    "author_example_fixtures_verified",
    "independent_holdout_reserved",
)
AVAILABILITY_INVARIANTS = (
    "no_v49_detectors_as_author_oracle",
    "no_proxies_passed_off_as_author_exact",
    "no_vps_mt5_prod",
)


def decide(contract: dict[str, Any]) -> dict[str, Any]:
    """Require all source + timing evidence; unknown means BLOCKED not PASS."""
    problems: list[str] = []
    if contract.get("schema") != SCHEMA or contract.get("identity") != IDENTITY:
        problems.append("WRONG_CANONICAL_MODEL_OR_SCHEMA")
    sources = contract.get("sources", [])
    src_by_id = {x.get("id"): x for x in sources if isinstance(x, dict)}
    if len(sources) != len(src_by_id) or not REQUIRED_SOURCE_IDS.issubset(src_by_id):
        problems.append("REQUIRED_PRIMARY_SOURCES_MISSING_OR_DUPLICATE")
    for name in REQUIRED_SOURCE_IDS:
        source = src_by_id.get(name, {})
        if not (
            source.get("primary_author") == "TTrades"
            and source.get("text_primary_accessed") is True
            and isinstance(source.get("url"), str)
            and source.get("url", "").startswith("https://ttrades.com/")
        ):
            problems.append(f"PRIMARY_SOURCE_NOT_VERIFIED:{name}")
    rules = contract.get("rules", [])
    by_id = {r.get("id"): r for r in rules if isinstance(r, dict)}
    if len(rules) != len(by_id) or set(by_id) != IDS:
        problems.append("REQUIRED_FIFTEEN_RULES_MISSING_OR_DUPLICATE")
    statuses = Counter()
    for name in sorted(IDS):
        rule = by_id.get(name)
        if rule is None:
            continue
        st = rule.get("status")
        statuses[st] += 1
        if not rule.get("source_ids") or not all(
            ref in src_by_id for ref in rule.get("source_ids", [])
        ):
            problems.append(f"RULE_WITHOUT_PRIMARY_SOURCE:{name}")
        if name == "TT01":
            if st != "SOURCE_EXPLICIT":
                problems.append("CANONICAL_SOURCE_IDENTITY_NOT_EXPLICIT")
            continue
        expected = (
            "AUTHOR_EXACT_IMPLEMENTABLE" if name in EXACT_RULES
            else "QORE_VARIANT_DOCUMENTED" if name in QORE_RULES
            else "EVIDENCE_VERIFIED"
        )
        if st != expected:
            problems.append(f"NOT_RESOLVED:{name}:{st}")
        if not rule.get("reviewer_adjudication"):
            problems.append(f"NO_REVIEWER_ADJUDICATION:{name}")
        if not rule.get("evidence_test_ref"):
            problems.append(f"NO_EXAMPLE_OR_TEST_EVIDENCE:{name}")
        if name == "TT15" and not rule.get("author_video_timecodes"):
            problems.append("NO_AUTHOR_VIDEO_FIXTURE_TIMECODES")
    verify = contract.get("verification", {})
    for key in EVIDENCE_FLAGS + AVAILABILITY_INVARIANTS:
        if verify.get(key) is not True:
            problems.append(f"REQUIRED_GATE_FLAG_FALSE:{key}")
    # Structural go must not be obtained by toggling one status field.
    allow = not problems
    if allow and verify.get("economic_replay_authorized") is not True:
        problems.append("NO_EXPLICIT_AUTHORIZATION_RECORD")
        allow = False
    if not allow and verify.get("economic_replay_authorized") is True:
        problems.append("ILLEGAL_AUTHORIZATION_WHILE_BLOCKED")
    return {
        "identity": IDENTITY,
        "author_source_gate": (
            "AUTHOR_SOURCE_AND_IMPLEMENTATION_READY_FOR_PREREGISTERED_TEST"
            if allow else "BLOCKED_SOURCE_FIDELITY"
        ),
        "economic_replay_authorized": allow,
        "blocking_reason_count": len(problems),
        "blocking_reasons": problems,
        "rule_status_counts": dict(statuses),
        "source_refs_checked": len(src_by_id),
        "author_fidelity_not_measured_by_this_script": True,
        "profitability_not_measured": True,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("contract", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--assert-blocked", action="store_true")
    args = parser.parse_args()
    report = decide(json.loads(args.contract.read_text(encoding="utf-8")))
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(
            json.dumps(report, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    print("TTRADES_AUTHOR_FIDELITY_GATE", json.dumps(report, sort_keys=True))
    if args.assert_blocked:
        if report["economic_replay_authorized"]:
            raise SystemExit("UNEXPECTED AUTHOR EXACT AUTHORIZATION: ASSERT BLOCKED FAILED")
    elif not report["economic_replay_authorized"]:
        raise SystemExit(3)


if __name__ == "__main__":
    main()
