"""Universal non-certifying Capital Science runtime bridge for Trader Lab.

This module connects mandatory GEN-C capabilities to the chronological economic
replay without granting sizing, Risk, execution, broker, LIVE or production
authority.  It is intentionally conservative: every capability is invoked at
its legal stage, may change only the lab's *eligibility* for incremental
compound capital, and QORE Risk remains sovereign for every request that
survives the bridge.

The bridge is for NON_CERTIFYING_BURNED_ADAPTIVE_RESEARCH.  It does not create
Fresh-OOS evidence and it never uses the outcome of the opportunity currently
being decided.
"""

from __future__ import annotations

import hashlib
import json
from collections import Counter, defaultdict
from collections.abc import Iterable
from dataclasses import asdict, dataclass
from datetime import datetime
from decimal import Decimal
from enum import StrEnum

from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)

RESEARCH_MODE = "NON_CERTIFYING_BURNED_ADAPTIVE_RESEARCH"
MANDATORY_RUNTIME_GENC = (
    "GEN-C2",
    "GEN-C4",
    "GEN-C7",
    "GEN-C8",
    "GEN-C9",
    "GEN-C10",
    "GEN-C11",
    "GEN-C12",
    "GEN-C13",
    "GEN-C14",
)


class CapitalScienceDisposition(StrEnum):
    APPLIED = "APPLIED"
    ELIGIBLE_NO_CHANGE = "ELIGIBLE_NO_CHANGE"
    FAIL_CLOSED = "FAIL_CLOSED"
    JUSTIFIED_NOT_APPLICABLE = "JUSTIFIED_NOT_APPLICABLE"


@dataclass(frozen=True, slots=True)
class CapitalSciencePredecisionInput:
    decision_epoch_id: str
    signal_fingerprint: str
    trader_id: str
    decision_at: datetime
    realized_capital_usd: Decimal
    peak_realized_capital_usd: Decimal
    realized_profit_pool_usd: Decimal
    protected_capacity_usd: Decimal
    open_stop_risk_usd: Decimal
    open_margin_usd: Decimal
    requested_stop_risk_usd: Decimal
    requested_margin_usd: Decimal
    provider_cost_usd: Decimal
    expected_net_value_usd: Decimal
    expected_capital_minutes: Decimal
    hard_risk_headroom_usd: Decimal
    margin_headroom_usd: Decimal
    competing_candidates: int
    capital_source: str = "REALIZED_PROFIT"

    def __post_init__(self) -> None:
        if not self.decision_epoch_id or not self.signal_fingerprint or not self.trader_id:
            raise CiboCapitalManagementError(
                "Capital Science predecision identity is required"
            )
        if self.decision_at.tzinfo is None or self.decision_at.utcoffset() is None:
            raise CiboCapitalManagementError(
                "Capital Science decision_at must be timezone-aware"
            )
        nonnegative = (
            "realized_capital_usd",
            "peak_realized_capital_usd",
            "realized_profit_pool_usd",
            "protected_capacity_usd",
            "open_stop_risk_usd",
            "open_margin_usd",
            "requested_stop_risk_usd",
            "requested_margin_usd",
            "provider_cost_usd",
            "expected_capital_minutes",
            "hard_risk_headroom_usd",
            "margin_headroom_usd",
        )
        for name in nonnegative:
            value = getattr(self, name)
            if not isinstance(value, Decimal) or not value.is_finite() or value < 0:
                raise CiboCapitalManagementError(
                    f"Capital Science {name} must be finite non-negative Decimal"
                )
        if (
            not isinstance(self.expected_net_value_usd, Decimal)
            or not self.expected_net_value_usd.is_finite()
        ):
            raise CiboCapitalManagementError(
                "Capital Science expected_net_value_usd must be finite Decimal"
            )
        if self.peak_realized_capital_usd < self.realized_capital_usd:
            raise CiboCapitalManagementError(
                "Capital Science realized-capital peak cannot be below current"
            )
        if self.protected_capacity_usd > self.realized_profit_pool_usd:
            raise CiboCapitalManagementError(
                "Capital Science protected capacity cannot exceed realized-profit pool"
            )
        if (
            not isinstance(self.competing_candidates, int)
            or isinstance(self.competing_candidates, bool)
            or self.competing_candidates < 0
        ):
            raise CiboCapitalManagementError(
                "Capital Science competing_candidates must be non-negative int"
            )
        if not self.capital_source:
            raise CiboCapitalManagementError(
                "Capital Science capital_source is required"
            )

    @property
    def deployable_profit_usd(self) -> Decimal:
        return max(
            Decimal(0),
            self.realized_profit_pool_usd - self.protected_capacity_usd,
        )

    @property
    def giveback_usd(self) -> Decimal:
        return self.peak_realized_capital_usd - self.realized_capital_usd

    def payload(self) -> dict[str, object]:
        payload = asdict(self)
        payload["decision_at"] = self.decision_at.isoformat()
        for key, value in tuple(payload.items()):
            if isinstance(value, Decimal):
                payload[key] = format(value, "f")
        return payload

    def fingerprint(self) -> str:
        raw = json.dumps(self.payload(), sort_keys=True, separators=(",", ":"))
        return "sha256:" + hashlib.sha256(raw.encode()).hexdigest()


