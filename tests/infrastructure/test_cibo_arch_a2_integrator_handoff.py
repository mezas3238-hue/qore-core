from __future__ import annotations

from qore.infrastructure.cibo_arch_a2_integrator_handoff import (
    ARCH_A_BASE_SHA,
    A2_BRANCH,
    SCHEMA,
    build_architect_a2_integrator_handoff,
)
from qore.infrastructure.cibo_arch_a2_internal_readiness import (
    evaluate_architect_a2_internal_readiness,
)
from qore.infrastructure.cibo_arch_a2_scientific_closure import (
    A2_WORKSTREAM_IDS,
    ArchitectA2ScientificClosurePacket,
)

MANIFEST = "sha256:" + "1" * 64
HEAD = "2" * 40


def _closure(
    *,
    falsified_ids: tuple[str, ...] = (),
    incomplete: bool = False,
) -> ArchitectA2ScientificClosurePacket:
    if incomplete:
        return ArchitectA2ScientificClosurePacket(
            phase22_manifest_sha256=MANIFEST,
            receipt_count=0,
            terminal_count=0,
            completed_ids=(),
            falsified_ids=(),
            external_ids=(),
            missing_ids=A2_WORKSTREAM_IDS,
            exact_a2_surface=True,
            ready_for_integrator=False,
        )
    falsified = set(falsified_ids)
    completed = tuple(
        item for item in A2_WORKSTREAM_IDS if item not in falsified
    )
    return ArchitectA2ScientificClosurePacket(
        phase22_manifest_sha256=MANIFEST,
        receipt_count=17,
        terminal_count=17,
        completed_ids=completed,
        falsified_ids=falsified_ids,
        external_ids=(),
        missing_ids=(),
        exact_a2_surface=True,
        ready_for_integrator=True,
    )


def test_a2_integrator_handoff_binds_exact_green_lane() -> None:
    receipt = build_architect_a2_integrator_handoff(
        a2_head_sha=HEAD,
        readiness=evaluate_architect_a2_internal_readiness(),
        closure=_closure(),
    )

    assert receipt.schema == SCHEMA
    assert receipt.branch == A2_BRANCH
    assert receipt.arch_a_base_sha == ARCH_A_BASE_SHA
    assert receipt.a2_head_sha == HEAD
    assert receipt.terminal_count == 17
    assert receipt.completed_ids == A2_WORKSTREAM_IDS
    assert receipt.falsified_ids == ()
    assert receipt.blockers == ()
    assert receipt.ready_for_integrator is True
    assert receipt.ledger_update_authority is False
    assert receipt.merge_authority is False
    assert receipt.certification_claimed is False
    assert receipt.productive_authority is False
    assert receipt.fingerprint().startswith("sha256:")


def test_a2_integrator_handoff_accepts_legitimate_falsification() -> None:
    receipt = build_architect_a2_integrator_handoff(
        a2_head_sha=HEAD,
        readiness=evaluate_architect_a2_internal_readiness(),
        closure=_closure(falsified_ids=("GEN-C12",)),
    )

    assert receipt.terminal_count == 17
    assert receipt.falsified_ids == ("GEN-C12",)
    assert receipt.ready_for_integrator is True
    assert receipt.blockers == ()


def test_a2_integrator_handoff_blocks_incomplete_science() -> None:
    receipt = build_architect_a2_integrator_handoff(
        a2_head_sha=HEAD,
        readiness=evaluate_architect_a2_internal_readiness(),
        closure=_closure(incomplete=True),
    )

    assert receipt.terminal_count == 0
    assert receipt.ready_for_integrator is False
    assert receipt.blockers == ("A2_SCIENTIFIC_CLOSURE_INCOMPLETE",)
