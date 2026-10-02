from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)
from qore.infrastructure.cibo_phase22_demo_calibration_contract import (
    REQUIRED_SYMBOLS,
)
from qore.kernel.result import Success
from scripts import cibo_phase22_demo_provider_calibration as calibration

_WORKFLOW = Path(
    ".github/workflows/cibo-phase22-demo-provider-calibration.yml"
)


def _content() -> str:
    return _WORKFLOW.read_text(encoding="utf-8")


def test_push_job_is_structurally_non_mutating_and_has_no_secrets() -> None:
    content = _content()
    validation = content.split("  manual-demo-calibration:", maxsplit=1)[0]

    assert "  push:" in validation
    assert "--validate-only" in validation
    assert "--execute" not in validation
    assert "secrets." not in validation
    assert "QORE_CTRADER_" not in validation
    assert "manual-demo-calibration:" in content
    assert "github.event_name == 'workflow_dispatch'" in content


def test_mutation_job_requires_manual_owner_demo_gate_and_hard_limit() -> None:
    content = _content()
    mutation = content.split("  manual-demo-calibration:", maxsplit=1)[1]

    assert "environment: ctrader-demo-broker-mutation" in mutation
    assert 'test "$GITHUB_EVENT_NAME" = "workflow_dispatch"' in mutation
    assert 'test "$GITHUB_ACTOR" = "mezas3238-hue"' in mutation
    assert "CIBO_PHASE22_DEMO_EXECUTION_CALIBRATION_AUTHORIZED" in mutation
    assert "DEMO_ONLY_NO_LIVE_NO_FUNDEDNEXT" in mutation
    assert "1|2|3|4|5|6" in mutation
    assert "--execute" in mutation


def test_workflow_has_only_demo_named_credentials_without_generic_fallbacks() -> None:
    content = _content()
    mutation = content.split("  manual-demo-calibration:", maxsplit=1)[1]

    for secret in (
        "QORE_CTRADER_DEMO_CLIENT_ID",
        "QORE_CTRADER_DEMO_CLIENT_SECRET",
        "QORE_CTRADER_DEMO_ACCESS_TOKEN",
        "QORE_CTRADER_DEMO_REFRESH_TOKEN",
        "QORE_CTRADER_DEMO_ACCOUNT_ID",
    ):
        assert f"secrets.{secret}" in mutation
    assert "|| secrets." not in content
    assert "secrets.QORE_CTRADER_ACCOUNT_ID" not in content
    assert "QORE_FUNDEDNEXT" not in content