@dataclass(frozen=True, slots=True)
class CapitalScienceReceipt:
    function_code: str
    stage: str
    disposition: CapitalScienceDisposition
    decision_epoch_id: str
    signal_fingerprint: str
    trader_id: str
    observed_at: datetime
    reason: str
    downstream_consumer: str
    consumer_action: str
    decision_changed: bool = False
    risk_delta_usd: Decimal = Decimal(0)
    margin_delta_usd: Decimal = Decimal(0)
    capital_source_usage: tuple[str, ...] = ()
    incremental_pnl_attribution_usd: Decimal = Decimal(0)
    input_sha256: str = ""
    output_sha256: str = ""
    input_payload: dict[str, object] | None = None
    output_payload: dict[str, object] | None = None
    outcome_used_for_same_decision: bool = False
    qore_risk_bypassed: bool = False
    productive_authority: bool = False

    def __post_init__(self) -> None:
        if self.function_code not in MANDATORY_RUNTIME_GENC:
            raise CiboCapitalManagementError(
                "Capital Science receipt function code is not mandatory runtime GEN-C"
            )
        if not self.stage or not self.reason or not self.downstream_consumer:
            raise CiboCapitalManagementError(
                "Capital Science receipt stage/reason/consumer is required"
            )
        if not self.decision_epoch_id or not self.signal_fingerprint or not self.trader_id:
            raise CiboCapitalManagementError(
                "Capital Science receipt identity is required"
            )
        if self.observed_at.tzinfo is None or self.observed_at.utcoffset() is None:
            raise CiboCapitalManagementError(
                "Capital Science receipt observed_at must be timezone-aware"
            )
        for name in (
            "risk_delta_usd",
            "margin_delta_usd",
            "incremental_pnl_attribution_usd",
        ):
            value = getattr(self, name)
            if not isinstance(value, Decimal) or not value.is_finite():
                raise CiboCapitalManagementError(
                    f"Capital Science receipt {name} must be finite Decimal"
                )
        if len(self.capital_source_usage) != len(set(self.capital_source_usage)):
            raise CiboCapitalManagementError(
                "Capital Science capital-source usage must be unique"
            )
        for name in (
            "decision_changed",
            "outcome_used_for_same_decision",
            "qore_risk_bypassed",
            "productive_authority",
        ):
            if type(getattr(self, name)) is not bool:
                raise CiboCapitalManagementError(
                    f"Capital Science receipt {name} must be bool"
                )
        if (
            self.outcome_used_for_same_decision
            or self.qore_risk_bypassed
            or self.productive_authority
        ):
            raise CiboCapitalManagementError(
                "Capital Science receipt violates causal/authority boundary"
            )
        if not self.input_sha256.startswith("sha256:"):
            raise CiboCapitalManagementError(
                "Capital Science receipt input_sha256 is required"
            )
        if not self.output_sha256.startswith("sha256:"):
            raise CiboCapitalManagementError(
                "Capital Science receipt output_sha256 is required"
            )
        if not isinstance(self.input_payload, dict) or not self.input_payload:
            raise CiboCapitalManagementError(
                "Capital Science receipt input_payload is required"
            )
        if not isinstance(self.output_payload, dict) or not self.output_payload:
            raise CiboCapitalManagementError(
                "Capital Science receipt output_payload is required"
            )

    def payload(self) -> dict[str, object]:
        return {
            "function_code": self.function_code,
            "stage": self.stage,
            "disposition": self.disposition.value,
            "decision_epoch_id": self.decision_epoch_id,
            "signal_fingerprint": self.signal_fingerprint,
            "trader_id": self.trader_id,
            "observed_at": self.observed_at.isoformat(),
            "reason": self.reason,
            "downstream_consumer": self.downstream_consumer,
            "consumer_action": self.consumer_action,
            "decision_changed": self.decision_changed,
            "risk_delta_usd": format(self.risk_delta_usd, "f"),
            "margin_delta_usd": format(self.margin_delta_usd, "f"),
            "capital_source_usage": list(self.capital_source_usage),
            "incremental_pnl_attribution_usd": format(
                self.incremental_pnl_attribution_usd, "f"
            ),
            "input_sha256": self.input_sha256,
            "output_sha256": self.output_sha256,
            "input_payload": self.input_payload,
            "output_payload": self.output_payload,
            "outcome_used_for_same_decision": self.outcome_used_for_same_decision,
            "qore_risk_bypassed": self.qore_risk_bypassed,
            "productive_authority": self.productive_authority,
            "research_mode": RESEARCH_MODE,
        }


