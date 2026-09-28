from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)
from qore.infrastructure.cibo_ce2i_advanced_evidence import (
    AdvancedCe2iEvidenceSnapshot,
    advanced_evidence_snapshot_sha256,
    assert_advanced_evidence_snapshot_causal,
)
from qore.infrastructure.cibo_ce2i_full_surface import (
    AdvancedPortfolioEvidence,
)


_NOW = datetime(2026, 9, 28, 5, 0, tzinfo=UTC)


def _snapshot(*, assembled_at: datetime = _NOW) -> AdvancedCe2iEvidenceSnapshot:
    return AdvancedCe2iEvidenceSnapshot(
        evidence_id="advanced-evidence-1",
        assembled_at=assembled_at,
        source_refs=("source:oos-calibration:v1",),
        evidence=AdvancedPortfolioEvidence(),
    )


def test_advanced_evidence_snapshot_digest_is_deterministic() -> None:
    left = advanced_evidence_snapshot_sha256(_snapshot())
    right = advanced_evidence_snapshot_sha256(_snapshot())

    assert left == right
    assert left.startswith("sha256:")
    assert len(left) == 71


def test_advanced_evidence_snapshot_must_precede_decision() -> None:
    with pytest.raises(
        CiboCapitalManagementError,
        match="cannot postdate decision",
    ):
        assert_advanced_evidence_snapshot_causal(
            _snapshot(assembled_at=_NOW + timedelta(milliseconds=1)),
            decision_at=_NOW,
            max_age_seconds=Decimal("2"),
        )


def test_advanced_evidence_snapshot_must_be_fresh() -> None:
    with pytest.raises(
        CiboCapitalManagementError,
        match="exceeds decision freshness bound",
    ):
        assert_advanced_evidence_snapshot_causal(
            _snapshot(assembled_at=_NOW - timedelta(seconds=3)),
            decision_at=_NOW,
            max_age_seconds=Decimal("2"),
        )


def test_advanced_evidence_snapshot_rejects_synthetic_or_outcome_aware() -> None:
    with pytest.raises(
        CiboCapitalManagementError,
        match="causal/non-synthetic",
    ):
        AdvancedCe2iEvidenceSnapshot(
            evidence_id="synthetic",
            assembled_at=_NOW,
            source_refs=("source:test",),
            evidence=AdvancedPortfolioEvidence(),
            synthetic=True,
        )
