"""A1 consumer contract for the Phase22 historical Compound lineage dependency.

Phase22 historical replay intentionally has no historical broker order/deal/
position identifiers. The legacy Compound engine requires positive broker
position/deal ids in its realized-profit identity. A1 must not fabricate those
ids or modify the A2-owned Compound engine.

This module defines the exact read-only receipt A1 requires from A2/Integrator
before GEN-C2..GEN-C7 can consume Compound lineage on the historical holdout.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict, dataclass

from qore.infrastructure.cibo_a1_phase22_scientific_consumption import (
    A1Phase22ScientificConsumptionManifest,
)
from qore.infrastructure.cibo_compound_capital import CiboCompoundCapitalError

CONTRACT_ID = "CIBO_A1_PHASE22_HISTORICAL_COMPOUND_LINEAGE_DEPENDENCY_V1"
_SHA1_RE = re.compile(r"^[0-9a-f]{40}$")
_SHA256_RE = re.compile(r"^sha256:[0-9a-f]{64}$")


@dataclass(frozen=True, slots=True)
class A1HistoricalCompoundLineageReceipt:
    contract_id: str
    source_workstream: str
    source_head: str
    artifact_sha256: str
    source_population_sha256: str
    a1_manifest_sha256: str
    adapter_identity: str
    historical_replay_supported: bool
    historical_broker_ids_required: bool
    historical_broker_ids_emitted: bool
    current_demo_ids_relabelled_as_historical: bool
    fabricated_execution_ids_used: bool
    realized_profit_only: bool
    floating_pnl_used_as_capital: bool
    capital_conservation_proven: bool
    double_spend_detected: bool
    decision_before_outcome_preserved: bool
    deterministic_replay: bool
    productive_authority: bool = False
    live_authorized: bool = False
    real_capital_authorized: bool = False
    a1_closes_source_workstream: bool = False

    def __post_init__(self) -> None:
        if self.contract_id != CONTRACT_ID:
            raise CiboCompoundCapitalError(
                "A1 historical Compound dependency contract identity drift"
            )
        if self.source_workstream != "COMPOUND_ENGINE":
            raise CiboCompoundCapitalError(
                "A1 historical Compound receipt must come from COMPOUND_ENGINE"
            )
        if _SHA1_RE.fullmatch(self.source_head) is None:
            raise CiboCompoundCapitalError(
                "A1 historical Compound source head invalid"
            )
        for name in (
            "artifact_sha256",
            "source_population_sha256",
            "a1_manifest_sha256",
        ):
            _sha(getattr(self, name), name)
        if not self.adapter_identity:
            raise CiboCompoundCapitalError(
                "A1 historical Compound adapter identity required"
            )

        required_true = (
            self.historical_replay_supported,
            self.realized_profit_only,
            self.capital_conservation_proven,
            self.decision_before_outcome_preserved,
            self.deterministic_replay,
        )
        if not all(required_true):
            raise CiboCompoundCapitalError(
                "A1 historical Compound receipt is not scientifically ready"
            )

        prohibited = (
            self.historical_broker_ids_required,
            self.historical_broker_ids_emitted,
            self.current_demo_ids_relabelled_as_historical,
            self.fabricated_execution_ids_used,
            self.floating_pnl_used_as_capital,
            self.double_spend_detected,
            self.productive_authority,
            self.live_authorized,
            self.real_capital_authorized,
            self.a1_closes_source_workstream,
        )
        if any(prohibited):
            raise CiboCompoundCapitalError(
                "A1 historical Compound receipt violates replay/governance law"
            )

    def fingerprint(self) -> str:
        raw = json.dumps(
            asdict(self),
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        ).encode("utf-8")
        return "sha256:" + hashlib.sha256(raw).hexdigest()


@dataclass(frozen=True, slots=True)
class A1HistoricalCompoundDependencyAdmission:
    contract_id: str
    manifest_sha256: str
    receipt_sha256: str
    source_workstream: str
    source_head: str
    ready_for_a1_genc_consumption: bool
    a2_workstream_modified: bool = False
    productive_authority: bool = False
    certification_ready: bool = False

    def __post_init__(self) -> None:
        if self.contract_id != CONTRACT_ID:
            raise CiboCompoundCapitalError(
                "A1 historical Compound admission identity drift"
            )
        for name in ("manifest_sha256", "receipt_sha256"):
            _sha(getattr(self, name), name)
        if self.source_workstream != "COMPOUND_ENGINE":
            raise CiboCompoundCapitalError(
                "A1 historical Compound admission source drift"
            )
        if _SHA1_RE.fullmatch(self.source_head) is None:
            raise CiboCompoundCapitalError(
                "A1 historical Compound admission source head invalid"
            )
        if not self.ready_for_a1_genc_consumption:
            raise CiboCompoundCapitalError(
                "A1 historical Compound admission must be ready"
            )
        if (
            self.a2_workstream_modified
            or self.productive_authority
            or self.certification_ready
        ):
            raise CiboCompoundCapitalError(
                "A1 historical Compound admission governance drift"
            )


def admit_historical_compound_lineage_for_a1(
    *,
    manifest: A1Phase22ScientificConsumptionManifest,
    receipt: A1HistoricalCompoundLineageReceipt,
) -> A1HistoricalCompoundDependencyAdmission:
    """Admit only an exact-population, non-fabricated A2 Compound adapter."""

    if not isinstance(manifest, A1Phase22ScientificConsumptionManifest):
        raise CiboCompoundCapitalError(
            "A1 historical Compound dependency requires canonical manifest"
        )
    if not isinstance(receipt, A1HistoricalCompoundLineageReceipt):
        raise CiboCompoundCapitalError(
            "A1 historical Compound dependency requires canonical receipt"
        )
    manifest_sha = manifest.fingerprint()
    if receipt.a1_manifest_sha256 != manifest_sha:
        raise CiboCompoundCapitalError(
            "A1 historical Compound receipt/manifest digest drift"
        )
    if receipt.source_population_sha256 != manifest.source_population_sha256:
        raise CiboCompoundCapitalError(
            "A1 historical Compound source population drift"
        )

    return A1HistoricalCompoundDependencyAdmission(
        contract_id=CONTRACT_ID,
        manifest_sha256=manifest_sha,
        receipt_sha256=receipt.fingerprint(),
        source_workstream=receipt.source_workstream,
        source_head=receipt.source_head,
        ready_for_a1_genc_consumption=True,
    )


def _sha(value: str, name: str) -> None:
    if _SHA256_RE.fullmatch(value) is None:
        raise CiboCompoundCapitalError(
            f"A1 historical Compound {name} must be canonical SHA-256"
        )
