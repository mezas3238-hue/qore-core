from __future__ import annotations

from decimal import Decimal

from qore.infrastructure.trader_lab import (
    vt08_index_r54_cisd_semantic_sequence_forensics as r54,
)


def test_r54_binds_existing_semantic_contracts() -> None:
    assert r54.SECONDARY_STRESS == Decimal("0.10")
    assert r54.R53_IDENTITY == (
        "VT08_INDEX_R53_SOURCE_COMPLETE_CISD_REACTION_QUALITY_FORENSICS_001"
    )
    assert r54.R47_CANDIDATE_ID == (
        "VT08_INDEX_R47_TRANSPORT_SAFE_STRUCTURAL_DEMOTION_001"
    )


def test_r54_concentration_fails_closed_on_empty_rows() -> None:
    report = r54._concentration(())
    assert report["sample"] == 0
    assert report["terminal_r"] == "0"
    assert report["winner_count"] == 0
    assert report["top_1_winner_fraction_of_terminal"] is None
    assert report["top_3_winner_fraction_of_terminal"] is None


def test_r54_all_periods_positive_requires_nonempty() -> None:
    assert r54._all_periods_positive({}) is False
    assert r54._all_periods_positive(
        {
            "Y1": {"total_r": "1"},
            "Y2": {"total_r": "0.1"},
        }
    ) is True
    assert r54._all_periods_positive(
        {
            "Y1": {"total_r": "1"},
            "Y2": {"total_r": "-0.1"},
        }
    ) is False
