"""VT08 FINAL #1: outcome-blind, one-family, three-final-verdict gate.

Research-only pure validation contract. Never opens orders or reads holdout.
A source-cited rule is NOT a causal selector. A discretionary selector can be
evaluated only with predecision market snapshots and 2 blinded independent
annotations, documented as QORE-C reproducibility control, never as TTrades-A
algorithm. The final decision is GO, NO_GO or NO_EVALUABLE; interim states
have separate names, no performance inference.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from enum import StrEnum

FAMILY = "BULLISH_M30_C2_REVERSAL_M3_CISD_C3_POSITIONAL"
MARKETS = frozenset(("EURJPY", "USDCHF", "NZDUSD", "CADJPY", "USDCAD"))
MIN_FILLS = 100
PF_GO_THRESHOLD = Decimal("1.15")
REQUIRED_SOURCE_FIELDS = frozenset((
    "HTF_BIAS_KNOWN_PRE_C2",
    "RELEVANT_SWING_REFERENCE_PRE_C2",
    "RELEVANT_POI_PRE_C2",
    "C2_CLOSURE_AND_M3_CISD_PS_ASOF",
    "C2_EQ_REGIME_CONFIRMED",
    "BREAKER_LOW_AUTHENTICATED",
    "STOP_BELOW_BOTH_EQ_AND_BREAKER",
    "EXTERNAL_TARGET_UNTOUCHED_ASOF",
    "C3_POSITIONAL_OPEN_AND_ORDER_CLOCK",
))
REQUIRED_VALIDATION_FIELDS = frozenset((
    "FIVE_MARKETS_FIXED",
    "INDEPENDENT_TIME_SPLIT",
    "REPRODUCIBLE_BID_ASK_AND_FEES",
    "A_B_SIGNED_MANIFEST_SHA256",
))


class FinalVerdict(StrEnum):
    GO = "GO"
    NO_GO = "NO_GO"
    NO_EVALUABLE = "NO_EVALUABLE"


class InterimState(StrEnum):
    PENDING_SOURCE = "PENDING_SOURCE_NOT_FINAL"
    READY_FOR_ONE_INDEPENDENT_TEST = "READY_FOR_ONE_INDEPENDENT_TEST_NOT_FINAL"


class SelectorMethod(StrEnum):
    DETERMINISTIC_ASOF = "DETERMINISTIC_ASOF_QORE_C"
    BLINDED_DISCRETIONARY_ASOF = "BLINDED_DISCRETIONARY_ASOF_QORE_C"
    UNRESOLVED = "UNRESOLVED_D"


@dataclass(frozen=True, slots=True)
class RuleReceipt:
    """Source category and selector are independent.

    Two reviewers can rate identical REDACTED-OUTCOME snapshots, before
    market outcome is read, but this is a QORE C approximation and cannot
    be misrepresented as a deterministic TTrades author A rule.
    """

    key: str
    source_uri: str
    source_class: str
    selector_method: SelectorMethod
    known_at: datetime | None
    decision_at: datetime | None
    source_snapshot_sha256: str | None
    verifier_sha256: str | None
    reviewer1_id: str | None = None
    reviewer2_id: str | None = None
    reviewer1_annotation_sha256: str | None = None
    reviewer2_annotation_sha256: str | None = None
    reviewers_agree: bool = False

    def validated(self) -> bool:
        if self.key not in REQUIRED_SOURCE_FIELDS:
            return False
        if self.source_class != "A_WRITTEN":
            return False
        if not self.source_uri.startswith("https://ttrades.com/"):
            return False
        if not all((
            self.known_at,
            self.decision_at,
            _sha256(self.source_snapshot_sha256),
            _sha256(self.verifier_sha256),
        )):
            return False
        if self.known_at.utcoffset() is None or self.decision_at.utcoffset() is None:
            return False
        if self.known_at.astimezone(UTC) > self.decision_at.astimezone(UTC):
            return False
        if self.selector_method == SelectorMethod.DETERMINISTIC_ASOF:
            return True
        if self.selector_method != SelectorMethod.BLINDED_DISCRETIONARY_ASOF:
            return False
        return bool(
            self.reviewers_agree
            and self.reviewer1_id
            and self.reviewer2_id
            and self.reviewer1_id != self.reviewer2_id
            and _sha256(self.reviewer1_annotation_sha256)
            and _sha256(self.reviewer2_annotation_sha256)
        )


def _sha256(text: str | None) -> bool:
    return bool(text and len(text) == 64 and all(x in "0123456789abcdef" for x in text))


@dataclass(frozen=True, slots=True)
class Final1Preflight:
    receipts: tuple[RuleReceipt, ...]
    validation_evidence: frozenset[str]
    manifest_a_sha256: str | None = None
    manifest_b_sha256: str | None = None
    independent_period_sha256: str | None = None
    broker_quote_and_fee_source_sha256: str | None = None

    def blockers(self) -> tuple[str, ...]:
        valid_receipts = {r.key for r in self.receipts if r.validated()}
        blocked = {
            f"UNRESOLVED_SOURCE_OR_CAUSAL_{key}"
            for key in REQUIRED_SOURCE_FIELDS - valid_receipts
        }
        names = [r.key for r in self.receipts]
        if len(set(names)) != len(names):
            blocked.add("DUPLICATE_SOURCE_RECEIPTS")
        blocked.update(
            f"UNVERIFIED_{k}" for k in
            REQUIRED_VALIDATION_FIELDS - self.validation_evidence
        )
        if not _sha256(self.manifest_a_sha256):
            blocked.add("A_MANIFEST_UNSIGNED")
        if not _sha256(self.manifest_b_sha256):
            blocked.add("B_MANIFEST_UNSIGNED")
        if not _sha256(self.independent_period_sha256):
            blocked.add("INDEPENDENT_PERIOD_UNVERIFIED")
        if not _sha256(self.broker_quote_and_fee_source_sha256):
            blocked.add("BID_ASK_FEES_UNVERIFIED")
        return tuple(sorted(blocked))


@dataclass(frozen=True, slots=True)
class VerifiedEconomicEvidence:
    family: str
    markets: frozenset[str]
    fills: int
    gross_profit_net_of_costs_r: Decimal
    gross_loss_net_of_costs_r: Decimal
    net_expectancy_per_fill_r: Decimal
    total_entry_decisions: int
    event_history_sha256: str
    independent_broker_executions_sha256: str

    def provenance_ok(self) -> bool:
        return bool(
            self.family == FAMILY
            and self.markets == MARKETS
            and self.fills >= 0
            and self.total_entry_decisions >= self.fills
            and self.gross_profit_net_of_costs_r >= 0
            and self.gross_loss_net_of_costs_r >= 0
            and _sha256(self.event_history_sha256)
            and _sha256(self.independent_broker_executions_sha256)
        )


@dataclass(frozen=True, slots=True)
class Final1Decision:
    status: FinalVerdict | InterimState
    reasons: tuple[str, ...]
    profit_factor_net: str | None
    fills: int | None
    research_only: bool = True
    live_orders_authorized: bool = False
    sealed_holdout_access_authorized: bool = False


def final1_decision(
    *,
    source: Final1Preflight,
    source_adjudication_closed: bool,
    economic: VerifiedEconomicEvidence | None,
) -> Final1Decision:
    """No status promotion from measured PF if source chain is D or unverified."""
    blockers = source.blockers()
    if blockers:
        return Final1Decision(
            status=(
                FinalVerdict.NO_EVALUABLE
                if source_adjudication_closed else InterimState.PENDING_SOURCE
            ),
            reasons=blockers, profit_factor_net=None, fills=None,
        )
    if economic is None:
        if source_adjudication_closed:
            # SOURCE completeness allows a single test, not result fabrication.
            return Final1Decision(
                InterimState.READY_FOR_ONE_INDEPENDENT_TEST,
                ("INDEPENDENT_ECONOMIC_TEST_NOT_PERFORMED",), None, None,
            )
        return Final1Decision(
            InterimState.READY_FOR_ONE_INDEPENDENT_TEST,
            ("INDEPENDENT_ECONOMIC_TEST_NOT_PERFORMED",), None, None,
        )
    if not economic.provenance_ok():
        return Final1Decision(
            FinalVerdict.NO_EVALUABLE, ("ECONOMIC_PROVENANCE_INVALID",), None,
            economic.fills,
        )
    if economic.fills < MIN_FILLS:
        return Final1Decision(
            FinalVerdict.NO_EVALUABLE, ("FEWER_THAN_100_VERIFIABLE_FILLS",),
            None, economic.fills,
        )
    if economic.gross_loss_net_of_costs_r <= 0:
        return Final1Decision(
            FinalVerdict.NO_EVALUABLE, ("NO_FINITE_PROFIT_FACTOR",),
            None, economic.fills,
        )
    pf = economic.gross_profit_net_of_costs_r / economic.gross_loss_net_of_costs_r
    if pf > PF_GO_THRESHOLD and economic.net_expectancy_per_fill_r > 0:
        return Final1Decision(FinalVerdict.GO, (), str(pf), economic.fills)
    return Final1Decision(
        FinalVerdict.NO_GO,
        ("PF_NOT_ABOVE_1_15_OR_EXPECTANCY_NON_POSITIVE",),
        str(pf), economic.fills,
    )


def long_stop_below_two_verified_levels(
    *,
    eq: Decimal,
    breaker_low: Decimal,
    stop: Decimal,
    broker_tick: Decimal,
) -> bool:
    """Below BOTH = below min(EQ, breaker); precise tick is QORE execution C.

    This predicate does NOT verify provenance or author selection of levels.
    """
    if min(eq, breaker_low, stop, broker_tick) <= 0:
        raise ValueError("source prices and broker tick must be positive")
    return stop <= min(eq, breaker_low) - broker_tick