def test_push_authorization_fails_before_broker_client_construction(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    constructed = 0

    def forbidden_client(*_args: object, **_kwargs: object) -> object:
        nonlocal constructed
        constructed += 1
        raise AssertionError("broker client must not be constructed")

    monkeypatch.setenv("GITHUB_EVENT_NAME", "push")
    monkeypatch.setenv("GITHUB_ACTOR", "mezas3238-hue")
    monkeypatch.setenv("GITHUB_RUN_ID", "36922694706")
    monkeypatch.setenv("GITHUB_RUN_ATTEMPT", "1")
    monkeypatch.setenv(
        "QORE_CIBO_PHASE22_DEMO_CALIBRATION_AUTHORIZATION",
        "CIBO_PHASE22_DEMO_EXECUTION_CALIBRATION_AUTHORIZED",
    )
    monkeypatch.setenv(
        "QORE_CIBO_PHASE22_DEMO_ONLY_CONFIRMATION",
        "DEMO_ONLY_NO_LIVE_NO_FUNDEDNEXT",
    )
    monkeypatch.setenv("QORE_CIBO_PHASE22_MAX_ROUND_TRIPS", "1")
    monkeypatch.setattr(
        calibration,
        "SpotwareCTraderOpenApiClient",
        forbidden_client,
    )

    with pytest.raises(CiboCapitalManagementError, match="failed closed"):
        calibration.run()

    assert constructed == 0


def test_validation_report_cannot_claim_or_perform_broker_mutation() -> None:
    report = calibration._validation_report()

    assert report["status"] == "VALIDATION_ONLY"
    assert report["broker_credentials_loaded"] is False
    assert report["broker_client_constructed"] is False
    assert report["broker_mutation_performed"] is False
    assert report["created_round_trip_count"] == 0
    assert report["fundednext_allowed"] is False
    assert report["live_allowed"] is False
    assert report["real_capital_allowed"] is False


def test_sufficient_real_broker_population_creates_zero_round_trips(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FakeClient:
        def __init__(self, *, credentials: object) -> None:
            del credentials

        def connect_and_authenticate(self) -> Success[None]:
            return Success(None)

        def close(self) -> None:
            return None

    contracts = tuple(
        SimpleNamespace(qore_symbol=symbol) for symbol in REQUIRED_SYMBOLS
    )
    binding = SimpleNamespace(
        contracts=contracts,
        account=SimpleNamespace(account_ref="demo-account"),
    )
    counts = {symbol: 8 for symbol in REQUIRED_SYMBOLS}

    monkeypatch.setenv("GITHUB_EVENT_NAME", "workflow_dispatch")
    monkeypatch.setenv("GITHUB_ACTOR", "mezas3238-hue")
    monkeypatch.setenv("GITHUB_RUN_ID", "36922694706")
    monkeypatch.setenv("GITHUB_RUN_ATTEMPT", "1")
    monkeypatch.setenv(
        "QORE_CIBO_PHASE22_DEMO_CALIBRATION_AUTHORIZATION",
        "CIBO_PHASE22_DEMO_EXECUTION_CALIBRATION_AUTHORIZED",
    )
    monkeypatch.setenv(
        "QORE_CIBO_PHASE22_DEMO_ONLY_CONFIRMATION",
        "DEMO_ONLY_NO_LIVE_NO_FUNDEDNEXT",
    )
    monkeypatch.setenv("QORE_CIBO_PHASE22_MAX_ROUND_TRIPS", "6")
    monkeypatch.setattr(calibration, "credentials_from_environment", object)
    monkeypatch.setattr(
        calibration,
        "SpotwareCTraderOpenApiClient",
        FakeClient,
    )
    monkeypatch.setattr(
        calibration,
        "discover_free_account_binding",
        lambda _client: binding,
    )
    monkeypatch.setattr(
        calibration,
        "_history",
        lambda *_args, **_kwargs: ({}, {}, counts),
    )
    monkeypatch.setattr(
        calibration,
        "_one_round_trip",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError("sufficient broker population must not mutate")
        ),
    )

    report = calibration.run()

    assert report["population_already_sufficient_before_run"] is True
    assert report["created_round_trip_count"] == 0
    assert report["broker_mutation_performed"] is False


def test_first_round_trip_error_aborts_without_attempting_another(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FakeClient:
        def __init__(self, *, credentials: object) -> None:
            del credentials

        def connect_and_authenticate(self) -> Success[None]:
            return Success(None)

        def close(self) -> None:
            return None

    binding = SimpleNamespace(
        contracts=tuple(
            SimpleNamespace(qore_symbol=symbol)
            for symbol in REQUIRED_SYMBOLS
        ),
        account=SimpleNamespace(account_ref="demo-account"),
    )
    counts = {symbol: 0 for symbol in REQUIRED_SYMBOLS}
    attempts = 0

    def fail_first_round_trip(*_args: object, **_kwargs: object) -> object:
        nonlocal attempts
        attempts += 1
        raise CiboCapitalManagementError("synthetic broker ambiguity")

    monkeypatch.setenv("GITHUB_EVENT_NAME", "workflow_dispatch")
    monkeypatch.setenv("GITHUB_ACTOR", "mezas3238-hue")
    monkeypatch.setenv("GITHUB_RUN_ID", "36922694706")
    monkeypatch.setenv("GITHUB_RUN_ATTEMPT", "1")
    monkeypatch.setenv(
        "QORE_CIBO_PHASE22_DEMO_CALIBRATION_AUTHORIZATION",
        "CIBO_PHASE22_DEMO_EXECUTION_CALIBRATION_AUTHORIZED",
    )
    monkeypatch.setenv(
        "QORE_CIBO_PHASE22_DEMO_ONLY_CONFIRMATION",
        "DEMO_ONLY_NO_LIVE_NO_FUNDEDNEXT",
    )
    monkeypatch.setenv("QORE_CIBO_PHASE22_MAX_ROUND_TRIPS", "6")
    monkeypatch.setattr(calibration, "credentials_from_environment", object)
    monkeypatch.setattr(
        calibration,
        "SpotwareCTraderOpenApiClient",
        FakeClient,
    )
    monkeypatch.setattr(
        calibration,
        "discover_free_account_binding",
        lambda _client: binding,
    )
    monkeypatch.setattr(
        calibration,
        "_history",
        lambda *_args, **_kwargs: ({}, {}, counts),
    )
    monkeypatch.setattr(
        calibration,
        "_one_round_trip",
        fail_first_round_trip,
    )

    with pytest.raises(
        CiboCapitalManagementError,
        match="synthetic broker ambiguity",
    ):
        calibration.run()

    assert attempts == 1
