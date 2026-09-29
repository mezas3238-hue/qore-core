"""Configuration-driven global sensor registry for Shared perception."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from enum import StrEnum
from typing import Final, Sequence


class GlobalSensorGovernanceStage(StrEnum):
    DISCOVER_PROVIDER_SYMBOL = "DISCOVER_PROVIDER_SYMBOL"
    VERIFY_IDENTITY = "VERIFY_IDENTITY"
    VERIFY_HISTORICAL_AVAILABILITY = "VERIFY_HISTORICAL_AVAILABILITY"
    VERIFY_TIMESTAMP_INTEGRITY = "VERIFY_TIMESTAMP_INTEGRITY"
    VERIFY_MARKET_DATA_QUALITY = "VERIFY_MARKET_DATA_QUALITY"
    CLASSIFY_SENSOR_FAMILY = "CLASSIFY_SENSOR_FAMILY"
    MEASURE_REDUNDANCY = "MEASURE_REDUNDANCY"
    MEASURE_INFORMATION_GAIN = "MEASURE_INFORMATION_GAIN"
    CAUSAL_VALIDATION = "CAUSAL_VALIDATION"
    TEMPORAL_REPLICATION = "TEMPORAL_REPLICATION"
    ADMISSION_DECISION = "ADMISSION_DECISION"


GLOBAL_SENSOR_GOVERNANCE_PIPELINE: Final = tuple(GlobalSensorGovernanceStage)


class GlobalSensorDisposition(StrEnum):
    DISCOVERED = "DISCOVERED"
    QUALIFYING = "QUALIFYING"
    OBSERVE_ONLY = "OBSERVE_ONLY"
    ADMITTED = "ADMITTED"
    REJECTED = "REJECTED"


@dataclass(frozen=True, slots=True)
class ProviderCatalogSensor:
    provider: str
    provider_symbol: str
    provider_symbol_id: int
    enabled: bool = True

    def __post_init__(self) -> None:
        if not self.provider.strip():
            raise ValueError("provider must be non-empty")
        if not self.provider_symbol.strip():
            raise ValueError("provider_symbol must be non-empty")
        if type(self.provider_symbol_id) is not int or self.provider_symbol_id <= 0:
            raise ValueError("provider_symbol_id must be a positive int")
        if type(self.enabled) is not bool:
            raise ValueError("enabled must be bool")


@dataclass(frozen=True, slots=True)
class GlobalSensorRecord:
    instrument_key: str
    provider: str
    provider_symbol: str
    provider_symbol_id: int
    family: str | None
    observed_at: datetime
    evidence_cutoff_at: datetime
    completed_stages: tuple[GlobalSensorGovernanceStage, ...]
    disposition: GlobalSensorDisposition
    uncertainty_bps: int
    provenance_refs: tuple[str, ...]
    reason_codes: tuple[str, ...]
    execution_authority: bool = False
    risk_authority: bool = False
    sizing_authority: bool = False
    strategy_mutation_authority: bool = False

    def __post_init__(self) -> None:
        for value in (self.observed_at, self.evidence_cutoff_at):
            if value.tzinfo is None or value.utcoffset() is None:
                raise ValueError("sensor timestamps must be timezone-aware")
        if self.evidence_cutoff_at > self.observed_at:
            raise ValueError("future sensor evidence is forbidden")
        if not self.instrument_key.strip():
            raise ValueError("instrument_key must be non-empty")
        if not self.provider.strip() or not self.provider_symbol.strip():
            raise ValueError("provider identity must be non-empty")
        if type(self.provider_symbol_id) is not int or self.provider_symbol_id <= 0:
            raise ValueError("provider_symbol_id must be a positive int")
        if not 0 <= self.uncertainty_bps <= 10_000:
            raise ValueError("uncertainty_bps must be within 0..10000")
        expected_prefix = GLOBAL_SENSOR_GOVERNANCE_PIPELINE[: len(self.completed_stages)]
        if self.completed_stages != expected_prefix:
            raise ValueError("sensor governance stages must form an exact prefix")
        if not self.completed_stages:
            raise ValueError("sensor requires at least discovery evidence")
        if self.provenance_refs != tuple(sorted(set(self.provenance_refs))):
            raise ValueError("sensor provenance_refs must be unique and canonical")
        if self.reason_codes != tuple(sorted(set(self.reason_codes))):
            raise ValueError("sensor reason_codes must be unique and canonical")
        if self.disposition is GlobalSensorDisposition.ADMITTED:
            if self.completed_stages != GLOBAL_SENSOR_GOVERNANCE_PIPELINE:
                raise ValueError("admitted sensor must complete the full pipeline")
        if (
            self.execution_authority
            or self.risk_authority
            or self.sizing_authority
            or self.strategy_mutation_authority
        ):
            raise ValueError("sensor observation cannot carry sovereign authority")


@dataclass(frozen=True, slots=True)
class GlobalPerceptionSensorRegistry:
    as_of: datetime
    provider_catalog_sha256: str
    sensors: tuple[GlobalSensorRecord, ...]
    current_trader_universe_defines_ceiling: bool = False
    execution_authority: bool = False
    risk_authority: bool = False
    sizing_authority: bool = False

    def __post_init__(self) -> None:
        if self.as_of.tzinfo is None or self.as_of.utcoffset() is None:
            raise ValueError("registry as_of must be timezone-aware")
        if len(self.provider_catalog_sha256) != 64:
            raise ValueError("provider_catalog_sha256 must be sha256 hex")
        try:
            int(self.provider_catalog_sha256, 16)
        except ValueError as error:
            raise ValueError("provider_catalog_sha256 must be sha256 hex") from error
        keys = tuple(item.instrument_key for item in self.sensors)
        if keys != tuple(sorted(keys)) or len(keys) != len(set(keys)):
            raise ValueError("sensor registry keys must be unique and canonical")
        provider_ids = tuple(
            (item.provider, item.provider_symbol_id) for item in self.sensors
        )
        if len(provider_ids) != len(set(provider_ids)):
            raise ValueError("provider symbol ids must be unique per provider")
        if any(item.observed_at > self.as_of for item in self.sensors):
            raise ValueError("future sensor record is forbidden")
        if (
            self.current_trader_universe_defines_ceiling
            or self.execution_authority
            or self.risk_authority
            or self.sizing_authority
        ):
            raise ValueError("global sensor registry is cognition-only")

    @property
    def sensor_count(self) -> int:
        return len(self.sensors)

    def fingerprint(self) -> str:
        payload = {
            "as_of": self.as_of.astimezone(UTC).isoformat(),
            "provider_catalog_sha256": self.provider_catalog_sha256,
            "sensors": [
                {
                    **asdict(item),
                    "observed_at": item.observed_at.astimezone(UTC).isoformat(),
                    "evidence_cutoff_at": item.evidence_cutoff_at.astimezone(
                        UTC
                    ).isoformat(),
                    "completed_stages": [
                        stage.value for stage in item.completed_stages
                    ],
                    "disposition": item.disposition.value,
                }
                for item in self.sensors
            ],
        }
        raw = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(raw.encode()).hexdigest()


def build_discovered_provider_registry(
    *,
    provider: str,
    catalog_sha256: str,
    observed_at: datetime,
    catalog: Sequence[ProviderCatalogSensor],
) -> GlobalPerceptionSensorRegistry:
    """Project any enabled provider catalogue into discovery-only records."""

    if observed_at.tzinfo is None or observed_at.utcoffset() is None:
        raise ValueError("observed_at must be timezone-aware")
    if not provider.strip():
        raise ValueError("provider must be non-empty")

    enabled = [item for item in catalog if item.enabled]
    sensors = tuple(
        sorted(
            (
                GlobalSensorRecord(
                    instrument_key=(
                        f"{item.provider}:{item.provider_symbol}:"
                        f"{item.provider_symbol_id}"
                    ),
                    provider=item.provider,
                    provider_symbol=item.provider_symbol,
                    provider_symbol_id=item.provider_symbol_id,
                    family=None,
                    observed_at=observed_at,
                    evidence_cutoff_at=observed_at,
                    completed_stages=(
                        GlobalSensorGovernanceStage.DISCOVER_PROVIDER_SYMBOL,
                    ),
                    disposition=GlobalSensorDisposition.DISCOVERED,
                    uncertainty_bps=10_000,
                    provenance_refs=(f"provider-catalog:{catalog_sha256}",),
                    reason_codes=("PROVIDER_DISCOVERED_NOT_ADMITTED",),
                )
                for item in enabled
                if item.provider == provider
            ),
            key=lambda item: item.instrument_key,
        )
    )
    return GlobalPerceptionSensorRegistry(
        as_of=observed_at,
        provider_catalog_sha256=catalog_sha256,
        sensors=sensors,
    )
