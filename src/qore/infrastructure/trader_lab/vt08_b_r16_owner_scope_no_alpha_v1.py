"""VT08 Owner R16 scope firewall: QORE-alpha excluded from current VT08.

The owner explicitly banned mixing QORE-alpha methodology, models, cognitive
signals or derived tracks into VT08. This is a research-governance check of
the frozen source dataset plus a reusable fail-closed manifest validator,
not an admission of source author fidelity, profitability or broker orders.
"""
from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping

PROGRAM = "VT08"
FAMILY = "BULLISH_M30_C2_REVERSAL_M3_CISD_C3_POSITIONAL"
FROZEN_SCHEMA = "qore.vt08.a.frozen_bullish_m30m3.source_funnel.v1"
STAGE = "UNIQUE_M3_CISD_PS_SHAPE_REQUIRES_AUTHOR_ADJUDICATION"
MARKETS = frozenset(("EURJPY", "USDCHF", "NZDUSD", "CADJPY", "USDCAD"))
EXPECTED = {"EURJPY": 538, "USDCHF": 518, "NZDUSD": 550,
            "CADJPY": 516, "USDCAD": 535}
AUTHORITY = {
    "trader_id": "VT08",
    "methodology_program": "VT08_TTRADES_CURRENT",
    "cognitive_program": "VT08_COGNITION_CURRENT",
    "variant": "CURRENT_ONLY",
    "family": FAMILY,
}
EXCLUDED = re.compile(
    r"(?:qore[\s_-]*alpha|vt08[\s_-]*alpha|"
    r"alpha[\s_-]*(?:fork|model|strategy|qore))",
    re.IGNORECASE,
)
FOREIGN_STRATEGY_FIELDS = (
    "fallback_strategy", "external_strategy",
    "imported_model", "foreign_signal_origin",
    "alpha_features", "alternate_lineage", "parallel_track",
)


def no_excluded_alpha_lineage(value: object) -> None:
    """Reject alpha reference in active program metadata or candidate lineage."""
    remaining: list[object] = [value]
    while remaining:
        current = remaining.pop()
        if isinstance(current, Mapping):
            for key, child in current.items():
                if isinstance(key, str) and EXCLUDED.search(key):
                    raise ValueError("VT08 OWNER BLOCKED excluded QORE-alpha key")
                remaining.append(child)
        elif isinstance(current, (list, tuple)):
            remaining.extend(current)
        elif isinstance(current, str) and EXCLUDED.search(current):
            raise ValueError("VT08 OWNER BLOCKED excluded QORE-alpha lineage")


def assert_single_vt08_current_manifest(payload: Mapping[str, object]) -> None:
    """Fail closed on variant, alpha fallback, false economic permissions."""
    no_excluded_alpha_lineage(payload)
    for key, wanted in AUTHORITY.items():
        if payload.get(key) != wanted:
            raise ValueError("VT08 OWNER scope identity/family mismatch: " + key)
    for key in FOREIGN_STRATEGY_FIELDS:
        if key in payload and payload[key] not in (None, [], (), ""):
            raise ValueError("VT08 OWNER disallows external/parallel strategy: " + key)
    # R16 only authorizes scrutiny of frozen *source-only* research snapshots.
    for key in ("sizing_used", "holdout_7y_accessed", "orders_enabled",
                "author_source_complete", "cognitive_admitted"):
        if payload.get(key) is not False:
            raise ValueError("VT08 OWNER source-only gate not fail-closed: " + key)
    if type(payload.get("broker_fills")) is not int or payload["broker_fills"] != 0:
        raise ValueError("VT08 OWNER forbids source-only broker fills")


def audit_frozen_source_program_scope(
    report: dict[str, object], *, expected_market: str,
) -> dict[str, object]:
    """Read every frozen source-positive case; preserve original denominator."""
    if expected_market not in MARKETS:
        raise ValueError("VT08 OWNER market outside approved frozen universe")
    no_excluded_alpha_lineage(report)
    if report.get("schema") != FROZEN_SCHEMA or report.get("market") != expected_market:
        raise ValueError("VT08 OWNER wrong VT08 frozen source identity")
    stage = report.get("stage_counts")
    examples = report.get("examples_by_stage")
    if not isinstance(stage, dict) or not isinstance(examples, dict):
        raise ValueError("VT08 OWNER missing frozen full source stages")
    cases = examples.get(STAGE)
    if (
        not isinstance(cases, list)
        or len(cases) != EXPECTED[expected_market]
        or stage.get(STAGE) != len(cases)
        or report.get("all_unique_proxy_cases_with_raw_receipts") != len(cases)
    ):
        raise ValueError("VT08 OWNER original positive census changed")
    if (
        report.get("source_complete_entries") != 0
        or report.get("real_cognitive_admissions") != 0
        or report.get("fills") != 0
        or report.get("sizing_applied") is not False
        or report.get("sealed_holdout_accessed") is not False
    ):
        raise ValueError("VT08 OWNER original source-only authority falsified")
    observed: set[str] = set()
    for case in cases:
        if (
            not isinstance(case, dict)
            or case.get("family") != FAMILY
            or case.get("market") != expected_market
            or case.get("stage") != STAGE
            or case.get("A_rule_complete") is not False
            or case.get("B_signoff") is not False
            or case.get("cognitive_ready") is not False
            or case.get("broker_fill") is not False
            or case.get("pnl_read") is not False
        ):
            raise ValueError("VT08 OWNER frozen candidate has foreign/source-true identity")
        identity = (case.get("c2_opened_at_utc"), case.get("decision_at_utc"))
        if not all(isinstance(x, str) for x in identity):
            raise ValueError("VT08 OWNER missing source case times")
        id_digest = hashlib.sha256(json.dumps(
            (expected_market, *identity), separators=(",", ":")
        ).encode()).hexdigest()
        if id_digest in observed:
            raise ValueError("VT08 OWNER duplicate candidate")
        observed.add(id_digest)
    return {
        "owner_scope": "VT08_CURRENT_ONLY_NO_QORE_ALPHA",
        "market": expected_market,
        "frozen_vt08_cases_verified": len(observed),
        "alpha_methodology_admitted": False,
        "alpha_cognition_admitted": False,
        "alpha_signals_admitted": False,
        "alternate_programs_authorized": 0,
        "source_author_complete": 0,
        "cognitive_admissions": 0,
        "broker_fills": 0,
        "economic_gates_evaluated": False,
        "holdout_7y_accessed": False,
        "sizing_used": False,
        "owner_scope_governance_only": True,
    }
