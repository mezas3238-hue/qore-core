import json
from datetime import UTC, datetime, timedelta

import pytest

from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)
from qore.infrastructure.cibo_phase20_demo_execution_activation import (
    load_phase20_demo_execution_activation,
)

SHA = "a" * 40


def _payload() -> dict[str, object]:
    return {
        "schema": "qore.cibo.phase20d.demo_execution_activation.v1",
        "authorization_token": "CIBO_PHASE20D_DEMO_EXECUTION_AUTHORIZED",
        "authorized_by_owner": True,
        "environment": "demo",
        "collector_git_sha": SHA,
        "authorized_at": (
            datetime.now(UTC) - timedelta(minutes=1)
        ).isoformat(),
        "fundednext_allowed": False,
        "live_allowed": False,
        "real_capital_allowed": False,
        "merge_allowed": False,
    }


def _write(tmp_path, payload: dict[str, object]):
    path = tmp_path / "activation.json"
    path.write_text(
        json.dumps(payload, sort_keys=True),
        encoding="utf-8",
    )
    return path


def test_phase20_demo_activation_accepts_exact_owner_scope(tmp_path) -> None:
    activation = load_phase20_demo_execution_activation(
        _write(tmp_path, _payload()),
        expected_git_sha=SHA,
    )

    assert activation.environment == "demo"
    assert activation.collector_git_sha == SHA
    assert activation.authorized_by_owner is True
    assert activation.fundednext_allowed is False
    assert activation.live_allowed is False
    assert activation.real_capital_allowed is False
    assert activation.merge_allowed is False


def test_phase20_demo_activation_requires_explicit_owner_token(tmp_path) -> None:
    payload = _payload()
    payload["authorization_token"] = "NOT_AUTHORIZED"

    with pytest.raises(
        CiboCapitalManagementError,
        match="Owner token missing",
    ):
        load_phase20_demo_execution_activation(
            _write(tmp_path, payload),
            expected_git_sha=SHA,
        )


def test_phase20_demo_activation_rejects_git_drift(tmp_path) -> None:
    with pytest.raises(
        CiboCapitalManagementError,
        match="Git lineage mismatch",
    ):
        load_phase20_demo_execution_activation(
            _write(tmp_path, _payload()),
            expected_git_sha="b" * 40,
        )


@pytest.mark.parametrize(
    "field",
    (
        "fundednext_allowed",
        "live_allowed",
        "real_capital_allowed",
        "merge_allowed",
    ),
)
def test_phase20_demo_activation_cannot_grant_other_authority(
    tmp_path,
    field: str,
) -> None:
    payload = _payload()
    payload[field] = True

    with pytest.raises(
        CiboCapitalManagementError,
        match="cannot grant non-DEMO authority",
    ):
        load_phase20_demo_execution_activation(
            _write(tmp_path, payload),
            expected_git_sha=SHA,
        )


def test_phase20_demo_activation_missing_file_fails_closed(tmp_path) -> None:
    with pytest.raises(
        CiboCapitalManagementError,
        match="activation file is required",
    ):
        load_phase20_demo_execution_activation(
            tmp_path / "missing.json",
            expected_git_sha=SHA,
        )
