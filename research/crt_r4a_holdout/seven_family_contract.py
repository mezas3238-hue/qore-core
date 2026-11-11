"""Seven distinct CRT *trade research* families plus original seven QA catalog roles.

PIN: R4-A Pine git blob 693e3f49719e86e2ea0702f7b355af33bd0c4c7c.
Original seven-category qaCatalogMask is not seven trade entries:
1 TRUE 3C, 2 pending 2C, 4 rejected expansion, 8 Inside return,
16 rejected Inside continuation, 32 Multi4/MultiN, 64 M15 retest.
Base ratified 2C RETURN is separately named by Pine entryFamily.

To pursue seven legitimate trade HYPOTHESES, preserve independent:
  two 2C MSS timing variants, TRUE3C, Inside return, Multi4, MultiN,
  and retest-M15. Candidate identity is NOT execution permission.

No broker/API/MT5/cTrader live or demo order capability in this file.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Iterable


class Family(str, Enum):
    TWO_C_MSS_C2 = "CRT_2C_RETURN_MSS15_IN_C2"
    TWO_C_MSS_C3 = "CRT_2C_RETURN_MSS15_IN_C3"
    TRUE_3C = "CRT_TRUE3C_MSS5"
    INSIDE_RETURN = "CRT_INSIDE_RETURN"
    MULTI4 = "CRT_MULTI4"
    MULTIN = "CRT_MULTI_N"
    M15_RETEST = "CRT_M15_RETEST"


class Readiness(str, Enum):
    # Explicitly separate usable QA events from permission to place orders.
    NOT_IMPLEMENTED = "NOT_IMPLEMENTED"
    DETECTOR_RESEARCH_ONLY = "DETECTOR_RESEARCH_ONLY"
    INVALID_PROVISIONAL = "INVALID_PROVISIONAL"


@dataclass(frozen=True)
class FamilySpecification:
    family: Family
    pine_source: str
    catalog_bit: int | None
    geometry: str
    mss_ownership: str
    earliest_legal_signal: str
    readiness: Readiness
    requires_independent_strategy_spec: bool = True
    requires_original_pine_parity: bool = True
    requires_net_cost_testing: bool = True


FAMILY_SPECS = (
    FamilySpecification(
        Family.TWO_C_MSS_C2,
        "entryFamily='CRT 3C REV MSS C2' (Pine L2113–2120)",
        None, "C1/C2 strict single sweep; C2 H4 closed",
        "Own pre-C2-sweep confirmed M15 pivot and M15 cross in C2",
        "C2 H4 close (never earlier)",
        Readiness.DETECTOR_RESEARCH_ONLY,
    ),
    FamilySpecification(
        Family.TWO_C_MSS_C3,
        "entryFamily='CRT 3C REV MSS C3' (Pine L2113–2120)",
        None, "C1/C2 strict single sweep; C2 H4 closed",
        "Own pre-C2-sweep confirmed M15 pivot; M15 cross in C3",
        "Own MSS M15 close after C2 ratification",
        Readiness.DETECTOR_RESEARCH_ONLY,
    ),
    FamilySpecification(
        Family.TRUE_3C,
        "categoryTrue3C bit 1, qaTrue3CConfirmed (L1342–1379, L2277–80)",
        1, "C1; C2 strictly inside C1; C3 sweeps C1 and closes inside",
        "Own pre-C3-sweep confirmed M5 pivot and M5 close crossover",
        "C3 H4 close (never during C3)",
        Readiness.DETECTOR_RESEARCH_ONLY,
    ),
    FamilySpecification(
        Family.INSIDE_RETURN,
        "categoryInsideReturn bit 8, InsideCandidate (L2142–80, L2279–87)",
        8, "C1/C2 strict inside; terminal H4 single sweep of C2, returns",
        "Own pre-sweep M5 or M15 confirmed pivot; not copied from base CRT",
        "Terminal inside-return H4 ratification plus own MSS close",
        Readiness.NOT_IMPLEMENTED,
    ),
    FamilySpecification(
        Family.MULTI4,
        "categoryMultiCandle bit 32, Multi4 (L1259–1325)",
        32, "C1 / C2a / C2b / C3 distributed reversal, 4 closed H4",
        "Own C2a pre-sweep M5/M15 pivot and owned close crossover",
        "C3 H4 close plus independent owned confirmation",
        Readiness.NOT_IMPLEMENTED,
    ),
    FamilySpecification(
        Family.MULTIN,
        "categoryMultiCandle bit 32, Multi-N (L1385–1457)",
        32, "C1, 2–5 strict-inside consolidation H4, terminal one-sided sweep",
        "Own terminal sweep and independent M5/M15 pivot/crossover",
        "Terminal H4 close plus independent owned confirmation",
        Readiness.NOT_IMPLEMENTED,
    ),
    FamilySpecification(
        Family.M15_RETEST,
        "categoryM15Retest bit 64 (L1100–1127, L2134–40)",
        64, "Previously ratified 2C CRT with own M15 MSS; retest in <=4h",
        "Same CRT id, source MSS timestamp and source M15 pivot",
        "Closed complete M15 retest after source MSS",
        Readiness.NOT_IMPLEMENTED,
    ),
)

_BY_FAMILY = {spec.family: spec for spec in FAMILY_SPECS}
assert len(FAMILY_SPECS) == 7 and len(_BY_FAMILY) == 7

# These are exactly the SEVEN legacy catalog categories displayed in Pine QA.
# They are deliberately not falsely described as seven profitable strategies.
PINE_CATALOG_BITS = {
    1: "TRUE3C_CONFIRMED",
    2: "2C_PENDING_NON_ENTRY",
    4: "2C_EXPANSION_REJECTED_NON_ENTRY",
    8: "INSIDE_RETURN_QA",
    16: "INSIDE_CONTINUATION_REJECTED_NON_ENTRY",
    32: "MULTICANDLE_QA",
    64: "M15_RETEST_QA",
}
NON_TRADABLE_CATALOG = frozenset((2, 4, 16))


def catalog_labels(mask: int) -> tuple[str, ...]:
    """Decode original qaCatalogMask only; no false execution authority."""
    if not isinstance(mask, int) or isinstance(mask, bool) or not 0 <= mask < 128:
        raise ValueError("invalid original seven-category Pine bit mask")
    return tuple(
        PINE_CATALOG_BITS[bit] for bit in PINE_CATALOG_BITS if mask & bit
    )


def research_family_from_base_event(
    *, model: str, mss_at: datetime, ratified_at: datetime
) -> Family:
    """Split already observed A/B events into 2C-C2, 2C-C3, TRUE3C."""
    if mss_at.tzinfo is None or ratified_at.tzinfo is None:
        raise ValueError("UTC-offset-aware time required")
    if model == "A_2C_MSS15":
        return (
            Family.TWO_C_MSS_C2
            if mss_at <= ratified_at else Family.TWO_C_MSS_C3
        )
    if model == "B_TRUE3C_MSS5":
        if mss_at > ratified_at:
            raise ValueError("TRUE 3C future-lookahead: MSS after C3 close")
        return Family.TRUE_3C
    raise ValueError("unknown or unsupported base source model")


@dataclass(frozen=True)
class Certification:
    """Fail-closed authority for research accounting, not placing orders."""
    family: Family
    detector_implemented: bool = False
    original_pine_parity: bool = False
    provider_market_parity: bool = False
    own_mss_confirmed: bool = False
    entry_stop_take_profit_frozen: bool = False
    bid_ask_costs_verified: bool = False
    unseen_24_months_attested: bool = False
    broker_execution_permissions: bool = False

    @property
    def can_simulate_certified_trades(self) -> bool:
        # Even an all-green certification record cannot authorize broker
        # transactions from the QA research module itself.
        return all((
            self.detector_implemented,
            self.original_pine_parity,
            self.provider_market_parity,
            self.own_mss_confirmed,
            self.entry_stop_take_profit_frozen,
            self.bid_ask_costs_verified,
            self.unseen_24_months_attested,
        ))

    @property
    def can_place_orders(self) -> bool:
        # No broker interface/authority exists in this research branch.
        return False


def readiness_summary(certifications: Iterable[Certification]) -> dict:
    certs = list(certifications)
    if {c.family for c in certs} != set(Family) or len(certs) != 7:
        raise ValueError("7 unique individual family certifications required")
    return {
        "expected_trade_research_families": 7,
        "families": {
            c.family.value: {
                "detector_implemented": c.detector_implemented,
                "qualified_for_certified_simulation": c.can_simulate_certified_trades,
                "eligible_for_broker_execution": c.can_place_orders,
                "default_readiness": _BY_FAMILY[c.family].readiness.value,
            }
            for c in certs
        },
        "broker_orders_executed": 0,
        "no_live_or_demo_execution": True,
    }