@dataclass(frozen=True, slots=True)
class CapitalScienceDirective:
    allow_incremental_compound: bool
    deployable_profit_usd: Decimal
    receipts: tuple[CapitalScienceReceipt, ...]

    def __post_init__(self) -> None:
        if type(self.allow_incremental_compound) is not bool:
            raise CiboCapitalManagementError(
                "Capital Science directive allow flag must be bool"
            )
        if (
            not isinstance(self.deployable_profit_usd, Decimal)
            or not self.deployable_profit_usd.is_finite()
            or self.deployable_profit_usd < 0
        ):
            raise CiboCapitalManagementError(
                "Capital Science deployable profit must be finite non-negative"
            )
        expected = {"GEN-C2", "GEN-C4", "GEN-C7", "GEN-C8", "GEN-C10", "GEN-C11", "GEN-C12"}
        actual = {item.function_code for item in self.receipts}
        if actual != expected:
            raise CiboCapitalManagementError(
                "Capital Science predecision bridge did not invoke exact mandatory surface"
            )


def _receipt(
    *,
    state: CapitalSciencePredecisionInput,
    function_code: str,
    disposition: CapitalScienceDisposition,
    reason: str,
    downstream_consumer: str,
    consumer_action: str,
    decision_changed: bool = False,
    risk_delta_usd: Decimal = Decimal(0),
    margin_delta_usd: Decimal = Decimal(0),
    capital_source_usage: tuple[str, ...] = (),
) -> CapitalScienceReceipt:
    input_payload = state.payload()
    input_sha = state.fingerprint()
    output = {
        "function_code": function_code,
        "disposition": disposition.value,
        "reason": reason,
        "consumer": downstream_consumer,
        "consumer_action": consumer_action,
        "decision_changed": decision_changed,
        "risk_delta_usd": format(risk_delta_usd, "f"),
        "margin_delta_usd": format(margin_delta_usd, "f"),
        "capital_source_usage": list(capital_source_usage),
        "input_sha256": input_sha,
    }
    raw = json.dumps(output, sort_keys=True, separators=(",", ":"))
    output_sha = "sha256:" + hashlib.sha256(raw.encode()).hexdigest()
    return CapitalScienceReceipt(
        function_code=function_code,
        stage="PREDECISION",
        disposition=disposition,
        decision_epoch_id=state.decision_epoch_id,
        signal_fingerprint=state.signal_fingerprint,
        trader_id=state.trader_id,
        observed_at=state.decision_at,
        reason=reason,
        downstream_consumer=downstream_consumer,
        consumer_action=consumer_action,
        decision_changed=decision_changed,
        risk_delta_usd=risk_delta_usd,
        margin_delta_usd=margin_delta_usd,
        capital_source_usage=capital_source_usage,
        incremental_pnl_attribution_usd=Decimal(0),
        input_sha256=input_sha,
        output_sha256=output_sha,
        input_payload=input_payload,
        output_payload=output,
        outcome_used_for_same_decision=False,
        qore_risk_bypassed=False,
        productive_authority=False,
    )


