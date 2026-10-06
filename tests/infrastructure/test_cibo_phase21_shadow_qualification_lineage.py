from dataclasses import replace

import pytest

from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)
from qore.infrastructure.cibo_phase21_shadow_qualification_lineage import (
    EVIDENCE_CLASS,
    PHASE21_SHADOW_QUALIFICATION_LINEAGE_RECEIPT,
)


def test_shadow_lineage_receipt_is_explicitly_not_forward_empirical() -> None:
    receipt = PHASE21_SHADOW_QUALIFICATION_LINEAGE_RECEIPT

    assert receipt.evidence_class == EVIDENCE_CLASS
    assert receipt.forward_empirical_claimed is False
    assert receipt.provider_economics_claimed is False
    assert receipt.final_holdout_2017h1_read is False
    assert receipt.policy_retuned_after_outcomes is False
    assert receipt.productive_authority is False
    assert len(receipt.protected_source_digests) == 7
    assert receipt.fingerprint().startswith("sha256:")


def test_shadow_lineage_receipt_rejects_forward_relabelling() -> None:
    with pytest.raises(
        CiboCapitalManagementError,
        match="governance contamination",
    ):
        replace(
            PHASE21_SHADOW_QUALIFICATION_LINEAGE_RECEIPT,
            forward_empirical_claimed=True,
        )
