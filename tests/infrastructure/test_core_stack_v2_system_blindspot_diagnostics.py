from datetime import UTC, datetime

import pytest

from qore.infrastructure.core_stack_v2.system_blindspot_diagnostics import (
    SecondOrderSystemDiagnosticSnapshot,
    SystemDiagnosticEvidence,
    SystemDiagnosticKind,
    SystemDiagnosticState,
    build_second_order_system_diagnostics,
)

NOW = datetime(2026, 9, 30, 21, 5, tzinfo=UTC)


def _evidence(
    kind: SystemDiagnosticKind,
    *,
    bound: bool = True,
) -> SystemDiagnosticEvidence:
    return SystemDiagnosticEvidence(
        kind=kind,
        state=(
            SystemDiagnosticState.HEALTHY
            if bound
            else SystemDiagnosticState.UNKNOWN
        ),
        severity_bps=0,
        observed_at=NOW,
        evidence_cutoff_at=NOW,
        evidence_refs=(f"diagnostic:{kind.value}",),
        diagnostic_evidence_bound=bound,
    )


def test_full_taxonomy_can_complete_only_when_all_diagnostics_are_bound() -> None:
    snapshot = build_second_order_system_diagnostics(
        tuple(_evidence(kind) for kind in SystemDiagnosticKind)
    )
    assert snapshot.complete is True
    assert snapshot.open_diagnostics == ()


def test_unknown_diagnostic_keeps_mc28_open() -> None:
    rows = tuple(
        _evidence(
            kind,
            bound=kind is not SystemDiagnosticKind.CLOCK_DRIFT,
        )
        for kind in SystemDiagnosticKind
    )
    snapshot = build_second_order_system_diagnostics(rows)
    assert snapshot.complete is False
    assert snapshot.open_diagnostics == (SystemDiagnosticKind.CLOCK_DRIFT,)


def test_missing_standard_006_category_fails_closed() -> None:
    rows = tuple(
        _evidence(kind)
        for kind in SystemDiagnosticKind
        if kind is not SystemDiagnosticKind.MAPPING_ERRORS
    )
    with pytest.raises(ValueError, match="all Standard 006"):
        SecondOrderSystemDiagnosticSnapshot(
            diagnostics=tuple(sorted(rows, key=lambda item: item.kind.value)),
            open_diagnostics=(),
            complete=True,
        )


def test_unbound_diagnostic_cannot_claim_health_or_authority() -> None:
    with pytest.raises(ValueError, match="must remain UNKNOWN"):
        SystemDiagnosticEvidence(
            kind=SystemDiagnosticKind.MODEL_RUNTIME_INSTABILITY,
            state=SystemDiagnosticState.HEALTHY,
            severity_bps=0,
            observed_at=NOW,
            evidence_cutoff_at=NOW,
            evidence_refs=("diagnostic:model-runtime",),
            diagnostic_evidence_bound=False,
        )

    with pytest.raises(ValueError, match="observational only"):
        SystemDiagnosticEvidence(
            kind=SystemDiagnosticKind.FEED_DEGRADATION,
            state=SystemDiagnosticState.HEALTHY,
            severity_bps=0,
            observed_at=NOW,
            evidence_cutoff_at=NOW,
            evidence_refs=("diagnostic:feed",),
            diagnostic_evidence_bound=True,
            restart_authority=True,
        )