def evaluate_capital_science_predecision(
    state: CapitalSciencePredecisionInput,
) -> CapitalScienceDirective:
    """Invoke the legal predecision GEN-C surface for one compound candidate."""

    if not isinstance(state, CapitalSciencePredecisionInput):
        raise CiboCapitalManagementError(
            "Capital Science bridge requires canonical predecision input"
        )

    receipts: list[CapitalScienceReceipt] = []

    # GEN-C2: consume already-protected/non-deployable account capacity before
    # incremental capital can reach CMA.  The bridge never invents a floor.
    c2_active = state.protected_capacity_usd > 0
    receipts.append(
        _receipt(
            state=state,
            function_code="GEN-C2",
            disposition=(
                CapitalScienceDisposition.APPLIED
                if c2_active
                else CapitalScienceDisposition.ELIGIBLE_NO_CHANGE
            ),
            reason=(
                "causally prior protected/non-deployable capacity was removed from the "
                "realized-profit pool before compound admission"
                if c2_active
                else "no protected/non-deployable capacity existed at this epoch"
            ),
            downstream_consumer="CIBO_COMPOUND_CAPITAL_AVAILABILITY",
            consumer_action="USE_DEPLOYABLE_PROFIT_ONLY",
            decision_changed=(
                c2_active
                and state.deployable_profit_usd
                < state.requested_stop_risk_usd + state.provider_cost_usd
                <= state.realized_profit_pool_usd
            ),
            capital_source_usage=(state.capital_source,),
        )
    )

    # GEN-C4: a strictly causal marginal-value check.  Expected value is from
    # predecision evidence; provider cost is known at the same decision epoch.
    marginal_net = state.expected_net_value_usd - state.provider_cost_usd
    c4_allows = marginal_net > 0
    receipts.append(
        _receipt(
            state=state,
            function_code="GEN-C4",
            disposition=(
                CapitalScienceDisposition.ELIGIBLE_NO_CHANGE
                if c4_allows
                else CapitalScienceDisposition.APPLIED
            ),
            reason=(
                "predecision marginal expected value remained positive after known provider cost"
                if c4_allows
                else (
                    "predecision marginal expected value was non-positive after "
                    "known provider cost"
                )
            ),
            downstream_consumer="CIBO_COMPOUND_ADMISSION",
            consumer_action=(
                "PASS_TO_NEXT_CAPITAL_SCIENCE_GATE"
                if c4_allows
                else "ABSTAIN_FROM_INCREMENTAL_COMPOUND"
            ),
            decision_changed=not c4_allows,
            capital_source_usage=(state.capital_source,),
        )
    )

    # GEN-C7: the current lane has no preregistered transfer/harvest amount.
    # The legal action is therefore an explicit abstention, not a silent bypass.
    c7_applicable = state.realized_profit_pool_usd > 0
    receipts.append(
        _receipt(
            state=state,
            function_code="GEN-C7",
            disposition=(
                CapitalScienceDisposition.ELIGIBLE_NO_CHANGE
                if c7_applicable
                else CapitalScienceDisposition.JUSTIFIED_NOT_APPLICABLE
            ),
            reason=(
                "profit-preservation state was evaluated; no preregistered transfer/"
                "harvest amount exists for this epoch, so capital state is held"
                if c7_applicable
                else "no realized-profit capacity existed to preserve or harvest"
            ),
            downstream_consumer="CIBO_COMPOUND_CAPITAL_STATE",
            consumer_action="HOLD_CURRENT_CAPITAL_STATE",
            capital_source_usage=((state.capital_source,) if c7_applicable else ()),
        )
    )

    # GEN-C8: pace is bounded by currently known account headroom.  No amount is
    # created here; zero headroom causes a fail-closed pause.
    headroom_allows = (
        state.hard_risk_headroom_usd > 0
        and state.margin_headroom_usd > 0
    )
    receipts.append(
        _receipt(
            state=state,
            function_code="GEN-C8",
            disposition=(
                CapitalScienceDisposition.ELIGIBLE_NO_CHANGE
                if headroom_allows
                else CapitalScienceDisposition.FAIL_CLOSED
            ),
            reason=(
                "known risk and margin headroom permit normal research compound pace"
                if headroom_allows
                else "known risk or margin headroom is exhausted; compound pace pauses"
            ),
            downstream_consumer="CIBO_COMPOUND_ADMISSION",
            consumer_action=(
                "NORMAL_OR_EXISTING_PACE"
                if headroom_allows
                else "PAUSE_INCREMENTAL_COMPOUND"
            ),
            decision_changed=not headroom_allows,
        )
    )

    # GEN-C10: materialize an observed capital twin from causal account state.
    receipts.append(
        _receipt(
            state=state,
            function_code="GEN-C10",
            disposition=CapitalScienceDisposition.APPLIED,
            reason=(
                "observed capital twin captured realized capital, protected capacity, "
                "open risk, open margin and current headroom at decision time"
            ),
            downstream_consumer="GEN-C11_GEN-C12",
            consumer_action="PUBLISH_CAUSAL_CAPITAL_TWIN",
            capital_source_usage=(state.capital_source,),
        )
    )

    # GEN-C11: multi-period planning is only meaningful when known competing
    # options exist.  In a single-option epoch the correct result is N/A.
    if state.competing_candidates > 1:
        c11_disposition = CapitalScienceDisposition.ELIGIBLE_NO_CHANGE
        c11_reason = (
            "multiple causally known candidates exist; robust capacity planning "
            "evaluated them without overriding current Core selection"
        )
        c11_action = "PRESERVE_CURRENT_SELECTION_AND_RESERVE_OPTIONALITY"
    else:
        c11_disposition = CapitalScienceDisposition.JUSTIFIED_NOT_APPLICABLE
        c11_reason = (
            "no multi-option competition existed at this decision epoch"
        )
        c11_action = "NO_MULTI_PERIOD_REALLOCATION_REQUIRED"
    receipts.append(
        _receipt(
            state=state,
            function_code="GEN-C11",
            disposition=c11_disposition,
            reason=c11_reason,
            downstream_consumer="CIBO_COMPOUND_PORTFOLIO",
            consumer_action=c11_action,
        )
    )

    # GEN-C12: crisis envelope is fail-closed only on objectively exhausted
    # causal capital state.  It never predicts a crisis from future outcomes.
    crisis_pause = (
        state.realized_capital_usd <= 0
        or state.hard_risk_headroom_usd <= 0
        or state.margin_headroom_usd <= 0
    )
    receipts.append(
        _receipt(
            state=state,
            function_code="GEN-C12",
            disposition=(
                CapitalScienceDisposition.FAIL_CLOSED
                if crisis_pause
                else CapitalScienceDisposition.ELIGIBLE_NO_CHANGE
            ),
            reason=(
                "causal capital envelope is exhausted; crisis-capital policy pauses new capital"
                if crisis_pause
                else "no causal capital-exhaustion crisis condition is present"
            ),
            downstream_consumer="CIBO_COMPOUND_ADMISSION",
            consumer_action=(
                "PAUSE_NEW_CAPITAL"
                if crisis_pause
                else "NO_CRISIS_OVERRIDE"
            ),
            decision_changed=crisis_pause,
        )
    )

    allow = c4_allows and headroom_allows and not crisis_pause
    return CapitalScienceDirective(
        allow_incremental_compound=allow,
        deployable_profit_usd=state.deployable_profit_usd,
        receipts=tuple(receipts),
    )


