from qore.infrastructure.core_stack_v2.stability_engine import (
    StabilityDomain,
    StabilityEvidence,
    StabilityState,
    build_stability_snapshot,
)


def _evidence(
    domain: StabilityDomain,
    *,
    available: bool = True,
    stability: int = 8_000,
    degradation: int = 2_000,
    recovery: int = 2_000,
    dislocation: int = 1_000,
) -> StabilityEvidence:
    return StabilityEvidence(
        domain=domain,
        evidence_available=available,
        stability_bps=stability,
        degradation_bps=degradation,
        recovery_bps=recovery,
        dislocation_bps=dislocation,
        evidence_refs=(f"stability:{domain.value}",),
    )


def test_missing_operational_evidence_stays_unknown() -> None:
    rows = tuple(
        _evidence(
            domain,
            available=domain not in {
                StabilityDomain.QORE_CORE,
                StabilityDomain.PROVIDER_BROKER,
            },
        )
        for domain in StabilityDomain
    )
    snapshot = build_stability_snapshot(rows)
    states = {item.domain: item.state for item in snapshot.channels}
    assert states[StabilityDomain.QORE_CORE] is StabilityState.UNKNOWN
    assert states[StabilityDomain.PROVIDER_BROKER] is StabilityState.UNKNOWN


def test_market_dislocation_is_descriptive_only() -> None:
    rows = tuple(
        _evidence(
            domain,
            dislocation=9_000 if domain is StabilityDomain.MARKET else 1_000,
        )
        for domain in StabilityDomain
    )
    snapshot = build_stability_snapshot(rows)
    market = next(
        item for item in snapshot.channels
        if item.domain is StabilityDomain.MARKET
    )
    assert market.state is StabilityState.DISLOCATION
    assert market.trading_command is False
    assert market.execution_authority is False


def test_snapshot_is_deterministic() -> None:
    rows = tuple(_evidence(domain) for domain in StabilityDomain)
    assert build_stability_snapshot(rows).fingerprint() == build_stability_snapshot(rows).fingerprint()
