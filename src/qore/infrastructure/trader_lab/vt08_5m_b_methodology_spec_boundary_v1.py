"""Independent methodology-spec and as-of contract preflight for VT08 5M.

Architect A supplies a TEXT-ONLY frozen spec (rule tags A/B/C/D and quotes).
Architect B owns this validator independently, never imports A methodology code.
Passing this preflight NEVER signs the A/B manifest or grants cognition/orders.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal, InvalidOperation
from typing import Final
from urllib.parse import urlparse

FAMILIES: Final = (
    "C2_COMPLETED",
    "C3_CONTINUATION_FROM_C2",
    "C3_CLOSURE_TO_C4",
)
ROLES: Final = (
    "REFERENCE_SWING", "POI", "EQ", "CISD", "PROTECTED_SWING", "FAMILY_BOUNDARY",
)
STATUS: Final = ("A", "B", "C", "D")
POI_CATEGORIES: Final = (
    "FVG", "HIGH", "LOW", "ORDER_BLOCK", "PROTECTED_SWING", "OPPOSING_CANDLE",
    "LIQUIDITY",
)
HEX64: Final = re.compile(r"[0-9a-f]{64}\Z")
# An actual two-party frozen manifest does not exist. Do not take an
# arbitrary caller-provided digest or permission boolean as approval.
APPROVED_JOINT_SOURCE_MANIFEST_SHA256: Final[str | None] = None


class BMethodologyBoundaryError(ValueError):
    """Methodology/time/lineage claims not independently demonstrable."""


@dataclass(frozen=True, slots=True)
class BMethodologyPreflight:
    family: str
    rule_status: tuple[tuple[str, str], ...]
    chronology_valid: bool
    blockers: tuple[str, ...]
    source_complete: bool = False
    cognitive_ready: bool = False
    order_authorized: bool = False


def _time(raw: object, name: str) -> datetime:
    if not isinstance(raw, str):
        raise BMethodologyBoundaryError(f"{name}: missing closed-source timestamp")
    try:
        dt = datetime.fromisoformat(raw)
    except ValueError as exc:
        raise BMethodologyBoundaryError(f"{name}: invalid source timestamp") from exc
    if dt.tzinfo is None or dt.utcoffset() is None:
        raise BMethodologyBoundaryError(f"{name}: timezone missing")
    return dt.astimezone(UTC)


def _hash(raw: object, name: str) -> str:
    if not isinstance(raw, str) or not HEX64.fullmatch(raw):
        raise BMethodologyBoundaryError(f"{name}: source SHA-256 missing")
    return raw


def _decimal(raw: object, name: str) -> Decimal:
    try:
        n = Decimal(str(raw))
    except (InvalidOperation, ValueError) as exc:
        raise BMethodologyBoundaryError(f"{name}: invalid Decimal") from exc
    if not n.is_finite() or n <= 0:
        raise BMethodologyBoundaryError(f"{name}: expected positive finite price")
    return n


def _closed_proof(raw: object, name: str, *, before: datetime) -> datetime:
    """Source barcode and availability must independently precede decision."""
    if not isinstance(raw, dict):
        raise BMethodologyBoundaryError(f"{name}: no source bar provenance")
    if not isinstance(raw.get("source_bar_id"), str) or not raw["source_bar_id"]:
        raise BMethodologyBoundaryError(f"{name}: source_bar_id missing")
    _hash(raw.get("source_bar_sha256"), name)
    closed = _time(raw.get("closed_at"), name)
    observed = _time(raw.get("available_at"), f"{name}.available_at")
    if closed > observed or observed >= before:
        raise BMethodologyBoundaryError(
            f"{name}: future/at-decision bar not causally available"
        )
    return closed


def validate_text_only_spec(spec: object) -> dict[str, dict[str, dict[str, object]]]:
    """Validate a producer-authored *text* rule matrix, without source code.

    A text citation is not independently proof of correct historical values:
    the verifier must still adjudicate video/screenshots/source-event inputs.
    """
    if not isinstance(spec, dict) or spec.get("schema") != (
        "qore.vt08.a_b_methodology_text_spec.proposed.v1"
    ):
        raise BMethodologyBoundaryError("missing producer TEXT-only spec v1")
    if spec.get("producer_role") != "ARCHITECT_A_SOURCE" or spec.get(
        "verifier_role"
    ) != "ARCHITECT_B_INDEPENDENT":
        raise BMethodologyBoundaryError("producer/verifier independence not declared")
    if spec.get("jointly_approved") is not False or spec.get(
        "cognition_authorized"
    ) is not False:
        raise BMethodologyBoundaryError("unsigned spec claims joint authority")
    raw_rules = spec.get("rules")
    if not isinstance(raw_rules, list):
        raise BMethodologyBoundaryError("missing source rules")
    out: dict[str, dict[str, dict[str, object]]] = {
        f: {} for f in FAMILIES
    }
    seen_ids: set[str] = set()
    for rule in raw_rules:
        if not isinstance(rule, dict):
            raise BMethodologyBoundaryError("source rule not structured")
        family, role, tag = rule.get("family"), rule.get("role"), rule.get("tag")
        identifier = rule.get("id")
        if family not in FAMILIES or role not in ROLES or tag not in STATUS:
            raise BMethodologyBoundaryError("bad family/role/A-B-C-D tag")
        if not isinstance(identifier, str) or not identifier or identifier in seen_ids:
            raise BMethodologyBoundaryError("duplicate or missing rule identity")
        seen_ids.add(identifier)
        if role in out[family]:
            raise BMethodologyBoundaryError("ambiguous multiple rules per family role")
        required = rule.get("required_closed_inputs")
        if not isinstance(required, list) or not required or not all(
            isinstance(v, str) and v for v in required
        ):
            raise BMethodologyBoundaryError("rule lacks closed-input declaration")
        if tag == "A":
            url = rule.get("source_url")
            citation = rule.get("source_quote")
            section = rule.get("source_section")
            published = rule.get("source_published_date")
            if (not isinstance(url, str)
                or urlparse(url).scheme != "https"
                or urlparse(url).hostname not in {"ttrades.com", "www.ttrades.com"}
                or not isinstance(citation, str)
                or not citation.strip()
                or len(citation.split()) > 25
                or not isinstance(section, str)
                or not section.strip()
                or not isinstance(published, str)
                or len(published) != 10):
                raise BMethodologyBoundaryError(
                    "A must cite brief verbatim primary TTrades quote, URL, section, date"
                )
        elif tag == "B":
            if not isinstance(rule.get("inference_rationale"), str) or not rule[
                "inference_rationale"
            ].strip():
                raise BMethodologyBoundaryError("B inference rationale required")
        elif tag == "C":
            if not isinstance(rule.get("qore_formalization"), str) or not rule[
                "qore_formalization"
            ].strip():
                raise BMethodologyBoundaryError("C must be explicitly labeled QORE")
        else:
            if not isinstance(rule.get("ambiguity"), str) or not rule[
                "ambiguity"
            ].strip():
                raise BMethodologyBoundaryError("D requires unresolved ambiguity")
        if role == "POI":
            allowed = rule.get("poi_allowed_for_this_family")
            if not isinstance(allowed, list) or not allowed or not set(
                allowed
            ).issubset(POI_CATEGORIES):
                raise BMethodologyBoundaryError(
                    "POI must be declared separately for EACH family"
                )
        out[family][role] = rule
    for family, roles in out.items():
        if set(roles) != set(ROLES):
            raise BMethodologyBoundaryError(
                f"{family}: text spec needs all six independently tagged roles"
            )
    return out


def verify_causal_event(
    event: object,
    text_spec: object,
) -> BMethodologyPreflight:
    """Check referential swing known before C2, strict closed-M15 confirmation.

    Does NOT allow retrospective C2 swing inference from C2's own extreme;
    does NOT treat a mathematically correct EQ as proof of source-valid swing.
    """
    rules = validate_text_only_spec(text_spec)
    if not isinstance(event, dict):
        raise BMethodologyBoundaryError("missing producer event")
    family = event.get("family")
    if family not in FAMILIES:
        raise BMethodologyBoundaryError("undefined source family")
    own = rules[family]
    c2_open = _time(event.get("c2_opened_at"), "c2.open")
    c2_close = _time(event.get("c2_closed_at"), "c2.close")
    decision = _time(event.get("decision_at"), "decision")
    entry = _time(event.get("hypothetical_entry_at"), "entry")
    if c2_close != c2_open + timedelta(hours=4) or decision < c2_close:
        raise BMethodologyBoundaryError("C2 must H4 close before EQ decision")
    if entry <= decision:
        raise BMethodologyBoundaryError("entry must be after source decision")
    if event.get("research_only") is not True or event.get(
        "order_authorized"
    ) is not False:
        raise BMethodologyBoundaryError("cannot authorize live/order from preflight")
    reference = event.get("reference_swing")
    if not isinstance(reference, dict):
        raise BMethodologyBoundaryError("missing pre-C2 reference swing")
    swing_seen = _time(reference.get("identified_at"), "swing.identified_at")
    if swing_seen >= c2_open:
        raise BMethodologyBoundaryError(
            "swing reference identified ex-post during/after C2 (lookahead)"
        )
    _closed_proof(reference.get("source_proof"), "reference_swing", before=c2_open)
    _closed_proof(reference.get("poi_proof"), "swing_poi", before=c2_open)
    if reference.get("side") not in ("long", "short") or reference.get(
        "side"
    ) != event.get("side"):
        raise BMethodologyBoundaryError("swing side unknown/mismatched")
    poi = event.get("poi")
    if not isinstance(poi, dict):
        raise BMethodologyBoundaryError("missing source-family POI")
    if poi.get("type") not in own["POI"]["poi_allowed_for_this_family"]:
        raise BMethodologyBoundaryError("POI not sourced for this exact family")
    _closed_proof(poi.get("source_proof"), "family_poi", before=entry)
    for role in ("cisd", "protected_swing"):
        proof = event.get(role)
        if not isinstance(proof, dict) or proof.get("confirmation") != "M15_CLOSED":
            raise BMethodologyBoundaryError(f"{role}: M15 close confirmation required")
        _closed_proof(proof.get("source_proof"), role, before=entry)
    c3_close: datetime | None = None
    if family == "C3_CLOSURE_TO_C4":
        c3_close = _time(event.get("c3_closed_at"), "c3.close")
        if c3_close != c2_close + timedelta(hours=4) or decision < c3_close:
            raise BMethodologyBoundaryError("C3 closure cannot use future H4")
        if entry <= c3_close:
            raise BMethodologyBoundaryError("C3 close is not an inside-C3 entry")
        for role in ("cisd", "protected_swing"):
            proof = event[role]
            bar = _time(proof["source_proof"]["closed_at"], role)
            if not c2_close < bar <= c3_close:
                raise BMethodologyBoundaryError(
                    f"{role}: C3 proxy/source confirmation cannot consume C4"
                )
        if event.get("c4_first_m15_observed") is True:
            observed = _time(event.get("c4_first_m15_closed_at"), "c4.m15")
            if observed != c3_close + timedelta(minutes=15) or decision < observed:
                raise BMethodologyBoundaryError("C4 M15 observation used before close")
    if event.get("c2_dual_sweep") is True and event.get(
        "dual_sweep_adjudicated"
    ) is not True:
        # Explicit exclusion, not a silent Model A or Model B classification.
        blockers = ("B_SOURCE:C2_DUAL_SWEEP_UNADJUDICATED",)
    else:
        blockers = ()
    if event.get("body_engulf_strong_proxy") is True and event.get(
        "body_engulf_source_tag"
    ) != "C_QORE_FULL_BODY_ENGULF_GEOMETRY_UNVERIFIED":
        raise BMethodologyBoundaryError(
            "36 body-engulf shapes must be C QORE non-source geometry"
        )
    if event.get("proxy_as_real_density_estimate") is not False:
        raise BMethodologyBoundaryError("M15 CISD/PS proxy cannot estimate real density")
    basis = event.get("eq_basis")
    direction = event.get("side")
    candle = event.get("c2_candle")
    if not isinstance(candle, dict):
        raise BMethodologyBoundaryError("C2 H4 source price missing")
    op = _decimal(candle.get("open"), "C2.open")
    hi = _decimal(candle.get("high"), "C2.high")
    lo = _decimal(candle.get("low"), "C2.low")
    close = _decimal(candle.get("close"), "C2.close")
    if not lo <= min(op, close) <= max(op, close) <= hi:
        raise BMethodologyBoundaryError("invalid C2 H4 OHLC")
    if family == "C2_COMPLETED":
        if op == close:
            blockers += ("B_SOURCE:C2_DOJI_EQ_REGIME_UNRESOLVED",)
        with_swing = (close > op) == (direction == "long")
        expected_basis = (
            "C2_FULL_WICK_TO_WICK_WITH_SWING" if with_swing
            else "C2_CLOSE_TO_EXTREME_AGAINST_SWING"
        )
        if basis != expected_basis and op != close:
            raise BMethodologyBoundaryError("C2 full/wick EQ branch wrong")
        if not with_swing and op != close:
            # Additional pre-C2 witness is mandatory even though C2 OHLC is known.
            if not reference.get("pre_c2_swing_regime_independently_attested"):
                blockers += ("B_SOURCE:PRE_C2_SWING_REGIME_NOT_ATTESTED",)
    else:
        if basis != "C3_FULL_WICK_TO_WICK_AFTER_CLOSURE":
            raise BMethodologyBoundaryError("C3 must use full wick-to-wick EQ")
    tags = tuple((role, str(own[role]["tag"])) for role in ROLES)
    for role, tag in tags:
        if tag != "A":
            blockers += (f"B_SOURCE:{family}:{role}_NOT_A",)
    # Even ALL A-labelled rules and passing timestamp shapes are not enough
    # without independent primary-source adjudication and bilateral freeze.
    blockers += ("B_SOURCE:INDEPENDENT_SOURCE_ADJUDICATION_PENDING",
                 "B_SOURCE:JOINT_MANIFEST_NOT_SIGNED")
    return BMethodologyPreflight(
        family=str(family), rule_status=tags,
        chronology_valid=True, blockers=blockers,
    )


def audit_proxy_metrics(metrics: object) -> dict[str, object]:
    """Separate incomparable counts, never convert 129 proxies into trades."""
    if not isinstance(metrics, dict):
        raise BMethodologyBoundaryError("missing strict proxy census")
    required = {
        "c3_shapes": 294, "c4_owner": 213, "outside_qore_owner": 81,
        "c2_dual_sweep_unadjudicated": 105,
        "cisd_ps_m15_formal_proxy": 129,
        "qore_strict_full_body_engulf_geometry": 36,
        "source_confirmed_cisd_ps": 0,
        "executed_trades": 0,
    }
    for key, observed in required.items():
        if type(metrics.get(key)) is not int or metrics[key] != observed:
            raise BMethodologyBoundaryError(f"{key}: census changed/summed")
    if metrics.get("proxy_density_extrapolation") is not None:
        raise BMethodologyBoundaryError("129 proxies cannot forecast real density")
    if metrics.get("qore_body_engulf_rule_tag") != "C":
        raise BMethodologyBoundaryError("36 body engulf proxy requires tag C")
    if metrics.get("body_engulf_source_verified") is not False:
        raise BMethodologyBoundaryError("QORE full-body engulf unverified in source")
    if metrics.get("dual_sweep_rule_tag") != "D":
        raise BMethodologyBoundaryError("105 double-sweep cases remain D")
    return {
        "c3_source_shapes_SHAPE_ONLY": 294,
        "c4_outside_owner_QORE_CAPABILITY_GAP": 81,
        "m15_CISD_PS_FORMAL_PROXY_NOT_DENSITY": 129,
        "source_confirmed_CISD_PS": 0,
        "QORE_FULL_BODY_ENGULF_GEOMETRY_C_UNVERIFIED": 36,
        "C2_DUAL_SWEEP_D_UNRESOLVED": 105,
        "source_complete": 0, "cognitive_ready": 0,
        "trades_executed": 0, "research_only": True,
    }
