from __future__ import annotations

import json
from pathlib import Path

import pytest

from qore.infrastructure.core_stack_v2.shared_b_fx_cnh_identity import (
    SharedBCnhIdentityError,
    resolve,
)


def _write(path: Path, payload: object) -> Path:
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def _iso() -> dict[str, object]:
    verified = [
        {
            "provider_currency_code": code,
            "iso4217_current_verified": True,
        }
        for code in (
            "AUD",
            "CAD",
            "CHF",
            "CZK",
            "DKK",
            "EUR",
            "GBP",
            "HKD",
            "HUF",
            "JPY",
            "MXN",
            "NOK",
            "NZD",
            "PLN",
            "SEK",
            "SGD",
            "THB",
            "TRY",
            "USD",
            "ZAR",
        )
    ]
    pairs = [
        {
            "provider": "CTRADER_DEMO",
            "provider_symbol_id": index + 1,
            "provider_symbol": f"P{index:02d}",
            "base_currency_code": "USD",
            "quote_currency_code": "CNH" if index == 0 else "EUR",
        }
        for index in range(60)
    ]
    return {
        "identity": "QORE_SHARED_GW2_FX_ISO4217_EVIDENCE_001",
        "evidence_fingerprint_sha256": "a" * 64,
        "verified_currency_codes": verified,
        "unresolved_currency_codes": [
            {
                "provider_currency_code": "CNH",
                "iso4217_current_verified": False,
                "canonical_alias_inferred": False,
            }
        ],
        "pairs": pairs,
    }


def _authority() -> dict[str, object]:
    return {
        "identity": "SHARED_B_GW2_CNH_AUTHORITY_EVIDENCE_001",
        "sources": [
            {
                "authority": "HONG_KONG_MONETARY_AUTHORITY",
                "url": "https://example.invalid/a",
            },
            {
                "authority": "HONG_KONG_MONETARY_AUTHORITY",
                "url": "https://example.invalid/b",
            },
        ],
        "assertions": {
            "provider_code": "CNH",
            "economic_identity": "OFFSHORE_RENMINBI",
            "canonical_alias_to_cny": False,
            "cny_and_cnh_interchangeable": False,
            "iso4217_current_code_claim": False,
            "tradable_instrument_identity_claim": False,
            "provider_symbol_mapping_claim": False,
            "calendar_claim": False,
            "venue_claim": False,
        },
    }


def test_cnh_closes_component_identity_without_product_claim(tmp_path: Path) -> None:
    payload = resolve(
        iso_evidence_path=_write(tmp_path / "iso.json", _iso()),
        authority_evidence_path=_write(
            tmp_path / "authority.json",
            _authority(),
        ),
    )

    assert payload["currency_component_identity_verified_count"] == 21
    assert payload["fx_pairs_with_all_currency_components_verified"] == 60
    assert payload["canonical_tradable_identity_verified_count"] == 0
    assert payload["provider_symbol_to_reference_mapping_authorized"] is False
    assert payload["calendar_mapping_authorized"] is False
    assert payload["cnh_component"] == {
        "provider_currency_code": "CNH",
        "economic_identity": "OFFSHORE_RENMINBI",
        "iso4217_current_verified": False,
        "authority_identity_verified": True,
        "canonical_alias_to_cny": False,
    }


def test_cnh_refuses_cny_alias(tmp_path: Path) -> None:
    authority = _authority()
    assertions = authority["assertions"]
    assert isinstance(assertions, dict)
    assertions["canonical_alias_to_cny"] = True

    with pytest.raises(SharedBCnhIdentityError, match="scope was widened"):
        resolve(
            iso_evidence_path=_write(tmp_path / "iso.json", _iso()),
            authority_evidence_path=_write(
                tmp_path / "authority.json",
                authority,
            ),
        )


def test_cnh_refuses_unexpected_unresolved_currency(tmp_path: Path) -> None:
    iso = _iso()
    unresolved = iso["unresolved_currency_codes"]
    assert isinstance(unresolved, list)
    assert isinstance(unresolved[0], dict)
    unresolved[0]["provider_currency_code"] = "ABC"

    with pytest.raises(
        SharedBCnhIdentityError,
        match="sole unresolved code must be CNH",
    ):
        resolve(
            iso_evidence_path=_write(tmp_path / "iso.json", iso),
            authority_evidence_path=_write(
                tmp_path / "authority.json",
                _authority(),
            ),
        )
