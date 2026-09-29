"""Causal world-at-entry lineage for Shared open-position observation."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import UTC, datetime

from qore.infrastructure.core_stack_v2.shared_trader_intelligence import (
    SharedTraderIntelligenceSnapshot,
    SharedTraderIntelligenceValidationError,
)


@dataclass(frozen=True, slots=True)
class SharedPositionEntryWorldRecord:
    """Immutable world-at-entry record bound to the position opening event."""

    entry_world_record_id: str
    position_id: str
    trader_id: str
    asset: str
    canonical_instrument_id: str
    opened_at: datetime
    captured_at: datetime
    snapshot_id: str
    snapshot_observed_at: datetime
    snapshot_evidence_cutoff_at: datetime
    snapshot_fingerprint: str
    world_state_at_entry: str
    market_regime_at_entry: str
    macro_regime_at_entry: str
    relationship_coherence_at_entry: str
    relationship_stability_at_entry: str
    provenance_refs: tuple[str, ...]
    post_hoc_reconstruction: bool = False
    position_management_authority: bool = False
    execution_authority: bool = False

    def __post_init__(self) -> None:
        for name in (
            "entry_world_record_id",
            "position_id",
            "trader_id",
            "asset",
            "canonical_instrument_id",
            "snapshot_id",
            "world_state_at_entry",
            "market_regime_at_entry",
            "macro_regime_at_entry",
            "relationship_coherence_at_entry",
            "relationship_stability_at_entry",
        ):
            value = str(getattr(self, name))
            if not value.strip():
                raise SharedTraderIntelligenceValidationError(
                    f"{name} must be non-empty"
                )
        for name in (
            "opened_at",
            "captured_at",
            "snapshot_observed_at",
            "snapshot_evidence_cutoff_at",
        ):
            value = getattr(self, name)
            if value.tzinfo is None or value.utcoffset() is None:
                raise SharedTraderIntelligenceValidationError(
                    f"{name} must be timezone-aware"
                )
        if self.captured_at != self.opened_at:
            raise SharedTraderIntelligenceValidationError(
                "entry world must be committed at the position opening event"
            )
        if self.snapshot_observed_at > self.opened_at:
            raise SharedTraderIntelligenceValidationError(
                "entry world cannot use a snapshot observed after position open"
            )
        if self.snapshot_evidence_cutoff_at > self.snapshot_observed_at:
            raise SharedTraderIntelligenceValidationError(
                "entry snapshot cannot contain future evidence"
            )
        if len(self.snapshot_fingerprint) != 64:
            raise SharedTraderIntelligenceValidationError(
                "snapshot_fingerprint must be sha256 hex"
            )
        try:
            int(self.snapshot_fingerprint, 16)
        except ValueError as exc:
            raise SharedTraderIntelligenceValidationError(
                "snapshot_fingerprint must be sha256 hex"
            ) from exc
        if not self.provenance_refs:
            raise SharedTraderIntelligenceValidationError(
                "entry world provenance must be non-empty"
            )
        if self.provenance_refs != tuple(sorted(set(self.provenance_refs))):
            raise SharedTraderIntelligenceValidationError(
                "entry world provenance must be unique and canonical"
            )
        if (
            self.post_hoc_reconstruction
            or self.position_management_authority
            or self.execution_authority
        ):
            raise SharedTraderIntelligenceValidationError(
                "entry world record is causal observation only"
            )

    def fingerprint(self) -> str:
        payload = asdict(self)
        for name in (
            "opened_at",
            "captured_at",
            "snapshot_observed_at",
            "snapshot_evidence_cutoff_at",
        ):
            payload[name] = getattr(self, name).astimezone(UTC).isoformat()
        raw = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(raw.encode()).hexdigest()


def capture_position_entry_world(
    *,
    entry_world_record_id: str,
    position_id: str,
    trader_id: str,
    opened_at: datetime,
    snapshot: SharedTraderIntelligenceSnapshot,
    provenance_refs: tuple[str, ...],
) -> SharedPositionEntryWorldRecord:
    """Capture exactly what Shared knew no later than the opening event."""

    return SharedPositionEntryWorldRecord(
        entry_world_record_id=entry_world_record_id,
        position_id=position_id,
        trader_id=trader_id,
        asset=snapshot.asset,
        canonical_instrument_id=snapshot.canonical_instrument_id,
        opened_at=opened_at,
        captured_at=opened_at,
        snapshot_id=snapshot.snapshot_id,
        snapshot_observed_at=snapshot.observed_at,
        snapshot_evidence_cutoff_at=snapshot.evidence_cutoff_at,
        snapshot_fingerprint=snapshot.fingerprint(),
        world_state_at_entry=snapshot.world_state,
        market_regime_at_entry=snapshot.market_regime,
        macro_regime_at_entry=snapshot.macro_regime,
        relationship_coherence_at_entry=(
            snapshot.relationship_coherence.value
        ),
        relationship_stability_at_entry=(
            snapshot.relationship_stability.value
        ),
        provenance_refs=provenance_refs,
    )


@dataclass(frozen=True, slots=True)
class SharedPositionWorldNowDelta:
    """Factual world change only; no threat threshold or management command."""

    delta_observation_id: str
    entry_world_record_id: str
    position_id: str
    trader_id: str
    compared_at: datetime
    evidence_cutoff_at: datetime
    entry_snapshot_id: str
    current_snapshot_id: str
    entry_snapshot_fingerprint: str
    current_snapshot_fingerprint: str
    elapsed_since_entry_ms: int
    world_state_changed: bool
    market_regime_changed: bool
    macro_regime_changed: bool
    relationship_coherence_changed: bool
    relationship_stability_changed: bool
    entry_world_state: str
    current_world_state: str
    entry_market_regime: str
    current_market_regime: str
    entry_macro_regime: str
    current_macro_regime: str
    entry_relationship_coherence: str
    current_relationship_coherence: str
    entry_relationship_stability: str
    current_relationship_stability: str
    provenance_refs: tuple[str, ...]
    threat_classification_authority: bool = False
    position_management_authority: bool = False
    execution_authority: bool = False

    def __post_init__(self) -> None:
        for name in (
            "delta_observation_id",
            "entry_world_record_id",
            "position_id",
            "trader_id",
            "entry_snapshot_id",
            "current_snapshot_id",
            "entry_world_state",
            "current_world_state",
            "entry_market_regime",
            "current_market_regime",
            "entry_macro_regime",
            "current_macro_regime",
            "entry_relationship_coherence",
            "current_relationship_coherence",
            "entry_relationship_stability",
            "current_relationship_stability",
        ):
            if not str(getattr(self, name)).strip():
                raise SharedTraderIntelligenceValidationError(
                    f"{name} must be non-empty"
                )
        for name in ("compared_at", "evidence_cutoff_at"):
            value = getattr(self, name)
            if value.tzinfo is None or value.utcoffset() is None:
                raise SharedTraderIntelligenceValidationError(
                    f"{name} must be timezone-aware"
                )
        if self.evidence_cutoff_at > self.compared_at:
            raise SharedTraderIntelligenceValidationError(
                "world-now delta cannot use future evidence"
            )
        if self.elapsed_since_entry_ms < 0:
            raise SharedTraderIntelligenceValidationError(
                "elapsed_since_entry_ms cannot be negative"
            )
        for name in (
            "entry_snapshot_fingerprint",
            "current_snapshot_fingerprint",
        ):
            value = str(getattr(self, name))
            if len(value) != 64:
                raise SharedTraderIntelligenceValidationError(
                    f"{name} must be sha256 hex"
                )
            try:
                int(value, 16)
            except ValueError as exc:
                raise SharedTraderIntelligenceValidationError(
                    f"{name} must be sha256 hex"
                ) from exc
        if not self.provenance_refs:
            raise SharedTraderIntelligenceValidationError(
                "world-now delta provenance must be non-empty"
            )
        if self.provenance_refs != tuple(sorted(set(self.provenance_refs))):
            raise SharedTraderIntelligenceValidationError(
                "world-now delta provenance must be unique and canonical"
            )
        if (
            self.threat_classification_authority
            or self.position_management_authority
            or self.execution_authority
        ):
            raise SharedTraderIntelligenceValidationError(
                "world-now delta is factual comparison only"
            )

    def fingerprint(self) -> str:
        payload = asdict(self)
        payload["compared_at"] = self.compared_at.astimezone(UTC).isoformat()
        payload["evidence_cutoff_at"] = (
            self.evidence_cutoff_at.astimezone(UTC).isoformat()
        )
        raw = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(raw.encode()).hexdigest()


def compare_position_world_now(
    *,
    delta_observation_id: str,
    entry: SharedPositionEntryWorldRecord,
    current_snapshot: SharedTraderIntelligenceSnapshot,
    compared_at: datetime,
    provenance_refs: tuple[str, ...],
) -> SharedPositionWorldNowDelta:
    """Compare immutable entry truth to current Shared truth without hindsight."""

    if current_snapshot.asset != entry.asset:
        raise SharedTraderIntelligenceValidationError(
            "current snapshot asset differs from entry-world asset"
        )
    if (
        current_snapshot.canonical_instrument_id
        != entry.canonical_instrument_id
    ):
        raise SharedTraderIntelligenceValidationError(
            "current canonical instrument differs from entry-world instrument"
        )
    if current_snapshot.observed_at < entry.opened_at:
        raise SharedTraderIntelligenceValidationError(
            "current snapshot cannot predate the position opening event"
        )
    if compared_at.tzinfo is None or compared_at.utcoffset() is None:
        raise SharedTraderIntelligenceValidationError(
            "compared_at must be timezone-aware"
        )
    if current_snapshot.observed_at > compared_at:
        raise SharedTraderIntelligenceValidationError(
            "comparison cannot consume a future current snapshot"
        )
    elapsed_ms = int(
        (current_snapshot.observed_at - entry.opened_at).total_seconds()
        * 1000
    )
    return SharedPositionWorldNowDelta(
        delta_observation_id=delta_observation_id,
        entry_world_record_id=entry.entry_world_record_id,
        position_id=entry.position_id,
        trader_id=entry.trader_id,
        compared_at=compared_at,
        evidence_cutoff_at=current_snapshot.evidence_cutoff_at,
        entry_snapshot_id=entry.snapshot_id,
        current_snapshot_id=current_snapshot.snapshot_id,
        entry_snapshot_fingerprint=entry.snapshot_fingerprint,
        current_snapshot_fingerprint=current_snapshot.fingerprint(),
        elapsed_since_entry_ms=elapsed_ms,
        world_state_changed=(
            entry.world_state_at_entry != current_snapshot.world_state
        ),
        market_regime_changed=(
            entry.market_regime_at_entry != current_snapshot.market_regime
        ),
        macro_regime_changed=(
            entry.macro_regime_at_entry != current_snapshot.macro_regime
        ),
        relationship_coherence_changed=(
            entry.relationship_coherence_at_entry
            != current_snapshot.relationship_coherence.value
        ),
        relationship_stability_changed=(
            entry.relationship_stability_at_entry
            != current_snapshot.relationship_stability.value
        ),
        entry_world_state=entry.world_state_at_entry,
        current_world_state=current_snapshot.world_state,
        entry_market_regime=entry.market_regime_at_entry,
        current_market_regime=current_snapshot.market_regime,
        entry_macro_regime=entry.macro_regime_at_entry,
        current_macro_regime=current_snapshot.macro_regime,
        entry_relationship_coherence=(
            entry.relationship_coherence_at_entry
        ),
        current_relationship_coherence=(
            current_snapshot.relationship_coherence.value
        ),
        entry_relationship_stability=(
            entry.relationship_stability_at_entry
        ),
        current_relationship_stability=(
            current_snapshot.relationship_stability.value
        ),
        provenance_refs=provenance_refs,
    )