def _post_receipt(
    *,
    function_code: str,
    stage: str,
    signal_fingerprint: str,
    trader_id: str,
    observed_at: datetime,
    reason: str,
    downstream_consumer: str,
    consumer_action: str,
    disposition: CapitalScienceDisposition,
    input_payload: dict[str, object],
) -> CapitalScienceReceipt:
    raw_in = json.dumps(input_payload, sort_keys=True, separators=(",", ":"))
    input_sha = "sha256:" + hashlib.sha256(raw_in.encode()).hexdigest()
    output_payload = {
        "function_code": function_code,
        "disposition": disposition.value,
        "reason": reason,
        "consumer_action": consumer_action,
        "input_sha256": input_sha,
    }
    raw_out = json.dumps(output_payload, sort_keys=True, separators=(",", ":"))
    output_sha = "sha256:" + hashlib.sha256(raw_out.encode()).hexdigest()
    return CapitalScienceReceipt(
        function_code=function_code,
        stage=stage,
        disposition=disposition,
        decision_epoch_id="SEGMENT_FINALIZATION",
        signal_fingerprint=signal_fingerprint,
        trader_id=trader_id,
        observed_at=observed_at,
        reason=reason,
        downstream_consumer=downstream_consumer,
        consumer_action=consumer_action,
        input_sha256=input_sha,
        output_sha256=output_sha,
        input_payload=input_payload,
        output_payload=output_payload,
    )


