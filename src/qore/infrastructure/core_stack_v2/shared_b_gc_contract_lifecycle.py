"""Architect-B COMEX GC observed-contract lifecycle boundary.

Classifies the exact dated GC descriptors already sealed by B-15 against an
official COMEX lifecycle rule. It intentionally refuses to infer a current
front contract, roll rule or continuous series from contract ordering.
"""

from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime
from typing import cast

IDENTITY = "SHARED_B_GC_OBSERVED_CONTRACT_LIFECYCLE_001"
EXPECTED_COMMODITY_IDENTITY = "SHARED_B_COMMODITY_OBSERVATION_IDENTITY_PACK_001"
EXPECTED_AUTHORITY_IDENTITY = (
    "SHARED_B_GC_CONTRACT_LIFECYCLE_AUTHORITY_EVIDENCE_001"
)
_CONTRACT_RE = re.compile(
    r"^QORE:FUTURES_CONTRACT:COMEX_GOLD_FUTURES_100_TROY_OZ:"
    r"(?P<year>[0-9]{4})-(?P<month>[0-9]{2}):COMEX$"
)


class SharedBGcContractLifecycleError(ValueError):
    """GC lifecycle evidence failed closed."""


def _fingerprint(value: object) -> str:
    return hashlib.sha256(
        json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        ).encode("utf-8")
    ).hexdigest()


def _parse_aware(value: object, *, field: str) -> datetime:
    if not isinstance(value, str) or not value.strip():
        raise SharedBGcContractLifecycleError(f"{field} missing")
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as exc:
        raise SharedBGcContractLifecycleError(f"{field} invalid") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise SharedBGcContractLifecycleError(
            f"{field} must be timezone-aware"
        )
    return parsed


