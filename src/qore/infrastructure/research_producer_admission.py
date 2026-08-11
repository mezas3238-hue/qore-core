from __future__ import annotations

import dataclasses
import hashlib
import json
from typing import TYPE_CHECKING

from qore.infrastructure.dataset_integrity_qualification import (
    IntegrityQualifiedResearchRun,
    IntegrityQualifiedResearchRunFingerprint,
)
from qore.infrastructure.research_execution_session import ResearchExecutionSession
from qore.infrastructure.research_lineage_errors import (
    ResearchLineageFingerprintError,
    ResearchLineageValidationError,
)
from qore.infrastructure.research_lineage_fingerprints import (
    ResearchExecutionSessionFingerprint,
)
from qore.infrastructure.research_strategy_freeze import (
    ResearchRunStrategyBinding,
    ResearchRunStrategyBindingFingerprint,
)

if TYPE_CHECKING:
    from qore.infrastructure.historical_dataset import HistoricalOhlcReplayDataset


class ResearchProducerAdmissionValidationError(ResearchLineageValidationError):
    """Violation of the Phase 1B integrity-qualified producer admission boundary."""

    __slots__ = ()


@dataclasses.dataclass(frozen=True, slots=True)
class ResearchProducerAdmissionFingerprint:
    """Canonical SHA-256 digest of exact producer-admission dependencies."""

    value: str

    def __post_init__(self) -> None:
        if not isinstance(self.value, str):
            raise ResearchLineageFingerprintError(
                f"producer admission fingerprint value must be str, got "
                f"{type(self.value).__qualname__}"
            )
        if len(self.value) != 64 or any(
            character not in "0123456789abcdef" for character in self.value
        ):
            raise ResearchLineageFingerprintError(
                "producer admission fingerprint must be 64 lowercase hex characters"
            )

    @classmethod
    def from_canonical_bytes(
        cls,
        data: bytes,
    ) -> ResearchProducerAdmissionFingerprint:
        if not isinstance(data, bytes):
            raise ResearchLineageFingerprintError(
                "producer admission canonical material must be bytes"
            )
        return cls(hashlib.sha256(data).hexdigest())


def _dataset_key(dataset: HistoricalOhlcReplayDataset) -> tuple[str, str]:
    return (
        str(dataset.manifest.dataset_id.value),
        str(dataset.manifest.revision_id.value),
    )


def _validate_dataset_membership(
    integrity_qualified_run: IntegrityQualifiedResearchRun,
    session: ResearchExecutionSession,
) -> None:
    qualified_keys = tuple(
        _dataset_key(qualification.dataset)
        for qualification in integrity_qualified_run.qualifications
    )
    session_keys = tuple(_dataset_key(dataset) for dataset in session.replay_datasets)
    if qualified_keys != session_keys:
        raise ResearchProducerAdmissionValidationError(
            "qualified dataset membership does not equal execution-session membership"
        )


def _compute_admission_fingerprint(
    run_fingerprint: IntegrityQualifiedResearchRunFingerprint,
    binding_fingerprint: ResearchRunStrategyBindingFingerprint,
    session_fingerprint: ResearchExecutionSessionFingerprint,
) -> ResearchProducerAdmissionFingerprint:
    if not isinstance(run_fingerprint, IntegrityQualifiedResearchRunFingerprint):
        raise ResearchLineageFingerprintError(
            "run_fingerprint must be IntegrityQualifiedResearchRunFingerprint"
        )
    if not isinstance(binding_fingerprint, ResearchRunStrategyBindingFingerprint):
        raise ResearchLineageFingerprintError(
            "binding_fingerprint must be ResearchRunStrategyBindingFingerprint"
        )
    if not isinstance(session_fingerprint, ResearchExecutionSessionFingerprint):
        raise ResearchLineageFingerprintError(
            "session_fingerprint must be ResearchExecutionSessionFingerprint"
        )
    projection = {
        "schema": "qore.research.producer.admission.v1",
        "integrity_qualified_run_fingerprint": run_fingerprint.value,
        "strategy_binding_fingerprint": binding_fingerprint.value,
        "execution_session_fingerprint": session_fingerprint.value,
    }
    canonical_bytes = json.dumps(
        projection,
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    return ResearchProducerAdmissionFingerprint.from_canonical_bytes(canonical_bytes)


@dataclasses.dataclass(frozen=True, slots=True)
class ResearchProducerAdmissionEvidence:
    """Exact bridge from integrity-qualified research inputs to one replay session."""

    integrity_qualified_run: IntegrityQualifiedResearchRun
    strategy_binding: ResearchRunStrategyBinding
    execution_session: ResearchExecutionSession = dataclasses.field(init=False)
    admission_fingerprint: ResearchProducerAdmissionFingerprint = dataclasses.field(
        init=False
    )

    def __post_init__(self) -> None:
        if not isinstance(self.integrity_qualified_run, IntegrityQualifiedResearchRun):
            raise ResearchProducerAdmissionValidationError(
                "integrity_qualified_run must be IntegrityQualifiedResearchRun"
            )
        if not isinstance(self.strategy_binding, ResearchRunStrategyBinding):
            raise ResearchProducerAdmissionValidationError(
                "strategy_binding must be ResearchRunStrategyBinding"
            )
        if self.strategy_binding.run != self.integrity_qualified_run.run:
            raise ResearchProducerAdmissionValidationError(
                "strategy_binding.run must equal integrity_qualified_run.run"
            )

        replay_datasets = tuple(
            qualification.dataset
            for qualification in self.integrity_qualified_run.qualifications
        )
        session = ResearchExecutionSession(
            strategy_binding=self.strategy_binding,
            replay_datasets=replay_datasets,
        )
        _validate_dataset_membership(self.integrity_qualified_run, session)
        object.__setattr__(self, "execution_session", session)

        fingerprint = _compute_admission_fingerprint(
            self.integrity_qualified_run.fingerprint,
            self.strategy_binding.binding_fingerprint,
            session.session_fingerprint,
        )
        object.__setattr__(self, "admission_fingerprint", fingerprint)
