from qore.infrastructure.traders.crt_pure_r2_readiness import (
    model1_r2_readiness,
)
from qore.infrastructure.traders.crt_pure_source_registry import CrtPureConceptId


def test_model1_r2_is_fail_closed_on_old_level_reference_selection() -> None:
    readiness = model1_r2_readiness()
    assert readiness.ready is False
    assert readiness.unresolved == (
        CrtPureConceptId.MODEL_1_REFERENCE_SELECTION,
    )
    assert readiness.grants_replay_authority is False
    assert readiness.grants_deployment_authority is False
