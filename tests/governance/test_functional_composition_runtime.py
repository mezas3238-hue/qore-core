from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from qore.core.configuration import Configuration
from qore.core.runtime import RuntimeContext
from qore.governance.composition import compose_functional_governance
from qore.kernel.errors import ValidationError
from qore.kernel.result import Failure, Success

_RUNTIME_CONTEXT = RuntimeContext(
    execution_id=UUID("70000000-0000-0000-0000-000000000001"),
    runtime_version="1.0",
)
_NOW = datetime(2026, 8, 7, 23, 45, tzinfo=UTC)


def test_functional_composition_preserves_deterministic_runtime_context() -> None:
    composed = compose_functional_governance(
        Configuration(application_name="qore-functional-runtime-test"),
        runtime_context=_RUNTIME_CONTEXT,
        clock=lambda: _NOW,
    )

    assert isinstance(composed, Success)
    assert composed.value.core.runtime_context is _RUNTIME_CONTEXT
    assert composed.value.core.lifecycle.runtime_context is _RUNTIME_CONTEXT


def test_functional_composition_rejects_partial_runtime_configuration() -> None:
    composed = compose_functional_governance(
        Configuration(application_name="qore-functional-runtime-test"),
        runtime_context=_RUNTIME_CONTEXT,
    )

    assert isinstance(composed, Failure)
    assert isinstance(composed.error, ValidationError)
