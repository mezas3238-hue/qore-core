"""Build AGRI-1 provider capability audit from governed provider catalog evidence."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime
from pathlib import Path
from typing import Any, cast

from qore.infrastructure.core_stack_v2.agricultural_sensor_governance import (
    AgriculturalDiscoveryTarget,
    AgriculturalProviderDiscoveryState,
    AgriculturalWorldFamily,
    GlobalAgriculturalSensorMatrix,
    ProviderAgriculturalCandidate,
    build_agricultural_provider_capability_matrix,
)

IDENTITY = "QORE_SHARED_AGRICULTURAL_PROVIDER_CAPABILITY_AUDIT_001"
MATRIX_IDENTITY = "QORE_SHARED_GLOBAL_AGRICULTURAL_SENSOR_MATRIX_001"
EXPECTED_UNIVERSE_IDENTITY = (
    "QORE_SHARED_AGRICULTURAL_CONCEPTUAL_UNIVERSE_001"
)
EXPECTED_PROVIDER_CATALOG_IDENTITY = (
    "QORE_SHARED_GEN2_CTRADER_PROVIDER_SCHEDULE_CATALOG_001"
)


class AgriculturalProviderCapabilityAuditError(RuntimeError):
    """AGRI-1 provider capability audit failed closed."""


def _load(path: Path) -> dict[str, Any]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise AgriculturalProviderCapabilityAuditError(
            f"{path} must contain a JSON object"
        )
    return cast(dict[str, Any], raw)


def _fingerprint(payload: object) -> str:
    raw = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    )
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _aware(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise AgriculturalProviderCapabilityAuditError(
            "provider catalog captured_at must be timezone-aware"
        )
    return parsed


def _targets(
    payload: dict[str, Any],
) -> tuple[AgriculturalDiscoveryTarget, ...]:
    if payload.get("identity") != EXPECTED_UNIVERSE_IDENTITY:
        raise AgriculturalProviderCapabilityAuditError(
            "unexpected agricultural conceptual universe identity"
        )
    if payload.get("provider_symbols_authorized") is not False:
        raise AgriculturalProviderCapabilityAuditError(
            "conceptual universe cannot authorize provider symbols"
        )
    if payload.get("automatic_canonical_identity_authorized") is not False:
        raise AgriculturalProviderCapabilityAuditError(
            "conceptual universe cannot authorize canonical identity"
        )
    raw_targets = payload.get("targets")
    if not isinstance(raw_targets, list) or not raw_targets:
        raise AgriculturalProviderCapabilityAuditError(
            "agricultural conceptual targets missing"
        )

    targets: list[AgriculturalDiscoveryTarget] = []
    seen: set[str] = set()
    for raw in raw_targets:
        if not isinstance(raw, dict):
            raise AgriculturalProviderCapabilityAuditError(
                "agricultural conceptual target must be object"
            )
        item = cast(dict[str, object], raw)
        key = item.get("conceptual_market_key")
        display_name = item.get("display_name")
        family_raw = item.get("world_family")
        memberships_raw = item.get("complex_memberships")
        terms_raw = item.get("discovery_terms")
        if (
            not isinstance(key, str)
            or not key
            or not isinstance(display_name, str)
            or not display_name
            or not isinstance(family_raw, str)
            or not isinstance(memberships_raw, list)
            or not isinstance(terms_raw, list)
        ):
            raise AgriculturalProviderCapabilityAuditError(
                "agricultural target fields invalid"
            )
        if key in seen:
            raise AgriculturalProviderCapabilityAuditError(
                "duplicate agricultural conceptual market"
            )
        seen.add(key)
        try:
            family = AgriculturalWorldFamily(family_raw)
        except ValueError as exc:
            raise AgriculturalProviderCapabilityAuditError(
                "unknown agricultural world family"
            ) from exc
        memberships = tuple(
            sorted(
                {
                    cast(str, value)
                    for value in memberships_raw
                    if isinstance(value, str) and value
                }
            )
        )
        terms = tuple(
            sorted(
                {
                    cast(str, value).casefold()
                    for value in terms_raw
                    if isinstance(value, str) and value.strip()
                }
            )
        )
        if len(memberships) != len(memberships_raw):
            raise AgriculturalProviderCapabilityAuditError(
                "agricultural memberships invalid or duplicated"
            )
        if len(terms) != len(terms_raw):
            raise AgriculturalProviderCapabilityAuditError(
                "agricultural discovery terms invalid or duplicated"
            )
        targets.append(
            AgriculturalDiscoveryTarget(
                conceptual_market_key=key,
                display_name=display_name,
                world_family=family,
                complex_memberships=memberships,
                discovery_terms=terms,
            )
        )
    return tuple(
        sorted(targets, key=lambda item: item.conceptual_market_key)
    )


def _provider_candidates(
    payload: dict[str, Any],
) -> tuple[ProviderAgriculturalCandidate, ...]:
    if payload.get("identity") != EXPECTED_PROVIDER_CATALOG_IDENTITY:
        raise AgriculturalProviderCapabilityAuditError(
            "unexpected provider schedule catalog identity"
        )
    source_fingerprint = payload.get(
        "provider_schedule_catalog_fingerprint_sha256"
    )
    if not isinstance(source_fingerprint, str) or len(source_fingerprint) != 64:
        raise AgriculturalProviderCapabilityAuditError(
            "provider schedule fingerprint missing"
        )
    rows = payload.get("symbols")
    if not isinstance(rows, list):
        raise AgriculturalProviderCapabilityAuditError(
            "provider symbol rows missing"
        )

    candidates: list[ProviderAgriculturalCandidate] = []
    for raw in rows:
        if not isinstance(raw, dict):
            raise AgriculturalProviderCapabilityAuditError(
                "provider symbol row must be object"
            )
        item = cast(dict[str, object], raw)
        provider = item.get("provider")
        provider_symbol = item.get("provider_symbol")
        provider_symbol_id = item.get("provider_symbol_id")
        native_name = item.get("provider_native_symbol_name")
        description = item.get("provider_description")
        if (
            not isinstance(provider, str)
            or not provider
            or not isinstance(provider_symbol, str)
            or not provider_symbol
            or type(provider_symbol_id) is not int
        ):
            raise AgriculturalProviderCapabilityAuditError(
                "provider symbol identity invalid"
            )
        candidates.append(
            ProviderAgriculturalCandidate(
                provider=provider,
                provider_symbol_id=provider_symbol_id,
                provider_symbol=provider_symbol,
                provider_native_symbol_name=(
                    cast(str, native_name)
                    if isinstance(native_name, str) and native_name
                    else None
                ),
                provider_description=(
                    cast(str, description)
                    if isinstance(description, str) and description
                    else None
                ),
                provenance_ref=(
                    "provider-schedule:" + source_fingerprint
                ),
            )
        )
    ordered = tuple(
        sorted(
            candidates,
            key=lambda item: (
                item.provider,
                item.provider_symbol_id,
                item.provider_symbol,
            ),
        )
    )
    if len(ordered) != len(set(ordered)):
        raise AgriculturalProviderCapabilityAuditError(
            "provider catalog contains duplicate candidate identity"
        )
    return ordered


def run(
    *,
    conceptual_universe_path: Path,
    provider_schedule_path: Path,
    audit_output_path: Path,
    matrix_output_path: Path,
) -> dict[str, object]:
    universe = _load(conceptual_universe_path)
    provider_payload = _load(provider_schedule_path)
    targets = _targets(universe)
    candidates = _provider_candidates(provider_payload)

    universe_fingerprint = _fingerprint(universe)
    provider_fingerprint = cast(
        str,
        provider_payload[
            "provider_schedule_catalog_fingerprint_sha256"
        ],
    )
    as_of = _aware(cast(str, provider_payload["captured_at"]))
    providers = tuple(sorted({item.provider for item in candidates}))
    if not providers:
        raise AgriculturalProviderCapabilityAuditError(
            "provider catalog must contain at least one provider"
        )

    rows = []
    for provider in providers:
        matrix = build_agricultural_provider_capability_matrix(
            provider=provider,
            as_of=as_of,
            source_catalog_fingerprint=provider_fingerprint,
            conceptual_universe_identity=cast(str, universe["identity"]),
            conceptual_universe_fingerprint=universe_fingerprint,
            targets=targets,
            provider_catalog=candidates,
        )
        rows.extend(matrix.rows)

    matrix = GlobalAgriculturalSensorMatrix(
        as_of=as_of,
        source_catalog_fingerprint=provider_fingerprint,
        rows=tuple(
            sorted(
                rows,
                key=lambda item: (
                    item.provider,
                    item.target.conceptual_market_key,
                ),
            )
        ),
        conceptual_universe_identity=cast(str, universe["identity"]),
        conceptual_universe_fingerprint=universe_fingerprint,
    )

    state_counts: dict[str, int] = {}
    family_counts: dict[str, int] = {}
    candidate_count = 0
    for row in matrix.rows:
        state_counts[row.discovery_state.value] = (
            state_counts.get(row.discovery_state.value, 0) + 1
        )
        family_counts[row.target.world_family.value] = (
            family_counts.get(row.target.world_family.value, 0) + 1
        )
        candidate_count += len(row.candidates)

    matrix_payload = {
        "identity": MATRIX_IDENTITY,
        "status": "AGRI1_DISCOVERY_ONLY",
        "as_of": matrix.as_of.isoformat(timespec="microseconds"),
        "source_catalog_fingerprint_sha256": provider_fingerprint,
        "conceptual_universe_identity": matrix.conceptual_universe_identity,
        "conceptual_universe_fingerprint_sha256": (
            matrix.conceptual_universe_fingerprint
        ),
        "matrix_fingerprint_sha256": matrix.fingerprint(),
        "provider_count": len(providers),
        "providers": list(providers),
        "row_count": len(matrix.rows),
        "target_count": len(targets),
        "discovery_state_counts": dict(sorted(state_counts.items())),
        "world_family_row_counts": dict(sorted(family_counts.items())),
        "provider_symbol_is_canonical_identity": False,
        "automatic_sensor_admission": False,
        "relational_claims_authorized": False,
        "protected_holdout_opened": False,
        "rows": [
            {
                "provider": row.provider,
                "conceptual_market_key": row.target.conceptual_market_key,
                "display_name": row.target.display_name,
                "world_family": row.target.world_family.value,
                "complex_memberships": list(
                    row.target.complex_memberships
                ),
                "discovery_state": row.discovery_state.value,
                "provider_candidates": [
                    {
                        "provider_symbol": item.provider_symbol,
                        "provider_symbol_id": item.provider_symbol_id,
                        "provider_native_symbol_name": (
                            item.provider_native_symbol_name
                        ),
                        "provider_description": (
                            item.provider_description
                        ),
                        "provenance_ref": item.provenance_ref,
                    }
                    for item in row.candidates
                ],
                "contract_type": row.contract_type,
                "historical_availability": (
                    row.historical_availability.value
                ),
                "history_depth_days": row.history_depth_days,
                "realtime_availability": (
                    row.realtime_availability.value
                ),
                "bid_ask_availability": (
                    row.bid_ask_availability.value
                ),
                "tick_availability": row.tick_availability.value,
                "ohlc_availability": row.ohlc_availability.value,
                "contract_metadata_availability": (
                    row.contract_metadata_availability.value
                ),
                "identity_verified": row.identity_verified,
                "contract_mapped": row.contract_mapped,
                "calendar_mapped": row.calendar_mapped,
                "data_quality_verified": row.data_quality_verified,
                "roll_policy_verified": row.roll_policy_verified,
                "relational_ready": row.relational_ready,
                "scientific_maturity": row.scientific_maturity.value,
                "final_global_admission_authority": False,
                "row_fingerprint_sha256": row.fingerprint(),
            }
            for row in matrix.rows
        ],
    }
    matrix_output_path.parent.mkdir(parents=True, exist_ok=True)
    matrix_output_path.write_text(
        json.dumps(matrix_payload, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )

    audit = {
        "identity": IDENTITY,
        "status": "AGRI1_PROVIDER_CAPABILITY_AUDIT",
        "as_of": matrix.as_of.isoformat(timespec="microseconds"),
        "source_provider_catalog_identity": provider_payload["identity"],
        "source_provider_catalog_fingerprint_sha256": provider_fingerprint,
        "source_provider_sensor_count": len(candidates),
        "conceptual_universe_identity": universe["identity"],
        "conceptual_universe_fingerprint_sha256": universe_fingerprint,
        "conceptual_market_count": len(targets),
        "provider_count": len(providers),
        "providers": list(providers),
        "discovery_state_counts": dict(sorted(state_counts.items())),
        "provider_candidate_count": candidate_count,
        "agricultural_candidate_identity_verified_count": 0,
        "agricultural_contract_mapped_count": 0,
        "agricultural_calendar_mapped_count": 0,
        "agricultural_relational_ready_count": 0,
        "provider_symbol_is_canonical_identity": False,
        "provider_availability_is_scientific_admission": False,
        "automatic_sensor_admission": False,
        "relational_claims_authorized": False,
        "protected_holdout_opened": False,
        "matrix_fingerprint_sha256": matrix.fingerprint(),
        "result": (
            "NO_AGRICULTURAL_SOFTS_OR_LIVESTOCK_CANDIDATES_DISCOVERED"
            if candidate_count == 0
            else "PROVIDER_CANDIDATES_REQUIRE_IDENTITY_REVIEW"
        ),
    }
    audit_output_path.parent.mkdir(parents=True, exist_ok=True)
    audit_output_path.write_text(
        json.dumps(audit, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    return audit


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--conceptual-universe",
        type=Path,
        required=True,
    )
    parser.add_argument(
        "--provider-schedule",
        type=Path,
        required=True,
    )
    parser.add_argument("--audit-output", type=Path, required=True)
    parser.add_argument("--matrix-output", type=Path, required=True)
    args = parser.parse_args()

    report = run(
        conceptual_universe_path=args.conceptual_universe,
        provider_schedule_path=args.provider_schedule,
        audit_output_path=args.audit_output,
        matrix_output_path=args.matrix_output,
    )
    print(json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    main()
