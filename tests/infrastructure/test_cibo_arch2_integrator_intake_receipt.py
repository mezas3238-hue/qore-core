from qore.infrastructure.cibo_arch2_integrator_intake_receipt import (
    ARCHITECT2_INTEGRATOR_INTAKE_RECEIPT,
)
from qore.infrastructure.cibo_arch2_active_scope_v2 import (
    ARCHITECT2_ACTIVE_OWNERSHIP,
)


def test_integrator_intake_covers_only_current_eight_front_scope() -> None:
    receipt = ARCHITECT2_INTEGRATOR_INTAKE_RECEIPT

    assert tuple(item.workstream_id for item in receipt.workstreams) == (
        ARCHITECT2_ACTIVE_OWNERSHIP
    )
    assert receipt.scope_count == 8
    assert receipt.terminal_recommendation_count == 4
    assert receipt.nonterminal_count == 4
    assert receipt.external_dependency_count == 2
    assert receipt.integrator_receipt_dependency_count == 1


def test_integrator_intake_has_no_authority_and_is_fingerprintable() -> None:
    receipt = ARCHITECT2_INTEGRATOR_INTAKE_RECEIPT

    assert receipt.canonical_ledger_modified is False
    assert receipt.phase22_v2_consumed is False
    assert receipt.merge_authority is False
    assert receipt.productive_authority is False
    assert receipt.fingerprint().startswith("sha256:")
    assert len(receipt.fingerprint()) == 71
