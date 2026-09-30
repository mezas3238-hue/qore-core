"""Architect-B CNH component identity closure.

This module extends the existing GW-2 ISO 4217 component evidence with a
separate authoritative identity for offshore renminbi (CNH). It deliberately
does not claim that CNH is a current ISO 4217 code, alias CNH to CNY, or map a
provider symbol to a canonical tradable instrument.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Final, cast

IDENTITY: Final = "SHARED_B_GW2_CNH_COMPONENT_IDENTITY_001"
EXPECTED_ISO_IDENTITY: Final = "QORE_SHARED_GW2_FX_ISO4217_EVIDENCE_001"
EXPECTED_AUTHORITY_IDENTITY: Final = "SHARED_B_GW2_CNH_AUTHORITY_EVIDENCE_001"


class SharedBCnhIdentityError(ValueError):
    """CNH identity evidence failed closed."""


def _load(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise SharedBCnhIdentityError(f"{path} must contain a JSON object")
    return cast(dict[str, Any], payload)


def _fingerprint(payload: object) -> str:
    return hashlib.sha256(
        json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        ).encode("utf-8")
    ).hexdigest()


def resolve(
    *,
    iso_evidence_path: Path,
    authority_evidence_path: Path,
) -> dict[str, object]:
    iso = _load(iso_evidence_path)
    authority = _load(authority_evidence_path)

    if iso.get("identity") != EXPECTED_ISO_IDENTITY:
        raise SharedBCnhIdentityError("unexpected ISO evidence identity")
    if authority.get("identity") != EXPECTED_AUTHORITY_IDENTITY:
        raise SharedBCnhIdentityError("unexpected CNH authority identity")

    unresolved = iso.get("unresolved_currency_codes")
    if not isinstance(unresolved, list) or len(unresolved) != 1:
        raise SharedBCnhIdentityError(
            "expected exactly one unresolved ISO provider currency code"
        )
    unresolved_row = unresolved[0]
    if not isinstance(unresolved_row, dict):
        raise SharedBCnhIdentityError("invalid unresolved currency row")
    if unresolved_row.get("provider_currency_code") != "CNH":
        raise SharedBCnhIdentityError("the sole unresolved code must be CNH")
    if unresolved_row.get("canonical_alias_inferred") is not False:
        raise SharedBCnhIdentityError("CNH must never be auto-aliased")

    assertions = authority.get("assertions")
    if not isinstance(assertions, dict):
        raise SharedBCnhIdentityError("authority assertions missing")
    required_false = (
        "canonical_alias_to_cny",
        "cny_and_cnh_interchangeable",
        "iso4217_current_code_claim",
        "tradable_instrument_identity_claim",
        "provider_symbol_mapping_claim",
        "calendar_claim",
        "venue_claim",
    )
    if assertions.get("provider_code") != "CNH":
        raise SharedBCnhIdentityError("authority provider code must be CNH")
    if assertions.get("economic_identity") != "OFFSHORE_RENMINBI":
        raise SharedBCnhIdentityError("CNH economic identity missing")
    if any(assertions.get(key) is not False for key in required_false):
        raise SharedBCnhIdentityError("CNH authority scope was widened")

    sources = authority.get("sources")
    if not isinstance(sources, list) or len(sources) < 2:
        raise SharedBCnhIdentityError("CNH requires independent authority refs")
    if any(
        not isinstance(row, dict)
        or row.get("authority") != "HONG_KONG_MONETARY_AUTHORITY"
        for row in sources
    ):
        raise SharedBCnhIdentityError("CNH authority must be HKMA")

    verified_codes = iso.get("verified_currency_codes")
    if not isinstance(verified_codes, list):
        raise SharedBCnhIdentityError("verified ISO currency evidence missing")
    iso_codes = {
        str(row.get("provider_currency_code"))
        for row in verified_codes
        if isinstance(row, dict)
        and row.get("iso4217_current_verified") is True
    }
    if len(iso_codes) != 20 or "CNH" in iso_codes:
        raise SharedBCnhIdentityError("unexpected ISO component universe")

    pairs = iso.get("pairs")
    if not isinstance(pairs, list) or len(pairs) != 60:
        raise SharedBCnhIdentityError("expected exact 60 FX provider pairs")

    resolved_pairs: list[dict[str, object]] = []
    for item in pairs:
        if not isinstance(item, dict):
            raise SharedBCnhIdentityError("invalid FX pair evidence")
        base = str(item.get("base_currency_code"))
        quote = str(item.get("quote_currency_code"))
        base_verified = base in iso_codes or base == "CNH"
        quote_verified = quote in iso_codes or quote == "CNH"
        components_verified = base_verified and quote_verified
        resolved_pairs.append(
            {
                "provider": item.get("provider"),
                "provider_symbol_id": item.get("provider_symbol_id"),
                "provider_symbol": item.get("provider_symbol"),
                "base_currency_code": base,
                "quote_currency_code": quote,
                "base_component_identity_verified": base_verified,
                "quote_component_identity_verified": quote_verified,
                "currency_components_verified": components_verified,
                "provider_neutral_reference_key": (
                    f"QORE:FX_REFERENCE:{base}/{quote}"
                    if components_verified
                    else None
                ),
                "provider_symbol_to_reference_mapping_authorized": False,
                "canonical_tradable_identity_verified": False,
            }
        )

    if not all(row["currency_components_verified"] for row in resolved_pairs):
        raise SharedBCnhIdentityError(
            "all 60 FX component identities should now be resolved"
        )

    payload: dict[str, object] = {
        "identity": IDENTITY,
        "status": "FX_COMPONENT_IDENTITY_COMPLETE_PRODUCT_IDENTITY_UNRESOLVED",
        "source_iso_evidence_fingerprint_sha256": iso[
            "evidence_fingerprint_sha256"
        ],
        "authority_evidence_fingerprint_sha256": _fingerprint(authority),
        "iso4217_current_verified_currency_code_count": 20,
        "non_iso_authority_verified_currency_code_count": 1,
        "currency_component_identity_verified_count": 21,
        "cnh_component": {
            "provider_currency_code": "CNH",
            "economic_identity": "OFFSHORE_RENMINBI",
            "iso4217_current_verified": False,
            "authority_identity_verified": True,
            "canonical_alias_to_cny": False,
        },
        "fx_pair_count": 60,
        "fx_pairs_with_all_currency_components_verified": 60,
        "pairs": resolved_pairs,
        "provider_symbol_to_reference_mapping_authorized": False,
        "canonical_tradable_identity_verified_count": 0,
        "calendar_mapping_authorized": False,
        "relational_claims_authorized": False,
        "historical_market_data_read": False,
        "target_or_outcome_read": False,
        "r6_r5_read": False,
        "fresh_holdout_opened": False,
        "productive_authority": False,
    }
    payload["resolution_fingerprint_sha256"] = _fingerprint(payload)
    return payload


def write_resolution(
    *,
    iso_evidence_path: Path,
    authority_evidence_path: Path,
    output_path: Path,
) -> dict[str, object]:
    payload = resolve(
        iso_evidence_path=iso_evidence_path,
        authority_evidence_path=authority_evidence_path,
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(payload, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    return payload
