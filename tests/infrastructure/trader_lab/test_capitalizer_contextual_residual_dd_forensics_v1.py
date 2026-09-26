from __future__ import annotations

from qore.infrastructure.trader_lab import (
    capitalizer_contextual_residual_dd_forensics_v1 as forensic,
)


def test_identity_and_policy_are_frozen() -> None:
    assert forensic.IDENTITY == "QORE_CAPITALIZER_CONTEXTUAL_RESIDUAL_DD_FORENSICS_V1"
    assert forensic.POLICY == "CONTEXT_STABILITY_STAGE"
