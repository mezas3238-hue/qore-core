from __future__ import annotations

import pytest

from qore.infrastructure.research_lineage_errors import ResearchLineageFingerprintError
from qore.infrastructure.research_lineage_fingerprints import (
    ResearchAnalysisInputEvidenceFingerprint,
    ResearchAnalysisLineageFingerprint,
    ResearchExecutionSessionFingerprint,
    ResearchExecutionTraceFingerprint,
    ResearchStateTransitionFingerprint,
    ResearchStrategyStateFingerprint,
    ResearchTraderCommandFingerprint,
)


_FINGERPRINT_TYPES = (
    ResearchExecutionSessionFingerprint,
    ResearchStrategyStateFingerprint,
    ResearchStateTransitionFingerprint,
    ResearchExecutionTraceFingerprint,
    ResearchAnalysisInputEvidenceFingerprint,
    ResearchTraderCommandFingerprint,
    ResearchAnalysisLineageFingerprint,
)


@pytest.mark.parametrize("fingerprint_type", _FINGERPRINT_TYPES)
def test_fingerprint_accepts_lowercase_sha256(fingerprint_type: type[object]) -> None:
    value = fingerprint_type("a" * 64)
    assert getattr(value, "value") == "a" * 64
    assert getattr(value, "logical_values")() == {
        "algorithm": "sha256",
        "value": "a" * 64,
    }


@pytest.mark.parametrize("fingerprint_type", _FINGERPRINT_TYPES)
def test_fingerprint_rejects_uppercase_or_wrong_length(
    fingerprint_type: type[object],
) -> None:
    with pytest.raises(ResearchLineageFingerprintError):
        fingerprint_type("A" * 64)
    with pytest.raises(ResearchLineageFingerprintError):
        fingerprint_type("a" * 63)
