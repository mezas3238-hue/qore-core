from qore.infrastructure.core_stack_v2.stability_engine import (
    StabilityDomain,
    StabilityState,
    assess_stability_channel,
)
from qore.infrastructure.core_stack_v2.stability_operational_binding import (
    OperationalSystemKind,
    OperationalSystemObservation,
    OperationalSystemState,
    operational_stability_evidence,
)


def _obs(
    system_id: str,
    kind: OperationalSystemKind,
    state: OperationalSystemState,
) -> OperationalSystemObservation:
    return OperationalSystemObservation(
        system_id=system_id,
        system_kind=kind,
        state=state,
        fingerprint_sha256="a" * 64,
    )


def test_healthy_operational_evidence_maps_to_stable_channels() -> None:
    evidence = operational_stability_evidence(
        (
            _obs(
                "core",
                OperationalSystemKind.CORE_COMPONENT,
                OperationalSystemState.HEALTHY,
            ),
            _obs(
                "provider",
                OperationalSystemKind.PROVIDER,
                OperationalSystemState.HEALTHY,
            ),
            _obs(
                "broker",
                OperationalSystemKind.BROKER,
                OperationalSystemState.HEALTHY,
            ),
        ),
        evidence_refs=("artifact:11120521150", "run:36764365409"),
    )
    channels = tuple(assess_stability_channel(item) for item in evidence)
    assert {item.domain for item in channels} == {
        StabilityDomain.QORE_CORE,
        StabilityDomain.PROVIDER_BROKER,
    }
    assert all(item.state is StabilityState.STABLE for item in channels)


def test_worst_provider_or_broker_state_is_preserved() -> None:
    evidence = operational_stability_evidence(
        (
            _obs(
                "core",
                OperationalSystemKind.CORE_COMPONENT,
                OperationalSystemState.HEALTHY,
            ),
            _obs(
                "provider",
                OperationalSystemKind.PROVIDER,
                OperationalSystemState.HEALTHY,
            ),
            _obs(
                "broker",
                OperationalSystemKind.BROKER,
                OperationalSystemState.DEGRADED,
            ),
        ),
        evidence_refs=("artifact:11120521150", "run:36764365409"),
    )
    provider = next(
        item
        for item in evidence
        if item.domain is StabilityDomain.PROVIDER_BROKER
    )
    channel = assess_stability_channel(provider)
    assert channel.state is StabilityState.DEFENSIVE_CONTEXT
    assert channel.trading_command is False


def test_operational_authority_is_rejected() -> None:
    try:
        OperationalSystemObservation(
            system_id="broker",
            system_kind=OperationalSystemKind.BROKER,
            state=OperationalSystemState.HEALTHY,
            fingerprint_sha256="a" * 64,
            order_authority=True,
        )
    except ValueError as exc:
        assert "read-only" in str(exc)
    else:
        raise AssertionError("operational mutation authority must fail closed")