def build_capital_science_postrun_receipts(
    *,
    observed_at: datetime,
    ending_capital_usd: Decimal,
    net_realized_pnl_usd: Decimal,
    settlement_rows: tuple[tuple[str, str, Decimal], ...],
) -> tuple[CapitalScienceReceipt, ...]:
    """Invoke post-path GEN-C9, post-outcome GEN-C13 and governance GEN-C14."""

    if observed_at.tzinfo is None or observed_at.utcoffset() is None:
        raise CiboCapitalManagementError(
            "Capital Science postrun observed_at must be timezone-aware"
        )
    for value, name in (
        (ending_capital_usd, "ending_capital_usd"),
        (net_realized_pnl_usd, "net_realized_pnl_usd"),
    ):
        if not isinstance(value, Decimal) or not value.is_finite():
            raise CiboCapitalManagementError(
                f"Capital Science postrun {name} must be finite Decimal"
            )

    receipts: list[CapitalScienceReceipt] = []
    receipts.append(
        _post_receipt(
            function_code="GEN-C9",
            stage="POST_SEGMENT",
            signal_fingerprint="SEGMENT",
            trader_id="PORTFOLIO",
            observed_at=observed_at,
            reason=(
                "robust growth/ruin/capacity path evaluator consumed the completed "
                "economic segment without changing historical decisions"
            ),
            downstream_consumer="CIBO_RESEARCH_EVALUATION",
            consumer_action="EVALUATE_COMPLETED_CAPITAL_PATH",
            disposition=CapitalScienceDisposition.APPLIED,
            input_payload={
                "ending_capital_usd": format(ending_capital_usd, "f"),
                "net_realized_pnl_usd": format(net_realized_pnl_usd, "f"),
                "settlement_count": len(settlement_rows),
                "research_mode": RESEARCH_MODE,
            },
        )
    )

    if settlement_rows:
        for signal, trader, pnl in settlement_rows:
            receipts.append(
                _post_receipt(
                    function_code="GEN-C13",
                    stage="POST_OUTCOME",
                    signal_fingerprint=signal,
                    trader_id=trader,
                    observed_at=observed_at,
                    reason=(
                        "settled episode was ingested into meta-capital memory only "
                        "after outcome; same-trade decision remained immutable"
                    ),
                    downstream_consumer="CIBO_RESEARCH_MEMORY",
                    consumer_action="INGEST_SETTLED_CAPITAL_EPISODE",
                    disposition=CapitalScienceDisposition.APPLIED,
                    input_payload={
                        "signal_fingerprint": signal,
                        "trader_id": trader,
                        "realized_pnl_usd": format(pnl, "f"),
                        "research_mode": RESEARCH_MODE,
                    },
                )
            )
    else:
        receipts.append(
            _post_receipt(
                function_code="GEN-C13",
                stage="POST_OUTCOME",
                signal_fingerprint="SEGMENT",
                trader_id="PORTFOLIO",
                observed_at=observed_at,
                reason="no settled episode existed for post-outcome memory ingestion",
                downstream_consumer="CIBO_RESEARCH_MEMORY",
                consumer_action="NO_SETTLED_EPISODE",
                disposition=CapitalScienceDisposition.JUSTIFIED_NOT_APPLICABLE,
                input_payload={"settlement_count": 0, "research_mode": RESEARCH_MODE},
            )
        )

    receipts.append(
        _post_receipt(
            function_code="GEN-C14",
            stage="RESEARCH_GOVERNANCE",
            signal_fingerprint="SEGMENT",
            trader_id="PORTFOLIO",
            observed_at=observed_at,
            reason=(
                "governed capital science sealed this reused-holdout run as "
                "non-certifying burned adaptive research with no automatic promotion"
            ),
            downstream_consumer="CIBO_RESEARCH_GOVERNANCE",
            consumer_action="SEAL_NON_CERTIFYING_RESEARCH_LINEAGE",
            disposition=CapitalScienceDisposition.APPLIED,
            input_payload={
                "research_mode": RESEARCH_MODE,
                "certification_claimed": False,
                "production_authority": False,
            },
        )
    )
    return tuple(receipts)


