"""Versioned compatibility manifest for shared Core integration."""
from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from enum import StrEnum

from qore.infrastructure.core_stack_v2.contracts import CORE_STACK_VERSION


class CompatibilityStatus(StrEnum):
    COMPATIBLE = "COMPATIBLE"
    ADAPTER_REQUIRED = "ADAPTER_REQUIRED"
    COGNITIVE_UPGRADE_REQUIRED = "COGNITIVE_UPGRADE_REQUIRED"
    NOT_COMPATIBLE = "NOT_COMPATIBLE"
    EXCLUDED = "EXCLUDED"


@dataclass(frozen=True, slots=True)
class CompatibilityEntry:
    trader_id: str
    status: CompatibilityStatus
    adapter_version: str | None
    integration_mode: str
    blocker: str | None
    live_mutation_allowed: bool
    methodology_mutation_allowed: bool


_ENTRIES = (
    CompatibilityEntry(
        trader_id="VT31_NAS100",
        status=CompatibilityStatus.COMPATIBLE,
        adapter_version="1.0.0-research",
        integration_mode="SHADOW_AB_FIRST",
        blocker="VT31_AB_AND_LATENCY_EVIDENCE_REQUIRED_BEFORE_ANY_PRODUCTION_MIGRATION",
        live_mutation_allowed=False,
        methodology_mutation_allowed=False,
    ),
    CompatibilityEntry(
        trader_id="CAPITALIZER",
        status=CompatibilityStatus.ADAPTER_REQUIRED,
        adapter_version=None,
        integration_mode="DEFERRED",
        blocker="TARGET_PHASE_MUST_CLOSE_AND_CAPITALIZER_FINAL_MUST_FREEZE",
        live_mutation_allowed=False,
        methodology_mutation_allowed=False,
    ),
    CompatibilityEntry(
        trader_id="VT08_CRT_PURE",
        status=CompatibilityStatus.ADAPTER_REQUIRED,
        adapter_version=None,
        integration_mode="RESEARCH_ONLY_AFTER_VT31",
        blocker="VT31_SHARED_CORE_AB_MUST_CLOSE_FIRST",
        live_mutation_allowed=False,
        methodology_mutation_allowed=False,
    ),
    CompatibilityEntry(
        trader_id="VT08_FOREX",
        status=CompatibilityStatus.EXCLUDED,
        adapter_version=None,
        integration_mode="CURRENT_ARCHITECTURE_ONLY",
        blocker="OWNER_ABSOLUTE_EXCLUSION_FROM_CORE_STACK_V2",
        live_mutation_allowed=False,
        methodology_mutation_allowed=False,
    ),
)


def compatibility_manifest() -> dict[str, object]:
    entries = [asdict(item) for item in _ENTRIES]
    return {
        "schema": "qore.core_stack_v2.compatibility_manifest.v1",
        "core_stack_version": CORE_STACK_VERSION,
        "inventory_scope": (
            "KNOWN_OWNER_SCOPED_TRADERS; repository/runtime discovery remains required "
            "before expanding integration"
        ),
        "entries": entries,
        "governance": {
            "vt08_forex_excluded": True,
            "live_deployment_authorized": False,
            "merge_authorized": False,
            "shadow_first": True,
        },
    }


def compatibility_manifest_fingerprint() -> str:
    raw = json.dumps(
        compatibility_manifest(),
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    )
    return hashlib.sha256(raw.encode()).hexdigest()