def build_gc_observed_contract_lifecycle(
    *,
    commodity_pack: dict[str, object],
    authority_evidence: dict[str, object],
    assessed_at: datetime,
) -> dict[str, object]:
    if commodity_pack.get("identity") != EXPECTED_COMMODITY_IDENTITY:
        raise SharedBGcContractLifecycleError(
            "unexpected commodity pack identity"
        )
    if authority_evidence.get("identity") != EXPECTED_AUTHORITY_IDENTITY:
        raise SharedBGcContractLifecycleError(
            "unexpected authority evidence identity"
        )
    if assessed_at.tzinfo is None or assessed_at.utcoffset() is None:
        raise SharedBGcContractLifecycleError(
            "assessed_at must be timezone-aware"
        )

    product = authority_evidence.get("product")
    conclusions = authority_evidence.get("frozen_conclusions")
    if not isinstance(product, dict) or not isinstance(conclusions, dict):
        raise SharedBGcContractLifecycleError(
            "authority product/conclusions missing"
        )
    required_product = {
        "canonical_product_identity": "COMEX_GOLD_FUTURES_100_TROY_OZ",
        "product_symbol": "GC",
        "venue": "COMEX",
        "contract_size_troy_oz": 100,
        "termination_rule": "THIRD_LAST_BUSINESS_DAY_OF_DELIVERY_MONTH",
    }
    for key, expected in required_product.items():
        if product.get(key) != expected:
            raise SharedBGcContractLifecycleError(
                f"authority product mismatch: {key}"
            )
    required_conclusions = {
        "gc_product_identity_verified": True,
        "gc_contract_size_verified": True,
        "gc_termination_occurs_within_delivery_month": True,
        "contract_month_before_assessment_month_is_expired": True,
        "contract_month_order_alone_proves_front_contract": False,
        "contract_month_order_alone_proves_roll_rule": False,
        "dated_contract_set_proves_continuous_series": False,
        "current_provider_front_contract_may_be_inferred": False,
    }
    for key, expected in required_conclusions.items():
        if conclusions.get(key) != expected:
            raise SharedBGcContractLifecycleError(
                f"authority conclusion mismatch: {key}"
            )

    authorities = authority_evidence.get("authorities")
    if not isinstance(authorities, list) or len(authorities) < 2:
        raise SharedBGcContractLifecycleError(
            "official authority evidence incomplete"
        )
    authority_ids: list[str] = []
    for raw in authorities:
        if not isinstance(raw, dict):
            raise SharedBGcContractLifecycleError(
                "authority row invalid"
            )
        authority_id = raw.get("authority_id")
        source_url = raw.get("source_url")
        if (
            not isinstance(authority_id, str)
            or not authority_id
            or not isinstance(source_url, str)
            or not source_url.startswith("https://www.cmegroup.com/")
        ):
            raise SharedBGcContractLifecycleError(
                "authority id/url invalid"
            )
        authority_ids.append(authority_id)
    if len(authority_ids) != len(set(authority_ids)):
        raise SharedBGcContractLifecycleError(
            "authority ids must be unique"
        )

    pack_known_at = _parse_aware(
        commodity_pack.get("known_at"),
        field="commodity pack known_at",
    )
    if assessed_at < pack_known_at:
        raise SharedBGcContractLifecycleError(
            "assessment cannot predate sealed commodity knowledge"
        )

    records = commodity_pack.get("records")
    if not isinstance(records, list):
        raise SharedBGcContractLifecycleError(
            "commodity records missing"
        )

    gc_rows: list[dict[str, object]] = []
    for raw in records:
        if not isinstance(raw, dict):
            raise SharedBGcContractLifecycleError(
                "commodity row invalid"
            )
        row = cast(dict[str, object], raw)
        if row.get("asset_world") != "METALS_FUTURES":
            continue
        if row.get("identity_kind") != "DATED_FUTURES_CONTRACT_DESCRIPTOR":
            raise SharedBGcContractLifecycleError(
                "unexpected metals-futures identity kind"
            )
        if row.get("dated_contract_identity_verified") is not True:
            raise SharedBGcContractLifecycleError(
                "dated GC contract identity not verified"
            )

        observation_identity = row.get("observation_identity")
        if not isinstance(observation_identity, str):
            raise SharedBGcContractLifecycleError(
                "GC observation identity missing"
            )
        match = _CONTRACT_RE.fullmatch(observation_identity)
        if match is None:
            raise SharedBGcContractLifecycleError(
                "GC observation identity shape invalid"
            )
        contract_year = int(match.group("year"))
        contract_month = int(match.group("month"))
        if not 1 <= contract_month <= 12:
            raise SharedBGcContractLifecycleError(
                "GC contract month invalid"
            )

        assessment_key = (assessed_at.year, assessed_at.month)
        contract_key = (contract_year, contract_month)
        if contract_key < assessment_key:
            lifecycle_status = "EXPIRED_BEFORE_ASSESSMENT_MONTH"
            expiry_proven = True
        elif contract_key == assessment_key:
            lifecycle_status = (
                "DELIVERY_MONTH_EXACT_LAST_TRADE_DATE_REQUIRED"
            )
            expiry_proven = False
        else:
            lifecycle_status = "FUTURE_CONTRACT_NOT_FRONT_PROOF"
            expiry_proven = False

        gc_rows.append(
            {
                "provider": row.get("provider"),
                "provider_symbol": row.get("provider_symbol"),
                "provider_symbol_id": row.get("provider_symbol_id"),
                "observation_identity": observation_identity,
                "contract_year": contract_year,
                "contract_month": contract_month,
                "lifecycle_status": lifecycle_status,
                "expired_before_assessment_month_verified": expiry_proven,
                "front_contract_verified": False,
                "roll_semantics_verified": False,
                "continuous_series_verified": False,
                "contract_order_used_as_front_proof": False,
                "contract_order_used_as_roll_proof": False,
                "authority_ids": tuple(sorted(authority_ids)),
                "historical_pre_freeze_mapping_authorized": False,
                "relational_claims_authorized": False,
                "execution_authority": False,
            }
        )

    gc_rows.sort(
        key=lambda row: (
            int(cast(int, row["contract_year"])),
            int(cast(int, row["contract_month"])),
            int(cast(int, row["provider_symbol_id"])),
        )
    )
    if len(gc_rows) != 5:
        raise SharedBGcContractLifecycleError(
            f"expected exact 5 dated GC contracts, got {len(gc_rows)}"
        )

    expired_count = sum(
        row["expired_before_assessment_month_verified"] is True
        for row in gc_rows
    )
    current_month_unresolved_count = sum(
        row["lifecycle_status"]
        == "DELIVERY_MONTH_EXACT_LAST_TRADE_DATE_REQUIRED"
        for row in gc_rows
    )
    future_count = sum(
        row["lifecycle_status"] == "FUTURE_CONTRACT_NOT_FRONT_PROOF"
        for row in gc_rows
    )

    all_observed_expired = expired_count == len(gc_rows)
    current_front_absent = all_observed_expired
    payload: dict[str, object] = {
        "identity": IDENTITY,
        "status": "OBSERVED_GC_CHAIN_LIFECYCLE_FROZEN",
        "assessed_at": assessed_at.isoformat(timespec="seconds"),
        "commodity_pack_known_at": pack_known_at.isoformat(
            timespec="microseconds"
        ),
        "dated_gc_contract_count": len(gc_rows),
        "expired_before_assessment_month_count": expired_count,
        "delivery_month_exact_expiry_unresolved_count": (
            current_month_unresolved_count
        ),
        "future_contract_count": future_count,
        "all_observed_gc_contracts_expired_before_assessment_month": (
            all_observed_expired
        ),
        "current_front_contract_in_observed_set_verified_count": 0,
        "current_front_contract_absent_from_observed_set": (
            current_front_absent
        ),
        "observed_set_can_prove_current_gc_chain": not current_front_absent,
        "front_contract_identity_complete": False,
        "roll_semantics_complete": False,
        "continuous_series_semantics_complete": False,
        "records": gc_rows,
        "target_or_outcome_read": False,
        "r6_r5_read": False,
        "fresh_holdout_opened": False,
        "historical_market_data_read": False,
        "broker_mutation": False,
        "sensor_admission_authorized": False,
        "relational_claims_authorized": False,
        "productive_authority": False,
        "b15_complete": False,
    }
    payload["lifecycle_fingerprint_sha256"] = _fingerprint(payload)
    return payload
