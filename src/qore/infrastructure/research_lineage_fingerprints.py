from __future__ import annotations

from dataclasses import dataclass
from re import fullmatch

from qore.infrastructure.research_lineage_errors import ResearchLineageFingerprintError


def _validate_sha256(value: str, *, field_name: str) -> None:
    if not isinstance(value, str) or fullmatch(r"[0-9a-f]{64}", value) is None:
        raise ResearchLineageFingerprintError(
            f"{field_name} must be 64 lowercase hex characters"
        )


@dataclass(frozen=True, slots=True)
class ResearchExecutionSessionFingerprint:
    value: str

    def __post_init__(self) -> None:
        _validate_sha256(self.value, field_name="execution session fingerprint")

    def logical_values(self) -> dict[str, str]:
        return {"algorithm": "sha256", "value": self.value}


@dataclass(frozen=True, slots=True)
class ResearchStrategyStateFingerprint:
    value: str

    def __post_init__(self) -> None:
        _validate_sha256(self.value, field_name="strategy state fingerprint")

    def logical_values(self) -> dict[str, str]:
        return {"algorithm": "sha256", "value": self.value}


@dataclass(frozen=True, slots=True)
class ResearchStateTransitionFingerprint:
    value: str

    def __post_init__(self) -> None:
        _validate_sha256(self.value, field_name="state transition fingerprint")

    def logical_values(self) -> dict[str, str]:
        return {"algorithm": "sha256", "value": self.value}


@dataclass(frozen=True, slots=True)
class ResearchExecutionTraceFingerprint:
    value: str

    def __post_init__(self) -> None:
        _validate_sha256(self.value, field_name="execution trace fingerprint")

    def logical_values(self) -> dict[str, str]:
        return {"algorithm": "sha256", "value": self.value}


@dataclass(frozen=True, slots=True)
class ResearchAnalysisInputEvidenceFingerprint:
    value: str

    def __post_init__(self) -> None:
        _validate_sha256(self.value, field_name="analysis input evidence fingerprint")

    def logical_values(self) -> dict[str, str]:
        return {"algorithm": "sha256", "value": self.value}


@dataclass(frozen=True, slots=True)
class ResearchTraderCommandFingerprint:
    value: str

    def __post_init__(self) -> None:
        _validate_sha256(self.value, field_name="research trader command fingerprint")

    def logical_values(self) -> dict[str, str]:
        return {"algorithm": "sha256", "value": self.value}


@dataclass(frozen=True, slots=True)
class ResearchAnalysisLineageFingerprint:
    value: str

    def __post_init__(self) -> None:
        _validate_sha256(self.value, field_name="analysis lineage fingerprint")

    def logical_values(self) -> dict[str, str]:
        return {"algorithm": "sha256", "value": self.value}
