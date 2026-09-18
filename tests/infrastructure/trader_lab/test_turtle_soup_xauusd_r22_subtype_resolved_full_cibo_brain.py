from __future__ import annotations

from qore.infrastructure.trader_lab import (
    turtle_soup_xauusd_r21_cautious_mixed_subtype_memory as r21,
)
from qore.infrastructure.trader_lab.turtle_soup_xauusd_r22_subtype_resolved_full_cibo_brain import (
    _resolve_entry_policy,
)


def test_supportive_executes_without_subtype_gate() -> None:
    mode, policy = _resolve_entry_policy(
        memory_state="SUPPORTIVE",
        signature="missing",
        subtype_memory={},
    )
    assert mode == "NEXT_SOURCE_OPEN"
    assert policy == "SUPPORTIVE_EXECUTE"


def test_recoverable_executes_now() -> None:
    mode, policy = _resolve_entry_policy(
        memory_state="CAUTIOUS",
        signature="sig",
        subtype_memory={"sig": {"classification": r21.RECOVERABLE}},
    )
    assert mode == "NEXT_SOURCE_OPEN"
    assert policy == "SUBTYPE_RECOVERABLE_EXECUTE"


def test_wait_uses_retest_only_when_stable_wait_exists() -> None:
    mode, policy = _resolve_entry_policy(
        memory_state="MIXED",
        signature="sig",
        subtype_memory={"sig": {"classification": r21.WAIT}},
    )
    assert mode == "CISD_THRESHOLD_RETEST"
    assert policy == "SUBTYPE_WAIT_FOR_CONFIRMATION"


def test_abstain_rejects_current_setup() -> None:
    mode, policy = _resolve_entry_policy(
        memory_state="CAUTIOUS",
        signature="sig",
        subtype_memory={"sig": {"classification": r21.ABSTAIN}},
    )
    assert mode is None
    assert policy == "SUBTYPE_ABSTAIN_STRUCTURAL"


def test_unresolved_waits_new_event_instead_of_generic_retest() -> None:
    mode, policy = _resolve_entry_policy(
        memory_state="MIXED",
        signature="sig",
        subtype_memory={"sig": {"classification": r21.UNRESOLVED}},
    )
    assert mode is None
    assert policy == "SUBTYPE_UNRESOLVED_WAIT_NEW_EVENT"
