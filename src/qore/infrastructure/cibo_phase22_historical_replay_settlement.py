"""Versioned counterfactual settlement for the historical Phase22 holdout.

No broker order/deal/position identifier is created for historical events.
Structural PnL comes from frozen Trader replay; the provider execution adjustment
is supplied by a separately frozen empirical calibration model and applied once.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import datetime
from decimal import Decimal
from typing import Any

from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)
from qore.infrastructure.cibo_ce2i_phase20_forward_store import (
    Phase20ForwardDecisionSeal,
)
from qore.infrastructure.cibo_phase22_historical_replay_economics_amendment import (
    EXECUTION_ECONOMICS_KIND,
    Phase22HistoricalReplayEconomicsAmendment,
)

_REPLAY_SCHEMA = "qore.cibo.phase22.historical-replay-settlement.v1"


def _finite(value: Decimal, name: str) -> None:
    if not isinstance(value, Decimal) or not value.is_finite():
        raise CiboCapitalManagementError(
            f"Phase22 replay settlement {name} must be finite Decimal"
        )


@dataclass(frozen=True, slots=True)
class Phase22HistoricalReplayOutcomeSeal:
    evidence_id: str
    decision_evidence_sha256: str
    signal_fingerprint: str
    trader_id: str
    qore_symbol: str
    observed_at: datetime
    gross_structural_outcome_r: Decimal
    provider_execution_adjustment_usd: Decimal
    decision_provider_cost_proxy_usd: Decimal
    realized_net_pnl_usd: Decimal
    executed_initial_stop_risk_usd: Decimal
    realized_structural_outcome_r: Decimal
    capital_deployed_at: datetime
    capital_released_at: datetime
    capital_minutes: Decimal
    provider_calibration_sha256: str
    amendment_sha256: str
    execution_economics_kind: str
    counterfactual_historical_replay: bool
    historical_broker_fills_claimed: bool
    fabricated_execution_evidence_used: bool
    outcome_reconciled: bool

    def __post_init__(self) -> None:
        if not self.evidence_id.startswith("phase22-replay-outcome:"):
            raise CiboCapitalManagementError(
                "Phase22 replay settlement evidence id drift"
            )
        if (
            not self.decision_evidence_sha256.startswith("sha256:")
            or len(self.decision_evidence_sha256) != 71
        ):
            raise CiboCapitalManagementError(
                "Phase22 replay settlement decision digest invalid"
            )
        if not self.signal_fingerprint or not self.trader_id or not self.qore_symbol:
            raise CiboCapitalManagementError(
                "Phase22 replay settlement lineage identity required"
            )
        for name in (
            "gross_structural_outcome_r",
            "provider_execution_adjustment_usd",
            "decision_provider_cost_proxy_usd",
            "realized_net_pnl_usd",
            "executed_initial_stop_risk_usd",
            "realized_structural_outcome_r",
            "capital_minutes",
        ):
            _finite(getattr(self, name), name)
        if self.executed_initial_stop_risk_usd <= 0:
            raise CiboCapitalManagementError(
                "Phase22 replay settlement executed risk must be positive"
            )
        if self.provider_execution_adjustment_usd < 0:
            raise CiboCapitalManagementError(
                "Phase22 replay settlement provider adjustment cannot be negative"
            )
        if self.decision_provider_cost_proxy_usd < 0:
            raise CiboCapitalManagementError(
                "Phase22 replay settlement provider proxy cannot be negative"
            )
        expected_gross = (
            self.gross_structural_outcome_r
            * self.executed_initial_stop_risk_usd
        )
        expected_net = expected_gross - self.provider_execution_adjustment_usd
        if self.realized_net_pnl_usd != expected_net:
            raise CiboCapitalManagementError(
                "Phase22 replay settlement net PnL identity drift"
            )
        if self.realized_structural_outcome_r != self.gross_structural_outcome_r:
            raise CiboCapitalManagementError(
                "Phase22 replay settlement structural-R identity drift"
            )
        for name, value in (
            ("observed_at", self.observed_at),
            ("capital_deployed_at", self.capital_deployed_at),
            ("capital_released_at", self.capital_released_at),
        ):
            if value.tzinfo is None or value.utcoffset() is None:
                raise CiboCapitalManagementError(
                    f"Phase22 replay settlement {name} must be timezone-aware"
                )
        if self.capital_released_at <= self.capital_deployed_at:
            raise CiboCapitalManagementError(
                "Phase22 replay settlement release must follow deployment"
            )
        if self.capital_released_at > self.observed_at:
            raise CiboCapitalManagementError(
                "Phase22 replay settlement release cannot postdate outcome"
            )
        expected_minutes = Decimal(
            str(
                (
                    self.capital_released_at - self.capital_deployed_at
                ).total_seconds()
            )
        ) / Decimal("60")
        if self.capital_minutes != expected_minutes or self.capital_minutes <= 0:
            raise CiboCapitalManagementError(
                "Phase22 replay settlement capital-minutes identity drift"
            )
        for name in ("provider_calibration_sha256", "amendment_sha256"):
            value = getattr(self, name)
            if not value.startswith("sha256:") or len(value) != 71:
                raise CiboCapitalManagementError(
                    f"Phase22 replay settlement {name} invalid"
                )
        if self.execution_economics_kind != EXECUTION_ECONOMICS_KIND:
            raise CiboCapitalManagementError(
                "Phase22 replay settlement economics-kind drift"
            )
        if not self.counterfactual_historical_replay:
            raise CiboCapitalManagementError(
                "Phase22 replay settlement must be explicitly counterfactual"
            )
        if self.historical_broker_fills_claimed:
            raise CiboCapitalManagementError(
                "Phase22 replay settlement cannot claim historical broker fills"
            )
        if self.fabricated_execution_evidence_used:
            raise CiboCapitalManagementError(
                "Phase22 replay settlement cannot fabricate execution evidence"
            )
        if not self.outcome_reconciled:
            raise CiboCapitalManagementError(
                "Phase22 replay settlement must be reconciled"
            )

    def as_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        for key in (
            "gross_structural_outcome_r",
            "provider_execution_adjustment_usd",
            "decision_provider_cost_proxy_usd",
            "realized_net_pnl_usd",
            "executed_initial_stop_risk_usd",
            "realized_structural_outcome_r",
            "capital_minutes",
        ):
            payload[key] = format(getattr(self, key), "f")
        for key in ("observed_at", "capital_deployed_at", "capital_released_at"):
            payload[key] = getattr(self, key).isoformat()
        payload["schema"] = _REPLAY_SCHEMA
        return payload

    def fingerprint(self) -> str:
        raw = json.dumps(
            self.as_dict(),
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        ).encode("utf-8")
        return "sha256:" + hashlib.sha256(raw).hexdigest()


@dataclass(frozen=True, slots=True)
class VersionedPhase22HistoricalReplayEvidenceBook:
    generation: int
    amendment_sha256: str
    decisions: tuple[Phase20ForwardDecisionSeal, ...]
    outcomes: tuple[Phase22HistoricalReplayOutcomeSeal, ...]

    def __post_init__(self) -> None:
        if (
            not isinstance(self.generation, int)
            or isinstance(self.generation, bool)
            or self.generation < 0
        ):
            raise CiboCapitalManagementError(
                "Phase22 replay evidence generation invalid"
            )
        if not self.amendment_sha256.startswith("sha256:"):
            raise CiboCapitalManagementError(
                "Phase22 replay evidence amendment digest invalid"
            )
        decision_shas = tuple(item.evidence_sha256 for item in self.decisions)
        if len(decision_shas) != len(set(decision_shas)):
            raise CiboCapitalManagementError(
                "Phase22 replay evidence duplicate decision"
            )
        decision_by_sha = {
            item.evidence_sha256: item for item in self.decisions
        }
        keys: set[tuple[str, str]] = set()
        for outcome in self.outcomes:
            key = (
                outcome.decision_evidence_sha256,
                outcome.signal_fingerprint,
            )
            if key in keys:
                raise CiboCapitalManagementError(
                    "Phase22 replay evidence duplicate outcome"
                )
            keys.add(key)
            decision = decision_by_sha.get(outcome.decision_evidence_sha256)
            if decision is None:
                raise CiboCapitalManagementError(
                    "Phase22 replay outcome has no sealed decision"
                )
            if outcome.signal_fingerprint not in decision.signal_fingerprints:
                raise CiboCapitalManagementError(
                    "Phase22 replay outcome signal not sealed pre-decision"
                )
            if outcome.observed_at <= decision.decision_at:
                raise CiboCapitalManagementError(
                    "Phase22 replay outcome must follow decision"
                )
            if outcome.amendment_sha256 != self.amendment_sha256:
                raise CiboCapitalManagementError(
                    "Phase22 replay outcome amendment lineage drift"
                )


def build_phase22_historical_replay_outcome(
    *,
    amendment: Phase22HistoricalReplayEconomicsAmendment,
    decision: Phase20ForwardDecisionSeal,
    signal_fingerprint: str,
    trader_id: str,
    qore_symbol: str,
    observed_at: datetime,
    gross_structural_outcome_r: Decimal,
    executed_initial_stop_risk_usd: Decimal,
    provider_execution_adjustment_usd: Decimal,
    decision_provider_cost_proxy_usd: Decimal,
    capital_deployed_at: datetime,
    capital_released_at: datetime,
) -> Phase22HistoricalReplayOutcomeSeal:
    if not isinstance(amendment, Phase22HistoricalReplayEconomicsAmendment):
        raise CiboCapitalManagementError(
            "Phase22 replay settlement requires canonical amendment"
        )
    if not isinstance(decision, Phase20ForwardDecisionSeal):
        raise CiboCapitalManagementError(
            "Phase22 replay settlement requires canonical decision seal"
        )
    if signal_fingerprint not in decision.signal_fingerprints:
        raise CiboCapitalManagementError(
            "Phase22 replay settlement signal was not sealed pre-decision"
        )
    for value, name in (
        (gross_structural_outcome_r, "gross_structural_outcome_r"),
        (executed_initial_stop_risk_usd, "executed_initial_stop_risk_usd"),
        (provider_execution_adjustment_usd, "provider_execution_adjustment_usd"),
        (decision_provider_cost_proxy_usd, "decision_provider_cost_proxy_usd"),
    ):
        _finite(value, name)
    gross = gross_structural_outcome_r * executed_initial_stop_risk_usd
    net = gross - provider_execution_adjustment_usd
    minutes = Decimal(
        str((capital_released_at - capital_deployed_at).total_seconds())
    ) / Decimal("60")
    raw = json.dumps(
        {
            "decision_evidence_sha256": decision.evidence_sha256,
            "signal_fingerprint": signal_fingerprint,
            "trader_id": trader_id,
            "qore_symbol": qore_symbol,
            "observed_at": observed_at.isoformat(),
            "gross_structural_outcome_r": format(
                gross_structural_outcome_r, "f"
            ),
            "provider_execution_adjustment_usd": format(
                provider_execution_adjustment_usd, "f"
            ),
            "executed_initial_stop_risk_usd": format(
                executed_initial_stop_risk_usd, "f"
            ),
            "provider_calibration_sha256": amendment.provider_calibration_sha256,
            "amendment_sha256": amendment.fingerprint(),
        },
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("utf-8")
    evidence_id = "phase22-replay-outcome:" + hashlib.sha256(raw).hexdigest()
    return Phase22HistoricalReplayOutcomeSeal(
        evidence_id=evidence_id,
        decision_evidence_sha256=decision.evidence_sha256,
        signal_fingerprint=signal_fingerprint,
        trader_id=trader_id,
        qore_symbol=qore_symbol,
        observed_at=observed_at,
        gross_structural_outcome_r=gross_structural_outcome_r,
        provider_execution_adjustment_usd=provider_execution_adjustment_usd,
        decision_provider_cost_proxy_usd=decision_provider_cost_proxy_usd,
        realized_net_pnl_usd=net,
        executed_initial_stop_risk_usd=executed_initial_stop_risk_usd,
        realized_structural_outcome_r=gross_structural_outcome_r,
        capital_deployed_at=capital_deployed_at,
        capital_released_at=capital_released_at,
        capital_minutes=minutes,
        provider_calibration_sha256=amendment.provider_calibration_sha256,
        amendment_sha256=amendment.fingerprint(),
        execution_economics_kind=EXECUTION_ECONOMICS_KIND,
        counterfactual_historical_replay=True,
        historical_broker_fills_claimed=False,
        fabricated_execution_evidence_used=False,
        outcome_reconciled=True,
    )
