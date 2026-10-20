"""R9 independent G2 SOURCE-only reviewer packet, never an auto certificate.

Review materials omit *engine-derived* C0/C1 direction/conflict labels and source
identity. The labels remain separately sealed for post-signature audit only.
All historical observations were consumed R5-R8, NOT new OOS.
"""
from __future__ import annotations

import hashlib
import json
from collections import Counter
from datetime import UTC, datetime, timedelta
from typing import Any

from qore.infrastructure.traders.crt_pure_identity import CrtPureMarket

SCHEMA = "qore.vt08.crt.g2_independent_blind_36.r9.research_only.v1"
H4 = timedelta(hours=4)
CANDLES = ("C0", "C1", "C2")
ALLOWED_CHOICES = (
    "C0", "C1", "BOTH_AMBIGUOUS", "NEITHER_VALID", "INSUFFICIENT_SOURCE",
)
PRICE_KEYS = (
    "open_relative", "high_relative", "low_relative", "close_relative"
)


def _canon(d: dict[str, Any]) -> bytes:
    return json.dumps(d, sort_keys=True, separators=(",", ":")).encode()


def _aware(s: str) -> datetime:
    d = datetime.fromisoformat(s)
    if d.tzinfo is None or d.utcoffset() is None:
        raise ValueError("G2 blind temporal witnesses must have timezone")
    return d.astimezone(UTC)


def _validated_ohlc(o: dict[str, Any], at: datetime) -> dict[str, Any]:
    if set(o) != {"opened_at_utc", *PRICE_KEYS}:
        raise ValueError("G2 H4 source payload must use exact OHLC keys")
    start = _aware(o["opened_at_utc"])
    if start + H4 > at:
        raise ValueError("G2 reviewer cannot receive an unclosed H4")
    if any(type(o[k]) is not int or o[k] <= 0 for k in PRICE_KEYS):
        raise ValueError("G2 original OHLC must be positive integral coordinates")
    if not (
        o["low_relative"] <= min(o["open_relative"], o["close_relative"])
        and max(o["open_relative"], o["close_relative"]) <= o["high_relative"]
    ):
        raise ValueError("G2 original OHLC invalid or fabricated")
    return dict(o)


