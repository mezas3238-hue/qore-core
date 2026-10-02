import pytest

from qore.infrastructure.cibo_phase22_demo_calibration_contract import (
    CALIBRATION_AUTHORIZATION_TOKEN,
    CALIBRATION_LABEL_PREFIX,
    DEMO_ONLY_CONFIRMATION,
    MANUAL_DISPATCH_EVENT,
    MAXIMUM_ROUND_TRIPS_PER_MANUAL_DISPATCH,
    MINIMUM_DISTINCT_ENTRY_ORDERS_PER_SYMBOL,
    OWNER_GITHUB_LOGIN,
    PHASE22_DEMO_CALIBRATION_GOVERNANCE,
    REQUIRED_SYMBOLS,
    Phase22DemoCalibrationInvocation,
    plan_missing_execution_slots,
)


def _invocation(
    *,
    event_name: str = MANUAL_DISPATCH_EVENT,
    run_attempt: int = 1,
    requested_round_trips: int = 6,
) -> Phase22DemoCalibrationInvocation:
    return Phase22DemoCalibrationInvocation(
        event_name=event_name,
        actor=OWNER_GITHUB_LOGIN,
        run_id="36922694706",
        run_attempt=run_attempt,
        owner_authorization=CALIBRATION_AUTHORIZATION_TOKEN,
        demo_only_confirmation=DEMO_ONLY_CONFIRMATION,
        requested_round_trips=requested_round_trips,
    )


def test_phase22_demo_calibration_surface_is_strict() -> None:
    assert CALIBRATION_AUTHORIZATION_TOKEN == (
        "CIBO_PHASE22_DEMO_EXECUTION_CALIBRATION_AUTHORIZED"
    )
    assert CALIBRATION_LABEL_PREFIX == "QORE:CIBO-CAL:"
    assert MINIMUM_DISTINCT_ENTRY_ORDERS_PER_SYMBOL == 8
    assert MAXIMUM_ROUND_TRIPS_PER_MANUAL_DISPATCH == 6
    assert REQUIRED_SYMBOLS == (
        "AUDJPY",
        "EURUSD",
        "GBPJPY",
        "GBPUSD",
        "NAS100",
        "XAUUSD",
    )


def test_phase22_demo_calibration_never_grants_live_or_real_capital() -> None:
    governance = PHASE22_DEMO_CALIBRATION_GOVERNANCE

    assert governance.environment == "demo"
    assert governance.endpoint_host == "demo.ctraderapi.com"
    assert governance.account_must_be_non_live is True
    assert governance.minimum_volume_only is True
    assert governance.close_created_position_only is True
    assert governance.holdout_outcomes_allowed is False
    assert governance.fundednext_allowed is False
    assert governance.live_allowed is False
    assert governance.real_capital_allowed is False
    assert governance.vps_required is False


def test_push_can_never_construct_mutation_authority() -> None:
    with pytest.raises(ValueError, match="workflow_dispatch"):
        _invocation(event_name="push")


def test_retry_is_reconciliation_only_and_plans_no_orders() -> None:
    invocation = _invocation(run_attempt=2)
    counts = {symbol: 0 for symbol in REQUIRED_SYMBOLS}

    assert invocation.mutation_budget == 0
    assert plan_missing_execution_slots(counts, invocation=invocation) == ()


def test_sufficient_broker_execution_population_plans_zero_orders() -> None:
    counts = {
        symbol: MINIMUM_DISTINCT_ENTRY_ORDERS_PER_SYMBOL
        for symbol in REQUIRED_SYMBOLS
    }

    assert plan_missing_execution_slots(
        counts,
        invocation=_invocation(),
    ) == ()


def test_broker_execution_plan_obeys_hard_dispatch_limit() -> None:
    counts = {symbol: 0 for symbol in REQUIRED_SYMBOLS}

    planned = plan_missing_execution_slots(
        counts,
        invocation=_invocation(requested_round_trips=3),
    )

    assert planned == (("AUDJPY", 1), ("AUDJPY", 2), ("AUDJPY", 3))


@pytest.mark.parametrize(
    ("field", "value"),
    (
        ("actor", "someone-else"),
        ("owner_authorization", "wrong"),
        ("demo_only_confirmation", "LIVE"),
        ("requested_round_trips", 7),
    ),
)
def test_any_ambiguous_manual_authority_fails_closed(
    field: str,
    value: object,
) -> None:
    kwargs: dict[str, object] = {
        "event_name": MANUAL_DISPATCH_EVENT,
        "actor": OWNER_GITHUB_LOGIN,
        "run_id": "36922694706",
        "run_attempt": 1,
        "owner_authorization": CALIBRATION_AUTHORIZATION_TOKEN,
        "demo_only_confirmation": DEMO_ONLY_CONFIRMATION,
        "requested_round_trips": 1,
    }
    kwargs[field] = value

    with pytest.raises(ValueError):
        Phase22DemoCalibrationInvocation(**kwargs)  # type: ignore[arg-type]
