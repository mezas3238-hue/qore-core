"""Independent qualitative G-M1..G-M5 certification authority for VT08 CRT PURE.

A methodology/cognition certificate is distinct from the economic/global gates
and cannot be bought by PnL, sizing, optimization or passing software tests.
No trading, broker connection or capital authority is granted here.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from qore.infrastructure.traders.crt_pure_three_source_methodology import (
    current_three_source_methodology,
)


class CrtPureMethodGateState(StrEnum):
    OPEN = "OPEN"
    PARTIAL = "PARTIAL"
    PASS = "PASS"


@dataclass(frozen=True, slots=True)
class CrtPureMethodGateEvidence:
    gate_id: str
    state: CrtPureMethodGateState
    audited_source_refs: tuple[str, ...] = ()
    independent_adjudicator: str | None = None
    no_future_leak_attested: bool = False
    sizing_used: bool = False

    def __post_init__(self) -> None:
        if self.gate_id not in ("G-M1", "G-M2", "G-M3", "G-M4"):
            raise ValueError("unknown G-M gate identifier")
        if self.sizing_used:
            raise ValueError("sizing is categorically forbidden in methodology/cognition")
        if self.state is CrtPureMethodGateState.PASS and (
            not self.audited_source_refs
            or not self.independent_adjudicator
            or not self.no_future_leak_attested
        ):
            raise ValueError("PASS requires source links, independent review, no leakage")


@dataclass(frozen=True, slots=True)
class CrtPureMethodCertificate:
    certificate_issued: bool
    blockers: tuple[str, ...]
    source_closed: bool
    gate_states: tuple[tuple[str, CrtPureMethodGateState], ...]
    broker_order_authorized: bool = False
    demo_authorized: bool = False
    live_authorized: bool = False
    volume_authorized: bool = False

    def __post_init__(self) -> None:
        if any((
            self.broker_order_authorized,
            self.demo_authorized,
            self.live_authorized,
            self.volume_authorized,
        )):
            raise ValueError("G-M5 certificate cannot grant order or capital authority")
        if self.certificate_issued != (self.source_closed and not self.blockers):
            raise ValueError("certificate must exactly match source and gate evidence")


def evaluate_methodological_gm5(
    gates: tuple[CrtPureMethodGateEvidence, ...],
) -> CrtPureMethodCertificate:
    """Complete G-M1..G-M4, with Owner-approved THREE-SOURCE CRT policy.

    This is not a Romeo-exclusive certificate. The current frozen composite
    still has seven open operational rules and cannot certify from fake flags.
    """
    expected = ("G-M1", "G-M2", "G-M3", "G-M4")
    if tuple(g.gate_id for g in gates) != expected:
        raise ValueError("G-M1 through G-M4 must be complete, ordered and unique")
    blockers = [
        f"{g.gate_id}_NOT_PASS:{g.state.value}"
        for g in gates if g.state is not CrtPureMethodGateState.PASS
    ]
    # Self-declared PASS is not an authenticated independent review.
    # Current gate evidence carries only free-text reviewer/ref claims and a
    # boolean no-leak statement; none can prove signer identity, SHA binding,
    # blinded review or independence. Refuse G-M5 until a trusted verifier is
    # designed and actually wired in (do not accept an injectable True flag).
    blockers.extend(
        f"{g.gate_id}_PASS_ATTESTATION_UNVERIFIED"
        for g in gates if g.state is CrtPureMethodGateState.PASS
    )
    source = current_three_source_methodology()
    blockers.extend(source.blockers)
    return CrtPureMethodCertificate(
        certificate_issued=not blockers,
        blockers=tuple(blockers),
        source_closed=source.methodology_closed,
        gate_states=tuple((g.gate_id, g.state) for g in gates),
    )

def present_vt08_gm5_status() -> CrtPureMethodCertificate:
    """A factual baseline; not a retrospective PASS by automated test suite."""
    return evaluate_methodological_gm5((
        CrtPureMethodGateEvidence("G-M1", CrtPureMethodGateState.PARTIAL),
        CrtPureMethodGateEvidence("G-M2", CrtPureMethodGateState.PARTIAL),
        CrtPureMethodGateEvidence("G-M3", CrtPureMethodGateState.PARTIAL),
        CrtPureMethodGateEvidence("G-M4", CrtPureMethodGateState.PARTIAL),
    ))