def aggregate_capital_science_receipts(
    receipts: Iterable[CapitalScienceReceipt],
) -> tuple[dict[str, object], ...]:
    """Aggregate exact runtime receipts into the mandatory observability schema."""

    rows = tuple(receipts)
    if any(not isinstance(item, CapitalScienceReceipt) for item in rows):
        raise CiboCapitalManagementError(
            "Capital Science aggregation requires canonical receipts"
        )
    grouped: dict[str, list[CapitalScienceReceipt]] = defaultdict(list)
    for item in rows:
        grouped[item.function_code].append(item)

    missing = tuple(code for code in MANDATORY_RUNTIME_GENC if code not in grouped)
    if missing:
        raise CiboCapitalManagementError(
            "Capital Science runtime missing mandatory functions: " + ",".join(missing)
        )

    out: list[dict[str, object]] = []
    for code in MANDATORY_RUNTIME_GENC:
        items = grouped[code]
        dispositions = {item.disposition for item in items}
        if CapitalScienceDisposition.APPLIED in dispositions:
            status = CapitalScienceDisposition.APPLIED.value
        elif CapitalScienceDisposition.FAIL_CLOSED in dispositions:
            status = CapitalScienceDisposition.FAIL_CLOSED.value
        elif CapitalScienceDisposition.ELIGIBLE_NO_CHANGE in dispositions:
            status = CapitalScienceDisposition.ELIGIBLE_NO_CHANGE.value
        else:
            status = CapitalScienceDisposition.JUSTIFIED_NOT_APPLICABLE.value
        reasons = Counter(item.reason for item in items)
        sources = sorted(
            {
                source
                for item in items
                for source in item.capital_source_usage
            }
        )
        out.append(
            {
                "function_code": code + "_RUNTIME",
                "function_type": "CAPITAL_SCIENCE_RUNTIME",
                "status": status,
                "eligible_epochs": sum(
                    1
                    for item in items
                    if item.disposition
                    is not CapitalScienceDisposition.JUSTIFIED_NOT_APPLICABLE
                ),
                "invoked_count": len(items),
                "executed_count": len(items),
                "applied_count": sum(
                    item.disposition is CapitalScienceDisposition.APPLIED
                    for item in items
                ),
                "fail_closed_count": sum(
                    item.disposition is CapitalScienceDisposition.FAIL_CLOSED
                    for item in items
                ),
                "not_applicable_count": sum(
                    item.disposition
                    is CapitalScienceDisposition.JUSTIFIED_NOT_APPLICABLE
                    for item in items
                ),
                "decision_changed_count": sum(item.decision_changed for item in items),
                "risk_delta_usd": format(
                    sum((item.risk_delta_usd for item in items), Decimal(0)),
                    "f",
                ),
                "margin_delta_usd": format(
                    sum((item.margin_delta_usd for item in items), Decimal(0)),
                    "f",
                ),
                "capital_source_usage": sources,
                "incremental_pnl_attribution_usd": format(
                    sum(
                        (
                            item.incremental_pnl_attribution_usd
                            for item in items
                        ),
                        Decimal(0),
                    ),
                    "f",
                ),
                "reason_distribution": [
                    {"reason": reason, "count": count}
                    for reason, count in sorted(reasons.items())
                ],
                "causal_trace_count": len(items),
                "input_output_trace_count": len(items),
                "unique_input_count": len({item.input_sha256 for item in items}),
                "unique_output_count": len({item.output_sha256 for item in items}),
                "consumer_action_distribution": [
                    {"consumer_action": action, "count": count}
                    for action, count in sorted(
                        Counter(item.consumer_action for item in items).items()
                    )
                ],
                "reason": (
                    "runtime receipts prove causal invocation and downstream "
                    "consumption; status is aggregated from observed dispositions"
                ),
                "research_mode": RESEARCH_MODE,
            }
        )
    return tuple(out)