def build_g2_independent_review_packets(
    market: CrtPureMarket,
    cases: tuple[dict[str, Any], ...],
) -> tuple[
    dict[str, Any],
    tuple[dict[str, Any], ...],
    tuple[dict[str, Any], ...],
    tuple[dict[str, Any], ...],
]:
    """Two outputs must never be combined when handing off to a reviewer."""
    if market not in (CrtPureMarket.AUDUSD, CrtPureMarket.USDJPY):
        raise ValueError("BTCUSD original Atlas sample is frozen")
    reviewer: list[dict[str, Any]] = []
    sealed: list[dict[str, Any]] = []
    templates: list[dict[str, Any]] = []
    original_ids: set[str] = set()
    blinded_ids: set[str] = set()
    distribution: Counter[str] = Counter()
    for original in cases:
        if (
            original.get("market") != market.value
            or original.get("selected_reference") is not None
            or original.get("independent_reviewer_adjudicated") is not False
            or original.get("owner_approval") is not False
            or original.get("not_a_trade") is not True
            or original.get("not_fresh_holdout") is not True
        ):
            raise ValueError("R9 cannot ingest other market or approved source")
        source_id = original.get("source_event_id")
        original_id = original.get("blind_case_id")
        if not isinstance(source_id, str) or not source_id:
            raise ValueError("missing frozen V3 source event")
        if not isinstance(original_id, str) or not original_id:
            raise ValueError("missing R5 G2 case identifier")
        if original_id in original_ids:
            raise ValueError("G2 source dispute identity repeated")
        original_ids.add(original_id)
        at = _aware(original["decision_clock_utc"])
        closed = _aware(original["c2_closed_at_utc"])
        if at <= closed:
            raise ValueError("G2 reviewer clock not later than C2 close")
        candles = tuple(
            {"H4": label, **_validated_ohlc(original[f"{label.lower()}_closed_h4"], at)}
            for label in CANDLES
        )
        opens = tuple(_aware(c["opened_at_utc"]) for c in candles)
        if opens[1] - opens[0] != H4 or opens[2] - opens[1] != H4:
            raise ValueError("G2 C0 C1 C2 clocks not contiguous")
        if opens[2] + H4 != closed:
            raise ValueError("G2 C2 declared close disagrees with OHLC")
        if original["c0_direction"] not in ("BULLISH", "BEARISH") or original[
            "c1_direction"
        ] not in ("BULLISH", "BEARISH"):
            raise ValueError("G2 engine sealed directions invalid")
        expected_conflict = (
            "SAME" if original["c0_direction"] == original["c1_direction"]
            else "OPPOSITE"
        )
        if original["conflict_kind"] != expected_conflict:
            raise ValueError("G2 original engine labels self-contradict")
        id_hash = hashlib.sha256(
            f"G2-R9|{market.value}|{original_id}".encode()
        ).hexdigest()[:28]
        if id_hash in blinded_ids:
            raise ValueError("G2 blinded identity repeated")
        blinded_ids.add(id_hash)
        review = {
            "schema": SCHEMA,
            "case_id": id_hash,
            "market": market.value,
            "decision_clock_utc": at.isoformat(),
            "closed_H4_C0_C1_C2": candles,
            "review_question": (
                "Independently determine relevant old CRT reference and "
                "direction from source-supported three-source CRT/QORE policy "
                "at this instant, or abstain. Only predecision evidence permitted."
            ),
            "allowed_answer_choices": ALLOWED_CHOICES,
            "proposed_reference": None,
            "reviewer_result": None,
            "independent_methodology_review_complete": False,
            "no_sizing": True,
            "not_a_trade": True,
            "not_fresh_OOS": True,
        }
        digest = hashlib.sha256(_canon(review)).hexdigest()
        sealed.append({
            "schema": SCHEMA,
            "case_id": id_hash,
            "source_event_id": source_id,
            "engine_case_id": original_id,
            "market": market.value,
            "engine_c0_direction": original["c0_direction"],
            "engine_c1_direction": original["c1_direction"],
            "engine_conflict_kind": expected_conflict,
            "reviewer_payload_sha256": digest,
            "release_to_reviewer_before_signed_review": False,
            "engine_labels_are_not_ground_truth": True,
            "no_sizing": True,
            "not_a_trade": True,
        })
        reviewer.append(review)
        templates.append({
            "schema": SCHEMA,
            "case_id": id_hash,
            "reviewer_payload_sha256": digest,
            "human_choice": None,
            "source_quote_locator": None,
            "causal_reason_for_choice": None,
            "counterexample_if_any": None,
            "independent_reviewer_github_review_verified": False,
            "owner_github_approval_verified": False,
            "methodology_gate_passed": False,
            "must_verify_external_github_identity": True,
        })
        distribution[expected_conflict] += 1
    if not reviewer:
        raise ValueError("empty G2 review packet")
    ordering = sorted(range(len(reviewer)), key=lambda i: reviewer[i]["case_id"])
    reviewer_out = tuple(reviewer[i] for i in ordering)
    sealed_out = tuple(sealed[i] for i in ordering)
    templates_out = tuple(templates[i] for i in ordering)
    if {x["case_id"] for x in reviewer_out} != {
        x["case_id"] for x in sealed_out
    } or {x["case_id"] for x in reviewer_out} != {
        x["case_id"] for x in templates_out
    }:
        raise ValueError("G2 sealed and reviewer packet identity mismatch")
    manifest = {
        "schema": SCHEMA,
        "market": market.value,
        "reviewer_cases": len(reviewer_out),
        "case_hashes": tuple(x["case_id"] for x in reviewer_out),
        "engine_distribution_SEALED_ONLY": dict(sorted(distribution.items())),
        "reviewer_packet_sha256": hashlib.sha256(
            b"\n".join(_canon(x) for x in reviewer_out)
        ).hexdigest(),
        "sealed_packet_sha256": hashlib.sha256(
            b"\n".join(_canon(x) for x in sealed_out)
        ).hexdigest(),
        "signed_review_received": False,
        "owner_signature_verified": False,
        "reviewer_signature_verified": False,
        "G_M1_PASS": False,
        "G_M2_PASS": False,
        "G_M5_ISSUED": False,
        "GLOBAL_CERTIFIED": False,
        "not_fresh_OOS": True,
        "no_sizing": True,
        "no_orders": True,
    }
    return manifest, reviewer_out, sealed_out, templates_out
